"""Her voice made higher and faster or slower, after any synthesizer: Piper, Kokoro or
another one behind SpeechSynthesizer."""

import numpy as np
from numpy.typing import NDArray

from src.domain.speech import SpeechSynthesizer, SpokenAudio, VoiceEffect
from src.infrastructure.pcm_samples import float_samples, pcm_audio

FRAME_SECONDS = 0.03
"""Each slice of sound WSOLA moves around: long enough to hold a few voice cycles."""
SEARCH_SECONDS = 0.01
"""How far WSOLA looks around the ideal spot for the slice that continues the sound best."""
MIN_WINDOW_SUM = 1e-6


class EffectSpeechSynthesizer:
    """Decorator: the wrapped synthesizer speaks, then the effect changes the voice."""

    def __init__(self, synthesizer: SpeechSynthesizer, effect: VoiceEffect) -> None:
        self._synthesizer = synthesizer
        self._effect = effect

    def synthesize(self, text: str) -> SpokenAudio:
        return apply_voice_effect(self._synthesizer.synthesize(text), self._effect)


def apply_voice_effect(audio: SpokenAudio, effect: VoiceEffect) -> SpokenAudio:
    """Raises the pitch by resampling: played at the same rate, fewer samples sound higher
    and faster, with the formants raised too, which is what makes a voice sound like a
    child's. Then WSOLA fixes the pace: back to the original length, times the speed."""
    if effect.is_neutral or audio.is_silent:
        return audio
    samples = float_samples(audio, audio.sample_rate)
    raised = _resample(samples, effect.pitch_ratio)
    paced = time_stretch(raised, effect.speed / effect.pitch_ratio, audio.sample_rate)
    return pcm_audio(paced, audio.sample_rate)


def _resample(samples: NDArray[np.float32], ratio: float) -> NDArray[np.float32]:
    """Reads the samples ratio times faster, by linear interpolation."""
    if ratio == 1.0:
        return samples
    new_positions = np.arange(0.0, len(samples) - 1, ratio)
    resampled: NDArray[np.float32] = np.interp(
        new_positions, np.arange(len(samples)), samples
    ).astype(np.float32)
    return resampled


def time_stretch(
    samples: NDArray[np.float32], rate: float, sample_rate: int
) -> NDArray[np.float32]:
    """WSOLA (waveform similarity overlap-add): the sound is cut into overlapping slices
    and glued back with a different spacing, so it lasts 1/rate as long with the same
    pitch. Each slice is taken a little before or after its ideal spot, wherever it best
    continues the slice before it, so the glued waves do not clash.
    """
    if rate == 1.0:
        return samples
    frame = int(FRAME_SECONDS * sample_rate)
    hop = frame // 2
    tolerance = int(SEARCH_SECONDS * sample_rate)
    window = np.hanning(frame).astype(np.float32)
    output_length = int(len(samples) / rate)
    padded = np.pad(samples, (tolerance, 2 * frame + 2 * tolerance))
    output = np.zeros(output_length + frame, dtype=np.float32)
    window_sum = np.zeros(output_length + frame, dtype=np.float32)
    previous_start = 0
    for index, output_start in enumerate(range(0, output_length, hop)):
        ideal_start = int(index * hop * rate)
        start = (
            ideal_start
            if index == 0
            else _best_start(padded, ideal_start, previous_start + hop, frame, tolerance)
        )
        slice_start = start + tolerance
        output[output_start : output_start + frame] += (
            padded[slice_start : slice_start + frame] * window
        )
        window_sum[output_start : output_start + frame] += window
        previous_start = start
    stretched = (output / np.maximum(window_sum, MIN_WINDOW_SUM)).astype(np.float32)
    return stretched[:output_length]


def _best_start(
    padded: NDArray[np.float32], ideal_start: int, natural_start: int, frame: int, tolerance: int
) -> int:
    """The start near ideal_start whose slice looks most like the natural continuation of
    the previous slice (the highest cross-correlation)."""
    continuation = padded[natural_start + tolerance : natural_start + tolerance + frame]
    region = padded[ideal_start : ideal_start + frame + 2 * tolerance]
    correlation = np.correlate(region, continuation, mode="valid")
    return ideal_start - tolerance + int(np.argmax(correlation))
