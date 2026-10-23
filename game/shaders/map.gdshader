// Strategic world map: displaced terrain + natural terrain shading + political overlay driven by a province-id raster
// and an owner LUT. Terrain textures are built by pipeline/build_map_visuals.py (see that file for channel layouts).
shader_type spatial;
render_mode cull_back, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D height_tex : filter_linear, repeat_enable;
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D normal_tex : filter_linear_mipmap, repeat_enable;       // rg slope (signed sqrt), b cavity
uniform sampler2D data_tex : filter_linear_mipmap, repeat_enable;         // r coast sdf, g border dist, b forest, a snow
uniform highp sampler2D nbr_tex : filter_nearest, repeat_enable;          // id across the nearest province border
uniform sampler2D detail_tex : filter_linear_mipmap, repeat_enable;       // r fine, g medium, b canopy, a fields
uniform highp sampler2D prov_tex : filter_nearest, repeat_enable;
uniform sampler2D lut_tex : filter_nearest, repeat_disable;   // 1024 x 2: row0 owner colour (a = owned), row1 flags
uniform vec2 prov_size = vec2(4096.0, 2048.0);
uniform float height_scale = 0.42;
uniform vec2 map_size = vec2(360.0, 180.0);
uniform vec3 era_tint = vec3(1.0);
uniform float era_sepia = 0.0;
uniform float political = 0.66;     // political tint at world zoom; fades toward terrain when zoomed in
uniform float time_s = 0.0;
uniform float cam_dist = 60.0;
uniform int quality = 1;            // 0 low (simple path), 1 medium, 2 high

const float COAST_R = 24.0;   // texels, must match the pipeline
const float BORDER_R = 48.0;
const float SLOPE_MAX = 4.0;

varying vec2 wuv;
varying float vh;

float height_at(vec2 uv) {
	return texture(height_tex, uv).r;
}

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wuv = wp.xz / map_size;
	float h = textureLod(height_tex, wuv, 0.0).r;
	vh = h;
	// same displacement as before the visual upgrade: CPU picking (GameData.surface_y) depends on it
	float y = h > 0.0 ? max(h, 0.03) * height_scale : -0.06;
	// LOD chunk skirts (UV2.x = 1) hang down to hide cracks between neighbouring LODs
	y -= UV2.x * 0.5;
	VERTEX.y += y;
}

int pid_at(vec2 uv) {
	ivec2 p = ivec2(int(floor(fract(uv.x) * prov_size.x)), int(clamp(uv.y, 0.0, 0.99999) * prov_size.y));
	vec2 rg = texelFetch(prov_tex, p, 0).rg;
	return int(rg.r * 255.0 + 0.5) + int(rg.g * 255.0 + 0.5) * 256;
}
int nbr_at(vec2 uv) {
	ivec2 p = ivec2(int(floor(fract(uv.x) * prov_size.x)), int(clamp(uv.y, 0.0, 0.99999) * prov_size.y));
	vec2 rg = texelFetch(nbr_tex, p, 0).rg;
	return int(rg.r * 255.0 + 0.5) + int(rg.g * 255.0 + 0.5) * 256;
}

vec4 owner_of(int id) {
	if (id <= 0 || id >= 1024) return vec4(0.0);
	return texelFetch(lut_tex, ivec2(id, 0), 0);
}
vec4 flags_of(int id) {
	if (id <= 0 || id >= 1024) return vec4(0.0);
	return texelFetch(lut_tex, ivec2(id, 1), 0);
}

float dec_signed(float v, float r) {
	float s = v * 2.0 - 1.0;
	return sign(s) * s * s * r;
}

// Distance (texels) to the nearest province boundary. Up close: manual bilinear filter of the signed border field in
// nbr_tex.b (sign flips across each border, so the zero crossing lies exactly on the boundary and lines are smooth
// instead of following the raster staircase). Far away: the mipmapped unsigned field.
float border_dist(vec2 uv, float far_d, float px) {
	if (px > 1.6) return far_d;
	vec2 t = uv * prov_size - 0.5;
	vec2 f = fract(t);
	ivec2 i0 = ivec2(floor(t));
	int w = int(prov_size.x);
	int y0 = clamp(i0.y, 0, int(prov_size.y) - 1);
	int y1 = clamp(i0.y + 1, 0, int(prov_size.y) - 1);
	int x0 = (i0.x % w + w) % w;
	int x1 = (x0 + 1) % w;
	float a = dec_signed(texelFetch(nbr_tex, ivec2(x0, y0), 0).b, 8.0);
	float b = dec_signed(texelFetch(nbr_tex, ivec2(x1, y0), 0).b, 8.0);
	float c = dec_signed(texelFetch(nbr_tex, ivec2(x0, y1), 0).b, 8.0);
	float d = dec_signed(texelFetch(nbr_tex, ivec2(x1, y1), 0).b, 8.0);
	float near_d;
	if (max(max(abs(a), abs(b)), max(abs(c), abs(d))) < 2.6) {
		near_d = abs(mix(mix(a, b, f.x), mix(c, d, f.x), f.y));
	} else {
		near_d = mix(mix(abs(a), abs(b), f.x), mix(abs(c), abs(d), f.x), f.y) - 0.5;
	}
	return mix(near_d, far_d, smoothstep(1.0, 1.6, px));
}

void fragment() {
	vec2 uv = wuv;
	vec4 dat = texture(data_tex, uv);
	// texels per screen pixel (line widths in pixels stay constant across zoom)
	vec2 fw = fwidth(uv * prov_size);
	float px = max(max(fw.x, fw.y), 0.05);
	float coast_d = dec_signed(dat.r, COAST_R);              // texels, + on land
	float aa = max(px * 0.75, 0.35);
	float landw = smoothstep(-aa, aa, coast_d);
	// close-zoom detail fades in as texels get bigger than pixels
	float near_f = clamp(1.2 - px * 1.5, 0.0, 1.0);
	float zoom_far = smoothstep(30.0, 170.0, cam_dist);    // 0 close .. 1 world view
	vec3 vdir = normalize((INV_VIEW_MATRIX * vec4(VIEW, 0.0)).xyz);

	// ---------------- land ----------------
	vec3 land_col = vec3(0.0);
	vec3 n_land = vec3(0.0, 1.0, 0.0);
	if (landw > 0.0) {
		int id = pid_at(uv);
		int nb = nbr_at(uv);
		vec4 own = owner_of(id);
		vec4 fl = flags_of(id);
		vec3 terrain = texture(albedo_tex, uv).rgb;
		vec3 ns = texture(normal_tex, uv).rgb;
		float gx = dec_signed(ns.r, SLOPE_MAX);
		float gz = dec_signed(ns.g, SLOPE_MAX);
		float relief = quality == 0 ? 1.0 : 1.25;
		n_land = normalize(vec3(-gx * relief, 1.0, -gz * relief));
		float slope = length(vec2(gx, gz));
		float cav = ns.b;
		float forest = dat.b;
		float snow = dat.a;
		// ambient occlusion in valleys, light catching ridges
		terrain *= mix(0.78, 1.12, cav);
		if (quality > 0) {
			vec2 wp = uv * map_size;
			float dfine = texture(detail_tex, wp * 0.7).r;
			float dmed = texture(detail_tex, wp * 0.11).g;
			float canopy = texture(detail_tex, wp * 1.9).b;
			float fields = texture(detail_tex, wp * 0.45).a;
			// large-scale tonal breakup at all zooms (avoids flat colour fields)
			terrain *= 0.9 + 0.2 * dmed;
			// forests: darker, mottled canopy up close
			float can_amt = forest * (0.35 + 0.65 * near_f);
			terrain = mix(terrain, terrain * (0.62 + 0.45 * canopy), can_amt * 0.8);
			// farmland patchwork on gentle open ground up close
			float open_g = (1.0 - forest) * (1.0 - snow) * (1.0 - smoothstep(0.25, 0.6, slope));
			terrain *= 1.0 + (fields - 0.5) * 0.16 * open_g * near_f;
			// exposed rock and scree on steep slopes
			float rock = smoothstep(0.55, 1.3, slope) * (1.0 - snow);
			vec3 rock_c = vec3(0.43, 0.41, 0.38) * (0.8 + 0.4 * dfine);
			terrain = mix(terrain, rock_c, rock * 0.55);
			terrain = mix(terrain, vec3(0.93, 0.95, 0.99) * (0.92 + 0.08 * dfine), snow * smoothstep(0.2, 0.7, snow) * 0.5);
			// close-up micro normal
			n_land = normalize(n_land + vec3(texture(detail_tex, wp * 0.7 + vec2(0.003, 0.0)).r - dfine, 0.0, texture(detail_tex, wp * 0.7 + vec2(0.0, 0.003)).r - dfine) * -4.0 * near_f * (0.3 + 0.7 * max(forest, rock)));
		}
		// ---- political layer ----
		vec4 own_n = owner_of(nb);
		vec4 fl_n = flags_of(nb);
		float bdist = dat.g * dat.g * BORDER_R;                     // texels to nearest province border
		bool owned = own.a > 0.5;
		bool country_b = nb != 0 && distance(own, own_n) > 0.004;
		float pol = owned ? political * mix(0.32, 1.0, zoom_far) : 0.0;
		float tl = dot(terrain, vec3(0.333));
		vec3 tint = own.rgb * (0.55 + 0.6 * tl);
		vec3 col = mix(terrain, tint, pol);
		// soft colour band inside country borders (Victoria-style edge emphasis)
		if (owned && country_b && quality > 0) {
			float band_w = max(px * 9.0, 2.5);
			float band = 1.0 - smoothstep(0.0, band_w, bdist);
			col = mix(col, own.rgb * 0.95, band * mix(0.35, 0.5, zoom_far));
		}
		if (fl.b > 0.5) {   // at war with the player: diagonal hatch
			float s = step(0.5, fract((uv.x + uv.y) * 900.0));
			col = mix(col, vec3(0.75, 0.12, 0.08), 0.22 * s);
		}
		if (fl.g > 0.5) col = mix(col, vec3(1.0), 0.12);           // hovered country
		if (fl.r > 0.5) col = mix(col, vec3(1.0, 0.95, 0.7), 0.28); // selected province
		// border lines from the distance field: width = max(pixel based, world based)
		float d_line = border_dist(uv, max(bdist - 0.5, 0.0), px);
		float prov_w = max(px * 0.55, 0.25);
		float prov_line = (1.0 - smoothstep(prov_w * 0.5, prov_w * 0.5 + px, d_line)) * (1.0 - smoothstep(60.0, 110.0, cam_dist));
		float ctry_w = max(px * 1.1, 0.6);
		float ctry_line = 1.0 - smoothstep(ctry_w * 0.5, ctry_w * 0.5 + px * 1.2, d_line);
		float ctry_shadow = 1.0 - smoothstep(ctry_w, ctry_w + px * 3.0, d_line);
		if (country_b) {
			col = mix(col, col * 0.55, ctry_shadow * 0.5);
			col = mix(col, vec3(0.06, 0.05, 0.045), ctry_line * 0.9);
		} else if (nb != 0) {
			col = mix(col, col * 0.6, prov_line * 0.6);
		}
		if ((fl.r > 0.5 || fl_n.r > 0.5) && nb != 0) {
			float sel_line = 1.0 - smoothstep(ctry_w * 0.6, ctry_w * 0.6 + px * 1.2, d_line);
			col = mix(col, vec3(1.0, 0.9, 0.5), sel_line);
		}
		// coastline: thin dark outline that keeps coasts readable at world zoom
		float cl = 1.0 - smoothstep(max(px * 0.6, 0.3), max(px * 0.6, 0.3) + px, coast_d);
		col = mix(col, vec3(0.08, 0.09, 0.09), cl * 0.55 * (0.4 + 0.6 * zoom_far));
		land_col = col;
	}

	// ---------------- water ----------------
	vec3 water_col = vec3(0.0);
	vec3 n_water = vec3(0.0, 1.0, 0.0);
	if (landw < 1.0) {
		float depth_km = max(-height_at(uv), 0.0);
		float cdist = max(-coast_d, 0.0);                                   // texels from shore (<= 24)
		float shelf = 1.0 - smoothstep(0.05, 0.6, depth_km);
		float dn = smoothstep(0.0, 4.5, depth_km);
		vec3 deep = vec3(0.028, 0.095, 0.19);
		vec3 mid = vec3(0.05, 0.19, 0.30);
		vec3 shallow = vec3(0.13, 0.36, 0.42);
		vec3 col = mix(mid, deep, sqrt(dn));
		col = mix(col, shallow, shelf * 0.8);
		float near_shore = 1.0 - smoothstep(0.0, 6.0, cdist);
		col = mix(col, vec3(0.22, 0.46, 0.48), near_shore * 0.45);
		if (quality > 0) {
			vec2 wp = uv * map_size;
			vec2 w1 = wp * 0.35 + vec2(time_s * 0.010, time_s * 0.006);
			vec2 w2 = wp * 0.9 + vec2(-time_s * 0.017, time_s * 0.011);
			float a1 = texture(detail_tex, w1).g;
			float a2 = texture(detail_tex, w2).r;
			float e = 0.004;
			float dx = texture(detail_tex, w1 + vec2(e, 0.0)).g - a1 + texture(detail_tex, w2 + vec2(e, 0.0)).r - a2;
			float dz = texture(detail_tex, w1 + vec2(0.0, e)).g - a1 + texture(detail_tex, w2 + vec2(0.0, e)).r - a2;
			float wave_k = mix(3.0, 0.8, zoom_far);
			n_water = normalize(vec3(-dx * wave_k, 1.0, -dz * wave_k));
			col *= 0.94 + 0.12 * a1;
			// soft surf line along the shore
			float foam = (1.0 - smoothstep(0.0, max(px * 2.5, 1.2), cdist)) * (0.55 + 0.45 * sin(cdist * 2.0 - time_s * 1.5 + a2 * 6.0));
			col = mix(col, vec3(0.75, 0.84, 0.84), foam * 0.35 * (1.0 - zoom_far * 0.6));
			// fresnel sky reflection
			float fres = pow(1.0 - clamp(dot(vdir, n_water), 0.0, 1.0), 4.0);
			col = mix(col, vec3(0.55, 0.68, 0.80), fres * 0.35);
		}
		water_col = col;
	}

	vec3 col = mix(water_col, land_col, landw);
	vec3 n = normalize(mix(n_water, n_land, landw));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ROUGHNESS = mix(0.32, 0.92, landw);
	SPECULAR = mix(0.55, 0.3, landw);
	// aerial perspective: distant ground fades into a light haze (oblique close-zoom views)
	float vd = length(VERTEX);
	float haze = (1.0 - exp(-max(vd - cam_dist * 0.9, 0.0) * 0.012)) * 0.55;
	col = mix(col, vec3(0.60, 0.68, 0.76), haze);
	// era tone: older eras read like aged campaign maps
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 sepia = vec3(lum * 1.08, lum * 0.95, lum * 0.74);
	col = mix(col, sepia, era_sepia) * era_tint;
	ALBEDO = col;
}
