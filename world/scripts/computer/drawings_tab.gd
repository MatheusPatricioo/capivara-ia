class_name DrawingsTab
extends MarginContainer

## The Drawings tab: a gallery of the capybara's drawings, newest first, and a
## button that opens the discoveries folder in the system file explorer. The cards flow
## like words in a paragraph: as many per row as the screen width fits, centered.

const EMPTY_TEXT: String = "> nenhum desenho ainda."
const THUMBNAIL_SIZE: Vector2 = Vector2(220, 165)
## Green like the terminal, so each white sheet sits in a thin frame.
const FRAME_COLOR: Color = Color(0.2, 0.9, 0.35)
const FRAME_WIDTH: int = 2

@onready var _drawing_grid: HFlowContainer = %DrawingGrid
@onready var _drawing_count: Label = %DrawingCount
@onready var _open_folder_button: Button = %OpenFolderButton

var _discoveries_path: String = ""


func _ready() -> void:
	_open_folder_button.pressed.connect(_open_folder)


## Loads the gallery again. Called every time the computer screen opens.
func show_drawings(discoveries_path: String) -> void:
	_discoveries_path = discoveries_path
	_open_folder_button.disabled = not DirAccess.dir_exists_absolute(discoveries_path)
	_clear_gallery()
	var file_names: PackedStringArray = DiscoveryFiles.list_newest_first(discoveries_path, DiscoveryFiles.DRAWING_EXTENSION)
	var shown_count: int = 0
	for file_name: String in file_names:
		var drawing: ImageTexture = DiscoveryFiles.load_drawing(discoveries_path, file_name)
		if drawing != null:
			_drawing_grid.add_child(_create_card(file_name, drawing))
			shown_count += 1
	_drawing_count.text = "> %d desenho(s)" % shown_count if shown_count > 0 else EMPTY_TEXT


func _clear_gallery() -> void:
	for card: Node in _drawing_grid.get_children():
		card.queue_free()


## One gallery card: the drawing scaled to fit inside a frame, with its title below.
func _create_card(file_name: String, drawing: ImageTexture) -> VBoxContainer:
	var picture: TextureRect = TextureRect.new()
	picture.texture = drawing
	picture.custom_minimum_size = THUMBNAIL_SIZE
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	picture.tooltip_text = file_name
	var frame: PanelContainer = PanelContainer.new()
	frame.add_theme_stylebox_override("panel", _create_frame_style())
	frame.add_child(picture)
	var caption: Label = Label.new()
	caption.text = DiscoveryFiles.title_from_file_name(file_name)
	caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	caption.custom_minimum_size.x = THUMBNAIL_SIZE.x
	caption.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	var card: VBoxContainer = VBoxContainer.new()
	card.add_child(frame)
	card.add_child(caption)
	return card


func _create_frame_style() -> StyleBoxFlat:
	var frame_style: StyleBoxFlat = StyleBoxFlat.new()
	frame_style.bg_color = Color.WHITE
	frame_style.border_color = FRAME_COLOR
	frame_style.set_border_width_all(FRAME_WIDTH)
	return frame_style


## The path always comes from DiscoveriesFolder, never from file contents.
func _open_folder() -> void:
	if DirAccess.dir_exists_absolute(_discoveries_path):
		OS.shell_open(_discoveries_path)
