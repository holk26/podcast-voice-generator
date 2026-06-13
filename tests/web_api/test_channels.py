from fastapi.testclient import TestClient
from unittest.mock import patch
from web_api.main import app
from web_api.database import init_db
from web_api.schemas import PlanEntryCreate


init_db()


def test_create_and_list_channels():
    with TestClient(app) as client:
        response = client.post("/api/channels", json={
            "name": "Canal Test",
            "description": "Desc",
            "niche": "tech",
            "format": "podcast",
            "default_voice_id": "jorge",
            "is_active": True,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Canal Test"

        response = client.get("/api/channels")
        assert response.status_code == 200
        assert any(c["name"] == "Canal Test" for c in response.json())


def test_generate_plan_creates_entries():
    with TestClient(app) as client:
        response = client.post("/api/channels", json={
            "name": "Canal IA",
            "format": "podcast",
            "niche": "historia",
            "default_voice_id": "jorge",
        })
        channel_id = response.json()["id"]

        with patch("web_api.routes.channels.generate_plan") as mock_generate:
            mock_generate.return_value = [
                PlanEntryCreate(title="T1", description="D1"),
                PlanEntryCreate(title="T2", description="D2"),
            ]
            response = client.post(f"/api/channels/{channel_id}/plan/generate")
            assert response.status_code == 200
            assert len(response.json()) == 2


def test_approve_entry_creates_episode():
    with TestClient(app) as client:
        response = client.post("/api/channels", json={
            "name": "Canal Aprobar",
            "format": "podcast",
            "default_voice_id": "jorge",
        })
        channel_id = response.json()["id"]

        response = client.post(f"/api/channels/{channel_id}/plan", json={
            "title": "Episodio a generar",
            "description": "Descripción",
        })
        entry_id = response.json()["id"]

        with patch("web_api.routes.channels.generate_script") as mock_script:
            mock_script.return_value = "Guion generado"
            response = client.post(f"/api/channels/plan/{entry_id}/approve")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "generated"
            assert data["episode_id"] is not None

        response = client.get(f"/api/episodes/{data['episode_id']}")
        assert response.status_code == 200
        assert response.json()["source_text"] == "Guion generado"
