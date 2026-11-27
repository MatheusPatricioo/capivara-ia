class_name ClipCamera
extends Camera3D

## A camera that films the capybara from the front, following her smoothly, like a camera
## operator walking with her. It only frames: what shot to use, and when to cut, is decided
## by ClipDirector.
##
## Every frame it moves only part of the way to where it should be (exponential smoothing),
## so it never shakes when she turns or speeds up. Rays from her head keep trees and walls
## out of the way: when the usual spot is blocked, the camera walks around her to the first
## side with a clear view; only when every side is blocked does it come closer, in front of
## the obstacle, and it goes back out slowly once the view is clear.

## Angles tried around her, in degrees, when the usual spot is blocked: nearest first.
const DETOUR_DEGREES: Array[float] = [35.0, -35.0, 70.0, -70.0, 110.0, -110.0]
## Meters between the ground points checked against the navigation map.
const MAP_CHECK_STEP: float = 0.4
## A ground point this far from where she can walk, in meters, is inside an obstacle. The
## map keeps about half a meter from objects, so a little less than that still counts as free.
const MAP_TOLERANCE: float = 0.45

## How quickly the camera catches up with her position. Higher follows tighter.
@export var follow_sharpness: float = 6.0
## How quickly the camera goes around her when she turns. Lower turns calmer.
@export var turn_sharpness: float = 2.0
## How quickly the camera goes back out after an obstacle left the view.
@export var release_sharpness: float = 2.0
## Meters kept between the camera and whatever blocked the view.
@export var obstacle_margin: float = 0.3
## The closest the camera ever gets, in meters, even with an obstacle right behind her.
@export var min_distance: float = 1.6
## A side counts as clear when the camera can stand at least this fraction of the shot's
## distance away from her there.
@export var clear_fraction: float = 0.8
## Which side of her face the camera stands on: 1 is her left, -1 her right. Staying on one
## side across cuts keeps her looking the same way, so the cuts do not confuse.
@export var side: float = 1.0

var _target: Capybara = null
var _shot: ClipShot = ClipShot.medium()
var _pivot: Vector3 = Vector3.ZERO
var _yaw: float = 0.0
var _distance: float = 0.0
## Extra angle around her to get past an obstacle, in radians; 0 when the usual spot is clear.
var _detour: float = 0.0


func follow(target: Capybara) -> void:
	_target = target


## Changes the framing at once, with no movement in between: a cut.
func cut_to(shot: ClipShot) -> void:
	_shot = shot
	fov = shot.field_of_view
	if _target == null:
		return
	_pivot = _aim_point()
	_detour = _choose_detour(_desired_yaw())
	_yaw = _desired_yaw() + _detour
	_distance = _clear_distance(_yaw, _shot.distance)
	_place()


func _process(delta: float) -> void:
	if _target == null:
		return
	_pivot = _pivot.lerp(_aim_point(), _smoothing(follow_sharpness, delta))
	_detour = _choose_detour(_desired_yaw())
	_yaw = lerp_angle(_yaw, _desired_yaw() + _detour, _smoothing(turn_sharpness, delta))
	var clear_distance: float = _clear_distance(_yaw, _shot.distance)
	# In at once, so the view is never blocked; out slowly, so it does not pop.
	if clear_distance < _distance:
		_distance = clear_distance
	else:
		_distance = lerpf(_distance, clear_distance, _smoothing(release_sharpness, delta))
	_place()


func _place() -> void:
	global_position = _pivot + _direction_to_camera(_yaw) * _distance
	look_at(_pivot + Vector3.UP * _shot.headroom, Vector3.UP)


func _aim_point() -> Vector3:
	return _target.global_position + Vector3.UP * _shot.aim_height


## The angle around her where the camera stands: in front of her face, turned a little to
## one side.
func _desired_yaw() -> float:
	var front: Vector3 = _target.facing_direction()
	return atan2(front.x, front.z) + side * deg_to_rad(_shot.yaw_degrees)


func _direction_to_camera(yaw: float) -> Vector3:
	var pitch: float = deg_to_rad(_shot.pitch_degrees)
	return Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))


## Keeps the current detour while it stays clear, so the camera does not hesitate between
## two sides. The usual spot wins back as soon as it is clear again.
func _choose_detour(usual_yaw: float) -> float:
	if _is_clear(usual_yaw):
		return 0.0
	if _detour != 0.0 and _is_clear(usual_yaw + _detour):
		return _detour
	for detour_degrees: float in DETOUR_DEGREES:
		var detour: float = deg_to_rad(detour_degrees * side)
		if _is_clear(usual_yaw + detour):
			return detour
	return 0.0


func _is_clear(yaw: float) -> bool:
	return _clear_distance(yaw, _shot.distance) >= _shot.distance * clear_fraction


## How far the camera can be, at this angle around her, with nothing between it and her
## head. Two checks, since many props are only meshes, with no collision: a physics ray for
## what has a body, and the navigation map for the rest.
func _clear_distance(yaw: float, wanted_distance: float) -> float:
	var direction: Vector3 = _direction_to_camera(yaw)
	var clear_distance: float = minf(
		_distance_to_first_body(direction, wanted_distance),
		_distance_to_first_obstacle_on_the_map(direction, wanted_distance)
	)
	if clear_distance >= wanted_distance:
		return wanted_distance
	return maxf(clear_distance - obstacle_margin, min_distance)


func _distance_to_first_body(direction: Vector3, wanted_distance: float) -> float:
	var query: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(
		_pivot, _pivot + direction * wanted_distance
	)
	query.exclude = [_target.get_rid()]
	var hit: Dictionary = get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return wanted_distance
	return _pivot.distance_to(hit["position"])


## The navigation map is where she can walk: trees, houses and furniture are holes in it,
## and the fences are its edge. Walking the ground under the line of sight, the first point
## far from the map is something in the way.
func _distance_to_first_obstacle_on_the_map(direction: Vector3, wanted_distance: float) -> float:
	var navigation_map: RID = get_world_3d().navigation_map
	# The map is built after the first physics frame; until then it knows nothing.
	if NavigationServer3D.map_get_iteration_id(navigation_map) == 0:
		return wanted_distance
	var walked: float = MAP_CHECK_STEP
	while walked <= wanted_distance:
		var point: Vector3 = _pivot + direction * walked
		var ground_point: Vector3 = Vector3(point.x, _target.global_position.y, point.z)
		var closest_walkable: Vector3 = NavigationServer3D.map_get_closest_point(
			navigation_map, ground_point
		)
		var off_map: Vector2 = Vector2(
			closest_walkable.x - ground_point.x, closest_walkable.z - ground_point.z
		)
		if off_map.length() > MAP_TOLERANCE:
			return walked
		walked += MAP_CHECK_STEP
	return wanted_distance


## The fraction of the way to move this frame. Written with exp, the camera moves the same
## no matter the frame rate.
static func _smoothing(sharpness: float, delta: float) -> float:
	return 1.0 - exp(-sharpness * delta)
