import pytest
import os
import tempfile
from utils.file_utils import ensure_dir, get_project_path, sanitize_filename


def test_ensure_dir_creates_directory():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "nested", "dir")
        ensure_dir(path)
        assert os.path.isdir(path)


def test_sanitize_filename():
    assert sanitize_filename("Hello World!") == "Hello_World"
    assert sanitize_filename("file/name\\test") == "file_name_test"
    assert sanitize_filename("a" * 300) == "a" * 100


def test_get_project_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = get_project_path(tmp, "My Podcast #1")
        assert path.startswith(tmp)
        assert "My_Podcast_1" in path
