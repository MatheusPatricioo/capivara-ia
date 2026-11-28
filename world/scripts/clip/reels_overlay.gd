class_name ReelsOverlay
extends Control

## The look of a phone recording, drawn over the vertical frame and never recorded: a
## blinking red REC dot, the time since it started, and the Instagram Reels safe zones,
## the bands at the top and bottom (and the thin side margins) where the app draws its
## own buttons, caption and profile over the video. What matters in the shot belongs in
## the clear area between them.

## Fractions of the frame covered by the app, from Meta's Reels safe zone guidance
## (about 250 px at the top, 670 px at the bottom and 65 px at each side of 1080x1920).
const TOP_BAND_FRACTION: float = 0.14
const BOTTOM_BAND_FRACTION: float = 0.35
const SIDE_MARGIN_FRACTION: float = 0.06
const BAND_COLOR: Color = Color(0.0, 0.0, 0.0, 0.28)
const GUIDE_COLOR: Color = Color(1.0, 1.0, 1.0, 0.55)
const GUIDE_WIDTH: float = 1.5
const GUIDE_DASH: float = 8.0
const REC_COLOR: Color = Color(0.93, 0.16, 0.16)
const TEXT_COLOR: Color = Color(1.0, 1.0, 1.0, 0.95)
const BLINK_SECONDS: float = 0.5
## Sizes relative to the frame's height, so the look is the same in any window.
const DOT_RADIUS_FRACTION: float = 0.009
const FONT_SIZE_FRACTION: float = 0.022
const MARGIN_FRACTION: float = 0.03
const SECONDS_PER_MINUTE: int = 60

var _elapsed_seconds: float = 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


## The REC clock starts again from zero.
func restart_clock() -> void:
	_elapsed_seconds = 0.0
	queue_redraw()


func _process(delta: float) -> void:
	_elapsed_seconds += delta
	queue_redraw()


## "mm:ss", the way a camera shows it.
static func format_clock(seconds: float) -> String:
	var whole_seconds: int = int(seconds)
	@warning_ignore("integer_division")
	var minutes: int = whole_seconds / SECONDS_PER_MINUTE
	return "%02d:%02d" % [minutes, whole_seconds % SECONDS_PER_MINUTE]


func _draw() -> void:
	_draw_safe_zones()
	_draw_rec_and_clock()


func _draw_safe_zones() -> void:
	var top_height: float = size.y * TOP_BAND_FRACTION
	var bottom_height: float = size.y * BOTTOM_BAND_FRACTION
	var side_width: float = size.x * SIDE_MARGIN_FRACTION
	var bottom_top: float = size.y - bottom_height
	draw_rect(Rect2(0.0, 0.0, size.x, top_height), BAND_COLOR)
	draw_rect(Rect2(0.0, bottom_top, size.x, bottom_height), BAND_COLOR)
	var clear_area: Rect2 = Rect2(side_width, top_height, size.x - 2.0 * side_width, bottom_top - top_height)
	_draw_dashed_rect(clear_area)


func _draw_dashed_rect(area: Rect2) -> void:
	var corners: Array[Vector2] = [
		area.position, Vector2(area.end.x, area.position.y), area.end, Vector2(area.position.x, area.end.y)
	]
	for corner_index: int in corners.size():
		var from: Vector2 = corners[corner_index]
		var to: Vector2 = corners[(corner_index + 1) % corners.size()]
		draw_dashed_line(from, to, GUIDE_COLOR, GUIDE_WIDTH, GUIDE_DASH)


func _draw_rec_and_clock() -> void:
	var margin: float = size.y * MARGIN_FRACTION
	var dot_radius: float = size.y * DOT_RADIUS_FRACTION
	var font_size: int = maxi(int(size.y * FONT_SIZE_FRACTION), 8)
	var font: Font = ThemeDB.fallback_font
	var dot_center: Vector2 = Vector2(margin + dot_radius, margin + dot_radius)
	var is_dot_lit: bool = int(_elapsed_seconds / BLINK_SECONDS) % 2 == 0
	if is_dot_lit:
		draw_circle(dot_center, dot_radius, REC_COLOR)
	var text_left: float = dot_center.x + dot_radius * 2.0
	# Text centered on the dot: the baseline sits half the letters' height below its center.
	var baseline: float = dot_center.y + (font.get_ascent(font_size) - font.get_descent(font_size)) / 2.0
	var text: String = "REC  " + format_clock(_elapsed_seconds)
	draw_string(font, Vector2(text_left, baseline), text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, TEXT_COLOR)
