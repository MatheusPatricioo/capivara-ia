class_name CapybaraListening
extends Node

## While her creator talks with her, she stops strolling, drops any errand and faces the
## camera. The brain says for how long; every new exchange starts that time again, so the
## world never needs an "it is over" message.

signal listening_started
signal listening_finished

var _seconds_left: float = 0.0

@onready var _capybara: Capybara = get_parent() as Capybara
@onready var _wander: CapybaraWander = $"../Wander" as CapybaraWander


func _ready() -> void:
	Brain.listening_requested.connect(_on_listening_requested)


func is_listening() -> bool:
	return _seconds_left > 0.0


func _on_listening_requested(seconds: float) -> void:
	var was_listening: bool = is_listening()
	_seconds_left = seconds
	if was_listening or not is_listening():
		return
	_wander.pause()
	listening_started.emit()


## Faces the camera every frame, because the camera can move while they talk.
func _physics_process(delta: float) -> void:
	if not is_listening():
		return
	_seconds_left -= delta
	if not is_listening():
		_wander.resume()
		listening_finished.emit()
		return
	var camera: Camera3D = get_viewport().get_camera_3d()
	if camera != null:
		_capybara.stop_and_face(camera.global_position)
