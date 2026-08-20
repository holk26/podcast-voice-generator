# Diseño: Canales y CrewAI

## 1. Resumen

Extender el Podcast Voice Generator con **canales de contenido** y un **equipo de agentes CrewAI** que, usando **Ollama local**, propongan un plan editorial y generen guiones listos para convertirse en episodios de audio.

Esta fase mantiene el flujo existente (`pending → running → completed`) y reutiliza el worker, SSE y reproductor ya implementados.

## 2. Alcance

### Dentro del alcance
- CRUD de canales (nombre, descripción, nicho, formato, voz por defecto).
- Generación de plan editorial con CrewAI (propuesta de entradas).
- Aprobación/rechazo de entradas del plan.
- Generación de guion con CrewAI al aprobar una entrada.
- Creación automática de episodio `pending` a partir del guion aprobado.
- Pantallas `/channels`, `/channels/:id/plan` y `/studio`.
- Configuración de Ollama (URL, modelo por agente) en `config.yaml`.

### Fuera del alcance
- Scheduler automático que dispare entradas por fecha.
- Estados avanzados (`ready_for_review`, `published`).
- Clonación de voces (Voice Lab avanzado).
- Sound Gallery y audiolibros (fases posteriores).

## 3. Modelos de datos

### `Channel`
| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `name` | str | |
| `description` | str | |
| `niche` | str | tema/nicho del canal |
| `format` | str | `podcast`, `news`, `meditation`, `motivation` |
| `default_voice_id` | str | voz por defecto para episodios |
| `is_active` | bool | |
| `created_at` | str | ISO |
| `updated_at` | str | ISO |

### `ContentPlanEntry`
| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | int | PK |
| `channel_id` | int | FK |
| `title` | str | propuesto por CrewAI o manual |
| `description` | str | sinopsis/prompt |
| `scheduled_date` | str | ISO date, opcional |
| `status` | str | `draft`, `approved`, `rejected`, `generated` |
| `episode_id` | int | FK opcional a Episode |
| `created_at` | str | ISO |
| `updated_at` | str | ISO |

### `Episode` (existente)
Se reutiliza. Al aprobar una entrada se crea un episodio con:
- `title` = entry.title
- `type` = channel.format
- `source_text` = guion generado por CrewAI
- `voice_id` = channel.default_voice_id
- `status` = `pending`

## 4. Backend

### Nuevos endpoints

#### Canales
- `GET /api/channels` — lista.
- `POST /api/channels` — crear.
- `GET /api/channels/{id}` — detalle.
- `PUT /api/channels/{id}` — editar.
- `DELETE /api/channels/{id}` — eliminar.
- `POST /api/channels/{id}/activate` / `deactivate`.

#### Plan editorial
- `GET /api/channels/{id}/plan` — entradas del canal.
- `POST /api/channels/{id}/plan/generate` — CrewAI propone entradas.
- `POST /api/plan/{entry_id}/approve` — genera guion con CrewAI y crea episodio.
- `POST /api/plan/{entry_id}/reject` — marca como `rejected`.
- `DELETE /api/plan/{entry_id}` — eliminar entrada.

#### CrewAI / utilidades
- `GET /api/llm/status` — Ollama disponible y modelo por defecto listo.

### CrewAI

Se usa un `Crew` pequeño con tres agentes para mantenerlo ligero:

1. **ContentStrategist**: propone temas y títulos acordes al nicho/formato.
2. **ScriptWriter**: escribe el guion completo en español según el formato.
3. **ScriptEditor**: revisa ritmo, claridad y longitud.

Flujo al generar plan:
```
INPUT: channel (name, niche, format)
→ ContentStrategist genera 5 entradas (título + descripción)
→ Backend guarda entradas como draft
```

Flujo al aprobar entrada:
```
INPUT: entry (title, description) + channel (format, niche)
→ ScriptWriter genera guion
→ ScriptEditor lo revisa
→ Backend crea Episode con source_text = guion final
→ entry.status = generated, entry.episode_id = episode.id
```

### Ollama

- `OLLAMA_URL` desde variable de entorno o `config.yaml` (default `http://localhost:11434`).
- Modelo por defecto configurable; sugerido `llama3.1:8b`.
- `starter.py` verifica que Ollama responda y avisa si no.

## 5. Frontend

### Nuevas rutas
- `/channels` — lista de canales.
- `/channels/new` — crear canal.
- `/channels/:id/plan` — plan editorial y acciones.
- `/studio` — CrewAI Studio: seleccionar canal, generar plan y ver entradas.

### Componentes nuevos
- `ChannelCard`: resumen de canal.
- `ChannelForm`: crear/editar canal.
- `ContentPlanList`: tabla/lista de entradas con acciones.
- `PlanEntryCard`: título, descripción, fecha, estado, botones aprobar/rechazar.
- `StudioPanel`: selección de canal + botón generar plan.

### Stores
- `channelStore.ts`: CRUD de canales y entradas de plan.
- Reutilizar `episodeStore.ts` para el estado de episodios generados.

## 6. Integración con worker

Sin cambios en el worker. La aprobación de una entrada crea un episodio `pending`; el worker lo procesa usando el motor TTS actual (Edge-TTS por defecto) y el pipeline de post-procesamiento existente.

## 7. Flujo de usuario

1. Usuario crea un canal en `/channels/new`.
2. En `/studio` selecciona el canal y pulsa "Generar plan editorial".
3. CrewAI devuelve entradas en estado `draft`.
4. Usuario va a `/channels/:id/plan`.
5. Revisa cada entrada; pulsa "Aprobar y generar guion".
6. CrewAI genera el guion; se crea un episodio `pending`.
7. El episodio aparece en `/queue` con SSE en tiempo real.
8. Cuando termina, el usuario puede escuchar el audio.

## 8. Configuración

```yaml
llm:
  provider: ollama
  base_url: http://localhost:11434
  default_model: llama3.1:8b
```

Variables de entorno:
- `OLLAMA_URL`
- `OLLAMA_MODEL`

## 9. Testing

### Backend
- Tests de CRUD de canales.
- Tests de generación de plan con CrewAI mockeado.
- Tests de aprobación de entrada creando episodio.

### Frontend
- Tests de ChannelForm.
- Tests de ContentPlanList.
- Tests de StudioPanel con mocked API.

## 10. Plan de implementación sugerido

1. **Infraestructura**: instalar `crewai` y cliente de Ollama; añadir modelos y config.
2. **Modelos y migración**: `Channel`, `ContentPlanEntry`.
3. **Backend endpoints**: CRUD canales + plan.
4. **CrewAI service**: agentes y tareas para plan y guion.
5. **Frontend rutas**: `/channels`, `/channels/:id/plan`, `/studio`.
6. **Integración**: aprobar entrada → crear episodio → worker.
7. **Tests y pulido**.
