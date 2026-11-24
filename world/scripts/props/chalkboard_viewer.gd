class_name ChalkboardViewer
extends CanvasLayer

## A close look at the chalkboard, drawn over the 3D world when the player clicks it:
## the capybara's 3 newest drawings, big, without captions (only the drawings, like on the
## board). The [X] button or Esc closes it.
## Like the board itself, it only reads PNG files from the discoveries folder.
## The board fills a share of the screen and the drawings share its width, so it fits any
## window size instead of a fixed one.

const DRAWING_COUNT: int = 3
## The smallest a card gets: below that the window is too small to see anything anyway.
const MIN_CARD_SIZE: Vector2 = Vector2(160, 120)
## Width / height of a card: the drawings are 4:3 (400x300 in the brain).
const CARD_RATIO: float = 4.0 / 3.0
## Chalk white, like the frames on the board in the world.
const FRAME_COLOR: Color = Color8(240, 240, 235)
const FRAME_WIDTH: int = 3
const EMPTY_TEXT: String = "A lousa ainda está vazia: nenhum desenho por enquanto."

@onready var _drawing_row: HBoxContainer = %DrawingRow
@onready var _empty_label: Label = %EmptyLabel
@onready var _close_button: Button = %CloseButton


func _ready() -> void:
	hide()
	_close_button.pressed.connect(close)


## Reads the folder again on every open, so it always shows the current drawings.
func open() -> void:
	_clear_drawings()
	var drawings: Array[Dictionary] = DiscoveryFiles.load_newest_drawings(DiscoveriesFolder.path(), DRAWING_COUNT)
	for drawing: Dictionary in drawings:
		_drawing_row.add_child(_create_card(drawing["texture"] as Texture2D))
	_empty_label.text = EMPTY_TEXT
	_empty_label.visible = drawings.is_empty()
	show()


func close() -> void:
	hide()


## _input runs before the GUI, so Esc closes the board even when the button has the focus.
func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _clear_drawings() -> void:
	for card: Node in _drawing_row.get_children():
		card.queue_free()


## One drawing in a chalk frame. Each card takes an equal share of the row, and the
## AspectRatioContainer keeps its shape at any window size (centered in the space it gets).
func _create_card(texture: Texture2D) -> AspectRatioContainer:
	var card: AspectRatioContainer = AspectRatioContainer.new()
	card.ratio = CARD_RATIO
	card.custom_minimum_size = MIN_CARD_SIZE
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	card.add_child(_create_framed_picture(texture))
	return card


func _create_framed_picture(texture: Texture2D) -> PanelContainer:
	var picture: TextureRect = TextureRect.new()
	picture.texture = texture
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	var frame: PanelContainer = PanelContainer.new()
	frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
	frame.add_theme_stylebox_override("panel", _create_frame_style())
	frame.add_child(picture)
	return frame


func _create_frame_style() -> StyleBoxFlat:
	var frame_style: StyleBoxFlat = StyleBoxFlat.new()
	frame_style.bg_color = Color.WHITE
	frame_style.border_color = FRAME_COLOR
	frame_style.set_border_width_all(FRAME_WIDTH)
	return frame_style
