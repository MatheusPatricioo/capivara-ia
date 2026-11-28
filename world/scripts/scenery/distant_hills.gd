@tool
class_name DistantHills
extends MeshInstance3D

## Rings of low poly hills far around the world, over a wide ground, so the edge of the
## floor meets the sky with depth instead of a flat band. The mesh is built in code
## (one draw call for everything); press "Rebuild hills" after changing a ring.

## Rough, faceted ridges: each ring is cut into this many slices around the circle.
@export_range(12, 256) var segments: int = 72
@export var rings: Array[HillRing] = []
## The wide ground starts under the floor's edge and runs to here.
@export var ground_inner_radius: float = 16.5
@export var ground_outer_radius: float = 140.0
## Below the floor, so the two never fight over the same pixels.
@export var ground_height: float = -0.25
@export var ground_color: Color = Color(0.33, 0.5, 0.3)
## Changing the seed gives another shape of ridges.
@export var noise_seed: int = 7
## How often the ridge goes up and down: higher values give more, narrower peaks.
@export var noise_frequency: float = 0.06
@export_tool_button("Rebuild hills") var rebuild_action: Callable = build


func _ready() -> void:
	build()


func build() -> void:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	# No shared smoothing: every triangle keeps its own normal, the low poly look.
	surface.set_smooth_group(-1)
	_add_ground(surface)
	var noise := FastNoiseLite.new()
	noise.seed = noise_seed
	noise.frequency = noise_frequency
	for ring_index: int in rings.size():
		if rings[ring_index] != null:
			_add_ring(surface, rings[ring_index], noise, ring_index)
	surface.generate_normals()
	mesh = surface.commit()
	material_override = _flat_material()
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


## A flat ring of ground from under the floor's edge out to the far hills.
func _add_ground(surface: SurfaceTool) -> void:
	surface.set_color(ground_color)
	for segment_index: int in segments:
		var angle_start: float = TAU * segment_index / segments
		var angle_end: float = TAU * (segment_index + 1) / segments
		var inner_start: Vector3 = _point(angle_start, ground_inner_radius, ground_height)
		var inner_end: Vector3 = _point(angle_end, ground_inner_radius, ground_height)
		var outer_start: Vector3 = _point(angle_start, ground_outer_radius, ground_height)
		var outer_end: Vector3 = _point(angle_end, ground_outer_radius, ground_height)
		_add_quad(surface, inner_start, inner_end, outer_end, outer_start)


## A slope that rises outward from the foot to a bumpy ridge, facing the world's center.
func _add_ring(surface: SurfaceTool, ring: HillRing, noise: FastNoiseLite, ring_index: int) -> void:
	surface.set_color(ring.color)
	var ridge_radius: float = ring.inner_radius + ring.depth
	for segment_index: int in segments:
		var angle_start: float = TAU * segment_index / segments
		var angle_end: float = TAU * (segment_index + 1) / segments
		var foot_start: Vector3 = _point(angle_start, ring.inner_radius, ground_height)
		var foot_end: Vector3 = _point(angle_end, ring.inner_radius, ground_height)
		var ridge_start: Vector3 = _point(angle_start, ridge_radius, _ridge_height(ring, noise, ring_index, angle_start))
		var ridge_end: Vector3 = _point(angle_end, ridge_radius, _ridge_height(ring, noise, ring_index, angle_end))
		_add_quad(surface, foot_start, foot_end, ridge_end, ridge_start)


## Samples the noise around a circle, so the ridge closes on itself without a seam.
## Each ring reads its own slice of the noise, so the rings do not share their peaks.
func _ridge_height(ring: HillRing, noise: FastNoiseLite, ring_index: int, angle: float) -> float:
	var circle_radius: float = ring.inner_radius + ring.depth
	var sample: float = noise.get_noise_3d(cos(angle) * circle_radius, sin(angle) * circle_radius, ring_index * 100.0)
	return lerpf(ring.min_height, ring.max_height, (sample + 1.0) * 0.5)


## Two triangles in clockwise order (Godot's front face) as seen from the world's center:
## near_start and near_end are the inner edge, far_end and far_start the outer one.
func _add_quad(surface: SurfaceTool, near_start: Vector3, near_end: Vector3, far_end: Vector3, far_start: Vector3) -> void:
	for corner: Vector3 in [near_start, far_start, far_end, near_start, far_end, near_end]:
		surface.add_vertex(corner)


func _point(angle: float, radius: float, height: float) -> Vector3:
	return Vector3(cos(angle) * radius, height, sin(angle) * radius)


func _flat_material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	# The ring colors are picked in the Inspector, in sRGB like every other color there.
	material.vertex_color_is_srgb = true
	material.roughness = 1.0
	return material
