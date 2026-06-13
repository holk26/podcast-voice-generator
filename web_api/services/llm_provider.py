from crewai import LLM
from web_api.config import (
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    OLLAMA_PLANNING_MODEL,
    OLLAMA_SCRIPT_MODEL,
)


def get_llm(model: str | None = None) -> LLM:
    return LLM(
        model=f"ollama/{model or OLLAMA_DEFAULT_MODEL}",
        base_url=OLLAMA_BASE_URL,
    )


def get_planning_llm() -> LLM:
    return get_llm(OLLAMA_PLANNING_MODEL)


def get_script_llm() -> LLM:
    return get_llm(OLLAMA_SCRIPT_MODEL)


def check_ollama() -> dict:
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_BASE_URL)
        models = [m["model"] for m in client.list()["models"]]
        default_ready = OLLAMA_DEFAULT_MODEL in models
        return {
            "available": True,
            "base_url": OLLAMA_BASE_URL,
            "default_model": OLLAMA_DEFAULT_MODEL,
            "default_ready": default_ready,
            "models": models,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
