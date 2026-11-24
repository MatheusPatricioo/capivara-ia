class_name ChalkboardDisplay
extends Node3D

## Shows the capybara's newest drawings on the chalkboard. A ChalkboardGallery paints the PNG
## files inside a SubViewport (an off-screen 2D screen), and its texture is shown on a quad
## over the slate. A drawing she just made is drawn stroke by stroke (ChalkboardNewDrawings).

## Canvas resolution in pixels. Keep the same proportion as surface_size (1.6 : 1).
@export var canvas_size: Vector2i = Vector2i(960, 600)
## Size of the painted area in meters, matching the slate of the chalkboard model.
@export var surface_size: Vector2 = Vector2(1.6, 1.0)
## Where she stands to draw: a new drawing waits for her arrival there.
@export var arrival_point_path: NodePath = ^"../ArrivalPoint"

var _gallery: ChalkboardGallery = ChalkboardGallery.new()


func _ready() -> void:
	var viewport: SubViewport = _create_viewport()
	add_child(viewport)
	add_child(_create_screen(viewport.get_texture()))
	add_child(ChalkboardNewDrawings.new(_gallery, get_node_or_null(arrival_point_path) as InteractionPoint))


func _create_viewport() -> SubViewport:
	var viewport: SubViewport = SubViewport.new()
	viewport.size = canvas_size
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_gallery.size = Vector2(canvas_size)
	viewport.add_child(_gallery)
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
