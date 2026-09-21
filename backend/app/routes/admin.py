"""Endpoints de administración del backend."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.config import WORKER_TOKEN
from backend.app.database import get_db
from backend.app.dependencies import require_admin
from backend.app.models import User
from backend.app.services.llm_provider import save_kimi_api_key, save_gemini_api_key, save_opencodego_api_key

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list)
def list_users(db=Depends(get_db), admin_user: User = Depends(require_admin)):
    """Lista usuarios registrados (username, is_admin)."""
    users = db.query(User).order_by(User.id).all()
    return [{"id": u.id, "username": u.username, "is_admin": u.is_admin} for u in users]


@router.delete("/users/{username}", status_code=204)
def delete_user(username: str, db=Depends(get_db), admin_user: User = Depends(require_admin)):
    """Elimina un usuario. Protegido: no se puede borrar el admin configurado
    en ADMIN_USER ni a uno mismo."""
    import os
    env_admin = os.getenv("ADMIN_USER", "admin")
    if username == env_admin:
        raise HTTPException(status_code=400, detail="No se puede borrar el admin configurado en ADMIN_USER")
    if username == admin_user.username:
        raise HTTPException(status_code=400, detail="No puedes borrar tu propio usuario")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None


class KimiTokenRequest(BaseModel):
    token: str


class GeminiTokenRequest(BaseModel):
    token: str


class OpenCodeGoTokenRequest(BaseModel):
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


@router.post("/gemini-token", response_model=dict)
def set_gemini_token(data: GeminiTokenRequest, admin_user: User = Depends(require_admin)):
    """Guarda (o actualiza) el token de Gemini en el volumen persistente.

    El backend lo usará con prioridad sobre GEMINI_API_KEY.
    Requiere autenticación de administrador.
    """
    token = data.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="El token no puede estar vacío")
    try:
        save_gemini_api_key(token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el token: {e}")
    return {"ok": True, "path": "/app/data/gemini_token.json"}


@router.post("/opencodego-token", response_model=dict)
def set_opencodego_token(data: OpenCodeGoTokenRequest, admin_user: User = Depends(require_admin)):
    """Guarda (o actualiza) el API key de OpenCode Go en el volumen persistente.

    El backend lo usará con prioridad sobre OPENCODEGO_API_KEY.
    Requiere autenticación de administrador.
    """
    token = data.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="El token no puede estar vacío")
    try:
        save_opencodego_api_key(token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el token: {e}")
    return {"ok": True, "path": "/app/data/opencodego_token.json"}
