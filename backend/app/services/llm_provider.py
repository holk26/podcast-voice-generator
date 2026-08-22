import json
import logging
import os
import threading
from pathlib import Path

from crewai import LLM

from backend.app.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    KIMI_API_KEY,
    KIMI_BASE_URL,
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    save_llm_settings,
)

logger = logging.getLogger(__name__)

KNOWN_PROVIDERS = {"ollama", "kimi"}

# Modelo/provider en uso (mutable en runtime; por defecto los de config.yaml)
_current_provider: str = DEFAULT_LLM_PROVIDER
_current_model: str = DEFAULT_LLM_MODEL

_state_lock = threading.Lock()


def _read_kimi_token_from_local_config() -> str:
    """Fallback local: lee el token de Kimi de su config de CLI."""
    home = Path.home()
    candidates = [
        home / ".kimi-code" / "credentials" / "kimi-code.json",
        home / ".kimi" / "credentials" / "kimi-code.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                token = data.get("access_token") or data.get("token") or data.get("api_key")
                if token:
                    return token
            except Exception as e:
                logger.warning("No se pudo leer el token de Kimi de %s: %s", path, e)
                continue
    return ""


def get_kimi_api_key() -> str:
    return KIMI_API_KEY or _read_kimi_token_from_local_config()


def get_current_provider() -> str:
    with _state_lock:
        return _current_provider


def get_current_model() -> str:
    with _state_lock:
        return _current_model


def set_current_settings(provider: str, model: str) -> None:
    """Cambia provider+modelo en runtime y lo persiste en config.yaml."""
    provider = provider.strip().lower()
    model = model.strip()
    if provider not in KNOWN_PROVIDERS:
        raise ValueError(f"Provider de IA no soportado: {provider}")
    if not model:
        raise ValueError("El modelo no puede estar vacío")
    global _current_provider, _current_model
    with _state_lock:
        _current_provider = provider
        _current_model = model
    save_llm_settings(provider, model)


def get_llm(provider: str | None = None, model: str | None = None) -> LLM:
    with _state_lock:
        p = provider or _current_provider
        m = model or _current_model

    if p == "kimi":
        api_key = get_kimi_api_key()
        if not api_key:
            raise RuntimeError("Kimi no está configurado: faltan KIMI_API_KEY o token local")
        return LLM(
            model=m,
            api_key=api_key,
            base_url=KIMI_BASE_URL,
        )

    if p == "ollama":
        return LLM(
            model=f"ollama/{m}",
            base_url=OLLAMA_BASE_URL,
        )

    raise ValueError(f"Provider de IA no soportado: {p}")


def get_planning_llm() -> LLM:
    return get_llm()


def get_script_llm() -> LLM:
    return get_llm()


def check_ollama() -> dict:
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_BASE_URL)
        models = [m["model"] for m in client.list()["models"]]
        return {
            "available": True,
            "base_url": OLLAMA_BASE_URL,
            "default_model": OLLAMA_DEFAULT_MODEL,
            "default_ready": OLLAMA_DEFAULT_MODEL in models,
            "models": models,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def check_kimi() -> dict:
    api_key = get_kimi_api_key()
    if not api_key:
        return {"available": False, "error": "Kimi no configurado"}
    try:
        import requests
        resp = requests.get(
            f"{KIMI_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return {"available": False, "error": f"Kimi respondió {resp.status_code}"}
        data = resp.json()
        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        if not models:
            models = ["kimi-for-coding", "kimi-for-coding-highspeed"]
        return {
            "available": True,
            "base_url": KIMI_BASE_URL,
            "default_model": "kimi-for-coding",
            "models": models,
        }
    except Exception as e:
        return {"available": False, "error": f"No se pudo contactar Kimi: {e}"}


def list_providers() -> list[dict]:
    providers = []
    ollama_status = check_ollama()
    providers.append({
        "id": "ollama",
        "name": "Ollama",
        "available": ollama_status["available"],
        "default_model": OLLAMA_DEFAULT_MODEL,
    })

    kimi_status = check_kimi()
    providers.append({
        "id": "kimi",
        "name": "Kimi",
        "available": kimi_status["available"],
        "default_model": "kimi-for-coding",
    })
    return providers


def list_models(provider: str | None = None) -> dict:
    p = provider or get_current_provider()
    if p == "ollama":
        status = check_ollama()
        return {
            "provider": p,
            "current": get_current_model() if get_current_provider() == p else OLLAMA_DEFAULT_MODEL,
            "models": status.get("models", []) if status["available"] else [],
        }
    if p == "kimi":
        status = check_kimi()
        models = status.get("models", [])
        return {
            "provider": p,
            "current": get_current_model() if get_current_provider() == p else "kimi-for-coding",
            "models": models,
        }
    raise ValueError(f"Provider desconocido: {p}")
