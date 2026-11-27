import logging

import pytest

from src.application.capybara_speech import CapybaraMouth, CapybaraSpeech, SpeakerOutput
from src.application.voice_mode_switch import VoiceModeSwitch
from src.domain.speech import SpeechError, SpokenAudio, VoiceMode
from tests.fakes.speech import (
    FAKE_SAMPLE_RATE,
    BrokenRecognizer,
    BrokenSynthesizer,
    RecordingSpeaker,
    RecordingSynthesizer,
    RecordingVoiceOutput,
    ScriptedRecognizer,
    recording_of,
)

SILENCE = SpokenAudio(b"", FAKE_SAMPLE_RATE)


class BrokenSpeaker:
    def play(self, audio: SpokenAudio) -> None:
        raise SpeechError("no sound card")


@pytest.fixture
def synthesizer() -> RecordingSynthesizer:
    return RecordingSynthesizer()


@pytest.fixture
def output() -> RecordingVoiceOutput:
    return RecordingVoiceOutput()


@pytest.fixture
def voice_mode() -> VoiceModeSwitch:
    return VoiceModeSwitch()


@pytest.fixture
def mouth(
    synthesizer: RecordingSynthesizer, output: RecordingVoiceOutput, voice_mode: VoiceModeSwitch
) -> CapybaraMouth:
    return CapybaraMouth(synthesizer, output, voice_mode)


@pytest.fixture
def recognizer() -> ScriptedRecognizer:
    return ScriptedRecognizer()


@pytest.fixture
def speech(recognizer: ScriptedRecognizer, mouth: CapybaraMouth) -> CapybaraSpeech:
    return CapybaraSpeech(recognizer, mouth)


def test_say_sends_the_clean_caption_with_her_voice(
    mouth: CapybaraMouth, output: RecordingVoiceOutput
) -> None:
    mouth.say("Eu **amo** água! 🦫")

    assert output.spoken == [("Eu amo água!", recording_of("Eu amo água!"))]


def test_muted_she_sends_only_the_caption(
    mouth: CapybaraMouth, output: RecordingVoiceOutput, voice_mode: VoiceModeSwitch
) -> None:
    voice_mode.switch_to(VoiceMode.MUTE)

    mouth.say("Oi, criador!")

    assert output.spoken == [("Oi, criador!", None)]


def test_muted_her_voice_is_not_even_synthesized(
    mouth: CapybaraMouth, synthesizer: RecordingSynthesizer, voice_mode: VoiceModeSwitch
) -> None:
    voice_mode.switch_to(VoiceMode.MUTE)

    mouth.say("Oi, criador!")

    assert synthesizer.synthesized_texts == []


def test_her_voice_is_not_synthesized_when_nobody_would_hear_it(
    synthesizer: RecordingSynthesizer,
) -> None:
    unheard_mouth = CapybaraMouth(synthesizer, RecordingVoiceOutput(plays_audio=False))

    unheard_mouth.say("Oi, criador!")

    assert synthesizer.synthesized_texts == []


def test_without_a_synthesizer_she_sends_only_the_caption(output: RecordingVoiceOutput) -> None:
    captions_only_mouth = CapybaraMouth(None, output)

    captions_only_mouth.say("Oi, criador!")

    assert output.spoken == [("Oi, criador!", None)]


def test_a_voice_failure_still_sends_the_caption(output: RecordingVoiceOutput) -> None:
    hoarse_mouth = CapybaraMouth(BrokenSynthesizer(), output)

    hoarse_mouth.say("Oi, criador!")

    assert output.spoken == [("Oi, criador!", None)]


def test_a_voice_failure_is_logged(
    output: RecordingVoiceOutput, caplog: pytest.LogCaptureFixture
) -> None:
    hoarse_mouth = CapybaraMouth(BrokenSynthesizer(), output)

    with caplog.at_level(logging.WARNING):
        hoarse_mouth.say("Oi, criador!")

    assert "could not say her reply" in caplog.text


def test_she_stays_quiet_when_nothing_in_the_reply_can_be_said(
    mouth: CapybaraMouth, output: RecordingVoiceOutput
) -> None:
    mouth.say("🦫✨")

    assert output.spoken == []


def test_the_speaker_output_plays_her_voice() -> None:
    speaker = RecordingSpeaker()

    SpeakerOutput(speaker).speak("Oi!", recording_of("Oi!"))

    assert speaker.played_audios == [recording_of("Oi!")]


def test_the_speaker_output_stays_quiet_without_a_voice() -> None:
    speaker = RecordingSpeaker()

    SpeakerOutput(speaker).speak("Oi!", None)

    assert speaker.played_audios == []


def test_the_speaker_output_only_logs_a_broken_speaker(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        SpeakerOutput(BrokenSpeaker()).speak("Oi!", recording_of("Oi!"))

    assert "could not play her voice" in caplog.text


def test_hear_returns_what_was_said_without_surrounding_spaces(speech: CapybaraSpeech) -> None:
    assert speech.hear(recording_of("  Oi, capivara!  ")) == "Oi, capivara!"


def test_hear_does_not_ask_the_recognizer_about_silence(
    speech: CapybaraSpeech, recognizer: ScriptedRecognizer
) -> None:
    heard = speech.hear(SILENCE)

    assert (heard, recognizer.heard_recordings) == ("", [])


def test_hear_lets_a_recognizer_failure_reach_the_chat(mouth: CapybaraMouth) -> None:
    deaf_speech = CapybaraSpeech(BrokenRecognizer(), mouth)

    with pytest.raises(SpeechError):
        deaf_speech.hear(recording_of("Oi"))


def test_speech_says_through_its_mouth(
    speech: CapybaraSpeech, output: RecordingVoiceOutput
) -> None:
    speech.say("Oi, criador!")

    assert output.spoken == [("Oi, criador!", recording_of("Oi, criador!"))]
