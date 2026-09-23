"""Lógica de negocio para la comunicación backend ↔ worker.

El backend expone trabajos pendientes (episodios) y el worker los reclama,
los procesa y reporta el resultado. El servicio también notifica a los
listeners SSE cuando aparece un nuevo trabajo.

Recuperación de trabajos atascados: un episodio en `running` cuyo `updated_at`
supere el lease (WORKER_LEASE_MINUTES, default 45) se considera huérfano
(el worker murió a mitad) y vuelve a `pending` automáticamente en el
siguiente claim. El worker envía heartbeats durante el procesamiento para
renovar el lease, así un episodio legítimamente largo no se reencola.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models import Episode


# Lease de un episodio en running: sin heartbeats del worker durante este
# tiempo, el episodio se considera huérfano y se reencola.
LEASE_MINUTES = float(os.getenv("WORKER_LEASE_MINUTES", "45"))


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


def reap_stale_running(db: Session) -> list[int]:
    """Reencola episodios `running` huérfanos (worker muerto a mitad).

    Un episodio es huérfano si lleva más de LEASE_MINUTES sin heartbeat
    (updated_at). Devuelve los ids reencolados y notifica por SSE.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LEASE_MINUTES)
    stale = (
        db.query(Episode)
        .filter(Episode.status == "running", Episode.updated_at < cutoff)
        .with_for_update()
        .all()
    )
    requeued: list[int] = []
    for episode in stale:
        episode.status = "pending"
        episode.error_message = "Reencolado: el worker perdió el lease (sin heartbeats)"
        episode.updated_at = datetime.now(timezone.utc)
        requeued.append(episode.id)
    if requeued:
        db.commit()
        for episode_id in requeued:
            notify_new_job()
    return requeued


def touch_running(db: Session, episode_id: int) -> Optional[Episode]:
    """Heartbeat del worker: renueva el lease de un episodio en running."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if episode is None or episode.status != "running":
        return None
    episode.updated_at = datetime.now(timezone.utc)
    db.commit()
    return episode


def claim_next_pending(db: Session) -> Optional[Episode]:
    """Reclama atómicamente el episodio pendiente más antiguo.

    Usa `with_for_update()` para evitar que dos workers procesen el mismo
    episodio simultáneamente. Antes de reclamar, reencola episodios
    `running` huérfanos para que no se queden atascados si el worker muere.
    """
    reap_stale_running(db)
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
