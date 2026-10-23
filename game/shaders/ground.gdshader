// Battlefield ground: vertex-coloured terrain with procedural variation and trampled earth near the centre.
// Visual pass (vis_pass = 1, c19 via scripts/battle/battle_visuals.gd): less saturated, more tonal variation
// (meadow patches, tussocks, fine speckle through an anisotropic sampler). vis_pass = 0 = legacy look.
shader_type spatial;
uniform vec4 grass_a : source_color = vec4(0.32, 0.42, 0.18, 1.0);
uniform vec4 grass_b : source_color = vec4(0.45, 0.48, 0.24, 1.0);
uniform vec4 dirt : source_color = vec4(0.42, 0.34, 0.24, 1.0);
uniform vec4 rock : source_color = vec4(0.45, 0.43, 0.4, 1.0);
uniform float snow = 0.0;
uniform sampler2D noise_tex : repeat_enable, filter_linear_mipmap;
uniform float vis_pass = 0.0;
uniform sampler2D noise_tex_aniso : repeat_enable, filter_linear_mipmap_anisotropic;
uniform float grass_saturation = 0.82;
uniform float grass_value = 0.82;
// polish pass (battle_visuals.gd, polish = 1): snow gets its own albedo / variation / slush instead of the flat
// near-white that washed out top-down winter views; trampled earth less khaki. polish = 0 = the v0.2.1 look.
uniform float polish = 0.0;
uniform vec3 snow_albedo = vec3(0.69, 0.69, 0.7);
uniform vec3 slush = vec3(0.40, 0.38, 0.36);
varying vec3 wpos;
varying vec3 wnorm;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = NORMAL;
}
void fragment() {
	if (vis_pass < 0.5) {
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
	} else {
		float n1 = texture(noise_tex_aniso, wpos.xz * 0.004).r;
		float n2 = texture(noise_tex_aniso, wpos.xz * 0.031).r;
		float n3 = texture(noise_tex_aniso, wpos.xz * 0.21).r;
		float n4 = texture(noise_tex_aniso, wpos.xz * 0.53 + vec2(0.31, 0.17)).r;
		vec3 ga = grass_a.rgb; vec3 gb = grass_b.rgb;
		// pull the meadow away from saturated lime: desaturate + nudge toward olive
		float la = dot(ga, vec3(0.299, 0.587, 0.114)); float lb = dot(gb, vec3(0.299, 0.587, 0.114));
		ga = mix(vec3(la), ga, grass_saturation) * vec3(0.98, 1.0, 0.96);
		gb = mix(vec3(lb), gb, grass_saturation) * vec3(0.98, 1.0, 0.92);
		vec3 g = mix(ga, gb, smoothstep(0.3, 0.7, n1 * 0.7 + n2 * 0.3));
		// darker tussock patches + fine speckle for tonal depth near the camera
		g *= mix(0.86, 1.05, smoothstep(0.3, 0.7, n2 * 0.65 + n3 * 0.35));
		g *= mix(0.93, 1.04, n4);
		float trample = smoothstep(150.0, 40.0, length(wpos.xz * vec2(0.8, 1.0))) * smoothstep(0.42, 0.62, n2 * 0.6 + n3 * 0.4);
		vec3 d = dirt.rgb * mix(0.85, 1.05, n4);
		g = mix(g, d, trample * 0.5);
		float slope = 1.0 - wnorm.y;
		g = mix(g, rock.rgb * 0.9, smoothstep(0.18, 0.38, slope + (n3 - 0.5) * 0.1));
		if (polish < 0.5) {
			g = mix(g, vec3(0.92, 0.94, 0.97), snow * smoothstep(0.45, 0.6, n1 + n3 * 0.3 + wpos.y * 0.01));
			g *= (0.88 + 0.24 * n3) * grass_value * vec3(0.97, 1.0, 0.97);
			ALBEDO = g;
			ROUGHNESS = 0.95;
			SPECULAR = 0.12;
		} else {
			g *= (0.88 + 0.24 * n3) * grass_value * vec3(0.97, 1.0, 0.97);
			float sm = snow * smoothstep(0.45, 0.6, n1 + n3 * 0.3 + wpos.y * 0.01);
			// wind-packed drifts (large), crust speckle (fine), cool blue in the hollows, tufts poking through
			vec3 sn = snow_albedo * mix(0.8, 1.04, smoothstep(0.25, 0.75, n2 * 0.7 + n1 * 0.3)) * mix(0.95, 1.02, n4);
			sn = mix(sn * vec3(0.94, 0.96, 0.99), sn, smoothstep(0.3, 0.6, n3));
			float tuft = smoothstep(0.6, 0.8, n3 * 0.6 + n4 * 0.4) * 0.45;
			g = mix(g, sn, sm * (1.0 - tuft));
			// trampled snow turns to grey-brown slush where the armies stand (reads as a battlefield from above)
			g = mix(g, slush * mix(0.85, 1.1, n4), sm * trample * 0.6);
			ALBEDO = g;
			ROUGHNESS = mix(0.95, 0.82, sm);
			SPECULAR = mix(0.12, 0.2, sm);
		}
	}
}
