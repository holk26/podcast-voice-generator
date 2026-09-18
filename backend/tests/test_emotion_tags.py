from core.emotion_tags import (
    HIGGS_TAGS,
    normalize_emotion_tags,
    sanitize_emotion_tags,
)


def test_normalize_prefixes_bare_emotion_tokens():
    text = "Crímenes.<|enthusiasm|> Hoy <|contemplation|> seguimos."
    assert normalize_emotion_tags(text) == (
        "Crímenes.<|emotion:enthusiasm|> Hoy <|emotion:contemplation|> seguimos."
    )


def test_normalize_leaves_already_prefixed_and_unknown_tokens():
    text = "<|emotion:awe|> ok <|prosody:pause|> <|totalmente_inventado|>"
    assert normalize_emotion_tags(text) == text


def test_normalize_plus_sanitize_yields_only_valid_higgs_tokens():
    text = "Hola.<|enthusiasm|> Mundo <|prosody:pause|> fin <|inventado|>."
    result = sanitize_emotion_tags(normalize_emotion_tags(text), "higgs")
    assert result == "Hola.<|emotion:enthusiasm|> Mundo <|prosody:pause|> fin ."


def test_higgs_keeps_known_emotion_tokens():
    text = "<|emotion:enthusiasm|> Hoy es un gran día. <|prosody:pause|> Sigamos."
    assert sanitize_emotion_tags(text, "higgs") == text


def test_higgs_strips_invented_tokens():
    text = "<|emotion:felicidad_extrema|> Hola <|emotion:awe|> mundo."
    assert sanitize_emotion_tags(text, "higgs") == "Hola <|emotion:awe|> mundo."


def test_edge_and_qwen_strip_all_tokens():
    text = "<|emotion:enthusiasm|> Hola <|style:whispering|> mundo."
    for engine in ("edge", "qwen3"):
        assert sanitize_emotion_tags(text, engine) == "Hola mundo."


def test_text_without_tags_is_untouched():
    text = "Guion normal, sin marcas. Con acentos y ¡signos!"
    for engine in ("higgs", "edge", "qwen3"):
        assert sanitize_emotion_tags(text, engine) == text


def test_catalog_covers_documented_higgs_tokens():
    for tag in ("emotion:elation", "emotion:sadness", "style:whispering",
                "sfx:laughter", "prosody:pause", "prosody:speed_slow"):
        assert tag in HIGGS_TAGS
