import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import starter
import starter_monitor


def test_log_dir_created(tmp_path, monkeypatch):
    monkeypatch.setattr(starter, "LOG_DIR", tmp_path / "logs")
    starter.LOG_DIR.mkdir(parents=True, exist_ok=True)
    assert starter.LOG_DIR.exists()


def test_find_python_prefers_venv(tmp_path):
    venv_bin = tmp_path / "venv311" / "bin"
    venv_bin.mkdir(parents=True)
    python_exe = venv_bin / ("python.exe" if sys.platform == "win32" else "python")
    python_exe.touch()

    with patch.object(starter, "BASE_DIR", tmp_path):
        found = starter._find_python()
        assert str(python_exe) == found


def test_wait_for_service_success():
    with patch("urllib.request.urlopen") as mock_open:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_open.return_value.__enter__.return_value = mock_response
        assert starter.wait_for_service("http://127.0.0.1:8000/health", timeout=1) is True


def test_wait_for_service_failure():
    with patch("urllib.request.urlopen", side_effect=Exception("down")):
        assert starter.wait_for_service("http://127.0.0.1:8000/health", timeout=0.1) is False


def test_monitor_get_port_from_env(monkeypatch):
    monkeypatch.setenv("API_PORT", "9000")
    assert starter_monitor._get_port(starter_monitor.SERVICES[0]) == 9000


def test_monitor_get_port_default(monkeypatch):
    monkeypatch.delenv("API_PORT", raising=False)
    assert starter_monitor._get_port(starter_monitor.SERVICES[0]) == 8000


def test_monitor_count_errors():
    lines = [
        "INFO: normal log",
        "ERROR: something failed",
        "Traceback (most recent call last):",
        "WARNING: careful",
    ]
    assert starter_monitor._count_errors(lines) == 2


def test_monitor_tail_lines(tmp_path):
    log = tmp_path / "test.log"
    log.write_text("line1\nline2\nline3\n")
    assert starter_monitor._tail_lines(log, 2) == ["line2", "line3"]


def test_monitor_check_health_ok():
    with patch("urllib.request.urlopen") as mock_open:
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status":"ok"}'
        mock_response.__enter__.return_value = mock_response
        mock_open.return_value = mock_response
        status, detail = starter_monitor._check_health("http://127.0.0.1:8000/api/health")
        assert status == "OK"
        assert "status" in detail


def test_monitor_check_health_down():
    with patch("urllib.request.urlopen", side_effect=Exception("refused")):
        status, detail = starter_monitor._check_health("http://127.0.0.1:8000/api/health")
        assert status == "DOWN"
        assert "refused" in detail
