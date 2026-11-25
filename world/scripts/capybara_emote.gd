class_name CapybaraEmote
extends Label3D

## A small symbol that pops up above the capybara's head for her strongest feeling:
## a note for joy, a question mark for curiosity, dots for loneliness...
## It appears when the feeling changes and again from time to time while it lasts.

const SYMBOLS: Dictionary[String, String] = {
	"joy": "♪",
	"curiosity": "?",
	"enthusiasm": "!",
	"flow": "✦",
	"pride": "★",
	"gratitude": "♥",
	"relief": "~",
	"determination": "»",
	"surprise": "!?",
	"loneliness": "…",
	"sadness": ";_;",
	"hurt": "♡",
	"insecurity": "?…",
	"apathy": "zzz",
	"boredom": "…zz",
	"irritation": "#",
	"frustration": "#!",
	"impatience": "…!",
	"disappointment": "…",
	"resignation": "…",
}

## Feelings weaker than this show no symbol.
@export var min_intensity: float = 0.35
## Seconds the symbol stays fully visible.
@export var show_seconds: float = 3.5
## Seconds between two pops of the same feeling.
@export var repeat_seconds: float = 25.0
## Seconds to fade in and out.
@export var fade_seconds: float = 0.4

var _symbol: String = ""
var _repeat_timer: Timer = Timer.new()
var _pop_tween: Tween


func _ready() -> void:
	modulate.a = 0.0
	_repeat_timer.wait_time = repeat_seconds
	_repeat_timer.timeout.connect(_pop)
	add_child(_repeat_timer)
	Brain.feelings_changed.connect(_on_feelings_changed)


func _on_feelings_changed(
	emotion: StringName, intensity: float, _valence: float, _arousal: float
) -> void:
	var symbol: String = SYMBOLS.get(String(emotion), "") if intensity >= min_intensity else ""
	if symbol == _symbol:
		return
	_symbol = symbol
	if _symbol.is_empty():
		_repeat_timer.stop()
		return
	_pop()
	_repeat_timer.start()


func _pop() -> void:
	if _symbol.is_empty():
		return
	text = _symbol
	if _pop_tween != null:
		_pop_tween.kill()
	_pop_tween = create_tween()
	_pop_tween.tween_property(self, "modulate:a", 1.0, fade_seconds)
	_pop_tween.tween_interval(show_seconds)
	_pop_tween.tween_property(self, "modulate:a", 0.0, fade_seconds)
