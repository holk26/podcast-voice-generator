from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from web_api.database import get_db
from web_api.models import Channel, ContentPlanEntry, Episode
from web_api.schemas import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    PlanEntryCreate,
    PlanEntryResponse,
)
from web_api.services.crew_service import generate_plan, generate_script

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


@router.post("/{channel_id}/plan/generate", response_model=List[PlanEntryResponse])
def generate_plan_entries(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    try:
        proposed = generate_plan(channel, count=5)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CrewAI error: {e}")

    entries = []
    for item in proposed:
        entry = ContentPlanEntry(channel_id=channel.id, title=item.title, description=item.description)
        db.add(entry)
        entries.append(entry)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


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


@router.post("/plan/{entry_id}/approve", response_model=PlanEntryResponse)
def approve_plan_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=400, detail="Entry already processed")

    channel = db.query(Channel).filter(Channel.id == entry.channel_id).first()
    try:
        script = generate_script(channel, entry)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CrewAI error: {e}")

    episode = Episode(
        title=entry.title,
        type=channel.format,
        source_text=script,
        voice_id=channel.default_voice_id,
        status="pending",
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)

    entry.status = "generated"
    entry.episode_id = episode.id
    db.commit()
    db.refresh(entry)
    return entry


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
