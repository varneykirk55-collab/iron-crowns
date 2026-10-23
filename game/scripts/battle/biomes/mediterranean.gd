extends RefCounted
## Mediterranean biome (the Med basin 30-45 N, California, central Chile, southern Australia): summer-dry hill
## country. Open fields and terraces with olive groves, umbrella pines and cypress lines, dark evergreen holm-oak
## woods and maquis on the slopes, low grey garrigue on the rocky ground, pale limestone and red terra-rossa soil.
## Sub-regions:
##   coast (Iberian / Provençal / Italian / Greek / Albanian / Levantine / Cypriot / Maltese lowland + Anatolian
##     Aegean side): olive, umbrella pine, cypress, holm oak, Aleppo pine; maquis + garrigue; karst limestone.
##   interior (sub-Mediterranean: Atlantic N Spain, Pyrenees, Balkan interior from ~41.4 N): deciduous downy /
##     Turkey oak woods with black pine, a little holm oak, scrub; browner soil, fewer olives / no stone pine.
##   anatolia (Anatolian / Armenian / Caucasus plateau, >= 37 N, lon >= 30, elev >= 0.9): open dry upland, scrub
##     oak, juniper and pine in scattered patches, grey cushion steppe, paler soil.
##   california: coast live oak + valley oak + grey pine over golden grass, chaparral and sage (drier, sparser on
##     the high Great Basin side).
##   chile: matorral of peumo / quillay evergreens (holm-oak model) with roble, dense sclerophyll scrub.
##   australia: eucalypt open woodland over golden grass, grey mallee / saltbush scrub, red soil.
## Season: summer-dry climate from the battle month and hemisphere (north: dry Jun-Oct; south: dry Dec-Apr).
## Wet = green winter-spring flush; dry = sun-bleached golden grass, dusty olive leaves, warm summer haze.
## Override: --env-season=wet|dry (summer / autumn map to dry).

static func season(lat: float) -> String:
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--env-season="):
			return "dry" if s.substr(13) in ["dry", "summer", "autumn"] else "wet"
	var ml := Engine.get_main_loop() as SceneTree
	var sim: Node = ml.root.get_node_or_null("Sim") if ml else null
	if sim == null or not sim.has_method("date_parts"):
		return "dry"
	var m: int = int(sim.call("date_parts")[1])          # 0 = January
	if lat < 0.0:
		m = (m + 6) % 12
	return "dry" if (m >= 5 and m <= 9) else "wet"

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var lon: float = b["lon"]; var elev: float = b["elev"]
	var sub := "coast"
	if lon < -100.0: sub = "california"
	elif lon < -30.0: sub = "chile"
	elif lon > 100.0: sub = "australia"
	elif lon >= 30.0 and lat >= 37.0 and elev >= 0.9: sub = "anatolia"
	elif (lat >= 42.3 and lon < -1.5) or elev >= 1.5 or (lon >= 17.0 and lon < 30.0 and lat >= 41.4): sub = "interior"
	b["sub"] = sub
	var wet := season(lat) == "wet"
	b["season"] = "wet" if wet else "dry"
	var hills := terr in ["hills", "mountains"]
	var high := elev >= 1.4

	# --- structure: field / grove / wood mosaic; woods thicken on the slopes, the high and dry sides open up
	var wood: float = {"coast": 0.45, "interior": 0.62, "anatolia": 0.25, "california": 0.4, "chile": 0.45, "australia": 0.5}[sub]
	if high and sub == "california": wood = 0.22                  # Great Basin side: pinyon-juniper scatter
	b["forest"] = clampf(wood + (0.08 if hills else 0.0), 0.15, 0.75)
	b["tree_cell"] = 10.0 - wood * 3.0; b["tree_p"] = 0.3 + wood * 0.45; b["tree_scale"] = Vector2(0.8, 1.2)
	var dry_sub := 0.12 if (sub == "anatolia" or (sub == "california" and high)) else (-0.12 if sub == "interior" else 0.0)
	b["dry"] = (0.6 if not wet else 0.25) + dry_sub
	b["rocks"] = clampf(float(b["rocks"]) * 0.9 + (0.3 if sub in ["coast", "anatolia", "interior"] else 0.1) + (0.15 if hills else 0.0), 0.3, 1.5)
	b["relief"] = float(b["relief"]) * 0.95
	b["lake"] = bool(b["coastal"]) and sub in ["coast", "california", "chile", "australia"] or (int(b["seed"]) % 3) == 0
	b["shore"] = "env_reeds"; b["shore_n"] = 260

	var t: Array = []; var lone: Array = []; var sh: Array = []
	var gar := {"m": "env_garrigue", "n": 1500, "fmin": -1.0, "fmax": 0.85, "r": 0.8, "s": Vector2(0.8, 1.4), "tier": 0.3}
	var maq := {"m": "env_maquis", "n": 1400, "fmin": -0.2, "fmax": 1.01, "r": 1.0, "s": Vector2(0.8, 1.4), "tier": 0.45}
	match sub:
		"coast":
			t = [["env_olive_a", 0.22, 0.4], ["env_olive_b", 0.14, 0.5], ["env_stone_pine", 0.17, 0.2], ["env_holm_oak", 0.22, -0.3],
				["env_aleppo_pine", 0.13, -0.1], ["env_cypress", 0.12, 0.6]]
			lone = ["env_olive_a", "env_stone_pine", "env_cypress", "env_olive_b", "env_cypress", "env_holm_oak"]
			sh = [maq, gar]
		"interior":
			t = [["env_oak_dec", 0.5, -0.2], ["env_aleppo_pine", 0.28, 0.0], ["env_holm_oak", 0.14, 0.2], ["env_cypress", 0.04, 0.6], ["env_olive_b", 0.04, 0.6]]
			lone = ["env_oak_dec", "env_oak_dec", "env_aleppo_pine", "env_holm_oak"]
			maq["n"] = 1000; gar["n"] = 700
			sh = [maq, gar, {"m": "env_juniper", "n": 260, "fmin": -1.0, "fmax": 1.01, "r": 0.8, "s": Vector2(0.7, 1.1), "tier": 0.4}]
		"anatolia":
			t = [["env_oak_dec", 0.42, 0.0], ["env_juniper", 0.3, 0.3], ["env_aleppo_pine", 0.28, -0.2]]
			lone = ["env_oak_dec", "env_aleppo_pine", "env_oak_dec"]
			maq["n"] = 500; gar["n"] = 1900; gar["fmax"] = 1.01
			sh = [gar, maq, {"m": "env_juniper", "n": 380, "fmin": -1.0, "fmax": 1.01, "r": 0.8, "s": Vector2(0.6, 1.0), "tier": 0.4}]
		"california":
			if high:
				t = [["env_juniper", 0.5, 0.2], ["env_aleppo_pine", 0.4, 0.0], ["env_holm_oak", 0.1, 0.0]]
				lone = ["env_juniper", "env_aleppo_pine"]
				maq["n"] = 500; gar["n"] = 2000; gar["fmax"] = 1.01
				sh = [gar, maq]
			else:
				t = [["env_holm_oak", 0.5, 0.0], ["env_oak_dec", 0.22, 0.5], ["env_aleppo_pine", 0.28, -0.2]]
				lone = ["env_oak_dec", "env_holm_oak", "env_holm_oak", "env_aleppo_pine"]
				maq["n"] = 1700; gar["n"] = 900
				sh = [maq, gar]
		"chile":
			t = [["env_holm_oak", 0.65, 0.0], ["env_oak_dec", 0.35, -0.3]]
			lone = ["env_holm_oak", "env_oak_dec"]
			maq["n"] = 2000; gar["n"] = 700
			sh = [maq, gar]
		_:   # australia
			t = [["env_eucalypt", 0.8, 0.0], ["env_holm_oak", 0.2, -0.2]]
			lone = ["env_eucalypt", "env_eucalypt", "env_eucalypt", "env_holm_oak"]
			maq["n"] = 1200; gar["n"] = 1100; gar["fmax"] = 1.01
			sh = [maq, gar]
	b["trees"] = t; b["lone"] = lone; b["shrubs"] = sh
	b["accents"] = [{"m": "env_garrigue", "open": 0.06, "knoll": 0.14, "s": Vector2(0.6, 1.0)}]
	b["far_model"] = "env_med_far"; b["far_dens"] = 0.55 + wood * 0.7; b["far_scale"] = Vector2(1.0, 1.5)
	b["outcrop"] = "env_karst"; b["boulders"] = ["env_limestone_a", "env_limestone_b", "env_limestone_a"]
	b["cover_main"] = "env_med_grass"; b["cover_cell"] = 3.0; b["cover_p"] = 0.9; b["cover_in"] = 0.3

	# --- ground palette: red terra rossa on the limestone coasts, browner interior soils, pale Anatolian plateau
	var soil: Color = {"coast": Color(0.55, 0.35, 0.25), "interior": Color(0.44, 0.34, 0.25), "anatolia": Color(0.58, 0.48, 0.36),
		"california": Color(0.5, 0.4, 0.29), "chile": Color(0.47, 0.36, 0.27), "australia": Color(0.57, 0.36, 0.24)}[sub]
	var green := Color(0.31, 0.41, 0.17)
	if sub == "interior": green = Color(0.27, 0.39, 0.15)
	var straw := Color(0.74, 0.63, 0.38)
	var dryk := 0.0 if sub == "interior" else (0.12 if dry_sub > 0.0 else 0.0)
	var gr_a := green.lerp(straw * 0.88, (0.25 if wet else 0.72) + dryk)
	var gr_b := green.lerp(straw, (0.4 if wet else 0.86) + dryk)
	var rock := Color(0.7, 0.67, 0.6) if sub in ["coast", "interior", "anatolia"] else Color(0.6, 0.55, 0.49)
	b["palette"] = {"grass_a": gr_a, "grass_b": gr_b, "dry": straw.lerp(Color(0.84, 0.76, 0.54), 0.4), "earth": soil,
		"floor_col": soil.lerp(gr_a, 0.45) * 0.86, "needle": soil * 0.8, "rock": rock, "scree": soil.lerp(rock, 0.55),
		"snow_col": Color(0.9, 0.92, 0.95), "far_forest": Color(0.22, 0.26, 0.13) if wet else Color(0.27, 0.28, 0.15),
		"straw": Color(0.88, 0.76, 0.46) if not wet else Color(0.6, 0.66, 0.34)}
	var leaf := [Color(0.92, 0.95, 0.86), Color(0.03, 0.03, 0.01)] if wet else [Color(0.98, 0.94, 0.8), Color(0.05, 0.04, 0.01)]
	var olive := [Color(0.98, 1.0, 0.96), Color(0.04, 0.04, 0.03)]
	var grass := [Color(0.66, 0.84, 0.5), Color(0.06, 0.08, 0.02)] if wet else [Color(1.08, 0.98, 0.84), Color(0.12, 0.1, 0.04)]
	var lime := [Color(1.0, 0.99, 0.97), Color(0.04, 0.04, 0.03)]
	if not (sub in ["coast", "interior", "anatolia"]): lime = [Color(0.92, 0.84, 0.76), Color(0.03, 0.01, 0.0)]  # granite / sandstone
	var scrub := leaf
	if sub == "australia": scrub = [Color(0.92, 0.98, 1.0), Color(0.04, 0.04, 0.04)]   # grey-blue mallee / saltbush
	b["tints"] = {"env_stone_pine": leaf, "env_cypress": leaf, "env_olive_a": olive, "env_olive_b": olive, "env_holm_oak": leaf,
		"env_oak_dec": leaf, "env_aleppo_pine": leaf if sub != "interior" else [Color(0.78, 0.84, 0.8), Color(0.0, 0.0, 0.0)],
		"env_eucalypt": [Color(0.96, 1.0, 1.02), Color(0.04, 0.04, 0.04)], "env_juniper": leaf,
		"env_maquis": scrub, "env_garrigue": scrub, "env_med_grass": grass,
		"env_karst": lime, "env_limestone_a": lime, "env_limestone_b": lime,
		"env_reeds": [Color(0.85, 0.9, 0.62), Color(0.12, 0.1, 0.05)], "env_med_far": [Color(0.95, 0.95, 0.88), Color(0.1, 0.1, 0.06)]}
	# --- light: clear, deep blue sky and hard sun; summer = high sun, warm dust haze; winter-spring = lower, crisper
	var haze := Color(0.82, 0.8, 0.74) if not wet else Color(0.76, 0.82, 0.88)
	b["look"] = {"sky_top": Color(0.26, 0.47, 0.8) if wet else Color(0.3, 0.5, 0.78), "sky_horizon": Color(0.8, 0.86, 0.92) if wet else Color(0.88, 0.86, 0.8),
		"ground_horizon": Color(0.7, 0.64, 0.52), "ground_bottom": Color(0.32, 0.27, 0.2),
		"ambient": 0.86, "exposure": 0.98, "contrast": 1.06, "saturation": 0.97 if wet else 0.93,
		"fog_begin": 320.0, "fog_end": 5600.0 if wet else 4600.0, "fog_density": 0.46 if wet else 0.58, "fog_color": haze, "fog_scatter": 0.3, "fog_sky": 0.34,
		"sun_rot": Vector3(-44.0 if wet else -60.0, 200.0, 0.0), "sun_color": Color(1.0, 0.95, 0.86) if wet else Color(1.0, 0.94, 0.8),
		"sun_energy": 1.5 if wet else 1.7, "shadow_opacity": 0.84}
	b["water"] = {"deep": Color(0.04, 0.1, 0.13), "sky": Color(0.64, 0.76, 0.86)}
	b["mats"] = {"tree": 2.1, "rock": 1.5, "cover": 1.0, "far": 2.1, "wind": 0.6}
	return b
