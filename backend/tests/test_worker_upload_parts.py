import os

import pytest
from fastapi.testclient import TestClient

from backend.app.database import SessionLocal, init_db
from backend.app.main import app
from backend.app.models import Episode
from shared.config import OUTPUT_DIR

os.environ.setdefault("WORKER_TOKEN", "worker-test-token")

client = TestClient(app)


def _auth_headers():
    return {"Authorization": f"Bearer {os.environ['WORKER_TOKEN']}"}


@pytest.fixture()
def episode_id():
    db = SessionLocal()
    episode = Episode(
        title="Upload parts test",
        type="podcast",
        source_text="Hola",
        voice_id="jorge",
        status="running",
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    episode_id = episode.id
    db.close()
    yield episode_id
    import shutil

    shutil.rmtree(OUTPUT_DIR / str(episode_id), ignore_errors=True)


class TestWorkerUploadParts:
    def test_upload_two_parts_and_assemble(self, episode_id):
        payload_a = b"A" * 1000
        payload_b = b"B" * 500

        for part_number, payload in enumerate([payload_a, payload_b]):
            response = client.post(
                f"/api/worker/jobs/{episode_id}/upload-part/{part_number}",
                files={"audio": (f"part_{part_number:04d}", payload, "application/octet-stream")},
                headers=_auth_headers(),
            )
            assert response.status_code == 200

        response = client.post(
            f"/api/worker/jobs/{episode_id}/assemble",
            json={"filename": "final.mp3", "parts": 2},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["audio_url"] == f"/outputs/{episode_id}/final.mp3"

        assembled = (OUTPUT_DIR / str(episode_id) / "final.mp3").read_bytes()
        assert assembled == payload_a + payload_b
        # El directorio de partes se limpia tras el ensamblado.
        assert not (OUTPUT_DIR / str(episode_id) / "_parts").exists()

    def test_assemble_with_missing_part_returns_400(self, episode_id):
        response = client.post(
            f"/api/worker/jobs/{episode_id}/upload-part/0",
            files={"audio": ("part_0000", b"x" * 10, "application/octet-stream")},
            headers=_auth_headers(),
        )
        assert response.status_code == 200

        response = client.post(
            f"/api/worker/jobs/{episode_id}/assemble",
            json={"filename": "final.mp3", "parts": 2},
            headers=_auth_headers(),
        )
        assert response.status_code == 400

    def test_upload_part_rejects_negative_number(self, episode_id):
        response = client.post(
            f"/api/worker/jobs/{episode_id}/upload-part/-1",
            files={"audio": ("part", b"x", "application/octet-stream")},
            headers=_auth_headers(),
        )
        assert response.status_code in (400, 422)

    def test_assemble_sanitizes_filename(self, episode_id):
        response = client.post(
            f"/api/worker/jobs/{episode_id}/upload-part/0",
            files={"audio": ("part_0000", b"ok", "application/octet-stream")},
            headers=_auth_headers(),
        )
        assert response.status_code == 200

        response = client.post(
            f"/api/worker/jobs/{episode_id}/assemble",
            json={"filename": "../../evil.mp3", "parts": 1},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["audio_url"] == f"/outputs/{episode_id}/evil.mp3"
        assert (OUTPUT_DIR / str(episode_id) / "evil.mp3").exists()
        assert not (OUTPUT_DIR / "evil.mp3").exists()

    def test_upload_part_requires_token(self, episode_id):
        response = client.post(
            f"/api/worker/jobs/{episode_id}/upload-part/0",
            files={"audio": ("part", b"x", "application/octet-stream")},
        )
        assert response.status_code == 401
