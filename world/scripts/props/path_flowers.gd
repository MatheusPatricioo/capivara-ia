@tool
class_name PathFlowers
extends Node3D

## Flowers along both edges of the SteppingStones path it is a child of, in small clumps
## with gaps between them, like a border planted by hand rather than a straight hedge.
## Flowers are MultiMesh copies with no collision; the seed is fixed, so the border looks
## the same every time the world opens.

## Each flower picks one of these models at random.
@export var models: Array[PackedScene] = []:
	set(value):
		models = value
		_rebuild()

## Meters between two clumps along the path, on each side.
@export var spacing: float = 0.45:
	set(value):
		spacing = maxf(value, 0.05)
		_rebuild()

## Distance from the path line to the clumps, in meters: a bit past the stones.
@export var distance: float = 0.42:
	set(value):
		distance = maxf(value, 0.0)
		_rebuild()

@export var min_flowers_per_clump: int = 1:
	set(value):
		min_flowers_per_clump = maxi(value, 1)
		_rebuild()

@export var max_flowers_per_clump: int = 3:
	set(value):
		max_flowers_per_clump = maxi(value, 1)
		_rebuild()

## How far a flower may sit from the center of its clump, in meters.
@export var clump_radius: float = 0.1:
	set(value):
		clump_radius = maxf(value, 0.0)
		_rebuild()

## Chance of leaving a spot empty, so the border breathes.
@export_range(0.0, 0.9) var gap_chance: float = 0.25:
	set(value):
		gap_chance = value
		_rebuild()

## Meters left bare at each end, so the door and the pond edge stay clear.
@export var bare_ends: float = 0.6:
	set(value):
		bare_ends = maxf(value, 0.0)
		_rebuild()

@export var min_scale: float = 0.7:
	set(value):
		min_scale = maxf(value, 0.01)
		_rebuild()

@export var max_scale: float = 1.0:
	set(value):
		max_scale = maxf(value, 0.01)
		_rebuild()

@export var random_seed: int = 1:
	set(value):
		random_seed = value
		_rebuild()

var _drawers: Array[MultiMeshInstance3D] = []


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	_clear_drawers()
	var path: SteppingStones = get_parent() as SteppingStones
	if path == null or models.is_empty():
		return
	var random: RandomNumberGenerator = RandomNumberGenerator.new()
	random.seed = random_seed
	var copies_per_model: Array[Array] = []
	for model_index: int in models.size():
		var model_copies: Array[Transform3D] = []
		copies_per_model.append(model_copies)
	var frames: Array[Transform3D] = PathSampler.frames_along(path.path_points, spacing)
	var bare_spots: int = ceili(bare_ends / spacing)
	for frame_index: int in range(bare_spots, frames.size() - bare_spots):
		for side: float in [-1.0, 1.0]:
			if random.randf() < gap_chance:
				continue
			var clump_center: Vector3 = frames[frame_index].origin + frames[frame_index].basis.x * side * distance
			for flower_index: int in random.randi_range(min_flowers_per_clump, max_flowers_per_clump):
				var model_index: int = random.randi_range(0, models.size() - 1)
				copies_per_model[model_index].append(_flower_transform(clump_center, random))
	for model_index: int in models.size():
		if models[model_index] != null:
			_drawers.append_array(MultiMeshCopies.add_to(self, models[model_index], copies_per_model[model_index]))
	for drawer: MultiMeshInstance3D in _drawers:
		# Small flowers: their shadow is barely visible and costs a draw call per split.
		drawer.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _flower_transform(clump_center: Vector3, random: RandomNumberGenerator) -> Transform3D:
	var angle: float = random.randf_range(0.0, TAU)
	var offset: Vector3 = Vector3(cos(angle), 0.0, sin(angle)) * random.randf_range(0.0, clump_radius)
	var flower_scale: float = random.randf_range(min_scale, max_scale)
	var flower_basis: Basis = Basis(Vector3.UP, random.randf_range(0.0, TAU)).scaled(Vector3.ONE * flower_scale)
	return Transform3D(flower_basis, clump_center + offset)


func _clear_drawers() -> void:
	for drawer: MultiMeshInstance3D in _drawers:
		drawer.queue_free()
	_drawers.clear()
