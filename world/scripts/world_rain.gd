class_name WorldRain
extends GPUParticles3D

## Rain over the whole world: thin falling streaks, built in code. It starts dry; the sky
## turns it on with fall(). The brain decides the weather, this only shows it.

const DROP_COLOR: Color = Color(0.75, 0.82, 0.95, 0.45)
const DROP_SIZE: Vector2 = Vector2(0.015, 0.45)
const FALL_SPEED_MIN: float = 11.0
const FALL_SPEED_MAX: float = 14.0
const DROP_LIFETIME_SECONDS: float = 1.3

## Half the width of the rainy area, in meters (the ground is 34 x 34).
@export var area_half_size: float = 16.0
## Height the drops start from.
@export var start_height: float = 12.0
## Drops at the heaviest rain (a storm). Light rain uses part of them.
@export var max_drops: int = 5000


func _ready() -> void:
	position = Vector3(0.0, start_height, 0.0)
	amount = max_drops
	lifetime = DROP_LIFETIME_SECONDS
	emitting = false
	# The particles live far from this node: without a big box, Godot would cull them.
	visibility_aabb = AABB(
		Vector3(-area_half_size, -start_height - 2.0, -area_half_size),
		Vector3(area_half_size * 2.0, start_height + 4.0, area_half_size * 2.0)
	)
	process_material = _falling_motion()
	draw_pass_1 = _drop_mesh()


## Strength from 0 (dry) to 1 (storm).
func fall(strength: float) -> void:
	emitting = strength > 0.0
	amount_ratio = clampf(strength, 0.0, 1.0)


func _falling_motion() -> ParticleProcessMaterial:
	var motion: ParticleProcessMaterial = ParticleProcessMaterial.new()
	motion.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	motion.emission_box_extents = Vector3(area_half_size, 0.5, area_half_size)
	motion.direction = Vector3.DOWN
	motion.spread = 3.0
	motion.initial_velocity_min = FALL_SPEED_MIN
	motion.initial_velocity_max = FALL_SPEED_MAX
	motion.gravity = Vector3(0.0, -9.8, 0.0)
	return motion


## A thin vertical quad that always faces the camera sideways, like a streak of water.
func _drop_mesh() -> QuadMesh:
	var look: StandardMaterial3D = StandardMaterial3D.new()
	look.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	look.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	look.albedo_color = DROP_COLOR
	look.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	look.billboard_keep_scale = true
	var drop: QuadMesh = QuadMesh.new()
	drop.size = DROP_SIZE
	drop.material = look
	return drop
