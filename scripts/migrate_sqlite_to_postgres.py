#!/usr/bin/env python3
"""Migrar datos de SQLite local a PostgreSQL remoto.

Uso (desde la raíz del repo, con el venv activado):
    PYTHONPATH=. DATABASE_URL=postgresql://... python scripts/migrate_sqlite_to_postgres.py
"""
import os
import sys

# Asegurar que podamos importar modelos del backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.models import Channel, Episode, ContentPlanEntry, DiagnosticLog, User

SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///data/app.db")
PG_URL = os.getenv("DATABASE_URL")

if not PG_URL:
    print("ERROR: define DATABASE_URL para PostgreSQL", file=sys.stderr)
    sys.exit(1)

# Conexiones
sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
pg_engine = create_engine(PG_URL)

SQLiteSession = sessionmaker(bind=sqlite_engine)
PGSession = sessionmaker(bind=pg_engine)

src = SQLiteSession()
dst = PGSession()

TABLES_ORDER = [
    ("channels", Channel),
    ("episodes", Episode),
    ("users", User),
    ("diagnostic_logs", DiagnosticLog),
    ("content_plan_entries", ContentPlanEntry),
]


def reset_sequence(table_name: str, session) -> None:
    """Ajusta la secuencia SERIAL de PostgreSQL al máximo id actual."""
    max_id = session.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")).scalar()
    session.execute(
        text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), :max_id, true)"),
        {"max_id": max_id},
    )
    session.commit()


try:
    for table_name, model in TABLES_ORDER:
        rows = src.query(model).all()
        print(f"[migrate] {table_name}: {len(rows)} filas en SQLite")
        if not rows:
            continue

        for row in rows:
            # Convertir a diccionario sin la columna identidad interna de SQLAlchemy
            data = {
                c.key: getattr(row, c.key)
                for c in row.__table__.columns
            }
            dst.merge(model(**data))

        dst.commit()
        reset_sequence(table_name, dst)
        print(f"[migrate] {table_name}: migrado y secuencia reseteada a {len(rows)} filas")

    print("[migrate] Migración completada.")
except Exception as exc:
    dst.rollback()
    print(f"[migrate] ERROR: {exc}", file=sys.stderr)
    raise
finally:
    src.close()
    dst.close()
