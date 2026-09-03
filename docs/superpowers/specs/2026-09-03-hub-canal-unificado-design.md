# Hub de canal unificado + flujo "Generar guion con IA"

Fecha: 2026-09-03
Estado: aprobado por el usuario (diseño completo, implementación autónoma autorizada)

## Problema

Tres superficies se solapan (ERRORES.txt P1/P2):

- `/studio` (393 líneas), `/channels` y `/channels/$id/plan` cubren el mismo
  flujo editorial. No está claro dónde se produce un episodio.
- La configuración del canal vive en 3 sitios: "Configuración rápida" y
  `StudioPanel` (con su propio selector de canal duplicado) en `/studio`, y
  `/channels/$id/edit`.
- `ScriptEditorModal.tsx` existe pero no está conectado en ninguna parte
  (código muerto).
- No hay forma de dar materia prima (txt/md) al congreso de agentes y obtener
  un guion editable antes de encolar el episodio.

## Objetivo

Un único lugar (`/channels/$id`) donde vive todo lo de un canal, con dos
acciones de producción claras: **Cargar guion** (txt/md directo a cola, flujo
actual) y **Generar guion con IA** (txt/md → congreso → edición → cola).

## Diseño

### Rutas

| Ruta | Estado |
|---|---|
| `/channels` | Se mantiene; la tarjeta de cada canal enlaza al hub |
| `/channels/$id` | **Nuevo hub**. Tabs vía search param `tab=plan\|episodios\|config` (default `plan`) |
| `/channels/$id/plan` | Redirect → `/channels/$id?tab=plan` |
| `/channels/$id/edit` | Redirect → `/channels/$id?tab=config` |
| `/studio` | Redirect → `/channels`; se elimina del menú lateral |

### Hub `/channels/$id`

**Header** (siempre visible):
- `ChannelSelector` para cambiar de canal sin salir del hub.
- Nombre, nicho • formato, badges (Activo/Inactivo, 🤖 autopilot, Publicado),
  línea de meta (min objetivo, eps/semana, nº de voces).
- Acciones: **Cargar guion** (UploadScriptModal actual), **Generar guion con IA**
  (wizard nuevo), Publicar/Desmarcar publicado, Eliminar (ConfirmDialog).

**Tab Plan editorial**: barra de progreso (generados/total), filtro por
temporada, toggle lista/calendario (ContentPlanList/PlanCalendar), botón
*Generar con IA* (3/5/8 ideas), selector de provider/modelo LLM con badge de
estado (configuración global, la UI se mueve desde `/studio`), CongressTable
(mesa redonda en vivo), aprobar/rechazar/eliminar entradas (ya con
confirmación).

**Tab Episodios**: episodios **del canal** vía nuevo filtro `?channel_id=` en
`GET /api/episodes`. Cada fila: título, badge de estado, reproductor de audio,
acciones: **Editar guion** (ScriptEditorModal, guardar / guardar y reintentar),
Reintentar (si falló), Marcar/Desmarcar publicado, enlace a la cola.

**Tab Configuración**: un único formulario con **guardado explícito** que
consolida todo lo que hoy está repartido: nombre, descripción, nicho, formato,
duración objetivo, episodios/semana, nº de voces (1 monólogo / 2 diálogo con
editor de `speaker_voices`), voz por defecto, autopilot, activo.

### Flujo "Generar guion con IA" (wizard de 3 pasos, modal)

1. **Fuente**: subir `.txt`/`.md` o pegar texto; título opcional.
   `POST /api/channels/{id}/script-jobs` (multipart archivo o JSON
   `{text, title}`) → 202 `{job_id}`. Rechaza si ya hay un job de guion en
   curso para el canal (409), si el canal no existe (404) o si el texto vacío
   (400).
2. **Congreso en vivo**: `EventSource` a `/api/jobs/{job_id}/events` (vía
   `sseUrl()`, que ya resuelve el token por query param). El backend corre el
   congreso en un hilo del job registry existente
   (`automation_service._start`, clave de dedup `script:channel:{id}:raw`),
   emitiendo pasos: limpieza/estructura → investigación → esquema → escritura
   por secciones → edición. UI: lista de pasos con estado + salida del agente.
   Si el provider LLM no está disponible, el botón de entrada va deshabilitado
   con tooltip que apunta al selector del tab Plan.
3. **Edición**: el guion resultante (`result.script_text` del evento final)
   abre un editor grande (título + textarea) con conteo de palabras y minutos
   estimados (~140 ppm). Tres salidas:
   - **Crear episodio** → `POST /api/channels/{id}/create-from-text` con el
     texto editado → navega a `/queue?highlight={episode_id}`.
   - **Regenerar** → vuelve al paso 1 conservando la fuente.
   - **Descartar** → cierra; no se persiste nada.

El resultado vive solo en memoria del job: nada en BD hasta *Crear episodio*.

### Backend

- **`GET /api/episodes?channel_id=`**: filtro opcional en
  `backend/app/routes/episodes.py` (~3 líneas). `Episode.channel_id` ya existe.
- **`POST /api/channels/{id}/script-jobs`**: en `channels.py`. Acepta
  multipart (`script` UploadFile + `title` Form) o JSON (`{text, title}`).
  Normaliza a `raw_text` (limpieza básica de markdown como `upload-script`) y
  lanza `start_raw_script_job(channel, raw_text, title, minutes)` en
  `automation_service.py`, que corre una variante de `generate_script`
  (`generate_script_from_raw` en `crew_service.py`) cuya materia prima es el
  texto completo en vez de `entry.description`, con título del request o
  derivado del nombre de archivo. `registry.finish(job_id, {script_text,
  title, word_count})`. LLM: `get_script_llm()` actual (mismo provider/modelo
  global del resto del congreso).
- **Reutiliza**: `create-from-text`, job registry + SSE, `_start` con dedup.

### Limpieza

- Borrar `frontend/src/routes/studio.tsx` y `frontend/src/components/StudioPanel.tsx`.
- Quitar ítem Studio de `Layout.tsx`.
- `ScriptEditorModal` conectado en `EpisodeCard` (/queue) y tab Episodios.
- `ChannelSelector` único en el header del hub.

### Errores de ERRORES.txt que cierra

- P1 solapamiento Studio/Canales/plan.
- P2 Studio (~400 líneas, selector duplicado, tabs que mezclan resumen y config).

Quedan fuera de este spec: responsive/móvil, ruido de navegación (emoji, /login
muerta), unificación de design system.

## Manejo de errores

- Job falla (LLM caído, timeout): paso 2 muestra el error del evento final y
  ofrece Regenerar/Descartar.
- 409 (job en curso): mensaje "ya hay un guion en generación".
- Provider no disponible: botón deshabilitado + tooltip.
- `channel_id` inválido en el filtro: respuesta vacía (no 404; el listado es
  global).

## Testing

- **Backend (pytest)**: filtro `channel_id` en listado de episodios; endpoint
  `script-jobs` (orquestador/crew mockeados — patrón de tests existentes,
  `REQUIRE_AUTH=false`); 400/404/409.
- **Frontend (vitest)**: render de los 3 tabs del hub con datos mockeados;
  wizard (paso fuente → crea job; paso edición → create-from-text); redirect
  de `/studio`. Seguir el estilo de `EpisodeCard.test.tsx`.
- **E2E manual (Playwright tras deploy)**: login, abrir hub, tabs, wizard con
  mock/LLM real según disponibilidad, editar guion, crear episodio.

## Despliegue

Push a `master` → auto-deploy Dokploy de `podcash-web` (frontend) y
`podcash-api` (backend, Dockerfile). Validar: health checks 200, smoke test
Playwright en producción, sin caché vieja de `index.html` (ya sirve
`no-cache`).
