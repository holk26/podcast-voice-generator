from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from web_api.main import app

client = TestClient(app)


@patch("web_api.routes.tts.edge_tts.Communicate")
def test_preview_generates_audio(mock_communicate):
    mock_instance = mock_communicate.return_value
    mock_instance.save = AsyncMock()

    response = client.post("/api/tts/preview", json={
        "text": "Hola, esto es una prueba.",
        "voice_id": "jorge"
    })
    assert response.status_code == 200
    data = response.json()
    assert "audio_url" in data
    assert data["audio_url"].startswith("/outputs/previews/")

    mock_communicate.assert_called_once()
    _, kwargs = mock_communicate.call_args
    assert kwargs["voice"] == "es-ES-AlvaroNeural"


def test_sanitize_applied_for_edge_preview():
    """Un texto con tokens <|…|> llega limpio a edge-tts."""
    from core.emotion_tags import sanitize_emotion_tags
    out = sanitize_emotion_tags("<|emotion:awe|> Hola qué tal", "edge")
    assert out == "Hola qué tal"
    out = sanitize_emotion_tags("<|emotion:awe|> Hola", "higgs")
    assert out == "<|emotion:awe|> Hola"
