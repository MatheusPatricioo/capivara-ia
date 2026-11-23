@tool
class_name SteppingStones
extends Node3D

## Small, flat, light stones laid along a path, drawn as one MultiMesh.
## Decoration only: there is no collision, so the capybara walks right over them.
## The path goes through path_points in order; a stone is placed every spacing meters.

const STONE_THICKNESS: float = 0.04
const STONE_SIDES: int = 7
## Each stone is a bit lighter or darker than the base color, like real stones.
const COLOR_JITTER: float = 0.08

## Points of the path in local coordinates; their height is ignored.
@export var path_points: PackedVector3Array = PackedVector3Array():
	set(value):
		path_points = value
		_rebuild()

@export var spacing: float = 0.32:
	set(value):
		spacing = maxf(value, 0.05)
		_rebuild()

@export var min_radius: float = 0.07:
	set(value):
		min_radius = maxf(value, 0.01)
		_rebuild()

@export var max_radius: float = 0.11:
	set(value):
		max_radius = maxf(value, 0.01)
		_rebuild()

## How far a stone may sit to the side of the path line, in meters.
@export var side_jitter: float = 0.08:
	set(value):
		side_jitter = maxf(value, 0.0)
		_rebuild()

@export var color: Color = Color(0.7, 0.63, 0.53):
	set(value):
		color = value
		_rebuild()

@export var random_seed: int = 1:
	set(value):
		random_seed = value
		_rebuild()

var _stones: MultiMeshInstance3D = null


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	if _stones != null:
		_stones.queue_free()
		_stones = null
	var stone_spots: Array[Transform3D] = _stone_spots()
	if stone_spots.is_empty():
		return
	_stones = MultiMeshInstance3D.new()
	_stones.name = "Stones"
	_stones.multimesh = _create_multimesh(stone_spots)
	add_child(_stones)


## Walks the path and drops a stone every spacing meters, each one turned, sized and
## shifted a little at random (with a fixed seed, so the path looks the same every time).
func _stone_spots() -> Array[Transform3D]:
	var spots: Array[Transform3D] = []
	if path_points.size() < 2:
		return spots
	var random: RandomNumberGenerator = RandomNumberGenerator.new()
	random.seed = random_seed
	var distance_to_next_stone: float = 0.0
	for segment_index: int in path_points.size() - 1:
		var segment_start: Vector3 = _flat(path_points[segment_index])
		var segment_end: Vector3 = _flat(path_points[segment_index + 1])
		var segment_length: float = segment_start.distance_to(segment_end)
		if segment_length <= 0.0:
			continue
		var direction: Vector3 = (segment_end - segment_start) / segment_length
		var side: Vector3 = Vector3(-direction.z, 0.0, direction.x)
		var walked: float = distance_to_next_stone
		while walked <= segment_length:
			var center: Vector3 = segment_start + direction * walked + side * random.randf_range(-side_jitter, side_jitter)
			spots.append(_stone_transform(center, random))
			walked += spacing
		distance_to_next_stone = walked - segment_length
	return spots


func _stone_transform(center: Vector3, random: RandomNumberGenerator) -> Transform3D:
	var radius: float = random.randf_range(min_radius, max_radius)
	var stone_size: Vector3 = Vector3(radius, 1.0, radius * random.randf_range(0.75, 1.0))
	var stone_basis: Basis = Basis(Vector3.UP, random.randf_range(0.0, TAU)).scaled(stone_size)
	return Transform3D(stone_basis, center + Vector3(0.0, STONE_THICKNESS / 2.0, 0.0))


func _create_multimesh(stone_spots: Array[Transform3D]) -> MultiMesh:
	var multimesh: MultiMesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	multimesh.mesh = _create_stone_mesh()
	multimesh.instance_count = stone_spots.size()
	var random: RandomNumberGenerator = RandomNumberGenerator.new()
	random.seed = random_seed + 1
	for stone_index: int in stone_spots.size():
		multimesh.set_instance_transform(stone_index, stone_spots[stone_index])
		var shade: float = random.randf_range(-COLOR_JITTER, COLOR_JITTER)
		multimesh.set_instance_color(stone_index, color.lightened(shade) if shade > 0.0 else color.darkened(-shade))
	return multimesh


## A low cylinder with few sides reads as a flat, slightly irregular stone.
func _create_stone_mesh() -> CylinderMesh:
	var material: StandardMaterial3D = StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	# Instance colors are picked in sRGB, like the colors in the inspector; without this the
	# engine reads them as linear and the brown comes out pale.
	material.vertex_color_is_srgb = true
	material.roughness = 0.95
	var stone_mesh: CylinderMesh = CylinderMesh.new()
	stone_mesh.top_radius = 0.9
	stone_mesh.bottom_radius = 1.0
	stone_mesh.height = STONE_THICKNESS
	stone_mesh.radial_segments = STONE_SIDES
	stone_mesh.rings = 1
	stone_mesh.material = material
	return stone_mesh


static func _flat(point: Vector3) -> Vector3:
	return Vector3(point.x, 0.0, point.z)
