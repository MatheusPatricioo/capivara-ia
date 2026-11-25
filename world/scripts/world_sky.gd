class_name WorldSky
extends Node3D

## Day, night and weather in the world. The brain sends the time of day and the sky
## (Brain.sky_changed); between messages the sun moves on its own, so it never jumps.
## Until the first message the scene keeps the look it has in the editor.

## Fraction of the day when the sun rises (06:00). It sets at 0.75 (18:00).
const SUNRISE_FRACTION: float = 0.25
## Seconds between two repaints of the sky: changing the sky every frame is expensive.
const REPAINT_SECONDS: float = 0.25
## Seconds for a new weather to settle in, so rain starts and clouds come little by little.
const WEATHER_TRANSITION_SECONDS: float = 8.0
const NIGHT_SKY_TOP: Color = Color(0.02, 0.03, 0.09)
const NIGHT_SKY_HORIZON: Color = Color(0.06, 0.08, 0.16)
const OVERCAST_SKY: Color = Color(0.5, 0.52, 0.56)
const TWILIGHT_HORIZON: Color = Color(0.95, 0.55, 0.35)
const LOW_SUN_COLOR: Color = Color(1.0, 0.72, 0.5)
const MOON_COLOR: Color = Color(0.6, 0.7, 1.0)
const MOON_ENERGY: float = 0.25
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

var _day_fraction: float = 0.5
var _day_length_seconds: float = 86400.0
var _follows_brain: bool = false
var _seconds_until_repaint: float = 0.0
var _weather_look: Vector3 = Vector3(-1.0, -1.0, -1.0)
var _weather_tween: Tween
var _overcast: float = 0.0
var _rain_strength: float = 0.0
var _fog_density: float = 0.0
var _sky_material: ProceduralSkyMaterial
var _day_sky_top: Color
var _day_sky_horizon: Color
var _day_ground_bottom: Color
var _sun_energy: float
var _sun_yaw: float
var _rain: WorldRain


func _ready() -> void:
	_sky_material = world_environment.environment.sky.sky_material as ProceduralSkyMaterial
	_day_sky_top = _sky_material.sky_top_color
	_day_sky_horizon = _sky_material.sky_horizon_color
	_day_ground_bottom = _sky_material.ground_bottom_color
	_sun_energy = sun.light_energy
	_sun_yaw = sun.rotation.y
	_rain = WorldRain.new()
	add_child(_rain)
	Brain.sky_changed.connect(_on_sky_changed)


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
	var daylight: float = smoothstep(0.0, 0.3, elevation)
	_place_light(sun_angle, elevation, daylight)
	_paint_sky(elevation, daylight)
	_rain.fall(_rain_strength)


## The same light is the sun by day and the moon by night (half a turn behind it).
func _place_light(sun_angle: float, elevation: float, daylight: float) -> void:
	var light_angle: float = sun_angle if elevation >= 0.0 else sun_angle - PI
	sun.rotation = Vector3(-light_angle, _sun_yaw, 0.0)
	var cloud_shade: float = 1.0 - 0.75 * _overcast
	sun.light_energy = lerpf(MOON_ENERGY, _sun_energy, daylight) * cloud_shade
	var sun_color: Color = LOW_SUN_COLOR.lerp(Color.WHITE, smoothstep(0.0, 0.5, elevation))
	sun.light_color = MOON_COLOR.lerp(sun_color, daylight)


func _paint_sky(elevation: float, daylight: float) -> void:
	var clear_top: Color = NIGHT_SKY_TOP.lerp(_day_sky_top, daylight)
	var clear_horizon: Color = NIGHT_SKY_HORIZON.lerp(_day_sky_horizon, daylight)
	# An orange horizon around sunrise and sunset, hidden by clouds.
	var twilight: float = (1.0 - clampf(absf(elevation) / 0.2, 0.0, 1.0)) * (1.0 - _overcast)
	clear_horizon = clear_horizon.lerp(TWILIGHT_HORIZON, twilight * 0.6)
	var clouds: Color = _dimmed(OVERCAST_SKY, lerpf(0.12, 1.0, daylight))
	_sky_material.sky_top_color = clear_top.lerp(clouds, _overcast)
	_sky_material.sky_horizon_color = clear_horizon.lerp(clouds, _overcast)
	_sky_material.ground_horizon_color = _sky_material.sky_horizon_color
	_sky_material.ground_bottom_color = _dimmed(_day_ground_bottom, lerpf(0.2, 1.0, daylight))
	var environment: Environment = world_environment.environment
	environment.ambient_light_color = NIGHT_AMBIENT
	environment.ambient_light_sky_contribution = lerpf(0.5, 1.0, daylight)
	environment.fog_enabled = _fog_density > 0.001
	environment.fog_density = _fog_density
	environment.fog_light_color = _sky_material.sky_horizon_color


## Darker color with the same alpha (Color * float would also scale the alpha).
func _dimmed(color: Color, brightness: float) -> Color:
	return Color(color.r * brightness, color.g * brightness, color.b * brightness, color.a)
