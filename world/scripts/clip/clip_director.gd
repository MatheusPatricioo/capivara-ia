class_name ClipDirector
extends Node

## Turns the world into a film set when it runs to record a clip (ClipMode): the clip
## camera becomes the active one, the interface is hidden (only her speech balloon and
## emote stay, as part of the story) and the shots are chosen.
##
## With the "auto" shot it edits like a series: it opens wide, then changes shot every few
## seconds, drawing the next one by weight among medium, close, profile and low (never the
## same twice in a row, and behind her while she walks), with the wide landscape now and
## then to show the world and its sky, and cuts to close when she speaks or her feeling
## changes. The calm changes (medium,
## close and landscape taking turns) glide from one framing to the other; what reacts to
## her (lines, feelings, arriving somewhere) cuts, the way an editor cuts on action. Cuts
## follow game time, so they land on the same frames in the Movie Maker. Until the brain is
## ready (ClipRecorder.story_started) it holds the wide shot: that part is cut off later.
## When she arrives at an interaction point (the computer, the mailbox...), it cuts over her
## shoulder to show her and the object, alternating with close shots, until she walks away.
## When she turns her back on the camera for a moment, it cuts to her front again, the way
## an editor would, instead of letting the camera swing slowly around her.
## Without clip mode it does nothing, and the game keeps its normal camera, until Reels
## mode asks it to film live (start_live) for the vertical preview.

## Seconds the opening wide shot lasts.
const OPENING_SECONDS: float = 3.0
## Seconds a medium or close shot lasts when nothing happens, picked between these two.
const MIN_SHOT_SECONDS: float = 4.0
const MAX_SHOT_SECONDS: float = 6.0
## Medium and close shots between two landscapes.
const SHOTS_BETWEEN_LANDSCAPES: int = 4
## Seconds a landscape lasts in the middle of the story, counting the glide into it.
const LANDSCAPE_SECONDS: float = 5.0
## Seconds a glide between two calm shots takes. It counts as part of the new shot.
const GLIDE_SECONDS: float = 2.0
## How often each calm shot is drawn, relative to the others: a shot with twice the
## weight comes up twice as often.
const CALM_SHOT_WEIGHTS: Dictionary[String, float] = {
	"medium": 3.0,
	"close": 3.0,
	"profile": 2.0,
	"low": 1.5,
}
## Weight of the shot behind her while she walks: high, since it shows where she goes.
const FOLLOW_WEIGHT_WHILE_WALKING: float = 6.0
## Above this ground speed, in m/s, she counts as walking.
const WALKING_SPEED: float = 0.3
## Seconds she can stand still before the shot behind her gives way to another.
const FOLLOW_STOP_SECONDS: float = 1.0
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
## The sun's shadow while filming. The game's shadow reaches 30 m in two cascades, and the
## sharp first one covers only its first 3 m: the clip camera, 2.6 to 6.5 m from her, often
## saw her through the coarse second one, and the shadow of her head on her body came out
## jagged. Filming, the shadow reaches 14 m and the sharp cascade covers its first 40%
## (5.6 m). Same cost: still two cascades.
const FILMING_SHADOW_DISTANCE: float = 14.0
const FILMING_SHADOW_SPLIT: float = 0.4

@export var capybara: Capybara
@export var clip_camera: ClipCamera
@export var recorder: ClipRecorder
@export var sun: DirectionalLight3D

var _is_auto: bool = false
var _seconds: float = 0.0
var _shot_started_at: float = 0.0
var _shot_ends_at: float = 0.0
var _current_shot_name: String = ""
## Until then the opening wide shot holds, whatever happens.
var _opening_ends_at: float = INF
var _shots_since_landscape: int = 0
var _last_emotion: StringName = &""
## The interaction point she is using, or null.
var _activity_point: InteractionPoint = null
var _back_turned_seconds: float = 0.0
## Seconds she has stood still while the camera follows her from behind.
var _stopped_while_followed_seconds: float = 0.0
## The game's own shadow settings, put back when filming stops.
var _game_shadow_distance: float = 0.0
var _game_shadow_split: float = 0.0


func _ready() -> void:
	if not ClipMode.is_on():
		_set_filming(false)
		return
	_hide_interface()
	_use_filming_shadows()
	clip_camera.current = true
	clip_camera.follow(capybara)
	# A vertical clip is a Reels video; a horizontal one keeps her centered.
	var window_size: Vector2 = get_viewport().get_visible_rect().size
	clip_camera.frame_for_reels(window_size.y > window_size.x)
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


## Reels mode in the live game: the auto edit starts at once, since the brain is already
## running. The clip camera films only for the Reels picture: the main window keeps its
## own camera.
func start_live() -> void:
	_seconds = 0.0
	_shots_since_landscape = 0
	_activity_point = null
	_last_emotion = &""
	_back_turned_seconds = 0.0
	_is_auto = true
	clip_camera.follow(capybara)
	clip_camera.frame_for_reels(true)
	_use_filming_shadows()
	_set_filming(true)
	_begin_story()


## Reels mode turned off: no more cuts, the clip camera rests and the game's shadows return.
func stop() -> void:
	_set_filming(false)
	_disconnect_story_events()
	clip_camera.clear_focus()
	sun.directional_shadow_max_distance = _game_shadow_distance
	sun.directional_shadow_split_1 = _game_shadow_split


func _use_filming_shadows() -> void:
	_game_shadow_distance = sun.directional_shadow_max_distance
	_game_shadow_split = sun.directional_shadow_split_1
	sun.directional_shadow_max_distance = FILMING_SHADOW_DISTANCE
	sun.directional_shadow_split_1 = FILMING_SHADOW_SPLIT


func _set_filming(is_filming: bool) -> void:
	clip_camera.set_process(is_filming)
	set_process(is_filming)


## The opening counts from here, and only from here can her lines and feelings cut.
func _begin_story() -> void:
	Brain.speech_received.connect(_on_speech_received)
	Brain.feelings_changed.connect(_on_feelings_changed)
	for interaction_point: InteractionPoint in _interaction_points():
		interaction_point.capybara_arrived.connect(_on_arrived_at.bind(interaction_point))
	_opening_ends_at = _seconds + OPENING_SECONDS
	_cut_to("wide", OPENING_SECONDS)


func _disconnect_story_events() -> void:
	if Brain.speech_received.is_connected(_on_speech_received):
		Brain.speech_received.disconnect(_on_speech_received)
	if Brain.feelings_changed.is_connected(_on_feelings_changed):
		Brain.feelings_changed.disconnect(_on_feelings_changed)
	for interaction_point: InteractionPoint in _interaction_points():
		var on_arrived: Callable = _on_arrived_at.bind(interaction_point)
		if interaction_point.capybara_arrived.is_connected(on_arrived):
			interaction_point.capybara_arrived.disconnect(on_arrived)


func _interaction_points() -> Array[InteractionPoint]:
	var points: Array[InteractionPoint] = []
	for point: Node in get_tree().get_nodes_in_group(InteractionPoint.GROUP):
		points.append(point as InteractionPoint)
	return points


func _process(delta: float) -> void:
	_seconds += delta
	_cut_to_her_front_when_back_turned(delta)
	if not _is_auto:
		return
	if _activity_point != null and _has_left(_activity_point):
		_end_activity()
	_end_follow_when_she_stops(delta)
	if _seconds >= _shot_ends_at:
		_cut_to_next_shot()


## Using something: over the shoulder, then her face, and again (cuts). Otherwise a calm
## shot drawn by weight, with a landscape every few shots (glides).
func _cut_to_next_shot() -> void:
	if _activity_point == null and _shots_since_landscape >= SHOTS_BETWEEN_LANDSCAPES:
		_shots_since_landscape = 0
		_glide_to("wide", LANDSCAPE_SECONDS)
	elif _activity_point == null:
		_shots_since_landscape += 1
		_glide_to(_draw_calm_shot(), randf_range(MIN_SHOT_SECONDS, MAX_SHOT_SECONDS))
	elif _current_shot_name == "activity":
		_cut_to("close", ACTIVITY_CLOSE_SECONDS)
	else:
		_cut_to("activity", randf_range(MIN_ACTIVITY_SECONDS, MAX_ACTIVITY_SECONDS))


## The next calm shot, never the current one. While she walks, the shot behind her joins
## the draw.
func _draw_calm_shot() -> String:
	var weights: Dictionary[String, float] = CALM_SHOT_WEIGHTS.duplicate()
	if _is_walking():
		weights["follow"] = FOLLOW_WEIGHT_WHILE_WALKING
	weights.erase(_current_shot_name)
	return _draw_by_weight(weights)


## A roulette wheel with slices as wide as the weights: a random point along all of them
## falls in one slice.
static func _draw_by_weight(weights: Dictionary[String, float]) -> String:
	var total_weight: float = 0.0
	for weight: float in weights.values():
		total_weight += weight
	var point: float = randf() * total_weight
	for shot_name: String in weights:
		point -= weights[shot_name]
		if point <= 0.0:
			return shot_name
	return weights.keys().back()


func _is_walking() -> bool:
	var ground_velocity: Vector3 = Vector3(capybara.velocity.x, 0.0, capybara.velocity.z)
	return ground_velocity.length() > WALKING_SPEED


## Behind her there is nothing to see once she stops: after a moment, the next shot.
func _end_follow_when_she_stops(delta: float) -> void:
	if _current_shot_name != "follow" or _is_walking():
		_stopped_while_followed_seconds = 0.0
		return
	_stopped_while_followed_seconds += delta
	if _stopped_while_followed_seconds >= FOLLOW_STOP_SECONDS:
		_stopped_while_followed_seconds = 0.0
		_shot_ends_at = minf(_shot_ends_at, _seconds)


## She turned and the camera is still swinging around her, showing her side or back. Not
## behind her while she walks: there the camera is meant to see her back, and swinging
## along her path is the shot.
func _cut_to_her_front_when_back_turned(delta: float) -> void:
	if _current_shot_name == "follow" or not clip_camera.is_lagging_behind():
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
## young, or is the opening. A landscape in the middle of the story gives way to her lines.
func _cut_to_close_for(hold_seconds: float) -> void:
	if _current_shot_name == "close":
		_shot_ends_at = maxf(_shot_ends_at, _seconds + hold_seconds)
		return
	if _seconds < _opening_ends_at or _seconds - _shot_started_at < MIN_SECONDS_BEFORE_CUT:
		return
	_cut_to("close", hold_seconds)


func _cut_to(shot_name: String, hold_seconds: float) -> void:
	_change_shot(shot_name, hold_seconds, 0.0)


func _glide_to(shot_name: String, hold_seconds: float) -> void:
	_change_shot(shot_name, hold_seconds, GLIDE_SECONDS)


## A transition of 0 seconds is a cut; longer, the camera glides there in that time.
func _change_shot(shot_name: String, hold_seconds: float, transition_seconds: float) -> void:
	_current_shot_name = shot_name
	_shot_started_at = _seconds
	_shot_ends_at = _seconds + hold_seconds
	# Only the over-the-shoulder shot frames the object; the others frame her face.
	if shot_name == "activity" and _activity_point != null:
		clip_camera.focus_on(_activity_point.look_target())
	else:
		clip_camera.clear_focus()
	clip_camera.glide_to(ClipShot.named(shot_name), transition_seconds)


func _hide_interface() -> void:
	for layer: Node in get_tree().get_nodes_in_group(HIDDEN_IN_CLIPS_GROUP):
		(layer as CanvasLayer).visible = false
	BrainStatus.visible = false
