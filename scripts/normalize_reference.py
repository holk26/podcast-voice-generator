"""Normalize every cloned reference audio file to 24 kHz mono 16-bit WAV."""

import subprocess
from pathlib import Path

CLONES_DIR = Path(__file__).resolve().parent.parent / "voices" / "clones"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}


def normalize(path: Path, out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(path),
            "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
            str(out),
        ],
        check=True,
    )


def main() -> None:
    if not CLONES_DIR.is_dir():
        CLONES_DIR.mkdir(parents=True, exist_ok=True)
        return

    for entry in sorted(CLONES_DIR.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        tmp = entry.with_suffix(".norm.wav")
        normalize(entry, tmp)
        tmp.replace(entry)
        print(f"Normalized {entry.name}")


if __name__ == "__main__":
    main()
