import threading
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from web_api.database import get_db, SessionLocal
from web_api.models import Channel, ContentPlanEntry, Episode
from web_api.schemas import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    PlanEntryCreate,
    PlanEntryResponse,
)
from web_api.services.crew_service import generate_plan, generate_script, suggest_channel
from web_api.services.job_service import registry


class ChannelSuggestRequest(BaseModel):
    hint: str | None = None

router = APIRouter()


@router.get("", response_model=List[ChannelResponse])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).order_by(Channel.created_at.desc()).all()


@router.post("", response_model=ChannelResponse, status_code=201)
def create_channel(data: ChannelCreate, db: Session = Depends(get_db)):
    channel = Channel(**data.dict())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/suggest")
def suggest_channel_endpoint(data: ChannelSuggestRequest):
    """Propone un canal (name/description/niche/format) con IA."""
    try:
        return suggest_channel(data.hint)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CrewAI error: {e}")


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(channel_id: int, data: ChannelUpdate, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()


@router.post("/{channel_id}/activate", response_model=ChannelResponse)
def activate_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = True
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/{channel_id}/deactivate", response_model=ChannelResponse)
def deactivate_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = False
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/{channel_id}/plan", response_model=List[PlanEntryResponse])
def list_plan_entries(channel_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ContentPlanEntry)
        .filter(ContentPlanEntry.channel_id == channel_id)
        .order_by(ContentPlanEntry.created_at.desc())
        .all()
    )


@router.post("/{channel_id}/plan/generate", status_code=202)
def generate_plan_entries(channel_id: int, count: int = 5, db: Session = Depends(get_db)):
    """Lanza la generación del plan en segundo plano y devuelve un job_id.

    El progreso del congreso de agentes se sigue en /api/jobs/{job_id}/events.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    count = max(1, min(count, 10))

    job_id = registry.create("plan", detail=f"Plan editorial: {channel.name}")

    def work():
        session = SessionLocal()
        try:
            ch = session.query(Channel).filter(Channel.id == channel_id).first()
            proposed = generate_plan(
                ch,
                count=count,
                on_progress=lambda step, msg, content=None: registry.emit(
                    job_id, step, msg, content
                ),
            )
            for item in proposed:
                session.add(
                    ContentPlanEntry(
                        channel_id=channel_id,
                        title=item.title,
                        description=item.description,
                    )
                )
            session.commit()
            registry.emit(job_id, "done", f"Plan listo: {len(proposed)} ideas")
            registry.finish(job_id, {"channel_id": channel_id, "count": len(proposed)})
        except Exception as e:
            session.rollback()
            registry.fail(job_id, str(e))
        finally:
            session.close()

    threading.Thread(target=work, daemon=True).start()
    return {"job_id": job_id}


@router.post("/{channel_id}/plan", response_model=PlanEntryResponse, status_code=201)
def create_plan_entry(channel_id: int, data: PlanEntryCreate, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    entry = ContentPlanEntry(channel_id=channel.id, **data.dict())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/plan/{entry_id}/approve", status_code=202)
def approve_plan_entry(entry_id: int, minutes: int = 10, db: Session = Depends(get_db)):
    """Lanza la generación del guion en segundo plano y devuelve un job_id.

    El progreso del congreso (investigador → planificador → guionista por
    secciones → editor → director de voz) se sigue en /api/jobs/{job_id}/events.
    `minutes` fija la duración objetivo del episodio (~150 palabras/minuto).
    """
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=400, detail="Entry already processed")
    minutes = max(2, min(minutes, 30))

    job_id = registry.create("script", detail=f"Guion: {entry.title}")

    def work():
        session = SessionLocal()
        try:
            ent = session.query(ContentPlanEntry).filter(
                ContentPlanEntry.id == entry_id
            ).first()
            channel = session.query(Channel).filter(
                Channel.id == ent.channel_id
            ).first()
            script = generate_script(
                channel,
                ent,
                target_minutes=minutes,
                on_progress=lambda step, msg, content=None: registry.emit(
                    job_id, step, msg, content
                ),
            )
            episode = Episode(
                title=ent.title,
                type=channel.format,
                source_text=script,
                voice_id=channel.default_voice_id,
                status="pending",
            )
            session.add(episode)
            session.commit()
            session.refresh(episode)

            ent.status = "generated"
            ent.episode_id = episode.id
            session.commit()
            registry.emit(job_id, "done", f"Guion listo, episodio #{episode.id} en cola")
            registry.finish(
                job_id,
                {"entry_id": entry_id, "episode_id": episode.id,
                 "channel_id": ent.channel_id},
            )
        except Exception as e:
            session.rollback()
            registry.fail(job_id, str(e))
        finally:
            session.close()

    threading.Thread(target=work, daemon=True).start()
    return {"job_id": job_id}


@router.post("/plan/{entry_id}/reject", response_model=PlanEntryResponse)
def reject_plan_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.status = "rejected"
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/plan/{entry_id}", status_code=204)
def delete_plan_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
