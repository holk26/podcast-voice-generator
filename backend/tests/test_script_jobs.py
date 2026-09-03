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


def _dummy_channel():
    from backend.app.models import Channel
    return Channel(
        name="C", format="podcast", niche="nicho", description="",
        default_voice_id="jorge", target_minutes=2, episodes_per_week=2,
        num_speakers=1,
    )


def test_generate_script_from_raw_uses_material(monkeypatch):
    import backend.app.services.crew_service as cs
    from types import SimpleNamespace

    class _FakeAgent:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(cs, "Agent", _FakeAgent)
    prompts = []

    def fake_run(agent, prompt, expected):
        prompts.append(prompt)
        if "JSON" in expected:
            return '[{"title": "S1", "points": "puntos"}]'
        return "palabra " * 400

    monkeypatch.setattr(cs, "_run_single_task", fake_run)

    # Variante cruda: la materia prima debe llegar a los prompts
    script = cs.generate_script_from_raw(
        _dummy_channel(), "MATERIAL_BRUTO_XYZ", "Título crudo", target_minutes=2
    )
    assert "palabra" in script
    assert any("MATERIAL_BRUTO_XYZ" in p for p in prompts)
    assert any("Título crudo" in p for p in prompts)

    # Wrapper viejo (entrada de plan) sigue funcionando igual
    prompts.clear()
    entry = SimpleNamespace(title="Título plan", description="DESC_PLAN_123")
    script2 = cs.generate_script(_dummy_channel(), entry, target_minutes=2)
    assert "palabra" in script2
    assert any("DESC_PLAN_123" in p for p in prompts)
    assert any("Título plan" in p for p in prompts)
