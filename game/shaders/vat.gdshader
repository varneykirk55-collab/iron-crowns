// Vertex Animation Texture crowd shader. One texel row per frame, one column per original vertex.
// INSTANCE_CUSTOM = (clip_start_frame, signed clip_count (negative = play once), clip_start_time, playback speed)
// Visual pass (vis_pass = 1, set by scripts/battle/battle_visuals.gd for c19 battles): per-part material classes
// from UV.v (pipeline common.MAT_*: mat = (1 - UV.y) * 16), deeper team dye, cheap height-based contact darkening,
// per-instance horse coats. vis_pass = 0 (default) is the exact legacy look for every other era / asset.
shader_type spatial;
render_mode cull_disabled;
uniform sampler2D vat_tex : filter_nearest, repeat_disable;
uniform int vat_verts = 1;
uniform float vat_fps = 24.0;
uniform float battle_time = 0.0;
uniform vec4 team_color : source_color = vec4(0.8, 0.2, 0.2, 1.0);
uniform float brightness = 1.0;
uniform float vis_pass = 0.0;
uniform float contact_dark = 0.3;    // albedo darkening at the feet (0 = off); readability pass: was 0.45
uniform float contact_height = 0.35; // metres over which it fades out (feet / gaiters only; was 0.75 = whole trouser leg)
uniform float dye_sat = 1.0;         // team dye saturation for ordinary (non-pastel) colours
uniform float dye_gain = 1.24;       // team dye brightness gain (legacy 1.2)
varying float team_amt;
varying float shade_var;
varying float mat_id;
varying float rest_h;
varying float inst_k;

void vertex() {
	rest_h = VERTEX.y;
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
	inst_k = fract(sin(float(INSTANCE_ID) * 78.233 + 1.7) * 43758.5453);
	mat_id = (1.0 - UV.y) * 16.0;
}

vec3 horse_coat(float k) {
	if (k < 0.34) return vec3(0.36, 0.22, 0.13);   // bay
	if (k < 0.55) return vec3(0.47, 0.27, 0.14);   // chestnut
	if (k < 0.80) return vec3(0.21, 0.14, 0.09);   // dark bay
	if (k < 0.92) return vec3(0.085, 0.078, 0.072); // black
	return vec3(0.56, 0.54, 0.51);                 // grey
}

void fragment() {
	// rest-pose normals (flat derivative normals were unreliable on GL Compatibility)
	vec3 base = COLOR.rgb;
	float ta = clamp(team_amt, 0.0, 1.0);
	if (vis_pass < 0.5) {
		ALBEDO = mix(base, base * team_color.rgb * 1.2, ta) * brightness * shade_var;
		ROUGHNESS = 0.85;
	} else {
		int m = int(mat_id + 0.5);
		// deeper, slightly richer team dye; pastel team colours are pulled down so white belts / facings read
		vec3 tc = team_color.rgb;
		float tl = dot(tc, vec3(0.299, 0.587, 0.114));
		vec3 tdeep = clamp(mix(vec3(tl), tc, mix(dye_sat, 2.4, smoothstep(0.45, 0.75, tl))), vec3(0.0), vec3(1.0)) * mix(1.0, 0.76, smoothstep(0.45, 0.8, tl));
		vec3 alb = mix(base, base * tdeep * dye_gain, ta);
		float sv = mix(1.0, shade_var, 0.7);
		float rough = 0.85; float metal = 0.0; float spec = 0.4;
		if (m == 1) { rough = 0.92; spec = 0.25; alb *= sv; }                       // wool
		else if (m == 2) { rough = 0.42; spec = 0.6; }                             // leather (black / brown)
		else if (m == 3) { rough = 0.3; metal = 0.85; spec = 0.6; }                // steel
		else if (m == 4) { rough = 0.38; metal = 0.8; spec = 0.6; }                // brass / gilt lace
		else if (m == 5) { rough = 0.62; spec = 0.35; alb *= mix(0.86, 1.08, inst_k); } // skin
		else if (m == 6) { rough = 0.55; spec = 0.4; alb *= sv; }                 // wood
		else if (m == 7) { rough = 0.7; spec = 0.35; alb = min(alb * 1.08, vec3(1.0)); } // pipeclay: kept bright
		else if (m == 8) { rough = 0.6; spec = 0.4; alb = horse_coat(inst_k) * mix(0.9, 1.1, (shade_var - 0.88) / 0.24); } // horse hide
		else if (m == 9) { rough = 1.0; spec = 0.1; }                              // fur / sheepskin / plume
		else if (m == 10) { rough = 0.5; metal = 0.6; spec = 0.5; }                // blackened iron
		else if (m == 11) { rough = 0.7; spec = 0.3; if (inst_k > 0.92) { alb = vec3(0.62, 0.6, 0.57); } } // hair / mane
		else { alb *= shade_var; }
		// contact darkening: cheap ground-proximity occlusion on the rest-pose height
		float ao = mix(1.0 - contact_dark, 1.0, smoothstep(0.0, contact_height, rest_h));
		if (m == 7) { ao = 1.0; }  // never darken the white belts / slings
		ALBEDO = alb * brightness * mix(1.0, ao, 0.65);
		AO = ao;
		ROUGHNESS = rough;
		METALLIC = metal;
		SPECULAR = spec;
	}
}
