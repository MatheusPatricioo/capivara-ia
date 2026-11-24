class_name MarkdownText
extends RefCounted

## Turns the capybara's Markdown notes into BBCode for a RichTextLabel, so the screen shows
## titles, bold text and bullets instead of raw "#", "**" and "-". Only the few pieces of
## Markdown her notes use are handled; anything else is shown as plain text.

const TITLE_PREFIX: String = "# "
const SECTION_PREFIX: String = "## "
const BULLET_PREFIX: String = "- "
const TITLE_FONT_SIZE: int = 24
const SECTION_COLOR: String = "#9dffa8"
const BULLET: String = "  • "
const BOLD_PATTERN: String = "\\*\\*(.+?)\\*\\*"


static func to_bbcode(markdown: String) -> String:
	var bold_regex: RegEx = RegEx.create_from_string(BOLD_PATTERN)
	var bbcode_lines: PackedStringArray = PackedStringArray()
	# Notes saved on Windows end their lines with "\r\n": a leftover "\r" shows as an extra blank line.
	for line: String in markdown.split("\n"):
		bbcode_lines.append(_line_to_bbcode(line.trim_suffix("\r"), bold_regex))
	return "\n".join(bbcode_lines)


## WebLinks escapes the text first, so a "[" from the file never becomes a tag.
static func _line_to_bbcode(line: String, bold_regex: RegEx) -> String:
	if line.begins_with(TITLE_PREFIX):
		return "[font_size=%d][b]%s[/b][/font_size]" % [TITLE_FONT_SIZE, _inline(line.trim_prefix(TITLE_PREFIX), bold_regex)]
	if line.begins_with(SECTION_PREFIX):
		return "[b][color=%s]%s[/color][/b]" % [SECTION_COLOR, _inline(line.trim_prefix(SECTION_PREFIX), bold_regex)]
	if line.begins_with(BULLET_PREFIX):
		return BULLET + _inline(line.trim_prefix(BULLET_PREFIX), bold_regex)
	return _inline(line, bold_regex)


static func _inline(text: String, bold_regex: RegEx) -> String:
	return bold_regex.sub(WebLinks.to_bbcode_with_links(text), "[b]$1[/b]", true)
