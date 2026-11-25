class_name LettersTab
extends HSplitContainer

## The letters she wrote to her creator: the list on the left (newest first, a dot on the
## unread ones) and the chosen letter on the right. Opening a letter tells the brain, which
## marks it as read. Under a letter her creator can write one reply: it goes to the brain,
## which keeps it with the letter and sends the letters back with the reply in it.
## The letters come from the brain (Brain.mailbox_changed); this only shows them.

const UNREAD_MARK: String = "● "
const READ_MARK: String = "    "
const EMPTY_TEXT: String = "Nenhuma carta ainda. Quando ela sentir saudade, uma cartinha aparece aqui."
const CHOOSE_TEXT: String = "Escolha uma carta na lista."
const REPLY_HEADING: String = "\n\n— Sua resposta (%s):\n\n"
const REPLY_PLACEHOLDER: String = "Escreva sua resposta para ela..."
const SENDING_TEXT: String = "Enviando..."
const REFUSED_TEXT: String = "Não deu para guardar a resposta. Veja o log do cérebro."
const OFFLINE_TEXT: String = "O cérebro está desligado. Tente de novo quando ele voltar."
const TOO_LONG_TEXT: String = "Muito longa: no máximo %d caracteres."
## The same limit the brain puts on a letter and on a reply.
const MAX_REPLY_LENGTH: int = 1500
const REPLY_BOX_HEIGHT: float = 110.0

var _letters: Array = []
var _letter_list: ItemList
var _letter_text: RichTextLabel
var _reply_box: VBoxContainer
var _reply_input: TextEdit
var _send_button: Button
var _reply_status: Label


func _ready() -> void:
	_build()
	Brain.mailbox_changed.connect(_on_mailbox_changed)


## Lists the letters again, keeping the chosen one chosen (the brain resends every letter
## right after one is opened or answered).
func refresh() -> void:
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


func _on_mailbox_changed(letters: Array) -> void:
	_letters = letters
	if is_visible_in_tree():
		refresh()


func _chosen_file_name() -> String:
	var selected: PackedInt32Array = _letter_list.get_selected_items()
	if selected.is_empty() or selected[0] >= _letters.size():
		return ""
	var letter: Dictionary = _letters[selected[0]]
	return str(letter.get("file_name", ""))


func _list_title(letter: Dictionary) -> String:
	var mark: String = UNREAD_MARK if bool(letter.get("unread", false)) else READ_MARK
	return mark + ReadableDates.day_and_time(str(letter.get("written_at", "")))


func _open_letter(letter_index: int) -> void:
	var letter: Dictionary = _letters[letter_index]
	_reply_input.clear()
	_show_letter(letter)
	if not bool(letter.get("unread", false)):
		return
	Brain.report_letter_opened(str(letter.get("file_name", "")))
	letter["unread"] = false
	_letter_list.set_item_text(letter_index, _list_title(letter))


## The letter, with her creator's reply under it, or the box to write one when it has none.
func _show_letter(letter: Dictionary) -> void:
	var reply: Variant = letter.get("reply")
	var text: String = str(letter.get("text", ""))
	if reply is String:
		var replied_at: String = ReadableDates.day_and_time(str(letter.get("replied_at", "")))
		text += (REPLY_HEADING % replied_at) + str(reply)
	_letter_text.text = text
	_reply_box.visible = not reply is String
	# The letters came back still without the reply: the brain refused it.
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
	# The brain answers with every letter, now with the reply: _show_letter hides the box.
	_send_button.disabled = true
	_reply_status.text = SENDING_TEXT


func _build() -> void:
	_letter_list = PaperStyle.side_list()
	_letter_list.item_selected.connect(_open_letter)
	add_child(_letter_list)
	var letter_column: VBoxContainer = VBoxContainer.new()
	letter_column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	letter_column.add_theme_constant_override("separation", 10)
	add_child(letter_column)
	_letter_text = PaperStyle.page_text()
	letter_column.add_child(_letter_text)
	_reply_box = _reply_box_control()
	letter_column.add_child(_reply_box)


func _reply_box_control() -> VBoxContainer:
	var reply_box: VBoxContainer = VBoxContainer.new()
	_reply_input = TextEdit.new()
	_reply_input.custom_minimum_size.y = REPLY_BOX_HEIGHT
	_reply_input.placeholder_text = REPLY_PLACEHOLDER
	_reply_input.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	_reply_input.add_theme_stylebox_override("normal", PaperStyle.panel(PaperStyle.LIST_COLOR, 1, 8))
	_reply_input.add_theme_stylebox_override("focus", PaperStyle.panel(PaperStyle.LIST_COLOR, 2, 8))
	_reply_input.add_theme_color_override("font_color", PaperStyle.INK_COLOR)
	_reply_input.add_theme_font_size_override("font_size", PaperStyle.TEXT_FONT_SIZE)
	reply_box.add_child(_reply_input)

	var footer: HBoxContainer = HBoxContainer.new()
	_reply_status = Label.new()
	_reply_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_reply_status.add_theme_color_override("font_color", PaperStyle.BORDER_COLOR)
	footer.add_child(_reply_status)
	_send_button = Button.new()
	_send_button.text = " Enviar resposta "
	_send_button.pressed.connect(_send_reply)
	footer.add_child(_send_button)
	reply_box.add_child(footer)
	reply_box.hide()
	return reply_box
