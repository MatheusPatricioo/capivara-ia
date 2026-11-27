class_name CapybaraBrainDriver
extends Node

## Makes the parent capybara obey the brain: she walks to the place it asks for (computer,
## pond, food bowl...), stays there a little while the brain works, then goes back to strolling.
## While her creator talks with her, listening comes first: the errand is dropped and new
## ones are ignored until the conversation is over.

## Seconds the capybara stays at a place after arriving, before strolling again.
@export var stay_seconds: float = 6.0
## Speed multiplier for errands from the brain: a determined walk, faster than a stroll.
@export var errand_speed_scale: float = 1.3

var _stay_timer: Timer = Timer.new()
var _is_on_errand: bool = false

@onready var _capybara: Capybara = get_parent() as Capybara
@onready var _wander: CapybaraWander = $"../Wander" as CapybaraWander
@onready var _listening: CapybaraListening = $"../Listening" as CapybaraListening


func _ready() -> void:
	_stay_timer.one_shot = true
	_stay_timer.timeout.connect(_finish_errand)
	add_child(_stay_timer)
	_capybara.destination_reached.connect(_on_destination_reached)
	Brain.go_to_requested.connect(_on_go_to_requested)
	_listening.listening_started.connect(_drop_errand)


func _on_go_to_requested(point_id: StringName) -> void:
	if _listening.is_listening():
		print("Capybara is listening to her creator, not going to %s" % point_id)
		return
	if not _capybara.go_to_point(point_id, errand_speed_scale):
		return
	print("Capybara going to %s" % point_id)
	_wander.pause()
	_stay_timer.stop()
	_is_on_errand = true


func _on_destination_reached() -> void:
	if _is_on_errand:
		print("Capybara arrived, staying %.0f seconds" % stay_seconds)
		_stay_timer.start(stay_seconds)


func _finish_errand() -> void:
	_is_on_errand = false
	_wander.resume()


## Listening stopped her where she was; strolling comes back when listening ends.
func _drop_errand() -> void:
	_stay_timer.stop()
	_is_on_errand = false
