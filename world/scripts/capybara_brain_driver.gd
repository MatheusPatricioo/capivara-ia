class_name CapybaraBrainDriver
extends Node

## Makes the parent capybara obey the brain: she walks to the place it asks for (computer,
## chalkboard, pond...), stays there a little while the brain works, then goes back to strolling.

## Seconds the capybara stays at a place after arriving, before strolling again.
@export var stay_seconds: float = 6.0
## Speed multiplier for errands from the brain: a determined walk, faster than a stroll.
@export var errand_speed_scale: float = 1.3

var _stay_timer: Timer = Timer.new()
var _is_on_errand: bool = false

@onready var _capybara: Capybara = get_parent() as Capybara
@onready var _wander: CapybaraWander = $"../Wander" as CapybaraWander


func _ready() -> void:
	_stay_timer.one_shot = true
	_stay_timer.timeout.connect(_finish_errand)
	add_child(_stay_timer)
	_capybara.destination_reached.connect(_on_destination_reached)
	Brain.go_to_requested.connect(_on_go_to_requested)


func _on_go_to_requested(point_id: StringName) -> void:
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
