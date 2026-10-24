extends RefCounted
## Battlefield environment (env/scandinavia-medieval prototype). RENDERING ONLY: builds the ground relief, terrain
## material, distant mountains, lake, forests, rocks and ground cover for a BattleView whose province maps to a
## supported biome, and the light / sky / fog for it. Nothing here has collision or feeds BattleSim: the sim stays 2-D,
## its inputs (b.terrain, seed, units) are untouched and so are battle results / hashes.
##
## Biome selection is data-driven (biome_for / biome_id): GameData.provinces[b.prov] terrain + lat / lon (+ region
## for the Nordic Scandes rules) pick one of BIOMES; scripts/battle/biomes/<id>.gd then sets that biome's species,
## rocks, ground cover, ground palette, water and light, and adjusts the generic numbers (_base: relief, forest
## density, rockiness, dryness, distant relief, snowline, lake) for the province. A biome whose file is not present
## keeps the legacy BattleView ground (so each biome lands on its own branch). docs/BIOMES.md has the grouping.
##
## Determinism / isolation: everything is placed from its own RNG + noise seeded from b.seed (BattleView.rng, which
## also jitters the soldiers, is consumed exactly as before by a dry run of the legacy scatter), so the same battle
## always gets the same field and the troops are byte-identical to the legacy build.
##
## Obstacle rules (plan()): the engagement corridor is derived from the deployed regiments (x extent of both lines +
## 70 m, z extent + 220 m for advance / pursuit, clamped); trees, boulders, outcrops, junipers and logs are kept out
## of it (+ their footprint radius + margin); only knee-high cover (grass, heather, pebbles) may appear inside, and
## sparser there. tests/test_env.gd runs real BattleSims and checks no regiment footprint ever meets an obstacle.
##
## Debug / evidence: --env=0 forces the legacy look (before/after shots), --env=1 ignores a biome's era gate,
## --env-prov=<id> PREVIEW-ONLY: dress the field as if the battle were fought in province <id>.

const FIELD := 1000.0
const FAR := 4600.0
const TREE_TILE := 125.0     # near-tree multimesh tile (m): detail mesh only for tiles whose centre is < TREE_DETAIL
const TREE_DETAIL := 190.0
const NEAR_TILE := 250.0
const COVER_TILE := 125.0
const REGIONS := ["Norway", "Sweden", "Denmark", "Finland", "Åland"]   # Nordic provinces (Scandes rules in boreal.gd)
const BIOME_DIR := "res://scripts/battle/biomes/%s.gd"   # one file per biome profile; a missing file = legacy ground
const BIOMES := ["boreal", "tundra", "temperate", "east_asia", "tropical", "savanna", "arid", "mediterranean", "steppe"]

static var _args := {}
static var _args_read := false

static func _arg(k: String, def: String = "") -> String:
	if not _args_read:
		_args_read = true
		for s in OS.get_cmdline_user_args():
			if s.begins_with("--env"):
				var kv := s.substr(2).split("=", true, 1)
				_args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	return str(_args.get(k, def))

# ============================================================== biome selection (data -> profile)
## Returns {} (legacy ground) or the biome profile for this battle.
static func biome_for(b: Dictionary, era: String) -> Dictionary:
	if _arg("env") == "0":
		return {}
	var pid := int(b.get("prov", -1))
	var pv := _arg("env-prov")
	if pv != "":
		pid = int(pv)
	if not GameData.provinces.has(pid):
		return {}
	var p: Dictionary = GameData.provinces[pid]
	var terr: String = str(p.get("terrain", "plains")) if pv != "" else str(b.get("terrain", p.get("terrain", "plains")))
	var prof := profile(p, terr, int(b.get("seed", 0)))
	if prof.is_empty():
		return {}
	var eras: Array = prof.get("eras", [])
	if _arg("env") != "1" and not eras.is_empty() and not (era in eras):
		return {}
	prof["era"] = era
	return prof

## Pure: province record -> biome id. Climate zones from the data fields only (terrain, lat / lon); see docs/BIOMES.md.
static func biome_id(p: Dictionary, terr: String) -> String:
	var region := str(p.get("region", ""))
	var lat: float = float(p.get("lat", 50.0)); var lon: float = float(p.get("lon", 10.0)); var a := absf(lat)
	var americas := lon >= -130.0 and lon <= -30.0
	if region in REGIONS:
		return "boreal"
	if terr == "desert":
		return "arid"
	if a >= 64.0 or region in ["Greenland", "Iceland", "Faeroe Is."] or lat < -46.0:
		return "tundra"
	if terr == "tundra":
		return "boreal"
	if terr == "jungle":
		return "tropical"
	if (lon >= 88.0 or lon <= -140.0) and a < 22.5 and not (lon >= 100.0 and lon <= 146.0 and lat >= 22.0):
		return "tropical"                                   # SE Asia, Pacific islands, Hawaii
	if lon >= 88.0 and lon < 100.0 and lat < 29.0 and terr != "mountains":
		return "tropical"                                   # Bengal / Assam / Burma monsoon lowlands
	if lon >= 100.0 and lon < 116.0 and lat >= 42.0 and lat < 50.0:
		return "steppe"                                     # Mongolian plateau / Inner Mongolia grassland
	if lon >= 100.0 and lon <= 146.0 and lat >= 20.0 and lat <= 46.0:
		return "east_asia"                                  # China (east), Korea, Japan, Taiwan
	if a < 8.0 or (americas and a < 26.0 and lon > -95.0):
		return "tropical"                                   # equatorial belt, Caribbean / Central America
	if lon >= 34.0 and lon <= 62.0 and lat >= 12.0 and lat <= 32.0:
		return "arid"                                       # Arabia / Gulf (non-desert-tagged coasts)
	if americas and lat >= 14.0 and lat <= 33.0:
		return "arid"                                       # Mexican plateau / Sierra Madre
	if (lon >= -26.0 and lon <= 55.0 and lat >= -36.0 and lat <= 24.0) or (lon >= 60.0 and lon < 88.0 and lat >= 5.0 and lat <= 30.0) or (americas and lat >= -30.0 and lat <= -8.0):
		return "savanna"                                    # Africa, Indian subcontinent, cerrado / chaco
	if (lat >= 30.0 and lat <= 45.0 and lon >= -10.0 and lon <= 45.0) or (lat >= 32.0 and lat <= 42.0 and lon >= -125.0 and lon <= -114.0) or (lat >= -38.0 and lat <= -28.0 and lon >= -75.0 and lon <= -69.0) or (lon > 110.0 and lat >= -40.0 and lat <= -25.0):
		return "mediterranean"                              # Med basin, California, central Chile, S Australia
	if (lat >= 30.0 and lat <= 55.0 and lon > 45.0 and lon < 120.0) or (americas and lat >= 30.0 and lat <= 50.0 and lon >= -106.0 and lon <= -97.0 and terr in ["plains", "hills"]) or (americas and lat < -30.0):
		return "steppe"                                     # Central Asia, Tibet, Great Plains, pampas / Patagonia
	if lon > -12.0 and lon < 30.0 and lat > 35.0:           # Atlantic / central Europe: broadleaf + mixed up to ~57 N
		return "boreal" if a >= 57.0 else "temperate"
	if a >= 52.0 or (a >= 50.0 and terr == "forest"):
		return "boreal"                                     # taiga (Russia, Canada, Siberia)
	return "temperate"                                      # Europe, eastern / northern US, NZ ...

## Pure: province record + battle terrain -> biome parameters. Generic numbers from the data fields (_base), then the
## biome file (scripts/battle/biomes/<id>.gd: make(p, terr, base)) adds its species, palette, light and adjustments.
static func profile(p: Dictionary, terr: String, seed: int) -> Dictionary:
	var id := biome_id(p, terr)
	var path := BIOME_DIR % id
	if not ResourceLoader.exists(path):
		return {}
	var base := _base(p, terr, seed)
	base["id"] = id
	return (load(path) as GDScript).call("make", p, terr, base)

static func _base(p: Dictionary, terr: String, seed: int) -> Dictionary:
	var lat: float = float(p.get("lat", 60.0)); var lon: float = float(p.get("lon", 15.0)); var elev: float = float(p.get("elev", 0.2))
	var a := absf(lat)
	var relief: float = {"plains": 2.6, "forest": 4.0, "tundra": 5.5, "hills": 9.0, "mountains": 12.0, "desert": 3.5, "jungle": 5.0}.get(terr, 4.0)
	relief += elev * 6.0
	var forest: float = {"plains": 0.45, "forest": 1.0, "tundra": 0.65, "hills": 0.8, "mountains": 0.7, "desert": 0.15, "jungle": 1.0}.get(terr, 0.7)
	var rocks: float = {"plains": 0.3, "forest": 0.6, "tundra": 1.0, "hills": 0.85, "mountains": 1.2, "desert": 0.9, "jungle": 0.3}.get(terr, 0.6)
	rocks = clampf(rocks + elev * 0.6, 0.2, 1.6)
	var dry: float = {"plains": 0.35, "forest": 0.22, "tundra": 0.5, "hills": 0.32, "mountains": 0.4, "desert": 0.9, "jungle": 0.05}.get(terr, 0.3)
	var mtn: float = {"mountains": 620.0 + elev * 700.0, "hills": 260.0 + elev * 300.0}.get(terr, 120.0 + elev * 260.0)
	var snow_h: float = maxf(700.0, 3600.0 - maxf(a - 25.0, 0.0) * 75.0)
	return {"variant": terr, "prov": p.get("id", -1), "name": p.get("name", ""), "region": str(p.get("region", "")),
		"lat": lat, "lon": lon, "elev": elev, "coastal": bool(p.get("coastal", false)),
		"relief": relief, "forest": forest, "rocks": rocks, "dry": dry, "mtn": mtn, "snow_h": snow_h, "treeline": snow_h - 700.0,
		"lake": bool(p.get("coastal", false)) or (seed % 3) != 0, "seed": seed, "eras": [],
		# content (biome files override): trees [model, weight, edge_bias], lod / far models, rocks, cover, shrubs
		"trees": [], "lod": {}, "lone": [], "lone_n": 90, "far_model": "", "far_dens": 1.0, "far_scale": Vector2(1.2, 1.8),
		"tree_cell": 7.4, "tree_p": 0.62, "tree_scale": Vector2(0.7, 1.2),
		"outcrop": "env_outcrop_a", "boulders": ["env_boulder_a", "env_boulder_b", "env_boulder_c"],
		"cover_main": "env_grass_tuft", "cover_cell": 3.2, "cover_p": 0.85, "cover_in": 0.28, "accents": [],
		"shrubs": [], "shore": "env_reeds", "shore_n": 420, "palette": {}, "tints": {}, "look": {}, "water": {}, "mats": {}}

# ============================================================== layout + relief (pure)
## ctx = profile + seeded noises + corridor / lake / rocky-hill sites. regs: Array of {pos: Vector2, width, depth}.
static func layout(prof: Dictionary, regs: Array) -> Dictionary:
	var seed: int = int(prof["seed"])
	var ctx := prof.duplicate()
	var xmax := 0.0; var zmax := 0.0
	for r in regs:
		var p: Vector2 = r["pos"]
		xmax = maxf(xmax, absf(p.x) + float(r.get("width", 20.0)) * 0.5)
		zmax = maxf(zmax, absf(p.y) + float(r.get("depth", 10.0)) * 0.5)
	var cw := clampf(xmax + 70.0, 160.0, 430.0)
	var cz := clampf(zmax + 220.0, 260.0, 360.0)
	ctx["corridor"] = Vector2(cw, cz)
	var rng := RandomNumberGenerator.new(); rng.seed = hash([seed, "env-layout"])
	ctx["n_relief"] = _noise(seed, 0.0032, 4, FastNoiseLite.FRACTAL_FBM)
	ctx["n_detail"] = _noise(seed + 1, 0.016, 2, FastNoiseLite.FRACTAL_FBM)
	ctx["n_hill"] = _noise(seed + 2, 0.0021, 3, FastNoiseLite.FRACTAL_FBM)
	ctx["n_mtn"] = _noise(seed + 3, 0.00075, 5, FastNoiseLite.FRACTAL_RIDGED)
	ctx["n_forest"] = _noise(seed + 4, 0.0065, 3, FastNoiseLite.FRACTAL_FBM)
	ctx["n_cover"] = _noise(seed + 5, 0.02, 2, FastNoiseLite.FRACTAL_FBM)
	# lake on the east flank, north of the line; rocky hill on the west flank, south (fixed sides so scripted evidence
	# cameras find them; size / shape jitter from the seed)
	var lr := Vector2(rng.randf_range(95.0, 125.0), rng.randf_range(70.0, 90.0))
	ctx["lake_c"] = Vector2(minf(cw + 140.0, 470.0) + rng.randf_range(-15.0, 15.0), rng.randf_range(250.0, 300.0))
	ctx["lake_r"] = lr
	ctx["lake_rot"] = rng.randf_range(-0.5, 0.5)
	ctx["has_lake"] = bool(prof["lake"])
	ctx["rock_c"] = Vector2(-minf(cw + 110.0, 450.0) + rng.randf_range(-15.0, 15.0), rng.randf_range(-260.0, -200.0))
	ctx["rock_r"] = rng.randf_range(75.0, 95.0)
	ctx["rock_h"] = 4.0 + float(prof["relief"]) * 1.4 + float(prof["rocks"]) * 4.0
	ctx["water_h"] = -1e5
	if ctx["has_lake"]:
		var lo := 1e9
		for k in 48:
			var a := TAU * k / 48.0
			var q := _lake_pt(ctx, a, 1.0)
			lo = minf(lo, height(ctx, q.x, q.y, false))
		ctx["water_h"] = lo - 1.6
	return ctx

static func _noise(seed: int, f: float, oct: int, ft: int) -> FastNoiseLite:
	var n := FastNoiseLite.new()
	n.seed = seed; n.frequency = f; n.fractal_octaves = oct; n.fractal_type = ft
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	return n

static func _lake_pt(ctx: Dictionary, a: float, k: float) -> Vector2:
	var r: Vector2 = ctx["lake_r"]; var c: Vector2 = ctx["lake_c"]
	return c + Vector2(cos(a) * r.x * k, sin(a) * r.y * k).rotated(float(ctx["lake_rot"]))

## elliptical distance to the lake centre (1 = shoreline)
static func lake_d(ctx: Dictionary, x: float, z: float) -> float:
	if not ctx["has_lake"]:
		return 99.0
	var r: Vector2 = ctx["lake_r"]
	var q: Vector2 = (Vector2(x, z) - (ctx["lake_c"] as Vector2)).rotated(-float(ctx["lake_rot"]))
	var nd: FastNoiseLite = ctx["n_detail"]
	return Vector2(q.x / r.x, q.y / r.y).length() * (1.0 + nd.get_noise_2d(x * 2.0, z * 2.0) * 0.12)

## outside distance from the engagement corridor (0 inside)
static func corridor_out(ctx: Dictionary, x: float, z: float) -> float:
	var c: Vector2 = ctx["corridor"]
	var dx := maxf(absf(x) - c.x, 0.0); var dz := maxf(absf(z) - c.y, 0.0)
	return sqrt(dx * dx + dz * dz)

static func height(ctx: Dictionary, x: float, z: float, with_lake: bool = true) -> float:
	var amp: float = ctx["relief"]
	var nr: FastNoiseLite = ctx["n_relief"]; var nd: FastNoiseLite = ctx["n_detail"]; var nh: FastNoiseLite = ctx["n_hill"]
	var n2 := nd.get_noise_2d(x, z)
	var h := nr.get_noise_2d(x, z) * amp + n2 * amp * 0.22
	var dout := corridor_out(ctx, x, z)
	# deployment / engagement zone: gentle (30 % of the local relief), rising rolling hills outside it
	h = lerpf(h * 0.3, h, smoothstep(0.0, 150.0, dout))
	var e := smoothstep(30.0, 650.0, dout)
	h += e * e * amp * 3.2 + e * (nh.get_noise_2d(x, z) * 0.5 + 0.5) * amp * 3.0
	# rocky hill (granite knoll with outcrops)
	var dr := (Vector2(x, z) - (ctx["rock_c"] as Vector2)).length() / float(ctx["rock_r"])
	h += float(ctx["rock_h"]) * exp(-dr * dr * 1.8) * (0.85 + 0.3 * n2)
	# distant relief: ridged noise rising from ~1.4 km to the horizon ring
	var r := Vector2(x, z).length()
	if r > 1200.0:
		var nm: FastNoiseLite = ctx["n_mtn"]
		var m := smoothstep(1300.0, 3200.0, r)
		var ridge := nm.get_noise_2d(x, z) * 0.5 + 0.5
		h += m * float(ctx["mtn"]) * (0.25 + 0.95 * ridge * ridge) + m * 40.0
	if with_lake and ctx["has_lake"]:
		var ld := lake_d(ctx, x, z)
		if ld < 1.7:
			var wh: float = ctx["water_h"]
			var bed := wh - 0.6 - 4.5 * maxf(0.0, 1.0 - ld * ld)
			var shore := minf(h, wh + 0.3 + maxf(ld - 1.0, 0.0) * 7.0)   # gently shelving beach
			if ld < 1.0:
				h = lerpf(bed, shore, smoothstep(0.8, 1.0, ld))
			else:
				h = lerpf(shore, h, smoothstep(1.0, 1.7, ld))
	return h

## 0..1 forest cover (drives trees + forest-floor tint)
static func forest_f(ctx: Dictionary, x: float, z: float) -> float:
	var dout := corridor_out(ctx, x, z)
	var base := smoothstep(15.0, 110.0, dout)
	if base <= 0.0:
		return 0.0
	var nf: FastNoiseLite = ctx["n_forest"]
	var cl := nf.get_noise_2d(x, z) * 0.5 + 0.5
	var dens: float = ctx["forest"]
	var f := base * smoothstep(0.5 - 0.2 * dens, 0.64 - 0.2 * dens, cl + base * 0.12)
	f *= smoothstep(1.25, 1.9, lake_d(ctx, x, z))
	var dr := (Vector2(x, z) - (ctx["rock_c"] as Vector2)).length() / float(ctx["rock_r"])
	f *= smoothstep(0.35, 1.1, dr) * 0.75 + 0.25 * smoothstep(0.9, 1.3, dr)
	return f

# ============================================================== placement plan (pure)
## Returns {"trees": [[model, x, z, scale, yaw, tier, tint]], "far": [...], "rocks": [...], "cover": [...],
## "obstacles": [[Vector2, radius]]}. tier 0 = all qualities, 1 = medium+, 2 = high only.
static func plan(ctx: Dictionary) -> Dictionary:
	var rng := RandomNumberGenerator.new(); rng.seed = hash([int(ctx["seed"]), "env-plan"])
	var cor: Vector2 = ctx["corridor"]
	var trees: Array = []; var far: Array = []; var rocks: Array = []; var cover: Array = []; var obst: Array = []
	var ok_obstacle := func(x: float, z: float, rad: float) -> bool:
		return absf(x) > cor.x + rad + 10.0 or absf(z) > cor.y + rad + 10.0
	# --- near trees: jittered grid over the field + a margin, accepted by the forest cover
	var cell: float = ctx["tree_cell"]
	var n := int((FIELD + 140.0) / cell)
	var species: Array = ctx["trees"]
	var tp: float = ctx["tree_p"]
	var tsc: Vector2 = ctx["tree_scale"]
	for j in n:
		for i in n:
			var x := -FIELD / 2 - 70.0 + (i + rng.randf()) * cell
			var z := -FIELD / 2 - 70.0 + (j + rng.randf()) * cell
			var f := forest_f(ctx, x, z)
			var u := rng.randf()
			if species.is_empty() or u > f * tp or not ok_obstacle.call(x, z, 3.0):
				continue
			if ctx["has_lake"] and lake_d(ctx, x, z) < 1.2:
				continue
			# species mix: weight x edge preference (edge_bias > 0: fringes / clearings, < 0: forest core)
			var edge := 1.0 - smoothstep(0.35, 0.9, f)
			var model := _pick(species, edge, rng.randf())
			var s := rng.randf_range(tsc.x, tsc.y) * (0.85 + 0.25 * f)
			var tier := 0 if rng.randf() < 0.5 else (1 if rng.randf() < 0.55 else 2)
			trees.append([model, x, z, s, rng.randf() * TAU, tier, rng.randf()])
			obst.append([Vector2(x, z), 1.2 * s])
	# lone trees / small groves just outside the corridor (break up the hard forest edge)
	for k in int(ctx.get("lone_n", 90)):
		var x := rng.randf_range(-FIELD / 2, FIELD / 2); var z := rng.randf_range(-FIELD / 2, FIELD / 2)
		if not ok_obstacle.call(x, z, 3.0) or corridor_out(ctx, x, z) > 120.0 or lake_d(ctx, x, z) < 1.3:
			continue
		var lone: Array = ctx["lone"]
		if lone.is_empty():
			continue
		var model2: String = lone[rng.randi() % lone.size()]
		var s2 := rng.randf_range(0.8, 1.15)
		trees.append([model2, x, z, s2, rng.randf() * TAU, int(rng.randf() < 0.3), rng.randf()])
		obst.append([Vector2(x, z), 1.2 * s2])
	# --- far forest belts (distance LOD) out to ~2.6 km, below the treeline, off the lake
	var far_m: String = ctx["far_model"]; var fsc: Vector2 = ctx["far_scale"]; var fdn: float = ctx["far_dens"]
	var fc := 36.0   # sparse silhouette trees; the terrain shader paints the belt canopy (far_mask) between them
	var fn := int(5400.0 / fc)
	var tl: float = ctx["treeline"]
	var nf: FastNoiseLite = ctx["n_forest"]
	for j in fn:
		for i in fn:
			var x := -2700.0 + (i + rng.randf()) * fc
			var z := -2700.0 + (j + rng.randf()) * fc
			var u := rng.randf()
			if absf(x) < FIELD / 2 + 60.0 and absf(z) < FIELD / 2 + 60.0:
				continue
			var r := Vector2(x, z).length()
			var cl := nf.get_noise_2d(x * 0.6, z * 0.6) * 0.5 + 0.5
			var dens := smoothstep(0.38, 0.55, cl) * (1.0 - smoothstep(1700.0, 2500.0, r))
			if far_m == "" or u > dens * 0.95 * fdn:
				continue
			var h := height(ctx, x, z)
			if h > tl * rng.randf_range(0.7, 1.0) or lake_d(ctx, x, z) < 1.2:
				continue
			far.append([far_m, x, z, rng.randf_range(fsc.x, fsc.y), rng.randf() * TAU, 0 if rng.randf() < 0.45 else (1 if rng.randf() < 0.6 else 2), rng.randf()])
	# --- rocks: the granite knoll (outcrops + boulders), erratic boulder fields, lake-shore stones
	var rk: float = ctx["rocks"]
	var rc: Vector2 = ctx["rock_c"]; var rr: float = ctx["rock_r"]
	var add_rock := func(model: String, x: float, z: float, s: float, rad: float) -> void:
		if not ok_obstacle.call(x, z, rad * s):
			return
		rocks.append([model, x, z, s, rng.randf() * TAU, 0, rng.randf()])
		obst.append([Vector2(x, z), rad * s])
	var oc: String = ctx["outcrop"]; var bl: Array = ctx["boulders"]
	for k in (int(6 + 6 * rk) if oc != "" else 0):
		var a := rng.randf() * TAU; var d := sqrt(rng.randf()) * rr * 0.8
		add_rock.call(oc, rc.x + cos(a) * d, rc.y + sin(a) * d, rng.randf_range(0.7, 1.25), 5.5)
	for k in int(26 + 30 * rk):
		var a := rng.randf() * TAU; var d := sqrt(rng.randf()) * rr * 1.25
		add_rock.call(bl[k % bl.size()], rc.x + cos(a) * d, rc.y + sin(a) * d, rng.randf_range(0.6, 1.3), 2.2)
	var clusters := int(5 + 8 * rk)
	for c in clusters:
		var cx := rng.randf_range(-FIELD / 2 + 20, FIELD / 2 - 20); var cz := rng.randf_range(-FIELD / 2 + 20, FIELD / 2 - 20)
		if not ok_obstacle.call(cx, cz, 12.0):
			continue
		for k in rng.randi_range(2, 7):
			var a := rng.randf() * TAU; var d := rng.randf_range(0.0, 14.0)
			add_rock.call(bl[(k + 1) % bl.size()], cx + cos(a) * d, cz + sin(a) * d, rng.randf_range(0.45, 1.1), 2.2)
	if ctx["has_lake"]:
		for k in int(18 + 14 * rk):
			var a := rng.randf() * TAU
			var q := _lake_pt(ctx, a, rng.randf_range(0.92, 1.15))
			add_rock.call(bl[(k + 1) % mini(2, bl.size())], q.x, q.y, rng.randf_range(0.5, 1.2), 2.0)
	# --- ground cover (knee-high, no obstacle): grass tufts everywhere (sparser + shorter in the corridor), heather on
	# dry / rocky ground, pebbles round the rocks, juniper + logs at forest edges, reeds on the shore
	var nc: FastNoiseLite = ctx["n_cover"]
	var gc: float = ctx["cover_cell"]
	var gn := int(FIELD / gc)
	var dry: float = ctx["dry"]
	var cmain: String = ctx["cover_main"]; var acc: Array = ctx["accents"]
	var cp: float = ctx["cover_p"]; var cin: float = ctx["cover_in"]
	for j in gn:
		for i in gn:
			var x := -FIELD / 2 + (i + rng.randf()) * gc
			var z := -FIELD / 2 + (j + rng.randf()) * gc
			var u := rng.randf()
			var cv := nc.get_noise_2d(x, z) * 0.5 + 0.5
			var inside := corridor_out(ctx, x, z) <= 0.0
			var p := smoothstep(0.35, 0.7, cv) * (cin if inside else cp)
			if ctx["has_lake"] and lake_d(ctx, x, z) < 1.05:
				continue
			if u > p:
				continue
			var tier := 0 if rng.randf() < 0.35 else (1 if rng.randf() < 0.55 else 2)
			var dr := (Vector2(x, z) - rc).length() / rr
			var w := rng.randf()
			# accents {m, knoll, open, rock, s}: chance on the rocky knoll / in open dry ground off the corridor /
			# round the rocks; first match wins, else the main grass
			var am := ""
			for ac in acc:
				if (dr < 1.2 and w < float(ac.get("knoll", 0.0))) or (not inside and w < float(ac.get("open", 0.0)) * (1.0 + dry * 2.0)) or (dr < 1.6 and w < float(ac.get("rock", 0.0))) or (inside and w < float(ac.get("inside", 0.0))):
					am = ac["m"]
					var asc: Vector2 = ac.get("s", Vector2(0.7, 1.4))
					cover.append([am, x, z, rng.randf_range(asc.x, asc.y), rng.randf() * TAU, tier, rng.randf()])
					break
			if am != "" or cmain == "":
				continue
			else:
				# tint: 0 = green, 1 = straw; dry patches follow the cover noise + the variant's dryness
				var dr2 := clampf(smoothstep(0.55 - dry * 0.5, 0.85, nc.get_noise_2d(x * 0.31, z * 0.31) * 0.5 + 0.5 + rng.randf() * 0.25), 0.0, 1.0)
				cover.append([cmain, x, z, rng.randf_range(0.7, 1.4) * (0.75 if inside else 1.0), rng.randf() * TAU, tier, dr2])
	# shrubs / logs {m, n, fmin, fmax, r (obstacle radius per unit scale), s, tier}: forest edges (or open ground
	# with fmin < 0), all obstacles -> kept out of the corridor
	for sh in ctx["shrubs"]:
		var ssc: Vector2 = sh.get("s", Vector2(0.7, 1.4))
		var srad: float = sh.get("r", 0.8)
		for k in int(sh["n"]):
			var x := rng.randf_range(-FIELD / 2, FIELD / 2); var z := rng.randf_range(-FIELD / 2, FIELD / 2)
			var f := forest_f(ctx, x, z)
			var s := rng.randf_range(ssc.x, ssc.y)
			if f < float(sh.get("fmin", 0.05)) or f > float(sh.get("fmax", 0.6)) or not ok_obstacle.call(x, z, maxf(1.5, srad * s + 0.5)):
				continue
			if ctx["has_lake"] and lake_d(ctx, x, z) < 1.15:
				continue
			rocks.append([sh["m"], x, z, s, rng.randf() * TAU, int(rng.randf() < float(sh.get("tier", 0.4))), rng.randf()])
			obst.append([Vector2(x, z), srad * s])
	var shore: String = ctx["shore"]
	if ctx["has_lake"] and shore != "":
		for k in int(ctx["shore_n"]):
			var a := rng.randf() * TAU
			var q := _lake_pt(ctx, a, rng.randf_range(0.9, 1.08))
			cover.append([shore, q.x, q.y, rng.randf_range(0.7, 1.3), rng.randf() * TAU, 0 if k % 3 == 0 else 1, rng.randf()])
	return {"trees": trees, "far": far, "rocks": rocks, "cover": cover, "obstacles": obst}

static func _pick(species: Array, edge: float, v: float) -> String:
	var tot := 0.0
	for sp in species:
		tot += float(sp[1]) * maxf(0.0, 1.0 + float(sp[2]) * (edge * 1.4 - 0.4))
	var acc := 0.0
	for sp in species:
		acc += float(sp[1]) * maxf(0.0, 1.0 + float(sp[2]) * (edge * 1.4 - 0.4))
		if v * tot <= acc:
			return sp[0]
	return species[species.size() - 1][0]

## Regiment footprint vs obstacle check used by tests/test_env.gd (and debug): returns the closest clearance (m) of
## any obstacle to the regiment rectangle (negative = overlap).
static func clearance(obst: Array, pos: Vector2, half: Vector2) -> float:
	var best := 1e9
	for o in obst:
		var c: Vector2 = o[0]
		var d := Vector2(maxf(absf(c.x - pos.x) - half.x, 0.0), maxf(absf(c.y - pos.y) - half.y, 0.0)).length() - float(o[1])
		best = minf(best, d)
	return best

static func regs_of(sim) -> Array:
	var out: Array = []
	for r in sim.regs:
		out.append({"pos": r["pos"], "width": r.get("width", 20.0), "depth": r.get("depth", 10.0)})
	return out

# ============================================================== scene building (BattleView hooks)
## BattleView._build_ground replacement: fills bv.heights (GRID x GRID, h_at() unchanged) and adds near + far terrain.
static func build_ground(bv: Node) -> void:
	var t0 := Time.get_ticks_msec()
	var ctx := layout(bv.biome, regs_of(bv.sim))
	var grid: int = bv.GRID
	var hs := PackedFloat32Array(); hs.resize(grid * grid)
	var cell := FIELD / (grid - 1)
	for j in grid:
		for i in grid:
			hs[j * grid + i] = height(ctx, -FIELD / 2 + i * cell, -FIELD / 2 + j * cell)
	bv.heights = hs
	var mat := _terrain_material(ctx)
	# near field (same vertices as h_at) + a 4 m skirt round its edge to hide the seam to the coarser far ring
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in grid:
		for i in grid:
			st.add_vertex(Vector3(-FIELD / 2 + i * cell, hs[j * grid + i], -FIELD / 2 + j * cell))
	for j in grid - 1:
		for i in grid - 1:
			var a := j * grid + i
			st.add_index(a); st.add_index(a + 1); st.add_index(a + grid)
			st.add_index(a + 1); st.add_index(a + grid + 1); st.add_index(a + grid)
	st.generate_normals()
	var near := MeshInstance3D.new(); near.name = "EnvTerrainNear"
	near.mesh = st.commit(); near.material_override = mat
	bv.add_child(near)
	# far terrain: rows / cols at the field's 62.5 m spacing inside, growing ~3.5 % per step outward to FAR
	var cs: Array = []
	var x := FIELD / 2; var step := 50.0
	var outer: Array = []
	while x < FAR:
		x += step; step *= 1.035; outer.append(minf(x, FAR))
	for k in range(outer.size() - 1, -1, -1): cs.append(-float(outer[k]))
	for k in 17: cs.append(-FIELD / 2 + k * 62.5)
	for v in outer: cs.append(float(v))
	var nc := cs.size()
	var fst := SurfaceTool.new()
	fst.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in nc:
		for i in nc:
			var fx: float = cs[i]; var fz: float = cs[j]
			var on_rim := absf(fx) <= FIELD / 2 + 0.1 and absf(fz) <= FIELD / 2 + 0.1
			fst.add_vertex(Vector3(fx, height(ctx, fx, fz) - (0.8 if on_rim else 0.0), fz))
	for j in nc - 1:
		for i in nc - 1:
			var cx := (float(cs[i]) + float(cs[i + 1])) * 0.5; var cz := (float(cs[j]) + float(cs[j + 1])) * 0.5
			if absf(cx) < FIELD / 2 and absf(cz) < FIELD / 2:
				continue
			var a := j * nc + i
			fst.add_index(a); fst.add_index(a + 1); fst.add_index(a + nc)
			fst.add_index(a + 1); fst.add_index(a + nc + 1); fst.add_index(a + nc)
	fst.generate_normals()
	var farm := MeshInstance3D.new(); farm.name = "EnvTerrainFar"
	farm.mesh = fst.commit(); farm.material_override = mat
	farm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	bv.add_child(farm)
	if ctx["has_lake"]:
		var w := MeshInstance3D.new(); w.name = "EnvLake"
		var pm := PlaneMesh.new()
		var lr: Vector2 = ctx["lake_r"]
		pm.size = Vector2(lr.x, lr.y) * 3.0
		w.mesh = pm
		var lc: Vector2 = ctx["lake_c"]
		w.position = Vector3(lc.x, float(ctx["water_h"]), lc.y)
		w.rotation.y = -float(ctx["lake_rot"])
		var wm := ShaderMaterial.new(); wm.shader = load("res://shaders/env_water.gdshader")
		if mat is ShaderMaterial: wm.set_shader_parameter("noise_tex", (mat as ShaderMaterial).get_shader_parameter("noise_tex"))
		var wp: Dictionary = ctx["water"]
		for k in wp:
			wm.set_shader_parameter(k, wp[k])
		w.material_override = wm
		w.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		bv.add_child(w)
	ctx["ms_ground"] = Time.get_ticks_msec() - t0
	bv.env = ctx

static func _terrain_material(ctx: Dictionary) -> Material:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/battle_terrain.gdshader")
	if "t" in _arg("env-dbg"):
		var sm := StandardMaterial3D.new(); sm.albedo_color = Color(0.3, 0.4, 0.2)
		return sm
	var nt := NoiseTexture2D.new()
	nt.width = 512; nt.height = 512; nt.seamless = true; nt.generate_mipmaps = true
	var n2 := FastNoiseLite.new(); n2.seed = int(ctx["seed"]) % 9973; n2.frequency = 0.011; n2.fractal_octaves = 4
	nt.noise = n2
	m.set_shader_parameter("noise_tex", nt)
	m.set_shader_parameter("dryness", float(ctx["dry"]))
	m.set_shader_parameter("snow_h", float(ctx["snow_h"]))
	m.set_shader_parameter("treeline", float(ctx["treeline"]))
	m.set_shader_parameter("water_h", float(ctx["water_h"]))
	var pal: Dictionary = ctx["palette"]   # biome ground palette (shader uniforms: grass_a, dry, earth, rock, ...)
	for k in pal:
		if k != "straw":
			m.set_shader_parameter(k, pal[k])
	# masks, baked from the same functions that place trees / rocks
	var N := 192
	var ne := 620.0; var fe := 3000.0
	var im := Image.create(N, N, false, Image.FORMAT_RGBA8)
	var imf := Image.create(N, N, false, Image.FORMAT_RGBA8)
	var rc: Vector2 = ctx["rock_c"]; var rr: float = ctx["rock_r"]
	var nf: FastNoiseLite = ctx["n_forest"]
	for j in N:
		for i in N:
			var x := (i + 0.5) / N * 2.0 * ne - ne; var z := (j + 0.5) / N * 2.0 * ne - ne
			var f := forest_f(ctx, x, z)
			var worn := 1.0 - smoothstep(0.0, 70.0, corridor_out(ctx, x, z))
			var dr := (Vector2(x, z) - rc).length() / rr
			var lk := 0.0
			if ctx["has_lake"]:
				lk = 1.0 - smoothstep(1.0, 1.6, lake_d(ctx, x, z))
			im.set_pixel(i, j, Color(f, worn, lk, exp(-dr * dr * 1.6)))
			var fx := (i + 0.5) / N * 2.0 * fe - fe; var fz := (j + 0.5) / N * 2.0 * fe - fe
			var cl := nf.get_noise_2d(fx * 0.6, fz * 0.6) * 0.5 + 0.5
			var r := Vector2(fx, fz).length()
			var dens := smoothstep(0.38, 0.55, cl) * (1.0 - smoothstep(2600.0, 3000.0, r))
			if absf(fx) < ne and absf(fz) < ne:
				dens = forest_f(ctx, fx, fz)
			imf.set_pixel(i, j, Color(dens, 0, 0, 1))
	m.set_shader_parameter("near_mask", ImageTexture.create_from_image(im))
	m.set_shader_parameter("far_mask", ImageTexture.create_from_image(imf))
	m.set_shader_parameter("near_ext", ne); m.set_shader_parameter("far_ext", fe)
	return m

const DEF_TINT := [Color(0.88, 0.9, 0.86), Color(0.22, 0.18, 0.18)]
static var _meshes := {}
static func _mesh(model: String) -> Mesh:
	if _meshes.has(model):
		return _meshes[model]
	var path := "res://assets/models/%s.glb" % model
	var out: Mesh = null
	if ResourceLoader.exists(path):
		var sc: Node = (load(path) as PackedScene).instantiate()
		var stack: Array = [sc]
		while stack.size() > 0 and out == null:
			var n: Node = stack.pop_front()
			if n is MeshInstance3D:
				out = (n as MeshInstance3D).mesh
			stack.append_array(n.get_children())
		sc.free()
	_meshes[model] = out
	return out

static func _foliage_mat(albedo: float, wind: float, tuft: bool) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/env_foliage.gdshader")
	m.set_shader_parameter("albedo_mul", albedo)
	m.set_shader_parameter("wind", wind)
	m.set_shader_parameter("tuft", 1.0 if tuft else 0.0)
	m.set_shader_parameter("bend", 0.6 if not tuft else 0.3)
	return m

## BattleView._build_scenery replacement (after the dry legacy run that keeps BattleView.rng in step).
static func build_scenery(bv: Node) -> void:
	var t0 := Time.get_ticks_msec()
	var ctx: Dictionary = bv.env
	var pl := plan(ctx)
	ctx["plan"] = pl
	ctx["mmis"] = []
	var ma: Dictionary = ctx["mats"]   # per-biome albedo multipliers / wind
	var mats := {"tree": _foliage_mat(float(ma.get("tree", 2.4)), float(ma.get("wind", 1.0)), false), "rock": _foliage_mat(float(ma.get("rock", 1.3)), 0.0, false),
		"cover": _foliage_mat(float(ma.get("cover", 1.0)), float(ma.get("wind", 1.0)), true), "far": _foliage_mat(float(ma.get("far", 2.2)), 0.0, false)}
	var pal: Dictionary = ctx["palette"]
	if pal.has("straw"):
		(mats["cover"] as ShaderMaterial).set_shader_parameter("straw", pal["straw"])
	# near trees: 250 m tiles, detail mesh to ~330 m from the camera, then the far-LOD conifer
	var dbg := _arg("env-dbg")
	if "c" in dbg: pl["cover"] = []
	if "f" in dbg: pl["far"] = []
	_tiled(bv, ctx, pl["trees"], TREE_TILE, mats["tree"], not ("s" in dbg), 0.0, TREE_DETAIL, "T")
	var lod: Array = []
	var lodm: Dictionary = ctx["lod"]
	for t in pl["trees"]:
		var e: Array = (t as Array).duplicate()
		e[0] = lodm.get(str(t[0]), ctx["far_model"])
		if str(e[0]) != "":
			lod.append(e)
	_tiled(bv, ctx, lod, TREE_TILE, mats["far"], false, TREE_DETAIL, 0.0, "L")
	_tiled(bv, ctx, pl["far"], 900.0, mats["far"], false, 0.0, 0.0, "F")
	var stones: Array = []; var shrubs: Array = []
	var shm := {}
	for sh in ctx["shrubs"]:
		shm[str(sh["m"])] = true
	for r in pl["rocks"]:
		(shrubs if shm.has(str(r[0])) else stones).append(r)
	_tiled(bv, ctx, stones, 2000.0, mats["rock"], true, 0.0, 0.0, "R")
	_tiled(bv, ctx, shrubs, 2000.0, mats["tree"], true, 0.0, 0.0, "S")
	_tiled(bv, ctx, pl["cover"], COVER_TILE, mats["cover"], false, 0.0, 150.0, "C")
	ctx["ms_scenery"] = Time.get_ticks_msec() - t0
	apply_quality(bv)

## One MultiMeshInstance3D per (model, tile). Instances sorted by quality tier so apply_quality() only changes
## visible_instance_count (no extra nodes / draw calls per level).
static func _tiled(bv: Node, ctx: Dictionary, items: Array, tile: float, mat: Material, shadow: bool, vis_begin: float, vis_end: float, tag: String) -> void:
	var groups := {}
	var tints: Dictionary = ctx["tints"]; var tuft_m: String = ctx["cover_main"]
	for it in items:
		var k := "%s|%d|%d" % [it[0], int(floor((float(it[1]) + 5000.0) / tile)), int(floor((float(it[2]) + 5000.0) / tile))]
		if not groups.has(k):
			groups[k] = []
		groups[k].append(it)
	for k in groups.keys():
		var arr: Array = groups[k]
		var model: String = str(k).get_slice("|", 0)
		var mesh := _mesh(model)
		if mesh == null:
			continue
		arr.sort_custom(func(a, b): return int(a[5]) < int(b[5]))
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true; mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = arr.size()
		var tiers := [0, 0, 0]
		for n in arr.size():
			var it: Array = arr[n]
			var x: float = it[1]; var z: float = it[2]; var s: float = it[3]
			var y = bv.h_at(x, z) if absf(x) < FIELD / 2 and absf(z) < FIELD / 2 else height(ctx, x, z)
			var basis := Basis(Vector3.UP, float(it[4])).scaled(Vector3.ONE * s)
			if model.begins_with("env_grass") or model == "env_reeds" or model == str(ctx["cover_main"]):
				basis = basis.scaled(Vector3(1.0, 0.8 + float(it[6]) * 0.5, 1.0))
			mm.set_instance_transform(n, Transform3D(basis, Vector3(x, y - (0.15 if not model.begins_with("env_boulder") else 0.25 * s), z)))
			var v: float = it[6]
			# per-biome tint [base, variation] by model ("L:<model>" for the LOD copies), default: mild jitter
			var tk: Array = tints.get(("L:" + model) if tag == "L" else model, tints.get(model, DEF_TINT))
			var col: Color = (tk[0] as Color) + (tk[1] as Color) * v
			mm.set_instance_color(n, col)
			mm.set_instance_custom_data(n, Color(0, 0, 0, v if model == tuft_m else 0.0))
			tiers[int(it[5])] += 1
		var mmi := MultiMeshInstance3D.new()
		mmi.name = "Env%s_%s" % [tag, str(k).replace("|", "_")]
		mmi.multimesh = mm
		mmi.material_override = mat
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if vis_begin > 0.0: mmi.visibility_range_begin = vis_begin
		if vis_end > 0.0: mmi.visibility_range_end = vis_end
		mmi.set_meta("env_tiers", tiers)
		bv.add_child(mmi)
		(ctx["mmis"] as Array).append(mmi)

## Quality level -> how many of each multimesh's (tier-sorted) instances draw. low: tier 0, medium: 0-1, high: all.
static func apply_quality(bv: Node) -> void:
	var ctx = bv.get("env")
	if not (ctx is Dictionary) or not ctx.has("mmis"):
		return
	var q := clampi(int(Controls.quality), 0, 2)
	for mmi in ctx["mmis"]:
		if not is_instance_valid(mmi):
			continue
		var tiers: Array = mmi.get_meta("env_tiers")
		var n := 0
		for t in q + 1:
			n += int(tiers[t])
		(mmi as MultiMeshInstance3D).multimesh.visible_instance_count = n

## Light / sky / fog for the biome; called after BattleVisuals.apply() so it wins. Rendering only, idempotent.
## Quality-owned settings (shadow on / distance, MSAA, glow on / off, LOD) are left to BattleVisuals.QUALITY.
static func apply_look(bv: Node) -> void:
	var env: Environment = bv.environment
	var sun: DirectionalLight3D = bv.sun
	var ctx: Dictionary = bv.env
	var lk: Dictionary = ctx["look"]   # biome overrides; defaults = the reviewed Scandinavian summer afternoon
	var sm := env.sky.sky_material as ProceduralSkyMaterial
	if sm != null:
		sm.sky_top_color = lk.get("sky_top", Color(0.22, 0.4, 0.68))
		sm.sky_horizon_color = lk.get("sky_horizon", Color(0.74, 0.77, 0.8))
		sm.sky_curve = 0.12
		sm.ground_horizon_color = lk.get("ground_horizon", Color(0.62, 0.66, 0.68))
		sm.ground_bottom_color = lk.get("ground_bottom", Color(0.25, 0.27, 0.22))
		sm.sun_angle_max = 24.0
		sm.sun_curve = 0.12
		sm.sky_energy_multiplier = float(lk.get("sky_energy", 1.0))
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = float(lk.get("ambient", 0.85))
	env.ambient_light_sky_contribution = 0.85
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = float(lk.get("exposure", 1.04))
	env.tonemap_white = 6.0
	env.adjustment_enabled = true
	env.adjustment_contrast = float(lk.get("contrast", 1.06))
	env.adjustment_saturation = float(lk.get("saturation", 0.94))
	env.adjustment_brightness = 1.0
	# aerial perspective: the field (< ~350 m) stays clear, hills turn blue-grey, the mountains sit in haze
	env.fog_enabled = not ("--nofog" in OS.get_cmdline_user_args())
	env.fog_mode = Environment.FOG_MODE_DEPTH
	env.fog_depth_begin = float(lk.get("fog_begin", 350.0))
	env.fog_depth_end = float(lk.get("fog_end", 5200.0))
	env.fog_depth_curve = 1.25
	env.fog_density = float(lk.get("fog_density", 0.62))
	env.fog_light_color = lk.get("fog_color", Color(0.66, 0.72, 0.8))
	env.fog_light_energy = 1.0
	env.fog_sun_scatter = float(lk.get("fog_scatter", 0.18))
	env.fog_sky_affect = float(lk.get("fog_sky", 0.25))
	env.fog_height_density = 0.0
	# default: warm afternoon sun from the south-west, ~30 deg high: long soft shadows across the line, lit faces
	# toward the default camera (biomes change height / colour, e.g. a high harsh desert sun)
	sun.rotation_degrees = lk.get("sun_rot", Vector3(-31.0, 212.0, 0.0))
	sun.light_color = lk.get("sun_color", Color(1.0, 0.9, 0.76))
	sun.light_energy = float(lk.get("sun_energy", 1.55))
	sun.light_angular_distance = 0.6
	sun.shadow_bias = 0.08
	sun.shadow_normal_bias = 1.6
	sun.shadow_blur = 0.8
	sun.shadow_opacity = float(lk.get("shadow_opacity", 0.86))
	sun.directional_shadow_fade_start = 0.75
	var cam = bv.get("cam")
	if cam is Camera3D:
		(cam as Camera3D).far = 7000.0
