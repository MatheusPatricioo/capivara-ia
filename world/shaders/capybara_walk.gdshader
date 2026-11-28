// The capybara's skin, with legs that walk. The model is one mesh with no skeleton, so the
// legs are moved here, vertex by vertex: every vertex below her belly belongs to one of the
// four legs and swings around that leg's hip, like a pendulum. The legs move in diagonal
// pairs (front left with back right), the trot of four-legged animals, and a foot lifts a
// little while it swings forward. CapybaraBodyAnimation sends the step phase and how
// strongly she walks every frame. All positions are in the model's own space: y up, her
// head at +x, her left at +z.
shader_type spatial;
render_mode diffuse_lambert_wrap, specular_disabled;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap;
uniform vec4 albedo_color : source_color = vec4(1.0);
// A little of her own color added to the light, so the side away from the sun shows brown
// instead of turning black: 0 is fully lit by the scene, 1 is flat like an unshaded material.
uniform float self_light : hint_range(0.0, 1.0) = 0.45;

// Where she is in her step cycle, in radians (0 to TAU), and 0 standing to 1 walking.
uniform float step_phase = 0.0;
uniform float gait_strength = 0.0;

// How far a leg swings to each side, and how high a foot lifts while it swings forward.
uniform float swing_degrees = 28.0;
uniform float lift_height = 0.025;

// The legs: below leg_bottom_y a vertex is all leg, above leg_top_y all belly, with a soft
// blend between (her belly starts at about -0.274). Each leg turns around a hip at hip_y,
// inside her body, above the front or back feet.
uniform float hip_y = -0.24;
uniform float leg_top_y = -0.25;
uniform float leg_bottom_y = -0.29;
uniform float sole_y = -0.352;
uniform float front_hip_x = 0.184;
uniform float back_hip_x = -0.255;
// Horizontal reach of a leg around its hip: the belly between the legs stays still.
uniform float foot_inner_radius = 0.07;
uniform float foot_outer_radius = 0.11;

vec2 rotate_around(vec2 point, vec2 pivot, float angle) {
	vec2 offset = point - pivot;
	return pivot + vec2(
		offset.x * cos(angle) - offset.y * sin(angle),
		offset.x * sin(angle) + offset.y * cos(angle)
	);
}

void vertex() {
	bool is_front = VERTEX.x > (front_hip_x + back_hip_x) * 0.5;
	bool is_left = VERTEX.z > 0.0;
	float hip_x = is_front ? front_hip_x : back_hip_x;

	float below_belly = 1.0 - smoothstep(leg_bottom_y, leg_top_y, VERTEX.y);
	float near_leg = 1.0 - smoothstep(foot_inner_radius, foot_outer_radius, abs(VERTEX.x - hip_x));
	float leg_weight = below_belly * near_leg * gait_strength;

	// Front left and back right step together; the other pair half a cycle later.
	float leg_phase = step_phase + (is_front == is_left ? 0.0 : PI);
	// The foot is ahead of the hip by sin(phase): it moves forward while cos(phase) > 0
	// (swinging through the air) and backward while it pushes against the ground.
	float swing_angle = radians(swing_degrees) * sin(leg_phase) * leg_weight;
	float depth = clamp((hip_y - VERTEX.y) / (hip_y - sole_y), 0.0, 1.0);
	float lift = max(cos(leg_phase), 0.0) * lift_height * leg_weight * depth;

	VERTEX.xy = rotate_around(VERTEX.xy, vec2(hip_x, hip_y), swing_angle) + vec2(0.0, lift);
	NORMAL.xy = rotate_around(NORMAL.xy, vec2(0.0), swing_angle);
}

void fragment() {
	vec3 skin = texture(albedo_texture, UV).rgb * albedo_color.rgb;
	ALBEDO = skin;
	EMISSION = skin * self_light;
	ROUGHNESS = 1.0;
}
