"""Says the same sentence with each voice and saves one WAV per voice, to listen and pick.

python -m src.compare_voices
python -m src.compare_voices --frase "Oi, criador!" --pasta D:/vozes
"""

import argparse
import sys
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.domain.speech import (
    BYTES_PER_SAMPLE,
    SpeechError,
    SpeechSynthesizer,
    SpokenAudio,
    VoiceEffect,
)
from src.infrastructure.kokoro_speech_synthesizer import KokoroSpeechSynthesizer
from src.infrastructure.piper_speech_synthesizer import PiperSpeechSynthesizer
from src.infrastructure.settings import PROJECT_ROOT, Settings
from src.infrastructure.voice_effect import apply_voice_effect

DEFAULT_SENTENCE = (
    "Oi, criador! Hoje eu fiquei olhando as estrelas lá do laguinho. "
    "Você sabia que algumas já nem existem mais? Que mistério!"
)
DEFAULT_FOLDER = PROJECT_ROOT / "brain" / "voices" / "comparacao"
MONO = 1


@dataclass(frozen=True)
class VoiceVariant:
    file_name: str
    engine: str
    effect: VoiceEffect


VARIANTS = (
    VoiceVariant("1-piper-faber.wav", "piper", VoiceEffect()),
    VoiceVariant("2-kokoro-dora.wav", "kokoro", VoiceEffect()),
    VoiceVariant("3-kokoro-dora-mais-3-semitons.wav", "kokoro", VoiceEffect(pitch_semitones=3)),
    VoiceVariant("4-kokoro-dora-mais-5-semitons.wav", "kokoro", VoiceEffect(pitch_semitones=5)),
    VoiceVariant(
        "5-kokoro-dora-mais-4-semitons-mais-rapida.wav",
        "kokoro",
        VoiceEffect(pitch_semitones=4, speed=1.1),
    ),
)


def main() -> None:
    arguments = parse_arguments(sys.argv[1:])
    settings = Settings()
    engines = load_engines(settings)
    arguments.pasta.mkdir(parents=True, exist_ok=True)
    spoken_by_engine = {
        name: engine.synthesize(arguments.frase) for name, engine in engines.items()
    }
    for variant in VARIANTS:
        if variant.engine not in spoken_by_engine:
            continue
        audio = apply_voice_effect(spoken_by_engine[variant.engine], variant.effect)
        path = arguments.pasta / variant.file_name
        save_wav(audio, path)
        print(f"{path}  ({audio.duration_seconds:.1f} s)")
    print(f"\nPronto: abra a pasta {arguments.pasta} e ouça na ordem.")


def parse_arguments(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m src.compare_voices", description=__doc__)
    parser.add_argument("--frase", default=DEFAULT_SENTENCE, help="o que as vozes vão dizer")
    parser.add_argument("--pasta", type=Path, default=DEFAULT_FOLDER, help="onde salvar os WAV")
    return parser.parse_args(arguments)


def load_engines(settings: Settings) -> dict[str, SpeechSynthesizer]:
    """Every engine that loads; a missing one is skipped with the reason."""
    loaders: dict[str, Callable[[], SpeechSynthesizer]] = {
        "piper": lambda: PiperSpeechSynthesizer.load(settings.voice_model_path),
        "kokoro": lambda: KokoroSpeechSynthesizer.load(
            settings.kokoro_model_path, settings.kokoro_voices_path, settings.kokoro_voice
        ),
    }
    engines: dict[str, SpeechSynthesizer] = {}
    for name, load in loaders.items():
        try:
            engines[name] = load()
        except SpeechError as error:
            print(f"Sem {name}: {error}", file=sys.stderr)
    return engines


def save_wav(audio: SpokenAudio, path: Path) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(MONO)
        wav_file.setsampwidth(BYTES_PER_SAMPLE)
        wav_file.setframerate(audio.sample_rate)
        wav_file.writeframes(audio.samples)


if __name__ == "__main__":
    main()
