extends RefCounted
## Savanna biome (sub-Saharan Africa outside the rainforest and desert belts, the Indian Deccan, Brazilian campos /
## NE Argentina, Madagascar): open grassland on red-brown laterite with trees standing apart, never a closed wall.
## Sub-regions:
##   bushveld (Africa south of ~20 S: Transvaal, Zimbabwe south, Mozambique south, Natal): umbrella thorn, candelabra
##     euphorbia, thorn scrub, the odd baobab, granite kopjes.
##   miombo (Africa 8-20 S: Zambia, Angola, Malawi, Katanga, N Mozambique, SE Tanzania, Zimbabwe north): open
##     Brachystegia woodland, more trees, termite mounds, granite domes.
##   sudan / guinea savanna + Sahel (Africa north of the equatorial belt: Nigeria, Chad, South Sudan, Guinea coast):
##     umbrella thorn and baobab over tall grass, termite mounds; drier and paler towards the Sahel.
##   deccan (India): dry-deciduous woodland (teak / sal stand-in), thorn scrub, a few acacia, Deccan granite tors.
##   campos (South America): rolling grass with scattered gnarled cerrado trees and termite mounds, no baobab /
##     euphorbia; greener on the humid campos of the south (Rio Grande do Sul).
##   highland (Ethiopian / Lesotho / Malagasy highlands, Kathmandu, Atlantic islands; elev >= 1.4 or mountains):
##     greener montane grassland, few trees.
## Season: tropical wet / dry season from the battle month and hemisphere (north: dry Nov-Apr; south: dry May-Oct;
## the Indian monsoon keeps the north rule). Dry = golden straw, grey-olive leaves, dust haze; wet = green flush.
## Override: --env-season=wet|dry.

static func season(lat: float) -> String:
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--env-season="):
			return "dry" if s.substr(13) in ["dry", "winter", "autumn"] else "wet"
	var ml := Engine.get_main_loop() as SceneTree
	var sim: Node = ml.root.get_node_or_null("Sim") if ml else null
	if sim == null or not sim.has_method("date_parts"):
		return "dry"
	var m: int = int(sim.call("date_parts")[1])          # 0 = January
	if lat < 0.0:
		m = (m + 6) % 12
	return "dry" if (m <= 3 or m >= 10) else "wet"

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var lon: float = b["lon"]; var elev: float = b["elev"]
	var americas := lon < -30.0
	var india := lon >= 60.0 and not americas
	var mada := lon >= 42.0 and lon <= 51.0 and lat < -11.0
	var highland := (elev >= 1.4 or terr == "mountains") and not americas
	var sahel := not americas and not india and lat >= 11.0
	var sudan := not americas and not india and lat > 0.0 and not sahel
	var miombo := not americas and not india and not mada and lat <= -7.0 and lat > -19.5
	var bushveld := not americas and not india and not mada and lat <= -19.5
	var wet := season(lat) == "wet"
	b["season"] = "wet" if wet else "dry"
	var sub := "campos" if americas else ("deccan" if india else ("highland" if highland else ("madagascar" if mada else
		("sahel" if sahel else ("sudan" if sudan else ("miombo" if miombo else "bushveld"))))))
	b["sub"] = sub
	var hills := terr in ["hills", "mountains"]

	# --- structure: open ground, trees in scattered groves (never the boreal / tropical wall)
	var wood: float = {"miombo": 0.62, "deccan": 0.55, "sudan": 0.45, "bushveld": 0.38, "campos": 0.3, "sahel": 0.22,
		"highland": 0.25, "madagascar": 0.3}[sub]
	b["forest"] = clampf(wood + (0.08 if hills else 0.0), 0.15, 0.75)
	b["tree_cell"] = 10.5 - wood * 3.0; b["tree_p"] = 0.3 + wood * 0.45; b["tree_scale"] = Vector2(0.8, 1.2)
	b["dry"] = (0.62 if not wet else 0.28) + (0.12 if sub == "sahel" else 0.0) - (0.15 if sub in ["highland", "campos"] else 0.0)
	b["rocks"] = clampf(float(b["rocks"]) * 0.8 + (0.25 if sub in ["bushveld", "miombo", "deccan"] else 0.0), 0.25, 1.4)
	b["relief"] = float(b["relief"]) * 0.85
	b["snow_h"] = maxf(float(b["snow_h"]), 4800.0); b["treeline"] = float(b["snow_h"]) - 700.0
	b["lake"] = bool(b["coastal"]) or (int(b["seed"]) % 3) == 0     # coast / pan / river pool
	b["shore"] = "env_reeds"; b["shore_n"] = 300

	var t: Array = []; var lone: Array = []
	var sh: Array = []
	var termites := 0.0
	match sub:
		"bushveld":
			t = [["env_umbrella_a", 0.42, 0.2], ["env_umbrella_b", 0.3, 0.0], ["env_miombo_b", 0.12, -0.3], ["env_baobab", 0.06, 0.6], ["env_euphorbia", 0.1, 0.4]]
			lone = ["env_umbrella_a", "env_umbrella_a", "env_baobab", "env_umbrella_b", "env_euphorbia"]
			sh = [{"m": "env_thornbush", "n": 1500, "fmin": -1.0, "fmax": 0.9, "r": 1.0, "s": Vector2(0.8, 1.4), "tier": 0.4},
				{"m": "env_euphorbia", "n": 120, "fmin": -1.0, "fmax": 0.6, "r": 0.8, "s": Vector2(0.7, 1.1), "tier": 0.3}]
			termites = 0.5
		"miombo":
			t = [["env_miombo_a", 0.5, -0.2], ["env_miombo_b", 0.36, 0.0], ["env_umbrella_b", 0.08, 0.5], ["env_baobab", 0.04, 0.8]]
			lone = ["env_miombo_a", "env_miombo_b", "env_baobab", "env_umbrella_b"]
			sh = [{"m": "env_thornbush", "n": 1300, "fmin": 0.0, "fmax": 1.01, "r": 1.0, "s": Vector2(0.9, 1.5), "tier": 0.45}]
			termites = 1.0
		"sudan", "sahel":
			var sa := sub == "sahel"
			t = [["env_umbrella_a", 0.42, 0.1], ["env_umbrella_b", 0.3 + (0.2 if sa else 0.0), 0.0], ["env_baobab", 0.12, 0.6], ["env_miombo_b", 0.0 if sa else 0.22, -0.3]]
			lone = ["env_baobab", "env_umbrella_a", "env_umbrella_b", "env_baobab"]
			sh = [{"m": "env_thornbush", "n": 900 if sa else 1300, "fmin": -1.0, "fmax": 0.9, "r": 1.0, "s": Vector2(0.7, 1.3), "tier": 0.4}]
			termites = 0.5 if sa else 0.9
		"deccan":
			t = [["env_miombo_a", 0.45, -0.2], ["env_miombo_b", 0.3, 0.0], ["env_umbrella_b", 0.18, 0.4], ["env_euphorbia", 0.05, 0.5]]
			lone = ["env_miombo_a", "env_umbrella_b", "env_miombo_b"]
			sh = [{"m": "env_thornbush", "n": 1700, "fmin": -1.0, "fmax": 1.01, "r": 1.0, "s": Vector2(0.8, 1.4), "tier": 0.4}]
			termites = 0.3
		"campos":
			t = [["env_miombo_b", 0.6, 0.0], ["env_miombo_a", 0.25, -0.3], ["env_umbrella_b", 0.15, 0.4]]
			lone = ["env_miombo_b", "env_miombo_a"]
			sh = [{"m": "env_thornbush", "n": 900, "fmin": -1.0, "fmax": 1.01, "r": 1.0, "s": Vector2(0.8, 1.3), "tier": 0.4}]
			termites = 0.8 if lat > -27.0 else 0.2
		_:   # highland / madagascar
			t = [["env_miombo_b", 0.5, -0.2], ["env_umbrella_b", 0.3, 0.2], ["env_euphorbia", 0.2 if sub == "madagascar" else 0.1, 0.4]]
			lone = ["env_miombo_b", "env_umbrella_b"]
			sh = [{"m": "env_thornbush", "n": 800, "fmin": -1.0, "fmax": 1.01, "r": 1.0, "s": Vector2(0.8, 1.3), "tier": 0.4}]
			termites = 0.1
	if termites > 0.0:   # termite mounds: hard obstacles off the corridor, a few in the open bush
		sh.append({"m": "env_termite_a", "n": int(160.0 * termites), "fmin": -1.0, "fmax": 1.01, "r": 1.2, "s": Vector2(0.8, 1.3), "tier": 0.6})
		sh.append({"m": "env_termite_b", "n": int(240.0 * termites), "fmin": -1.0, "fmax": 1.01, "r": 1.0, "s": Vector2(0.8, 1.3), "tier": 0.6})
	b["trees"] = t; b["lone"] = lone; b["shrubs"] = sh
	b["accents"] = [{"m": "env_thornbush", "open": 0.05, "knoll": 0.1, "s": Vector2(0.5, 0.8)}]
	b["far_model"] = "env_sav_far"; b["far_dens"] = 0.5 + wood * 0.7; b["far_scale"] = Vector2(1.0, 1.5)
	b["outcrop"] = "env_kopje"; b["boulders"] = ["env_kopje_a", "env_kopje_b", "env_kopje_a"]
	b["cover_main"] = "env_sav_grass"; b["cover_cell"] = 3.0; b["cover_p"] = 0.92; b["cover_in"] = 0.3

	# --- ground palette: red laterite (Africa / Deccan / cerrado), darker black-cotton soil on the Deccan basalt
	var soil := Color(0.5, 0.33, 0.22)
	if india: soil = Color(0.42, 0.32, 0.24)
	if sub == "sahel": soil = Color(0.62, 0.45, 0.3)
	if sub in ["highland", "campos"]: soil = Color(0.44, 0.3, 0.2)
	var green := Color(0.3, 0.4, 0.15)
	var straw := Color(0.66, 0.56, 0.32)
	if sub in ["highland", "campos"]: green = Color(0.26, 0.38, 0.14)
	var gr_a := green.lerp(straw * 0.86, 0.35 if wet else 0.72)
	var gr_b := green.lerp(straw, 0.5 if wet else 0.88)
	b["palette"] = {"grass_a": gr_a, "grass_b": gr_b, "dry": straw.lerp(Color(0.78, 0.68, 0.44), 0.4), "earth": soil,
		"floor_col": soil.lerp(gr_a, 0.5) * 0.88, "needle": soil * 0.85, "rock": Color(0.55, 0.51, 0.46), "scree": soil.lerp(Color(0.5, 0.46, 0.4), 0.5),
		"snow_col": Color(0.9, 0.92, 0.95), "far_forest": Color(0.24, 0.27, 0.13) if wet else Color(0.32, 0.3, 0.17),
		"straw": Color(0.86, 0.74, 0.44) if not wet else Color(0.62, 0.66, 0.34)}
	var leaf := [Color(0.76, 0.78, 0.64), Color(0.2, 0.16, 0.1)] if wet else [Color(0.9, 0.76, 0.58), Color(0.22, 0.16, 0.08)]
	var grass := [Color(0.62, 0.8, 0.5), Color(0.1, 0.12, 0.04)] if wet else [Color(1.0, 0.94, 0.82), Color(0.12, 0.1, 0.05)]
	var gran := [Color(1.04, 0.98, 0.92), Color(0.14, 0.12, 0.1)]
	if india: gran = [Color(0.98, 0.9, 0.84), Color(0.14, 0.12, 0.1)]
	var mound := [Color(0.8, 0.76, 0.74) if not india else Color(0.7, 0.68, 0.66), Color(0.1, 0.06, 0.04)]
	b["tints"] = {"env_umbrella_a": leaf, "env_umbrella_b": leaf, "env_miombo_a": leaf, "env_miombo_b": leaf, "env_baobab": leaf,
		"env_thornbush": leaf, "env_euphorbia": [Color(0.95, 1.0, 0.9), Color(0.12, 0.14, 0.08)], "env_sav_grass": grass,
		"env_kopje": gran, "env_kopje_a": gran, "env_kopje_b": gran, "env_termite_a": mound, "env_termite_b": mound,
		"env_reeds": [Color(0.85, 0.9, 0.62), Color(0.14, 0.12, 0.06)], "env_sav_far": [Color(0.95, 0.95, 0.85), Color(0.14, 0.12, 0.06)]}
	# --- light: high, hot sun; dry season = dust / smoke haze and a pale sky, wet season = clear and deep blue
	var haze := Color(0.8, 0.76, 0.68) if not wet else Color(0.74, 0.8, 0.84)
	b["look"] = {"sky_top": Color(0.3, 0.5, 0.78) if wet else Color(0.4, 0.54, 0.72), "sky_horizon": Color(0.82, 0.86, 0.88) if wet else Color(0.88, 0.82, 0.72),
		"ground_horizon": Color(0.7, 0.62, 0.48), "ground_bottom": Color(0.32, 0.26, 0.18),
		"ambient": 0.88, "exposure": 0.98, "contrast": 1.06, "saturation": 0.95 if wet else 0.92,
		"fog_begin": 300.0, "fog_end": 5200.0 if wet else 4200.0, "fog_density": 0.5 if wet else 0.62, "fog_color": haze, "fog_scatter": 0.3, "fog_sky": 0.36,
		"sun_rot": Vector3(-56.0, 200.0, 0.0), "sun_color": Color(1.0, 0.94, 0.82), "sun_energy": 1.6, "shadow_opacity": 0.82}
	b["water"] = {"deep": Color(0.08, 0.1, 0.07), "sky": Color(0.72, 0.76, 0.78)}
	b["mats"] = {"tree": 2.1, "rock": 1.5, "cover": 1.0, "far": 2.1, "wind": 0.7}
	return b
