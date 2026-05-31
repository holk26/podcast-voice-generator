import os
import re


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def sanitize_filename(name: str, max_length: int = 100) -> str:
    sanitized = re.sub(r'[^\w\s-]', '_', name).strip()
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    return sanitized[:max_length]


def get_project_path(base_dir: str, project_name: str) -> str:
    safe_name = sanitize_filename(project_name)
    return os.path.join(base_dir, safe_name)


def validate_audio_file(path: str) -> bool:
    if not os.path.exists(path):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def get_file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024)
