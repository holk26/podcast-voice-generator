"""Almacén clave/valor de ajustes de la aplicación en la base de datos.

Sobrevive redeploys (Postgres), a diferencia de config.yaml o archivos
en el filesystem del contenedor. Toda lectura/escritura está blindada
para no romper el arranque si la tabla aún no existe.
"""
import logging
import threading

from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import SessionLocal
from backend.app.models import AppSetting

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def get_setting(key: str) -> str | None:
    try:
        with _lock, SessionLocal() as db:
            row = db.get(AppSetting, key)
            return row.value if row else None
    except SQLAlchemyError as e:
        logger.debug("get_setting(%s) no disponible aún: %s", key, e)
        return None
    except Exception as e:
        logger.warning("get_setting(%s) falló: %s", key, e)
        return None


def set_setting(key: str, value: str) -> None:
    try:
        with _lock, SessionLocal() as db:
            row = db.get(AppSetting, key)
            if row is None:
                row = AppSetting(key=key)
                db.add(row)
            row.value = value
            db.commit()
    except Exception as e:
        logger.warning("set_setting(%s) falló: %s", key, e)
