"""Endpoints de administración del backend."""

from fastapi import APIRouter, Depends

from backend.app.config import WORKER_TOKEN
from backend.app.dependencies import require_admin
from backend.app.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/worker-token", response_model=dict)
def get_worker_token(admin_user: User = Depends(require_admin)):
    """Devuelve el token estático compartido con el worker.

    Útil para configurar el worker local sin tener que leer el .env del servidor.
    Requiere autenticación de administrador.
    """
    return {"worker_token": WORKER_TOKEN}
