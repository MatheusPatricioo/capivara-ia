class_name CreatorChatBox
extends CanvasLayer

## Where her creator talks with her, at the bottom of the screen. Closed, it is a small
## "Conversar" button (Enter also opens it). Open, a dark rounded bar with the text field
## and a send button; Esc closes it. It stays open after sending, so the conversation
## flows, and her replies appear in the balloon above her. The Voz/Mudo pill in the bar
## switches whether she also says them out loud.

const LAYER: int = 5
const BAR_WIDTH: float = 620.0
const BOTTOM_MARGIN: float = 28.0
const FONT_SIZE: int = 18
const KEYCAP_FONT_SIZE: int = 12
const OPEN_SECONDS: float = 0.15
## Same limit as the brain (MAX_CREATOR_MESSAGE_LENGTH): longer messages are refused there.
const MAX_MESSAGE_LENGTH: int = 2000

const PLACEHOLDER: String = "Diga algo para ela…"
const OFFLINE_PLACEHOLDER: String = "O cérebro dela está desligado"
const OPEN_BUTTON_TEXT: String = "Conversar"
const OPEN_KEY_TEXT: String = "Enter"
const SEND_BUTTON_TEXT: String = "Enviar"

const BAR_COLOR: Color = Color(0.12, 0.09, 0.07, 0.82)
const BUTTON_HOVER_COLOR: Color = Color(0.2, 0.15, 0.11, 0.9)
const TEXT_COLOR: Color = Color(0.98, 0.95, 0.88)
const MUTED_TEXT_COLOR: Color = Color(0.98, 0.95, 0.88, 0.45)
const ACCENT_COLOR: Color = Color(0.86, 0.62, 0.34)
const ACCENT_HOVER_COLOR: Color = Color(0.93, 0.7, 0.42)

var _open_button: Button
var _bar: PanelContainer
var _message_field: LineEdit


func _ready() -> void:
	layer = LAYER
	_build()
	close()


func open() -> void:
	_open_button.hide()
	_bar.show()
	_message_field.placeholder_text = PLACEHOLDER
	_message_field.grab_focus()
	_bar.modulate.a = 0.0
	create_tween().set_ease(Tween.EASE_OUT).tween_property(_bar, "modulate:a", 1.0, OPEN_SECONDS)


func close() -> void:
	_message_field.release_focus()
	_bar.hide()
	_open_button.show()


## Enter opens the bar, or gives the focus back to it after a click in the world.
## Unhandled, so it only happens when no other screen or field took the key first.
func _unhandled_input(event: InputEvent) -> void:
	if not _is_enter(event) or KeyboardFocus.is_typing(get_viewport()):
		return
	if _bar.visible:
		_message_field.grab_focus()
	else:
		open()
	get_viewport().set_input_as_handled()


## _input runs before the GUI, so Esc closes the bar even while the text has the focus.
func _input(event: InputEvent) -> void:
	if _bar.visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _send() -> void:
	var message: String = _message_field.text.strip_edges()
	if message.is_empty():
		return
	if not Brain.send_creator_message(message):
		_message_field.placeholder_text = OFFLINE_PLACEHOLDER
		return
	_message_field.clear()
	_message_field.grab_focus()


func _is_enter(event: InputEvent) -> bool:
	var key: InputEventKey = event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return false
	return key.keycode == KEY_ENTER or key.keycode == KEY_KP_ENTER


func _build() -> void:
	_bar = _build_bar()
	add_child(_bar)
	_open_button = _build_open_button()
	add_child(_open_button)


func _build_bar() -> PanelContainer:
	var bar: PanelContainer = PanelContainer.new()
	_anchor_bottom_center(bar, BAR_WIDTH)
	bar.add_theme_stylebox_override("panel", _rounded(BAR_COLOR, 26.0, Vector2(18.0, 6.0)))

	var row: HBoxContainer = HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	bar.add_child(row)

	_message_field = LineEdit.new()
	_message_field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_message_field.max_length = MAX_MESSAGE_LENGTH
	_message_field.flat = true
	_message_field.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	_message_field.add_theme_color_override("font_color", TEXT_COLOR)
	_message_field.add_theme_color_override("font_placeholder_color", MUTED_TEXT_COLOR)
	_message_field.add_theme_color_override("caret_color", ACCENT_COLOR)
	_message_field.add_theme_font_size_override("font_size", FONT_SIZE)
	_message_field.text_submitted.connect(func(_text: String) -> void: _send())
	row.add_child(_message_field)
	row.add_child(_build_voice_toggle())

	var send_button: Button = Button.new()
	send_button.text = SEND_BUTTON_TEXT
	send_button.focus_mode = Control.FOCUS_NONE
	send_button.add_theme_stylebox_override("normal", _rounded(ACCENT_COLOR, 18.0, Vector2(16.0, 6.0)))
	send_button.add_theme_stylebox_override("hover", _rounded(ACCENT_HOVER_COLOR, 18.0, Vector2(16.0, 6.0)))
	send_button.add_theme_stylebox_override("pressed", _rounded(ACCENT_COLOR, 18.0, Vector2(16.0, 6.0)))
	send_button.add_theme_color_override("font_color", BAR_COLOR)
	send_button.add_theme_color_override("font_hover_color", BAR_COLOR)
	send_button.add_theme_font_size_override("font_size", FONT_SIZE - 2)
	send_button.pressed.connect(_send)
	row.add_child(send_button)
	return bar


## Outlined in the accent color while her voice is on, faded while she is muted.
func _build_voice_toggle() -> VoiceModeToggle:
	var toggle: VoiceModeToggle = VoiceModeToggle.new()
	var voice_on_style: StyleBoxFlat = _rounded(Color(0, 0, 0, 0), 18.0, Vector2(14.0, 6.0))
	voice_on_style.border_color = ACCENT_COLOR
	voice_on_style.set_border_width_all(1)
	var muted_style: StyleBoxFlat = _rounded(Color(0, 0, 0, 0), 18.0, Vector2(14.0, 6.0))
	muted_style.border_color = MUTED_TEXT_COLOR
	muted_style.set_border_width_all(1)
	toggle.add_theme_stylebox_override("normal", muted_style)
	toggle.add_theme_stylebox_override("hover", muted_style)
	toggle.add_theme_stylebox_override("pressed", voice_on_style)
	toggle.add_theme_stylebox_override("hover_pressed", voice_on_style)
	toggle.add_theme_color_override("font_color", MUTED_TEXT_COLOR)
	toggle.add_theme_color_override("font_hover_color", TEXT_COLOR)
	toggle.add_theme_color_override("font_pressed_color", ACCENT_COLOR)
	toggle.add_theme_color_override("font_hover_pressed_color", ACCENT_HOVER_COLOR)
	toggle.add_theme_font_size_override("font_size", FONT_SIZE - 2)
	return toggle


## A small pill with the label and the key that also opens it, drawn as a keycap.
func _build_open_button() -> Button:
	var button: Button = Button.new()
	_anchor_bottom_center(button, 0.0)
	button.grow_horizontal = Control.GROW_DIRECTION_BOTH
	button.focus_mode = Control.FOCUS_NONE
	button.text = OPEN_BUTTON_TEXT
	button.add_theme_stylebox_override("normal", _rounded(BAR_COLOR, 20.0, Vector2(18.0, 8.0), 62.0))
	button.add_theme_stylebox_override("hover", _rounded(BUTTON_HOVER_COLOR, 20.0, Vector2(18.0, 8.0), 62.0))
	button.add_theme_stylebox_override("pressed", _rounded(BAR_COLOR, 20.0, Vector2(18.0, 8.0), 62.0))
	button.add_theme_color_override("font_color", TEXT_COLOR)
	button.add_theme_color_override("font_hover_color", TEXT_COLOR)
	button.add_theme_font_size_override("font_size", FONT_SIZE - 2)
	button.pressed.connect(open)

	var keycap: Label = Label.new()
	keycap.text = OPEN_KEY_TEXT
	keycap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	keycap.anchor_left = 1.0
	keycap.anchor_right = 1.0
	keycap.anchor_top = 0.5
	keycap.anchor_bottom = 0.5
	keycap.offset_left = -54.0
	keycap.offset_right = -12.0
	keycap.offset_top = -10.0
	keycap.offset_bottom = 10.0
	keycap.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	keycap.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	keycap.add_theme_font_size_override("font_size", KEYCAP_FONT_SIZE)
	keycap.add_theme_color_override("font_color", MUTED_TEXT_COLOR)
	var keycap_style: StyleBoxFlat = _rounded(Color(0, 0, 0, 0), 5.0, Vector2.ZERO)
	keycap_style.border_color = MUTED_TEXT_COLOR
	keycap_style.set_border_width_all(1)
	keycap.add_theme_stylebox_override("normal", keycap_style)
	button.add_child(keycap)
	return button


func _anchor_bottom_center(control: Control, width: float) -> void:
	control.anchor_left = 0.5
	control.anchor_right = 0.5
	control.anchor_top = 1.0
	control.anchor_bottom = 1.0
	control.offset_left = -width / 2.0
	control.offset_right = width / 2.0
	control.offset_bottom = -BOTTOM_MARGIN
	control.offset_top = -BOTTOM_MARGIN
	control.grow_vertical = Control.GROW_DIRECTION_BEGIN


## right_padding leaves room on the right, like for the keycap inside the open button.
func _rounded(color: Color, radius: float, padding: Vector2, right_padding: float = -1.0) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(int(radius))
	style.content_margin_left = padding.x
	style.content_margin_right = right_padding if right_padding >= 0.0 else padding.x
	style.content_margin_top = padding.y
	style.content_margin_bottom = padding.y
	style.anti_aliasing = true
	return style
