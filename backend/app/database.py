import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate() -> None:
    """Añade columnas nuevas a tablas existentes (SQLite no lo hace create_all)."""
    new_columns = {
        "channels": [
            ("brief", "TEXT"),
            ("autopilot", "BOOLEAN DEFAULT 0 NOT NULL"),
            ("episodes_per_week", "INTEGER DEFAULT 2 NOT NULL"),
            ("target_minutes", "INTEGER DEFAULT 10 NOT NULL"),
            ("published_at", "DATETIME"),
        ],
        "content_plan_entries": [
            ("season", "INTEGER DEFAULT 1 NOT NULL"),
        ],
        "episodes": [
            ("published_at", "DATETIME"),
        ],
    }
    with engine.connect() as conn:
        for table, columns in new_columns.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for name, ddl in columns:
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        conn.commit()


def init_db():
    print(f"[init_db] DATABASE_URL={DATABASE_URL}", flush=True)
    # Normalizar a ruta absoluta; sqlite:/// es relativo, sqlite://// es absoluto.
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[len("sqlite:///") :]
        if not db_path.startswith("/"):
            db_path = str(Path(os.getcwd()) / db_path)
    else:
        db_path = DATABASE_URL
    parent = Path(db_path).parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    print(
        f"[init_db] db_path={db_path} parent={parent} exists={parent.exists()} "
        f"writable={os.access(parent, os.W_OK) if parent.exists() else 'N/A'} "
        f"user={os.getenv('USER') or os.getenv('USERNAME') or 'unknown'} "
        f"cwd={os.getcwd()}",
        flush=True,
    )
    Base.metadata.create_all(bind=engine)
    _migrate()
    print("[init_db] Database initialized successfully.", flush=True)
