extends RefCounted
## Temperate biome (eastern / midwestern North America, Atlantic & central Europe below 57 N, New Zealand ...):
## deciduous and mixed forest of white oak, maple and ash with eastern white pine, a hazel / bracken understorey,
## meadow grass and wildflowers in the open, buff limestone ledges. Sub-regions from the data:
##   * Americas west of 100 W on hills / mountains (Rockies, Cascades): conifer forest (spruce / fir, pine), granite.
##   * Americas plains 100..85 W (Midwest prairie / farm belt): open tall-grass country, oak groves, few woods.
##   * Europe: oak / ash / maple woods, Scots pine instead of white pine.
## SEASONAL: the battle date's month (Sim.date_parts, hemisphere-aware; preview override --env-season=spring|summer|
## autumn|winter) sets foliage tints, grass dryness and the sun: autumn reds / golds, winter brown dormant hardwoods.

const SEASONS := ["winter", "winter", "spring", "spring", "spring", "summer", "summer", "summer", "autumn", "autumn", "autumn", "winter"]

static func season(lat: float) -> String:
	var ov := ""
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--env-season="):
			ov = s.substr(13)
	if ov != "":
		return ov
	var ml := Engine.get_main_loop() as SceneTree
	var sim: Node = ml.root.get_node_or_null("Sim") if ml else null
	if sim == null or not sim.has_method("date_parts"):
		return "summer"
	var m: int = int(sim.call("date_parts")[1])
	if lat < 0.0:
		m = (m + 6) % 12
	return SEASONS[clampi(m, 0, 11)]

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var lon: float = b["lon"]; var elev: float = b["elev"]
	var americas := lon >= -130.0 and lon <= -30.0
	var west := americas and lon < -100.0 and terr in ["hills", "mountains"]
	var prairie := americas and lon >= -100.0 and lon < -85.0 and terr == "plains"
	var europe := lon > -12.0 and lon < 45.0
	var sea := season(lat)
	b["season"] = sea
	b["tree_cell"] = 7.0; b["tree_p"] = 0.7
	if prairie:
		b["forest"] = clampf(float(b["forest"]) * 0.45, 0.15, 0.5)
	b["rocks"] = clampf(float(b["rocks"]) + (0.2 if west else -0.1), 0.15, 1.5)
	var pine_m := "env_pine_a" if europe else "env_wpine"
	if west:
		b["trees"] = [["env_spruce_a", 0.3, -0.3], ["env_spruce_b", 0.25, -0.2], ["env_pine_a", 0.25 + elev * 0.2, 0.4],
			["env_wpine", 0.1, 0.0], ["env_ash_t", 0.08, 1.2]]
		b["far_model"] = "env_conifer_far"
		b["lone"] = ["env_pine_a", "env_spruce_b", "env_pine_a"]
		b["outcrop"] = "env_outcrop_a"; b["boulders"] = ["env_boulder_a", "env_boulder_b", "env_boulder_c"]
	else:
		b["trees"] = [["env_oak_a", 0.34 if prairie else 0.26, 0.6], ["env_maple_t", 0.26, 0.0], ["env_ash_t", 0.22, -0.4],
			[pine_m, 0.06 if prairie else (0.26 if lat > 40.0 else 0.16), -0.8]]
		b["far_model"] = "env_hw_far"
		b["lone"] = ["env_oak_a", "env_oak_a", "env_maple_t", "env_oak_a"]
		b["outcrop"] = "env_lime_outcrop"; b["boulders"] = ["env_lime_a", "env_lime_b", "env_lime_c"]
	b["cover_main"] = "env_meadow"; b["cover_p"] = 0.9 if prairie else 0.8
	b["accents"] = [{"m": "env_wildflowers", "open": 0.07 if sea in ["spring", "summer"] else 0.02, "knoll": 0.1, "s": Vector2(0.8, 1.3)},
		{"m": "env_bracken", "rock": 0.07, "s": Vector2(0.8, 1.2)}]
	b["shrubs"] = [{"m": "env_hazel", "n": 1700, "fmin": 0.03, "fmax": 0.9, "r": 1.2, "s": Vector2(1.0, 1.8), "tier": 0.5},
		{"m": "env_bracken", "n": 1200, "fmin": 0.02, "fmax": 1.01, "r": 0.6, "s": Vector2(1.0, 1.7), "tier": 0.5},
		{"m": "env_log", "n": 60, "fmin": 0.3, "fmax": 1.01, "r": 3.0, "s": Vector2(0.7, 1.2), "tier": 1.0}]
	# ---- season
	var g := [Color(0.98, 1.02, 0.92), Color(0.22, 0.18, 0.14)]            # summer green spread
	var maple := g; var oak := g; var ash := g; var under := g; var far := [Color(0.9, 0.95, 0.88), Color(0.14, 0.12, 0.08)]
	var dry := float(b["dry"])
	var grass_a := Color(0.24, 0.36, 0.13); var grass_b := Color(0.38, 0.45, 0.2)
	var sun := Vector3(-46.0, 210.0, 0.0); var sun_c := Color(1.0, 0.95, 0.86); var sun_e := 1.55
	match sea:
		"spring":
			g = [Color(1.08, 1.16, 0.9), Color(0.2, 0.16, 0.12)]; maple = g; oak = g; ash = g; under = g
			grass_a = Color(0.26, 0.4, 0.13)
		"autumn":
			# leaf colours are baked into *_aut models (scarlet maple, russet oak, gold ash) so bark stays bark;
			# the tint only spreads the per-tree variation
			maple = [Color(0.92, 0.9, 0.9), Color(0.3, 0.22, 0.12)]; oak = [Color(0.92, 0.92, 0.9), Color(0.22, 0.18, 0.12)]
			ash = [Color(0.92, 0.92, 0.9), Color(0.25, 0.2, 0.1)]; under = ash; far = [Color(0.95, 0.95, 0.92), Color(0.18, 0.14, 0.1)]
			dry += 0.3; grass_a = Color(0.3, 0.35, 0.15); grass_b = Color(0.46, 0.44, 0.22)
			sun = Vector3(-34.0, 220.0, 0.0); sun_c = Color(1.0, 0.9, 0.76); sun_e = 1.45
		"winter":
			var dead := [Color(0.95, 0.95, 0.95), Color(0.16, 0.14, 0.12)]   # *_win models: thin brown marcescent crowns
			maple = dead; oak = dead; ash = dead; under = dead
			far = [Color(1.4, 1.15, 0.95), Color(0.3, 0.2, 0.15)]
			dry += 0.55; grass_a = Color(0.36, 0.36, 0.22); grass_b = Color(0.48, 0.44, 0.3)
			sun = Vector3(-24.0, 205.0, 0.0); sun_c = Color(0.98, 0.9, 0.8); sun_e = 1.3
	b["dry"] = clampf(dry, 0.0, 1.0)
	b["palette"] = {"grass_a": grass_a, "grass_b": grass_b, "dry": Color(0.58, 0.52, 0.3), "earth": Color(0.33, 0.26, 0.18),
		"floor_col": Color(0.2, 0.2, 0.12) if sea != "summer" else Color(0.16, 0.2, 0.1), "needle": Color(0.36, 0.26, 0.15),
		"rock": Color(0.5, 0.48, 0.43), "scree": Color(0.54, 0.5, 0.44),
		"far_forest": Color(0.1, 0.17, 0.08) if sea in ["spring", "summer"] else Color(0.2, 0.15, 0.09), "straw": Color(0.74, 0.66, 0.42)}
	var stone := [Color(1.05, 1.03, 1.0), Color(0.16, 0.14, 0.12)]
	b["tints"] = {"env_maple_t": maple, "env_oak_a": oak, "env_ash_t": ash, "env_hazel": under, "env_bracken": under,
		"env_hw_far": far, "env_lime_a": stone, "env_lime_b": stone, "env_lime_c": stone, "env_lime_outcrop": stone,
		"env_meadow": [Color(0.86, 0.92, 0.74), Color(0.14, 0.12, 0.08)]}
	# seasonal model swap: hardwoods / far belts / hazel -> *_aut or *_win variants (conifers stay evergreen)
	var suf: String = {"autumn": "_aut", "winter": "_win"}.get(sea, "")
	if suf != "":
		var SW := ["env_oak_a", "env_maple_t", "env_ash_t", "env_hw_far", "env_hazel"]
		for t in b["trees"]:
			if str(t[0]) in SW: t[0] = str(t[0]) + suf
		var lone: Array = []
		for m in b["lone"]: lone.append(str(m) + suf if str(m) in SW else m)
		b["lone"] = lone
		if str(b["far_model"]) in SW: b["far_model"] = str(b["far_model"]) + suf
		for sh in b["shrubs"]:
			if str(sh["m"]) in SW: sh["m"] = str(sh["m"]) + suf
		var tn: Dictionary = b["tints"]
		for m in SW:
			if tn.has(m): tn[m + suf] = tn[m]
	b["look"] = {"sky_top": Color(0.24, 0.43, 0.72), "sky_horizon": Color(0.76, 0.82, 0.86), "ground_horizon": Color(0.6, 0.64, 0.62),
		"ground_bottom": Color(0.22, 0.24, 0.18), "ambient": 0.86, "exposure": 1.0, "contrast": 1.04, "saturation": 0.98,
		"fog_begin": 260.0, "fog_end": 4600.0, "fog_density": 0.6, "fog_color": Color(0.74, 0.8, 0.86), "fog_scatter": 0.2, "fog_sky": 0.3,
		"sun_rot": sun, "sun_color": sun_c, "sun_energy": sun_e, "shadow_opacity": 0.78}
	b["water"] = {"deep": Color(0.04, 0.08, 0.1), "sky": Color(0.64, 0.74, 0.82)}
	return b
