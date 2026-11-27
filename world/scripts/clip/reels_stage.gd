class_name ReelsStage
extends Control

## The vertical picture of Reels mode. The world is rendered a second time, by the Reels
## camera, into a SubViewport of the clip's own size (1080x1920): an image that exists
## only in the video card, the size of the clip whatever the window's size. This control
## shows it as big as fits, centered, with black bars at the sides, and the recording look
## (ReelsOverlay) on top of the picture only. The SubViewport holds just the world and her
## speech balloon, so it is also the clean image a recording takes.

const BAR_COLOR: Color = Color.BLACK

## The size of the vertical image, in pixels.
@export var frame_size: Vector2i = Vector2i(1080, 1920)

var _viewport: SubViewport
var _camera: ReelsCamera
var _picture: TextureRect
var _overlay: ReelsOverlay


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build()
	resized.connect(_fit_picture)
	_fit_picture()
	turn_off()


## Where the vertical image is rendered; her speech balloon draws itself into it.
func viewport() -> SubViewport:
	return _viewport


func turn_on(clip_camera: Camera3D) -> void:
	_camera.copy(clip_camera)
	_camera.current = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_overlay.restart_clock()
	show()


## Off, the SubViewport stops rendering: the world is drawn once again, as before.
func turn_off() -> void:
	_viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
	hide()


## The biggest 9:16 rectangle that fits the window, centered.
static func fitted_rect(window_size: Vector2, picture_size: Vector2) -> Rect2:
	var scale_factor: float = minf(window_size.x / picture_size.x, window_size.y / picture_size.y)
	var fitted_size: Vector2 = picture_size * scale_factor
	return Rect2((window_size - fitted_size) / 2.0, fitted_size)


func _fit_picture() -> void:
	var picture_rect: Rect2 = fitted_rect(size, Vector2(frame_size))
	for frame_control: Control in [_picture, _overlay]:
		frame_control.position = picture_rect.position
		frame_control.size = picture_rect.size


func _build() -> void:
	var bars: ColorRect = ColorRect.new()
	bars.color = BAR_COLOR
	bars.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bars.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bars)

	# Not own_world_3d: it films the same world as the main window.
	_viewport = SubViewport.new()
	_viewport.size = frame_size
	_viewport.audio_listener_enable_3d = false
	add_child(_viewport)
	_camera = ReelsCamera.new()
	_viewport.add_child(_camera)

	_picture = TextureRect.new()
	_picture.texture = _viewport.get_texture()
	_picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_picture.stretch_mode = TextureRect.STRETCH_SCALE
	_picture.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_picture)

	_overlay = ReelsOverlay.new()
	add_child(_overlay)
