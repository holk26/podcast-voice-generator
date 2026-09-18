# Podcast Voice Generator — Arquitectura web

El proyecto está organizado en una arquitectura desacoplada para que el **backend** y el **frontend** puedan desplegarse en un servidor y el **worker** corra en tu PC local.

```
backend/     API REST + SSE (FastAPI)
frontend/    Aplicación web (Vite)
worker/      Proceso local que consume trabajos del backend
shared/      Contratos y configuración compartida (schemas, constantes)
```

La app de escritorio PyQt6 fue eliminada. Todo pasa por la web.

## Pila de servicios

`starter.py` levanta los tres servicios localmente para desarrollo:

| Servicio   | Origen                          | Puerto default | Health check                            |
|------------|---------------------------------|----------------|-----------------------------------------|
| API        | `python -m backend.app.main` (desde raíz) | 8000           | `GET http://127.0.0.1:8000/api/health`  |
| Worker     | `python -m worker.main` (desde raíz)      | 8001           | `GET http://127.0.0.1:8001/health`      |
| Web (Vite) | `npm run dev` (en `frontend/`)     | 5173           | `http://127.0.0.1:5173`                 |

Los tres procesos se lanzan en segundo plano, su salida se redirige a `logs/{api,worker,web}.log` **y** se reemite a la consola con el prefijo `[api]`/`[worker]`/`[web]`. Al finalizar, `starter.py` abre el monitor curses (`starter_monitor.py`) y el navegador en `http://127.0.0.1:5173`.

## Cómo ejecutar en desarrollo

### Lanzadores

- **Linux/macOS**: `./starter.sh`
- **Windows**: `starter.bat`

### Directamente

```bash
python starter.py
```

Desde el entorno virtual:

```bash
source venv311/bin/activate   # Windows: venv311\Scripts\activate
python starter.py
```

### Variables de entorno

```bash
API_PORT=9000 WORKER_PORT=9001 WEB_PORT=5174 python starter.py
```

| Variable      | Default | Descripción                                |
|---------------|---------|--------------------------------------------|
| `API_PORT`    | 8000    | FastAPI (`backend/app/main.py`)            |
| `WORKER_PORT` | 8001    | Worker de generación (`worker/main.py`)    |
| `WEB_PORT`    | 5173    | Vite dev server (`frontend/`)              |

## Autenticación y seguridad

La API está protegida con JWT para usuarios web y con un token estático para el worker.

### Variables de auth (backend)

| Variable               | Default | Descripción                                                  |
|------------------------|---------|--------------------------------------------------------------|
| `SECRET_KEY`           | *(vacío)* | Clave para firmar JWT. **Cambiar en producción.**          |
| `ACCESS_TOKEN_EXPIRE_DAYS` | 7   | Duración de los tokens de acceso.                          |
| `ADMIN_USER`           | `admin` | Usuario admin inicial.                                       |
| `ADMIN_PASSWORD`       | *(vacío)* | Contraseña inicial del admin (se hashea al primer login).  |
| `ADMIN_PASSWORD_HASH`  | *(vacío)* | Hash bcrypt directo del admin (opcional).                  |
| `WORKER_TOKEN`         | *(vacío)* | Token compartido entre backend y worker. **Obligatorio.**  |
| `REQUIRE_AUTH`         | `true` | En `false` deshabilita JWT para tests/desenvolvimiento.     |

### Endpoints de auth

- `POST /api/auth/login` — login de usuario, devuelve JWT.
- `GET /api/auth/me` — información del usuario actual.

Todos los endpoints de la API (salvo `/api/health` y `/api/auth/login`) requieren el header `Authorization: Bearer <jwt>`.

### Solución de problemas de login

Si la web muestra `Error: HTTP 401: User not found` después de iniciar sesión:

1. El navegador guarda el JWT en `localStorage` (`podcast_studio_auth`).
2. Si la base de datos del backend se reinicia (redeploy sin volumen persistente, nuevo contenedor, etc.), el usuario del token ya no existe, aunque el token siga siendo técnicamente válido.
3. **Solución rápida:** cierra sesión y vuelve a entrar. Esto recrea el usuario admin en la base de datos actual y genera un token nuevo.
4. Si persiste, abre las herramientas de desarrollador del navegador → Application → Local Storage → `https://podcash.app.moonsbow.com`, borra la clave `podcast_studio_auth` y recarga.
5. En el servidor, confirma que `DATABASE_URL` apunta a `/app/data/app.db` y que el volumen `/app/data` está montado.

### Endpoints del worker

- `GET /api/worker/jobs/next` — reclama el siguiente episodio pendiente.
- `POST /api/worker/jobs/{id}/complete` — marca episodio como completado.
- `POST /api/worker/jobs/{id}/fail` — marca episodio como fallido.
- `GET /api/worker/events` — stream SSE de nuevos trabajos.

Todos requieren `Authorization: Bearer <WORKER_TOKEN>`.

## Deploy en producción (servidor + PC local)

### 1. Servidor: backend + frontend

Copia `backend/` y `frontend/` al servidor (o el repo completo, los modelos y assets grandes pueden quedar en el PC local si no se usan voces clonadas en servidor).

```bash
# Backend
cd /ruta/al/repo
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp backend/.env.example backend/.env
# Edita backend/.env: SECRET_KEY, ADMIN_PASSWORD, WORKER_TOKEN, DATABASE_URL...
PYTHONPATH=/ruta/al/repo python -m backend.app.main
```

```bash
# Frontend
cd frontend
npm install
npm run build
# Sirve dist/ con nginx/caddy o usa el preview de Vite solo para pruebas
```

Expón `backend` en HTTPS con un dominio y añade ese origen a `CORS_ORIGINS` en el backend.

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

### 2. PC local: worker

El worker debe poder alcanzar la URL pública del backend. En este proyecto ya existe `worker/.env` configurado para apuntar al backend remoto. **No subas `worker/.env` a git** (está en `.gitignore`).

```bash
cd worker
source ../venv311/bin/activate
python -m main
```

Variables que controla `worker/.env`:

| Variable            | Default | Descripción |
|---------------------|---------|-------------|
| `BACKEND_URL`       | `http://127.0.0.1:8000` | URL pública del backend (`https://api.podcash.app.moonsbow.com`). |
| `WORKER_TOKEN`      | *(vacío)* | Token estático compartido con el backend. **Obligatorio.** |
| `AUTOPILOT_HOUR`    | 7 | Hora local a la que corre el piloto automático. |
| `SSE_RETRY_SECONDS` | 5 | Reconexión SSE ante desconexiones. |
| `POLL_BACKUP_SECONDS` | 30 | Intervalo de polling si el SSE no funciona. |
| `WORKER_GUI`        | `0` | Si se pone a `1`, lanza la ventana de estado tkinter. |

El worker guarda los archivos de audio generados localmente; **no los sube al servidor**.

> **Deploy actual:** backend en `https://api.podcash.app.moonsbow.com`.
> Si necesitas regenerar el `WORKER_TOKEN`, usa el endpoint de admin:
> ```bash
> TOKEN=$(curl -s -X POST https://api.podcash.app.moonsbow.com/api/auth/login \
>   -H 'Content-Type: application/json' \
>   -d '{"username":"admin","password":"admin"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
> curl -s -H "Authorization: Bearer $TOKEN" \
>   https://api.podcash.app.moonsbow.com/api/admin/worker-token
> ```
> Luego actualiza `WORKER_TOKEN` en `worker/.env` y en la variable de entorno del backend en Dokploy, y redepliega ambos.

El worker intenta conectarse por SSE a `/api/worker/events`; si falla, hace polling a `/api/worker/jobs/next` cada `POLL_BACKUP_SECONDS` (default 30 s).

## Comunicación backend ↔ worker

- **Push primario**: SSE (`/api/worker/events`). El backend notifica `new_job` cuando se crea o reintenta un episodio.
- **Respaldo**: polling periódico a `/api/worker/jobs/next`.
- **Resultado**: el worker reporta con `complete`/`fail` vía POST.

El worker **no toca la base de datos**; todo pasa por la API.

## Monitor curses (`starter_monitor.py`)

Dashboard en vivo en desarrollo. Muestra estado, logs y errores de cada servicio. Salir con `q`. **Cerrar el monitor no detiene los servicios**: para pararlos usa `Ctrl+C` en la terminal donde corre `starter.py`.

## Detener todo

`starter.py` captura `SIGINT` y `SIGTERM` y apaga limpiamente los tres procesos. **Nunca uses `kill -9`** salvo emergencia.

## Dependencias previas

```bash
# Python
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt

# Node (frontend)
cd frontend && npm install
```

### Dos venvs de inferencia (higgs y qwen3)

Los motores TTS clonados tienen requisitos incompatibles de `transformers` y no
pueden convivir en un mismo venv:

| Venv | `transformers` | Motor | Por qué |
|------|----------------|-------|---------|
| `venv311` | `==4.57.3` (pin) | qwen3 (qwen-tts) | Con tf 5.x el talker nunca emite el token EOS y el audio sale degenerado |
| `venv-higgs` | `>=5.3.0,<5.9` | higgs (voice clone v2) | `HiggsAudioV2TokenizerModel` solo existe en tf 5.3+ |

El worker corre cada síntesis en un subproceso y elige el intérprete por motor
(`worker/handlers.py::_tts_python_for`): `clone:<nombre>:qwen3` → `venv311`,
`clone:<nombre>` (higgs) → `venv-higgs`. Overrides: `QWEN3_PYTHON` / `HIGGS_PYTHON`.

Para crear el venv de higgs (clon del principal con transformers actualizado):

```bash
cp -a venv311 venv-higgs
venv-higgs/bin/python -m pip install 'transformers>=5.3.0,<5.9'  # OJO: usar python -m pip, los scripts del venv copiado apuntan a venv311
```

Opcional para CrewAI: tener [Ollama](https://ollama.ai) corriendo con el modelo configurado en `OLLAMA_DEFAULT_MODEL`.

## Estructura clave

| Archivo / Carpeta    | Qué hace                                                                      |
|----------------------|-------------------------------------------------------------------------------|
| `backend/app/main.py`| Aplicación FastAPI: routers, CORS, auth, static files.                        |
| `backend/app/auth.py`| Hashing bcrypt y JWT.                                                         |
| `backend/app/dependencies.py` | Dependencias de FastAPI: `get_current_user`, `require_worker_token`. |
| `backend/app/routes/worker.py` | Endpoints exclusivos del worker (jobs + SSE).                          |
| `backend/app/services/worker_service.py` | Lógica de reclamar/ completar/fallar jobs + notificaciones SSE. |
| `worker/client.py`   | Cliente HTTP del worker para hablar con el backend.                           |
| `worker/runner.py`   | Bucle principal: SSE + polling + procesamiento de episodios.                  |
| `worker/handlers.py` | Renderizado de audio y postproducción local.                                  |
| `shared/schemas/__init__.py` | Schemas Pydantic compartidos entre backend y worker.                  |
| `shared/config.py`   | Rutas y configuración compartida.                                             |
| `starter.py`         | Orquestador de desarrollo: api + worker + web + monitor.                      |

## Tests

```bash
python -m pytest backend/tests worker/tests -v --tb=short
```

En `backend/tests/conftest.py` se deshabilita auth (`REQUIRE_AUTH=false`) y se configura una base de datos SQLite temporal para los tests.
