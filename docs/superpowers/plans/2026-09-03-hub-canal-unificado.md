# Hub de canal unificado + "Generar guion con IA" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar Studio/Canales/plan en un único hub `/channels/$id` con tabs Plan/Episodios/Config y añadir el flujo txt/md → congreso de agentes → guion editable → cola.

**Architecture:** Backend: filtro `channel_id` en episodios, refactor de `generate_script` para aceptar materia prima cruda, job `script:channel:{id}:raw` reutilizando el job registry con SSE. Frontend: ruta hub con 3 tabs (componentes en `components/channel-hub/`), wizard de 3 pasos con EventSource a `/api/jobs/{id}/events`, redirecciones desde rutas viejas.

**Tech Stack:** FastAPI + pytest; React 18 + TanStack Router + Zustand + Tailwind + vitest.

**Spec:** `docs/superpowers/specs/2026-09-03-hub-canal-unificado-design.md`

---

### Task 1: Backend — filtro `channel_id` en listado de episodios

**Files:**
- Modify: `backend/app/routes/episodes.py:16-18`
- Test: `backend/tests/test_script_jobs.py` (creado en este task; se extiende en Task 3)

- [ ] **Step 1: Escribir el test que falla**

Crear `backend/tests/test_script_jobs.py`:

```python
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def _create_channel(name: str) -> dict:
    r = client.post("/api/channels", json={
        "name": name, "format": "podcast", "default_voice_id": "jorge",
    })
    assert r.status_code == 201, r.text
    return r.json()


def _create_episode(channel_id: int, title: str) -> dict:
    r = client.post("/api/episodes", json={
        "title": title,
        "type": "podcast",
        "source_text": "Texto de prueba suficientemente largo.",
        "voice_id": "jorge",
        "channel_id": channel_id,
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_list_episodes_filter_by_channel():
    c1 = _create_channel("Filtro A")
    c2 = _create_channel("Filtro B")
    _create_episode(c1["id"], "Ep A1")
    _create_episode(c2["id"], "Ep B1")

    r = client.get(f"/api/episodes?channel_id={c1['id']}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Ep A1"
    assert all(e["channel_id"] == c1["id"] for e in data)

    r_all = client.get("/api/episodes")
    assert len(r_all.json()) >= 2
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest backend/tests/test_script_jobs.py::test_list_episodes_filter_by_channel -v`
Expected: FAIL — `channel_id` se ignora y el filtro devuelve todos.

- [ ] **Step 3: Implementar el filtro**

En `backend/app/routes/episodes.py`, reemplazar `list_episodes`:

```python
@router.get("", response_model=List[EpisodeResponse])
def list_episodes(channel_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Episode).order_by(Episode.created_at.desc())
    if channel_id is not None:
        query = query.filter(Episode.channel_id == channel_id)
    return query.all()
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m pytest backend/tests/test_script_jobs.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/episodes.py backend/tests/test_script_jobs.py
git commit -m "feat(api): filtro channel_id en listado de episodios"
```

---

### Task 2: Backend — `generate_script_from_raw` (refactor DRY)

**Files:**
- Modify: `backend/app/services/crew_service.py:311` (`generate_script` y su cuerpo, hasta ~linea 470)
- Test: `backend/tests/test_script_jobs.py`

- [ ] **Step 1: Escribir el test que falla**

Añadir a `backend/tests/test_script_jobs.py`:

```python
def _dummy_channel():
    from backend.app.models import Channel
    return Channel(
        name="C", format="podcast", niche="nicho", description="",
        default_voice_id="jorge", target_minutes=2, episodes_per_week=2,
        num_speakers=1,
    )


def test_generate_script_from_raw_uses_material(monkeypatch):
    import backend.app.services.crew_service as cs
    from types import SimpleNamespace

    monkeypatch.setattr(cs, "get_script_llm", lambda: object())
    prompts = []

    def fake_run(agent, prompt, expected):
        prompts.append(prompt)
        if "JSON" in expected:
            return '[{"title": "S1", "points": "puntos"}]'
        return "palabra " * 400

    monkeypatch.setattr(cs, "_run_single_task", fake_run)

    # Variante cruda: la materia prima debe llegar a los prompts
    script = cs.generate_script_from_raw(
        _dummy_channel(), "MATERIAL_BRUTO_XYZ", "Título crudo", target_minutes=2
    )
    assert "palabra" in script
    assert any("MATERIAL_BRUTO_XYZ" in p for p in prompts)
    assert any("Título crudo" in p for p in prompts)

    # Wrapper viejo (entrada de plan) sigue funcionando igual
    prompts.clear()
    entry = SimpleNamespace(title="Título plan", description="DESC_PLAN_123")
    script2 = cs.generate_script(_dummy_channel(), entry, target_minutes=2)
    assert "palabra" in script2
    assert any("DESC_PLAN_123" in p for p in prompts)
    assert any("Título plan" in p for p in prompts)
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `python -m pytest backend/tests/test_script_jobs.py::test_generate_script_from_raw_uses_material -v`
Expected: FAIL — `generate_script_from_raw` no existe (`AttributeError`).

- [ ] **Step 3: Refactor en crew_service.py**

1. Renombrar `def generate_script(channel, entry, target_minutes: int = 10, on_progress=None) -> str:` a:

```python
def _generate_script_impl(
    channel, title: str, material: str, target_minutes: int = 10, on_progress=None
) -> str:
```

2. Dentro del cuerpo, reemplazar:
   - `desc = entry.description or ""` → `desc = material`
   - todas las demás ocurrencias de `entry.title` → `title` (en `RESEARCH_PROMPT.format`, `OUTLINE_PROMPT.format`, `SECTION_PROMPT.format`, los prompts de expansión `f"Esta sección de un episodio titulado \"{entry.title}\"..."`, `f"El guion del episodio \"{entry.title}\"..."` y el fallback `sections = [{"title": entry.title, "points": desc}]`).

3. Añadir antes del impl:

```python
def generate_script(channel, entry, target_minutes: int = 10, on_progress=None) -> str:
    """Congreso de agentes a partir de una entrada del plan editorial."""
    return _generate_script_impl(
        channel, entry.title, entry.description or "", target_minutes, on_progress
    )


def generate_script_from_raw(
    channel, raw_text: str, title: str, target_minutes: int = 10, on_progress=None
) -> str:
    """Congreso de agentes a partir de materia prima (txt/md subido o pegado).

    El texto completo actúa como material del investigador: los agentes lo
    analizan y lo convierten en guion listo para TTS.
    """
    return _generate_script_impl(channel, title, raw_text, target_minutes, on_progress)
```

(El docstring largo original de `generate_script` —"Congreso de agentes: investigador → planificador…"— queda en `_generate_script_impl`, junto con `emit` y `make_agent`.)

- [ ] **Step 4: Correr tests**

Run: `python -m pytest backend/tests/test_script_jobs.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/crew_service.py backend/tests/test_script_jobs.py
git commit -m "feat(crew): generate_script_from_raw reutiliza el pipeline del congreso"
```

---

### Task 3: Backend — endpoint `POST /channels/{id}/script-jobs`

**Files:**
- Modify: `backend/app/services/automation_service.py` (añadir `run_raw_script_job` + `start_raw_script_job` junto a `start_script_job`)
- Modify: `backend/app/routes/channels.py` (import + endpoint)
- Test: `backend/tests/test_script_jobs.py`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `backend/tests/test_script_jobs.py`:

```python
def test_script_jobs_accepts_pasted_text(monkeypatch):
    ch = _create_channel("ScriptJob A")
    monkeypatch.setattr(
        "backend.app.routes.channels.start_raw_script_job", lambda *a, **k: "jobabc123"
    )
    r = client.post(
        f"/api/channels/{ch['id']}/script-jobs",
        data={"text": "Material de prueba", "title": "Mi título"},
    )
    assert r.status_code == 202, r.text
    assert r.json() == {"job_id": "jobabc123"}


def test_script_jobs_accepts_file_upload(monkeypatch):
    ch = _create_channel("ScriptJob B")
    monkeypatch.setattr(
        "backend.app.routes.channels.start_raw_script_job", lambda *a, **k: "jobfile456"
    )
    r = client.post(
        f"/api/channels/{ch['id']}/script-jobs",
        files={"script": ("caso.md", b"# Caso\n\nMaterial markdown", "text/markdown")},
    )
    assert r.status_code == 202, r.text
    assert r.json() == {"job_id": "jobfile456"}


def test_script_jobs_validations(monkeypatch):
    monkeypatch.setattr(
        "backend.app.routes.channels.start_raw_script_job", lambda *a, **k: "jobx"
    )
    ch = _create_channel("ScriptJob C")
    # Sin texto ni archivo
    assert client.post(f"/api/channels/{ch['id']}/script-jobs", data={}).status_code == 400
    # Texto vacío
    assert client.post(
        f"/api/channels/{ch['id']}/script-jobs", data={"text": "   "}
    ).status_code == 400
    # Canal inexistente
    assert client.post(
        "/api/channels/99999/script-jobs", data={"text": "hola"}
    ).status_code == 404
    # Ya hay un job en curso para el canal
    monkeypatch.setattr(
        "backend.app.routes.channels.start_raw_script_job", lambda *a, **k: None
    )
    assert client.post(
        f"/api/channels/{ch['id']}/script-jobs", data={"text": "hola"}
    ).status_code == 409
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `python -m pytest backend/tests/test_script_jobs.py -k script_jobs -v`
Expected: FAIL 404 (la ruta no existe).

- [ ] **Step 3: Implementar en automation_service.py**

Añadir tras `start_script_job` (importar `generate_script_from_raw` arriba junto a los otros imports de `crew_service`):

```python
def run_raw_script_job(
    job_id: str, channel_id: int, raw_text: str, title: str, minutes: int
) -> None:
    """Congreso de agentes sobre materia prima: termina con el guion editable.

    A diferencia de run_script_job NO crea el episodio: el resultado vive en
    el job (result.script_text) hasta que el usuario confirma desde la UI.
    """
    session = SessionLocal()
    try:
        channel = session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            registry.fail(job_id, "Channel not found")
            return
        registry.emit(job_id, "load", "Material cargado, el congreso empieza a trabajar…")
        script = generate_script_from_raw(
            channel, raw_text, title,
            target_minutes=minutes, on_progress=_progress(job_id),
        )
        word_count = len(script.split())
        registry.emit(job_id, "done", f"Guion listo: {word_count} palabras")
        registry.finish(job_id, {"script_text": script, "title": title, "word_count": word_count})
    except Exception as e:
        session.rollback()
        registry.fail(job_id, str(e))
    finally:
        session.close()


def start_raw_script_job(
    channel: Channel, raw_text: str, title: str, minutes: int = 10
) -> str | None:
    return _start(
        "script",
        f"Guion con IA: {channel.name}",
        f"script:channel:{channel.id}:raw",
        lambda job_id: run_raw_script_job(job_id, channel.id, raw_text, title, minutes),
    )
```

- [ ] **Step 4: Implementar el endpoint en channels.py**

1. En el import de automation_service (línea ~19) añadir `start_raw_script_job`.
2. Tras el endpoint `create_from_text` (línea ~339), añadir:

```python
@router.post("/{channel_id}/script-jobs", status_code=202)
def create_script_job(
    channel_id: int,
    script: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Lanza el congreso de agentes sobre materia prima (txt/md o texto pegado).

    Devuelve 202 + job_id; el progreso se sigue en /api/jobs/{job_id}/events y
    el resultado (guion editable) llega en el evento final. No crea episodio:
    la UI lo crea con create-from-text tras la edición del usuario.
    """
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    raw_text = ""
    if script is not None:
        try:
            raw_text = script.file.read().decode("utf-8", errors="replace")
        finally:
            script.file.close()
        if not title and script.filename:
            title = Path(script.filename).stem
    elif text:
        raw_text = text

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No hay material: sube un .txt/.md o pega texto")

    title = (title or f"Episodio de {channel.name}").strip()
    minutes = max(2, min(int(channel.target_minutes or 10), 30))
    job_id = start_raw_script_job(channel, raw_text, title, minutes)
    if job_id is None:
        raise HTTPException(status_code=409, detail="Ya hay un guion en generación para este canal")
    return {"job_id": job_id}
```

- [ ] **Step 5: Correr tests**

Run: `python -m pytest backend/tests/test_script_jobs.py -v`
Expected: PASS (7 tests).

- [ ] **Step 6: Suite backend completa**

Run: `python -m pytest backend/tests -x -q --tb=short`
Expected: PASS (salvo los 7 fallos preexistentes de `test_platform.py`, que fallan igual en master).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/automation_service.py backend/app/routes/channels.py backend/tests/test_script_jobs.py
git commit -m "feat(api): script-jobs — congreso de agentes sobre materia prima cruda"
```

---

### Task 4: Frontend — api client + episodeStore

**Files:**
- Modify: `frontend/src/api/client.ts:106` y sección de channels (~linea 171)
- Modify: `frontend/src/stores/episodeStore.ts:10,24-32`

- [ ] **Step 1: api client**

En `client.ts`, reemplazar `getEpisodes`:

```ts
getEpisodes: (channelId?: number) =>
  fetchJson<Episode[]>(channelId ? `/episodes?channel_id=${channelId}` : '/episodes'),
```

Añadir junto a `createFromText` (sección channels):

```ts
startScriptJob: (channelId: number, input: { file?: File; text?: string; title?: string }) => {
  const form = new FormData()
  if (input.file) form.append('script', input.file)
  if (input.text) form.append('text', input.text)
  if (input.title) form.append('title', input.title)
  return fetchJson<{ job_id: string }>(`/channels/${channelId}/script-jobs`, {
    method: 'POST',
    body: form,
  })
},
```

**Importante:** `fetchJson`/`buildHeaders` fijan `Content-Type: application/json`, lo que rompe FormData. Verificar cómo lo maneja `uploadScript` (linea ~171) y aplicar el mismo mecanismo (si `uploadScript` hace fetch a mano, extraer un helper `fetchForm` sin Content-Type y usarlo en ambos). Si `buildHeaders` ya omite el header para FormData, basta con lo anterior.

- [ ] **Step 2: episodeStore**

```ts
fetchEpisodes: (channelId?: number) => Promise<void>
```

y en la implementación: `const episodes = await api.getEpisodes(channelId)`.

- [ ] **Step 3: Verificar compilación**

Run: `cd frontend && npx tsc --noEmit`
Expected: sin errores (o solo los preexistentes).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/stores/episodeStore.ts
git commit -m "feat(web): cliente startScriptJob y filtro por canal en episodios"
```

---

### Task 5: Frontend — componente `LlmSelector`

**Files:**
- Create: `frontend/src/components/channel-hub/LlmSelector.tsx`

Extrae las lineas 36-139 de `frontend/src/routes/studio.tsx` (state de providers/models + badge de estado + dos selects) en un componente autocontenido. Se usa luego en PlanTab (Task 7).

```tsx
import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { LlmProvider } from '../../types'

export default function LlmSelector() {
  const [providers, setProviders] = useState<LlmProvider[]>([])
  const [currentProvider, setCurrentProvider] = useState<string>('')
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, string[]>>({})
  const [currentModel, setCurrentModel] = useState<string>('')

  useEffect(() => {
    api.getLlmProviders()
      .then((d) => {
        setProviders(d.providers)
        setCurrentProvider(d.current_provider)
        setCurrentModel(d.current_model)
        d.providers.forEach((p) => {
          if (!p.available) return
          api.getLlmModels(p.id)
            .then((m) => {
              setModelsByProvider((prev) => ({ ...prev, [m.provider]: m.models }))
              if (p.id === d.current_provider && !m.models.includes(d.current_model)) {
                setCurrentModel(m.models[0] || '')
              }
            })
            .catch(() => {})
        })
      })
      .catch(() => setProviders([]))
  }, [])

  const activeProvider = providers.find((p) => p.id === currentProvider)
  const llmOk = activeProvider?.available ?? false

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {activeProvider && (
        <span
          className={`text-xs px-2 py-1 rounded-lg border ${
            llmOk
              ? 'bg-green-500/15 border-green-500/40 text-green-300'
              : 'bg-amber-500/15 border-amber-500/40 text-amber-300'
          }`}
          title={llmOk ? undefined : 'Provider no disponible'}
        >
          {llmOk ? `● ${activeProvider.name} lista` : `● ${activeProvider.name} no disponible`}
        </span>
      )}
      <label className="flex items-center gap-1 text-xs text-slate-400">
        Provider:
        <select
          className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-1 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={currentProvider}
          onChange={async (e) => {
            const provider = e.target.value
            setCurrentProvider(provider)
            const models = modelsByProvider[provider] || []
            const model = models[0] || ''
            setCurrentModel(model)
            if (model) await api.setLlmModel(provider, model)
          }}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.available}>
              {p.name} {!p.available ? '(no configurado)' : ''}
            </option>
          ))}
        </select>
      </label>
      {currentProvider && (modelsByProvider[currentProvider]?.length ?? 0) > 0 && (
        <label className="flex items-center gap-1 text-xs text-slate-400">
          Modelo:
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-1 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={currentModel}
            onChange={async (e) => {
              const model = e.target.value
              setCurrentModel(model)
              await api.setLlmModel(currentProvider, model)
            }}
          >
            {modelsByProvider[currentProvider]?.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}
```

- [ ] **Commit**

```bash
git add frontend/src/components/channel-hub/LlmSelector.tsx
git commit -m "feat(web): extrae LlmSelector desde studio"
```

---

### Task 6: Frontend — ruta hub `/channels/$id` (header + tabs)

**Files:**
- Create: `frontend/src/routes/channels.$id.tsx`
- Create: `frontend/src/components/channel-hub/PlanTab.tsx` (stub en este task, se completa en Task 7)
- Create: `frontend/src/components/channel-hub/EpisodesTab.tsx` (stub, Task 8)
- Create: `frontend/src/components/channel-hub/ConfigTab.tsx` (stub, Task 9)

- [ ] **Step 1: Crear la ruta con header y tabs**

`frontend/src/routes/channels.$id.tsx`:

```tsx
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { useAppStore } from '../stores/appStore'
import ChannelSelector from '../components/ChannelSelector'
import UploadScriptModal from '../components/UploadScriptModal'
import GenerateScriptWizard from '../components/GenerateScriptWizard'
import PlanTab from '../components/channel-hub/PlanTab'
import EpisodesTab from '../components/channel-hub/EpisodesTab'
import ConfigTab from '../components/channel-hub/ConfigTab'

type HubTab = 'plan' | 'episodios' | 'config'

export const Route = createFileRoute('/channels/$id')({
  validateSearch: (search: Record<string, unknown>): { tab: HubTab } => ({
    tab: ['plan', 'episodios', 'config'].includes(search.tab as string)
      ? (search.tab as HubTab)
      : 'plan',
  }),
  component: ChannelHubPage,
})

function ChannelHubPage() {
  const { id } = Route.useParams()
  const { tab } = Route.useSearch()
  const navigate = useNavigate()
  const channelId = Number(id)
  const {
    channels, error, fetchChannels, deleteChannel,
    publishChannel, unpublishChannel, fetchPlanEntries,
  } = useChannelStore()
  const askConfirm = useAppStore((s) => s.askConfirm)
  const [showUpload, setShowUpload] = useState(false)
  const [showWizard, setShowWizard] = useState(false)

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  useEffect(() => {
    fetchPlanEntries(channelId)
  }, [channelId, fetchPlanEntries])

  const channel = channels.find((c) => c.id === channelId)

  if (!channel) {
    return <div className="text-slate-400">Cargando canal...</div>
  }

  const handleDelete = async () => {
    const ok = await askConfirm({
      title: 'Eliminar canal',
      message: `¿Seguro que quieres eliminar "${channel.name}"? Esta acción no se puede deshacer.`,
      confirmLabel: 'Eliminar',
      danger: true,
    })
    if (ok) {
      await deleteChannel(channel.id)
      navigate({ to: '/channels' })
    }
  }

  return (
    <div>
      {/* Header del canal */}
      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-4">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <ChannelSelector
                channels={channels}
                value={channel.id}
                onChange={(newId) =>
                  navigate({ to: '/channels/$id', params: { id: String(newId) }, search: { tab } })
                }
                compact
              />
              <span className={`text-xs px-2 py-1 rounded-lg border ${channel.is_active ? 'bg-green-500/15 border-green-500/40 text-green-300' : 'bg-slate-700/50 border-slate-600 text-slate-400'}`}>
                {channel.is_active ? 'Activo' : 'Inactivo'}
              </span>
              {channel.autopilot && (
                <span className="text-xs px-2 py-1 rounded-lg border bg-violet-500/15 border-violet-500/40 text-violet-300" title="Piloto automático">🤖 Autopiloto</span>
              )}
              {channel.published_at && (
                <span className="text-xs px-2 py-1 rounded-lg border bg-emerald-500/15 border-emerald-500/40 text-emerald-300">Publicado</span>
              )}
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-100">{channel.name}</h2>
            <p className="text-sm text-slate-400 mt-1">{channel.description || 'Sin descripción'}</p>
            <p className="text-xs text-slate-500 mt-2">
              {channel.format} · nicho: {channel.niche || 'general'} · {channel.target_minutes} min · {channel.episodes_per_week} episodios/semana · {channel.num_speakers} voz{channel.num_speakers > 1 ? 'es' : ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setShowUpload(true)}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors"
            >
              Cargar guion
            </button>
            <button
              type="button"
              onClick={() => setShowWizard(true)}
              className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-500 transition-colors"
            >
              Generar guion con IA
            </button>
            {channel.published_at ? (
              <button type="button" onClick={() => unpublishChannel(channel.id)}
                className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                Desmarcar publicado
              </button>
            ) : (
              <button type="button" onClick={() => publishChannel(channel.id)}
                className="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-500 transition-colors">
                Marcar publicado
              </button>
            )}
            <button type="button" onClick={handleDelete}
              className="bg-red-600/80 text-white px-4 py-2 rounded-lg hover:bg-red-500 transition-colors">
              Eliminar
            </button>
          </div>
        </div>
        {error && (
          <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mt-4">Error: {error}</div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {([['plan', 'Plan editorial'], ['episodios', 'Episodios'], ['config', 'Configuración']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => navigate({ to: '/channels/$id', params: { id }, search: { tab: key } })}
            className={`px-3 py-1 rounded-lg text-sm border ${
              tab === key
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'plan' && <PlanTab channel={channel} />}
      {tab === 'episodios' && <EpisodesTab channel={channel} />}
      {tab === 'config' && <ConfigTab channel={channel} />}

      {showUpload && (
        <UploadScriptModal
          channel={channel}
          onClose={() => setShowUpload(false)}
          onUploaded={(episodeId) => navigate({ to: '/queue', search: { highlight: episodeId } })}
        />
      )}
      {showWizard && (
        <GenerateScriptWizard channel={channel} onClose={() => setShowWizard(false)} />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Stubs de los tabs**

`PlanTab.tsx`, `EpisodesTab.tsx`, `ConfigTab.tsx` (en `frontend/src/components/channel-hub/`):

```tsx
import { Channel } from '../../types'

export default function PlanTab({ channel }: { channel: Channel }) {
  return <p className="text-slate-400">Plan editorial de {channel.name} (en construcción).</p>
}
```

(idéntica estructura para los otros dos).

- [ ] **Step 3: Stub del wizard**

Crear `frontend/src/components/GenerateScriptWizard.tsx` temporal (se implementa en Task 10):

```tsx
import { Channel } from '../types'

export default function GenerateScriptWizard({ channel, onClose }: { channel: Channel; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6">
        <p className="text-slate-300">Wizard de {channel.name} (en construcción).</p>
        <button onClick={onClose} className="mt-4 bg-slate-700 px-4 py-2 rounded-lg text-white">Cerrar</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verificar build**

Run: `cd frontend && npm run build`
Expected: build OK (routeTree.gen.ts regenera la ruta nueva).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/channels.\$id.tsx frontend/src/components/channel-hub frontend/src/components/GenerateScriptWizard.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(web): hub de canal /channels/\$id con header y tabs"
```

---

### Task 7: Frontend — PlanTab completo

**Files:**
- Modify: `frontend/src/components/channel-hub/PlanTab.tsx`

Reúne lo que hoy está repartido entre `studio.tsx` (tab Plan + selector LLM + Generar ideas/temporada) y `channels.$id.plan.tsx` (progreso, temporadas, lista/calendario, CongressTable).

```tsx
import { useState } from 'react'
import { useChannelStore } from '../../stores/channelStore'
import ContentPlanList from '../ContentPlanList'
import PlanCalendar from '../PlanCalendar'
import CongressTable from '../CongressTable'
import LlmSelector from './LlmSelector'
import { Channel } from '../../types'

export default function PlanTab({ channel }: { channel: Channel }) {
  const {
    entries, loading, generatePlan, generateSeason,
    approveEntry, rejectEntry, deleteEntry,
  } = useChannelStore()
  const [count, setCount] = useState(5)
  const [seasonFilter, setSeasonFilter] = useState<number | null>(null)
  const [view, setView] = useState<'list' | 'calendar'>('list')

  const planEntries = entries[channel.id] || []
  const total = channel.entries_total ?? planEntries.length
  const generated = channel.entries_generated ?? planEntries.filter((e) => e.status === 'generated').length
  const pct = total > 0 ? Math.round((generated / total) * 100) : 0
  const seasons = [...new Set(planEntries.map((e) => e.season ?? 1))].sort((a, b) => a - b)
  const filtered = seasonFilter === null
    ? planEntries
    : planEntries.filter((e) => (e.season ?? 1) === seasonFilter)

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-3">
        <LlmSelector />
        <div className="flex gap-2 items-center flex-wrap">
          <select
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            title="Número de ideas"
          >
            {[3, 5, 8].map((n) => <option key={n} value={n}>{n} ideas</option>)}
          </select>
          <button
            type="button"
            disabled={loading}
            onClick={() => generatePlan(channel.id, count)}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50"
          >
            Generar con IA
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => generateSeason(channel.id, 4)}
            className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50"
          >
            📅 Planificar temporada
          </button>
          <button
            type="button"
            onClick={() => setView(view === 'list' ? 'calendar' : 'list')}
            className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors"
          >
            {view === 'list' ? '📅 Calendario' : '📋 Lista'}
          </button>
        </div>
      </div>

      {total > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-slate-400 mb-1">
            <span>{generated}/{total} capítulos generados</span>
            <span>{pct}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div className="bg-green-500 h-2 rounded-full" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {seasons.length > 1 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <button type="button" onClick={() => setSeasonFilter(null)}
            className={`px-3 py-1 rounded-lg text-sm ${seasonFilter === null ? 'bg-purple-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'}`}>
            Todas
          </button>
          {seasons.map((s) => (
            <button key={s} type="button" onClick={() => setSeasonFilter(s)}
              className={`px-3 py-1 rounded-lg text-sm ${seasonFilter === s ? 'bg-purple-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'}`}>
              Temporada {s}
            </button>
          ))}
        </div>
      )}

      <CongressTable />

      {view === 'list' ? (
        <ContentPlanList entries={filtered} onApprove={approveEntry} onReject={rejectEntry} onDelete={deleteEntry} />
      ) : (
        <PlanCalendar entries={filtered} />
      )}
    </div>
  )
}
```

Nota: verificar en `channelStore` que `generatePlan(channelId, count)` y `generateSeason(channelId, weeks)` existen con esa firma (studio.tsx los usa así). El plan antiguo de `channels.$id.plan.tsx` pasaba `count` por defecto del endpoint; aquí se pasa el `count` elegido.

- [ ] **Verificar build** — `cd frontend && npm run build` → OK.
- [ ] **Commit**

```bash
git add frontend/src/components/channel-hub/PlanTab.tsx
git commit -m "feat(web): PlanTab del hub (LLM, temporadas, calendario, congreso)"
```

---

### Task 8: Frontend — EpisodesTab + botón "Editar guion" en EpisodeCard

**Files:**
- Modify: `frontend/src/components/channel-hub/EpisodesTab.tsx`
- Modify: `frontend/src/components/EpisodeCard.tsx` (añadir botón + modal)
- Reutiliza: `EpisodeCard`, `ScriptEditorModal`, `episodeStore`

- [ ] **Step 1: Conectar ScriptEditorModal en EpisodeCard**

En `EpisodeCard.tsx`:
1. Añadir imports: `useState` (si no está), `ScriptEditorModal`.
2. En el componente: `const [editing, setEditing] = useState(false)`.
3. En la fila de acciones (junto a los botones existentes, antes de "Eliminar"), añadir:

```tsx
<button
  type="button"
  onClick={() => setEditing(true)}
  className="text-amber-400 hover:text-amber-300 text-sm hover:underline transition-colors"
>
  Editar guion
</button>
```

4. Al final del JSX del card (antes del cierre):

```tsx
{editing && (
  <ScriptEditorModal episode={episode} onClose={() => setEditing(false)} />
)}
```

- [ ] **Step 2: EpisodesTab**

```tsx
import { useEffect, useState } from 'react'
import { useEpisodeStore } from '../../stores/episodeStore'
import EpisodeCard from '../EpisodeCard'
import { Channel } from '../../types'

export default function EpisodesTab({ channel }: { channel: Channel }) {
  const {
    episodes, loading, error,
    fetchEpisodes, deleteEpisode, retryEpisode,
  } = useEpisodeStore()
  const [filter, setFilter] = useState<'all' | 'unpublished' | 'published'>('all')

  useEffect(() => {
    fetchEpisodes(channel.id)
  }, [channel.id, fetchEpisodes])

  const channelEpisodes = episodes.filter((e) => e.channel_id === channel.id)
  const visible = channelEpisodes.filter((e) => {
    if (filter === 'unpublished') return !e.published_at
    if (filter === 'published') return !!e.published_at
    return true
  })

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {([['all', 'Todos'], ['unpublished', 'Sin publicar'], ['published', 'Publicados']] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`px-3 py-1 rounded-lg text-sm border ${
              filter === key
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">Error: {error}</div>
      )}
      {loading && <div className="text-slate-400">Cargando episodios...</div>}
      {!loading && visible.length === 0 && (
        <p className="text-slate-400">No hay episodios{filter !== 'all' ? ' con este filtro' : ''} en este canal. Usa «Cargar guion» o «Generar guion con IA».</p>
      )}
      <div className="space-y-3">
        {visible.map((episode) => (
          <EpisodeCard
            key={episode.id}
            episode={episode}
            onDelete={deleteEpisode}
            onRetry={retryEpisode}
          />
        ))}
      </div>
    </div>
  )
}
```

Nota: `EpisodeCard` muestra el audio con `episode.audio_url` (ruta `/outputs/...` servida por el backend — funciona también fuera de /queue; verificar en implementation que no dependa del contexto de la página).

- [ ] **Step 3: Verificar build + tests existentes**

Run: `cd frontend && npm run build && npx vitest run`
Expected: build OK; vitest PASS (EpisodeCard.test puede necesitar actualización si el render cambia — ajustar si falla).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/channel-hub/EpisodesTab.tsx frontend/src/components/EpisodeCard.tsx frontend/src/components/__tests__
git commit -m "feat(web): EpisodesTab del hub y editor de guion en EpisodeCard"
```

---

### Task 9: Frontend — ConfigTab (ChannelForm con voces de diálogo)

**Files:**
- Modify: `frontend/src/components/ChannelForm.tsx` (añadir `num_speakers` + `speaker_voices` al formulario y al submit)
- Modify: `frontend/src/components/channel-hub/ConfigTab.tsx`

- [ ] **Step 1: Extender ChannelForm**

En `ChannelForm.tsx`:

1. Añadir state:

```tsx
const [numSpeakers, setNumSpeakers] = useState(initial?.num_speakers ?? 1)
const [speakerVoices, setSpeakerVoices] = useState<Record<string, string>>(
  initial?.speaker_voices ?? {}
)
```

2. En `handleSubmit`, añadir al payload: `num_speakers: numSpeakers, speaker_voices: numSpeakers > 1 ? speakerVoices : null`.
3. En el JSX (tras el select de `voiceId`, visible siempre; la sección de diálogo solo cuando `numSpeakers === 2`), insertar:

```tsx
<label className="block">
  <span className="text-sm text-slate-400">Número de voces</span>
  <select
    className="mt-1 w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
    value={numSpeakers}
    onChange={(e) => {
      const n = Number(e.target.value)
      setNumSpeakers(n)
      if (n > 1 && Object.keys(speakerVoices).length === 0) {
        setSpeakerVoices({ Narrador: voiceId, Invitado: voiceId })
      }
    }}
  >
    <option value={1}>1 voz (monólogo)</option>
    <option value={2}>2 voces (diálogo)</option>
  </select>
</label>

{numSpeakers > 1 && (
  <div className="block md:col-span-2">
    <span className="text-sm text-slate-400">Voces del diálogo</span>
    <div className="mt-2 space-y-2">
      {Object.entries(speakerVoices).map(([speaker, vId]) => (
        <div key={speaker} className="flex gap-2 items-center">
          <input
            className="w-32 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={speaker}
            onChange={(e) => {
              const next = { ...speakerVoices }
              delete next[speaker]
              next[e.target.value] = vId
              setSpeakerVoices(next)
            }}
          />
          <select
            className="flex-1 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={vId}
            onChange={(e) => setSpeakerVoices({ ...speakerVoices, [speaker]: e.target.value })}
          >
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.type === 'cloned' ? '🎙️ ' : ''}{v.name}
              </option>
            ))}
          </select>
        </div>
      ))}
    </div>
  </div>
)}
```

(El campo `target_minutes` y `episodes_per_week` ya existen en el formulario; verificar que se incluyan en el submit — si ChannelForm actual no los envía, añadirlos: `target_minutes: targetMinutes`, `episodes_per_week: episodesPerWeek` con sus inputs existentes o nuevos inputs numéricos.)

- [ ] **Step 2: ConfigTab**

```tsx
import { useEffect } from 'react'
import { useChannelStore } from '../../stores/channelStore'
import { useVoiceStore } from '../../stores/voiceStore'
import { useAppStore } from '../../stores/appStore'
import ChannelForm from '../ChannelForm'
import { Channel, CreateChannelRequest } from '../../types'

export default function ConfigTab({ channel }: { channel: Channel }) {
  const { updateChannel } = useChannelStore()
  const { voices, fetchVoices } = useVoiceStore()
  const pushToast = useAppStore((s) => s.pushToast)

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  const handleSubmit = async (data: CreateChannelRequest) => {
    await updateChannel(channel.id, data)
    pushToast({ kind: 'success', message: 'Canal actualizado' })
  }

  return (
    <div className="max-w-2xl">
      <p className="text-sm text-slate-400 mb-4">
        Cambios con guardado explícito. El formato y la voz se usan al generar guiones con IA.
      </p>
      <ChannelForm voices={voices} initial={channel} onSubmit={handleSubmit} onCancel={() => {}} submitLabel="Guardar cambios" />
    </div>
  )
}
```

Si `ChannelForm` no tiene prop `submitLabel`, añadirla (opcional, default "Crear canal"/"Guardar"). Verificar la firma real de `updateChannel` en channelStore (acepta `Partial<CreateChannelRequest>`).

- [ ] **Step 3: Tests**

Ampliar `frontend/src/components/__tests__/ChannelForm.test.tsx` con un caso: al elegir "2 voces", aparecen los selectores de diálogo y el submit incluye `num_speakers: 2` y `speaker_voices`. Seguir el patrón de tests existente (render + fireEvent + expect onSubmit mock).

Run: `cd frontend && npx vitest run`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ChannelForm.tsx frontend/src/components/channel-hub/ConfigTab.tsx frontend/src/components/__tests__/ChannelForm.test.tsx
git commit -m "feat(web): ConfigTab con voces de diálogo y guardado explícito"
```

---

### Task 10: Frontend — GenerateScriptWizard completo

**Files:**
- Modify: `frontend/src/components/GenerateScriptWizard.tsx` (reemplaza el stub)

- [ ] **Step 1: Implementación**

```tsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { api, sseUrl } from '../api/client'
import { Channel } from '../types'

type Step = 'source' | 'progress' | 'edit'

interface JobEvent {
  step: string
  message: string
  status?: string
  error?: string | null
  result?: { script_text?: string; title?: string; word_count?: number }
}

export default function GenerateScriptWizard({ channel, onClose }: { channel: Channel; onClose: () => void }) {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('source')
  const [file, setFile] = useState<File | null>(null)
  const [pasted, setPasted] = useState('')
  const [title, setTitle] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [events, setEvents] = useState<{ step: string; message: string }[]>([])
  const [jobError, setJobError] = useState<string | null>(null)
  const [script, setScript] = useState('')
  const [scriptTitle, setScriptTitle] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  const source = file ? file.name : pasted.trim() ? 'texto pegado' : ''
  const wordCount = useMemo(
    () => (script.trim() ? script.trim().split(/\s+/).length : 0),
    [script]
  )

  useEffect(() => () => esRef.current?.close(), [])

  const startJob = async () => {
    setJobError(null)
    setEvents([])
    try {
      const { job_id } = await api.startScriptJob(channel.id, {
        file: file ?? undefined,
        text: !file && pasted.trim() ? pasted : undefined,
        title: title.trim() || undefined,
      })
      setJobId(job_id)
      setStep('progress')
      const es = new EventSource(sseUrl(`/jobs/${job_id}/events`))
      esRef.current = es
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as JobEvent
          if (data.step === '__status__') {
            es.close()
            if (data.status === 'done' && data.result?.script_text) {
              setScript(data.result.script_text)
              setScriptTitle(title.trim() || data.result.title || '')
              setStep('edit')
            } else {
              setJobError(data.error || 'El congreso no devolvió guion')
            }
          } else {
            setEvents((prev) => [...prev, { step: data.step, message: data.message }])
          }
        } catch {
          // payload malformado: ignorar
        }
      }
      es.onerror = () => {
        es.close()
        setJobError('Conexión con el job perdida')
      }
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'No se pudo lanzar el congreso')
    }
  }

  const handleCreate = async () => {
    setCreating(true)
    setCreateError(null)
    try {
      const episode = await api.createFromText(channel.id, script, scriptTitle.trim() || undefined)
      onClose()
      navigate({ to: '/queue', search: { highlight: episode.id } })
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'No se pudo crear el episodio')
      setCreating(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget && step !== 'progress') onClose() }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 shrink-0">
          <h2 className="text-lg font-bold text-slate-100">Generar guion con IA — {channel.name}</h2>
          {step !== 'progress' && (
            <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none" aria-label="Cerrar">×</button>
          )}
        </div>

        {step === 'source' && (
          <div className="p-5 space-y-4 overflow-y-auto">
            <label className="block">
              <span className="text-sm text-slate-400">Título (opcional)</span>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="El caso que vas a contar..."
              />
            </label>
            <div>
              <span className="text-sm text-slate-400">Materia prima (.txt o .md)</span>
              <input
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="mt-1 block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-slate-700 file:text-slate-100 hover:file:bg-slate-600"
              />
            </div>
            <div className="text-center text-slate-500 text-sm">— o pega el texto —</div>
            <textarea
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              rows={8}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Pega aquí notas, transcripciones, artículos..."
            />
            {jobError && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg">{jobError}</div>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                Cancelar
              </button>
              <button
                onClick={startJob}
                disabled={!file && !pasted.trim()}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Lanzar congreso 🎬
              </button>
            </div>
          </div>
        )}

        {step === 'progress' && (
          <div className="p-5 overflow-y-auto">
            <p className="text-sm text-slate-300 mb-3">
              El congreso está trabajando sobre «{source}». Puede tardar varios minutos.
            </p>
            <div className="space-y-1">
              {events.map((ev, i) => (
                <div key={i} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-purple-400">✓</span>
                  <span>{ev.message}</span>
                </div>
              ))}
              <div className="text-sm text-slate-400 flex gap-2">
                <span className="animate-pulse">●</span>
                <span>trabajando…</span>
              </div>
            </div>
            {jobError && (
              <div className="mt-4 bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg">
                {jobError}
                <div className="flex gap-2 mt-3">
                  <button onClick={() => setStep('source')} className="bg-slate-700 text-slate-100 px-3 py-1 rounded-lg text-sm hover:bg-slate-600">
                    Volver y reintentar
                  </button>
                  <button onClick={onClose} className="bg-slate-700 text-slate-100 px-3 py-1 rounded-lg text-sm hover:bg-slate-600">
                    Descartar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {step === 'edit' && (
          <div className="flex-1 min-h-0 flex flex-col p-5 gap-3 overflow-hidden">
            <input
              type="text"
              value={scriptTitle}
              onChange={(e) => setScriptTitle(e.target.value)}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Título del episodio"
            />
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              className="flex-1 min-h-[40vh] w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-purple-500"
              spellCheck={false}
            />
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="text-xs text-slate-500">
                {wordCount.toLocaleString()} palabras · ~{Math.max(1, Math.round(wordCount / 140))} min
              </span>
              <div className="flex gap-2">
                <button onClick={() => setStep('source')} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                  Regenerar
                </button>
                <button onClick={onClose} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                  Descartar
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !script.trim()}
                  className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50"
                >
                  {creating ? 'Creando…' : 'Crear episodio'}
                </button>
              </div>
            </div>
            {createError && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg">{createError}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

Notas de implementación:
- Verificar que `pushToast` existe en `appStore` con esa firma (se añadió en el trabajo anterior de toasts); si no, omitir toasts.
- `api.createFromText` ya existe en client.ts (linea ~180).

- [ ] **Step 2: Test del wizard**

Crear `frontend/src/components/__tests__/GenerateScriptWizard.test.tsx` (patrón MockEventSource de `useEpisodeSSE.test.ts`):

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import GenerateScriptWizard from '../GenerateScriptWizard'
import { api } from '../../api/client'

jest.mock('../../api/client', () => ({
  api: {
    startScriptJob: jest.fn(),
    createFromText: jest.fn(),
  },
  sseUrl: (p: string) => p,
}))

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  closed = false
  constructor(url: string) { this.url = url; MockEventSource.instances.push(this) }
  close() { this.closed = true }
  emit(data: object) { this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent) }
}

const channel = { id: 3, name: 'Crimenes', format: 'podcast' } as never

describe('GenerateScriptWizard', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    ;(global as unknown as { EventSource: unknown }).EventSource = MockEventSource
    jest.clearAllMocks()
  })

  it('fuente → progreso → edición → crear episodio', async () => {
    ;(api.startScriptJob as jest.Mock).mockResolvedValue({ job_id: 'job1' })
    ;(api.createFromText as jest.Mock).mockResolvedValue({ id: 99 })

    render(<GenerateScriptWizard channel={channel} onClose={() => {}} />)

    fireEvent.change(screen.getByPlaceholderText(/Pega aquí/), { target: { value: 'Material' } })
    fireEvent.click(screen.getByText('Lanzar congreso 🎬'))

    await waitFor(() => expect(api.startScriptJob).toHaveBeenCalledWith(3, expect.objectContaining({ text: 'Material' })))
    expect(screen.getByText(/trabajando/)).toBeInTheDocument()

    const es = MockEventSource.instances[0]
    es.emit({ step: 'research', message: 'Investigando…' })
    es.emit({ step: '__status__', status: 'done', result: { script_text: 'Guion final', title: 'T', word_count: 2 } })

    await waitFor(() => expect(screen.getByDisplayValue('Guion final')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Crear episodio'))

    await waitFor(() => expect(api.createFromText).toHaveBeenCalledWith(3, 'Guion final', undefined))
  })

  it('job con error muestra mensaje', async () => {
    ;(api.startScriptJob as jest.Mock).mockResolvedValue({ job_id: 'job2' })
    render(<GenerateScriptWizard channel={channel} onClose={() => {}} />)
    fireEvent.change(screen.getByPlaceholderText(/Pega aquí/), { target: { value: 'x' } })
    fireEvent.click(screen.getByText('Lanzar congreso 🎬'))
    await waitFor(() => expect(MockEventSource.instances.length).toBe(1))
    MockEventSource.instances[0].emit({ step: '__status__', status: 'error', error: 'LLM caído' })
    await waitFor(() => expect(screen.getByText(/LLM caído/)).toBeInTheDocument())
  })
})
```

(Ajustar imports/placeholder al texto real del componente; si el proyecto usa `vi.mock` en vez de `jest.mock` — vitest con globals — usar el estilo de los tests existentes.)

- [ ] **Step 3: Correr tests + build**

Run: `cd frontend && npx vitest run && npm run build`
Expected: PASS + build OK.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/GenerateScriptWizard.tsx frontend/src/components/__tests__/GenerateScriptWizard.test.tsx
git commit -m "feat(web): wizard Generar guion con IA (fuente → congreso → edición → cola)"
```

---

### Task 11: Frontend — redirects, navegación y limpieza de Studio

**Files:**
- Modify: `frontend/src/routes/channels.$id.plan.tsx` → redirect
- Modify: `frontend/src/routes/channels.$id.edit.tsx` → redirect
- Modify: `frontend/src/routes/studio.tsx` → redirect
- Modify: `frontend/src/components/Layout.tsx:55` (quitar Studio)
- Modify: `frontend/src/components/ChannelCard.tsx` ("Ver plan" → hub)
- Delete: `frontend/src/components/StudioPanel.tsx`

- [ ] **Step 1: Redirects**

`channels.$id.plan.tsx` completo:

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/channels/$id/plan')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/channels/$id', params: { id: params.id }, search: { tab: 'plan' } })
  },
})
```

`channels.$id.edit.tsx` completo:

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/channels/$id/edit')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/channels/$id', params: { id: params.id }, search: { tab: 'config' } })
  },
})
```

`studio.tsx` completo:

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/studio')({
  beforeLoad: () => {
    throw redirect({ to: '/channels' })
  },
})
```

- [ ] **Step 2: Layout** — quitar la línea `{ to: '/studio', label: 'Studio', Icon: FilmIcon },` de `NAV_ITEMS`. (Si `FilmIcon` queda sin usar, eliminar su definición.)

- [ ] **Step 3: ChannelCard** — cambiar el link "Ver plan":

```tsx
<Link
  to="/channels/$id"
  params={{ id: String(channel.id) }}
  search={{ tab: 'plan' }}
  className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors"
>
  Ver plan
</Link>
```

(El `Link` de TanStack acepta `search`; verificar tipo — si el target requiere search validada, la ruta `/channels/$id` ya la tiene.)

- [ ] **Step 4: Borrar StudioPanel**

```bash
git rm frontend/src/components/StudioPanel.tsx
```

Verificar que nada más lo importa: `grep -rn "StudioPanel" frontend/src` → solo el archivo borrado.

- [ ] **Step 5: Verificar build + tests completos**

Run: `cd frontend && npm run build && npx vitest run`
Expected: build OK; todos los tests PASS.

- [ ] **Step 6: Commit**

```bash
git add -A frontend/src
git commit -m "refactor(web): elimina Studio; redirecciones y navegación al hub"
```

---

### Task 12: Verificación completa local

- [ ] **Step 1: Suite backend**

Run: `python -m pytest backend/tests -q --tb=short`
Expected: PASS salvo los 7 fallos preexistentes de test_platform.py (verificados en master).

- [ ] **Step 2: Suite frontend**

Run: `cd frontend && npx vitest run`
Expected: PASS (todos, incluidos los nuevos).

- [ ] **Step 3: Builds**

Run: `cd frontend && npm run build`
Expected: OK.

- [ ] **Step 4: Worker intacto**

Run: `tail -5 logs/worker.log` — el worker sigue corriendo (no se tocó).

---

### Task 13: Push, deploy Dokploy y validación en producción

- [ ] **Step 1: Push**

```bash
git push origin master
```

- [ ] **Step 2: Deploys**

- Confirmar auto-deploy de `podcash-web` y `podcash-api` en Dokploy (MCP `dokploy.deployment-all` para ambas appIds: web `EvKd8T4NRjaCtC7If0ryx`, api `upqUVo_VoWUtINjk0VvNB`). Si el api no se disparó, `application-redeploy`.
- Esperar a `status: done` en ambos.

- [ ] **Step 3: Validación API**

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.podcash.app.moonsbow.com/api/health   # 200
curl -s "https://api.podcash.app.moonsbow.com/api/episodes?channel_id=3" | head -c 200   # JSON array
curl -s -X POST "https://api.podcash.app.moonsbow.com/api/channels/3/script-jobs" -H "Authorization: Bearer $TOKEN" -F "text=Material de prueba"  # 202 job_id (o 409 si hay uno en curso)
```

(TOKEN: login admin/admin como en sesiones anteriores.)

- [ ] **Step 4: Smoke test Playwright en producción**

Con playwright MCP: login en https://podcash.app.moonsbow.com → abrir `/channels/3` → verificar header del hub, los 3 tabs → tab Episodios lista episodios del canal → abrir `/studio` y verificar redirect a `/channels` → abrir wizard (sin lanzar el congreso en producción, o lanzarlo y verificar 202 si se quiere una prueba real con LLM).

- [ ] **Step 5: Commit final si hubo ajustes**

```bash
git add -A && git commit -m "chore: ajustes post-validación" && git push origin master
```

- [ ] **Step 6: Reporte final** — resumen en español: qué se implementó, estado del deploy, validaciones, deuda conocida.
