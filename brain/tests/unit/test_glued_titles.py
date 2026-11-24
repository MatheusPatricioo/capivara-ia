"""The glued titles here are real ones, taken from the capybara's search log."""

from src.infrastructure.glued_titles import first_title

NO_OTHER_TITLES: list[str] = []


def test_keeps_a_normal_title_as_it_is() -> None:
    title = "Estrelas: o que são, formação, tipos - Brasil Escola"

    assert first_title(title, NO_OTHER_TITLES) == title


def test_keeps_a_short_title_with_a_brand_written_in_camel_case() -> None:
    title = "Os maiores mistérios das estrelas e do universo - YouTube"

    assert first_title(title, NO_OTHER_TITLES) == title


def test_cuts_where_a_cut_title_touches_the_next_one() -> None:
    glued = (
        "Família de Capivaras na Natureza Momentos Incríveis e ..."
        "10 Cidades no Brasil Onde Você Pode Encontrar Capivaras na ..."
        "Capivara: características, habitat, reprodução - Brasil Escola"
    )

    assert first_title(glued, NO_OTHER_TITLES) == (
        "Família de Capivaras na Natureza Momentos Incríveis e ..."
    )


def test_cuts_where_the_title_of_another_result_starts() -> None:
    other_result_title = "Pedras para Revestimento de Lareira | Pedras Ouro e Prata"
    glued = (
        "Como dar BRILHO EM PEDRAS COMUNS - YouTube"
        f"{other_result_title}"
        "Unhas Com Brilhantes PedrasLareira Com Pedras - MercadoLivre"
    )

    assert first_title(glued, [other_result_title]) == "Como dar BRILHO EM PEDRAS COMUNS - YouTube"


def test_takes_the_earliest_sign_of_glue() -> None:
    other_result_title = "Flor de lótus: descubra o significado e como plantar no jardim"
    glued = (
        "A Flor de Lotus (Nelumbo Nucifera) do Laguinho de 62x18 ..."
        "Uma linda flor da minha rosa do deserto lavei o laguinho e ..."
        f"{other_result_title}"
    )

    assert first_title(glued, [other_result_title]) == (
        "A Flor de Lotus (Nelumbo Nucifera) do Laguinho de 62x18 ..."
    )


def test_falls_back_to_a_lowercase_letter_touching_an_uppercase_one() -> None:
    glued = (
        "Satélites artificiais: o que são, os tipos e para quê servem"
        "Satélites - Agência Espacial Brasileira"
    )

    assert first_title(glued, NO_OTHER_TITLES) == (
        "Satélites artificiais: o que são, os tipos e para quê servem"
    )


def test_keeps_a_long_title_without_any_sign_of_glue() -> None:
    title = "a" * 100

    assert first_title(title, NO_OTHER_TITLES) == title
