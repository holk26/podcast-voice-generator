# Canales y CrewAI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir canales de contenido y un flujo CrewAI + Ollama que proponga planes editoriales y genere guiones convertidos en episodios de audio.

**Architecture:** Se reutiliza el flujo de episodios y worker existente. Se añaden dos modelos SQLite (`Channel`, `ContentPlanEntry`), un servicio CrewAI con dos crews (plan y script), endpoints REST para canales/plan, y pantallas React para gestionarlos.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, CrewAI, Ollama, React, Vite, Tailwind, TanStack Router, Zustand.

---

## File Structure

### Backend
- `web_api/models.py` — añade `Channel` y `ContentPlanEntry` junto a `Episode`.
- `web_api/schemas.py` — añade schemas Pydantic para canales y entradas de plan.
- `web_api/config.py` — añade helpers para leer config de Ollama.
- `web_api/services/crew_service.py` — crews de CrewAI para plan y guion.
- `web_api/services/llm_provider.py` — wrapper de Ollama para CrewAI.
- `web_api/routes/channels.py` — endpoints de canales y plan editorial.
- `web_api/routes/llm.py` — endpoint `/api/llm/status`.
- `web_api/main.py` — registra routers nuevos.

### Frontend
- `web/src/types/index.ts` — añade `Channel`, `ContentPlanEntry`, `CreateChannelRequest`, etc.
- `web/src/api/client.ts` — métodos para canales y plan.
- `web/src/stores/channelStore.ts` — estado de canales y entradas.
- `web/src/routes/channels.tsx` — lista de canales.
- `web/src/routes/channels.new.tsx` — crear canal.
- `web/src/routes/channels.$id.plan.tsx` — plan editorial.
- `web/src/routes/studio.tsx` — CrewAI Studio.
- `web/src/components/ChannelCard.tsx`
- `web/src/components/ChannelForm.tsx`
- `web/src/components/ContentPlanList.tsx`
- `web/src/components/PlanEntryCard.tsx`
- `web/src/components/StudioPanel.tsx`
- `web/src/components/Layout.tsx` — añade enlaces.

### Tests
- `tests/web_api/test_channels.py`
- `tests/web_api/test_crew_service.py`
- `web/src/stores/__tests__/channelStore.test.ts`
- `web/src/components/__tests__/ChannelForm.test.tsx`
- `web/src/components/__tests__/PlanEntryCard.test.tsx`

---

### Task 1: Instalar dependencias

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Añadir `crewai` y cliente de Ollama**

```text
# requirements.txt (append)
crewai>=0.30.0
ollama>=0.1.0
```

- [ ] **Step 2: Instalar en el entorno activo**

```bash
cd "/home/holk/Documents/proyectos/podcast/podcast with VRAM nvidia"
source venv311/bin/activate
pip install crewai ollama
```

- [ ] **Step 3: Verificar instalación**

```bash
python -c "import crewai; import ollama; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add crewai and ollama dependencies"
```

---

### Task 2: Configuración de Ollama

**Files:**
- Modify: `config.yaml`
- Modify: `web_api/config.py`

- [ ] **Step 1: Añadir sección `llm` a `config.yaml`**

```yaml
llm:
  provider: ollama
  base_url: http://localhost:11434
  default_model: llama3.1:8b
```

- [ ] **Step 2: Añadir helpers en `web_api/config.py`**

```python
import os
import yaml


def _load_config() -> dict:
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


_CONFIG = _load_config()
_LLM_CONFIG = _CONFIG.get("llm", {})

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", _LLM_CONFIG.get("base_url", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", _LLM_CONFIG.get("default_model", "llama3.1:8b"))
```

- [ ] **Step 3: Commit**

```bash
git add config.yaml web_api/config.py
git commit -m "config: add ollama settings"
```

---

### Task 3: Modelos de base de datos

**Files:**
- Modify: `web_api/models.py`

- [ ] **Step 1: Añadir modelos `Channel` y `ContentPlanEntry`**

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    niche = Column(String, nullable=True)
    format = Column(String, nullable=False, default="podcast")
    default_voice_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    entries = relationship("ContentPlanEntry", back_populates="channel", cascade="all, delete-orphan")


class ContentPlanEntry(Base):
    __tablename__ = "content_plan_entries"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    scheduled_date = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="draft")
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    channel = relationship("Channel", back_populates="entries")
    episode = relationship("Episode")
```

- [ ] **Step 2: Commit**

```bash
git add web_api/models.py
git commit -m "feat: add Channel and ContentPlanEntry models"
```

---

### Task 4: Schemas Pydantic

**Files:**
- Modify: `web_api/schemas.py`

- [ ] **Step 1: Añadir schemas**

```python
from typing import Optional, List


class ChannelBase(BaseModel):
    name: str
    description: Optional[str] = None
    niche: Optional[str] = None
    format: str = "podcast"
    default_voice_id: str
    is_active: bool = True


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    format: Optional[str] = None
    default_voice_id: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelResponse(ChannelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlanEntryBase(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: Optional[datetime] = None


class PlanEntryCreate(PlanEntryBase):
    pass


class PlanEntryResponse(PlanEntryBase):
    id: int
    channel_id: int
    status: str
    episode_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChannelWithPlanResponse(ChannelResponse):
    entries: List[PlanEntryResponse] = []
```

- [ ] **Step 2: Commit**

```bash
git add web_api/schemas.py
git commit -m "feat: add channel and plan schemas"
```

---

### Task 5: LLM provider para CrewAI

**Files:**
- Create: `web_api/services/llm_provider.py`

- [ ] **Step 1: Crear wrapper de Ollama para CrewAI**

```python
import os
from crewai import LLM
from web_api.config import OLLAMA_BASE_URL, OLLAMA_MODEL


def get_llm(model: str | None = None) -> LLM:
    return LLM(
        model=f"ollama/{model or OLLAMA_MODEL}",
        base_url=OLLAMA_BASE_URL,
    )


def check_ollama() -> dict:
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_BASE_URL)
        models = [m["model"] for m in client.list()["models"]]
        default_ready = OLLAMA_MODEL in models
        return {
            "available": True,
            "base_url": OLLAMA_BASE_URL,
            "default_model": OLLAMA_MODEL,
            "default_ready": default_ready,
            "models": models,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
```

- [ ] **Step 2: Commit**

```bash
git add web_api/services/llm_provider.py
git commit -m "feat: add ollama llm provider for crewai"
```

---

### Task 6: Servicio CrewAI

**Files:**
- Create: `web_api/services/crew_service.py`

- [ ] **Step 1: Crear crew para generar plan editorial**

```python
from typing import List
from crewai import Agent, Task, Crew
from web_api.services.llm_provider import get_llm
from web_api.schemas import PlanEntryCreate


PLAN_PROMPT = """Eres un estratega de contenidos. Para el canal "{name}" ({format}) sobre el nicho "{niche}",
propón {count} ideas de episodios. Devuélvelas EXACTAMENTE en este formato JSON:
[
  {{"title": "Título 1", "description": "Descripción corta 1"}},
  ...
]
Solo JSON, sin explicaciones."""


def generate_plan(channel, count: int = 5) -> List[PlanEntryCreate]:
    strategist = Agent(
        role="Content Strategist",
        goal="Proponer ideas de episodios relevantes para un canal",
        backstory="Experto en contenido digital y nichos de audiencia.",
        llm=get_llm(),
        verbose=False,
    )

    task = Task(
        description=PLAN_PROMPT.format(
            name=channel.name,
            format=channel.format,
            niche=channel.niche or "general",
            count=count,
        ),
        expected_output="Un array JSON con objetos title y description",
        agent=strategist,
    )

    crew = Crew(agents=[strategist], tasks=[task], verbose=False)
    result = crew.kickoff()
    import json
    data = json.loads(str(result))
    return [PlanEntryCreate(title=item["title"], description=item.get("description")) for item in data]
```

- [ ] **Step 2: Crear crew para generar guion**

```python
SCRIPT_PROMPT = """Eres un guionista de audio. Escribe un guion completo en español para un episodio de tipo "{format}"
titulado "{title}". Descripción: {description}. Nicho: {niche}.
El guion debe tener entre 300 y 800 palabras, ser natural al leerse en voz alta y no incluir notas de producción.
Devuelve SOLO el texto del guion, sin introducciones ni comentarios."""


def generate_script(channel, entry) -> str:
    writer = Agent(
        role="Script Writer",
        goal="Escribir guiones atractivos para audio",
        backstory="Experto en escritura para podcast y narración hablada.",
        llm=get_llm(),
        verbose=False,
    )
    editor = Agent(
        role="Script Editor",
        goal="Revisar guiones para mejorar ritmo y claridad",
        backstory="Editor con oído para contenido hablado.",
        llm=get_llm(),
        verbose=False,
    )

    write_task = Task(
        description=SCRIPT_PROMPT.format(
            format=channel.format,
            title=entry.title,
            description=entry.description or "",
            niche=channel.niche or "general",
        ),
        expected_output="Un guion en español listo para leer en voz alta",
        agent=writer,
    )

    edit_task = Task(
        description="Revisa el guion anterior, mejora ritmo y claridad, y devuelve SOLO el texto final del guion.",
        expected_output="Guion final pulido",
        agent=editor,
        context=[write_task],
    )

    crew = Crew(agents=[writer, editor], tasks=[write_task, edit_task], verbose=False)
    result = crew.kickoff()
    return str(result).strip()
```

- [ ] **Step 3: Commit**

```bash
git add web_api/services/crew_service.py
git commit -m "feat: add CrewAI crews for plan and script generation"
```

---

### Task 7: Endpoints de canales y plan editorial

**Files:**
- Create: `web_api/routes/channels.py`
- Create: `web_api/routes/llm.py`
- Modify: `web_api/main.py`

- [ ] **Step 1: Crear `web_api/routes/channels.py`**

```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from web_api.database import get_db
from web_api.models import Channel, ContentPlanEntry, Episode
from web_api.schemas import (
    ChannelCreate, ChannelUpdate, ChannelResponse,
    PlanEntryCreate, PlanEntryResponse,
)
from web_api.services.crew_service import generate_plan, generate_script

router = APIRouter()


@router.get("", response_model=List[ChannelResponse])
def list_channels(db: Session = Depends(get_db)):
    return db.query(Channel).order_by(Channel.created_at.desc()).all()


@router.post("", response_model=ChannelResponse, status_code=201)
def create_channel(data: ChannelCreate, db: Session = Depends(get_db)):
    channel = Channel(**data.dict())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/{channel_id}", response_model=ChannelResponse)
def get_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/{channel_id}", response_model=ChannelResponse)
def update_channel(channel_id: int, data: ChannelUpdate, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(channel)
    db.commit()


@router.post("/{channel_id}/activate", response_model=ChannelResponse)
def activate_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = True
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/{channel_id}/deactivate", response_model=ChannelResponse)
def deactivate_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = False
    db.commit()
    db.refresh(channel)
    return channel


@router.get("/{channel_id}/plan", response_model=List[PlanEntryResponse])
def list_plan_entries(channel_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ContentPlanEntry)
        .filter(ContentPlanEntry.channel_id == channel_id)
        .order_by(ContentPlanEntry.created_at.desc())
        .all()
    )


@router.post("/{channel_id}/plan/generate", response_model=List[PlanEntryResponse])
def generate_plan_entries(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    try:
        proposed = generate_plan(channel, count=5)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CrewAI error: {e}")

    entries = []
    for item in proposed:
        entry = ContentPlanEntry(channel_id=channel.id, title=item.title, description=item.description)
        db.add(entry)
        entries.append(entry)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


@router.post("/{channel_id}/plan", response_model=PlanEntryResponse, status_code=201)
def create_plan_entry(channel_id: int, data: PlanEntryCreate, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    entry = ContentPlanEntry(channel_id=channel.id, **data.dict())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/plan/{entry_id}/approve", response_model=PlanEntryResponse)
def approve_plan_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.status != "draft":
        raise HTTPException(status_code=400, detail="Entry already processed")

    channel = db.query(Channel).filter(Channel.id == entry.channel_id).first()
    try:
        script = generate_script(channel, entry)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CrewAI error: {e}")

    episode = Episode(
        title=entry.title,
        type=channel.format,
        source_text=script,
        voice_id=channel.default_voice_id,
        status="pending",
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)

    entry.status = "generated"
    entry.episode_id = episode.id
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/plan/{entry_id}/reject", response_model=PlanEntryResponse)
def reject_plan_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry.status = "rejected"
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/plan/{entry_id}", status_code=204)
def delete_plan_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
```

- [ ] **Step 2: Crear `web_api/routes/llm.py`**

```python
from fastapi import APIRouter
from web_api.services.llm_provider import check_ollama

router = APIRouter()


@router.get("/status")
def llm_status():
    return check_ollama()
```

- [ ] **Step 3: Registrar routers en `web_api/main.py`**

```python
from web_api.routes import voices, tts, episodes, channels, llm

app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
```

- [ ] **Step 4: Commit**

```bash
git add web_api/routes/channels.py web_api/routes/llm.py web_api/main.py
git commit -m "feat: add channels and plan endpoints with CrewAI integration"
```

---

### Task 8: Tipos de frontend

**Files:**
- Modify: `web/src/types/index.ts`

- [ ] **Step 1: Añadir tipos de canal y entrada de plan**

```typescript
export type ChannelFormat = 'podcast' | 'news' | 'meditation' | 'motivation'
export type PlanEntryStatus = 'draft' | 'approved' | 'rejected' | 'generated'

export interface Channel {
  id: number
  name: string
  description?: string
  niche?: string
  format: ChannelFormat
  default_voice_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ContentPlanEntry {
  id: number
  channel_id: number
  title: string
  description?: string
  scheduled_date?: string
  status: PlanEntryStatus
  episode_id?: number
  created_at: string
  updated_at: string
}

export interface CreateChannelRequest {
  name: string
  description?: string
  niche?: string
  format: ChannelFormat
  default_voice_id: string
  is_active?: boolean
}

export interface CreatePlanEntryRequest {
  title: string
  description?: string
  scheduled_date?: string
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/types/index.ts
git commit -m "feat: add channel and plan types"
```

---

### Task 9: Cliente API frontend

**Files:**
- Modify: `web/src/api/client.ts`

- [ ] **Step 1: Añadir métodos de canales y plan**

```typescript
import { Channel, CreateChannelRequest, ContentPlanEntry, CreatePlanEntryRequest } from '../types'

export const api = {
  // ... existing methods ...

  getChannels: () => fetchJson<Channel[]>('/channels'),
  createChannel: (data: CreateChannelRequest) =>
    fetchJson<Channel>('/channels', { method: 'POST', body: JSON.stringify(data) }),
  getChannel: (id: number) => fetchJson<Channel>(`/channels/${id}`),
  updateChannel: (id: number, data: Partial<CreateChannelRequest>) =>
    fetchJson<Channel>(`/channels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteChannel: (id: number) => fetchVoid(`/channels/${id}`, { method: 'DELETE' }),
  activateChannel: (id: number) => fetchJson<Channel>(`/channels/${id}/activate`, { method: 'POST' }),
  deactivateChannel: (id: number) => fetchJson<Channel>(`/channels/${id}/deactivate`, { method: 'POST' }),

  getPlanEntries: (channelId: number) =>
    fetchJson<ContentPlanEntry[]>(`/channels/${channelId}/plan`),
  generatePlan: (channelId: number) =>
    fetchJson<ContentPlanEntry[]>(`/channels/${channelId}/plan/generate`, { method: 'POST' }),
  createPlanEntry: (channelId: number, data: CreatePlanEntryRequest) =>
    fetchJson<ContentPlanEntry>(`/channels/${channelId}/plan`, { method: 'POST', body: JSON.stringify(data) }),
  approvePlanEntry: (entryId: number) =>
    fetchJson<ContentPlanEntry>(`/channels/plan/${entryId}/approve`, { method: 'POST' }),
  rejectPlanEntry: (entryId: number) =>
    fetchJson<ContentPlanEntry>(`/channels/plan/${entryId}/reject`, { method: 'POST' }),
  deletePlanEntry: (entryId: number) => fetchVoid(`/channels/plan/${entryId}`, { method: 'DELETE' }),

  getLlmStatus: () => fetchJson<{ available: boolean; default_ready: boolean; error?: string }>('/llm/status'),
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/api/client.ts
git commit -m "feat: add channel and plan api client"
```

---

### Task 10: Store Zustand de canales

**Files:**
- Create: `web/src/stores/channelStore.ts`

- [ ] **Step 1: Crear store**

```typescript
import { create } from 'zustand'
import { Channel, ContentPlanEntry, CreateChannelRequest, CreatePlanEntryRequest } from '../types'
import { api } from '../api/client'
import { formatError } from '../utils/error'

interface ChannelState {
  channels: Channel[]
  entries: Record<number, ContentPlanEntry[]>
  loading: boolean
  error: string | null
  fetchChannels: () => Promise<void>
  createChannel: (data: CreateChannelRequest) => Promise<Channel>
  deleteChannel: (id: number) => Promise<void>
  fetchPlanEntries: (channelId: number) => Promise<void>
  generatePlan: (channelId: number) => Promise<void>
  createPlanEntry: (channelId: number, data: CreatePlanEntryRequest) => Promise<void>
  approveEntry: (entryId: number) => Promise<void>
  rejectEntry: (entryId: number) => Promise<void>
  deleteEntry: (entryId: number) => Promise<void>
}

export const useChannelStore = create<ChannelState>((set, get) => ({
  channels: [],
  entries: {},
  loading: false,
  error: null,

  fetchChannels: async () => {
    set({ loading: true, error: null })
    try {
      const channels = await api.getChannels()
      set({ channels, loading: false })
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },

  createChannel: async (data) => {
    set({ error: null })
    const channel = await api.createChannel(data)
    set((state) => ({ channels: [channel, ...state.channels] }))
    return channel
  },

  deleteChannel: async (id) => {
    set({ error: null })
    await api.deleteChannel(id)
    set((state) => ({
      channels: state.channels.filter((c) => c.id !== id),
    }))
  },

  fetchPlanEntries: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const entries = await api.getPlanEntries(channelId)
      set((state) => ({
        entries: { ...state.entries, [channelId]: entries },
        loading: false,
      }))
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },

  generatePlan: async (channelId) => {
    set({ error: null })
    const entries = await api.generatePlan(channelId)
    set((state) => ({
      entries: { ...state.entries, [channelId]: entries },
    }))
  },

  createPlanEntry: async (channelId, data) => {
    set({ error: null })
    const entry = await api.createPlanEntry(channelId, data)
    set((state) => ({
      entries: {
        ...state.entries,
        [channelId]: [entry, ...(state.entries[channelId] || [])],
      },
    }))
  },

  approveEntry: async (entryId) => {
    set({ error: null })
    const entry = await api.approvePlanEntry(entryId)
    const channelId = entry.channel_id
    set((state) => ({
      entries: {
        ...state.entries,
        [channelId]: (state.entries[channelId] || []).map((e) =>
          e.id === entryId ? entry : e
        ),
      },
    }))
  },

  rejectEntry: async (entryId) => {
    set({ error: null })
    const entry = await api.rejectPlanEntry(entryId)
    const channelId = entry.channel_id
    set((state) => ({
      entries: {
        ...state.entries,
        [channelId]: (state.entries[channelId] || []).map((e) =>
          e.id === entryId ? entry : e
        ),
      },
    }))
  },

  deleteEntry: async (entryId) => {
    set({ error: null })
    const channelId = get().entries[Object.keys(get().entries).find((key) =>
      get().entries[Number(key)].some((e) => e.id === entryId)
    ) as any]?.find((e) => e.id === entryId)?.channel_id
    if (channelId === undefined) return
    await api.deletePlanEntry(entryId)
    set((state) => ({
      entries: {
        ...state.entries,
        [channelId]: (state.entries[channelId] || []).filter((e) => e.id !== entryId),
      },
    }))
  },
}))
```

- [ ] **Step 2: Commit**

```bash
git add web/src/stores/channelStore.ts
git commit -m "feat: add channel store"
```

---

### Task 11: Componentes de canales

**Files:**
- Create: `web/src/components/ChannelCard.tsx`
- Create: `web/src/components/ChannelForm.tsx`
- Create: `web/src/components/ContentPlanList.tsx`
- Create: `web/src/components/PlanEntryCard.tsx`
- Create: `web/src/components/StudioPanel.tsx`

- [ ] **Step 1: ChannelCard**

```tsx
import { Link } from '@tanstack/react-router'
import { Channel } from '../types'

interface Props {
  channel: Channel
  onDelete: (id: number) => void
}

export default function ChannelCard({ channel, onDelete }: Props) {
  return (
    <div className="bg-white p-4 rounded shadow">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold">{channel.name}</h3>
          <p className="text-sm text-gray-600">{channel.niche || 'Sin nicho'} • {channel.format}</p>
          <p className="text-sm text-gray-500 mt-1">{channel.description}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded ${channel.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
          {channel.is_active ? 'Activo' : 'Inactivo'}
        </span>
      </div>
      <div className="mt-4 space-x-2">
        <Link to="/channels/$id/plan" params={{ id: String(channel.id) }} className="text-blue-600 hover:underline text-sm">
          Ver plan
        </Link>
        <button type="button" onClick={() => onDelete(channel.id)} className="text-red-600 hover:underline text-sm">
          Eliminar
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: ChannelForm**

```tsx
import { useState } from 'react'
import { CreateChannelRequest, ChannelFormat } from '../types'

interface Props {
  onSubmit: (data: CreateChannelRequest) => void
  onCancel: () => void
}

const FORMATS: { value: ChannelFormat; label: string }[] = [
  { value: 'podcast', label: 'Podcast' },
  { value: 'news', label: 'Noticias' },
  { value: 'meditation', label: 'Meditación' },
  { value: 'motivation', label: 'Motivación' },
]

export default function ChannelForm({ onSubmit, onCancel }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [niche, setNiche] = useState('')
  const [format, setFormat] = useState<ChannelFormat>('podcast')
  const [voiceId, setVoiceId] = useState('jorge')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ name, description, niche, format, default_voice_id: voiceId, is_active: true })
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow space-y-4">
      <div>
        <label className="block text-sm font-medium">Nombre</label>
        <input className="w-full border rounded p-2" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div>
        <label className="block text-sm font-medium">Descripción</label>
        <textarea className="w-full border rounded p-2" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div>
        <label className="block text-sm font-medium">Nicho</label>
        <input className="w-full border rounded p-2" value={niche} onChange={(e) => setNiche(e.target.value)} />
      </div>
      <div>
        <label className="block text-sm font-medium">Formato</label>
        <select className="w-full border rounded p-2" value={format} onChange={(e) => setFormat(e.target.value as ChannelFormat)}>
          {FORMATS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Voz por defecto</label>
        <input className="w-full border rounded p-2" value={voiceId} onChange={(e) => setVoiceId(e.target.value)} required />
      </div>
      <div className="space-x-2">
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">Guardar</button>
        <button type="button" onClick={onCancel} className="bg-gray-300 px-4 py-2 rounded">Cancelar</button>
      </div>
    </form>
  )
}
```

- [ ] **Step 3: PlanEntryCard**

```tsx
import { ContentPlanEntry } from '../types'

interface Props {
  entry: ContentPlanEntry
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

const statusLabels: Record<string, string> = {
  draft: 'Borrador',
  generated: 'Generado',
  rejected: 'Rechazado',
}

export default function PlanEntryCard({ entry, onApprove, onReject, onDelete }: Props) {
  return (
    <div className="bg-white p-4 rounded shadow border-l-4 border-blue-500">
      <div className="flex justify-between items-start">
        <div>
          <h4 className="font-bold">{entry.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{entry.description}</p>
          <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded mt-2 inline-block">
            {statusLabels[entry.status] || entry.status}
          </span>
        </div>
        <div className="space-x-2">
          {entry.status === 'draft' && (
            <>
              <button type="button" onClick={() => onApprove(entry.id)} className="text-green-600 hover:underline text-sm">Aprobar</button>
              <button type="button" onClick={() => onReject(entry.id)} className="text-yellow-600 hover:underline text-sm">Rechazar</button>
            </>
          )}
          <button type="button" onClick={() => onDelete(entry.id)} className="text-red-600 hover:underline text-sm">Eliminar</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: ContentPlanList**

```tsx
import { ContentPlanEntry } from '../types'
import PlanEntryCard from './PlanEntryCard'

interface Props {
  entries: ContentPlanEntry[]
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

export default function ContentPlanList({ entries, onApprove, onReject, onDelete }: Props) {
  if (entries.length === 0) return <p className="text-gray-500">No hay entradas en el plan.</p>
  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <PlanEntryCard key={entry.id} entry={entry} onApprove={onApprove} onReject={onReject} onDelete={onDelete} />
      ))}
    </div>
  )
}
```

- [ ] **Step 5: StudioPanel**

```tsx
import { useState } from 'react'
import { Channel } from '../types'

interface Props {
  channels: Channel[]
  onGenerate: (channelId: number) => void
  loading: boolean
}

export default function StudioPanel({ channels, onGenerate, loading }: Props) {
  const [selectedId, setSelectedId] = useState<number | ''>(channels[0]?.id ?? '')

  return (
    <div className="bg-white p-6 rounded shadow">
      <h3 className="text-lg font-bold mb-4">CrewAI Studio</h3>
      <p className="text-sm text-gray-600 mb-4">Selecciona un canal y genera un plan editorial con IA.</p>
      <div className="flex gap-2">
        <select className="border rounded p-2" value={selectedId} onChange={(e) => setSelectedId(Number(e.target.value))}>
          {channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <button
          type="button"
          disabled={loading || selectedId === ''}
          onClick={() => onGenerate(Number(selectedId))}
          className="bg-purple-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Generando...' : 'Generar plan'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ChannelCard.tsx web/src/components/ChannelForm.tsx web/src/components/ContentPlanList.tsx web/src/components/PlanEntryCard.tsx web/src/components/StudioPanel.tsx
git commit -m "feat: add channel and plan components"
```

---

### Task 12: Rutas frontend

**Files:**
- Create: `web/src/routes/channels.tsx`
- Create: `web/src/routes/channels.new.tsx`
- Create: `web/src/routes/channels.$id.plan.tsx`
- Create: `web/src/routes/studio.tsx`
- Modify: `web/src/components/Layout.tsx`

- [ ] **Step 1: `web/src/routes/channels.tsx`**

```tsx
import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import ChannelCard from '../components/ChannelCard'

export const Route = createFileRoute('/channels')({
  component: ChannelsPage,
})

function ChannelsPage() {
  const { channels, loading, error, fetchChannels, deleteChannel } = useChannelStore()

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  if (loading) return <div>Cargando canales...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Canales</h2>
        <Link to="/channels/new" className="bg-blue-600 text-white px-4 py-2 rounded">Nuevo canal</Link>
      </div>
      {error && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>}
      <div className="grid gap-4 md:grid-cols-2">
        {channels.map((channel) => (
          <ChannelCard key={channel.id} channel={channel} onDelete={deleteChannel} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: `web/src/routes/channels.new.tsx`**

```tsx
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useChannelStore } from '../stores/channelStore'
import ChannelForm from '../components/ChannelForm'

export const Route = createFileRoute('/channels/new')({
  component: NewChannelPage,
})

function NewChannelPage() {
  const navigate = useNavigate()
  const { createChannel } = useChannelStore()

  const handleSubmit = async (data) => {
    await createChannel(data)
    navigate({ to: '/channels' })
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Nuevo canal</h2>
      <ChannelForm onSubmit={handleSubmit} onCancel={() => navigate({ to: '/channels' })} />
    </div>
  )
}
```

- [ ] **Step 3: `web/src/routes/channels.$id.plan.tsx`**

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useChannelStore } from '../stores/channelStore'
import ContentPlanList from '../components/ContentPlanList'

export const Route = createFileRoute('/channels/$id/plan')({
  component: ChannelPlanPage,
})

function ChannelPlanPage() {
  const { id } = Route.useParams()
  const channelId = Number(id)
  const {
    channels,
    entries,
    loading,
    error,
    fetchChannels,
    fetchPlanEntries,
    generatePlan,
    approveEntry,
    rejectEntry,
    deleteEntry,
  } = useChannelStore()

  useEffect(() => {
    fetchChannels()
    fetchPlanEntries(channelId)
  }, [fetchChannels, fetchPlanEntries, channelId])

  const channel = channels.find((c) => c.id === channelId)
  const planEntries = entries[channelId] || []

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Plan editorial: {channel?.name}</h2>
        <button
          type="button"
          onClick={() => generatePlan(channelId)}
          className="bg-purple-600 text-white px-4 py-2 rounded"
          disabled={loading}
        >
          Generar con IA
        </button>
      </div>
      {error && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>}
      <ContentPlanList
        entries={planEntries}
        onApprove={approveEntry}
        onReject={rejectEntry}
        onDelete={deleteEntry}
      />
    </div>
  )
}
```

- [ ] **Step 4: `web/src/routes/studio.tsx`**

```tsx
import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useChannelStore } from '../stores/channelStore'
import StudioPanel from '../components/StudioPanel'

export const Route = createFileRoute('/studio')({
  component: StudioPage,
})

function StudioPage() {
  const { channels, loading, error, fetchChannels, generatePlan } = useChannelStore()

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Studio</h2>
      {error && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>}
      <StudioPanel channels={channels} onGenerate={generatePlan} loading={loading} />
    </div>
  )
}
```

- [ ] **Step 5: Actualizar Layout**

```tsx
<Link to="/channels" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Canales</Link>
<Link to="/studio" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Studio</Link>
```

- [ ] **Step 6: Regenerar route tree**

```bash
cd web
npx @tanstack/router-cli generate
```

- [ ] **Step 7: Commit**

```bash
git add web/src/routes/channels.tsx web/src/routes/channels.new.tsx web/src/routes/channels.\$id.plan.tsx web/src/routes/studio.tsx web/src/components/Layout.tsx web/src/routeTree.gen.ts
git commit -m "feat: add channels, plan and studio routes"
```

---

### Task 13: Verificar build y tests frontend

**Files:**
- All frontend files above

- [ ] **Step 1: Ejecutar tests**

```bash
cd web
npm test -- --run
```

Expected: all pass.

- [ ] **Step 2: Ejecutar build**

```bash
cd web
npm run build
```

Expected: no errors.

- [ ] **Step 3: Commit si se generan cambios**

```bash
git add .
git commit -m "chore: regenerate route tree and fix build"
```

---

### Task 14: Tests backend

**Files:**
- Create: `tests/web_api/test_channels.py`
- Create: `tests/web_api/test_crew_service.py`

- [ ] **Step 1: Test de CRUD de canales**

```python
from fastapi.testclient import TestClient
from web_api.main import app
from web_api.database import SessionLocal
from web_api.models import Channel, ContentPlanEntry

client = TestClient(app)


def test_create_and_list_channels():
    response = client.post("/api/channels", json={
        "name": "Canal Test",
        "description": "Desc",
        "niche": "tech",
        "format": "podcast",
        "default_voice_id": "jorge",
        "is_active": True,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Canal Test"

    response = client.get("/api/channels")
    assert response.status_code == 200
    assert any(c["name"] == "Canal Test" for c in response.json())


def test_generate_plan_creates_entries():
    # Create channel
    response = client.post("/api/channels", json={
        "name": "Canal IA",
        "format": "podcast",
        "niche": "historia",
        "default_voice_id": "jorge",
    })
    channel_id = response.json()["id"]

    with patch("web_api.routes.channels.generate_plan") as mock_generate:
        mock_generate.return_value = [
            PlanEntryCreate(title="T1", description="D1"),
            PlanEntryCreate(title="T2", description="D2"),
        ]
        response = client.post(f"/api/channels/{channel_id}/plan/generate")
        assert response.status_code == 200
        assert len(response.json()) == 2
```

- [ ] **Step 2: Test de aprobación crea episodio**

```python
from unittest.mock import patch
from web_api.schemas import PlanEntryCreate


def test_approve_entry_creates_episode():
    # Create channel
    response = client.post("/api/channels", json={
        "name": "Canal Aprobar",
        "format": "podcast",
        "default_voice_id": "jorge",
    })
    channel_id = response.json()["id"]

    # Create entry
    response = client.post(f"/api/channels/{channel_id}/plan", json={
        "title": "Episodio a generar",
        "description": "Descripción",
    })
    entry_id = response.json()["id"]

    with patch("web_api.routes.channels.generate_script") as mock_script:
        mock_script.return_value = "Guion generado"
        response = client.post(f"/api/channels/plan/{entry_id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "generated"
        assert data["episode_id"] is not None

    # Verify episode exists
    response = client.get(f"/api/episodes/{data['episode_id']}")
    assert response.status_code == 200
    assert response.json()["source_text"] == "Guion generado"
```

- [ ] **Step 3: Commit**

```bash
git add tests/web_api/test_channels.py tests/web_api/test_crew_service.py
git commit -m "test: add backend tests for channels and crewai integration"
```

---

### Task 15: Tests frontend

**Files:**
- Create: `web/src/components/__tests__/ChannelForm.test.tsx`
- Create: `web/src/components/__tests__/PlanEntryCard.test.tsx`
- Create: `web/src/stores/__tests__/channelStore.test.ts`

- [ ] **Step 1: ChannelForm test**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChannelForm from '../ChannelForm'

describe('ChannelForm', () => {
  it('submits channel data', () => {
    const onSubmit = vi.fn()
    render(<ChannelForm onSubmit={onSubmit} onCancel={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/Nombre/i), { target: { value: 'Canal X' } })
    fireEvent.change(screen.getByLabelText(/Nicho/i), { target: { value: 'tech' } })
    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ name: 'Canal X', niche: 'tech' }))
  })
})
```

- [ ] **Step 2: PlanEntryCard test**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PlanEntryCard from '../PlanEntryCard'
import type { ContentPlanEntry } from '../../types'

const entry: ContentPlanEntry = {
  id: 1,
  channel_id: 1,
  title: 'E1',
  description: 'Desc',
  status: 'draft',
  created_at: '',
  updated_at: '',
}

describe('PlanEntryCard', () => {
  it('calls approve on click', () => {
    const onApprove = vi.fn()
    render(<PlanEntryCard entry={entry} onApprove={onApprove} onReject={vi.fn()} onDelete={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Aprobar/i }))
    expect(onApprove).toHaveBeenCalledWith(1)
  })
})
```

- [ ] **Step 3: channelStore test**

```ts
import { describe, it, expect } from 'vitest'
import { useChannelStore } from '../channelStore'

describe('channelStore', () => {
  it('has empty channels by default', () => {
    const state = useChannelStore.getState()
    expect(state.channels).toEqual([])
    expect(state.loading).toBe(false)
  })
})
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/__tests__/ChannelForm.test.tsx web/src/components/__tests__/PlanEntryCard.test.tsx web/src/stores/__tests__/channelStore.test.ts
git commit -m "test: add frontend tests for channels"
```

---

### Task 16: Integración final

**Files:**
- Modify: `starter.py`
- Modify: `docs/WEB.md`

- [ ] **Step 1: Verificar Ollama en `starter.py`**

Antes de lanzar servicios, añadir:

```python
from web_api.services.llm_provider import check_ollama


def main():
    _register_signals()
    status = check_ollama()
    if not status["available"]:
        print("[STARTER] WARNING: Ollama not available. CrewAI features will fail.")
    elif not status["default_ready"]:
        print(f"[STARTER] WARNING: Model {OLLAMA_MODEL} not found in Ollama.")
    # ... resto
```

- [ ] **Step 2: Actualizar `docs/WEB.md`**

Añadir sección:

```markdown
## Canales y CrewAI

1. Crea un canal en `/channels`.
2. Ve a `/studio`, selecciona el canal y pulsa "Generar plan".
3. Revisa las entradas en `/channels/<id>/plan`.
4. Pulsa "Aprobar" para generar el guion con CrewAI y crear el episodio.
5. Sigue la generación de audio en `/queue`.

### Requisitos de Ollama

Asegúrate de que Ollama esté corriendo y tenga el modelo configurado:

```bash
ollama run llama3.1:8b
```
```

- [ ] **Step 3: Commit**

```bash
git add starter.py docs/WEB.md
git commit -m "docs: document channels and crewai flow; check ollama on startup"
```

---

### Task 17: Push final

- [ ] **Step 1: Push a la rama**

```bash
git push origin feature/media-automation-platform
```

---

## Self-Review

- [x] Spec coverage: canales CRUD, plan manual, generación con CrewAI, aprobación → episodio, frontend rutas/componentes, tests, Ollama config.
- [x] No placeholders: cada tarea incluye código y comandos.
- [x] Type consistency: `Channel`, `ContentPlanEntry`, `PlanEntryCreate`, `ChannelCreate` usados en backend y frontend.
- [x] Reutilización: no se modifica el worker; se crea episodio `pending` y fluye por el sistema existente.
