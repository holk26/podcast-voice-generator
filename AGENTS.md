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
| API        | `cd backend && python -m app.main` | 8000           | `GET http://127.0.0.1:8000/api/health`  |
| Worker     | `cd worker && python -m main`      | 8001           | `GET http://127.0.0.1:8001/health`      |
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
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env
# Edita .env: SECRET_KEY, ADMIN_PASSWORD, WORKER_TOKEN, DATABASE_URL...
python -m app.main
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

1. Crea dos aplicaciones en Dokploy:
   - **Frontend**: tipo `static` o `nixpacks`, build path `/frontend`, dominio `https://podcash.app.moonsbow.com`.
   - **Backend**: tipo `dockerfile`, build path `/backend`, dominio `https://api.podcash.app.moonsbow.com`, puerto `8000`.
2. Variables de entorno obligatorias del backend:
   - `SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`, `WORKER_TOKEN`
   - `DATABASE_URL=sqlite:////app/data/app.db` (ruta **absoluta**, 4 barras)
   - `CORS_ORIGINS=https://podcash.app.moonsbow.com`
   - `API_PORT=8000`, `REQUIRE_AUTH=true`
3. Monta volúmenes persistentes en el backend para no perder datos al redeployar:
   - `/app/data` → base SQLite (`app.db`)
   - `/app/output` → audios generados expuestos por `/outputs`
   - `/app/voices` → muestras de voz clonadas
   - `/app/projects` → archivos de proyectos
   - `/app/music` → música/branding subido
4. Asegúrate de que el frontend apunte a la URL pública de la API (`VITE_API_URL=https://api.podcash.app.moonsbow.com`).

> **Deploy actual:** backend en `https://api.podcash.app.moonsbow.com` con volúmenes persistentes para `/app/data`, `/app/output`, `/app/voices`, `/app/projects` y `/app/music`. Usuario inicial: `admin` / `admin`.

### 2. PC local: worker

El worker debe poder alcanzar la URL pública del backend.

```bash
cd worker
source ../venv311/bin/activate
export BACKEND_URL=https://tu-dominio.com/api
export WORKER_TOKEN=<mismo_token_que_backend>
python -m main
```

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
