import logging
from dataclasses import replace
from datetime import date

import pytest

from src.application.attention_inbox import AttentionInbox
from src.application.inner_voice import InnerVoice
from src.application.related_discoveries import RelatedDiscoveries
from src.domain.attention import Attention
from src.domain.discovery import Discovery, DiscoveryHeadline, DiscoveryStorageError
from src.domain.discovery_memory import RememberedDiscovery
from src.domain.world_suggestion import WorldSuggestion
from tests.fakes.in_memory_suggestions import InMemorySuggestionArchive, a_suggestion

INVITATION = "(Você está sozinha. O que quer fazer?)"
MEMORY_TEMPLATE = "(Você já guardou:\n{discoveries}\nNão repita.)"
MAX_REMEMBERED_DISCOVERIES = 2
INNER_VOICE_LOGGER = "src.application.inner_voice"
NOTICED_TEMPLATE = "(Você reparou em:\n{noticed}\nPesquise se quiser.)"


class FakeCatalog:
    """Returns the given headlines and remembers the limit it was asked for."""

    def __init__(self, headlines: list[DiscoveryHeadline]) -> None:
        self.headlines = headlines
        self.requested_limits: list[int] = []

    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        self.requested_limits.append(limit)
        return self.headlines[:limit]


class BrokenCatalog:
    def latest_headlines(self, limit: int) -> list[DiscoveryHeadline]:
        raise DiscoveryStorageError("disk unplugged")


def build_inner_voice(catalog: FakeCatalog | BrokenCatalog) -> InnerVoice:
    return InnerVoice(INVITATION, catalog, MEMORY_TEMPLATE, MAX_REMEMBERED_DISCOVERIES)


@pytest.fixture
def catalog_with_discoveries() -> FakeCatalog:
    return FakeCatalog(
        [
            DiscoveryHeadline(title="Peixes de rio", topic="animais"),
            DiscoveryHeadline(title="Estrelas gêmeas", topic=""),
        ]
    )


def test_lists_the_saved_discoveries_before_the_invitation(
    catalog_with_discoveries: FakeCatalog,
) -> None:
    composed = build_inner_voice(catalog_with_discoveries).compose()

    assert composed == (
        "(Você já guardou:\n"
        "- Peixes de rio (tema: animais)\n"
        "- Estrelas gêmeas\n"
        "Não repita.)\n\n"
        f"{INVITATION}"
    )


def test_asks_the_catalog_for_the_configured_number_of_discoveries(
    catalog_with_discoveries: FakeCatalog,
) -> None:
    build_inner_voice(catalog_with_discoveries).compose()

    assert catalog_with_discoveries.requested_limits == [MAX_REMEMBERED_DISCOVERIES]


def test_is_just_the_invitation_when_nothing_was_saved_yet() -> None:
    assert build_inner_voice(FakeCatalog([])).compose() == INVITATION


def test_is_just_the_invitation_when_the_discoveries_cannot_be_read() -> None:
    assert build_inner_voice(BrokenCatalog()).compose() == INVITATION


def test_logs_a_warning_when_the_discoveries_cannot_be_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=INNER_VOICE_LOGGER)

    build_inner_voice(BrokenCatalog()).compose()

    assert caplog.messages == ["Could not remember the saved discoveries: disk unplugged"]


@pytest.fixture
def attention() -> AttentionInbox:
    return AttentionInbox(Attention(capacity=5, rest_seconds=600.0))


@pytest.fixture
def attentive_inner_voice(attention: AttentionInbox) -> InnerVoice:
    return InnerVoice(
        INVITATION,
        FakeCatalog([]),
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        attention=attention,
        noticed_template=NOTICED_TEMPLATE,
    )


FEELINGS = "(Por dentro: você está muito curiosa.)"


def test_tells_how_she_feels_before_what_she_noticed(attention: AttentionInbox) -> None:
    inner_voice = InnerVoice(
        INVITATION,
        FakeCatalog([]),
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        attention=attention,
        noticed_template=NOTICED_TEMPLATE,
        feelings=lambda: FEELINGS,
    )
    attention.notice("mushrooms", "cogumelos vermelhos")

    assert inner_voice.compose() == (
        f"{FEELINGS}\n\n"
        "(Você reparou em:\n- cogumelos vermelhos\nPesquise se quiser.)\n\n"
        f"{INVITATION}"
    )


def test_tells_how_she_feels_even_when_she_noticed_nothing() -> None:
    inner_voice = InnerVoice(
        INVITATION,
        FakeCatalog([]),
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        feelings=lambda: FEELINGS,
    )

    assert inner_voice.compose() == f"{FEELINGS}\n\n{INVITATION}"


def test_lists_what_she_noticed_before_the_invitation(
    attentive_inner_voice: InnerVoice, attention: AttentionInbox
) -> None:
    attention.notice("water_lilies", "vitórias-régias no laguinho")
    attention.notice("mushrooms", "cogumelos vermelhos")

    assert attentive_inner_voice.compose() == (
        "(Você reparou em:\n"
        "- cogumelos vermelhos\n"
        "- vitórias-régias no laguinho\n"
        "Pesquise se quiser.)\n\n"
        f"{INVITATION}"
    )


def test_puts_the_memory_before_what_she_noticed(
    catalog_with_discoveries: FakeCatalog, attention: AttentionInbox
) -> None:
    inner_voice = InnerVoice(
        INVITATION,
        catalog_with_discoveries,
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        attention=attention,
        noticed_template=NOTICED_TEMPLATE,
    )
    attention.notice("mushrooms", "cogumelos vermelhos")

    composed = inner_voice.compose()

    assert composed.index("Você já guardou") < composed.index("Você reparou em")


def test_is_just_the_invitation_when_she_noticed_nothing(
    attentive_inner_voice: InnerVoice,
) -> None:
    assert attentive_inner_voice.compose() == INVITATION


def test_releasing_lets_go_of_what_was_offered(
    attentive_inner_voice: InnerVoice, attention: AttentionInbox
) -> None:
    attention.notice("mushrooms", "cogumelos vermelhos")
    attentive_inner_voice.compose()

    attentive_inner_voice.release_offered()

    assert attention.pending() == ()


def test_releasing_keeps_what_she_noticed_after_the_inner_voice_was_composed(
    attentive_inner_voice: InnerVoice, attention: AttentionInbox
) -> None:
    attention.notice("mushrooms", "cogumelos vermelhos")
    attentive_inner_voice.compose()
    attention.notice("big_oak", "um carvalho enorme")

    attentive_inner_voice.release_offered()

    assert [point.thing_id for point in attention.pending()] == ["big_oak"]


def test_releasing_twice_does_not_let_go_of_anything_new(
    attentive_inner_voice: InnerVoice, attention: AttentionInbox
) -> None:
    attention.notice("mushrooms", "cogumelos vermelhos")
    attentive_inner_voice.compose()
    attentive_inner_voice.release_offered()
    attention.notice("big_oak", "um carvalho enorme")

    attentive_inner_voice.release_offered()

    assert [point.thing_id for point in attention.pending()] == ["big_oak"]


RELATED_TEMPLATE = "(Você já aprendeu:\n{related}\nVá além.)"
LILIES_DESCRIPTION = "vitórias-régias no laguinho"
VICTORIA = Discovery(
    title="Vitória-régia",
    topic="plantas",
    summary="As folhas boiam e aguentam peso.\n\nA flor abre à noite.",
    sources=("https://example.com/vitoria",),
    discovered_on=date(2026, 11, 24),
)


class FixedRelatedMemory:
    """Recalls the same discovery, with the same similarity, for any subject."""

    def __init__(self, remembered: list[RememberedDiscovery]) -> None:
        self._remembered = remembered
        self.recalled_subjects: list[str] = []

    def remember(self, file_name: str, discovery: Discovery) -> None:
        raise AssertionError("the inner voice must only recall")

    def recall(self, text: str, limit: int) -> list[RememberedDiscovery]:
        self.recalled_subjects.append(text)
        return self._remembered[:limit]


def build_inner_voice_with_related(
    attention: AttentionInbox, memory: FixedRelatedMemory
) -> InnerVoice:
    return InnerVoice(
        INVITATION,
        FakeCatalog([]),
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        attention=attention,
        noticed_template=NOTICED_TEMPLATE,
        related=RelatedDiscoveries(memory, min_similarity=0.70),
        related_template=RELATED_TEMPLATE,
    )


@pytest.fixture
def related_memory() -> FixedRelatedMemory:
    return FixedRelatedMemory([RememberedDiscovery(VICTORIA, 0.81)])


def test_brings_back_the_related_discoveries_before_what_she_noticed(
    attention: AttentionInbox, related_memory: FixedRelatedMemory
) -> None:
    attention.notice("water_lilies", LILIES_DESCRIPTION)

    composed = build_inner_voice_with_related(attention, related_memory).compose()

    assert composed == (
        "(Você já aprendeu:\n"
        "- Vitória-régia: As folhas boiam e aguentam peso. A flor abre à noite.\n"
        "Vá além.)\n\n"
        "(Você reparou em:\n"
        f"- {LILIES_DESCRIPTION}\n"
        "Pesquise se quiser.)\n\n"
        f"{INVITATION}"
    )


def test_looks_for_related_discoveries_with_what_she_noticed(
    attention: AttentionInbox, related_memory: FixedRelatedMemory
) -> None:
    attention.notice("water_lilies", LILIES_DESCRIPTION)

    build_inner_voice_with_related(attention, related_memory).compose()

    assert related_memory.recalled_subjects == [LILIES_DESCRIPTION]


def test_does_not_look_for_related_discoveries_when_she_noticed_nothing(
    attention: AttentionInbox, related_memory: FixedRelatedMemory
) -> None:
    build_inner_voice_with_related(attention, related_memory).compose()

    assert related_memory.recalled_subjects == []


def test_has_no_related_section_when_nothing_saved_is_close_enough(
    attention: AttentionInbox,
) -> None:
    distant_memory = FixedRelatedMemory([RememberedDiscovery(VICTORIA, 0.50)])
    attention.notice("water_lilies", LILIES_DESCRIPTION)

    composed = build_inner_voice_with_related(attention, distant_memory).compose()

    assert "Você já aprendeu" not in composed


def test_releasing_logs_what_she_thought_about(
    attentive_inner_voice: InnerVoice,
    attention: AttentionInbox,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=INNER_VOICE_LOGGER)
    attention.notice("mushrooms", "cogumelos vermelhos")
    attentive_inner_voice.compose()

    attentive_inner_voice.release_offered()

    assert caplog.messages == ["She thought about what she noticed: mushrooms"]


SUGGESTIONS_TEMPLATE = "(Você já pediu:\n{suggestions}\nNão peça de novo.)"
LILIES_REQUEST = "Um laguinho com vitórias-régias"


def build_inner_voice_with_suggestions(
    suggestions: list[WorldSuggestion], attention: AttentionInbox | None = None
) -> InnerVoice:
    return InnerVoice(
        INVITATION,
        FakeCatalog([]),
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        attention=attention,
        noticed_template=NOTICED_TEMPLATE,
        suggestions=InMemorySuggestionArchive(suggestions),
        suggestions_template=SUGGESTIONS_TEMPLATE,
    )


def test_lists_the_earlier_suggestions_newest_first_before_the_invitation() -> None:
    composed = build_inner_voice_with_suggestions(
        [a_suggestion(LILIES_REQUEST), a_suggestion("Vaga-lumes no jardim")]
    ).compose()

    assert composed == (
        "(Você já pediu:\n"
        "- Vaga-lumes no jardim (esperando)\n"
        "- Um laguinho com vitórias-régias (esperando)\n"
        "Não peça de novo.)\n\n"
        f"{INVITATION}"
    )


def test_tells_which_earlier_suggestions_were_built() -> None:
    composed = build_inner_voice_with_suggestions(
        [a_suggestion(LILIES_REQUEST).built("water_lilies")]
    ).compose()

    assert "- Um laguinho com vitórias-régias (o criador construiu!)" in composed


def test_lists_at_most_the_ten_newest_suggestions() -> None:
    suggestions = [a_suggestion(f"Pedido {number}") for number in range(1, 13)]

    composed = build_inner_voice_with_suggestions(suggestions).compose()

    assert "- Pedido 12 (" in composed
    assert "- Pedido 3 (" in composed
    assert "- Pedido 2 (" not in composed


def test_leaves_the_suggestions_out_when_she_never_suggested_anything() -> None:
    assert build_inner_voice_with_suggestions([]).compose() == INVITATION


def test_puts_the_earlier_suggestions_right_after_the_saved_discoveries(
    catalog_with_discoveries: FakeCatalog,
) -> None:
    inner_voice = InnerVoice(
        INVITATION,
        catalog_with_discoveries,
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        suggestions=InMemorySuggestionArchive([a_suggestion("Vaga-lumes no jardim")]),
        suggestions_template=SUGGESTIONS_TEMPLATE,
    )

    composed = inner_voice.compose()

    assert composed.index("Você já guardou") < composed.index("Você já pediu")


def test_tells_her_a_noticed_thing_is_the_wish_that_was_built(
    attention: AttentionInbox,
) -> None:
    inner_voice = build_inner_voice_with_suggestions(
        [a_suggestion(LILIES_REQUEST).built("water_lilies")], attention
    )
    attention.notice("water_lilies", "vitórias-régias no laguinho")

    composed = inner_voice.compose()

    assert (
        "- vitórias-régias no laguinho (é o que você pediu pro criador: "
        '"Um laguinho com vitórias-régias". Ele construiu pra você!)'
    ) in composed


def test_does_not_link_a_noticed_thing_to_a_suggestion_still_waiting(
    attention: AttentionInbox,
) -> None:
    waiting = replace(a_suggestion(LILIES_REQUEST), world_thing_id="water_lilies")
    inner_voice = build_inner_voice_with_suggestions([waiting], attention)
    attention.notice("water_lilies", "vitórias-régias no laguinho")

    composed = inner_voice.compose()

    assert "- vitórias-régias no laguinho\n" in composed


def test_leaves_other_noticed_things_as_they_are(attention: AttentionInbox) -> None:
    inner_voice = build_inner_voice_with_suggestions(
        [a_suggestion(LILIES_REQUEST).built("water_lilies")], attention
    )
    attention.notice("mushrooms", "cogumelos vermelhos")

    composed = inner_voice.compose()

    assert "- cogumelos vermelhos\n" in composed


REPLIES = "(O criador respondeu sua cartinha!)"


def test_tells_his_replies_before_how_she_feels() -> None:
    inner_voice = InnerVoice(
        INVITATION,
        FakeCatalog([]),
        MEMORY_TEMPLATE,
        MAX_REMEMBERED_DISCOVERIES,
        feelings=lambda: FEELINGS,
        replies=lambda: REPLIES,
    )

    assert inner_voice.compose() == f"{REPLIES}\n\n{FEELINGS}\n\n{INVITATION}"


def test_says_nothing_about_replies_when_there_are_none() -> None:
    inner_voice = InnerVoice(
        INVITATION, FakeCatalog([]), MEMORY_TEMPLATE, MAX_REMEMBERED_DISCOVERIES, replies=str
    )

    assert inner_voice.compose() == INVITATION
