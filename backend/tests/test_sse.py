from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Episode
import json

client = TestClient(app)


def test_sse_stream_exists():
    create_resp = client.post("/api/episodes", json={
        "title": "SSE test",
        "type": "podcast",
        "source_text": "test",
        "voice_id": "jorge"
    })
    episode_id = create_resp.json()["id"]

    # Mark the episode completed so the SSE stream closes during the test.
    db = SessionLocal()
    try:
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        episode.status = "completed"
        episode.audio_url = "/outputs/test.mp3"
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/episodes/{episode_id}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "no-cache" in response.headers.get("cache-control", "")
    assert response.headers.get("x-accel-buffering") == "no"

    # Read first event and verify payload
    text = response.text
    assert "data:" in text
    data_line = [line for line in text.split("\n") if line.startswith("data:")][0]
    payload = json.loads(data_line.replace("data: ", ""))
    assert payload["id"] == episode_id
    assert payload["status"] in ("pending", "completed", "failed")
    assert payload["audio_url"] == "/outputs/test.mp3"


def test_sse_stream_not_found():
    response = client.get("/api/episodes/999999/events")
    assert response.status_code == 404
