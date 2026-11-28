class_name CapybaraSpeechBalloon
extends Node3D

## Her words in a speech balloon drawn on the screen, with its tip just above her head:
## it grows upwards, so a long reply never covers her, and it stays inside the screen.
## It shows "…" while she thinks about what her creator said, then her reply for the time
## it takes to read it. A newer speech replaces the one on screen at once; an older one
## that arrives late is dropped. This node only marks the spot above her head.

const THINKING_TEXT: String = "…"
const NO_SPEECH_YET: int = 0
const LAYER: int = 4
const MAX_WIDTH: float = 340.0
const FONT_SIZE: int = 17
const TIP_SIZE: Vector2 = Vector2(18.0, 10.0)
const GAP_ABOVE_HEAD: float = 8.0
const SCREEN_MARGIN: float = 12.0
const BALLOON_COLOR: Color = Color(0.12, 0.09, 0.07, 0.88)
const TEXT_COLOR: Color = Color(0.98, 0.95, 0.88)
const FADE_SECONDS: float = 0.15

## Reading time per character of the reply, in seconds.
@export var seconds_per_character: float = 0.06
## Shortest time a reply stays, even a one-word reply.
@export var min_seconds: float = 3.0
## Longest time a reply stays, so a long reply does not stay for minutes.
@export var max_seconds: float = 30.0
## How long "…" waits for her reply before giving up (the brain may be busy or offline).
@export var thinking_max_seconds: float = 90.0

var _shown_speech_id: int = NO_SPEECH_YET
var _hide_timer: Timer = Timer.new()
var _layer: CanvasLayer
## Where the balloon is drawn and whose camera places it; null for the main window.
var _target_viewport: Viewport = null
var _balloon: PanelContainer
var _label: Label
var _tip: Polygon2D


func _ready() -> void:
	_build()
	_hide_timer.one_shot = true
	_hide_timer.timeout.connect(_hide_balloon)
	add_child(_hide_timer)
	Brain.creator_message_sent.connect(_show_thinking)
	Brain.speech_received.connect(_on_speech_received)
	Brain.connection_changed.connect(_on_connection_changed)


func _process(_delta: float) -> void:
	if _balloon.visible:
		_balloon.reset_size()
		_follow_her_head()


## Draws the balloon inside another viewport (the Reels picture), placed by its camera.
## The balloon is scaled like the game's interface would be in a window of that size, so
## it looks the same as in the Movie Maker clips.
func draw_in(target_viewport: SubViewport) -> void:
	_target_viewport = target_viewport
	_move_layer_to(target_viewport)
	_layer.scale = Vector2.ONE * _interface_scale(Vector2(target_viewport.size))


## Back to the main window, at its usual size.
func draw_on_screen() -> void:
	_target_viewport = null
	# Godot refuses null here: the main window is given by name.
	_move_layer_to(get_viewport())
	_layer.scale = Vector2.ONE


## Changing the viewport of a layer that is in the tree confuses Godot 4.7 on the second
## change (it disconnects a signal twice), so the layer leaves the tree while it moves.
func _move_layer_to(target_viewport: Viewport) -> void:
	remove_child(_layer)
	_layer.custom_viewport = target_viewport
	add_child(_layer)


## The stretch the "canvas_items" mode would apply in a window of this size.
static func _interface_scale(window_size: Vector2) -> float:
	var base_size: Vector2 = Vector2(
		ProjectSettings.get_setting("display/window/size/viewport_width"),
		ProjectSettings.get_setting("display/window/size/viewport_height")
	)
	return minf(window_size.x / base_size.x, window_size.y / base_size.y)


func _drawing_viewport() -> Viewport:
	return _target_viewport if _target_viewport != null else get_viewport()


func _show_thinking(_text: String) -> void:
	_show_for(THINKING_TEXT, thinking_max_seconds)


func _on_speech_received(speech_id: int, caption: String) -> void:
	if speech_id <= _shown_speech_id or caption.is_empty():
		return
	_shown_speech_id = speech_id
	var reading_seconds: float = caption.length() * seconds_per_character
	_show_for(caption, clampf(reading_seconds, min_seconds, max_seconds))


func _show_for(balloon_text: String, seconds: float) -> void:
	_label.text = balloon_text
	_fit_label_width()
	if not _balloon.visible:
		_balloon.modulate.a = 0.0
		create_tween().tween_property(_balloon, "modulate:a", 1.0, FADE_SECONDS)
	_balloon.show()
	_tip.show()
	_follow_her_head()
	_hide_timer.start(seconds)


## A wrapping label measures its height with the width it has right now, so the width is
## given first: the text's own width, up to MAX_WIDTH. Without it the label was 0 wide,
## wrapped one letter per line and the balloon became a dark column across the screen.
func _fit_label_width() -> void:
	var font: Font = _label.get_theme_font("font")
	var text_width: float = font.get_string_size(
		_label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, FONT_SIZE
	).x
	var width: float = minf(ceilf(text_width) + 2.0, MAX_WIDTH)
	_label.custom_minimum_size = Vector2(width, 0.0)
	_label.size = Vector2(width, 0.0)
	_balloon.reset_size()


func _hide_balloon() -> void:
	_balloon.hide()
	_tip.hide()


## The tip sits right above her head; the balloon is centered on it but kept on screen.
func _follow_her_head() -> void:
	var drawing_viewport: Viewport = _drawing_viewport()
	var camera: Camera3D = drawing_viewport.get_camera_3d()
	if camera == null or camera.is_position_behind(global_position):
		_balloon.hide()
		_tip.hide()
		return
	# In the layer's own units: a scaled layer draws everything bigger.
	var head: Vector2 = camera.unproject_position(global_position) / _layer.scale.x
	var screen: Vector2 = drawing_viewport.get_visible_rect().size / _layer.scale.x
	var balloon_size: Vector2 = _balloon.size
	var tip_top: float = head.y - GAP_ABOVE_HEAD - TIP_SIZE.y
	var left: float = clampf(
		head.x - balloon_size.x / 2.0, SCREEN_MARGIN, screen.x - balloon_size.x - SCREEN_MARGIN
	)
	var top: float = maxf(tip_top - balloon_size.y, SCREEN_MARGIN)
	_balloon.position = Vector2(left, top)
	_tip.position = Vector2(clampf(head.x, left + TIP_SIZE.x, left + balloon_size.x - TIP_SIZE.x), top + balloon_size.y)
	_balloon.show()
	_tip.show()


func _build() -> void:
	_layer = CanvasLayer.new()
	_layer.layer = LAYER
	add_child(_layer)

	_balloon = PanelContainer.new()
	_balloon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = BALLOON_COLOR
	style.set_corner_radius_all(16)
	style.content_margin_left = 14.0
	style.content_margin_right = 14.0
	style.content_margin_top = 8.0
	style.content_margin_bottom = 9.0
	style.anti_aliasing = true
	_balloon.add_theme_stylebox_override("panel", style)
	_layer.add_child(_balloon)

	_label = Label.new()
	_label.add_theme_font_size_override("font_size", FONT_SIZE)
	_label.add_theme_color_override("font_color", TEXT_COLOR)
	_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_balloon.add_child(_label)

	_tip = Polygon2D.new()
	_tip.color = BALLOON_COLOR
	_tip.polygon = PackedVector2Array([
		Vector2(-TIP_SIZE.x / 2.0, 0.0), Vector2(TIP_SIZE.x / 2.0, 0.0), Vector2(0.0, TIP_SIZE.y)
	])
	_layer.add_child(_tip)
	_hide_balloon()


## A restarted brain counts its speeches from 1 again.
func _on_connection_changed(brain_is_connected: bool) -> void:
	if brain_is_connected:
		_shown_speech_id = NO_SPEECH_YET
