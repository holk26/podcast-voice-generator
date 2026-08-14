from pathlib import Path
from unittest.mock import patch, MagicMock

from shared.schemas import WorkerJob
from worker import runner


def test_process_single_job_completes_successfully(tmp_path):
    job = WorkerJob(
        episode_id=42,
        title="Test episode",
        type="podcast",
        source_text="Hola mundo",
        voice_id="jorge",
    )
    output_path = tmp_path / "final.mp3"
    output_path.touch()

    with patch("worker.client.get_next_job", return_value=job) as mock_get, \
         patch("worker.runner.handle_podcast_episode", return_value=output_path) as mock_handle, \
         patch("worker.client.complete_job") as mock_complete, \
         patch("worker.client.fail_job") as mock_fail:

        result = runner._process_single_job()

        assert result is True
        mock_get.assert_called_once()
        mock_handle.assert_called_once_with(job)
        mock_complete.assert_called_once_with(42, "/outputs/42/final.mp3")
        mock_fail.assert_not_called()


def test_process_single_job_reports_failure():
    job = WorkerJob(
        episode_id=43,
        title="Failing episode",
        type="podcast",
        source_text="Hola",
        voice_id="jorge",
    )

    with patch("worker.client.get_next_job", return_value=job), \
         patch("worker.runner.handle_podcast_episode", side_effect=RuntimeError("boom")), \
         patch("worker.client.complete_job") as mock_complete, \
         patch("worker.client.fail_job") as mock_fail:

        result = runner._process_single_job()

        assert result is True
        mock_complete.assert_not_called()
        mock_fail.assert_called_once()
        assert "boom" in mock_fail.call_args[0][1]


def test_process_single_job_no_pending():
    with patch("worker.client.get_next_job", return_value=None):
        result = runner._process_single_job()
        assert result is False
