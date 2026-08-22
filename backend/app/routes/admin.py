"""Endpoints de administración del backend."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.config import WORKER_TOKEN
from backend.app.dependencies import require_admin
from backend.app.models import User
from backend.app.services.llm_provider import save_kimi_api_key

router = APIRouter(prefix="/admin", tags=["admin"])


class KimiTokenRequest(BaseModel):
    token: str


@router.get("/worker-token", response_model=dict)
def get_worker_token(admin_user: User = Depends(require_admin)):
    """Devuelve el token estático compartido con el worker.

    Útil para configurar el worker local sin tener que leer el .env del servidor.
    Requiere autenticación de administrador.
    """
    return {"worker_token": WORKER_TOKEN}


@router.post("/kimi-token", response_model=dict)
def set_kimi_token(data: KimiTokenRequest, admin_user: User = Depends(require_admin)):
    """Guarda (o actualiza) el token de Kimi en el volumen persistente.

    El backend lo usará con prioridad sobre KIMI_API_KEY y el token local del CLI.
    Requiere autenticación de administrador.
    """
    token = data.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="El token no puede estar vacío")
    try:
        save_kimi_api_key(token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el token: {e}")
    return {"ok": True, "path": "/app/data/kimi_token.json"}
