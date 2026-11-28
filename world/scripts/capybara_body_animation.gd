class_name CapybaraBodyAnimation
extends Node3D

## Procedural animation for the capybara body, driven by its walking speed.
## The model is a single mesh with no skeleton: the whole body bobs, shifts its weight and
## leans here, and the legs swing in the capybara_walk shader, which this script feeds with
## the step phase. Standing: slow breathing.
##
## Her feet never leave the ground: after tilting the body, it is raised or lowered so the
## lowest foot touches the floor, and breathing grows her body from the feet up.

const WALK_SHADER: Shader = preload("res://shaders/capybara_walk.gdshader")
## The middle of each sole, in the model's own space (measured in the .glb).
const FEET_IN_MODEL: Array[Vector3] = [
	Vector3(0.184, -0.352, 0.1),
	Vector3(0.184, -0.352, -0.103),
	Vector3(-0.255, -0.352, 0.102),
	Vector3(-0.255, -0.352, -0.104),
]

@export_group("Walk")
## Distance covered by one full step cycle, in meters.
@export var stride_length: float = 0.45
## Speed at which the walk animation reaches full strength, in m/s.
@export var full_gait_speed: float = 3.0
## How high the body rises on each step, in meters. Small: her legs are only 6 cm long.
@export var step_bob_height: float = 0.012
## Side-to-side roll as the weight moves from one side to the other.
@export var weight_shift_degrees: float = 4.0
## Forward tilt at full speed.
@export var forward_lean_degrees: float = 4.0

@export_group("Idle")
## Breaths per second times TAU; around 2 feels calm.
@export var breathing_speed: float = 2.2
## How much the body grows on each breath, as a fraction of its size.
@export var breathing_amount: float = 0.02

## Extra forward tilt from her mood, in degrees: positive droops her head (sad),
## negative lifts it (happy). Set by CapybaraFeelings.
var mood_droop_degrees: float = 0.0
## Multiplies the breathing speed: slower when calm or sad, faster when agitated.
var mood_breathing_scale: float = 1.0

var _step_phase: float = 0.0
var _idle_time: float = 0.0
var _body_base_position: Vector3
var _model_base_position: Vector3
var _model_base_scale: Vector3
## The soles in this node's space, standing still.
var _feet: Array[Vector3] = []
## From the model's origin down to its soles, in this node's space.
var _model_height_above_soles: float = 0.0
var _walk_material: ShaderMaterial

@onready var _capybara: CharacterBody3D = get_parent() as CharacterBody3D
@onready var _model: Node3D = $Model


func _ready() -> void:
	_body_base_position = position
	_model_base_position = _model.position
	_model_base_scale = _model.scale
	for foot_in_model: Vector3 in FEET_IN_MODEL:
		_feet.append(_model.transform * foot_in_model)
	_model_height_above_soles = _model_base_position.y - _feet[0].y
	_walk_material = _make_walk_material()


func _process(delta: float) -> void:
	var speed: float = Vector2(_capybara.velocity.x, _capybara.velocity.z).length()
	var gait_strength: float = clampf(speed / full_gait_speed, 0.0, 1.0)
	_step_phase = fmod(_step_phase + speed / stride_length * TAU * delta, TAU)
	_idle_time += delta
	_animate_body(gait_strength)
	_animate_breathing(gait_strength)
	_walk_material.set_shader_parameter("step_phase", _step_phase)
	_walk_material.set_shader_parameter("gait_strength", gait_strength)


## abs(sin) gives two bumps per cycle: one for each diagonal pair of legs touching the ground.
func _animate_body(gait_strength: float) -> void:
	rotation.z = deg_to_rad(weight_shift_degrees) * sin(_step_phase) * gait_strength
	rotation.x = -deg_to_rad(forward_lean_degrees * gait_strength + mood_droop_degrees)
	var bob: float = absf(sin(_step_phase)) * step_bob_height * gait_strength
	position.y = _body_base_position.y + bob + _height_keeping_feet_down()


## Tilting turns the body around its middle, so some feet sink into the floor and others
## rise. This is how much to raise the body (or lower it, when negative) so the lowest
## foot stands exactly where it stood before the tilt.
func _height_keeping_feet_down() -> float:
	var deepest_sinking: float = -INF
	for foot: Vector3 in _feet:
		var tilted_foot: Vector3 = basis * foot
		deepest_sinking = maxf(deepest_sinking, foot.y - tilted_foot.y)
	return deepest_sinking


## Scales the model, not the Body, so the scale set in the editor is kept as the base. The
## model grows from its soles: it moves up by what the growing would push the feet down.
func _animate_breathing(gait_strength: float) -> void:
	var breath: float = (
		sin(_idle_time * breathing_speed * mood_breathing_scale)
		* breathing_amount
		* (1.0 - gait_strength)
	)
	_model.scale = _model_base_scale * Vector3(1.0, 1.0 + breath, 1.0)
	_model.position.y = _model_base_position.y + _model_height_above_soles * breath


## Swaps the model's material for the walking one, with the same texture and color.
func _make_walk_material() -> ShaderMaterial:
	var mesh_instance: MeshInstance3D = _model.find_children("*", "MeshInstance3D", true, false)[0]
	var original: StandardMaterial3D = mesh_instance.get_active_material(0) as StandardMaterial3D
	var walk_material: ShaderMaterial = ShaderMaterial.new()
	walk_material.shader = WALK_SHADER
	walk_material.set_shader_parameter("albedo_texture", original.albedo_texture)
	walk_material.set_shader_parameter("albedo_color", original.albedo_color)
	mesh_instance.material_override = walk_material
	return walk_material
