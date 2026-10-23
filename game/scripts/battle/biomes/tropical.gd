extends RefCounted
## Tropical biome (Philippines, Indonesia, Malaysia, Amazon / Orinoco, Congo basin, Caribbean, Central America, Hawaii,
## Pacific islands): the fighting ground is an open grassy clearing (cogon / guinea grass) on red laterite soil, ringed
## by dense multi-layer rainforest outside the corridor: canopy trees with buttress roots, emergents above the canopy,
## coconut palms on the fringes (more on coasts), banana and ferns in the understorey. Rock is dark, mossy basalt.
## Humid, hazy light with a high sun and saturated greens.

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var coastal: bool = b["coastal"]
	var elev: float = b["elev"]
	b["forest"] = maxf(float(b["forest"]), 0.92)                 # jungle walls on every terrain
	b["dry"] = float(b["dry"]) * 0.35                             # wet season green, little straw
	b["rocks"] = clampf(float(b["rocks"]) * 0.7, 0.2, 1.2)
	b["tree_cell"] = 6.4; b["tree_p"] = 0.88; b["tree_scale"] = Vector2(0.75, 1.15)
	var palm := 0.22 if coastal else 0.1
	b["trees"] = [["env_rain_tree_a", 0.36, -0.2], ["env_rain_tree_b", 0.3, 0.4], ["env_rain_emergent", 0.12 + elev * 0.1, -0.9],
		["env_palm_a", palm, 1.6], ["env_palm_b", palm * 0.8, 1.6]]
	b["lone"] = ["env_palm_a", "env_palm_b", "env_palm_a", "env_rain_tree_b", "env_banana"]
	b["far_model"] = "env_tropic_far"; b["far_dens"] = 1.15; b["far_scale"] = Vector2(1.1, 1.6)
	b["outcrop"] = "env_basalt_outcrop"; b["boulders"] = ["env_basalt_a", "env_basalt_b", "env_basalt_c"]
	b["cover_main"] = "env_grass_lush"; b["cover_p"] = 0.95; b["cover_in"] = 0.3
	b["accents"] = [{"m": "env_taro", "knoll": 0.12, "open": 0.07, "s": Vector2(0.8, 1.4)}]
	b["shrubs"] = [{"m": "env_fern", "n": 1600, "fmin": 0.02, "fmax": 1.01, "r": 0.6, "s": Vector2(1.0, 2.0), "tier": 0.5},
		{"m": "env_jungle_bush", "n": 3200, "fmin": 0.06, "fmax": 1.01, "r": 1.3, "s": Vector2(1.0, 2.0), "tier": 0.45},
		{"m": "env_banana", "n": 500, "fmin": 0.05, "fmax": 0.85, "r": 1.4, "s": Vector2(0.8, 1.2), "tier": 0.6}]
	b["shore"] = "env_reeds"; b["shore_n"] = 360
	b["palette"] = {"grass_a": Color(0.2, 0.33, 0.1), "grass_b": Color(0.34, 0.42, 0.16), "dry": Color(0.5, 0.48, 0.24),
		"earth": Color(0.38, 0.25, 0.15), "floor_col": Color(0.12, 0.18, 0.08), "needle": Color(0.3, 0.21, 0.11),
		"rock": Color(0.3, 0.29, 0.27), "scree": Color(0.38, 0.3, 0.24), "far_forest": Color(0.08, 0.17, 0.07),
		"straw": Color(0.6, 0.58, 0.3)}
	var leaf := [Color(0.84, 0.92, 0.78), Color(0.3, 0.22, 0.16)]   # per-tree hue / value spread in the canopy
	var basalt := [Color(1.45, 1.42, 1.36), Color(0.2, 0.18, 0.16)]
	b["tints"] = {"env_rain_tree_a": leaf, "env_rain_tree_b": leaf, "env_rain_emergent": leaf, "env_jungle_bush": [Color(0.6, 0.68, 0.52), Color(0.22, 0.18, 0.12)],
		"env_basalt_a": basalt, "env_basalt_b": basalt, "env_basalt_c": basalt, "env_basalt_outcrop": basalt,"env_reeds": [Color(0.7, 0.95, 0.62), Color(0.12, 0.1, 0.06)],
		"env_tropic_far": [Color(0.86, 0.94, 0.84), Color(0.14, 0.12, 0.06)]}
	b["look"] = {"sky_top": Color(0.28, 0.48, 0.74), "sky_horizon": Color(0.8, 0.84, 0.85), "ground_horizon": Color(0.66, 0.7, 0.68),
		"ground_bottom": Color(0.2, 0.26, 0.16), "ambient": 0.9, "exposure": 1.02, "contrast": 1.04, "saturation": 1.0,
		"fog_begin": 220.0, "fog_end": 3800.0, "fog_density": 0.78, "fog_color": Color(0.76, 0.81, 0.82), "fog_scatter": 0.24, "fog_sky": 0.32,
		"sun_rot": Vector3(-54.0, 205.0, 0.0), "sun_color": Color(1.0, 0.95, 0.85), "sun_energy": 1.65, "shadow_opacity": 0.8}
	b["water"] = {"deep": Color(0.04, 0.1, 0.07), "sky": Color(0.66, 0.76, 0.8)}
	return b
