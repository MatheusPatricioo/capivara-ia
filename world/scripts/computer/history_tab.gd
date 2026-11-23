class_name HistoryTab
extends MarginContainer

## The History tab: every web search with its date, query and sites, newest first.
## Clicking a site opens it in the default browser.

const EMPTY_HISTORY_TEXT: String = "> nenhuma pesquisa ainda."
const NO_RESULTS_TEXT: String = "    (nenhum site encontrado)"
const SITE_INDENT: int = 24
## LinkButton never wraps, so long titles are cut to keep them inside the screen.
const MAX_TITLE_LENGTH: int = 90

@onready var _entry_list: VBoxContainer = %EntryList


## Rebuilds the list from the search log. Called every time the computer screen opens.
func show_history(discoveries_path: String) -> void:
	_clear_entries()
	var entries: Array[SearchLogEntry] = SearchLogReader.read_newest_first(discoveries_path)
	if entries.is_empty():
		_entry_list.add_child(_create_label(EMPTY_HISTORY_TEXT))
		return
	for entry: SearchLogEntry in entries:
		_entry_list.add_child(_create_entry(entry))


func _clear_entries() -> void:
	for child: Node in _entry_list.get_children():
		child.queue_free()


func _create_entry(entry: SearchLogEntry) -> VBoxContainer:
	var entry_box: VBoxContainer = VBoxContainer.new()
	entry_box.add_child(_create_label("[%s] %s" % [entry.display_date(), entry.query]))
	if entry.pages.is_empty():
		entry_box.add_child(_create_label(NO_RESULTS_TEXT))
	for page: SearchLogEntry.FoundPage in entry.pages:
		entry_box.add_child(_create_site_link(page))
	return entry_box


func _create_label(text: String) -> Label:
	var label: Label = Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return label


func _create_site_link(page: SearchLogEntry.FoundPage) -> MarginContainer:
	var link: LinkButton = LinkButton.new()
	link.text = _shorten(page.title if not page.title.is_empty() else page.url)
	link.tooltip_text = page.url
	link.pressed.connect(WebLinks.open.bind(page.url))
	var indented_link: MarginContainer = MarginContainer.new()
	indented_link.add_theme_constant_override("margin_left", SITE_INDENT)
	indented_link.add_child(link)
	return indented_link


func _shorten(text: String) -> String:
	if text.length() <= MAX_TITLE_LENGTH:
		return text
	return text.left(MAX_TITLE_LENGTH - 1) + "…"

