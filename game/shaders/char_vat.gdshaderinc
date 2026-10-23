// (include) Character-refinement crowd shader (c19sr_* soldiers; pipeline/blender/char_build.py bake).
// Same instance layout as vat.gdshader: INSTANCE_CUSTOM = (clip_start_row, signed clip_count (negative = play once),
// clip_start_time, playback speed), so BattleView._update_units drives it unchanged. Additions:
//  * per-frame normals (.vatn RGBA8, n*0.5+0.5) instead of rest-pose normals
//  * colour from a per-side nation palette texture (32 x 1): UV.x = (slot + 0.5) / 32, material class from UV.y
//  * two death variants: "die" rows are swapped for "die_b" by a hash of the death time
//  * optional clip crossfade: instance COLOR = (prev_start, prev_signed_count, seconds elapsed in the prev clip, weight)
//    (BattleVisuals.xfade; elapsed rather than an absolute time so half-float instance colours stay exact). The default
//    instance colour (1,1,1,1) means weight 1 = no blend, so it works without any BattleView change.
// Stage 7 (perf): body lives in char_vat.gdshaderinc; compile-time variants
//  CHAR_NRM1  = one nearest-frame normal fetch instead of two blended ones
//  CHAR_NONRM = rest-pose normals (no .vatn fetch)
//  CHAR_NOXF  = no clip crossfade (ignores instance COLOR; no second VAT fetch)
//  CHAR_VPAL  = palette + material class resolved per vertex (flat per part anyway) instead of per pixel
// char_vat.gdshader = LOD0 (full), char_vat_lod1.gdshader = LOD1 (cheap variant).

uniform sampler2D vat_tex : filter_nearest, repeat_disable;
uniform sampler2D vat_nrm : filter_nearest, repeat_disable;
uniform sampler2D palette : source_color, filter_nearest, repeat_disable;
uniform int vat_verts = 1;
uniform float vat_fps = 24.0;
uniform float battle_time = 0.0;
uniform vec4 team_color : source_color = vec4(0.8, 0.2, 0.2, 1.0);
uniform float brightness = 1.0;
uniform float vis_pass = 1.0;       // accepted for battle_visuals compatibility (always the refined look)
uniform float team_dye = 0.0;       // 0 = nation coat colour, 1 = coat dyed with the side colour (mirror matches)
uniform float die_row = -1.0;       // start row of "die" (from the json); -1 = no variant swap
uniform float die_b_row = -1.0;
uniform float has_normals = 1.0;
uniform float contact_dark = 0.3;
uniform float contact_height = 0.3;
uniform int near_verts = 0x7fffffff;  // stage 7: LOD0 mesh = near set [0,near_verts) + far (LOD1) set after it
uniform float char_lod_dist = 1.0e9;  // battle_visuals char_lod: instances farther than this draw the far set
varying float team_amt;
varying float shade_var;
varying float mat_id;
varying float slot_u;
varying float rest_h;
varying float inst_k;

#ifdef CHAR_VPAL
varying vec3 v_alb;
varying vec4 v_rsm;   // rough, metal, spec, ao
#endif

void vmat(float slot_u_, float team_amt_, float mat_id_, float rest_h_, float shade_var_, float inst_k_, out vec3 alb_o, out float rough_o, out float metal_o, out float spec_o, out float ao_o) {
	int slot = clamp(int(slot_u_ * 32.0), 0, 31);
	vec3 alb = texelFetch(palette, ivec2(slot, 0), 0).rgb;
	float ta = clamp(team_amt_, 0.0, 1.0) * team_dye;
	alb = mix(alb, team_color.rgb * 0.75, ta);
	int m = int(mat_id_ + 0.5);
	float sv = mix(1.0, shade_var_, 0.6);
	float rough = 0.85; float metal = 0.0; float spec = 0.4;
	if (m == 1) { rough = 0.93; spec = 0.22; alb *= sv; }                       // wool
	else if (m == 2) { rough = 0.38; spec = 0.6; }                              // leather
	else if (m == 3) { rough = 0.28; metal = 0.85; spec = 0.6; }                // steel
	else if (m == 4) { rough = 0.35; metal = 0.85; spec = 0.6; }                // brass / gilt
	else if (m == 5) { rough = 0.6; spec = 0.35; alb *= mix(0.84, 1.08, inst_k_); } // skin
	else if (m == 6) { rough = 0.55; spec = 0.4; alb *= sv; }                  // wood
	else if (m == 7) { rough = 0.7; spec = 0.35; }                             // pipeclay
	else if (m == 9) { rough = 1.0; spec = 0.1; }                              // fur / plume
	else if (m == 10) { rough = 0.5; metal = 0.6; spec = 0.5; }                // blackened iron
	else if (m == 11) { rough = 0.75; spec = 0.3; alb *= mix(0.7, 1.3, inst_k_); } // hair
	else if (m == 13) { rough = 0.9; spec = 0.2; alb *= sv; }                  // canvas / linen
	float ao = mix(1.0 - contact_dark, 1.0, smoothstep(0.0, contact_height, rest_h_));
	if (m == 7 || m == 13) { ao = 1.0; }
	alb_o = alb * brightness * mix(1.0, ao, 0.6); rough_o = rough; metal_o = metal; spec_o = spec; ao_o = ao;
}

vec3 vat_at(int vid, float start, float cnt_s, float t0, float spd, out vec3 nrm) {
	float cnt = max(abs(cnt_s), 1.0);
	bool loop_clip = cnt_s > 0.0;
	float f = max(battle_time - t0, 0.0) * spd * vat_fps;
	float fr = loop_clip ? mod(f, cnt) : clamp(f, 0.0, cnt - 1.0);
	int f0 = int(floor(fr));
	int f1 = loop_clip ? int(mod(float(f0 + 1), cnt)) : min(f0 + 1, int(cnt) - 1);
	int r0 = int(start) + f0; int r1 = int(start) + f1;
	float a = fract(fr);
#if defined(CHAR_NONRM)
	nrm = vec3(0.0);
#elif defined(CHAR_NRM1)
	nrm = texelFetch(vat_nrm, ivec2(vid, a < 0.5 ? r0 : r1), 0).xyz * 2.0 - 1.0;   // nearest frame: one fetch
#else
	nrm = mix(texelFetch(vat_nrm, ivec2(vid, r0), 0).xyz, texelFetch(vat_nrm, ivec2(vid, r1), 0).xyz, a) * 2.0 - 1.0;
#endif
	return mix(texelFetch(vat_tex, ivec2(vid, r0), 0).xyz, texelFetch(vat_tex, ivec2(vid, r1), 0).xyz, a);
}

void vertex() {
	rest_h = VERTEX.y;
	vec3 rest_n = NORMAL;
	int vid = clamp(int(UV2.x * float(vat_verts)), 0, vat_verts - 1);
	bool hide = false;
	if (near_verts < vat_verts) {   // LOD0 only: pick the near or far geometry set per instance, collapse the other
		vec3 dc = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz - CAMERA_POSITION_WORLD;
		hide = (vid >= near_verts) != (dot(dc, dc) > char_lod_dist * char_lod_dist);
	}
	if (hide) {
		VERTEX = vec3(0.0, -50.0, 0.0);
		NORMAL = vec3(0.0, 1.0, 0.0);
	} else {
		float start = INSTANCE_CUSTOM.x;
		if (die_row >= 0.0 && abs(start - die_row) < 0.5 && fract(sin(INSTANCE_CUSTOM.z * 91.17 + 3.1) * 43758.5453) > 0.5) {
			start = die_b_row;
		}
		vec3 n0;
		vec3 p = vat_at(vid, start, INSTANCE_CUSTOM.y, INSTANCE_CUSTOM.z, INSTANCE_CUSTOM.w, n0);
#ifndef CHAR_NOXF
		float w = clamp(COLOR.a, 0.0, 1.0);
		if (w < 0.999) {   // crossfade from the previous clip (hook-driven)
			vec3 n1;
			vec3 q = vat_at(vid, COLOR.r, COLOR.g, battle_time - COLOR.b, 1.0, n1);
			float e = w * w * (3.0 - 2.0 * w);
			p = mix(q, p, e); n0 = mix(n1, n0, e);
		}
#endif
		VERTEX = p;
#ifdef CHAR_NONRM
		NORMAL = rest_n;
#else
		NORMAL = has_normals > 0.5 ? normalize(n0) : rest_n;
#endif
		team_amt = 1.0 - UV2.y;
		shade_var = 0.9 + 0.2 * fract(sin(float(INSTANCE_ID) * 12.9898) * 43758.5453);
		inst_k = fract(sin(float(INSTANCE_ID) * 78.233 + 1.7) * 43758.5453);
		mat_id = (1.0 - UV.y) * 16.0;
		slot_u = UV.x;
#ifdef CHAR_VPAL
		vec3 va3; float vr; float vm; float vs; float va;
		vmat(slot_u, team_amt, mat_id, rest_h, shade_var, inst_k, va3, vr, vm, vs, va);
		v_alb = va3; v_rsm = vec4(vr, vm, vs, va);
#endif
	}
}

void fragment() {
#ifdef CHAR_VPAL
	ALBEDO = v_alb; ROUGHNESS = v_rsm.x; METALLIC = v_rsm.y; SPECULAR = v_rsm.z; AO = v_rsm.w;
#else
	vec3 alb; float rough; float metal; float spec; float ao;
	vmat(slot_u, team_amt, mat_id, rest_h, shade_var, inst_k, alb, rough, metal, spec, ao);
	ALBEDO = alb; ROUGHNESS = rough; METALLIC = metal; SPECULAR = spec; AO = ao;
#endif
}
