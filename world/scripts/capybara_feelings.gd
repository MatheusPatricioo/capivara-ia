class_name CapybaraFeelings
extends Node

## Lets the capybara's feelings show in her body: how fast she walks, how long she rests,
## her posture and her breathing. The brain decides what she feels; this only shows it.

## Walking speed multiplier when she is as low as she gets (sad, apathetic).
@export var low_pace: float = 0.65
## Walking speed multiplier when she is as lively as she gets (joy, flow).
@export var lively_pace: float = 1.1
## Rest multiplier when low: longer pauses between walks.
@export var low_rest: float = 2.2
## Rest multiplier when lively: short, eager pauses.
@export var lively_rest: float = 0.6
## Head droop at the saddest, in degrees. Happiness lifts it by half of this.
@export var max_droop_degrees: float = 9.0
## Seconds for the posture to change, so a new feeling sinks in instead of snapping.
@export var transition_seconds: float = 2.5

var _posture_tween: Tween

@onready var _wander: CapybaraWander = $"../Wander" as CapybaraWander
@onready var _body_animation: CapybaraBodyAnimation = $"../Body" as CapybaraBodyAnimation


func _ready() -> void:
	Brain.feelings_changed.connect(_on_feelings_changed)


func _on_feelings_changed(
	_emotion: StringName, _intensity: float, valence: float, arousal: float
) -> void:
	var liveliness: float = _liveliness(valence, arousal)
	if liveliness >= 0.0:
		_wander.mood_pace = lerpf(1.0, lively_pace, liveliness)
		_wander.mood_rest = lerpf(1.0, lively_rest, liveliness)
	else:
		_wander.mood_pace = lerpf(1.0, low_pace, -liveliness)
		_wander.mood_rest = lerpf(1.0, low_rest, -liveliness)
	_change_posture(valence, arousal)


## From -1 (low and slow) to 1 (lively). Good feelings and agitation both add energy;
## a calm, happy capybara is only a little lively.
func _liveliness(valence: float, arousal: float) -> float:
	return clampf(valence * 0.7 + (arousal - 0.3) * 0.6, -1.0, 1.0)


func _change_posture(valence: float, arousal: float) -> void:
	var droop: float = -valence * max_droop_degrees
	if droop < 0.0:
		droop *= 0.5
	if _posture_tween != null:
		_posture_tween.kill()
	_posture_tween = create_tween().set_parallel().set_trans(Tween.TRANS_SINE)
	_posture_tween.tween_property(
		_body_animation, "mood_droop_degrees", droop, transition_seconds
	)
	_posture_tween.tween_property(
		_body_animation, "mood_breathing_scale", lerpf(0.7, 1.5, arousal), transition_seconds
	)
