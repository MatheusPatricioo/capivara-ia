class_name ChalkboardViewer
extends CanvasLayer

## A close look at the chalkboard, drawn over the 3D world when the player clicks it:
## the capybara's 3 newest drawings, big, with their titles. The [X] button or Esc closes it.
## Like the board itself, it only reads PNG files from the discoveries folder.

const DRAWING_COUNT: int = 3
const DRAWING_SIZE: Vector2 = Vector2(360, 270)
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
		_drawing_row.add_child(_create_card(drawing["title"] as String, drawing["texture"] as Texture2D))
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


## One drawing scaled to fit its frame, with the title written below it.
func _create_card(title: String, texture: Texture2D) -> VBoxContainer:
	var picture: TextureRect = TextureRect.new()
	picture.texture = texture
	picture.custom_minimum_size = DRAWING_SIZE
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	var caption: Label = Label.new()
	caption.text = title
	caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	caption.custom_minimum_size.x = DRAWING_SIZE.x
	caption.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	var card: VBoxContainer = VBoxContainer.new()
	card.add_child(picture)
	card.add_child(caption)
	return card
