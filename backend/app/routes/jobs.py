import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.services.job_service import registry

router = APIRouter()

# Segundos de silencio antes de enviar un heartbeat (comentario SSE) para que
# proxies como Cloudflare/nginx no corten conexiones idle durante fases largas.
HEARTBEAT_SECONDS = 15


@router.get("")
def list_jobs():
    """Jobs en curso (congreso CrewAI, síntesis TTS...)."""
    return registry.list_running()


@router.get("/{job_id}")
def get_job(job_id: str):
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/events")
def job_events(job_id: str):
    if registry.get(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    def event_generator():
        sent = 0
        last_yield = time.time()
        while True:
            job = registry.get(job_id)
            if job is None:
                break
            events = job["events"]
            emitted = False
            while sent < len(events):
                yield f"data: {json.dumps(events[sent])}\n\n"
                sent += 1
                emitted = True
                last_yield = time.time()
            if job["status"] != "running":
                payload = {
                    "step": "__status__",
                    "status": job["status"],
                    "error": job["error"],
                    "result": job["result"],
                }
                yield f"data: {json.dumps(payload)}\n\n"
                break
            # Heartbeat para que proxies (Cloudflare/nginx) no corten la conexión
            # durante fases largas sin eventos nuevos.
            if not emitted and time.time() - last_yield >= HEARTBEAT_SECONDS:
                yield ": ping\n\n"
                last_yield = time.time()
            time.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
