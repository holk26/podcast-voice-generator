import logging
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.config import OUTPUT_DIR, API_PORT, DATA_DIR, init_dirs
from backend.app.database import init_db
from backend.app import models  # noqa: F401 - ensures tables are registered
from backend.app.dependencies import get_current_user
from backend.app.routes import voices, tts, episodes, channels, llm, jobs, books, auth, worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

WEB_PORT = int(os.getenv("WEB_PORT", "5173"))
EXTRA_CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

logger.info("=== Startup diagnostics ===")
logger.info("USER=%s", os.getenv("USER") or os.getenv("USERNAME") or "unknown")
logger.info("CWD=%s", os.getcwd())
logger.info("PYTHONPATH=%s", os.getenv("PYTHONPATH", "<unset>"))
logger.info("DATA_DIR=%s exists=%s", DATA_DIR, Path(DATA_DIR).exists())
logger.info("OUTPUT_DIR=%s exists=%s", OUTPUT_DIR, Path(OUTPUT_DIR).exists())
try:
    logger.info("ls -la /app:\n%s", subprocess.check_output(["ls", "-la", "/app"], text=True))
except Exception as exc:  # noqa: BLE001
    logger.warning("Could not ls /app: %s", exc)

# Asegurar que los directorios existen antes de montar static files
init_dirs()
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_dirs()
    init_db()
    yield


app = FastAPI(title="Podcast Voice Generator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{WEB_PORT}",
        f"http://127.0.0.1:{WEB_PORT}",
    ] + EXTRA_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# Auth router is public (login does not require a token)
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

# Worker router uses its own static-token dependency
app.include_router(worker.router, prefix="/api", tags=["worker"])

# Protected API routers
auth_dep = [Depends(get_current_user)]
app.include_router(voices.router, prefix="/api/voices", tags=["voices"], dependencies=auth_dep)
app.include_router(tts.router, prefix="/api/tts", tags=["tts"], dependencies=auth_dep)
app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"], dependencies=auth_dep)
app.include_router(channels.router, prefix="/api/channels", tags=["channels"], dependencies=auth_dep)
app.include_router(llm.router, prefix="/api/llm", tags=["llm"], dependencies=auth_dep)
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"], dependencies=auth_dep)
app.include_router(books.router, prefix="/api/books", tags=["books"], dependencies=auth_dep)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=API_PORT)
