class_name ComputerScreen
extends CanvasLayer

## The capybara's retro computer, drawn over the 3D world. It only shows what the brain
## sends about her saved things, and never reads the disk: no AI logic lives here.
## The [X] button or the Esc key closes it.
## The game keeps running while it is open, so the brain connection never stops.

const TAB_TITLES: PackedStringArray = ["Histórico", "Descobertas", "Desenhos", "Sugestões"]
## Shown until the brain tells where the discoveries folder is.
const UNKNOWN_FOLDER_TEXT: String = "Pasta: (esperando o cérebro)"

@onready var _tabs: TabContainer = %Tabs
@onready var _close_button: Button = %CloseButton
@onready var _folder_label: Label = %FolderLabel
@onready var _history_tab: HistoryTab = %HistoryTab
@onready var _discoveries_tab: NoteFolderTab = %DiscoveriesTab
@onready var _drawings_tab: DrawingsTab = %DrawingsTab
@onready var _suggestions_tab: NoteFolderTab = %SuggestionsTab


func _ready() -> void:
	hide()
	for tab_index: int in TAB_TITLES.size():
		_tabs.set_tab_title(tab_index, TAB_TITLES[tab_index])
	_close_button.pressed.connect(close)
	_discoveries_tab.folder_path_received.connect(_show_folder_path)


## Asks the brain again on every open, so the tabs always show the latest things.
## The tabs fill in as the answers arrive; the screen opens right away.
func open() -> void:
	_folder_label.text = UNKNOWN_FOLDER_TEXT
	_history_tab.show_history()
	_discoveries_tab.show_notes()
	_drawings_tab.show_drawings()
	_suggestions_tab.show_notes()
	show()


func _show_folder_path(folder_path: String) -> void:
	_folder_label.text = "Pasta: %s" % folder_path


func close() -> void:
	hide()


## _input runs before the GUI, so Esc closes the screen even when a tab has the focus.
func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()
