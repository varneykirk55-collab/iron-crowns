// Strategic world map: displaced terrain + political overlay driven by a province-id raster and an owner LUT.
shader_type spatial;
render_mode cull_back, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D height_tex : filter_linear, repeat_enable;
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform highp sampler2D prov_tex : filter_nearest, repeat_enable;
uniform sampler2D lut_tex : filter_nearest, repeat_disable;   // 1024 x 2: row0 owner colour (a = owned), row1 flags
uniform vec2 prov_size = vec2(4096.0, 2048.0);
uniform float height_scale = 0.42;
uniform vec2 map_size = vec2(360.0, 180.0);
uniform vec3 era_tint = vec3(1.0);
uniform float era_sepia = 0.0;
uniform float political = 0.66;
uniform float time_s = 0.0;
uniform float cam_dist = 60.0;

varying vec2 wuv;
varying float vh;

float height_at(vec2 uv) {
	return texture(height_tex, uv).r;
}

void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wuv = wp.xz / map_size;
	float h = height_at(wuv);
	vh = h;
	float y = h > 0.0 ? max(h, 0.03) * height_scale : -0.06;
	VERTEX.y += y;
}

int pid_at(vec2 uv) {
	ivec2 p = ivec2(int(floor(fract(uv.x) * prov_size.x)), int(clamp(uv.y, 0.0, 0.99999) * prov_size.y));
	vec2 rg = texelFetch(prov_tex, p, 0).rg;
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

void fragment() {
	vec2 uv = wuv;
	int id = pid_at(uv);
	bool land = id != 0;
	vec3 base = texture(albedo_tex, uv).rgb;
	// texels per screen pixel -> border width independent of zoom
	vec2 fw = fwidth(uv * prov_size);
	float px = max(max(fw.x, fw.y), 0.6);
	vec2 tx = 1.0 / prov_size;
	vec4 own = owner_of(id);
	vec4 fl = flags_of(id);
	float country_edge = 0.0;
	float prov_edge = 0.0;
	float glow = 0.0;
	float coast = 0.0;
	vec2 dirs[8] = vec2[](vec2(1, 0), vec2(-1, 0), vec2(0, 1), vec2(0, -1), vec2(0.7, 0.7), vec2(-0.7, 0.7), vec2(0.7, -0.7), vec2(-0.7, -0.7));
	for (int k = 0; k < 8; k++) {
		vec2 o1 = dirs[k] * tx * px * 1.3;
		int n1 = pid_at(uv + o1);
		if (n1 != id) {
			vec4 on = owner_of(n1);
			if (land && n1 != 0 && distance(on, own) > 0.004) country_edge = 1.0;
			else if (land && n1 != 0) prov_edge = 1.0;
			if (!land && n1 != 0) coast = max(coast, 0.6);
			if (land && n1 == 0) country_edge = max(country_edge, 0.55);
		}
		vec2 o2 = dirs[k] * tx * px * 6.0;
		int n2 = pid_at(uv + o2);
		if (land && n2 != 0 && distance(owner_of(n2), own) > 0.004) glow += 0.125;
		if (!land && n2 != 0) coast = max(coast, 0.25);
	}
	vec3 col;
	if (land) {
		// relief shading from the height field
		float e = 1.0 / 2048.0;
		float hx = (height_at(uv + vec2(e, 0)) - height_at(uv - vec2(e, 0)));
		float hz = (height_at(uv + vec2(0, e * 0.5)) - height_at(uv - vec2(0, e * 0.5)));
		vec3 n = normalize(vec3(-hx * height_scale * 6.0, 1.0, -hz * height_scale * 6.0));
		NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
		vec3 terrain = base;
		float pol = own.a > 0.5 ? political : 0.0;
		col = mix(terrain, own.rgb * (0.6 + 0.55 * dot(terrain, vec3(0.333))), pol);
		col = mix(col, own.rgb, glow * 0.35 * own.a);
		// enemy (at war with the player) hatch
		if (fl.b > 0.5) {
			float s = step(0.5, fract((uv.x + uv.y) * 900.0));
			col = mix(col, vec3(0.75, 0.12, 0.08), 0.22 * s);
		}
		if (fl.g > 0.5) col = mix(col, vec3(1.0), 0.12);           // hovered country
		if (fl.r > 0.5) col = mix(col, vec3(1.0, 0.95, 0.7), 0.28); // selected province
		col = mix(col, col * 0.62, prov_edge * 0.55 * clamp(70.0 / cam_dist, 0.0, 1.0));
		col = mix(col, vec3(0.06, 0.05, 0.04), country_edge * 0.85);
		if (fl.r > 0.5 && prov_edge + country_edge > 0.0) col = vec3(1.0, 0.93, 0.6);
		ROUGHNESS = 0.92;
	} else {
		float depth = clamp(-vh / 5.0, 0.0, 1.0);
		vec3 deep = vec3(0.04, 0.13, 0.24);
		vec3 shallow = vec3(0.12, 0.32, 0.42);
		col = mix(shallow, deep, sqrt(depth));
		col = mix(col, base * vec3(0.7, 0.85, 1.0), 0.25);
		float w = sin(uv.x * 2400.0 + time_s * 1.3 + sin(uv.y * 900.0) * 2.0) * sin(uv.y * 1900.0 - time_s * 0.9);
		// fade the wave pattern out before it aliases into moire stripes at distance
		float wf = fwidth(uv.y * 1900.0) + fwidth(uv.x * 2400.0);
		w *= clamp(1.0 - wf * 0.6, 0.0, 1.0);
		col += vec3(0.03, 0.05, 0.06) * w * clamp(40.0 / cam_dist, 0.0, 1.0);
		col = mix(col, vec3(0.55, 0.7, 0.72), coast * 0.5);
		vec3 n = normalize(vec3(w * 0.05, 1.0, w * 0.03));
		NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
		ROUGHNESS = 0.35;
		SPECULAR = 0.6;
	}
	// era tone: older eras read like aged campaign maps
	float lum = dot(col, vec3(0.299, 0.587, 0.114));
	vec3 sepia = vec3(lum * 1.08, lum * 0.95, lum * 0.74);
	col = mix(col, sepia, era_sepia) * era_tint;
	ALBEDO = col;
}
