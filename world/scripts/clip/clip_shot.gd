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


func _init(
	shot_distance: float,
	shot_pitch_degrees: float,
	shot_yaw_degrees: float,
	shot_field_of_view: float,
	shot_aim_height: float,
	shot_headroom: float
) -> void:
	distance = shot_distance
	pitch_degrees = shot_pitch_degrees
	yaw_degrees = shot_yaw_degrees
	field_of_view = shot_field_of_view
	aim_height = shot_aim_height
	headroom = shot_headroom


## Her face and whole body: for feelings and lines.
static func close() -> ClipShot:
	return ClipShot.new(2.6, 12.0, 25.0, 42.0, 0.45, -0.05)


## Her whole body and what is around her: to show what she is doing.
static func medium() -> ClipShot:
	return ClipShot.new(3.3, 16.0, 30.0, 45.0, 0.4, 0.0)


## A wide view of her in the world: to open an episode.
static func wide() -> ClipShot:
	return ClipShot.new(6.5, 28.0, 30.0, 50.0, 0.4, 0.3)


## The shot with this name ("close", "medium" or "wide"); null for any other name.
static func named(shot_name: String) -> ClipShot:
	match shot_name:
		"close":
			return close()
		"medium":
			return medium()
		"wide":
			return wide()
	return null
