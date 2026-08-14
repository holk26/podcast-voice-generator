import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.config import OUTPUT_DIR, API_PORT, init_dirs
from backend.app.database import init_db
from backend.app import models  # noqa: F401 - ensures tables are registered
from backend.app.routes import voices, tts, episodes, channels, llm, jobs, books

WEB_PORT = int(os.getenv("WEB_PORT", "5173"))

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

app.include_router(voices.router, prefix="/api/voices", tags=["voices"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(books.router, prefix="/api/books", tags=["books"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=API_PORT)
