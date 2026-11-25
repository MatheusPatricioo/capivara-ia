class_name MailboxViewer
extends CanvasLayer

## The inside of the mailbox, drawn over the 3D world like a sheet of letter paper: the
## letters on the left (newest first, a dot on the unread ones) and the chosen letter on
## the right. Opening a letter tells the brain, which marks it as read. The letters come
## from the brain (Brain.mailbox_changed); this only shows them. Under a letter Matheus
## can write one reply: it is sent to the brain, which keeps it with the letter and sends
## the mailbox back with the reply in it. [X] or Esc closes it.

const LAYER: int = 10
const UNREAD_MARK: String = "● "
const READ_MARK: String = "    "
const EMPTY_TEXT: String = "A caixa está vazia. Quando ela sentir saudade, uma cartinha aparece aqui."
const CHOOSE_TEXT: String = "Escolha uma carta na lista."
const REPLY_HEADING: String = "

— Sua resposta (%s):

"
const REPLY_PLACEHOLDER: String = "Escreva sua resposta para ela..."
const SENDING_TEXT: String = "Enviando..."
const REFUSED_TEXT: String = "Não deu para guardar a resposta. Veja o log do cérebro."
const OFFLINE_TEXT: String = "O cérebro está desligado. Tente de novo quando ele voltar."
const TOO_LONG_TEXT: String = "Muito longa: no máximo %d caracteres."
## The same limit the brain puts on a letter and on a reply.
const MAX_REPLY_LENGTH: int = 1500
const REPLY_BOX_HEIGHT: float = 110.0
const PAPER_COLOR: Color = Color(0.98, 0.95, 0.86)
const LIST_COLOR: Color = Color(0.93, 0.88, 0.76)
const INK_COLOR: Color = Color(0.25, 0.17, 0.1)
const BORDER_COLOR: Color = Color(0.55, 0.38, 0.22)
const SHADE_COLOR: Color = Color(0.0, 0.0, 0.0, 0.45)
const TITLE_FONT_SIZE: int = 26
const TEXT_FONT_SIZE: int = 19
const LIST_WIDTH: float = 230.0
## Share of the screen left empty around the paper on each side.
const SCREEN_MARGIN: float = 0.12

var _letters: Array = []
var _letter_list: ItemList
var _letter_text: RichTextLabel
var _reply_box: VBoxContainer
var _reply_input: TextEdit
var _send_button: Button
var _reply_status: Label


func _ready() -> void:
	layer = LAYER
	_build()
	hide()
	Brain.mailbox_changed.connect(_on_mailbox_changed)


func open() -> void:
	_fill_list()
	show()


func close() -> void:
	hide()


## _input runs before the GUI, so Esc closes the mailbox even when the list has the focus.
func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


func _on_mailbox_changed(letters: Array) -> void:
	_letters = letters
	if visible:
		_fill_list()


## Lists the letters again, keeping the chosen one chosen (the brain resends the whole
## mailbox right after a letter is opened).
func _fill_list() -> void:
	var chosen_file_name: String = _chosen_file_name()
	_letter_list.clear()
	for letter_index: int in _letters.size():
		var letter: Dictionary = _letters[letter_index]
		_letter_list.add_item(_list_title(letter))
		if str(letter.get("file_name", "")) == chosen_file_name:
			_letter_list.select(letter_index)
			_show_letter(letter)
	if _letter_list.get_selected_items().is_empty():
		_letter_text.text = EMPTY_TEXT if _letters.is_empty() else CHOOSE_TEXT
		_reply_box.hide()


func _chosen_file_name() -> String:
	var selected: PackedInt32Array = _letter_list.get_selected_items()
	if selected.is_empty() or selected[0] >= _letters.size():
		return ""
	var letter: Dictionary = _letters[selected[0]]
	return str(letter.get("file_name", ""))


func _list_title(letter: Dictionary) -> String:
	var mark: String = UNREAD_MARK if bool(letter.get("unread", false)) else READ_MARK
	return mark + _readable_date(str(letter.get("written_at", "")))


## "2026-11-25T14:30" becomes "25/11 às 14:30".
func _readable_date(written_at: String) -> String:
	var date_and_time: PackedStringArray = written_at.split("T")
	if date_and_time.size() != 2:
		return written_at
	var date_parts: PackedStringArray = date_and_time[0].split("-")
	if date_parts.size() != 3:
		return written_at
	return "%s/%s às %s" % [date_parts[2], date_parts[1], date_and_time[1]]


func _open_letter(letter_index: int) -> void:
	var letter: Dictionary = _letters[letter_index]
	_reply_input.clear()
	_show_letter(letter)
	if not bool(letter.get("unread", false)):
		return
	Brain.report_letter_opened(str(letter.get("file_name", "")))
	letter["unread"] = false
	_letter_list.set_item_text(letter_index, _list_title(letter))


## The letter, with Matheus's reply under it, or the box to write one when it has none.
func _show_letter(letter: Dictionary) -> void:
	var reply: Variant = letter.get("reply")
	var text: String = str(letter.get("text", ""))
	if reply is String:
		var replied_at: String = _readable_date(str(letter.get("replied_at", "")))
		text += (REPLY_HEADING % replied_at) + str(reply)
	_letter_text.text = text
	_reply_box.visible = not reply is String
	# The mailbox came back still without the reply: the brain refused it.
	var was_refused: bool = _reply_status.text == SENDING_TEXT and not reply is String
	_reply_status.text = REFUSED_TEXT if was_refused else ""
	_send_button.disabled = false


func _send_reply() -> void:
	var file_name: String = _chosen_file_name()
	var text: String = _reply_input.text.strip_edges()
	if file_name.is_empty() or text.is_empty():
		return
	if text.length() > MAX_REPLY_LENGTH:
		_reply_status.text = TOO_LONG_TEXT % MAX_REPLY_LENGTH
		return
	if not Brain.report_letter_replied(file_name, text):
		_reply_status.text = OFFLINE_TEXT
		return
	# The brain answers with the whole mailbox, now with the reply: _show_letter hides the box.
	_send_button.disabled = true
	_reply_status.text = SENDING_TEXT


func _build() -> void:
	var shade: ColorRect = ColorRect.new()
	shade.color = SHADE_COLOR
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(shade)

	var paper: PanelContainer = PanelContainer.new()
	paper.anchor_left = SCREEN_MARGIN
	paper.anchor_top = SCREEN_MARGIN
	paper.anchor_right = 1.0 - SCREEN_MARGIN
	paper.anchor_bottom = 1.0 - SCREEN_MARGIN
	paper.add_theme_stylebox_override("panel", _paper_style(PAPER_COLOR, 3, 18))
	shade.add_child(paper)

	var column: VBoxContainer = VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	paper.add_child(column)
	column.add_child(_header())

	var split: HSplitContainer = HSplitContainer.new()
	split.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(split)
	_letter_list = _letter_list_control()
	split.add_child(_letter_list)
	var letter_column: VBoxContainer = VBoxContainer.new()
	letter_column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	letter_column.add_theme_constant_override("separation", 10)
	split.add_child(letter_column)
	_letter_text = _letter_text_control()
	letter_column.add_child(_letter_text)
	_reply_box = _reply_box_control()
	letter_column.add_child(_reply_box)


func _header() -> HBoxContainer:
	var header: HBoxContainer = HBoxContainer.new()
	var title: Label = Label.new()
	title.text = "Caixa de correio"
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_theme_font_size_override("font_size", TITLE_FONT_SIZE)
	title.add_theme_color_override("font_color", INK_COLOR)
	header.add_child(title)
	var close_button: Button = Button.new()
	close_button.text = " X "
	close_button.pressed.connect(close)
	header.add_child(close_button)
	return header


func _letter_list_control() -> ItemList:
	var letter_list: ItemList = ItemList.new()
	letter_list.custom_minimum_size.x = LIST_WIDTH
	letter_list.add_theme_stylebox_override("panel", _paper_style(LIST_COLOR, 1, 8))
	letter_list.add_theme_color_override("font_color", INK_COLOR)
	letter_list.add_theme_color_override("font_selected_color", INK_COLOR)
	letter_list.add_theme_color_override("font_hovered_color", INK_COLOR)
	letter_list.add_theme_font_size_override("font_size", TEXT_FONT_SIZE)
	letter_list.item_selected.connect(_open_letter)
	return letter_list


func _letter_text_control() -> RichTextLabel:
	var letter_text: RichTextLabel = RichTextLabel.new()
	letter_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	letter_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	letter_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	letter_text.selection_enabled = true
	letter_text.add_theme_color_override("default_color", INK_COLOR)
	letter_text.add_theme_font_size_override("normal_font_size", TEXT_FONT_SIZE)
	return letter_text


func _reply_box_control() -> VBoxContainer:
	var reply_box: VBoxContainer = VBoxContainer.new()
	_reply_input = TextEdit.new()
	_reply_input.custom_minimum_size.y = REPLY_BOX_HEIGHT
	_reply_input.placeholder_text = REPLY_PLACEHOLDER
	_reply_input.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	_reply_input.add_theme_stylebox_override("normal", _paper_style(LIST_COLOR, 1, 8))
	_reply_input.add_theme_stylebox_override("focus", _paper_style(LIST_COLOR, 2, 8))
	_reply_input.add_theme_color_override("font_color", INK_COLOR)
	_reply_input.add_theme_font_size_override("font_size", TEXT_FONT_SIZE)
	reply_box.add_child(_reply_input)

	var footer: HBoxContainer = HBoxContainer.new()
	_reply_status = Label.new()
	_reply_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_reply_status.add_theme_color_override("font_color", BORDER_COLOR)
	footer.add_child(_reply_status)
	_send_button = Button.new()
	_send_button.text = " Enviar resposta "
	_send_button.pressed.connect(_send_reply)
	footer.add_child(_send_button)
	reply_box.add_child(footer)
	reply_box.hide()
	return reply_box


func _paper_style(color: Color, border_width: int, margin: float) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = BORDER_COLOR
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(margin)
	return style
