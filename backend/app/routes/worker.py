"""Endpoints exclusivos para el worker local.

Todas las rutas requieren el token estático compartido entre backend y worker.
"""

import asyncio
import json
import os
import shutil
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import require_worker_token
from backend.app.models import Channel, Episode
from backend.app.services import worker_service
from backend.app.services.automation_service import autopilot_tick
from shared.config import OUTPUT_DIR
from shared.schemas import WorkerJob, WorkerJobCompleteRequest, WorkerJobFailRequest

router = APIRouter(prefix="/worker", tags=["worker"])
WORKER_SSE_KEEPALIVE_SECONDS = 30.0


def _episode_to_job(episode: Episode, db: Session) -> WorkerJob:
    channel = (
        db.query(Channel).filter(Channel.id == episode.channel_id).first()
        if episode.channel_id
        else None
    )
    return WorkerJob(
        episode_id=episode.id,
        title=episode.title,
        type=episode.type,
        source_text=episode.source_text,
        voice_id=episode.voice_id,
        target_duration_minutes=episode.target_duration_minutes,
        channel_id=episode.channel_id,
        speaker_voices=channel.speaker_voices if channel else None,
        intro_track=channel.intro_track if channel else None,
        bg_music=channel.bg_music if channel else None,
    )


@router.get("/jobs/next", response_model=WorkerJob)
def next_job(
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    episode = worker_service.claim_next_pending(db)
    if episode is None:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    return _episode_to_job(episode, db)


@router.post("/jobs/{episode_id}/complete", response_model=dict)
def complete_job(
    episode_id: int,
    request: WorkerJobCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    try:
        worker_service.mark_completed(db, episode_id, request.audio_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"status": "ok"}


@router.post("/jobs/{episode_id}/upload", response_model=dict)
def upload_job_audio(
    episode_id: int,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    """Recibe el audio generado por el worker y lo guarda en el volumen compartido del servidor."""
    episode_dir = OUTPUT_DIR / str(episode_id)
    episode_dir.mkdir(parents=True, exist_ok=True)

    # Nombre seguro: usa el nombre original o un default.
    filename = audio.filename or "final.mp3"
    file_path = episode_dir / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    audio_url = f"/outputs/{episode_id}/{filename}"
    return {"audio_url": audio_url}


MAX_PART_BYTES = 10 * 1024 * 1024


@router.post("/jobs/{episode_id}/upload-part/{part_number}", response_model=dict)
def upload_job_audio_part(
    episode_id: int,
    part_number: int,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    """Recibe una parte del audio (multipart) y la guarda en {OUTPUT_DIR}/{episode_id}/_parts/."""
    if part_number < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="part_number debe ser >= 0")

    parts_dir = OUTPUT_DIR / str(episode_id) / "_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    file_path = parts_dir / f"part_{part_number:04d}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    if file_path.stat().st_size > MAX_PART_BYTES:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"La parte supera el límite de {MAX_PART_BYTES} bytes",
        )

    return {"part": part_number, "size": file_path.stat().st_size}


class AssembleRequest(BaseModel):
    filename: str = "final.mp3"
    parts: int = Field(..., ge=1)


@router.post("/jobs/{episode_id}/assemble", response_model=dict)
def assemble_job_audio(
    episode_id: int,
    request: AssembleRequest,
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    """Concatena las partes 0..N-1 en {OUTPUT_DIR}/{episode_id}/{filename} y limpia _parts/."""
    filename = os.path.basename(request.filename)
    if not filename or filename in (".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filename inválido")

    parts_dir = OUTPUT_DIR / str(episode_id) / "_parts"
    part_paths = [parts_dir / f"part_{n:04d}" for n in range(request.parts)]
    missing = [p.name for p in part_paths if not p.is_file()]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faltan partes: {missing}",
        )

    episode_dir = OUTPUT_DIR / str(episode_id)
    episode_dir.mkdir(parents=True, exist_ok=True)
    file_path = episode_dir / filename

    with open(file_path, "wb") as out:
        for part_path in part_paths:
            with open(part_path, "rb") as part:
                shutil.copyfileobj(part, out)

    shutil.rmtree(parts_dir, ignore_errors=True)

    audio_url = f"/outputs/{episode_id}/{filename}"
    return {"audio_url": audio_url}


@router.post("/jobs/{episode_id}/fail", response_model=dict)
def fail_job(
    episode_id: int,
    request: WorkerJobFailRequest,
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    try:
        worker_service.mark_failed(db, episode_id, request.error)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"status": "ok"}


async def _sse_event_stream() -> AsyncGenerator[str, None]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    worker_service.register_listener(queue)
    try:
        # Envia un evento inicial para confirmar conexión
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(
                    queue.get(), timeout=WORKER_SSE_KEEPALIVE_SECONDS
                )
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
    finally:
        worker_service.unregister_listener(queue)


@router.get("/events")
def worker_events(token: str = Depends(require_worker_token)):
    return StreamingResponse(
        _sse_event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/autopilot/tick", response_model=dict)
def worker_autopilot_tick(token: str = Depends(require_worker_token)):
    """El worker pide al backend que ejecute un tick del piloto automático.

    Esta ruta está protegida por el token estático del worker; no requiere JWT.
    """
    launched = autopilot_tick()
    return {"launched": launched}
