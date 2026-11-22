class_name CapybaraBodyAnimation
extends Node3D

## Procedural animation for the capybara body, driven by its walking speed.
## The model is a single mesh with no skeleton, so the whole body moves at once.
## Walking: each step bobs the body, weight shifts side to side and the body leans
## forward. Standing: slow breathing.

@export_group("Walk")
## Distance covered by one full step cycle, in meters.
@export var stride_length: float = 0.45
## Speed at which the walk animation reaches full strength, in m/s.
@export var full_gait_speed: float = 3.0
## How high the body rises on each step, in meters.
@export var step_bob_height: float = 0.06
## Side-to-side roll as the weight moves from one side to the other.
@export var weight_shift_degrees: float = 7.0
## Forward tilt at full speed.
@export var forward_lean_degrees: float = 6.0

@export_group("Idle")
## Breaths per second times TAU; around 2 feels calm.
@export var breathing_speed: float = 2.2
## How much the body grows on each breath, as a fraction of its size.
@export var breathing_amount: float = 0.02

var _step_phase: float = 0.0
var _idle_time: float = 0.0
var _body_base_position: Vector3
var _model_base_scale: Vector3

@onready var _capybara: CharacterBody3D = get_parent() as CharacterBody3D
@onready var _model: Node3D = $Model


func _ready() -> void:
	_body_base_position = position
	_model_base_scale = _model.scale


func _process(delta: float) -> void:
	var speed: float = Vector2(_capybara.velocity.x, _capybara.velocity.z).length()
	var gait_strength: float = clampf(speed / full_gait_speed, 0.0, 1.0)
	_step_phase = fmod(_step_phase + speed / stride_length * TAU * delta, TAU)
	_idle_time += delta
	_animate_body(gait_strength)
	_animate_breathing(gait_strength)


## abs(sin) gives two bumps per cycle: one for each diagonal pair of legs touching the ground.
func _animate_body(gait_strength: float) -> void:
	position.y = _body_base_position.y + absf(sin(_step_phase)) * step_bob_height * gait_strength
	rotation.z = deg_to_rad(weight_shift_degrees) * sin(_step_phase) * gait_strength
	rotation.x = -deg_to_rad(forward_lean_degrees) * gait_strength


## Scales the model, not the Body, so the scale set in the editor is kept as the base.
func _animate_breathing(gait_strength: float) -> void:
	var breath: float = sin(_idle_time * breathing_speed) * breathing_amount * (1.0 - gait_strength)
	_model.scale = _model_base_scale * Vector3(1.0, 1.0 + breath, 1.0)
