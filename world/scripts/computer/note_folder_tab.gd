class_name NoteFolderTab
extends MarginContainer

## A tab that shows the Markdown notes of one folder, asked to the brain: the notes on the
## left, newest first, and the text of the selected note on the right, shown as titles, bold
## text and bullets. The newest note opens by itself, and every web address in the text
## (like the sources) opens in the default browser when clicked.
##
## Used by the Discoveries tab and the Suggestions tab. Titles and the "done" mark come ready
## from the brain: this tab never reads files. Its nodes are found by path, not by unique
## name, because a scene can only have one node with each unique name and there are two of
## these tabs.

## Tells where the brain keeps the notes of this tab, only to show it.
signal folder_path_received(folder_path: String)

const UNREADABLE_TEXT: String = "> não consegui ler este arquivo."
const UNAVAILABLE_TEXT: String = "> não consegui falar com o cérebro."
const DONE_MARK: String = "✔ "

## Which notes the brain sends: "discoveries" or "suggestions".
@export_enum("discoveries", "suggestions") var folder: String = "discoveries"
## Shown when the folder has no notes yet.
@export var empty_text: String = "> nada por aqui ainda."

@onready var _note_list: ItemList = $Split/NoteList
@onready var _note_text: RichTextLabel = $Split/NoteText

## Grows on every list or note asked, so an answer to an older question is ignored.
var _question_count: int = 0


func _ready() -> void:
	_note_list.item_selected.connect(_show_note)
	_note_text.meta_clicked.connect(_open_link)


## Asks the brain for the notes again. Called every time the computer screen opens.
func show_notes() -> void:
	var this_question: int = _next_question()
	_note_list.clear()
	_note_text.text = ""
	var reply: Dictionary = await BrainQuestion.ask({"type": "list_discoveries", "folder": folder})
	if this_question != _question_count:
		return
	if reply.get("type") != "discovery_list":
		_note_text.text = UNAVAILABLE_TEXT
		return
	folder_path_received.emit(str(reply.get("folder_path", "")))
	_fill_list(reply.get("discoveries", []))
	if _note_list.item_count == 0:
		_note_text.text = empty_text
		return
	_note_list.select(0)
	_show_note(0)


## Each item shows the ready title and keeps the note's id to ask for its text later.
func _fill_list(notes: Variant) -> void:
	if not notes is Array:
		return
	for note: Variant in notes:
		if not note is Dictionary or not note.get("id") is String:
			continue
		var mark: String = DONE_MARK if note.get("done", false) == true else ""
		var item_index: int = _note_list.add_item(mark + str(note.get("title", "")))
		_note_list.set_item_metadata(item_index, note["id"])


func _show_note(item_index: int) -> void:
	var this_question: int = _next_question()
	var note_id: String = _note_list.get_item_metadata(item_index)
	var reply: Dictionary = await BrainQuestion.ask(
		{"type": "get_discovery", "folder": folder, "id": note_id}
	)
	if this_question != _question_count:
		return
	var markdown: String = str(reply.get("markdown", ""))
	if reply.get("type") != "discovery" or markdown.is_empty():
		_note_text.text = UNREADABLE_TEXT
		return
	_note_text.text = MarkdownText.to_bbcode(markdown)
	_note_text.scroll_to_line(0)


func _next_question() -> int:
	_question_count += 1
	return _question_count


## meta_clicked sends the value of the [url=...] tag that was clicked.
func _open_link(link: Variant) -> void:
	WebLinks.open(str(link))
