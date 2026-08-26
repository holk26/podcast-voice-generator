#!/usr/bin/env python3
"""Start the local worker connected to the production backend.

This launcher runs the worker process on your local GPU machine, pointing to
the remote production backend (https://api.podcash.app.moonsbow.com), and opens
the production web interface.
"""

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
WORKER_ENV_PATH = BASE_DIR / "worker" / ".env"

DEFAULT_PROD_BACKEND = "https://api.podcash.app.moonsbow.com"
DEFAULT_PROD_WEB = "https://podcash.app.moonsbow.com"
WORKER_PORT = int(os.getenv("WORKER_PORT", "8001"))

processes: list[tuple[str, subprocess.Popen]] = []
log_files: list = []
threads: list[threading.Thread] = []
_shutdown_called = False


def _find_python() -> str:
    if sys.platform == "win32":
        candidates = [
            BASE_DIR / "venv311" / "Scripts" / "python.exe",
            BASE_DIR / ".venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates = [
            BASE_DIR / "venv311" / "bin" / "python",
            BASE_DIR / ".venv" / "bin" / "python",
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _register_signals():
    signal.signal(signal.SIGINT, lambda s, f: shutdown(0, s, f))
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, lambda s, f: shutdown(0, s, f))


def start_process(name, cmd, cwd=None, env=None):
    print(f"[STARTER PROD] Starting {name}...")
    log_path = LOG_DIR / f"{name}.log"
    log_file = open(log_path, "a", encoding="utf-8", errors="ignore")
    log_files.append(log_file)

    proc_env = (env or os.environ).copy()
    proc_env["PYTHONPATH"] = str(BASE_DIR)

    proc = subprocess.Popen(
        cmd,
        cwd=cwd or BASE_DIR,
        env=proc_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append((name, proc))
    t = threading.Thread(
        target=_stream_output, args=(name, proc, log_file), daemon=True
    )
    t.start()
    threads.append(t)
    return proc


def _stream_output(name, proc, log_file):
    for line in proc.stdout:
        formatted = f"[{name}] {line}"
        log_file.write(formatted)
        log_file.flush()
        print(formatted, end="")


def wait_for_service(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def shutdown(exit_code=0, signum=None, frame=None):
    global _shutdown_called
    if _shutdown_called:
        return
    _shutdown_called = True

    print("\n[STARTER PROD] Shutting down...")
    for name, proc in processes:
        print(f"[STARTER PROD] Stopping {name}...")
        proc.terminate()
    time.sleep(2)
    for name, proc in processes:
        if proc.poll() is None:
            proc.kill()
    for log_file in log_files:
        try:
            log_file.close()
        except Exception:
            pass
    sys.exit(exit_code)


def main():
    _register_signals()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    venv_python = _find_python()

    # Cargar valores desde worker/.env o usar defaults de producción
    dotenv_dict = {}
    if WORKER_ENV_PATH.exists():
        dotenv_dict = dotenv_values(WORKER_ENV_PATH)

    backend_url = os.environ.get(
        "BACKEND_URL", dotenv_dict.get("BACKEND_URL", DEFAULT_PROD_BACKEND)
    )
    worker_token = os.environ.get(
        "WORKER_TOKEN", dotenv_dict.get("WORKER_TOKEN", "")
    )
    web_url = os.environ.get("WEB_URL", DEFAULT_PROD_WEB)

    print("=" * 60)
    print("🚀 PODCAST VOICE GENERATOR — WORKER DE PRODUCCIÓN")
    print(f"   Backend Server : {backend_url}")
    print(f"   Frontend Web   : {web_url}")
    print(f"   Worker Token   : {'***' + worker_token[-6:] if worker_token else '⚠️ NO CONFIGURADO'}")
    print("=" * 60)

    if not worker_token:
        print("\n❌ ERROR: WORKER_TOKEN no está definido en worker/.env ni en variables de entorno.")
        print("Por favor configura WORKER_TOKEN en worker/.env para conectar con producción.\n")
        sys.exit(1)

    worker_env = os.environ.copy()
    worker_env["PYTHONPATH"] = str(BASE_DIR)
    worker_env["BACKEND_URL"] = backend_url
    worker_env["WORKER_TOKEN"] = worker_token
    
    # Preservar otras configuraciones de worker/.env si existen
    for key, val in dotenv_dict.items():
        if key not in worker_env and val is not None:
            worker_env[key] = val

    start_process(
        "worker",
        [str(venv_python), "-m", "worker.main"],
        cwd=BASE_DIR,
        env=worker_env,
    )

    if not wait_for_service(f"http://127.0.0.1:{WORKER_PORT}/health"):
        print("[STARTER PROD] ❌ Worker local no pudo iniciar")
        shutdown(exit_code=1)

    print(f"[STARTER PROD] Worker activo y conectado a {backend_url}")
    print(f"[STARTER PROD] Abriendo interfaz web: {web_url}")
    webbrowser.open(web_url)

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
