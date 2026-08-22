# Diseño: Integración de Kimi en Studio, flujo de prueba remoto y GUI del worker

## Estado

Aprobado por el usuario el 2026-08-22.

## Contexto

El Podcast Voice Generator tiene una arquitectura desacoplada:

- `backend/` — API REST + SSE (FastAPI), desplegado en `https://api.podcash.app.moonsbow.com`.
- `frontend/` — Aplicación web (Vite), desplegada en `https://podcash.app.moonsbow.com`.
- `worker/` — Proceso local en la PC del usuario que consume trabajos del backend.

Actualmente el backend solo soporta Ollama como provider de IA. El frontend en `/studio` muestra un único selector de modelo Ollama y un badge de disponibilidad.

## Objetivos

1. Hacer disponible **Kimi** como provider de IA en la web (`https://podcash.app.moonsbow.com`), leyendo su token de las configuraciones locales del usuario.
2. Permitir generar un guion desde la web, dejar el episodio en cola y que el **worker local** lo ejecute.
3. No subir el audio generado a la web; con que quede bien nombrado en local es suficiente.
4. Agregar una **GUI sencilla de escritorio (tkinter)** al worker para ver estado de conexión y trabajo activo.
5. Documentar el deploy con Dokploy en `AGENTS.md`.

## Decisiones de diseño

### Proveedores de IA

- Se implementa un switch minimalista de providers en el backend: `ollama` y `kimi`.
- Kimi se integra como provider OpenAI-compatible usando CrewAI (`LLM(model="kimi-for-coding", api_key=..., base_url="https://api.kimi.com/coding/v1")`).
- El token de Kimi se obtiene de la variable de entorno `KIMI_API_KEY`. En desarrollo, si no está definida, se lee como fallback de `~/.kimi-code/credentials/kimi-code.json`.
- OpenCode Go queda fuera del selector inicial porque su configuración local (`~/.config/opencode/opencode.jsonc`) no expone URL ni token propio.

### Persistencia del provider/modelo seleccionado

- Se guardan dos valores en `config.yaml`: `llm_provider` y `llm_model`.
- `backend/app/config.py` se extiende para leer/escribir ambos.
- El provider/modelo por defecto sigue siendo Ollama si no hay Kimi configurado.

### API del backend

- `GET /llm/providers` — lista providers disponibles con `id`, `name`, `available`, `default_model`.
- `GET /llm/models?provider=<id>` — modelos del provider seleccionado.
- `POST /llm/model` — acepta `{ "provider": "kimi", "model": "kimi-for-coding" }` y persiste.
- `GET /llm/status` — estado del provider activo.

### Frontend

- En `/studio` se reemplaza el selector único de modelo por dos selects: **Provider** y **Modelo**.
- El selector de modelo se actualiza dinámicamente según el provider elegido.
- El badge "IA lista" / "IA no disponible" refleja el provider activo.
- Un provider no configurado aparece deshabilitado.

### Flujo de podcast de prueba

1. El usuario crea un canal de prueba en `https://podcash.app.moonsbow.com/channels`.
2. En `/studio` selecciona el canal, provider = **Kimi**, modelo = **kimi-for-coding**.
3. Pulsa "Generar 5 ideas"; el backend genera entradas de plan.
4. Aprueba una entrada; el backend crea un episodio en estado `pending`.
5. El usuario corre el worker en su PC local.
6. El worker reclama el job vía SSE/polling, genera el audio y lo guarda en `output/<episode_id>/` con nombre descriptivo.
7. El worker reporta `complete` al backend; el episodio aparece generado en la web sin archivo de audio remoto.

### GUI del worker

- Nueva ventana tkinter (`worker/gui.py`) lanzada opcionalmente con `WORKER_GUI=1`.
- Muestra:
  - Estado de conexión al backend.
  - Job actual en ejecución (ID, título).
  - Últimos logs (tail de ~20 líneas).
  - Botones Reconectar y Salir.
- Corre en un hilo separado sin bloquear el bucle del worker.

### Documentación

- Se actualiza `AGENTS.md` con una sección clara de deploy con Dokploy, incluyendo variables de entorno, volúmenes persistentes, dominios y regeneración de `WORKER_TOKEN`.

## Archivos a modificar/crear

### Backend

- `backend/app/services/llm_provider.py` — soporte multi-provider.
- `backend/app/routes/llm.py` — nuevos endpoints.
- `backend/app/config.py` — nuevas variables y persistencia.
- `backend/app/services/crew_service.py` — pasar provider/modelo al LLM.

### Frontend

- `frontend/src/routes/studio.tsx` — selector de provider + modelo.
- `frontend/src/api/client.ts` — nuevos métodos de API.
- `frontend/src/types.ts` — tipos si son necesarios.

### Worker

- `worker/gui.py` — nueva GUI tkinter.
- `worker/main.py` — lanzar GUI condicionalmente.

### Docs

- `AGENTS.md` — sección Dokploy.

## Verificación

- `GET /llm/providers` devuelve Kimi cuando `KIMI_API_KEY` está configurado.
- El frontend muestra Kimi y permite seleccionar modelo.
- Se crea canal de prueba, se generan ideas, se aprueba una entrada y el worker local la procesa.
- La GUI tkinter abre y muestra el estado del worker.
- `AGENTS.md` refleja el proceso de deploy en Dokploy.
