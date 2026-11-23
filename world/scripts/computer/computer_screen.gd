class_name ComputerScreen
extends CanvasLayer

## The capybara's retro computer, drawn over the 3D world. It only shows files from the
## discoveries folder: no AI logic lives here. The [X] button or the Esc key closes it.
## The game keeps running while it is open, so the brain connection never stops.

const TAB_TITLES: PackedStringArray = ["Histórico", "Descobertas", "Desenhos"]

@onready var _tabs: TabContainer = %Tabs
@onready var _close_button: Button = %CloseButton
@onready var _folder_label: Label = %FolderLabel
@onready var _history_tab: HistoryTab = %HistoryTab
@onready var _discoveries_tab: DiscoveriesTab = %DiscoveriesTab
@onready var _drawings_tab: DrawingsTab = %DrawingsTab


func _ready() -> void:
	hide()
	for tab_index: int in TAB_TITLES.size():
		_tabs.set_tab_title(tab_index, TAB_TITLES[tab_index])
	_close_button.pressed.connect(close)


## Reads the folder again on every open, so the tabs always show the latest files.
func open() -> void:
	var discoveries_path: String = DiscoveriesFolder.path()
	_folder_label.text = "Pasta: %s" % discoveries_path
	_history_tab.show_history(discoveries_path)
	_discoveries_tab.show_discoveries(discoveries_path)
	_drawings_tab.show_drawings(discoveries_path)
	show()


func close() -> void:
	hide()


## _input runs before the GUI, so Esc closes the screen even when a tab has the focus.
func _input(event: InputEvent) -> void:
	if visible and event.is_action_pressed("ui_cancel"):
		close()
		get_viewport().set_input_as_handled()
