from processors.dialogue_parser import parse_dialogue


def test_parse_two_speakers():
    script = (
        "Alejandra: Hello, how are you?\n"
        "Homero: Estoy bien, gracias.\n"
        "Alejandra: Great!"
    )
    segments = parse_dialogue(script)
    assert len(segments) == 3
    assert segments[0].speaker == "Alejandra"
    assert "Hello" in segments[0].text
    assert segments[1].speaker == "Homero"
    assert segments[2].speaker == "Alejandra"


def test_parse_ignores_unprefixed_lines_until_first_speaker():
    script = "Intro musical\nAlejandra: Let's begin.\nHomero: OK."
    segments = parse_dialogue(script)
    assert len(segments) == 2
    assert segments[0].text == "Let's begin."


def test_parse_case_insensitive():
    script = "ALEJANDRA: Hi.\nhomero: Hola."
    segments = parse_dialogue(script)
    assert segments[0].speaker == "Alejandra"
    assert segments[1].speaker == "Homero"


def test_parse_valid_speakers_ignores_colon_sentences():
    # Frase narrativa seguida de dos puntos: NO es un turno de diálogo.
    script = (
        "Hola, soy Alejandra.\n"
        "Hoy vamos a responder una pregunta que casi nadie se hace: "
        "como es posible que nadie hiciera nada.\n"
        "Eduardo: Empecemos.\n"
        "Yolis: De acuerdo."
    )
    segments = parse_dialogue(script, valid_speakers={"Eduardo", "Yolis"})
    assert [s.speaker for s in segments] == ["Eduardo", "Yolis"]


def test_parse_without_valid_speakers_keeps_legacy_behavior():
    script = "Alejandra: Hola.\nHomero: Adios."
    segments = parse_dialogue(script)
    assert len(segments) == 2
