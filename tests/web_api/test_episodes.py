from fastapi.testclient import TestClient
from web_api.main import app
from web_api.database import init_db

init_db()


def test_create_and_list_episodes():
    with TestClient(app) as client:
        create_resp = client.post("/api/episodes", json={
            "title": "Episodio de prueba",
            "type": "podcast",
            "source_text": "Bienvenidos a este podcast de prueba.",
            "voice_id": "jorge"
        })
        assert create_resp.status_code == 201
        episode = create_resp.json()
        assert episode["status"] == "pending"
        assert episode["title"] == "Episodio de prueba"

        list_resp = client.get("/api/episodes")
        assert list_resp.status_code == 200
        assert any(e["id"] == episode["id"] for e in list_resp.json())


def test_update_episode():
    with TestClient(app) as client:
        create_resp = client.post("/api/episodes", json={
            "title": "Original",
            "type": "podcast",
            "source_text": "Texto original",
            "voice_id": "jorge"
        })
        episode_id = create_resp.json()["id"]

        update_resp = client.put(f"/api/episodes/{episode_id}", json={
            "title": "Actualizado",
            "type": "motivation",
            "source_text": "Texto actualizado",
            "voice_id": "dalia"
        })
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["title"] == "Actualizado"
        assert updated["type"] == "motivation"


def test_publish_episode_requires_completed():
    with TestClient(app) as client:
        create_resp = client.post("/api/episodes", json={
            "title": "Sin audio",
            "type": "podcast",
            "source_text": "Texto",
            "voice_id": "jorge",
        })
        episode_id = create_resp.json()["id"]

        resp = client.post(f"/api/episodes/{episode_id}/publish")
        assert resp.status_code == 409


def test_publish_and_unpublish_episode():
    with TestClient(app) as client:
        create_resp = client.post("/api/episodes", json={
            "title": "Listo",
            "type": "podcast",
            "source_text": "Texto",
            "voice_id": "jorge",
        })
        episode_id = create_resp.json()["id"]
        from web_api.database import SessionLocal
        from web_api.models import Episode
        db = SessionLocal()
        db.query(Episode).filter(Episode.id == episode_id).first().status = "completed"
        db.commit()
        db.close()

        resp = client.post(f"/api/episodes/{episode_id}/publish")
        assert resp.status_code == 200
        body = resp.json()
        assert body["published_at"] is not None

        resp2 = client.post(f"/api/episodes/{episode_id}/publish")
        assert resp2.status_code == 200
        assert resp2.json()["published_at"] is not None

        resp3 = client.post(f"/api/episodes/{episode_id}/unpublish")
        assert resp3.status_code == 200
        assert resp3.json()["published_at"] is None


def test_publish_episode_not_found():
    with TestClient(app) as client:
        assert client.post("/api/episodes/99999/publish").status_code == 404
        assert client.post("/api/episodes/99999/unpublish").status_code == 404
