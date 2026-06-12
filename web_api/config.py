import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
PREVIEW_DIR = OUTPUT_DIR / "previews"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

try:
    API_PORT = int(os.getenv("API_PORT", "8000"))
except (ValueError, TypeError):
    API_PORT = 8000

try:
    WORKER_PORT = int(os.getenv("WORKER_PORT", "8001"))
except (ValueError, TypeError):
    WORKER_PORT = 8001
