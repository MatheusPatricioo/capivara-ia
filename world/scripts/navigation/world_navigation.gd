class_name WorldNavigation
extends NavigationRegion3D

## Bakes the navigation mesh when the world starts, so it always matches the current props
## without a manual "Bake NavigationMesh" click in the editor.


func _ready() -> void:
	# Deferred so every prop has finished its own _ready (rocks and bushes create their
	# collisions there) before the scene is parsed. "true" bakes on a background thread.
	bake_navigation_mesh.call_deferred(true)
