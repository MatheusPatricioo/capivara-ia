class_name DiscoveriesTab
extends MarginContainer

## The Discoveries tab: the capybara's notes on the left, newest first, and the text of
## the selected note on the right. The newest note opens by itself, and every web address
## in the text (like the sources) opens in the default browser when clicked.

const EMPTY_TEXT: String = "> nenhuma descoberta ainda."
const UNREADABLE_TEXT: String = "> não consegui ler este arquivo."

@onready var _note_list: ItemList = %NoteList
@onready var _note_text: RichTextLabel = %NoteText

var _discoveries_path: String = ""


func _ready() -> void:
	_note_list.item_selected.connect(_show_note)
	_note_text.meta_clicked.connect(_open_link)


## Lists the notes again. Called every time the computer screen opens.
func show_discoveries(discoveries_path: String) -> void:
	_discoveries_path = discoveries_path
	_note_list.clear()
	for file_name: String in DiscoveryFiles.list_newest_first(discoveries_path, DiscoveryFiles.NOTE_EXTENSION):
		_note_list.add_item(file_name.get_basename())
		_note_list.set_item_metadata(_note_list.item_count - 1, file_name)
	if _note_list.item_count == 0:
		_note_text.text = EMPTY_TEXT
		return
	_note_list.select(0)
	_show_note(0)


func _show_note(item_index: int) -> void:
	var file_name: String = _note_list.get_item_metadata(item_index)
	var note_text: String = DiscoveryFiles.read_text(_discoveries_path, file_name)
	_note_text.text = WebLinks.to_bbcode_with_links(note_text) if not note_text.is_empty() else UNREADABLE_TEXT
	_note_text.scroll_to_line(0)


## meta_clicked sends the value of the [url=...] tag that was clicked.
func _open_link(link: Variant) -> void:
	WebLinks.open(str(link))
