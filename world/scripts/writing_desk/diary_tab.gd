class_name DiaryTab
extends HSplitContainer

## Her personal diary: the days on the left (newest first, with how the day went) and the
## page of the chosen day on the right, each thought under the time she wrote it and how
## she felt (the mood meter, in words). Only for reading: the diary is hers.
## The pages come from the brain (Brain.diary_changed); this only shows them.

const EMPTY_TEXT: String = "O diário ainda está em branco. Depois de cada tempinho livre, ela escreve aqui o que pensou."
const PAGE_TITLE_FORMAT: String = "[b]%s[/b]%s\n\n"
const ENTRY_FORMAT: String = "[b]%s[/b]%s\n%s"
const MOOD_FORMAT: String = "  ·  [i]%s[/i]"
const ENTRY_SEPARATOR: String = "\n\n"
const DAY_MOOD_FORMAT: String = "  ·  %s"
## Wider than the letters list, so "25/11  ·  um dia muito difícil" fits on one line.
const DAY_LIST_WIDTH: float = 330.0

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


## "25/11  ·  um dia bom", or only "25/11" when no entry of the day has a mood.
func _list_title(diary_day: Dictionary) -> String:
	var day_and_month: String = ReadableDates.day_and_month(str(diary_day.get("day", "")))
	return day_and_month + _mood_suffix(diary_day.get("mood"), DAY_MOOD_FORMAT)


## The full date and how the day went on top, then every entry of the day.
func _open_day(day_index: int) -> void:
	_day_list.select(day_index)
	var diary_day: Dictionary = _days[day_index]
	var full_day: String = ReadableDates.full_day(str(diary_day.get("day", "")))
	var page_title: String = PAGE_TITLE_FORMAT % [full_day, _mood_suffix(diary_day.get("mood"), MOOD_FORMAT)]
	var entry_texts: PackedStringArray = []
	for entry: Variant in _entries_of(diary_day):
		if entry is Dictionary:
			entry_texts.append(_entry_text(entry))
	_page_text.text = page_title + ENTRY_SEPARATOR.join(entry_texts)
	_page_text.scroll_to_line(0)


## The time in bold and how she felt in italics, then what she wrote. Brackets are
## escaped, so her text never turns into formatting by accident.
func _entry_text(entry: Dictionary) -> String:
	var written_time: String = ReadableDates.time_only(str(entry.get("written_at", "")))
	var text: String = str(entry.get("text", "")).replace("[", "[lb]")
	return ENTRY_FORMAT % [written_time, _mood_suffix(entry.get("mood"), MOOD_FORMAT), text]


## The mood in the given format, or nothing for days and entries without a mood.
func _mood_suffix(mood: Variant, mood_format: String) -> String:
	return mood_format % mood if mood is String else ""


func _entries_of(diary_day: Dictionary) -> Array:
	var entries: Variant = diary_day.get("entries", [])
	return entries if entries is Array else []


func _build() -> void:
	_day_list = PaperStyle.side_list()
	_day_list.custom_minimum_size.x = DAY_LIST_WIDTH
	_day_list.item_selected.connect(_open_day)
	add_child(_day_list)
	_page_text = PaperStyle.page_text()
	_page_text.bbcode_enabled = true
	add_child(_page_text)
