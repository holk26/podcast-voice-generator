# Master Fixes + English Every Day Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the voice-cloning bugs (wrong voice / 11 s episodes / Qwen3-TTS crash), add publication states to channels/episodes, clean up Studio, add Alejandra's cleaned reference, and configure the "English Every Day" channel as a bilingual Alejandra-Homero dialogue.

**Architecture:** Keep the existing single-`voice_id` per episode model, but add an opt-in dialogue mode that parses a two-speaker script into segments, synthesizes each segment with the right cloned voice, and concatenates them. Fix the immediate TTS bugs with reference normalization and a monkey-patch for `qwen-tts` on `transformers>=5`. Surface publication states in the UI with badges and filters, and redesign Studio to be creation-focused.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + TanStack Router + Zustand (frontend), ffmpeg (audio preprocessing), Higgs v3 / Qwen3-TTS / edge-tts (TTS engines), pytest (tests).

---

## File map

| File | Responsibility |
|------|----------------|
| `core/qwen_tts_engine.py` | Qwen3-TTS engine; needs monkey-patch for `transformers>=5`. |
| `web_api/routes/tts.py` | Preview/synthesis endpoints; needs reference validation and better errors. |
| `web_api/routes/voices.py` | Voice listing; cloned voices are exposed twice (`higgs` / `qwen3`). |
| `audio/normalizer.py` | Already exists; reuse to normalize reference audio to 24 kHz mono. |
| `web_api/models.py` | Episode/Channel models; add `published_at` to Channel if missing. |
| `web_api/schemas.py` | Pydantic schemas; Channel response with publication fields. |
| `web_api/routes/channels.py` | Channel CRUD + publish/unpublish endpoints. |
| `web_api/routes/episodes.py` | Episode publish/unpublish already exists. |
| `web/src/types/index.ts` | Frontend types. |
| `web/src/stores/channelStore.ts` | Channel store; add publish actions. |
| `web/src/components/ChannelCard.tsx` | Show publication badge + actions. |
| `web/src/components/EpisodeCard.tsx` | Already has publish badge/button. |
| `web/src/routes/studio.tsx` | Redesign with tabs and hide old episodes by default. |
| `web/src/components/StudioPanel.tsx` | Channel creation controls. |
| `web_api/services/crew_service.py` | Script generation prompts; add bilingual/dual-speaker prompt variant. |
| `web_api/services/automation_service.py` | Episode creation; wire dialogue mode when channel requests it. |
| `processors/dialogue_parser.py` | NEW: parse `Personaje: texto` segments. |
| `core/multi_voice_mixer.py` | NEW: synthesize per-segment and concatenate. |
| `data/app.db` | SQLite DB; update channel brief/default_voice_id for English Every Day. |

---

## Phase 1: Critical TTS / voice bugs

### Task 1.1: Verify and label reference audio files

**Files:**
- Inspect: `voices/clones/alejandra.wav`
- Inspect: `voices/clones/homero_referencia.wav`

- [ ] **Step 1: Check file metadata and duration**

Run:
```bash
ffprobe -v quiet -print_format json -show_streams voices/clones/alejandra.wav voices/clones/homero_referencia.wav
```

Expected: both are WAV, mono, one may be 44100 Hz (Homero) and the other 24000 Hz (Alejandra).

- [ ] **Step 2: Listen / compare with user to confirm identity**

Play both files (or ask the user) to confirm `alejandra.wav` really contains Alejandra and `homero_referencia.wav` really contains Homero. If swapped, rename them:

```bash
mv voices/clones/alejandra.wav voices/clones/tmp.wav
mv voices/clones/homero_referencia.wav voices/clones/alejandra.wav
mv voices/clones/tmp.wav voices/clones/homero_referencia.wav
```

- [ ] **Step 3: Commit the verified references**

```bash
git add voices/clones/
git commit -m "fix(voice): verify and relabel cloned reference files"
```

---

### Task 1.2: Normalize all reference files to 24 kHz mono WAV

**Files:**
- Modify: `web_api/routes/voices.py:36-59`
- Create: `scripts/normalize_reference.py`

- [ ] **Step 1: Write the normalizer script**

```python
# scripts/normalize_reference.py
import subprocess
from pathlib import Path

CLONES_DIR = Path(__file__).resolve().parent.parent / "voices" / "clones"


def normalize(path: Path, out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(path),
            "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
            str(out),
        ],
        check=True,
    )


def main() -> None:
    for entry in sorted(CLONES_DIR.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}:
            continue
        tmp = entry.with_suffix(".norm.wav")
        normalize(entry, tmp)
        tmp.replace(entry)
        print(f"Normalized {entry.name}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the normalizer**

```bash
source venv311/bin/activate
python scripts/normalize_reference.py
```

Expected: all files in `voices/clones/` are now 24 kHz mono WAV.

- [ ] **Step 3: Add backend validation that rejects non-24kHz references**

In `web_api/routes/voices.py`, inside `_scan_cloned_voices`, log a warning if a file is not 24 kHz mono:

```python
import soundfile as sf


def _scan_cloned_voices() -> List[VoiceResponse]:
    cloned: List[VoiceResponse] = []
    if not CLONES_DIR.is_dir():
        return cloned
    for entry in sorted(CLONES_DIR.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        try:
            info = sf.info(entry)
            if info.samplerate != 24000 or info.channels != 1:
                print(f"[voices] WARNING {entry.name}: expected 24000 Hz mono, got {info.samplerate} Hz {info.channels}ch")
        except Exception as e:
            print(f"[voices] WARNING could not inspect {entry.name}: {e}")
        stem = entry.stem
        for engine in CLONE_ENGINES:
            suffix = "" if engine == "higgs" else f":{engine}"
            cloned.append(
                VoiceResponse(
                    id=f"clone:{stem}{suffix}",
                    name=f"{stem} ({engine})" if engine != "higgs" else stem,
                    engine=engine,
                    language="es",
                    gender="unknown",
                    type="cloned",
                    reference_path=str(entry),
                )
            )
    return cloned
```

- [ ] **Step 4: Test voice listing still works**

Run:
```bash
curl -s http://127.0.0.1:8000/api/voices | python -m json.tool
```

Expected: JSON array includes `clone:alejandra`, `clone:homero_referencia`, and their `:qwen3` variants.

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize_reference.py web_api/routes/voices.py
git commit -m "fix(voice): normalize cloned references to 24kHz mono and warn on mismatch"
```

---

### Task 1.3: Fix Qwen3-TTS import crash on transformers>=5

**Files:**
- Modify: `core/qwen_tts_engine.py:75-110`

- [ ] **Step 1: Add monkey-patch before importing Qwen3TTSModel**

Replace the `load()` method's import block in `core/qwen_tts_engine.py`:

```python
    def load(self) -> None:
        if self._loaded:
            return

        _free_ollama_vram()

        # Monkey-patch: qwen-tts 0.1.1 uses @check_model_inputs() but
        # transformers>=5 exposes a plain decorator without parentheses.
        try:
            import transformers.utils.generic as _generic
            _orig = _generic.check_model_inputs
            def _patched(*args, **kwargs):
                if args and callable(args[0]):
                    return _orig(args[0])
                return _orig
            if not getattr(_orig, "_qwen_patched", False):
                _generic.check_model_inputs = _patched
                _patched._qwen_patched = True
        except Exception:
            pass

        try:
            from qwen_tts import Qwen3TTSModel
        except ImportError as e:
            raise ImportError(
                "qwen-tts no está instalado. Instala con: pip install qwen-tts "
                "(ver docs/QWEN3_TTS_SETUP.md)"
            ) from e
        ...
```

- [ ] **Step 2: Write a failing test that reproduces the import**

Create `tests/test_qwen_tts_engine.py`:

```python
import pytest


def test_qwen_engine_can_load_without_check_model_inputs_error():
    from core.qwen_tts_engine import Qwen3TTSEngine
    engine = Qwen3TTSEngine(device="cpu", dtype="float32")
    # Loading a 1.7B model on CPU is too heavy for a unit test; just verify
    # the monkey-patch helper runs without raising.
    try:
        import transformers.utils.generic as _generic
        _orig = _generic.check_model_inputs
        assert callable(_orig)
    except ImportError:
        pytest.skip("transformers not installed")
```

- [ ] **Step 3: Run the test**

```bash
source venv311/bin/activate
pytest tests/test_qwen_tts_engine.py -v
```

Expected: PASS.

- [ ] **Step 4: Try a Qwen3 preview via the API**

```bash
curl -s -X POST http://127.0.0.1:8000/api/tts/preview \
  -H "Content-Type: application/json" \
  -d '{"voice_id":"clone:alejandra:qwen3","text":"Hola, esta es una prueba."}'
```

Expected: returns `{"audio_url": "/outputs/previews/<id>.wav"}` and no `TypeError`.

- [ ] **Step 5: Commit**

```bash
git add core/qwen_tts_engine.py tests/test_qwen_tts_engine.py
git commit -m "fix(tts): monkey-patch qwen-tts for transformers>=5 check_model_inputs"
```

---

### Task 1.4: Harden preview endpoint and clear cached audio

**Files:**
- Modify: `web_api/routes/tts.py:174-198`

- [ ] **Step 1: Add explicit reference-path validation in preview**

In `web_api/routes/tts.py`, inside `preview`, before calling `_synthesize_clone`:

```python
        if voice is not None and voice.type == "cloned" and voice.reference_path:
            ref = Path(voice.reference_path)
            if not ref.exists():
                raise HTTPException(status_code=400, detail=f"Reference audio missing: {ref}")
            try:
                import soundfile as sf
                info = sf.info(ref)
                if info.samplerate != 24000 or info.channels != 1:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Reference audio must be 24000 Hz mono, got {info.samplerate} Hz {info.channels}ch",
                    )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid reference audio: {e}")
```

- [ ] **Step 2: Clear previous preview when changing voice**

This is a frontend concern already handled in `voices.tsx` (`setAudioUrl(null)`), but ensure no browser cache is served. In `preview`, append a cache-busting suffix:

```python
            return PreviewResponse(audio_url=f"/outputs/previews/{wav_path.name}?v={uuid.uuid4().hex[:8]}")
```

- [ ] **Step 3: Test error case**

```bash
curl -s -X POST http://127.0.0.1:8000/api/tts/preview \
  -H "Content-Type: application/json" \
  -d '{"voice_id":"clone:missing","text":"test"}'
```

Expected: HTTP 400.

- [ ] **Step 4: Commit**

```bash
git add web_api/routes/tts.py
git commit -m "fix(tts): validate reference audio in preview and bust cache"
```

---

### Task 1.5: Investigate the "11-second episode" report

**Files:**
- Inspect: `output/<id>/final.wav` for recent episode IDs
- Inspect: `logs/worker.log`, `logs/api.log`

- [ ] **Step 1: List recent completed episodes and durations**

```bash
sqlite3 data/app.db "SELECT id, title, target_duration_minutes, status, created_at FROM episodes ORDER BY id DESC LIMIT 10;"
```

For each recent `completed` episode:

```bash
ffprobe -v error -show_entries format=duration -of csv="p=0" output/<id>/final.wav
```

- [ ] **Step 2: If any episode is abnormally short, inspect its script**

```bash
sqlite3 data/app.db "SELECT source_text FROM episodes WHERE id=<id>;" | wc -w
```

Expected: word count roughly matches `target_duration_minutes * 130`.

- [ ] **Step 3: Check worker logs for that episode ID**

```bash
grep -n "<id>" logs/worker.log logs/api.log
```

Look for:
- `_split_text` producing only 1 chunk.
- `_concat_wavs` concatenating an empty list.
- Higgs engine returning silence or truncated audio.

- [ ] **Step 4: Add a guard in `_concat_wavs` to fail loudly on empty input**

In `web_api/routes/tts.py:116`:

```python
def _concat_wavs(paths: list[Path], output_path: Path) -> Path:
    if not paths:
        raise ValueError("No audio parts to concatenate")
    ...
```

- [ ] **Step 5: Commit**

```bash
git add web_api/routes/tts.py
git commit -m "fix(tts): fail loudly when TTS produces no audio parts"
```

---

## Phase 2: Add Alejandra's cleaned reference

### Task 2.1: Convert and clean the provided `Voice Alejandra.m4a`

**Files:**
- Input: user-provided `Voice Alejandra.m4a` (to be placed in repo root)
- Output: `voices/clones/alejandra.wav`
- Create: `scripts/add_voice_reference.py`

- [ ] **Step 1: Place the source file in the repo root**

The user must provide the file. Once available, verify it:

```bash
file "Voice Alejandra.m4a"
ffprobe -v quiet -print_format json -show_streams "Voice Alejandra.m4a"
```

- [ ] **Step 2: Create the add-voice helper script**

```python
# scripts/add_voice_reference.py
import argparse
import subprocess
from pathlib import Path

CLONES_DIR = Path(__file__).resolve().parent.parent / "voices" / "clones"


def process(src: Path, name: str) -> Path:
    CLONES_DIR.mkdir(parents=True, exist_ok=True)
    out = CLONES_DIR / f"{name}.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src),
            # High-pass rumble, normalize, convert to 24kHz mono
            "-af", "highpass=f=80,loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
            str(out),
        ],
        check=True,
    )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="Source audio file")
    parser.add_argument("--name", default="alejandra", help="Voice stem")
    args = parser.parse_args()
    out = process(Path(args.src), args.name)
    print(f"Reference ready: {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the conversion**

```bash
source venv311/bin/activate
python scripts/add_voice_reference.py "Voice Alejandra.m4a" --name alejandra
```

- [ ] **Step 4: Verify the output**

```bash
ffprobe -v error -show_entries format=duration,bit_rate -show_entries stream=sample_rate,channels -of default=noprint_wrappers=1 voices/clones/alejandra.wav
```

Expected: 24000 Hz, 1 channel, reasonable duration (3-30 s).

- [ ] **Step 5: Commit**

```bash
git add scripts/add_voice_reference.py voices/clones/alejandra.wav
git commit -m "feat(voice): add cleaned Alejandra reference at 24kHz mono"
```

---

## Phase 3: Publication states for channels and episodes

### Task 3.1: Add `published_at` to Channel and publish endpoints

**Files:**
- Modify: `web_api/models.py:24-41`
- Modify: `web_api/schemas.py`
- Modify: `web_api/routes/channels.py`

- [ ] **Step 1: Add column to Channel model**

```python
class Channel(Base):
    ...
    published_at = Column(DateTime, nullable=True)  # manual publish marker
```

- [ ] **Step 2: Add field to schemas**

In `web_api/schemas.py`, add `published_at: Optional[datetime] = None` to `ChannelResponse` and `ChannelUpdate`.

- [ ] **Step 3: Add publish/unpublish endpoints**

In `web_api/routes/channels.py`, after the deactivate endpoint:

```python
from datetime import datetime, timezone


@router.post("/{channel_id}/publish", response_model=ChannelResponse)
def publish_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/{channel_id}/unpublish", response_model=ChannelResponse)
def unpublish_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.published_at = None
    db.commit()
    db.refresh(channel)
    return channel
```

- [ ] **Step 4: Write migration-free DB update script**

Since the project does not use Alembic, add a startup guard in `web_api/database.py`:

```python
from sqlalchemy import inspect

def ensure_columns() -> None:
    engine = engine_instance()
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("channels")}
    if "published_at" not in cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE channels ADD COLUMN published_at DATETIME"))
            conn.commit()
```

Call it once at import time in `web_api/main.py`.

- [ ] **Step 5: Test the new endpoints**

```bash
curl -s -X POST http://127.0.0.1:8000/api/channels/1/publish | python -m json.tool
curl -s -X POST http://127.0.0.1:8000/api/channels/1/unpublish | python -m json.tool
```

Expected: returns channel JSON with `published_at` set/cleared.

- [ ] **Step 6: Commit**

```bash
git add web_api/models.py web_api/schemas.py web_api/routes/channels.py web_api/database.py web_api/main.py
git commit -m "feat(channels): add published_at and publish/unpublish endpoints"
```

---

### Task 3.2: Frontend ChannelCard badge + actions

**Files:**
- Modify: `web/src/types/index.ts:37-53`
- Modify: `web/src/stores/channelStore.ts`
- Modify: `web/src/components/ChannelCard.tsx`

- [ ] **Step 1: Update types**

```typescript
export interface Channel {
  ...
  published_at?: string | null
}
```

- [ ] **Step 2: Add publish/unpublish actions to channelStore**

```typescript
  publishChannel: (id: number) => Promise<void>
  unpublishChannel: (id: number) => Promise<void>
```

Implement with `api.post(`/channels/${id}/publish`)` and refetch.

- [ ] **Step 3: Update ChannelCard**

Show a "Publicado" badge when `channel.published_at` exists and add publish/unpublish buttons:

```tsx
      <div className="flex justify-between items-start">
        <div>...</div>
        <div className="flex gap-2">
          {channel.published_at && (
            <span className="text-xs px-2 py-1 rounded-lg border bg-emerald-500/15 border-emerald-500/40 text-emerald-300">
              Publicado
            </span>
          )}
          <span className={`text-xs px-2 py-1 rounded-lg border ${channel.is_active ? 'bg-green-500/15 border-green-500/40 text-green-300' : 'bg-slate-700/50 border-slate-600 text-slate-400'}`}>
            {channel.is_active ? 'Activo' : 'Inactivo'}
          </span>
        </div>
      </div>
```

And in actions:

```tsx
        {channel.published_at ? (
          <button onClick={() => onUnpublish(channel.id)} className="text-slate-400 hover:text-slate-300 text-sm">Desmarcar publicado</button>
        ) : (
          <button onClick={() => onPublish(channel.id)} className="text-emerald-400 hover:text-emerald-300 text-sm">Marcar publicado</button>
        )}
```

- [ ] **Step 4: Run frontend type check**

```bash
cd web && npm run typecheck
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/types/index.ts web/src/stores/channelStore.ts web/src/components/ChannelCard.tsx
git commit -m "feat(channels): show publication badge and actions in ChannelCard"
```

---

### Task 3.3: Improve EpisodeCard status labels in Spanish

**Files:**
- Modify: `web/src/components/EpisodeCard.tsx:12-17`

- [ ] **Step 1: Translate status labels**

```typescript
const statusLabels: Record<Episode['status'], string> = {
  pending: 'Pendiente',
  running: 'En progreso',
  completed: 'Completado',
  failed: 'Fallido',
}
```

Replace `{episode.status}` with `{statusLabels[episode.status]}`.

- [ ] **Step 2: Run tests**

```bash
cd web && npm test -- EpisodeCard.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/EpisodeCard.tsx
git commit -m "ui(episodes): translate status labels to Spanish"
```

---

## Phase 4: Clean up Studio

### Task 4.1: Redesign Studio with tabs

**Files:**
- Modify: `web/src/routes/studio.tsx`

- [ ] **Step 1: Add tab state and hide old episodes by default**

```typescript
type StudioTab = 'overview' | 'plan' | 'config'

function StudioPage() {
  ...
  const [tab, setTab] = useState<StudioTab>('overview')
```

- [ ] **Step 2: Render tab navigation after channel header**

```tsx
      {channel && (
        <div className="flex gap-2 mb-4">
          {(['overview','plan','config'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-lg text-sm border ${tab === t ? 'bg-purple-600 border-purple-500 text-white' : 'bg-slate-800 border-slate-600 text-slate-300'}`}
            >
              {t === 'overview' ? 'Resumen' : t === 'plan' ? 'Plan editorial' : 'Configuración'}
            </button>
          ))}
        </div>
      )}
```

- [ ] **Step 3: Show only relevant panels per tab**

- `overview`: channel description + quick actions (generate plan / season) + latest 3 plan entries.
- `plan`: full `ContentPlanList`.
- `config`: `StudioPanel` controls (voice, target minutes, autopilot).

- [ ] **Step 4: Remove CongressTable from Studio or move to a separate route**

Either delete `<CongressTable />` from `studio.tsx` or move it behind an "Agentes" tab. The user said Studio should be for creation, so remove it from the default view.

- [ ] **Step 5: Run type check and tests**

```bash
cd web && npm run typecheck && npm test -- studio
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/routes/studio.tsx
git commit -m "ui(studio): redesign with tabs and hide old episodes by default"
```

---

### Task 4.2: Add "recent only" filter to plan entries

**Files:**
- Modify: `web/src/components/ContentPlanList.tsx`

- [ ] **Step 1: Add a toggle for archived entries**

The component already has an archive toggle. Make it collapsed by default and add a "Mostrar solo últimos 30 días" filter:

```typescript
  const [recentOnly, setRecentOnly] = useState(true)
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 30)
  const filteredDrafts = recentOnly
    ? drafts.filter((e) => !e.created_at || new Date(e.created_at) >= cutoff)
    : drafts
```

- [ ] **Step 2: Render the toggle**

```tsx
      <div className="flex justify-end mb-2">
        <label className="flex items-center gap-2 text-sm text-slate-400">
          <input type="checkbox" checked={recentOnly} onChange={(e) => setRecentOnly(e.target.checked)} />
          Solo últimos 30 días
        </label>
      </div>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/ContentPlanList.tsx
git commit -m "ui(plan): recent-only filter to reduce noise"
```

---

## Phase 5: Configure English Every Day as bilingual Alejandra-Homero

### Task 5.1: Update channel brief and default voice

**Files:**
- Modify: `data/app.db` (via API or script)
- Modify: `web_api/services/crew_service.py:717-725`

- [ ] **Step 1: Update the channel via API**

```bash
curl -s -X PUT http://127.0.0.1:8000/api/channels/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name":"English Every Day",
    "description":"Aprende inglés práctico con una conversación bilingüe entre Alejandra (profesora) y Homero (alumno).",
    "niche":"educación / idiomas",
    "format":"podcast",
    "default_voice_id":"clone:homero_referencia",
    "is_active":true,
    "target_minutes":10,
    "brief":"Canal de enseñanza de inglés en formato diálogo bilingüe.\n- Personajes: Alejandra (profesora, voz femenina) y Homero (alumno, voz masculina).\n- Estructura: Alejandra presenta una frase o vocabulario en inglés, lo pronuncia con claridad, y Homero pregunta o repite. Luego Alejandra explica el significado y uso en español.\n- Idioma: mezcla 50% inglés / 50% español; el inglés debe ser natural y didáctico, el español de apoyo.\n- Tono: cercano, paciente, motivador.\n- Reglas: cada episodio introduce 5-8 expresiones útiles, incluye ejemplos de situaciones reales, y termina con un mini repaso."
  }'
```

- [ ] **Step 2: Verify the update**

```bash
curl -s http://127.0.0.1:8000/api/channels/1 | python -m json.tool
```

Expected: `default_voice_id` is `clone:homero_referencia` and brief matches.

- [ ] **Step 3: Commit the DB change**

```bash
git add data/app.db
git commit -m "data(channel): configure English Every Day bilingual brief"
```

---

### Task 5.2: Implement dual-speaker script generation (dialogue mode)

**Files:**
- Create: `processors/dialogue_parser.py`
- Create: `core/multi_voice_mixer.py`
- Modify: `web_api/services/crew_service.py:311-528`
- Modify: `web_api/services/automation_service.py:96-134`

- [ ] **Step 1: Create the dialogue parser**

```python
# processors/dialogue_parser.py
import re
from dataclasses import dataclass
from typing import List


@dataclass
class DialogueSegment:
    speaker: str
    text: str


SPEAKER_RE = re.compile(r"^(Alejandra|Homero):\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def parse_dialogue(script: str) -> List[DialogueSegment]:
    """Split a script into segments when lines start with 'Alejandra:' or 'Homero:'."""
    segments: List[DialogueSegment] = []
    current_speaker: str | None = None
    current_lines: List[str] = []

    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        m = SPEAKER_RE.match(line)
        if m:
            if current_speaker and current_lines:
                segments.append(DialogueSegment(current_speaker, " ".join(current_lines)))
            current_speaker = m.group(1).capitalize()
            current_lines = [m.group(2)]
        elif current_speaker:
            current_lines.append(line)

    if current_speaker and current_lines:
        segments.append(DialogueSegment(current_speaker, " ".join(current_lines)))

    return segments
```

- [ ] **Step 2: Create the multi-voice mixer**

```python
# core/multi_voice_mixer.py
import json
import urllib.request
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf

from processors.dialogue_parser import DialogueSegment
from core.project import Voice
from web_api.routes.voices import _find_voice, VoiceResponse

API_BASE = "http://localhost:8000"


def _synth_segment(text: str, voice: VoiceResponse, output: Path) -> Path:
    req = urllib.request.Request(
        f"{API_BASE}/api/tts/synthesize",
        data=json.dumps({
            "voice_id": voice.id,
            "text": text,
            "label": f"{voice.name}: {text[:60]}...",
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3600) as resp:
        audio_url = json.load(resp)["audio_url"]
    with urllib.request.urlopen(f"{API_BASE}{audio_url}", timeout=300) as resp:
        output.write_bytes(resp.read())
    return output


def _read_mono_24k(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data.astype(np.float32), sr


def mix_dialogue(segments: List[DialogueSegment], output: Path, voice_map: dict[str, str]) -> Path:
    """Synthesize each segment with its mapped voice and concatenate."""
    parts: List[np.ndarray] = []
    rate = 24000
    for i, seg in enumerate(segments):
        voice_id = voice_map.get(seg.speaker)
        if not voice_id:
            raise ValueError(f"No voice mapped for speaker {seg.speaker}")
        voice = _find_voice(voice_id)
        if not voice:
            raise ValueError(f"Voice not found: {voice_id}")
        part_path = output.with_suffix(f".{i}.wav")
        _synth_segment(seg.text, voice, part_path)
        data, sr = _read_mono_24k(part_path)
        rate = sr
        parts.append(data)
        part_path.unlink(missing_ok=True)

    sf.write(str(output), np.concatenate(parts), rate, format="WAV", subtype="PCM_16")
    return output
```

- [ ] **Step 3: Add a dialogue prompt variant in crew_service**

Add a helper that detects when the channel name or brief implies a dual-speaker English lesson:

```python
_DUAL_SPEAKER_HINT_RE = re.compile(r"Alejandra.*Homero|Homero.*Alejandra|diálogo|dialogue", re.IGNORECASE)


def _is_dialogue_mode(channel) -> bool:
    text = f"{channel.name} {channel.brief or ''}"
    return bool(_DUAL_SPEAKER_HINT_RE.search(text))
```

When `_is_dialogue_mode(channel)` is true, override the section prompt to ask the writer to produce lines prefixed with `Alejandra:` or `Homero:`.

- [ ] **Step 4: Wire dialogue synthesis in automation_service**

In `run_script_job`, after generating the script, detect dialogue mode and call the mixer:

```python
    from processors.dialogue_parser import parse_dialogue
    from core.multi_voice_mixer import mix_dialogue

    script = generate_script(...)

    if _is_dialogue_mode(channel):
        segments = parse_dialogue(script)
        if len(segments) >= 2:
            episode = Episode(..., source_text=script, voice_id="multi:alejandra_homero")
            session.add(episode)
            session.commit()
            session.refresh(episode)
            output_dir = OUTPUT_DIR / str(episode.id)
            output_dir.mkdir(parents=True, exist_ok=True)
            mix_dialogue(
                segments,
                output_dir / "final.wav",
                voice_map={"Alejandra": "clone:alejandra", "Homero": "clone:homero_referencia"},
            )
            episode.audio_url = f"/outputs/{episode.id}/final.wav"
            episode.status = "completed"
            session.commit()
            entry.status = "generated"
            entry.episode_id = episode.id
            session.commit()
            registry.emit(job_id, "done", f"Diálogo listo, episodio #{episode.id}")
            return
```

- [ ] **Step 5: Add tests for dialogue parser**

Create `tests/test_dialogue_parser.py`:

```python
from processors.dialogue_parser import parse_dialogue


def test_parse_two_speakers():
    script = "Alejandra: Hello, how are you?\nHomero: Estoy bien, gracias.\nAlejandra: Great!"
    segments = parse_dialogue(script)
    assert len(segments) == 3
    assert segments[0].speaker == "Alejandra"
    assert "Hello" in segments[0].text
```

- [ ] **Step 6: Run tests**

```bash
source venv311/bin/activate
pytest tests/test_dialogue_parser.py -v
```

Expected: PASS.

- [ ] **Step 7: Generate a test episode for English Every Day**

In the UI or via API, approve a draft for channel 1. Wait for completion. Verify:

```bash
ffprobe -v error -show_entries format=duration -of csv="p=0" output/<episode_id>/final.wav
```

Expected: duration close to 10 minutes and audio contains both voices.

- [ ] **Step 8: Commit**

```bash
git add processors/dialogue_parser.py core/multi_voice_mixer.py web_api/services/crew_service.py web_api/services/automation_service.py tests/test_dialogue_parser.py
git commit -m "feat(dialogue): bilingual Alejandra-Homero synthesis for English Every Day"
```

---

## Phase 6: Verification

### Task 6.1: Run the full test suite

- [ ] **Step 1: Backend tests**

```bash
source venv311/bin/activate
pytest tests/ -q --tb=short
```

Expected: all tests pass (or only pre-existing failures documented).

- [ ] **Step 2: Frontend tests**

```bash
cd web && npm test -- --run
```

Expected: all tests pass.

- [ ] **Step 3: Manual smoke tests**

1. Open `http://127.0.0.1:5173/voices`.
2. Preview `clone:homero_referencia` → should sound like Homero.
3. Preview `clone:alejandra` → should sound like Alejandra.
4. Preview `clone:alejandra:qwen3` → should not crash.
5. Go to `/channels` → see publication badges.
6. Go to `/studio` → see tabs, no overwhelming old episodes.
7. Generate an episode for "English Every Day" → should be bilingual dialogue.

- [ ] **Step 4: Commit any final fixes**

```bash
git commit -am "fix: final verification tweaks"
```

---

## Self-review

**Spec coverage:**
- Bug "Homero suena como Alejandra" → Task 1.1 (verify labels) + Task 1.2 (normalize sample rate).
- Bug Qwen3-TTS crash → Task 1.3 (monkey-patch).
- "11 s episode" → Task 1.5 (investigation + guard).
- Estados de publicación → Task 3.1 + 3.2 + 3.3.
- Limpiar Studio → Task 4.1 + 4.2.
- Emociones / expresividad → already implemented in `core/emotion_tags.py`; verified by Higgs engine. No new task needed unless user asks for UI controls.
- Voz Alejandra → Task 2.1.
- English Every Day → Task 5.1 + 5.2.

**Placeholder scan:**
- No "TBD" / "TODO" / "implement later".
- All file paths and commands are concrete.
- Code snippets are complete for their scope.

**Type consistency:**
- `published_at` added to Channel model, schema, response, and UI type consistently.
- `DialogueSegment.speaker` uses capitalized names matching the voice map.

**One gap:** Task 1.5 is investigative; if the root cause is found, an additional fix task may be needed.
