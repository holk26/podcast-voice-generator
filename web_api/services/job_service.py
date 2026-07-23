"""Registro en memoria de trabajos CrewAI (plan/guion).

Los endpoints de generación lanzan el crew en un hilo y devuelven un job_id;
el frontend sigue el progreso en vivo vía SSE (/api/jobs/{id}/events) o
polling (/api/jobs/{id}).
"""

import threading
import time
import uuid

MAX_JOBS = 50
JOB_TTL_SECONDS = 3600


class JobRegistry:
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, detail: str = "") -> str:
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._gc()
            self._jobs[job_id] = {
                "id": job_id,
                "kind": kind,
                "detail": detail,
                "status": "running",  # running | done | error
                "events": [],
                "result": None,
                "error": None,
                "created_at": time.time(),
            }
        return job_id

    def emit(self, job_id: str, step: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["events"].append(
                    {"ts": time.time(), "step": step, "message": message}
                )

    def finish(self, job_id: str, result: dict | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["status"] = "done"
                job["result"] = result or {}

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["status"] = "error"
                job["error"] = error

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None

    def _gc(self) -> None:
        """Descarta jobs antiguos y limita el tamaño del registro."""
        now = time.time()
        stale = [
            jid
            for jid, j in self._jobs.items()
            if j["status"] != "running" and now - j["created_at"] > JOB_TTL_SECONDS
        ]
        for jid in stale:
            del self._jobs[jid]
        if len(self._jobs) >= MAX_JOBS:
            oldest = sorted(self._jobs, key=lambda j: self._jobs[j]["created_at"])
            for jid in oldest[: len(self._jobs) - MAX_JOBS + 1]:
                if self._jobs[jid]["status"] != "running":
                    del self._jobs[jid]


registry = JobRegistry()
