class_name ReelsMode
extends CanvasLayer

## Reels mode, in the live game: a preview of how a clip of this very moment looks. The
## "Reels" button at the top right, or the R key, turns it on and off. On, the vertical
## stage covers the screen and the clip director films her up close with its automatic
## cuts; her speech balloon moves into the vertical picture. Off, everything is as before.
## The chat stays on top, so her creator can keep talking with her.
##
## It is a thing of the world, like the camera: the brain knows nothing about it. It does
## not exist in the Movie Maker clips, which already film with the clip camera.

## Below the chat (5), so the bar stays usable over the vertical picture.
const LAYER: int = 3
const TOGGLE_ACTION: StringName = &"toggle_reels_mode"
const BUTTON_MARGIN: float = 16.0
const FONT_SIZE: int = 15
const OFF_TEXT: String = "Reels  (R)"
const ON_TEXT: String = "Sair do Reels  (R)"
const BUTTON_COLOR: Color = Color(0.12, 0.09, 0.07, 0.82)
const BUTTON_HOVER_COLOR: Color = Color(0.2, 0.15, 0.11, 0.9)
const TEXT_COLOR: Color = Color(0.98, 0.95, 0.88)

@export var clip_director: ClipDirector
@export var clip_camera: ClipCamera
@export var speech_balloon: CapybaraSpeechBalloon

var _is_on: bool = false
var _stage: ReelsStage
var _button: Button


func _ready() -> void:
	layer = LAYER
	if ClipMode.is_on():
		set_process_unhandled_input(false)
		return
	_build()


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed(TOGGLE_ACTION) or KeyboardFocus.is_typing(get_viewport()):
		return
	toggle()
	get_viewport().set_input_as_handled()


func toggle() -> void:
	if _is_on:
		_turn_off()
	else:
		_turn_on()


func _turn_on() -> void:
	_is_on = true
	_stage.turn_on(clip_camera)
	clip_director.start_live()
	speech_balloon.draw_in(_stage.viewport())
	# The main window's 3D is hidden behind the stage: not drawing it spares the video card.
	get_viewport().disable_3d = true
	_button.text = ON_TEXT


func _turn_off() -> void:
	_is_on = false
	clip_director.stop()
	_stage.turn_off()
	speech_balloon.draw_on_screen()
	get_viewport().disable_3d = false
	_button.text = OFF_TEXT


func _build() -> void:
	_stage = ReelsStage.new()
	add_child(_stage)

	_button = Button.new()
	_button.text = OFF_TEXT
	# A click must not leave the focus on it: Enter would press it again instead of
	# opening the chat.
	_button.focus_mode = Control.FOCUS_NONE
	_button.add_theme_font_size_override("font_size", FONT_SIZE)
	for state: String in ["font_color", "font_hover_color", "font_pressed_color"]:
		_button.add_theme_color_override(state, TEXT_COLOR)
	_button.add_theme_stylebox_override("normal", _button_style(BUTTON_COLOR))
	_button.add_theme_stylebox_override("hover", _button_style(BUTTON_HOVER_COLOR))
	_button.add_theme_stylebox_override("pressed", _button_style(BUTTON_HOVER_COLOR))
	_button.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT, Control.PRESET_MODE_MINSIZE, int(BUTTON_MARGIN))
	_button.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_button.pressed.connect(toggle)
	add_child(_button)


static func _button_style(color: Color) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(12)
	style.content_margin_left = 14.0
	style.content_margin_right = 14.0
	style.content_margin_top = 6.0
	style.content_margin_bottom = 7.0
	return style
