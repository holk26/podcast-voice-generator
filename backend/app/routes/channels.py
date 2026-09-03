import re
from pathlib import Path
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Channel, ContentPlanEntry, Episode
from backend.app.services import worker_service
from shared.schemas import (
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    EpisodeResponse,
    PlanEntryCreate,
    PlanEntryResponse,
)
from backend.app.services.crew_service import suggest_channel, improve_channel_prompt
from backend.app.services.automation_service import start_plan_job, start_script_job, start_raw_script_job, start_season_job, autopilot_tick


class ChannelSuggestRequest(BaseModel):
    hint: str | None = None


class CreateFromTextRequest(BaseModel):
    source_text: str
    title: str | None = None

router = APIRouter()


@router.get("", response_model=List[ChannelResponse])
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(Channel).order_by(Channel.created_at.desc()).all()
    result = []
    for ch in channels:
        total = (
            db.query(ContentPlanEntry)
            .filter(ContentPlanEntry.channel_id == ch.id)
            .count()
        )
        generated = (
            db.query(ContentPlanEntry)
            .filter(
                ContentPlanEntry.channel_id == ch.id,
                ContentPlanEntry.status == "generated",
            )
            .count()
        )
        resp = ChannelResponse.model_validate(ch)
        resp.entries_total = total
        resp.entries_generated = generated
        result.append(resp)
    return result


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


@router.post("/{channel_id}/improve-prompt")
def improve_prompt(channel_id: int, db: Session = Depends(get_db)):
    """El productor ejecutivo reescribe el brief de producción del canal
    (idioma, audiencia, tono, reglas) y lo guarda."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    try:
        brief = improve_channel_prompt(channel)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CrewAI error: {e}")
    channel.brief = brief
    db.commit()
    return {"brief": brief}


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


@router.post("/{channel_id}/publish", response_model=ChannelResponse)
def publish_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/{channel_id}/unpublish", response_model=ChannelResponse)
def unpublish_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.published_at = None
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/{channel_id}/plan", response_model=List[PlanEntryResponse])
def list_plan_entries(channel_id: int, db: Session = Depends(get_db)):
    entries = (
        db.query(ContentPlanEntry)
        .filter(ContentPlanEntry.channel_id == channel_id)
        .order_by(ContentPlanEntry.created_at.desc())
        .all()
    )
    result = []
    for entry in entries:
        resp = PlanEntryResponse.model_validate(entry)
        if entry.episode_id:
            episode = db.query(Episode).filter(Episode.id == entry.episode_id).first()
            if episode:
                resp.audio_url = episode.audio_url
                resp.episode_published_at = episode.published_at
        result.append(resp)
    return result


@router.post("/{channel_id}/plan/generate", status_code=202)
def generate_plan_entries(channel_id: int, count: int = 5, db: Session = Depends(get_db)):
    """Lanza la generación del plan en segundo plano y devuelve un job_id.

    El progreso del congreso de agentes se sigue en /api/jobs/{job_id}/events.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    count = max(1, min(count, 10))

    job_id = start_plan_job(channel, count=count)
    if job_id is None:
        raise HTTPException(status_code=409, detail="Ya hay un plan en generación para este canal")
    return {"job_id": job_id}


@router.post("/{channel_id}/season", status_code=202)
def generate_channel_season(channel_id: int, weeks: int = 4, db: Session = Depends(get_db)):
    """Lanza el showrunner: diseña una temporada completa (arco + episodios
    repartidos por semana) y devuelve un job_id."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    weeks = max(1, min(weeks, 12))

    job_id = start_season_job(channel, weeks=weeks)
    if job_id is None:
        raise HTTPException(status_code=409, detail="Ya hay una temporada en generación para este canal")
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


def _strip_markdown(text: str) -> str:
    """Limpia markup markdown básico para dejar texto hablable."""
    # Quita bloques de código
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Headers
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Bold e itálico
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", text)
    # Links: [texto](url) -> texto
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Imágenes
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Blockquotes y listas
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # Líneas horizontales
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def _create_episode_from_text(
    channel: Channel,
    content: str,
    fallback_filename: str | None,
    explicit_title: str | None,
    db: Session,
) -> Episode:
    """Crea un episodio y su entrada de plan a partir de texto limpio."""
    if not content.strip():
        raise HTTPException(status_code=400, detail="El texto está vacío")

    cleaned = _strip_markdown(content)
    if not cleaned.strip():
        raise HTTPException(status_code=400, detail="El texto no contiene contenido hablable")

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    fallback_title = lines[0][:120] if lines else (fallback_filename or "Episodio sin título")
    episode_title = (explicit_title.strip() if explicit_title else fallback_title) or fallback_title
    description = " ".join(lines[:3])[:250] if lines else ""

    episode = Episode(
        title=episode_title,
        type=channel.format,
        source_text=cleaned,
        voice_id=channel.default_voice_id,
        status="pending",
        target_duration_minutes=float(channel.target_minutes or 10),
        channel_id=channel.id,
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)

    entry = ContentPlanEntry(
        channel_id=channel.id,
        title=episode_title,
        description=description,
        status="generated",
        episode_id=episode.id,
    )
    db.add(entry)
    db.commit()

    worker_service.notify_new_job()
    return episode


@router.post("/{channel_id}/upload-script", response_model=EpisodeResponse, status_code=201)
def upload_script(
    channel_id: int,
    script: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Sube un archivo de guion directamente a un canal y crea el episodio en cola.

    Acepta .txt y .md. Si el archivo es markdown se limpia markup básico antes
    de guardar. Salta el planning y la generación de guion por IA.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    try:
        content = script.file.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo: {e}")
    finally:
        script.file.close()

    filename = Path(script.filename).stem if script.filename else None
    return _create_episode_from_text(channel, content, filename, title, db)


@router.post("/{channel_id}/create-from-text", response_model=EpisodeResponse, status_code=201)
def create_from_text(
    channel_id: int,
    request: CreateFromTextRequest,
    db: Session = Depends(get_db),
):
    """Crea un episodio a partir de texto pegado/editado manualmente."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return _create_episode_from_text(channel, request.source_text, None, request.title, db)


@router.post("/{channel_id}/script-jobs", status_code=202)
def create_script_job(
    channel_id: int,
    script: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Lanza el congreso de agentes sobre materia prima (txt/md o texto pegado).

    Devuelve 202 + job_id; el progreso se sigue en /api/jobs/{job_id}/events y
    el resultado (guion editable) llega en el evento final. No crea episodio:
    la UI lo crea con create-from-text tras la edición del usuario.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    raw_text = ""
    if script is not None:
        try:
            raw_text = script.file.read().decode("utf-8", errors="replace")
        finally:
            script.file.close()
        if not title and script.filename:
            title = Path(script.filename).stem
    elif text:
        raw_text = text

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No hay material: sube un .txt/.md o pega texto")

    title = (title or f"Episodio de {channel.name}").strip()
    minutes = max(2, min(int(channel.target_minutes or 10), 30))
    job_id = start_raw_script_job(channel, raw_text, title, minutes)
    if job_id is None:
        raise HTTPException(status_code=409, detail="Ya hay un guion en generación para este canal")
    return {"job_id": job_id}


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

    job_id = start_script_job(entry, minutes=minutes)
    if job_id is None:
        raise HTTPException(status_code=409, detail="Ya hay un guion en generación para esta entrada")
    return {"job_id": job_id}


@router.put("/plan/{entry_id}", response_model=PlanEntryResponse)
def update_plan_entry(entry_id: int, data: PlanEntryCreate, db: Session = Depends(get_db)):
    """Edita título, descripción y fecha programada de una entrada."""
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.title = data.title
    if data.description is not None:
        entry.description = data.description
    if data.scheduled_date is not None:
        entry.scheduled_date = data.scheduled_date
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


@router.post("/autopilot/tick")
def autopilot_tick_endpoint():
    """Ejecuta un tick del piloto automático en el backend.

    El worker puede llamar a este endpoint periódicamente para que el backend
    genere nuevas entradas de contenido sin necesidad de acceder a la BD.
    """
    launched = autopilot_tick()
    return {"launched": launched}
