// Battlefield ground: vertex-coloured terrain with procedural variation and trampled earth near the centre.
shader_type spatial;
uniform vec4 grass_a : source_color = vec4(0.32, 0.42, 0.18, 1.0);
uniform vec4 grass_b : source_color = vec4(0.45, 0.48, 0.24, 1.0);
uniform vec4 dirt : source_color = vec4(0.42, 0.34, 0.24, 1.0);
uniform vec4 rock : source_color = vec4(0.45, 0.43, 0.4, 1.0);
uniform float snow = 0.0;
uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
varying vec3 wpos;
varying vec3 wnorm;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = NORMAL;
}
void fragment() {
	float n1 = texture(noise_tex, wpos.xz * 0.004).r;
	float n2 = texture(noise_tex, wpos.xz * 0.031).r;
	float n3 = texture(noise_tex, wpos.xz * 0.21).r;
	vec3 g = mix(grass_a.rgb, grass_b.rgb, smoothstep(0.35, 0.65, n1 * 0.7 + n2 * 0.3));
	float trample = smoothstep(150.0, 40.0, length(wpos.xz * vec2(0.8, 1.0))) * smoothstep(0.42, 0.62, n2 * 0.6 + n3 * 0.4);
	g = mix(g, dirt.rgb, trample * 0.55);
	float slope = 1.0 - wnorm.y;
	g = mix(g, rock.rgb, smoothstep(0.18, 0.38, slope + (n3 - 0.5) * 0.1));
	g = mix(g, vec3(0.92, 0.94, 0.97), snow * smoothstep(0.45, 0.6, n1 + n3 * 0.3 + wpos.y * 0.01));
	g *= (0.85 + 0.3 * n3) * 0.82;
	ALBEDO = g;
	ROUGHNESS = 0.95;
	SPECULAR = 0.08;
}
