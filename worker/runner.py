import os
import threading
import time
import logging
from datetime import datetime

import worker.client as client
from worker.handlers import handle_podcast_episode

logger = logging.getLogger(__name__)

# Intervalo entre heartbeats mientras se procesa un episodio. Debe ser
# claramente menor que WORKER_LEASE_MINUTES del backend (default 45 min).
HEARTBEAT_SECONDS = int(os.getenv("WORKER_HEARTBEAT_SECONDS", "300"))

# Hora local a la que se ejecuta la producción diaria de los canales en
# piloto automático (temporadas + guiones del día). Configurable por env.
AUTOPILOT_HOUR = int(os.getenv("AUTOPILOT_HOUR", "7"))

# Si UPLOAD_AUDIO=1 se sube el binario al backend por HTTP; de lo contrario se guarda localmente.
UPLOAD_AUDIO = os.getenv("UPLOAD_AUDIO", "0").lower() in ("1", "true", "yes")

# Intervalo de polling de respaldo cuando el SSE no está disponible.
POLL_BACKUP_SECONDS = int(os.getenv("POLL_BACKUP_SECONDS", "30"))


def _process_single_job() -> bool:
    """Procesa un único job pendiente. Retorna True si procesó algo."""
    job = client.get_next_job()
    if job is None:
        return False

    logger.info(f"Processing episode {job.episode_id}: {job.title}")
    # Heartbeats en segundo plano: renuevan el lease para que el backend
    # no reencole el episodio si la síntesis dura más que el lease.
    stop = threading.Event()

    def _heartbeat_loop():
        while not stop.wait(HEARTBEAT_SECONDS):
            client.send_heartbeat(job.episode_id)

    hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    hb_thread.start()
    try:
        output_path = handle_podcast_episode(job)
        if UPLOAD_AUDIO:
            audio_url = client.upload_audio(job.episode_id, output_path)
        else:
            audio_url = f"/outputs/{job.episode_id}/{output_path.name}"
        client.complete_job(job.episode_id, audio_url)
        logger.info(f"Episode {job.episode_id} completed -> {audio_url}")
        return True
    except Exception as e:
        logger.error(f"Episode {job.episode_id} failed: {e}")
        try:
            client.fail_job(job.episode_id, str(e)[:500])
        except Exception as e2:
            logger.error(f"Could not report failure for episode {job.episode_id}: {e2}")
        return True
    finally:
        stop.set()


def _drain_pending_jobs() -> None:
    """Procesa todos los jobs pendientes disponibles en una ráfaga."""
    while _process_single_job():
        pass


def _drain_safe() -> None:
    """Drenaje que no puede matar el hilo del loop: un fallo de red
    temporal del backend (502/DNS) se registra y se reintenta en el
    próximo ciclo en vez de terminar el thread de procesamiento."""
    try:
        _drain_pending_jobs()
    except Exception as e:
        logger.error(f"Drain de jobs falló (se reintenta en el próximo ciclo): {e}")


def _autopilot_due(last_run_date: str | None) -> bool:
    """True si hoy ya pasó la hora de ejecución y aún no se ha corrido hoy."""
    now = datetime.now()
    if now.hour < AUTOPILOT_HOUR:
        return False
    return last_run_date != now.date().isoformat()


def _run_autopilot(last_run_date: str | None) -> str | None:
    if not _autopilot_due(last_run_date):
        return last_run_date
    launched = client.run_autopilot_tick()
    for job_id in launched:
        logger.info(f"Autopilot daily run launched job {job_id}")
    return datetime.now().date().isoformat()


def run_loop():
    """Bucle principal del worker.

    Intenta mantener una conexión SSE con el backend para reaccionar en cuanto
    hay trabajo nuevo. Si el SSE falla, hace polling de respaldo. También
    ejecuta el autopilot diario.
    """
    last_run_date: str | None = None
    use_sse = True

    while True:
        try:
            last_run_date = _run_autopilot(last_run_date)
        except Exception as e:
            logger.error(f"Autopilot tick failed: {e}")

        _drain_safe()

        if use_sse:
            try:
                logger.info("Connecting to backend SSE stream...")
                for event in client.listen_sse():
                    if event.get("type") == "new_job":
                        _drain_safe()
                    elif event.get("type") == "disconnected":
                        raise ConnectionError("SSE disconnected")
                # Si el stream termina limpiamente, reconectamos
                continue
            except Exception as e:
                logger.warning(f"SSE error: {e}; falling back to polling")
                use_sse = False

        # Modo polling de respaldo
        time.sleep(POLL_BACKUP_SECONDS)
        _drain_safe()

        # Reintentar SSE periódicamente
        if int(time.time()) % 60 < POLL_BACKUP_SECONDS:
            use_sse = True
