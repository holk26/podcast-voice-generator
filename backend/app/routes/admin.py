"""Endpoints de administración del backend."""

import os
import tempfile

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.config import DATABASE_URL, WORKER_TOKEN
from backend.app.dependencies import require_admin
from backend.app.models import Channel, ContentPlanEntry, DiagnosticLog, Episode, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/worker-token", response_model=dict)
def get_worker_token(admin_user: User = Depends(require_admin)):
    """Devuelve el token estático compartido con el worker.

    Útil para configurar el worker local sin tener que leer el .env del servidor.
    Requiere autenticación de administrador.
    """
    return {"worker_token": WORKER_TOKEN}


@router.post("/migrate-sqlite", response_model=dict)
def migrate_sqlite(
    db_file: UploadFile = File(...),
    admin_user: User = Depends(require_admin),
):
    """ Migra datos de un SQLite exportado a la base PostgreSQL activa.

    Solo migra canales, episodios y entradas de plan de contenido.
    No toca el usuario admin existente. Uso puntual para la migración inicial.
    """
    if DATABASE_URL.startswith("sqlite"):
        return {"error": "El backend no está configurado con PostgreSQL"}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        tmp.write(db_file.file.read())
        sqlite_path = tmp.name

    try:
        sqlite_engine = create_engine(
            f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False}
        )
        SQLiteSession = sessionmaker(bind=sqlite_engine)
        PgSession = sessionmaker(bind=create_engine(DATABASE_URL))

        src = SQLiteSession()
        dst = PgSession()

        counts = {}
        try:
            # Vaciar tablas destino (conservar users para no perder admin)
            dst.execute(text("DELETE FROM content_plan_entries"))
            dst.execute(text("DELETE FROM diagnostic_logs"))
            dst.execute(text("DELETE FROM episodes"))
            dst.execute(text("DELETE FROM channels"))
            dst.commit()

            tables = [
                ("channels", Channel),
                ("episodes", Episode),
                ("diagnostic_logs", DiagnosticLog),
                ("content_plan_entries", ContentPlanEntry),
            ]
            for table_name, model in tables:
                rows = src.query(model).all()
                for row in rows:
                    data = {c.key: getattr(row, c.key) for c in row.__table__.columns}
                    dst.add(model(**data))
                dst.commit()
                # Ajustar secuencias SERIAL de PostgreSQL
                max_id = dst.execute(
                    text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
                ).scalar()
                dst.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), :max_id, true)"
                    ),
                    {"max_id": max_id},
                )
                dst.commit()
                counts[table_name] = len(rows)

            return {
                "status": "ok",
                "migrated": counts,
                "database_url": DATABASE_URL.replace(
                    "://", "://***:***@"
                ),
            }
        finally:
            src.close()
            dst.close()
    finally:
        os.unlink(sqlite_path)
