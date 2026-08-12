"""Configuration dataclass and conversion helpers for the podcast mastering chain."""

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

import numpy as np


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


def process_voice_mix(
    input_path: str,
    output_path: str,
    config: Optional[MasteringConfig] = None,
) -> str:
    """
    Apply EQ, compression, limiting and noise gate to a voice mix.
    Uses ffmpeg. If config.enabled is False, copies input to output.
    The output is forced to 24 kHz mono.
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
            f"agate=threshold={config.gate_threshold_db}dB:attack=10:release=250"
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
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        stderr_msg = exc.stderr.decode(errors="ignore") if exc.stderr else ""
        raise RuntimeError(f"ffmpeg mastering failed: {stderr_msg}") from exc
    return output_path


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

    target_lufs = float(np.clip(target_lufs, -23.0, -14.0))

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
    try:
        subprocess.run(apply_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        stderr_msg = exc.stderr.decode(errors="ignore") if exc.stderr else ""
        raise RuntimeError(f"ffmpeg loudnorm failed: {stderr_msg}") from exc
    return output_path
