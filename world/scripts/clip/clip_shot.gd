class_name ClipShot
extends RefCounted

## How the clip camera frames the capybara in one kind of shot. All the series' shots live
## here, so every episode has the same look.

## Meters from her head to the camera.
var distance: float
## How far above her head the camera looks down from, in degrees (0 is eye level).
var pitch_degrees: float
## How far around from her face the camera stands, in degrees: 0 is straight in front of
## her, 90 is her side. A little off the front shows her face and her shape.
var yaw_degrees: float
## Vertical field of view, in degrees. Narrower is more zoom, like a longer lens.
var field_of_view: float
## Meters above her feet where the camera looks: around her head, so the face is framed.
var aim_height: float
## Meters the camera aims above aim_height. Above zero she sits lower in the frame, with
## room for the speech balloon; below zero she rises, away from the bottom of a Reel,
## where Instagram puts the caption and buttons.
var headroom: float

## The slow movement while the shot lasts, done over move_seconds (eased) and then at rest.
## Degrees the camera goes around her (an arc): positive goes further toward her side.
var orbit_degrees: float
## Meters the camera comes closer (negative, a dolly in) or goes back (positive).
var push_meters: float
## Meters the aim rises (a tilt up): she slides down a little and more sky shows.
var tilt_meters: float
## Seconds the movement takes; 0 for a still shot.
var move_seconds: float


func _init(
	shot_distance: float,
	shot_pitch_degrees: float,
	shot_yaw_degrees: float,
	shot_field_of_view: float,
	shot_aim_height: float,
	shot_headroom: float,
	shot_orbit_degrees: float = 0.0,
	shot_push_meters: float = 0.0,
	shot_tilt_meters: float = 0.0,
	shot_move_seconds: float = 0.0
) -> void:
	distance = shot_distance
	pitch_degrees = shot_pitch_degrees
	yaw_degrees = shot_yaw_degrees
	field_of_view = shot_field_of_view
	aim_height = shot_aim_height
	headroom = shot_headroom
	orbit_degrees = shot_orbit_degrees
	push_meters = shot_push_meters
	tilt_meters = shot_tilt_meters
	move_seconds = shot_move_seconds


## Her face and whole body: for feelings and lines. A slow arc toward her side shows her
## face turning into three quarters.
static func close() -> ClipShot:
	return ClipShot.new(2.6, 12.0, 25.0, 42.0, 0.33, -0.05, 20.0, 0.0, 0.0, 8.0)


## Her whole body and what is around her: to show what she is doing. Low enough that the
## distant hills show behind her. A slow dolly in, with a small arc.
static func medium() -> ClipShot:
	return ClipShot.new(3.3, 12.0, 30.0, 45.0, 0.28, 0.0, 10.0, -0.5, 0.0, 7.0)


## The landscape, with her small in it: to open an episode and, now and then, to breathe
## between shots. Almost at eye level, so the sky and the hills fill the top of the frame;
## the headroom keeps her below the middle, but above the Reels caption. The camera stays
## inside the fence (it counts everything past it as an obstacle), so the wider lens is
## what makes her small, not the distance. The aim tilts up slowly, revealing the sky,
## while the camera drifts a little around her.
static func wide() -> ClipShot:
	return ClipShot.new(7.0, 9.0, 30.0, 55.0, 0.28, 0.5, 8.0, 0.0, 0.5, 6.0)


## Over her shoulder, from behind and to one side: her and what she is using (the
## computer, the mailbox...) in the same frame. Used with ClipCamera.focus_on. A slow
## dolly in, toward what she does.
static func activity() -> ClipShot:
	return ClipShot.new(2.8, 14.0, 135.0, 48.0, 0.33, 0.1, 0.0, -0.3, 0.0, 6.0)


## Her side, her silhouette against the world. A slow arc turns toward her face, so the
## shot ends in three quarters.
static func profile() -> ClipShot:
	return ClipShot.new(3.0, 6.0, 90.0, 45.0, 0.28, 0.1, -15.0, 0.0, 0.0, 7.0)


## From close to the ground, looking a little up at her: she looks bigger and cuter, with
## the sky behind her. The camera stays just above the grass (the Reels lens shift lowers
## it further); the look up comes from aiming above her head. A slow arc.
static func low() -> ClipShot:
	return ClipShot.new(2.4, 3.0, 20.0, 50.0, 0.25, 0.4, 12.0, 0.0, 0.0, 7.0)


## Behind her while she walks, a little to one side: where she is going, with the world
## ahead of her. The aim is high, to show the way and the sky; the camera drifts back.
static func follow() -> ClipShot:
	return ClipShot.new(3.4, 14.0, 160.0, 50.0, 0.28, 0.35, 0.0, 0.4, 0.0, 6.0)


## This framing with part of the movement of `moving` done: weight 0 is none of it, 1 all.
## The result is a still framing (no movement of its own).
static func moved(framing: ClipShot, moving: ClipShot, weight: float) -> ClipShot:
	return ClipShot.new(
		framing.distance + moving.push_meters * weight,
		framing.pitch_degrees,
		framing.yaw_degrees + moving.orbit_degrees * weight,
		framing.field_of_view,
		framing.aim_height,
		framing.headroom + moving.tilt_meters * weight
	)


## A framing part of the way from one shot to another: weight 0 is from, 1 is to. Used
## by ClipCamera to glide between shots instead of cutting. The result is a still framing:
## the movement of a shot is added on top by ClipCamera.
static func blended(from: ClipShot, to: ClipShot, weight: float) -> ClipShot:
	return ClipShot.new(
		lerpf(from.distance, to.distance, weight),
		lerpf(from.pitch_degrees, to.pitch_degrees, weight),
		lerpf(from.yaw_degrees, to.yaw_degrees, weight),
		lerpf(from.field_of_view, to.field_of_view, weight),
		lerpf(from.aim_height, to.aim_height, weight),
		lerpf(from.headroom, to.headroom, weight)
	)


## The shot with this name ("close", "medium", "wide", "activity", "profile", "low" or
## "follow"); null for any other.
static func named(shot_name: String) -> ClipShot:
	match shot_name:
		"activity":
			return activity()
		"close":
			return close()
		"follow":
			return follow()
		"low":
			return low()
		"medium":
			return medium()
		"profile":
			return profile()
		"wide":
			return wide()
	return null
