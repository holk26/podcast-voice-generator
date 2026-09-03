"""Tests del validador de consistencia por chunk.

Usan tonos sintéticos (soundfile) y un embedder mockeado, así no requieren
pesos de resemblyzer ni GPU.
"""
import math
from pathlib import Path

import numpy as np
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
    params = dict(
        max_attempts=3,
        sim_threshold=0.80,
        pitch_tolerance=0.15,
        speed_tolerance=0.20,
        lufs_tolerance=6.0,
        emotion_relax=1.5,
    )
    params.update(cfg_overrides)
    cfg = QualityConfig(**params)
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
    v.accept(a, extract_emotion("<|emotion:neutral|> Texto."))
    # Mismo salto de pitch (+100%) y emoción distinta: 0.15*1.5=0.225 < 1.0 → falla igual
    b = _score(v, _tone(tmp_path / "b.wav", 240.0), "<|emotion:fear|> Texto.")
    assert not b.passed
    # Salto pequeño (20%) con emoción distinta: > 0.15 estricto, <= 0.225 relajado → pasa
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


def test_synthesize_clone_best_of_n(tmp_path, monkeypatch):
    """Con un motor que desafina 2 veces y acierta a la 3ª, se acepta el 3er intento."""
    import worker.tts_local as tts_local
    from worker import tts_quality

    attempts = {"n": 0}

    class _FakeEngine:
        def synthesize(self, text, voice, output_path):
            attempts["n"] += 1
            freq = 240.0 if attempts["n"] < 3 else 120.0
            _tone(Path(output_path), freq)

    monkeypatch.setattr(tts_local, "_get_engine", lambda name: _FakeEngine())
    monkeypatch.setenv("TTS_QUALITY_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("TTS_QUALITY_SIM_THRESHOLD", "0.0")
    monkeypatch.setattr(
        tts_local,
        "_parse_clone_voice_id",
        lambda voice_id: tts_local.Voice(
            id=voice_id, name="fake", type="cloned", engine="higgs", language="es",
            reference_path=str(_tone(tmp_path / "ref.wav", 120.0)),
        ),
    )

    orig_init = tts_quality.ChunkValidator.__init__

    def fake_init(self, reference_path, config=None, embedder=None):
        orig_init(self, reference_path, config=config, embedder=_FakeEmbedder())

    monkeypatch.setattr(tts_quality.ChunkValidator, "__init__", fake_init)

    text = "Una frase corta de prueba. Otra frase más."
    out = tmp_path / "out.wav"
    tts_local.synthesize_clone(text, "clone:fake", str(out))
    assert attempts["n"] == 3
    assert out.exists()
