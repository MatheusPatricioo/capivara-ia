class_name WorldSky
extends Node3D

## Day, night and weather in the world. The brain sends the time of day and the sky
## (Brain.sky_changed); between messages the sun moves on its own, so it never jumps.
## Until the first message the scene keeps the look it has in the editor.
## Lights that turn on at night find the sky by its group and follow daylight_changed.
## The sky shader (shaders/sky.gdshader) owns the colors; this script only sends it
## the state: daylight, sun direction, clouds, whether it is morning or afternoon and
## the moon (its phase, from the brain, and where its path puts it).

## How much daylight there is, from 0 (night) to 1 (full day). Sent on every repaint.
signal daylight_changed(daylight: float)

const GROUP_NAME: StringName = &"world_sky"

## Fraction of the day when the sun rises (06:00). It sets at 0.75 (18:00).
const SUNRISE_FRACTION: float = 0.25
## Seconds between two repaints of the sky: changing the sky every frame is expensive.
const REPAINT_SECONDS: float = 0.25
## Seconds for a new weather to settle in, so rain starts and clouds come little by little.
const WEATHER_TRANSITION_SECONDS: float = 8.0
const LOW_SUN_COLOR: Color = Color(1.0, 0.72, 0.5)
const MOON_COLOR: Color = Color(0.6, 0.7, 1.0)
## Moon light at full moon and at new moon: a full moon lights the night more.
const MOON_ENERGY: float = 0.25
const NEW_MOON_ENERGY: float = 0.1
## Ambient light color that takes over at night, so the world is dark but still visible.
const NIGHT_AMBIENT: Color = Color(0.25, 0.3, 0.45)
## How each sky looks: x = clouds (0 to 1), y = rain (0 to 1), z = fog density.
const WEATHER_LOOKS: Dictionary[StringName, Vector3] = {
	&"clear": Vector3(0.0, 0.0, 0.0),
	&"cloudy": Vector3(0.6, 0.0, 0.0),
	&"fog": Vector3(0.7, 0.0, 0.04),
	&"rain": Vector3(0.8, 0.45, 0.012),
	&"storm": Vector3(0.95, 1.0, 0.02),
}
const CLEAR_LOOK: Vector3 = Vector3(0.0, 0.0, 0.0)

@export var sun: DirectionalLight3D
@export var world_environment: WorldEnvironment
## How far the moon's path leans away from straight overhead. At 60 degrees she climbs
## no higher than 30, so the low clip cameras see her; she rises behind the game camera
## and sets in front of it, near dawn.
@export_range(0.0, 80.0) var moon_path_tilt_degrees: float = 60.0

## Full day until the brain says otherwise, like the editor look of the scene.
var current_daylight: float = 1.0
var _day_fraction: float = 0.5
var _day_length_seconds: float = 86400.0
var _follows_brain: bool = false
var _seconds_until_repaint: float = 0.0
var _weather_look: Vector3 = Vector3(-1.0, -1.0, -1.0)
var _weather_tween: Tween
var _overcast: float = 0.0
var _rain_strength: float = 0.0
var _fog_density: float = 0.0
var _sky_material: ShaderMaterial
## Full until the brain says otherwise.
var _moon_phase: float = 0.5
var _sun_energy: float
var _sun_yaw: float
var _rain: WorldRain


## Joins the group on entering the tree, before any _ready, so every light finds the sky.
func _enter_tree() -> void:
	add_to_group(GROUP_NAME)


func _ready() -> void:
	_sky_material = world_environment.environment.sky.sky_material as ShaderMaterial
	_sun_energy = sun.light_energy
	_sun_yaw = sun.rotation.y
	_rain = WorldRain.new()
	add_child(_rain)
	Brain.sky_changed.connect(_on_sky_changed)
	Brain.moon_changed.connect(_on_moon_changed)


func _process(delta: float) -> void:
	if not _follows_brain:
		return
	_day_fraction = fposmod(_day_fraction + delta / _day_length_seconds, 1.0)
	_seconds_until_repaint -= delta
	if _seconds_until_repaint <= 0.0:
		_seconds_until_repaint = REPAINT_SECONDS
		_paint()


func _on_sky_changed(day_fraction: float, day_length_seconds: float, weather: StringName) -> void:
	var is_first_message: bool = not _follows_brain
	_follows_brain = true
	_day_fraction = day_fraction
	_day_length_seconds = maxf(day_length_seconds, 1.0)
	_change_weather(WEATHER_LOOKS.get(weather, CLEAR_LOOK), is_first_message)
	_paint()


func _on_moon_changed(phase: float) -> void:
	_moon_phase = fposmod(phase, 1.0)
	_paint()


## The first message sets the weather at once; later changes settle in slowly.
func _change_weather(look: Vector3, instantly: bool) -> void:
	if look == _weather_look:
		return
	_weather_look = look
	if _weather_tween != null:
		_weather_tween.kill()
	if instantly:
		_overcast = look.x
		_rain_strength = look.y
		_fog_density = look.z
		return
	_weather_tween = create_tween().set_parallel()
	_weather_tween.tween_property(self, "_overcast", look.x, WEATHER_TRANSITION_SECONDS)
	_weather_tween.tween_property(self, "_rain_strength", look.y, WEATHER_TRANSITION_SECONDS)
	_weather_tween.tween_property(self, "_fog_density", look.z, WEATHER_TRANSITION_SECONDS)


func _paint() -> void:
	# 0 at sunrise, a quarter turn at noon, half a turn at sunset.
	var sun_angle: float = (_day_fraction - SUNRISE_FRACTION) * TAU
	var elevation: float = sin(sun_angle)
	current_daylight = smoothstep(0.0, 0.3, elevation)
	_place_light(sun_angle, elevation, current_daylight)
	_paint_sky(sun_angle, current_daylight)
	_rain.fall(_rain_strength)
	daylight_changed.emit(current_daylight)


## The same light is the sun by day and the moon by night, shining from where the sky
## shader draws each of them.
func _place_light(sun_angle: float, elevation: float, daylight: float) -> void:
	if elevation >= 0.0:
		sun.rotation = Vector3(-sun_angle, _sun_yaw, 0.0)
	else:
		# A light shines along its -Z: pointing -Z away from the moon brings her light down.
		sun.basis = Basis.looking_at(-_direction_toward_moon(sun_angle))
	var cloud_shade: float = 1.0 - 0.75 * _overcast
	var moon_energy: float = lerpf(NEW_MOON_ENERGY, MOON_ENERGY, _moon_lit_fraction())
	sun.light_energy = lerpf(moon_energy, _sun_energy, daylight) * cloud_shade
	var sun_color: Color = LOW_SUN_COLOR.lerp(Color.WHITE, smoothstep(0.0, 0.5, elevation))
	sun.light_color = MOON_COLOR.lerp(sun_color, daylight)


## Sends the state to the sky shader; the fog takes its color from the sky itself
## (fog_aerial_perspective in the scene), so it follows the shader's colors.
func _paint_sky(sun_angle: float, daylight: float) -> void:
	_sky_material.set_shader_parameter(&"daylight", daylight)
	_sky_material.set_shader_parameter(&"sun_direction", _direction_toward_sun(sun_angle))
	_sky_material.set_shader_parameter(&"overcast", _overcast)
	_sky_material.set_shader_parameter(&"dusk", 1.0 if _day_fraction >= 0.5 else 0.0)
	_sky_material.set_shader_parameter(&"moon_phase", _moon_phase)
	_sky_material.set_shader_parameter(&"moon_direction", _direction_toward_moon(sun_angle))
	var environment: Environment = world_environment.environment
	environment.ambient_light_color = NIGHT_AMBIENT
	environment.ambient_light_sky_contribution = lerpf(0.5, 1.0, daylight)
	environment.fog_enabled = _fog_density > 0.001
	environment.fog_density = _fog_density


## The light shines along its -Z axis, so +Z of the sun's rotation points toward the sun.
func _direction_toward_sun(sun_angle: float) -> Vector3:
	return Basis.from_euler(Vector3(-sun_angle, _sun_yaw, 0.0)).z


## Half a turn behind the sun, so she rises as it sets. The sun's path, (0, sin, cos)
## turned by its yaw, passes overhead; the moon's leans sideways by moon_path_tilt_degrees.
func _direction_toward_moon(sun_angle: float) -> Vector3:
	var moon_angle: float = sun_angle + PI
	var tilt: float = deg_to_rad(moon_path_tilt_degrees)
	var on_path := Vector3(
		-sin(moon_angle) * sin(tilt), sin(moon_angle) * cos(tilt), cos(moon_angle)
	)
	return on_path.rotated(Vector3.UP, _sun_yaw)


## How much of the moon's face is lit: 0 at new moon, 1 at full (as in the sky shader).
func _moon_lit_fraction() -> float:
	return 0.5 - 0.5 * cos(_moon_phase * TAU)
