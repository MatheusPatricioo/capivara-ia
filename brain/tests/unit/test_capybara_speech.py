import logging

import pytest

from src.application.capybara_speech import CapybaraSpeech
from src.domain.speech import SpeechError, SpokenAudio
from tests.fakes.speech import (
    FAKE_SAMPLE_RATE,
    BrokenRecognizer,
    BrokenSynthesizer,
    RecordingSpeaker,
    RecordingSynthesizer,
    ScriptedRecognizer,
    recording_of,
)

SILENCE = SpokenAudio(b"", FAKE_SAMPLE_RATE)


@pytest.fixture
def recognizer() -> ScriptedRecognizer:
    return ScriptedRecognizer()


@pytest.fixture
def synthesizer() -> RecordingSynthesizer:
    return RecordingSynthesizer()


@pytest.fixture
def speaker() -> RecordingSpeaker:
    return RecordingSpeaker()


@pytest.fixture
def speech(
    recognizer: ScriptedRecognizer, synthesizer: RecordingSynthesizer, speaker: RecordingSpeaker
) -> CapybaraSpeech:
    return CapybaraSpeech(recognizer, synthesizer, speaker)


def test_hear_returns_what_was_said_without_surrounding_spaces(speech: CapybaraSpeech) -> None:
    assert speech.hear(recording_of("  Oi, capivara!  ")) == "Oi, capivara!"


def test_hear_does_not_ask_the_recognizer_about_silence(
    speech: CapybaraSpeech, recognizer: ScriptedRecognizer
) -> None:
    heard = speech.hear(SILENCE)

    assert (heard, recognizer.heard_recordings) == ("", [])


def test_hear_lets_a_recognizer_failure_reach_the_chat(
    synthesizer: RecordingSynthesizer, speaker: RecordingSpeaker
) -> None:
    deaf_speech = CapybaraSpeech(BrokenRecognizer(), synthesizer, speaker)

    with pytest.raises(SpeechError):
        deaf_speech.hear(recording_of("Oi"))


def test_say_plays_the_reply_without_markdown_or_emojis(
    speech: CapybaraSpeech, speaker: RecordingSpeaker
) -> None:
    speech.say("Eu **amo** água! 🦫")

    assert speaker.played_audios == [recording_of("Eu amo água!")]


def test_say_stays_quiet_when_nothing_in_the_reply_can_be_said(
    speech: CapybaraSpeech, synthesizer: RecordingSynthesizer
) -> None:
    speech.say("🦫✨")

    assert synthesizer.synthesized_texts == []


def test_say_only_logs_a_voice_failure(
    recognizer: ScriptedRecognizer,
    speaker: RecordingSpeaker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mute_speech = CapybaraSpeech(recognizer, BrokenSynthesizer(), speaker)

    with caplog.at_level(logging.WARNING):
        mute_speech.say("Oi, criador!")

    assert "could not say her reply" in caplog.text
