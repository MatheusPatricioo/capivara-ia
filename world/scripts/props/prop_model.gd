@tool
class_name PropModel
extends StaticBody3D

## 3D model (.glb) shown by this prop. Lets one scene serve many variants.
@export var model: PackedScene:
	set(value):
		model = value
		_refresh_model()

## Builds a convex collision wrapping the model meshes. Good for solid props like rocks;
## leave it off for trees, where the canopy would become an invisible wall.
@export var collision_from_model: bool = false:
	set(value):
		collision_from_model = value
		_refresh_model()

var _model_instance: Node3D = null
var _generated_collisions: Array[CollisionShape3D] = []


func _ready() -> void:
	_refresh_model()


func _refresh_model() -> void:
	if not is_node_ready():
		return
	_clear_model()
	if model == null:
		return
	_model_instance = model.instantiate() as Node3D
	if _model_instance == null:
		return
	add_child(_model_instance)
	if collision_from_model:
		_build_collision_from_model()


func _clear_model() -> void:
	if _model_instance != null:
		_model_instance.queue_free()
		_model_instance = null
	for generated_collision: CollisionShape3D in _generated_collisions:
		generated_collision.queue_free()
	_generated_collisions.clear()


func _build_collision_from_model() -> void:
	var mesh_nodes: Array[Node] = _model_instance.find_children("*", "MeshInstance3D", true, false)
	for mesh_node: Node in mesh_nodes:
		var mesh_instance: MeshInstance3D = mesh_node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var collision: CollisionShape3D = CollisionShape3D.new()
		collision.shape = mesh_instance.mesh.create_convex_shape()
		add_child(collision)
		collision.global_transform = mesh_instance.global_transform
		_generated_collisions.append(collision)
