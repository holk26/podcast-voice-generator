"""Tests del flujo VoiceFixer en subproceso y de la espera de VRAM libre."""
from pathlib import Path
from unittest.mock import patch

from worker import handlers


class _FakeCompleted:
    def __init__(self, returncode: int):
        self.returncode = returncode


def test_voicefixer_runs_in_subprocess_and_replaces(tmp_path):
    path = tmp_path / "final.mp3"
    path.write_bytes(b"original")
    enhanced = path.with_suffix(".enhanced.mp3")

    def fake_run(cmd, **kwargs):
        assert cmd[1] == "-c"
        assert "VoiceFixerEnhancer" in cmd[2]
        assert kwargs["env"]["PYTHONPATH"]
        enhanced.write_bytes(b"enhanced")
        return _FakeCompleted(0)

    with patch.object(handlers.subprocess, "run", side_effect=fake_run) as mock_run:
        handlers._apply_voicefixer_enhancer(path)

    assert mock_run.call_count == 1
    assert path.read_bytes() == b"enhanced"
    assert not enhanced.exists()


def test_voicefixer_failure_keeps_original(tmp_path):
    path = tmp_path / "final.mp3"
    path.write_bytes(b"original")

    with patch.object(handlers.subprocess, "run", return_value=_FakeCompleted(1)):
        handlers._apply_voicefixer_enhancer(path)

    assert path.read_bytes() == b"original"
    assert not path.with_suffix(".enhanced.mp3").exists()


def test_wait_for_free_vram_returns_when_enough():
    with patch.object(handlers, "_free_vram_gib", return_value=7.0), \
         patch.object(handlers.time, "sleep") as mock_sleep:
        handlers._wait_for_free_vram(min_free_gib=6.0, timeout_s=60)
    mock_sleep.assert_not_called()


def test_wait_for_free_vram_polls_until_free():
    with patch.object(handlers, "_free_vram_gib", side_effect=[5.0, 5.5, 7.0]), \
         patch.object(handlers.time, "sleep") as mock_sleep:
        handlers._wait_for_free_vram(min_free_gib=6.0, timeout_s=60)
    assert mock_sleep.call_count == 2


def test_wait_for_free_vram_gives_up_after_timeout():
    with patch.object(handlers, "_free_vram_gib", return_value=1.0), \
         patch.object(handlers.time, "sleep"):
        # timeout_s=0: el primer chequeo ya supera el deadline
        handlers._wait_for_free_vram(min_free_gib=6.0, timeout_s=0)
