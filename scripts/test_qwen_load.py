import traceback
import transformers.utils.generic as _generic

_orig = _generic.check_model_inputs

def _patched(*args, **kwargs):
    if args and callable(args[0]):
        return _orig(args[0])
    return _orig

_generic.check_model_inputs = _patched

from core.qwen_tts_engine import Qwen3TTSEngine

engine = Qwen3TTSEngine(device="cuda", dtype="bfloat16")
try:
    engine.load()
    print("Engine loaded successfully")
except Exception as e:
    print("FAILED:", e)
    traceback.print_exc()
