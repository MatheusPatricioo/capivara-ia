class_name TalkButton
extends Button

## Push to talk: while her creator holds this button, the brain records the microphone.
## Releasing it, or the window losing focus while held, ends the recording, so the
## microphone is never left on.

signal heard(text: String)

const IDLE_TEXT: String = "Falar"
const TALKING_TEXT: String = "Ouvindo…"
const OFFLINE_TEXT: String = "Sem cérebro"
const IDLE_TOOLTIP: String = "Segure enquanto fala com ela."

var _is_talking: bool = false


func _ready() -> void:
	text = IDLE_TEXT
	tooltip_text = IDLE_TOOLTIP
	focus_mode = Control.FOCUS_NONE
	button_down.connect(_start_talking)
	button_up.connect(_stop_talking)
	Brain.creator_heard.connect(func(heard_text: String) -> void: heard.emit(heard_text))


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_stop_talking()


func _start_talking() -> void:
	if not Brain.set_creator_talking(true):
		text = OFFLINE_TEXT
		return
	_is_talking = true
	text = TALKING_TEXT


func _stop_talking() -> void:
	text = IDLE_TEXT
	if not _is_talking:
		return
	_is_talking = false
	Brain.set_creator_talking(false)
