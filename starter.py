import os
import sys
import time
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
API_PORT = os.getenv("API_PORT", "8000")
WORKER_PORT = os.getenv("WORKER_PORT", "8001")
WEB_PORT = os.getenv("WEB_PORT", "5173")

processes = []


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
    return proc


def wait_for_service(url, timeout=30):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def shutdown(signum=None, frame=None):
    print("\n[STARTER] Shutting down...")
    for name, proc in processes:
        print(f"[STARTER] Stopping {name}...")
        proc.terminate()
    time.sleep(2)
    for name, proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)


def _register_signals():
    signal.signal(signal.SIGINT, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown)


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
    venv_python = _find_python()

    start_process("api", [str(venv_python), "-m", "web_api.main"])
    if not wait_for_service(f"http://127.0.0.1:{API_PORT}/api/health"):
        print("[STARTER] API did not start")
        shutdown()

    start_process("worker", [str(venv_python), "-m", "worker.main"])
    if not wait_for_service(f"http://127.0.0.1:{WORKER_PORT}/health"):
        print("[STARTER] Worker did not start")
        shutdown()

    start_process("web", ["npm", "run", "dev", "--", "--port", WEB_PORT, "--host", "127.0.0.1"], cwd=BASE_DIR / "web")
    if not wait_for_service(f"http://127.0.0.1:{WEB_PORT}"):
        print("[STARTER] Web did not start")
        shutdown()

    print("[STARTER] All services running. Opening browser...")
    webbrowser.open(f"http://127.0.0.1:{WEB_PORT}")

    threads = []
    for name, proc in processes:
        t = threading.Thread(target=_stream_output, args=(name, proc), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
