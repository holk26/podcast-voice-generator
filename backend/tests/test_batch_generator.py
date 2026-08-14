import pytest
from unittest.mock import patch, MagicMock
from core.batch_generator import BatchGenerator, GenerationTask
from core.project import Project, Voice


def test_create_task():
    task = GenerationTask(section_id="sec_001", status="pending")
    assert task.section_id == "sec_001"
    assert task.status == "pending"


def test_batch_generator_queue():
    gen = BatchGenerator()
    project = Project(name="Test")
    project.add_voice(Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es"))
    project.add_section("Intro", "Hello", "v1")
    gen.add_project(project)
    assert len(gen.queue) == 1
    assert gen.queue[0].section_id == "sec_001"
