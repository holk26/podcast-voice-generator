# Diseño: Reorganización a arquitectura web con backend, worker y frontend separados

**Fecha:** 2026-08-14  
**Autor:** Kimi Code (con el usuario)  
**Estado:** Aprobado para implementación

---

## 1. Contexto

El proyecto actual es una aplicación de podcast generado por IA que tiene:

- Una **aplicación de escritorio** PyQt6 (`gui/`, `main.py`, `generate_podcast_gpu.py`).
- Una **API web** (`web_api/`).
- Un **worker** de generación (`worker/`).
- Un **frontend web** (`web/`).
- Modelos TTS descargados (`models/`, `Qwen3-TTS-12Hz-1.7B-Base/`, `zonos/`).
- Assets y datos compartidos (`data/`, `output/`, `voices/`, `projects/`, `media_packages/`, `sfx_library/`, `templates/`, `music/`, `docs/`).

El objetivo es:

1. Eliminar la aplicación de escritorio.
2. Dejar solo la versión web.
3. Reorganizar el código en carpetas claras: `backend/`, `worker/`, `frontend/`.
4. Permitir desplegar `backend/` y `frontend/` en un servidor remoto.
5. Ejecutar `worker/` en el PC local del usuario para procesar episodios.
6. Añadir autenticación JWT para proteger la web pública.
7. Añadir un token seguro para que el worker se comunique con el backend.

---

## 2. Objetivos

- **Eliminar** toda la interfaz de escritorio y su documentación asociada.
- **Separar** el código en tres componentes independientes:
  - `backend/`: API FastAPI + base de datos + autenticación.
  - `worker/`: Cliente de generación de audio que corre en el PC local.
  - `frontend/`: Aplicación web React/Vite.
- **Crear** una carpeta `shared/` con el contrato de datos entre backend y worker.
- **Mantener** los modelos descargados y los assets en la raíz del repositorio (no moverlos).
- **Actualizar** `AGENTS.md` y `README.md` para reflejar la nueva arquitectura.
- **No duplicar** código: backend y worker comparten solo schemas y constantes.

---

## 3. Arquitectura final

```
podcast-voice-generator/
├── backend/                      # FastAPI (servidor remoto)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # punto de entrada FastAPI
│   │   ├── config.py             # settings y rutas
│   │   ├── database.py           # SQLAlchemy engine + SessionLocal
│   │   ├── models.py             # modelos SQLAlchemy
│   │   ├── auth.py               # JWT + hashing + login
│   │   ├── dependencies.py       # get_db, get_current_user, require_worker_token
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── voices.py
│   │   │   ├── tts.py
│   │   │   ├── episodes.py
│   │   │   ├── channels.py
│   │   │   ├── llm.py
│   │   │   ├── jobs.py
│   │   │   ├── books.py
│   │   │   └── worker.py         # endpoints exclusivos del worker
│   │   └── services/
│   │       ├── automation_service.py
│   │       ├── crew_service.py
│   │       ├── diagnostics_service.py
│   │       ├── job_service.py
│   │       └── llm_provider.py
│   ├── scripts/                  # scripts útiles mantenidos
│   ├── tests/                    # tests de backend
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── worker/                       # Cliente de generación (PC local)
│   ├── main.py
│   ├── client.py                 # cliente HTTP hacia backend
│   ├── runner.py                 # bucle SSE + polling de respaldo
│   ├── handlers.py               # generación de episodios
│   ├── tests/                    # tests de worker
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                     # React + Vite (antes web/)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── routes/
│   │   ├── stores/
│   │   └── ...
│   └── .env.example
│
├── shared/                       # Contrato de datos (sin lógica de negocio)
│   ├── __init__.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── episode.py
│   │   ├── voice.py
│   │   ├── channel.py
│   │   └── worker.py
│   ├── config.py                 # rutas y constantes
│   └── constants.py              # tasas de sampleo, formatos, etc.
│
├── data/                         # SQLite y datos (en raíz)
├── output/                       # archivos generados
├── voices/
├── models/                       # modelos descargados (NO mover)
├── Qwen3-TTS-12Hz-1.7B-Base/     # modelo Qwen3 (NO mover)
├── zonos/                        # modelo Zonos (NO mover)
├── media_packages/
├── sfx_library/
├── templates/
├── music/
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-08-14-reorganizacion-web-backend-worker-design.md
├── logs/
├── starter.py                    # orquestador local actualizado
├── starter.sh
├── starter_monitor.py
├── config.yaml
├── pytest.ini                    # actualizado
├── .gitignore                    # actualizado
├── requirements.txt              # opcional: dependencias de desarrollo
├── README.md                     # reescrito
└── AGENTS.md                     # actualizado
```

---

## 4. Qué se mueve, qué se crea y qué se elimina

### 4.1 Se mueve

| Origen | Destino | Notas |
|---|---|---|
| `web_api/main.py` | `backend/app/main.py` | actualizar imports |
| `web_api/config.py` | `backend/app/config.py` | añadir settings de auth |
| `web_api/database.py` | `backend/app/database.py` | sin cambios de lógica |
| `web_api/models.py` | `backend/app/models.py` | sin cambios de lógica |
| `web_api/routes/*.py` | `backend/app/routes/*.py` | añadir `worker.py` |
| `web_api/services/*.py` | `backend/app/services/*.py` | sin cambios de lógica |
| `web_api/schemas.py` | `shared/schemas/*.py` | separar por dominio |
| `web/` | `frontend/` | renombrar carpeta |
| `tests/*.py` (excepto web_api/worker) | `backend/tests/` | actualizar imports |
| `tests/web_api/*.py` | `backend/tests/` | actualizar imports |
| `tests/worker/*.py` | `worker/tests/` | actualizar imports |
| Scripts útiles de `scripts/` | `backend/scripts/` | filtrar temporales |

### 4.2 Se crea

- `backend/app/auth.py`: utilidades de JWT y hashing.
- `backend/app/dependencies.py`: dependencias de FastAPI.
- `backend/app/routes/worker.py`: endpoints del worker.
- `backend/app/routes/auth.py`: login y refresh.
- `worker/client.py`: cliente HTTP autónomo del worker.
- `shared/schemas/`: schemas Pydantic por dominio.
- `shared/config.py`: rutas base y constantes.
- `shared/constants.py`: constantes de audio.
- `frontend/src/stores/authStore.ts`: estado de autenticación.
- `.env.example` en backend, worker y frontend.
- `backend/Dockerfile`.

### 4.3 Se elimina

- `gui/` completo.
- `main.py` (punto de entrada PyQt6).
- `generate_podcast_gpu.py`.
- `MANUAL_DE_USO.md` (habla de PyQt6) → archivar o eliminar.
- Scripts temporales: `scripts/_tmp_*`, `scripts/test_qwen_*`, etc.
- `__pycache__/` y `.pytest_cache/`.

> **Importante:** No se tocan los modelos descargados (`models/`, `Qwen3-TTS-12Hz-1.7B-Base/`, `zonos/`).

---

## 5. Autenticación y seguridad

### 5.1 Login para usuarios (JWT)

- Se usa `python-jose` + `passlib[bcrypt]`.
- Endpoint `POST /api/auth/login` recibe `username` y `password`.
- Devuelve `access_token` (JWT) y `token_type: bearer`.
- El frontend almacena el token (por seguridad, preferiblemente en `httpOnly cookie`; de lo contrario `localStorage`).
- Las rutas protegidas usan `get_current_user`.
- El primer usuario se crea con variables de entorno:
  - `ADMIN_USER`
  - `ADMIN_PASSWORD_HASH` (o `ADMIN_PASSWORD` en desarrollo).

### 5.2 Token para el worker

- Variable de entorno `WORKER_TOKEN` en backend y worker.
- El worker envía el token en cada request: `Authorization: Worker <token>`.
- El backend valida el token con `require_worker_token` en:
  - `GET /api/worker/jobs/next`
  - `POST /api/worker/jobs/{id}/start`
  - `POST /api/worker/jobs/{id}/complete`
  - `POST /api/worker/jobs/{id}/fail`
  - `GET /api/worker/events` (SSE)

### 5.3 CORS

- El backend permite CORS solo desde el dominio del frontend.
- En desarrollo: `http://localhost:{WEB_PORT}` y `http://127.0.0.1:{WEB_PORT}`.

---

## 6. Comunicación backend ↔ worker

### 6.1 Mecanismo: Server-Sent Events (SSE)

Se elige SSE sobre polling puro porque:

- El proyecto ya usa SSE en el frontend (`useEpisodeSSE.ts`).
- Es más simple que WebSocket para notificaciones unidireccionales.
- Permite reconexión automática.

### 6.2 Endpoints del worker

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/worker/events` | SSE: notifica `new_job`, `job_cancelled` |
| `GET` | `/api/worker/jobs/next` | Reserva y devuelve el siguiente job `pending` |
| `POST` | `/api/worker/jobs/{id}/start` | Marca el job como `running` |
| `POST` | `/api/worker/jobs/{id}/complete` | Marca el job como `done` y sube el audio |
| `POST` | `/api/worker/jobs/{id}/fail` | Marca el job como `failed` con mensaje |

### 6.3 Flujo de trabajo

1. El usuario crea un episodio desde el frontend.
2. Backend guarda el episodio en DB con estado `pending`.
3. Backend emite evento SSE `new_job` a los workers conectados.
4. Worker recibe el evento y llama a `GET /api/worker/jobs/next`.
5. Backend reserva el job (con `SELECT ... FOR UPDATE`) y lo devuelve.
6. Worker ejecuta `handle_podcast_episode(...)`.
7. Worker sube el audio con `POST /api/worker/jobs/{id}/complete`.
8. Backend guarda el archivo en `output/` y actualiza el estado.

### 6.4 Polling de respaldo

Si la conexión SSE se pierde, el worker hace polling a `/api/worker/jobs/next` cada 30 segundos.

### 6.5 Formato de los datos

Todos los payloads usan los schemas definidos en `shared/schemas/`.

---

## 7. Desacoplamiento

### 7.1 Reglas de dependencia

```
frontend ──HTTP──> backend
                     │
                     ├──> shared
                     │
worker ────HTTP/SSE──┘
   │
   └──> shared
```

- `frontend/` no importa código de `backend/` ni `worker/`.
- `worker/` no importa código de `backend/`.
- `backend/` no importa código de `worker/`.
- `shared/` no importa código de `backend/`, `worker/` ni `frontend/`.

### 7.2 Contenido de `shared/`

Solo:

- Schemas Pydantic.
- Constantes (rutas, formatos de audio).
- Tipos de datos.

Nunca:

- SQLAlchemy.
- FastAPI.
- Lógica de generación de audio.
- Llamadas HTTP.

### 7.3 Cliente del worker

`worker/client.py` es un cliente HTTP genérico. No sabe nada de SQLAlchemy ni de la implementación del backend. Solo consume la API pública expuesta por el backend para los workers.

---

## 8. Dependencias

### 8.1 `backend/requirements.txt`

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
```

### 8.2 `worker/requirements.txt`

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
```

### 8.3 `shared/requirements.txt`

```text
pydantic>=2.6.0
pyyaml>=6.0
```

### 8.4 `frontend/package.json`

Sin cambios significativos. Se añade manejo de login en la app.

---

## 9. Tests

### 9.1 `backend/tests/`

- Tests de rutas API.
- Tests de servicios.
- Tests de autenticación.
- Tests del contrato worker.

### 9.2 `worker/tests/`

- Tests de `client.py` usando `responses` o `pytest-httpx`.
- Tests de `handlers.py` con mocks.
- Tests de `runner.py`.

### 9.3 `frontend/`

- Tests existentes en `src/components/__tests__/` y `src/hooks/__tests__/`.
- Tests del store de autenticación.

### 9.4 Ejecución

```bash
pytest backend/tests
pytest worker/tests
cd frontend && npm test
```

---

## 10. Arranque y despliegue

### 10.1 Desarrollo local con `starter.py`

```bash
python starter.py
```

Levanta backend, worker y frontend en terminales separadas.

### 10.2 Desarrollo manual

```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Worker
cd worker && python main.py

# Frontend
cd frontend && npm run dev
```

### 10.3 Despliegue en servidor

```bash
cd backend
docker build -t podcast-backend .
docker run -d -p 8000:8000 --env-file .env podcast-backend
```

El frontend se puede desplegar con Vite preview, nginx o un CDN.

### 10.4 Worker en PC local

```bash
cd worker
cp .env.example .env
# Editar BACKEND_URL y WORKER_TOKEN
python main.py
```

---

## 11. Plan de migración

### Fase 1: Preparación
- Hacer commit del estado actual.
- Limpiar cachés (`__pycache__`, `.pytest_cache`).
- Actualizar `.gitignore`.

### Fase 2: Estructura
- Crear `backend/`, `worker/`, `frontend/`, `shared/`.
- Mover `web/` → `frontend/`.
- Mover `web_api/` → `backend/app/`.
- Mover `worker/` actual → nuevo `worker/`.
- Crear `shared/schemas/`, `shared/config.py`, `shared/constants.py`.

### Fase 3: Eliminación escritorio
- Eliminar `gui/`, `main.py`, `generate_podcast_gpu.py`.
- Archivar o eliminar `MANUAL_DE_USO.md`.
- Filtrar scripts temporales.

### Fase 4: Imports
- Cambiar `from web_api...` → `from backend.app...`.
- Mover schemas a `shared/`.
- Crear `worker/client.py` independiente.
- Actualizar `starter.py`, `starter.sh`, `starter_monitor.py`.

### Fase 5: Autenticación
- Implementar `backend/app/auth.py`.
- Proteger rutas.
- Añadir login en frontend.
- Configurar token de worker.

### Fase 6: Comunicación worker
- Crear endpoints del worker.
- Implementar SSE `/api/worker/events`.
- Adaptar `worker/runner.py`.
- Subir audio por multipart.

### Fase 7: Tests
- Mover y actualizar tests.
- Ejecutar `pytest`.

### Fase 8: Documentación
- Reescribir `README.md`.
- Actualizar `AGENTS.md`.
- Crear `.env.example`.

---

## 12. Decisiones

| Decisión | Opción elegida | Razón |
|---|---|---|
| Estructura de carpetas | `backend/`, `worker/`, `frontend/`, `shared/` | Desacoplamiento y claridad |
| Assets y modelos | Mantener en raíz | Evita cambios de rutas y no toca modelos descargados |
| Scripts útiles | `backend/scripts/` | Cerca del backend, que es quien más los usa |
| Tests | Separados por componente | Independencia de ejecución |
| Autenticación usuarios | JWT + bcrypt | Estándar, simple, seguro |
| Autenticación worker | Token estático en header | Suficiente para un único worker local |
| Comunicación worker | SSE + polling de respaldo | Más moderno que polling puro; ya hay experiencia SSE en frontend |
| Desacoplamiento | Contrato API en `shared/` | Worker no importa código del backend |
| Entornos virtuales | Mantener en raíz, ignorar en `.gitignore` | No romper entornos activos |

---

## 13. Notas de riesgo

- Los imports absolutos actuales (`from web_api...`, `from worker...`) deben actualizarse cuidadosamente.
- Los modelos descargados no deben moverse ni eliminarse.
- La base de datos SQLite actual (`data/app.db`) debe conservarse durante la migración.
- El worker en PC local necesita acceso a internet para comunicarse con el backend remoto.
- Si el backend y el worker usan rutas relativas distintas, `shared/config.py` debe resolver siempre desde la raíz del repo.

---

## 14. Próximos pasos

Invocar el skill `writing-plans` para crear un plan de implementación detallado con archivos, comandos y orden de ejecución.
