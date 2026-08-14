import pytest
import json
import tempfile
import os
from core.project import Project, ProjectSettings, Section, Voice


def test_create_project():
    p = Project(name="Test Podcast")
    assert p.name == "Test Podcast"
    assert len(p.sections) == 0
    assert len(p.voices) == 0


def test_add_section():
    p = Project(name="Test")
    p.add_section("Intro", "Hello world", "voz1")
    assert len(p.sections) == 1
    assert p.sections[0].text == "Hello world"


def test_add_voice():
    p = Project(name="Test")
    v = Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es")
    p.add_voice(v)
    assert len(p.voices) == 1


def test_save_and_load_project():
    with tempfile.TemporaryDirectory() as tmp:
        p = Project(name="Save Test")
        p.add_section("Intro", "Hello", "v1")
        v = Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es")
        p.add_voice(v)
        path = os.path.join(tmp, "project.json")
        p.save(path)
        assert os.path.exists(path)
        loaded = Project.load(path)
        assert loaded.name == "Save Test"
        assert len(loaded.sections) == 1
        assert loaded.sections[0].text == "Hello"
