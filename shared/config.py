from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
PREVIEW_DIR = OUTPUT_DIR / "previews"
VOICES_DIR = Path(os.getenv("VOICES_DIR", BASE_DIR / "voices"))
CLONES_DIR = VOICES_DIR / "clones"
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", BASE_DIR / "projects"))
MUSIC_DIR = Path(os.getenv("MUSIC_DIR", BASE_DIR / "music"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", BASE_DIR / "models"))


def init_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    CLONES_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
