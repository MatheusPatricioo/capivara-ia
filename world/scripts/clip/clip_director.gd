class_name ClipDirector
extends Node

## Turns the world into a film set when it runs to record a clip (ClipMode): the clip
## camera becomes the active one, the interface is hidden (only her speech balloon and
## emote stay, as part of the story) and the shots are chosen.
##
## With the "auto" shot it edits like a series: it opens wide, then cuts between medium and
## close every few seconds, and cuts to close when she speaks or her feeling changes. Cuts
## follow game time, so they land on the same frames in the Movie Maker. Until the brain is
## ready (ClipRecorder.story_started) it holds the wide shot: that part is cut off later.
## When she arrives at an interaction point (the computer, the mailbox...), it cuts over her
## shoulder to show her and the object, alternating with close shots, until she walks away.
## When she turns her back on the camera for a moment, it cuts to her front again, the way
## an editor would, instead of letting the camera swing slowly around her.
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
## Seconds the over-the-shoulder shot lasts before a close shot of her face.
const MIN_ACTIVITY_SECONDS: float = 5.0
const MAX_ACTIVITY_SECONDS: float = 7.0
## Seconds of her face between two over-the-shoulder shots.
const ACTIVITY_CLOSE_SECONDS: float = 3.0
## Meters from the point at which she counts as gone.
const LEAVE_DISTANCE: float = 1.0
## Seconds the camera can lag behind her turn before the cut to her front.
const BACK_TURNED_SECONDS: float = 0.5
## CanvasLayers in this group disappear in clips; the brain status banner is an autoload
## and is hidden by name.
const HIDDEN_IN_CLIPS_GROUP: StringName = &"hidden_in_clips"

@export var capybara: Capybara
@export var clip_camera: ClipCamera
@export var recorder: ClipRecorder

var _is_auto: bool = false
var _seconds: float = 0.0
var _shot_started_at: float = 0.0
var _shot_ends_at: float = 0.0
var _current_shot_name: String = ""
var _last_emotion: StringName = &""
## The interaction point she is using, or null.
var _activity_point: InteractionPoint = null
var _back_turned_seconds: float = 0.0


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
		_cut_to("wide", INF)
		recorder.story_started.connect(_begin_story)
		return
	var fixed_shot: ClipShot = ClipShot.named(requested_shot)
	if fixed_shot == null:
		push_warning("Unknown clip shot '%s'; using medium." % requested_shot)
		requested_shot = "medium"
	_cut_to(requested_shot, INF)


## The opening counts from here, and only from here can her lines and feelings cut.
func _begin_story() -> void:
	Brain.speech_received.connect(_on_speech_received)
	Brain.feelings_changed.connect(_on_feelings_changed)
	for point: Node in get_tree().get_nodes_in_group(InteractionPoint.GROUP):
		var interaction_point: InteractionPoint = point as InteractionPoint
		interaction_point.capybara_arrived.connect(_on_arrived_at.bind(interaction_point))
	_cut_to("wide", OPENING_SECONDS)


func _process(delta: float) -> void:
	_seconds += delta
	_cut_to_her_front_when_back_turned(delta)
	if not _is_auto:
		return
	if _activity_point != null and _has_left(_activity_point):
		_end_activity()
	if _seconds >= _shot_ends_at:
		_cut_to_next_shot()


## Using something: over the shoulder, then her face, and again. Otherwise medium and close.
func _cut_to_next_shot() -> void:
	if _activity_point == null:
		var next_shot_name: String = "close" if _current_shot_name == "medium" else "medium"
		_cut_to(next_shot_name, randf_range(MIN_SHOT_SECONDS, MAX_SHOT_SECONDS))
	elif _current_shot_name == "activity":
		_cut_to("close", ACTIVITY_CLOSE_SECONDS)
	else:
		_cut_to("activity", randf_range(MIN_ACTIVITY_SECONDS, MAX_ACTIVITY_SECONDS))


## She turned and the camera is still swinging around her, showing her side or back.
func _cut_to_her_front_when_back_turned(delta: float) -> void:
	if not clip_camera.is_lagging_behind():
		_back_turned_seconds = 0.0
		return
	_back_turned_seconds += delta
	if _back_turned_seconds < BACK_TURNED_SECONDS:
		return
	if _seconds - _shot_started_at < MIN_SECONDS_BEFORE_CUT:
		return
	_back_turned_seconds = 0.0
	# The same shot, cut again: the camera snaps to its place, the shot keeps its end.
	_shot_started_at = _seconds
	clip_camera.cut_to(ClipShot.named(_current_shot_name))


func _on_arrived_at(point: InteractionPoint) -> void:
	# She can "arrive" again at the point she is using (a new errand there): same activity.
	if point == _activity_point:
		return
	_activity_point = point
	# The cut to the activity happens as soon as the current shot is old enough.
	_shot_ends_at = minf(_shot_ends_at, _shot_started_at + MIN_SECONDS_BEFORE_CUT)


func _has_left(point: InteractionPoint) -> bool:
	return capybara.global_position.distance_to(point.global_position) > LEAVE_DISTANCE


## She walks away: the camera goes back to her face, and the series' usual shots.
func _end_activity() -> void:
	_activity_point = null
	if _current_shot_name == "activity":
		_cut_to("medium", randf_range(MIN_SHOT_SECONDS, MAX_SHOT_SECONDS))


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
	# Only the over-the-shoulder shot frames the object; the others frame her face.
	if shot_name == "activity" and _activity_point != null:
		clip_camera.focus_on(_activity_point.look_target())
	else:
		clip_camera.clear_focus()
	clip_camera.cut_to(ClipShot.named(shot_name))


func _hide_interface() -> void:
	for layer: Node in get_tree().get_nodes_in_group(HIDDEN_IN_CLIPS_GROUP):
		(layer as CanvasLayer).visible = false
	BrainStatus.visible = false
