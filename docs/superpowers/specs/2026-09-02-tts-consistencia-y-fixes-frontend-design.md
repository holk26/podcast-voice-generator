# Diseño: Validación de consistencia TTS por chunk + fixes frontend

Fecha: 2026-09-02
Estado: aprobado para planificación
Alcance: worker (validación por chunk) + frontend (fixes puntuales)

## Contexto

El podcast se sintetiza por chunks en `worker/tts_local.py::synthesize_clone`.
Cada chunk se genera de forma independiente con Higgs/Qwen3 (motor
autoregresivo), lo que produce variaciones ocasionales de timbre, pitch,
velocidad o energía entre chunks de la misma voz. El resultado suena a
"varias grabaciones pegadas" en lugar de una sola toma continua.

Paralelamente, `ERRORES.txt` (auditoría de agosto 2026) lista hallazgos de
frontend. Re-verificación 2026-09-02: varios hallazgos ya están resueltos
(nav móvil, nav emoji, confirmación en ChannelCard, toast global, README
inexistente). Este spec cubre solo los hallazgos aún vigentes.

Decisions tomadas con el usuario:

- Validación **inline en el loop de síntesis** (no segunda pasada).
- **best-of-N**: si ningún intento supera el umbral, se acepta el mejor con
  warning. El episodio nunca falla por validación.
- El P1 de solapamiento Studio/Canales se **difiere** a un spec aparte.

## Frente A — Validación de consistencia por chunk (worker)

### Componente nuevo: `worker/tts_quality.py`

`ChunkValidator`, instanciado una vez por episodio dentro del proceso hijo de
síntesis (la GPU está ocupada por vLLM; todo corre en CPU):

- **Similitud de timbre** (peso principal): Resemblyzer (d-vectors) contra la
  muestra de referencia fija del speaker (`voice.reference_path`). Cosine
  similarity. Resemblyzer es dependencia nueva (`resemblyzer`); si la descarga
  de pesos falla, fallback a similitud de MFCC con librosa (más débil pero
  sin dependencias nuevas) y warning en el log.
- **Pitch**: F0 mediano vía librosa (`pyin`, piso 50 Hz). Comparado contra el
  chunk anterior (Δ relativo).
- **Velocidad**: palabras del chunk / duración en segundos, comparado contra
  el promedio móvil de los chunks ya aceptados.
- **Loudness**: RMS del chunk vs RMS medio de los aceptados.
- **Score**: similitud_timbre (umbral 0.80) como condición principal; Δpitch,
  Δvelocidad y Δloudness como penalización. Umbral y pesos configurables por
  env (patrón `os.getenv` ya usado en el worker).

### Regla de emociones

Los guiones llevan tags Higgs (`<|emotion:fear|>`, etc.) embebidos en el
texto del chunk. Al cambiar el tag entre chunks, pitch y energía cambian
*intencionalmente*. El validador parsea el tag por chunk y, si difiere del
chunk anterior, relaja los umbrales de pitch/energía (factor configurable,
default ×1.5). La similitud de timbre nunca se relaja.

### Integración en `synthesize_clone`

En el loop (`worker/tts_local.py:209-221`), entre `engine.synthesize()` y
`part_paths.append(part)`:

1. Generar chunk (intento 1).
2. Validar. ¿Pasa? → aceptar.
3. Si no: reintentar hasta 3 intentos (cada intento re-muestrea: Higgs corre
   con temperature 0.8 y `synthesize` no expone seed, así que la variación
   entre intentos viene del muestreo; añadir `seed` al API de motores queda
   fuera de alcance), guardando el WAV y score de cada intento.
4. Aceptar el de mayor score. Si supera el umbral: log normal. Si no: warning
   `[TTS] chunk N/M: mejor intento score=X.XX < umbral; se acepta igual`.
5. Fail-open: si el validador lanza excepción (modelo no disponible, audio
   corrupto), se acepta el chunk y se loguea el error. La síntesis nunca
  rompe por el validador.

Log por intento: `[TTS] chunk 12/36 intento 2: sim=0.83 Δpitch=+4% Δspeed=-3% ✓`
Los scores se acumulan y se loguea un resumen al final del episodio
(score mínimo/medio por episodio) para ajustar umbrales con datos reales.

Config por env (defaults):

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TTS_QUALITY_ENABLED` | `1` | `0` desactiva el validador por completo |
| `TTS_QUALITY_MAX_ATTEMPTS` | `3` | intentos máximos por chunk |
| `TTS_QUALITY_SIM_THRESHOLD` | `0.80` | umbral cosine similarity timbre |
| `TTS_QUALITY_PITCH_TOLERANCE` | `0.15` | Δ pitch relativo tolerado |
| `TTS_QUALITY_SPEED_TOLERANCE` | `0.20` | Δ velocidad relativo tolerado |
| `TTS_QUALITY_LUFS_TOLERANCE` | `6.0` | Δ RMS tolerado (dB) |
| `TTS_QUALITY_EMOTION_RELAX` | `1.5` | factor de relajación si cambia emoción |

### Tests

- Test unitario del score: WAVs sintéticos (tono puro con distintas
  frecuencias / RMS) — verificar que el score cae al cambiar pitch y que la
  relajación por emoción se aplica. Mock del embedder si no hay pesos.
- Test de best-of-N: validador mockeado que falla 2 veces y pasa a la 3ª.

## Frente B — Fixes frontend (hallazgos vigentes de ERRORES.txt)

1. **Confirmaciones de borrado** (P2): `EpisodeCard` (`EpisodeCard.tsx:89`)
   y `PlanEntryCard` (`PlanEntryCard.tsx:149`) deben usar `askConfirm` del
   `appStore`, igual que `ChannelCard` (patrón existente: título, mensaje con
   nombre del elemento, `danger: true`).
2. **Toast en create** (P2): `create.tsx:28` reemplaza `alert()` por
   `showToast` del `appStore` (ya existe y está montado global en `Layout`).
3. **Dashboard** (P1): `index.tsx` ya tiene KPIs + acciones rápidas; añadir
   sección "Episodios recientes" (últimos 5 por `created_at`, con estado y
   link a `/queue`) y atajo al primer canal con episodios pendientes. Reusa
   `useEpisodeStore` (ya cargado en la página).
4. **Limpieza de studio.tsx** (P2, sin cambiar el flujo): extraer el
   selector de canal a un componente `ChannelSelector` usado una sola vez
   (hoy está duplicado en el header y en la sección del canal), y mover los
   tabs de sección a subcomponentes en `frontend/src/components/studio/` si
   el archivo supera ~300 líneas tras la extracción. No tocar UX ni rutas.

### Fuera de alcance (explícito)

- Unificación Studio/Canales (P1 de IA de producto) — spec aparte.
- Pasarela `/login` redundante (P3, ruta muerta menor) — se anota para el
  spec de unificación.
- Cualquier hallazgo ya resuelto según re-verificación de 2026-09-02.

## Verificación

- `python -m pytest backend/tests worker/tests -v --tb=short` en verde.
- `npm run build` en `frontend/` sin errores de tipos.
- Generación real de un episodio de prueba en el worker con
  `TTS_QUALITY_ENABLED=1`: los logs muestran scores por chunk y el resumen
  por episodio; la GPU queda libre tras la síntesis (sin regresión del
  flujo fixer→música).
