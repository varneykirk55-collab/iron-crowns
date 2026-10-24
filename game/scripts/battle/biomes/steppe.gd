extends RefCounted
## Steppe biome (Kazakh / Pontic-Caspian / Central Asian grassland, the Mongolian plateau and southern Siberian
## forest-steppe, the Tibetan / Pamir / Hindu Kush high steppe, the Great Plains, the pampa and the dry Andean-foot
## monte): an open, nearly treeless sea of grass under a huge sky. Feather grass and wormwood, pea-shrub scrub in the
## hollows, weathered granite tors on the low hills, kurgan burial mounds; trees only in groves, in valleys and on cool
## north slopes. Few obstacles: the openness IS the look (long sightlines, far horizon, low haze).
## Sub-regions (from lat / lon / elev of the province):
##   kazakh (Kazakh uplands + Siberian edge; forest-steppe birch kolki from 50 N): feather grass, wormwood, pea-shrub,
##     birch + cottonwood/poplar groves, granite tors, kurgans.
##   semi (Caspian / Aral / Turan semi-desert, Caspian-Caucasus and Iranian edge: lat < 48.5 and elev < 0.5, or
##     lon < 50): sparse grass on pale sandy-loam, much wormwood, almost no trees (poplar in a river hollow).
##   mongol (Mongolia, Inner Mongolia, Baikal / Altai side, lon >= 88): rolling grass, larch + birch on the north
##     slopes of the mountain / northern provinces, granite tors, khirigsuur mounds.
##   highland (Tibet, Ladakh, Pamir, Tien Shan, Hindu Kush: elev >= 2.2): high cold steppe; thin grass and cushion
##     scrub on stony ground, bare scree, snow on the surrounding peaks; juniper scatter. The moister Himalayan front
##     (lat < 32.5, elev < 3.5: Himachal, Uttarakhand) adds blue pine / spruce stands.
##   prairie (Great Plains, lon < -30 north): mixed / shortgrass prairie, cottonwood along the creeks.
##   pampa (Buenos Aires / Uruguay pampa): flat, green tall-grass plain, a rare ombu shade tree, reeds by the lagoons.
##   monte (Mendoza / Neuquén Andean foot, lon < -65): dry jarilla scrub (pea-shrub model) and bunch grass, pale gravel.
## Season (continental): spring flush (green, Apr-Jun), summer-autumn (tawny / golden, Jul-Oct), winter (Nov-Mar,
## dormant grey-brown grass, low cold sun, snow caps on the hill tops). Southern hemisphere shifted 6 months.
## The humid pampa / prairie stay greener in summer; the monte is dry all year.
## Override: --env-season=spring|summer|winter (wet = spring, dry / autumn = summer).

static func season(lat: float) -> String:
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--env-season="):
			var v := s.substr(13)
			if v in ["dry", "summer", "autumn"]: return "summer"
			if v in ["winter", "snow"]: return "winter"
			return "spring"
	var ml := Engine.get_main_loop() as SceneTree
	var sim: Node = ml.root.get_node_or_null("Sim") if ml else null
	if sim == null or not sim.has_method("date_parts"):
		return "summer"
	var m: int = int(sim.call("date_parts")[1])          # 0 = January
	if lat < 0.0:
		m = (m + 6) % 12
	if m >= 3 and m <= 5: return "spring"
	if m >= 6 and m <= 9: return "summer"
	return "winter"

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var lon: float = b["lon"]; var elev: float = b["elev"]
	var sub := "kazakh"
	if lat < 0.0: sub = "monte" if lon < -65.0 else "pampa"
	elif lon < -30.0: sub = "prairie"
	elif elev >= 2.2: sub = "highland"
	elif lon >= 88.0 and lat >= 40.0: sub = "mongol"
	elif (lat < 48.5 and elev < 0.5) or lon < 50.0: sub = "semi"
	b["sub"] = sub
	var sea := season(lat)
	if sub == "monte" and sea == "spring": sea = "summer"
	b["season"] = sea
	var spring := sea == "spring"; var winter := sea == "winter"
	var hills := terr in ["hills", "mountains"]
	var moist_hi := sub == "highland" and lat < 32.5 and elev < 3.5
	var north := lat >= 50.0 or (sub == "mongol" and (terr == "mountains" or lat >= 48.5))

	# --- structure: open grass; trees only in groves / valleys / north slopes
	var wood: float = {"kazakh": 0.1, "semi": 0.03, "mongol": 0.1, "highland": 0.03, "prairie": 0.08, "pampa": 0.03, "monte": 0.04}[sub]
	if sub == "kazakh" and lat >= 50.0: wood = 0.26                     # forest-steppe birch kolki
	if sub == "mongol" and north: wood = 0.3                           # larch on the north slopes
	if moist_hi: wood = 0.34
	b["forest"] = wood
	b["tree_cell"] = 9.0; b["tree_p"] = 0.35 + wood; b["tree_scale"] = Vector2(0.8, 1.15)
	b["lone_n"] = int({"kazakh": 14, "semi": 4, "mongol": 8, "highland": 4, "prairie": 14, "pampa": 5, "monte": 6}[sub])
	var dryness: float = {"kazakh": 0.5, "semi": 0.75, "mongol": 0.5, "highland": 0.7, "prairie": 0.38, "pampa": 0.2, "monte": 0.8}[sub]
	b["dry"] = clampf(dryness + (-0.22 if spring else (0.12 if not winter else 0.18)), 0.05, 0.95)
	var rocky := sub in ["mongol", "highland", "monte"] or (sub == "kazakh" and hills)
	b["rocks"] = clampf(float(b["rocks"]) * 0.8 + (0.35 if rocky else 0.0), 0.2, 1.6)
	b["relief"] = float(b["relief"]) * (0.8 if sub in ["pampa", "prairie", "semi"] else 1.0)
	b["lake"] = sub in ["pampa", "prairie", "kazakh"] and (int(b["seed"]) % 2 == 0) or (bool(b["coastal"]) and sub == "pampa")
	b["shore"] = "env_reeds"; b["shore_n"] = 300 if sub in ["pampa", "prairie"] else 180
	# snow: peaks in the high steppe all year; hill tops in a continental winter (not pampa / monte)
	var mtn: float = b["mtn"]
	if sub == "highland":
		b["snow_h"] = maxf(mtn * (0.5 if not winter else 0.32), 90.0); b["treeline"] = maxf(mtn * 0.3, 60.0) if not moist_hi else mtn * 0.45
	elif winter and sub in ["kazakh", "mongol", "prairie", "semi"]:
		b["snow_h"] = maxf(mtn * 0.45, 40.0); b["treeline"] = b["snow_h"] + 200.0

	var t: Array = []; var lone: Array = []
	var ww := {"m": "env_wormwood", "n": 1400, "fmin": -1.0, "fmax": 0.6, "r": 0.5, "s": Vector2(0.7, 1.3), "tier": 0.3}
	var pea := {"m": "env_pea_shrub", "n": 500, "fmin": -0.2, "fmax": 1.01, "r": 0.6, "s": Vector2(0.7, 1.2), "tier": 0.45}
	var kur := {"m": "env_kurgan", "n": 6, "fmin": -1.0, "fmax": 0.4, "r": 7.5, "s": Vector2(0.7, 1.3), "tier": 0.0}
	var jun := {"m": "env_juniper", "n": 300, "fmin": -1.0, "fmax": 1.01, "r": 0.8, "s": Vector2(0.6, 1.0), "tier": 0.4}
	var sh: Array = []
	match sub:
		"kazakh":
			t = [["env_birch_a", 0.42, 0.0], ["env_birch_b", 0.3, 0.3], ["env_cottonwood", 0.28, -0.2]]
			lone = ["env_birch_a", "env_cottonwood", "env_birch_b"]
			sh = [ww, pea, kur]
		"semi":
			t = [["env_cottonwood", 1.0, 0.0]]
			lone = ["env_cottonwood"]
			ww["n"] = 2600; ww["fmax"] = 1.01; pea["n"] = 260; kur["n"] = 4
			sh = [ww, pea, kur]
		"mongol":
			t = [["env_larch", 0.66, -0.2], ["env_birch_a", 0.2, 0.4], ["env_birch_b", 0.14, 0.4]]
			lone = ["env_larch", "env_larch", "env_birch_a"]
			ww["n"] = 1000; pea["n"] = 420; kur["n"] = 5
			sh = [ww, pea, kur]
		"highland":
			if moist_hi:
				t = [["env_pine_a", 0.5, 0.0], ["env_spruce_a", 0.3, -0.3], ["env_juniper", 0.2, 0.5]]
				lone = ["env_pine_a", "env_juniper"]
			else:
				t = [["env_juniper", 0.7, 0.2], ["env_cottonwood", 0.3, -0.3]]    # valley poplar / willow
				lone = ["env_juniper"]
			ww["n"] = 1700; ww["fmax"] = 1.01; pea["n"] = 300; kur["n"] = 0
			sh = [ww, pea, jun]
		"prairie":
			t = [["env_cottonwood", 1.0, 0.0]]                               # creek-bottom cottonwood
			lone = ["env_cottonwood"]
			ww["n"] = 700; ww["m"] = "env_wormwood"; pea["n"] = 300; kur["n"] = 0
			sh = [ww, pea]
		"pampa":
			t = [["env_ombu", 0.5, 0.0], ["env_cottonwood", 0.5, -0.2]]
			lone = ["env_ombu"]
			ww["n"] = 300; pea["n"] = 260; kur["n"] = 0
			sh = [ww, pea]
		_:   # monte
			t = [["env_cottonwood", 1.0, 0.0]]                               # irrigated-valley poplar rows
			lone = ["env_pea_shrub"]
			pea["n"] = 2200; pea["fmin"] = -1.0; ww["n"] = 900; kur["n"] = 0
			sh = [pea, ww]
	b["trees"] = t; b["lone"] = lone; b["shrubs"] = sh
	b["accents"] = [{"m": "env_tor_a", "open": 0.02, "knoll": 0.18 if rocky else 0.06, "s": Vector2(0.7, 1.2)}]
	b["far_model"] = "env_steppe_far"; b["far_dens"] = 0.12 + wood * 1.4; b["far_scale"] = Vector2(1.0, 1.5)
	b["outcrop"] = "env_tor_outcrop"; b["boulders"] = ["env_tor_a", "env_tor_b", "env_tor_a"]
	b["cover_main"] = "env_feather_grass" if sub != "pampa" else "env_grass_dry"
	b["cover_cell"] = {"semi": 3.6, "highland": 3.8, "monte": 3.6}.get(sub, 2.8)
	b["cover_p"] = {"semi": 0.6, "highland": 0.5, "monte": 0.55}.get(sub, 0.92)
	b["cover_in"] = 0.34

	# --- ground palette: chernozem / chestnut soils; pale loess and sandy loam in the semi-desert; grey gravel up high
	var soil: Color = {"kazakh": Color(0.4, 0.33, 0.24), "semi": Color(0.62, 0.55, 0.42), "mongol": Color(0.47, 0.4, 0.3),
		"highland": Color(0.55, 0.5, 0.44), "prairie": Color(0.38, 0.31, 0.23), "pampa": Color(0.32, 0.27, 0.2), "monte": Color(0.6, 0.52, 0.4)}[sub]
	var green := Color(0.34, 0.45, 0.19)
	if sub == "pampa": green = Color(0.3, 0.45, 0.17)
	var tawny := Color(0.7, 0.6, 0.38)
	var dormant := Color(0.55, 0.5, 0.4)
	var k: float = {"kazakh": 0.0, "semi": 0.25, "mongol": 0.05, "highland": 0.3, "prairie": -0.08, "pampa": -0.2, "monte": 0.3}[sub]
	var gr_a: Color; var gr_b: Color
	if spring:
		gr_a = green.lerp(tawny, clampf(0.2 + k, 0.0, 1.0)); gr_b = green.lerp(tawny, clampf(0.34 + k, 0.0, 1.0))
	elif winter:
		gr_a = dormant.lerp(green, 0.25 if sub == "pampa" else 0.0); gr_b = dormant.lerp(tawny, 0.4)
	else:
		gr_a = green.lerp(tawny, clampf(0.68 + k, 0.0, 1.0)); gr_b = green.lerp(tawny * 1.06, clampf(0.86 + k, 0.0, 1.0))
	var rock := Color(0.62, 0.59, 0.54)
	b["palette"] = {"grass_a": gr_a, "grass_b": gr_b, "dry": tawny.lerp(Color(0.82, 0.76, 0.6), 0.35), "earth": soil,
		"floor_col": soil.lerp(gr_a, 0.5) * 0.85, "needle": soil * 0.8, "rock": rock, "scree": soil.lerp(rock, 0.6),
		"snow_col": Color(0.9, 0.92, 0.96), "far_forest": Color(0.24, 0.29, 0.15) if not winter else Color(0.3, 0.28, 0.24),
		"straw": Color(0.86, 0.76, 0.5) if not spring else Color(0.64, 0.7, 0.38)}
	var leaf := [Color(1.08, 1.1, 0.98), Color(0.03, 0.035, 0.015)]
	if sea == "summer": leaf = [Color(1.12, 1.08, 0.92), Color(0.04, 0.035, 0.015)]
	var bare := [Color(0.95, 0.82, 0.68), Color(0.1, 0.08, 0.06)]          # leafless twig-brown crowns in winter
	var larch := leaf
	if winter: larch = bare
	elif sea == "summer" and lat >= 0.0: larch = [Color(1.18, 1.08, 0.82), Color(0.05, 0.04, 0.01)]
	var grass: Array
	if spring: grass = [Color(0.85, 1.0, 0.7), Color(0.03, 0.05, 0.01)]
	elif winter: grass = [Color(0.92, 0.86, 0.76), Color(0.12, 0.1, 0.08)]
	else: grass = [Color(1.12, 1.0, 0.78), Color(0.12, 0.09, 0.03)]
	if sub == "pampa" and not winter: grass = [Color(0.8, 0.95, 0.66), Color(0.04, 0.05, 0.01)]
	var ever := [Color(1.05, 1.06, 1.0), Color(0.02, 0.02, 0.015)]
	var decid := bare if winter and sub != "pampa" else leaf
	var stone := [Color(1.0, 0.99, 0.97), Color(0.02, 0.02, 0.02)]
	b["tints"] = {"env_feather_grass": grass, "env_grass_dry": grass, "env_wormwood": [Color(1.05, 1.05, 1.02), Color(0.04, 0.04, 0.04)] if not winter else [Color(0.95, 0.92, 0.86), Color(0.06, 0.05, 0.04)],
		"env_pea_shrub": decid, "env_larch": larch, "env_birch_a": decid, "env_birch_b": decid, "env_cottonwood": decid,
		"env_ombu": leaf, "env_juniper": ever, "env_pine_a": ever, "env_spruce_a": ever,
		"env_tor_a": stone, "env_tor_b": stone, "env_tor_outcrop": stone, "env_kurgan": grass,
		"env_reeds": [Color(0.88, 0.9, 0.66), Color(0.1, 0.09, 0.05)], "env_steppe_far": decid if sub != "highland" else ever}
	# --- light: huge open sky; spring clear and fresh, summer hazy-warm, winter pale + low sun; thin air high up
	var hi := sub == "highland"
	var sky_top := Color(0.24, 0.45, 0.8)
	var sky_hz := Color(0.78, 0.85, 0.92)
	var haze := Color(0.78, 0.83, 0.88)
	var sun_c := Color(1.0, 0.96, 0.88); var sun_e := 1.6; var sun_x := -46.0
	if sea == "summer":
		sky_top = Color(0.3, 0.49, 0.78); sky_hz = Color(0.86, 0.85, 0.8); haze = Color(0.84, 0.82, 0.74); sun_c = Color(1.0, 0.94, 0.8); sun_e = 1.7; sun_x = -54.0
	elif winter:
		sky_top = Color(0.42, 0.55, 0.72); sky_hz = Color(0.84, 0.86, 0.88); haze = Color(0.82, 0.84, 0.86); sun_c = Color(1.0, 0.92, 0.82); sun_e = 1.3; sun_x = -22.0
	if hi:
		sky_top = Color(0.14, 0.32, 0.72); sky_hz = Color(0.7, 0.8, 0.9); haze = Color(0.76, 0.82, 0.9); sun_e += 0.15
	b["look"] = {"sky_top": sky_top, "sky_horizon": sky_hz, "ground_horizon": Color(0.66, 0.6, 0.48), "ground_bottom": Color(0.3, 0.26, 0.2),
		"ambient": 0.84, "exposure": 0.98, "contrast": 1.05, "saturation": 0.9 if not winter else 0.8,
		"fog_begin": 380.0, "fog_end": 7000.0 if hi else (6000.0 if spring else 5200.0), "fog_density": 0.34 if hi else (0.42 if spring else 0.5),
		"fog_color": haze, "fog_scatter": 0.3, "fog_sky": 0.3,
		"sun_rot": Vector3(sun_x, 205.0, 0.0), "sun_color": sun_c, "sun_energy": sun_e, "shadow_opacity": 0.86 if hi else 0.82}
	b["water"] = {"deep": Color(0.05, 0.1, 0.12), "sky": Color(0.66, 0.76, 0.86)}
	b["mats"] = {"tree": 2.0, "rock": 1.5, "cover": 1.0, "far": 2.0, "wind": 0.85}
	return b
