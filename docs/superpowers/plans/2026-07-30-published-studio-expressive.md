# Estado "Publicado" + Studio ordenado + Voces expresivas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Marca manual de episodios publicados (lista + canal), Studio reordenado (config primero, borradores primero, archivo plegable) y tokens de emoción Higgs insertados por el congreso y sanitizados por motor.

**Architecture:** Campo ortogonal `published_at` en `episodes` (no toca la máquina de estados del worker). Frontend consume dos endpoints nuevos. El "director de voz" del congreso inserta tokens `<|emotion:…|>` de una lista cerrada; una utilidad ligera (`core/emotion_tags.py`) los filtra por motor antes de sintetizar.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite, React + Zustand + TanStack Router + Vitest, pytest + TestClient, CrewAI/Ollama.

**Spec:** `docs/superpowers/specs/2026-07-30-published-studio-expressive-design.md`

---

### Task 1: Backend — `published_at` en episodios (modelo, migración, schema, endpoints)

**Files:**
- Modify: `web_api/models.py:7-20`
- Modify: `web_api/database.py:24-34`
- Modify: `web_api/schemas.py:30-44`
- Modify: `web_api/routes/episodes.py` (añadir al final)
- Test: `tests/web_api/test_episodes.py` (añadir al final)

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `tests/web_api/test_episodes.py`:

```python
def test_publish_episode_requires_completed():
    create_resp = client.post("/api/episodes", json={
        "title": "Sin audio",
        "type": "podcast",
        "source_text": "Texto",
        "voice_id": "jorge",
    })
    episode_id = create_resp.json()["id"]

    resp = client.post(f"/api/episodes/{episode_id}/publish")
    assert resp.status_code == 409


def test_publish_and_unpublish_episode():
    create_resp = client.post("/api/episodes", json={
        "title": "Listo",
        "type": "podcast",
        "source_text": "Texto",
        "voice_id": "jorge",
    })
    episode_id = create_resp.json()["id"]
    # Marcar como completed directamente en BD vía PUT de estado no existe;
    # se usa la sesión de SQLAlchemy del propio test.
    from web_api.database import SessionLocal
    from web_api.models import Episode
    db = SessionLocal()
    db.query(Episode).filter(Episode.id == episode_id).first().status = "completed"
    db.commit()
    db.close()

    resp = client.post(f"/api/episodes/{episode_id}/publish")
    assert resp.status_code == 200
    body = resp.json()
    assert body["published_at"] is not None

    # Idempotente: republicar devuelve 200 con fecha
    resp2 = client.post(f"/api/episodes/{episode_id}/publish")
    assert resp2.status_code == 200
    assert resp2.json()["published_at"] is not None

    resp3 = client.post(f"/api/episodes/{episode_id}/unpublish")
    assert resp3.status_code == 200
    assert resp3.json()["published_at"] is None


def test_publish_episode_not_found():
    assert client.post("/api/episodes/99999/publish").status_code == 404
    assert client.post("/api/episodes/99999/unpublish").status_code == 404
```

- [ ] **Step 2: Ejecutar y verificar que fallan**

Run: `venv311/bin/python -m pytest tests/web_api/test_episodes.py -q`
Expected: FAIL — `404`/`405` en publish (la ruta no existe) y/o `published_at` ausente.

- [ ] **Step 3: Implementar modelo + migración + schema + endpoints**

`web_api/models.py` — añadir la columna a `Episode` (tras `target_duration_minutes`):

```python
    target_duration_minutes = Column(Float, nullable=True)
    published_at = Column(DateTime, nullable=True)  # marca manual de publicación
```

`web_api/database.py` — añadir la entrada `"episodes"` en `_migrate()`:

```python
    new_columns = {
        "channels": [
            ("brief", "TEXT"),
            ("autopilot", "BOOLEAN DEFAULT 0 NOT NULL"),
            ("episodes_per_week", "INTEGER DEFAULT 2 NOT NULL"),
            ("target_minutes", "INTEGER DEFAULT 10 NOT NULL"),
        ],
        "content_plan_entries": [
            ("season", "INTEGER DEFAULT 1 NOT NULL"),
        ],
        "episodes": [
            ("published_at", "DATETIME"),
        ],
    }
```

`web_api/schemas.py` — en `EpisodeResponse`, añadir antes de `class Config`:

```python
    published_at: Optional[datetime] = None
```

`web_api/routes/episodes.py` — añadir al final (necesita `from datetime import datetime, timezone` arriba):

```python
@router.post("/{episode_id}/publish", response_model=EpisodeResponse)
def publish_episode(episode_id: int, db: Session = Depends(get_db)):
    """Marca manualmente el episodio como publicado (guarda la fecha)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    if episode.status != "completed":
        raise HTTPException(status_code=409, detail="Solo se pueden publicar episodios completados")
    episode.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(episode)
    return episode


@router.post("/{episode_id}/unpublish", response_model=EpisodeResponse)
def unpublish_episode(episode_id: int, db: Session = Depends(get_db)):
    """Quita la marca de publicado (reversible)."""
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    episode.published_at = None
    db.commit()
    db.refresh(episode)
    return episode
```

- [ ] **Step 4: Ejecutar y verificar que pasan**

Run: `venv311/bin/python -m pytest tests/web_api/test_episodes.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add web_api/models.py web_api/database.py web_api/schemas.py web_api/routes/episodes.py tests/web_api/test_episodes.py
git commit -m "feat(api): marca manual de publicado en episodios (published_at + publish/unpublish)"
```

---

### Task 2: Backend — `episode_published_at` en las entradas del plan

**Files:**
- Modify: `web_api/schemas.py:108-119`
- Modify: `web_api/routes/channels.py:134-150` (`list_plan_entries`)
- Test: `tests/web_api/test_channels.py` (añadir al final)

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/web_api/test_channels.py`:

```python
def test_plan_entries_include_episode_published_at():
    ch = client.post("/api/channels", json={
        "name": "Canal pub",
        "format": "podcast",
        "default_voice_id": "jorge",
    }).json()
    entry = client.post(f"/api/channels/{ch['id']}/plan", json={
        "title": "Cap 1",
    }).json()
    # Vincular un episodio completado y publicado
    ep = client.post("/api/episodes", json={
        "title": "Cap 1",
        "type": "podcast",
        "source_text": "Texto",
        "voice_id": "jorge",
    }).json()
    from web_api.database import SessionLocal
    from web_api.models import Episode, ContentPlanEntry
    db = SessionLocal()
    db.query(Episode).filter(Episode.id == ep["id"]).first().status = "completed"
    db.query(ContentPlanEntry).filter(ContentPlanEntry.id == entry["id"]).first().episode_id = ep["id"]
    db.commit()
    db.close()
    client.post(f"/api/episodes/{ep['id']}/publish")

    entries = client.get(f"/api/channels/{ch['id']}/plan").json()
    linked = next(e for e in entries if e["id"] == entry["id"])
    assert linked["episode_published_at"] is not None
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `venv311/bin/python -m pytest tests/web_api/test_channels.py -q`
Expected: FAIL — KeyError/`None` en `episode_published_at`.

- [ ] **Step 3: Implementar**

`web_api/schemas.py` — en `PlanEntryResponse`, tras `audio_url`:

```python
    episode_published_at: Optional[datetime] = None
```

`web_api/routes/channels.py` — en `list_plan_entries`, dentro del `if episode:`:

```python
            if episode:
                resp.audio_url = episode.audio_url
                resp.episode_published_at = episode.published_at
```

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `venv311/bin/python -m pytest tests/web_api/test_channels.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add web_api/schemas.py web_api/routes/channels.py tests/web_api/test_channels.py
git commit -m "feat(api): episode_published_at en entradas del plan de canal"
```

---

### Task 3: Frontend — tipos, cliente API y store para publicar

**Files:**
- Modify: `web/src/types/index.ts:13-24,54-66`
- Modify: `web/src/api/client.ts:65-74`
- Modify: `web/src/stores/episodeStore.ts`

- [ ] **Step 1: Tipos**

`web/src/types/index.ts` — en `Episode`, tras `error_message?`:

```ts
  published_at?: string | null
```

y en `ContentPlanEntry`, tras `audio_url?`:

```ts
  episode_published_at?: string | null
```

- [ ] **Step 2: Cliente API**

`web/src/api/client.ts` — tras `retryEpisode`:

```ts
  publishEpisode: (id: number) =>
    fetchJson<Episode>(`/episodes/${id}/publish`, { method: 'POST' }),
  unpublishEpisode: (id: number) =>
    fetchJson<Episode>(`/episodes/${id}/unpublish`, { method: 'POST' }),
```

- [ ] **Step 3: Store**

`web/src/stores/episodeStore.ts` — añadir a la interfaz:

```ts
  publishEpisode: (id: number) => Promise<void>
  unpublishEpisode: (id: number) => Promise<void>
```

y al store (mismo patrón que `retryEpisode`):

```ts
  publishEpisode: async (id) => {
    set({ error: null })
    try {
      const episode = await api.publishEpisode(id)
      set((state) => ({
        episodes: state.episodes.map((e) => (e.id === id ? episode : e)),
      }))
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  unpublishEpisode: async (id) => {
    set({ error: null })
    try {
      const episode = await api.unpublishEpisode(id)
      set((state) => ({
        episodes: state.episodes.map((e) => (e.id === id ? episode : e)),
      }))
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
```

- [ ] **Step 4: Verificar compilación**

Run: `cd web && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 5: Commit**

```bash
git add web/src/types/index.ts web/src/api/client.ts web/src/stores/episodeStore.ts
git commit -m "feat(web): tipos, cliente y store para publish/unpublish de episodios"
```

---

### Task 4: Frontend — badge y botón de publicado en `EpisodeCard` + filtro en la cola

**Files:**
- Modify: `web/src/components/EpisodeCard.tsx`
- Modify: `web/src/routes/queue.tsx`
- Test: `web/src/components/EpisodeCard.test.tsx`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `web/src/components/EpisodeCard.test.tsx` (el mock de store es necesario):

```tsx
vi.mock('../stores/episodeStore', () => ({
  useEpisodeStore: (sel: any) =>
    sel({
      publishEpisode: vi.fn(),
      unpublishEpisode: vi.fn(),
    }),
}))

// dentro de describe:
  it('shows publish button when completed and not published', () => {
    render(<EpisodeCard episode={makeEpisode({ status: 'completed' })} onDelete={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Marcar publicado/i })).toBeInTheDocument()
  })

  it('shows published badge and unpublish button when published', () => {
    render(
      <EpisodeCard
        episode={makeEpisode({ status: 'completed', published_at: '2026-07-30T10:00:00' })}
        onDelete={vi.fn()}
      />
    )
    expect(screen.getByText(/Publicado/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Desmarcar/i })).toBeInTheDocument()
  })

  it('does not show publish button when not completed', () => {
    render(<EpisodeCard episode={makeEpisode({ status: 'pending' })} onDelete={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /Marcar publicado/i })).not.toBeInTheDocument()
  })
```

- [ ] **Step 2: Ejecutar y verificar que fallan**

Run: `cd web && npx vitest run src/components/EpisodeCard.test.tsx`
Expected: FAIL — no encuentra los botones.

- [ ] **Step 3: Implementar `EpisodeCard`**

`web/src/components/EpisodeCard.tsx` — dentro del componente, obtener acciones del store (ya importado) y renderizar badge + botón. Contenido completo del return modificado:

```tsx
export default function EpisodeCard({ episode, onDelete, onRetry, highlighted }: Props) {
  const publishEpisode = useEpisodeStore((s) => s.publishEpisode)
  const unpublishEpisode = useEpisodeStore((s) => s.unpublishEpisode)
  const published = Boolean(episode.published_at)

  return (
    <div className={`bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20 ${highlighted ? 'ring-2 ring-purple-500' : ''}`}>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg tracking-tight text-slate-100">{episode.title}</h3>
          <p className="text-sm text-slate-400">{episode.type} • {episode.voice_id}</p>
        </div>
        <div className="flex gap-2">
          {published && (
            <span className="px-2 py-1 rounded-lg text-xs font-medium bg-emerald-500/15 border border-emerald-500/40 text-emerald-300">
              Publicado · {new Date(episode.published_at!).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}
            </span>
          )}
          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusColors[episode.status] || 'bg-slate-700 text-slate-300'}`}>
            {episode.status}
          </span>
        </div>
      </div>

      {episode.error_message && (
        <p className="text-red-400 text-sm mt-2">{episode.error_message}</p>
      )}

      {episode.audio_url && (
        <AudioPlayer src={episode.audio_url} />
      )}

      <div className="mt-3 flex gap-4">
        {episode.status === 'failed' && (
          <button
            type="button"
            onClick={() => onRetry(episode.id)}
            aria-label={`Reintentar episodio ${episode.title}`}
            className="text-blue-400 text-sm hover:text-blue-300 hover:underline transition-colors"
          >
            Reintentar
          </button>
        )}
        {episode.status === 'completed' && !published && (
          <button
            type="button"
            onClick={() => publishEpisode(episode.id)}
            className="text-emerald-400 text-sm hover:text-emerald-300 hover:underline transition-colors"
          >
            Marcar publicado
          </button>
        )}
        {published && (
          <button
            type="button"
            onClick={() => unpublishEpisode(episode.id)}
            className="text-slate-400 text-sm hover:text-slate-300 hover:underline transition-colors"
          >
            Desmarcar publicado
          </button>
        )}
        <button
          type="button"
          onClick={() => onDelete(episode.id)}
          aria-label={`Eliminar episodio ${episode.title}`}
          className="text-red-400 text-sm hover:text-red-300 hover:underline transition-colors"
        >
          Eliminar
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Filtro en la cola**

`web/src/routes/queue.tsx` — añadir estado local y barra de filtro:

```tsx
import { createFileRoute, useSearch } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
// ...

type PubFilter = 'all' | 'unpublished' | 'published'

function QueuePage() {
  // ... hooks existentes ...
  const [pubFilter, setPubFilter] = useState<PubFilter>('all')
  const visible = episodes.filter((e) =>
    pubFilter === 'all' ? true : pubFilter === 'published' ? Boolean(e.published_at) : !e.published_at
  )

  // en el JSX, tras <LiveJobsPanel />:
      <div className="flex gap-2 mb-4">
        {([['all', 'Todos'], ['unpublished', 'Sin publicar'], ['published', 'Publicados']] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setPubFilter(key)}
            className={`px-3 py-1 rounded-lg text-sm border transition-colors ${
              pubFilter === key
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-300 hover:border-slate-500'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

  // y en el map: visible.map((episode) => ( ... ))
```

- [ ] **Step 5: Ejecutar tests y typecheck**

Run: `cd web && npx vitest run src/components/EpisodeCard.test.tsx && npx tsc --noEmit`
Expected: tests PASS, sin errores de tipos

- [ ] **Step 6: Commit**

```bash
git add web/src/components/EpisodeCard.tsx web/src/components/EpisodeCard.test.tsx web/src/routes/queue.tsx
git commit -m "feat(web): badge/botón de publicado en tarjeta y filtro en la cola"
```

---

### Task 5: Frontend — badge "Publicado" en la vista del canal (`PlanEntryCard`)

**Files:**
- Modify: `web/src/components/PlanEntryCard.tsx:89-104`

- [ ] **Step 1: Implementar badge**

En `PlanEntryCard.tsx`, dentro del `<div className="flex gap-2 mt-2">`, tras el badge de temporada:

```tsx
            {entry.episode_published_at && (
              <span className="text-xs bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 px-2 py-1 rounded-lg inline-block">
                Publicado
              </span>
            )}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: sin errores

- [ ] **Step 3: Commit**

```bash
git add web/src/components/PlanEntryCard.tsx
git commit -m "feat(web): badge Publicado en entradas del plan con episodio publicado"
```

---

### Task 6: Frontend — Studio reordenado (canal primero, borradores primero, archivo plegable)

**Files:**
- Modify: `web/src/routes/studio.tsx`
- Modify: `web/src/components/ContentPlanList.tsx`

- [ ] **Step 1: Cabecera del canal antes del panel de configuración**

En `web/src/routes/studio.tsx`, entre `<StudioPanel … />` NO — el orden nuevo es: **cabecera canal → StudioPanel (config básica) → plan**. Insertar justo DESPUÉS de `<CongressTable />` y el bloque `{error && …}`, y ANTES de `<StudioPanel`:

```tsx
      {channel && (
        <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-4">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg font-bold tracking-tight text-slate-100">{channel.name}</h3>
              <p className="text-sm text-slate-400 mt-1">{channel.description || 'Sin descripción'}</p>
              <p className="text-xs text-slate-500 mt-2">
                {channel.format} · nicho: {channel.niche || 'general'}
              </p>
            </div>
            <Link
              to="/channels/$id/edit"
              params={{ id: String(channel.id) }}
              className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors"
            >
              Editar canal
            </Link>
          </div>
        </div>
      )}
```

Añadir el import arriba: `import { createFileRoute, Link } from '@tanstack/react-router'` (reemplaza el import actual de `createFileRoute`).

Verificar que `channels.$id.edit.tsx` acepta el param `id` (sí, por convención TanStack Router del proyecto).

- [ ] **Step 2: Plan: borradores visibles, archivo plegable**

`web/src/components/ContentPlanList.tsx` — reescribir el cuerpo del componente:

```tsx
import { useState } from 'react'
import { ContentPlanEntry } from '../types'
import PlanEntryCard from './PlanEntryCard'

interface Props {
  entries: ContentPlanEntry[]
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

export default function ContentPlanList({ entries, onApprove, onReject, onDelete }: Props) {
  const [showArchive, setShowArchive] = useState(false)
  if (entries.length === 0) return <p className="text-slate-400">No hay entradas en el plan.</p>

  const drafts = entries.filter((e) => e.status === 'draft')
  const archive = entries.filter((e) => e.status !== 'draft')

  // Agrupa borradores por temporada (más recientes primero; el backend ya
  // devuelve created_at desc dentro de cada grupo)
  const seasons = new Map<number, ContentPlanEntry[]>()
  drafts.forEach((entry) => {
    const list = seasons.get(entry.season ?? 1) ?? []
    list.push(entry)
    seasons.set(entry.season ?? 1, list)
  })
  const sortedSeasons = [...seasons.entries()].sort((a, b) => b[0] - a[0])

  return (
    <div className="space-y-6">
      {drafts.length === 0 && (
        <p className="text-slate-400">Sin borradores pendientes. Genera un plan o una temporada.</p>
      )}
      {sortedSeasons.map(([season, seasonEntries]) => (
        <section key={season}>
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-md font-bold tracking-tight text-purple-300">Temporada {season}</h3>
            <span className="text-xs text-slate-400">{seasonEntries.length} borradores</span>
          </div>
          <div className="space-y-3">
            {seasonEntries.map((entry) => (
              <PlanEntryCard
                key={entry.id}
                entry={entry}
                onApprove={onApprove}
                onReject={onReject}
                onDelete={onDelete}
              />
            ))}
          </div>
        </section>
      ))}

      {archive.length > 0 && (
        <section>
          <button
            type="button"
            onClick={() => setShowArchive((v) => !v)}
            className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
          >
            {showArchive ? '▾' : '▸'} Archivo ({archive.length} generadas/rechazadas)
          </button>
          {showArchive && (
            <div className="space-y-3 mt-3">
              {archive.map((entry) => (
                <PlanEntryCard
                  key={entry.id}
                  entry={entry}
                  onApprove={onApprove}
                  onReject={onReject}
                  onDelete={onDelete}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Typecheck y build**

Run: `cd web && npx tsc --noEmit && npm run build`
Expected: compila sin errores

- [ ] **Step 4: Commit**

```bash
git add web/src/routes/studio.tsx web/src/components/ContentPlanList.tsx
git commit -m "feat(web): studio ordenado — canal y config primero, borradores primero, archivo plegable"
```

---

### Task 7: Tokens de emoción — `core/emotion_tags.py` + tests

**Files:**
- Create: `core/emotion_tags.py`
- Test: `tests/test_emotion_tags.py`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_emotion_tags.py`:

```python
from core.emotion_tags import sanitize_emotion_tags, HIGGS_TAGS


def test_higgs_keeps_known_emotion_tokens():
    text = "<|emotion:enthusiasm|> Hoy es un gran día. <|prosody:pause|> Sigamos."
    assert sanitize_emotion_tags(text, "higgs") == text


def test_higgs_strips_invented_tokens():
    text = "<|emotion:felicidad_extrema|> Hola <|emotion:awe|> mundo."
    assert sanitize_emotion_tags(text, "higgs") == "Hola <|emotion:awe|> mundo."


def test_edge_and_qwen_strip_all_tokens():
    text = "<|emotion:enthusiasm|> Hola <|style:whispering|> mundo."
    for engine in ("edge", "qwen3"):
        assert sanitize_emotion_tags(text, engine) == "Hola mundo."


def test_text_without_tags_is_untouched():
    text = "Guion normal, sin marcas. Con acentos y ¡signos!"
    for engine in ("higgs", "edge", "qwen3"):
        assert sanitize_emotion_tags(text, engine) == text


def test_catalog_covers_documented_higgs_tokens():
    for tag in ("emotion:elation", "emotion:sadness", "style:whispering",
                "sfx:laughter", "prosody:pause", "prosody:speed_slow"):
        assert tag in HIGGS_TAGS
```

- [ ] **Step 2: Ejecutar y verificar que fallan**

Run: `venv311/bin/python -m pytest tests/test_emotion_tags.py -q`
Expected: FAIL — `ModuleNotFoundError: core.emotion_tags`

- [ ] **Step 3: Implementar `core/emotion_tags.py`**

```python
"""Tokens inline de emoción/estilo/prosodia para TTS expresivo.

Higgs v3 interpreta tokens <|tipo:valor|> (emociones, estilos, efectos);
el resto de motores (edge-tts, Qwen3-Base) no los entiende y hay que
quitárselos al texto antes de sintetizar o los pronunciaría.

Mantener las listas sincronizadas con core/higgs_engine.py
(HIGGS_EMOTIONS / HIGGS_STYLES / HIGGS_SFX) — se duplican aquí para no
importar el motor (que carga torch) en el camino caliente de la API.
"""

import re

_TAG_RE = re.compile(r"<\|([a-z]+):([a-z_]+)\|>")
_SPACES_RE = re.compile(r"[ \t]{2,}")

_EMOTIONS = [
    "elation", "amusement", "enthusiasm", "determination", "pride",
    "contentment", "affection", "relief", "contemplation", "confusion",
    "surprise", "awe", "longing", "arousal", "anger", "fear", "disgust",
    "bitterness", "sadness", "shame", "helplessness",
]

# Nombres públicos para el prompt del congreso (crew_service)
HIGGS_EMOTION_NAMES: list[str] = list(_EMOTIONS)
_STYLES = ["singing", "shouting", "whispering"]
_SFX = ["cough", "laughter", "crying", "screaming", "burping",
        "humming", "sigh", "sniff", "sneeze"]
_PROSODY = ["speed_slow", "speed_fast", "pitch_high", "pitch_low", "pause"]

HIGGS_TAGS: frozenset[str] = frozenset(
    {f"emotion:{t}" for t in _EMOTIONS}
    | {f"style:{t}" for t in _STYLES}
    | {f"sfx:{t}" for t in _SFX}
    | {f"prosody:{t}" for t in _PROSODY}
)

# Tags soportados por motor; vacío = quitar todos los tokens
ENGINE_TAGS: dict[str, frozenset[str]] = {
    "higgs": HIGGS_TAGS,
    "qwen3": frozenset(),
    "edge": frozenset(),
}


def sanitize_emotion_tags(text: str, engine: str) -> str:
    """Quita los tokens <|tipo:valor|> que `engine` no soporta.

    Devuelve el texto solo con los tokens que el motor entiende; el resto
    desaparece (junto con el doble espacio resultante) para que nunca se
    pronuncien literalmente.
    """
    allowed = ENGINE_TAGS.get(engine, frozenset())

    def _repl(match: re.Match) -> str:
        return match.group(0) if f"{match.group(1)}:{match.group(2)}" in allowed else ""

    return _SPACES_RE.sub(" ", _TAG_RE.sub(_repl, text)).strip() if "<|" in text else text
```

- [ ] **Step 4: Ejecutar y verificar que pasan**

Run: `venv311/bin/python -m pytest tests/test_emotion_tags.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add core/emotion_tags.py tests/test_emotion_tags.py
git commit -m "feat(core): sanitize_emotion_tags — whitelist de tokens <|…|> por motor TTS"
```

---

### Task 8: Congreso — el director de voz inserta emociones

**Files:**
- Modify: `web_api/services/crew_service.py:70-75` (`CLEAN_PROMPT`) y su uso en `generate_script`
- Test: `tests/web_api/test_crew_service.py` (añadir al final)

- [ ] **Step 1: Escribir el test que falla**

Añadir a `tests/web_api/test_crew_service.py`:

```python
def test_clean_prompt_lists_emotion_tokens_and_keeps_them():
    from web_api.services.crew_service import CLEAN_PROMPT, _strip_markup
    # El prompt del director de voz incluye la lista cerrada de emociones
    assert "<|emotion:" in CLEAN_PROMPT
    assert "enthusiasm" in CLEAN_PROMPT
    # _strip_markup no destruye los tokens (ni hoy ni en el futuro)
    text = "**Negrita** <|emotion:awe|> Texto limpio"
    assert "<|emotion:awe|>" in _strip_markup(text)
```

- [ ] **Step 2: Ejecutar y verificar que falla**

Run: `venv311/bin/python -m pytest tests/web_api/test_crew_service.py -q`
Expected: FAIL — `"<|emotion:" not in CLEAN_PROMPT`

- [ ] **Step 3: Implementar**

`web_api/services/crew_service.py` — sustituir `CLEAN_PROMPT` por:

```python
CLEAN_PROMPT = """Del guion anterior, prepara la versión FINAL PARA SÍNTESIS DE VOZ (TTS).
Elimina TODO lo que no deba leerse en voz alta: notas de producción, indicaciones
("Intro Musical", "Narrador:", "Pausa", efectos de sonido), formato markdown
(**, ##, *), títulos de sección y cualquier comentario técnico.
NO ACORTES ni resumas: conserva TODO el contenido y la longitud.

EXPRESIVIDAD (motor Higgs): inserta UN token de emoción al inicio de cada
sección o cambio de tono claro, usando SOLO esta lista cerrada:
{emotions}
Formato exacto: <|emotion:nombre_en_inglés|> — ejemplo: "<|emotion:enthusiasm|> Hoy vamos a…"
No traduzcas los tokens, no inventes otros, no uses más de uno por párrafo.
Conserva intactos los tokens <|…|> ya presentes.

Devuelve SOLO el texto hablable, tal cual debe pronunciarse."""
```

Y en `generate_script`, donde se construye el prompt de limpieza, formatear la lista:

```python
    # 5. Limpieza para TTS
    from core.emotion_tags import HIGGS_EMOTION_NAMES  # lista cerrada para el prompt
    emotions = ", ".join(HIGGS_EMOTION_NAMES)
    prompt = CLEAN_PROMPT.format(emotions=emotions) + f"\n\nGuion:\n{polished}"
```

(Import local para no cargar nada extra en import time; alternativa: import arriba del módulo, también válido — `core/emotion_tags.py` es ligero.)

- [ ] **Step 4: Ejecutar y verificar que pasa**

Run: `venv311/bin/python -m pytest tests/web_api/test_crew_service.py -q`
Expected: all passed (los tests existentes no se rompen: el `FakeCrew` del test de colapso busca `"FINAL PARA SÍNTESIS DE VOZ"` en el prompt, que sigue presente)

- [ ] **Step 5: Commit**

```bash
git add web_api/services/crew_service.py tests/web_api/test_crew_service.py
git commit -m "feat(crew): director de voz inserta tokens <|emotion:…|> de lista cerrada"
```

---

### Task 9: Síntesis — sanitización por motor antes de sintetizar

**Files:**
- Modify: `web_api/routes/tts.py`
- Modify: `worker/handlers.py:113-131`
- Test: `tests/web_api/test_tts.py` (añadir al final)

- [ ] **Step 1: Escribir el test que falla**

Mirar primero `tests/web_api/test_tts.py` para seguir su patrón (usa TestClient y/o mocks). Añadir:

```python
def test_sanitize_applied_for_edge_preview(monkeypatch):
    """Un texto con tokens <|…|> llega limpio a edge-tts."""
    from core.emotion_tags import sanitize_emotion_tags
    out = sanitize_emotion_tags("<|emotion:awe|> Hola qué tal", "edge")
    assert out == "Hola qué tal"
    out = sanitize_emotion_tags("<|emotion:awe|> Hola", "higgs")
    assert out == "<|emotion:awe|> Hola"
```

(Si ya está cubierto por los tests de la Task 7, este test se puede omitir; lo importante es el siguiente paso de integración.)

- [ ] **Step 2: Implementar en `web_api/routes/tts.py`**

Import arriba: `from core.emotion_tags import sanitize_emotion_tags`

En `synthesize()` (ruta de texto largo), sanitizar una vez antes de trocear:

```python
    voice = _find_voice(request.voice_id)
    if voice is None or voice.type != "cloned" or not voice.reference_path:
        raise HTTPException(status_code=400, detail="Solo voces clonadas (clone:*)")
    engine_kind = voice.engine if voice.engine in ("higgs", "qwen3") else "higgs"
    clean_text = sanitize_emotion_tags(request.text, engine_kind)
```

y usar `chunks = _split_text(clean_text)`.

En `preview()`: sanitizar `request.text` antes de cada camino:

```python
    if voice is not None and voice.type == "cloned" and voice.reference_path:
        text = sanitize_emotion_tags(request.text, voice.engine if voice.engine in ("higgs", "qwen3") else "higgs")
        # ... _synthesize_clone(text, voice, wav_path)
    edge_voice = VOICE_MAP.get(request.voice_id, DEFAULT_VOICE)
    communicate = edge_tts.Communicate(sanitize_emotion_tags(request.text, "edge"), voice=edge_voice)
```

- [ ] **Step 3: Implementar en `worker/handlers.py`**

El episodio con voz edge también puede recibir tokens si el guion viene del congreso. En `handle_podcast_episode`, rama edge:

```python
        from core.emotion_tags import sanitize_emotion_tags
        async def _run():
            communicate = edge_tts.Communicate(
                sanitize_emotion_tags(episode.source_text or "", "edge"),
                voice=voice
            )
            await communicate.save(str(output_path))
```

(La rama clonada pasa por `/api/tts/synthesize`, ya sanitizada en Step 2.)

- [ ] **Step 4: Ejecutar tests**

Run: `venv311/bin/python -m pytest tests/web_api/test_tts.py tests/test_emotion_tags.py tests/worker -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add web_api/routes/tts.py worker/handlers.py tests/web_api/test_tts.py
git commit -m "feat(tts): sanitiza tokens de emoción por motor antes de sintetizar"
```

---

### Task 10: Verificación integral

- [ ] **Step 1: Suite Python completa**

Run: `venv311/bin/python -m pytest tests/ -q`
Expected: all passed

- [ ] **Step 2: Suite frontend completa + build**

Run: `cd web && npx vitest run && npx tsc --noEmit && npm run build`
Expected: todo verde

- [ ] **Step 3: Humo en vivo**

1. Reiniciar la pila (`starter.py`) para cargar la migración y el código nuevo.
2. `GET /api/episodes` → los episodios existentes traen `published_at: null`.
3. Publicar un episodio completed: `curl -X POST /api/episodes/{id}/publish` → 200 con fecha; en la cola aparece el badge verde y en el canal el badge "Publicado".
4. Studio: entradas ordenadas reciente→antiguo, solo borradores visibles, archivo plegable, cabecera de canal con Editar.
5. Relanzar un guion de prueba (entrada draft del canal) y comprobar en los eventos del job (`voice_director_done`) que el texto lleva algún `<|emotion:…|>` y que el audio se genera sin pronunciar tokens.

- [ ] **Step 4: Commit final (si hay ajustes del humo)**

```bash
git add -A
git commit -m "chore: ajustes tras verificación en vivo"
```

---

## Self-Review

**Spec coverage:**
- Publicado (API, badge lista, filtro, badge canal) → Tasks 1–5 ✓
- Studio ordenado (reciente primero, canal+config primero, archivo plegable) → Task 6 ✓ (orden backend ya existía, verificado en spec)
- Emociones (prompt, conservación, whitelist por motor) → Tasks 7–9 ✓
- Tests de cada feature ✓ — YAGNI respetado (sin RSS, sin historial, sin borrado de datos)

**Type consistency:** `published_at` (Episode / EpisodeResponse / TS `Episode`), `episode_published_at` (PlanEntryResponse / TS `ContentPlanEntry`), `sanitize_emotion_tags(text, engine)`, `HIGGS_TAGS`, `ENGINE_TAGS` — mismos nombres en todas las tasks ✓
