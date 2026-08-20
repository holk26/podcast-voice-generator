"""Cliente HTTP para comunicarse con el backend.

El worker no accede directamente a la base de datos; consume los endpoints
exclusivos de worker (`/api/worker/*`) usando un token estático compartido.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import requests

from shared.schemas import WorkerJob

logger = logging.getLogger(__name__)

API_BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WORKER_TOKEN}",
    }


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def get_next_job() -> Optional[WorkerJob]:
    """Reclama el siguiente episodio pendiente del backend.

    Retorna None si no hay trabajos disponibles.
    """
    req = urllib.request.Request(
        _url("/api/worker/jobs/next"),
        headers=_headers(),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 204:
                return None
            return WorkerJob(**json.load(resp))
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return None
        logger.error(f"Error fetching next job: {e.code} {e.reason}")
        raise
    except Exception as e:
        logger.error(f"Error fetching next job: {e}")
        raise


def upload_audio(episode_id: int, file_path: Path) -> str:
    """Sube el archivo de audio al backend y devuelve la URL pública del recurso."""
    url = _url(f"/api/worker/jobs/{episode_id}/upload")
    headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
    with open(file_path, "rb") as f:
        files = {"audio": (file_path.name, f, "audio/mpeg")}
        resp = requests.post(url, headers=headers, files=files, timeout=300)
    resp.raise_for_status()
    return resp.json()["audio_url"]


def complete_job(episode_id: int, audio_url: str) -> None:
    req = urllib.request.Request(
        _url(f"/api/worker/jobs/{episode_id}/complete"),
        data=json.dumps({"audio_url": audio_url}).encode(),
        headers=_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"Unexpected status completing job: {resp.status}")


def fail_job(episode_id: int, error: str) -> None:
    req = urllib.request.Request(
        _url(f"/api/worker/jobs/{episode_id}/fail"),
        data=json.dumps({"error": error}).encode(),
        headers=_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"Unexpected status failing job: {resp.status}")


def run_autopilot_tick() -> list[str]:
    """Pide al backend que ejecute un tick del piloto automático.

    Retorna la lista de job_ids lanzados.
    """
    req = urllib.request.Request(
        _url("/api/channels/autopilot/tick"),
        data=b"{}",
        headers=_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp).get("launched", [])
    except urllib.error.HTTPError as e:
        logger.error(f"Autopilot tick failed: {e.code} {e.reason}")
        return []
    except Exception as e:
        logger.error(f"Autopilot tick failed: {e}")
        return []


def listen_sse():
    """Generador SSE que escucha eventos del backend.

    Reconecta automáticamente ante desconexiones. En producción el worker usa
    esto como disparador principal y recurre al polling si el SSE falla.
    """
    import urllib.request

    req = urllib.request.Request(
        _url("/api/worker/events"),
        headers=_headers(),
        method="GET",
    )
    while True:
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
        except Exception as e:
            logger.warning(f"SSE disconnected: {e}; will reconnect")
            yield {"type": "disconnected"}
