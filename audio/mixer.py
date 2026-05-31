import numpy as np
from audio.normalizer import db_to_linear


def mix_with_background(voice: np.ndarray, background: np.ndarray, bg_volume_db: float = -18.0) -> np.ndarray:
    bg_gain = db_to_linear(bg_volume_db)
    bg_adjusted = background * bg_gain
    if len(bg_adjusted) < len(voice):
        repeats = int(np.ceil(len(voice) / len(bg_adjusted)))
        bg_adjusted = np.tile(bg_adjusted, repeats)
    bg_adjusted = bg_adjusted[:len(voice)]
    mixed = voice + bg_adjusted
    return np.clip(mixed, -1.0, 1.0)


def apply_ducking(background: np.ndarray, duck_db: float = 12.0) -> np.ndarray:
    duck_gain = db_to_linear(-duck_db)
    return background * duck_gain
