// Vertex Animation Texture crowd shader. One texel row per frame, one column per original vertex.
// INSTANCE_CUSTOM = (clip_start_frame, signed clip_count (negative = play once), clip_start_time, playback speed)
shader_type spatial;
render_mode cull_disabled;
uniform sampler2D vat_tex : filter_nearest, repeat_disable;
uniform int vat_verts = 1;
uniform float vat_fps = 24.0;
uniform float battle_time = 0.0;
uniform vec4 team_color : source_color = vec4(0.8, 0.2, 0.2, 1.0);
uniform float brightness = 1.0;
varying float team_amt;
varying float shade_var;

void vertex() {
	int vid = clamp(int(UV2.x * float(vat_verts)), 0, vat_verts - 1);
	float start = INSTANCE_CUSTOM.x;
	float cnt = abs(INSTANCE_CUSTOM.y);
	bool loop_clip = INSTANCE_CUSTOM.y > 0.0;
	float f = max(battle_time - INSTANCE_CUSTOM.z, 0.0) * INSTANCE_CUSTOM.w * vat_fps;
	float fr;
	if (loop_clip) { fr = mod(f, cnt); } else { fr = clamp(f, 0.0, cnt - 1.0); }
	int f0 = int(floor(fr));
	int f1 = loop_clip ? int(mod(float(f0 + 1), cnt)) : min(f0 + 1, int(cnt) - 1);
	vec3 p0 = texelFetch(vat_tex, ivec2(vid, int(start) + f0), 0).xyz;
	vec3 p1 = texelFetch(vat_tex, ivec2(vid, int(start) + f1), 0).xyz;
	VERTEX = mix(p0, p1, fract(fr));
	team_amt = 1.0 - UV2.y;
	shade_var = 0.88 + 0.24 * fract(sin(float(INSTANCE_ID) * 12.9898) * 43758.5453);
}

void fragment() {
	// rest-pose normals (flat derivative normals were unreliable on GL Compatibility)
	vec3 base = COLOR.rgb;
	ALBEDO = mix(base, base * team_color.rgb * 1.2, clamp(team_amt, 0.0, 1.0)) * brightness * shade_var;
	ROUGHNESS = 0.85;
}
