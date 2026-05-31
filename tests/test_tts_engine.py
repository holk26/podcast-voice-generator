import pytest
from core.tts_engine import TTSBase
from core.project import Voice


def test_tts_base_is_abstract():
    with pytest.raises(TypeError):
        TTSBase()


def test_dummy_engine_implements_interface():
    class DummyEngine(TTSBase):
        def synthesize(self, text, voice, output_path):
            return output_path
        def clone_voice(self, reference_path, name):
            return "voice_id"
        def get_speakers(self):
            return ["speaker1"]
        def is_loaded(self):
            return True
        def load(self):
            pass
        def unload(self):
            pass

    engine = DummyEngine()
    assert engine.is_loaded() is True
    assert engine.get_speakers() == ["speaker1"]
