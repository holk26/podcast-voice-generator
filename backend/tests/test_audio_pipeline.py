import pytest
import numpy as np
import tempfile
import os
from unittest.mock import patch, MagicMock
from core.audio_pipeline import AudioPipeline
from core.project import Project, Section, Voice


def test_pipeline_init():
    pipeline = AudioPipeline(output_dir="output")
    assert pipeline.output_dir == "output"


def test_pipeline_generate_section():
    with tempfile.TemporaryDirectory() as tmp:
        pipeline = AudioPipeline(output_dir=tmp)
        project = Project(name="Test")
        v = Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es")
        project.add_voice(v)
        project.add_section("Intro", "Hello", "v1")
        
        mock_engine = MagicMock()
        mock_engine.synthesize.return_value = os.path.join(tmp, "test.wav")
        engines = {"xtts": mock_engine}
        
        with patch.object(pipeline, '_load_or_get_engine', return_value=mock_engine):
            with patch('core.audio_pipeline.sf.read', return_value=(np.ones(24000, dtype=np.float32), 24000)):
                result = pipeline.generate_section(project, project.sections[0], engines)
        assert result is not None
