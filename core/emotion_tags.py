"""Tokens inline de emoción/estilo/prosodia para TTS expresivo.

Higgs v3 interpreta tokens <|tipo:valor|> (emociones, estilos, efectos);
el resto de motores (edge-tts, Qwen3-Base) no los entiende y hay que
quitárselos al texto antes de sintetizar o los pronunciaría.

Mantener las listas sincronizadas con core/higgs_engine.py
(HIGGS_EMOTIONS / HIGGS_STYLES / HIGGS_SFX) — se duplican aquí para no
importar el motor (que carga torch) en el camino caliente de la API.
"""

import re

_TAG_RE = re.compile(r"<\|([a-z]+):([a-z_]+)\|>")
_SPACES_RE = re.compile(r"[ \t]{2,}")

_EMOTIONS = [
    "elation", "amusement", "enthusiasm", "determination", "pride",
    "contentment", "affection", "relief", "contemplation", "confusion",
    "surprise", "awe", "longing", "arousal", "anger", "fear", "disgust",
    "bitterness", "sadness", "shame", "helplessness",
]

# Nombres públicos para el prompt del congreso (crew_service)
HIGGS_EMOTION_NAMES: list[str] = list(_EMOTIONS)
_STYLES = ["singing", "shouting", "whispering"]
_SFX = ["cough", "laughter", "crying", "screaming", "burping",
        "humming", "sigh", "sniff", "sneeze"]
_PROSODY = ["speed_slow", "speed_fast", "pitch_high", "pitch_low", "pause"]

HIGGS_TAGS: frozenset[str] = frozenset(
    {f"emotion:{t}" for t in _EMOTIONS}
    | {f"style:{t}" for t in _STYLES}
    | {f"sfx:{t}" for t in _SFX}
    | {f"prosody:{t}" for t in _PROSODY}
)

# Tags soportados por motor; vacío = quitar todos los tokens
ENGINE_TAGS: dict[str, frozenset[str]] = {
    "higgs": HIGGS_TAGS,
    "qwen3": frozenset(),
    "edge": frozenset(),
}


def sanitize_emotion_tags(text: str, engine: str) -> str:
    """Quita los tokens <|tipo:valor|> que `engine` no soporta.

    Devuelve el texto solo con los tokens que el motor entiende; el resto
    desaparece (junto con el doble espacio resultante) para que nunca se
    pronuncien literalmente.
    """
    allowed = ENGINE_TAGS.get(engine, frozenset())

    def _repl(match: re.Match) -> str:
        return match.group(0) if f"{match.group(1)}:{match.group(2)}" in allowed else ""

    return _SPACES_RE.sub(" ", _TAG_RE.sub(_repl, text)).strip() if "<|" in text else text
