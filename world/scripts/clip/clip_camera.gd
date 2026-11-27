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
## Between shots it can cut (cut_to) or glide (glide_to): a glide travels from one framing
## to the other, starting and stopping gently, like an operator moving the camera. Within a
## shot it plays the shot's own slow movement (an arc, a dolly, a tilt) on top.

## Angles tried around her, in degrees, when the usual spot is blocked: nearest first.
const DETOUR_DEGREES: Array[float] = [35.0, -35.0, 70.0, -70.0, 110.0, -110.0]
## Meters between the ground points checked against the navigation map.
const MAP_CHECK_STEP: float = 0.4
## A ground point this far from where she can walk, in meters, is inside an obstacle. The
## map keeps about half a meter from objects, so a little less than that still counts as free.
const MAP_TOLERANCE: float = 0.45
## Degrees between where the camera is around her and where it should be, past which it
## counts as lagging: she turned faster than the camera follows.
const LAG_DEGREES: float = 45.0
## Walking speed, in m/s, at which the look room is complete; slower, it is smaller.
const LOOK_ROOM_FULL_SPEED: float = 2.0
## Below this speed, in m/s, she counts as standing still.
const STANDING_SPEED: float = 0.05
## The lowest the camera goes, in meters above her feet, after the Reels lens shift lowers
## it: a camera under the ground films the sky from below.
const MIN_CAMERA_HEIGHT: float = 0.15

## How quickly the camera catches up with her position. Higher follows tighter.
@export var follow_sharpness: float = 6.0
## How quickly the camera goes around her when she turns. Lower turns calmer.
@export var turn_sharpness: float = 2.0
## How quickly the camera goes back out after an obstacle left the view.
@export var release_sharpness: float = 2.0
## Meters kept between the camera and whatever blocked the view.
@export var obstacle_margin: float = 0.3
## How far the camera turns its eyes from her toward the object she uses: 0 looks only
## at her, 1 only at the object.
@export var focus_weight: float = 0.5
## The closest the camera ever gets, in meters, even with an obstacle right behind her.
@export var min_distance: float = 1.6
## A side counts as clear when the camera can stand at least this fraction of the shot's
## distance away from her there.
@export var clear_fraction: float = 0.8
## Which side of her face the camera stands on: 1 is her left, -1 her right. Staying on one
## side across cuts keeps her looking the same way, so the cuts do not confuse.
@export var side: float = 1.0
## Meters of empty space kept in front of her while she walks, so she walks into the
## picture instead of out of it (look room). Full at LOOK_ROOM_FULL_SPEED and above.
@export var look_room_meters: float = 0.2
## In a vertical clip, how far up the picture moves, as a fraction of its height: the
## Reels app covers the bottom 35% and the top 14%, so the middle of what is left sits at
## about 40% of the height, not 50%.
@export var reels_frame_shift: float = 0.11

var _target: Capybara = null
## The framing of this frame, movement included: everything that places the camera reads it.
var _shot: ClipShot = ClipShot.medium()
## The framing before the movement: the shot itself, or part of the way along a glide.
var _base_shot: ClipShot = ClipShot.medium()
## The shot whose movement plays, and for how long it has been playing.
var _moving_shot: ClipShot = ClipShot.medium()
var _move_elapsed: float = 0.0
var _pivot: Vector3 = Vector3.ZERO
var _yaw: float = 0.0
var _distance: float = 0.0
## Extra angle around her to get past an obstacle, in radians; 0 when the usual spot is clear.
var _detour: float = 0.0
## The object she is using, framed together with her; only while _has_focus.
var _focus_point: Vector3 = Vector3.ZERO
var _has_focus: bool = false
var _is_framing_for_reels: bool = false
## The glide in progress: from one framing to the shot it ends on; null when not gliding.
var _glide_from: ClipShot = null
var _glide_target: ClipShot = null
var _glide_seconds: float = 0.0
var _glide_elapsed: float = 0.0


func follow(target: Capybara) -> void:
	_target = target


## On, the picture moves up into the part of a Reels video the app leaves clear. Only for
## vertical pictures: a horizontal clip keeps her centered.
func frame_for_reels(is_on: bool) -> void:
	_is_framing_for_reels = is_on


## Frames her together with this object (the computer, the mailbox...): the shot's angle
## counts from the direction she looks at it, and the camera looks between her and it.
func focus_on(object_position: Vector3) -> void:
	_focus_point = object_position
	_has_focus = true


func clear_focus() -> void:
	_has_focus = false


## Changes the framing at once, with no movement in between: a cut. It stops any glide,
## and the new shot's movement starts from the beginning.
func cut_to(shot: ClipShot) -> void:
	_glide_target = null
	_base_shot = shot
	_moving_shot = shot
	_move_elapsed = 0.0
	_shot = shot
	fov = shot.field_of_view
	if _target == null:
		return
	# A cut has no smoothing to catch up with: only the look room. It forgets the old
	# detour, so the usual spot is tried first.
	_pivot = _framed_point()
	_detour = 0.0
	_detour = _choose_detour(_desired_yaw())
	_yaw = _desired_yaw() + _detour
	_distance = _clear_distance(_yaw, _shot.distance)
	_place()


## Travels from the current framing to this shot over these seconds. It leaves from the
## framing of this frame, movement and any glide in progress included, so it never jumps.
## The new shot's movement starts along with the glide.
func glide_to(shot: ClipShot, seconds: float) -> void:
	if _target == null or seconds <= 0.0:
		cut_to(shot)
		return
	_glide_from = _shot
	_glide_target = shot
	_glide_seconds = seconds
	_glide_elapsed = 0.0
	_moving_shot = shot
	_move_elapsed = 0.0


func _process(delta: float) -> void:
	if _target == null:
		return
	_advance_framing(delta)
	_pivot =_pivot.lerp(_aim_point(), _smoothing(follow_sharpness, delta))
	_detour = _choose_detour(_desired_yaw())
	_yaw = lerp_angle(_yaw, _desired_yaw() + _detour, _smoothing(turn_sharpness, delta))
	var clear_distance: float = _clear_distance(_yaw, _shot.distance)
	# In at once, so the view is never blocked; out slowly, so it does not pop.
	if clear_distance < _distance:
		_distance = clear_distance
	else:
		_distance = lerpf(_distance, clear_distance, _smoothing(release_sharpness, delta))
	_place()


## The framing of this frame: the base (part of the way along any glide) plus the part of
## the shot's movement done so far. Like an operator, the movement stops where its next
## step would put something between the camera and her: otherwise the obstacle rules
## would make the camera jump closer or to another side in the middle of a slow move.
func _advance_framing(delta: float) -> void:
	_advance_glide(delta)
	var elapsed_before: float = _move_elapsed
	_move_elapsed += delta
	var next_framing: ClipShot = ClipShot.moved(_base_shot, _moving_shot, _movement_progress())
	if _moving_into_obstacle(next_framing):
		_move_elapsed = elapsed_before
		next_framing = ClipShot.moved(_base_shot, _moving_shot, _movement_progress())
	_shot = next_framing
	fov = _shot.field_of_view


## True when the next framing would see her less clearly than this one: the movement may
## never make the view worse. That covers both obstacle rules (coming closer and walking
## around to another side), and still lets the movement go on while it helps or changes
## nothing, for example when she stands by the fence.
func _moving_into_obstacle(next_framing: ClipShot) -> bool:
	if _moving_shot.move_seconds <= 0.0:
		return false
	return _clear_fraction_of(next_framing) < _clear_fraction_of(_shot)


## How much of the framing's distance is free of obstacles, from 0 to 1.
func _clear_fraction_of(framing: ClipShot) -> float:
	var yaw: float = _desired_yaw_for(framing) + _detour
	return _clear_distance(yaw, framing.distance) / framing.distance


## smoothstep eases the glide: slow at the start, faster in the middle and slow at the end.
func _advance_glide(delta: float) -> void:
	if _glide_target == null:
		return
	_glide_elapsed += delta
	var progress: float = minf(_glide_elapsed / _glide_seconds, 1.0)
	_base_shot = ClipShot.blended(_glide_from, _glide_target, smoothstep(0.0, 1.0, progress))
	if progress >= 1.0:
		_base_shot = _glide_target
		_glide_target = null


## From 0 to 1, eased like the glide, then held at 1: the movement ends at rest.
func _movement_progress() -> float:
	if _moving_shot.move_seconds <= 0.0:
		return 0.0
	return smoothstep(0.0, 1.0, minf(_move_elapsed / _moving_shot.move_seconds, 1.0))


## True while the camera is far from its place around her, still swinging after she turned.
## Not when an obstacle keeps it aside: that place already counts the detour.
func is_lagging_behind() -> bool:
	if _target == null:
		return false
	var place_yaw: float = _desired_yaw() + _detour
	return absf(angle_difference(_yaw, place_yaw)) > deg_to_rad(LAG_DEGREES)


func _place() -> void:
	global_position = _pivot + _direction_to_camera(_yaw) * _distance
	# v_offset lowers the camera by the Reels shift: keep it above the ground after that.
	var lowest_height: float = _target.global_position.y + MIN_CAMERA_HEIGHT + _reels_shift_meters()
	global_position.y = maxf(global_position.y, lowest_height)
	look_at(_look_point() + Vector3.UP * _shot.headroom, Vector3.UP)
	v_offset = -_reels_shift_meters()


## v_offset slides the picture like a shifted lens, without turning the camera. Lowering
## the camera moves her up in the picture. The fraction is turned into meters at her
## distance, where the picture is 2 * distance * tan(fov / 2) tall.
func _reels_shift_meters() -> float:
	if not _is_framing_for_reels:
		return 0.0
	return reels_frame_shift * 2.0 * _distance * tan(deg_to_rad(fov) / 2.0)


## Her head, or a point between her head and the object she uses, at her head's height.
func _look_point() -> Vector3:
	if not _has_focus:
		return _pivot
	var focus_at_head_height: Vector3 = Vector3(_focus_point.x, _pivot.y, _focus_point.z)
	return _pivot.lerp(focus_at_head_height, focus_weight)


## Where the camera's pivot heads for. The pivot follows with smoothing, so while she
## walks it stays velocity / follow_sharpness behind: aiming that far ahead of her cancels
## the lag, and the pivot settles on _framed_point.
func _aim_point() -> Vector3:
	return _framed_point() + _ground_velocity() / follow_sharpness


## The point the picture centers on: her body, shifted ahead of her by the look room, so
## she sits behind the center with space in front of her.
func _framed_point() -> Vector3:
	return _target.global_position + _look_room() + Vector3.UP * _shot.aim_height


func _look_room() -> Vector3:
	var ground_velocity: Vector3 = _ground_velocity()
	var speed: float = ground_velocity.length()
	if speed < STANDING_SPEED:
		return Vector3.ZERO
	var speed_fraction: float = minf(speed / LOOK_ROOM_FULL_SPEED, 1.0)
	return ground_velocity / speed * look_room_meters * speed_fraction


func _ground_velocity() -> Vector3:
	return Vector3(_target.velocity.x, 0.0, _target.velocity.z)


## The angle around her where the camera stands: in front of her face, turned a little to
## one side. With a focus, the front is toward the object, which stays still while she
## fidgets.
func _desired_yaw() -> float:
	return _desired_yaw_for(_shot)


func _desired_yaw_for(shot: ClipShot) -> float:
	var front: Vector3 = _target.facing_direction()
	if _has_focus:
		var to_focus: Vector3 = _focus_point - _target.global_position
		front = Vector3(to_focus.x, 0.0, to_focus.z).normalized()
	return atan2(front.x, front.z) + side * deg_to_rad(shot.yaw_degrees)


func _direction_to_camera(yaw: float) -> Vector3:
	var pitch: float = deg_to_rad(_shot.pitch_degrees)
	return Vector3(sin(yaw) * cos(pitch), sin(pitch), cos(yaw) * cos(pitch))


## Keeps the current detour while it stays clear, so the camera does not hesitate between
## two sides, nor swing back to the usual spot in the middle of a slow move the moment it
## clears (swinging fast, it would brush past obstacles and jump closer). A cut chooses
## again from the usual spot.
func _choose_detour(usual_yaw: float) -> float:
	if _detour != 0.0 and _is_clear(usual_yaw + _detour):
		return _detour
	if _is_clear(usual_yaw):
		return 0.0
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
