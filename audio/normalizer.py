import numpy as np


def db_to_linear(db: float) -> float:
    return 10 ** (db / 20.0)


def linear_to_db(value: float) -> float:
    return 20 * np.log10(max(abs(value), 1e-10))


def normalize_peak(audio: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    if len(audio) == 0:
        return audio
    peak = np.max(np.abs(audio))
    if peak == 0:
        return audio
    target_peak = db_to_linear(target_db)
    gain = target_peak / peak
    return audio * gain


def normalize_lufs(audio: np.ndarray, sample_rate: int, target_lufs: float = -14.0) -> np.ndarray:
    """Simple RMS-based approximation of LUFS normalization."""
    if len(audio) == 0:
        return audio
    rms = np.sqrt(np.mean(audio ** 2))
    if rms == 0:
        return audio
    target_rms = db_to_linear(target_lufs)
    gain = target_rms / rms
    return np.clip(audio * gain, -1.0, 1.0)
