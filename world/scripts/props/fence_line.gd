@tool
class_name FenceLine
extends Node3D

## Repeats a fence model along the local X axis, centered on this node.
## The piece length is measured from the model itself, so any fence from the kit fits
## without hand-tuned spacing.

## Fence piece (.glb) repeated along the line.
@export var piece_model: PackedScene:
	set(value):
		piece_model = value
		_rebuild()

## Total length of the line in meters, rounded to a whole number of pieces.
@export var length: float = 6.0:
	set(value):
		length = maxf(value, 0.0)
		_rebuild()

## Uniform scale applied to every piece.
@export var piece_scale: float = 2.0:
	set(value):
		piece_scale = maxf(value, 0.01)
		_rebuild()

var _pieces: Array[Node3D] = []


func _ready() -> void:
	_rebuild()


func _rebuild() -> void:
	if not is_node_ready():
		return
	_clear_pieces()
	if piece_model == null:
		return
	var piece_bounds: AABB = _measure_piece_bounds()
	if piece_bounds.size.is_zero_approx():
		return
	var runs_along_z: bool = piece_bounds.size.z > piece_bounds.size.x
	var piece_basis: Basis = Basis(Vector3.UP, PI / 2.0) if runs_along_z else Basis.IDENTITY
	var piece_length: float = maxf(piece_bounds.size.x, piece_bounds.size.z) * piece_scale
	var piece_count: int = maxi(roundi(length / piece_length), 1)
	var center_offset: Vector3 = piece_basis * piece_bounds.get_center() * piece_scale
	center_offset.y = 0.0
	var first_slot_x: float = -(piece_count - 1) * piece_length / 2.0
	for piece_index: int in piece_count:
		var slot_position: Vector3 = Vector3(first_slot_x + piece_index * piece_length, 0.0, 0.0)
		_add_piece(piece_basis, slot_position - center_offset)


func _add_piece(piece_basis: Basis, piece_position: Vector3) -> void:
	var piece: Node3D = piece_model.instantiate() as Node3D
	if piece == null:
		return
	piece.basis = piece_basis
	piece.scale = Vector3.ONE * piece_scale
	piece.position = piece_position
	add_child(piece)
	_pieces.append(piece)


func _clear_pieces() -> void:
	for piece: Node3D in _pieces:
		piece.queue_free()
	_pieces.clear()


## Bounding box of the model in its own space, at scale 1.
func _measure_piece_bounds() -> AABB:
	var probe: Node3D = piece_model.instantiate() as Node3D
	if probe == null:
		return AABB()
	var bounds: AABB = AABB()
	var has_bounds: bool = false
	for mesh_node: Node in probe.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance: MeshInstance3D = mesh_node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		var mesh_bounds: AABB = _transform_relative_to(mesh_instance, probe) * mesh_instance.mesh.get_aabb()
		bounds = bounds.merge(mesh_bounds) if has_bounds else mesh_bounds
		has_bounds = true
	probe.free()
	return bounds


## The probe is not inside the scene tree, so global_transform is unavailable:
## walk up the parents and combine the local transforms by hand.
func _transform_relative_to(node: Node3D, root: Node3D) -> Transform3D:
	var relative: Transform3D = Transform3D.IDENTITY
	var current: Node = node
	while current != root and current is Node3D:
		relative = (current as Node3D).transform * relative
		current = current.get_parent()
	return relative
