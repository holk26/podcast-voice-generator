# Kimi Provider, Worker GUI y Dokploy Docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Kimi as an available AI provider in the Studio UI, route LLM calls through the selected provider, give the local worker a simple tkinter status GUI, and document the Dokploy deploy in `AGENTS.md`.

**Architecture:** Extend the backend `llm_provider.py` to support multiple providers (Ollama and Kimi) behind a single `get_llm(provider, model)` interface. Expose provider/model metadata via new `/llm/*` endpoints. Update the Studio page to show a provider selector that drives the model selector. The worker gets a non-blocking tkinter window that displays connection state, current job, and recent logs. No audio is uploaded to the server; the worker keeps files local.

**Tech Stack:** FastAPI, CrewAI (LLM/OpenAI-compatible), Python 3.11, React + Vite + Tailwind, tkinter, PyYAML.

---

## File structure

| File | Responsibility |
|------|----------------|
| `backend/app/config.py` | Load `KIMI_API_KEY`, default provider/model, and persist `llm_provider`/`llm_model` to `config.yaml`. |
| `backend/app/services/llm_provider.py` | Multi-provider LLM factory: Ollama via `ollama/<model>` and Kimi via OpenAI-compatible endpoint. |
| `backend/app/routes/llm.py` | REST endpoints for providers, models, status, and setting the active provider+model. |
| `backend/app/services/crew_service.py` | Read active provider/model from config and pass them to `get_planning_llm()` / `get_script_llm()`. |
| `frontend/src/types/index.ts` | TypeScript types for `LlmProvider` and `LlmModelResponse`. |
| `frontend/src/api/client.ts` | API methods: `getLlmProviders`, `getLlmModels(provider)`, updated `setLlmModel`. |
| `frontend/src/routes/studio.tsx` | Provider + model selectors, availability badge. |
| `worker/gui.py` | New tkinter window showing worker connection/job/logs. |
| `worker/main.py` | Launch GUI thread when `WORKER_GUI=1`. |
| `AGENTS.md` | Dokploy deploy section. |

---

## Task 1: Backend config — add Kimi env vars and persistence

**Files:**
- Modify: `backend/app/config.py`
- Test: `python -c "from backend.app.config import KIMI_API_KEY, DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL; print(KIMI_API_KEY, DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL)"`

- [ ] **Step 1: Add env vars and default config values**

Insert after line 30 (`WORKER_TOKEN = ...`):

```python
# Kimi / OpenCode Go settings
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1")

# OpenCode Go (reserved for future use)
OPENCODEGO_API_KEY = os.getenv("OPENCODEGO_API_KEY", "")
OPENCODEGO_BASE_URL = os.getenv("OPENCODEGO_BASE_URL", "")
```

Replace lines 42-48 with:

```python
_LLM_CONFIG = _CONFIG.get("llm", {})

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", _LLM_CONFIG.get("base_url", "http://localhost:11434"))
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", _LLM_CONFIG.get("default_model", "llama3.1:8b"))

DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER",
                                 _LLM_CONFIG.get("provider", "ollama"))
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL",
                              _LLM_CONFIG.get("model", OLLAMA_DEFAULT_MODEL))
```

- [ ] **Step 2: Replace save_llm_model with save_llm_settings**

Replace lines 50-63 with:

```python
def save_llm_settings(provider: str, model: str) -> None:
    """Persiste el provider y modelo elegidos en config.yaml (sección llm)."""
    global _CONFIG, _LLM_CONFIG
    config_path = BASE_DIR / "config.yaml"
    data = dict(_CONFIG)
    llm = dict(data.get("llm", {}))
    llm["provider"] = provider
    llm["model"] = model
    data["llm"] = llm
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    _CONFIG = data
    _LLM_CONFIG = llm


def save_llm_model(model: str) -> None:
    """Compatibilidad legacy: ahora el provider y modelo se persisten juntos."""
    # Stub mantenido por posibles imports legacy. Usar save_llm_settings() o
    # llm_provider.set_current_settings() para cambios reales.
    pass
```

- [ ] **Step 3: Run smoke test**

Run:

```bash
python -c "from backend.app.config import KIMI_API_KEY, KIMI_BASE_URL, DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL; print(DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL, bool(KIMI_API_KEY))"
```

Expected: prints `ollama llama3.1:8b False` (assuming no env vars set).

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py
git commit -m "config: add Kimi env vars and llm provider/model persistence"
```

---

## Task 2: Backend llm_provider — multi-provider support

**Files:**
- Modify: `backend/app/services/llm_provider.py`
- Test: `python -c "from backend.app.services.llm_provider import list_providers, list_models, get_llm; print(list_providers())"`

- [ ] **Step 1: Implement provider helpers**

Replace the entire file content with:

```python
import json
import os
from pathlib import Path

from crewai import LLM

from backend.app.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    KIMI_API_KEY,
    KIMI_BASE_URL,
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
    save_llm_settings,
)

# Modelo/provider en uso (mutable en runtime; por defecto los de config.yaml)
_current_provider: str = DEFAULT_LLM_PROVIDER
_current_model: str = DEFAULT_LLM_MODEL


def _read_kimi_token_from_local_config() -> str:
    """Fallback local: lee el token de Kimi de su config de CLI."""
    home = Path.home()
    candidates = [
        home / ".kimi-code" / "credentials" / "kimi-code.json",
        home / ".kimi" / "credentials" / "kimi-code.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                token = data.get("access_token") or data.get("token") or data.get("api_key")
                if token:
                    return token
            except Exception:
                continue
    return ""


def get_kimi_api_key() -> str:
    return KIMI_API_KEY or _read_kimi_token_from_local_config()


def get_current_provider() -> str:
    return _current_provider


def get_current_model() -> str:
    return _current_model


def set_current_settings(provider: str, model: str) -> None:
    """Cambia provider+modelo en runtime y lo persiste en config.yaml."""
    global _current_provider, _current_model
    _current_provider = provider
    _current_model = model
    save_llm_settings(provider, model)


def get_llm(provider: str | None = None, model: str | None = None) -> LLM:
    p = provider or _current_provider
    m = model or _current_model

    if p == "kimi":
        api_key = get_kimi_api_key()
        if not api_key:
            raise RuntimeError("Kimi no está configurado: faltan KIMI_API_KEY o token local")
        return LLM(
            model=m,
            api_key=api_key,
            base_url=KIMI_BASE_URL,
        )

    if p == "ollama":
        return LLM(
            model=f"ollama/{m}",
            base_url=OLLAMA_BASE_URL,
        )

    raise ValueError(f"Provider de IA no soportado: {p}")


def get_planning_llm() -> LLM:
    return get_llm()


def get_script_llm() -> LLM:
    return get_llm()


def check_ollama() -> dict:
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_BASE_URL)
        models = [m["model"] for m in client.list()["models"]]
        return {
            "available": True,
            "base_url": OLLAMA_BASE_URL,
            "default_model": OLLAMA_DEFAULT_MODEL,
            "default_ready": OLLAMA_DEFAULT_MODEL in models,
            "models": models,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


def check_kimi() -> dict:
    api_key = get_kimi_api_key()
    if not api_key:
        return {"available": False, "error": "Kimi no configurado"}
    # Modelos conocidos; evitamos una llamada de red en el health check.
    return {
        "available": True,
        "base_url": KIMI_BASE_URL,
        "default_model": "kimi-for-coding",
        "models": ["kimi-for-coding", "kimi-for-coding-highspeed"],
    }


def list_providers() -> list[dict]:
    providers = []
    ollama_status = check_ollama()
    providers.append({
        "id": "ollama",
        "name": "Ollama",
        "available": ollama_status["available"],
        "default_model": OLLAMA_DEFAULT_MODEL,
    })

    kimi_status = check_kimi()
    providers.append({
        "id": "kimi",
        "name": "Kimi",
        "available": kimi_status["available"],
        "default_model": "kimi-for-coding",
    })
    return providers


def list_models(provider: str | None = None) -> dict:
    p = provider or _current_provider
    if p == "ollama":
        status = check_ollama()
        return {
            "provider": p,
            "current": _current_model if _current_provider == p else OLLAMA_DEFAULT_MODEL,
            "models": status.get("models", []) if status["available"] else [],
        }
    if p == "kimi":
        status = check_kimi()
        models = status.get("models", [])
        return {
            "provider": p,
            "current": _current_model if _current_provider == p else "kimi-for-coding",
            "models": models,
        }
    raise ValueError(f"Provider desconocido: {p}")
```

- [ ] **Step 2: Run provider smoke test**

Run:

```bash
python -c "from backend.app.services.llm_provider import list_providers, list_models; print(list_providers()); print(list_models('ollama'))"
```

Expected: JSON list with `ollama` and `kimi` providers (kimi `available: False` unless token is set).

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/llm_provider.py
git commit -m "feat(llm): add Kimi as an OpenAI-compatible provider"
```

---

## Task 3: Backend LLM routes — providers, models, and settings

**Files:**
- Modify: `backend/app/routes/llm.py`
- Test: `curl http://127.0.0.1:8000/api/llm/providers`

- [ ] **Step 1: Replace route file content**

Replace the entire file with:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.llm_provider import (
    check_kimi,
    check_ollama,
    get_current_model,
    get_current_provider,
    list_models,
    list_providers,
    set_current_settings,
)

router = APIRouter()


class SettingsRequest(BaseModel):
    provider: str
    model: str


@router.get("/status")
def llm_status():
    provider = get_current_provider()
    if provider == "kimi":
        return check_kimi()
    return check_ollama()


@router.get("/providers")
def llm_providers():
    return {
        "current_provider": get_current_provider(),
        "current_model": get_current_model(),
        "providers": list_providers(),
    }


@router.get("/models")
def llm_models(provider: str | None = None):
    try:
        return list_models(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/model")
def set_model(data: SettingsRequest):
    """Cambia el provider y modelo de IA activos (runtime + config.yaml)."""
    provider = data.provider.strip().lower()
    model = data.model.strip()
    if not provider or not model:
        raise HTTPException(status_code=400, detail="Provider y modelo son obligatorios")

    valid = {p["id"] for p in list_providers() if p["available"]}
    if provider not in valid:
        raise HTTPException(status_code=400, detail=f"Provider no disponible: {provider}")

    set_current_settings(provider, model)
    return {
        "current_provider": get_current_provider(),
        "current_model": get_current_model(),
    }
```

- [ ] **Step 2: Start API and test endpoints**

In one terminal:

```bash
python -m backend.app.main
```

In another:

```bash
curl -s http://127.0.0.1:8000/api/llm/providers | python3 -m json.tool
```

Expected: JSON with `current_provider`, `current_model`, and `providers` array.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/llm.py
git commit -m "feat(api): add /llm/providers, /llm/models and provider+model selection"
```

---

## Task 4: crew_service uses active provider/model

**Files:**
- Modify: `backend/app/services/crew_service.py`
- Test: `python -c "from backend.app.services.crew_service import generate_plan"` (just import check)

- [ ] **Step 1: Update imports and pass provider/model**

At the top, replace the import line with:

```python
from backend.app.config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from backend.app.services.llm_provider import get_planning_llm, get_script_llm
```

No other changes are strictly required because `get_planning_llm()` and `get_script_llm()` already use the runtime defaults. The existing agent definitions stay the same.

- [ ] **Step 2: Verify import**

Run:

```bash
python -c "from backend.app.services.crew_service import generate_plan, generate_script; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/crew_service.py
git commit -m "refactor(crew): import config defaults for llm provider/model"
```

---

## Task 5: Frontend types and API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Test: `npm run typecheck` or `npx tsc --noEmit`

- [ ] **Step 1: Add LLM types**

Append to `frontend/src/types/index.ts`:

```typescript
export interface LlmProvider {
  id: string
  name: string
  available: boolean
  default_model: string
}

export interface LlmProvidersResponse {
  current_provider: string
  current_model: string
  providers: LlmProvider[]
}

export interface LlmModelsResponse {
  provider: string
  current: string
  models: string[]
}

export interface LlmSettingsRequest {
  provider: string
  model: string
}
```

- [ ] **Step 2: Add API methods**

In `frontend/src/api/client.ts`, replace the LLM section (lines 152-160) with:

```typescript
  getLlmProviders: () =>
    fetchJson<LlmProvidersResponse>('/llm/providers'),
  getLlmModels: (provider?: string) =>
    fetchJson<LlmModelsResponse>(`/llm/models${provider ? `?provider=${encodeURIComponent(provider)}` : ''}`),
  setLlmModel: (provider: string, model: string) =>
    fetchJson<{ current_provider: string; current_model: string }>('/llm/model', {
      method: 'POST',
      body: JSON.stringify({ provider, model } as LlmSettingsRequest),
    }),
```

Ensure the new types are imported at the top of `client.ts`:

```typescript
import {
  ...
  LlmProvidersResponse,
  LlmModelsResponse,
  LlmSettingsRequest,
} from '../types'
```

- [ ] **Step 3: Type-check**

Run:

```bash
cd frontend && npx tsc --noEmit
```

Expected: no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend): add LLM provider/model types and api methods"
```

---

## Task 6: Studio page provider + model selectors

**Files:**
- Modify: `frontend/src/routes/studio.tsx`
- Test: Open `http://127.0.0.1:5173/studio` and verify selectors.

- [ ] **Step 1: Update state and effects**

Add to imports:

```typescript
import { LlmProvider } from '../types'
```

Replace the LLM state block (lines 41-44) with:

```typescript
  const [providers, setProviders] = useState<LlmProvider[]>([])
  const [currentProvider, setCurrentProvider] = useState<string>('')
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, string[]>>({})
  const [currentModel, setCurrentModel] = useState<string>('')
```

Replace the first `useEffect` (lines 49-59) with:

```typescript
  useEffect(() => {
    fetchChannels()
    fetchVoices()
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
  }, [fetchChannels, fetchVoices])
```

- [ ] **Step 2: Replace badge and model selector**

Replace lines 82-112 with:

```typescript
  const activeProvider = providers.find((p) => p.id === currentProvider)
  const llmOk = activeProvider?.available ?? false

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <h2 className="text-2xl font-bold tracking-tight">Studio</h2>
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
```

Also remove the extra `return (` that now duplicates the one already at line 78.

- [ ] **Step 3: Verify build**

Run:

```bash
cd frontend && npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/studio.tsx
git commit -m "feat(studio): add provider + model selectors for Kimi/Ollama"
```

---

## Task 7: Worker tkinter GUI

**Files:**
- Create: `worker/gui.py`
- Test: `python -c "from worker.gui import WorkerGui; print('ok')"`

- [ ] **Step 1: Create GUI module**

Create `worker/gui.py`:

```python
import logging
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

logger = logging.getLogger(__name__)


class WorkerGui:
    """Ventana tkinter simple de estado del worker."""

    def __init__(self, on_reconnect: Callable[[], None] | None = None) -> None:
        self.on_reconnect = on_reconnect
        self._queue: queue.Queue[dict] = queue.Queue()
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._status_var: tk.StringVar | None = None
        self._job_var: tk.StringVar | None = None
        self._log_box: scrolledtext.ScrolledText | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("Podcast Worker")
        self._root.geometry("600x400")
        self._root.configure(bg="#1e293b")

        self._status_var = tk.StringVar(value="Conectando...")
        self._job_var = tk.StringVar(value="Sin trabajo activo")

        header = tk.Label(
            self._root,
            text="Worker de Podcast",
            fg="#e2e8f0",
            bg="#1e293b",
            font=("Helvetica", 16, "bold"),
        )
        header.pack(pady=(12, 8))

        status_frame = tk.Frame(self._root, bg="#1e293b")
        status_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(status_frame, text="Estado:", fg="#94a3b8", bg="#1e293b", font=("Helvetica", 11)).pack(side="left")
        tk.Label(status_frame, textvariable=self._status_var, fg="#4ade80", bg="#1e293b", font=("Helvetica", 11, "bold")).pack(side="left", padx=(8, 0))

        job_frame = tk.Frame(self._root, bg="#1e293b")
        job_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(job_frame, text="Job actual:", fg="#94a3b8", bg="#1e293b", font=("Helvetica", 11)).pack(side="left")
        tk.Label(job_frame, textvariable=self._job_var, fg="#e2e8f0", bg="#1e293b", font=("Helvetica", 11)).pack(side="left", padx=(8, 0), fill="x")

        tk.Label(self._root, text="Logs recientes:", fg="#94a3b8", bg="#1e293b", font=("Helvetica", 11)).pack(anchor="w", padx=16, pady=(12, 4))

        self._log_box = scrolledtext.ScrolledText(
            self._root,
            wrap=tk.WORD,
            bg="#0f172a",
            fg="#cbd5e1",
            insertbackground="#cbd5e1",
            font=("Consolas", 10),
            height=12,
        )
        self._log_box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._log_box.config(state="disabled")

        btn_frame = tk.Frame(self._root, bg="#1e293b")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        reconnect_btn = tk.Button(
            btn_frame,
            text="Reconectar",
            command=self._on_reconnect,
            bg="#7c3aed",
            fg="white",
            activebackground="#6d28d9",
            borderwidth=0,
            padx=12,
            pady=4,
        )
        reconnect_btn.pack(side="left", padx=(0, 8))

        quit_btn = tk.Button(
            btn_frame,
            text="Salir",
            command=self._root.destroy,
            bg="#334155",
            fg="#e2e8f0",
            activebackground="#475569",
            borderwidth=0,
            padx=12,
            pady=4,
        )
        quit_btn.pack(side="left")

        self._poll_queue()
        self._root.protocol("WM_DELETE_WINDOW", self._root.destroy)
        self._root.mainloop()

    def _on_reconnect(self) -> None:
        if self.on_reconnect:
            threading.Thread(target=self.on_reconnect, daemon=True).start()

    def _poll_queue(self) -> None:
        if self._root is None:
            return
        try:
            while True:
                msg = self._queue.get_nowait()
                self._apply_update(msg)
        except queue.Empty:
            pass
        self._root.after(200, self._poll_queue)

    def _apply_update(self, msg: dict) -> None:
        kind = msg.get("kind")
        if kind == "status" and self._status_var:
            self._status_var.set(msg.get("value", ""))
        elif kind == "job" and self._job_var:
            self._job_var.set(msg.get("value", ""))
        elif kind == "log" and self._log_box:
            self._log_box.config(state="normal")
            self._log_box.insert("end", msg.get("value", "") + "\n")
            self._log_box.see("end")
            self._log_box.config(state="disabled")

    def update_status(self, text: str) -> None:
        self._queue.put({"kind": "status", "value": text})

    def update_job(self, text: str) -> None:
        self._queue.put({"kind": "job", "value": text})

    def log(self, text: str) -> None:
        self._queue.put({"kind": "log", "value": text})


class GuiLogHandler(logging.Handler):
    """Handler de logging que redirige los registros a una WorkerGui."""

    def __init__(self, gui: WorkerGui) -> None:
        super().__init__()
        self.gui = gui

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.gui.log(msg)
        except Exception:
            self.handleError(record)
```

- [ ] **Step 2: Verify import**

Run:

```bash
python -c "from worker.gui import WorkerGui; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add worker/gui.py
git commit -m "feat(worker): add tkinter status GUI"
```

---

## Task 8: Worker main launches GUI conditionally

**Files:**
- Modify: `worker/main.py`
- Test: `WORKER_GUI=1 python -m worker.main` (verify window opens)

- [ ] **Step 1: Integrate GUI**

Replace the file content with:

```python
import os
import logging
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde worker/.env sin depender del CWD.
load_dotenv(Path(__file__).with_name(".env"), override=False)

from fastapi import FastAPI
from worker.runner import run_loop
from worker.gui import WorkerGui, GuiLogHandler
from backend.app.config import WORKER_PORT

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Podcast Worker")


gui_instance: WorkerGui | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from threading import Thread

    if os.getenv("WORKER_GUI", "") == "1":
        gui_instance = WorkerGui(on_reconnect=lambda: logging.info("Reconectar solicitado desde GUI"))
        gui_instance.start()
        gui_instance.update_status("Conectando al backend...")
        gui_handler = GuiLogHandler(gui_instance)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(gui_handler)

    worker_thread = Thread(target=run_loop, daemon=True)
    worker_thread.start()

    port = int(os.getenv("WORKER_PORT", WORKER_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

- [ ] **Step 2: Smoke test with GUI**

Run (optional, requires display):

```bash
WORKER_GUI=1 python -m worker.main
```

Expected: tkinter window appears and the health endpoint responds at `http://127.0.0.1:8001/health`.

- [ ] **Step 3: Commit**

```bash
git add worker/main.py
git commit -m "feat(worker): launch tkinter GUI when WORKER_GUI=1"
```

---

## Task 9: Update AGENTS.md with Dokploy deploy section

**Files:**
- Modify: `AGENTS.md`
- Test: Visual review of the rendered markdown.

- [ ] **Step 1: Insert Dokploy section**

After the existing `#### Opción A: Dokploy (recomendada)` section (around line 127-153), replace it with the following expanded section:

```markdown
#### Opción A: Dokploy (recomendada)

El deploy actual usa Dokploy. A continuación los pasos exactos para replicarlo o actualizarlo.

1. **Crear aplicaciones en Dokploy:**
   - **Frontend**: tipo `static` o `nixpacks`, build path `/frontend`, dominio `https://podcash.app.moonsbow.com`.
   - **Backend**: tipo `dockerfile`, build path `/backend`, dominio `https://api.podcash.app.moonsbow.com`, puerto `8000`.

2. **Variables de entorno obligatorias del backend:**
   | Variable | Valor / ejemplo | Nota |
   |----------|-----------------|------|
   | `SECRET_KEY` | generar cadena larga | Firma de JWT |
   | `ADMIN_USER` | `admin` | Usuario inicial |
   | `ADMIN_PASSWORD` | `admin` | Se hashea al primer login |
   | `WORKER_TOKEN` | generar UUID largo | Token compartido con el worker |
   | `DATABASE_URL` | `sqlite:////app/data/app.db` | Ruta absoluta, 4 barras |
   | `CORS_ORIGINS` | `https://podcash.app.moonsbow.com` | Origen del frontend |
   | `API_PORT` | `8000` | Puerto interno de FastAPI |
   | `REQUIRE_AUTH` | `true` | Obligatorio en producción |
   | `KIMI_API_KEY` | *(opcional)* | Token de Kimi para usar IA en la web |
   | `DEFAULT_LLM_PROVIDER` | `ollama` o `kimi` | Provider por defecto |
   | `DEFAULT_LLM_MODEL` | `llama3.1:8b` / `kimi-for-coding` | Modelo por defecto |

3. **Volúmenes persistentes del backend:**
   Montar en Dokploy para no perder datos al redeployar:
   - `/app/data` → base SQLite (`app.db`)
   - `/app/output` → audios generados expuestos por `/outputs`
   - `/app/voices` → muestras de voz clonadas
   - `/app/projects` → archivos de proyectos
   - `/app/music` → música/branding subido

4. **Variables del frontend:**
   Asegurarse de que `VITE_API_URL=https://api.podcash.app.moonsbow.com` en el build.

> **Deploy actual:**
> - Frontend: `https://podcash.app.moonsbow.com` (acceso directo a canales: `https://podcash.app.moonsbow.com/channels`).
> - Backend: `https://api.podcash.app.moonsbow.com` con volúmenes persistentes para `/app/data`, `/app/output`, `/app/voices`, `/app/projects` y `/app/music`.
> - Usuario inicial: `admin` / `admin`.
>
> **Regenerar WORKER_TOKEN:**
> ```bash
> TOKEN=$(curl -s -X POST https://api.podcash.app.moonsbow.com/api/auth/login \
>   -H 'Content-Type: application/json' \
>   -d '{"username":"admin","password":"admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
> curl -s -H "Authorization: Bearer $TOKEN" \
>   https://api.podcash.app.moonsbow.com/api/admin/worker-token
> ```
> Actualiza `WORKER_TOKEN` en Dokploy (backend) y en `worker/.env` local, luego redepliega.
>
> **Nota sobre caché de edge/CDN:** moonsbow/Cloudflare cachea agresivamente el `index.html`. Si tras un redeploy sigues viendo un build antiguo, purga la caché del dominio desde el panel de moonsbow/Cloudflare, o espera a que expire el TTL.
```

- [ ] **Step 2: Review markdown**

Run:

```bash
python -c "import markdown; print(markdown.markdown(open('AGENTS.md').read()))" 2>/dev/null || head -n 200 AGENTS.md
```

Expected: section renders without broken headers/tables.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs(AGENTS): expand Dokploy deploy section with env vars and volumes"
```

---

## Task 10: End-to-end verification

**Files:** no code changes; only manual checks.

- [ ] **Step 1: Configure backend with Kimi**

Set environment for local backend test:

```bash
export KIMI_API_KEY=$(python3 -c "import json; print(json.load(open('/home/holk/.kimi-code/credentials/kimi-code.json'))['access_token'])")
export DEFAULT_LLM_PROVIDER=kimi
export DEFAULT_LLM_MODEL=kimi-for-coding
```

- [ ] **Step 2: Start backend locally**

```bash
python -m backend.app.main
```

Verify:

```bash
curl -s http://127.0.0.1:8000/api/llm/providers | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/llm/models?provider=kimi | python3 -m json.tool
```

Expected: Kimi appears as available with models `kimi-for-coding` and `kimi-for-coding-highspeed`.

- [ ] **Step 3: Start frontend and select Kimi**

```bash
cd frontend && npm run dev
```

Open `http://127.0.0.1:5173/studio`. Confirm the provider selector shows **Kimi** and the model selector shows **kimi-for-coding**.

- [ ] **Step 4: Create test channel and generate plan**

1. Go to `http://127.0.0.1:5173/channels` and create a test channel (e.g., "TechPulse Test").
2. In Studio, select the channel, provider = Kimi, model = kimi-for-coding.
3. Click **Generar 5 ideas**.
4. Approve one entry to create a pending episode.

- [ ] **Step 5: Run worker with GUI**

In another terminal:

```bash
export BACKEND_URL=http://127.0.0.1:8000
export WORKER_TOKEN=<token>
cd worker && WORKER_GUI=1 python -m main
```

Verify the tkinter window shows connection status and processes the pending episode. The audio file should appear in `output/<episode_id>/` with a descriptive name.

- [ ] **Step 6: Deploy to Dokploy**

1. Push changes to the repository Dokploy watches.
2. In Dokploy, trigger redeploy for backend and frontend.
3. Wait for both to finish.
4. Open `https://podcash.app.moonsbow.com/studio` and confirm Kimi is available.

- [ ] **Step 7: Final commit**

After successful verification, push to remote:

```bash
git push
```

---

## Spec coverage check

| Spec requirement | Plan task |
|------------------|-----------|
| Kimi available in Studio UI | Tasks 1-6 |
| Worker runs job from web queue | Task 10 (verification) |
| Audio stays local | Not a code change; verified in Task 10 |
| Worker tkinter GUI | Tasks 7-8 |
| Dokploy docs in AGENTS.md | Task 9 |

## Placeholder scan

No TBD, TODO, or vague steps remain. Each code block is complete and each command includes expected output.
