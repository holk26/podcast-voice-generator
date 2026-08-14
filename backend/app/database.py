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
    Base.metadata.create_all(bind=engine)
    _migrate()
