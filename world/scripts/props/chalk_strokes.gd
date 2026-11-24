class_name ChalkStrokes
extends RefCounted

## The strokes of one drawing, in the order she drew them, revealed little by little like
## chalk on a board. The points come from the brain, in its 400x300 drawing grid.
##
## Progress is measured in length of chalk used: a long stroke takes longer than a short
## one, and lifting the chalk between two strokes costs a little length too (a short pause).

## The brain's drawing grid (CANVAS_WIDTH x CANVAS_HEIGHT in brain/src/domain/drawing.py).
const GRID_SIZE: Vector2 = Vector2(400, 300)
## The pause for lifting the chalk between two strokes, as if it were this much line.
const LIFT_LENGTH: float = 40.0
const MIN_POINTS_PER_STROKE: int = 2

var _strokes: Array[PackedVector2Array] = []
var _stroke_lengths: PackedFloat32Array = PackedFloat32Array()
var _total_length: float = 0.0


func _init(strokes: Array[PackedVector2Array]) -> void:
	_strokes = strokes
	for stroke: PackedVector2Array in strokes:
		_stroke_lengths.append(_length_of(stroke))
	for stroke_length: float in _stroke_lengths:
		_total_length += stroke_length
	_total_length += LIFT_LENGTH * maxi(strokes.size() - 1, 0)


## Reads one drawing of the brain's chalkboard message: {"title": ..., "strokes": [{"points":
## [{"x": 10, "y": 20}, ...]}, ...]}. Anything malformed is skipped, never trusted.
static func from_message(drawing: Dictionary) -> ChalkStrokes:
	var strokes: Array[PackedVector2Array] = []
	var raw_strokes: Variant = drawing.get("strokes", [])
	if raw_strokes is Array:
		for raw_stroke: Variant in raw_strokes:
			var stroke: PackedVector2Array = _stroke_from_message(raw_stroke)
			if stroke.size() >= MIN_POINTS_PER_STROKE:
				strokes.append(stroke)
	return ChalkStrokes.new(strokes)


func is_empty() -> bool:
	return _strokes.is_empty()


## Length of chalk needed to draw everything, pauses included.
func total_length() -> float:
	return _total_length


## The part already on the board after drawn_length of chalk: the finished strokes, plus
## the stroke being drawn cut where the chalk is now.
func visible_part(drawn_length: float) -> Array[PackedVector2Array]:
	var visible: Array[PackedVector2Array] = []
	var length_left: float = drawn_length
	for stroke_index: int in _strokes.size():
		if length_left <= 0.0:
			break
		visible.append(_cut(_strokes[stroke_index], length_left))
		length_left -= _stroke_lengths[stroke_index] + LIFT_LENGTH
	return visible


static func _stroke_from_message(raw_stroke: Variant) -> PackedVector2Array:
	var stroke: PackedVector2Array = PackedVector2Array()
	if not raw_stroke is Dictionary:
		return stroke
	var raw_points: Variant = (raw_stroke as Dictionary).get("points", [])
	if not raw_points is Array:
		return stroke
	for raw_point: Variant in raw_points:
		if raw_point is Dictionary:
			var point: Dictionary = raw_point
			stroke.append(Vector2(float(point.get("x", 0)), float(point.get("y", 0))))
	return stroke


static func _length_of(stroke: PackedVector2Array) -> float:
	var stroke_length: float = 0.0
	for point_index: int in range(1, stroke.size()):
		stroke_length += stroke[point_index - 1].distance_to(stroke[point_index])
	return stroke_length


## The beginning of the stroke, up to `length` along its points.
static func _cut(stroke: PackedVector2Array, length: float) -> PackedVector2Array:
	var part: PackedVector2Array = PackedVector2Array([stroke[0]])
	var length_left: float = length
	for point_index: int in range(1, stroke.size()):
		var segment_start: Vector2 = stroke[point_index - 1]
		var segment_end: Vector2 = stroke[point_index]
		var segment_length: float = segment_start.distance_to(segment_end)
		if length_left >= segment_length:
			part.append(segment_end)
			length_left -= segment_length
			continue
		part.append(segment_start.lerp(segment_end, length_left / segment_length))
		break
	return part
