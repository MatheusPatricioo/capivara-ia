"""Builds the voice chosen in the .env: the engine (Piper or Kokoro) and, when set, the
effect that makes it higher or changes its pace. Imported only when a voice is wanted,
so the brain runs without the voice extra installed."""

from src.domain.speech import SpeechSynthesizer
from src.infrastructure.settings import Settings


def build_speech_synthesizer(settings: Settings) -> SpeechSynthesizer:
    """Raises SpeechError when a voice file is missing, and ImportError without the extra."""
    engine = build_voice_engine(settings)
    effect = settings.voice_effect()
    if effect.is_neutral:
        return engine
    from src.infrastructure.voice_effect import EffectSpeechSynthesizer

    return EffectSpeechSynthesizer(engine, effect)


def build_voice_engine(settings: Settings) -> SpeechSynthesizer:
    if settings.voice_engine == "kokoro":
        from src.infrastructure.kokoro_speech_synthesizer import KokoroSpeechSynthesizer

        return KokoroSpeechSynthesizer.load(
            settings.kokoro_model_path, settings.kokoro_voices_path, settings.kokoro_voice
        )
    from src.infrastructure.piper_speech_synthesizer import PiperSpeechSynthesizer

    return PiperSpeechSynthesizer.load(settings.voice_model_path)
