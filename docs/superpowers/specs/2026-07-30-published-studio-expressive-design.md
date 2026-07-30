# Diseño: Estado "Publicado", Studio ordenado y voces expresivas

Fecha: 2026-07-30
Estado: aprobado por el usuario (diseño), pendiente de plan de implementación.

## Contexto

Tres mejoras sobre la pila web (`web_api` FastAPI + `web` React + `worker`):

1. El usuario no recuerda qué episodios ya publicó (Spotify/YouTube a mano).
2. El Studio acumula entradas de plan viejas y abruma; debe centrarse en crear
   y potenciar canales: descripción y configuración básica primero.
3. Las voces clonadas Higgs soportan tokens inline (`<|emotion:…|>`,
   `<|style:…|>`, `<|prosody:…|>`, `<|sfx:…|>`) que hoy no se usan; se quieren
   voces más expresivas de forma automática.

Decisiones ya tomadas con el usuario:

- "Publicado" = **marca manual** (no integración automática con RSS).
- Visible y cambiable en **lista de episodios y vista del canal**.
- Entradas viejas: **no borrar datos**; ordenar con lo más reciente primero y
  plegar lo antiguo.
- Emociones: **automáticas por contenido**, decididas por el congreso.

## Feature 1 — Estado "Publicado"

### Datos

- `Episode.published_at`: `DateTime`, nullable. `NULL` = no publicado.
- Migración ligera en `web_api/database.py` al arrancar: si la tabla
  `episodes` existe y le falta la columna, `ALTER TABLE episodes ADD COLUMN
  published_at DATETIME`. Instalaciones nuevas la obtienen vía `create_all`.

### API

- `POST /api/episodes/{id}/publish` → `published_at = ahora` (UTC naive, como
  el resto del modelo). Idempotente: republicar solo actualiza la fecha.
  409 si el episodio no está `completed` (no hay audio que publicar).
  404 si no existe.
- `POST /api/episodes/{id}/unpublish` → `published_at = NULL`. Idempotente.
- `EpisodeResponse` incluye `published_at: datetime | None`.

### Web

- `api/client.ts`: `publishEpisode(id)`, `unpublishEpisode(id)`.
- `episodeStore`: acciones `publish(id)` / `unpublish(id)` que actualizan el
  episodio en el estado local con la respuesta del servidor.
- `EpisodeCard`: badge verde `Publicado · <fecha corta>` junto al badge de
  estado; botón "Marcar publicado" (solo si `completed` y sin `published_at`)
  o "Desmarcar" (si tiene `published_at`).
- `queue.tsx`: filtro Todos / Sin publicar / Publicados (local, sobre el
  store ya cargado).
- Vista del canal (plan/temporadas): entradas con `episode_id` enlazado
  muestran badge "Publicado" si `episode_published_at` no es `NULL` (el
  endpoint del plan lo expone, ver Feature 2).

## Feature 2 — Studio ordenado

- El backend `GET /api/channels/{id}/plan` **ya ordena** por `created_at desc`;
  no requiere cambio. La vista del canal sí necesita el estado de publicación:
  el endpoint ya consulta el episodio enlazado para `audio_url`; se añade
  `episode_published_at: datetime | None` a `PlanEntryResponse` poblado en el
  mismo bucle.
- `studio.tsx`, al seleccionar canal, orden de secciones:
  1. Cabecera del canal: nombre, descripción, nicho, formato + botón Editar
     (lleva a `channels.$id.edit.tsx`).
  2. Configuración básica (voz, minutos, episodios/semana, autopilot) — el
     `StudioPanel` actual, que ya edita en vivo.
  3. Plan editorial: por defecto **solo borradores** (`status === 'draft'`);
     sección "Archivo" plegable con `generated` y `rejected`, más recientes
     primero.
- Sin cambios de datos ni borrados.

## Feature 3 — Voces expresivas automáticas (Higgs)

### Congreso (`web_api/services/crew_service.py`)

- `CLEAN_PROMPT` (paso "director de voz") pasa a tener dos misiones: limpiar
  para TTS **y** colocar tokens de emoción. Se le da la lista cerrada
  (`HIGGS_EMOTIONS`, importada de `core/higgs_engine.py`) y la regla: **un
  token `<|emotion:…|>` al inicio de cada sección**, elegido según el tono
  del contenido; prohibido inventar tokens fuera de la lista.
- `CLEAN_PROMPT` deja de decir "elimina todo lo que no se lee": ahora conserva
  explícitamente los tokens `<|…|>`.
- `_strip_markup` conserva los tokens `<|…|>` (hoy no los toca, pero se fija
  en tests para que nadie lo rompa).

### Síntesis (`web_api/routes/tts.py` y motores)

- Nueva utilidad compartida (p. ej. `core/emotion_tags.py`):
  - `sanitize_emotion_tags(text, allowed: set[str]) -> str`: elimina tokens
    `<|…|>` no reconocidos y los reconocidos no soportados por el motor.
  - Catálogos: Higgs = `HIGGS_EMOTIONS` + `HIGGS_STYLES` + `HIGGS_SFX` +
    prosody (`speed_slow`, `speed_fast`, `pitch_high`, `pitch_low`, `pause`);
    edge y Qwen3 = conjunto vacío (se les quita todo token antes de sintetizar).
- `tts.py` aplica la sanitización según el motor de la voz antes de llamar al
  engine. Rutas de episodios (worker → `/api/tts/synthesize`) quedan cubiertas
  por el mismo punto.

### Alcance

- Emociones solo en Higgs (voces `clone:…` sin sufijo). Qwen3-Base no las
  soporta; edge-tts tampoco.

## Tests

- `tests/web_api/test_episodes.py`: publish/unpublish happy path, 409 si no
  `completed`, 404, idempotencia, `published_at` en la respuesta.
- `tests/web_api/test_channels.py`: orden del plan (`created_at desc`).
- `tests/web_api/test_crew_service.py`: `_strip_markup` conserva tokens
  `<|emotion:elation|>`; caso de limpieza con tokens presentes.
- Nuevo `tests/test_emotion_tags.py`: whitelist por motor, eliminación de
  tokens desconocidos, texto sin tokens intacto.
- Frontend: actualizar `EpisodeCard.test.tsx` con el badge/botón de publicado.

## Fuera de alcance (YAGNI)

- Integración con `publishers/rss_publisher.py` (legacy de scripts demo).
- Historial de publicaciones / destinos múltiples / fechas por destino.
- Emociones en Qwen3 o edge-tts; control manual de emociones en la UI.
- Borrado o purga de episodios/entradas viejas.

## Errores y edge cases

- Publicar un episodio `pending/running/failed` → 409 con mensaje claro.
- LLM inventa tokens (`<|emotion:felicidad_extrema|>`) → se eliminan en
  síntesis; nunca se pronuncian.
- Guion sin tokens (LLM los omite) → válido; síntesis normal, sin expresividad
  extra. No es error.
- Migración con BD ya existente: `ALTER TABLE` envuelto en chequeo de
  `PRAGMA table_info`; si la columna ya está, no-op.
