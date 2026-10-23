// Lake surface (scripts/battle/battle_environment.gd). Opaque (no depth / screen texture reads, works on GL Compat):
// dark peaty water, two scrolling noise octaves perturb the normal for ripples, Fresnel blend toward the sky
// horizon colour, sharp sun glint from the GGX specular. Shore blending is done by the terrain shader (wet band).
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
uniform vec3 deep : source_color = vec3(0.05, 0.08, 0.09);
uniform vec3 sky : source_color = vec3(0.62, 0.7, 0.8);
uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
	vec2 p = wpos.xz;
	float a = texture(noise_tex, p * 0.06 + vec2(TIME * 0.006, TIME * 0.002)).r;
	float b = texture(noise_tex, p * 0.17 - vec2(TIME * 0.004, -TIME * 0.007)).r;
	float c = texture(noise_tex, p * 0.06 + vec2(0.02 + TIME * 0.006, TIME * 0.002)).r;
	float d = texture(noise_tex, p * 0.17 - vec2(TIME * 0.004, 0.02 - TIME * 0.007)).r;
	vec3 wn = normalize(vec3((a - c) * 0.35 + (b - d) * 0.2, 1.0, (c - d) * 0.25));
	NORMAL = normalize((VIEW_MATRIX * vec4(wn, 0.0)).xyz);
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 4.0);
	ALBEDO = mix(deep, sky * 0.5, 0.08 + fres * 0.55);
	ROUGHNESS = 0.16;
	SPECULAR = 0.4;
	METALLIC = 0.0;
}
