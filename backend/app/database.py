import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import DATABASE_URL

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
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
    """Añade columnas nuevas a tablas existentes (SQLite/Postgres)."""
    new_columns = {
        "channels": [
            ("brief", "TEXT"),
            ("autopilot", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("episodes_per_week", "INTEGER DEFAULT 2 NOT NULL"),
            ("target_minutes", "INTEGER DEFAULT 10 NOT NULL"),
            ("published_at", "TIMESTAMP"),
            ("intro_track", "TEXT"),
            ("bg_music", "TEXT"),
        ],
        "content_plan_entries": [
            ("season", "INTEGER DEFAULT 1 NOT NULL"),
        ],
        "episodes": [
            ("published_at", "TIMESTAMP"),
            ("channel_id", "INTEGER"),
        ],
    }

    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            for table, columns in new_columns.items():
                existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
                for name, ddl in columns:
                    if name not in existing:
                        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
            conn.commit()
    else:
        with engine.connect() as conn:
            for table, columns in new_columns.items():
                result = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :table AND table_schema = 'public'"
                    ),
                    {"table": table},
                )
                existing = {row[0] for row in result}
                for name, ddl in columns:
                    if name not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
            conn.commit()

    # Rellenar channel_id de episodios creados antes de la columna (vía su entrada de plan)
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE episodes SET channel_id = "
            "(SELECT channel_id FROM content_plan_entries "
            "WHERE content_plan_entries.episode_id = episodes.id) "
            "WHERE channel_id IS NULL"
        ))


def init_db():
    print(f"[init_db] DATABASE_URL={DATABASE_URL}", flush=True)
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL[len("sqlite:///") :]
        if not db_path.startswith("/"):
            db_path = str(Path(os.getcwd()) / db_path)
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
