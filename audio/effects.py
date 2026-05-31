import numpy as np


def fade_in(audio: np.ndarray, sample_rate: int, duration_ms: int) -> np.ndarray:
    samples = int(sample_rate * duration_ms / 1000)
    if samples <= 0:
        return audio
    if samples > len(audio):
        samples = len(audio)
    fade_curve = np.linspace(0.0, 1.0, samples)
    result = audio.copy()
    result[:samples] *= fade_curve
    return result


def fade_out(audio: np.ndarray, sample_rate: int, duration_ms: int) -> np.ndarray:
    samples = int(sample_rate * duration_ms / 1000)
    if samples <= 0:
        return audio
    if samples > len(audio):
        samples = len(audio)
    fade_curve = np.linspace(1.0, 0.0, samples)
    result = audio.copy()
    result[-samples:] *= fade_curve
    return result


def add_silence(audio: np.ndarray, sample_rate: int, duration_ms: int) -> np.ndarray:
    silence_samples = int(sample_rate * duration_ms / 1000)
    silence = np.zeros(silence_samples, dtype=audio.dtype)
    return np.concatenate([audio, silence])
