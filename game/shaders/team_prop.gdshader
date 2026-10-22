// Static prop / vehicle: vertex colours, team tint mask in UV2.y (glTF flips V, so mask = 1 - v).
shader_type spatial;
render_mode cull_back;
uniform vec4 team_color : source_color = vec4(0.8, 0.2, 0.2, 1.0);
uniform float brightness = 1.0;
varying float team_amt;
void vertex() {
	team_amt = 1.0 - UV2.y;
}
void fragment() {
	vec3 base = COLOR.rgb;
	ALBEDO = mix(base, base * team_color.rgb * 1.15, clamp(team_amt, 0.0, 1.0)) * brightness;
	ROUGHNESS = 0.8;
}
