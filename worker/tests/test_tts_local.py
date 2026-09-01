from worker.tts_local import _split_text


def _has_broken_tag(chunk: str) -> bool:
    """Devuelve True si el chunk contiene un token <|...|> cortado."""
    open_count = chunk.count("<|")
    close_count = chunk.count("|>")
    if open_count == 0 and close_count == 0:
        return False
    # Cada tag válido aporta un <| y un |>
    import re
    valid_tags = len(re.findall(r"<\|[a-z]+:[a-z_]+\|>", chunk))
    return open_count != valid_tags or close_count != valid_tags


def test_split_text_does_not_break_emotion_tags():
    """El troceado por frases no debe cortar tokens <|emotion:...|>.

    _split_text divide en límites de frase (.!?…), no dentro de palabras,
    por lo que los tags viajan atómicos junto a su frase.
    """
    text = " ".join([
        "<|emotion:fear|>Era una noche oscura.",
        "<|emotion:sadness|>El viento soplaba entre los árboles.",
        "<|prosody:pause|>De pronto, un ruido.",
        "<|emotion:surprise|>¿Quién está ahí?",
        "<|style:whispering|>Nadie respondió.",
    ] * 20)

    chunks = _split_text(text, max_chars=400)
    assert len(chunks) > 1, "el texto debería trocearse en varios fragmentos"
    for chunk in chunks:
        assert not _has_broken_tag(chunk), f"tag cortado en chunk: {chunk[:120]}"


def test_split_text_keeps_tag_attached_to_sentence():
    """Un tag pegado a una frase viaja completo en el mismo chunk."""
    text = "Primera.<|emotion:fear|> Segunda. Tercera."
    chunks = _split_text(text, max_chars=400)
    assert len(chunks) == 1
    assert "<|emotion:fear|>" in chunks[0]
    assert not _has_broken_tag(chunks[0])
