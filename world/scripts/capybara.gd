class_name Capybara
extends CharacterBody3D

## Emitted when the capybara arrives at the point given to walk_to().
signal destination_reached

enum ControlMode { AUTONOMOUS, MANUAL }

## Walking speed with the keyboard (manual mode), in meters per second.
@export var manual_speed: float = 5.0
## Base walking speed when following a navigation path, in meters per second.
@export var navigation_speed: float = 3.2
## How quickly the capybara speeds up, in m/s². Lower feels softer, like a cat starting to walk.
@export var acceleration: float = 7.0
## How quickly the capybara slows down, in m/s².
@export var deceleration: float = 9.0
## Distance from the destination where the capybara starts slowing down, in meters.
@export var arrival_slowdown_distance: float = 1.2
## Slowest fraction of the speed kept while arriving, so it never crawls.
@export var arrival_min_speed_ratio: float = 0.3
## How fast the body turns towards the walking direction. Higher is snappier.
@export var turn_speed: float = 7.0

var control_mode: ControlMode = ControlMode.AUTONOMOUS
var _is_walking_to_destination: bool = false
var _current_speed_scale: float = 1.0

@onready var _body: Node3D = $Body
@onready var _navigation_agent: NavigationAgent3D = $NavigationAgent3D


func _ready() -> void:
	_navigation_agent.navigation_finished.connect(_on_navigation_finished)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_control_mode"):
		_toggle_control_mode()


## Sends the capybara to a point in the world. It finds a path around obstacles and emits
## destination_reached on arrival. Unreachable points lead to the closest reachable one.
## speed_scale multiplies navigation_speed: 1.0 is a calm walk, higher is a trot.
func walk_to(destination: Vector3, speed_scale: float = 1.0) -> void:
	_navigation_agent.target_position = destination
	_current_speed_scale = speed_scale
	_is_walking_to_destination = true


## Sends the capybara to the interaction point with this id (bed, food_bowl, computer...).
## Returns false when no point has that id, so the caller can report the mistake.
func go_to_point(point_id: StringName, speed_scale: float = 1.0) -> bool:
	var point: InteractionPoint = _find_interaction_point(point_id)
	if point == null:
		push_warning("Unknown interaction point: %s" % point_id)
		return false
	walk_to(point.global_position, speed_scale)
	return true


func _find_interaction_point(point_id: StringName) -> InteractionPoint:
	for node: Node in get_tree().get_nodes_in_group(InteractionPoint.GROUP):
		var point: InteractionPoint = node as InteractionPoint
		if point != null and point.point_id == point_id:
			return point
	return null


func _physics_process(delta: float) -> void:
	_apply_gravity(delta)
	var desired_velocity: Vector3 = _manual_velocity() if control_mode == ControlMode.MANUAL else _navigation_velocity()
	_accelerate_towards(desired_velocity, delta)
	_turn_body_towards_movement(delta)
	move_and_slide()


func _apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta


## Moves the horizontal velocity a little towards the desired one each frame, instead of
## jumping to it. This gives soft starts, rounded turns and gentle stops.
func _accelerate_towards(desired_velocity: Vector3, delta: float) -> void:
	var horizontal_velocity: Vector3 = Vector3(velocity.x, 0.0, velocity.z)
	var is_speeding_up: bool = desired_velocity.length() > horizontal_velocity.length()
	var rate: float = acceleration if is_speeding_up else deceleration
	horizontal_velocity = horizontal_velocity.move_toward(desired_velocity, rate * delta)
	velocity.x = horizontal_velocity.x
	velocity.z = horizontal_velocity.z


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
	return direction.normalized() * navigation_speed * _current_speed_scale * _arrival_speed_ratio()


## 1.0 while far away, dropping smoothly to arrival_min_speed_ratio near the destination.
func _arrival_speed_ratio() -> float:
	var distance_left: float = _navigation_agent.distance_to_target()
	return clampf(distance_left / arrival_slowdown_distance, arrival_min_speed_ratio, 1.0)


func _toggle_control_mode() -> void:
	if control_mode == ControlMode.AUTONOMOUS:
		control_mode = ControlMode.MANUAL
	else:
		control_mode = ControlMode.AUTONOMOUS
		_recalculate_path()
	print("Capybara control mode: %s" % ControlMode.keys()[control_mode])


## While in manual mode the capybara may have been moved far from the old path.
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
	if horizontal_velocity.length() < 0.1:
		return
	var target_angle: float = atan2(-velocity.x, -velocity.z)
	var turn_weight: float = minf(turn_speed * delta, 1.0)
	_body.rotation.y = lerp_angle(_body.rotation.y, target_angle, turn_weight)
