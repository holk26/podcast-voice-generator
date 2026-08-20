#!/usr/bin/env python3
"""Start the podcast voice generator stack and open a live monitor window."""

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"

API_PORT = int(os.getenv("API_PORT", "8000"))
WORKER_PORT = int(os.getenv("WORKER_PORT", "8001"))
WEB_PORT = int(os.getenv("WEB_PORT", "5173"))

processes: list[tuple[str, subprocess.Popen]] = []
log_files: list = []
threads: list[threading.Thread] = []
_shutdown_called = False


def _check_ollama():
    try:
        from backend.app.config import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL
        from backend.app.services.llm_provider import check_ollama

        status = check_ollama()
        if not status["available"]:
            print(
                f"[STARTER] WARNING: Ollama not available at {OLLAMA_BASE_URL}. "
                "CrewAI features will fail."
            )
        elif not status["default_ready"]:
            print(
                f"[STARTER] WARNING: Model {OLLAMA_DEFAULT_MODEL} not found in Ollama. "
                f"Run: ollama pull {OLLAMA_DEFAULT_MODEL}"
            )
        else:
            print(
                f"[STARTER] Ollama ready at {OLLAMA_BASE_URL} with model {OLLAMA_DEFAULT_MODEL}"
            )
    except Exception as e:
        print(f"[STARTER] WARNING: Could not check Ollama status: {e}")


def _find_python():
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
    print(f"[STARTER] Starting {name}...")
    log_path = LOG_DIR / f"{name}.log"
    log_file = open(log_path, "w", encoding="utf-8", errors="ignore")
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
        line = f"[{name}] {line}"
        log_file.write(line)
        log_file.flush()
        print(line, end="")


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


def _find_terminal():
    """Return the first available terminal emulator command."""
    terminals = [
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "alacritty",
        "wezterm",
        "kitty",
        "xterm",
    ]
    for term in terminals:
        path = shutil.which(term)
        if path:
            return term, path
    return None, None


def _open_monitor():
    """Open the live monitor in a new terminal window."""
    term, term_path = _find_terminal()
    if not term:
        print(
            "[STARTER] No terminal emulator found; monitor will not open. "
            "Logs are available in ./logs/"
        )
        return

    monitor_cmd = f"cd {BASE_DIR} && {sys.executable} -u starter_monitor.py"
    if term == "gnome-terminal":
        cmd = [term_path, "--", "bash", "-c", f"{monitor_cmd}; exec bash"]
    elif term == "konsole":
        cmd = [term_path, "-e", "bash", "-c", f"{monitor_cmd}; exec bash"]
    elif term in ("xfce4-terminal", "alacritty", "wezterm", "kitty"):
        cmd = [term_path, "-e", "bash", "-c", f"{monitor_cmd}; exec bash"]
    else:
        # xterm and others
        cmd = [term_path, "-e", "bash", "-c", f"{monitor_cmd}; exec bash"]

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[STARTER] Monitor opened in {term}")
    except Exception as e:
        print(f"[STARTER] Could not open monitor: {e}")


def shutdown(exit_code=0, signum=None, frame=None):
    global _shutdown_called
    if _shutdown_called:
        return
    _shutdown_called = True

    print("\n[STARTER] Shutting down...")
    for name, proc in processes:
        print(f"[STARTER] Stopping {name}...")
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
    _check_ollama()
    venv_python = _find_python()

    # En modo desarrollo local backend y worker deben compartir el mismo
    # WORKER_TOKEN; si el usuario lo exporta, lo respetamos.
    dev_worker_token = os.environ.get("WORKER_TOKEN", "dev-worker-token-local")

    api_env = os.environ.copy()
    api_env["PYTHONPATH"] = str(BASE_DIR)
    api_env["WORKER_TOKEN"] = dev_worker_token

    start_process(
        "api",
        [str(venv_python), "-m", "backend.app.main"],
        cwd=BASE_DIR,
        env=api_env,
    )
    if not wait_for_service(f"http://127.0.0.1:{API_PORT}/api/health"):
        print("[STARTER] API did not start")
        shutdown(exit_code=1)

    worker_env = os.environ.copy()
    worker_env["PYTHONPATH"] = str(BASE_DIR)
    worker_env["BACKEND_URL"] = f"http://127.0.0.1:{API_PORT}"
    worker_env["WORKER_TOKEN"] = dev_worker_token
    start_process(
        "worker",
        [str(venv_python), "-m", "worker.main"],
        cwd=BASE_DIR,
        env=worker_env,
    )
    if not wait_for_service(f"http://127.0.0.1:{WORKER_PORT}/health"):
        print("[STARTER] Worker did not start")
        shutdown(exit_code=1)

    start_process(
        "web",
        ["npm", "run", "dev", "--", "--port", str(WEB_PORT), "--host", "127.0.0.1"],
        cwd=BASE_DIR / "frontend",
    )
    if not wait_for_service(f"http://127.0.0.1:{WEB_PORT}"):
        print("[STARTER] Web did not start")
        shutdown(exit_code=1)

    print("[STARTER] All services running.")
    _open_monitor()
    webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
