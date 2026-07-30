# Qwen3-TTS Setup Guide

## Motor integrado: Qwen/Qwen3-TTS-12Hz-1.7B-Base

El proyecto soporta el modelo **Qwen3-TTS-12Hz-1.7B-Base** de Qwen para clonación de voz.
Añade como opción en la interfaz web junto al motor Higgs existente.

## Detalles del modelo

| Campo | Valor |
|-------|-------|
| Modelo HuggingFace | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` |
| Licencia | Apache 2.0 |
| Idiomas | zh, en, ja, ko, de, fr, ru, pt, es, it |
| VRAM | ~4 GB en bfloat16 (1.7B params) |
| Salida | 24 kHz mono WAV |
| Método de clonación | 3 s de audio de referencia |

## Instalación

### Desde requirements.txt

```bash
pip install -r requirements.txt   # ya incluye qwen-tts
```

### Alternativa con pip directamente

```bash
venv311/bin/pip install qwen-tts
```

### Dependencias opcionales recomendadas

```bash
venv311/bin/pip install flash-attn --no-build-isolation
```

FlashAttention 2 reduce el consumo de VRAM y acelera la inferencia. Se usa `sdpa` ( Atención escalada por defecto) si FlashAttention no está disponible.

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `QWEN3_TTS_MODEL` | `Qwen/Qwen3-TTS-12Hz-1.7B-Base` | Modelo a cargar |
| `QWEN3_TTS_DEVICE` | `cuda` | Dispositivo (`cuda`, `cpu`) |
| `QWEN3_TTS_DTYPE` | *(vacío)* | `bfloat16`, `float16` o `float32` |

Uso en Docker con `docker-compose.yml` de la app:

```bash
QWEN3_TTS_MODEL="Qwen/Qwen3-TTS-12Hz-1.7B-Base" \
QWEN3_TTS_DEVICE="cuda:0" \
QWEN3_TTS_DTYPE="bfloat16" \
python starter.py
```

## Cómo funciona en la interfaz web

Cuando el usuario clona una voz subiendo un archivo de audio y lo guarda en `voices/clones/<nombre>.wav`, el archivo se expone **dos veces** en el dropdown de la interfaz:

- `nombre` (motor **higgs**, opción existente, retrocompatible)
- `nombre (qwen3)` (motor **qwen3**, nuevo)

El motor se elige según el `engine` de la voz seleccionada.

## Uso directo (sin la interfaz)

```python
from core.qwen_tts_engine import Qwen3TTSEngine
from core.project import Voice

engine = Qwen3TTSEngine(device="cuda")
engine.load()

voice = Voice(
    id="qwen3_clone_mi_voz",
    name="Mi clon Qwen3",
    type="cloned",
    engine="qwen3",
    language="es",
    reference_path="voices/clones/mi_referencia.wav",
)

engine.synthesize(
    "Hola, esto es una prueba de clonación de voz con Qwen3-TTS.",
    voice,
    "output/qwen3_test.wav",
)
engine.unload()
```

## Solución de problemas

### `ImportError: qwen-tts not installed`

```bash
venv311/bin/pip install qwen-tts
```

### OOM (Out of Memory) en GPU de 8 GB

- Usa `QWEN3_TTS_DTYPE=float16` (reduce uso de VRAM a ~3 GB aprox).
- Cierra Ollama primero si compites por la misma GPU (ya se libera automáticamente en `load()`).

### `flash_attention_2` not available

El motor cae automáticamente a `sdpa` (PyTorch nativo). El rendimiento es ligeramente inferior pero funcional.

### Modelo lento al descargar la primera vez

La primera carga tarda 1-3 minutos (descarga de pesos desde HuggingFace). Los pesos se cachean en `~/.cache/huggingface/hub/`.

## Comparativa con Higgs

| Feature | Higgs v3 | Qwen3-TTS 1.7B Base |
|---------|----------|---------------------|
| VRAM | ~8-18 GB | ~4 GB (bfloat16) |
| Clonación de voz | ✅ Ref audio + texto | ✅ Ref audio + texto (3 s) |
| Idiomas | 100+ | 10 |
| Emociones inline | ✅ Tags `<emotion:...>` | ✅ Control por instrucción (`instruct`) |
| Streaming | ✅ (vLLM-Omni) | ✅ (doble track) |
| Latencia inicial | 1-3 min | 1-3 min (1ª vez) |
| Calidad en español | Buena | Muy buena (benchmark líder) |