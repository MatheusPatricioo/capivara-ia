class_name CapybaraBodyAnimation
extends Node3D

## Procedural four-legged gait for the capybara body, driven by its walking speed.
## Walking: legs move in diagonal pairs, each step bobs the body, weight shifts side to
## side and the little tail wiggles. Standing: slow breathing, a lazy tail wiggle and the
## head looks around.

@export_group("Walk")
## Distance covered by one full step cycle (both diagonal pairs), in meters.
@export var stride_length: float = 0.45
## Speed at which the walk animation reaches full strength, in m/s.
@export var full_gait_speed: float = 3.0
## How high the body rises on each step, in meters.
@export var step_bob_height: float = 0.035
## Side-to-side roll as the weight moves from one diagonal pair to the other.
@export var weight_shift_degrees: float = 4.0
## Forward tilt at full speed.
@export var forward_lean_degrees: float = 6.0
## How far each leg moves forward and back, in meters.
@export var leg_swing_distance: float = 0.06
## How high each leg lifts while moving forward, in meters.
@export var leg_lift_height: float = 0.03
## Tail swing while walking.
@export var walk_tail_swing_degrees: float = 18.0

@export_group("Idle")
## Breaths per second times TAU; around 2 feels calm.
@export var breathing_speed: float = 2.2
## How much the torso grows on each breath, as a fraction of its size.
@export var breathing_amount: float = 0.02
## Speed of the lazy tail wiggle while standing.
@export var idle_tail_swish_speed: float = 1.3
## Tail wiggle while standing.
@export var idle_tail_swish_degrees: float = 12.0
## Largest head turn while looking around.
@export var head_look_max_degrees: float = 45.0
## Shortest time before the head picks a new direction to look at, in seconds.
@export var head_look_min_interval: float = 1.5
## Longest time before the head picks a new direction to look at, in seconds.
@export var head_look_max_interval: float = 4.0
## How fast the head turns. Higher is snappier.
@export var head_turn_speed: float = 4.0

var _step_phase: float = 0.0
var _idle_time: float = 0.0
var _head_look_angle: float = 0.0
var _seconds_until_next_look: float = 0.0
var _body_base_position: Vector3
var _head_base_position: Vector3
var _torso_base_scale: Vector3
var _leg_base_positions: Dictionary[Node3D, Vector3] = {}

@onready var _capybara: CharacterBody3D = get_parent() as CharacterBody3D
@onready var _torso: Node3D = $Torso
@onready var _head: Node3D = $Head
@onready var _front_left_leg: Node3D = $FrontLegLeft
@onready var _front_right_leg: Node3D = $FrontLegRight
@onready var _back_left_leg: Node3D = $BackLegLeft
@onready var _back_right_leg: Node3D = $BackLegRight
@onready var _tail_pivot: Node3D = $TailPivot


func _ready() -> void:
	_body_base_position = position
	_head_base_position = _head.position
	_torso_base_scale = _torso.scale
	for leg: Node3D in [_front_left_leg, _front_right_leg, _back_left_leg, _back_right_leg]:
		_leg_base_positions[leg] = leg.position


func _process(delta: float) -> void:
	var speed: float = Vector2(_capybara.velocity.x, _capybara.velocity.z).length()
	var gait_strength: float = clampf(speed / full_gait_speed, 0.0, 1.0)
	_step_phase = fmod(_step_phase + speed / stride_length * TAU * delta, TAU)
	_idle_time += delta
	_animate_body(gait_strength)
	_animate_legs(gait_strength)
	_animate_tail(gait_strength)
	_animate_breathing(gait_strength)
	_animate_head(gait_strength, delta)


## abs(sin) gives two bumps per cycle: one for each diagonal pair touching the ground.
func _animate_body(gait_strength: float) -> void:
	position.y = _body_base_position.y + _step_bounce() * step_bob_height * gait_strength
	rotation.z = deg_to_rad(weight_shift_degrees) * sin(_step_phase) * gait_strength
	rotation.x = -deg_to_rad(forward_lean_degrees) * gait_strength


## Diagonal gait, like a trotting dog: front-left moves with back-right, and front-right
## with back-left. The two pairs run half a cycle apart, so the body always rests on two
## opposite corners and stays balanced.
func _animate_legs(gait_strength: float) -> void:
	var first_pair_phase: float = _step_phase
	var second_pair_phase: float = _step_phase + PI
	_place_leg(_front_left_leg, first_pair_phase, gait_strength)
	_place_leg(_back_right_leg, first_pair_phase, gait_strength)
	_place_leg(_front_right_leg, second_pair_phase, gait_strength)
	_place_leg(_back_left_leg, second_pair_phase, gait_strength)


## A leg lifts only while it moves forward (cos > 0).
func _place_leg(leg: Node3D, leg_phase: float, gait_strength: float) -> void:
	var base_position: Vector3 = _leg_base_positions[leg]
	leg.position.z = base_position.z - sin(leg_phase) * leg_swing_distance * gait_strength
	leg.position.y = base_position.y + maxf(cos(leg_phase), 0.0) * leg_lift_height * gait_strength


## Walking swing and idle wiggle blend by gait strength, so the tail never stops abruptly.
func _animate_tail(gait_strength: float) -> void:
	var walk_swing: float = deg_to_rad(walk_tail_swing_degrees) * sin(_step_phase) * gait_strength
	var idle_swish: float = deg_to_rad(idle_tail_swish_degrees) * sin(_idle_time * idle_tail_swish_speed)
	_tail_pivot.rotation.y = walk_swing + idle_swish * (1.0 - gait_strength)


func _animate_breathing(gait_strength: float) -> void:
	var breath: float = sin(_idle_time * breathing_speed) * breathing_amount * (1.0 - gait_strength)
	_torso.scale = _torso_base_scale * Vector3(1.0, 1.0 + breath, 1.0)


## The head stays steadier than the body: it cancels part of the step bounce.
## Standing still, it looks around now and then; walking, it faces forward.
func _animate_head(gait_strength: float, delta: float) -> void:
	_head.position.y = _head_base_position.y - _step_bounce() * step_bob_height * gait_strength * 0.5
	_update_head_look_angle(gait_strength, delta)
	var turn_weight: float = minf(head_turn_speed * delta, 1.0)
	_head.rotation.y = lerp_angle(_head.rotation.y, _head_look_angle, turn_weight)


func _update_head_look_angle(gait_strength: float, delta: float) -> void:
	if gait_strength > 0.1:
		_head_look_angle = 0.0
		_seconds_until_next_look = randf_range(head_look_min_interval, head_look_max_interval)
		return
	_seconds_until_next_look -= delta
	if _seconds_until_next_look > 0.0:
		return
	var max_angle: float = deg_to_rad(head_look_max_degrees)
	_head_look_angle = randf_range(-max_angle, max_angle)
	_seconds_until_next_look = randf_range(head_look_min_interval, head_look_max_interval)


func _step_bounce() -> float:
	return absf(sin(_step_phase))
