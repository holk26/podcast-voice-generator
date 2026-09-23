import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.database import SessionLocal, init_db
from backend.app.main import app
from backend.app.models import Episode

os.environ.setdefault("WORKER_TOKEN", "worker-test-token")

client = TestClient(app)


def _auth_headers():
    return {"Authorization": f"Bearer {os.environ['WORKER_TOKEN']}"}


class TestWorkerNextJob:
    def test_next_job_returns_pending_episode(self):
        db = SessionLocal()
        db.query(Episode).filter(Episode.status == "pending").delete()
        db.commit()

        episode = Episode(title="Worker API test", type="podcast", source_text="Hola", voice_id="jorge", status="pending")
        db.add(episode)
        db.commit()
        db.refresh(episode)
        episode_id = episode.id
        db.close()

        response = client.get("/api/worker/jobs/next", headers=_auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["episode_id"] == episode_id
        assert data["voice_id"] == "jorge"

        db = SessionLocal()
        updated = db.query(Episode).filter(Episode.id == episode_id).first()
        assert updated.status == "running"
        db.close()

    def test_next_job_empty_returns_204(self):
        db = SessionLocal()
        db.query(Episode).filter(Episode.status == "pending").delete()
        db.commit()
        db.close()

        response = client.get("/api/worker/jobs/next", headers=_auth_headers())
        assert response.status_code == 204

    def test_next_job_requires_token(self):
        response = client.get("/api/worker/jobs/next")
        assert response.status_code == 401

    def test_next_job_includes_channel_voice_and_music_config(self):
        from backend.app.models import Channel

        db = SessionLocal()
        db.query(Episode).filter(Episode.status == "pending").delete()
        channel = Channel(
            name="Canal worker cfg",
            format="podcast",
            default_voice_id="clone:eduardo_aponte",
            num_speakers=2,
            speaker_voices={"Yolis": "clone:yolis"},
            intro_track="intro noticias.mp3",
            bg_music="none",
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        channel_id = channel.id
        episode = Episode(
            title="Ep cfg",
            type="podcast",
            source_text="EDUARDO: Hola.\n\nYOLIS: Buenas.",
            voice_id=channel.default_voice_id,
            status="pending",
            channel_id=channel_id,
        )
        db.add(episode)
        db.commit()
        db.refresh(episode)
        episode_id = episode.id
        db.close()

        response = client.get("/api/worker/jobs/next", headers=_auth_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["episode_id"] == episode_id
        assert data["channel_id"] == channel_id
        assert data["speaker_voices"] == {"Yolis": "clone:yolis"}
        assert data["intro_track"] == "intro noticias.mp3"
        assert data["bg_music"] == "none"


class TestWorkerCompleteFail:
    def test_complete_and_fail_job(self):
        db = SessionLocal()
        episode = Episode(title="Complete test", type="podcast", source_text="Hola", voice_id="jorge", status="running")
        db.add(episode)
        db.commit()
        db.refresh(episode)
        episode_id = episode.id
        db.close()

        response = client.post(
            f"/api/worker/jobs/{episode_id}/complete",
            json={"audio_url": "/outputs/123/final.mp3"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200

        db = SessionLocal()
        updated = db.query(Episode).filter(Episode.id == episode_id).first()
        assert updated.status == "completed"
        assert updated.audio_url == "/outputs/123/final.mp3"
        db.close()

        response = client.post(
            f"/api/worker/jobs/{episode_id}/fail",
            json={"error": "something went wrong"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200

        db = SessionLocal()
        updated = db.query(Episode).filter(Episode.id == episode_id).first()
        assert updated.status == "failed"
        assert "something went wrong" in updated.error_message
        db.close()

    def test_complete_missing_job_returns_404(self):
        response = client.post(
            "/api/worker/jobs/999999/complete",
            json={"audio_url": "/outputs/123/final.mp3"},
            headers=_auth_headers(),
        )
        assert response.status_code == 404


class TestWorkerLeaseRecovery:
    def test_stale_running_gets_requeued_and_claimed(self):
        """Un running huérfano (sin heartbeat en >45 min) se reencola solo."""
        from datetime import datetime, timedelta, timezone
        from backend.app.services import worker_service

        db = SessionLocal()
        db.query(Episode).filter(Episode.status == "pending").delete()
        stale = Episode(
            title="Running huérfano",
            type="podcast",
            source_text="Hola",
            voice_id="jorge",
            status="running",
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=worker_service.LEASE_MINUTES + 5),
        )
        db.add(stale)
        db.commit()
        db.refresh(stale)
        stale_id = stale.id
        db.close()

        response = client.get("/api/worker/jobs/next", headers=_auth_headers())
        assert response.status_code == 200
        assert response.json()["episode_id"] == stale_id

    def test_fresh_running_survives_claim(self):
        """Un running con heartbeat reciente NO se reencola."""
        from datetime import datetime, timezone

        db = SessionLocal()
        db.query(Episode).filter(Episode.status == "pending").delete()
        fresh = Episode(
            title="Running vivo",
            type="podcast",
            source_text="Hola",
            voice_id="jorge",
            status="running",
            updated_at=datetime.now(timezone.utc),
        )
        db.add(fresh)
        db.commit()
        db.refresh(fresh)
        fresh_id = fresh.id
        db.close()

        response = client.get("/api/worker/jobs/next", headers=_auth_headers())
        assert response.status_code == 204

        db = SessionLocal()
        still = db.query(Episode).filter(Episode.id == fresh_id).first()
        assert still.status == "running"
        db.close()

    def test_heartbeat_renews_lease(self):
        """El endpoint heartbeat renueva updated_at de un running."""
        from backend.app.services import worker_service

        db = SessionLocal()
        ep = Episode(title="HB test", type="podcast", source_text="Hola", voice_id="jorge", status="running")
        db.add(ep)
        db.commit()
        db.refresh(ep)
        ep_id = ep.id
        db.close()

        response = client.post(f"/api/worker/jobs/{ep_id}/heartbeat", headers=_auth_headers())
        assert response.status_code == 200

        db = SessionLocal()
        ep = db.query(Episode).filter(Episode.id == ep_id).first()
        age = datetime.now(timezone.utc) - ep.updated_at.replace(tzinfo=timezone.utc) if ep.updated_at.tzinfo is None else datetime.now(timezone.utc) - ep.updated_at
        assert age.total_seconds() < 10
        db.close()

    def test_heartbeat_on_non_running_returns_404(self):
        db = SessionLocal()
        ep = Episode(title="HB 404", type="podcast", source_text="Hola", voice_id="jorge", status="completed")
        db.add(ep)
        db.commit()
        db.refresh(ep)
        ep_id = ep.id
        db.close()

        response = client.post(f"/api/worker/jobs/{ep_id}/heartbeat", headers=_auth_headers())
        assert response.status_code == 404
