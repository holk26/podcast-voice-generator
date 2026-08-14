from crewai import LLM
from backend.app.config import (
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    save_llm_model,
)

# Modelo en uso (mutable en runtime; por defecto el de config.yaml)
_current_model: str = OLLAMA_DEFAULT_MODEL


def get_current_model() -> str:
    return _current_model


def set_current_model(model: str) -> None:
    """Cambia el modelo en runtime y lo persiste en config.yaml."""
    global _current_model
    _current_model = model
    save_llm_model(model)


def get_llm(model: str | None = None) -> LLM:
    return LLM(
        model=f"ollama/{model or _current_model}",
        base_url=OLLAMA_BASE_URL,
    )


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
            "default_model": _current_model,
            "default_ready": _current_model in models,
            "models": models,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
