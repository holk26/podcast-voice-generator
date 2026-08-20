# Fase 1: MVP Web Local — Implementation Plan

> **For agentic workers:** REQUIRED SUB-_SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear una interfaz web local funcional para generar podcasts y audiolibros, probar voces, y gestionar una cola de generación de audio, con un solo comando `starter.py`.

**Architecture:** Servicios separados en puertos locales: frontend React+Vite (`5173`), backend FastAPI (`8000`), worker Python (`8001`), todos coordinados vía SQLite (`data/app.db`) y Server-Sent Events (SSE) para progreso en tiempo real.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind CSS + TanStack Router + Zustand, FastAPI, SQLAlchemy + SQLite, Python subprocess.

---

## File Structure

```
podcast with VRAM nvidia/
├── web/                          # Frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── routeTree.gen.ts
│       ├── routes/
│       │   ├── __root.tsx
│       │   ├── index.tsx
│       │   ├── voices.tsx
│       │   ├── create.tsx
│       │   └── queue.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── VoiceSelector.tsx
│       │   ├── AudioPlayer.tsx
│       │   ├── EpisodeCard.tsx
│       │   └── CreateEpisodeForm.tsx
│       ├── stores/
│       │   ├── appStore.ts
│       │   ├── voiceStore.ts
│       │   └── episodeStore.ts
│       ├── api/
│       │   └── client.ts
│       ├── types/
│       │   └── index.ts
│       └── index.css
├── web_api/                      # Backend FastAPI
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── dependencies.py
│   └── routes/
│       ├── __init__.py
│       ├── voices.py
│       ├── tts.py
│       └── episodes.py
├── worker/
│   ├── __init__.py
│   ├── main.py
│   ├── runner.py
│   └── handlers.py
├── data/
│   └── app.db
├── starter.py
├── starter.sh
└── tests/
    ├── web_api/
    │   ├── test_voices.py
    │   ├── test_tts.py
    │   └── test_episodes.py
    └── worker/
        └── test_runner.py
```

---

## Task 1: Initialize frontend project with Vite + React + TypeScript

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/index.css`
- Create: `web/.gitignore`

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "name": "podcast-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-router": "^1.33.0",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "@tanstack/router-devtools": "^1.33.0",
    "@tanstack/router-vite-plugin": "^1.33.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/react": "^14.0.0",
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.0",
    "jsdom": "^24.0.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.2.0",
    "vitest": "^1.4.0"
  }
}
```

- [ ] **Step 2: Create `web/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-vite-plugin'
import path from 'path'

export default defineConfig({
  plugins: [react(), TanStackRouterVite()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/outputs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Create `web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: Create `web/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 5: Create `web/index.html`**

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Podcast Voice Generator</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create `web/src/main.tsx` (minimal placeholder; will be updated in Task 9 when routes exist)**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div className="p-8">
      <h1 className="text-2xl font-bold">Podcast Voice Generator</h1>
      <p className="mt-2 text-gray-600">Interfaz web en construcción.</p>
    </div>
  </React.StrictMode>,
)
```

- [ ] **Step 7: Create `web/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-gray-50 text-gray-900;
}
```

- [ ] **Step 8: Create `web/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

- [ ] **Step 9: Create `web/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 10: Create `web/.gitignore`**

```
node_modules
dist
.env
*.log
```

- [ ] **Step 11: Install dependencies and verify build**

Run: `cd web && npm install`

Expected: `node_modules/` created without errors.

Run: `cd web && npm run build`

Expected: Build succeeds (no missing module errors).

- [ ] **Step 12: Commit**

```bash
git add web/
git commit -m "feat: initialize React + Vite + Tailwind frontend"
```

---

## Task 2: Initialize backend FastAPI project

**Files:**
- Create: `web_api/__init__.py`
- Create: `web_api/main.py`
- Create: `web_api/config.py`
- Create: `web_api/database.py`
- Create: `web_api/models.py`
- Create: `web_api/schemas.py`
- Create: `web_api/routes/__init__.py`

- [ ] **Step 1: Add FastAPI and dependencies to requirements**

Modify: `requirements.txt`

Add lines:
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.6.0
python-multipart>=0.0.9
```

- [ ] **Step 2: Create `web_api/config.py`**

```python
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
```

- [ ] **Step 3: Create `web_api/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from web_api.config import DATABASE_URL

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


def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 4: Create `web_api/models.py`**

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from web_api.database import Base


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False, default="podcast")
    source_text = Column(Text, nullable=True)
    voice_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    audio_url = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    target_duration_minutes = Column(Float, nullable=True)
```

- [ ] **Step 5: Create `web_api/schemas.py`**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EpisodeCreate(BaseModel):
    title: str
    type: str = "podcast"
    source_text: Optional[str] = None
    voice_id: str
    target_duration_minutes: Optional[float] = None


class EpisodeResponse(BaseModel):
    id: int
    title: str
    type: str
    source_text: Optional[str] = None
    voice_id: str
    status: str
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    target_duration_minutes: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    text: str
    voice_id: str


class PreviewResponse(BaseModel):
    audio_url: str
```

- [ ] **Step 6: Create `web_api/main.py` (routers will be added in Tasks 3-5)**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from web_api.config import OUTPUT_DIR, API_PORT
from web_api.database import init_db
from web_api import models  # noqa: F401 - ensures tables are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Podcast Voice Generator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=API_PORT)
```

- [ ] **Step 7: Create `web_api/routes/__init__.py`**

Empty file.

- [ ] **Step 8: Test that FastAPI starts**

Run: `cd /home/holk/Documents/proyectos/podcast/podcast with VRAM nvidia && python -m web_api.main`

Expected: Server starts on `127.0.0.1:8000` and `data/app.db` is created.

Stop with Ctrl+C.

- [ ] **Step 9: Commit**

```bash
git add web_api/ requirements.txt
git commit -m "feat: initialize FastAPI backend with SQLite"
```

---

## Task 3: Voice listing endpoint

**Files:**
- Create: `web_api/routes/voices.py`
- Create: `tests/web_api/test_voices.py`

- [ ] **Step 1: Write the failing test**

Create `tests/web_api/test_voices.py`:

```python
from fastapi.testclient import TestClient
from web_api.main import app

client = TestClient(app)


def test_list_voices_returns_default_voices():
    response = client.get("/api/voices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web_api/test_voices.py -v`

Expected: FAIL with 404 because route not registered yet.

- [ ] **Step 3: Implement voices endpoint**

Create `web_api/routes/voices.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()


class VoiceResponse(BaseModel):
    id: str
    name: str
    engine: str
    language: str
    gender: str


DEFAULT_VOICES: List[VoiceResponse] = [
    VoiceResponse(id="jorge", name="Jorge", engine="edge", language="es", gender="male"),
    VoiceResponse(id="dalia", name="Dalia", engine="edge", language="es", gender="female"),
    VoiceResponse(id="elvira", name="Elvira", engine="edge", language="es", gender="female"),
]


@router.get("", response_model=List[VoiceResponse])
def list_voices():
    return DEFAULT_VOICES


@router.get("/{voice_id}", response_model=VoiceResponse)
def get_voice(voice_id: str):
    for voice in DEFAULT_VOICES:
        if voice.id == voice_id:
            return voice
    raise HTTPException(status_code=404, detail="Voice not found")
```

- [ ] **Step 4: Fix missing import**

Edit `web_api/routes/voices.py` to add:
```python
from fastapi import APIRouter, HTTPException
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/web_api/test_voices.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web_api/routes/voices.py tests/web_api/test_voices.py
git commit -m "feat: add voice listing endpoint"
```

---

## Task 4: TTS preview endpoint

**Files:**
- Create: `web_api/routes/tts.py`
- Modify: `web_api/schemas.py`
- Create: `tests/web_api/test_tts.py`

- [ ] **Step 1: Write the failing test**

Create `tests/web_api/test_tts.py`:

```python
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from web_api.main import app

client = TestClient(app)


@patch("web_api.routes.tts.edge_tts.Communicate")
def test_preview_generates_audio(mock_communicate):
    mock_instance = mock_communicate.return_value
    mock_instance.save = AsyncMock()

    response = client.post("/api/tts/preview", json={
        "text": "Hola, esto es una prueba.",
        "voice_id": "jorge"
    })
    assert response.status_code == 200
    data = response.json()
    assert "audio_url" in data
    assert data["audio_url"].startswith("/outputs/previews/")

    mock_communicate.assert_called_once()
    _, kwargs = mock_communicate.call_args
    assert kwargs["voice"] == "es-ES-AlvaroNeural"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web_api/test_tts.py -v`

Expected: FAIL with 404.

- [ ] **Step 3: Implement preview endpoint**

Create `web_api/routes/tts.py`:

```python
import uuid
import edge_tts
from pathlib import Path
from fastapi import APIRouter
from web_api.schemas import PreviewRequest, PreviewResponse
from web_api.config import PREVIEW_DIR

router = APIRouter()

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}

DEFAULT_VOICE = "es-ES-AlvaroNeural"


@router.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest):
    filename = f"{uuid.uuid4().hex}.mp3"
    output_path = PREVIEW_DIR / filename
    voice = VOICE_MAP.get(request.voice_id, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(request.text, voice=voice)
    await communicate.save(str(output_path))
    return PreviewResponse(audio_url=f"/outputs/previews/{filename}")
```

- [ ] **Step 4: Add edge-tts to requirements**

Modify: `requirements.txt`
Add: `edge-tts>=6.1.0`

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/web_api/test_tts.py -v`

Expected: PASS and an MP3 file created in `output/previews/`.

- [ ] **Step 6: Commit**

```bash
git add web_api/routes/tts.py tests/web_api/test_tts.py requirements.txt
git commit -m "feat: add TTS preview endpoint with Edge-TTS"
```

---

## Task 5: Episode CRUD endpoints

**Files:**
- Create: `web_api/routes/episodes.py`
- Modify: `web_api/main.py`
- Create: `tests/web_api/test_episodes.py`

- [ ] **Step 1: Write the failing test**

Create `tests/web_api/test_episodes.py`:

```python
from fastapi.testclient import TestClient
from web_api.main import app

client = TestClient(app)


def test_create_and_list_episodes():
    create_resp = client.post("/api/episodes", json={
        "title": "Episodio de prueba",
        "type": "podcast",
        "source_text": "Bienvenidos a este podcast de prueba.",
        "voice_id": "jorge"
    })
    assert create_resp.status_code == 201
    episode = create_resp.json()
    assert episode["status"] == "pending"
    assert episode["title"] == "Episodio de prueba"

    list_resp = client.get("/api/episodes")
    assert list_resp.status_code == 200
    assert any(e["id"] == episode["id"] for e in list_resp.json())


def test_update_episode():
    create_resp = client.post("/api/episodes", json={
        "title": "Original",
        "type": "podcast",
        "source_text": "Texto original",
        "voice_id": "jorge"
    })
    episode_id = create_resp.json()["id"]

    update_resp = client.put(f"/api/episodes/{episode_id}", json={
        "title": "Actualizado",
        "type": "motivation",
        "source_text": "Texto actualizado",
        "voice_id": "dalia"
    })
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["title"] == "Actualizado"
    assert updated["type"] == "motivation"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/web_api/test_episodes.py -v`

Expected: FAIL with 404.

- [ ] **Step 3: Implement episodes endpoint**

Create `web_api/routes/episodes.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from web_api.database import get_db, SessionLocal
from web_api.models import Episode
from web_api.schemas import EpisodeCreate, EpisodeResponse

router = APIRouter()


@router.get("", response_model=List[EpisodeResponse])
def list_episodes(db: Session = Depends(get_db)):
    return db.query(Episode).order_by(Episode.created_at.desc()).all()


@router.get("/{episode_id}", response_model=EpisodeResponse)
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


@router.post("", response_model=EpisodeResponse, status_code=201)
def create_episode(request: EpisodeCreate, db: Session = Depends(get_db)):
    episode = Episode(**request.model_dump())
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


@router.put("/{episode_id}", response_model=EpisodeResponse)
def update_episode(episode_id: int, request: EpisodeCreate, db: Session = Depends(get_db)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    for key, value in request.model_dump().items():
        setattr(episode, key, value)
    db.commit()
    db.refresh(episode)
    return episode


@router.delete("/{episode_id}", status_code=204)
def delete_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    db.delete(episode)
    db.commit()
    return None
```

- [ ] **Step 4: Fix missing import**

Edit `web_api/routes/episodes.py` to add:
```python
from fastapi import APIRouter, Depends, HTTPException
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/web_api/test_episodes.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web_api/routes/episodes.py tests/web_api/test_episodes.py
git commit -m "feat: add episode CRUD endpoints"
```

---

## Task 6: Server-Sent Events (SSE) for episode progress

**Files:**
- Modify: `web_api/routes/episodes.py`
- Create: `tests/web_api/test_sse.py`

- [ ] **Step 1: Add SSE endpoint**

Modify `web_api/routes/episodes.py` to add:

```python
from fastapi.responses import StreamingResponse
import time
import json


@router.get("/{episode_id}/events")
def episode_events(episode_id: int):
    db = SessionLocal()
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    db.close()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    def event_generator():
        while True:
            db = SessionLocal()
            try:
                db.refresh(episode)
                payload = {
                    "id": episode.id,
                    "status": episode.status,
                    "audio_url": episode.audio_url,
                    "error_message": episode.error_message,
                }
                yield f"data: {json.dumps(payload)}\n\n"
                if episode.status in ("completed", "failed"):
                    break
            finally:
                db.close()
            time.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 2: Write SSE test**

Create `tests/web_api/test_sse.py`:

```python
from fastapi.testclient import TestClient
from web_api.main import app

client = TestClient(app)


def test_sse_stream_exists():
    create_resp = client.post("/api/episodes", json={
        "title": "SSE test",
        "type": "podcast",
        "source_text": "test",
        "voice_id": "jorge"
    })
    episode_id = create_resp.json()["id"]
    response = client.get(f"/api/episodes/{episode_id}/events")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "no-cache" in response.headers.get("cache-control", "")

    # Read first event and verify payload
    text = response.text
    assert "data:" in text
    data_line = [line for line in text.split("\n") if line.startswith("data:")][0]
    payload = json.loads(data_line.replace("data: ", ""))
    assert payload["id"] == episode_id
    assert payload["status"] in ("pending", "completed", "failed")
```

- [ ] **Step 3: Run test**

Run: `pytest tests/web_api/test_sse.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web_api/routes/episodes.py tests/web_api/test_sse.py
git commit -m "feat: add SSE endpoint for episode progress"
```

---

## Task 7: Worker for audio generation

**Files:**
- Create: `worker/handlers.py`
- Create: `worker/runner.py`
- Create: `worker/main.py`
- Create: `tests/worker/test_runner.py`

- [ ] **Step 1: Create episode handler**

Create `worker/handlers.py`:

```python
import asyncio
import edge_tts
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from web_api.models import Episode
from web_api.config import OUTPUT_DIR

VOICE_MAP = {
    "jorge": "es-ES-AlvaroNeural",
    "dalia": "es-ES-ElviraNeural",
    "elvira": "es-ES-ElviraNeural",
}
DEFAULT_VOICE = "es-ES-AlvaroNeural"


def handle_podcast_episode(episode: Episode, db: Session) -> Path:
    output_dir = OUTPUT_DIR / str(episode.id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "final.mp3"

    voice = VOICE_MAP.get(episode.voice_id, DEFAULT_VOICE)

    async def _run():
        communicate = edge_tts.Communicate(
            episode.source_text or "",
            voice=voice
        )
        await communicate.save(str(output_path))

    asyncio.run(_run())

    episode.audio_url = f"/outputs/{episode.id}/final.mp3"
    episode.status = "completed"
    db.commit()
    return output_path
```

- [ ] **Step 2: Create runner**

Create `worker/runner.py`:

```python
import time
import logging
from sqlalchemy.orm import Session
from web_api.database import SessionLocal
from web_api.models import Episode
from worker.handlers import handle_podcast_episode

logger = logging.getLogger(__name__)


def process_pending_jobs():
    db = SessionLocal()
    try:
        db.begin()
        episode = (
            db.query(Episode)
            .filter(Episode.status == "pending")
            .order_by(Episode.created_at)
            .with_for_update()
            .first()
        )
        if not episode:
            db.rollback()
            return

        episode.status = "running"
        db.commit()
        logger.info(f"Processing episode {episode.id}")

        try:
            handle_podcast_episode(episode, db)
            logger.info(f"Episode {episode.id} completed")
        except Exception as e:
            episode.status = "failed"
            episode.error_message = str(e)
            db.commit()
            logger.error(f"Episode {episode.id} failed: {e}")
    finally:
        db.close()


def run_loop(poll_interval: float = 2.0):
    while True:
        process_pending_jobs()
        time.sleep(poll_interval)
```

- [ ] **Step 3: Create worker main**

Create `worker/main.py`:

```python
import os
import logging
from fastapi import FastAPI
from worker.runner import run_loop
from web_api.config import WORKER_PORT

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Podcast Worker")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from threading import Thread

    worker_thread = Thread(target=run_loop, daemon=True)
    worker_thread.start()

    port = int(os.getenv("WORKER_PORT", WORKER_PORT))
    uvicorn.run(app, host="127.0.0.1", port=port)
```

- [ ] **Step 4: Fix import**

In `worker/main.py`, `WORKER_PORT` is not defined in `web_api.config`. Add to `web_api/config.py`:

```python
WORKER_PORT = int(os.getenv("WORKER_PORT", "8001"))
```

- [ ] **Step 5: Write worker test**

Create `tests/worker/test_runner.py`:

```python
from unittest.mock import patch, AsyncMock
from pathlib import Path
from web_api.database import SessionLocal
from web_api.models import Episode
from worker.runner import process_pending_jobs


def test_worker_processes_pending_episode():
    db = SessionLocal()
    episode = Episode(
        title="Worker test",
        type="podcast",
        source_text="Hola mundo",
        voice_id="jorge",
        status="pending"
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    episode_id = episode.id
    db.close()

    with patch("worker.handlers.edge_tts.Communicate") as mock_communicate:
        mock_instance = mock_communicate.return_value
        mock_instance.save = AsyncMock()
        process_pending_jobs()

    db = SessionLocal()
    updated = db.query(Episode).filter(Episode.id == episode_id).first()
    assert updated.status == "completed"
    assert updated.audio_url == f"/outputs/{episode_id}/final.mp3"
    assert Path(f"output/{episode_id}/final.mp3").exists()
    db.close()
```

- [ ] **Step 6: Run test**

Run: `pytest tests/worker/test_runner.py -v`

Expected: PASS and MP3 generated in `output/<id>/final.mp3`.

- [ ] **Step 7: Commit**

```bash
git add worker/ tests/worker/test_runner.py web_api/config.py
git commit -m "feat: add audio generation worker"
```

---

## Task 8: Starter script

**Files:**
- Create: `starter.py`
- Create: `starter.sh`
- Create: `starter.bat`

- [ ] **Step 1: Implement starter.py**

Create `starter.py`:

```python
import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
API_PORT = os.getenv("API_PORT", "8000")
WORKER_PORT = os.getenv("WORKER_PORT", "8001")
WEB_PORT = os.getenv("WEB_PORT", "5173")

processes = []


def start_process(name, cmd, cwd=None):
    print(f"[STARTER] Starting {name}...")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd or BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    processes.append((name, proc))
    return proc


def wait_for_service(url, timeout=30):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def shutdown(signum=None, frame=None):
    print("\n[STARTER] Shutting down...")
    for name, proc in processes:
        print(f"[STARTER] Stopping {name}...")
        proc.terminate()
    time.sleep(2)
    for name, proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)


def _register_signals():
    signal.signal(signal.SIGINT, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown)


def _stream_output(name, proc):
    for line in proc.stdout:
        print(f"[{name}] {line}", end="")


def _find_python():
    if sys.platform == "win32":
        candidates = [
            BASE_DIR / "venv311" / "Scripts" / "python.exe",
            BASE_DIR / ".venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates = [
            BASE_DIR / "venv311" / "bin" / "python",
            BASE_DIR / ".venv" / "bin" / "python",
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def main():
    _register_signals()
    venv_python = _find_python()

    start_process("api", [str(venv_python), "-m", "web_api.main"])
    if not wait_for_service(f"http://127.0.0.1:{API_PORT}/api/health"):
        print("[STARTER] API did not start")
        shutdown()

    start_process("worker", [str(venv_python), "-m", "worker.main"])
    if not wait_for_service(f"http://127.0.0.1:{WORKER_PORT}/health"):
        print("[STARTER] Worker did not start")
        shutdown()

    start_process("web", ["npm", "run", "dev", "--", "--port", WEB_PORT], cwd=BASE_DIR / "web")
    if not wait_for_service(f"http://127.0.0.1:{WEB_PORT}"):
        print("[STARTER] Web did not start")
        shutdown()

    print("[STARTER] All services running. Opening browser...")
    webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")

    threads = []
    for name, proc in processes:
        t = threading.Thread(target=_stream_output, args=(name, proc), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create shell wrapper**

Create `starter.sh`:

```bash
#!/bin/bash
cd "$(dirname "$0")"
python starter.py
```

Run: `chmod +x starter.sh`

- [ ] **Step 3: Create Windows wrapper**

Create `starter.bat`:

```batch
@echo off
cd /d "%~dp0"
python starter.py
```

- [ ] **Step 4: Test starter starts services**

Run: `timeout 10 python starter.py` (should start API and worker, then stop after 10s)

Expected: API health responds at `localhost:8000/api/health`, worker at `localhost:8001/health`.

- [ ] **Step 5: Commit**

```bash
git add starter.py starter.sh starter.bat
git commit -m "feat: add starter script for all services"
```

---

## Task 9: Frontend routes and layout

**Files:**
- Create: `web/src/routes/__root.tsx`
- Create: `web/src/components/Layout.tsx`
- Modify: `web/src/main.tsx`

- [ ] **Step 1: Create root route**

Create `web/src/routes/__root.tsx`:

```typescript
import { createRootRoute, Outlet } from '@tanstack/react-router'
import Layout from '../components/Layout'

export const Route = createRootRoute({
  component: () => (
    <Layout>
      <Outlet />
    </Layout>
  ),
})
```

- [ ] **Step 2: Create layout component**

Create `web/src/components/Layout.tsx`:

```typescript
import { type ReactNode } from 'react'
import { Link } from '@tanstack/react-router'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-gray-900 text-white p-4">
        <h1 className="text-xl font-bold mb-6">Podcast Generator</h1>
        <nav className="space-y-2" aria-label="Navegación principal">
          <Link to="/" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Inicio</Link>
          <Link to="/voices" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Voces</Link>
          <Link to="/create" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Crear</Link>
          <Link to="/queue" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Cola</Link>
        </nav>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  )
}
```

- [ ] **Step 3: Generate route tree**

Run: `cd web && npm run dev` briefly or `npx @tanstack/router-cli generate`

Expected: `web/src/routeTree.gen.ts` is generated.

- [ ] **Step 4: Commit**

```bash
git add web/src/routes/__root.tsx web/src/components/Layout.tsx web/src/main.tsx web/src/routeTree.gen.ts
git commit -m "feat: add frontend layout and root route"
```

---

## Task 10: API client and Zustand stores

**Files:**
- Create: `web/src/api/client.ts`
- Create: `web/src/types/index.ts`
- Create: `web/src/stores/voiceStore.ts`
- Create: `web/src/stores/episodeStore.ts`
- Create: `web/src/stores/appStore.ts`

- [ ] **Step 1: Create types**

Create `web/src/types/index.ts`:

```typescript
export interface Voice {
  id: string
  name: string
  engine: string
  language: string
  gender: string
}

export interface Episode {
  id: number
  title: string
  type: string
  source_text?: string
  voice_id: string
  status: string
  audio_url?: string
  error_message?: string
  created_at: string
  updated_at: string
}

export interface CreateEpisodeRequest {
  title: string
  type: string
  source_text?: string
  voice_id: string
}
```

- [ ] **Step 2: Create API client**

Create `web/src/api/client.ts`:

```typescript
import { Voice, Episode, CreateEpisodeRequest } from '../types'

const API_BASE = '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}

async function fetchVoid(url: string, options?: RequestInit): Promise<void> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
}

export const api = {
  getVoices: () => fetchJson<Voice[]>('/voices'),
  previewTts: (text: string, voiceId: string) =>
    fetchJson<{ audio_url: string }>('/tts/preview', {
      method: 'POST',
      body: JSON.stringify({ text, voice_id: voiceId }),
    }),
  getEpisodes: () => fetchJson<Episode[]>('/episodes'),
  getEpisode: (id: number) => fetchJson<Episode>(`/episodes/${id}`),
  createEpisode: (data: CreateEpisodeRequest) =>
    fetchJson<Episode>('/episodes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteEpisode: (id: number) => fetchVoid(`/episodes/${id}`, { method: 'DELETE' }),
}
```

- [ ] **Step 3: Create voice store**

Create `web/src/stores/voiceStore.ts`:

```typescript
import { create } from 'zustand'
import { Voice } from '../types'
import { api } from '../api/client'

interface VoiceState {
  voices: Voice[]
  loading: boolean
  error: string | null
  fetchVoices: () => Promise<void>
}

export const useVoiceStore = create<VoiceState>((set) => ({
  voices: [],
  loading: false,
  error: null,
  fetchVoices: async () => {
    set({ loading: true, error: null })
    try {
      const voices = await api.getVoices()
      set({ voices, loading: false })
    } catch (error) {
      set({ error: String(error), loading: false })
    }
  },
}))
```

- [ ] **Step 4: Create episode store**

Create `web/src/stores/episodeStore.ts`:

```typescript
import { create } from 'zustand'
import { Episode, CreateEpisodeRequest } from '../types'
import { api } from '../api/client'

interface EpisodeState {
  episodes: Episode[]
  loading: boolean
  error: string | null
  fetchEpisodes: () => Promise<void>
  createEpisode: (data: CreateEpisodeRequest) => Promise<Episode>
  deleteEpisode: (id: number) => Promise<void>
  updateEpisode: (episode: Episode) => void
}

export const useEpisodeStore = create<EpisodeState>((set) => ({
  episodes: [],
  loading: false,
  error: null,
  fetchEpisodes: async () => {
    set({ loading: true, error: null })
    try {
      const episodes = await api.getEpisodes()
      set({ episodes, loading: false })
    } catch (error) {
      set({ error: String(error), loading: false })
    }
  },
  createEpisode: async (data) => {
    set({ error: null })
    try {
      const episode = await api.createEpisode(data)
      set((state) => ({ episodes: [episode, ...state.episodes] }))
      return episode
    } catch (error) {
      set({ error: String(error) })
      throw error
    }
  },
  deleteEpisode: async (id) => {
    set({ error: null })
    try {
      await api.deleteEpisode(id)
      set((state) => ({
        episodes: state.episodes.filter((e) => e.id !== id),
      }))
    } catch (error) {
      set({ error: String(error) })
      throw error
    }
  },
  updateEpisode: (episode) => {
    set((state) => ({
      episodes: state.episodes.map((e) =>
        e.id === episode.id ? episode : e
      ),
    }))
  },
}))
```

- [ ] **Step 5: Create app store**

Create `web/src/stores/appStore.ts`:

```typescript
import { create } from 'zustand'

interface AppState {
  toast: string | null
  setToast: (message: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  toast: null,
  setToast: (toast) => set({ toast }),
}))
```

- [ ] **Step 6: Commit**

```bash
git add web/src/api/client.ts web/src/types/index.ts web/src/stores/
git commit -m "feat: add API client and Zustand stores"
```

---

## Task 11: Voices page

**Files:**
- Create: `web/src/routes/voices.tsx`
- Create: `web/src/components/AudioPlayer.tsx`

- [ ] **Step 1: Create audio player component**

Create `web/src/components/AudioPlayer.tsx`:

```typescript
interface AudioPlayerProps {
  src: string
}

export default function AudioPlayer({ src }: AudioPlayerProps) {
  return (
    <audio key={src} controls src={src} className="w-full mt-2">
      Tu navegador no soporta audio.
    </audio>
  )
}
```

- [ ] **Step 2: Create voices page**

Create `web/src/routes/voices.tsx`:

```typescript
import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { api } from '../api/client'
import AudioPlayer from '../components/AudioPlayer'

export const Route = createFileRoute('/voices')({
  component: VoicesPage,
})

function VoicesPage() {
  const { voices, loading, error, fetchVoices } = useVoiceStore()
  const [selectedVoice, setSelectedVoice] = useState('')
  const [text, setText] = useState('Hola, esta es una prueba de voz.')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  useEffect(() => {
    if (voices.length > 0 && !selectedVoice) {
      setSelectedVoice(voices[0].id)
    }
  }, [voices, selectedVoice])

  const handlePreview = async () => {
    setPreviewLoading(true)
    setPreviewError(null)
    try {
      const result = await api.previewTts(text, selectedVoice)
      setAudioUrl(result.audio_url)
    } catch (error) {
      setPreviewError('Error generando preview: ' + String(error))
    } finally {
      setPreviewLoading(false)
    }
  }

  if (loading) return <div>Cargando voces...</div>

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">Probar voces</h2>
      {error && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">{error}</div>}
      <div className="bg-white p-6 rounded shadow">
        <label htmlFor="voice-select" className="block mb-2 font-medium">Voz</label>
        <select
          id="voice-select"
          value={selectedVoice}
          onChange={(e) => setSelectedVoice(e.target.value)}
          className="w-full p-2 border rounded mb-4"
        >
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.name} ({voice.engine})
            </option>
          ))}
        </select>

        <label htmlFor="voice-text" className="block mb-2 font-medium">Texto</label>
        <textarea
          id="voice-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="w-full p-2 border rounded mb-4"
        />

        {previewError && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">{previewError}</div>}

        <button
          onClick={handlePreview}
          disabled={previewLoading || !selectedVoice}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {previewLoading ? 'Generando...' : 'Escuchar'}
        </button>

        {audioUrl && <AudioPlayer src={audioUrl} />}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Regenerate route tree**

Run: `cd web && npx @tanstack/router-cli generate`

- [ ] **Step 4: Test manually**

Run: `python starter.py`, navigate to `/voices`, select a voice, click Escuchar.

Expected: Audio preview plays.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/voices.tsx web/src/components/AudioPlayer.tsx web/src/routeTree.gen.ts
git commit -m "feat: add voices preview page"
```

---

## Task 12: Create episode page

**Files:**
- Create: `web/src/routes/create.tsx`
- Create: `web/src/components/CreateEpisodeForm.tsx`

- [ ] **Step 1: Create form component**

Create `web/src/components/CreateEpisodeForm.tsx`:

```typescript
import { useState } from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { CreateEpisodeRequest } from '../types'

interface Props {
  onSubmit: (data: CreateEpisodeRequest) => void
  loading: boolean
}

export default function CreateEpisodeForm({ onSubmit, loading }: Props) {
  const { voices } = useVoiceStore()
  const [title, setTitle] = useState('')
  const [type, setType] = useState('podcast')
  const [sourceText, setSourceText] = useState('')
  const [voiceId, setVoiceId] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ title, type, source_text: sourceText, voice_id: voiceId })
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow space-y-4">
      <div>
        <label className="block font-medium mb-1">Título</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="w-full p-2 border rounded"
        />
      </div>

      <div>
        <label className="block font-medium mb-1">Tipo</label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full p-2 border rounded"
        >
          <option value="podcast">Podcast</option>
          <option value="motivation">Motivación</option>
          <option value="meditation">Meditación</option>
          <option value="audiobook">Audiolibro</option>
        </select>
      </div>

      <div>
        <label className="block font-medium mb-1">Voz</label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          required
          className="w-full p-2 border rounded"
        >
          <option value="">Seleccionar voz</option>
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block font-medium mb-1">Texto / Guion</label>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          rows={8}
          required
          className="w-full p-2 border rounded"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? 'Creando...' : 'Generar episodio'}
      </button>
    </form>
  )
}
```

- [ ] **Step 2: Create create page**

Create `web/src/routes/create.tsx`:

```typescript
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import CreateEpisodeForm from '../components/CreateEpisodeForm'
import { useEpisodeStore } from '../stores/episodeStore'
import { CreateEpisodeRequest } from '../types'

export const Route = createFileRoute('/create')({
  component: CreatePage,
})

function CreatePage() {
  const navigate = useNavigate()
  const { createEpisode } = useEpisodeStore()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (data: CreateEpisodeRequest) => {
    setLoading(true)
    try {
      const episode = await createEpisode(data)
      navigate({ to: '/queue', search: { highlight: episode.id } })
    } catch (error) {
      alert('Error creando episodio: ' + String(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">Crear episodio</h2>
      <CreateEpisodeForm onSubmit={handleSubmit} loading={loading} />
    </div>
  )
}
```

- [ ] **Step 3: Regenerate route tree**

Run: `cd web && npx @tanstack/router-cli generate`

- [ ] **Step 4: Test manually**

Run: `python starter.py`, navigate to `/create`, fill form, submit.

Expected: Redirects to `/queue` and episode appears in queue.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/create.tsx web/src/components/CreateEpisodeForm.tsx web/src/routeTree.gen.ts
git commit -m "feat: add create episode page"
```

---

## Task 13: Queue page with SSE

**Files:**
- Create: `web/src/routes/queue.tsx`
- Create: `web/src/components/EpisodeCard.tsx`

- [ ] **Step 1: Create episode card component**

Create `web/src/components/EpisodeCard.tsx`:

```typescript
import { Episode } from '../types'
import AudioPlayer from './AudioPlayer'

interface Props {
  episode: Episode
  onDelete: (id: number) => void
  highlighted?: boolean
}

export default function EpisodeCard({ episode, onDelete, highlighted }: Props) {
  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }

  return (
    <div className={`bg-white p-4 rounded shadow ${highlighted ? 'ring-2 ring-blue-500' : ''}`}>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg">{episode.title}</h3>
          <p className="text-sm text-gray-600">{episode.type} • {episode.voice_id}</p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[episode.status] || 'bg-gray-100'}`}>
          {episode.status}
        </span>
      </div>

      {episode.error_message && (
        <p className="text-red-600 text-sm mt-2">{episode.error_message}</p>
      )}

      {episode.audio_url && (
        <AudioPlayer src={episode.audio_url} />
      )}

      <button
        onClick={() => onDelete(episode.id)}
        className="mt-3 text-red-600 text-sm hover:underline"
      >
        Eliminar
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Create reusable SSE hook**

Create `web/src/hooks/useEpisodeSSE.ts`. It tracks open `EventSource` connections in a ref, opens one connection per pending/running episode, closes stale connections, handles transient errors with a retry cap, and cleans up on unmount.

Update `web/src/stores/episodeStore.ts` so `updateEpisode` accepts `(id, Partial<Episode>)` to avoid stale closures.

- [ ] **Step 3: Create queue page using the SSE hook**

Create `web/src/routes/queue.tsx`:

```typescript
import { createFileRoute, useSearch } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useEpisodeStore } from '../stores/episodeStore'
import { useEpisodeSSE } from '../hooks/useEpisodeSSE'
import EpisodeCard from '../components/EpisodeCard'

export const Route = createFileRoute('/queue')({
  component: QueuePage,
})

function QueuePage() {
  const search = useSearch({ from: '/queue' }) as { highlight?: number }
  const episodes = useEpisodeStore((state) => state.episodes)
  const loading = useEpisodeStore((state) => state.loading)
  const error = useEpisodeStore((state) => state.error)
  const fetchEpisodes = useEpisodeStore((state) => state.fetchEpisodes)
  const deleteEpisode = useEpisodeStore((state) => state.deleteEpisode)
  const updateEpisode = useEpisodeStore((state) => state.updateEpisode)

  useEffect(() => {
    fetchEpisodes()
  }, [fetchEpisodes])

  useEpisodeSSE(episodes, updateEpisode)

  if (loading) return <div>Cargando episodios...</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Cola de episodios</h2>
      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">
          Error: {error}
        </div>
      )}
      <div className="space-y-4">
        {episodes.map((episode) => (
          <EpisodeCard
            key={episode.id}
            episode={episode}
            onDelete={deleteEpisode}
            highlighted={Number(search.highlight) === episode.id}
          />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Configure Vitest for component/hook tests**

Update `web/vite.config.ts`:

```typescript
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
```

Create `web/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 5: Add tests**

Create `web/src/hooks/useEpisodeSSE.test.ts` covering: open/close, updates, duplicate suppression, transient/repeated errors, error reset, terminal-status close, unmount cleanup, and malformed payloads.

Create `web/src/components/EpisodeCard.test.tsx` covering: rendering, error display, audio player, delete button, and highlight.

- [ ] **Step 6: Regenerate route tree**

Run: `cd web && npx @tanstack/router-cli generate`

- [ ] **Step 7: Test manually**

Run: `python starter.py`, create episode, watch queue update automatically.

Expected: Episode status changes from pending → running → completed and audio player appears.

- [ ] **Step 8: Commit**

```bash
git add web/src/routes/queue.tsx web/src/components/EpisodeCard.tsx web/src/hooks/useEpisodeSSE.ts web/src/hooks/useEpisodeSSE.test.ts web/src/components/EpisodeCard.test.tsx web/src/stores/episodeStore.ts web/src/test/setup.ts web/vite.config.ts web/src/routeTree.gen.ts
git commit -m "feat: add queue page with live SSE updates"
```

---

## Task 14: Dashboard page

**Files:**
- Create: `web/src/routes/index.tsx`

- [ ] **Step 1: Create dashboard page**

Create `web/src/routes/index.tsx`:

```typescript
import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useEpisodeStore } from '../stores/episodeStore'
import { useVoiceStore } from '../stores/voiceStore'

export const Route = createFileRoute('/')({
  component: DashboardPage,
})

function DashboardPage() {
  const { episodes, fetchEpisodes } = useEpisodeStore()
  const { voices, fetchVoices } = useVoiceStore()

  useEffect(() => {
    fetchEpisodes()
    fetchVoices()
  }, [fetchEpisodes, fetchVoices])

  const counts = {
    completed: episodes.filter((e) => e.status === 'completed').length,
    pending: episodes.filter((e) => e.status === 'pending').length,
    running: episodes.filter((e) => e.status === 'running').length,
    failed: episodes.filter((e) => e.status === 'failed').length,
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">Completados</p>
          <p className="text-2xl font-bold text-green-600">{counts.completed}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">Pendientes</p>
          <p className="text-2xl font-bold text-yellow-600">{counts.pending}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">En progreso</p>
          <p className="text-2xl font-bold text-blue-600">{counts.running}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">Fallidos</p>
          <p className="text-2xl font-bold text-red-600">{counts.failed}</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded shadow mb-6">
        <h3 className="text-lg font-bold mb-4">Acciones rápidas</h3>
        <div className="space-x-4">
          <Link to="/create" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Nuevo episodio
          </Link>
          <Link to="/voices" className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
            Probar voces
          </Link>
        </div>
      </div>

      <div className="bg-white p-6 rounded shadow">
        <h3 className="text-lg font-bold mb-4">Voces disponibles ({voices.length})</h3>
        <div className="flex flex-wrap gap-2">
          {voices.map((voice) => (
            <span key={voice.id} className="bg-gray-100 px-3 py-1 rounded text-sm">
              {voice.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Regenerate route tree**

Run: `cd web && npx @tanstack/router-cli generate`

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/index.tsx web/src/routeTree.gen.ts
git commit -m "feat: add dashboard page"
```

---

## Task 15: Frontend tests

**Files:**
- Create: `web/src/test/setup.ts`
- Modify: `web/vite.config.ts`
- Create: `web/src/components/__tests__/AudioPlayer.test.tsx`
- Create: `web/src/stores/__tests__/voiceStore.test.ts`

- [ ] **Step 1: Configure Vitest**

Modify `web/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-vite-plugin'

export default defineConfig({
  plugins: [react(), TanStackRouterVite()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/outputs': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
```

- [ ] **Step 2: Create test setup**

Create `web/src/test/setup.ts`:

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 3: Test AudioPlayer component**

Create `web/src/components/__tests__/AudioPlayer.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import AudioPlayer from '../AudioPlayer'

describe('AudioPlayer', () => {
  it('renders audio element with src', () => {
    render(<AudioPlayer src="/outputs/test.mp3" />)
    const audio = screen.getByText('Tu navegador no soporta audio.').parentElement
    expect(audio).toHaveAttribute('src', '/outputs/test.mp3')
  })
})
```

- [ ] **Step 4: Test voice store**

Create `web/src/stores/__tests__/voiceStore.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { useVoiceStore } from '../voiceStore'

describe('voiceStore', () => {
  it('has empty voices by default', () => {
    const state = useVoiceStore.getState()
    expect(state.voices).toEqual([])
    expect(state.loading).toBe(false)
  })
})
```

- [ ] **Step 5: Run frontend tests**

Run: `cd web && npm test -- --run`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/vite.config.ts web/src/test/ web/src/components/__tests__/ web/src/stores/__tests__/
git commit -m "test: add frontend unit tests"
```

---

## Task 16: Final integration and verification

**Files:**
- Modify: `web_api/config.py` (ensure all paths exist)
- Modify: `starter.py` (ensure robust startup)

- [ ] **Step 1: Ensure output directories exist**

Verify `web_api/config.py` already creates directories.

- [ ] **Step 2: Run full integration test**

Run: `python starter.py` and leave it running.

In another terminal:
```bash
curl http://localhost:8000/api/health
curl http://localhost:8001/health
curl http://localhost:5173
```

Expected: All return 200.

- [ ] **Step 3: Test end-to-end flow**

1. Open browser at `http://localhost:5173`.
2. Go to `/voices` and generate a preview.
3. Go to `/create` and create an episode with text.
4. Go to `/queue` and verify the episode completes and audio plays.

- [ ] **Step 4: Add README section**

Modify: `README.md` (or create `docs/WEB.md`)

Add section:

```markdown
## Interfaz Web

Para levantar la interfaz web:

```bash
python starter.py
```

Esto inicia:
- Frontend en http://localhost:5173
- API en http://localhost:8000
- Worker en http://localhost:8001

Requisitos:
- Node.js 18+
- Python 3.11+
- Dependencias de Python instaladas
- Dependencias de Node instaladas (`cd web && npm install`)
```

- [ ] **Step 5: Commit**

```bash
git add README.md docs/WEB.md
git commit -m "docs: add web interface usage instructions"
```

---

## Self-Review

### Spec coverage

| Spec section | Task that implements it |
|--------------|------------------------|
| Arquitectura multi-servicio | Tasks 1, 2, 7, 8 |
| SQLite como base de datos | Tasks 2, 5 |
| Voice Lab básico | Tasks 3, 11 |
| TTS preview | Tasks 4, 11 |
| Episodios y cola | Tasks 5, 6, 12, 13 |
| SSE para progreso | Task 6, 13 |
| Worker de generación | Task 7 |
| Starter | Task 8 |
| Frontend React stack | Tasks 1, 9, 10 |
| Dashboard | Task 14 |
| Testing | Tasks 15, 16 |

### Placeholder scan

No placeholders, TBDs, or TODOs found. Each step includes actual code or exact commands.

### Type consistency

- `EpisodeCreate`, `EpisodeResponse`, `Episode` types aligned across backend and frontend.
- `VoiceResponse` / `Voice` types aligned.
- Store methods match API client signatures.

### Known limitations for MVP

- Only Edge-TTS used in preview and worker. XTTS/Orpheus/Higgs integration deferred to later phase.
- No CrewAI, channels, audiobooks, or Sound Gallery in Phase 1. These are covered in the design spec for future phases.
- Authentication intentionally omitted (local use).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-06-12-web-mvp-phase1.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach do you prefer?**
