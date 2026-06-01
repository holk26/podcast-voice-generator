# 🎙️ Podcast Voice Generator

Aplicación de escritorio en Python con PyQt6 para generar podcasts con voz sintética de alta calidad usando GPU NVIDIA. Soporta múltiples motores TTS (Text-to-Speech), clonación de voz y procesamiento de audio profesional.

## ✨ Características

- **🖥️ Interfaz Gráfica Intuitiva**: Construida con PyQt6, diseño moderno y responsivo
- **🔊 Múltiples Motores TTS**:
  - **XTTS v2** (Coqui) - Clonación de voz con solo 6 segundos de audio de referencia
  - **Bark** (Suno) - Generación de voz expresiva y natural
  - **Edge-TTS** - Síntesis rápida en la nube (sin requisitos de GPU)
- **🎭 Clonación de Voz**: Clona cualquier voz a partir de un archivo de audio de referencia
- **⚡ Aceleración GPU**: Soporte completo para NVIDIA CUDA con gestión inteligente de VRAM
- **🎚️ Procesamiento de Audio**: Mezcla, normalización, efectos y exportación profesional
- **📁 Gestión de Proyectos**: Guarda y organiza tus proyectos de podcast
- **🌍 Multi-idioma**: Soporte para 16 idiomas (español, inglés, francés, alemán, etc.)

## 🚀 Instalación

### Requisitos

- Python 3.11+
- NVIDIA GPU con CUDA (opcional pero recomendado)
- 8GB+ RAM (16GB recomendado)
- ~5GB espacio libre para modelos

### Paso 1: Clonar el repositorio

```bash
git clone <repo-url>
cd podcast-voice-generator
```

### Paso 2: Crear entorno virtual

```bash
python3.11 -m venv venv311
source venv311/bin/activate  # Linux/Mac
# venv311\Scripts\activate  # Windows
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

> **Nota para RTX 50-series (5060/5070/5080/5090)**: PyTorch 2.6 no es compatible con la arquitectura sm_120 (Blackwell). La aplicación detectará automáticamente esto y usará CPU fallback para XTTS/Bark. Para usar GPU, instala PyTorch 2.7+ o 2.12+ con CUDA 12.8+:
> ```bash
> pip install torch==2.12.0 torchaudio --index-url https://download.pytorch.org/whl/cu118
> ```

### Paso 4: Configurar HuggingFace (para Bark)

Si planeas usar el motor Bark, configura tu token de HuggingFace para evitar rate limiting:

```bash
# Obtén tu token en https://huggingface.co/settings/tokens
huggingface-cli login
# o
export HF_TOKEN="tu_token_aqui"
```

### Paso 5: Ejecutar la aplicación

```bash
python main.py
```

## 📖 Uso

### Generar un Podcast

1. Abre la aplicación con `python main.py`
2. Crea un nuevo proyecto o abre uno existente
3. Escribe o importa tu guion en el editor de texto
4. Selecciona la voz y el motor TTS deseado
5. Haz clic en **Generar Audio**
6. El archivo resultante se guardará en la carpeta `output/`

### Clonar una Voz

1. Ve al panel **Voces** → **Clonar Voz**
2. Selecciona un archivo de audio de referencia (mínimo 6 segundos, voz clara)
3. Dale un nombre a la voz clonada
4. Usa la voz clonada en cualquier proyecto

### Configuración de GPU

Edita `config.yaml` para ajustar:

```yaml
gpu:
  device: "auto"          # auto, cpu, cuda:0, cuda:1...
  use_fp16: true          # Media precisión para ahorrar VRAM
  max_vram_gb: 22         # Límite de VRAM a usar
  keep_model_loaded: true # Mantener modelo en memoria
```

## 🏗️ Arquitectura

```
podcast-voice-generator/
├── main.py                  # Punto de entrada
├── config.yaml              # Configuración global
├── requirements.txt         # Dependencias
├── core/                    # Lógica de negocio
│   ├── project.py           # Modelos de datos
│   ├── xtts_engine.py       # Motor XTTS v2
│   ├── bark_engine.py       # Motor Bark
│   ├── batch_generator.py   # Generación por lotes
│   └── audio_pipeline.py    # Pipeline de audio
├── gui/                     # Interfaz gráfica
│   ├── main_window.py       # Ventana principal
│   ├── generation_panel.py  # Panel de generación
│   ├── voice_manager.py     # Gestor de voces
│   └── script_editor.py     # Editor de guiones
├── audio/                   # Procesamiento de audio
│   ├── mixer.py             # Mezclador
│   ├── effects.py           # Efectos
│   ├── normalizer.py        # Normalización
│   └── exporter.py          # Exportación
├── utils/                   # Utilidades
│   ├── gpu_utils.py         # Gestión de GPU
│   ├── config_manager.py    # Configuración
│   └── file_utils.py        # Archivos
├── tests/                   # Tests unitarios
├── voices/                  # Voces almacenadas
├── output/                  # Archivos generados
└── projects/                # Proyectos guardados
```

## 🧪 Tests

```bash
pytest tests/ -v
```

34 tests unitarios cubriendo:
- Motores TTS (XTTS, Bark)
- Pipeline de audio
- Gestión de GPU/VRAM
- Utilidades y configuración

## 🖥️ Compatibilidad de GPU

| GPU | Arquitectura | CUDA | PyTorch Recomendado | Estado |
|-----|-------------|------|-------------------|--------|
| RTX 3060-4090 | Ampere/Ada | sm_86/sm_89 | 2.6.0+cu124 | ✅ GPU |
| RTX 5060-5090 | Blackwell | sm_120 | 2.12.0+cu130 | ⚠️ CPU fallback* |
| GTX 1060-1080 | Pascal | sm_61 | 2.6.0+cu124 | ✅ GPU |
| Sin GPU | - | - | Cualquiera | ✅ CPU |

\* La aplicación detecta automáticamente GPUs no compatibles y usa CPU fallback para estabilidad.

## 📝 Notas sobre Modelos

### XTTS v2
- **Tamaño**: ~1.9GB
- **Descarga automática** en primer uso
- **Licencia**: CPML (Coqui Public Model License)
- **Requiere aceptación** de términos en primer uso

### Bark
- **Tamaño**: ~1.5GB (small) / ~3.9GB (large)
- **Descarga automática** vía HuggingFace (requiere `HF_TOKEN` para evitar rate limiting)
- **Modelos**: `suno/bark-small`, `suno/bark-large`
- **Nota**: Sin token, HuggingFace puede aplicar rate limiting tras múltiples descargas

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commitea tus cambios
4. Abre un Pull Request

## 📄 Licencia

MIT License - ver archivo LICENSE para detalles.

Los modelos XTTS v2 y Bark tienen sus propias licencias (CPML y MIT respectivamente).

## 🙏 Agradecimientos

- [Coqui AI](https://github.com/coqui-ai/TTS) - XTTS v2
- [Suno AI](https://github.com/suno-ai/bark) - Bark
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - Framework GUI
- [PyTorch](https://pytorch.org/) - Framework ML
