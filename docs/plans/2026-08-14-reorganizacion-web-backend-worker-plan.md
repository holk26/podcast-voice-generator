# Plan de implementación: Reorganización a arquitectura web con backend, worker y frontend separados

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) o superpowers:executing-plans para implementar este plan fase por fase. Las tareas usan checkbox (`- [ ]`) para seguimiento.

**Goal:** Reorganizar el proyecto en carpetas `backend/`, `worker/`, `frontend/` y `shared/`, eliminar la aplicación de escritorio, añadir autenticación JWT + token de worker, implementar comunicación backend-worker vía SSE y actualizar documentación.

**Architecture:** Monorepo desacoplado: `backend/` expone API FastAPI con autenticación, `worker/` consume la API desde el PC local, `frontend/` es React/Vite y `shared/` contiene schemas y constantes comunes. Los modelos descargados y assets permanecen en raíz.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic, JWT (python-jose + passlib), React + Vite, SSE, pytest.

---

## Estructura del plan

El plan está dividido en **fases independientes**. Cada fase produce cambios testeables.

- **Fase 1:** Reestructuración física y limpieza de escritorio.
- **Fase 2:** Crear `shared/` y adaptar imports base.
- **Fase 3:** Autenticación JWT y token de worker.
- **Fase 4:** API del worker: SSE + endpoints REST.
- **Fase 5:** Adaptar el worker para consumir la API.
- **Fase 6:** Tests y documentación.

---

## Fase 1: Reestructuración física y limpieza de escritorio

**Objetivo:** Crear la nueva estructura de carpetas, mover el código existente y eliminar la aplicación de escritorio.

### Task 1.1: Backup y limpieza inicial

**Files:**
- Modify: `.gitignore`
- Delete: `__pycache__/`, `.pytest_cache/`, `gui/`, `main.py`, `generate_podcast_gpu.py`

- [ ] **Step 1: Hacer commit del estado actual**

```bash
cd /home/holk/Documents/proyectos/podcast/podcast\ with\ VRAM\ nvidia
git add -A
git commit -m "chore: backup antes de reorganización web"
```

- [ ] **Step 2: Actualizar `.gitignore` para ignorar cachés y entornos en cualquier ubicación**

```bash
# Añadir al final de .gitignore
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
venv*/
.env
.env.local
```

- [ ] **Step 3: Eliminar cachés Python**

```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +
```

- [ ] **Step 4: Eliminar aplicación de escritorio y scripts legacy**

```bash
rm -rf gui/
rm -f main.py generate_podcast_gpu.py
rm -f MANUAL_DE_USO.md
```

- [ ] **Step 5: Commit de limpieza**

```bash
git add -A
git commit -m "chore: elimina app de escritorio y limpia cachés"
```

---

### Task 1.2: Crear estructura backend/

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`
- Create: `backend/scripts/`
- Move: `web_api/main.py` → `backend/app/main.py`
- Move: `web_api/config.py` → `backend/app/config.py`
- Move: `web_api/database.py` → `backend/app/database.py`
- Move: `web_api/models.py` → `backend/app/models.py`
- Move: `web_api/routes/` → `backend/app/routes/`
- Move: `web_api/services/` → `backend/app/services/`
- Move: `web_api/schemas.py` → `shared/schemas/__init__.py` (temporal, se separará en Fase 2)
- Move: `tests/*.py` → `backend/tests/`
- Move: `tests/web_api/*.py` → `backend/tests/`

- [ ] **Step 1: Crear directorios backend/**

```bash
mkdir -p backend/app/routes backend/app/services backend/tests backend/scripts
touch backend/app/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Mover web_api/**

```bash
mv web_api/main.py backend/app/main.py
mv web_api/config.py backend/app/config.py
mv web_api/database.py backend/app/database.py
mv web_api/models.py backend/app/models.py
mv web_api/routes/* backend/app/routes/
mv web_api/services/* backend/app/services/
rmdir web_api/routes web_api/services web_api
```

- [ ] **Step 3: Mover tests de backend**

```bash
mv tests/*.py backend/tests/
mv tests/web_api/*.py backend/tests/
rmdir tests/web_api
```

- [ ] **Step 4: Crear `backend/requirements.txt`**

```text
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.6.0
python-multipart>=0.0.9
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
pyyaml>=6.0
requests>=2.31
beautifulsoup4>=4.12
ollama>=0.1.0
crewai>=0.30.0
pytest>=7.4.0
```

- [ ] **Step 5: Crear `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar paquetes de audio/ML
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY shared/ ./shared/
COPY config.yaml .

ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data
ENV OUTPUT_DIR=/app/output

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Crear `backend/.env.example`**

```text
DATABASE_URL=sqlite:///data/app.db
SECRET_KEY=cambia_esto_por_una_clave_secreta_larga
ADMIN_USER=admin
ADMIN_PASSWORD=admin
WORKER_TOKEN=cambia_esto_por_un_token_largo_y_seguro
API_PORT=8000
```

- [ ] **Step 7: Commit de estructura backend**

```bash
git add -A
git commit -m "chore: mueve web_api a backend/ y reorganiza tests"
```

---

### Task 1.3: Reorganizar worker/

**Files:**
- Create: `worker/tests/__init__.py`
- Create: `worker/requirements.txt`
- Create: `worker/.env.example`
- Move: `tests/worker/*.py` → `worker/tests/`
- Keep: `worker/main.py`, `worker/runner.py`, `worker/handlers.py` (se adaptarán en Fase 5)

- [ ] **Step 1: Crear estructura worker/**

```bash
mkdir -p worker/tests
touch worker/tests/__init__.py
```

- [ ] **Step 2: Mover tests del worker**

```bash
mv tests/worker/*.py worker/tests/
rmdir tests/worker
```

- [ ] **Step 3: Crear `worker/requirements.txt`**

```text
requests>=2.31
pydantic>=2.6.0
pyyaml>=6.0
torch>=2.0.0
torchaudio>=2.0.0
TTS>=0.22.0
edge-tts>=6.1.0
pydub>=0.25.1
soundfile>=0.12.1
pynvml>=11.5.0
qwen-tts>=0.1.0
pytest>=7.4.0
responses>=0.25.0
```

- [ ] **Step 4: Crear `worker/.env.example`**

```text
BACKEND_URL=http://127.0.0.1:8000
WORKER_TOKEN=cambia_esto_por_un_token_largo_y_seguro
AUTOPILOT_HOUR=7
SSE_RETRY_SECONDS=5
POLL_BACKUP_SECONDS=30
```

- [ ] **Step 5: Commit de estructura worker**

```bash
git add -A
git commit -m "chore: reorganiza tests del worker y añade requirements"
```

---

### Task 1.4: Renombrar web/ a frontend/

**Files:**
- Move: `web/` → `frontend/`
- Create: `frontend/.env.example`

- [ ] **Step 1: Renombrar carpeta**

```bash
mv web frontend
```

- [ ] **Step 2: Actualizar `vite.config.ts` si hace referencia a `web/`**

Revisar que no haya referencias explícitas. Normalmente no es necesario.

- [ ] **Step 3: Crear `frontend/.env.example`**

```text
VITE_API_URL=http://127.0.0.1:8000
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: renombra web/ a frontend/"
```

---

### Task 1.5: Actualizar starter.py y starter_monitor.py

**Files:**
- Modify: `starter.py`
- Modify: `starter_monitor.py`
- Modify: `starter.sh`

- [ ] **Step 1: Leer `starter.py` actual y adaptar los comandos de arranque**

El objetivo es cambiar:
- `python -m web_api.main` → `cd backend && python -m app.main`
- `python -m worker.main` → `cd worker && python -m main`
- `npm run dev` (en `web/`) → `cd frontend && npm run dev`

- [ ] **Step 2: Editar `starter.py`**

Buscar las líneas que definen los comandos y actualizarlos:

```python
# Antes
api_cmd = [sys.executable, "-m", "web_api.main"]
worker_cmd = [sys.executable, "-m", "worker.main"]
web_cmd = ["npm", "run", "dev"]
web_cwd = "web"

# Después
api_cmd = [sys.executable, "-m", "app.main"]
api_cwd = "backend"
worker_cmd = [sys.executable, "-m", "main"]
worker_cwd = "worker"
web_cmd = ["npm", "run", "dev"]
web_cwd = "frontend"
```

- [ ] **Step 3: Editar `starter.sh` para reflejar la nueva estructura si es necesario**

Normalmente `starter.sh` solo hace `cd` y ejecuta `python starter.py`, así que no requiere cambios.

- [ ] **Step 4: Editar `starter_monitor.py` si referencia rutas de logs antiguas**

Asegurar que lee `logs/api.log`, `logs/worker.log`, `logs/web.log`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: actualiza starter.py para nueva estructura"
```

---

## Fase 2: Crear shared/ y adaptar imports base

**Objetivo:** Definir el contrato común entre backend y worker, y actualizar los imports para que el backend arranque.

### Task 2.1: Crear shared/

**Files:**
- Create: `shared/__init__.py`
- Create: `shared/schemas/__init__.py`
- Create: `shared/schemas/episode.py`
- Create: `shared/schemas/voice.py`
- Create: `shared/schemas/channel.py`
- Create: `shared/schemas/worker.py`
- Create: `shared/config.py`
- Create: `shared/constants.py`
- Create: `shared/requirements.txt`

- [ ] **Step 1: Crear directorios**

```bash
mkdir -p shared/schemas
touch shared/__init__.py shared/schemas/__init__.py
```

- [ ] **Step 2: Crear `shared/config.py`**

```python
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
PREVIEW_DIR = OUTPUT_DIR / "previews"
VOICES_DIR = Path(os.getenv("VOICES_DIR", BASE_DIR / "voices"))
CLONES_DIR = VOICES_DIR / "clones"
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", BASE_DIR / "projects"))
MUSIC_DIR = Path(os.getenv("MUSIC_DIR", BASE_DIR / "music"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", BASE_DIR / "models"))


def init_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    CLONES_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 3: Crear `shared/constants.py`**

```python
DEFAULT_SAMPLE_RATE = 24_000
DEFAULT_BITRATE = "192k"
DEFAULT_AUDIO_FORMAT = "mp3"
DEFAULT_FADE_IN_MS = 500
DEFAULT_FADE_OUT_MS = 1000
```

- [ ] **Step 4: Crear `shared/schemas/episode.py`**

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EpisodeBase(BaseModel):
    title: str
    script: Optional[str] = None
    voice_id: Optional[int] = None
    channel_id: Optional[int] = None
    status: str = "pending"
    error_message: Optional[str] = None


class EpisodeCreate(EpisodeBase):
    pass


class EpisodeResponse(EpisodeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EpisodeJob(BaseModel):
    id: int
    title: str
    script: Optional[str] = None
    voice_id: Optional[int] = None
    channel_id: Optional[int] = None
```

- [ ] **Step 5: Crear `shared/schemas/voice.py`**

```python
from pydantic import BaseModel
from typing import Optional


class VoiceBase(BaseModel):
    name: str
    engine: Optional[str] = None
    language: Optional[str] = None
    sample_path: Optional[str] = None


class VoiceCreate(VoiceBase):
    pass


class VoiceResponse(VoiceBase):
    id: int

    class Config:
        from_attributes = True
```

- [ ] **Step 6: Crear `shared/schemas/channel.py`**

```python
from pydantic import BaseModel
from typing import Optional


class ChannelBase(BaseModel):
    name: str
    description: Optional[str] = None
    language: Optional[str] = "es"


class ChannelCreate(ChannelBase):
    pass


class ChannelResponse(ChannelBase):
    id: int

    class Config:
        from_attributes = True
```

- [ ] **Step 7: Crear `shared/schemas/worker.py`**

```python
from pydantic import BaseModel
from typing import Optional


class WorkerJobRequest(BaseModel):
    worker_token: Optional[str] = None


class WorkerJobComplete(BaseModel):
    status: str  # "done" | "failed"
    error_message: Optional[str] = None


class WorkerEvent(BaseModel):
    event: str  # "new_job", "job_cancelled", "ping"
    job_id: Optional[int] = None
```

- [ ] **Step 8: Actualizar `shared/schemas/__init__.py`**

```python
from .episode import EpisodeBase, EpisodeCreate, EpisodeResponse, EpisodeJob
from .voice import VoiceBase, VoiceCreate, VoiceResponse
from .channel import ChannelBase, ChannelCreate, ChannelResponse
from .worker import WorkerJobRequest, WorkerJobComplete, WorkerEvent

__all__ = [
    "EpisodeBase",
    "EpisodeCreate",
    "EpisodeResponse",
    "EpisodeJob",
    "VoiceBase",
    "VoiceCreate",
    "VoiceResponse",
    "ChannelBase",
    "ChannelCreate",
    "ChannelResponse",
    "WorkerJobRequest",
    "WorkerJobComplete",
    "WorkerEvent",
]
```

- [ ] **Step 9: Crear `shared/requirements.txt`**

```text
pydantic>=2.6.0
pyyaml>=6.0
```

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat(shared): añade contrato de datos entre backend y worker"
```

---

### Task 2.2: Actualizar imports en backend/

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/routes/*.py`
- Modify: `backend/app/services/*.py`
- Modify: `backend/tests/*.py`

- [ ] **Step 1: Reemplazar imports `from web_api...` por `from backend.app...` en todo backend/**

```bash
cd backend
find . -type f -name "*.py" -exec sed -i 's/from web_api\./from backend.app./g' {} +
find . -type f -name "*.py" -exec sed -i 's/import web_api/import backend.app/g' {} +
```

- [ ] **Step 2: Verificar que `backend/app/main.py` usa imports correctos**

```python
from backend.app.config import OUTPUT_DIR, API_PORT, init_dirs
from backend.app.database import init_db
from backend.app import models  # noqa: F401
from backend.app.routes import voices, tts, episodes, channels, llm, jobs, books
```

- [ ] **Step 3: Reemplazar imports de schemas en backend/app/routes/**

Donde se usen schemas Pydantic, cambiar `from backend.app import schemas` por `from shared import schemas` o importar desde `shared.schemas`.

Ejemplo en `backend/app/routes/episodes.py`:

```python
# antes
from backend.app import schemas

# después
from shared.schemas import EpisodeCreate, EpisodeResponse
```

- [ ] **Step 4: Ejecutar tests de backend**

```bash
cd /home/holk/Documents/proyectos/podcast/podcast\ with\ VRAM\ nvidia
python -m pytest backend/tests -v --tb=short
```

Esperado: puede haber errores de importación; corregirlos antes de continuar.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(backend): adapta imports a nueva estructura"
```

---

### Task 2.3: Actualizar imports en worker/

**Files:**
- Modify: `worker/main.py`
- Modify: `worker/runner.py`
- Modify: `worker/handlers.py`
- Modify: `worker/tests/*.py`

- [ ] **Step 1: Eliminar imports de `web_api` en worker/**

El worker no debe importar nada de `backend.app`. Reemplazar temporalmente los imports de modelos por placeholders hasta Fase 5.

En `worker/runner.py`:

```python
# Eliminar
# from sqlalchemy.orm import Session
# from web_api.database import SessionLocal
# from web_api.models import Episode
# from web_api.services.automation_service import autopilot_tick

# Añadir (temporal)
from shared.schemas import EpisodeJob
from worker.client import BackendClient
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "refactor(worker): elimina imports directos a backend"
```

---

## Fase 3: Autenticación JWT y token de worker

**Objetivo:** Proteger la API con JWT para usuarios y añadir token de worker.

### Task 3.1: Añadir dependencias de autenticación

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Asegurar que están incluidas**

```text
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.9
```

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore(backend): añade dependencias de autenticación"
```

---

### Task 3.2: Crear backend/app/auth.py

**Files:**
- Create: `backend/app/auth.py`

- [ ] **Step 1: Implementar utilidades de JWT y hashing**

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os

SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/auth.py
git commit -m "feat(auth): añade utilidades JWT y bcrypt"
```

---

### Task 3.3: Crear backend/app/dependencies.py

**Files:**
- Create: `backend/app/dependencies.py`

- [ ] **Step 1: Implementar dependencias de FastAPI**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app import auth
import os

security = HTTPBearer()
worker_security = HTTPBearer()

WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    username = auth.decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


def require_worker_token(credentials: HTTPAuthorizationCredentials = Depends(worker_security)) -> None:
    token = credentials.credentials
    if not WORKER_TOKEN or token != WORKER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token de worker inválido",
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "feat(auth): añade dependencias de autenticación"
```

---

### Task 3.4: Crear backend/app/routes/auth.py

**Files:**
- Create: `backend/app/routes/auth.py`

- [ ] **Step 1: Implementar login**

```python
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.app import auth

router = APIRouter(tags=["auth"])

# Usuario inicial desde variables de entorno (solo para MVP)
import os

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
# Opcional: soporte para hash pre-calculado
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")


def _verify_admin(password: str) -> bool:
    if ADMIN_PASSWORD_HASH:
        return auth.verify_password(password, ADMIN_PASSWORD_HASH)
    # Solo para desarrollo; en producción usar hash
    return password == ADMIN_PASSWORD


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != ADMIN_USER or not _verify_admin(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    access_token = auth.create_access_token(data={"sub": ADMIN_USER})
    return {"access_token": access_token, "token_type": "bearer"}
```

- [ ] **Step 2: Registrar la ruta en backend/app/main.py**

```python
from backend.app.routes import voices, tts, episodes, channels, llm, jobs, books, auth

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(auth): añade endpoint de login JWT"
```

---

### Task 3.5: Proteger rutas existentes

**Files:**
- Modify: `backend/app/routes/*.py`

- [ ] **Step 1: Añadir `Depends(get_current_user)` a rutas que modifiquen datos**

Ejemplo en `backend/app/routes/episodes.py`:

```python
from fastapi import APIRouter, Depends
from backend.app.dependencies import get_current_user

router = APIRouter()

@router.post("/")
def create_episode(
    episode: EpisodeCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user),
):
    ...
```

- [ ] **Step 2: Dejar rutas de solo lectura sin protección (o protegerlas también)**

Decisión de diseño: proteger todo por simplicidad, excepto health check.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(auth): protege rutas con JWT"
```

---

### Task 3.6: Login en frontend

**Files:**
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/components/LoginForm.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/routes/__root.tsx`

- [ ] **Step 1: Crear `frontend/src/stores/authStore.ts`**

```typescript
import { create } from 'zustand';

interface AuthState {
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  login: (token) => {
    localStorage.setItem('token', token);
    set({ token });
  },
  logout: () => {
    localStorage.removeItem('token');
    set({ token: null });
  },
}));
```

- [ ] **Step 2: Actualizar `frontend/src/api/client.ts` para enviar token**

```typescript
import { useAuthStore } from '../stores/authStore';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = useAuthStore.getState().token;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (response.status === 401) {
    useAuthStore.getState().logout();
    window.location.href = '/login';
  }
  return response;
}
```

- [ ] **Step 3: Crear `frontend/src/components/LoginForm.tsx`**

Formulario simple que llama a `/api/auth/login` y guarda el token.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(frontend): añade login y store de autenticación"
```

---

## Fase 4: API del worker (SSE + endpoints REST)

**Objetivo:** Implementar en el backend los endpoints que el worker consumirá.

### Task 4.1: Crear backend/app/routes/worker.py

**Files:**
- Create: `backend/app/routes/worker.py`

- [ ] **Step 1: Implementar endpoints del worker**

```python
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.dependencies import get_db, require_worker_token
from backend.app.models import Episode
from shared.schemas import EpisodeJob, WorkerJobComplete

router = APIRouter(prefix="/api/worker", tags=["worker"])

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")


@router.get("/jobs/next", response_model=Optional[EpisodeJob])
def get_next_job(
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    episode = (
        db.query(Episode)
        .filter(Episode.status == "pending")
        .order_by(Episode.created_at)
        .with_for_update()
        .first()
    )
    if not episode:
        return None
    episode.status = "running"
    db.commit()
    db.refresh(episode)
    return EpisodeJob(
        id=episode.id,
        title=episode.title,
        script=episode.script,
        voice_id=episode.voice_id,
        channel_id=episode.channel_id,
    )


@router.post("/jobs/{job_id}/start")
def start_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    episode = db.get(Episode, job_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    episode.status = "running"
    db.commit()
    return {"ok": True}


@router.post("/jobs/{job_id}/complete")
def complete_job(
    job_id: int,
    status: str = Form(...),
    error_message: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    _: None = Depends(require_worker_token),
):
    episode = db.get(Episode, job_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    episode.status = status
    if error_message:
        episode.error_message = error_message[:500]

    if audio and status == "done":
        from pathlib import Path
        out_dir = Path(OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(audio.filename)[1] or ".mp3"
        file_path = out_dir / f"episode_{job_id}{ext}"
        with open(file_path, "wb") as f:
            f.write(audio.file.read())
        episode.audio_path = str(file_path)

    db.commit()
    return {"ok": True}
```

- [ ] **Step 2: Registrar la ruta en backend/app/main.py**

```python
from backend.app.routes import voices, tts, episodes, channels, llm, jobs, books, auth, worker

app.include_router(worker.router)
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(worker-api): añade endpoints REST para el worker"
```

---

### Task 4.2: Implementar SSE para notificar al worker

**Files:**
- Modify: `backend/app/routes/worker.py`
- Create: `backend/app/sse.py`

- [ ] **Step 1: Crear `backend/app/sse.py` con gestor de conexiones SSE**

```python
from typing import List
from fastapi import Request
from asyncio import Queue


class WorkerConnectionManager:
    def __init__(self):
        self.connections: List[Queue] = []

    async def connect(self) -> Queue:
        queue: Queue = Queue()
        self.connections.append(queue)
        return queue

    def disconnect(self, queue: Queue):
        if queue in self.connections:
            self.connections.remove(queue)

    async def broadcast(self, message: str):
        for queue in self.connections:
            await queue.put(message)


worker_manager = WorkerConnectionManager()
```

- [ ] **Step 2: Añadir endpoint SSE en `backend/app/routes/worker.py`**

```python
from fastapi import Request
from fastapi.responses import StreamingResponse
from backend.app.sse import worker_manager


@router.get("/events")
async def worker_events(
    request: Request,
    _: None = Depends(require_worker_token),
):
    async def event_stream():
        queue = await worker_manager.connect()
        try:
            while True:
                if await request.is_disconnected():
                    break
                message = await queue.get()
                yield f"data: {message}\n\n"
        finally:
            worker_manager.disconnect(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 3: Emitir evento cuando se crea un episodio**

En `backend/app/routes/episodes.py`, después de crear un episodio:

```python
import json
from backend.app.sse import worker_manager
from shared.schemas import WorkerEvent

# dentro de create_episode
await worker_manager.broadcast(
    WorkerEvent(event="new_job", job_id=episode.id).model_dump_json()
)
```

Nota: si la ruta es síncrona, usar `asyncio.create_task`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(worker-api): añade SSE para notificar jobs al worker"
```

---

## Fase 5: Adaptar el worker para consumir la API

**Objetivo:** Reemplazar el acceso directo a la base de datos por llamadas HTTP al backend.

### Task 5.1: Crear worker/client.py

**Files:**
- Create: `worker/client.py`

- [ ] **Step 1: Implementar cliente HTTP del worker**

```python
import os
import requests
from pathlib import Path
from typing import Optional
from shared.schemas import EpisodeJob, WorkerJobComplete


class BackendClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (base_url or os.getenv("BACKEND_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.token = token or os.getenv("WORKER_TOKEN", "")
        self.headers = {"Authorization": f"Worker {self.token}"}

    def get_next_job(self) -> Optional[EpisodeJob]:
        r = requests.get(f"{self.base_url}/api/worker/jobs/next", headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data is None:
            return None
        return EpisodeJob(**data)

    def start_job(self, job_id: int) -> None:
        r = requests.post(f"{self.base_url}/api/worker/jobs/{job_id}/start", headers=self.headers, timeout=10)
        r.raise_for_status()

    def complete_job(self, job_id: int, audio_path: Optional[Path] = None, error_message: Optional[str] = None) -> None:
        files = {}
        data = {"status": "done" if error_message is None else "failed"}
        if error_message:
            data["error_message"] = error_message
        if audio_path and audio_path.exists():
            files["audio"] = open(audio_path, "rb")
        try:
            r = requests.post(
                f"{self.base_url}/api/worker/jobs/{job_id}/complete",
                headers=self.headers,
                data=data,
                files=files,
                timeout=120,
            )
            r.raise_for_status()
        finally:
            if "audio" in files:
                files["audio"].close()

    def event_stream(self):
        import sseclient
        r = requests.get(f"{self.base_url}/api/worker/events", headers=self.headers, stream=True, timeout=None)
        return sseclient.SSEClient(r)
```

- [ ] **Step 2: Añadir `sseclient-py` a `worker/requirements.txt`**

```text
sseclient-py>=1.8.0
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(worker): añade cliente HTTP para backend"
```

---

### Task 5.2: Adaptar worker/runner.py

**Files:**
- Modify: `worker/runner.py`

- [ ] **Step 1: Reescribir el bucle principal**

```python
import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from worker.client import BackendClient
from worker.handlers import handle_podcast_episode

logger = logging.getLogger(__name__)

SSE_RETRY_SECONDS = int(os.getenv("SSE_RETRY_SECONDS", "5"))
POLL_BACKUP_SECONDS = int(os.getenv("POLL_BACKUP_SECONDS", "30"))
AUTOPILOT_HOUR = int(os.getenv("AUTOPILOT_HOUR", "7"))


def _process_one_job(client: BackendClient, job) -> None:
    logger.info(f"Procesando job {job.id}: {job.title}")
    try:
        client.start_job(job.id)
        output_path = handle_podcast_episode(job)
        client.complete_job(job.id, audio_path=Path(output_path) if output_path else None)
        logger.info(f"Job {job.id} completado")
    except Exception as e:
        logger.error(f"Job {job.id} falló: {e}")
        client.complete_job(job.id, error_message=str(e)[:500])


def _poll_once(client: BackendClient) -> bool:
    job = client.get_next_job()
    if job is None:
        return False
    _process_one_job(client, job)
    return True


def run_loop():
    client = BackendClient()
    while True:
        try:
            # Intentar SSE primero
            logger.info("Conectando a SSE del backend...")
            for event in client.event_stream():
                if event.event == "new_job":
                    # Aún usamos el endpoint para reservar el job de forma segura
                    _poll_once(client)
        except Exception as e:
            logger.warning(f"SSE desconectado: {e}. Reintentando en {SSE_RETRY_SECONDS}s")
            time.sleep(SSE_RETRY_SECONDS)

        # Polling de respaldo
        try:
            while _poll_once(client):
                pass
        except Exception as e:
            logger.error(f"Error en polling: {e}")

        time.sleep(POLL_BACKUP_SECONDS)
```

- [ ] **Step 2: Adaptar `handle_podcast_episode` para recibir `EpisodeJob` en lugar de modelo SQLAlchemy**

En `worker/handlers.py`:

```python
from shared.schemas import EpisodeJob
from pathlib import Path

def handle_podcast_episode(job: EpisodeJob) -> Optional[str]:
    # Lógica actual adaptada para usar job.script, job.voice_id, etc.
    # Debe devolver la ruta del archivo generado o None
    ...
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(worker): adapta runner a comunicación API/SSE"
```

---

## Fase 6: Tests y documentación

**Objetivo:** Asegurar que todo funciona y documentar la nueva arquitectura.

### Task 6.1: Actualizar y ejecutar tests

**Files:**
- Modify: `backend/tests/*.py`
- Modify: `worker/tests/*.py`
- Modify: `pytest.ini`

- [ ] **Step 1: Actualizar imports en tests de backend**

```bash
cd backend
find tests -type f -name "*.py" -exec sed -i 's/from web_api\./from backend.app./g' {} +
find tests -type f -name "*.py" -exec sed -i 's/import web_api/import backend.app/g' {} +
```

- [ ] **Step 2: Añadir tests de autenticación en `backend/tests/test_auth.py`**

```python
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_login_success(monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    r = client.post("/api/auth/login", data={"username": "admin", "password": "secret"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_failure():
    r = client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
    assert r.status_code == 401
```

- [ ] **Step 3: Añadir tests del worker en `worker/tests/test_client.py`**

```python
import responses
from worker.client import BackendClient
from shared.schemas import EpisodeJob


@responses.activate
def test_get_next_job():
    responses.add(responses.GET, "http://test/api/worker/jobs/next", json={
        "id": 1, "title": "Test", "script": "Hola", "voice_id": 1, "channel_id": None
    }, status=200)
    client = BackendClient(base_url="http://test", token="tok")
    job = client.get_next_job()
    assert isinstance(job, EpisodeJob)
    assert job.id == 1
```

- [ ] **Step 4: Actualizar `pytest.ini`**

```ini
[pytest]
testpaths = backend/tests worker/tests shared/tests
pythonpath = . backend worker shared
```

- [ ] **Step 5: Ejecutar tests**

```bash
python -m pytest backend/tests worker/tests -v --tb=short
```

Esperado: todos los tests pasan.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "test: actualiza tests para nueva arquitectura"
```

---

### Task 6.2: Actualizar README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Reescribir README.md con la nueva arquitectura**

Incluir:
- Descripción del proyecto web.
- Estructura de carpetas.
- Cómo instalar backend, worker y frontend.
- Cómo configurar variables de entorno.
- Cómo desplegar en servidor.
- Cómo ejecutar el worker local.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: reescribe README para arquitectura web"
```

---

### Task 6.3: Actualizar AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Reescribir AGENTS.md**

Reemplazar la sección de scripts de arranque y arquitectura para reflejar:
- `backend/`, `worker/`, `frontend/`.
- Autenticación JWT.
- Token de worker.
- Eliminación de la app de escritorio.

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: actualiza AGENTS.md con nueva arquitectura"
```

---

## Verificación final

- [ ] Arrancar backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- [ ] Arrancar worker: `cd worker && python main.py`
- [ ] Arrancar frontend: `cd frontend && npm run dev`
- [ ] Probar login en frontend.
- [ ] Crear un episodio y verificar que el worker lo procesa.
- [ ] Verificar que el audio aparece en `output/`.
- [ ] Ejecutar `pytest backend/tests worker/tests`.

---

## Notas para el implementador

- **No mover ni eliminar** las carpetas `models/`, `Qwen3-TTS-12Hz-1.7B-Base/` ni `zonos/`.
- **No mover** la base de datos `data/app.db`; solo actualizar rutas si es necesario.
- Si un test falla por imports, priorizar corregir el import antes de modificar la lógica.
- Hacer commits frecuentes; cada Task sugiere un commit.
