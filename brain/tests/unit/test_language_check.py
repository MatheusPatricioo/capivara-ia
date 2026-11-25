from src.evals.language_check import looks_portuguese


def test_recognizes_a_portuguese_summary() -> None:
    assert looks_portuguese("As capivaras são ótimas nadadoras e ficam debaixo da água.")


def test_recognizes_an_english_summary() -> None:
    assert not looks_portuguese("Capybaras are great swimmers and they stay under the water.")


def test_a_text_without_common_words_is_not_counted_as_portuguese() -> None:
    assert not looks_portuguese("Bioluminescência")
