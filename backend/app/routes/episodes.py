from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import time
from web_api.database import get_db, SessionLocal
from web_api.models import Episode
from web_api.schemas import EpisodeCreate, EpisodeResponse

router = APIRouter()


@router.get("", response_model=List[EpisodeResponse])
def list_episodes(db: Session = Depends(get_db)):
    return db.query(Episode).order_by(Episode.created_at.desc()).all()


@router.get("/{episode_id}", response_model=EpisodeResponse)
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.get("/{episode_id}/events")
def episode_events(episode_id: int):
    db = SessionLocal()
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        db.close()
        raise HTTPException(status_code=404, detail="Episode not found")

    def event_generator():
        try:
            while True:
                db.refresh(episode)
                payload = {
                    "id": episode.id,
                    "status": episode.status,
                    "audio_url": episode.audio_url,
                    "error_message": episode.error_message,
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if episode.status in ("completed", "failed"):
                    break
                time.sleep(2)
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=EpisodeResponse, status_code=201)
def create_episode(request: EpisodeCreate, db: Session = Depends(get_db)):
    episode = Episode(**request.model_dump())
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


@router.put("/{episode_id}", response_model=EpisodeResponse)
def update_episode(episode_id: int, request: EpisodeCreate, db: Session = Depends(get_db)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    for key, value in request.model_dump().items():
        setattr(episode, key, value)
    db.commit()
    db.refresh(episode)
    return episode


@router.delete("/{episode_id}", status_code=204)
def delete_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    db.delete(episode)
    db.commit()
    return None


@router.post("/{episode_id}/retry", response_model=EpisodeResponse)
def retry_episode(episode_id: int, db: Session = Depends(get_db)):
    """Reintenta un episodio fallido poniéndolo de nuevo en pending."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.status != "failed":
        raise HTTPException(status_code=400, detail="Solo se pueden reintentar episodios fallidos")
    episode.status = "pending"
    episode.error_message = None
    episode.audio_url = None
    db.commit()
    db.refresh(episode)
    return episode


@router.post("/{episode_id}/publish", response_model=EpisodeResponse)
def publish_episode(episode_id: int, db: Session = Depends(get_db)):
    """Marca manualmente el episodio como publicado (guarda la fecha)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.status != "completed":
        raise HTTPException(status_code=409, detail="Solo se pueden publicar episodios completados")
    episode.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(episode)
    return episode


@router.post("/{episode_id}/unpublish", response_model=EpisodeResponse)
def unpublish_episode(episode_id: int, db: Session = Depends(get_db)):
    """Quita la marca de publicado (reversible)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    episode.published_at = None
    db.commit()
    db.refresh(episode)
    return episode
