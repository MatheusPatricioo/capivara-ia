class_name ClickableProp
extends StaticBody3D

## A piece of furniture the player can click. It re-emits the click of its ClickArea child
## from the scene root, so the world scene connects to the root (Workspace/Desk), never to
## the inner ClickArea: the editor only saves connections that start at nodes the world
## scene owns, and silently drops the ones that start inside an instanced scene.

signal clicked

@onready var _click_area: ClickableArea = $ClickArea


func _ready() -> void:
	_click_area.clicked.connect(clicked.emit)
