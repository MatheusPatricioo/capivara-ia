class_name WritingDeskViewer
extends CanvasLayer

## Her writing desk, drawn over the 3D world like a sheet of paper, with two tabs: the
## letters she wrote to Matheus (he can answer them here) and her personal diary.
## The game keeps running while it is open, so the brain connection never stops.
## [X] or Esc closes it.

const LAYER: int = 10
const TITLE: String = "Cantinho de escrita"
const LETTERS_TAB_TITLE: String = "Cartas"
const DIARY_TAB_TITLE: String = "Diário"
const SHADE_COLOR: Color = Color(0.0, 0.0, 0.0, 0.45)
## Share of the screen left empty around the paper on each side.
const SCREEN_MARGIN: float = 0.12

var _tabs: TabContainer
var _letters_tab: LettersTab
var _diary_tab: DiaryTab


func _ready() -> void:
	layer = LAYER
	_build()
	hide()


## Opens on the tab used last, with the latest letters and pages.
func open() -> void:
	_letters_tab.refresh()
	_diary_tab.refresh()
	show()


func close() -> void:
	hide()


## _input runs before the GUI, so Esc closes the desk even when a list has the focus.
func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()


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
	paper.add_theme_stylebox_override("panel", PaperStyle.panel(PaperStyle.PAPER_COLOR, 3, 18))
	shade.add_child(paper)

	var column: VBoxContainer = VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	paper.add_child(column)
	column.add_child(_header())

	_tabs = TabContainer.new()
	_tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_tabs.add_theme_stylebox_override("panel", StyleBoxEmpty.new())
	column.add_child(_tabs)
	_letters_tab = LettersTab.new()
	_letters_tab.name = LETTERS_TAB_TITLE
	_tabs.add_child(_letters_tab)
	_diary_tab = DiaryTab.new()
	_diary_tab.name = DIARY_TAB_TITLE
	_tabs.add_child(_diary_tab)


func _header() -> HBoxContainer:
	var header: HBoxContainer = HBoxContainer.new()
	var title: Label = Label.new()
	title.text = TITLE
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_theme_font_size_override("font_size", PaperStyle.TITLE_FONT_SIZE)
	title.add_theme_color_override("font_color", PaperStyle.INK_COLOR)
	header.add_child(title)
	var close_button: Button = Button.new()
	close_button.text = " X "
	close_button.pressed.connect(close)
	header.add_child(close_button)
	return header
