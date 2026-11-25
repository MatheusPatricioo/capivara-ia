class_name CreatorChatBox
extends CanvasLayer

## A line at the bottom of the screen for her creator to talk with her. Enter opens it,
## Enter sends and Esc closes. It stays open after sending, so the conversation flows;
## her replies appear in the balloon above her. While the box has the focus, the keys go
## to the text and never to the world.

const LAYER: int = 5
const BOX_WIDTH: float = 640.0
const BOTTOM_MARGIN: float = 24.0
const BOX_HEIGHT: float = 48.0
const HINT_HEIGHT: float = 28.0
## Same limit as the brain (MAX_CREATOR_MESSAGE_LENGTH): longer messages are refused there.
const MAX_MESSAGE_LENGTH: int = 2000
const PLACEHOLDER: String = "Fale com ela... (Enter envia, Esc fecha)"
const OFFLINE_PLACEHOLDER: String = "O cérebro dela está desligado. Tente de novo daqui a pouco."
const HINT: String = "Enter: falar com ela"

var _message_field: LineEdit
var _hint: Label


func _ready() -> void:
	layer = LAYER
	_build()
	close()


func open() -> void:
	_message_field.show()
	_hint.hide()
	_message_field.placeholder_text = PLACEHOLDER
	_message_field.grab_focus()


func close() -> void:
	_message_field.release_focus()
	_message_field.hide()
	_hint.show()


## Unhandled, so Enter only opens the box when no other screen or field took it first.
func _unhandled_input(event: InputEvent) -> void:
	if not _message_field.visible and _is_enter(event):
		open()
		get_viewport().set_input_as_handled()


## _input runs before the GUI, so Esc closes the box even while the text has the focus.
func _input(event: InputEvent) -> void:
	if _message_field.visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _send(text: String) -> void:
	var message: String = text.strip_edges()
	if message.is_empty():
		return
	if not Brain.send_creator_message(message):
		_message_field.placeholder_text = OFFLINE_PLACEHOLDER
		return
	_message_field.clear()


func _is_enter(event: InputEvent) -> bool:
	var key: InputEventKey = event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return false
	return key.keycode == KEY_ENTER or key.keycode == KEY_KP_ENTER


func _build() -> void:
	_message_field = LineEdit.new()
	_message_field.anchor_left = 0.5
	_message_field.anchor_right = 0.5
	_message_field.anchor_top = 1.0
	_message_field.anchor_bottom = 1.0
	_message_field.offset_left = -BOX_WIDTH / 2.0
	_message_field.offset_right = BOX_WIDTH / 2.0
	_message_field.offset_top = -BOTTOM_MARGIN - BOX_HEIGHT
	_message_field.offset_bottom = -BOTTOM_MARGIN
	_message_field.max_length = MAX_MESSAGE_LENGTH
	_message_field.add_theme_stylebox_override("normal", PaperStyle.panel(PaperStyle.PAPER_COLOR, 2, 10))
	_message_field.add_theme_stylebox_override("focus", PaperStyle.panel(PaperStyle.PAPER_COLOR, 3, 10))
	_message_field.add_theme_color_override("font_color", PaperStyle.INK_COLOR)
	_message_field.add_theme_color_override("font_placeholder_color", PaperStyle.BORDER_COLOR)
	_message_field.add_theme_font_size_override("font_size", PaperStyle.TEXT_FONT_SIZE)
	_message_field.text_submitted.connect(_send)
	add_child(_message_field)

	_hint = Label.new()
	_hint.text = HINT
	_hint.anchor_top = 1.0
	_hint.anchor_bottom = 1.0
	_hint.offset_left = BOTTOM_MARGIN
	_hint.offset_top = -BOTTOM_MARGIN - HINT_HEIGHT
	_hint.offset_bottom = -BOTTOM_MARGIN
	_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hint.add_theme_color_override("font_color", Color(1, 1, 1, 0.8))
	_hint.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.6))
	_hint.add_theme_constant_override("outline_size", 4)
	add_child(_hint)
