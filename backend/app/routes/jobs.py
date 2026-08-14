import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.services.job_service import registry

router = APIRouter()


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
        while True:
            job = registry.get(job_id)
            if job is None:
                break
            events = job["events"]
            while sent < len(events):
                yield f"data: {json.dumps(events[sent])}\n\n"
                sent += 1
            if job["status"] != "running":
                payload = {
                    "step": "__status__",
                    "status": job["status"],
                    "error": job["error"],
                    "result": job["result"],
                }
                yield f"data: {json.dumps(payload)}\n\n"
                break
            time.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
