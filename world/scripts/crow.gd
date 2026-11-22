class_name Crow
extends CharacterBody3D

## Walking speed in meters per second.
@export var move_speed: float = 5.0
## How fast the body turns towards the walking direction. Higher is snappier.
@export var turn_speed: float = 10.0

@onready var _body: Node3D = $Body


func _physics_process(delta: float) -> void:
	_apply_gravity(delta)
	_apply_walk_input()
	_turn_body_towards_movement(delta)
	move_and_slide()


func _apply_gravity(delta: float) -> void:
	if not is_on_floor():
		velocity += get_gravity() * delta


func _apply_walk_input() -> void:
	var input_direction: Vector2 = Input.get_vector(
		"move_left", "move_right", "move_forward", "move_backward"
	)
	velocity.x = input_direction.x * move_speed
	velocity.z = input_direction.y * move_speed


func _turn_body_towards_movement(delta: float) -> void:
	var horizontal_velocity: Vector2 = Vector2(velocity.x, velocity.z)
	if horizontal_velocity.is_zero_approx():
		return
	var target_angle: float = atan2(-velocity.x, -velocity.z)
	var turn_weight: float = minf(turn_speed * delta, 1.0)
	_body.rotation.y = lerp_angle(_body.rotation.y, target_angle, turn_weight)
