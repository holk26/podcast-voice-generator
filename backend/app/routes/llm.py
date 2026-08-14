from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from web_api.services.llm_provider import (
    check_ollama,
    get_current_model,
    set_current_model,
)

router = APIRouter()


class ModelRequest(BaseModel):
    model: str


@router.get("/status")
def llm_status():
    return check_ollama()


@router.get("/models")
def llm_models():
    status = check_ollama()
    if not status.get("available"):
        raise HTTPException(status_code=502, detail=status.get("error", "Ollama no disponible"))
    return {"current": get_current_model(), "models": status.get("models", [])}


@router.post("/model")
def set_model(data: ModelRequest):
    """Cambia el modelo de IA del congreso (runtime + config.yaml)."""
    if not data.model.strip():
        raise HTTPException(status_code=400, detail="Modelo vacío")
    set_current_model(data.model.strip())
    return {"current": get_current_model()}
