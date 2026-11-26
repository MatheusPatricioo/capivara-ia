import numpy as np
from numpy.typing import NDArray

from src.domain.speech import SpokenAudio

PCM_DTYPE = "<i2"
"""16-bit signed integers, little endian: the layout of SpokenAudio.samples."""
PCM_FULL_SCALE = 32768.0
"""The largest 16-bit sample, used to bring samples into the [-1, 1] range."""


def pcm_array(audio: SpokenAudio) -> NDArray[np.int16]:
    """The samples as a numpy array of integers, ready for the sound card."""
    return np.frombuffer(audio.samples, dtype=PCM_DTYPE)


def pcm_audio(samples: NDArray[np.float32], sample_rate: int) -> SpokenAudio:
    """Float samples in [-1, 1], like the ones speech models make, as 16-bit PCM audio.
    Anything beyond the range is clipped, instead of wrapping around into a loud crack."""
    clipped = np.clip(samples, -1.0, 1.0)
    integers = np.round(clipped * (PCM_FULL_SCALE - 1)).astype(PCM_DTYPE)
    return SpokenAudio(integers.tobytes(), sample_rate)


def float_samples(audio: SpokenAudio, sample_rate: int) -> NDArray[np.float32]:
    """The samples as floats in [-1, 1] at the given rate, the input speech models expect.
    A different rate is resampled by linear interpolation: for each new instant, the
    value on the straight line between the two original samples around it."""
    samples = pcm_array(audio).astype(np.float32) / PCM_FULL_SCALE
    if audio.sample_rate == sample_rate:
        return samples
    resampled_count = round(len(samples) * sample_rate / audio.sample_rate)
    original_instants = np.arange(len(samples)) / audio.sample_rate
    resampled_instants = np.arange(resampled_count) / sample_rate
    resampled: NDArray[np.float32] = np.interp(
        resampled_instants, original_instants, samples
    ).astype(np.float32)
    return resampled
