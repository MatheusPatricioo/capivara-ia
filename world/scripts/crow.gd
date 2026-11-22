class_name Crow
extends CharacterBody3D

## Walking speed in meters per second.
@export var move_speed: float = 5.0


func _physics_process(delta: float) -> void:
	_apply_gravity(delta)
	_apply_walk_input()
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
