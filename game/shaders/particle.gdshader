// Camera-facing soft particle (smoke, dust, flashes). INSTANCE_CUSTOM = rgba; instance scale = size.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;
varying vec4 pcol;
varying float seed;
void vertex() {
	vec3 c = MODEL_MATRIX[3].xyz;
	float s = length(MODEL_MATRIX[0].xyz);
	vec3 wp = c + (INV_VIEW_MATRIX[0].xyz * VERTEX.x + INV_VIEW_MATRIX[1].xyz * VERTEX.y) * s;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(wp, 1.0);
	pcol = INSTANCE_CUSTOM;
	seed = fract(c.x * 0.37 + c.z * 0.11);
}
void fragment() {
	vec2 d = UV - 0.5;
	float r = length(d) * 2.0;
	float ang = atan(d.y, d.x);
	float wob = 0.85 + 0.15 * sin(ang * 5.0 + seed * 40.0) * sin(ang * 3.0 - seed * 20.0);
	float a = smoothstep(wob, wob * 0.35, r);
	ALBEDO = pcol.rgb * (0.85 + 0.25 * (1.0 - r));
	ALPHA = a * pcol.a;
}
