# Podcast Voice Generator — Manual de Uso

Plataforma automatizada de producción de podcasts con inteligencia artificial. Convierte contenido (RSS, libros, texto) en episodios completos con múltiples voces, efectos, música y publicación.

---

## Índice

1. [Arquitectura General](#1-arquitectura-general)
2. [Requisitos del Sistema](#2-requisitos-del-sistema)
3. [Instalación](#3-instalación)
4. [Configuración](#4-configuración)
5. [Interfaz Gráfica (GUI)](#5-interfaz-gráfica-gui)
6. [Pipeline Completo de Producción](#6-pipeline-completo-de-producción)
7. [Modos de Entrada de Contenido](#7-modos-de-entrada-de-contenido)
8. [Sistema de Voces y Casting](#8-sistema-de-voces-y-casting)
9. [Motor de Audio y Mejora con VoiceFixer](#9-motor-de-audio-y-mejora-con-voicefixer)
10. [Branding (Intro/Outro)](#10-branding-introoutro)
11. [Efectos de Sonido](#11-efectos-de-sonido)
12. [Cola de Episodios y Revisión](#12-cola-de-episodios-y-revisión)
13. [Publicación y RSS](#13-publicación-y-rss)
14. [Programación y Automatización](#14-programación-y-automatización)
15. [API de Plataforma (Uso por Código)](#15-api-de-plataforma-uso-por-código)
16. [Scripts de Demostración](#16-scripts-de-demostración)
17. [Tests](#17-tests)
18. [Solución de Problemas](#18-solución-de-problemas)

---

## 1. Arquitectura General

```
                    ┌──────────────┐
                    │   GUI (PyQt6) │
                    └──────┬───────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│              MediaAutomationPlatform                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Queue   │  │  Pipeline    │  │  ReviewTool   │  │
│  │  Service  │──│ Orchestrator │──│               │  │
│  └──────────┘  └──────┬───────┘  └───────┬───────┘  │
│                        │                  │          │
│  ┌──────────┐  ┌──────▼───────┐  ┌──────▼───────┐  │
│  │Scheduler │  │  Publishers  │  │ AutoPublisher│  │
│  └──────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌──────────┐        ┌──────────┐           ┌──────────┐
│Content   │        │  Agents  │           │  Audio   │
│Fetchers  │        │  (LLM)   │           │ Pipeline │
│- RSS     │        │- Cleaner │           │- XTTS    │
│- Gutenberg│       │- Writer  │           │- Edge-TTS│
│- Templates│       │- Editor  │           │- Bark    │
└──────────┘        │- Caster  │           │- Zonos   │
                    │- Metadata│           │- DramaMix│
                    └──────────┘           │- VoiceFix│
                                           │- SFX     │
                                           │- Branding│
                                           └──────────┘
```

### Componentes Principales

| Componente | Descripción |
|---|---|
| **GUI (PyQt6)** | Interfaz gráfica con pestañas: Proyecto, Guion, Voces, Generar, Reproductor |
| **MediaAutomationPlatform** | Punto de entrada unificado que orquesta cola, pipeline, revisión, publicación y scheduler |
| **PipelineOrchestrator** | Ejecuta 6 etapas secuenciales para producir un episodio |
| **AgentOrchestrator** | Coordina 5 agentes LLM para generar guion, casting y metadatos |
| **DramaMixer** | Sintetiza cada línea del guion con la voz asignada y mezcla el audio final |
| **VoiceFixerEnhancer** | Mejora la calidad del audio (24kHz → 44.1kHz) mediante IA |
| **EpisodeQueue** | Cola persistente de episodios con estados: pending → rendering → review → approved → published |
| **ReviewTool** | Herramienta de revisión y aprobación manual |
| **Publishers** | FilePublisher (copia local) + RSSPublisher (genera feed RSS 2.0) |
| **EpisodeScheduler** | Programación CRON recurrente de episodios |

---

## 2. Requisitos del Sistema

### Hardware
- **GPU**: NVIDIA RTX 3060+ (recomendada RTX 4060+ con 12GB+ VRAM)
  - Compatible con RTX 5060 (sm_120) con PyTorch 2.11+
  - VoiceFixer requiere ~4GB VRAM adicionales
- **RAM**: 16GB+ (32GB recomendado)
- **Disco**: 20GB+ para modelos y proyectos

### Software
- **Sistema**: Linux (probado en Fedora/Ubuntu/Debian)
- **Python**: 3.11
- **CUDA**: 12.4+ (para PyTorch con GPU)
- **FFmpeg**: 7.1+ (para reproducción de audio en Qt multimedia)

---

## 3. Instalación

```bash
# 1. Crear entorno virtual
python3.11 -m venv venv311
source venv311/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno (al menos una para los agentes LLM)
export OPENAI_API_KEY="sk-..."       # OpenAI o compatible (Groq, Together)
# export ANTHROPIC_API_KEY="sk-..."  # Alternativa: Claude
# export LLM_PROVIDER="ollama"       # Alternativa: modelo local

# 4. Ejecutar
python main.py                       # GUI
```

### Dependencias (`requirements.txt`)
```
PyQt6>=6.5.0      # Interfaz gráfica
TTS>=0.22.0       # XTTS v2 (clonación de voz local)
torch>=2.0.0      # PyTorch (GPU)
torchaudio>=2.0.0 # Audio para PyTorch
pydub>=0.25.1     # Manipulación de audio
soundfile>=0.12.1 # Lectura/escritura de WAV
pynvml>=11.5.0    # Monitoreo de VRAM
pytest>=7.4.0     # Tests
pyyaml>=6.0       # Configuración
```

---

## 4. Configuración

`config.yaml` — archivo central de configuración:

```yaml
app:
  name: "Podcast Voice Generator"
  version: "1.0.0"

gpu:
  device: "auto"          # "auto", "cuda:0", "cpu"
  use_fp16: true          # Mitad de precisión (ahorra VRAM)
  max_vram_gb: 22         # Límite de VRAM a usar
  keep_model_loaded: true # Mantener modelo en GPU entre usos

xtts:
  model: "tts_models/multilingual/multi-dataset/xtts_v2"
  gpu_layers: "all"       # Capas del modelo en GPU
  languages:
    - "es"  # Español
    - "en"  # Inglés
    - "fr"  # Francés
    # ... 17 idiomas en total

bark:
  enabled: true           # Usar Bark como respaldo
  model_size: "large"     # "small", "large"
  fallback_if_oom: "xtts" # Si Bark se queda sin VRAM, usar XTTS

paths:
  voices_dir: "voices"
  clones_dir: "voices/clones"
  output_dir: "output"
  projects_dir: "projects"
  music_dir: "music"

audio:
  default_format: "mp3"      # "mp3", "wav", "flac"
  default_sample_rate: 24000 # 24000, 44100, 48000
  default_bitrate: "192k"
  normalize_default: true
```

---

## 5. Interfaz Gráfica (GUI)

Ejecutar con `python main.py`. Se abren 5 pestañas:

### 5.1 Proyecto
- Crear, abrir y gestionar proyectos
- Cada proyecto contiene secciones, voces asignadas y configuración

### 5.2 Guion
- Editor de texto tipo screenplay
- Formato: `PERSONAJE: texto del diálogo`
- Asignación de voces a personajes

### 5.3 Voces
- Gestión de perfiles de voz
- Clonación de voz (grabar o importar audio)
- Cada perfil incluye: voice_id, motor TTS, idioma, velocidad, speaker_id, ruta de referencia

### 5.4 Generar
- Generación por lotes con barra de progreso
- Selección de formato de salida
- Monitor de VRAM en tiempo real

### 5.5 Reproductor
- Reproducción de audio generado
- Controles: play, pausa, stop, volumen

---

## 6. Pipeline Completo de Producción

El `PipelineOrchestrator` ejecuta **6 etapas** en secuencia:

```
EpisodeConfig
    │
    ▼
┌─────────────────────────────────────────────┐
│ ETAPA 1: Adquisición de Contenido           │
│                                             │
│  news  ──► RSSFetcher.fetch()               │
│  book  ──► GutenbergFetcher.download_book() │
│  meditation ──► TemplateEngine              │
│  motivation ──► TemplateEngine              │
│  raw   ──► contenido inline                 │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ ETAPA 2: Procesamiento con Agentes LLM      │
│                                             │
│  1. ContentCleanerAgent                     │
│     - Limpia HTML, extrae título/resumen    │
│  2. ScriptWriterAgent                       │
│     - Escribe guion formato CHAR: texto     │
│  3. ScriptEditorAgent (iterativo)           │
│     - Revisa y mejora hasta calidad ≥7/10   │
│  4. CharacterCasterAgent                    │
│     - Asigna voces a personajes             │
│  5. MetadataAgent                           │
│     - SEO title, descripción, tags          │
│                                             │
│  Salida: MediaPackage (script.json +        │
│           manifest.yaml)                    │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ ETAPA 3: Guardar Skeleton                   │
│  - Crea carpeta assets/                     │
│  - Guarda script.json y manifest.yaml       │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ ETAPA 4: Renderizado de Audio               │
│                                             │
│  DramaMixer.mix_package():                  │
│  1. Para cada línea del guion:              │
│     a. Resolver voz (VoiceCastManager)      │
│     b. Obtener motor TTS (XTTS/Edge/Bark)   │
│     c. Sintetizar línea a WAV               │
│     d. VoiceFixer (por línea, si se activa) │
│     e. Añadir silencios pre/post            │
│  2. Concatenar todas las líneas             │
│  3. Normalizar y aplicar fades             │
│  4. VoiceFixer (final, si se activa)        │
│  5. Exportar a main_mix.mp3                 │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ ETAPA 5: Branding (Intro/Outro)             │
│                                             │
│  BrandingEngine.apply_to_package():         │
│  1. Generar intro (música + voz del host)   │
│  2. Generar outro                           │
│  3. Concatenar intro + main + outro         │
│  4. Exportar como final.mp3                 │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ ETAPA 6: Actualizar Manifest                │
│  - Lee duración final con pydub             │
│  - Guarda episode_number, season_number     │
│  - Fecha de publicación                     │
└─────────────────────────────────────────────┘
```

---

## 7. Modos de Entrada de Contenido

El sistema soporta **5 tipos de episodio**:

### 7.1 News (Noticias)
- **Entrada**: URL de feed RSS
- **Procesador**: `NewsProcessor` → fusiona artículos → `AgentOrchestrator`
- **Uso**:
  ```python
  EpisodeConfig(
      episode_type="news",
      title="Noticias Tech",
      sources=[{"url": "https://example.com/rss"}]
  )
  ```

### 7.2 Book (Libros)
- **Entrada**: Título de búsqueda en Project Gutenberg
- **Procesador**: `GutenbergFetcher` → `BookProcessor` (divide en capítulos) → `AgentOrchestrator` por capítulo
- **Uso**:
  ```python
  EpisodeConfig(
      episode_type="book",
      title="Don Quijote",
      sources=[{"gutenberg_search": "Don Quijote"}]
  )
  ```

### 7.3 Meditation (Meditación)
- **Entrada**: Tema y duración
- **Procesador**: `TemplateEngine` genera guion guiado con instrucciones de respiración
- **Uso**:
  ```python
  EpisodeConfig(
      episode_type="meditation",
      title="Meditación Matutina",
      target_duration_minutes=15
  )
  ```

### 7.4 Motivation (Motivación)
- **Entrada**: Tema y duración
- **Procesador**: `TemplateEngine` genera discurso motivacional con citas
- **Uso**:
  ```python
  EpisodeConfig(
      episode_type="motivation",
      title="Motivación Diaria"
  )
  ```

### 7.5 Raw (Texto Crudo)
- **Entrada**: Texto directo
- **Procesador**: `AgentOrchestrator.run()` directo
- **Uso**:
  ```python
  EpisodeConfig(
      episode_type="raw",
      sources=[{"content": "Texto del episodio..."}]
  )
  ```

---

## 8. Sistema de Voces y Casting

### Motores TTS Disponibles

| Motor | Calidad | GPU | Clonación | Idiomas |
|---|---|---|---|---|
| **XTTS v2** | ★★★★ | Sí | Sí (17 idiomas) | 17 |
| **Edge-TTS** | ★★★★★ | No | No (voces Azure) | 15 voces español |
| **Bark** | ★★★ | Sí | No | 10 voces español |
| **Zonos** | ★★★★ | Sí | Sí (Mamba) | En desarrollo |

### VoiceCastManager

- Perfiles de voz en `cast/voice_profiles/` (YAML)
- Mapa personaje→voz en `cast/character_voice_map.json`
- `resolve_voice_for_line(character, fallback)`:
  1. Busca en mapa de personajes
  2. Busca por voice_id
  3. Usa fallback

### Clonación de Voz (XTTS)

1. Grabar o importar audio de referencia (mínimo 10s, ideal 30-60s)
2. El perfil se guarda en `voices/clones/`
3. XTTS genera nuevas líneas con esa voz

---

## 9. Motor de Audio y VoiceFixer

### DramaMixer
- Procesa cada línea del guion secuencialmente
- Elige el motor TTS adecuado según el perfil de voz
- Añade silencios entre líneas
- Normaliza volumen final

### VoiceFixerEnhancer
Restauración de voz mediante IA (2 etapas: análisis + vocoder neural).

**Modos**:
- `mode=0`: Original (recomendado)
- `mode=1`: Pre-procesamiento (elimina frecuencias altas)
- `mode=2`: Entrenamiento (mejor para audio muy degradado)

**Configuración en pipeline**:
```python
audio_enhancer: "none"            # Sin mejora
audio_enhancer: "voicefixer"      # Solo al final
audio_enhancer: "voicefixer_line" # Por línea
audio_enhancer: "voicefixer_final"# Solo al final
audio_enhancer: "voicefixer_both" # Por línea + final
```

**Resultado**: 24kHz → 44.1kHz (1.84x sample rate), reconstrucción de frecuencias altas.

### SFX Engine
- Biblioteca de efectos categorizados (ambientes, golpes, música)
- `AutoAmbience`: sugiere efectos basados en el texto del guion
- `SFXMixer`: superpone ambientes, música de fondo y golpes

---

## 10. Branding (Intro/Outro)

`BrandingEngine` genera intros y outros personalizados:

1. Renderiza template Jinja2 (`templates/branding/`)
2. Sintetiza voz del host con XTTS
3. Carga música de fondo desde `music/`
4. Mezcla voz + música
5. Concatena intro + audio principal + outro
6. Exporta como `final.mp3`

Se controla con `branding_enabled: true/false` en `EpisodeConfig`.

---

## 11. Efectos de Sonido

### SFXLibrary
- Categorías: ambience, impacts, music, foley
- Búsqueda por palabra clave
- Volumen configurable por efecto

### AutoAmbience
- Analiza el texto de cada escena
- Sugiere efectos relevantes (ej. "lluvia" → sonido de lluvia)
- Se integra en el guion mediante `sfx_cue` en `ScriptLine`

---

## 12. Cola de Episodios y Revisión

### Ciclo de Vida de un Episodio

```
pending ──► rendering ──► review ──► approved ──► published
                              │
                              └──► rejected
```

### EpisodeQueue
- Cola persistente en JSON (`data/episode_queue.json`)
- Prioridad (mayor número = mayor prioridad)
- `enqueue(config, priority)` → agrega a cola
- `get_next_pending()` → obtiene el siguiente
- `update_status(episode_id, status)` → cambia estado

### ReviewTool
- `preview_audio(episode_id)` → escuchar audio
- `get_package(episode_id)` → ver metadatos
- `approve()` → aprueba (va a "approved")
- `reject(reason)` → rechaza (va a "rejected")
- `request_revision(notes)` → solicita revisión
- `edit_metadata()` → editar campos del manifest
- `get_stats()` → estadísticas del dashboard

---

## 13. Publicación y RSS

### FilePublisher
- Copia el audio final a directorios organizados por fecha
- `output/published/YYYY/MM/DD/titulo_sanitizado.mp3`

### RSSPublisher
- Genera feed RSS 2.0 con extensiones iTunes
- Configuración:
  ```python
  RSSPublisher(
      title="Mi Podcast",
      description="Descripción",
      author="Autor",
      language="es",
      web_dir="output/web",
      site_url="https://example.com",
      image_url="https://example.com/cover.jpg"
  )
  ```
- Soporta: iTunes categories, explicit flag, duration, enclosure, pubDate

---

## 14. Programación y Automatización

### EpisodeScheduler
- Programación CRON-like
- Recurrencia: `"daily"`, `"weekly"`, `"none"`
- `schedule(config, when, recurrence)` → programa
- `tick()` → verifica tareas vencidas y las encola
- Persistencia en `data/schedule.json`

### AutoPublisher
- `run()` → publica todos los episodios aprobados
- `run_single(episode_id)` → publica uno específico

### Ciclo de Automatización (tick)
```python
platform.tick()  # Hace en un solo llamado:
# 1. Verifica schedule → encola episodios vencidos
# 2. Corre el próximo pending
# 3. Auto-publica episodios approved
```

---

## 15. API de Plataforma (Uso por Código)

```python
from core.platform import MediaAutomationPlatform

platform = MediaAutomationPlatform()

# 1. Enviar episodio
config = EpisodeConfig(
    episode_type="news",
    title="Noticias de Tecnología",
    sources=[{"url": "https://example.com/rss"}],
    voice_cast_path="cast/voice_profiles/mis_voces.yaml",
    host_voice_id="mi_voz_host",
    branding_enabled=True,
    audio_enhancer="voicefixer_final"
)
episode_id = platform.submit(config)

# 2. Ejecutar pipeline completo
platform.run_pipeline(episode_id)

# 3. Revisar
platform.approve(episode_id)

# 4. Publicar
platform.publish(episode_id)

# 5. Automatización
platform.schedule(config, when="2026-06-10T08:00:00", recurrence="daily")
platform.tick()  # Ciclo completo
```

### Métodos Principales

| Método | Descripción |
|---|---|
| `submit(EpisodeConfig)` | Encola un episodio |
| `submit_raw(title, content, ...)` | Encola texto directo |
| `run_pipeline(episode_id)` | Ejecuta pipeline completo |
| `run_next_pending()` | Automático: corre el próximo |
| `approve(episode_id)` | Aprueba episodio |
| `reject(episode_id, reason)` | Rechaza con motivo |
| `request_revision(episode_id, notes)` | Solicita cambios |
| `edit_metadata(episode_id, updates)` | Edita metadatos |
| `publish(episode_id)` | Publica episodio |
| `auto_publish()` | Publica todos los aprobados |
| `schedule(config, when, recurrence)` | Programa episodio |
| `cancel_schedule(schedule_id)` | Cancela programación |
| `tick()` | Ciclo completo de automatización |
| `get_dashboard()` | Estadísticas generales |

---

## 16. Scripts de Demostración

| Script | Comando | Qué demuestra |
|---|---|---|
| Fase 1 - Media Package | `python scripts/demo_fase1_media_package.py` | Creación manual de MediaPackage + Edge-TTS |
| Fase 2 - Drama Mixer | `python scripts/demo_fase2_drama_mixer.py` | Multi-voice mixing con DramaMixer |
| Fase 4 - News Pipeline | `python scripts/demo_fase4_news_pipeline.py` | RSS → agentes → audio → branding |
| Fase 5 - Pipeline | `python scripts/demo_fase5_pipeline.py` | PipelineOrchestrator end-to-end |
| Fase 6 - Queue/Review | `python scripts/demo_fase6_queue_review.py` | Cola + revisión (enqueue → render → review) |
| Fase 7 - Publish/Schedule | `python scripts/demo_fase7_publish_schedule.py` | FilePublisher + RSSPublisher + Scheduler |
| Fase 8 - Platform | `python scripts/demo_fase8_platform.py` | Plataforma completa (submit → pipeline → review → publish → schedule → tick) |
| VoiceFixer | `python scripts/demo_voicefixer_enhancer.py` | Mejora de audio con VoiceFixer |
| Generar episodios Homer | `python scripts/generate_homer_real_episodes.py` | Podcast real con voz clonada de Homero |
| SFX Library | `python scripts/generate_sfx_library.py` | Generación de biblioteca de efectos |

```bash
# Ejecutar demo completa de la plataforma
cd /ruta/del/proyecto
source venv311/bin/activate
python scripts/demo_fase8_platform.py
```

---

## 17. Tests

```bash
# Ejecutar todos los tests
source venv311/bin/activate
pytest tests/ -v

# Tests específicos
pytest tests/test_platform.py -v
pytest tests/test_pipeline_orchestrator.py -v
pytest tests/test_audio_enhancer.py -v
pytest tests/test_agents.py -v

# Tests con cobertura
pytest tests/ --cov=. --cov-report=term
```

30 archivos de test que cubren todos los componentes:

| Test | Componentes |
|---|---|
| `test_agents.py` | 5 agentes LLM + AgentOrchestrator |
| `test_pipeline_orchestrator.py` | Pipeline completo con todos los tipos |
| `test_platform.py` | Plataforma: submit, run, review, publish, schedule, tick |
| `test_episode_queue.py` | Cola: CRUD, prioridad, estados, persistencia |
| `test_review_tool.py` | Revisión: preview, approve, reject, edit |
| `test_scheduler.py` | Schedule: CRUD, recurrencia, tick |
| `test_publishers.py` | FilePublisher, RSSPublisher, feed XML |
| `test_media_package.py` | Save/load, script, manifest, assets |
| `test_drama_mixer.py` | Single line, full package mixing |
| `test_branding_engine.py` | Intro/outro, branding de paquete |
| `test_audio_enhancer.py` | VoiceFixer enhancement |
| `test_sfx_engine.py` | Biblioteca, auto-ambience |
| `test_dialogue_parser.py` | 3 formatos de entrada |
| `test_content_acquisition.py` | RSS, Gutenberg, TemplateEngine |
| `test_integration.py` | Integración cross-componente |

---

## 18. Solución de Problemas

### GPU / VRAM

| Problema | Solución |
|---|---|
| `CUDA out of memory` | Reducir `max_vram_gb` en `config.yaml` |
| `RTX 5060 not detected` | Usar PyTorch 2.11+ (cu130). Ver `main.py` fix |
| `VoiceFixer: model corrupted` | Eliminar `~/.cache/voicefixer/` y re-ejecutar |
| `Bark OOM` | Activar `fallback_if_oom: xtts` en config |

### Agentes LLM

| Problema | Solución |
|---|---|
| `No LLM provider available` | Configurar `OPENAI_API_KEY` o `ANTHROPIC_API_KEY` |
| `Rate limit` | Usar `OllamaProvider` con modelo local |
| `MockProvider active` | Verificar que `OPENAI_API_KEY` esté configurada |

### Audio

| Problema | Solución |
|---|---|
| `No audio output` | Verificar `output_dir` y permisos de escritura |
| `Voice not found` | Revisar `voice_cast_path` y perfiles en `cast/voice_profiles/` |
| `TTS engine failed` | Verificar VRAM disponible, probar con Edge-TTS |
| `FFmpeg not found` | Instalar FFmpeg 7.1+: `sudo dnf install ffmpeg` |

### VoiceFixer

```bash
# Verificar estado de los modelos
python -c "
import torch
torch.load('~/.cache/voicefixer/analysis_module/checkpoints/vf.ckpt')
torch.load('~/.cache/voicefixer/synthesis_module/44100/model.ckpt-1490000_trimed.pt')
print('Modelos OK')
"

# Re-descargar modelos (si están corruptos)
rm -rf ~/.cache/voicefixer/
```

---

## Resumen del Flujo Completo

```
1. GUI o API
   │
2. EpisodeConfig (tipo, fuente, voces, config)
   │
3. MediaAutomationPlatform.submit() ──► Queue (pending)
   │
4. PipelineOrchestrator.run()
   ├── Stage 1: Adquirir contenido (RSS/Gutenberg/Template/raw)
   ├── Stage 2: Agentes LLM (clean → write → edit → cast → metadata)
   ├── Stage 3: Guardar skeleton
   ├── Stage 4: DramaMixer (TTS + VoiceFixer + SFX)
   ├── Stage 5: Branding (intro/outro)
   └── Stage 6: Actualizar manifest
   │
5. Queue → review (escuchar, aprobar/rechazar)
   │
6. Publish (FilePublisher + RSSPublisher)
   │
7. Schedule (si es recurrente)
   │
8. tick() → loop automático
```

---

*Documentación generada para Podcast Voice Generator v1.0.0*
