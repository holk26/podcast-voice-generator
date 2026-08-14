"""Rutas de autenticación: login y usuario actual."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import os

from backend.app.auth import create_access_token, get_password_hash, verify_password
from backend.app.database import get_db
from backend.app.dependencies import get_current_user
from backend.app.models import User
from shared.schemas import Token, UserResponse, LoginRequest

router = APIRouter(tags=["auth"])


def _admin_credentials() -> tuple[str, str]:
    """Lee credenciales admin de las variables de entorno en tiempo de ejecución."""
    username = os.getenv("ADMIN_USER", "admin")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    if not password_hash:
        password = os.getenv("ADMIN_PASSWORD", "")
        if password:
            password_hash = get_password_hash(password)
    return username, password_hash


def _ensure_admin_user(db: Session) -> Optional[User]:
    """Crea el usuario admin desde variables de entorno si no existe."""
    admin_user, password_hash = _admin_credentials()
    existing = db.query(User).filter(User.username == admin_user).first()
    if existing:
        return existing

    if not password_hash:
        return None

    user = User(username=admin_user, password_hash=password_hash, is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    _ensure_admin_user(db)

    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(username=current_user.username, is_admin=current_user.is_admin)
