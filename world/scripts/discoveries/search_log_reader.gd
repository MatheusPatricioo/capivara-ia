class_name SearchLogReader
extends RefCounted

## Reads history/searches.jsonl, where the brain appends one JSON object per search:
## {"searched_at": "...", "query": "...", "results": [{"title": "...", "url": "..."}]}
## Broken or unexpected lines are skipped, so one bad line never hides the whole history.

const LOG_RELATIVE_PATH: String = "history/searches.jsonl"


## All valid searches, newest first. Returns an empty list when the file does not exist yet.
static func read_newest_first(discoveries_path: String) -> Array[SearchLogEntry]:
	var entries: Array[SearchLogEntry] = []
	var log_file: FileAccess = FileAccess.open(discoveries_path.path_join(LOG_RELATIVE_PATH), FileAccess.READ)
	if log_file == null:
		return entries
	while not log_file.eof_reached():
		var entry: SearchLogEntry = _parse_line(log_file.get_line())
		if entry != null:
			entries.append(entry)
	entries.reverse()
	return entries


## Returns null for empty lines, invalid JSON or objects without a text query.
static func _parse_line(line: String) -> SearchLogEntry:
	var parser: JSON = JSON.new()
	if line.strip_edges().is_empty() or parser.parse(line) != OK:
		return null
	var record: Variant = parser.data
	if not record is Dictionary or not record.get("query") is String:
		return null
	var entry: SearchLogEntry = SearchLogEntry.new(str(record.get("searched_at", "")), record["query"])
	var results: Variant = record.get("results", [])
	if results is Array:
		entry.pages = _parse_pages(results)
	return entry


static func _parse_pages(results: Array) -> Array[SearchLogEntry.FoundPage]:
	var pages: Array[SearchLogEntry.FoundPage] = []
	for result: Variant in results:
		if result is Dictionary and result.get("url") is String:
			pages.append(SearchLogEntry.FoundPage.new(str(result.get("title", "")), result["url"]))
	return pages
