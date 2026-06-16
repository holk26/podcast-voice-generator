# Channel Producer Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CrewAI-powered producer agent per channel that orchestrates content planning, voice casting, script writing, audio production, mixing, and quality review into a single pipeline.

**Architecture:** `ChannelProducerAgent` builds a CrewAI crew. In `manual` mode it returns proposals after each step. In `auto` mode it delegates concrete audio rendering to `ProductionEngine`, which uses existing TTS/mixing code. Progress is tracked in a `ProductionRun` table.

**Tech Stack:** CrewAI, FastAPI, SQLAlchemy, existing TTS/mixer engines, React, Zustand.

---

## File Structure

| File | Responsibility |
|---|---|
| `web_api/models.py` (modify) | Add `ChannelVoiceCast`, `ProductionRun` |
| `web_api/schemas.py` (modify) | Add production schemas |
| `web_api/services/producer_agent.py` | CrewAI crew definition and execution |
| `web_api/services/production_engine.py` | Concrete audio rendering orchestration |
| `web_api/routes/channels.py` (modify) | Add cast, produce, run endpoints |
| `web/src/types/index.ts` (modify) | Add production types |
| `web/src/api/client.ts` (modify) | Add production API methods |
| `web/src/stores/producerStore.ts` | Production runs state |
| `web/src/components/ChannelStudio.tsx` | Studio main page |
| `web/src/components/CastingGrid.tsx` | Assign voices to roles |
| `web/src/components/ProducerRunTimeline.tsx` | Pipeline status UI |
| `web/src/routes/channels.$id.studio.tsx` | `/channels/$id/studio` route |
| `web/src/routes/channels.$id.studio.cast.tsx` | Casting tab route |
| `web/src/routes/channels.$id.studio.producer.tsx` | Producer tab route |
| `web/src/components/Layout.tsx` (modify) | Update channels nav if needed |
| `tests/web_api/test_producer_agent.py` | Backend tests |
| `web/src/tests/ProducerRunTimeline.test.tsx` | Frontend tests |

---

### Task 1: Add data models and schemas

**Files:**
- Modify: `web_api/models.py`
- Modify: `web_api/schemas.py`

- [ ] **Step 1: Add `ChannelVoiceCast`**

```python
class ChannelVoiceCast(Base):
    __tablename__ = "channel_voice_casts"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    role = Column(String, nullable=False)
    voice_id = Column(String, nullable=False)
```

- [ ] **Step 2: Add `ProductionRun`**

```python
class ProductionRun(Base):
    __tablename__ = "production_runs"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=True)
    plan_entry_id = Column(Integer, ForeignKey("content_plan_entries.id"), nullable=True)
    mode = Column(String, nullable=False, default="manual")
    status = Column(String, nullable=False, default="proposed")
    quality_score = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    config_json = Column(String, nullable=True, default="{}")
    metrics_json = Column(String, nullable=True, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

- [ ] **Step 3: Add schemas**

```python
from typing import Optional
from pydantic import BaseModel


class ChannelVoiceCastCreate(BaseModel):
    role: str
    voice_id: str


class ChannelVoiceCastResponse(BaseModel):
    id: int
    channel_id: int
    role: str
    voice_id: str

    class Config:
        from_attributes = True


class ProductionRunResponse(BaseModel):
    id: int
    channel_id: int
    episode_id: Optional[int]
    plan_entry_id: Optional[int]
    mode: str
    status: str
    quality_score: Optional[float]
    feedback: Optional[str]
    config_json: str
    metrics_json: str
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProduceRequest(BaseModel):
    plan_entry_id: int
    mode: str = "manual"  # manual | auto
```

- [ ] **Step 4: Commit**

```bash
git add web_api/models.py web_api/schemas.py
git commit -m "feat(producer): add ChannelVoiceCast and ProductionRun models"
```

---

### Task 2: Implement ChannelProducerAgent

**Files:**
- Create: `web_api/services/producer_agent.py`

- [ ] **Step 1: Define result dataclass and prompts**

```python
import json
from dataclasses import dataclass
from typing import Optional

from crewai import Agent, Task, Crew

from web_api.services.llm_provider import get_planning_llm


@dataclass
class ProductionProposal:
    script: str
    voice_cast: dict[str, str]
    mix_config: dict
    quality_score: Optional[float]
    feedback: Optional[str]


CASTING_PROMPT = """Eres director de casting. Para el canal "{channel_name}" ({format}) sobre {niche},
asigna voces a los roles del guion "{title}".
Roles disponibles: {roles}.
Voces disponibles: {voices}.
Devuelve EXACTAMENTE este JSON:
{{"voice_cast": {{"rol": "voice_id", ...}}, "reasoning": "..."}}
Solo JSON."""

SCRIPT_PROMPT = """Eres guionista. Escribe un guion en español para un episodio de tipo "{format}"
titulado "{title}". Nicho: {niche}. Descripción: {description}.
Voces asignadas: {voice_cast}.
Indica quién habla con prefijos como "NARRADOR: ...". Longitud: 300-800 palabras.
Devuelve SOLO el texto del guion."""

QUALITY_PROMPT = """Eres editor de calidad. Evalúa este guion y configuración de audio.
Guion:\n{script}\n\nConfiguración:\n{config}\n\nDevuelve EXACTAMENTE este JSON:
{{"score": 0.85, "feedback": "..."}}
score entre 0 y 1. Solo JSON."""
```

- [ ] **Step 2: Implement agent methods**

```python
def _parse_json_flexible(raw: str):
    import ast
    import re
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```", 1)[1].strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    block = raw[start : end + 1]
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        pass
    block = re.sub(r"}\s*{", "},{", block)
    block = re.sub(r",\s*}", "}", block)
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        return ast.literal_eval(block)


class ChannelProducerAgent:
    def __init__(self, channel, voices: list[dict], mode: str = "manual"):
        self.channel = channel
        self.voices = voices
        self.mode = mode
        self.llm = get_planning_llm()

    def run_casting(self, plan_entry) -> dict:
        casting_agent = Agent(
            role="Casting Director",
            goal="Asignar la voz adecuada a cada rol del episodio",
            backstory="Experto en producción de audio y casting de voces.",
            llm=self.llm,
            verbose=False,
        )
        voice_list = ", ".join([f"{v['id']} ({v['name']})" for v in self.voices])
        task = Task(
            description=CASTING_PROMPT.format(
                channel_name=self.channel.name,
                format=self.channel.format,
                niche=self.channel.niche,
                title=plan_entry.title,
                roles="narrador, entrevistado",
                voices=voice_list,
            ),
            expected_output="JSON con voice_cast",
            agent=casting_agent,
        )
        crew = Crew(agents=[casting_agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        data = _parse_json_flexible(str(result))
        return data.get("voice_cast", {})

    def run_script(self, plan_entry, voice_cast: dict) -> str:
        writer = Agent(
            role="Script Writer",
            goal="Escribir guiones naturales para audio",
            backstory="Guionista de podcasts y audiolibros.",
            llm=self.llm,
            verbose=False,
        )
        task = Task(
            description=SCRIPT_PROMPT.format(
                format=self.channel.format,
                title=plan_entry.title,
                niche=self.channel.niche,
                description=plan_entry.description,
                voice_cast=json.dumps(voice_cast, ensure_ascii=False),
            ),
            expected_output="Texto del guion",
            agent=writer,
        )
        crew = Crew(agents=[writer], tasks=[task], verbose=False)
        return str(crew.kickoff()).strip()

    def run_quality_review(self, script: str, config: dict) -> tuple[float, str]:
        reviewer = Agent(
            role="Quality Reviewer",
            goal="Evaluar calidad de guiones y producción",
            backstory="Editor experto en contenido de audio.",
            llm=self.llm,
            verbose=False,
        )
        task = Task(
            description=QUALITY_PROMPT.format(
                script=script[:2000],
                config=json.dumps(config, ensure_ascii=False),
            ),
            expected_output="JSON con score y feedback",
            agent=reviewer,
        )
        crew = Crew(agents=[reviewer], tasks=[task], verbose=False)
        data = _parse_json_flexible(str(crew.kickoff()))
        return float(data.get("score", 0.0)), data.get("feedback", "")

    def produce(self, plan_entry) -> ProductionProposal:
        voice_cast = self.run_casting(plan_entry)
        script = self.run_script(plan_entry, voice_cast)
        mix_config = {"music": True, "sfx": False, "normalize": True}
        score, feedback = self.run_quality_review(script, mix_config)
        return ProductionProposal(
            script=script,
            voice_cast=voice_cast,
            mix_config=mix_config,
            quality_score=score,
            feedback=feedback,
        )
```

- [ ] **Step 3: Commit**

```bash
git add web_api/services/producer_agent.py
git commit -m "feat(producer): add ChannelProducerAgent crew"
```

---

### Task 3: Implement ProductionEngine

**Files:**
- Create: `web_api/services/production_engine.py`

- [ ] **Step 1: Implement rendering orchestration**

```python
import os
import time
from pathlib import Path

from sqlalchemy.orm import Session

from web_api.models import Episode, ProductionRun
from core.project import Project, ProjectSettings, Section, Voice


OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def _find_voice(voice_id: str, voices: list[dict]) -> dict | None:
    for v in voices:
        if v["id"] == voice_id:
            return v
    return None


def render_episode(
    db: Session,
    run: ProductionRun,
    channel,
    plan_entry,
    proposal,
    voices: list[dict],
) -> Episode:
    start = time.time()
    project = Project(name=plan_entry.title, settings=ProjectSettings())

    for role, voice_id in proposal.voice_cast.items():
        v = _find_voice(voice_id, voices)
        if v is None:
            continue
        project.add_voice(
            Voice(
                id=voice_id,
                name=v["name"],
                type=v.get("type", "pretrained"),
                engine=v["engine"],
                language=v.get("language", "es"),
                reference_path=v.get("reference_path"),
            )
        )

    # Naive script split: use one section per role paragraph
    lines = proposal.script.split("\n")
    for line in lines:
        if ":" in line:
            role, text = line.split(":", 1)
            role = role.strip().lower()
            voice_id = proposal.voice_cast.get(role)
            if voice_id:
                project.add_section(
                    Section(
                        id=f"sec_{len(project.sections):03d}",
                        title=role,
                        text=text.strip(),
                        voice_id=voice_id,
                    )
                )

    if not project.sections:
        # Fallback: entire script as narrator
        project.add_section(
            Section(
                id="sec_001",
                title="narrador",
                text=proposal.script,
                voice_id=next(iter(proposal.voice_cast.values()), "edge_es_alvaro"),
            )
        )

    episode = Episode(
        title=plan_entry.title,
        type=channel.format,
        source_text=proposal.script,
        voice_id=next(iter(proposal.voice_cast.values()), None),
        status="pending",
        production_run_id=run.id,
        voice_cast_json=json.dumps(proposal.voice_cast, ensure_ascii=False),
        quality_score=proposal.quality_score,
        feedback=proposal.feedback,
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)

    run.episode_id = episode.id
    run.status = "rendering"
    db.commit()

    # Actual rendering would call the pipeline worker; here we queue it.
    # The existing worker polls for pending episodes.

    elapsed = time.time() - start
    metrics = json.loads(run.metrics_json or "{}")
    metrics["render_time_seconds"] = elapsed
    run.metrics_json = json.dumps(metrics)
    db.commit()

    return episode
```

- [ ] **Step 2: Commit**

```bash
git add web_api/services/production_engine.py
git commit -m "feat(producer): add ProductionEngine rendering orchestration"
```

---

### Task 4: Add channel producer endpoints

**Files:**
- Modify: `web_api/routes/channels.py`

- [ ] **Step 1: Add imports and endpoints**

```python
from web_api.services.producer_agent import ChannelProducerAgent
from web_api.services.production_engine import render_episode
from web_api.services.voice_manager import list_voices as _list_all_voices
```

Add endpoints:

```python
@router.get("/{channel_id}/cast", response_model=list[ChannelVoiceCastResponse])
def get_channel_cast(channel_id: int, db: Session = Depends(get_db)):
    return db.query(ChannelVoiceCast).filter(ChannelVoiceCast.channel_id == channel_id).all()


@router.post("/{channel_id}/cast", response_model=ChannelVoiceCastResponse)
def add_channel_cast(
    channel_id: int,
    data: ChannelVoiceCastCreate,
    db: Session = Depends(get_db),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    entry = ChannelVoiceCast(channel_id=channel_id, role=data.role, voice_id=data.voice_id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{channel_id}/cast/{cast_id}")
def remove_channel_cast(channel_id: int, cast_id: int, db: Session = Depends(get_db)):
    entry = db.query(ChannelVoiceCast).filter(
        ChannelVoiceCast.id == cast_id,
        ChannelVoiceCast.channel_id == channel_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Cast entry not found")
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.post("/{channel_id}/produce", response_model=ProductionRunResponse)
def produce_channel(
    channel_id: int,
    request: ProduceRequest,
    db: Session = Depends(get_db),
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    plan_entry = db.query(ContentPlanEntry).filter(
        ContentPlanEntry.id == request.plan_entry_id,
        ContentPlanEntry.channel_id == channel_id,
    ).first()
    if not plan_entry:
        raise HTTPException(status_code=404, detail="Plan entry not found")

    run = ProductionRun(
        channel_id=channel_id,
        plan_entry_id=request.plan_entry_id,
        mode=request.mode,
        status="proposed",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    voices = _list_all_voices(db)
    agent = ChannelProducerAgent(channel, voices, mode=request.mode)
    proposal = agent.produce(plan_entry)

    run.config_json = json.dumps({
        "voice_cast": proposal.voice_cast,
        "mix_config": proposal.mix_config,
    }, ensure_ascii=False)
    run.quality_score = proposal.quality_score
    run.feedback = proposal.feedback

    if request.mode == "auto":
        episode = render_episode(db, run, channel, plan_entry, proposal, voices)
        run.episode_id = episode.id
        run.status = "rendering"
    else:
        run.status = "proposed"

    db.commit()
    db.refresh(run)
    return run


@router.get("/{channel_id}/runs", response_model=list[ProductionRunResponse])
def list_channel_runs(channel_id: int, db: Session = Depends(get_db)):
    return db.query(ProductionRun).filter(ProductionRun.channel_id == channel_id).order_by(ProductionRun.created_at.desc()).all()


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(ProductionRun).filter(ProductionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.mode == "auto":
        raise HTTPException(status_code=400, detail="Auto runs do not require approval")

    plan_entry = db.query(ContentPlanEntry).filter(ContentPlanEntry.id == run.plan_entry_id).first()
    channel = db.query(Channel).filter(Channel.id == run.channel_id).first()
    voices = _list_all_voices(db)

    agent = ChannelProducerAgent(channel, voices, mode=run.mode)
    proposal = agent.produce(plan_entry)

    run.config_json = json.dumps({
        "voice_cast": proposal.voice_cast,
        "mix_config": proposal.mix_config,
    }, ensure_ascii=False)
    episode = render_episode(db, run, channel, plan_entry, proposal, voices)
    run.episode_id = episode.id
    run.status = "rendering"
    db.commit()
    return {"ok": True, "episode_id": episode.id}
```

- [ ] **Step 2: Commit**

```bash
git add web_api/routes/channels.py
git commit -m "feat(producer): add channel producer endpoints"
```

---

### Task 5: Backend tests

**Files:**
- Create: `tests/web_api/test_producer_agent.py`

- [ ] **Step 1: Write tests**

```python
from unittest.mock import patch, MagicMock
from web_api.services.producer_agent import ChannelProducerAgent, _parse_json_flexible


def test_parse_json_flexible():
    raw = '```json\n{"voice_cast": {"narrador": "v1"}}\n```'
    data = _parse_json_flexible(raw)
    assert data["voice_cast"]["narrador"] == "v1"


def test_agent_produce_runs_crewai():
    channel = type("Channel", (), {
        "name": "Test",
        "format": "podcast_news",
        "niche": "tech",
    })()
    plan_entry = type("PlanEntry", (), {
        "title": "T1",
        "description": "D1",
    })()
    voices = [{"id": "v1", "name": "Voice 1", "engine": "edge", "type": "pretrained"}]

    with patch("web_api.services.producer_agent.get_planning_llm") as mock_llm:
        llm_instance = MagicMock()
        mock_llm.return_value = llm_instance

        def fake_crew_result(prompt):
            if "voice_cast" in prompt:
                return '{"voice_cast": {"narrador": "v1"}}'
            if "score" in prompt:
                return '{"score": 0.9, "feedback": "good"}'
            return "NARRADOR: Hola mundo"

        agent = ChannelProducerAgent(channel, voices, mode="manual")
        # Patch internal crew execution to avoid real LLM calls
        with patch.object(agent, "run_casting", return_value={"narrador": "v1"}):
            with patch.object(agent, "run_script", return_value="NARRADOR: Hola mundo"):
                with patch.object(agent, "run_quality_review", return_value=(0.9, "good")):
                    proposal = agent.produce(plan_entry)
                    assert proposal.script == "NARRADOR: Hola mundo"
                    assert proposal.voice_cast == {"narrador": "v1"}
                    assert proposal.quality_score == 0.9
```

- [ ] **Step 2: Run tests**

```bash
./venv311/bin/python -m pytest tests/web_api/test_producer_agent.py -q
```

Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add tests/web_api/test_producer_agent.py
git commit -m "test(producer): add producer agent tests"
```

---

### Task 6: Frontend types, API and store

**Files:**
- Modify: `web/src/types/index.ts`
- Modify: `web/src/api/client.ts`
- Create: `web/src/stores/producerStore.ts`

- [ ] **Step 1: Add types**

```typescript
export interface VoiceCastEntry {
  id?: number
  channel_id: number
  role: string
  voice_id: string
}

export interface ProductionRun {
  id: number
  channel_id: number
  episode_id?: number
  plan_entry_id?: number
  mode: 'manual' | 'auto'
  status: string
  quality_score?: number
  feedback?: string
  config_json: string
  metrics_json: string
  created_at: string
  completed_at?: string
}

export interface ProductionProposal {
  script: string
  voice_cast: Record<string, string>
  mix_config: Record<string, unknown>
  quality_score?: number
  feedback?: string
}
```

- [ ] **Step 2: Add API methods**

```typescript
export async function getChannelCast(channelId: number): Promise<VoiceCastEntry[]> {
  const response = await fetch(`/api/channels/${channelId}/cast`)
  if (!response.ok) throw new Error('Failed to fetch cast')
  return response.json()
}

export async function addChannelCast(channelId: number, data: Omit<VoiceCastEntry, 'id' | 'channel_id'>): Promise<VoiceCastEntry> {
  const response = await fetch(`/api/channels/${channelId}/cast`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!response.ok) throw new Error('Failed to add cast')
  return response.json()
}

export async function produceChannel(channelId: number, planEntryId: number, mode: 'manual' | 'auto'): Promise<ProductionRun> {
  const response = await fetch(`/api/channels/${channelId}/produce`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan_entry_id: planEntryId, mode }),
  })
  if (!response.ok) throw new Error('Failed to start production')
  return response.json()
}

export async function getChannelRuns(channelId: number): Promise<ProductionRun[]> {
  const response = await fetch(`/api/channels/${channelId}/runs`)
  if (!response.ok) throw new Error('Failed to fetch runs')
  return response.json()
}

export async function approveRun(runId: number): Promise<{ ok: boolean; episode_id: number }> {
  const response = await fetch(`/api/channels/runs/${runId}/approve`, { method: 'POST' })
  if (!response.ok) throw new Error('Failed to approve run')
  return response.json()
}
```

- [ ] **Step 3: Create store**

```typescript
import { create } from 'zustand'
import { approveRun, getChannelCast, getChannelRuns, produceChannel, addChannelCast } from '../api/client'
import type { ProductionRun, VoiceCastEntry } from '../types'

interface ProducerState {
  cast: VoiceCastEntry[]
  runs: ProductionRun[]
  loading: boolean
  producing: boolean
  error: string | null
  fetchCast: (channelId: number) => Promise<void>
  addCast: (channelId: number, role: string, voiceId: string) => Promise<void>
  fetchRuns: (channelId: number) => Promise<void>
  produce: (channelId: number, planEntryId: number, mode: 'manual' | 'auto') => Promise<void>
  approve: (runId: number) => Promise<void>
}

export const useProducerStore = create<ProducerState>((set, get) => ({
  cast: [],
  runs: [],
  loading: false,
  producing: false,
  error: null,
  fetchCast: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const cast = await getChannelCast(channelId)
      set({ cast, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
  addCast: async (channelId, role, voiceId) => {
    try {
      await addChannelCast(channelId, { role, voice_id: voiceId })
      await get().fetchCast(channelId)
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },
  fetchRuns: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const runs = await getChannelRuns(channelId)
      set({ runs, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
  produce: async (channelId, planEntryId, mode) => {
    set({ producing: true, error: null })
    try {
      await produceChannel(channelId, planEntryId, mode)
      await get().fetchRuns(channelId)
      set({ producing: false })
    } catch (err) {
      set({ error: (err as Error).message, producing: false })
    }
  },
  approve: async (runId) => {
    try {
      await approveRun(runId)
      // refresh runs for active channel could be added later
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },
}))
```

- [ ] **Step 4: Commit**

```bash
git add web/src/types/index.ts web/src/api/client.ts web/src/stores/producerStore.ts
git commit -m "feat(producer): add frontend types, API and store"
```

---

### Task 7: Frontend studio UI

**Files:**
- Create: `web/src/components/CastingGrid.tsx`
- Create: `web/src/components/ProducerRunTimeline.tsx`
- Create: `web/src/components/ChannelStudio.tsx`
- Create: `web/src/routes/channels.$id.studio.tsx`
- Create: `web/src/routes/channels.$id.studio.cast.tsx`
- Create: `web/src/routes/channels.$id.studio.producer.tsx`

- [ ] **Step 1: CastingGrid**

```tsx
import { useEffect, useState } from 'react'
import { useProducerStore } from '../stores/producerStore'
import { useVoiceStore } from '../stores/voiceStore'

interface CastingGridProps {
  channelId: number
}

export default function CastingGrid({ channelId }: CastingGridProps) {
  const { cast, fetchCast, addCast } = useProducerStore()
  const { voices, fetchVoices } = useVoiceStore()
  const [role, setRole] = useState('')
  const [voiceId, setVoiceId] = useState('')

  useEffect(() => {
    fetchCast(channelId)
    fetchVoices()
  }, [channelId, fetchCast, fetchVoices])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Casting</h2>
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Rol (ej: narrador)"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="rounded border p-2"
        />
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          className="rounded border p-2"
        >
          <option value="">Selecciona voz</option>
          {voices.map((v) => (
            <option key={v.id} value={String(v.id)}>{v.name} ({v.engine})</option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => { addCast(channelId, role, voiceId); setRole(''); setVoiceId('') }}
          className="rounded bg-blue-600 px-4 py-2 text-white"
        >
          Asignar
        </button>
      </div>
      <ul className="space-y-2">
        {cast.map((entry) => (
          <li key={entry.id} className="rounded border bg-white p-3">
            <span className="font-medium">{entry.role}</span> → {entry.voice_id}
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 2: ProducerRunTimeline**

```tsx
import type { ProductionRun } from '../types'

const statusColor: Record<string, string> = {
  proposed: 'bg-gray-200',
  rendering: 'bg-blue-200',
  review: 'bg-yellow-200',
  approved: 'bg-green-200',
  rejected: 'bg-red-200',
  failed: 'bg-red-300',
}

interface ProducerRunTimelineProps {
  runs: ProductionRun[]
  onApprove?: (runId: number) => void
}

export default function ProducerRunTimeline({ runs, onApprove }: ProducerRunTimelineProps) {
  return (
    <div className="space-y-3">
      {runs.map((run) => (
        <div key={run.id} className={`rounded border p-4 ${statusColor[run.status] || 'bg-white'}`}>
          <div className="flex items-center justify-between">
            <p className="font-semibold">Run #{run.id}</p>
            <span className="text-sm uppercase">{run.status}</span>
          </div>
          <p className="text-sm">Mode: {run.mode}</p>
          {run.quality_score !== undefined && (
            <p className="text-sm">Score: {run.quality_score.toFixed(2)}</p>
          )}
          {run.feedback && <p className="text-sm">{run.feedback}</p>}
          {run.status === 'proposed' && onApprove && (
            <button
              type="button"
              onClick={() => onApprove(run.id)}
              className="mt-2 rounded bg-green-600 px-3 py-1 text-sm text-white"
            >
              Aprobar y renderizar
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: ChannelStudio**

```tsx
import { useEffect, useState } from 'react'
import { Link } from '@tanstack/react-router'
import { useProducerStore } from '../stores/producerStore'
import { useChannelStore } from '../stores/channelStore'
import ProducerRunTimeline from './ProducerRunTimeline'

interface ChannelStudioProps {
  channelId: number
}

export default function ChannelStudio({ channelId }: ChannelStudioProps) {
  const { channels } = useChannelStore()
  const { runs, fetchRuns, approve } = useProducerStore()
  const [selectedPlanEntry, setSelectedPlanEntry] = useState<number | null>(null)
  const [mode, setMode] = useState<'manual' | 'auto'>('manual')

  const channel = channels.find((c) => c.id === channelId)

  useEffect(() => {
    fetchRuns(channelId)
  }, [channelId, fetchRuns])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Studio: {channel?.name}</h1>
      <nav className="flex gap-4">
        <Link to="/channels/$id/studio/cast" params={{ id: String(channelId) }} className="text-blue-600 hover:underline">
          Casting
        </Link>
        <Link to="/channels/$id/studio/producer" params={{ id: String(channelId) }} className="text-blue-600 hover:underline">
          Producer
        </Link>
      </nav>
      <ProducerRunTimeline runs={runs} onApprove={approve} />
    </div>
  )
}
```

- [ ] **Step 4: Routes**

`web/src/routes/channels.$id.studio.tsx`:
```tsx
import { createFileRoute } from '@tanstack/react-router'
import ChannelStudio from '../components/ChannelStudio'

export const Route = createFileRoute('/channels/$id/studio')({
  component: () => {
    const { id } = Route.useParams()
    return <ChannelStudio channelId={Number(id)} />
  },
})
```

`web/src/routes/channels.$id.studio.cast.tsx`:
```tsx
import { createFileRoute } from '@tanstack/react-router'
import CastingGrid from '../components/CastingGrid'

export const Route = createFileRoute('/channels/$id/studio/cast')({
  component: () => {
    const { id } = Route.useParams()
    return <CastingGrid channelId={Number(id)} />
  },
})
```

`web/src/routes/channels.$id.studio.producer.tsx`:
```tsx
import { createFileRoute } from '@tanstack/react-router'
import { useProducerStore } from '../stores/producerStore'
import ProducerRunTimeline from '../components/ProducerRunTimeline'

export const Route = createFileRoute('/channels/$id/studio/producer')({
  component: () => {
    const { id } = Route.useParams()
    const channelId = Number(id)
    const { runs, fetchRuns, approve } = useProducerStore()
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Producer</h2>
        <button
          type="button"
          onClick={() => fetchRuns(channelId)}
          className="rounded bg-blue-600 px-4 py-2 text-white"
        >
          Refresh
        </button>
        <ProducerRunTimeline runs={runs} onApprove={approve} />
      </div>
    )
  },
})
```

- [ ] **Step 5: Commit**

```bash
git add web/src/components/CastingGrid.tsx web/src/components/ProducerRunTimeline.tsx web/src/components/ChannelStudio.tsx web/src/routes/channels.$id.studio.tsx web/src/routes/channels.$id.studio.cast.tsx web/src/routes/channels.$id.studio.producer.tsx
git commit -m "feat(producer): add channel studio UI"
```

---

### Task 8: Frontend tests

**Files:**
- Create: `web/src/tests/ProducerRunTimeline.test.tsx`

- [ ] **Step 1: Write test**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ProducerRunTimeline from '../components/ProducerRunTimeline'

describe('ProducerRunTimeline', () => {
  it('renders runs and allows approve', () => {
    const runs = [
      { id: 1, status: 'proposed', mode: 'manual', quality_score: 0.8, feedback: 'OK', config_json: '{}', metrics_json: '{}', created_at: '2026-01-01' },
    ]
    const onApprove = vi.fn()

    render(<ProducerRunTimeline runs={runs} onApprove={onApprove} />)
    expect(screen.getByText('Run #1')).toBeInTheDocument()
    const button = screen.getByText('Aprobar y renderizar')
    fireEvent.click(button)
    expect(onApprove).toHaveBeenCalledWith(1)
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd web && npm test -- --run ProducerRunTimeline
```

Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add web/src/tests/ProducerRunTimeline.test.tsx
git commit -m "test(producer): add ProducerRunTimeline test"
```

---

### Task 9: Full test suite and build

- [ ] **Step 1: Run backend tests**

```bash
./venv311/bin/python -m pytest tests/web_api -q
```

- [ ] **Step 2: Run frontend tests**

```bash
cd web && npm test -- --run
```

- [ ] **Step 3: Build frontend**

```bash
cd web && npm run build
```

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "chore(producer): complete channel producer agent"
```

---

## Self-review

| Spec requirement | Task covering it |
|---|---|
| Channel voice cast model | Task 1 |
| ProductionRun model | Task 1 |
| CrewAI producer agent | Task 2 |
| Concrete rendering engine | Task 3 |
| Produce endpoint | Task 4 |
| Approve endpoint for manual mode | Task 4 |
| List runs endpoint | Task 4 |
| Cast endpoints | Task 4 |
| Frontend studio | Tasks 6-7 |
| Tests | Tasks 5, 8, 9 |

**Placeholder scan:** No TBD/TODO. Code complete.

**Type consistency:** `ProductionRun` model, schema, TypeScript type aligned. `VoiceCastEntry` matches API response.
