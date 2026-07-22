# Higgs Audio v3 TTS — Configuración y uso

Guía verificada (22-jul-2026) para generar voz clonada con **Higgs Audio v3 TTS 4B**
(Boson AI) en este equipo: **RTX 5060 Laptop 8 GB VRAM**, Python 3.11 (`venv311`),
vLLM-Omni 0.22.1.

Resultado validado: voz clonada de Homero con calidad "perfecta" (vs XTTS v2, que
sonaba robótica/metálica).

---

## 1. Referencia de voz

- **Archivo usado**: `voices/clones/homero_referencia.wav`
  (WAV PCM 44.1 kHz mono, ~10 s — la única referencia conservada en `voices/clones/`).
- **Solo WAV/FLAC**: soundfile NO lee `.m4a`/AAC (`Format not recognised`).
  Convierte antes con ffmpeg si hace falta:
  `ffmpeg -i entrada.m4a -ar 44100 -ac 1 salida.wav`
- Mejor 6-15 s de voz limpia, sin música ni ruido de fondo.
- Demo del resultado: `output/higgs_v3_test/prueba_higgs_v3.wav`.

## 2. Modelo

Local en `models/higgs-audio-v3-tts-4b/` (~9 GB, en `.gitignore`, no se sube a git).

## 3. Cómo ejecutar

```bash
export PATH="$PWD/venv311/bin:$PATH"
export VLLM_USE_FLASHINFER_SAMPLER=0
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

venv311/bin/python scripts/test_higgs_v3_local.py \
    "Texto a sintetizar." \
    "voices/clones/homero_referencia.wav" \
    "transcripción opcional de la referencia"
```

Salida: `output/higgs_v3_test/prueba_higgs_v3.wav` (24 kHz mono).

## 4. Configuración del motor (clave, no tocar a la ligera)

En `scripts/test_higgs_v3_local.py`:

```python
engine_kwargs = {
    "trust_remote_code": True,
    "max_model_len": 1536,        # con 512 los textos largos salen cortados (ver 5.7)
    "max_num_seqs": 1,
    "max_num_batched_tokens": 1536,
    "dtype": "bfloat16",          # NO "half" (ver 5.5)
    "quantization": "fp8",
    "enforce_eager": False,       # CUDA graphs: 24x más rápido (ver 6)
    "disable_custom_all_reduce": True,
    "stage_overrides": '{"0": {"gpu_memory_utilization": 0.64}, '
                       '"1": {"gpu_memory_utilization": 0.25}}',
}
```

`core/higgs_engine.py` ya incluye esta misma configuración por defecto y fija
las variables de entorno necesarias al hacer `load()`.

## 5. Problemas encontrados y solución (historial completo)

### 5.1 `cpu_offload_gb` + FP8 → crash
`NotImplementedError: Cannot copy out of meta tensor; no data!`
El offloader de vLLM no puede copiar pesos FP8 (meta tensors).
**Solución**: no usar `cpu_offload_gb`; FP8 solo (~4.5 GB) cabe en 8 GB.

### 5.2 `FileNotFoundError: 'ninja'`
vLLM/flashinfer invoca ninja para compilar kernels JIT.
**Solución**: `pip install ninja` y exportar `PATH` con `venv311/bin`.

### 5.3 flashinfer JIT + ruta con espacios → build roto
El proyecto vive en `podcast with VRAM nvidia` (espacios). Ninja trunca la ruta:
`ninja: error: '/home/holk/.../podcast', needed by ... missing`.
**Solución**: `VLLM_USE_FLASHINFER_SAMPLER=0` (sampler nativo de torch).

### 5.4 Stage 1 (vocoder) moría al arrancar
vllm-omni es multi-etapa: stage 0 = LLM autoregresivo, stage 1 = vocoder.
Con `gpu_memory_utilization=0.85` global, stage 0 acaparaba 6.4 GB y stage 1
no encontraba memoria (`Free memory 0.57 GiB < desired`).
**Solución**: `stage_overrides` repartiendo la GPU (0.62 / 0.28) +
`max_num_seqs=1`, `max_num_batched_tokens=512`, `enforce_eager=True`,
`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.

### 5.5 Audio generado = silencio total (NaN)
Con `dtype="half"` (FP16) + FP8 el modelo producía NaN; el WAV salía 100% ceros
(`RuntimeWarning: invalid value encountered in cast`).
**Solución**: `dtype="bfloat16"` (mayor rango dinámico, sin overflow).

### 5.6 numpy/pandas/scikit-learn (afectaba a XTTS, ya resuelto)
`venv311` tenía numpy 2.3.5 con pandas 1.5.3 y scikit-learn 1.3.2 (compilados
contra numpy 1.x) → `numpy.dtype size changed` al cargar XTTS.
**Solución aplicada**: `pandas 2.3.3`, `scikit-learn 1.9.0`.

### 5.7 Textos largos cortados / KV cache insuficiente
Con `max_model_len=512` el audio de textos largos salía truncado (los tokens de
la referencia + prompt + salida no caben). Al subirlo, con stage0=0.62 saltaba
`0.28 GiB KV cache is needed... larger than the available (0.11 GiB)`.
**Solución**: `max_model_len=1536` + reparto 0.64/0.25. Para guiones largos el
endpoint `/api/tts/synthesize` trocea el texto en frases y concatena, así que
1536 tokens por chunk son suficientes.

## 6. Rendimiento medido

- Carga del motor: ~2-3 min (incluye captura de CUDA graphs; solo la primera vez)
- Generación con `enforce_eager=False` (CUDA graphs): **~3.5 s para 5 s de audio (RTF ≈ 0.7)**
- Generación con `enforce_eager=True`: ~83 s para 5 s de audio (RTF ≈ 16) — 24x más lento
- Uso de VRAM: stage 0 ≈ 5.6 GiB + stage 1 ≈ 1.8 GiB
- **Ojo**: si Ollama (u otro proceso) tiene un modelo cargado en VRAM, Higgs no
  cabe. Descárgalo antes con `ollama stop <modelo>` o espera a su keep-alive.

## 7. Estado de integración

- `core/higgs_engine.py`: incluye la config de la sección 4 por defecto y fija
  las variables de entorno en `load()`.
- Preview web (`/api/tts/preview`): las voces clonadas se sintetizan con Higgs
  (ya no con XTTS). La primera llamada tarda ~2-3 min (carga del motor);
  las siguientes, unos segundos. Las voces edge siguen igual.
- Episodios desde la web: el worker delega las voces `clone:*` en la API
  (`POST /api/tts/synthesize`, troceo + concatenación de texto largo), así solo
  hay una instancia del motor en GPU. Verificado end-to-end (episodio de
  motivación de ~41 s con voz de Homero).
- Perfil de cast listo: `cast/voice_profiles/higgs_homero.yaml`
  (apunta a `voices/clones/homero_referencia.wav`).
- Pendiente: usar Higgs en el pipeline clásico (GUI PyQt) y en el Studio/CrewAI.
