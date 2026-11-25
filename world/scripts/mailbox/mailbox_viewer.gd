class_name MailboxViewer
extends CanvasLayer

## The inside of the mailbox, drawn over the 3D world like a sheet of letter paper: the
## letters on the left (newest first, a dot on the unread ones) and the chosen letter on
## the right. Opening a letter tells the brain, which marks it as read. The letters come
## from the brain (Brain.mailbox_changed); this only shows them. [X] or Esc closes it.

const LAYER: int = 10
const UNREAD_MARK: String = "● "
const READ_MARK: String = "    "
const EMPTY_TEXT: String = "A caixa está vazia. Quando ela sentir saudade, uma cartinha aparece aqui."
const CHOOSE_TEXT: String = "Escolha uma carta na lista."
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
	if _letters.is_empty():
		_letter_text.text = EMPTY_TEXT
	elif chosen_file_name.is_empty():
		_letter_text.text = CHOOSE_TEXT


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
	_letter_text.text = str(letter.get("text", ""))
	if not bool(letter.get("unread", false)):
		return
	Brain.report_letter_opened(str(letter.get("file_name", "")))
	letter["unread"] = false
	_letter_list.set_item_text(letter_index, _list_title(letter))


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
	_letter_text = _letter_text_control()
	split.add_child(_letter_text)


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


func _paper_style(color: Color, border_width: int, margin: float) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = BORDER_COLOR
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(margin)
	return style
