# Validación consistencia TTS + fixes frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validar cada chunk TTS contra la voz de referencia (best-of-3, fail-open) para que el podcast suene como una sola grabación, y resolver los hallazgos vigentes de `ERRORES.txt` en el frontend.

**Architecture:** Módulo nuevo `worker/tts_quality.py` (CPU, corre dentro del proceso hijo de síntesis) con `ChunkValidator` (similitud de timbre con Resemblyzer + pitch/velocidad/RMS con librosa). Se integra en el loop de `synthesize_clone`. Frontend: confirmaciones con `askConfirm`, toast global, dashboard con episodios recientes, dedup del selector de canal en Studio.

**Tech Stack:** Python 3.11 (worker), resemblyzer, librosa, numpy, soundfile; React 18 + TanStack Router + Zustand + Tailwind (frontend), vitest.

**Spec:** `docs/superpowers/specs/2026-09-02-tts-consistencia-y-fixes-frontend-design.md`

**Convenciones del repo:**
- Tests worker: `python -m pytest backend/tests worker/tests -v --tb=short` (venv: `venv311/`, correr desde la raíz).
- Tests frontend: `cd frontend && npm test -- --run` (vitest run).
- Build frontend: `cd frontend && npm run build` (tsc + vite).
- Commits: solo los archivos tocados por cada tarea. NO commitear los cambios preexistentes en `worker/handlers.py`, `worker/main.py`, `worker/tts_local.py` que no sean parte de esta tarea… **excepción**: las tareas 4-5 SÍ tocan `worker/tts_local.py`; antes de commitear usar `git diff` para incluir solo el diff de esa tarea.
- venv: usar siempre `venv311/bin/python` y `venv311/bin/pip` desde la raíz del repo.

---

### Task 1: Instalar resemblyzer y registrar la dependencia

**Files:**
- Modify: `requirements.txt` (raíz del repo)

- [ ] **Step 1: Instalar en el venv**

```bash
venv311/bin/pip install "resemblyzer>=0.1.2,<0.2"
```

Esperado: instala `resemblyzer` (torch/numpy ya están). Verificar:

```bash
venv311/bin/python -c "from resemblyzer import VoiceEncoder; print('ok')"
```

Esperado: `ok` (la descarga de pesos del encoder ocurre al instanciar, no al importar).

- [ ] **Step 2: Registrar en requirements.txt**

Añadir al final de `requirements.txt` (mantener orden alfabético si existe):

```
resemblyzer>=0.1.2,<0.2
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: resemblyzer para validación de timbre por chunk"
```

---

### Task 2: Tests del validador (TDD — fallan primero)

**Files:**
- Test: `worker/tests/test_tts_quality.py`

- [ ] **Step 1: Escribir el test**

```python
"""Tests del validador de consistencia por chunk.

Usan tonos sintéticos (soundfile) y un embedder mockeado, así no requieren
pesos de resemblyzer ni GPU.
"""
import math

import numpy as np
import pytest
import soundfile as sf

from worker.tts_quality import (
    ChunkScore,
    ChunkValidator,
    QualityConfig,
    extract_emotion,
    select_best,
)

SR = 24000


def _tone(path, freq: float, seconds: float = 1.5, rms: float = 0.2):
    t = np.arange(int(SR * seconds)) / SR
    y = rms * np.sin(2 * math.pi * freq * t)
    sf.write(str(path), y, SR)
    return path


class _FakeEmbedder:
    """Embedder determinista controlado: devuelve vectores unitarios fijos."""

    def __call__(self, wav_path):
        return np.array([1.0, 0.0])


def _make_validator(tmp_path, **cfg_overrides):
    cfg = QualityConfig(
        max_attempts=3,
        sim_threshold=0.80,
        pitch_tolerance=0.15,
        speed_tolerance=0.20,
        lufs_tolerance=6.0,
        emotion_relax=1.5,
        **cfg_overrides,
    )
    ref = _tone(tmp_path / "ref.wav", 120.0)
    v = ChunkValidator(str(ref), config=cfg, embedder=_FakeEmbedder())
    return v


def _score(v, wav_path, text="palabras para medir velocidad"):
    return v.validate(str(wav_path), text)


def test_extract_emotion():
    assert extract_emotion("<|emotion:fear|> Era oscuro.") == "fear"
    assert extract_emotion("Sin tag aquí.") is None


def test_pitch_change_detected(tmp_path):
    v = _make_validator(tmp_path, sim_threshold=0.0)
    a = _score(v, _tone(tmp_path / "a.wav", 120.0))
    assert a.passed  # primer chunk solo mide sim (sin anterior)
    v.accept(a)
    b = _score(v, _tone(tmp_path / "b.wav", 240.0))  # +100% pitch
    assert not b.passed


def test_emotion_change_relaxes_threshold(tmp_path):
    v = _make_validator(tmp_path, sim_threshold=0.0, pitch_tolerance=0.15)
    a = _score(v, _tone(tmp_path / "a.wav", 120.0), "<|emotion:neutral|> Texto.")
    v.accept(a)
    # Mismo salto de pitch (+100%) pero cambia la emoción: 0.15*1.5=0.225 < 1.0 → sigue fallando
    b = _score(v, _tone(tmp_path / "b.wav", 240.0), "<|emotion:fear|> Texto.")
    assert not b.passed
    # Con un salto pequeño (20%) y emoción distinta pasa (0.20 > 0.15 estricto, <= 0.225 relajado)
    c = _score(v, _tone(tmp_path / "c.wav", 144.0), "<|emotion:sadness|> Texto.")
    assert c.passed


def test_select_best_prefers_passing_then_similarity(tmp_path):
    s_pass = ChunkScore(similarity=0.85, pitch_median=120.0, speed_wps=2.0, rms_db=-14.0, passed=True)
    s_fail_high = ChunkScore(similarity=0.90, pitch_median=120.0, speed_wps=2.0, rms_db=-14.0, passed=False)
    s_fail_low = ChunkScore(similarity=0.70, pitch_median=120.0, speed_wps=2.0, rms_db=-14.0, passed=False)
    p = tmp_path / "x.wav"
    sf.write(str(p), np.zeros(SR), SR)
    best_path, best = select_best([(p, s_fail_high), (p, s_pass), (p, s_fail_low)])
    assert best.passed and best.similarity == 0.85


def test_loudness_jump_detected(tmp_path):
    v = _make_validator(tmp_path, sim_threshold=0.0, lufs_tolerance=3.0)
    a = _score(v, _tone(tmp_path / "a.wav", 120.0, rms=0.2))
    v.accept(a)
    b = _score(v, _tone(tmp_path / "b.wav", 120.0, rms=0.02))  # -20 dB
    assert not b.passed
```

Nota sobre `test_pitch_change_detected`: el primer chunk no tiene chunk anterior, así que solo se exige similitud (con `sim_threshold=0.0` siempre pasa). El estado del validador se actualiza con `accept()`.

- [ ] **Step 2: Correr y verificar que falla**

```bash
venv311/bin/python -m pytest worker/tests/test_tts_quality.py -v --tb=short
```

Esperado: FAIL con `ModuleNotFoundError: No module named 'worker.tts_quality'`.

---

### Task 3: Implementar `worker/tts_quality.py`

**Files:**
- Create: `worker/tts_quality.py`

- [ ] **Step 1: Implementar el módulo**

```python
"""Validación de consistencia por chunk TTS.

Cada chunk sintetizado se compara con la muestra de referencia fija del
speaker (similitud de timbre) y con el chunk anterior (pitch, velocidad,
loudness). Pensado para correr en CPU dentro del proceso hijo de síntesis:
la GPU está ocupada por vLLM.

Fail-open por diseño: si el validador falla (pesos no descargables, audio
ilegible), el chunk se acepta igual; la síntesis nunca rompe por esto.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

EMOTION_RE = re.compile(r"<\|emotion:([a-z_]+)\|>")


def extract_emotion(text: str) -> str | None:
    """Devuelve el tag de emoción Higgs del chunk, o None."""
    m = EMOTION_RE.search(text)
    return m.group(1) if m else None


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class QualityConfig:
    max_attempts: int = 3
    sim_threshold: float = 0.80
    pitch_tolerance: float = 0.15
    speed_tolerance: float = 0.20
    lufs_tolerance: float = 6.0
    emotion_relax: float = 1.5

    @classmethod
    def from_env(cls) -> "QualityConfig":
        return cls(
            max_attempts=_env_int("TTS_QUALITY_MAX_ATTEMPTS", 3),
            sim_threshold=_env_float("TTS_QUALITY_SIM_THRESHOLD", 0.80),
            pitch_tolerance=_env_float("TTS_QUALITY_PITCH_TOLERANCE", 0.15),
            speed_tolerance=_env_float("TTS_QUALITY_SPEED_TOLERANCE", 0.20),
            lufs_tolerance=_env_float("TTS_QUALITY_LUFS_TOLERANCE", 6.0),
            emotion_relax=_env_float("TTS_QUALITY_EMOTION_RELAX", 1.5),
        )


@dataclass
class ChunkScore:
    similarity: float
    pitch_median: float
    speed_wps: float
    rms_db: float
    passed: bool


def select_best(attempts: list) -> tuple:
    """Elige el mejor intento: primero que pase, luego mayor similitud."""
    if not attempts:
        raise ValueError("No attempts to select from")
    return max(attempts, key=lambda item: (item[1].passed, item[1].similarity))


class ChunkValidator:
    """Valida chunks contra la referencia fija y el chunk anterior."""

    def __init__(self, reference_path: str, config: QualityConfig | None = None,
                 embedder=None):
        self.config = config or QualityConfig.from_env()
        self._embedder = embedder  # callable(wav_path) -> np.ndarray; None = lazy real
        self._ref_emb = self._embed(Path(reference_path))
        self._ref_pitch = self._median_pitch(Path(reference_path))
        self._prev: ChunkScore | None = None
        self._prev_emotion: str | None = None
        self._speed_hist: list[float] = []
        self.scores: list[float] = []

    # -- métricas -----------------------------------------------------------

    def _embed(self, wav_path: Path) -> np.ndarray:
        if self._embedder is not None:
            emb = np.asarray(self._embedder(str(wav_path)), dtype=np.float32)
            return emb / (np.linalg.norm(emb) + 1e-10)
        try:
            from resemblyzer import VoiceEncoder, preprocess_wav
            if not hasattr(self, "_encoder"):
                self._encoder = VoiceEncoder(device="cpu")
            wav = preprocess_wav(str(wav_path))
            emb = self._encoder.embed_utterance(wav)
            return emb / (np.linalg.norm(emb) + 1e-10)
        except Exception as e:
            logger.warning(f"[TTS-Quality] Resemblyzer no disponible ({e}); "
                           "usando fallback MFCC (menos fiable)")
            emb = self._mfcc_embed(wav_path)
            return emb / (np.linalg.norm(emb) + 1e-10)

    def _mfcc_embed(self, wav_path: Path) -> np.ndarray:
        import librosa
        y, sr = librosa.load(str(wav_path), sr=None, mono=True)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        return mfcc.mean(axis=1).astype(np.float32)

    @staticmethod
    def _median_pitch(wav_path: Path) -> float:
        import librosa
        y, sr = librosa.load(str(wav_path), sr=None, mono=True)
        f0 = librosa.yin(y, fmin=50, fmax=500, sr=sr)
        voiced = f0[f0 > 0]
        return float(np.median(voiced)) if voiced.size else 0.0

    # -- validación ----------------------------------------------------------

    def validate(self, wav_path: str, text: str) -> ChunkScore:
        import librosa
        wav = Path(wav_path)
        y, sr = librosa.load(str(wav), sr=None, mono=True)
        duration = len(y) / sr if sr else 0.0
        rms = float(np.sqrt(np.mean(y ** 2) + 1e-12))
        rms_db = 20.0 * float(np.log10(rms + 1e-10))
        f0 = librosa.yin(y, fmin=50, fmax=500, sr=sr)
        voiced = f0[f0 > 0]
        pitch = float(np.median(voiced)) if voiced.size else 0.0
        speed = (len(text.split()) / duration) if duration > 0 else 0.0

        emb = self._embed(wav)
        similarity = float(np.dot(emb, self._ref_emb))

        emotion = extract_emotion(text)
        relax = self.config.emotion_relax if (
            emotion and self._prev_emotion and emotion != self._prev_emotion
        ) else 1.0

        pitch_ref = self._prev.pitch_median if self._prev else self._ref_pitch
        pitch_ok = True
        if pitch > 0 and pitch_ref > 0:
            pitch_ok = abs(pitch - pitch_ref) / pitch_ref <= self.config.pitch_tolerance * relax

        speed_ref = (
            sum(self._speed_hist) / len(self._speed_hist)
            if self._speed_hist else (self._prev.speed_wps if self._prev else 0.0)
        )
        speed_ok = True
        if speed > 0 and speed_ref > 0:
            speed_ok = abs(speed - speed_ref) / speed_ref <= self.config.speed_tolerance * relax

        rms_ok = True
        if self._prev is not None:
            rms_ok = abs(rms_db - self._prev.rms_db) <= self.config.lufs_tolerance

        passed = (
            similarity >= self.config.sim_threshold
            and pitch_ok and speed_ok and rms_ok
        )
        return ChunkScore(
            similarity=similarity, pitch_median=pitch,
            speed_wps=speed, rms_db=rms_db, passed=passed,
        )

    def accept(self, score: ChunkScore) -> None:
        """Fija el chunk aceptado como referencia para el siguiente."""
        self._prev = score
        if score.speed_wps > 0:
            self._speed_hist.append(score.speed_wps)
            self._speed_hist = self._speed_hist[-5:]
        self.scores.append(score.similarity)

    def summary(self) -> str:
        if not self.scores:
            return "sin chunks validados"
        return (f"sim min={min(self.scores):.2f} "
                f"media={sum(self.scores) / len(self.scores):.2f} "
                f"chunks={len(self.scores)}")
```

- [ ] **Step 2: Correr los tests**

```bash
venv311/bin/python -m pytest worker/tests/test_tts_quality.py -v --tb=short
```

Esperado: 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add worker/tts_quality.py worker/tests/test_tts_quality.py
git commit -m "feat(worker): validador de consistencia por chunk (timbre/pitch/velocidad/loudness)"
```

---

### Task 4: Integrar el validador en `synthesize_clone`

**Files:**
- Modify: `worker/tts_local.py` (función `synthesize_clone`, líneas ~202-235)

- [ ] **Step 1: Añadir el validador al loop de chunks**

En `worker/tts_local.py`, en `synthesize_clone`, reemplazar el bloque del `try` (líneas 208-228 aprox) por:

```python
    out_p = Path(output_path)
    tmp_dir = out_p.parent / f"_chunks_{out_p.stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    validator = None
    if os.getenv("TTS_QUALITY_ENABLED", "1").lower() in ("1", "true", "yes"):
        from worker.tts_quality import ChunkValidator

        try:
            validator = ChunkValidator(voice.reference_path)
            logger.info("[TTS] Validación de consistencia activada "
                        f"(umbral sim={validator.config.sim_threshold}, "
                        f"máx intentos={validator.config.max_attempts})")
        except Exception as e:
            logger.warning(f"[TTS] No se pudo iniciar el validador ({e}); "
                           "continuando sin validación")

    part_paths: list[Path] = []
    total_start = time.time()
    try:
        for i, chunk in enumerate(chunks):
            pct = int(((i + 1) / total_chunks) * 100)
            preview = chunk[:40].replace("\n", " ")
            logger.info(
                f"[TTS] [{pct}%] Fragmento {i + 1}/{total_chunks} sintetizando: '{preview}...'"
            )
            part_start = time.time()
            part = tmp_dir / f"chunk_{i:04d}.wav"
            max_attempts = validator.config.max_attempts if validator else 1
            best: tuple | None = None
            for attempt in range(1, max_attempts + 1):
                engine.synthesize(chunk, voice, str(part))
                if validator is None:
                    best = (part, None)
                    break
                try:
                    score = validator.validate(str(part), chunk)
                except Exception as e:
                    logger.warning(f"[TTS] Validador falló en chunk {i + 1} "
                                   f"({e}); se acepta el chunk (fail-open)")
                    best = (part, None)
                    break
                delta_pitch = ""
                if validator_prev_pitch(validator) > 0 and score.pitch_median > 0:
                    rel = (score.pitch_median - validator_prev_pitch(validator)) / validator_prev_pitch(validator)
                    delta_pitch = f" Δpitch={rel:+.0%}"
                logger.info(
                    f"[TTS] chunk {i + 1}/{total_chunks} intento {attempt}: "
                    f"sim={score.similarity:.2f} speed={score.speed_wps:.1f} pal/seg"
                    f"{delta_pitch} {'✓' if score.passed else '✗'}"
                )
                if best is None or (score.passed, score.similarity) > (best[1].passed, best[1].similarity):
                    best_part = tmp_dir / f"chunk_{i:04d}_best.wav"
                    shutil.copy2(part, best_part)
                    best = (best_part, score)
                if score.passed:
                    break

            best_part, best_score = best
            if validator is not None and best_score is not None:
                if not best_score.passed:
                    logger.warning(
                        f"[TTS] chunk {i + 1}/{total_chunks}: mejor intento "
                        f"sim={best_score.similarity:.2f} < umbral; se acepta igual (best-of-N)"
                    )
                validator.accept(best_score)
                shutil.copy2(best_part, part)
                best_part.unlink(missing_ok=True)
            part_paths.append(part)
            logger.info(
                f"[TTS] Fragmento {i + 1}/{total_chunks} generado en {time.time() - part_start:.1f}s"
            )

        if validator is not None:
            logger.info(f"[TTS] Resumen consistencia: {validator.summary()}")
        logger.info(f"[TTS] Concatenando {total_chunks} fragmentos de audio...")
        _concat_wavs(part_paths, out_p)
        logger.info(
            f"[TTS] Síntesis de voz clonada completada con éxito en {time.time() - total_start:.1f}s -> {out_p.name}"
        )
        return str(out_p)
    finally:
        for p in part_paths:
            p.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except Exception:
            pass
```

Y añadir en la cabecera del archivo (junto a los otros imports):

```python
import shutil
```

Y esta función auxiliar a nivel de módulo (antes de `synthesize_clone`):

```python
def validator_prev_pitch(validator) -> float:
    """Pitch de referencia vigente del validador (anterior o referencia)."""
    prev = getattr(validator, "_prev", None)
    if prev is not None and prev.pitch_median > 0:
        return prev.pitch_median
    return getattr(validator, "_ref_pitch", 0.0) or 0.0
```

Notas de implementación:
- No usar `select_best` dentro del loop: el ranking incremental con `best` evita guardar todos los WAVs.
- `_chunks_` tmp dir ya existe en el código actual; se reutiliza.
- El resumen por episodio usa `validator.summary()` (spec: score min/medio logueado al final).

- [ ] **Step 2: Verificar sintaxis y tests existentes**

```bash
venv311/bin/python -c "import ast; ast.parse(open('worker/tts_local.py').read()); print('syntax ok')"
venv311/bin/python -m pytest worker/tests -v --tb=short
```

Esperado: syntax ok + todos los tests worker PASS (incluidos los de `_split_text`, que no se tocaron).

- [ ] **Step 3: Commit (solo el diff de esta tarea)**

```bash
git diff worker/tts_local.py > /tmp/tts_local_task4.diff
git add worker/tts_local.py
git commit -m "feat(worker): validación best-of-N por chunk en synthesize_clone"
```

(Ojo: `worker/tts_local.py` puede tener cambios previos sin commitear en el working tree. Revisar con `git log -1 --format=%H -- worker/tts_local.py` y `git stash` no es necesario si los cambios previos ya eran la baseline de este trabajo — en ese caso el commit incluye todo el diff actual del archivo, que es lo deseado.)

---

### Task 5: Test de integración best-of-N con motor mockeado

**Files:**
- Test: `worker/tests/test_tts_quality.py` (ampliar)

- [ ] **Step 1: Añadir el test de integración**

```python
def test_synthesize_clone_best_of_n(tmp_path, monkeypatch):
    """Con un motor que falla 2 veces y acierta a la 3ª, se acepta el 3er intento."""
    import worker.tts_local as tts_local

    attempts = {"n": 0}

    class _FakeEngine:
        def synthesize(self, text, voice, output_path):
            attempts["n"] += 1
            freq = 240.0 if attempts["n"] < 3 else 120.0
            _tone(Path(output_path), freq)

    monkeypatch.setattr(tts_local, "_get_engine", lambda name: _FakeEngine())
    monkeypatch.setenv("TTS_QUALITY_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("TTS_QUALITY_SIM_THRESHOLD", "0.0")
    # Evita que el validador real cargue resemblyzer: embedder fijo vía env no
    # existe, así que parcheamos ChunkValidator.__init__ para inyectar uno.
    from worker import tts_quality

    orig_init = tts_quality.ChunkValidator.__init__

    def fake_init(self, reference_path, config=None, embedder=None):
        orig_init(self, reference_path, config=config, embedder=_FakeEmbedder())

    monkeypatch.setattr(tts_quality.ChunkValidator, "__init__", fake_init)

    text = "Una frase corta de prueba. Otra frase más."
    out = tmp_path / "out.wav"
    tts_local.synthesize_clone(text, "clone:fake", str(out))
    assert attempts["n"] == 3
    assert out.exists()
```

Requiere que `_parse_clone_voice_id` funcione con `clone:fake`: busca `voices/clones/fake.wav`, que no existe → `FileNotFoundError`. Por eso también hay que parchear `_parse_clone_voice_id`:

```python
    monkeypatch.setattr(
        tts_local,
        "_parse_clone_voice_id",
        lambda voice_id: tts_local.Voice(
            id=voice_id, name="fake", type="cloned", engine="higgs", language="es",
            reference_path=str(_tone(tmp_path / "ref.wav", 120.0)),
        ),
    )
```

(Añadir este `monkeypatch.setattr` antes de la llamada a `synthesize_clone` en el mismo test. Verificar el constructor de `core.project.Voice` en `worker/tts_local.py:97-103` para pasar los mismos campos: `id`, `name`, `type`, `engine`, `language`, `reference_path`.)

- [ ] **Step 2: Correr**

```bash
venv311/bin/python -m pytest worker/tests/test_tts_quality.py -v --tb=short
```

Esperado: 6 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add worker/tests/test_tts_quality.py
git commit -m "test(worker): integración best-of-N con motor mockeado"
```

---

### Task 6: Confirmación al eliminar episodio (EpisodeCard)

**Files:**
- Modify: `frontend/src/components/EpisodeCard.tsx`
- Test: `frontend/src/components/EpisodeCard.test.tsx`

- [ ] **Step 1: Actualizar el test (mock de appStore + test de cancel)**

En `EpisodeCard.test.tsx`, añadir el mock junto a los existentes:

```tsx
vi.mock('../stores/appStore', () => ({
  useAppStore: (sel: any) =>
    sel({
      pushToast: vi.fn(),
      askConfirm: vi.fn().mockResolvedValue(true),
    }),
}))
```

Y reemplazar el test `'calls onDelete when delete button is clicked'` por dos:

```tsx
  it('calls onDelete when delete is confirmed', async () => {
    const onDelete = vi.fn()
    render(<EpisodeCard episode={makeEpisode()} onDelete={onDelete} onRetry={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /eliminar/i }))
    await vi.waitFor(() => expect(onDelete).toHaveBeenCalledWith(1))
  })

  it('does not call onDelete when delete is cancelled', async () => {
    const askConfirm = vi.fn().mockResolvedValue(false)
    vi.mocked(useAppStore).mockImplementation((sel: any) =>
      sel({ pushToast: vi.fn(), askConfirm }))
    const onDelete = vi.fn()
    render(<EpisodeCard episode={makeEpisode()} onDelete={onDelete} onRetry={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /eliminar/i }))
    await new Promise((r) => setTimeout(r, 50))
    expect(onDelete).not.toHaveBeenCalled()
  })
```

(Ajustar el import: `import { useAppStore } from '../stores/appStore'` arriba del test.)

- [ ] **Step 2: Verificar que falla**

```bash
cd frontend && npm test -- --run EpisodeCard
```

Esperado: el test nuevo falla (todavía no hay confirmación; el borrado es directo). El test de cancel falla porque onDelete sí se llama.

- [ ] **Step 3: Implementar en EpisodeCard.tsx**

Añadir el import y el handler, siguiendo el patrón de `ChannelCard.tsx:16-34`:

```tsx
import { useAppStore } from '../stores/appStore'
```

Dentro del componente:

```tsx
  const askConfirm = useAppStore((s) => s.askConfirm)

  const handleDelete = async () => {
    const ok = await askConfirm({
      title: 'Eliminar episodio',
      message: `¿Seguro que quieres eliminar "${episode.title}"? Esta acción no se puede deshacer.`,
      confirmLabel: 'Eliminar',
      danger: true,
    })
    if (ok) onDelete(episode.id)
  }
```

Y el botón Eliminar:

```tsx
        <button
          type="button"
          onClick={handleDelete}
          aria-label={`Eliminar episodio ${episode.title}`}
          className="text-red-400 text-sm hover:text-red-300 hover:underline transition-colors"
        >
          Eliminar
        </button>
```

- [ ] **Step 4: Correr tests**

```bash
cd frontend && npm test -- --run EpisodeCard
```

Esperado: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/EpisodeCard.tsx frontend/src/components/EpisodeCard.test.tsx
git commit -m "feat(web): confirmación al eliminar episodio"
```

---

### Task 7: Confirmación al eliminar entrada del plan (PlanEntryCard)

**Files:**
- Modify: `frontend/src/components/PlanEntryCard.tsx:149`

- [ ] **Step 1: Implementar (patrón idéntico a ChannelCard)**

Añadir import:

```tsx
import { useAppStore } from '../stores/appStore'
```

Dentro del componente (tras los otros hooks):

```tsx
  const askConfirm = useAppStore((s) => s.askConfirm)

  const handleDelete = async () => {
    const ok = await askConfirm({
      title: 'Eliminar entrada',
      message: `¿Seguro que quieres eliminar "${entry.title}" del plan? Esta acción no se puede deshacer.`,
      confirmLabel: 'Eliminar',
      danger: true,
    })
    if (ok) onDelete(entry.id)
  }
```

Botón (línea ~149):

```tsx
            <button
              type="button"
              onClick={handleDelete}
              className="text-red-400 hover:text-red-300 hover:underline text-sm transition-colors"
            >
              Eliminar
            </button>
```

- [ ] **Step 2: Verificar**

```bash
cd frontend && npm run build
```

Esperado: `tsc` sin errores y build OK.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PlanEntryCard.tsx
git commit -m "feat(web): confirmación al eliminar entrada del plan"
```

---

### Task 8: Toast en create.tsx (reemplazar alert)

**Files:**
- Modify: `frontend/src/routes/create.tsx:28`

- [ ] **Step 1: Implementar**

Añadir import:

```tsx
import { useAppStore } from '../stores/appStore'
```

Dentro del componente:

```tsx
  const pushToast = useAppStore((s) => s.pushToast)
```

Y en el catch de `handleSubmit`:

```tsx
    } catch (error) {
      pushToast('Error creando episodio: ' + String(error), 'error')
    } finally {
```

- [ ] **Step 2: Verificar**

```bash
cd frontend && npm run build
```

Esperado: build OK.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/create.tsx
git commit -m "feat(web): toast de error al crear episodio (reemplaza alert)"
```

---

### Task 9: Dashboard — episodios recientes

**Files:**
- Modify: `frontend/src/routes/index.tsx`

- [ ] **Step 1: Implementar**

Añadir import:

```tsx
import { useChannelStore } from '../stores/channelStore'
```

En el componente, junto a los otros stores:

```tsx
  const channels = useChannelStore((state) => state.channels)
  const fetchChannels = useChannelStore((state) => state.fetchChannels)
```

En el `useEffect` existente, añadir `fetchChannels()`:

```tsx
  useEffect(() => {
    fetchEpisodes()
    fetchVoices()
    fetchChannels()
  }, [fetchEpisodes, fetchVoices, fetchChannels])
```

Derived data (tras `counts`):

```tsx
  const recentEpisodes = useMemo(
    () =>
      [...episodes]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5),
    [episodes],
  )
  const statusBadge: Record<Episode['status'], string> = {
    pending: 'text-amber-300',
    running: 'text-purple-300',
    completed: 'text-green-300',
    failed: 'text-red-300',
  }
  const channelWithPending = channels.find(
    (c) => (c.entries_total ?? 0) > (c.entries_generated ?? 0),
  )
```

(Añadir `import { Episode } from '../types'` si no está.)

Sección JSX — insertar entre "Acciones rápidas" y "Voces disponibles":

```tsx
      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold tracking-tight">Episodios recientes</h3>
          <Link to="/queue" className="text-sm text-purple-400 hover:text-purple-300 transition-colors">
            Ver cola →
          </Link>
        </div>
        {recentEpisodes.length === 0 ? (
          <p className="text-sm text-slate-400">Aún no hay episodios. Crea el primero desde "Nuevo episodio".</p>
        ) : (
          <ul className="divide-y divide-slate-700/60">
            {recentEpisodes.map((ep) => (
              <li key={ep.id} className="py-2 flex justify-between items-center gap-4">
                <Link
                  to="/queue"
                  search={{ highlight: ep.id }}
                  className="font-medium text-slate-100 hover:text-purple-300 transition-colors truncate"
                >
                  {ep.title}
                </Link>
                <span className={`text-sm ${statusBadge[ep.status]} shrink-0`}>
                  {ep.status}
                </span>
              </li>
            ))}
          </ul>
        )}
        {channelWithPending && (
          <p className="text-sm mt-4">
            <Link
              to="/channels/$id/plan"
              params={{ id: String(channelWithPending.id) }}
              className="text-violet-400 hover:text-violet-300 transition-colors"
            >
              → {channelWithPending.name} tiene {(channelWithPending.entries_total ?? 0) - (channelWithPending.entries_generated ?? 0)} entradas pendientes de generar
            </Link>
          </p>
        )}
      </div>
```

Nota: `Link to="/queue"` con `search` requiere que la ruta `/queue` acepte search param `highlight` — ya lo hace (`queue.tsx:15` usa `useSearch` con `highlight`). Verificar que el tipo de ruta lo permita; si `tsc` se queja de `search={{ highlight: ep.id }}`, añadir en `queue.tsx` la validación de search (verificar primero cómo está declarada la ruta; `create.tsx:26` ya navega con ese search, así que el tipo existe).

- [ ] **Step 2: Verificar**

```bash
cd frontend && npm run build
```

Esperado: build OK.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/index.tsx
git commit -m "feat(web): episodios recientes y atajo a canal pendiente en dashboard"
```

---

### Task 10: Studio — componente ChannelSelector compartido

**Files:**
- Create: `frontend/src/components/ChannelSelector.tsx`
- Modify: `frontend/src/components/StudioPanel.tsx:56-64`
- Modify: `frontend/src/routes/studio.tsx:150-158`

- [ ] **Step 1: Crear ChannelSelector.tsx**

```tsx
import { Channel } from '../types'

interface Props {
  channels: Channel[]
  value: number | ''
  onChange: (id: number) => void
  compact?: boolean
}

export default function ChannelSelector({ channels, value, onChange, compact }: Props) {
  const cls = compact
    ? 'bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500'
    : 'bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500'
  return (
    <select
      className={cls}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      aria-label="Seleccionar canal"
    >
      {channels.map((c) => (
        <option key={c.id} value={c.id}>{c.name}</option>
      ))}
    </select>
  )
}
```

- [ ] **Step 2: Usarlo en studio.tsx (reemplaza el select de líneas 150-158)**

```tsx
import ChannelSelector from '../components/ChannelSelector'
```

```tsx
              <div className="flex items-center gap-3 mb-2">
                <ChannelSelector
                  channels={channels}
                  value={selectedId}
                  onChange={setSelectedId}
                  compact
                />
```

- [ ] **Step 3: Usarlo en StudioPanel.tsx (reemplaza el select de líneas 56-64)**

Ver primero el JSX exacto de `StudioPanel.tsx:50-70` para conservar clases y wrapper. Sustituir el `<select>` de canal por:

```tsx
import ChannelSelector from './ChannelSelector'
```

```tsx
        <ChannelSelector
          channels={channels}
          value={selectedId}
          onChange={onSelectChannel}
          compact
        />
```

(El nombre de la prop de cambio en StudioPanel puede diferir; verificar la firma de props de `StudioPanel` en `frontend/src/components/StudioPanel.tsx` antes de editar y usar la que recibe `(id: number) => void`.)

- [ ] **Step 4: Verificar**

```bash
cd frontend && npm run build && npm test -- --run
```

Esperado: build OK, tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChannelSelector.tsx frontend/src/components/StudioPanel.tsx frontend/src/routes/studio.tsx
git commit -m "refactor(web): ChannelSelector compartido en Studio (dedup)"
```

Nota: `studio.tsx` queda en ~390 líneas tras la extracción. El spec permite dejar los tabs inline si no supera ~300 de forma natural; **no** hacer split adicional de tabs en esta tarea (YAGNI — el selector duplicado era el hallazgo P2).

---

### Task 11: Verificación local completa

**Files:** ninguno (solo verificación)

- [ ] **Step 1: Tests backend + worker**

```bash
venv311/bin/python -m pytest backend/tests worker/tests -v --tb=short
```

Esperado: todo PASS.

- [ ] **Step 2: Tests + build frontend**

```bash
cd frontend && npm test -- --run && npm run build
```

Esperado: todo PASS, build OK.

- [ ] **Step 3: Generación real con validación activa**

Reiniciar el worker local (está corriendo como `python -m worker.main`; matar por PID y relanzar):

```bash
kill <PID de worker.main>   # sin -9; encontrar con: pgrep -f "python -m worker.main"
cd /home/holk/Documents/proyectos/podcast/podcast\ with\ VRAM\ nvidia
PYTHONPATH=. venv311/bin/python -m worker.main > logs/worker.log 2>&1 &
```

Encolar un episodio corto de prueba (voz `clone:alejandra`, texto de ~2 párrafos) vía API de producción con el JWT en `/tmp/podcash_token` (si 401, re-login admin/admin contra `/api/auth/login`). Observar:

```bash
tail -f logs/worker.log
```

Criterios de aceptación en el log:
- Línea `Validación de consistencia activada (umbral sim=0.8, máx intentos=3)`.
- Por chunk: líneas `chunk N/M intento K: sim=... speed=... ✓/✗`.
- Al final: `Resumen consistencia: sim min=... media=... chunks=N`.
- El episodio llega a `completed` y aparece `final.mp3`.

- [ ] **Step 4: GPU libre tras la síntesis**

```bash
nvidia-smi --query-gpu=memory.used --format=csv
```

Esperado: < 500 MiB usados tras completar el episodio (sin regresión del flujo hijo-que-muere).

---

### Task 12: Deploy en Dokploy y validación de servicios

**Files:** ninguno (deploy + verificación)

- [ ] **Step 1: Push a origin**

```bash
git log origin/master..master --oneline   # revisar qué se va a subir
git push origin master
```

(Ojo: NO incluir en el push archivos no commiteados. El push sube commits, no el working tree; verificar el log antes.)

- [ ] **Step 2: Verificar redeploy en Dokploy**

Listar aplicaciones vía MCP Dokploy y confirmar que el deploy del frontend se dispara (o dispararlo manualmente con `application-redeploy` / `compose-redeploy` según el tipo de app). El backend no cambió en este trabajo; si Dokploy redeploya por push, validar que vuelva a `running` sano.

- [ ] **Step 3: Validar producción**

```bash
curl -s https://api.podcash.app.moonsbow.com/api/health
curl -s -o /dev/null -w "%{http_code}" https://podcash.app.moonsbow.com
```

Esperado: health OK / 200. Si el `index.html` sigue cacheado (nota de AGENTS.md sobre Cloudflare), purgar caché del dominio desde el panel.

Login visual rápido (playwright/chrome-devtools) en `https://podcash.app.moonsbow.com` con admin/admin: verificar dashboard con "Episodios recientes". Probar el diálogo de confirmación: en `/queue`, pulsar Eliminar en un episodio → debe aparecer el ConfirmDialog; cancelar no borra nada.

- [ ] **Step 4: Worker local corriendo**

Confirmar el worker local activo con el código nuevo (log de arranque reciente, SSE conectado):

```bash
pgrep -af "python -m worker.main" && tail -3 logs/worker.log
```

---

## Self-Review del plan

- **Spec coverage**: validación por chunk (T2-T5), env config (T3 `QualityConfig.from_env`, T4 `TTS_QUALITY_ENABLED`), regla de emociones (T3 test `test_emotion_change_relaxes_threshold`), best-of-N (T4-T5), resumen por episodio (T4), confirmaciones EpisodeCard/PlanEntryCard (T6-T7), toast create (T8), dashboard recientes + atajo canal (T9), selector Studio (T10), verificación completa + Dokploy (T11-T12). Spec pide `TTS_QUALITY_*` — 6 vars de spec + ENABLED cubiertas. ✓
- **Placeholders**: ningún TBD; los pasos "verificar firma de props de StudioPanel" son instrucciones concretas de lectura previa, no código omitido. ✓
- **Consistencia de tipos**: `ChunkValidator(reference_path, config=..., embedder=...)`, `validate(wav_path, text) -> ChunkScore`, `accept(score)`, `summary()`, `select_best(attempts) -> (path, score)` usados igual en T3, T4, T5. `QualityConfig` campos = env vars = spec. `pushToast(text, kind)` coincide con `appStore.ts:21`. `askConfirm({title, message, confirmLabel, danger})` coincide con `ChannelCard` y `appStore.ts:24`. ✓
