class_name ClipDirector
extends Node

## Turns the world into a film set when it runs to record a clip (ClipMode): the clip
## camera becomes the active one, the interface is hidden (only her speech balloon and
## emote stay, as part of the story) and the shots are chosen.
##
## With the "auto" shot it edits like a series: it opens wide, then cuts between medium and
## close every few seconds, and cuts to close when she speaks or her feeling changes. Cuts
## follow game time, so they land on the same frames in the Movie Maker.
## Without clip mode it does nothing, and the game keeps its normal camera.

## Seconds the opening wide shot lasts.
const OPENING_SECONDS: float = 3.0
## Seconds a medium or close shot lasts when nothing happens, picked between these two.
const MIN_SHOT_SECONDS: float = 4.0
const MAX_SHOT_SECONDS: float = 6.0
## A shot lasts at least this long before an event can cut away from it, so cuts never
## come one on top of another.
const MIN_SECONDS_BEFORE_CUT: float = 1.5
## How long the close shot holds after her feeling changes.
const FEELING_HOLD_SECONDS: float = 4.0
## Close shot hold while she speaks: her reading time, like the speech balloon.
const SECONDS_PER_CHARACTER: float = 0.06
const MIN_SPEECH_HOLD_SECONDS: float = 3.0
const MAX_SPEECH_HOLD_SECONDS: float = 12.0
## CanvasLayers in this group disappear in clips; the brain status banner is an autoload
## and is hidden by name.
const HIDDEN_IN_CLIPS_GROUP: StringName = &"hidden_in_clips"

@export var capybara: Capybara
@export var clip_camera: ClipCamera

var _is_auto: bool = false
var _seconds: float = 0.0
var _shot_started_at: float = 0.0
var _shot_ends_at: float = 0.0
var _current_shot_name: String = ""
var _last_emotion: StringName = &""


func _ready() -> void:
	if not ClipMode.is_on():
		clip_camera.set_process(false)
		set_process(false)
		return
	_hide_interface()
	clip_camera.current = true
	clip_camera.follow(capybara)
	var requested_shot: String = ClipMode.requested_shot()
	_is_auto = requested_shot == "auto"
	if _is_auto:
		Brain.speech_received.connect(_on_speech_received)
		Brain.feelings_changed.connect(_on_feelings_changed)
		# The warm-up is cut off later, so the opening counts from its end.
		_cut_to("wide", ClipMode.warmup_seconds() + OPENING_SECONDS)
		return
	var fixed_shot: ClipShot = ClipShot.named(requested_shot)
	if fixed_shot == null:
		push_warning("Unknown clip shot '%s'; using medium." % requested_shot)
		requested_shot = "medium"
	_cut_to(requested_shot, INF)


func _process(delta: float) -> void:
	_seconds += delta
	if _is_auto and _seconds >= _shot_ends_at:
		var next_shot_name: String = "close" if _current_shot_name == "medium" else "medium"
		_cut_to(next_shot_name, randf_range(MIN_SHOT_SECONDS, MAX_SHOT_SECONDS))


func _on_speech_received(_speech_id: int, caption: String) -> void:
	var hold_seconds: float = clampf(
		caption.length() * SECONDS_PER_CHARACTER, MIN_SPEECH_HOLD_SECONDS, MAX_SPEECH_HOLD_SECONDS
	)
	_cut_to_close_for(hold_seconds)


func _on_feelings_changed(
	emotion: StringName, _intensity: float, _valence: float, _arousal: float
) -> void:
	# The first feeling arrives when the brain connects: it is not a change.
	var is_change: bool = _last_emotion != &"" and emotion != _last_emotion
	_last_emotion = emotion
	if is_change:
		_cut_to_close_for(FEELING_HOLD_SECONDS)


## Already close: it only holds longer. Otherwise it cuts, unless the current shot is too
## young, or is the opening.
func _cut_to_close_for(hold_seconds: float) -> void:
	if _current_shot_name == "close":
		_shot_ends_at = maxf(_shot_ends_at, _seconds + hold_seconds)
		return
	if _current_shot_name == "wide" or _seconds - _shot_started_at < MIN_SECONDS_BEFORE_CUT:
		return
	_cut_to("close", hold_seconds)


func _cut_to(shot_name: String, hold_seconds: float) -> void:
	_current_shot_name = shot_name
	_shot_started_at = _seconds
	_shot_ends_at = _seconds + hold_seconds
	clip_camera.cut_to(ClipShot.named(shot_name))


func _hide_interface() -> void:
	for layer: Node in get_tree().get_nodes_in_group(HIDDEN_IN_CLIPS_GROUP):
		(layer as CanvasLayer).visible = false
	BrainStatus.visible = false
