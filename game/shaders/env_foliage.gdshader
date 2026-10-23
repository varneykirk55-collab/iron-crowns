// Vegetation + stones of the battlefield environment (scripts/battle/battle_environment.gd). Vertex colour x
// MultiMesh instance colour (per-instance hue / value jitter so no two trees share a colour). UV2.y = foliage mask
// from pipeline/blender/env_nordic.py: foliage gets a gentle wind sway and rounded "crown" normals (soft volumetric
// shading instead of faceted cones); wood / stone stays rigid. dry = grass tufts blend green -> straw by INSTANCE
// colour alpha. No textures, no alpha test, no transparency: one pass, shadow-castable.
shader_type spatial;
render_mode cull_disabled, diffuse_lambert, specular_schlick_ggx;
uniform float wind = 1.0;
uniform float bend = 0.6;
uniform float albedo_mul = 1.0;
uniform float tuft = 0.0;
uniform vec3 straw : source_color = vec3(0.62, 0.55, 0.33);
varying float fol;
varying vec4 icol;

void vertex() {
	fol = UV2.y;
	icol = INSTANCE_CUSTOM;
	if (fol > 0.5) {
		vec3 wp = MODEL_MATRIX[3].xyz;
		float ph = wp.x * 0.043 + wp.z * 0.061;
		float s = sin(TIME * 1.1 + ph) * 0.6 + sin(TIME * 2.3 + ph * 1.7) * 0.25;
		float k = VERTEX.y * VERTEX.y * 0.0009 * wind * (1.0 + tuft * 60.0);
		VERTEX.xz += vec2(s, s * 0.6) * k;
		vec3 sph = normalize(vec3(VERTEX.x, 0.45 * length(VERTEX.xz) + 0.25, VERTEX.z));
		NORMAL = normalize(mix(NORMAL, sph, bend));
	}
}

void fragment() {
	vec3 c = COLOR.rgb;
	if (tuft > 0.5) {
		c = mix(c, straw * (0.7 + 0.5 * c.g / max(c.r + c.g, 0.01)), icol.a);
	}
	ALBEDO = c * albedo_mul;
	ROUGHNESS = fol > 0.5 ? 0.86 : 0.8;
	SPECULAR = fol > 0.5 ? 0.25 : 0.3;
	if (fol > 0.5) {
		BACKLIGHT = c * 0.25;   // a little light through needles / leaves at low sun
	}
}
