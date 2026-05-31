# Especificación de Diseño: Podcast Voice Generator

## Fecha
2026-05-31

## Estado
Aprobado por el usuario. Listo para implementación.

---

## 1. Resumen

Aplicación de escritorio en Python con interfaz gráfica (PyQt6) para automatizar la generación de audio con voz sintética usando toda la potencia de la GPU NVIDIA del usuario. El motor principal es XTTS v2 por su naturalidad y capacidad de clonación de voz; Bark se incluye como motor secundario para casos que requieran mayor expresividad dramática.

**Casos de uso principales:**
- Podcasts con host propio o voces pre-entrenadas
- Meditaciones guiadas con música de fondo
- Cuentos narrados con una o múltiples voces
- Cualquier contenido de audio largo generado por lotes

---

## 2. Arquitectura

### 2.1 Estructura de carpetas

```
podcast-voice-generator/
├── main.py                    # Punto de entrada
├── config.yaml                # Config global (modelos, rutas, GPU)
│
├── gui/                       # Capa de presentación (PyQt6)
│   ├── __init__.py
│   ├── main_window.py         # Ventana principal con menú, tabs
│   ├── project_panel.py       # Crear/abrir/guardar proyectos
│   ├── script_editor.py       # Editor de guion con soporte multi-sección
│   ├── voice_manager.py       # Selector de voz + clonación
│   ├── generation_panel.py    # Config de generación y barra de progreso
│   └── audio_player.py        # Reproductor integrado para preview
│
├── core/                      # Capa de negocio
│   ├── __init__.py
│   ├── tts_engine.py          # Interfaz abstracta: TTSBase
│   ├── xtts_engine.py         # Implementación XTTS v2
│   ├── bark_engine.py         # Implementación Bark (opcional)
│   ├── project.py             # Modelo de datos: Project, Section, Voice
│   ├── audio_pipeline.py      # Orquesta generación + post-procesado
│   └── batch_generator.py     # Generación por lotes con cola
│
├── audio/                     # Capa de procesamiento de audio
│   ├── __init__.py
│   ├── mixer.py               # Mezcla voz + música de fondo
│   ├── normalizer.py          # Normalización de volumen
│   ├── exporter.py            # Exporta a MP3/WAV/FLAC
│   └── effects.py             # Fade in/out, silencios
│
├── utils/                     # Capa de utilidades
│   ├── __init__.py
│   ├── gpu_utils.py           # Detección VRAM, selección GPU, optimización
│   ├── config_manager.py      # Lee/escribe config.yaml
│   └── file_utils.py          # Rutas, validaciones
│
└── tests/                     # Tests unitarios y de integración
    ├── __init__.py
    ├── test_gpu_utils.py
    ├── test_xtts_engine.py
    ├── test_project.py
    ├── test_audio_pipeline.py
    └── test_batch_generator.py
```

### 2.2 Principio de diseño

Cada capa solo conoce la que está debajo. La GUI no habla directamente con XTTS; habla con `core/audio_pipeline.py`, que a su vez usa los motores. Esto permite cambiar XTTS por otro modelo sin tocar la interfaz.

---

## 3. Flujo de Datos y Casos de Uso

### UC1: Crear un nuevo proyecto
1. Usuario abre la app → `gui/main_window.py` muestra ventana vacía
2. Clic en "Nuevo Proyecto" → `gui/project_panel.py` pide nombre y carpeta
3. Se crea un objeto `core/project.py::Project` con lista vacía de secciones
4. Se guarda en disco como `proyecto.json`

### UC2: Escribir guion y asignar voces
1. Usuario escribe en `gui/script_editor.py` (dividido en secciones)
2. Cada sección tiene: texto, voz asignada, velocidad, énfasis
3. Los datos fluyen: `gui/script_editor.py` → `core/project.py::Section` → se actualiza `proyecto.json`

### UC3: Clonar una voz
1. Usuario abre `gui/voice_manager.py` → pestaña "Clonar Voz"
2. Selecciona archivo WAV/MP3 de su voz (~10-30 segundos)
3. `core/xtts_engine.py` procesa el audio de referencia y crea un embedding
4. La voz clonada se guarda en `voices/clones/<nombre>/` y aparece en el selector

### UC4: Generar audio
1. Usuario configura en `gui/generation_panel.py`: formato, calidad, música de fondo
2. Clic en "Generar" → `core/batch_generator.py` crea una cola de tareas
3. Para cada sección:
   - `core/audio_pipeline.py` selecciona el motor (XTTS o Bark)
   - El motor genera el audio crudo (usa `utils/gpu_utils.py` para asignar VRAM)
   - `audio/mixer.py` añade música de fondo si está configurada
   - `audio/normalizer.py` ajusta niveles de volumen
   - `audio/exporter.py` guarda el archivo final
4. Barra de progreso en GUI se actualiza por cada sección completada
5. Al finalizar, `gui/audio_player.py` permite escuchar el resultado

### Diagrama de flujo

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   GUI       │────▶│   Core      │────▶│   TTS Engines   │
│  (PyQt6)    │◀────│  (Pipeline) │◀────│ (XTTS/Bark)     │
└─────────────┘     └──────┬──────┘     └─────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Audio     │
                    │  (Mix/Export)│
                    └─────────────┘
```

---

## 4. Gestión de GPU y Optimización

### 4.1 Detección de recursos

`utils/gpu_utils.py` monitorea el hardware:
- Al inicio: detecta GPUs NVIDIA, VRAM disponible, compute capability
- Antes de cada generación: calcula si el modelo cabe en VRAM con margen de seguridad
- Fallback automático: si la VRAM no alcanza para un modelo grande (ej. Bark), avisa y sugiere XTTS o CPU

### 4.2 Estrategias de optimización

| Estrategia | Descripción | Beneficio |
|------------|-------------|-----------|
| Batch size dinámico | Ajusta cuántas secciones genera en paralelo según VRAM libre | Sin OOM, máximo throughput |
| Mixed precision (FP16) | Usa half-precision en lugar de float32 | Doble de velocidad, mitad de VRAM |
| Modelo en memoria persistente | Carga XTTS una sola vez al abrir el proyecto | Sin recarga entre secciones |
| Generación por chunks | Divide guiones largos en fragmentos de ~400 tokens | Evita truncation, mejor calidad |
| Offloading inteligente | Mueve buffers intermedios a RAM cuando no se usan | Más VRAM disponible |

### 4.3 Configuración por motor (config.yaml)

```yaml
gpu:
  device: "cuda:0"           # o "auto"
  use_fp16: true
  max_vram_gb: 22            # límite con margen para el sistema
  keep_model_loaded: true    # no descargar entre generaciones

xtts:
  model: "tts_models/multilingual/multi-dataset/xtts_v2"
  gpu_layers: "all"

bark:
  enabled: true
  model_size: "large"        # small/medium/large
  fallback_if_oom: "xtts"    # si no hay VRAM, usa XTTS
```

### 4.4 Panel de generación

Muestra en tiempo real:
- Progreso por sección (X de Y)
- VRAM usada / total
- Tiempo estimado restante
- Temperatura GPU (opcional, vía NVML)

---

## 5. Modelo de Datos

Cada proyecto se guarda como `proyecto.json`:

```json
{
  "project": {
    "name": "Podcast Salud Mental #12",
    "created_at": "2026-05-31T10:30:00Z",
    "modified_at": "2026-05-31T14:20:00Z",
    "settings": {
      "output_format": "mp3",
      "sample_rate": 24000,
      "bitrate": "192k",
      "normalize_audio": true,
      "fade_in_ms": 500,
      "fade_out_ms": 1000
    }
  },
  "voices": [
    {
      "id": "voz_host",
      "name": "Host Principal",
      "type": "cloned",
      "engine": "xtts",
      "reference_path": "voices/clones/mi_voz.wav",
      "language": "es",
      "speed": 1.0
    },
    {
      "id": "voz_invitado",
      "name": "Invitado",
      "type": "pretrained",
      "engine": "xtts",
      "speaker_id": "Damien Black",
      "language": "es",
      "speed": 0.95
    }
  ],
  "sections": [
    {
      "id": "sec_001",
      "title": "Introducción",
      "text": "Bienvenidos a nuestro podcast de hoy...",
      "voice_id": "voz_host",
      "pause_after_ms": 2000,
      "music": {
        "track": "music/ambient_intro.mp3",
        "volume_db": -18,
        "fade_duration": 3.0
      }
    },
    {
      "id": "sec_002",
      "title": "Meditación Guiada",
      "text": "Cierra los ojos y respira profundamente...",
      "voice_id": "voz_host",
      "speed": 0.85,
      "pause_after_ms": 5000,
      "music": {
        "track": "music/nature_sounds.mp3",
        "volume_db": -22,
        "ducking": true
      }
    }
  ],
  "generation_state": {
    "status": "partial",
    "completed_sections": ["sec_001"],
    "output_files": {
      "sec_001": "output/Podcast_Salud_Mental_12/sec_001_introduccion.mp3"
    }
  }
}
```

### Características clave

- **Secciones numeradas:** reordenar, duplicar, eliminar sin romper referencias
- **Voces desacopladas:** cambiar la voz de una sección es solo cambiar `voice_id`
- **Estado de generación persistente:** si se interrumpe, se sabe qué ya está listo
- **Música por sección:** cada parte puede tener su propio fondo sonoro con volumen independiente

---

## 6. Manejo de Errores

| Escenario | Comportamiento |
|-----------|----------------|
| OOM (VRAM insuficiente) | Detecta antes de generar, sugiere reducir batch, usar FP16, o cambiar a CPU. Nunca crashea. |
| Archivo de referencia corrupto | Valida el audio al clonar. Si falla, muestra diálogo con recomendaciones de formato (WAV 22050Hz mono). |
| Modelo no descargado | Descarga automáticamente en primer uso con barra de progreso. Reintenta o permite cancelar. |
| Interrupción durante generación | Guarda estado parcial. Al reabrir, pregunta si continuar desde donde quedó. |
| Texto demasiado largo | Divide automáticamente en chunks coherentes. Avisa cuántos chunks generará. |

---

## 7. Testing

Tests modulares en `tests/`:

- `test_gpu_utils.py` — Simula GPUs con distinta VRAM
- `test_xtts_engine.py` — Mock del modelo, prueba pipeline
- `test_project.py` — Guardar/cargar proyectos, serialización
- `test_audio_pipeline.py` — Generación + mezcla + exportación
- `test_batch_generator.py` — Cola de tareas, orden, paralelismo

Ejecución: `python -m pytest tests/`

---

## 8. Dependencias principales

- `PyQt6` — interfaz gráfica
- `TTS` (Coqui) — motor XTTS v2
- `bark` — motor Bark (opcional)
- `torch` + `torchaudio` — backend de deep learning
- `pydub` — manipulación de audio
- `soundfile` — lectura/escritura de audio
- `pynvml` — monitoreo de GPU
- `pytest` — testing

---

## 9. Decisiones de diseño aprobadas

1. **Motor principal XTTS v2**, Bark como secundario
2. **Clonación de voz y voces pre-entrenadas** (ambas soportadas)
3. **GUI con PyQt6** (no Gradio/Streamlit)
4. **Arquitectura en 4 capas** (gui, core, audio, utils)
5. **Proyectos persistentes en JSON**
6. **Optimización agresiva de GPU** (FP16, batch dinámico, modelo persistente)
7. **Manejo de errores con recuperación** (OOM, interrupciones, archivos corruptos)
