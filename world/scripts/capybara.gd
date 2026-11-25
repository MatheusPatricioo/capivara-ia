class_name Capybara
extends CharacterBody3D

## Emitted when the capybara arrives at the point given to walk_to().
signal destination_reached

enum ControlMode { AUTONOMOUS, MANUAL }

## Walking speed with the keyboard (manual mode), in meters per second.
@export var manual_speed: float = 5.0
## Base walking speed when following a navigation path, in meters per second.
@export var navigation_speed: float = 2.2
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
## Speed of the last small step from the end of the path to an interaction point, in m/s.
## The path keeps half a meter away from objects; this step brings her right up to them.
@export var final_step_speed: float = 0.6
## The final step gives up after this many seconds, for example when something is in the way.
@export var final_step_max_seconds: float = 1.5
## Close enough to the interaction point to stop the final step, in meters.
@export var final_step_tolerance: float = 0.05

var control_mode: ControlMode = ControlMode.AUTONOMOUS
var _is_walking_to_destination: bool = false
var _current_speed_scale: float = 1.0
## Set while she goes to an interaction point: where to stand and what to face on arrival.
var _point_position: Vector3 = Vector3.ZERO
var _look_target: Vector3 = Vector3.ZERO
var _is_going_to_point: bool = false
var _target_point: InteractionPoint = null
var _is_taking_final_step: bool = false
var _final_step_seconds_left: float = 0.0
var _is_facing_look_target: bool = false

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
	_is_going_to_point = false
	_target_point = null
	_is_taking_final_step = false
	_is_facing_look_target = false


## Sends the capybara to the interaction point with this id (bed, food_bowl, computer...).
## Returns false when no point has that id, so the caller can report the mistake.
func go_to_point(point_id: StringName, speed_scale: float = 1.0) -> bool:
	var point: InteractionPoint = _find_interaction_point(point_id)
	if point == null:
		push_warning("Unknown interaction point: %s" % point_id)
		return false
	walk_to(point.global_position, speed_scale)
	_point_position = point.global_position
	_look_target = point.look_target()
	_is_going_to_point = true
	_target_point = point
	return true


## Stops where she is, dropping any walk in progress, and keeps facing the given point,
## like the camera while her creator talks with her. She turns smoothly, as when she
## arrives at a place. A later walk_to() or go_to_point() makes her move again.
func stop_and_face(target: Vector3) -> void:
	_is_walking_to_destination = false
	_is_going_to_point = false
	_is_taking_final_step = false
	_target_point = null
	_look_target = target
	_is_facing_look_target = true


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
	if _is_facing_look_target:
		_turn_body_towards(_look_target - global_position, delta)
	else:
		_turn_body_towards_movement(delta)
	move_and_slide()
	_update_final_step(delta)


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
	if _is_taking_final_step:
		return _flat_direction_to(_point_position) * final_step_speed
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
	if _is_going_to_point:
		_is_taking_final_step = true
		_final_step_seconds_left = final_step_max_seconds
		return
	destination_reached.emit()


## The last small, straight step to the interaction point. It ends when she is there,
## or when time runs out because her body bumped into the object.
func _update_final_step(delta: float) -> void:
	if not _is_taking_final_step:
		return
	_final_step_seconds_left -= delta
	var distance_left: float = _flat_distance_to(_point_position)
	if distance_left > final_step_tolerance and _final_step_seconds_left > 0.0:
		return
	_is_taking_final_step = false
	_is_going_to_point = false
	_is_facing_look_target = true
	if _target_point != null:
		_target_point.mark_capybara_arrived()
		_target_point = null
	destination_reached.emit()


func _flat_direction_to(target: Vector3) -> Vector3:
	var direction: Vector3 = target - global_position
	direction.y = 0.0
	return direction.normalized()


func _flat_distance_to(target: Vector3) -> float:
	return Vector2(target.x - global_position.x, target.z - global_position.z).length()


func _turn_body_towards_movement(delta: float) -> void:
	var horizontal_velocity: Vector2 = Vector2(velocity.x, velocity.z)
	if horizontal_velocity.length() < 0.1:
		return
	_turn_body_towards(velocity, delta)


## Turns the body smoothly so its front (-Z) points along the given direction.
func _turn_body_towards(direction: Vector3, delta: float) -> void:
	if Vector2(direction.x, direction.z).length() < 0.01:
		return
	var target_angle: float = atan2(-direction.x, -direction.z)
	var turn_weight: float = minf(turn_speed * delta, 1.0)
	_body.rotation.y = lerp_angle(_body.rotation.y, target_angle, turn_weight)
