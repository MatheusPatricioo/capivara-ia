class_name DiaryTab
extends HSplitContainer

## Her personal diary: the days on the left (newest first) and the page of the chosen day
## on the right, each thought under the time she wrote it. Only for reading: the diary is
## hers. The pages come from the brain (Brain.diary_changed); this only shows them.

const EMPTY_TEXT: String = "O diário ainda está em branco. Depois de cada tempinho livre, ela escreve aqui o que pensou."
const ENTRY_FORMAT: String = "[b]%s[/b]\n%s"
const ENTRY_SEPARATOR: String = "\n\n"
const ENTRY_COUNT_FORMAT: String = "%s  (%d)"

var _days: Array = []
var _day_list: ItemList
var _page_text: RichTextLabel


func _ready() -> void:
	_build()
	Brain.diary_changed.connect(_on_diary_changed)


## Lists the days again, keeping the chosen day chosen, or opening the newest one.
func refresh() -> void:
	var chosen_day: String = _chosen_day()
	_day_list.clear()
	for day_index: int in _days.size():
		_day_list.add_item(_list_title(_days[day_index]))
	if _days.is_empty():
		_page_text.text = EMPTY_TEXT
		return
	_open_day(maxi(_index_of_day(chosen_day), 0))


func _on_diary_changed(days: Array) -> void:
	_days = days
	if is_visible_in_tree():
		refresh()


func _chosen_day() -> String:
	var selected: PackedInt32Array = _day_list.get_selected_items()
	if selected.is_empty() or selected[0] >= _days.size():
		return ""
	var diary_day: Dictionary = _days[selected[0]]
	return str(diary_day.get("day", ""))


func _index_of_day(day: String) -> int:
	for day_index: int in _days.size():
		var diary_day: Dictionary = _days[day_index]
		if str(diary_day.get("day", "")) == day:
			return day_index
	return -1


func _list_title(diary_day: Dictionary) -> String:
	var entries: Array = _entries_of(diary_day)
	return ENTRY_COUNT_FORMAT % [ReadableDates.full_day(str(diary_day.get("day", ""))), entries.size()]


func _open_day(day_index: int) -> void:
	_day_list.select(day_index)
	var page_parts: PackedStringArray = []
	for entry: Variant in _entries_of(_days[day_index]):
		if entry is Dictionary:
			page_parts.append(_entry_text(entry))
	_page_text.text = ENTRY_SEPARATOR.join(page_parts)
	_page_text.scroll_to_line(0)


## The time in bold, then what she wrote. Brackets are escaped, so her text never turns
## into formatting by accident.
func _entry_text(entry: Dictionary) -> String:
	var written_time: String = ReadableDates.time_only(str(entry.get("written_at", "")))
	var text: String = str(entry.get("text", "")).replace("[", "[lb]")
	return ENTRY_FORMAT % [written_time, text]


func _entries_of(diary_day: Dictionary) -> Array:
	var entries: Variant = diary_day.get("entries", [])
	return entries if entries is Array else []


func _build() -> void:
	_day_list = PaperStyle.side_list()
	_day_list.item_selected.connect(_open_day)
	add_child(_day_list)
	_page_text = PaperStyle.page_text()
	_page_text.bbcode_enabled = true
	add_child(_page_text)
