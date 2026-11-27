class_name NightLight
extends OmniLight3D

## A light that turns on as the sky gets dark (street lamps, the lamp on her desk). It
## follows WorldSky.daylight_changed: off by day, full at night, fading in at dusk.
## Optionally a glowing material (the glass of a lantern) fades together with the light.

## Daylight below which the light starts to turn on, so it is already on at dusk.
const DUSK_DAYLIGHT: float = 0.6

@export var night_energy: float = 1.5
@export var glow_material: StandardMaterial3D
@export var night_glow_energy: float = 2.0


func _ready() -> void:
	var sky: WorldSky = get_tree().get_first_node_in_group(WorldSky.GROUP_NAME) as WorldSky
	if sky == null:
		push_warning("NightLight %s found no WorldSky: it stays off" % name)
		_shine(1.0)
		return
	sky.daylight_changed.connect(_shine)
	_shine(sky.current_daylight)


func _shine(daylight: float) -> void:
	var darkness: float = 1.0 - smoothstep(0.0, DUSK_DAYLIGHT, daylight)
	light_energy = night_energy * darkness
	visible = darkness > 0.01
	if glow_material != null:
		glow_material.emission_energy_multiplier = night_glow_energy * darkness
