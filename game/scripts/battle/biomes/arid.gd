extends RefCounted
## Arid biome (every province the game data tags `desert`, plus Arabia / the Mexican plateau): dry earth and gravel,
## sparse straw bunchgrass, open desert scrub kept well apart, wind-rounded sandstone and layered butte outcrops, a
## harsh high sun under a pale, dusty sky. No grass carpet, no conifers / heather.
## core (0..1, from lat / lon) grades true deserts (Sahara, Arabia, Sonora, Gobi, Atacama, Australian interior) against
## the semi-arid margins the data also marks desert (Great Plains, N China / Gangetic plains, Sahel, Iberian meseta,
## Ethiopian highlands): more bunchgrass, more and greener trees, softer light as core falls.
## Species by region: Americas = creosote, prickly pear, mesquite (+ saguaro only in the Sonoran desert, pinyon-type
## juniper on the Colorado plateau); N Africa / Arabia / Mesopotamia = umbrella acacia, date palm (coasts, rivers,
## oases), tamarisk, saltbush; Iran / Central Asia / Gobi = saxaul, tamarisk, poplar oases, juniper on the highlands;
## India / Pakistan = khejri-type acacia + tamarisk; southern Africa = camelthorn acacia; Australia = spinifex hummocks,
## mulga acacia, saltbush on red earth.

static func _core(lat: float, lon: float, elev: float) -> float:
	var c := 0.3
	if lat >= 16.0 and lat <= 31.5 and lon >= -17.5 and lon <= 34.0: c = 1.0          # Sahara + Nile
	elif lat >= 14.0 and lat <= 32.5 and lon > 34.0 and lon <= 60.0: c = 0.95         # Arabia
	elif lat > 30.0 and lat <= 36.0 and lon > 34.0 and lon <= 48.0: c = 0.7           # Syrian desert / Iraq
	elif lat >= 25.0 and lat <= 42.5 and lon > 48.0 and lon <= 70.0: c = 0.8          # Iran / Afghanistan / Turkmen / Kyzylkum
	elif lat >= 24.0 and lat <= 30.5 and lon > 66.0 and lon <= 75.0: c = 0.75         # Thar / Sindh
	elif lat >= 34.0 and lat <= 46.0 and lon > 75.0 and lon <= 107.0: c = 0.9         # Taklamakan / Gobi / Qaidam
	elif lat >= 24.0 and lat <= 37.5 and lon >= -118.0 and lon <= -103.0: c = 0.9     # Mojave / Sonora / Chihuahua
	elif lat > 37.5 and lat <= 42.0 and lon >= -118.0 and lon <= -108.0: c = 0.75     # Great Basin / Utah
	elif lat >= -31.0 and lat <= -17.0 and lon >= -72.5 and lon <= -67.0: c = 1.0     # Atacama
	elif lat >= -29.0 and lat <= -17.0 and lon >= 11.0 and lon <= 25.0: c = 0.75      # Namib / Kalahari
	elif lat >= -32.0 and lat <= -17.0 and lon >= 114.0 and lon <= 146.0: c = 0.8     # Australian interior
	elif lat >= 0.0 and lat <= 12.0 and lon >= 39.0 and lon <= 52.0: c = 0.65         # Horn of Africa lowlands
	elif lat >= 12.0 and lat < 16.0 and lon >= -17.5 and lon <= 40.0: c = 0.5         # Sahel
	return clampf(c - maxf(elev - 1.2, 0.0) * 0.25, 0.2, 1.0)                        # high plateaus: cooler, grassier

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var lon: float = b["lon"]; var elev: float = b["elev"]
	var core := _core(lat, lon, elev)
	var semi := 1.0 - core
	var americas := lon >= -130.0 and lon <= -30.0
	var sonora := americas and lon >= -115.5 and lon <= -109.0 and lat >= 26.0 and lat <= 34.8
	var plateau := americas and lat >= 33.5 and lon <= -103.0 and elev >= 1.2      # Colorado plateau / NM uplands
	var aus := lon >= 110.0 and lat < -10.0
	var safr := lat < -10.0 and lon >= 10.0 and lon <= 35.0
	var asia := not americas and not aus and lon > 48.0 and lat > 24.0 and not (lon >= 66.0 and lon <= 90.0 and lat < 32.0)
	var india := lon >= 66.0 and lon <= 90.0 and lat < 32.0 and lat > 5.0
	var china_e := lon >= 104.0 and lat > 30.0 and not aus                          # loess / N China plain margin
	var afr := not americas and not aus and not asia and not india and not safr     # N Africa, Arabia, Levant, Horn, Sahel
	var wet: bool = b["coastal"] or (lon >= 30.5 and lon <= 33.5 and lat >= 15.0 and lat <= 31.0) or (lat >= 30.0 and lat <= 36.0 and lon >= 38.0 and lon <= 48.0)   # coasts, Nile, Mesopotamia
	var red := americas and lat > 20.0 and not plateau or aus or (afr and lon >= 34.0 and lon <= 40.0 and lat >= 26.0) or plateau   # red rock country
	var grey := asia or (americas and lat < 0.0) or china_e                          # grey-brown gravel / volcanic

	b["forest"] = clampf(0.1 + semi * 0.45 + (0.1 if terr in ["hills", "mountains"] else 0.0), 0.08, 0.6)
	b["dry"] = clampf(0.45 + core * 0.25, 0.4, 0.7)        # pale drift sand only on crests / open flats; the rest is soil / pavement mosaic
	b["snow_h"] = maxf(float(b["snow_h"]), 4600.0 if elev < 2.5 else 3800.0)   # desert ranges are bare rock, not snow-capped
	b["treeline"] = float(b["snow_h"]) - 700.0
	b["rocks"] = clampf(float(b["rocks"]) + core * 0.3 + (0.2 if red else 0.0), 0.4, 1.6)
	b["relief"] = float(b["relief"]) * (1.0 + core * 0.15)
	b["tree_cell"] = 11.0 - semi * 2.5; b["tree_p"] = 0.24 + semi * 0.34; b["tree_scale"] = Vector2(0.75, 1.15)
	b["lake"] = bool(b["coastal"]) or (int(b["seed"]) % 5) == 0       # sea / estuary on coasts, otherwise a rare oasis pool
	b["shore"] = "env_reeds"; b["shore_n"] = 260
	# --- trees / scrub
	var t: Array = []
	var lone: Array = []
	var sh: Array = []
	var acc: Array = [{"m": "env_gravel", "open": 0.08 + core * 0.08, "knoll": 0.2, "rock": 0.12, "s": Vector2(0.8, 1.6)}]
	var n_open := int(900.0 + core * 400.0)          # open-ground scrub (obstacles, off the corridor)
	if americas and lat > 0.0:
		t = [["env_mesquite", 0.6, 0.2], ["env_juniper", 0.25 + (0.6 if plateau else 0.0), -0.2], ["env_poplar", 0.1 if wet else 0.0, 0.6]]
		lone = ["env_mesquite", "env_mesquite", "env_juniper"]
		sh = [{"m": "env_creosote", "n": n_open, "fmin": -1.0, "fmax": 0.6, "r": 0.7, "s": Vector2(0.7, 1.3), "tier": 0.4},
			{"m": "env_prickly", "n": 260, "fmin": -1.0, "fmax": 0.4, "r": 0.6, "s": Vector2(0.7, 1.3), "tier": 0.5},
			{"m": "env_saltbush", "n": int(semi * 600.0) + (500 if plateau else 0), "fmin": -1.0, "fmax": 0.7, "r": 0.6, "s": Vector2(0.8, 1.4), "tier": 0.5}]
		if sonora:
			sh.append({"m": "env_saguaro_a", "n": 160, "fmin": -1.0, "fmax": 0.5, "r": 0.7, "s": Vector2(0.8, 1.15), "tier": 0.2})
			sh.append({"m": "env_saguaro_b", "n": 140, "fmin": -1.0, "fmax": 0.5, "r": 0.6, "s": Vector2(0.8, 1.15), "tier": 0.3})
	elif americas:   # Atacama / Andean desert: almost bare
		t = [["env_saltbush", 1.0, 0.0]]
		lone = []
		sh = [{"m": "env_saltbush", "n": 300, "fmin": -1.0, "fmax": 1.0, "r": 0.6, "s": Vector2(0.6, 1.1), "tier": 0.5}]
		b["forest"] = 0.05
	elif aus:
		t = [["env_acacia_b", 0.7, 0.0], ["env_acacia_a", 0.3, 0.4]]
		lone = ["env_acacia_b", "env_acacia_a"]
		sh = [{"m": "env_saltbush", "n": n_open, "fmin": -1.0, "fmax": 0.7, "r": 0.6, "s": Vector2(0.7, 1.3), "tier": 0.4}]
		acc.push_front({"m": "env_spinifex", "open": 0.22, "knoll": 0.3, "inside": 0.04, "s": Vector2(0.9, 1.7)})
	elif asia:
		t = [["env_saxaul", 0.5, 0.0], ["env_poplar", 0.15 + (0.35 if wet or china_e else 0.0), 0.5], ["env_juniper", 0.15 + elev * 0.1, -0.3], ["env_tamarisk", 0.25, 0.6]]
		lone = ["env_poplar", "env_tamarisk", "env_saxaul"]
		sh = [{"m": "env_saxaul", "n": n_open, "fmin": -1.0, "fmax": 0.6, "r": 0.8, "s": Vector2(0.7, 1.3), "tier": 0.4},
			{"m": "env_tamarisk", "n": 220, "fmin": -1.0, "fmax": 0.6, "r": 0.9, "s": Vector2(0.7, 1.2), "tier": 0.5}]
	elif india:
		t = [["env_acacia_b", 0.55, 0.0], ["env_acacia_a", 0.25, 0.3], ["env_tamarisk", 0.2, 0.6], ["env_date_palm", 0.1 if wet else 0.0, 0.8]]
		lone = ["env_acacia_b", "env_acacia_a"]
		sh = [{"m": "env_tamarisk", "n": int(n_open * 0.5), "fmin": -1.0, "fmax": 0.6, "r": 0.9, "s": Vector2(0.6, 1.1), "tier": 0.4},
			{"m": "env_saltbush", "n": int(n_open * 0.5), "fmin": -1.0, "fmax": 0.6, "r": 0.6, "s": Vector2(0.7, 1.2), "tier": 0.5}]
	elif safr:
		t = [["env_acacia_a", 0.6, 0.2], ["env_acacia_b", 0.4, 0.0]]
		lone = ["env_acacia_a"]
		sh = [{"m": "env_saltbush", "n": n_open, "fmin": -1.0, "fmax": 0.7, "r": 0.6, "s": Vector2(0.7, 1.3), "tier": 0.4}]
	else:            # N Africa, Arabia, Levant, Horn, Sahel
		var palm := 0.6 if wet else 0.12
		t = [["env_acacia_a", 0.5, 0.3], ["env_acacia_b", 0.35, 0.0], ["env_date_palm", palm, 0.6], ["env_tamarisk", 0.2, 0.8]]
		lone = ["env_acacia_a", "env_date_palm" if wet else "env_acacia_b", "env_acacia_b"]
		sh = [{"m": "env_saltbush", "n": int(n_open * 0.7), "fmin": -1.0, "fmax": 0.7, "r": 0.6, "s": Vector2(0.6, 1.2), "tier": 0.4},
			{"m": "env_tamarisk", "n": int(n_open * 0.25), "fmin": -1.0, "fmax": 0.6, "r": 0.9, "s": Vector2(0.6, 1.1), "tier": 0.5}]
	b["trees"] = t; b["lone"] = lone; b["shrubs"] = sh; b["accents"] = acc
	b["far_model"] = "env_arid_far"; b["far_dens"] = 0.35 + semi * 0.6; b["far_scale"] = Vector2(0.9, 1.4)
	b["outcrop"] = "env_mesa_outcrop"; b["boulders"] = ["env_sandstone_a", "env_sandstone_b", "env_sandstone_c"]
	b["cover_main"] = "env_dry_tuft" if core > 0.55 else "env_grass_dry"
	b["cover_cell"] = 3.2; b["cover_p"] = 0.22 + semi * 0.7; b["cover_in"] = 0.08 + semi * 0.2
	# --- ground palette: red ochre / buff sand / grey gravel, with dusty olive grass on the semi-arid margins
	var soil := Color(0.66, 0.5, 0.34)                    # buff sand (Sahara, Arabia)
	if red: soil = Color(0.62, 0.4, 0.26)                 # red earth (Sonora, Colorado plateau, Australia, Hejaz)
	if grey: soil = Color(0.52, 0.47, 0.4)                # grey-brown gravel (Gobi, Iran, Atacama, loess margin)
	var sand := soil.lerp(Color(0.76, 0.68, 0.52), 0.3)                     # pale wind-blown sand (crests, open flats)
	var pave := soil * Color(0.78, 0.76, 0.74)                               # darker gravel / desert pavement
	var grass := Color(0.4, 0.4, 0.24).lerp(Color(0.34, 0.38, 0.18), semi)   # dusty bunchgrass on the margins
	b["palette"] = {"grass_a": grass.lerp(pave, core * 0.8), "grass_b": grass.lerp(soil, core * 0.75),
		"dry": sand, "earth": soil * 0.86, "floor_col": soil * Color(0.95, 0.94, 0.93), "needle": soil * Color(0.9, 0.88, 0.86),
		"rock": (Color(0.56, 0.4, 0.3) if red else (Color(0.48, 0.45, 0.41) if grey else Color(0.6, 0.53, 0.43))),
		"scree": soil * Color(0.78, 0.74, 0.72), "snow_col": soil * 1.2, "far_forest": soil * Color(0.7, 0.72, 0.62), "straw": Color(0.76, 0.68, 0.48),
		"lichen": soil * 0.7, "lichen_amt": 0.2}
	var leaf := [Color(1.0, 0.84, 0.82), Color(0.16, 0.14, 0.1)]      # dusty olive / grey-green desert foliage
	var rk := [Color(1.25, 1.2, 1.15), Color(0.2, 0.18, 0.16)]
	if red: rk = [Color(1.05, 0.8, 0.68), Color(0.16, 0.1, 0.08)]          # red Navajo / Hejaz sandstone
	elif grey: rk = [Color(0.86, 0.88, 0.92), Color(0.14, 0.14, 0.14)]     # grey-brown gravel / volcanic
	else: rk = [Color(1.06, 1.02, 0.96), Color(0.14, 0.12, 0.1)]          # pale buff sandstone / limestone
	b["tints"] = {"env_mesquite": leaf, "env_acacia_a": leaf, "env_acacia_b": leaf, "env_date_palm": leaf, "env_poplar": leaf,
		"env_tamarisk": leaf, "env_saxaul": leaf, "env_creosote": leaf, "env_saltbush": leaf, "env_prickly": leaf,
		"env_saguaro_a": [Color(0.98, 0.8, 0.82), Color(0.1, 0.1, 0.08)], "env_saguaro_b": [Color(0.98, 0.8, 0.82), Color(0.1, 0.1, 0.08)],
		"env_juniper": [Color(0.8, 0.86, 0.74), Color(0.16, 0.14, 0.1)],
		"env_spinifex": [Color(0.95, 0.95, 0.85), Color(0.14, 0.12, 0.06)], "env_dry_tuft": [Color(0.95, 0.92, 0.85), Color(0.12, 0.1, 0.06)],
		"env_grass_dry": [Color(0.9, 0.86, 0.72), Color(0.12, 0.1, 0.06)], "env_reeds": [Color(0.85, 0.85, 0.7), Color(0.16, 0.12, 0.08)],
		"env_gravel": rk, "env_sandstone_a": rk, "env_sandstone_b": rk, "env_sandstone_c": rk, "env_mesa_outcrop": rk,
		"env_arid_far": [Color(0.88, 0.86, 0.76), Color(0.14, 0.12, 0.08)]}
	# --- light: high harsh sun, short soft shadows lifted by bright ground bounce, pale dusty sky, warm haze
	var haze := Color(0.72, 0.7, 0.68).lerp(Color(0.72, 0.75, 0.78), semi * 0.6)   # dusty grey-violet distance, not cream
	b["look"] = {"sky_top": Color(0.36, 0.52, 0.74).lerp(Color(0.32, 0.48, 0.72), semi), "sky_horizon": Color(0.86, 0.82, 0.74).lerp(Color(0.8, 0.82, 0.84), semi),
		"ground_horizon": Color(0.74, 0.64, 0.5), "ground_bottom": Color(0.36, 0.3, 0.22),
		"ambient": 0.86, "exposure": 0.94, "contrast": 1.08, "saturation": 0.92 + semi * 0.06,
		"fog_begin": 320.0, "fog_end": 7000.0, "fog_density": 0.42 + core * 0.08, "fog_color": haze, "fog_scatter": 0.28, "fog_sky": 0.38,
		"sun_rot": Vector3(-58.0 + semi * 10.0, 205.0, 0.0), "sun_color": Color(1.0, 0.95, 0.84), "sun_energy": 1.65 - semi * 0.15, "shadow_opacity": 0.8}
	b["water"] = {"deep": Color(0.05, 0.12, 0.13), "sky": Color(0.74, 0.78, 0.8)}
	b["mats"] = {"tree": 2.3, "rock": 1.15, "cover": 1.0, "far": 2.0, "wind": 0.6}
	return b
