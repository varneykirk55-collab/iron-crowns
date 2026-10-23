// Static prop / vehicle: vertex colours, team tint mask in UV2.y (glTF flips V, so mask = 1 - v).
// Visual pass (vis_pass = 1, set per battle material by scripts/battle/battle_visuals.gd for c19): material classes
// from UV.v (pipeline common.MAT_*), cheap contact darkening. vis_pass = 0 (default) = legacy look (world map etc.).
shader_type spatial;
render_mode cull_back;
uniform vec4 team_color : source_color = vec4(0.8, 0.2, 0.2, 1.0);
uniform float brightness = 1.0;
uniform float vis_pass = 0.0;
varying float team_amt;
varying float mat_id;
varying float rest_h;
void vertex() {
	team_amt = 1.0 - UV2.y;
	mat_id = (1.0 - UV.y) * 16.0;
	rest_h = VERTEX.y;
}
void fragment() {
	vec3 base = COLOR.rgb;
	float ta = clamp(team_amt, 0.0, 1.0);
	if (vis_pass < 0.5) {
		ALBEDO = mix(base, base * team_color.rgb * 1.15, ta) * brightness;
		ROUGHNESS = 0.8;
	} else {
		int m = int(mat_id + 0.5);
		vec3 tc = team_color.rgb;
		float tl = dot(tc, vec3(0.299, 0.587, 0.114));
		vec3 tdeep = clamp(mix(vec3(tl), tc, mix(1.12, 2.4, smoothstep(0.45, 0.75, tl))), vec3(0.0), vec3(1.0)) * mix(1.0, 0.76, smoothstep(0.45, 0.8, tl));
		vec3 alb = mix(base, base * tdeep * 1.15, ta);
		float rough = 0.8; float metal = 0.0; float spec = 0.4;
		if (m == 2) { rough = 0.42; spec = 0.6; }
		else if (m == 3) { rough = 0.3; metal = 0.85; spec = 0.6; }
		else if (m == 4) { rough = 0.36; metal = 0.8; spec = 0.6; }
		else if (m == 6) { rough = 0.6; spec = 0.35; }
		else if (m == 9) { rough = 1.0; spec = 0.1; }
		else if (m == 10) { rough = 0.5; metal = 0.6; spec = 0.5; }
		float ao = mix(0.6, 1.0, smoothstep(0.0, 0.6, rest_h));
		ALBEDO = alb * brightness * mix(1.0, ao, 0.6);
		AO = ao;
		ROUGHNESS = rough;
		METALLIC = metal;
		SPECULAR = spec;
	}
}
