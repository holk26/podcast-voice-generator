import time
import logging
from sqlalchemy.orm import Session
from web_api.database import SessionLocal
from web_api.models import Episode
from worker.handlers import handle_podcast_episode
from web_api.services.automation_service import autopilot_tick

logger = logging.getLogger(__name__)

AUTOPILOT_INTERVAL = 60.0  # segundos entre pasadas de piloto automático


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
            episode.status = "failed"
            episode.error_message = str(e)
            db.commit()
            logger.error(f"Episode {episode.id} failed: {e}")
    finally:
        db.close()


def run_loop(poll_interval: float = 2.0):
    last_tick = 0.0
    while True:
        process_pending_jobs()
        now = time.time()
        if now - last_tick >= AUTOPILOT_INTERVAL:
            last_tick = now
            try:
                launched = autopilot_tick()
                for job_id in launched:
                    logger.info(f"Autopilot lanzó job {job_id}")
            except Exception as e:
                logger.error(f"Autopilot tick falló: {e}")
        time.sleep(poll_interval)
