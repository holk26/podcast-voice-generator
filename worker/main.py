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


gui_instance = None


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import atexit
    import uvicorn
    from threading import Thread

    # Al salir (incluido SIGINT/SIGTERM con apagado graceful de uvicorn),
    # descargar los motores TTS de la GPU. Si no, los subprocesos núcleo de
    # vLLM quedan huérfanos y siguen ocupando VRAM.
    from worker.tts_local import release_engine

    atexit.register(release_engine)

    if os.getenv("WORKER_GUI", "") == "1":
        from worker.gui import WorkerGui, GuiLogHandler
        gui_instance = WorkerGui(on_reconnect=lambda: logging.info("Reconectar solicitado desde GUI"))
        gui_instance.start()
        gui_instance.update_status("Conectando al backend...")
        gui_handler = GuiLogHandler(gui_instance)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S"))
        logging.getLogger().addHandler(gui_handler)

    worker_thread = Thread(target=run_loop, daemon=True)
    worker_thread.start()

    port = int(os.getenv("WORKER_PORT", WORKER_PORT))
    uvicorn.run(app, host="0.0.0.0", port=port)
