"""Normaliza todos los audios de referencia clonada a 24 kHz mono WAV."""
import subprocess
import sys
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
    failed = []
    for entry in sorted(CLONES_DIR.iterdir()):
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        tmp = entry.with_suffix(".norm.wav")
        try:
            normalize(entry, tmp)
            tmp.replace(entry)
            print(f"Normalized {entry.name}")
        except subprocess.CalledProcessError as e:
            failed.append((entry.name, e))
            print(f"Failed to normalize {entry.name}: {e}", file=sys.stderr)
        finally:
            tmp.unlink(missing_ok=True)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
