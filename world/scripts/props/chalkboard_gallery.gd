class_name ChalkboardGallery
extends Control

## The capybara's gallery on the chalkboard: her 3 newest drawings, read straight from the
## PNG files in the discoveries folder (the same place the brain saves them). The folder is
## checked every few seconds, and the board is only redrawn when the newest drawings change.

## Same color as the slate, so the space around the drawings blends in.
const BOARD_COLOR: Color = Color(0.12, 0.25, 0.18)
const CHALK_COLOR: Color = Color8(240, 240, 235)
const FRAME_WIDTH: float = 3.0
const TITLE_FONT_SIZE: int = 22
const TITLE_GAP: float = 6.0

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
var _font: Font = ThemeDB.fallback_font


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
	for drawing_index: int in _drawings.size():
		var panel: Rect2 = Rect2(panel_positions[drawing_index], panel_size)
		draw_texture_rect(_drawings[drawing_index]["texture"] as Texture2D, panel, false)
		draw_rect(panel, CHALK_COLOR, false, FRAME_WIDTH)
		var title_position: Vector2 = panel.position + Vector2(0, panel.size.y + TITLE_FONT_SIZE + TITLE_GAP)
		draw_string(_font, title_position, _drawings[drawing_index]["title"] as String, HORIZONTAL_ALIGNMENT_CENTER, panel.size.x, TITLE_FONT_SIZE, CHALK_COLOR)
