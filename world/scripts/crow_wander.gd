class_name CrowWander
extends Node

## Stroll mode for the parent crow: picks a random free point, walks there,
## rests for a few seconds and picks another one.

const ALL_NAVIGATION_LAYERS: int = 1

## Shortest rest between two walks, in seconds.
@export var min_rest_seconds: float = 2.0
## Longest rest between two walks, in seconds.
@export var max_rest_seconds: float = 5.0
## How many random points to try before giving up until the next rest.
@export var max_destination_attempts: int = 10
## How close the end of a path must be to the picked point to count as reachable.
@export var reachable_tolerance: float = 0.5

var _rest_timer: Timer = Timer.new()

@onready var _crow: Crow = get_parent() as Crow


func _ready() -> void:
	_rest_timer.one_shot = true
	_rest_timer.timeout.connect(_walk_to_random_point)
	add_child(_rest_timer)
	_crow.destination_reached.connect(_start_rest)
	_start_rest()


func _start_rest() -> void:
	_rest_timer.start(randf_range(min_rest_seconds, max_rest_seconds))


func _walk_to_random_point() -> void:
	var navigation_map: RID = _crow.get_world_3d().navigation_map
	# The navigation mesh is baked on a thread at startup; until then the map is empty.
	if NavigationServer3D.map_get_iteration_id(navigation_map) == 0:
		_start_rest()
		return
	for _attempt: int in max_destination_attempts:
		var destination: Vector3 = NavigationServer3D.map_get_random_point(
			navigation_map, ALL_NAVIGATION_LAYERS, true
		)
		if _is_reachable(navigation_map, destination):
			_crow.walk_to(destination)
			return
	_start_rest()


## Random points may land on an island the crow cannot reach (like the top of a rock),
## so a path is planned first and must end close to the picked point.
func _is_reachable(navigation_map: RID, destination: Vector3) -> bool:
	var path: PackedVector3Array = NavigationServer3D.map_get_path(
		navigation_map, _crow.global_position, destination, true
	)
	if path.is_empty():
		return false
	return path[path.size() - 1].distance_to(destination) <= reachable_tolerance
