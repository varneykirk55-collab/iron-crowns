extends RefCounted
## East Asian biome (Japan, Taiwan, Korea, eastern / southern China): varied green hill country. Sugi cedar and
## Japanese red pine on the slopes, evergreen broadleaf (camphor / evergreen oak) and maple below, bamboo groves at the
## forest edge, a sasa dwarf-bamboo and azalea understorey, susuki silver grass on the knolls, mossy grey andesite.
## Latitude gradient: Hokkaido / Manchuria (>= 41 N) add Ezo spruce + white birch, more sasa; the subtropical south
## (< 28 N: Okinawa, Taiwan, Guangdong / Fujian) is broadleaf + bamboo dominated with lusher greens; Korea is red-pine
## country. Soft, humid, slightly hazy light.

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var elev: float = b["elev"]
	var region: String = b["region"]
	var north: float = clampf((lat - 38.0) / 6.0, 0.0, 1.0)        # 0 = Honshu / Korea, 1 = Hokkaido / Jilin
	var south: float = clampf((30.0 - lat) / 6.0, 0.0, 1.0)        # 1 = Okinawa / Taiwan / Guangdong
	var korea: bool = region in ["North Korea", "South Korea"]
	var farm: bool = region == "China" and terr == "plains"         # Yangtze / north China plain: farmland, groves
	b["forest"] = clampf(float(b["forest"]) * (0.65 if farm else 1.0) + (0.15 if terr in ["hills", "mountains"] else 0.0), 0.25, 1.0)
	b["dry"] = float(b["dry"]) * 0.6
	b["rocks"] = clampf(float(b["rocks"]) + (0.15 if terr in ["hills", "mountains"] else 0.0), 0.2, 1.4)
	b["tree_cell"] = 6.8; b["tree_p"] = 0.74
	var pine := (0.34 if korea else 0.2) * (1.0 - south * 0.6) + elev * 0.15
	var sugi := 0.3 * (1.0 - south * 0.75) * (1.0 - north * 0.6) * (0.4 if korea else 1.0) + elev * 0.1
	var broad := 0.26 + south * 0.3
	var maple := 0.12 + north * 0.05
	var bamboo := 0.03 * (1.0 - north) + south * 0.04
	b["trees"] = [["env_sugi_a", sugi * 0.55, -0.6], ["env_sugi_b", sugi * 0.45, -0.3], ["env_jpine_a", pine * 0.6, 0.3],
		["env_jpine_b", pine * 0.4, 0.8], ["env_broadleaf_a", broad, 0.0], ["env_maple_a", maple, 0.9], ["env_bamboo", bamboo, 1.4]]
	if north > 0.0:
		b["trees"].append(["env_spruce_a", 0.3 * north, -0.5])
		b["trees"].append(["env_birch_a", 0.18 * north, 1.0])
	b["lone"] = ["env_jpine_a", "env_jpine_b", "env_maple_a", "env_broadleaf_a", "env_jpine_a"]
	b["far_model"] = "env_ea_far"; b["far_dens"] = 1.05
	b["outcrop"] = "env_andesite_outcrop"; b["boulders"] = ["env_andesite_a", "env_andesite_b", "env_andesite_c"]
	b["cover_main"] = "env_grass_tuft"; b["cover_p"] = 0.85
	b["accents"] = [{"m": "env_susuki", "knoll": 0.3, "open": 0.05, "s": Vector2(0.8, 1.3)},
		{"m": "env_azalea", "rock": 0.06, "s": Vector2(0.6, 1.0)}]
	b["shrubs"] = [{"m": "env_sasa", "n": 2400 + int(north * 1200.0), "fmin": 0.02, "fmax": 1.01, "r": 0.9, "s": Vector2(1.3, 2.3), "tier": 0.5},
		{"m": "env_azalea", "n": 420, "fmin": 0.03, "fmax": 0.7, "r": 0.8, "s": Vector2(0.8, 1.3), "tier": 0.6},
		{"m": "env_bamboo", "n": int(160 * (1.0 - north) + south * 160.0), "fmin": 0.05, "fmax": 0.6, "r": 1.8, "s": Vector2(0.8, 1.1), "tier": 0.8}]
	b["palette"] = {"grass_a": Color(0.24, 0.36, 0.14).lerp(Color(0.2, 0.36, 0.12), south), "grass_b": Color(0.36, 0.44, 0.2),
		"dry": Color(0.56, 0.52, 0.32), "earth": Color(0.3, 0.24, 0.18), "floor_col": Color(0.16, 0.22, 0.11),
		"needle": Color(0.32, 0.24, 0.15), "rock": Color(0.42, 0.41, 0.39), "scree": Color(0.46, 0.44, 0.4),
		"far_forest": Color(0.09, 0.16, 0.09), "straw": Color(0.72, 0.68, 0.48)}
	var leaf := [Color(0.98, 1.02, 0.92), Color(0.24, 0.2, 0.16)]
	b["tints"] = {"env_sugi_a": leaf, "env_sugi_b": leaf, "env_bamboo": [Color(0.78, 0.84, 0.7), Color(0.16, 0.14, 0.1)], "env_broadleaf_a": leaf, "env_maple_a": leaf, "env_jpine_a": leaf, "env_jpine_b": leaf,
		"env_sasa": [Color(0.72, 0.8, 0.66), Color(0.2, 0.16, 0.1)], "env_azalea": [Color(0.8, 0.84, 0.76), Color(0.2, 0.16, 0.12)],
		"env_grass_tuft": [Color(0.78, 0.92, 0.66), Color(0.14, 0.12, 0.08)],
		"env_birch_a": [Color(0.38, 0.4, 0.33), Color(0.05, 0.06, 0.05)],
		"env_andesite_a": [Color(1.5, 1.48, 1.44), Color(0.2, 0.18, 0.16)], "env_andesite_b": [Color(1.5, 1.48, 1.44), Color(0.2, 0.18, 0.16)],
		"env_andesite_c": [Color(1.5, 1.48, 1.44), Color(0.2, 0.18, 0.16)],
		"env_andesite_outcrop": [Color(1.5, 1.48, 1.44), Color(0.2, 0.18, 0.16)],
		"env_ea_far": [Color(0.86, 0.92, 0.86), Color(0.14, 0.12, 0.08)]}
	b["look"] = {"sky_top": Color(0.3, 0.46, 0.7), "sky_horizon": Color(0.78, 0.82, 0.84), "ground_horizon": Color(0.62, 0.66, 0.66),
		"ground_bottom": Color(0.2, 0.24, 0.18), "ambient": 0.88, "exposure": 1.0, "contrast": 1.03, "saturation": 0.96,
		"fog_begin": 180.0, "fog_end": 3400.0, "fog_density": 0.72, "fog_color": Color(0.74, 0.79, 0.82), "fog_scatter": 0.22, "fog_sky": 0.34,
		"sun_rot": Vector3(-44.0, 215.0, 0.0), "sun_color": Color(1.0, 0.96, 0.88), "sun_energy": 1.5, "shadow_opacity": 0.78}
	b["water"] = {"deep": Color(0.04, 0.09, 0.1), "sky": Color(0.66, 0.74, 0.8)}
	return b
