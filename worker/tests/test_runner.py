from unittest.mock import patch, AsyncMock
from pathlib import Path
from backend.app.database import SessionLocal, init_db
from backend.app.models import Episode
from worker.runner import process_pending_jobs

init_db()


def test_worker_processes_pending_episode():
    db = SessionLocal()
    db.query(Episode).filter(Episode.status == "pending").delete()
    db.commit()

    episode = Episode(
        title="Worker test",
        type="podcast",
        source_text="Hola mundo",
        voice_id="jorge",
        status="pending"
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    episode_id = episode.id
    db.close()

    async def fake_save(path: str) -> None:
        Path(path).touch()

    with patch("worker.handlers.edge_tts.Communicate") as mock_communicate:
        mock_instance = mock_communicate.return_value
        mock_instance.save = AsyncMock(side_effect=fake_save)
        process_pending_jobs()

        mock_communicate.assert_called_once()
        _, kwargs = mock_communicate.call_args
        assert kwargs["voice"] == "es-ES-AlvaroNeural"

    db = SessionLocal()
    updated = db.query(Episode).filter(Episode.id == episode_id).first()
    assert updated.status == "completed"
    assert updated.audio_url == f"/outputs/{episode_id}/final.mp3"
    from backend.app.config import OUTPUT_DIR
    assert (OUTPUT_DIR / str(episode_id) / "final.mp3").exists()
    db.close()
