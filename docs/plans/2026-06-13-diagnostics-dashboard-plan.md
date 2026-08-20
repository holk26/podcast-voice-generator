# Diagnostics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend diagnostics service and a frontend dashboard that show the health of GPU, CUDA, Ollama, TTS engines, disk space, worker, and web assets.

**Architecture:** A stateless `DiagnosticsService` runs checks in parallel and returns typed records. Results are exposed via FastAPI endpoints and consumed by a React dashboard using a Zustand store. Checks are read-only and safe to run repeatedly.

**Tech Stack:** FastAPI, SQLAlchemy, PyTorch, `urllib`, React 18, TanStack Router, Zustand, Tailwind CSS.

---

## File Structure

| File | Responsibility |
|---|---|
| `web_api/services/diagnostics_service.py` | Run all system checks and return typed results |
| `web_api/routes/diagnostics.py` | FastAPI endpoints: `GET /api/diagnostics`, `GET /api/diagnostics/report` |
| `web_api/models.py` (modify) | Add `DiagnosticLog` model |
| `web_api/schemas.py` (modify) | Add `DiagnosticCheckResult`, `DiagnosticsReport` schemas |
| `web_api/main.py` (modify) | Register diagnostics router |
| `web/src/types/index.ts` (modify) | Add `DiagnosticCheck`, `DiagnosticsReport` types |
| `web/src/api/client.ts` (modify) | Add `getDiagnostics()` and `getDiagnosticsReport()` |
| `web/src/stores/diagnosticsStore.ts` | Fetch and cache diagnostics state |
| `web/src/components/DiagnosticsDashboard.tsx` | Dashboard UI |
| `web/src/components/DiagnosticCard.tsx` | Single check card |
| `web/src/routes/system.tsx` | Route component for `/system` |
| `web/src/components/Layout.tsx` (modify) | Add `/system` nav link |
| `tests/web_api/test_diagnostics_service.py` | Backend unit tests |
| `web/src/tests/DiagnosticsDashboard.test.tsx` | Frontend component tests |

---

### Task 1: Add diagnostics types and dataclass

**Files:**
- Create: `web_api/services/diagnostics_service.py`

- [ ] **Step 1: Define `DiagnosticStatus` and `DiagnosticCheckResult`**

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DiagnosticStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DiagnosticCheckResult:
    component: str
    status: DiagnosticStatus
    detail: str
    checked_at: datetime
```

- [ ] **Step 2: Commit**

```bash
git add web_api/services/diagnostics_service.py
git commit -m "feat(diagnostics): add base result datatypes"
```

---

### Task 2: Implement individual checks

**Files:**
- Modify: `web_api/services/diagnostics_service.py`

- [ ] **Step 1: Add helper functions for GPU, CUDA, Ollama, disk, worker, web**

```python
import os
import shutil
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
VOICES_DIR = BASE_DIR / "voices"
DATA_DIR = BASE_DIR / "data"


def _check_gpu() -> DiagnosticCheckResult:
    try:
        import torch

        if not torch.cuda.is_available():
            return DiagnosticCheckResult(
                component="gpu",
                status=DiagnosticStatus.ERROR,
                detail="CUDA is not available. NVIDIA GPU not detected or drivers missing.",
                checked_at=datetime.utcnow(),
            )
        free_bytes = torch.cuda.mem_get_info()[0]
        free_gb = free_bytes / (1024**3)
        name = torch.cuda.get_device_name(0)
        if free_gb < 2:
            return DiagnosticCheckResult(
                component="gpu",
                status=DiagnosticStatus.WARNING,
                detail=f"{name} detected but only {free_gb:.1f} GB VRAM free.",
                checked_at=datetime.utcnow(),
            )
        return DiagnosticCheckResult(
            component="gpu",
            status=DiagnosticStatus.OK,
            detail=f"{name} detected with {free_gb:.1f} GB VRAM free.",
            checked_at=datetime.utcnow(),
        )
    except Exception as e:
        return DiagnosticCheckResult(
            component="gpu",
            status=DiagnosticStatus.ERROR,
            detail=f"Could not query GPU: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_ollama() -> DiagnosticCheckResult:
    from web_api.config import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL

    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="ignore")
            data = json.loads(body)
            models = [m.get("name", "") for m in data.get("models", [])]
            if OLLAMA_DEFAULT_MODEL in models:
                return DiagnosticCheckResult(
                    component="ollama",
                    status=DiagnosticStatus.OK,
                    detail=f"Ollama running; model {OLLAMA_DEFAULT_MODEL} available.",
                    checked_at=datetime.utcnow(),
                )
            return DiagnosticCheckResult(
                component="ollama",
                status=DiagnosticStatus.WARNING,
                detail=f"Ollama running but model {OLLAMA_DEFAULT_MODEL} not found. Run: ollama pull {OLLAMA_DEFAULT_MODEL}",
                checked_at=datetime.utcnow(),
            )
    except Exception as e:
        return DiagnosticCheckResult(
            component="ollama",
            status=DiagnosticStatus.ERROR,
            detail=f"Ollama not reachable: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_disk() -> DiagnosticCheckResult:
    paths = {
        "data": DATA_DIR,
        "output": OUTPUT_DIR,
        "voices": VOICES_DIR,
    }
    min_gb = 5
    warnings = []
    for label, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        free_gb = shutil.disk_usage(path).free / (1024**3)
        if free_gb < min_gb:
            warnings.append(f"{label}: {free_gb:.1f} GB free")
    if warnings:
        return DiagnosticCheckResult(
            component="disk",
            status=DiagnosticStatus.WARNING,
            detail="; ".join(warnings),
            checked_at=datetime.utcnow(),
        )
    return DiagnosticCheckResult(
        component="disk",
        status=DiagnosticStatus.OK,
        detail="All directories have >= 5 GB free.",
        checked_at=datetime.utcnow(),
    )


def _check_worker() -> DiagnosticCheckResult:
    from web_api.config import WORKER_PORT

    url = f"http://127.0.0.1:{WORKER_PORT}/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                return DiagnosticCheckResult(
                    component="worker",
                    status=DiagnosticStatus.OK,
                    detail=f"Worker responds on port {WORKER_PORT}.",
                    checked_at=datetime.utcnow(),
                )
            return DiagnosticCheckResult(
                component="worker",
                status=DiagnosticStatus.ERROR,
                detail=f"Worker returned status {response.status}.",
                checked_at=datetime.utcnow(),
            )
    except Exception as e:
        return DiagnosticCheckResult(
            component="worker",
            status=DiagnosticStatus.ERROR,
            detail=f"Worker not reachable: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_web_assets() -> DiagnosticCheckResult:
    dist_dir = BASE_DIR / "web" / "dist"
    if dist_dir.exists() and any(dist_dir.iterdir()):
        return DiagnosticCheckResult(
            component="web_assets",
            status=DiagnosticStatus.OK,
            detail="Production build found in web/dist.",
            checked_at=datetime.utcnow(),
        )
    from web_api.config import WEB_PORT

    url = f"http://127.0.0.1:{WEB_PORT}"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                return DiagnosticCheckResult(
                    component="web_assets",
                    status=DiagnosticStatus.OK,
                    detail=f"Dev server responds on port {WEB_PORT}.",
                    checked_at=datetime.utcnow(),
                )
            return DiagnosticCheckResult(
                component="web_assets",
                status=DiagnosticStatus.WARNING,
                detail=f"Web responded with status {response.status}.",
                checked_at=datetime.utcnow(),
            )
    except Exception as e:
        return DiagnosticCheckResult(
            component="web_assets",
            status=DiagnosticStatus.WARNING,
            detail=f"No build found and dev server not reachable: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_tts_engines() -> DiagnosticCheckResult:
    engines = []
    warnings = []
    try:
        from core.xtts_engine import XTTS_AVAILABLE
        engines.append("xtts")
    except Exception as e:
        warnings.append(f"xtts not importable: {e}")
    try:
        from core.higgs_engine import HiggsEngine
        engines.append("higgs")
    except Exception as e:
        warnings.append(f"higgs not importable: {e}")
    try:
        from zonos.speaker_cloning import load_model
        engines.append("zonos")
    except Exception as e:
        warnings.append(f"zonos not importable: {e}")

    if not engines:
        return DiagnosticCheckResult(
            component="tts_engines",
            status=DiagnosticStatus.ERROR,
            detail="No TTS engine available: " + "; ".join(warnings),
            checked_at=datetime.utcnow(),
        )
    if warnings:
        return DiagnosticCheckResult(
            component="tts_engines",
            status=DiagnosticStatus.WARNING,
            detail=f"Available: {', '.join(engines)}. Missing: " + "; ".join(warnings),
            checked_at=datetime.utcnow(),
        )
    return DiagnosticCheckResult(
        component="tts_engines",
        status=DiagnosticStatus.OK,
        detail=f"Available engines: {', '.join(engines)}.",
        checked_at=datetime.utcnow(),
    )
```

- [ ] **Step 2: Add top-level `run_diagnostics()` function**

```python
import json
import concurrent.futures


def run_diagnostics() -> list[DiagnosticCheckResult]:
    checks = [
        _check_gpu,
        _check_ollama,
        _check_disk,
        _check_worker,
        _check_web_assets,
        _check_tts_engines,
    ]
    results: list[DiagnosticCheckResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = {executor.submit(fn): i for i, fn in enumerate(checks)}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append(
                    DiagnosticCheckResult(
                        component="unknown",
                        status=DiagnosticStatus.ERROR,
                        detail=f"Check crashed: {e}",
                        checked_at=datetime.utcnow(),
                    )
                )
    order = ["gpu", "ollama", "disk", "worker", "web_assets", "tts_engines"]
    results.sort(key=lambda r: order.index(r.component) if r.component in order else 99)
    return results
```

- [ ] **Step 3: Commit**

```bash
git add web_api/services/diagnostics_service.py
git commit -m "feat(diagnostics): implement all checks"
```

---

### Task 3: Add database model and schemas

**Files:**
- Modify: `web_api/models.py`
- Modify: `web_api/schemas.py`

- [ ] **Step 1: Add `DiagnosticLog` model**

```python
class DiagnosticLog(Base):
    __tablename__ = "diagnostic_logs"

    id = Column(Integer, primary_key=True, index=True)
    component = Column(String, nullable=False)
    status = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Add Pydantic schemas**

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DiagnosticCheckResult(BaseModel):
    component: str
    status: str  # ok | warning | error
    detail: str
    checked_at: datetime

    class Config:
        from_attributes = True


class DiagnosticsReport(BaseModel):
    checks: list[DiagnosticCheckResult]
    overall: str
    generated_at: datetime
```

- [ ] **Step 3: Commit**

```bash
git add web_api/models.py web_api/schemas.py
git commit -m "feat(diagnostics): add DiagnosticLog model and schemas"
```

---

### Task 4: Add diagnostics router

**Files:**
- Create: `web_api/routes/diagnostics.py`
- Modify: `web_api/main.py`

- [ ] **Step 1: Create router**

```python
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from web_api.database import get_db
from web_api.models import DiagnosticLog
from web_api.schemas import DiagnosticCheckResult, DiagnosticsReport
from web_api.services.diagnostics_service import run_diagnostics

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("", response_model=DiagnosticsReport)
def get_diagnostics(db: Session = Depends(get_db)):
    checks = run_diagnostics()
    for check in checks:
        db.add(
            DiagnosticLog(
                component=check.component,
                status=check.status,
                detail=check.detail,
                checked_at=check.checked_at,
            )
        )
    db.commit()

    overall = "ok"
    if any(c.status == "error" for c in checks):
        overall = "error"
    elif any(c.status == "warning" for c in checks):
        overall = "warning"

    return DiagnosticsReport(checks=checks, overall=overall, generated_at=datetime.utcnow())


@router.get("/report")
def download_report():
    checks = run_diagnostics()
    overall = "ok"
    if any(c.status == "error" for c in checks):
        overall = "error"
    elif any(c.status == "warning" for c in checks):
        overall = "warning"
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "overall": overall,
        "checks": [c.__dict__ for c in checks],
    }
```

- [ ] **Step 2: Register router in `web_api/main.py`**

Add import:
```python
from web_api.routes import voices, tts, episodes, channels, llm, diagnostics
```

Add:
```python
app.include_router(diagnostics.router, prefix="/api/diagnostics", tags=["diagnostics"])
```

- [ ] **Step 3: Commit**

```bash
git add web_api/routes/diagnostics.py web_api/main.py
git commit -m "feat(diagnostics): add diagnostics endpoints"
```

---

### Task 5: Backend tests

**Files:**
- Create: `tests/web_api/test_diagnostics_service.py`

- [ ] **Step 1: Write tests**

```python
from unittest.mock import patch, MagicMock
from web_api.services.diagnostics_service import (
    DiagnosticStatus,
    _check_disk,
    _check_worker,
    _check_web_assets,
    run_diagnostics,
)


def test_check_disk_returns_ok_when_space_available(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "web_api.services.diagnostics_service.DATA_DIR", tmp_path / "data"
    )
    monkeypatch.setattr(
        "web_api.services.diagnostics_service.OUTPUT_DIR", tmp_path / "output"
    )
    monkeypatch.setattr(
        "web_api.services.diagnostics_service.VOICES_DIR", tmp_path / "voices"
    )
    result = _check_disk()
    assert result.component == "disk"
    assert result.status == DiagnosticStatus.OK


def test_check_worker_ok():
    with patch("urllib.request.urlopen") as mock_open:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_open.return_value.__enter__.return_value = mock_response
        result = _check_worker()
        assert result.component == "worker"
        assert result.status == DiagnosticStatus.OK


def test_check_web_assets_finds_dist(tmp_path, monkeypatch):
    dist = tmp_path / "web" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")
    monkeypatch.setattr(
        "web_api.services.diagnostics_service.BASE_DIR", tmp_path
    )
    result = _check_web_assets()
    assert result.status == DiagnosticStatus.OK


def test_run_diagnostics_returns_all_checks():
    results = run_diagnostics()
    components = {r.component for r in results}
    assert components == {"gpu", "ollama", "disk", "worker", "web_assets", "tts_engines"}
```

- [ ] **Step 2: Run tests**

```bash
./venv311/bin/python -m pytest tests/web_api/test_diagnostics_service.py -q
```

Expected: 4 passed

- [ ] **Step 3: Commit**

```bash
git add tests/web_api/test_diagnostics_service.py
git commit -m "test(diagnostics): add diagnostics service tests"
```

---

### Task 6: Add frontend types and API client

**Files:**
- Modify: `web/src/types/index.ts`
- Modify: `web/src/api/client.ts`

- [ ] **Step 1: Add types**

```typescript
export interface DiagnosticCheck {
  component: string
  status: 'ok' | 'warning' | 'error'
  detail: string
  checked_at: string
}

export interface DiagnosticsReport {
  checks: DiagnosticCheck[]
  overall: 'ok' | 'warning' | 'error'
  generated_at: string
}
```

- [ ] **Step 2: Add API methods**

```typescript
export async function getDiagnostics(): Promise<DiagnosticsReport> {
  const response = await fetch('/api/diagnostics')
  if (!response.ok) throw new Error('Failed to fetch diagnostics')
  return response.json()
}

export async function getDiagnosticsReport(): Promise<Record<string, unknown>> {
  const response = await fetch('/api/diagnostics/report')
  if (!response.ok) throw new Error('Failed to fetch diagnostics report')
  return response.json()
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/types/index.ts web/src/api/client.ts
git commit -m "feat(diagnostics): add frontend types and API methods"
```

---

### Task 7: Create diagnostics store

**Files:**
- Create: `web/src/stores/diagnosticsStore.ts`

- [ ] **Step 1: Implement store**

```typescript
import { create } from 'zustand'
import { getDiagnostics } from '../api/client'
import type { DiagnosticsReport } from '../types'

interface DiagnosticsState {
  report: DiagnosticsReport | null
  loading: boolean
  error: string | null
  fetch: () => Promise<void>
  refetch: () => Promise<void>
}

export const useDiagnosticsStore = create<DiagnosticsState>((set) => ({
  report: null,
  loading: false,
  error: null,
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const report = await getDiagnostics()
      set({ report, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
  refetch: async () => {
    set({ loading: true, error: null })
    try {
      const report = await getDiagnostics()
      set({ report, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
}))
```

- [ ] **Step 2: Commit**

```bash
git add web/src/stores/diagnosticsStore.ts
git commit -m "feat(diagnostics): add diagnostics store"
```

---

### Task 8: Create dashboard components

**Files:**
- Create: `web/src/components/DiagnosticCard.tsx`
- Create: `web/src/components/DiagnosticsDashboard.tsx`

- [ ] **Step 1: Create `DiagnosticCard.tsx`**

```tsx
import type { DiagnosticCheck } from '../types'

const statusColor: Record<string, string> = {
  ok: 'bg-green-100 text-green-800 border-green-300',
  warning: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  error: 'bg-red-100 text-red-800 border-red-300',
}

const statusDot: Record<string, string> = {
  ok: 'bg-green-500',
  warning: 'bg-yellow-500',
  error: 'bg-red-500',
}

interface DiagnosticCardProps {
  check: DiagnosticCheck
}

export default function DiagnosticCard({ check }: DiagnosticCardProps) {
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${statusColor[check.status]}`}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold capitalize">{check.component}</h3>
        <span className={`h-3 w-3 rounded-full ${statusDot[check.status]}`} aria-hidden="true" />
      </div>
      <p className="mt-2 text-sm">{check.detail}</p>
      <p className="mt-1 text-xs opacity-75">
        {new Date(check.checked_at).toLocaleString()}
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Create `DiagnosticsDashboard.tsx`**

```tsx
import { useEffect } from 'react'
import { useDiagnosticsStore } from '../stores/diagnosticsStore'
import DiagnosticCard from './DiagnosticCard'

const overallColor: Record<string, string> = {
  ok: 'text-green-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
}

export default function DiagnosticsDashboard() {
  const { report, loading, error, fetch } = useDiagnosticsStore()

  useEffect(() => {
    fetch()
  }, [fetch])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">System Diagnostics</h1>
        <button
          type="button"
          onClick={() => fetch()}
          disabled={loading}
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Checking...' : 'Re-check'}
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-300 bg-red-100 p-4 text-red-800">
          {error}
        </div>
      )}

      {report && (
        <>
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <p className="text-lg font-medium">
              Overall status:{" "}
              <span className={`font-bold uppercase ${overallColor[report.overall]}`}>
                {report.overall}
              </span>
            </p>
            <p className="text-sm text-gray-500">
              Generated at {new Date(report.generated_at).toLocaleString()}
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {report.checks.map((check) => (
              <DiagnosticCard key={check.component} check={check} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/DiagnosticCard.tsx web/src/components/DiagnosticsDashboard.tsx
git commit -m "feat(diagnostics): add dashboard UI components"
```

---

### Task 9: Add `/system` route and navigation

**Files:**
- Create: `web/src/routes/system.tsx`
- Modify: `web/src/components/Layout.tsx`

- [ ] **Step 1: Create route**

```tsx
import { createFileRoute } from '@tanstack/react-router'
import DiagnosticsDashboard from '../components/DiagnosticsDashboard'

export const Route = createFileRoute('/system')({
  component: DiagnosticsDashboard,
})
```

- [ ] **Step 2: Add nav link**

Add inside `<nav>` in `web/src/components/Layout.tsx`:

```tsx
<Link to="/system" className="block p-2 rounded hover:bg-gray-800" activeProps={{ className: 'bg-gray-800' }}>Sistema</Link>
```

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/system.tsx web/src/components/Layout.tsx
git commit -m "feat(diagnostics): add /system route and navigation"
```

---

### Task 10: Frontend tests

**Files:**
- Create: `web/src/tests/DiagnosticsDashboard.test.tsx`

- [ ] **Step 1: Write test**

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DiagnosticsDashboard from '../components/DiagnosticsDashboard'
import * as client from '../api/client'

vi.mock('../api/client')

describe('DiagnosticsDashboard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders checks after loading', async () => {
    vi.mocked(client.getDiagnostics).mockResolvedValue({
      overall: 'ok',
      generated_at: new Date().toISOString(),
      checks: [
        { component: 'gpu', status: 'ok', detail: 'RTX 5060 OK', checked_at: new Date().toISOString() },
        { component: 'ollama', status: 'ok', detail: 'Model ready', checked_at: new Date().toISOString() },
      ],
    })

    render(<DiagnosticsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('RTX 5060 OK')).toBeInTheDocument()
    })
    expect(screen.getByText('gpu')).toBeInTheDocument()
  })

  it('shows error message when fetch fails', async () => {
    vi.mocked(client.getDiagnostics).mockRejectedValue(new Error('Network error'))

    render(<DiagnosticsDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('refetches when clicking Re-check', async () => {
    vi.mocked(client.getDiagnostics).mockResolvedValue({
      overall: 'ok',
      generated_at: new Date().toISOString(),
      checks: [],
    })

    render(<DiagnosticsDashboard />)
    const button = await screen.findByRole('button', { name: /Re-check/i })
    fireEvent.click(button)

    await waitFor(() => {
      expect(client.getDiagnostics).toHaveBeenCalledTimes(2)
    })
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd web && npm test -- --run DiagnosticsDashboard
```

Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
git add web/src/tests/DiagnosticsDashboard.test.tsx
git commit -m "test(diagnostics): add dashboard component tests"
```

---

### Task 11: Full test suite and build

- [ ] **Step 1: Run backend tests**

```bash
./venv311/bin/python -m pytest tests/web_api -q
```

Expected: all pass

- [ ] **Step 2: Run frontend tests**

```bash
cd web && npm test -- --run
```

Expected: all pass

- [ ] **Step 3: Build frontend**

```bash
cd web && npm run build
```

Expected: success

- [ ] **Step 4: Commit if all green**

```bash
git commit --allow-empty -m "chore(diagnostics): complete diagnostics dashboard"
```

---

## Self-review

| Spec requirement | Task covering it |
|---|---|
| GPU check | Task 2 `_check_gpu` |
| CUDA compatibility check | Task 2 `_check_gpu` |
| Ollama check | Task 2 `_check_ollama` |
| TTS engines check | Task 2 `_check_tts_engines` |
| Disk space check | Task 2 `_check_disk` |
| Worker health check | Task 2 `_check_worker` |
| Web assets check | Task 2 `_check_web_assets` |
| `/api/diagnostics` endpoint | Task 4 |
| Downloadable report | Task 4 `/report` |
| Frontend dashboard | Tasks 7-9 |
| Re-check button | Task 8 |
| Backend tests | Task 5 |
| Frontend tests | Task 10 |

**Placeholder scan:** No TBD/TODO placeholders. Every code block is complete.

**Type consistency:** `DiagnosticCheckResult` dataclass matches `DiagnosticCheckResult` schema and `DiagnosticCheck` TypeScript type. Status values are `"ok" | "warning" | "error"` everywhere.
