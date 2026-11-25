class_name PathSampler
extends RefCounted

## Walks a path made of points (a polyline seen from above) and returns a spot every
## spacing meters. Used by SteppingStones and PathFlowers, so both follow the same line.
##
## Each spot is a Transform3D: origin is the point on the line, basis.x points to the
## right side of the path, basis.z points forward. Point heights are ignored.


static func frames_along(points: PackedVector3Array, spacing: float, start_distance: float = 0.0) -> Array[Transform3D]:
	var frames: Array[Transform3D] = []
	if points.size() < 2 or spacing <= 0.0:
		return frames
	var distance_to_next_spot: float = start_distance
	for segment_index: int in points.size() - 1:
		var segment_start: Vector3 = _flat(points[segment_index])
		var segment_end: Vector3 = _flat(points[segment_index + 1])
		var segment_length: float = segment_start.distance_to(segment_end)
		if segment_length <= 0.0:
			continue
		var direction: Vector3 = (segment_end - segment_start) / segment_length
		var side: Vector3 = Vector3(-direction.z, 0.0, direction.x)
		var walked: float = distance_to_next_spot
		while walked <= segment_length:
			frames.append(Transform3D(Basis(side, Vector3.UP, direction), segment_start + direction * walked))
			walked += spacing
		distance_to_next_spot = walked - segment_length
	return frames


static func _flat(point: Vector3) -> Vector3:
	return Vector3(point.x, 0.0, point.z)
