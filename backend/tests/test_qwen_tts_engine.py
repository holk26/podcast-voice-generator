import pytest


def test_engine_imports_without_qwen_tts_installed():
    """El motor debe importarse sin qwen-tts instalado (lazy load en load())."""
    from core.qwen_tts_engine import Qwen3TTSEngine, _normalize_language

    engine = Qwen3TTSEngine()
    assert engine.name == "qwen3"
    assert not engine.is_loaded()


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("es", "Spanish"),
        ("en", "English"),
        ("es-ES", "Spanish"),
        ("", "Spanish"),
        (None, "Spanish"),
        ("pt-BR", "Portuguese"),
    ],
)
def test_normalize_language(lang, expected):
    from core.qwen_tts_engine import _normalize_language

    assert _normalize_language(lang) == expected
