shader_type spatial;
render_mode cull_disabled;
uniform vec4 team_color : source_color = vec4(0.8, 0.2, 0.2, 1.0);
uniform float time_s = 0.0;
void vertex() {
	float u = UV.x;
	VERTEX.z += sin(time_s * 4.0 + u * 6.0 + MODEL_MATRIX[3].x * 0.3) * 0.18 * u;
	VERTEX.y += sin(time_s * 3.0 + u * 4.0) * 0.06 * u;
}
void fragment() {
	vec3 c = team_color.rgb;
	if (UV.y > 0.38 && UV.y < 0.62) { c = mix(c, vec3(0.95, 0.9, 0.75), 0.75); }
	ALBEDO = c * (0.75 + 0.25 * UV.x);
	ROUGHNESS = 0.9;
}
