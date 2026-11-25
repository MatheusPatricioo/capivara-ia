class_name PaperStyle
extends RefCounted

## The look of her writing paper, shared by every tab of the writing desk, so letters and
## diary pages feel like the same notebook.

const PAPER_COLOR: Color = Color(0.98, 0.95, 0.86)
const LIST_COLOR: Color = Color(0.93, 0.88, 0.76)
const INK_COLOR: Color = Color(0.25, 0.17, 0.1)
const BORDER_COLOR: Color = Color(0.55, 0.38, 0.22)
const TITLE_FONT_SIZE: int = 26
const TEXT_FONT_SIZE: int = 19
const LIST_WIDTH: float = 230.0


static func panel(color: Color, border_width: int, margin: float) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = BORDER_COLOR
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(margin)
	return style


## A list on the left side of a tab (letters, diary days), written in ink.
static func side_list() -> ItemList:
	var side_list_control: ItemList = ItemList.new()
	side_list_control.custom_minimum_size.x = LIST_WIDTH
	side_list_control.add_theme_stylebox_override("panel", panel(LIST_COLOR, 1, 8))
	side_list_control.add_theme_color_override("font_color", INK_COLOR)
	side_list_control.add_theme_color_override("font_selected_color", INK_COLOR)
	side_list_control.add_theme_color_override("font_hovered_color", INK_COLOR)
	side_list_control.add_theme_font_size_override("font_size", TEXT_FONT_SIZE)
	return side_list_control


## The text of a letter or a diary page, filling the rest of the tab.
static func page_text() -> RichTextLabel:
	var page_text_control: RichTextLabel = RichTextLabel.new()
	page_text_control.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	page_text_control.size_flags_vertical = Control.SIZE_EXPAND_FILL
	page_text_control.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	page_text_control.selection_enabled = true
	page_text_control.add_theme_color_override("default_color", INK_COLOR)
	page_text_control.add_theme_font_size_override("normal_font_size", TEXT_FONT_SIZE)
	page_text_control.add_theme_font_size_override("bold_font_size", TEXT_FONT_SIZE)
	return page_text_control
