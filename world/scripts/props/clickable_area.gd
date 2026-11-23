class_name ClickableArea
extends Area3D

## Turns a prop into something the player can click. Give it a CollisionShape3D covering
## the prop and connect to clicked. It knows nothing about what the click opens.

signal clicked


## Called by the engine when the mouse ray from the camera hits this area's shape.
func _input_event(
	_camera: Camera3D,
	event: InputEvent,
	_event_position: Vector3,
	_normal: Vector3,
	_shape_index: int
) -> void:
	var mouse_button: InputEventMouseButton = event as InputEventMouseButton
	if mouse_button == null:
		return
	if mouse_button.button_index == MOUSE_BUTTON_LEFT and mouse_button.pressed:
		clicked.emit()
