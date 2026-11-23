from src.domain.search_history import search_key


def test_ignores_case_accents_and_punctuation() -> None:
    assert search_key("Buracos Negros!") == search_key("buracos negros")


def test_ignores_word_order() -> None:
    assert search_key("negros buracos") == search_key("buracos negros")


def test_ignores_filler_words() -> None:
    assert search_key("os buracos negros da galáxia") == search_key("buracos negros galáxia")


def test_treats_hyphens_as_spaces() -> None:
    assert search_key("buracos-negros") == search_key("buracos negros")


def test_more_specific_search_gets_a_different_key() -> None:
    assert search_key("estrelas gêmeas") != search_key("estrelas")


def test_keeps_filler_words_when_the_query_has_nothing_else() -> None:
    assert search_key("de") == "de"
