@tool
class_name WaterTint
extends Node

## Repaints the water of an imported kit model with our own water material.
## Add it as a child of the model instance: every mesh surface whose material name
## contains "water" gets the override, so rocks and grass keep their own colors.

const WATER_NAME_PART: String = "water"

@export var water_material: Material


func _ready() -> void:
	if water_material == null:
		return
	_tint_tree(get_parent())


func _tint_tree(node: Node) -> void:
	if node is MeshInstance3D:
		_tint_mesh(node as MeshInstance3D)
	for child: Node in node.get_children():
		_tint_tree(child)


func _tint_mesh(mesh_instance: MeshInstance3D) -> void:
	if mesh_instance.mesh == null:
		return
	for surface_index: int in mesh_instance.mesh.get_surface_count():
		var surface_material: Material = mesh_instance.mesh.surface_get_material(surface_index)
		if surface_material != null and surface_material.resource_name.to_lower().contains(WATER_NAME_PART):
			mesh_instance.set_surface_override_material(surface_index, water_material)
