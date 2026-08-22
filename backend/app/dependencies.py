"""Dependencias reutilizables de FastAPI (auth, DB, worker token)."""

import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.auth import decode_access_token
from backend.app.config import WORKER_TOKEN
from backend.app.database import get_db
from backend.app.models import User

security = HTTPBearer(auto_error=False)


def _auth_disabled() -> bool:
    return os.getenv("REQUIRE_AUTH", "true").lower() in ("false", "0", "")


def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    request: Request,
) -> Optional[str]:
    """Obtiene el JWT del header Authorization o del query param `token`.

    El query param se usa para SSE/EventSource, que no puede enviar headers
    personalizados.
    """
    if credentials is not None:
        return credentials.credentials
    return request.query_params.get("token") or request.query_params.get("access_token")


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if _auth_disabled():
        return User(username="test", is_admin=True)

    token = _extract_token(credentials, request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependencia para restringir endpoints a administradores."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_worker_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Valida el token estático compartido entre backend y worker."""
    if not WORKER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Worker token not configured",
        )

    if credentials is None or credentials.credentials != WORKER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid worker token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
