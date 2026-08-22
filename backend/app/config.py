import os
from pathlib import Path

import yaml

from shared.config import BASE_DIR, DATA_DIR, OUTPUT_DIR, PREVIEW_DIR, init_dirs

# Rutas y constantes compartidas se reexportan para compatibilidad
__all__ = ["BASE_DIR", "DATA_DIR", "OUTPUT_DIR", "PREVIEW_DIR", "init_dirs"]

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

try:
    API_PORT = int(os.getenv("API_PORT", "8000"))
except (ValueError, TypeError):
    API_PORT = 8000

try:
    WORKER_PORT = int(os.getenv("WORKER_PORT", "8001"))
except (ValueError, TypeError):
    WORKER_PORT = 8001


# Auth settings
SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto_por_una_clave_secreta_larga")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")

# Kimi / OpenCode Go settings
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1")

# OpenCode Go (reserved for future use)
OPENCODEGO_API_KEY = os.getenv("OPENCODEGO_API_KEY", "")
OPENCODEGO_BASE_URL = os.getenv("OPENCODEGO_BASE_URL", "")


def _load_config() -> dict:
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


_CONFIG = _load_config()
_LLM_CONFIG = _CONFIG.get("llm", {})

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", _LLM_CONFIG.get("base_url", "http://localhost:11434"))
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", _LLM_CONFIG.get("default_model", "llama3.1:8b"))

DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER",
                                 _LLM_CONFIG.get("provider", "ollama"))
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL",
                              _LLM_CONFIG.get("model", OLLAMA_DEFAULT_MODEL))


def save_llm_settings(provider: str, model: str) -> None:
    """Persiste el provider y modelo elegidos en config.yaml (sección llm)."""
    global _CONFIG, _LLM_CONFIG
    config_path = BASE_DIR / "config.yaml"
    data = dict(_CONFIG)
    llm = dict(data.get("llm", {}))
    llm["provider"] = provider
    llm["model"] = model
    data["llm"] = llm
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    _CONFIG = data
    _LLM_CONFIG = llm


def save_llm_model(model: str) -> None:
    """Compatibilidad legacy: ahora el provider y modelo se persisten juntos."""
    # Stub mantenido por posibles imports legacy. Usar save_llm_settings() o
    # llm_provider.set_current_settings() para cambios reales.
    pass
