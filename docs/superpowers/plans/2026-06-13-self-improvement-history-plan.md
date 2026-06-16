# Self-Improvement History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic self-improvement per channel with a full audit history of config changes, user-visible insights, and one-click rollback.

**Architecture:** `AutoImprovementService` analyzes completed `ProductionRun` metrics, decides config adjustments, and writes them to `ChannelConfigHistory`. The frontend shows an improvement timeline and lets users revert any change. Changes are limited to channel config/prompts, never code.

**Tech Stack:** FastAPI, SQLAlchemy, CrewAI (for insight summarization), React, Zustand.

---

## File Structure

| File | Responsibility |
|---|---|
| `web_api/models.py` (modify) | Add `ChannelConfigHistory` |
| `web_api/schemas.py` (modify) | Add history and insight schemas |
| `web_api/services/auto_improvement_service.py` | Analyze runs and apply config changes |
| `web_api/routes/channels.py` (modify) | Add history and insights endpoints |
| `web/src/types/index.ts` (modify) | Add history types |
| `web/src/api/client.ts` (modify) | Add history API methods |
| `web/src/stores/improvementStore.ts` | History + insights state |
| `web/src/components/ImprovementTimeline.tsx` | History UI |
| `web/src/components/ChannelInsights.tsx` | Insights cards |
| `web/src/routes/channels.$id.studio.improvements.tsx` | `/channels/$id/studio/improvements` route |
| `tests/web_api/test_auto_improvement_service.py` | Backend tests |
| `web/src/tests/ImprovementTimeline.test.tsx` | Frontend tests |

---

### Task 1: Add ChannelConfigHistory model and schemas

**Files:**
- Modify: `web_api/models.py`
- Modify: `web_api/schemas.py`

- [ ] **Step 1: Add model**

```python
class ChannelConfigHistory(Base):
    __tablename__ = "channel_config_history"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    change_type = Column(String, nullable=False)  # prompt | voice_cast | mix | plan_style
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    production_run_id = Column(Integer, ForeignKey("production_runs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Add schemas**

```python
class ChannelConfigHistoryResponse(BaseModel):
    id: int
    channel_id: int
    change_type: str
    old_value: Optional[str]
    new_value: Optional[str]
    reason: Optional[str]
    production_run_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelInsight(BaseModel):
    id: str
    title: str
    description: str
    confidence: float
    based_on_runs: int
```

- [ ] **Step 3: Commit**

```bash
git add web_api/models.py web_api/schemas.py
git commit -m "feat(improvement): add ChannelConfigHistory model and schemas"
```

---

### Task 2: Implement AutoImprovementService

**Files:**
- Create: `web_api/services/auto_improvement_service.py`

- [ ] **Step 1: Implement analyzer**

```python
import json
from typing import Optional

from sqlalchemy.orm import Session

from web_api.models import Channel, ChannelConfigHistory, ProductionRun


def _get_completed_runs(db: Session, channel_id: int, limit: int = 20) -> list[ProductionRun]:
    return (
        db.query(ProductionRun)
        .filter(ProductionRun.channel_id == channel_id)
        .filter(ProductionRun.status.in_(["approved", "completed"]))
        .order_by(ProductionRun.created_at.desc())
        .limit(limit)
        .all()
    )


def _compute_average_score(runs: list[ProductionRun]) -> Optional[float]:
    scores = [r.quality_score for r in runs if r.quality_score is not None]
    if not scores:
        return None
    return sum(scores) / len(scores)


def _suggest_voice_cast_change(runs: list[ProductionRun]) -> Optional[dict]:
    # Group runs by voice cast and compare scores
    groups: dict[str, list[float]] = {}
    for run in runs:
        if not run.config_json:
            continue
        config = json.loads(run.config_json)
        cast = config.get("voice_cast", {})
        narrator = cast.get("narrador")
        if not narrator or run.quality_score is None:
            continue
        groups.setdefault(narrator, []).append(run.quality_score)

    if len(groups) < 2:
        return None

    averages = {k: sum(v) / len(v) for k, v in groups.items()}
    best = max(averages, key=averages.get)
    return {
        "change_type": "voice_cast",
        "new_value": json.dumps({"narrador": best}),
        "reason": f"Voice '{best}' has highest average score ({averages[best]:.2f}).",
    }


def _suggest_mix_change(runs: list[ProductionRun]) -> Optional[dict]:
    low_score_runs = [r for r in runs if r.quality_score is not None and r.quality_score < 0.6]
    if not low_score_runs:
        return None
    feedback_keywords = ["música", "tap", "bajo", "alto", "mezcla"]
    mentions = sum(1 for r in low_score_runs if r.feedback and any(k in r.feedback.lower() for k in feedback_keywords))
    if mentions >= 2:
        return {
            "change_type": "mix",
            "new_value": json.dumps({"music_volume": 0.15, "normalize": True}),
            "reason": f"{mentions} low-score runs mention mix issues; lowering music volume.",
        }
    return None


def apply_improvements(db: Session, channel_id: int) -> list[ChannelConfigHistory]:
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise ValueError("Channel not found")

    runs = _get_completed_runs(db, channel_id)
    if len(runs) < 3:
        return []

    changes = []
    for suggest in [_suggest_voice_cast_change, _suggest_mix_change]:
        suggestion = suggest(runs)
        if suggestion:
            old_value = channel.voice_cast_json if suggestion["change_type"] == "voice_cast" else None
            history = ChannelConfigHistory(
                channel_id=channel_id,
                change_type=suggestion["change_type"],
                old_value=old_value,
                new_value=suggestion["new_value"],
                reason=suggestion["reason"],
                production_run_id=runs[0].id,
            )
            db.add(history)
            if suggestion["change_type"] == "voice_cast":
                channel.voice_cast_json = suggestion["new_value"]
            changes.append(history)

    if changes:
        db.commit()
    return changes


def get_insights(db: Session, channel_id: int) -> list[dict]:
    runs = _get_completed_runs(db, channel_id)
    insights = []
    avg = _compute_average_score(runs)
    if avg is not None:
        insights.append({
            "id": f"{channel_id}_avg_score",
            "title": "Average quality score",
            "description": f"Last {len(runs)} runs average {avg:.2f}.",
            "confidence": 0.9,
            "based_on_runs": len(runs),
        })

    suggestion = _suggest_voice_cast_change(runs)
    if suggestion:
        insights.append({
            "id": f"{channel_id}_voice",
            "title": "Best performing voice",
            "description": suggestion["reason"],
            "confidence": 0.75,
            "based_on_runs": len(runs),
        })

    return insights
```

- [ ] **Step 2: Commit**

```bash
git add web_api/services/auto_improvement_service.py
git commit -m "feat(improvement): add AutoImprovementService"
```

---

### Task 3: Add history endpoints

**Files:**
- Modify: `web_api/routes/channels.py`

- [ ] **Step 1: Add endpoints**

```python
from web_api.services.auto_improvement_service import apply_improvements, get_insights
```

Add endpoints:

```python
@router.post("/{channel_id}/improvements/apply")
def apply_channel_improvements(channel_id: int, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    changes = apply_improvements(db, channel_id)
    return {"applied": len(changes), "changes": changes}


@router.get("/{channel_id}/improvements", response_model=list[ChannelConfigHistoryResponse])
def get_channel_improvements(channel_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ChannelConfigHistory)
        .filter(ChannelConfigHistory.channel_id == channel_id)
        .order_by(ChannelConfigHistory.created_at.desc())
        .all()
    )


@router.get("/{channel_id}/insights", response_model=list[ChannelInsight])
def get_channel_insights(channel_id: int, db: Session = Depends(get_db)):
    return get_insights(db, channel_id)


@router.post("/{channel_id}/improvements/{history_id}/revert")
def revert_improvement(channel_id: int, history_id: int, db: Session = Depends(get_db)):
    history = (
        db.query(ChannelConfigHistory)
        .filter(ChannelConfigHistory.id == history_id)
        .filter(ChannelConfigHistory.channel_id == channel_id)
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="History entry not found")

    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if history.change_type == "voice_cast":
        channel.voice_cast_json = history.old_value

    reverted = ChannelConfigHistory(
        channel_id=channel_id,
        change_type=history.change_type,
        old_value=history.new_value,
        new_value=history.old_value,
        reason=f"Reverted change {history_id}",
    )
    db.add(reverted)
    db.commit()
    return {"ok": True}
```

- [ ] **Step 2: Commit**

```bash
git add web_api/routes/channels.py
git commit -m "feat(improvement): add improvement history endpoints"
```

---

### Task 4: Backend tests

**Files:**
- Create: `tests/web_api/test_auto_improvement_service.py`

- [ ] **Step 1: Write tests**

```python
import json
from web_api.services.auto_improvement_service import (
    _suggest_voice_cast_change,
    _suggest_mix_change,
)


def make_run(score, voice_cast, feedback=None):
    r = type("Run", (), {})()
    r.quality_score = score
    r.config_json = json.dumps({"voice_cast": voice_cast})
    r.feedback = feedback
    return r


def test_suggest_voice_cast_change():
    runs = [
        make_run(0.9, {"narrador": "v1"}),
        make_run(0.8, {"narrador": "v1"}),
        make_run(0.4, {"narrador": "v2"}),
    ]
    suggestion = _suggest_voice_cast_change(runs)
    assert suggestion is not None
    assert "v1" in suggestion["new_value"]


def test_suggest_mix_change():
    runs = [
        make_run(0.4, {"narrador": "v1"}, "la música tapa la voz"),
        make_run(0.3, {"narrador": "v1"}, "mezcla muy baja"),
    ]
    suggestion = _suggest_mix_change(runs)
    assert suggestion is not None
    assert suggestion["change_type"] == "mix"
```

- [ ] **Step 2: Run tests**

```bash
./venv311/bin/python -m pytest tests/web_api/test_auto_improvement_service.py -q
```

Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add tests/web_api/test_auto_improvement_service.py
git commit -m "test(improvement): add auto improvement tests"
```

---

### Task 5: Frontend types, API and store

**Files:**
- Modify: `web/src/types/index.ts`
- Modify: `web/src/api/client.ts`
- Create: `web/src/stores/improvementStore.ts`

- [ ] **Step 1: Add types**

```typescript
export interface ConfigHistoryEntry {
  id: number
  channel_id: number
  change_type: string
  old_value?: string
  new_value?: string
  reason?: string
  production_run_id?: number
  created_at: string
}

export interface ChannelInsight {
  id: string
  title: string
  description: string
  confidence: number
  based_on_runs: number
}
```

- [ ] **Step 2: Add API methods**

```typescript
export async function getChannelImprovements(channelId: number): Promise<ConfigHistoryEntry[]> {
  const response = await fetch(`/api/channels/${channelId}/improvements`)
  if (!response.ok) throw new Error('Failed to fetch improvements')
  return response.json()
}

export async function getChannelInsights(channelId: number): Promise<ChannelInsight[]> {
  const response = await fetch(`/api/channels/${channelId}/insights`)
  if (!response.ok) throw new Error('Failed to fetch insights')
  return response.json()
}

export async function applyChannelImprovements(channelId: number): Promise<{ applied: number }> {
  const response = await fetch(`/api/channels/${channelId}/improvements/apply`, { method: 'POST' })
  if (!response.ok) throw new Error('Failed to apply improvements')
  return response.json()
}

export async function revertImprovement(channelId: number, historyId: number): Promise<{ ok: boolean }> {
  const response = await fetch(`/api/channels/${channelId}/improvements/${historyId}/revert`, { method: 'POST' })
  if (!response.ok) throw new Error('Failed to revert')
  return response.json()
}
```

- [ ] **Step 3: Create store**

```typescript
import { create } from 'zustand'
import {
  applyChannelImprovements,
  getChannelImprovements,
  getChannelInsights,
  revertImprovement,
} from '../api/client'
import type { ChannelInsight, ConfigHistoryEntry } from '../types'

interface ImprovementState {
  history: ConfigHistoryEntry[]
  insights: ChannelInsight[]
  loading: boolean
  error: string | null
  fetchHistory: (channelId: number) => Promise<void>
  fetchInsights: (channelId: number) => Promise<void>
  apply: (channelId: number) => Promise<void>
  revert: (channelId: number, historyId: number) => Promise<void>
}

export const useImprovementStore = create<ImprovementState>((set, get) => ({
  history: [],
  insights: [],
  loading: false,
  error: null,
  fetchHistory: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const history = await getChannelImprovements(channelId)
      set({ history, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
  fetchInsights: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const insights = await getChannelInsights(channelId)
      set({ insights, loading: false })
    } catch (err) {
      set({ error: (err as Error).message, loading: false })
    }
  },
  apply: async (channelId) => {
    try {
      await applyChannelImprovements(channelId)
      await get().fetchHistory(channelId)
      await get().fetchInsights(channelId)
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },
  revert: async (channelId, historyId) => {
    try {
      await revertImprovement(channelId, historyId)
      await get().fetchHistory(channelId)
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },
}))
```

- [ ] **Step 4: Commit**

```bash
git add web/src/types/index.ts web/src/api/client.ts web/src/stores/improvementStore.ts
git commit -m "feat(improvement): add frontend types, API and store"
```

---

### Task 6: Frontend UI

**Files:**
- Create: `web/src/components/ImprovementTimeline.tsx`
- Create: `web/src/components/ChannelInsights.tsx`
- Create: `web/src/routes/channels.$id.studio.improvements.tsx`

- [ ] **Step 1: ImprovementTimeline**

```tsx
import { useEffect } from 'react'
import { useImprovementStore } from '../stores/improvementStore'

interface ImprovementTimelineProps {
  channelId: number
}

export default function ImprovementTimeline({ channelId }: ImprovementTimelineProps) {
  const { history, loading, fetchHistory, revert } = useImprovementStore()

  useEffect(() => {
    fetchHistory(channelId)
  }, [channelId, fetchHistory])

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Improvement history</h2>
      {loading && <p>Loading...</p>}
      <ul className="space-y-2">
        {history.map((entry) => (
          <li key={entry.id} className="rounded border bg-white p-3">
            <div className="flex items-center justify-between">
              <span className="font-medium capitalize">{entry.change_type}</span>
              <span className="text-xs text-gray-500">{new Date(entry.created_at).toLocaleString()}</span>
            </div>
            <p className="text-sm text-gray-600">{entry.reason}</p>
            {entry.old_value && (
              <p className="text-xs text-gray-400">From: {entry.old_value}</p>
            )}
            {entry.new_value && (
              <p className="text-xs text-gray-400">To: {entry.new_value}</p>
            )}
            {!entry.reason?.startsWith('Reverted') && (
              <button
                type="button"
                onClick={() => revert(channelId, entry.id)}
                className="mt-2 text-sm text-red-600 hover:underline"
              >
                Revert
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 2: ChannelInsights**

```tsx
import { useEffect } from 'react'
import { useImprovementStore } from '../stores/improvementStore'

interface ChannelInsightsProps {
  channelId: number
}

export default function ChannelInsights({ channelId }: ChannelInsightsProps) {
  const { insights, loading, fetchInsights, apply } = useImprovementStore()

  useEffect(() => {
    fetchInsights(channelId)
  }, [channelId, fetchInsights])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Insights</h2>
        <button
          type="button"
          onClick={() => apply(channelId)}
          className="rounded bg-green-600 px-4 py-2 text-white hover:bg-green-700"
        >
          Apply improvements
        </button>
      </div>
      {loading && <p>Loading...</p>}
      <div className="grid gap-4 md:grid-cols-2">
        {insights.map((insight) => (
          <div key={insight.id} className="rounded border bg-white p-4 shadow-sm">
            <h3 className="font-semibold">{insight.title}</h3>
            <p className="text-sm text-gray-600">{insight.description}</p>
            <p className="text-xs text-gray-400 mt-1">
              Confidence: {(insight.confidence * 100).toFixed(0)}% · {insight.based_on_runs} runs
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Route**

`web/src/routes/channels.$id.studio.improvements.tsx`:
```tsx
import { createFileRoute } from '@tanstack/react-router'
import ChannelInsights from '../components/ChannelInsights'
import ImprovementTimeline from '../components/ImprovementTimeline'

export const Route = createFileRoute('/channels/$id/studio/improvements')({
  component: () => {
    const { id } = Route.useParams()
    const channelId = Number(id)
    return (
      <div className="space-y-6">
        <ChannelInsights channelId={channelId} />
        <ImprovementTimeline channelId={channelId} />
      </div>
    )
  },
})
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ImprovementTimeline.tsx web/src/components/ChannelInsights.tsx web/src/routes/channels.$id.studio.improvements.tsx
git commit -m "feat(improvement): add improvement history UI"
```

---

### Task 7: Frontend tests

**Files:**
- Create: `web/src/tests/ImprovementTimeline.test.tsx`

- [ ] **Step 1: Write test**

```tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ImprovementTimeline from '../components/ImprovementTimeline'
import * as client from '../api/client'

vi.mock('../api/client')

describe('ImprovementTimeline', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders history entries', async () => {
    vi.mocked(client.getChannelImprovements).mockResolvedValue([
      { id: 1, channel_id: 10, change_type: 'voice_cast', reason: 'Best voice', old_value: '{}', new_value: '{"narrador":"v1"}', created_at: '2026-01-01' },
    ])

    render(<ImprovementTimeline channelId={10} />)

    await waitFor(() => {
      expect(screen.getByText('Best voice')).toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd web && npm test -- --run ImprovementTimeline
```

Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add web/src/tests/ImprovementTimeline.test.tsx
git commit -m "test(improvement): add ImprovementTimeline test"
```

---

### Task 8: Full test suite and build

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
git commit --allow-empty -m "chore(improvement): complete self-improvement history"
```

---

## Self-review

| Spec requirement | Task covering it |
|---|---|
| ChannelConfigHistory model | Task 1 |
| Auto analyze runs and suggest changes | Task 2 |
| Apply changes to channel config | Task 2 |
| History endpoints | Task 3 |
| Insights endpoint | Task 3 |
| Revert endpoint | Task 3 |
| Frontend timeline + insights | Tasks 5-6 |
| Tests | Tasks 4, 7, 8 |

**Placeholder scan:** No TBD/TODO. Code complete.

**Type consistency:** `ChannelConfigHistory` model, schema, TypeScript type aligned across backend and frontend.
