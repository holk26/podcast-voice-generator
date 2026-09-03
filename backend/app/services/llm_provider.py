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
    OPENCODEGO_BASE_URL,
    save_llm_settings,
)

logger = logging.getLogger(__name__)

KNOWN_PROVIDERS = {"ollama", "kimi", "gemini", "opencodego"}

# Modelo/provider en uso (mutable en runtime; por defecto los de config.yaml)
_current_provider: str = DEFAULT_LLM_PROVIDER
_current_model: str = DEFAULT_LLM_MODEL

_state_lock = threading.Lock()


DATA_DIR_KIMI_TOKEN = Path(os.environ.get("DATA_DIR", "/app/data")) / "kimi_token.json"
DATA_DIR_GEMINI_TOKEN = Path(os.environ.get("DATA_DIR", "/app/data")) / "gemini_token.json"
DATA_DIR_OPENCODEGO_TOKEN = Path(os.environ.get("DATA_DIR", "/app/data")) / "opencodego_token.json"


def _read_gemini_token_from_data_dir() -> str:
    """Lee un token persistente guardado por el endpoint admin."""
    if DATA_DIR_GEMINI_TOKEN.exists():
        try:
            data = json.loads(DATA_DIR_GEMINI_TOKEN.read_text())
            token = data.get("token") or data.get("api_key")
            if token:
                return token
        except Exception as e:
            logger.warning("No se pudo leer %s: %s", DATA_DIR_GEMINI_TOKEN, e)
    return ""


def get_gemini_api_key() -> str:
    from backend.app.config import GEMINI_API_KEY
    return _read_gemini_token_from_data_dir() or GEMINI_API_KEY


def save_gemini_api_key(token: str) -> None:
    """Persiste el token de Gemini en el volumen de datos para sobrevivir redeploys."""
    DATA_DIR_GEMINI_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR_GEMINI_TOKEN.write_text(json.dumps({"token": token}, indent=2))
    logger.info("Token de Gemini guardado en %s", DATA_DIR_GEMINI_TOKEN)


def _read_kimi_token_from_data_dir() -> str:
    """Lee un token persistente guardado por el endpoint admin."""
    if DATA_DIR_KIMI_TOKEN.exists():
        try:
            data = json.loads(DATA_DIR_KIMI_TOKEN.read_text())
            token = data.get("token") or data.get("access_token") or data.get("api_key")
            if token:
                return token
        except Exception as e:
            logger.warning("No se pudo leer %s: %s", DATA_DIR_KIMI_TOKEN, e)
    return ""


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
    return _read_kimi_token_from_data_dir() or KIMI_API_KEY or _read_kimi_token_from_local_config()


def save_kimi_api_key(token: str) -> None:
    """Persiste el token de Kimi en el volumen de datos para sobrevivir redeploys."""
    DATA_DIR_KIMI_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR_KIMI_TOKEN.write_text(json.dumps({"token": token}, indent=2))
    logger.info("Token de Kimi guardado en %s", DATA_DIR_KIMI_TOKEN)


def _read_opencodego_token_from_data_dir() -> str:
    """Lee un token persistente guardado por el endpoint admin."""
    if DATA_DIR_OPENCODEGO_TOKEN.exists():
        try:
            data = json.loads(DATA_DIR_OPENCODEGO_TOKEN.read_text())
            token = data.get("token") or data.get("api_key")
            if token:
                return token
        except Exception as e:
            logger.warning("No se pudo leer %s: %s", DATA_DIR_OPENCODEGO_TOKEN, e)
    return ""


def get_opencodego_api_key() -> str:
    from backend.app.config import OPENCODEGO_API_KEY
    return _read_opencodego_token_from_data_dir() or OPENCODEGO_API_KEY


def save_opencodego_api_key(token: str) -> None:
    """Persiste el token de OpenCode Go en el volumen de datos para sobrevivir redeploys."""
    DATA_DIR_OPENCODEGO_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR_OPENCODEGO_TOKEN.write_text(json.dumps({"token": token}, indent=2))
    logger.info("Token de OpenCode Go guardado en %s", DATA_DIR_OPENCODEGO_TOKEN)


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


def set_current_model(model: str) -> None:
    """Compatibilidad legacy: cambia solo el modelo manteniendo el provider actual."""
    set_current_settings(get_current_provider(), model)


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

    if p == "gemini":
        api_key = get_gemini_api_key()
        if not api_key:
            raise RuntimeError("Gemini no está configurado: falta GEMINI_API_KEY")
        model_name = m if m.startswith("gemini/") else f"gemini/{m}"
        return LLM(
            model=model_name,
            api_key=api_key,
        )

    if p == "opencodego":
        api_key = get_opencodego_api_key()
        if not api_key:
            raise RuntimeError("OpenCode Go no está configurado: falta OPENCODEGO_API_KEY o token guardado")
        return LLM(
            model=m,
            api_key=api_key,
            base_url=OPENCODEGO_BASE_URL,
            extra_headers={"x-opencode-session": "podcash-web"},
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
        logger.warning("Kimi no está configurado: falta KIMI_API_KEY o token local")
        return {"available": False, "error": "Kimi no configurado"}
    try:
        import requests
        logger.info("Verificando Kimi en %s (token len=%s)", KIMI_BASE_URL, len(api_key))
        resp = requests.get(
            f"{KIMI_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Kimi respondió %s: %s", resp.status_code, resp.text[:200])
            return {"available": False, "error": f"Kimi respondió {resp.status_code}"}
        data = resp.json()
        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        if not models:
            models = ["kimi-for-coding", "kimi-for-coding-highspeed"]
        logger.info("Kimi disponible. Modelos: %s", models)
        return {
            "available": True,
            "base_url": KIMI_BASE_URL,
            "default_model": "kimi-for-coding",
            "models": models,
        }
    except Exception as e:
        logger.warning("No se pudo contactar Kimi: %s", e, exc_info=True)
        return {"available": False, "error": f"No se pudo contactar Kimi: {e}"}


def check_gemini() -> dict:
    api_key = get_gemini_api_key()
    if not api_key:
        logger.warning("Gemini no está configurado: falta GEMINI_API_KEY")
        return {"available": False, "error": "Gemini no configurado"}
    try:
        import requests
        logger.info("Verificando Gemini con API key (len=%s)", len(api_key))
        resp = requests.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Gemini respondió %s: %s", resp.status_code, resp.text[:200])
            return {"available": False, "error": f"Gemini respondió {resp.status_code}"}
        
        data = resp.json()
        models = []
        for m in data.get("models", []):
            name = m.get("name", "")
            if "gemini-" in name:
                models.append(name.split("/")[-1])
        
        default_gemini_models = [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        
        retrieved_gemini = [m for m in models if m.startswith("gemini-")]
        if not retrieved_gemini:
            retrieved_gemini = default_gemini_models
        else:
            # Sort or prioritize the default ones
            retrieved_gemini = sorted(list(set(retrieved_gemini + default_gemini_models)), reverse=True)

        logger.info("Gemini disponible. Modelos: %s", retrieved_gemini)
        return {
            "available": True,
            "base_url": "https://generativelanguage.googleapis.com",
            "default_model": "gemini-2.5-flash",
            "models": retrieved_gemini,
        }
    except Exception as e:
        logger.warning("No se pudo contactar Gemini: %s", e, exc_info=True)
        return {"available": False, "error": f"No se pudo contactar Gemini: {e}"}


def check_opencodego() -> dict:
    api_key = get_opencodego_api_key()
    if not api_key:
        logger.warning("OpenCode Go no está configurado: falta OPENCODEGO_API_KEY o token guardado")
        return {"available": False, "error": "OpenCode Go no configurado"}
    try:
        import requests
        logger.info("Verificando OpenCode Go en %s (token len=%s)", OPENCODEGO_BASE_URL, len(api_key))
        resp = requests.get(
            f"{OPENCODEGO_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("OpenCode Go respondió %s: %s", resp.status_code, resp.text[:200])
            return {"available": False, "error": f"OpenCode Go respondió {resp.status_code}"}
        data = resp.json()
        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        if not models:
            models = ["kimi-k2.6", "glm-5.2", "deepseek-v4-flash"]
        logger.info("OpenCode Go disponible. Modelos: %s", models)
        return {
            "available": True,
            "base_url": OPENCODEGO_BASE_URL,
            "default_model": "kimi-k2.6",
            "models": models,
        }
    except Exception as e:
        logger.warning("No se pudo contactar OpenCode Go: %s", e, exc_info=True)
        return {"available": False, "error": f"No se pudo contactar OpenCode Go: {e}"}


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

    gemini_status = check_gemini()
    providers.append({
        "id": "gemini",
        "name": "Gemini",
        "available": gemini_status["available"],
        "default_model": "gemini-2.5-flash",
    })

    opencodego_status = check_opencodego()
    providers.append({
        "id": "opencodego",
        "name": "OpenCode Go",
        "available": opencodego_status["available"],
        "default_model": "kimi-k2.6",
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
    if p == "gemini":
        status = check_gemini()
        models = status.get("models", [])
        return {
            "provider": p,
            "current": get_current_model() if get_current_provider() == p else "gemini-2.5-flash",
            "models": models,
        }
    if p == "opencodego":
        status = check_opencodego()
        models = status.get("models", [])
        return {
            "provider": p,
            "current": get_current_model() if get_current_provider() == p else "kimi-k2.6",
            "models": models,
        }
    raise ValueError(f"Provider desconocido: {p}")
