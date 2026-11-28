class_name ReelsCamera
extends Camera3D

## The eyes of the Reels SubViewport. It films nothing on its own: every frame it copies
## where the clip camera is, how wide it sees and how its lens is shifted, so the vertical image is exactly the
## clip camera's shot. Copying keeps the clip camera where it is, also for the Movie Maker
## clips, where it is the main window's camera.

## Runs after the clip camera and the director moved, so the copy is never a frame late.
const AFTER_THE_CLIP_CAMERA: int = 100

var _source: Camera3D = null


func _ready() -> void:
	process_priority = AFTER_THE_CLIP_CAMERA


func copy(source: Camera3D) -> void:
	_source = source
	_copy_now()


func _process(_delta: float) -> void:
	_copy_now()


func _copy_now() -> void:
	if _source == null:
		return
	global_transform = _source.global_transform
	fov = _source.fov
	h_offset = _source.h_offset
	v_offset = _source.v_offset
