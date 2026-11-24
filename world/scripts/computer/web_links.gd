class_name WebLinks
extends RefCounted

## Opens links from the capybara's files in the default browser. Those links come from the
## internet, so only web addresses are opened: a file:// or any other scheme must never
## reach the operating system (web content is data, never instructions).

const ALLOWED_URL_PREFIXES: PackedStringArray = ["http://", "https://"]
## A web address inside plain text. It stops at spaces and at characters that usually
## close it in Markdown, like ")" or ">".
const URL_PATTERN: String = "https?://[^\\s<>()\\[\\]\"']+"
## Punctuation that ends a sentence, not the address: "veja https://site.com." keeps the dot out.
const TRAILING_PUNCTUATION: String = ".,;:!?"
## Light blue, so links stand out from the green terminal text.
const LINK_COLOR: String = "#8cd9ff"


static func is_web_url(url: String) -> bool:
	for allowed_prefix: String in ALLOWED_URL_PREFIXES:
		if url.to_lower().begins_with(allowed_prefix):
			return true
	return false


static func open(url: String) -> void:
	if not is_web_url(url):
		push_warning("Refusing to open a non-web link: %s" % url)
		return
	OS.shell_open(url)


## Turns plain text into BBCode for a RichTextLabel: every web address becomes a clickable
## [url] tag, and any "[" in the text is escaped so it is shown instead of read as a tag.
static func to_bbcode_with_links(text: String) -> String:
	var url_regex: RegEx = RegEx.create_from_string(URL_PATTERN)
	var bbcode: String = ""
	var copied_until: int = 0
	for url_match: RegExMatch in url_regex.search_all(text):
		var url: String = url_match.get_string().rstrip(TRAILING_PUNCTUATION)
		bbcode += _escape(text.substr(copied_until, url_match.get_start() - copied_until))
		bbcode += "[color=%s][url=%s]%s[/url][/color]" % [LINK_COLOR, url, _escape(url)]
		copied_until = url_match.get_start() + url.length()
	return bbcode + _escape(text.substr(copied_until))


static func _escape(plain_text: String) -> String:
	return plain_text.replace("[", "[lb]")
