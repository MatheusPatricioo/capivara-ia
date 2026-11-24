class_name ChalkboardGallery
extends Control

## The capybara's gallery on the chalkboard: her 3 newest drawings, read straight from the
## PNG files in the discoveries folder (the same place the brain saves them). The folder is
## checked every few seconds, and the board is only redrawn when the newest drawings change.
##
## A drawing she just made is drawn stroke by stroke in the first panel: the panel waits
## blank (wait_for_new_drawing) until she reaches the board, then the chalk goes through
## the strokes (draw_new_drawing). It ends looking exactly like the PNG: a white card
## with black lines of the same width.

## Same color as the slate, so the space around the drawings blends in.
const BOARD_COLOR: Color = Color(0.12, 0.25, 0.18)
const CHALK_COLOR: Color = Color8(240, 240, 235)
const FRAME_WIDTH: float = 3.0
## The look of the PNG files (png_drawing_repository.py): white card, black 3 px pen.
const CARD_COLOR: Color = Color.WHITE
const PEN_COLOR: Color = Color.BLACK
const PEN_WIDTH_IN_GRID: float = 3.0
## How fast the chalk moves, in the brain's 400x300 grid units per second.
const CHALK_SPEED: float = 450.0
const MIN_DRAWING_SECONDS: float = 1.5
## Short enough to finish while she stays at the board (stay_seconds of her errand).
const MAX_DRAWING_SECONDS: float = 5.0

## How many drawings fit on the board.
@export var drawing_count: int = 3
## Seconds between two looks at the folder.
@export var check_interval_seconds: float = 3.0
## Top-left corner and size of each panel in canvas pixels, newest drawing first.
@export var panel_positions: Array[Vector2] = [Vector2(150, 40), Vector2(510, 40), Vector2(330, 320)]
@export var panel_size: Vector2 = Vector2(300, 225)

var _discoveries_path: String = ""
var _shown_signature: String = ""
var _drawings: Array[Dictionary] = []
## The drawing being drawn stroke by stroke in the first panel, or null.
var _new_strokes: ChalkStrokes = null
var _drawn_length: float = 0.0:
	set(value):
		_drawn_length = value
		queue_redraw()
var _drawing_tween: Tween = null


func _ready() -> void:
	_discoveries_path = DiscoveriesFolder.path()
	var check_timer: Timer = Timer.new()
	check_timer.wait_time = check_interval_seconds
	check_timer.timeout.connect(refresh)
	add_child(check_timer)
	check_timer.start()
	refresh()


## Reloads the drawings when the newest files changed (a new drawing, or one redrawn).
func refresh() -> void:
	var newest_names: PackedStringArray = _newest_drawing_names()
	var signature: String = _signature(newest_names)
	if signature == _shown_signature:
		return
	_shown_signature = signature
	_drawings = DiscoveryFiles.load_newest_drawings(_discoveries_path, newest_names.size())
	queue_redraw()


## Clears the first panel for a drawing she just made, until draw_new_drawing is called.
## Its PNG is already in the folder, so the board is refreshed to move the others along.
func wait_for_new_drawing(strokes: ChalkStrokes) -> void:
	_stop_drawing()
	_new_strokes = strokes
	_drawn_length = 0.0
	refresh()


func is_waiting_for_chalk() -> bool:
	return _new_strokes != null and _drawing_tween == null


## Draws the waiting drawing stroke by stroke; longer drawings take longer, within limits.
func draw_new_drawing() -> void:
	if not is_waiting_for_chalk():
		return
	var seconds: float = clampf(_new_strokes.total_length() / CHALK_SPEED, MIN_DRAWING_SECONDS, MAX_DRAWING_SECONDS)
	_drawing_tween = create_tween()
	_drawing_tween.tween_property(self, "_drawn_length", _new_strokes.total_length(), seconds)
	_drawing_tween.finished.connect(_stop_drawing)


## Back to the PNG of every panel.
func _stop_drawing() -> void:
	if _drawing_tween != null:
		_drawing_tween.kill()
		_drawing_tween = null
	_new_strokes = null
	queue_redraw()


func _newest_drawing_names() -> PackedStringArray:
	var all_names: PackedStringArray = DiscoveryFiles.list_newest_first(_discoveries_path, DiscoveryFiles.DRAWING_EXTENSION)
	return all_names.slice(0, mini(drawing_count, panel_positions.size()))


## Names plus modified times: changes when a file is added, removed or overwritten.
func _signature(file_names: PackedStringArray) -> String:
	var parts: PackedStringArray = PackedStringArray()
	for file_name: String in file_names:
		parts.append("%s@%d" % [file_name, FileAccess.get_modified_time(_discoveries_path.path_join(file_name))])
	return "|".join(parts)


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BOARD_COLOR)
	var panel_count: int = mini(maxi(_drawings.size(), 1 if _new_strokes != null else 0), panel_positions.size())
	for panel_index: int in panel_count:
		var panel: Rect2 = Rect2(panel_positions[panel_index], panel_size)
		if panel_index == 0 and _new_strokes != null:
			_draw_strokes_so_far(panel)
		else:
			draw_texture_rect(_drawings[panel_index]["texture"] as Texture2D, panel, false)
		draw_rect(panel, CHALK_COLOR, false, FRAME_WIDTH)


## The white card and the strokes drawn up to now, scaled from the brain's grid to the panel.
func _draw_strokes_so_far(panel: Rect2) -> void:
	draw_rect(panel, CARD_COLOR)
	var grid_to_panel: Vector2 = panel.size / ChalkStrokes.GRID_SIZE
	var pen_width: float = PEN_WIDTH_IN_GRID * grid_to_panel.x
	for stroke: PackedVector2Array in _new_strokes.visible_part(_drawn_length):
		var panel_points: PackedVector2Array = PackedVector2Array()
		for point: Vector2 in stroke:
			panel_points.append(panel.position + point * grid_to_panel)
		draw_polyline(panel_points, PEN_COLOR, pen_width, true)
