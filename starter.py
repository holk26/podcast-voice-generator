import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser
import urllib.request
from pathlib import Path


def _check_ollama():
    try:
        from web_api.config import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL
        from web_api.services.llm_provider import check_ollama
        status = check_ollama()
        if not status["available"]:
            print(f"[STARTER] WARNING: Ollama not available at {OLLAMA_BASE_URL}. CrewAI features will fail.")
        elif not status["default_ready"]:
            print(f"[STARTER] WARNING: Model {OLLAMA_DEFAULT_MODEL} not found in Ollama. Run: ollama pull {OLLAMA_DEFAULT_MODEL}")
        else:
            print(f"[STARTER] Ollama ready at {OLLAMA_BASE_URL} with model {OLLAMA_DEFAULT_MODEL}")
    except Exception as e:
        print(f"[STARTER] WARNING: Could not check Ollama status: {e}")

BASE_DIR = Path(__file__).resolve().parent


def _get_port(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except (ValueError, TypeError):
        print(f"[STARTER] Invalid {name}={raw!r}, using default {default}")
        return int(default)


API_PORT = _get_port("API_PORT", "8000")
WORKER_PORT = _get_port("WORKER_PORT", "8001")
WEB_PORT = _get_port("WEB_PORT", "5173")

processes = []
threads = []
_shutdown_called = False


def start_process(name, cmd, cwd=None):
    print(f"[STARTER] Starting {name}...")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd or BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    processes.append((name, proc))
    t = threading.Thread(target=_stream_output, args=(name, proc), daemon=True)
    t.start()
    threads.append(t)
    return proc


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

    print("\n[STARTER] Shutting down...")
    for name, proc in processes:
        print(f"[STARTER] Stopping {name}...")
        proc.terminate()
    time.sleep(2)
    for name, proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(exit_code)


def _register_signals():
    signal.signal(signal.SIGINT, lambda s, f: shutdown(0, s, f))
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, lambda s, f: shutdown(0, s, f))


def _stream_output(name, proc):
    for line in proc.stdout:
        print(f"[{name}] {line}", end="")


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


def main():
    _register_signals()
    _check_ollama()
    venv_python = _find_python()

    start_process("api", [str(venv_python), "-m", "web_api.main"])
    if not wait_for_service(f"http://127.0.0.1:{API_PORT}/api/health"):
        print("[STARTER] API did not start")
        shutdown(exit_code=1)

    start_process("worker", [str(venv_python), "-m", "worker.main"])
    if not wait_for_service(f"http://127.0.0.1:{WORKER_PORT}/health"):
        print("[STARTER] Worker did not start")
        shutdown(exit_code=1)

    start_process(
        "web",
        ["npm", "run", "dev", "--", "--port", str(WEB_PORT), "--host", "127.0.0.1"],
        cwd=BASE_DIR / "web",
    )
    if not wait_for_service(f"http://127.0.0.1:{WEB_PORT}"):
        print("[STARTER] Web did not start")
        shutdown(exit_code=1)

    print("[STARTER] All services running. Opening browser...")
    webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
