from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_list_voices_returns_default_voices():
    response = client.get("/api/voices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]
