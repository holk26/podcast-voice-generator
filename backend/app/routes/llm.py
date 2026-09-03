from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.llm_provider import (
    check_kimi,
    check_gemini,
    check_ollama,
    check_opencodego,
    get_current_model,
    get_current_provider,
    list_models,
    list_providers,
    set_current_settings,
)

router = APIRouter()


class SettingsRequest(BaseModel):
    provider: str
    model: str


@router.get("/status")
def llm_status():
    provider = get_current_provider()
    if provider == "kimi":
        return check_kimi()
    if provider == "gemini":
        return check_gemini()
    if provider == "opencodego":
        return check_opencodego()
    return check_ollama()


@router.get("/providers")
def llm_providers():
    return {
        "current_provider": get_current_provider(),
        "current_model": get_current_model(),
        "providers": list_providers(),
    }


@router.get("/models")
def llm_models(provider: str | None = None):
    try:
        return list_models(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/model")
def set_model(data: SettingsRequest):
    """Cambia el provider y modelo de IA activos (runtime + config.yaml)."""
    provider = data.provider.strip().lower()
    model = data.model.strip()
    if not provider or not model:
        raise HTTPException(status_code=400, detail="Provider y modelo son obligatorios")

    valid = {p["id"] for p in list_providers() if p["available"]}
    if provider not in valid:
        raise HTTPException(status_code=400, detail=f"Provider no disponible: {provider}")

    set_current_settings(provider, model)
    return {
        "current_provider": get_current_provider(),
        "current_model": get_current_model(),
    }
