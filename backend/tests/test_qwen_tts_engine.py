import pytest


def test_patch_helper_runs_without_error():
    """The monkey-patch helper must not raise and must leave a callable symbol."""
    pytest.importorskip("transformers")
    from core.qwen_tts_engine import _patch_check_model_inputs

    _patch_check_model_inputs()

    import transformers.utils.generic as _generic

    assert callable(_generic.check_model_inputs)
