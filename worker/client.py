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


MULTIPART_PART_SIZE = int(1.5 * 1024 * 1024)  # 1.5 MiB: cabe holgadamente bajo el límite del proxy
MULTIPART_THRESHOLD = MULTIPART_PART_SIZE


def _upload_part(episode_id: int, part_number: int, chunk: bytes) -> None:
    url = _url(f"/api/worker/jobs/{episode_id}/upload-part/{part_number}")
    headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
    files = {"audio": (f"part_{part_number:04d}", chunk, "application/octet-stream")}
    resp = requests.post(url, headers=headers, files=files, timeout=120)
    resp.raise_for_status()


def upload_audio(episode_id: int, file_path: Path) -> str:
    """Sube el archivo de audio al backend y devuelve la URL pública del recurso.

    Archivos pequeños suben en un único POST; los grandes (>= ~1.5 MiB) suben
    por partes (< 2 MiB cada una) y se ensamblan en el servidor, para evitar
    el límite de cuerpo del proxy intermedio.
    """
    headers = {"Authorization": f"Bearer {WORKER_TOKEN}"}
    file_size = os.path.getsize(file_path)

    if file_size < MULTIPART_THRESHOLD:
        url = _url(f"/api/worker/jobs/{episode_id}/upload")
        with open(file_path, "rb") as f:
            files = {"audio": (file_path.name, f, "audio/mpeg")}
            resp = requests.post(url, headers=headers, files=files, timeout=300)
        resp.raise_for_status()
        return resp.json()["audio_url"]

    total_parts = (file_size + MULTIPART_PART_SIZE - 1) // MULTIPART_PART_SIZE
    logger.info(f"Subiendo {file_path} ({file_size} bytes) en {total_parts} partes")
    with open(file_path, "rb") as f:
        for part_number in range(total_parts):
            chunk = f.read(MULTIPART_PART_SIZE)
            _upload_part(episode_id, part_number, chunk)

    url = _url(f"/api/worker/jobs/{episode_id}/assemble")
    resp = requests.post(
        url,
        headers={**headers, "Content-Type": "application/json"},
        json={"filename": file_path.name, "parts": total_parts},
        timeout=120,
    )
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


def send_heartbeat(episode_id: int) -> None:
    """Renueva el lease del episodio en running. Nunca lanza: es opcional."""
    try:
        req = urllib.request.Request(
            _url(f"/api/worker/jobs/{episode_id}/heartbeat"),
            data=b"",
            headers=_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"heartbeat status {resp.status}")
    except Exception as e:
        logger.debug(f"Heartbeat {episode_id} no enviado: {e}")


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
        _url("/api/worker/autopilot/tick"),
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
