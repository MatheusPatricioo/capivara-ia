class_name NoteFolderTab
extends MarginContainer

## A tab that reads the Markdown notes of one folder: the notes on the left, newest first,
## and the text of the selected note on the right, shown as titles, bold text and bullets.
## The newest note opens by itself, and every web address in the text (like the sources)
## opens in the default browser when clicked.
##
## Used by the Discoveries tab (the root of the discoveries folder) and the Suggestions tab
## (its "sugestoes" subfolder). Its nodes are found by path, not by unique name, because a
## scene can only have one node with each unique name and there are two of these tabs.

const UNREADABLE_TEXT: String = "> não consegui ler este arquivo."

## Shown when the folder has no notes yet.
@export var empty_text: String = "> nada por aqui ainda."

@onready var _note_list: ItemList = $Split/NoteList
@onready var _note_text: RichTextLabel = $Split/NoteText

var _folder_path: String = ""


func _ready() -> void:
	_note_list.item_selected.connect(_show_note)
	_note_text.meta_clicked.connect(_open_link)


## Lists the notes again. Called every time the computer screen opens.
func show_folder(folder_path: String) -> void:
	_folder_path = folder_path
	_note_list.clear()
	for file_name: String in DiscoveryFiles.list_newest_first(folder_path, DiscoveryFiles.NOTE_EXTENSION):
		var item_index: int = _note_list.add_item(_list_title(file_name))
		_note_list.set_item_metadata(item_index, file_name)
		_note_list.set_item_tooltip(item_index, file_name)
	if _note_list.item_count == 0:
		_note_text.text = empty_text
		return
	_note_list.select(0)
	_show_note(0)


## The note's own "# " title keeps accents and hyphens ("Vaga-lumes no jardim à noite"),
## which the file name lost. A note without one falls back to its file name.
func _list_title(file_name: String) -> String:
	for line: String in DiscoveryFiles.read_text(_folder_path, file_name).split("\n"):
		if line.begins_with(MarkdownText.TITLE_PREFIX):
			return line.trim_prefix(MarkdownText.TITLE_PREFIX).strip_edges()
	return DiscoveryFiles.title_from_file_name(file_name)


func _show_note(item_index: int) -> void:
	var file_name: String = _note_list.get_item_metadata(item_index)
	var note_text: String = DiscoveryFiles.read_text(_folder_path, file_name)
	_note_text.text = MarkdownText.to_bbcode(note_text) if not note_text.is_empty() else UNREADABLE_TEXT
	_note_text.scroll_to_line(0)


## meta_clicked sends the value of the [url=...] tag that was clicked.
func _open_link(link: Variant) -> void:
	WebLinks.open(str(link))
