from core.emotion_tags import sanitize_emotion_tags, HIGGS_TAGS


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
