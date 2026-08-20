import os
import logging
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde worker/.env sin depender del CWD.
load_dotenv(Path(__file__).with_name(".env"), override=False)

from fastapi import FastAPI
from worker.runner import run_loop
from backend.app.config import WORKER_PORT

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Podcast Worker")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from threading import Thread

    worker_thread = Thread(target=run_loop, daemon=True)
    worker_thread.start()

    port = int(os.getenv("WORKER_PORT", WORKER_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
