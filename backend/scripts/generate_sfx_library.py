"""
Generate basic synthetic SFX and music for the Media Automation Platform demo.

Run this once to populate sfx_library/ with placeholder sounds.
Replace these with real assets for production.
"""

import os
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import soundfile as sf


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def generate_sine_tone(freq: float, duration_s: float, sample_rate: int = 24000, volume: float = 0.3):
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    wave = volume * np.sin(2 * np.pi * freq * t)
    # Apply envelope
    attack = int(0.05 * sample_rate)
    release = int(0.1 * sample_rate)
    envelope = np.ones_like(wave)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    return wave * envelope


def generate_jingle(output_path: str, sample_rate: int = 24000):
    """Generate a simple 5-tone major arpeggio jingle."""
    base_freq = 440  # A4
    freqs = [base_freq, base_freq * 5/4, base_freq * 3/2, base_freq * 2, base_freq * 5/2]
    tones = [generate_sine_tone(f, 0.25, sample_rate, 0.25) for f in freqs]
    # Add slight silence between tones
    silence = np.zeros(int(sample_rate * 0.05))
    parts = []
    for tone in tones:
        parts.extend([tone, silence])
    jingle = np.concatenate(parts)
    sf.write(output_path, jingle, sample_rate)


def generate_outro_theme(output_path: str, sample_rate: int = 24000):
    """Generate a calm descending outro theme."""
    base_freq = 523.25  # C5
    freqs = [base_freq, base_freq * 4/5, base_freq * 2/3, base_freq * 3/5, base_freq / 2]
    tones = [generate_sine_tone(f, 0.4, sample_rate, 0.2) for f in freqs]
    silence = np.zeros(int(sample_rate * 0.1))
    parts = []
    for tone in tones:
        parts.extend([tone, silence])
    theme = np.concatenate(parts)
    sf.write(output_path, theme, sample_rate)


def generate_forest_ambience(output_path: str, duration_s: float = 10.0, sample_rate: int = 24000):
    """Generate soft pink-noise-like forest ambience."""
    samples = int(sample_rate * duration_s)
    # Pink noise approximation
    white = np.random.randn(samples)
    pink = np.cumsum(white)
    pink = pink / np.max(np.abs(pink))
    # Low-pass filter effect via moving average
    window = 50
    pink_smooth = np.convolve(pink, np.ones(window)/window, mode='same')
    pink_smooth = pink_smooth * 0.15
    # Fade in/out
    fade = int(0.5 * sample_rate)
    pink_smooth[:fade] *= np.linspace(0, 1, fade)
    pink_smooth[-fade:] *= np.linspace(1, 0, fade)
    sf.write(output_path, pink_smooth, sample_rate)


def generate_rain_ambience(output_path: str, duration_s: float = 10.0, sample_rate: int = 24000):
    """Generate rain-like white noise."""
    samples = int(sample_rate * duration_s)
    noise = np.random.randn(samples) * 0.1
    fade = int(0.5 * sample_rate)
    noise[:fade] *= np.linspace(0, 1, fade)
    noise[-fade:] *= np.linspace(1, 0, fade)
    sf.write(output_path, noise, sample_rate)


def main():
    base = Path("sfx_library")
    ensure_dir(base / "music")
    ensure_dir(base / "ambience")
    ensure_dir(base / "impacts")

    print("Generating placeholder SFX library...")
    generate_jingle(str(base / "music" / "intro_jingle.wav"))
    print("  → intro_jingle.wav")

    generate_outro_theme(str(base / "music" / "outro_theme.wav"))
    print("  → outro_theme.wav")

    generate_forest_ambience(str(base / "ambience" / "forest.wav"), duration_s=20.0)
    print("  → forest.wav")

    generate_rain_ambience(str(base / "ambience" / "rain.wav"), duration_s=20.0)
    print("  → rain.wav")

    # Placeholder applause
    samples = int(24000 * 2.0)
    noise = np.random.randn(samples) * 0.2
    fade = int(0.3 * 24000)
    noise[:fade] *= np.linspace(0, 1, fade)
    noise[-fade:] *= np.linspace(1, 0, fade)
    sf.write(str(base / "impacts" / "applause.wav"), noise, 24000)
    print("  → applause.wav")

    print("\nSFX library ready. Replace these with real assets for production.")


if __name__ == "__main__":
    main()
