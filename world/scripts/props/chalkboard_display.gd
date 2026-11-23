class_name ChalkboardDisplay
extends Node3D

## Shows the brain's latest drawings on the chalkboard. A ChalkboardCanvas paints them inside
## a SubViewport (an off-screen 2D screen), and its texture is shown on a quad over the slate.

## Canvas resolution in pixels. Keep the same proportion as surface_size (1.6 : 1).
@export var canvas_size: Vector2i = Vector2i(960, 600)
## Size of the painted area in meters, matching the slate of the chalkboard model.
@export var surface_size: Vector2 = Vector2(1.6, 1.0)

var _canvas: ChalkboardCanvas = ChalkboardCanvas.new()


func _ready() -> void:
	var viewport: SubViewport = _create_viewport()
	add_child(viewport)
	add_child(_create_screen(viewport.get_texture()))
	Brain.chalkboard_changed.connect(_canvas.show_drawings)


func _create_viewport() -> SubViewport:
	var viewport: SubViewport = SubViewport.new()
	viewport.size = canvas_size
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_canvas.size = Vector2(canvas_size)
	viewport.add_child(_canvas)
	return viewport


func _create_screen(texture: Texture2D) -> MeshInstance3D:
	var quad: QuadMesh = QuadMesh.new()
	quad.size = surface_size
	var material: StandardMaterial3D = StandardMaterial3D.new()
	material.albedo_texture = texture
	material.roughness = 0.9
	var screen: MeshInstance3D = MeshInstance3D.new()
	screen.mesh = quad
	screen.material_override = material
	return screen
