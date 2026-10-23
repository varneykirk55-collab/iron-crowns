// Battlefield terrain for scripts/battle/battle_environment.gd (biome ground; the legacy ground.gdshader is untouched).
// Layers: lush grass / dry grass / bare earth (trampled corridor + patches) / forest floor / granite by slope / wet
// shore + lake bed / alpine scree / summer snow on high peaks. Anti-tiling: one seamless noise sampled at 5 scales
// with rotated, offset coordinates + a macro variation layer, no repeating albedo texture at all. Masks: near
// (forest cover, battle-worn zone, rocky knoll) and far (forest belts) baked on the CPU from the same functions that
// place the trees, so the ground under the forest is forest floor. ~10 texture reads, no loops: cheap on GL Compat.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
uniform vec3 grass_a : source_color = vec3(0.29, 0.35, 0.15);
uniform vec3 grass_b : source_color = vec3(0.40, 0.42, 0.2);
uniform vec3 dry : source_color = vec3(0.56, 0.5, 0.3);
uniform vec3 earth : source_color = vec3(0.35, 0.28, 0.19);
uniform vec3 floor_col : source_color = vec3(0.2, 0.21, 0.12);
uniform vec3 needle : source_color = vec3(0.26, 0.2, 0.13);
uniform vec3 rock : source_color = vec3(0.47, 0.46, 0.43);
uniform vec3 scree : source_color = vec3(0.42, 0.4, 0.36);
uniform vec3 snow_col : source_color = vec3(0.9, 0.92, 0.95);
uniform vec3 far_forest : source_color = vec3(0.13, 0.19, 0.11);
uniform float dryness = 0.25;
uniform float snow_h = 1000.0;
uniform float treeline = 600.0;
uniform float water_h = -100000.0;
uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D near_mask : repeat_disable, filter_linear;
uniform sampler2D far_mask : repeat_disable, filter_linear;
uniform float near_ext = 620.0;
uniform float far_ext = 3000.0;
varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

vec2 rot(vec2 p, float a) { float c = cos(a), s = sin(a); return vec2(c * p.x - s * p.y, s * p.x + c * p.y); }

void fragment() {
	vec2 p = wpos.xz;
	float dist = length(VERTEX);
	float macro = texture(noise_tex, rot(p, 0.7) * 0.00045 + vec2(0.13, 0.71)).r;
	float n1 = texture(noise_tex, p * 0.0037).r;
	float n2 = texture(noise_tex, rot(p, 0.52) * 0.023 + vec2(0.37, 0.11)).r;
	// fine detail fades out with distance (no shimmer / visible tiling far away) and is not even sampled there
	float n3 = 0.5, n4 = 0.5;
	if (dist < 1200.0) {
		n3 = mix(0.5, texture(noise_tex, rot(p, 1.13) * 0.13 + vec2(0.71, 0.29)).r, 1.0 - smoothstep(300.0, 1200.0, dist));
	}
	if (dist < 260.0) {
		n4 = mix(0.5, texture(noise_tex, rot(p, 2.2) * 0.61 + vec2(0.21, 0.53)).r, 1.0 - smoothstep(60.0, 260.0, dist));
	}
	vec4 nm = vec4(0.0);
	if (max(abs(p.x), abs(p.y)) < near_ext) {
		nm = texture(near_mask, p / (2.0 * near_ext) + 0.5);
	}
	vec4 fm = texture(far_mask, p / (2.0 * far_ext) + 0.5);
	float in_near = 1.0 - smoothstep(near_ext * 0.85, near_ext, max(abs(p.x), abs(p.y)));
	float forest = mix(fm.r, nm.r, in_near);
	float worn = nm.g * in_near;
	float knoll = nm.a * in_near;
	float slope = 1.0 - clamp(wnorm.y, 0.0, 1.0);

	// grass: two greens by meso noise, sun-dried straw by macro noise / dryness / exposed crests
	vec3 g = mix(grass_a, grass_b, smoothstep(0.3, 0.7, n1 * 0.6 + n2 * 0.4));
	float dmask = smoothstep(0.62 - dryness * 0.5, 0.86 - dryness * 0.4, macro * 0.55 + n2 * 0.3 + n3 * 0.15 + slope * 0.6 + knoll * 0.25);
	g = mix(g, dry * mix(0.9, 1.08, n3), dmask * 0.85);
	g *= mix(0.9, 1.04, smoothstep(0.2, 0.8, n2 * 0.4 + n3 * 0.6));   // tussocks / hollows
	g *= mix(0.93, 1.05, n4);                                             // close speckle
	// battle-worn corridor: trampled earth patches + tracks, never a solid brown sheet
	float bare = worn * smoothstep(0.5, 0.68, n2 * 0.55 + n3 * 0.3 + n4 * 0.15);
	bare = max(bare, smoothstep(0.74, 0.8, n2 * 0.6 + macro * 0.4) * 0.6);   // scattered bare patches everywhere
	g = mix(g, earth * mix(0.82, 1.1, n4), bare * 0.75);
	// forest floor: moss + needle litter, darker (canopy AO)
	vec3 ff = mix(floor_col, needle, smoothstep(0.4, 0.65, n3 * 0.7 + n4 * 0.3));
	g = mix(g, ff * mix(0.8, 1.05, n2), smoothstep(0.15, 0.6, forest));
	// far forest belts read as dark canopy from a distance where the far LOD trees thin out
	g = mix(g, far_forest * mix(0.85, 1.1, n2), smoothstep(0.35, 0.8, fm.r) * smoothstep(400.0, 1400.0, dist) * (1.0 - in_near * 0.6));
	// rock: steep slopes + the granite knoll shows through as polished slabs
	float rk = smoothstep(0.22, 0.42, slope + (n3 - 0.5) * 0.18) + knoll * smoothstep(0.55, 0.7, n2 * 0.6 + n3 * 0.4);
	vec3 rc = rock * mix(0.78, 1.08, n3) * mix(0.92, 1.05, n4);
	rc = mix(rc, vec3(0.45, 0.47, 0.36), smoothstep(0.6, 0.8, n2) * 0.4 * (1.0 - slope));   // lichen
	g = mix(g, rc, clamp(rk, 0.0, 1.0));
	// alpine: above the treeline grass gives way to heath / scree, summer snow only on the highest peaks + gullies
	float alp = smoothstep(treeline * 0.9, treeline * 1.25, wpos.y + (n2 - 0.5) * 80.0);
	g = mix(g, mix(scree, rock * 0.9, smoothstep(0.3, 0.6, slope)) * mix(0.85, 1.1, n2), alp * 0.85);
	float sn = smoothstep(snow_h - 30.0, snow_h + 60.0, wpos.y + (n2 - 0.5) * 140.0 + (n1 - 0.5) * 80.0) * (1.0 - smoothstep(0.45, 0.75, slope) * 0.6);
	g = mix(g, snow_col * mix(0.88, 1.0, n2), sn);
	// wet shore + lake bed
	float lake = nm.b * in_near;
	float wet = (1.0 - smoothstep(water_h + 0.2, water_h + 1.6, wpos.y)) * lake;
	g = mix(g, mix(earth * 0.6, vec3(0.42, 0.39, 0.32), smoothstep(0.4, 0.6, n3)), wet * 0.7);
	g = mix(g, vec3(0.16, 0.17, 0.13), (1.0 - smoothstep(water_h - 1.2, water_h - 0.1, wpos.y)) * lake);
	// gentle macro value variation + aerial desaturation far away (the fog then tints it)
	g *= mix(0.9, 1.05, macro);
	float far = smoothstep(900.0, 3500.0, dist);
	g = mix(g, vec3(dot(g, vec3(0.3, 0.59, 0.11))), far * 0.35);
	ALBEDO = g;
	ROUGHNESS = mix(0.95, 0.55, wet * (1.0 - sn));
	SPECULAR = mix(0.12, 0.3, wet);
}
