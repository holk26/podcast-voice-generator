"""Endpoints exclusivos para el worker local.

Todas las rutas requieren el token estático compartido entre backend y worker.
"""

import asyncio
import json
import shutil
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import require_worker_token
from backend.app.models import Episode
from backend.app.services import worker_service
from shared.config import OUTPUT_DIR
from shared.schemas import WorkerJob, WorkerJobCompleteRequest, WorkerJobFailRequest

router = APIRouter(prefix="/worker", tags=["worker"])
WORKER_SSE_KEEPALIVE_SECONDS = 30.0


def _episode_to_job(episode: Episode) -> WorkerJob:
    return WorkerJob(
        episode_id=episode.id,
        title=episode.title,
        type=episode.type,
        source_text=episode.source_text,
        voice_id=episode.voice_id,
        target_duration_minutes=episode.target_duration_minutes,
    )


@router.get("/jobs/next", response_model=WorkerJob)
def next_job(
    db: Session = Depends(get_db),
    token: str = Depends(require_worker_token),
):
    episode = worker_service.claim_next_pending(db)
    if episode is None:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)
    return _episode_to_job(episode)


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
