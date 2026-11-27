class_name InteractionPoint
extends Marker3D

## A place in the world with a purpose (sleeping, eating, working...). The marker position
## is where the capybara stands when using it. The brain refers to it by point_id.

## Emitted when the capybara arrives here, so the object can react to her.
signal capybara_arrived

const GROUP: StringName = &"interaction_points"
const NEVER: int = -1

## Identifier shared with the brain, like dog_house, food_bowl, computer or pond.
@export var point_id: StringName

var _last_arrival_msec: int = NEVER


func _ready() -> void:
	add_to_group(GROUP)


## Called by the capybara when she gets here.
func mark_capybara_arrived() -> void:
	_last_arrival_msec = Time.get_ticks_msec()
	capybara_arrived.emit()


## INF when she never came. Lets an object tell whether she is probably still standing here.
func seconds_since_capybara_arrived() -> float:
	if _last_arrival_msec == NEVER:
		return INF
	return (Time.get_ticks_msec() - _last_arrival_msec) / 1000.0


## Where the capybara looks while using the point: the object the marker belongs to.
func look_target() -> Vector3:
	var owner_object: Node3D = get_parent() as Node3D
	return owner_object.global_position if owner_object != null else global_position
