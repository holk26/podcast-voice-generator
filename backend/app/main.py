import os
import subprocess
import traceback
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

WEB_PORT = int(os.getenv("WEB_PORT", "5173"))
EXTRA_CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

print("=== Startup diagnostics ===", flush=True)
print(f"USER={os.getenv('USER') or os.getenv('USERNAME') or 'unknown'}", flush=True)
print(f"CWD={os.getcwd()}", flush=True)
print(f"PYTHONPATH={os.getenv('PYTHONPATH', '<unset>')}", flush=True)
print(f"DATA_DIR={DATA_DIR} exists={Path(DATA_DIR).exists()}", flush=True)
print(f"OUTPUT_DIR={OUTPUT_DIR} exists={Path(OUTPUT_DIR).exists()}", flush=True)
try:
    print(f"ls -la /app:\n{subprocess.check_output(['ls', '-la', '/app'], text=True)}", flush=True)
except Exception as exc:  # noqa: BLE001
    print(f"Could not ls /app: {exc}", flush=True)

# Asegurar que los directorios existen antes de montar static files
init_dirs()
try:
    init_db()
except Exception as exc:  # noqa: BLE001
    print(f"init_db failed: {exc}", flush=True)
    traceback.print_exc()
    raise


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
# Compatibilidad con builds antiguos del frontend que apuntan a /auth/login
app.include_router(auth.router, prefix="/auth", tags=["auth-compat"])

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

# Root-level aliases for frontends that don't use the /api prefix.
# The CDN aggressively caches the old index.html/index-*.js which calls
# https://api.podcash.app.moonsbow.com/voices, etc. Rather than relying on
# cache purges we expose both /api/* and /* for the protected routes.
app.include_router(voices.router, prefix="/voices", tags=["voices-root"], dependencies=auth_dep)
app.include_router(tts.router, prefix="/tts", tags=["tts-root"], dependencies=auth_dep)
app.include_router(episodes.router, prefix="/episodes", tags=["episodes-root"], dependencies=auth_dep)
app.include_router(channels.router, prefix="/channels", tags=["channels-root"], dependencies=auth_dep)
app.include_router(llm.router, prefix="/llm", tags=["llm-root"], dependencies=auth_dep)
app.include_router(jobs.router, prefix="/jobs", tags=["jobs-root"], dependencies=auth_dep)
app.include_router(books.router, prefix="/books", tags=["books-root"], dependencies=auth_dep)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=API_PORT)
