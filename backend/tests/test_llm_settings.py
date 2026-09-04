"""Tests de persistencia de settings de IA en la base de datos."""
import pytest

from backend.app.database import init_db
from backend.app.services import llm_provider, settings_store

init_db()


@pytest.fixture(autouse=True)
def _clean_settings():
    keys = [
        llm_provider.SETTING_KEY_PROVIDER,
        llm_provider.SETTING_KEY_MODEL,
        llm_provider.SETTING_KEY_KIMI_TOKEN,
        llm_provider.SETTING_KEY_GEMINI_TOKEN,
        llm_provider.SETTING_KEY_OPENCODEGO_TOKEN,
    ]
    for key in keys:
        settings_store.set_setting(key, "")
    yield
    for key in keys:
        settings_store.set_setting(key, "")


def test_set_current_settings_persists_in_db():
    llm_provider.set_current_settings("opencodego", "kimi-k2.6")
    assert settings_store.get_setting(llm_provider.SETTING_KEY_PROVIDER) == "opencodego"
    assert settings_store.get_setting(llm_provider.SETTING_KEY_MODEL) == "kimi-k2.6"
    assert llm_provider.get_current_provider() == "opencodego"
    assert llm_provider.get_current_model() == "kimi-k2.6"


def test_load_persisted_settings_overrides_env_default():
    # Valores "guardados en BD" (como tras elegir provider en la web)
    settings_store.set_setting(llm_provider.SETTING_KEY_PROVIDER, "gemini")
    settings_store.set_setting(llm_provider.SETTING_KEY_MODEL, "gemini-2.5-flash")

    llm_provider.load_persisted_settings()

    assert llm_provider.get_current_provider() == "gemini"
    assert llm_provider.get_current_model() == "gemini-2.5-flash"


def test_load_persisted_settings_keeps_default_when_db_empty():
    before = (llm_provider.get_current_provider(), llm_provider.get_current_model())
    llm_provider.load_persisted_settings()
    assert (llm_provider.get_current_provider(), llm_provider.get_current_model()) == before


def test_ensure_provider_available_switches_when_current_down(monkeypatch):
    llm_provider.set_current_settings("kimi", "kimi-for-coding")

    def fake_status(provider):
        if provider == "kimi":
            return {"available": False, "error": "401"}
        if provider == "opencodego":
            return {"available": True, "default_model": "kimi-k2.6"}
        return {"available": False}

    monkeypatch.setattr(llm_provider, "_provider_status", fake_status)
    llm_provider.ensure_provider_available()

    assert llm_provider.get_current_provider() == "opencodego"
    assert llm_provider.get_current_model() == "kimi-k2.6"
    # La conmutación queda persistida para el próximo arranque
    assert settings_store.get_setting(llm_provider.SETTING_KEY_PROVIDER) == "opencodego"


def test_ensure_provider_available_keeps_current_when_ok(monkeypatch):
    llm_provider.set_current_settings("gemini", "gemini-2.5-flash")

    def fake_status(provider):
        if provider == "gemini":
            return {"available": True, "default_model": "gemini-2.5-flash"}
        return {"available": False}

    monkeypatch.setattr(llm_provider, "_provider_status", fake_status)
    llm_provider.ensure_provider_available()

    assert llm_provider.get_current_provider() == "gemini"


def test_ensure_provider_available_no_provider_at_all(monkeypatch):
    llm_provider.set_current_settings("kimi", "kimi-for-coding")
    monkeypatch.setattr(
        llm_provider, "_provider_status", lambda p: {"available": False}
    )
    llm_provider.ensure_provider_available()
    # No hay alternativa: se mantiene el provider (fallará al usarse)
    assert llm_provider.get_current_provider() == "kimi"


def test_api_key_persists_in_db(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_provider, "DATA_DIR_OPENCODEGO_TOKEN", tmp_path / "tok.json")
    llm_provider.save_opencodego_api_key("sk-test-123")
    # Lee desde la BD aunque el archivo no exista
    assert settings_store.get_setting(llm_provider.SETTING_KEY_OPENCODEGO_TOKEN) == "sk-test-123"
    assert llm_provider.get_opencodego_api_key() == "sk-test-123"
