"""Configuration dataclass and conversion helpers for the podcast mastering chain."""

import math
import subprocess
from dataclasses import dataclass


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
    except (FileNotFoundError, subprocess.CalledProcessError, PermissionError):
        return False
