class_name MultiMeshCopies
extends RefCounted

## Draws many copies of one model (.glb) with MultiMeshInstance3D: one draw call per mesh
## instead of one node per copy. Used by ScatterPatch and FlowerBed.


## Adds one MultiMeshInstance3D per mesh in the model (a tree may have trunk and leaves apart)
## as children of parent, and returns them so the caller can clear them later.
static func add_to(parent: Node3D, model: PackedScene, copy_transforms: Array[Transform3D]) -> Array[MultiMeshInstance3D]:
	var drawers: Array[MultiMeshInstance3D] = []
	if copy_transforms.is_empty():
		return drawers
	var probe: Node3D = model.instantiate() as Node3D
	if probe == null:
		return drawers
	for mesh_node: Node in probe.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance: MeshInstance3D = mesh_node as MeshInstance3D
		if mesh_instance.mesh == null:
			continue
		var drawer: MultiMeshInstance3D = MultiMeshInstance3D.new()
		drawer.multimesh = _build_multimesh(mesh_instance.mesh, _transform_relative_to(mesh_instance, probe), copy_transforms)
		parent.add_child(drawer)
		drawers.append(drawer)
	probe.free()
	return drawers


static func _build_multimesh(mesh: Mesh, mesh_offset: Transform3D, copy_transforms: Array[Transform3D]) -> MultiMesh:
	var multimesh: MultiMesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.mesh = mesh
	multimesh.instance_count = copy_transforms.size()
	for copy_index: int in copy_transforms.size():
		# The offset keeps each mesh where it sits inside the model.
		multimesh.set_instance_transform(copy_index, copy_transforms[copy_index] * mesh_offset)
	return multimesh


## The probe is not inside the scene tree, so global_transform is unavailable:
## walk up the parents and combine the local transforms by hand.
static func _transform_relative_to(node: Node3D, root: Node3D) -> Transform3D:
	var relative: Transform3D = Transform3D.IDENTITY
	var current: Node = node
	while current != root and current is Node3D:
		relative = (current as Node3D).transform * relative
		current = current.get_parent()
	return relative
