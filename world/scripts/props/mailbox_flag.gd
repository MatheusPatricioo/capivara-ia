class_name MailboxFlag
extends StaticBody3D

## The red flag of the mailbox: up while a letter from the capybara waits unread, down when
## Matheus has read them all. The brain sends the letters; this only shows them.

const FLAG_UP_DEGREES: float = 0.0
const FLAG_DOWN_DEGREES: float = -90.0

## Seconds the flag takes to go up or down.
@export var flag_seconds: float = 0.6

var _flag_tween: Tween

@onready var _flag_pivot: Node3D = $FlagPivot


func _ready() -> void:
	_flag_pivot.rotation_degrees.x = FLAG_DOWN_DEGREES
	Brain.mailbox_changed.connect(_on_mailbox_changed)


func _on_mailbox_changed(letters: Array) -> void:
	_raise_flag(_has_unread(letters))


func _has_unread(letters: Array) -> bool:
	for letter: Variant in letters:
		if letter is Dictionary and bool((letter as Dictionary).get("unread", false)):
			return true
	return false


func _raise_flag(is_up: bool) -> void:
	if _flag_tween != null:
		_flag_tween.kill()
	_flag_tween = create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	var target_degrees: float = FLAG_UP_DEGREES if is_up else FLAG_DOWN_DEGREES
	_flag_tween.tween_property(_flag_pivot, "rotation_degrees:x", target_degrees, flag_seconds)
