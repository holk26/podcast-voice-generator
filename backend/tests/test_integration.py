import pytest
import tempfile
import os
import numpy as np
from unittest.mock import patch, MagicMock
from core.project import Project, Voice
from core.batch_generator import BatchGenerator
from core.audio_pipeline import AudioPipeline


def test_full_pipeline_mock():
    with tempfile.TemporaryDirectory() as tmp:
        project = Project(name="Integration Test")
        project.add_voice(Voice(id="v1", name="Host", type="pretrained", engine="xtts", language="es"))
        project.add_section("Intro", "Hello world", "v1")
        
        pipeline = AudioPipeline(output_dir=tmp)
        generator = BatchGenerator(pipeline)
        
        mock_engine = MagicMock()
        mock_engine.is_loaded.return_value = True
        mock_engine.synthesize.return_value = os.path.join(tmp, "test.wav")
        generator.register_engine("xtts", mock_engine)
        generator.add_project(project)
        
        with patch('core.audio_pipeline.sf.read', return_value=(np.ones(24000, dtype=np.float32), 24000)):
            results = generator.run(project)
        
        assert len(results) == 1
        assert results[0].status == "completed"
