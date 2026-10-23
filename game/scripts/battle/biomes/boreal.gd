extends RefCounted
## Boreal biome (the merged Scandinavian battlefield, now also the taiga of Russia / Canada and N. Britain):
## spruce-dominated forest, birch fringes rising to the north, Scots pine on dry / thin ground, glacier-polished granite,
## heather + juniper, reed-lined lake, cool summer-afternoon light. Nordic provinces keep the Scandes / Denmark rules.

static func make(p: Dictionary, terr: String, b: Dictionary) -> Dictionary:
	var lat: float = b["lat"]; var lon: float = b["lon"]; var elev: float = b["elev"]
	var region: String = b["region"]
	var nordic: bool = region in ["Norway", "Sweden", "Denmark", "Finland", "Åland"]
	b["id"] = "boreal"
	b["rocks"] = clampf(float(b["rocks"]) + (0.25 if region in ["Norway", "Finland"] else 0.0), 0.2, 1.6)
	# boreal gradient: birch share rises to the north, pine on thin / dry (tundra, high) ground
	var birch: float = clampf(0.16 + (absf(lat) - 56.0) * 0.035, 0.12, 0.45) + (0.15 if region == "Denmark" else 0.0)
	var pine: float = clampf(0.18 + (0.22 if terr == "tundra" else 0.0) + elev * 0.3, 0.12, 0.5)
	b["birch"] = birch; b["pine"] = pine
	# distant relief: Scandes (Norway, western / northern Sweden: lon < 16 and lat > 59, or high elev) -> snow-capped
	# mountains; southern Sweden / Finland -> forested ridges; Denmark -> low hills. Elsewhere by terrain / elev.
	var mtn: float = 180.0
	if nordic:
		if region == "Denmark":
			mtn = 70.0
		elif region == "Norway" or (lat > 59.0 and lon < 16.5) or lat > 64.0 or elev > 0.35:
			mtn = 560.0 + elev * 600.0
		elif region == "Finland":
			mtn = 120.0
	elif terr == "mountains" or elev > 0.45:
		mtn = 560.0 + elev * 600.0
	elif terr == "hills":
		mtn = 260.0
	b["mtn"] = mtn
	b["snow_h"] = 1400.0 - (absf(lat) - 55.0) * 70.0        # summer snowline falls ~70 m per degree north (stylised)
	b["treeline"] = 900.0 - (absf(lat) - 55.0) * 45.0
	var sp := maxf(0.2, 1.0 - birch * 1.3 - pine)
	b["trees"] = [["env_birch_a", birch, 1.0], ["env_pine_a", pine, 0.0], ["env_spruce_a", sp * 0.55, 0.0], ["env_spruce_b", sp * 0.45, 0.0]]
	b["lone"] = ["env_birch_a", "env_birch_a", "env_pine_a", "env_spruce_b"]
	b["far_model"] = "env_conifer_far"
	b["accents"] = [{"m": "env_heather", "knoll": 0.35, "open": 0.06}, {"m": "env_pebbles", "rock": 0.09, "s": Vector2(0.6, 1.3)}]
	b["shrubs"] = [{"m": "env_juniper", "n": 260, "fmin": 0.05, "fmax": 0.6, "r": 0.8},
		{"m": "env_log", "n": 70, "fmin": 0.3, "fmax": 1.01, "r": 3.0, "s": Vector2(0.7, 1.2), "tier": 1.0}]
	b["tints"] = {"env_birch_a": [Color(0.35, 0.36, 0.3), Color(0.05, 0.06, 0.05)],   # (x2.4 tree albedo) muted summer birch
		"L:env_conifer_far": [Color(0.9, 0.95, 0.9), Color(0.15, 0.1, 0.0)]}
	var north: float = clampf((absf(lat) - 55.0) / 15.0, 0.0, 1.0)
	b["look"] = {"sky_top": Color(0.22, 0.4, 0.68).lerp(Color(0.26, 0.43, 0.68), north)}
	return b
