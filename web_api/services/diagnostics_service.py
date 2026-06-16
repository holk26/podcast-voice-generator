import concurrent.futures
import json
import os
import shutil
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class DiagnosticStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DiagnosticCheckResult:
    component: str
    status: DiagnosticStatus
    detail: str
    checked_at: datetime


BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
VOICES_DIR = BASE_DIR / "voices"
DATA_DIR = BASE_DIR / "data"


def _check_gpu() -> DiagnosticCheckResult:
    try:
        import torch

        if not torch.cuda.is_available():
            return DiagnosticCheckResult(
                component="gpu",
                status=DiagnosticStatus.ERROR,
                detail="CUDA is not available. NVIDIA GPU not detected or drivers missing.",
                checked_at=datetime.utcnow(),
            )
        free_bytes = torch.cuda.mem_get_info()[0]
        free_gb = free_bytes / (1024**3)
        name = torch.cuda.get_device_name(0)
        if free_gb < 2:
            return DiagnosticCheckResult(
                component="gpu",
                status=DiagnosticStatus.WARNING,
                detail=f"{name} detected but only {free_gb:.1f} GB VRAM free.",
                checked_at=datetime.utcnow(),
            )
        return DiagnosticCheckResult(
            component="gpu",
            status=DiagnosticStatus.OK,
            detail=f"{name} detected with {free_gb:.1f} GB VRAM free.",
            checked_at=datetime.utcnow(),
        )
    except Exception as e:
        return DiagnosticCheckResult(
            component="gpu",
            status=DiagnosticStatus.ERROR,
            detail=f"Could not query GPU: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_ollama() -> DiagnosticCheckResult:
    from web_api.config import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL

    try:
        url = f"{OLLAMA_BASE_URL}/api/tags"
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="ignore")
            data = json.loads(body)
            models = [m.get("name", "") for m in data.get("models", [])]
            if OLLAMA_DEFAULT_MODEL in models:
                return DiagnosticCheckResult(
                    component="ollama",
                    status=DiagnosticStatus.OK,
                    detail=f"Ollama running; model {OLLAMA_DEFAULT_MODEL} available.",
                    checked_at=datetime.utcnow(),
                )
            return DiagnosticCheckResult(
                component="ollama",
                status=DiagnosticStatus.WARNING,
                detail=f"Ollama running but model {OLLAMA_DEFAULT_MODEL} not found. Run: ollama pull {OLLAMA_DEFAULT_MODEL}",
                checked_at=datetime.utcnow(),
            )
    except Exception as e:
        return DiagnosticCheckResult(
            component="ollama",
            status=DiagnosticStatus.ERROR,
            detail=f"Ollama not reachable: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_disk() -> DiagnosticCheckResult:
    paths = {
        "data": DATA_DIR,
        "output": OUTPUT_DIR,
        "voices": VOICES_DIR,
    }
    min_gb = 5
    warnings = []
    for label, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)
        free_gb = shutil.disk_usage(path).free / (1024**3)
        if free_gb < min_gb:
            warnings.append(f"{label}: {free_gb:.1f} GB free")
    if warnings:
        return DiagnosticCheckResult(
            component="disk",
            status=DiagnosticStatus.WARNING,
            detail="; ".join(warnings),
            checked_at=datetime.utcnow(),
        )
    return DiagnosticCheckResult(
        component="disk",
        status=DiagnosticStatus.OK,
        detail="All directories have >= 5 GB free.",
        checked_at=datetime.utcnow(),
    )


def _check_worker() -> DiagnosticCheckResult:
    from web_api.config import WORKER_PORT

    url = f"http://127.0.0.1:{WORKER_PORT}/health"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                return DiagnosticCheckResult(
                    component="worker",
                    status=DiagnosticStatus.OK,
                    detail=f"Worker responds on port {WORKER_PORT}.",
                    checked_at=datetime.utcnow(),
                )
            return DiagnosticCheckResult(
                component="worker",
                status=DiagnosticStatus.ERROR,
                detail=f"Worker returned status {response.status}.",
                checked_at=datetime.utcnow(),
            )
    except Exception as e:
        return DiagnosticCheckResult(
            component="worker",
            status=DiagnosticStatus.ERROR,
            detail=f"Worker not reachable: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_web_assets() -> DiagnosticCheckResult:
    dist_dir = BASE_DIR / "web" / "dist"
    if dist_dir.exists() and any(dist_dir.iterdir()):
        return DiagnosticCheckResult(
            component="web_assets",
            status=DiagnosticStatus.OK,
            detail="Production build found in web/dist.",
            checked_at=datetime.utcnow(),
        )
    from web_api.config import WEB_PORT

    url = f"http://127.0.0.1:{WEB_PORT}"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                return DiagnosticCheckResult(
                    component="web_assets",
                    status=DiagnosticStatus.OK,
                    detail=f"Dev server responds on port {WEB_PORT}.",
                    checked_at=datetime.utcnow(),
                )
            return DiagnosticCheckResult(
                component="web_assets",
                status=DiagnosticStatus.WARNING,
                detail=f"Web responded with status {response.status}.",
                checked_at=datetime.utcnow(),
            )
    except Exception as e:
        return DiagnosticCheckResult(
            component="web_assets",
            status=DiagnosticStatus.WARNING,
            detail=f"No build found and dev server not reachable: {e}",
            checked_at=datetime.utcnow(),
        )


def _check_tts_engines() -> DiagnosticCheckResult:
    engines = []
    warnings = []
    try:
        from core.xtts_engine import XTTS_AVAILABLE
        engines.append("xtts")
    except Exception as e:
        warnings.append(f"xtts not importable: {e}")
    try:
        from core.higgs_engine import HiggsEngine
        engines.append("higgs")
    except Exception as e:
        warnings.append(f"higgs not importable: {e}")
    try:
        from zonos.speaker_cloning import load_model
        engines.append("zonos")
    except Exception as e:
        warnings.append(f"zonos not importable: {e}")

    if not engines:
        return DiagnosticCheckResult(
            component="tts_engines",
            status=DiagnosticStatus.ERROR,
            detail="No TTS engine available: " + "; ".join(warnings),
            checked_at=datetime.utcnow(),
        )
    if warnings:
        return DiagnosticCheckResult(
            component="tts_engines",
            status=DiagnosticStatus.WARNING,
            detail=f"Available: {', '.join(engines)}. Missing: " + "; ".join(warnings),
            checked_at=datetime.utcnow(),
        )
    return DiagnosticCheckResult(
        component="tts_engines",
        status=DiagnosticStatus.OK,
        detail=f"Available engines: {', '.join(engines)}.",
        checked_at=datetime.utcnow(),
    )


def run_diagnostics() -> list[DiagnosticCheckResult]:
    checks = [
        _check_gpu,
        _check_ollama,
        _check_disk,
        _check_worker,
        _check_web_assets,
        _check_tts_engines,
    ]
    results: list[DiagnosticCheckResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = {executor.submit(fn): i for i, fn in enumerate(checks)}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append(
                    DiagnosticCheckResult(
                        component="unknown",
                        status=DiagnosticStatus.ERROR,
                        detail=f"Check crashed: {e}",
                        checked_at=datetime.utcnow(),
                    )
                )
    order = ["gpu", "ollama", "disk", "worker", "web_assets", "tts_engines"]
    results.sort(key=lambda r: order.index(r.component) if r.component in order else 99)
    return results
