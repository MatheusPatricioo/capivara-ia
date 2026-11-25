from src.domain.speech import SpokenAudio

ONE_SECOND_AT_16_KHZ = bytes(2 * 16000)


def test_duration_comes_from_the_sample_count_and_rate() -> None:
    audio = SpokenAudio(ONE_SECOND_AT_16_KHZ, sample_rate=16000)

    assert audio.duration_seconds == 1.0


def test_audio_without_samples_is_silent() -> None:
    assert SpokenAudio(b"", sample_rate=16000).is_silent


def test_audio_with_samples_is_not_silent() -> None:
    assert not SpokenAudio(ONE_SECOND_AT_16_KHZ, sample_rate=16000).is_silent
