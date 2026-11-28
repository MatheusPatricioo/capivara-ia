shader_type sky;

// The world's sky: day, night, dawn and dusk gradients and the sun.
// Colors and intensities are tuned in the Inspector; the "state" group is written
// by WorldSky on every repaint, so editing it by hand has no lasting effect.

group_uniforms state;
// How much daylight there is, from 0 (night) to 1 (full day).
uniform float daylight : hint_range(0.0, 1.0) = 1.0;
// Direction from the world toward the sun (it points down at night).
uniform vec3 sun_direction = vec3(0.0, 1.0, 0.0);
// How much the clouds cover the sky, from 0 (clear) to 1 (overcast).
uniform float overcast : hint_range(0.0, 1.0) = 0.0;
// 0 in the morning (dawn colors), 1 in the afternoon (dusk colors).
uniform float dusk : hint_range(0.0, 1.0) = 0.0;

group_uniforms day;
uniform vec3 day_top_color : source_color = vec3(0.32, 0.58, 0.9);
uniform vec3 day_horizon_color : source_color = vec3(0.72, 0.86, 0.96);

group_uniforms night;
uniform vec3 night_top_color : source_color = vec3(0.02, 0.03, 0.09);
uniform vec3 night_horizon_color : source_color = vec3(0.06, 0.08, 0.16);

group_uniforms twilight;
uniform vec3 dawn_color : source_color = vec3(1.0, 0.62, 0.58);
uniform vec3 dusk_color : source_color = vec3(0.98, 0.52, 0.3);
uniform float twilight_strength : hint_range(0.0, 1.0) = 0.7;
// How high above the horizon the warm band climbs.
uniform float twilight_height : hint_range(0.05, 1.0) = 0.35;
// How far below and above the horizon the sun still paints the band.
uniform float twilight_sun_window : hint_range(0.05, 0.6) = 0.25;
// Warmth left on the side of the sky away from the sun.
uniform float twilight_far_side : hint_range(0.0, 1.0) = 0.3;

group_uniforms sun;
uniform vec3 sun_color : source_color = vec3(1.0, 0.97, 0.88);
uniform vec3 sun_low_color : source_color = vec3(1.0, 0.6, 0.35);
// Radius of the sun disc, as an angle in radians.
uniform float sun_size : hint_range(0.005, 0.2) = 0.045;
// Above 1 the disc goes past white and the glow effect makes it shine.
uniform float sun_intensity : hint_range(0.0, 16.0) = 4.0;
uniform float sun_halo_strength : hint_range(0.0, 2.0) = 0.35;
// Higher values keep the halo closer to the disc.
uniform float sun_halo_tightness : hint_range(1.0, 256.0) = 24.0;

group_uniforms clouds;
uniform vec3 overcast_color : source_color = vec3(0.5, 0.52, 0.56);
// Brightness of the overcast sky at night, relative to the day.
uniform float overcast_night_brightness : hint_range(0.0, 1.0) = 0.12;

group_uniforms stars;
uniform vec3 star_color : source_color = vec3(0.85, 0.9, 1.0);
// Some stars lean toward this color, so the sky is not all the same white.
uniform vec3 star_warm_color : source_color = vec3(1.0, 0.86, 0.66);
// Above 1 the brightest stars go past white and the glow effect makes them shine.
uniform float star_intensity : hint_range(0.0, 8.0) = 2.0;
// How many grid cells fit across the sky: more cells, smaller and closer stars.
// The far layer stays put; the near layer, fewer and bigger stars, slides a little as
// the camera moves (parallax), as if it hung at star_near_distance meters.
uniform float star_density : hint_range(10.0, 200.0) = 70.0;
uniform float star_near_density : hint_range(10.0, 200.0) = 30.0;
uniform float star_near_distance : hint_range(5.0, 500.0) = 40.0;
// Brightness of the far layer next to the near one: faint stars read as far away.
uniform float star_far_brightness : hint_range(0.0, 1.0) = 0.6;
// Cloud cover (overcast) at which the stars are all hidden: a rainy sky shows none.
uniform float star_cloud_cutoff : hint_range(0.01, 1.0) = 0.7;
// Fraction of the cells that hold a star.
uniform float star_amount : hint_range(0.0, 1.0) = 0.35;
// Star radius as a fraction of a cell, for the smallest and the largest star.
uniform float star_size_min : hint_range(0.01, 0.3) = 0.08;
uniform float star_size_max : hint_range(0.01, 0.3) = 0.2;
uniform float twinkle_speed : hint_range(0.0, 10.0) = 1.5;
// How much a star dims at the low point of its twinkle.
uniform float twinkle_strength : hint_range(0.0, 1.0) = 0.45;
// Sun heights where the stars start to fade in (fade_start) and are all gone (fade_end):
// they show before the sun is fully down and leave as dawn comes.
uniform float star_fade_start : hint_range(-1.0, 0.0) = -0.2;
uniform float star_fade_end : hint_range(-0.5, 0.5) = 0.03;
// How high above the horizon the stars reach full brightness. Small, since the game
// camera sees only a thin band of sky above the hills.
uniform float star_horizon_fade : hint_range(0.001, 0.5) = 0.04;

group_uniforms moon;
// Both set by world_sky.gd: the phase comes from the brain (0 new, 0.25 first quarter,
// 0.5 full, 0.75 last quarter) and the direction from the moon's path across the night.
uniform float moon_phase : hint_range(0.0, 1.0) = 0.5;
uniform vec3 moon_direction = vec3(0.0, 0.5, -0.87);
uniform vec3 moon_color : source_color = vec3(0.96, 0.94, 0.86);
// The unlit side is not black: sunlight bounced off the Earth (earthshine) shows it faintly.
uniform vec3 moon_dark_color : source_color = vec3(0.07, 0.08, 0.13);
// Radius in radians; the real moon is far smaller (0.0045), this one is cozy-sized.
uniform float moon_size : hint_range(0.01, 0.2) = 0.06;
uniform float moon_intensity : hint_range(0.0, 4.0) = 0.85;
// How much darker the round "seas" (maria) on its face are.
uniform float moon_maria_strength : hint_range(0.0, 1.0) = 0.22;
uniform float moon_glow_strength : hint_range(0.0, 1.0) = 0.15;
// Glow radius, in moon radii.
uniform float moon_glow_size : hint_range(1.0, 12.0) = 5.0;
// Cloud cover (overcast) at which the moon is all hidden; just past rain (0.8) it still
// glows faintly through.
uniform float moon_cloud_cutoff : hint_range(0.01, 1.0) = 0.9;

group_uniforms lighting;
// How strongly the sky lights the world, apart from how it looks: a vivid sky stays
// vivid while the light it casts is softer and less colored.
uniform float sky_light_strength : hint_range(0.0, 2.0) = 0.7;
// 0 lights the world with a gray of the same brightness, 1 with the sky's full color.
uniform float sky_light_saturation : hint_range(0.0, 1.0) = 0.4;
// Brightness of the lower half of the sky in the lighting snapshot (radiance): the
// world is lit from below by it, so a full-bright lower sky washes everything out.
uniform float lower_sky_light : hint_range(0.0, 1.0) = 0.3;
// How far below the horizon that darkening takes to settle in.
uniform float lower_sky_blend : hint_range(0.001, 1.0) = 0.3;

group_uniforms;


vec3 base_gradient(float upward) {
	// The square root keeps the pale horizon band thin and the top color wide.
	float top_blend = sqrt(upward);
	vec3 day_sky = mix(day_horizon_color, day_top_color, top_blend);
	vec3 night_sky = mix(night_horizon_color, night_top_color, top_blend);
	return mix(night_sky, day_sky, daylight);
}

// How much of the warm band shows: the sun near the horizon, the eye low and toward the sun.
float twilight_amount(vec3 eye_direction, float upward) {
	float sun_near_horizon = 1.0 - smoothstep(0.0, twilight_sun_window, abs(sun_direction.y));
	float low_in_sky = 1.0 - smoothstep(0.0, twilight_height, upward);
	// Guarded so a sun straight up (no horizontal direction) does not divide by zero.
	vec2 sun_flat = sun_direction.xz / max(length(sun_direction.xz), 0.0001);
	float toward_sun = dot(eye_direction.xz, sun_flat) * 0.5 + 0.5;
	float side = mix(twilight_far_side, 1.0, toward_sun * toward_sun);
	return sun_near_horizon * low_in_sky * side * twilight_strength;
}

vec3 sun_light(vec3 eye_direction) {
	float facing = dot(eye_direction, sun_direction);
	float angle = acos(clamp(facing, -1.0, 1.0));
	float disc = 1.0 - smoothstep(sun_size * 0.85, sun_size, angle);
	float halo = pow(max(facing, 0.0), sun_halo_tightness) * sun_halo_strength;
	float sun_height = smoothstep(0.0, 0.4, sun_direction.y);
	vec3 color = mix(sun_low_color, sun_color, sun_height);
	return color * (disc * sun_intensity + halo);
}

// Three pseudo-random numbers from 0 to 1, always the same for the same cell.
vec3 hash_cell(vec3 cell) {
	vec3 mixed = fract(cell * vec3(0.1031, 0.1030, 0.0973));
	mixed += dot(mixed, mixed.yxz + 33.33);
	return fract((mixed.xxy + mixed.yxx) * mixed.zyx);
}

// The sky is cut into a 3D grid of cells; some cells hold one star at a random spot.
// The layer seed keeps the two layers from sharing the same random stars.
vec3 star_light(vec3 eye_direction, float density, float layer_seed) {
	vec3 cell = floor(eye_direction * density);
	vec3 random = hash_cell(cell + layer_seed);
	if (random.x > star_amount) {
		return vec3(0.0);
	}
	// The spot sits inside the cell, then is pulled onto the sky sphere.
	vec3 star_direction = normalize(cell + 0.25 + random * 0.5);
	float distance_in_cells = length(eye_direction - star_direction) * density;
	float size = mix(star_size_min, star_size_max, random.y);
	float shape = 1.0 - smoothstep(size * 0.4, size, distance_in_cells);
	// Each star twinkles at its own speed and moment.
	float wave = sin(TIME * twinkle_speed * (0.5 + random.z) + random.y * TAU) * 0.5 + 0.5;
	float twinkle = 1.0 - twinkle_strength * wave;
	vec3 color = mix(star_color, star_warm_color, random.z * random.z);
	return color * shape * twinkle * mix(0.35, 1.0, random.y) * star_intensity;
}

// Stars show only at night, fade near the horizon and hide behind the clouds.
float star_visibility(vec3 eye_direction) {
	float night = 1.0 - smoothstep(star_fade_start, star_fade_end, sun_direction.y);
	float above_horizon = smoothstep(0.0, star_horizon_fade, eye_direction.y);
	float behind_clouds = smoothstep(0.0, star_cloud_cutoff, overcast);
	return night * above_horizon * (1.0 - behind_clouds);
}

// Both star layers. The near one is read where the eye meets a sphere of radius
// star_near_distance around the world's center, seen from the camera: as the camera
// moves, that spot shifts, while the far layer (at infinity) does not.
vec3 starfield(vec3 eye_direction, vec3 camera_position) {
	vec3 near_direction = normalize(eye_direction + camera_position / star_near_distance);
	vec3 near_stars = star_light(near_direction, star_near_density, 17.0);
	vec3 far_stars = star_light(eye_direction, star_density, 0.0) * star_far_brightness;
	return near_stars + far_stars;
}

// How much of the moon's face is lit: 0 at new moon, 1 at full.
float moon_lit_fraction() {
	return 0.5 - 0.5 * cos(moon_phase * TAU);
}

// Where the eye falls on the moon's face: x to the right, y up, in moon radii (1 is the
// edge). Seen from the camera, "right" is across the line of sight and the sky's up.
vec2 point_on_moon(vec3 eye_direction) {
	vec3 right = cross(moon_direction, vec3(0.0, 1.0, 0.0));
	// Guarded: a moon straight up has no "right"; any side works there.
	right = length(right) > 0.001 ? normalize(right) : vec3(1.0, 0.0, 0.0);
	vec3 up = cross(right, moon_direction);
	return vec2(dot(eye_direction, right), dot(eye_direction, up)) / moon_size;
}

// A few round, darker seas at fixed spots on its face, for a hint of the real moon.
float moon_maria(vec2 point) {
	float seas = 1.0 - smoothstep(0.2, 0.36, length(point - vec2(-0.25, 0.3)));
	seas = max(seas, 1.0 - smoothstep(0.14, 0.26, length(point - vec2(0.3, 0.15))));
	seas = max(seas, 1.0 - smoothstep(0.1, 0.2, length(point - vec2(0.05, -0.35))));
	return 1.0 - seas * moon_maria_strength;
}

// The moon's face, treated as a half ball lit by the sun from an angle that turns with
// the phase: from behind at new moon, from the right at first quarter (the waxing moon,
// as seen from the northern hemisphere), from the front at full and from the left at last
// quarter. Returns the color in rgb and how much of the pixel it covers in a.
vec4 moon_face(vec3 eye_direction) {
	vec2 point = point_on_moon(eye_direction);
	float radius = length(point);
	float in_front = step(0.0, dot(eye_direction, moon_direction));
	float coverage = (1.0 - smoothstep(0.92, 1.0, radius)) * in_front;
	vec3 normal = vec3(point, sqrt(max(1.0 - radius * radius, 0.0)));
	float sun_angle = moon_phase * TAU;
	vec3 toward_sun = vec3(sin(sun_angle), 0.0, -cos(sun_angle));
	float lit = smoothstep(-0.06, 0.06, dot(normal, toward_sun));
	vec3 bright = moon_color * moon_intensity * moon_maria(point);
	return vec4(mix(moon_dark_color, bright, lit), coverage);
}

// A soft glow around the moon, as strong as the moon is full.
vec3 moon_glow(vec3 eye_direction) {
	float angle = acos(clamp(dot(eye_direction, moon_direction), -1.0, 1.0));
	float glow = 1.0 - clamp(angle / (moon_size * moon_glow_size), 0.0, 1.0);
	return moon_color * glow * glow * moon_glow_strength * moon_lit_fraction();
}

// The horizon cuts the moon, as it does the sun, and clouds hide it.
float moon_visibility(vec3 eye_direction) {
	float above_horizon = smoothstep(-0.01, 0.01, eye_direction.y);
	return above_horizon * (1.0 - smoothstep(0.0, moon_cloud_cutoff, overcast));
}

// The light the sky casts on the world (radiance): softer, less colored and darker below.
vec3 sky_light(vec3 color, vec3 eye_direction) {
	float brightness = dot(color, vec3(0.2126, 0.7152, 0.0722));
	vec3 softened = mix(vec3(brightness), color, sky_light_saturation) * sky_light_strength;
	return softened * mix(1.0, lower_sky_light, smoothstep(0.0, lower_sky_blend, -eye_direction.y));
}

// Below the horizon the sky keeps the horizon color, like a far haze: the high game
// camera sees past the edge of the floor, and the fog takes its color from the sky there.
void sky() {
	float upward = clamp(EYEDIR.y, 0.0, 1.0);
	vec3 color = base_gradient(upward);
	vec3 twilight_color = mix(dawn_color, dusk_color, dusk);
	color = mix(color, twilight_color, twilight_amount(EYEDIR, upward));

	vec3 clouds = overcast_color * mix(overcast_night_brightness, 1.0, daylight);
	color = mix(color, clouds, overcast);
	// Skipped in the lighting snapshot (radiance): twinkling there would relight the
	// world every frame, and tiny stars add no light anyway.
	if (!AT_CUBEMAP_PASS) {
		color += starfield(EYEDIR, POSITION) * star_visibility(EYEDIR);
		// The moon covers the stars behind it; the night light it casts comes from the
		// world's moon light (world_sky.gd), so it stays out of the snapshot too.
		float moon_shown = moon_visibility(EYEDIR);
		vec4 moon = moon_face(EYEDIR);
		color = mix(color, moon.rgb, moon.a * moon_shown);
		color += moon_glow(EYEDIR) * moon_shown;
	}
	// Squared so even a partly cloudy sky already hides most of the sun.
	float clear_sky = 1.0 - overcast;
	// The horizon cuts the sun disc, so a setting sun sinks instead of shining from below.
	float above_horizon = smoothstep(-0.01, 0.01, EYEDIR.y);
	color += sun_light(EYEDIR) * clear_sky * clear_sky * above_horizon;
	if (AT_CUBEMAP_PASS) {
		color = sky_light(color, EYEDIR);
	}
	COLOR = color;
}
