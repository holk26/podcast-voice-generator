from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def _create_channel(name: str) -> dict:
    r = client.post("/api/channels", json={
        "name": name, "format": "podcast", "default_voice_id": "jorge",
    })
    assert r.status_code == 201, r.text
    return r.json()


def _create_episode(channel_id: int, title: str) -> dict:
    r = client.post("/api/episodes", json={
        "title": title,
        "type": "podcast",
        "source_text": "Texto de prueba suficientemente largo.",
        "voice_id": "jorge",
        "channel_id": channel_id,
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_list_episodes_filter_by_channel():
    c1 = _create_channel("Filtro A")
    c2 = _create_channel("Filtro B")
    _create_episode(c1["id"], "Ep A1")
    _create_episode(c2["id"], "Ep B1")

    r = client.get(f"/api/episodes?channel_id={c1['id']}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Ep A1"
    assert all(e["channel_id"] == c1["id"] for e in data)

    r_all = client.get("/api/episodes")
    assert len(r_all.json()) >= 2
