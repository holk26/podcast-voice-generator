import time
import logging
from sqlalchemy.orm import Session
from web_api.database import SessionLocal
from web_api.models import Episode
from worker.handlers import handle_podcast_episode

logger = logging.getLogger(__name__)


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
    while True:
        process_pending_jobs()
        time.sleep(poll_interval)
