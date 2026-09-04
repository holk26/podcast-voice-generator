from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Episode
import json
import time

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


def test_job_sse_sends_heartbeat_and_replays_events(monkeypatch):
    """El stream de jobs envía heartbeats en silencio y re-emite los eventos
    acumulados al conectar (el frontend se reconecta y reconstruye la lista)."""
    import threading

    from backend.app.routes import jobs as jobs_module
    from backend.app.services.job_service import registry

    monkeypatch.setattr(jobs_module, "HEARTBEAT_SECONDS", 1)
    job_id = registry.create("test", "heartbeat")
    registry.emit(job_id, "research", "investigando")

    def complete():
        time.sleep(2.5)
        registry.finish(job_id)

    threading.Thread(target=complete, daemon=True).start()

    body = b""
    with client.stream("GET", f"/api/jobs/{job_id}/events") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        for chunk in response.iter_raw():
            body += chunk
            if b": ping" in body and b"__status__" in body:
                break

    text = body.decode()
    assert ": ping" in text
    assert '"step": "research"' in text
    assert '"message": "investigando"' in text
    assert '"status": "done"' in text
