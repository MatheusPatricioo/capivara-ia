class_name DrawingsTab
extends MarginContainer

## The Drawings tab: a gallery of the capybara's drawings, newest first, and a
## button that opens the discoveries folder in the system file explorer. The cards flow
## like words in a paragraph: as many per row as the screen width fits, centered.
## The brain sends the list first and then each drawing as a PNG in base64, asked one
## by one, so the cards appear as they arrive and no message grows with the gallery.

const EMPTY_TEXT: String = "> nenhum desenho ainda."
const UNAVAILABLE_TEXT: String = "> não consegui falar com o cérebro."
const THUMBNAIL_SIZE: Vector2 = Vector2(220, 165)
## Green like the terminal, so each white sheet sits in a thin frame.
const FRAME_COLOR: Color = Color(0.2, 0.9, 0.35)
const FRAME_WIDTH: int = 2

@onready var _drawing_grid: HFlowContainer = %DrawingGrid
@onready var _drawing_count: Label = %DrawingCount
@onready var _open_folder_button: Button = %OpenFolderButton

var _discoveries_path: String = ""
## Grows on every show_drawings(), so a gallery still loading stops when a new one starts.
var _load_count: int = 0


func _ready() -> void:
	_open_folder_button.pressed.connect(_open_folder)


## Asks the brain for the gallery again. Called every time the computer screen opens.
func show_drawings() -> void:
	_load_count += 1
	var this_load: int = _load_count
	_clear_gallery()
	_open_folder_button.disabled = true
	var reply: Dictionary = await BrainQuestion.ask({"type": "list_drawings"})
	if this_load != _load_count:
		return
	if reply.get("type") != "drawing_list":
		_drawing_count.text = UNAVAILABLE_TEXT
		return
	_discoveries_path = str(reply.get("folder_path", ""))
	# The brain may run on another machine: the button only opens a folder that is here.
	_open_folder_button.disabled = not DirAccess.dir_exists_absolute(_discoveries_path)
	var drawings: Variant = reply.get("drawings", [])
	if not drawings is Array:
		drawings = []
	var shown_count: int = 0
	for drawing: Variant in drawings:
		if not drawing is Dictionary or not drawing.get("id") is String:
			continue
		var picture: ImageTexture = await _download_drawing(drawing["id"])
		if this_load != _load_count:
			return
		if picture != null:
			_drawing_grid.add_child(_create_card(str(drawing.get("title", "")), picture))
			shown_count += 1
	_drawing_count.text = "> %d desenho(s)" % shown_count if shown_count > 0 else EMPTY_TEXT


## The drawing as a texture, or null when the brain could not send a valid PNG.
func _download_drawing(drawing_id: String) -> ImageTexture:
	var reply: Dictionary = await BrainQuestion.ask({"type": "get_drawing", "id": drawing_id})
	if reply.get("type") != "drawing":
		return null
	var png: PackedByteArray = Marshalls.base64_to_raw(str(reply.get("png_base64", "")))
	var picture: Image = Image.new()
	if png.is_empty() or picture.load_png_from_buffer(png) != OK:
		return null
	return ImageTexture.create_from_image(picture)


func _clear_gallery() -> void:
	for card: Node in _drawing_grid.get_children():
		card.queue_free()


## One gallery card: the drawing scaled to fit inside a frame, with its title below.
func _create_card(title: String, drawing: ImageTexture) -> VBoxContainer:
	var picture: TextureRect = TextureRect.new()
	picture.texture = drawing
	picture.custom_minimum_size = THUMBNAIL_SIZE
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	picture.tooltip_text = title
	var frame: PanelContainer = PanelContainer.new()
	frame.add_theme_stylebox_override("panel", _create_frame_style())
	frame.add_child(picture)
	var caption: Label = Label.new()
	caption.text = title
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


## The path always comes from the brain's list reply, never from file contents.
func _open_folder() -> void:
	if DirAccess.dir_exists_absolute(_discoveries_path):
		OS.shell_open(_discoveries_path)
