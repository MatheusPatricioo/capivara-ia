@tool
class_name ScatterPatch
extends Node3D

## Scatters many copies of a few models (flowers, grass, pebbles, mushrooms, even far-away
## trees) inside an ellipse centered on this node. Copies are drawn with MultiMeshInstance3D:
## one draw call per mesh instead of one node per copy, so hundreds of flowers stay cheap.
## Copies have no collision: the capybara walks over them and the navigation ignores them.
## The random seed is fixed, so the patch looks the same every time the world opens.

## Copies tried per wanted copy before giving up, when min_distance leaves no room.
const MAX_ATTEMPTS_PER_COPY: int = 20

## Models (.glb) to scatter; each copy picks one of them at random.
@export var models: Array[PackedScene] = []:
	set(value):
		models = value
		_rebuild()

## How many copies to place.
@export var count: int = 10:
	set(value):
		count = maxi(value, 0)
		_rebuild()

## Half-size of the ellipse in meters: x is the local X axis, y is the local Z axis.
@export var extents: Vector2 = Vector2(1.0, 1.0):
	set(value):
		extents = value
		_rebuild()

## 0 fills the whole ellipse; 0.8 leaves the inner 80% empty, making a ring (around the pond).
@export_range(0.0, 0.95) var inner_ratio: float = 0.0:
	set(value):
		inner_ratio = value
		_rebuild()

@export var min_scale: float = 0.8:
	set(value):
		min_scale = maxf(value, 0.01)
		_rebuild()

@export var max_scale: float = 1.2:
	set(value):
		max_scale = maxf(value, 0.01)
		_rebuild()

## Smallest gap between two copies, in meters. Use it for trees so trunks never overlap.
@export var min_distance: float = 0.0:
	set(value):
		min_distance = maxf(value, 0.0)
		_rebuild()

## Change it to get another arrangement with the same settings.
@export var random_seed: int = 1:
	set(value):
		random_seed = value
		_rebuild()

## Areas of the world where no copy is placed, like a stream. Each Rect2 uses world
## coordinates seen from above: position is (x, z), size is (width in x, depth in z).
@export var keep_out_areas: Array[Rect2] = []:
	set(value):
		keep_out_areas = value
		_rebuild()

## Off for small plants: their shadow is barely visible but costs a draw call per
## shadow split, and with the local model sharing the GPU every draw call counts.
@export var casts_shadows: bool = true:
	set(value):
		casts_shadows = value
		_rebuild()

var _drawers: Array[MultiMeshInstance3D] = []


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	_clear_drawers()
	var usable_models: Array[PackedScene] = []
	for model: PackedScene in models:
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
	for copy_position: Vector3 in _pick_positions(random):
		var model_index: int = random.randi_range(0, usable_models.size() - 1)
		var copy_scale: float = random.randf_range(min_scale, max_scale)
		var copy_basis: Basis = Basis(Vector3.UP, random.randf_range(0.0, TAU)).scaled(Vector3.ONE * copy_scale)
		copies_per_model[model_index].append(Transform3D(copy_basis, copy_position))
	for model_index: int in usable_models.size():
		_drawers.append_array(MultiMeshCopies.add_to(self, usable_models[model_index], copies_per_model[model_index]))
	if not casts_shadows:
		for drawer: MultiMeshInstance3D in _drawers:
			drawer.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _pick_positions(random: RandomNumberGenerator) -> Array[Vector3]:
	var positions: Array[Vector3] = []
	var attempts_left: int = count * MAX_ATTEMPTS_PER_COPY
	while positions.size() < count and attempts_left > 0:
		attempts_left -= 1
		var candidate: Vector3 = _random_point_in_ellipse(random)
		if _is_far_from_all(candidate, positions) and not _is_kept_out(candidate):
			positions.append(candidate)
	return positions


func _random_point_in_ellipse(random: RandomNumberGenerator) -> Vector3:
	var angle: float = random.randf_range(0.0, TAU)
	# The square root spreads copies evenly; without it they would crowd the center.
	var distance: float = sqrt(random.randf_range(inner_ratio * inner_ratio, 1.0))
	return Vector3(cos(angle) * distance * extents.x, 0.0, sin(angle) * distance * extents.y)


func _is_kept_out(local_point: Vector3) -> bool:
	var world_point: Vector3 = to_global(local_point)
	for keep_out_area: Rect2 in keep_out_areas:
		if keep_out_area.has_point(Vector2(world_point.x, world_point.z)):
			return true
	return false


func _is_far_from_all(candidate: Vector3, positions: Array[Vector3]) -> bool:
	for placed_position: Vector3 in positions:
		if placed_position.distance_to(candidate) < min_distance:
			return false
	return true


func _clear_drawers() -> void:
	for drawer: MultiMeshInstance3D in _drawers:
		drawer.queue_free()
	_drawers.clear()

