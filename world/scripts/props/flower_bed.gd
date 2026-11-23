@tool
class_name FlowerBed
extends Node3D

## A tidy garden bed: a low wooden frame filled with soil and straight rows of flowers.
## The rows run along the local Z axis. Flowers are MultiMesh copies, and the bed has one
## box collision, so the capybara walks around it instead of over the flowers.

const FRAME_HEIGHT: float = 0.14
const FRAME_THICKNESS: float = 0.06
const SOIL_SINK: float = 0.03
const WOOD_COLOR: Color = Color(0.55, 0.36, 0.2)
const SOIL_COLOR: Color = Color(0.33, 0.22, 0.14)
## Small random size changes so the rows look planted by hand, not stamped.
const FLOWER_SCALE_JITTER: float = 0.12

## Width (local X) and length (local Z) of the bed in meters.
@export var size: Vector2 = Vector2(0.8, 2.0):
	set(value):
		size = value
		_rebuild()

@export var rows: int = 2:
	set(value):
		rows = maxi(value, 1)
		_rebuild()

@export var flowers_per_row: int = 6:
	set(value):
		flowers_per_row = maxi(value, 1)
		_rebuild()

## Each flower picks one of these models at random.
@export var flower_models: Array[PackedScene] = []:
	set(value):
		flower_models = value
		_rebuild()

@export var flower_scale: float = 1.0:
	set(value):
		flower_scale = maxf(value, 0.01)
		_rebuild()

@export var random_seed: int = 1:
	set(value):
		random_seed = value
		_rebuild()

var _built_nodes: Array[Node] = []


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	_clear()
	_add_box("Soil", Vector3(size.x, FRAME_HEIGHT - SOIL_SINK, size.y), Vector3.ZERO, SOIL_COLOR)
	_add_frame()
	_add_collision()
	_add_flowers()


func _add_frame() -> void:
	var long_side: Vector3 = Vector3(FRAME_THICKNESS, FRAME_HEIGHT, size.y + FRAME_THICKNESS)
	var short_side: Vector3 = Vector3(size.x + FRAME_THICKNESS, FRAME_HEIGHT, FRAME_THICKNESS)
	_add_box("FrameLeft", long_side, Vector3(-size.x / 2.0, 0.0, 0.0), WOOD_COLOR)
	_add_box("FrameRight", long_side, Vector3(size.x / 2.0, 0.0, 0.0), WOOD_COLOR)
	_add_box("FrameFront", short_side, Vector3(0.0, 0.0, size.y / 2.0), WOOD_COLOR)
	_add_box("FrameBack", short_side, Vector3(0.0, 0.0, -size.y / 2.0), WOOD_COLOR)


## Boxes sit on the ground: bottom_center.y is the bottom, not the middle.
func _add_box(box_name: String, box_size: Vector3, bottom_center: Vector3, color: Color) -> void:
	var box_mesh: BoxMesh = BoxMesh.new()
	box_mesh.size = box_size
	var material: StandardMaterial3D = StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.95
	box_mesh.material = material
	var box: MeshInstance3D = MeshInstance3D.new()
	box.name = box_name
	box.mesh = box_mesh
	box.position = bottom_center + Vector3(0.0, box_size.y / 2.0, 0.0)
	_keep(box)


func _add_collision() -> void:
	var shape: BoxShape3D = BoxShape3D.new()
	shape.size = Vector3(size.x + FRAME_THICKNESS, FRAME_HEIGHT * 3.0, size.y + FRAME_THICKNESS)
	var collision: CollisionShape3D = CollisionShape3D.new()
	collision.shape = shape
	collision.position.y = shape.size.y / 2.0
	var body: StaticBody3D = StaticBody3D.new()
	body.name = "Body"
	body.add_child(collision)
	_keep(body)


func _add_flowers() -> void:
	var usable_models: Array[PackedScene] = []
	for model: PackedScene in flower_models:
		if model != null:
			usable_models.append(model)
	if usable_models.is_empty():
		return
	var random: RandomNumberGenerator = RandomNumberGenerator.new()
	random.seed = random_seed
	var copies_per_model: Array[Array] = []
	for model_index: int in usable_models.size():
		var model_copies: Array[Transform3D] = []
		copies_per_model.append(model_copies)
	var row_spacing: float = size.x / rows
	var flower_spacing: float = size.y / flowers_per_row
	for row_index: int in rows:
		for flower_index: int in flowers_per_row:
			var flower_position: Vector3 = Vector3(
				-size.x / 2.0 + (row_index + 0.5) * row_spacing,
				FRAME_HEIGHT - SOIL_SINK,
				-size.y / 2.0 + (flower_index + 0.5) * flower_spacing
			)
			var flower_size: float = flower_scale * random.randf_range(1.0 - FLOWER_SCALE_JITTER, 1.0 + FLOWER_SCALE_JITTER)
			var flower_basis: Basis = Basis(Vector3.UP, random.randf_range(0.0, TAU)).scaled(Vector3.ONE * flower_size)
			var model_index: int = random.randi_range(0, usable_models.size() - 1)
			copies_per_model[model_index].append(Transform3D(flower_basis, flower_position))
	for model_index: int in usable_models.size():
		for drawer: MultiMeshInstance3D in MultiMeshCopies.add_to(self, usable_models[model_index], copies_per_model[model_index]):
			# Small flowers: their shadow is barely visible and costs a draw call per shadow split.
			drawer.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			_built_nodes.append(drawer)


func _keep(node: Node) -> void:
	add_child(node)
	_built_nodes.append(node)


func _clear() -> void:
	for built_node: Node in _built_nodes:
		built_node.queue_free()
	_built_nodes.clear()
