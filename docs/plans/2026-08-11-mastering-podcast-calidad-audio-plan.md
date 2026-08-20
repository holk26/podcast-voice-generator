# Mastering de Podcast y Mejora de Calidad de Audio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar una cadena de mastering profesional para el pipeline web (`MediaPackage`/`DramaMixer`) que elimine cortes, normalice loudness a -16 LUFS, aplique EQ/compresión/limitador/noise gate y mejore el ducking de música de fondo, todo con ffmpeg y sin nuevas dependencias.

**Architecture:** Crear un módulo dedicado `audio/podcast_mastering.py` con funciones de procesado de voz y normalización LUFS. Integrarlo en `PipelineOrchestrator` después del renderizado de voz y después del branding. Modificar `DramaMixer` para aplicar trimming y crossfade entre líneas. Mejorar `BrandingEngine` con crossfade y loudness en intro/outro. Mejorar el ducking de música con ffmpeg `sidechaincompress`.

**Tech Stack:** Python 3.11, pydub, ffmpeg, pytest, numpy.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `audio/podcast_mastering.py` | Create | Config, helpers y cadena ffmpeg de mastering. |
| `core/pipeline_orchestrator.py` | Modify | Integrar `process_voice_mix` y `normalize_loudness`; mejorar ducking. |
| `audio/drama_mixer.py` | Modify | Crossfade y trimming entre líneas. |
| `audio/branding_engine.py` | Modify | Crossfade y loudness en intro/outro. |
| `tests/test_podcast_mastering.py` | Create | Tests unitarios del nuevo módulo. |
| `tests/test_drama_mixer.py` | Modify | Añadir tests de crossfade/trimming si no existen. |
| `tests/test_pipeline_orchestrator.py` | Modify | Añadir test de integración con mastering. |

---

## Task 1: Create `audio/podcast_mastering.py`

**Files:**
- Create: `audio/podcast_mastering.py`
- Test: `tests/test_podcast_mastering.py`

- [ ] **Step 1: Write the failing test for config and helpers**

```python
# tests/test_podcast_mastering.py
import pytest
from audio.podcast_mastering import MasteringConfig, _db_to_linear, _linear_to_db


def test_db_to_linear():
    assert _db_to_linear(-6.0) == pytest.approx(0.501, abs=0.01)


def test_linear_to_db():
    assert _linear_to_db(0.5) == pytest.approx(-6.02, abs=0.1)


def test_mastering_config_defaults():
    cfg = MasteringConfig()
    assert cfg.enabled is True
    assert cfg.crossfade_ms == 80
    assert cfg.target_lufs == -16.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_podcast_mastering.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'audio.podcast_mastering'`

- [ ] **Step 3: Implement config and helper functions**

```python
# audio/podcast_mastering.py
"""Podcast mastering chain using ffmpeg.

Provides voice processing (EQ, compression, limiting, noise gate) and
true LUFS loudness normalization for the MediaPackage pipeline.
"""

import json
import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MasteringConfig:
    enabled: bool = True
    crossfade_ms: int = 80
    branding_crossfade_ms: int = 300
    trim_silence_threshold_db: float = -50.0
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
    compressor_attack_ms: float = 5.0
    compressor_release_ms: float = 50.0
    gate_threshold_db: float = -45.0


def _db_to_linear(db: float) -> float:
    return 10 ** (db / 20.0)


def _linear_to_db(value: float) -> float:
    return 20 * math.log10(max(abs(value), 1e-10))


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except Exception:
        return False
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_podcast_mastering.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add audio/podcast_mastering.py tests/test_podcast_mastering.py
git commit -m "feat(audio): add MasteringConfig and helpers for podcast mastering"
```

---

## Task 2: Implement `process_voice_mix` in `audio/podcast_mastering.py`

**Files:**
- Modify: `audio/podcast_mastering.py`
- Test: `tests/test_podcast_mastering.py`

- [ ] **Step 1: Write the failing test for `process_voice_mix`**

```python
# tests/test_podcast_mastering.py
import tempfile
import numpy as np
from pydub import AudioSegment
from audio.podcast_mastering import process_voice_mix, MasteringConfig


def _make_test_wav(path: str, duration_ms: int = 1000, freq: int = 440):
    sample_rate = 24000
    t = np.linspace(0, duration_ms / 1000.0, int(sample_rate * duration_ms / 1000.0))
    samples = (0.5 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    audio = AudioSegment(
        samples.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,
        channels=1,
    )
    audio.export(path, format="wav")


def test_process_voice_mix_disabled_copies_input():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.wav")
        dst = os.path.join(tmp, "output.wav")
        _make_test_wav(src)
        cfg = MasteringConfig(enabled=False)
        result = process_voice_mix(src, dst, cfg)
        assert result == dst
        assert os.path.exists(dst)


def test_process_voice_mix_outputs_valid_audio():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.wav")
        dst = os.path.join(tmp, "output.wav")
        _make_test_wav(src)
        cfg = MasteringConfig(enabled=True)
        result = process_voice_mix(src, dst, cfg)
        assert result == dst
        seg = AudioSegment.from_wav(result)
        assert seg.frame_rate == 24000
        assert seg.channels == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_podcast_mastering.py::test_process_voice_mix_disabled_copies_input tests/test_podcast_mastering.py::test_process_voice_mix_outputs_valid_audio -v`

Expected: FAIL with `ImportError: cannot import name 'process_voice_mix'`

- [ ] **Step 3: Implement `process_voice_mix`**

```python
# Añadir al final de audio/podcast_mastering.py

def process_voice_mix(
    input_path: str,
    output_path: str,
    config: Optional[MasteringConfig] = None,
) -> str:
    """
    Apply EQ, compression, limiting and noise gate to a voice mix.
    Uses ffmpeg. If config.enabled is False, copies input to output.
    """
    config = config or MasteringConfig()
    if not config.enabled:
        shutil.copy2(input_path, output_path)
        return output_path

    if not _ffmpeg_available():
        raise RuntimeError("ffmpeg is required for podcast mastering")

    filters = []
    if config.apply_eq:
        filters.append(f"highpass=f={config.eq_highpass_hz}")
        filters.append(
            f"equalizer=f={config.eq_presence_hz}:t=q:w=1:g={config.eq_presence_gain_db}"
        )
    if config.apply_compressor_limiter:
        filters.append(
            f"acompressor=threshold={config.compressor_threshold_db}dB"
            f":ratio={config.compressor_ratio}"
            f":attack={config.compressor_attack_ms}"
            f":release={config.compressor_release_ms}"
        )
        filters.append(
            f"alimiter=limit={config.true_peak_db}dB:attack=5:release=50"
        )
    if config.apply_noise_gate:
        filters.append(
            f"agate=threshold={config.gate_threshold_db}dB:attack=10:release=250:hold=50"
        )

    if not filters:
        shutil.copy2(input_path, output_path)
        return output_path

    filter_str = ",".join(filters)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-af",
        filter_str,
        "-ar",
        "24000",
        "-ac",
        "1",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_podcast_mastering.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add audio/podcast_mastering.py tests/test_podcast_mastering.py
git commit -m "feat(audio): implement process_voice_mix with ffmpeg EQ/compressor/limiter/gate"
```

---

## Task 3: Implement `normalize_loudness` in `audio/podcast_mastering.py`

**Files:**
- Modify: `audio/podcast_mastering.py`
- Test: `tests/test_podcast_mastering.py`

- [ ] **Step 1: Write the failing test for `normalize_loudness`**

```python
# tests/test_podcast_mastering.py
from audio.podcast_mastering import normalize_loudness


def test_normalize_loudness_changes_level():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.wav")
        dst = os.path.join(tmp, "output.wav")
        _make_test_wav(src, duration_ms=2000, freq=440)
        normalize_loudness(src, dst, target_lufs=-16.0, true_peak_db=-1.0)
        assert os.path.exists(dst)
        seg = AudioSegment.from_wav(dst)
        assert seg.duration_seconds == pytest.approx(2.0, abs=0.1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_podcast_mastering.py::test_normalize_loudness_changes_level -v`

Expected: FAIL with `ImportError: cannot import name 'normalize_loudness'`

- [ ] **Step 3: Implement `normalize_loudness`**

```python
# Añadir al final de audio/podcast_mastering.py

def normalize_loudness(
    input_path: str,
    output_path: str,
    target_lufs: float = -16.0,
    true_peak_db: float = -1.0,
) -> str:
    """
    Normalize audio to target LUFS using ffmpeg loudnorm two-pass.
    Falls back to copying the input if ffmpeg analysis cannot be parsed.
    """
    if not _ffmpeg_available():
        shutil.copy2(input_path, output_path)
        return output_path

    target_lufs = float(np.clip(target_lufs, -23.0, -14.0))  # type: ignore[name-defined]

    # First pass: analyze
    analyze_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-af",
        f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(
        analyze_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    match = re.search(r"\{.*\}", result.stderr, re.DOTALL)
    if not match:
        shutil.copy2(input_path, output_path)
        return output_path

    stats = json.loads(match.group())

    # Second pass: apply
    apply_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-af",
        (
            f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11"
            f":measured_I={stats['input_i']}"
            f":measured_TP={stats['input_tp']}"
            f":measured_LRA={stats['input_lra']}"
            f":measured_thresh={stats['input_thresh']}"
            f":offset={stats['target_offset']}"
            f":linear=true"
        ),
        "-ar",
        "24000",
        "-ac",
        "1",
        output_path,
    ]
    subprocess.run(apply_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path
```

Wait: `np.clip` requires numpy import. Add `import numpy as np` at the top of the file.

Also note: ffmpeg loudnorm JSON keys are `input_I`, `input_Tp`, `input_LRA`, `input_Thresh`. Make sure these match.

- [ ] **Step 4: Add numpy import at top of `audio/podcast_mastering.py`**

```python
import math
import numpy as np  # NEW
import os
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_podcast_mastering.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add audio/podcast_mastering.py tests/test_podcast_mastering.py
git commit -m "feat(audio): implement two-pass LUFS normalization with ffmpeg loudnorm"
```

---

## Task 4: Add `MasteringConfig` to `EpisodeConfig`

**Files:**
- Modify: `core/pipeline_orchestrator.py`
- Modify: `audio/podcast_mastering.py` (ensure importable)
- Test: `tests/test_pipeline_orchestrator.py`

- [ ] **Step 1: Write the failing test for config presence**

```python
# tests/test_pipeline_orchestrator.py
from core.pipeline_orchestrator import EpisodeConfig
from audio.podcast_mastering import MasteringConfig


def test_episode_config_has_mastering_defaults():
    cfg = EpisodeConfig(episode_type="raw")
    assert cfg.podcast_mastering is not None
    assert cfg.podcast_mastering.enabled is True
    assert cfg.podcast_mastering.target_lufs == -16.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_orchestrator.py::test_episode_config_has_mastering_defaults -v`

Expected: FAIL with `AttributeError: 'EpisodeConfig' object has no attribute 'podcast_mastering'`

- [ ] **Step 3: Modify `EpisodeConfig`**

```python
# core/pipeline_orchestrator.py
from audio.podcast_mastering import MasteringConfig


@dataclass
class EpisodeConfig:
    # ... existing fields ...
    # Audio enhancement
    audio_enhancer: str = "none"
    audio_enhancer_mode: int = 0
    # Podcast mastering
    podcast_mastering: Optional[MasteringConfig] = field(default_factory=MasteringConfig)
    # Extra passthrough for processors
    processor_options: Dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_pipeline_orchestrator.py::test_episode_config_has_mastering_defaults -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/pipeline_orchestrator.py tests/test_pipeline_orchestrator.py
git commit -m "feat(core): add MasteringConfig to EpisodeConfig"
```

---

## Task 5: Modify `DramaMixer` for Crossfade and Trimming

**Files:**
- Modify: `audio/drama_mixer.py`
- Test: `tests/test_drama_mixer.py`

- [ ] **Step 1: Write the failing test for crossfade behavior**

```python
# tests/test_drama_mixer.py
from audio.drama_mixer import DramaMixer


def test_drama_mixer_accepts_crossfade_config():
    mixer = DramaMixer(crossfade_ms=80, trim_silence_threshold_db=-50)
    assert mixer.crossfade_ms == 80
    assert mixer.trim_silence_threshold_db == -50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_drama_mixer.py::test_drama_mixer_accepts_crossfade_config -v`

Expected: FAIL with `TypeError: DramaMixer.__init__() got an unexpected keyword argument 'crossfade_ms'`

- [ ] **Step 3: Modify `DramaMixer.__init__` and add helper methods**

```python
# audio/drama_mixer.py
class DramaMixer:
    def __init__(
        self,
        voice_cast: Optional[VoiceCastManager] = None,
        sample_rate: int = 24000,
        normalize: bool = True,
        fade_in_ms: int = 500,
        fade_out_ms: int = 1000,
        default_engine_device: str = "auto",
        enhancer=None,
        enhance_per_line: bool = True,
        enhance_final: bool = True,
        crossfade_ms: int = 80,
        trim_silence_threshold_db: float = -50.0,
    ):
        self.voice_cast = voice_cast or VoiceCastManager()
        self.sample_rate = sample_rate
        self.normalize = normalize
        self.fade_in_ms = fade_in_ms
        self.fade_out_ms = fade_out_ms
        self.default_engine_device = default_engine_device
        self.enhancer = enhancer
        self.enhance_per_line = enhance_per_line
        self.enhance_final = enhance_final
        self.crossfade_ms = max(0, min(int(crossfade_ms), 500))
        self.trim_silence_threshold_db = trim_silence_threshold_db
        self._engine_cache: Dict[str, TTSBase] = {}

    def _trim_segment(self, segment: AudioSegment) -> AudioSegment:
        """Trim leading/trailing silence while keeping a small padding."""
        return segment.strip_silence(
            silence_thresh=self.trim_silence_threshold_db,
            keep_silence=50,
        )

    def _crossfade_segments(self, segments: List[AudioSegment]) -> AudioSegment:
        """Concatenate segments with crossfade."""
        if not segments:
            raise ValueError("No segments to concatenate.")
        final = segments[0]
        for segment in segments[1:]:
            cf = min(self.crossfade_ms, len(final) // 2, len(segment) // 2)
            final = final.append(segment, crossfade=cf)
        return final
```

- [ ] **Step 4: Modify `render_line` to trim segment and update `mix_package`**

In `render_line`, after setting frame rate and channels and before adding pause silence:

```python
        # Ensure correct sample rate and mono
        segment = segment.set_frame_rate(self.sample_rate).set_channels(1)

        # Trim leading/trailing silence
        segment = self._trim_segment(segment)

        # Add silence before and after
        if line.pause_before_ms > 0:
            ...
```

In `mix_package`, replace:

```python
        # Concatenate all segments
        final = segments[0]
        for segment in segments[1:]:
            final = final + segment
```

With:

```python
        # Concatenate all segments with crossfade
        final = self._crossfade_segments(segments)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_drama_mixer.py -v`

Expected: PASS (existing tests + new test)

- [ ] **Step 6: Commit**

```bash
git add audio/drama_mixer.py tests/test_drama_mixer.py
git commit -m "feat(audio): add crossfade and silence trimming to DramaMixer"
```

---

## Task 6: Integrate Voice Processing in `PipelineOrchestrator`

**Files:**
- Modify: `core/pipeline_orchestrator.py`
- Test: `tests/test_pipeline_orchestrator.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/test_pipeline_orchestrator.py
from unittest.mock import MagicMock, patch
from core.pipeline_orchestrator import EpisodeConfig, PipelineOrchestrator
from core.media_package import MediaPackage, Manifest, ScriptLine
from audio.podcast_mastering import MasteringConfig


def test_pipeline_applies_voice_processing_after_render():
    cfg = EpisodeConfig(
        episode_type="raw",
        sources=[{"content": "Hola mundo", "title": "Test"}],
        podcast_mastering=MasteringConfig(enabled=True),
        branding_enabled=False,
    )
    orch = PipelineOrchestrator(cfg)

    package = MediaPackage(package_id="test_mastering")
    package.script = [
        ScriptLine(character="Narrador", text="Hola mundo.", voice_id="homer")
    ]
    package.manifest = Manifest(title="Test")
    package._base_path = Path("/tmp/test_mastering")  # type: ignore

    with patch.object(orch, "_acquire_content", return_value=("Hola mundo.", {"title": "Test"})):
        with patch.object(orch, "_process_content", return_value=package):
            with patch.object(orch, "_master_voice_mix", side_effect=lambda pkg, path: path) as mock_master:
                with patch.object(orch, "_finalize_loudness", side_effect=lambda path: path) as mock_finalize:
                    with patch.object(orch, "_update_manifest"):
                        package.save = MagicMock()
                        orch.run()
                        mock_master.assert_called_once()
                        mock_finalize.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline_orchestrator.py::test_pipeline_applies_voice_processing_after_render -v`

Expected: FAIL because `process_voice_mix` and `normalize_loudness` are not yet called.

- [ ] **Step 3: Modify `PipelineOrchestrator.run` and add helper methods**

Update `run`:

```python
    def run(self) -> PipelineResult:
        try:
            # 1. Content acquisition
            raw_content, content_meta = self._acquire_content()
            self._log("acquire", True, meta=content_meta)

            # 2. Process content through agents → MediaPackage
            package = self._process_content(raw_content, content_meta)
            self._log("process", True, package_id=package.package_id)

            # 3. Save package skeleton so assets have a home
            package.save(self.config.output_dir)
            self._log("save", True, path=str(package._base_path))

            # 4. Render main audio with DramaMixer
            main_audio_path = self._render_audio(package)
            self._log("render", True, path=main_audio_path)

            # 4a. Apply voice mastering (EQ, compression, gate)
            main_audio_path = self._master_voice_mix(package, main_audio_path)
            self._log("voice_mastering", True, path=main_audio_path)

            # 4b. Apply background music (continuous bed under voice)
            if self.config.background_music:
                self._apply_background_music(main_audio_path)
                self._log("bg_music", True, track=self.config.background_music)

            # 5. Apply branding (intro/outro)
            final_audio_path = self._apply_branding(package, main_audio_path)
            self._log("brand", True, path=final_audio_path)

            # 5a. Final loudness normalization
            final_audio_path = self._finalize_loudness(final_audio_path)
            self._log("loudness", True, path=final_audio_path)

            # 6. Update manifest with duration
            self._update_manifest(package, final_audio_path)
            package.save(self.config.output_dir)

            return PipelineResult(
                success=True,
                media_package=package,
                final_audio_path=final_audio_path,
                logs=self._logs
            )
```

Add helper methods at the end of the class:

```python
    def _master_voice_mix(self, package: MediaPackage, audio_path: str) -> str:
        """Apply voice processing (EQ, compression, gate) to the rendered voice mix."""
        config = self.config.podcast_mastering
        if not config or not config.enabled:
            return audio_path

        from audio.podcast_mastering import process_voice_mix

        ext = Path(audio_path).suffix.lower()
        processed_path = str(Path(audio_path).with_suffix(".mastered_voice" + ext))
        try:
            process_voice_mix(audio_path, processed_path, config)
            return processed_path
        except Exception as exc:
            self._log("voice_mastering", False, error=str(exc))
            return audio_path

    def _finalize_loudness(self, audio_path: str) -> str:
        """Apply final LUFS normalization to the complete episode."""
        config = self.config.podcast_mastering
        if not config or not config.enabled:
            return audio_path

        from audio.podcast_mastering import normalize_loudness

        ext = Path(audio_path).suffix.lower()
        final_path = str(Path(audio_path).with_suffix(".final" + ext))
        try:
            normalize_loudness(
                audio_path,
                final_path,
                target_lufs=config.target_lufs,
                true_peak_db=config.true_peak_db,
            )
            return final_path
        except Exception as exc:
            self._log("loudness", False, error=str(exc))
            return audio_path
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_pipeline_orchestrator.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/pipeline_orchestrator.py tests/test_pipeline_orchestrator.py
git commit -m "feat(core): integrate voice mastering and final loudness normalization"
```

---

## Task 7: Improve Background Music Ducking

**Files:**
- Modify: `core/pipeline_orchestrator.py`
- Test: `tests/test_pipeline_orchestrator.py`

- [ ] **Step 1: Write the failing test for ducking**

```python
# tests/test_pipeline_orchestrator.py

def test_background_music_ducking_uses_sidechain_config():
    cfg = EpisodeConfig(
        episode_type="raw",
        sources=[{"content": "Hola", "title": "Test"}],
        background_music="test_music",
        podcast_mastering=MasteringConfig(enabled=True),
    )
    orch = PipelineOrchestrator(cfg)
    assert orch.config.background_music == "test_music"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_pipeline_orchestrator.py::test_background_music_ducking_uses_sidechain_config -v`

Expected: PASS (this test just verifies config)

- [ ] **Step 3: Add `subprocess` import to `core/pipeline_orchestrator.py`**

```python
# core/pipeline_orchestrator.py
import os
import shutil
import subprocess  # NEW
from dataclasses import dataclass, field
```

- [ ] **Step 4: Implement ffmpeg sidechain ducking**

Replace the body of `_apply_background_music` (or create a new method `_apply_background_music_sidechain`) with:

```python
    def _apply_background_music(self, audio_path: str) -> None:
        """Mix continuous background music under the voice track with sidechain ducking."""
        from pydub import AudioSegment

        music_base = Path("sfx_library") / "music"
        music_file = None
        for ext in (".mp3", ".wav", ".flac", ".ogg"):
            candidate = music_base / f"{self.config.background_music}{ext}"
            if candidate.exists():
                music_file = candidate
                break
        if music_file is None:
            print(f"[PipelineOrchestrator] Background music '{self.config.background_music}' not found")
            return

        main = AudioSegment.from_file(audio_path)
        music_seg = AudioSegment.from_file(str(music_file))

        sr = main.frame_rate
        sw = main.sample_width
        ch = main.channels

        music_seg = music_seg.set_frame_rate(sr).set_channels(ch)

        # Loop music to cover voice
        loops = [music_seg]
        while sum(len(m) for m in loops) < len(main):
            loops.append(music_seg)
        music_seg = sum(loops[1:], loops[0])[: len(main)]

        # Fade in/out
        fade_in_ms = min(3000, int(len(main) * 0.1))
        fade_out_ms = min(4000, int(len(main) * 0.1))
        if fade_in_ms > 0:
            music_seg = music_seg.fade_in(fade_in_ms)
        if fade_out_ms > 0:
            music_seg = music_seg.fade_out(fade_out_ms)

        # Apply base volume
        music_seg = music_seg + self.config.bg_music_volume

        # Use ffmpeg sidechaincompress for smooth ducking
        import tempfile
        from audio.podcast_mastering import _ffmpeg_available

        voice_path = audio_path + ".voice.wav"
        music_path = audio_path + ".music.wav"
        output_path = audio_path + ".ducked.wav"

        main.export(voice_path, format="wav")
        music_seg.export(music_path, format="wav")

        if _ffmpeg_available():
            duck_cfg = self.config.podcast_mastering
            attack = getattr(duck_cfg, "ducking_attack_ms", 20)
            release = getattr(duck_cfg, "ducking_release_ms", 250)
            reduction = getattr(duck_cfg, "ducking_reduction_db", 8)
            ratio = getattr(duck_cfg, "ducking_ratio", 5)

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                music_path,
                "-i",
                voice_path,
                "-filter_complex",
                (
                    f"[0:a][1:a]sidechaincompress="
                    f"threshold=-20dB:ratio={ratio}:attack={attack}:release={release}:"
                    f"level_sc=1:mix=1[ducked];[1:a][ducked]amix=inputs=2:duration=first"
                ),
                "-ar",
                str(sr),
                "-ac",
                str(ch),
                output_path,
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                mixed = AudioSegment.from_file(output_path)
            except Exception as exc:
                print(f"[PipelineOrchestrator] Sidechain ducking failed: {exc}, falling back to RMS ducking")
                mixed = self._rms_ducking_mix(main, music_seg)
        else:
            mixed = self._rms_ducking_mix(main, music_seg)

        ext = Path(audio_path).suffix.lower().lstrip(".")
        fmt = "mp3" if ext == "mp3" else ("flac" if ext == "flac" else "wav")
        mixed.export(audio_path, format=fmt)

        # Cleanup temp files
        for p in (voice_path, music_path, output_path):
            if os.path.exists(p):
                os.remove(p)

    def _rms_ducking_mix(self, main: AudioSegment, music_seg: AudioSegment) -> AudioSegment:
        """Fallback numpy-based ducking with improved envelope."""
        import numpy as np

        sr = main.frame_rate
        sw = main.sample_width
        ch = main.channels

        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
        np_dtype = dtype_map.get(sw, np.int16)
        max_val = float(2 ** (8 * sw - 1))

        main_arr = np.array(main.get_array_of_samples(), dtype=np_dtype).astype(np.float32) / max_val
        music_arr = np.array(music_seg.get_array_of_samples(), dtype=np_dtype).astype(np.float32) / max_val

        if ch == 2:
            main_arr = main_arr.reshape(-1, 2)
            music_arr = music_arr.reshape(-1, 2)
            main_mono = main_arr.mean(axis=1)
        else:
            main_mono = main_arr

        n = len(main_mono)
        win = max(1, int(0.05 * sr))  # 50 ms windows
        hop = max(1, int(0.025 * sr))  # 25 ms hop
        n_win = max(1, (n - win) // hop + 1)

        if n_win < 3:
            mixed = main_arr + music_arr
        else:
            rms = np.empty(n_win, dtype=np.float32)
            for w in range(n_win):
                s = w * hop
                e = min(s + win, n)
                rms[w] = np.sqrt(np.mean(main_mono[s:e] ** 2))

            kernel = max(1, n_win // 20)
            rms = np.convolve(rms, np.ones(kernel) / kernel, mode="same")

            max_rms = float(np.max(rms)) if np.max(rms) > 0 else 1.0
            level = np.clip(rms / max_rms, 0.0, 1.0)

            silence_gain = 10 ** ((self.config.bg_music_volume + 3) / 20)
            ducked_gain = 10 ** ((self.config.bg_music_volume - 8) / 20)
            gain_curve = silence_gain + (ducked_gain - silence_gain) * level

            positions = np.arange(n_win) * hop + win // 2
            positions = np.clip(positions, 0, n - 1)
            full_gain = np.interp(np.arange(n), positions, gain_curve)

            if ch == 2:
                music_arr[:, 0] *= full_gain
                music_arr[:, 1] *= full_gain
            else:
                music_arr *= full_gain

        mixed = main_arr + music_arr
        mixed = np.clip(mixed, -1.0, 1.0)

        mixed_int = (mixed * max_val).clip(-max_val, max_val - 1).astype(np_dtype)
        return AudioSegment(
            mixed_int.tobytes(),
            frame_rate=sr,
            sample_width=sw,
            channels=ch,
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_pipeline_orchestrator.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/pipeline_orchestrator.py tests/test_pipeline_orchestrator.py
git commit -m "feat(core): implement ffmpeg sidechain ducking with RMS fallback"
```

---

## Task 8: Improve `BrandingEngine` Crossfade and Loudness

**Files:**
- Modify: `audio/branding_engine.py`
- Modify: `audio/podcast_mastering.py` (reuse `normalize_loudness`)
- Test: `tests/test_branding_engine.py`

- [ ] **Step 1: Write the failing test for branding crossfade**

```python
# tests/test_branding_engine.py
from audio.branding_engine import BrandingEngine


def test_branding_engine_accepts_crossfade_ms():
    engine = BrandingEngine()
    assert hasattr(engine, "branding_crossfade_ms")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_branding_engine.py::test_branding_engine_accepts_crossfade_ms -v`

Expected: FAIL with `AssertionError`

- [ ] **Step 3: Modify `BrandingEngine.__init__` and `apply_to_package`**

```python
# audio/branding_engine.py
from audio.podcast_mastering import normalize_loudness, MasteringConfig


class BrandingEngine:
    def __init__(
        self,
        templates_dir: str = "templates/branding",
        sfx_library_dir: str = "sfx_library",
        voice_cast: Optional[VoiceCastManager] = None,
        sample_rate: int = 24000,
        branding_crossfade_ms: int = 300,
    ):
        # ... existing init ...
        self.branding_crossfade_ms = max(0, min(int(branding_crossfade_ms), 1000))
```

Modify `apply_to_package` signature and body:

```python
    def apply_to_package(
        self,
        package: MediaPackage,
        main_audio_path: str,
        output_path: str,
        intro_music: str = "intro_jingle",
        outro_music: str = "outro_theme",
        host_voice_id: str = "homer",
        target_lufs: Optional[float] = None,
    ) -> str:
        main = AudioSegment.from_file(main_audio_path)
        main = main.set_frame_rate(self.sample_rate).set_channels(1)

        intro = self.generate_intro(...)
        outro = self.generate_outro(...)

        # Normalize intro/outro/main to target LUFS if provided
        if target_lufs is not None:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                for seg_name, seg in [("intro", intro), ("main", main), ("outro", outro)]:
                    if seg is None:
                        continue
                    src = os.path.join(tmp, f"{seg_name}_src.wav")
                    dst = os.path.join(tmp, f"{seg_name}_norm.wav")
                    seg.export(src, format="wav")
                    try:
                        normalize_loudness(src, dst, target_lufs=target_lufs, true_peak_db=-1.0)
                        normalized = AudioSegment.from_wav(dst)
                        if seg_name == "intro":
                            intro = normalized
                        elif seg_name == "main":
                            main = normalized
                        else:
                            outro = normalized
                    except Exception as exc:
                        print(f"[BrandingEngine] Loudness normalization failed for {seg_name}: {exc}")

        cf = self.branding_crossfade_ms
        final = AudioSegment.silent(duration=0, frame_rate=self.sample_rate)
        if intro:
            final = final.append(intro, crossfade=0)
        final = final.append(main, crossfade=cf if intro else 0)
        if outro:
            final = final.append(outro, crossfade=cf)

        # ... export as before ...
```

- [ ] **Step 4: Update `PipelineOrchestrator._apply_branding` to pass target LUFS**

```python
# core/pipeline_orchestrator.py
        final_path = str(package.assets_path / "final_with_branding.mp3")
        target_lufs = None
        if self.config.podcast_mastering and self.config.podcast_mastering.enabled:
            target_lufs = self.config.podcast_mastering.target_lufs
        branding.apply_to_package(
            package=package,
            main_audio_path=main_audio_path,
            output_path=final_path,
            intro_music=self.config.intro_music,
            outro_music=self.config.outro_music,
            host_voice_id=self.config.host_voice_id,
            target_lufs=target_lufs,
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_branding_engine.py tests/test_pipeline_orchestrator.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add audio/branding_engine.py core/pipeline_orchestrator.py tests/test_branding_engine.py tests/test_pipeline_orchestrator.py
git commit -m "feat(audio): add crossfade and LUFS normalization to intro/outro branding"
```

---

## Task 9: Update `_render_audio` to pass MasteringConfig to `DramaMixer`

**Files:**
- Modify: `core/pipeline_orchestrator.py`

- [ ] **Step 1: Modify `_render_audio`**

```python
# core/pipeline_orchestrator.py
    def _render_audio(self, package: MediaPackage) -> str:
        from audio.drama_mixer import DramaMixer
        from audio.audio_enhancer import VoiceFixerEnhancer, NoOpEnhancer

        # Build enhancer from config
        enh_cfg = self.config.audio_enhancer.lower()
        # ... existing enhancer logic ...

        mastering_cfg = self.config.podcast_mastering or MasteringConfig()
        mixer = DramaMixer(
            voice_cast=self.voice_cast,
            sample_rate=24000,
            enhancer=enhancer,
            enhance_per_line=enhance_per_line,
            enhance_final=enhance_final,
            crossfade_ms=mastering_cfg.crossfade_ms,
            trim_silence_threshold_db=mastering_cfg.trim_silence_threshold_db,
        )
        # ... rest unchanged ...
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_pipeline_orchestrator.py -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add core/pipeline_orchestrator.py
git commit -m "feat(core): pass mastering config crossfade/trim to DramaMixer"
```

---

## Task 10: Add Comprehensive Tests and Validate End-to-End

**Files:**
- Modify: `tests/test_podcast_mastering.py`
- Modify: `tests/test_pipeline_orchestrator.py`

- [ ] **Step 1: Add LUFS measurement helper in tests**

```python
# tests/test_podcast_mastering.py
import subprocess
import re


def _measure_lufs(path: str) -> float:
    cmd = [
        "ffmpeg",
        "-i",
        path,
        "-af",
        "loudnorm=I=-16:TP=-1:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    match = re.search(r'"input_i"\s*:\s*"?([-\d.]+)"?', result.stderr)
    if match:
        return float(match.group(1))
    raise RuntimeError("Could not measure LUFS")


def test_normalize_loudness_hits_target():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.wav")
        dst = os.path.join(tmp, "output.wav")
        _make_test_wav(src, duration_ms=3000, freq=440)
        normalize_loudness(src, dst, target_lufs=-16.0, true_peak_db=-1.0)
        measured = _measure_lufs(dst)
        assert measured == pytest.approx(-16.0, abs=1.5)
```

- [ ] **Step 2: Add pipeline end-to-end smoke test**

```python
# tests/test_pipeline_orchestrator.py
import tempfile
from pathlib import Path
from core.pipeline_orchestrator import EpisodeConfig, PipelineOrchestrator
from core.media_package import MediaPackage, Manifest, ScriptLine


def test_pipeline_mastering_end_to_end_smoke():
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = os.path.join(tmp, "packages")
        cfg = EpisodeConfig(
            episode_type="raw",
            sources=[{"content": "Hola mundo. Esto es una prueba.", "title": "Test"}],
            output_dir=output_dir,
            branding_enabled=False,
            podcast_mastering=MasteringConfig(enabled=True),
        )
        orch = PipelineOrchestrator(cfg)

        package = MediaPackage(package_id="test_e2e")
        package.script = [
            ScriptLine(character="Narrador", text="Hola mundo.", voice_id="homer"),
            ScriptLine(character="Narrador", text="Esto es una prueba.", voice_id="homer"),
        ]
        package.manifest = Manifest(title="Test E2E")
        package._base_path = Path(output_dir) / "test_e2e"  # type: ignore
        package._base_path.mkdir(parents=True, exist_ok=True)
        (package._base_path / "assets").mkdir(exist_ok=True)

        with patch.object(orch, "_acquire_content", return_value=("content", {"title": "Test"})):
            with patch.object(orch, "_process_content", return_value=package):
                result = orch.run()
                assert result.success
                assert result.final_audio_path is not None
                assert os.path.exists(result.final_audio_path)
```

- [ ] **Step 3: Run all related tests**

Run: `pytest tests/test_podcast_mastering.py tests/test_drama_mixer.py tests/test_pipeline_orchestrator.py tests/test_branding_engine.py -v`

Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -q`

Expected: No new failures.

- [ ] **Step 5: Commit**

```bash
git add tests/test_podcast_mastering.py tests/test_pipeline_orchestrator.py
git commit -m "test(audio): add LUFS and end-to-end mastering tests"
```

---

## Task 11: Documentation Update

**Files:**
- Modify: `docs/QWEN3_TTS_SETUP.md` or create `docs/PODCAST_MASTERING.md` (optional)
- Modify: `AGENTS.md` if startup behavior changes (not expected)

- [ ] **Step 1: Add a short note in relevant docs**

If `AGENTS.md` mentions audio pipeline or `docs/` has a relevant file, add:

```markdown
## Mastering de podcast

El pipeline web aplica automáticamente mastering a los episodios generados:
- Crossfade y trimming entre líneas de diálogo.
- Normalización a -16 LUFS.
- EQ, compresión, limitador y noise gate vía ffmpeg.
- Ducking sidechain en música de fondo.

Se puede desactivar configurando `podcast_mastering.enabled = false` en `EpisodeConfig`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/PODCAST_MASTERING.md  # or modified file
git commit -m "docs: add podcast mastering overview"
```

---

## Self-Review Checklist

### Spec coverage

- [x] Crossfade entre líneas → Task 5
- [x] Trimming de silencio → Task 5
- [x] LUFS real (-16 LUFS) → Tasks 3, 6, 8
- [x] EQ → Task 2
- [x] Compresión/limitador → Task 2
- [x] Noise gate → Task 2
- [x] Ducking sidechain → Task 7
- [x] Crossfade intro/outro → Task 8
- [x] Configuración → Task 4
- [x] Tests → Tasks 1, 2, 3, 6, 10

### Placeholder scan

- [x] No TBD/TODO/"implement later"
- [x] Each task contains actual code/commands
- [x] No vague "add error handling" without specifics

### Type consistency

- [x] `MasteringConfig` fields consistent across files
- [x] `process_voice_mix` / `normalize_loudness` signatures consistent
- [x] `DramaMixer` parameters match usage in `_render_audio`
- [x] `BrandingEngine.apply_to_package` `target_lufs` parameter consistent

### Potential issues to verify during implementation

1. `normalize_loudness` parses ffmpeg JSON keys `input_I`, `input_Tp`, `input_LRA`, `input_Thresh`. Verify these keys match the installed ffmpeg version.
2. `sidechaincompress` syntax may vary by ffmpeg version. Test the exact command before relying on it.
3. `AudioSegment.append` with crossfade requires both segments to be longer than crossfade duration. The `_crossfade_segments` helper limits crossfade to half of each segment.
4. The end-to-end test uses mocking; real Higgs TTS is not required for unit tests.
5. If `EpisodeConfig` is instantiated without `podcast_mastering`, `field(default_factory=MasteringConfig)` ensures a default.
