class_name CapybaraSpeechBalloon
extends Label3D

## Her words in a balloon above her head. It shows "…" while she thinks about what her
## creator said, then her reply for the time it takes to read it. A newer speech replaces
## the one on screen at once; an older one that arrives late is dropped.

const THINKING_TEXT: String = "…"
const NO_SPEECH_YET: int = 0

## Reading time per character of the reply, in seconds.
@export var seconds_per_character: float = 0.06
## Shortest time a reply stays, even a one-word reply.
@export var min_seconds: float = 3.0
## Longest time a reply stays, so a long reply does not cover her for minutes.
@export var max_seconds: float = 30.0
## How long "…" waits for her reply before giving up (the brain may be busy or offline).
@export var thinking_max_seconds: float = 90.0

var _shown_speech_id: int = NO_SPEECH_YET
var _hide_timer: Timer = Timer.new()


func _ready() -> void:
	visible = false
	_hide_timer.one_shot = true
	_hide_timer.timeout.connect(hide)
	add_child(_hide_timer)
	Brain.creator_message_sent.connect(_show_thinking)
	Brain.speech_received.connect(_on_speech_received)
	Brain.connection_changed.connect(_on_connection_changed)


func _show_thinking(_text: String) -> void:
	_show_for(THINKING_TEXT, thinking_max_seconds)


func _on_speech_received(speech_id: int, caption: String) -> void:
	if speech_id <= _shown_speech_id or caption.is_empty():
		return
	_shown_speech_id = speech_id
	var reading_seconds: float = caption.length() * seconds_per_character
	_show_for(caption, clampf(reading_seconds, min_seconds, max_seconds))


func _show_for(balloon_text: String, seconds: float) -> void:
	text = balloon_text
	show()
	_hide_timer.start(seconds)


## A restarted brain counts its speeches from 1 again.
func _on_connection_changed(brain_is_connected: bool) -> void:
	if brain_is_connected:
		_shown_speech_id = NO_SPEECH_YET
