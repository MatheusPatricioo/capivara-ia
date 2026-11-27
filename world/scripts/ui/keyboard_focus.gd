class_name KeyboardFocus
extends RefCounted

## Keyboard shortcuts must never fire while her creator is typing (talking with her or
## answering a letter). Every shortcut asks this first.


static func is_typing(viewport: Viewport) -> bool:
	var focused: Control = viewport.gui_get_focus_owner()
	return focused is LineEdit or focused is TextEdit
