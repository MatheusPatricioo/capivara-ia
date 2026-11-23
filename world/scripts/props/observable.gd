class_name Observable
extends Area3D

## Something in the world the capybara can notice: an invisible sphere around it. When she
## walks into the sphere, the world tells the brain what she saw. The brain decides whether
## it deserves her attention; the world only reports it.

## Short, stable id the brain uses to recognize the thing, like &"water_lilies".
@export var thing_id: StringName = &""
## What she sees, in Brazilian Portuguese, as she would describe it.
@export_multiline var description: String = ""
## How close she must get, in meters, to notice it.
@export var notice_radius: float = 1.5
## Seconds before the same thing is reported again, so walking around it does not repeat it.
@export var renotice_seconds: float = 60.0

const NEVER_NOTICED: int = -1

var _last_noticed_at_msec: int = NEVER_NOTICED


func _ready() -> void:
	# A sensor only: it must not block clicks on the computer or be seen by other areas.
	input_ray_pickable = false
	monitorable = false
	_add_notice_sphere()
	body_entered.connect(_on_body_entered)


func _add_notice_sphere() -> void:
	var sphere: SphereShape3D = SphereShape3D.new()
	sphere.radius = notice_radius
	var notice_shape: CollisionShape3D = CollisionShape3D.new()
	notice_shape.name = "NoticeSphere"
	notice_shape.shape = sphere
	add_child(notice_shape)


func _on_body_entered(body: Node3D) -> void:
	if not body is Capybara or not _can_notice_again():
		return
	_last_noticed_at_msec = Time.get_ticks_msec()
	Brain.report_noticed(thing_id, description)


func _can_notice_again() -> bool:
	if _last_noticed_at_msec == NEVER_NOTICED:
		return true
	return Time.get_ticks_msec() - _last_noticed_at_msec >= renotice_seconds * 1000.0
