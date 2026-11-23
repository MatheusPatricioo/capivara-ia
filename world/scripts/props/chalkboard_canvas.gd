class_name ChalkboardCanvas
extends Control

## Paints the brain's chalkboard drawings in chalk: lines, circles, rectangles and texts.
## Each drawing uses the brain's 400x300 board coordinates and gets its own panel.
## When there are more drawings than panels, only the newest ones are shown.

const BRAIN_BOARD_SIZE: Vector2 = Vector2(400, 300)
## Same color as the slate material of the chalkboard model, so the panel blends in.
const BOARD_COLOR: Color = Color(0.12, 0.25, 0.18)
const CHALK_COLORS: Dictionary = {
	"white": Color8(240, 240, 235),
	"yellow": Color8(245, 225, 120),
	"pink": Color8(240, 160, 190),
	"blue": Color8(140, 190, 240),
	"green": Color8(160, 220, 150),
}
const DEFAULT_CHALK: String = "white"
const STROKE_WIDTH: float = 3.0
const FONT_SIZE: int = 18
const TITLE_FONT_SIZE: int = 22
const CIRCLE_SEGMENTS: int = 48

## Top-left corner of each panel in canvas pixels, from the oldest drawing to the newest.
@export var panel_positions: Array[Vector2] = [Vector2(150, 40), Vector2(510, 40), Vector2(330, 320)]
## Size of a panel compared to the brain's 400x300 board.
@export var panel_scale: float = 0.75

var _drawings: Array = []
var _font: Font = ThemeDB.fallback_font


func show_drawings(drawings: Array) -> void:
	_drawings = drawings
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BOARD_COLOR)
	var visible_count: int = mini(_drawings.size(), panel_positions.size())
	var first_visible: int = _drawings.size() - visible_count
	for panel_index: int in visible_count:
		_draw_drawing(_drawings[first_visible + panel_index], panel_positions[panel_index])
	draw_set_transform_matrix(Transform2D.IDENTITY)


## Moves and scales the pen to the panel, so shapes keep the brain's coordinates.
func _draw_drawing(drawing: Variant, panel_position: Vector2) -> void:
	if not drawing is Dictionary:
		return
	var drawing_data: Dictionary = drawing
	draw_set_transform(panel_position, 0.0, Vector2.ONE * panel_scale)
	var shapes: Variant = drawing_data.get("shapes", [])
	if shapes is Array:
		for shape: Variant in shapes:
			_draw_shape(shape)
	var title_position: Vector2 = Vector2(0, BRAIN_BOARD_SIZE.y + TITLE_FONT_SIZE + 6)
	draw_string(
		_font, title_position, str(drawing_data.get("title", "")),
		HORIZONTAL_ALIGNMENT_LEFT, BRAIN_BOARD_SIZE.x, TITLE_FONT_SIZE, _chalk(DEFAULT_CHALK)
	)


func _draw_shape(shape: Variant) -> void:
	if not shape is Dictionary:
		return
	var shape_data: Dictionary = shape
	var color: Color = _chalk(str(shape_data.get("color", DEFAULT_CHALK)))
	match shape_data.get("type"):
		"line":
			draw_line(_point(shape_data, "x1", "y1"), _point(shape_data, "x2", "y2"), color, STROKE_WIDTH)
		"circle":
			var radius: float = float(shape_data.get("radius", 0))
			draw_arc(_point(shape_data, "x", "y"), radius, 0.0, TAU, CIRCLE_SEGMENTS, color, STROKE_WIDTH)
		"rectangle":
			var top_left: Vector2 = _point(shape_data, "x1", "y1")
			var bottom_right: Vector2 = _point(shape_data, "x2", "y2")
			draw_rect(Rect2(top_left, bottom_right - top_left), color, false, STROKE_WIDTH)
		"text":
			# The brain places text by its top-left corner; Godot draws from the baseline.
			var baseline: Vector2 = _point(shape_data, "x", "y") + Vector2(0, FONT_SIZE)
			draw_string(
				_font, baseline, str(shape_data.get("text", "")),
				HORIZONTAL_ALIGNMENT_LEFT, -1, FONT_SIZE, color
			)


func _point(shape_data: Dictionary, x_key: String, y_key: String) -> Vector2:
	return Vector2(float(shape_data.get(x_key, 0)), float(shape_data.get(y_key, 0)))


func _chalk(color_name: String) -> Color:
	return CHALK_COLORS.get(color_name, CHALK_COLORS[DEFAULT_CHALK])
