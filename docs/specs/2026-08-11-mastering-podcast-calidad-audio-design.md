# Diseño: Mastering de Podcast y Mejora de Calidad de Audio

**Fecha:** 2026-08-11  
**Estado:** Aprobado para implementación  
**Autor:** Asistente de desarrollo  
**Pipeline objetivo:** Generación web (`MediaPackage` / `DramaMixer`) con voces clonadas Higgs

---

## 1. Resumen ejecutivo

El usuario genera episodios desde la web usando el pipeline `MediaPackage`/`DramaMixer` y voces clonadas con Higgs. Los audios finales presentan cuatro problemas principales:

1. **Cortes/saltos entre frases** causados por concatenación directa de líneas (`+` en pydub) sin crossfade.
2. **Voz poco profesional** por falta de compresión, EQ y loudness estándar.
3. **Ruido/siseo en pausas** porque no hay reducción de ruido ni gate.
4. **Mezcla con música de fondo rígida** debido a ducking por ganancia fija/RMS simple.

Este diseño propone una cadena de **mastering de podcast** basada en ffmpeg (sin nuevas dependencias) que:

- Aplica crossfade y trimming entre líneas de diálogo.
- Normaliza a **-16 LUFS** con pico **-1 dB** (estándar podcast).
- Aplica EQ ligero, compresión, limitador y noise gate.
- Mejora el ducking de música de fondo con sidechain suave.
- Aplica crossfade y loudness también a intro/outro.

---

## 2. Motivación y contexto

### 2.1 Pipeline actual

El flujo web genera episodios a través de:

1. `PipelineOrchestrator.run()` → adquiere contenido y genera `MediaPackage`.
2. `_render_audio()` → `DramaMixer.mix_package()` genera línea por línea y las concatena.
3. `_apply_background_music()` → mezcla música con ducking simple.
4. `_apply_branding()` → añade intro/outro.
5. Exporta `final_with_branding.mp3`.

### 2.2 Problemas detectados en código

| Problema | Ubicación | Impacto |
|----------|-----------|---------|
| Concatenación directa sin crossfade | `audio/drama_mixer.py:157` (`final = final + segment`) | Cortes audibles entre frases |
| Silencios fijos por línea | `core/media_package.py:31-32` | Pausas robóticas, ritmo irregular |
| No hay LUFS real en DramaMixer | `audio/drama_mixer.py:165` usa `pydub.normalize()` | Niveles inconsistentes |
| No hay compresor/limitador/EQ/gate | Pipeline Python | Voz sin cuerpo, picos, ruido |
| Ducking simple por ganancia fija | `audio/mixer.py:16`, `core/pipeline_orchestrator.py:437` | Música entra/sale bruscamente |
| Intro/outro sin crossfade | `audio/branding_engine.py:222` | Transiciones duras |

---

## 3. Alcance

### Dentro del alcance

- Mejorar `audio/drama_mixer.py` (crossfade + trimming).
- Crear `audio/podcast_mastering.py` con cadena ffmpeg.
- Integrar mastering en `core/pipeline_orchestrator.py`.
- Mejorar ducking de música de fondo.
- Mejorar `audio/branding_engine.py` (crossfade + loudness).
- Añadir configuración y tests.

### Fuera del alcance

- Cambiar motores TTS.
- Reescribir el pipeline clásico por secciones (`core/audio_pipeline.py`).
- Añadir dependencias de terceros como `pedalboard` o `noisereduce`.
- Procesamiento en tiempo real.

---

## 4. Diseño técnico

### 4.1 Nuevo módulo: `audio/podcast_mastering.py`

Responsabilidad: aplicar mastering profesional a un archivo de audio usando ffmpeg.

#### Funciones públicas

```python
def process_voice_mix(
    input_path: str,
    output_path: str,
    config: Optional[MasteringConfig] = None,
) -> str:
    """
    Aplica el procesado de voz:
    loudness normalization -> EQ -> compresión -> limitador -> noise gate.
    Se usa sobre el mix de diálogo antes de mezclar música/intro/outro.
    """

def normalize_loudness(
    input_path: str,
    output_path: str,
    target_lufs: float = -16.0,
    true_peak_db: float = -1.0,
) -> str:
    """Normaliza a LUFS usando ffmpeg loudnorm a dos pasadas."""

def apply_compressor_limiter(
    input_path: str,
    output_path: str,
    threshold_db: float = -18.0,
    ratio: float = 3.0,
    attack_ms: float = 5.0,
    release_ms: float = 50.0,
) -> str:
    """Aplica compresión suave seguida de limitador."""

def apply_light_eq(input_path: str, output_path: str, config: MasteringConfig) -> str:
    """Aplica EQ ligero: high-pass y presencia según config."""

def apply_noise_gate(
    input_path: str,
    output_path: str,
    threshold_db: float = -45.0,
) -> str:
    """Aplica noise gate para eliminar siseo en pausas."""
```

#### Configuración por defecto

```python
@dataclass
class MasteringConfig:
    enabled: bool = True
    crossfade_ms: int = 80
    branding_crossfade_ms: int = 300
    trim_silence_threshold_db: float = -50
    target_lufs: float = -16.0
    true_peak_db: float = -1.0
    apply_eq: bool = True
    apply_compressor_limiter: bool = True
    apply_noise_gate: bool = True
    eq_highpass_hz: float = 80.0
    eq_presence_hz: float = 3000.0
    eq_presence_gain_db: float = 2.0
    compressor_threshold_db: float = -18.0
    compressor_ratio: float = 3.0
    gate_threshold_db: float = -45.0
```

### 4.2 Cambios en `audio/drama_mixer.py`

#### Trimming de silencio por línea

Después de sintetizar cada línea, se detecta y corta silencio al inicio y final por debajo de un umbral:

```python
segment = segment.strip_silence(
    silence_thresh=config.trim_silence_threshold_db,
    keep_silence=50,  # ms de silencio mínimo respetado
)
```

#### Concatenación con crossfade

Reemplazar:

```python
final = final + segment
```

Por:

```python
final = final.append(segment, crossfade=crossfade_ms)
```

- `crossfade_ms` configurable, default **80 ms**.
- Máximo permitido **500 ms** para evitar solapamiento excesivo.

### 4.3 Cambios en `core/pipeline_orchestrator.py`

#### Procesamiento de la voz

Después de `_render_audio()`, se aplica el procesamiento de voz (EQ, compresión, gate y loudness) al mix de diálogo:

```python
# Después de _render_audio()
if package.config.podcast_mastering.enabled:
    voice_mix_path = podcast_mastering.process_voice_mix(
        voice_mix_path,
        output_path=processed_voice_path,
        config=package.config.podcast_mastering,
    )
```

Este paso solo afecta a la voz, dejando intacta la dinámica de la música de fondo.

#### Normalización final

Después de añadir música de fondo e intro/outro, se aplica una **normalización final de loudness** al archivo completo:

```python
# Después de _apply_background_music() y _apply_branding()
if package.config.podcast_mastering.enabled:
    final_path = podcast_mastering.normalize_loudness(
        final_path,
        output_path=final_path,
        target_lufs=config.target_lufs,
        true_peak_db=config.true_peak_db,
    )
```

### 4.4 Mejora de ducking de música de fondo

**Opción preferida:** reemplazar el ducking por ganancia fija/RMS por sidechain con ffmpeg:

```bash
ffmpeg -i music.wav -i voice.wav -filter_complex \
"[0:a]asplit=2[sc][mix];[mix]volume=1.0[bg];[sc][1:a]sidechaincompress=threshold=-20dB:ratio=5:attack=20:release=250:level_sc=1[ducked];[1:a][ducked]amix" \
output.wav
```

**Fallback:** si la arquitectura actual no permite pasar ambas pistas a ffmpeg de forma directa, se mejorará la curva de ganancia existente con:

- Ventanas RMS más cortas (50 ms).
- Ataque rápido (20 ms) y liberación suave (250 ms).
- Rango de ducking ampliado (-8 dB con voz, +0 dB en silencio).

### 4.5 Cambios en `audio/branding_engine.py`

- Aplicar crossfade al unir `intro + main + outro`.
- Normalizar intro/outro al mismo `target_lufs` que el cuerpo antes de concatenar.

```python
# Helper: calcular ganancia necesaria para llevar un segmento al target LUFS.
# Puede implementarse con ffmpeg loudnorm o aproximación pydub RMS si loudnorm no está disponible.
intro = intro.apply_gain(lufs_delta(intro, target_lufs))
main = main.apply_gain(lufs_delta(main, target_lufs))
outro = outro.apply_gain(lufs_delta(outro, target_lufs))

branding_crossfade_ms = config.podcast_mastering.branding_crossfade_ms
result = intro.append(main, crossfade=branding_crossfade_ms)
result = result.append(outro, crossfade=branding_crossfade_ms)
```

---

## 5. Configuración del proyecto

Nueva sección en la configuración de proyecto/MediaPackage:

```json
{
  "podcast_mastering": {
    "enabled": true,
    "crossfade_ms": 80,
    "branding_crossfade_ms": 300,
    "trim_silence_threshold_db": -50,
    "target_lufs": -16,
    "true_peak_db": -1,
    "apply_eq": true,
    "apply_compressor_limiter": true,
    "apply_noise_gate": true,
    "background_ducking": {
      "enabled": true,
      "attack_ms": 20,
      "release_ms": 250,
      "voice_reduction_db": 8
    }
  }
}
```

La interfaz web debe exponer estas opciones en el panel de generación con valores por defecto razonables.

---

## 6. Flujo de datos actualizado

```
1. Generar línea TTS (Higgs/Edge/etc.)
2. Trimmear silencio de cada línea
3. Concatenar líneas con crossfade
   ↓
4. Procesado de voz (EQ, compresión, limitador, noise gate)
   ↓
5. Mezclar música de fondo con sidechain ducking
   ↓
6. Añadir intro/outro con crossfade y loudness
   ↓
7. Normalización final de loudness (-16 LUFS, -1 dB TP)
   ↓
8. Exportar MP3/WAV final
```

---

## 7. Manejo de errores

| Escenario | Comportamiento |
|-----------|----------------|
| ffmpeg no disponible | Fallback a pydub `normalize()` y log de warning. Continuar generación. |
| Mastering falla | Loggear error, devolver audio sin mastering. No abortar episodio. |
| Crossfade mayor al 50% de la duración de un segmento | Limitar crossfade al 50% de la duración más corta. |
| LUFS fuera de rango permitido | Forzar a rango [-23, -14]. |
| Audio mono/stereo inconsistente | Convertir a mono 24 kHz antes de mastering si es necesario. |

---

## 8. Testing

### 8.1 Tests unitarios

Nuevo archivo: `tests/test_podcast_mastering.py`

- Verificar que `master_audio` genera un archivo de salida válido.
- Verificar que no hay clipping (muestras dentro de [-1.0, 1.0]).
- Verificar que el LUFS medido está dentro de ±1.5 dB del target.
- Verificar que la duración no cambia de forma inesperada (>95% de la original).

### 8.2 Tests de integración

- Generar un `MediaPackage` de prueba con 3 líneas de diálogo.
- Verificar que la concatenación con crossfade no produce caídas de señal en los puntos de unión.
- Verificar que el audio final tiene loudness cercano a -16 LUFS.

### 8.3 Validación auditiva

- Generar episodio corto antes y después del cambio.
- Comparar A/B: cortes, ruido, dinámica y presencia de voz.

---

## 9. Métricas de éxito

- No hay cortes audibles entre líneas de diálogo.
- Loudness final del episodio: **-16 LUFS ± 1.5 dB**.
- True peak **≤ -1 dB**.
- Reducción de energía en silencios (gate): **≥ 10 dB** respecto al audio original.
- Ducking de música de fondo suave y natural.
- Tiempo de procesamiento extra: **< 50%** del tiempo actual de generación de audio.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| ffmpeg no esté instalado en el entorno de despliegue | Fallback a pydub; añadir ffmpeg a documentación de dependencias. |
| Crossfade excesivo cause solapamiento de palabras | Default conservador de 80 ms, máximo 500 ms. |
| Noise gate corte inicios de palabras suaves | Umbral conservador (-45 dB) y keep_silence de 50 ms. |
| Compresión excesiva deje la voz plana | Ratio suave (3:1), threshold -18 dB. |
| Aumento de tiempo de procesamiento | Medir en tests; si supera 50%, optimizar o hacer etapas opcionales. |

---

## 11. Notas de implementación

- Mantener compatibilidad hacia atrás: el mastering debe poder desactivarse por configuración.
- No modificar motores TTS ni el pipeline clásico por secciones.
- Reutilizar funciones existentes de `audio/normalizer.py` donde sea posible, pero delegar LUFS real a ffmpeg.
- Todos los cambios deben estar cubiertos por tests antes de mergear.

---

## 12. Próximos pasos

1. Invocar `writing-plans` para crear plan de implementación detallado.
2. Ejecutar plan en sesión de implementación.
3. Validar con episodio de prueba A/B.
