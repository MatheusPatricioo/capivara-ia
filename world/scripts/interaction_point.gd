class_name InteractionPoint
extends Marker3D

## A place in the world with a purpose (sleeping, eating, working...). The marker position
## is where the capybara stands when using it. The brain refers to it by point_id.

const GROUP: StringName = &"interaction_points"

## Identifier shared with the brain, like bed, food_bowl, computer or chalkboard.
@export var point_id: StringName


func _ready() -> void:
	add_to_group(GROUP)
