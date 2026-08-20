# Diseño: Interfaz Web + Content Machine para Podcast Voice Generator

## 1. Resumen

Se diseña una interfaz web local para el proyecto **Podcast Voice Generator**, transformándolo en una **máquina de contenido automatizado** para generar podcasts, audiolibros, meditaciones y motivaciones. La solución incluye:

- Interfaz web moderna (**React + Vite + Tailwind + TanStack Router + Zustand**).
- Backend API en **FastAPI**.
- Worker de generación de audio como proceso independiente.
- **CrewAI** con agentes especializados (estratega, investigador, guionista, editor, revisor, audio engineer).
- **Ollama** como LLM local por defecto para reducir costos.
- **Voice Lab** para gestionar y clonar voces.
- **Sound Gallery** para sonidos ambientes, música y efectos.
- **Audiolibros** con procesamiento por capítulos.
- Base de datos local **SQLite** para robustez.
- Archivo único `starter.py` para levantar todos los servicios.

## 2. Objetivos

- Permitir generar podcasts y audiolibros desde el navegador.
- Probar diferentes voces de forma sencilla.
- Gestionar voces clonadas con nombre, motor y muestras.
- Automatizar la creación de contenido mediante canales y calendario editorial.
- Mezclar audio de forma inteligente con ambientes, música y branding.
- Usar modelos locales (Ollama) como motor de IA por defecto.
- Mantener todo local, simple y fácil de levantar.

## 3. Arquitectura y servicios

La aplicación corre localmente con servicios separados en sus propios puertos:

| Servicio | Tecnología | Puerto | Responsabilidad |
|----------|-----------|--------|-----------------|
| `web` | React + Vite + Tailwind + TanStack Router + Zustand | `5173` | Interfaz de usuario |
| `api` | FastAPI | `8000` | Endpoints REST, gestión de base de datos, servir archivos |
| `worker` | Python | `8001` | Worker de generación de audio + health check |
| `ollama` | Ollama | `11434` | LLM local para agentes CrewAI |

**Datos compartidos**
- Base de datos SQLite: `data/app.db`.
- Archivos de audio: `output/`.
- Muestras de voz: `voices/clones/`.
- Sonidos: `sfx_library/`.

**Comunicación**
- Frontend ↔ API: HTTP REST + Server-Sent Events (SSE) para progreso.
- API ↔ Worker: SQLite compartida.
- API/Worker ↔ Ollama: API local de Ollama.
- API sirve archivos estáticos desde `output/` en `/outputs/*`.

**Seguridad local**
- Sin autenticación (uso local).
- CORS permitiendo `http://localhost:5173`.
- Bind solo a `127.0.0.1`.

## 4. Estructura de archivos

```
podcast with VRAM nvidia/
├── web/                          # Frontend React + Vite
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── routes/
│       │   ├── __root.tsx
│       │   ├── index.tsx         # Dashboard
│       │   ├── voices.tsx        # Voice Lab + probar voces
│       │   ├── create.tsx        # Crear episodio
│       │   ├── queue.tsx         # Cola y resultados
│       │   ├── channels.tsx      # Canales
│       │   ├── channel-plan.tsx  # Plan editorial
│       │   ├── studio.tsx        # CrewAI Studio
│       │   ├── machine.tsx       # Máquina de contenido
│       │   ├── audiobooks.tsx    # Audiolibros
│       │   └── sounds.tsx        # Sound Gallery
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── VoiceSelector.tsx
│       │   ├── AudioPlayer.tsx
│       │   ├── EpisodeCard.tsx
│       │   ├── CreateEpisodeForm.tsx
│       │   └── SoundUploader.tsx
│       ├── stores/
│       │   ├── appStore.ts
│       │   ├── episodeStore.ts
│       │   ├── voiceStore.ts
│       │   └── channelStore.ts
│       ├── api/
│       │   └── client.ts
│       └── types/
│           └── index.ts
├── web_api/                      # Backend FastAPI
│   ├── main.py
│   ├── dependencies.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routes/
│   │   ├── voices.py
│   │   ├── tts.py
│   │   ├── episodes.py
│   │   ├── channels.py
│   │   ├── plans.py
│   │   ├── audiobooks.py
│   │   ├── sounds.py
│   │   ├── crew.py
│   │   └── llm.py
│   └── services/
│       ├── queue_service.py
│       ├── file_service.py
│       ├── crew_service.py
│       └── tts_service.py
├── worker/                       # Worker de generación
│   ├── __init__.py
│   ├── main.py
│   ├── runner.py
│   └── handlers/
│       ├── podcast_handler.py
│       ├── audiobook_handler.py
│       └── voice_clone_handler.py
├── crew/                         # Agentes CrewAI
│   ├── agents/
│   │   ├── strategist.py
│   │   ├── researcher.py
│   │   ├── writer.py
│   │   ├── editor.py
│   │   ├── reviewer.py
│   │   └── audio_engineer.py
│   ├── tasks/
│   │   ├── research_task.py
│   │   ├── brief_task.py
│   │   ├── write_task.py
│   │   ├── edit_task.py
│   │   ├── review_task.py
│   │   ├── format_task.py
│   │   └── mixing_plan_task.py
│   └── crews/
│       └── content_crew.py
├── data/                         # SQLite + backups
│   └── app.db
├── output/                       # Audios generados
├── starter.py                    # Lanza todos los servicios
├── starter.sh
└── starter.bat
```

## 5. Frontend

### Stack
- **React 18+** con TypeScript.
- **Vite** como build tool y dev server.
- **Tailwind CSS** para estilos.
- **TanStack Router** para routing tipo archivo.
- **Zustand** para estado global.

### Rutas
| Ruta | Pantalla |
|------|----------|
| `/` | Dashboard |
| `/voices` | Voice Lab: probar, crear, clonar y gestionar voces |
| `/create` | Crear episodio manual |
| `/queue` | Cola de episodios y resultados |
| `/channels` | Lista de canales |
| `/channels/:id/plan` | Plan editorial del canal |
| `/studio` | CrewAI Studio: generar contenido con IA |
| `/machine` | Máquina de contenido automática |
| `/audiobooks` | Audiolibros |
| `/sounds` | Sound Gallery |
| `/settings/llm` | Configuración de Ollama y modelos |

### Componentes clave
- `Layout`: navegación lateral y contenedor.
- `VoiceSelector`: dropdown con búsqueda de voces.
- `AudioPlayer`: reproductor con controles.
- `EpisodeCard`: tarjeta con estado, progreso y acciones.
- `CreateEpisodeForm`: formulario de nuevo episodio.
- `SoundUploader`: subida de sonidos con preview.
- `ChannelCard`: resumen de canal.
- `ContentCalendar`: calendario editorial.

## 6. Backend — Endpoints

### Voces
- `GET /api/voices` — lista de perfiles de voz.
- `POST /api/voices` — crear perfil.
- `GET /api/voices/:id` — detalle.
- `PUT /api/voices/:id` — editar.
- `DELETE /api/voices/:id` — eliminar.
- `POST /api/voices/:id/clone` — clonar voz desde muestra.
- `POST /api/voices/:id/test` — generar preview.

### TTS
- `POST /api/tts/preview` — genera audio corto de prueba.

### Episodios
- `GET /api/episodes` — lista con filtros.
- `GET /api/episodes/:id` — detalle.
- `POST /api/episodes` — crear episodio.
- `POST /api/episodes/:id/run` — forzar ejecución.
- `POST /api/episodes/:id/cancel` — cancelar.
- `POST /api/episodes/:id/remix` — re-mezclar.
- `POST /api/episodes/:id/enhance` — re-aplicar post-procesamiento.
- `DELETE /api/episodes/:id` — eliminar.
- `GET /api/episodes/:id/stems` — pistas intermedias.

### Canales
- CRUD de canales.
- `POST /api/channels/:id/activate` / `deactivate`.

### Plan editorial
- `GET /api/channels/:id/plan` — plan del canal.
- `POST /api/channels/:id/plan/generate` — generar plan con IA.
- `POST /api/plan/:entry_id/approve` — aprobar entrada.

### CrewAI
- `POST /api/crew/generate` — generar guion con CrewAI.
- `GET /api/crew/status` — estado de tareas.

### Audiolibros
- `POST /api/audiobooks` — crear desde archivo/URL.
- `GET /api/audiobooks` — lista.
- `GET /api/audiobooks/:id` — detalle.
- `POST /api/audiobooks/:id/generate` — encolar generación.
- `GET /api/audiobooks/:id/chapters/:num/audio` — audio de capítulo.

### Sonidos
- `GET /api/sounds` — lista con filtros.
- `POST /api/sounds` — subir sonido.
- `DELETE /api/sounds/:id`.
- `POST /api/sounds/:id/preview`.

### Dashboard / config
- `GET /api/dashboard` — contadores.
- `GET /api/config` — estado de servicios, GPU, motores.
- `GET /api/llm/status` — estado de Ollama y modelos.

### Archivos
- `GET /outputs/*` — sirve archivos generados.

## 7. Base de datos SQLite

Se reemplaza el JSON compartido por SQLite para evitar race conditions y facilitar queries.

### Tablas principales
- `episodes`: episodios generados.
- `channels`: canales de contenido.
- `content_plans`: entradas del calendario editorial.
- `voice_profiles`: perfiles de voz.
- `sounds`: sonidos de la galería.
- `audiobooks`: audiolibros.
- `chapters`: capítulos de audiolibros.
- `jobs`: tareas del worker.
- `crew_tasks`: tareas de CrewAI.

### Modelo de estados de episodio
```
pending → running → ready_for_review → ready → published
   ↓         ↓            ↓
failed   cancelled     rejected
```

## 8. Worker

Proceso Python independiente que consume la cola SQLite.

**Responsabilidades**
- Leer trabajos pendientes cada 2 segundos.
- Ejecutar un episodio principal a la vez.
- Para audiolibros, procesar capítulos en paralelo limitado por VRAM.
- Actualizar estado y errores en SQLite.
- Exponer `GET /health` en puerto `8001`.

**Configuración**
- `WORKER_POLL_INTERVAL=2`
- `MAX_CONCURRENT_CHAPTERS=2`
- `MAX_VRAM_USAGE_GB=16`
- `WORKER_DATA_DIR=./data`
- `WORKER_OUTPUT_DIR=./output`

**Fallback de motores**
- Si el motor principal falla, usar Edge-TTS como fallback.
- Configurable por canal.

## 9. Starter

`starter.py` levanta todos los servicios con un solo comando.

**Pasos**
1. Verificar puertos libres.
2. Verificar/levantar Ollama.
3. Verificar modelos de Ollama descargados.
4. Lanzar FastAPI en `localhost:8000`.
5. Lanzar Worker en `localhost:8001`.
6. Lanzar Vite en `localhost:5173`.
7. Esperar health checks.
8. Abrir navegador en `http://localhost:5173`.
9. Capturar `Ctrl+C` y detener todos los procesos limpiamente.

**Variables de entorno**
| Variable | Default |
|----------|---------|
| `API_PORT` | `8000` |
| `WORKER_PORT` | `8001` |
| `WEB_PORT` | `5173` |
| `OLLAMA_URL` | `http://localhost:11434` |
| `DATA_DIR` | `./data` |
| `OUTPUT_DIR` | `./output` |

## 10. Voice Lab

Gestión completa de voces.

**Funcionalidades**
- Listar voces con nombre, motor, idioma, estado.
- Probar voz con texto corto.
- Crear perfil manual.
- Clonar voz subiendo muestra de audio (XTTS/Zonos/Higgs).
- Editar nombre, descripción y parámetros.
- Eliminar perfil.

**Almacenamiento**
- Metadatos en SQLite.
- Muestras en `voices/clones/<voice_id>/`.

## 11. CrewAI Content Machine

Sistema de agentes para generación automática de contenido.

### Agentes
| Agente | Rol |
|--------|-----|
| `ContentStrategist` | Crea canales, planes editoriales y decide qué generar. |
| `NicheResearcher` | Investiga temas relevantes para cada canal. |
| `TopicCurator` | Filtra y prioriza temas. |
| `ScriptWriter` | Escribe el guion del episodio. |
| `ScriptEditor` | Pule ritmo, claridad y formato. |
| `QualityReviewer` | Valida coherencia, tono y longitud. |
| `FormatSpecialist` | Adapta al formato: podcast, meditación, motivación, noticias. |
| `SEOSpecialist` | Genera títulos, descripciones y tags. |

### Flujo
1. Usuario crea canal con nicho, formato y frecuencia.
2. Estratega genera `ContentPlan` con N episodios futuros.
3. Scheduler revisa el plan periódicamente.
4. Cuando toca generar, CrewAI ejecuta tareas y entrega guion.
5. Guion se convierte en episodio y se encola para audio.
6. Worker genera audio.
7. Episodio pasa a `ready_for_review`.

### Límites y seguridad
- Máximo episodios por día/semana configurables.
- Máximo tokens por día.
- Cooldown entre generaciones de CrewAI.
- Modo automático requiere aprobación del plan antes de activarse.
- El estratega propone, no ejecuta directamente.

## 12. Audiolibros

**Flujo**
1. Usuario sube archivo (PDF/EPUB/TXT) o elige fuente Gutenberg/URL.
2. Sistema extrae texto y detecta/divide capítulos.
3. Usuario elige voz narradora y voces para personajes.
4. CrewAI opcionalmente adapta diálogos.
5. Se encola generación capítulo por capítulo.
6. Worker genera audios en paralelo limitado por VRAM.
7. Se ensambla audiolibro completo con metadatos.

**Límites**
- Máximo capítulos por lote.
- Opción de generar rango de capítulos.
- Pausar/reanudar generación.

## 13. Sound Gallery

Biblioteca de sonidos clasificados.

**Categorías**
- `ambience`: naturaleza, ciudad, oficina, etc.
- `music`: lo-fi, épica, relajante, suspense.
- `effects`: transiciones, impactos.
- `branding`: intros, outros.

**Funcionalidades**
- Galería con filtros y búsqueda.
- Preview.
- Subida de sonidos con validación de formato.
- Asignación a canales (intro/outro/background).
- Identificación por hash para evitar duplicados.
- Versionado de archivos.

## 14. Audio Engineer Agent y post-procesamiento

**Audio Engineer Agent**
- Selecciona sonidos de fondo según mood.
- Decide momentos de música y transiciones.
- Planifica mezcla final.

**Pipeline de post-procesamiento**
| Etapa | Output |
|-------|--------|
| Generación TTS | `audio_raw.wav` |
| Limpieza | `audio_clean.wav` |
| Mezcla | `audio_mixed.wav` |
| Mejora de resolución | `audio_enhanced.wav` |
| Mastering | `audio_mastered.wav` |
| Exportación | `final.mp3` |

**Buenas prácticas**
- Guardar stems temporalmente (24-48h por defecto).
- Opción "mantener stems" por episodio.
- Metadatos ID3 en MP3 final.
- Loudness objetivo: -16 LUFS (podcast), -14 LUFS (música).
- Sample rate 44.1 kHz, bitrate 192 kbps.
- Logs de cada etapa en `output/<episode_id>/log.json`.

## 15. Ollama integration

Ollama es el LLM por defecto para todos los agentes CrewAI.

**Modelos recomendados por tarea**
| Tarea | Modelo |
|-------|--------|
| Estratega/Planner | `llama3.1:8b` o `qwen2.5:7b` |
| Investigador/Curador | `phi4` o `llama3.2:3b` |
| Guionista | `llama3.1:8b` o `mistral:7b` |
| Editor | `qwen2.5:7b` |
| Revisor | `llama3.2:3b` |
| Audio Engineer | `llama3.2:3b` |

**Configuración**
```yaml
llm:
  provider: ollama
  base_url: http://localhost:11434
  default_model: llama3.1:8b
  fallback_provider: openrouter  # opcional
  models:
    strategist: llama3.1:8b
    researcher: phi4
    writer: llama3.1:8b
    editor: qwen2.5:7b
    reviewer: llama3.2:3b
    audio_engineer: llama3.2:3b
```

**Optimizaciones**
- Caché local de respuestas por prompt+modelo (TTL 24h).
- `starter.py` verifica que Ollama esté corriendo y descarga modelos faltantes.
- Fallback opcional a API de pago si Ollama no responde.

## 16. Flujos de datos

### Generación manual de episodio
```
Usuario en /create
  → POST /api/episodes
  → API inserta en SQLite (pending)
  → Worker toma el job
  → Ejecuta PipelineOrchestrator/DramaMixer
  → Post-procesa y exporta MP3
  → Actualiza SQLite (ready_for_review)
  → Frontend recibe evento SSE
```

### Generación automática con CrewAI
```
Canal activo + plan aprobado
  → Scheduler ejecuta entrada del plan
  → CrewAI genera guion
  → POST /api/episodes con guion
  → Worker genera audio
  → Ready for review
```

### Preview de voz
```
Usuario en /voices
  → POST /api/tts/preview
  → API genera audio corto (Edge-TTS por defecto)
  → Guarda en output/previews/
  → Devuelve URL
```

### Clonación de voz
```
Usuario sube muestra
  → POST /api/voices/:id/clone
  → API valida y entrena perfil
  → Guarda en voices/clones/
  → Estado ready
```

## 17. Manejo de errores

- Worker guarda estado `failed` con mensaje de error.
- Frontend muestra errores y permite reintentar.
- Fallback automático de motor TTS a Edge-TTS.
- Validaciones de archivos y tamaños.
- Si API/Worker cae, frontend muestra "servicio no disponible".
- Reintentos exponenciales en llamadas a Ollama.

## 18. Testing

**Backend**
- Tests de endpoints con `TestClient`.
- Tests de creación y actualización de episodios.
- Test de preview con Edge-TTS.
- Test de worker con job simulado.

**Frontend**
- Renderizado de componentes con React Testing Library.
- Tests de navegación entre rutas.
- Tests de stores Zustand.

**Integración**
- Test de generación de preview real.
- Test de `starter.py` levantando y deteniendo servicios.

## 19. Cuellos de botella corregidos

| Problema original | Corrección |
|-------------------|-----------|
| JSON compartido con race conditions | SQLite transaccional |
| Worker único bloqueado por audiolibros largos | Paralelización de capítulos limitada por VRAM |
| Polling constante del frontend | Server-Sent Events (SSE) |
| CrewAI sin límites | Límites de episodios/tokens, aprobación de plan |
| Stems llenando disco | Retención temporal por defecto |
| Fallo de motor bloquea episodio | Fallback automático a Edge-TTS |
| Estratega con poder absoluto | Propone plan, scheduler y worker ejecutan |
| Duplicados en Sound Gallery | Hash de archivo + versionado |
| Audiolibros sin control | Lotes, rangos, pausa/reanudación |
| Publicación sin control de calidad | Estado `ready_for_review` obligatorio |
| Costo de tokens de LLM | Ollama local por defecto + caché |

## 20. Plan de implementación sugerido (MVP)

### Fase 1: Infraestructura base
- Crear `web/`, `web_api/`, `worker/`.
- Configurar Vite + React + Tailwind + TanStack Router + Zustand.
- Configurar FastAPI, SQLite, CORS.
- Crear `starter.py`.

### Fase 2: Voces y preview
- Voice Lab: listar, probar, crear perfiles.
- Endpoint `/api/tts/preview`.
- Integrar motores TTS existentes.

### Fase 3: Episodios y cola
- CRUD de episodios.
- Worker básico con SQLite.
- Pantalla `/queue` con SSE.
- Post-procesamiento básico.

### Fase 4: Canales y CrewAI
- Canales y plan editorial.
- Integrar CrewAI + Ollama.
- CrewAI Studio.

### Fase 5: Audiolibros y Sound Gallery
- Procesamiento de libros.
- Galería de sonidos.
- Audio Engineer Agent.

### Fase 6: Pulido
- Testing.
- Limpieza automática.
- Optimizaciones de VRAM.

---

*Diseño aprobado para su implementación.*
