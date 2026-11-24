class_name HistoryTab
extends MarginContainer

## The History tab: every web search with its date, query and sites, newest first.
## Clicking a site opens it in the default browser.
##
## Each search is one RichTextLabel that wraps long titles onto the next line. A LinkButton
## never wraps, so a long title used to widen the whole computer screen on this tab only.

const EMPTY_HISTORY_TEXT: String = "> nenhuma pesquisa ainda."
const NO_RESULTS_TEXT: String = "(nenhum site encontrado)"
const QUERY_COLOR: String = "#9dffa8"
const DATE_COLOR: String = "#5fae6c"
## Some search results glue several page titles into one: past this, the title is cut.
const MAX_TITLE_LENGTH: int = 110

@onready var _entry_list: VBoxContainer = %EntryList


## Rebuilds the list from the search log. Called every time the computer screen opens.
func show_history(discoveries_path: String) -> void:
	_clear_entries()
	var entries: Array[SearchLogEntry] = SearchLogReader.read_newest_first(discoveries_path)
	if entries.is_empty():
		_entry_list.add_child(_create_entry_text(EMPTY_HISTORY_TEXT))
		return
	for entry: SearchLogEntry in entries:
		_entry_list.add_child(_create_entry_text(_entry_to_bbcode(entry)))


func _clear_entries() -> void:
	for child: Node in _entry_list.get_children():
		child.queue_free()


## The query and date on the first line, then one indented line per site found.
func _entry_to_bbcode(entry: SearchLogEntry) -> String:
	var lines: PackedStringArray = [
		"[color=%s][lb]%s][/color] [b][color=%s]%s[/color][/b]"
		% [DATE_COLOR, entry.display_date(), QUERY_COLOR, _escape(entry.query)]
	]
	if entry.pages.is_empty():
		lines.append("[indent]%s[/indent]" % NO_RESULTS_TEXT)
	for page: SearchLogEntry.FoundPage in entry.pages:
		lines.append("[indent]%s[/indent]" % _site_link(page))
	return "\n".join(lines)


## Only web addresses become links (WebLinks.open checks again on click). A "]" would
## close the [url] tag early, so such an address is shown as plain text.
func _site_link(page: SearchLogEntry.FoundPage) -> String:
	var title: String = _shorten(page.title if not page.title.is_empty() else page.url)
	if not WebLinks.is_web_url(page.url) or page.url.contains("]"):
		return _escape(title)
	return "[color=%s][url=%s]%s[/url][/color]" % [WebLinks.LINK_COLOR, page.url, _escape(title)]


func _create_entry_text(bbcode: String) -> RichTextLabel:
	var entry_text: RichTextLabel = RichTextLabel.new()
	entry_text.bbcode_enabled = true
	entry_text.fit_content = true
	entry_text.scroll_active = false
	entry_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	entry_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	entry_text.text = bbcode
	entry_text.meta_clicked.connect(_open_link)
	return entry_text


## meta_clicked sends the value of the [url=...] tag that was clicked.
func _open_link(link: Variant) -> void:
	WebLinks.open(str(link))


func _shorten(text: String) -> String:
	if text.length() <= MAX_TITLE_LENGTH:
		return text
	return text.left(MAX_TITLE_LENGTH - 1) + "…"


## A "[" in a title from the web is shown, never read as a tag.
func _escape(plain_text: String) -> String:
	return plain_text.replace("[", "[lb]")
