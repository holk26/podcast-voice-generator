"""Lógica de negocio para la comunicación backend ↔ worker.

El backend expone trabajos pendientes (episodios) y el worker los reclama,
los procesa y reporta el resultado. El servicio también notifica a los
listeners SSE cuando aparece un nuevo trabajo.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models import Episode


# Cola global para notificaciones SSE a workers conectados.
# En un despliegue con múltiples réplicas del backend esto requeriría un
# broker real (Redis, RabbitMQ, etc.); para una sola instancia es suficiente.
_sse_listeners: set[asyncio.Queue] = set()


def notify_new_job() -> None:
    """Notifica a todos los workers conectados vía SSE que hay trabajo nuevo."""
    for queue in list(_sse_listeners):
        try:
            queue.put_nowait({"type": "new_job"})
        except asyncio.QueueFull:
            pass


def register_listener(queue: asyncio.Queue) -> None:
    _sse_listeners.add(queue)


def unregister_listener(queue: asyncio.Queue) -> None:
    _sse_listeners.discard(queue)


def claim_next_pending(db: Session) -> Optional[Episode]:
    """Reclama atómicamente el episodio pendiente más antiguo.

    Usa `with_for_update()` para evitar que dos workers procesen el mismo
    episodio simultáneamente.
    """
    episode = (
        db.query(Episode)
        .filter(Episode.status == "pending")
        .order_by(Episode.created_at)
        .with_for_update()
        .first()
    )
    if episode is None:
        return None

    episode.status = "running"
    episode.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(episode)
    return episode


def mark_completed(db: Session, episode_id: int, audio_url: str) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise ValueError(f"Episode {episode_id} not found")
    episode.status = "completed"
    episode.audio_url = audio_url
    episode.error_message = None
    episode.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(episode)
    return episode


def mark_failed(db: Session, episode_id: int, error: str) -> Episode:
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None:
        raise ValueError(f"Episode {episode_id} not found")
    episode.status = "failed"
    episode.error_message = error[:500]
    episode.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(episode)
    return episode
