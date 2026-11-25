import numpy as np

from src.domain.speech import SpokenAudio
from src.infrastructure.pcm_samples import float_samples, pcm_array


def audio_of(samples: list[int], sample_rate: int) -> SpokenAudio:
    return SpokenAudio(np.array(samples, dtype="<i2").tobytes(), sample_rate)


def test_pcm_array_reads_the_16_bit_samples() -> None:
    audio = audio_of([0, 1000, -1000], sample_rate=16000)

    assert pcm_array(audio).tolist() == [0, 1000, -1000]


def test_float_samples_scale_into_minus_one_to_one() -> None:
    audio = audio_of([-32768, 0, 16384], sample_rate=16000)

    assert float_samples(audio, 16000).tolist() == [-1.0, 0.0, 0.5]


def test_float_samples_are_float32_for_the_speech_model() -> None:
    audio = audio_of([0, 16384], sample_rate=16000)

    assert float_samples(audio, 16000).dtype == np.float32


def test_resampling_to_half_the_rate_keeps_half_the_samples() -> None:
    audio = audio_of([0] * 32000, sample_rate=32000)

    assert len(float_samples(audio, 16000)) == 16000


def test_resampling_up_fills_the_new_instants_on_the_line_between_samples() -> None:
    audio = audio_of([0, 16384], sample_rate=2)

    assert float_samples(audio, 4).tolist() == [0.0, 0.25, 0.5, 0.5]
