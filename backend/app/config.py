import os
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
PREVIEW_DIR = OUTPUT_DIR / "previews"


def init_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

try:
    API_PORT = int(os.getenv("API_PORT", "8000"))
except (ValueError, TypeError):
    API_PORT = 8000

try:
    WORKER_PORT = int(os.getenv("WORKER_PORT", "8001"))
except (ValueError, TypeError):
    WORKER_PORT = 8001


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
OLLAMA_PLANNING_MODEL = os.getenv("OLLAMA_PLANNING_MODEL", _LLM_CONFIG.get("planning_model", OLLAMA_DEFAULT_MODEL))
OLLAMA_SCRIPT_MODEL = os.getenv("OLLAMA_SCRIPT_MODEL", _LLM_CONFIG.get("script_model", OLLAMA_DEFAULT_MODEL))


def save_llm_model(model: str) -> None:
    """Persiste el modelo elegido en config.yaml (sección llm)."""
    global _CONFIG, _LLM_CONFIG
    config_path = BASE_DIR / "config.yaml"
    data = dict(_CONFIG)
    llm = dict(data.get("llm", {}))
    llm["default_model"] = model
    llm["script_model"] = model
    llm["planning_model"] = model
    data["llm"] = llm
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    _CONFIG = data
    _LLM_CONFIG = llm
