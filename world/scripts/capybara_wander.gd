class_name CapybaraWander
extends Node

## Stroll mode for the parent capybara: picks a random free point, walks there,
## rests for a few seconds and picks another one.

const ALL_NAVIGATION_LAYERS: int = 1

## Shortest rest between two walks, in seconds. Short rests look like a quick sniff.
@export var min_rest_seconds: float = 0.8
## Longest rest between two walks, in seconds.
@export var max_rest_seconds: float = 4.0
## Chance (0 to 1) that a walk is a trot instead of a calm stroll.
@export var trot_chance: float = 0.3
## Speed multiplier used when trotting.
@export var trot_speed_scale: float = 1.5
## How many random points to try before giving up until the next rest.
@export var max_destination_attempts: int = 10
## How close the end of a path must be to the picked point to count as reachable.
@export var reachable_tolerance: float = 0.5

## Multiplies the walking speed. Set by CapybaraFeelings: below 1 when she is down.
var mood_pace: float = 1.0
## Multiplies the rests between walks. Set by CapybaraFeelings: above 1 when she is down.
var mood_rest: float = 1.0

var _rest_timer: Timer = Timer.new()
var _is_paused: bool = false

@onready var _capybara: Capybara = get_parent() as Capybara


func _ready() -> void:
	_rest_timer.one_shot = true
	_rest_timer.timeout.connect(_walk_to_random_point)
	add_child(_rest_timer)
	_capybara.destination_reached.connect(_start_rest)
	_start_rest()


## Stops strolling, for example while the brain sends the capybara somewhere.
func pause() -> void:
	_is_paused = true
	_rest_timer.stop()


## Goes back to strolling after a short rest.
func resume() -> void:
	_is_paused = false
	_start_rest()


func _start_rest() -> void:
	if _is_paused:
		return
	_rest_timer.start(randf_range(min_rest_seconds, max_rest_seconds) * mood_rest)


func _walk_to_random_point() -> void:
	var navigation_map: RID = _capybara.get_world_3d().navigation_map
	# The navigation mesh is baked on a thread at startup; until then the map is empty.
	if NavigationServer3D.map_get_iteration_id(navigation_map) == 0:
		_start_rest()
		return
	for _attempt: int in max_destination_attempts:
		var destination: Vector3 = NavigationServer3D.map_get_random_point(
			navigation_map, ALL_NAVIGATION_LAYERS, true
		)
		if _is_reachable(navigation_map, destination):
			_capybara.walk_to(destination, _pick_pace())
			return
	_start_rest()


func _pick_pace() -> float:
	var base_pace: float = trot_speed_scale if randf() < trot_chance else 1.0
	return base_pace * mood_pace


## Random points may land on an island the capybara cannot reach (like the top of a rock),
## so a path is planned first and must end close to the picked point.
func _is_reachable(navigation_map: RID, destination: Vector3) -> bool:
	var path: PackedVector3Array = NavigationServer3D.map_get_path(
		navigation_map, _capybara.global_position, destination, true
	)
	if path.is_empty():
		return false
	return path[path.size() - 1].distance_to(destination) <= reachable_tolerance
