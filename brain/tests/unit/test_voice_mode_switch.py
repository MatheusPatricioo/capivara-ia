from src.application.voice_mode_switch import VoiceModeSwitch
from src.domain.speech import VoiceMode


def test_starts_in_conversation_mode() -> None:
    assert VoiceModeSwitch().mode is VoiceMode.CONVERSATION


def test_keeps_the_mode_it_was_switched_to() -> None:
    switch = VoiceModeSwitch()

    switch.switch_to(VoiceMode.MUTE)

    assert switch.mode is VoiceMode.MUTE
