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
from dataclasses import dataclass
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

    def accept(self, score: ChunkScore, emotion: str | None = None) -> None:
        """Fija el chunk aceptado como referencia para el siguiente."""
        self._prev = score
        self._prev_emotion = emotion
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
