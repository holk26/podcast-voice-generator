# Design: Channel Producer Agent, Voice Cloning & System Diagnostics

## Status

Approved design — ready for implementation planning.

## Goal

Transform the channel system from a simple CRUD + editorial planner into an autonomous production team per channel, with:

1. Multi-engine voice cloning (XTTS, Higgs, Zonos).
2. A `ChannelProducerAgent` that orchestrates the full pipeline from plan to final audio.
3. A global diagnostics/health dashboard.
4. Continuous self-improvement backed by a structured history of changes and metrics.

## 1. High-level flow

Each channel owns a `ProducerAgent` that runs a CrewAI crew:

```
Channel configured with niche, format and voice cast
    ↓
[1] ContentStrategist  → proposes editorial plan
[2] CastingDirector    → assigns voices to roles/narrator
[3] ScriptWriter       → writes script with voice directions
[4] AudioProducer      → chooses TTS engine and mix settings
[5] DramaMixer         → renders multi-voice audio + music + SFX
[6] QualityReviewer    → evaluates the final episode and gives feedback
    ↓
Episode final + metrics → publish / review queue
```

Modes:

- **manual**: each step returns a proposal; the user approves/rejects before continuing.
- **auto**: the crew runs end-to-end, creating the episode automatically.

Self-improvement is **on by default** in both modes, but only adjusts prompts and per-channel config — never code.

## 2. Backend components

### 2.1 `VoiceCloneService` — `web_api/services/voice_clone_service.py`

- Receives a reference audio file and engine choice.
- Executes the selected engine:
  - **XTTS v2** via `core/xtts_engine.py` (fast, ~6 GB VRAM).
  - **Higgs Audio v3** via `core/higgs_engine.py` (best quality, ~8 GB+ VRAM).
  - **Zonos** via a new `core/zonos_engine.py` wrapper around `zonos/speaker_cloning.py`.
- Persists:
  - Reference audio in `voices/clones/<voice_id>/reference.<ext>`.
  - Profile YAML in `voices/clones/<voice_id>/profile.yaml`.
  - Row in `VoiceProfile` table.
- Endpoint: `POST /api/voices/clone` with multipart upload.
- Endpoint: `POST /api/voices/<id>/preview` to generate a sample.

### 2.2 `VoiceManager` — `web_api/services/voice_manager.py`

- Unified registry of pretrained and cloned voices.
- Endpoint: `GET /api/voices` returns merged list with metadata (engine, language, reference path).
- Endpoint: `DELETE /api/voices/<id>` for cloned voices.

### 2.3 `ChannelProducerAgent` — `web_api/services/producer_agent.py`

- CrewAI crew of 5 agents with well-defined prompts.
- Inputs: `Channel`, optional `ContentPlanEntry`, mode (`manual`/`auto`).
- Outputs a `ProductionResult` dataclass:
  - `script: str`
  - `voice_cast: dict[str, str]`  # role → voice_id
  - `audio_segments: list[Segment]`
  - `mix_config: MixConfig`
  - `quality_score: float`
  - `feedback: str`
- In **manual** mode returns the proposal without rendering audio.
- In **auto** mode delegates rendering to `ProductionEngine`.

### 2.4 `ProductionEngine` — `web_api/services/production_engine.py`

- Orchestrates concrete execution:
  1. Parses script into a `MediaPackage` via `AgentOrchestrator`.
  2. Calls TTS engines according to the voice cast.
  3. Mixes via `DramaMixer`.
  4. Writes outputs to `output/<episode_id>/`.
  5. Updates `Episode` status and paths.
- Implements fallback: if Higgs OOMs, retry with XTTS; if XTTS fails, fallback to Edge-TTS.

### 2.5 `DiagnosticsService` — `web_api/services/diagnostics_service.py`

Runs parallel checks and returns a list of diagnostic records:

| Component | Check | Expected OK state |
|---|---|---|
| GPU | `torch.cuda.is_available()` + free VRAM | NVIDIA GPU present, ≥2 GB free |
| CUDA | PyTorch CUDA version vs driver | Compatible versions |
| Ollama | `GET /api/tags` | Configured model available |
| TTS engines | Models downloaded | XTTS/Higgs/Zonos ready per config |
| Disk | Free space under `data/`, `output/`, `voices/` | ≥5 GB free each |
| Worker | `GET /health` | HTTP 200 |
| Web assets | Build or dev server | `web/dist/` exists or `127.0.0.1:5173` responds |

Endpoint: `GET /api/diagnostics`.
Endpoint: `GET /api/diagnostics/report` returns downloadable JSON report.

## 3. Data models

### New SQLAlchemy models

```python
class VoiceProfile(Base):
    id: int
    name: str
    engine: str          # xtts | higgs | zonos | edge | bark | orpheus
    type: str            # pretrained | cloned
    reference_path: str | None
    language: str | None
    owner_channel_id: int | None
    config_json: str     # engine-specific metadata
    created_at: datetime

class ChannelVoiceCast(Base):
    id: int
    channel_id: int
    role: str            # narrator, host, guest_a, etc.
    voice_id: int

class ProductionRun(Base):
    id: int
    channel_id: int
    episode_id: int | None
    plan_entry_id: int | None
    mode: str            # manual | auto
    status: str          # proposed | rendering | review | approved | rejected | failed
    quality_score: float | None
    feedback: str | None
    config_json: str     # voice_cast, mix_config, engine choices
    metrics_json: str    # render_time, segments, errors, user_rating
    created_at: datetime
    completed_at: datetime | None

class DiagnosticLog(Base):
    id: int
    component: str
    status: str          # ok | warning | error
    detail: str
    checked_at: datetime

class ChannelConfigHistory(Base):
    id: int
    channel_id: int
    change_type: str     # prompt | voice_cast | mix | plan_style
    old_value: str | None
    new_value: str | None
    reason: str | None
    production_run_id: int | None
    created_at: datetime
```

### Changes to existing models

- `Channel`:
  - `producer_mode: str` (`manual`/`auto`), default `manual`
  - `publish_rss_url: str | None`
  - `schedule_cron: str | None`
  - `voice_cast_json: str | None`
- `Episode`:
  - `production_run_id: int | None`
  - `voice_cast_json: str | None`
  - `quality_score: float | None`
  - `feedback: str | None`

## 4. Frontend

### New routes

- `/voices` — Voice Manager
- `/voices/clone` — Clone voice form
- `/channels/$id/studio` — Channel Studio (replaces/extends `/channels/$id/plan`)
- `/channels/$id/studio/cast` — Voice casting
- `/channels/$id/studio/producer` — Producer run panel
- `/system` — Diagnostics dashboard

### New stores

- `voiceCloneStore.ts`
- `producerStore.ts`
- `diagnosticsStore.ts`

### Key components

- `VoiceCard`, `CloneVoiceForm`, `VoiceUploader`
- `CastingGrid` — assign voices to roles
- `ProducerRunTimeline` — step-by-step pipeline status
- `DiagnosticCard`, `DiagnosticsDashboard`

## 5. Self-improvement with history

Self-improvement is **automatic by default** but fully auditable.

### What is captured

Every `ProductionRun` stores:

```json
{
  "tts_segments": 12,
  "render_time_seconds": 45,
  "errors": [],
  "engine_fallbacks": ["higgs → xtts"],
  "llm_quality_score": 0.82,
  "llm_feedback": "El ritmo es bueno, pero la música tapa la voz en 02:15",
  "user_rating": 4,
  "prompt_version": "script_writer_v3"
}
```

### What changes automatically

- `Channel` config/prompts stored in `config_json`.
- Adjustments are limited to:
  - Script writing style instructions.
  - Mix levels and SFX intensity.
  - Voice/engine assignments per role.
  - Plan editorial style.

### History and rollback

- `ChannelConfigHistory` table tracks every automatic change:
  - `change_type`, `old_value`, `new_value`, `reason`, `production_run_id`, `created_at`.
- UI shows a timeline of improvements per channel.
- User can revert any automatic change.

### Continuous learning

- When 3+ runs exist for a channel, the producer summarizes patterns:
  - "Episodios con voz clonada XTTS tienen score 15% mayor que Edge-TTS."
  - "Guiones de 600-700 palabras reciben mejor rating."
- These insights are surfaced in the Studio dashboard and can inform default prompts.

## 6. API endpoints

### Voices

- `GET /api/voices`
- `POST /api/voices/clone`
- `POST /api/voices/<id>/preview`
- `DELETE /api/voices/<id>`

### Channel producer

- `GET /api/channels/<id>/cast`
- `POST /api/channels/<id>/cast` — update voice assignments
- `POST /api/channels/<id>/produce` — start a production run
- `GET /api/channels/<id>/runs` — list production runs
- `GET /api/runs/<id>` — production run detail
- `POST /api/runs/<id>/approve` — continue/approve manual step
- `POST /api/runs/<id>/reject` — reject and stop

### Diagnostics

- `GET /api/diagnostics`
- `GET /api/diagnostics/report`

## 7. File layout

```
voices/clones/<voice_id>/
  reference.<ext>
  profile.yaml

output/<episode_id>/
  segments/
  final.mp3
  manifest.yaml

data/
  app.db
  production_runs/
```

## 8. Testing

### Unit tests

- `tests/web_api/test_voice_clone_service.py`
- `tests/web_api/test_voice_manager.py`
- `tests/web_api/test_producer_agent.py` (mocked CrewAI)
- `tests/web_api/test_diagnostics_service.py`

### Integration tests

- Clone voice endpoint with fake audio.
- Channel production endpoint creates `ProductionRun` + `Episode`.
- Diagnostics endpoint covers all components.

### Frontend tests

- `VoiceManager` renders voice list and clone form.
- `DiagnosticsDashboard` shows status cards.
- `ProducerRunTimeline` updates step states.

### Smoke test

- `scripts/smoke_test.py`: checks Ollama, GPU, voices, generates a 10-second sample.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Cloning uses too much VRAM on 8 GB cards | Engine selection with VRAM warnings; fallback chain Higgs → XTTS → Edge. |
| CrewAI produces malformed output | Reuse and extend the existing tolerant JSON parser. |
| Long render times block the API | Production runs are async; worker handles rendering. |
| Auto-improvement makes bad changes | History/rollback; changes limited to config/prompts, never code. |
| Many new endpoints to maintain | Follow existing FastAPI patterns; add tests from day one. |

## 10. Out of scope (for this cycle)

- Billing / usage limits.
- Multi-user permissions beyond current auth.
- Real-time collaborative editing.
- Cloud deployment packaging.
- Automatic code changes by the agent.
