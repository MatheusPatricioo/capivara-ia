import numpy as np
import pytest

from src.domain.speech import SpokenAudio, VoiceEffect
from src.infrastructure.pcm_samples import float_samples, pcm_audio
from src.infrastructure.voice_effect import EffectSpeechSynthesizer, apply_voice_effect

SAMPLE_RATE = 24000
TONE_HERTZ = 220.0
ONE_SECOND = 1.0


def tone(seconds: float = ONE_SECOND, hertz: float = TONE_HERTZ) -> SpokenAudio:
    instants = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return pcm_audio((0.5 * np.sin(2 * np.pi * hertz * instants)).astype(np.float32), SAMPLE_RATE)


def strongest_frequency(audio: SpokenAudio) -> float:
    samples = float_samples(audio, audio.sample_rate)
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    frequencies = np.fft.rfftfreq(len(samples), 1 / audio.sample_rate)
    return float(frequencies[int(np.argmax(spectrum))])


class ToneSynthesizer:
    def synthesize(self, text: str) -> SpokenAudio:
        return tone()


def test_a_neutral_effect_leaves_the_voice_as_it_was() -> None:
    audio = tone()

    assert apply_voice_effect(audio, VoiceEffect()) is audio


def test_silence_stays_silent() -> None:
    silence = SpokenAudio(b"", SAMPLE_RATE)

    assert apply_voice_effect(silence, VoiceEffect(pitch_semitones=5)) is silence


def test_an_octave_up_doubles_the_pitch() -> None:
    raised = apply_voice_effect(tone(), VoiceEffect(pitch_semitones=12))

    assert strongest_frequency(raised) == pytest.approx(2 * TONE_HERTZ, rel=0.03)


def test_a_higher_pitch_keeps_the_length() -> None:
    raised = apply_voice_effect(tone(), VoiceEffect(pitch_semitones=5))

    assert raised.duration_seconds == pytest.approx(ONE_SECOND, rel=0.03)


def test_a_faster_speed_shortens_the_voice() -> None:
    faster = apply_voice_effect(tone(), VoiceEffect(speed=2.0))

    assert faster.duration_seconds == pytest.approx(ONE_SECOND / 2, rel=0.03)


def test_a_faster_speed_keeps_the_pitch() -> None:
    faster = apply_voice_effect(tone(), VoiceEffect(speed=1.5))

    assert strongest_frequency(faster) == pytest.approx(TONE_HERTZ, rel=0.03)


def test_the_effect_changes_what_the_wrapped_synthesizer_says() -> None:
    synthesizer = EffectSpeechSynthesizer(ToneSynthesizer(), VoiceEffect(pitch_semitones=12))

    spoken = synthesizer.synthesize("Oi!")

    assert strongest_frequency(spoken) == pytest.approx(2 * TONE_HERTZ, rel=0.03)


def test_five_semitones_up_raise_every_frequency_by_about_a_third() -> None:
    assert VoiceEffect(pitch_semitones=5).pitch_ratio == pytest.approx(1.335, rel=0.001)


def test_an_effect_without_changes_is_neutral() -> None:
    assert VoiceEffect().is_neutral
