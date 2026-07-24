import os
import time
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from web_api.database import SessionLocal
from web_api.models import Episode
from worker.handlers import handle_podcast_episode
from web_api.services.automation_service import autopilot_tick

logger = logging.getLogger(__name__)

# Hora local a la que se ejecuta la producción diaria de los canales en
# piloto automático (temporadas + guiones del día). Configurable por env.
AUTOPILOT_HOUR = int(os.getenv("AUTOPILOT_HOUR", "7"))


def process_pending_jobs():
    db = SessionLocal()
    try:
        db.begin()
        episode = (
            db.query(Episode)
            .filter(Episode.status == "pending")
            .order_by(Episode.created_at)
            .with_for_update()
            .first()
        )
        if not episode:
            db.rollback()
            return

        episode.status = "running"
        db.commit()
        logger.info(f"Processing episode {episode.id}")

        try:
            handle_podcast_episode(episode, db)
            logger.info(f"Episode {episode.id} completed")
        except Exception as e:
            # La sesión puede estar rota (p. ej. episodio borrado a mitad de
            # síntesis): rollback obligatorio antes de reintentar commit.
            db.rollback()
            try:
                fresh = db.query(Episode).filter(Episode.id == episode.id).first()
                if fresh is not None:
                    fresh.status = "failed"
                    fresh.error_message = str(e)[:500]
                    db.commit()
            except Exception as e2:
                db.rollback()
                logger.error(f"No se pudo marcar el episodio {episode.id} como failed: {e2}")
            logger.error(f"Episode {episode.id} failed: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"process_pending_jobs error: {e}")
    finally:
        db.close()


def _autopilot_due(last_run_date: str | None) -> bool:
    """True si hoy ya pasó la hora de ejecución y aún no se ha corrido hoy."""
    now = datetime.now()
    if now.hour < AUTOPILOT_HOUR:
        return False
    return last_run_date != now.date().isoformat()


def run_loop(poll_interval: float = 2.0):
    last_run_date: str | None = None
    while True:
        process_pending_jobs()
        if _autopilot_due(last_run_date):
            last_run_date = datetime.now().date().isoformat()
            try:
                launched = autopilot_tick()
                for job_id in launched:
                    logger.info(f"Autopilot diario lanzó job {job_id}")
            except Exception as e:
                logger.error(f"Autopilot tick falló: {e}")
        time.sleep(poll_interval)
