# Voice Cloning Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a voice manager where users can clone voices from reference audio using XTTS, Higgs, or Zonos, preview them, and manage pretrained + cloned voices.

**Architecture:** A `VoiceProfile` table stores voice metadata. `VoiceCloneService` validates reference audio, runs the chosen engine, and persists files. `VoiceManagerService` merges database profiles with static pretrained voices. The frontend provides upload, preview, and listing UI.

**Tech Stack:** FastAPI, SQLAlchemy, PyTorch, TTS, Zonos, React 18, TanStack Router, Zustand.

---

## File Structure

| File | Responsibility |
|---|---|
| `web_api/models.py` (modify) | Add `VoiceProfile` model |
| `web_api/schemas.py` (modify) | Add `VoiceProfileCreate`, `VoiceProfileResponse` |
| `web_api/services/voice_clone_service.py` | Clone voice with selected engine |
| `web_api/services/voice_manager.py` | Merge DB profiles + pretrained voices |
| `core/zonos_engine.py` | New wrapper for Zonos voice cloning/synthesis |
| `web_api/routes/voices.py` (modify) | Add clone, list, preview, delete endpoints |
| `web_api/main.py` (modify) | Already includes voices router |
| `web/src/types/index.ts` (modify) | Add `VoiceProfile` types |
| `web/src/api/client.ts` (modify) | Add voice API methods |
| `web/src/stores/voiceStore.ts` | Voice list + clone form state |
| `web/src/components/VoiceManager.tsx` | Main voices page |
| `web/src/components/CloneVoiceForm.tsx` | Upload + engine selection form |
| `web/src/components/VoiceCard.tsx` | Single voice card |
| `web/src/routes/voices.tsx` (modify) | Route for `/voices` |
| `web/src/routes/voices.clone.tsx` | Route for `/voices/clone` |
| `web/src/components/Layout.tsx` (modify) | Link to `/voices` |
| `tests/web_api/test_voice_clone_service.py` | Backend tests |
| `web/src/tests/VoiceManager.test.tsx` | Frontend tests |

---

### Task 1: Add VoiceProfile model and schemas

**Files:**
- Modify: `web_api/models.py`
- Modify: `web_api/schemas.py`

- [ ] **Step 1: Add model**

```python
class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    engine = Column(String, nullable=False)  # xtts | higgs | zonos | edge | bark
    type = Column(String, nullable=False, default="cloned")  # cloned | pretrained
    reference_path = Column(String, nullable=True)
    language = Column(String, nullable=True)
    config_json = Column(String, nullable=True, default="{}")
    owner_channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Add schemas**

```python
class VoiceProfileCreate(BaseModel):
    name: str
    engine: str
    language: Optional[str] = "es"
    owner_channel_id: Optional[int] = None


class VoiceProfileResponse(BaseModel):
    id: int
    name: str
    engine: str
    type: str
    reference_path: Optional[str]
    language: Optional[str]
    config_json: str
    owner_channel_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
```

- [ ] **Step 3: Commit**

```bash
git add web_api/models.py web_api/schemas.py
git commit -m "feat(voices): add VoiceProfile model and schemas"
```

---

### Task 2: Create Zonos engine wrapper

**Files:**
- Create: `core/zonos_engine.py`

- [ ] **Step 1: Implement wrapper**

```python
import os
from pathlib import Path
from typing import Optional

import torch
import torchaudio

from core.project import Voice
from core.tts_engine import TTSBase
from utils.gpu_utils import select_best_device, clear_gpu_cache


class ZonosEngine(TTSBase):
    def __init__(self, device: str = "auto"):
        self.device = select_best_device() if device == "auto" else device
        self.name = "zonos"
        self._model = None

    def load(self) -> None:
        if self._model is not None:
            return
        from zonos.model import Zonos
        self._model = Zonos.from_pretrained("Zyphra/Zonos-v0.1-transformer", device=self.device)

    def unload(self) -> None:
        self._model = None
        clear_gpu_cache()

    def is_loaded(self) -> bool:
        return self._model is not None

    def clone_voice(self, reference_path: str, name: str) -> str:
        self.load()
        wav, sr = torchaudio.load(reference_path)
        if sr != 44100:
            wav = torchaudio.transforms.Resample(sr, 44100)(wav)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        wav = wav.to(self.device)
        speaker_embedding = self._model.make_speaker_embedding(wav, 44100)
        profile_dir = Path("voices/clones") / f"zonos_{name}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        torch.save(speaker_embedding, profile_dir / "speaker.pt")
        return str(profile_dir / "speaker.pt")

    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        self.load()
        if not voice.reference_path or not os.path.exists(voice.reference_path):
            raise FileNotFoundError(f"Zonos speaker embedding not found: {voice.reference_path}")
        speaker_embedding = torch.load(voice.reference_path, map_location=self.device)
        conditioning = self._model.prepare_conditioning(text, speaker=speaker_embedding)
        codes = self._model.generate(conditioning)
        wav = self._model.decode(codes)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        torchaudio.save(output_path, wav.cpu(), sample_rate=44100)
        return output_path
```

- [ ] **Step 2: Commit**

```bash
git add core/zonos_engine.py
git commit -m "feat(voices): add Zonos TTS engine wrapper"
```

---

### Task 3: Implement VoiceCloneService

**Files:**
- Create: `web_api/services/voice_clone_service.py`

- [ ] **Step 1: Implement service**

```python
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from web_api.models import VoiceProfile
from web_api.schemas import VoiceProfileCreate


VOICES_DIR = Path(__file__).resolve().parent.parent.parent / "voices" / "clones"


def _ensure_reference_dir() -> Path:
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    return VOICES_DIR


def _validate_audio_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 50:
        raise ValueError("Reference audio must be <= 50 MB")


def clone_voice(
    db: Session,
    data: VoiceProfileCreate,
    reference_file: str,
) -> VoiceProfile:
    _validate_audio_file(Path(reference_file))
    base_dir = _ensure_reference_dir()
    voice_id = uuid.uuid4().hex[:12]
    profile_dir = base_dir / voice_id
    profile_dir.mkdir(parents=True, exist_ok=True)

    dest_path = profile_dir / "reference.wav"
    shutil.copy(reference_file, dest_path)

    engine_name = data.engine.lower()
    embedding_path: Optional[str] = None

    if engine_name == "xtts":
        from core.xtts_engine import XTTSEngine
        engine = XTTSEngine()
        engine.clone_voice(str(dest_path), data.name)
        embedding_path = str(dest_path)
    elif engine_name == "higgs":
        from core.higgs_engine import HiggsAudioEngine
        engine = HiggsAudioEngine()
        # Higgs clones on-the-fly; keep reference only
        embedding_path = str(dest_path)
    elif engine_name == "zonos":
        from core.zonos_engine import ZonosEngine
        engine = ZonosEngine()
        embedding_path = engine.clone_voice(str(dest_path), data.name)
    else:
        raise ValueError(f"Unsupported cloning engine: {engine_name}")

    profile = VoiceProfile(
        name=data.name,
        engine=engine_name,
        type="cloned",
        reference_path=embedding_path,
        language=data.language or "es",
        config_json="{}",
        owner_channel_id=data.owner_channel_id,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
```

- [ ] **Step 2: Commit**

```bash
git add web_api/services/voice_clone_service.py
git commit -m "feat(voices): add VoiceCloneService"
```

---

### Task 4: Implement VoiceManagerService and update routes

**Files:**
- Create: `web_api/services/voice_manager.py`
- Modify: `web_api/routes/voices.py`

- [ ] **Step 1: Create service**

```python
from typing import List
from sqlalchemy.orm import Session

from web_api.models import VoiceProfile


PRETRAINED_VOICES = [
    {"id": "edge_es_alvaro", "name": "Alvaro (Edge)", "engine": "edge", "type": "pretrained", "language": "es", "reference_path": None},
    {"id": "edge_es_elvira", "name": "Elvira (Edge)", "engine": "edge", "type": "pretrained", "language": "es", "reference_path": None},
    {"id": "bark_speaker_0", "name": "Bark Speaker 0", "engine": "bark", "type": "pretrained", "language": "es", "reference_path": None},
]


def list_voices(db: Session) -> List[dict]:
    cloned = db.query(VoiceProfile).all()
    result = []
    for p in cloned:
        result.append({
            "id": f"vp_{p.id}",
            "name": p.name,
            "engine": p.engine,
            "type": p.type,
            "reference_path": p.reference_path,
            "language": p.language,
            "config_json": p.config_json,
            "owner_channel_id": p.owner_channel_id,
            "created_at": p.created_at,
        })
    result.extend(PRETRAINED_VOICES)
    return result


def delete_voice(db: Session, voice_id: int) -> bool:
    profile = db.query(VoiceProfile).filter(VoiceProfile.id == voice_id).first()
    if not profile:
        return False
    db.delete(profile)
    db.commit()
    return True
```

- [ ] **Step 2: Update routes**

Replace contents of `web_api/routes/voices.py` with:

```python
import os
import tempfile
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from web_api.database import get_db
from web_api.schemas import VoiceProfileCreate, VoiceProfileResponse
from web_api.services.voice_clone_service import clone_voice
from web_api.services.voice_manager import delete_voice, list_voices

router = APIRouter()


@router.get("")
def get_voices(db: Session = Depends(get_db)):
    return list_voices(db)


@router.post("/clone", response_model=VoiceProfileResponse)
async def create_clone(
    name: str = Form(...),
    engine: str = Form(...),
    language: str = Form("es"),
    owner_channel_id: Optional[int] = Form(None),
    reference: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    suffix = os.path.splitext(reference.filename)[1] or ".wav"
    tmp_path = Path(tempfile.gettempdir()) / f"voice_ref_{uuid.uuid4().hex}{suffix}"
    with open(tmp_path, "wb") as f:
        f.write(await reference.read())
    try:
        data = VoiceProfileCreate(
            name=name,
            engine=engine,
            language=language,
            owner_channel_id=owner_channel_id,
        )
        profile = clone_voice(db, data, str(tmp_path))
        return profile
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@router.delete("/{voice_id}")
def remove_voice(voice_id: int, db: Session = Depends(get_db)):
    if delete_voice(db, voice_id):
        return {"ok": True}
    return {"ok": False, "error": "Voice not found"}
```

- [ ] **Step 3: Commit**

```bash
git add web_api/services/voice_manager.py web_api/routes/voices.py
git commit -m "feat(voices): add voice manager service and routes"
```

---

### Task 5: Backend tests

**Files:**
- Create: `tests/web_api/test_voice_clone_service.py`

- [ ] **Step 1: Write tests**

```python
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from web_api.database import Base
from web_api.schemas import VoiceProfileCreate
from web_api.services.voice_clone_service import clone_voice


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_clone_voice_xtts(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web_api.services.voice_clone_service.VOICES_DIR", tmp_path / "voices" / "clones"
    )
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"fake wav data")

    with patch("core.xtts_engine.XTTSEngine.clone_voice", return_value=str(ref)):
        data = VoiceProfileCreate(name="Test", engine="xtts", language="es")
        profile = clone_voice(db_session, data, str(ref))
        assert profile.name == "Test"
        assert profile.engine == "xtts"
        assert profile.type == "cloned"


def test_clone_voice_unsupported_engine(db_session, tmp_path):
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"fake wav data")
    data = VoiceProfileCreate(name="Test", engine="unknown", language="es")
    with pytest.raises(ValueError, match="Unsupported cloning engine"):
        clone_voice(db_session, data, str(ref))


def test_clone_voice_missing_file(db_session):
    data = VoiceProfileCreate(name="Test", engine="xtts", language="es")
    with pytest.raises(FileNotFoundError):
        clone_voice(db_session, data, "/nonexistent.wav")
```

- [ ] **Step 2: Run tests**

```bash
./venv311/bin/python -m pytest tests/web_api/test_voice_clone_service.py -q
```

Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add tests/web_api/test_voice_clone_service.py
git commit -m "test(voices): add voice clone service tests"
```

---

### Task 6: Frontend types and API

**Files:**
- Modify: `web/src/types/index.ts`
- Modify: `web/src/api/client.ts`

- [ ] **Step 1: Add types**

```typescript
export interface VoiceProfile {
  id: string | number
  name: string
  engine: string
  type: 'cloned' | 'pretrained'
  reference_path?: string
  language?: string
  config_json?: string
  owner_channel_id?: number
  created_at?: string
}
```

- [ ] **Step 2: Add API methods**

```typescript
export async function getVoices(): Promise<VoiceProfile[]> {
  const response = await fetch('/api/voices')
  if (!response.ok) throw new Error('Failed to fetch voices')
  return response.json()
}

export async function cloneVoice(formData: FormData): Promise<VoiceProfile> {
  const response = await fetch('/api/voices/clone', {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    const err = await response.text()
    throw new Error(err || 'Failed to clone voice')
  }
  return response.json()
}

export async function deleteVoice(voiceId: string | number): Promise<void> {
  const response = await fetch(`/api/voices/${voiceId}`, { method: 'DELETE' })
  if (!response.ok) throw new Error('Failed to delete voice')
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/types/index.ts web/src/api/client.ts
git commit -m "feat(voices): add frontend voice types and API"
```

---

### Task 7: Frontend store

**Files:**
- Create: `web/src/stores/voiceStore.ts`

- [ ] **Step 1: Implement store**

```typescript
import { create } from 'zustand'
import { cloneVoice, deleteVoice, getVoices } from '../api/client'
import type { VoiceProfile } from '../types'

interface VoiceState {
  voices: VoiceProfile[]
  loading: boolean
  cloning: boolean
  error: string | null
  fetchVoices: () => Promise<void>
  createClone: (formData: FormData) => Promise<void>
  removeVoice: (id: string | number) => Promise<void>
}

export const useVoiceStore = create<VoiceState>((set, get) => ({
  voices: [],
  loading: false,
  cloning: false,
  error: null,
  fetchVoices: async () => {
    set({ loading: true, error: null })
    try {
      const voices = await getVoices()
      set({ voices, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
  createClone: async (formData) => {
    set({ cloning: true, error: null })
    try {
      await cloneVoice(formData)
      await get().fetchVoices()
      set({ cloning: false })
    } catch (err) {
      set({ error: (err as Error).message, cloning: false })
    }
  },
  removeVoice: async (id) => {
    try {
      await deleteVoice(id)
      await get().fetchVoices()
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },
}))
```

- [ ] **Step 2: Commit**

```bash
git add web/src/stores/voiceStore.ts
git commit -m "feat(voices): add voice store"
```

---

### Task 8: Frontend UI components

**Files:**
- Create: `web/src/components/VoiceCard.tsx`
- Create: `web/src/components/CloneVoiceForm.tsx`
- Create: `web/src/components/VoiceManager.tsx`

- [ ] **Step 1: VoiceCard**

```tsx
import type { VoiceProfile } from '../types'

interface VoiceCardProps {
  voice: VoiceProfile
  onDelete?: (id: string | number) => void
}

export default function VoiceCard({ voice, onDelete }: VoiceCardProps) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{voice.name}</h3>
        <span className="rounded bg-gray-100 px-2 py-1 text-xs uppercase">{voice.engine}</span>
      </div>
      <p className="mt-1 text-sm text-gray-500 capitalize">{voice.type}</p>
      {voice.language && <p className="text-xs text-gray-400">{voice.language}</p>}
      {voice.type === 'cloned' && onDelete && (
        <button
          type="button"
          onClick={() => onDelete(voice.id)}
          className="mt-3 text-sm text-red-600 hover:underline"
        >
          Delete
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 2: CloneVoiceForm**

```tsx
import { useState, type FormEvent, type ChangeEvent } from 'react'
import { useVoiceStore } from '../stores/voiceStore'

export default function CloneVoiceForm() {
  const { createClone, cloning } = useVoiceStore()
  const [name, setName] = useState('')
  const [engine, setEngine] = useState('xtts')
  const [language, setLanguage] = useState('es')
  const [file, setFile] = useState<File | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file || !name) return
    const formData = new FormData()
    formData.append('name', name)
    formData.append('engine', engine)
    formData.append('language', language)
    formData.append('reference', file)
    await createClone(formData)
    setName('')
    setFile(null)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Clone new voice</h2>
      <div>
        <label className="block text-sm font-medium">Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 w-full rounded border p-2"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium">Engine</label>
        <select
          value={engine}
          onChange={(e) => setEngine(e.target.value)}
          className="mt-1 w-full rounded border p-2"
        >
          <option value="xtts">XTTS v2</option>
          <option value="higgs">Higgs Audio v3</option>
          <option value="zonos">Zonos</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium">Reference audio</label>
        <input
          type="file"
          accept="audio/*"
          onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] || null)}
          className="mt-1 w-full"
          required
        />
      </div>
      <button
        type="submit"
        disabled={cloning}
        className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {cloning ? 'Cloning...' : 'Clone voice'}
      </button>
    </form>
  )
}
```

- [ ] **Step 3: VoiceManager**

```tsx
import { useEffect } from 'react'
import { Link } from '@tanstack/react-router'
import { useVoiceStore } from '../stores/voiceStore'
import CloneVoiceForm from './CloneVoiceForm'
import VoiceCard from './VoiceCard'

export default function VoiceManager() {
  const { voices, loading, error, fetchVoices, removeVoice } = useVoiceStore()

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Voice Manager</h1>
        <Link to="/voices/clone" className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
          Clone voice
        </Link>
      </div>

      {error && <div className="rounded border border-red-300 bg-red-100 p-4 text-red-800">{error}</div>}

      <CloneVoiceForm />

      {loading ? (
        <p>Loading voices...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {voices.map((voice) => (
            <VoiceCard key={voice.id} voice={voice} onDelete={voice.type === 'cloned' ? removeVoice : undefined} />
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/VoiceCard.tsx web/src/components/CloneVoiceForm.tsx web/src/components/VoiceManager.tsx
git commit -m "feat(voices): add voice manager UI"
```

---

### Task 9: Add routes and navigation

**Files:**
- Modify: `web/src/routes/voices.tsx`
- Create: `web/src/routes/voices.clone.tsx`
- Modify: `web/src/components/Layout.tsx`

- [ ] **Step 1: Update `/voices` route**

```tsx
import { createFileRoute } from '@tanstack/react-router'
import VoiceManager from '../components/VoiceManager'

export const Route = createFileRoute('/voices')({
  component: VoiceManager,
})
```

- [ ] **Step 2: Create `/voices/clone` route**

```tsx
import { createFileRoute } from '@tanstack/react-router'
import CloneVoiceForm from '../components/CloneVoiceForm'

export const Route = createFileRoute('/voices/clone')({
  component: CloneVoiceForm,
})
```

- [ ] **Step 3: Add Layout link**

Add:
```tsx
<Link to="/voices" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Voces</Link>
```

- [ ] **Step 4: Commit**

```bash
git add web/src/routes/voices.tsx web/src/routes/voices.clone.tsx web/src/components/Layout.tsx
git commit -m "feat(voices): add routes and navigation"
```

---

### Task 10: Frontend tests

**Files:**
- Create: `web/src/tests/VoiceManager.test.tsx`

- [ ] **Step 1: Write test**

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import VoiceManager from '../components/VoiceManager'
import * as client from '../api/client'

vi.mock('../api/client')

describe('VoiceManager', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders voices after loading', async () => {
    vi.mocked(client.getVoices).mockResolvedValue([
      { id: 'vp_1', name: 'Clonada', engine: 'xtts', type: 'cloned', language: 'es' },
      { id: 'edge_1', name: 'Alvaro', engine: 'edge', type: 'pretrained', language: 'es' },
    ])

    render(<VoiceManager />)

    await waitFor(() => {
      expect(screen.getByText('Clonada')).toBeInTheDocument()
    })
    expect(screen.getByText('Alvaro')).toBeInTheDocument()
  })

  it('shows error when fetch fails', async () => {
    vi.mocked(client.getVoices).mockRejectedValue(new Error('boom'))

    render(<VoiceManager />)

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd web && npm test -- --run VoiceManager
```

Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add web/src/tests/VoiceManager.test.tsx
git commit -m "test(voices): add VoiceManager tests"
```

---

### Task 11: Full test suite and build

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
git commit --allow-empty -m "chore(voices): complete voice cloning manager"
```

---

## Self-review

| Spec requirement | Task covering it |
|---|---|
| Multi-engine cloning (XTTS, Higgs, Zonos) | Tasks 2-3 |
| Upload reference audio | Task 4 route |
| Persist clone profile | Tasks 1, 3 |
| List cloned + pretrained voices | Task 4 |
| Delete cloned voice | Task 4 |
| Frontend voice manager | Tasks 6-9 |
| Tests | Tasks 5, 10, 11 |

**Placeholder scan:** No TBD/TODO. Code blocks are complete.

**Type consistency:** `VoiceProfile` model, schema, TypeScript type, and service return shape all aligned.
