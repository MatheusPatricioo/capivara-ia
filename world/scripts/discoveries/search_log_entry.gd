class_name SearchLogEntry
extends RefCounted

## One web search the capybara did, as written by the brain in history/searches.jsonl.


## A site that came back in the search results.
class FoundPage:
	var title: String
	var url: String

	func _init(page_title: String, page_url: String) -> void:
		title = page_title
		url = page_url


## ISO 8601 date and time, like 2026-11-23T10:15:02-03:00.
var searched_at: String
var query: String
var pages: Array[FoundPage] = []


func _init(search_time: String, search_query: String) -> void:
	searched_at = search_time
	query = search_query


## Turns 2026-11-23T10:15:02-03:00 into 23/11/2026 10:15. Unknown formats are shown as they are.
func display_date() -> String:
	var date_and_time: PackedStringArray = searched_at.split("T")
	var date_parts: PackedStringArray = date_and_time[0].split("-")
	if date_and_time.size() != 2 or date_parts.size() != 3:
		return searched_at
	return "%s/%s/%s %s" % [date_parts[2], date_parts[1], date_parts[0], date_and_time[1].left(5)]
