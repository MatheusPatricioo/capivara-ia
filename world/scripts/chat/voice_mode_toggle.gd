class_name VoiceModeToggle
extends Button

## A small pill in the chat bar that switches her voice between "Voz" (she says her
## replies out loud) and "Mudo" (only the balloon). The choice lives in the Brain autoload,
## which sends it to the brain; this button only shows it and changes it.

const VOICE_TEXT: String = "Voz"
const MUTE_TEXT: String = "Mudo"
const VOICE_TOOLTIP: String = "Ela fala as respostas. Clique para deixar só o balão."
const MUTE_TOOLTIP: String = "Só o balão, sem voz. Clique para ela falar."


func _ready() -> void:
	toggle_mode = true
	focus_mode = Control.FOCUS_NONE
	toggled.connect(_on_toggled)
	Brain.voice_mode_changed.connect(_show_mode)
	_show_mode(Brain.voice_mode)


## Pressed means her voice is on.
func _on_toggled(voice_is_on: bool) -> void:
	Brain.set_voice_mode(Brain.VOICE_MODE_CONVERSATION if voice_is_on else Brain.VOICE_MODE_MUTE)


func _show_mode(mode: StringName) -> void:
	var voice_is_on: bool = mode == Brain.VOICE_MODE_CONVERSATION
	set_pressed_no_signal(voice_is_on)
	text = VOICE_TEXT if voice_is_on else MUTE_TEXT
	tooltip_text = VOICE_TOOLTIP if voice_is_on else MUTE_TOOLTIP
