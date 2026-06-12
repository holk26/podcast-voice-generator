from fastapi.testclient import TestClient
from web_api.main import app

client = TestClient(app)


def test_create_and_list_episodes():
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
