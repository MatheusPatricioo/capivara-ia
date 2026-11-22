class_name Crow
extends CharacterBody3D

## Emitted when the crow arrives at the point given to walk_to().
signal destination_reached

enum ControlMode { AUTONOMOUS, MANUAL }

## Walking speed with the keyboard (manual mode), in meters per second.
@export var manual_speed: float = 5.0
## Walking speed when following a navigation path, in meters per second.
@export var navigation_speed: float = 2.5
## How fast the body turns towards the walking direction. Higher is snappier.
@export var turn_speed: float = 10.0

var control_mode: ControlMode = ControlMode.AUTONOMOUS
var _is_walking_to_destination: bool = false

@onready var _body: Node3D = $Body
@onready var _navigation_agent: NavigationAgent3D = $NavigationAgent3D


func _ready() -> void:
	_navigation_agent.navigation_finished.connect(_on_navigation_finished)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_control_mode"):
		_toggle_control_mode()


## Sends the crow to a point in the world. It finds a path around obstacles and emits
## destination_reached on arrival. Unreachable points lead to the closest reachable one.
func walk_to(destination: Vector3) -> void:
	_navigation_agent.target_position = destination
	_is_walking_to_destination = true


func _physics_process(delta: float) -> void:
	_apply_gravity(delta)
	var walk_velocity: Vector3 = _manual_velocity() if control_mode == ControlMode.MANUAL else _navigation_velocity()
	velocity.x = walk_velocity.x
	velocity.z = walk_velocity.z
	_turn_body_towards_movement(delta)
	move_and_slide()


func _apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta


func _manual_velocity() -> Vector3:
	var input_direction: Vector2 = Input.get_vector(
		"move_left", "move_right", "move_forward", "move_backward"
	)
	return Vector3(input_direction.x, 0.0, input_direction.y) * manual_speed


func _navigation_velocity() -> Vector3:
	if not _is_walking_to_destination or _navigation_agent.is_navigation_finished():
		return Vector3.ZERO
	var next_path_position: Vector3 = _navigation_agent.get_next_path_position()
	var direction: Vector3 = next_path_position - global_position
	direction.y = 0.0
	return direction.normalized() * navigation_speed


func _toggle_control_mode() -> void:
	if control_mode == ControlMode.AUTONOMOUS:
		control_mode = ControlMode.MANUAL
	else:
		control_mode = ControlMode.AUTONOMOUS
		_recalculate_path()
	print("Crow control mode: %s" % ControlMode.keys()[control_mode])


## While in manual mode the crow may have been moved far from the old path.
## Assigning the target again forces the agent to plan a fresh path.
func _recalculate_path() -> void:
	if _is_walking_to_destination:
		_navigation_agent.target_position = _navigation_agent.target_position


func _on_navigation_finished() -> void:
	if not _is_walking_to_destination:
		return
	_is_walking_to_destination = false
	destination_reached.emit()


func _turn_body_towards_movement(delta: float) -> void:
	var horizontal_velocity: Vector2 = Vector2(velocity.x, velocity.z)
	if horizontal_velocity.is_zero_approx():
		return
	var target_angle: float = atan2(-velocity.x, -velocity.z)
	var turn_weight: float = minf(turn_speed * delta, 1.0)
	_body.rotation.y = lerp_angle(_body.rotation.y, target_angle, turn_weight)
