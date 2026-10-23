extends Node
## Battlefield-environment checks (all biome profiles present under scripts/battle/biomes). Run:
##   godot --headless --path game res://tests/test_env.tscn
## 1. biome selection is data-driven (every province -> a biome id; present biome files -> env, absent -> legacy {});
##    every model a present biome references exists
## 2. the env plan is deterministic per battle seed (each present biome)
## 3. obstacle clearance: real BattleSims (several sizes / objectives / seeds) are run to the end and every regiment
##    footprint is checked against every obstacle (trees, boulders, outcrops, junipers, logs) at every 0.5 s.
##    Fighting regiments must never touch an obstacle; routing regiments are reported (render-only props: no effect).
## Exit code = number of failures.

const BE := preload("res://scripts/battle/battle_environment.gd")
var fails := 0

func check(name: String, ok: bool, detail: String = "") -> void:
	if not ok:
		fails += 1
	print(("  [PASS] " if ok else "  [FAIL] ") + name + ("  -- " + detail if detail != "" else ""))

func _ready() -> void:
	GameData.load_all()
	call_deferred("_run")

func _units(era_id: String, roles: Array, mult: float) -> Array:
	var out: Array = []
	for i in roles.size():
		var uid := GameData.unit_for_role(era_id, roles[i])
		out.append({"army_id": 0, "unit_index": i, "type": uid, "men": float(GameData.units[uid]["men"]) * mult})
	return out

func _present() -> Array:
	var out: Array = []
	for id in BE.BIOMES:
		if ResourceLoader.exists(BE.BIOME_DIR % id):
			out.append(id)
	return out

## models a profile references (trees, LOD / far, rocks, cover, shrubs, shore)
func _models(pr: Dictionary) -> Array:
	var ms: Array = []
	for t in pr["trees"]: ms.append(t[0])
	ms.append_array(pr["lone"]); ms.append_array(pr["lod"].values()); ms.append_array(pr["boulders"])
	for k in ["far_model", "outcrop", "cover_main", "shore"]:
		ms.append(pr[k])
	for a in pr["accents"]: ms.append(a["m"])
	for sh in pr["shrubs"]: ms.append(sh["m"])
	return ms.filter(func(m): return str(m) != "")

func _run() -> void:
	var present := _present()
	print("== Biome selection (present biome files: %s) ==" % [present])
	var nordic := 0; var nordic_ok := 0; var bad_id := 0; var gate_ok := true
	var reps := {}   # biome -> sample province ids (different terrains first)
	var missing: Array = []
	for pid in GameData.provinces:
		var p: Dictionary = GameData.provinces[pid]
		var terr := str(p.get("terrain", "plains"))
		var id := BE.biome_id(p, terr)
		if not (id in BE.BIOMES):
			bad_id += 1
		var bi := BE.biome_for({"prov": pid, "terrain": terr, "seed": 7}, "medieval")
		if bi.is_empty() == (id in present):
			gate_ok = false
		if str(p.get("region", "")) in BE.REGIONS:
			nordic += 1
			if id == "boreal" and not bi.is_empty():
				nordic_ok += 1
		if id in present:
			if not reps.has(id): reps[id] = {}
			if not reps[id].has(terr): reps[id][terr] = pid
			for m in _models(bi):
				if not ResourceLoader.exists("res://assets/models/%s.glb" % m) and not (m in missing):
					missing.append(m)
	check("every province maps to a known biome profile", bad_id == 0, "%d unknown" % bad_id)
	check("every Nordic province (Norway/Sweden/Denmark/Finland/Åland) gets the boreal biome", nordic > 0 and nordic_ok == nordic, "%d/%d" % [nordic_ok, nordic])
	check("provinces of a present biome get it, absent biomes keep the legacy ground", gate_ok)
	check("every model a present biome references exists", missing.is_empty(), str(missing))
	check("all eras get the biome (no era gate)", not BE.biome_for({"prov": 348, "terrain": "forest", "seed": 1}, "c19").is_empty() and not BE.biome_for({"prov": 348, "terrain": "forest", "seed": 1}, "modern").is_empty())
	var malmo := BE.biome_for({"prov": 348, "terrain": "forest", "seed": 1}, "medieval")
	var oslo := BE.biome_for({"prov": 328, "terrain": "tundra", "seed": 1}, "medieval")
	check("profile follows the data (Oslo: higher mountains than Malmö)", float(oslo.get("mtn", 0)) > float(malmo.get("mtn", 0)), "malmo %s oslo %s" % [malmo.get("mtn"), oslo.get("mtn")])

	print("== Determinism ==")
	var sim := BattleSim.new()
	sim.setup([_units("medieval", ["ranged", "inf", "ranged", "cav", "inf"], 1.0), _units("medieval", ["ranged", "inf", "ranged", "cav", "inf"], 1.0)], "forest", [{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 11)
	for id in reps:
		var pid0: int = reps[id].values()[0]
		var c1 := BE.layout(BE.profile(GameData.provinces[pid0], str(GameData.provinces[pid0]["terrain"]), 11), BE.regs_of(sim))
		var c2 := BE.layout(BE.profile(GameData.provinces[pid0], str(GameData.provinces[pid0]["terrain"]), 11), BE.regs_of(sim))
		var h1 := str(BE.plan(c1)).md5_text(); var h2 := str(BE.plan(c2)).md5_text()
		var c3 := BE.layout(BE.profile(GameData.provinces[pid0], str(GameData.provinces[pid0]["terrain"]), 12), BE.regs_of(sim))
		check("%s: same seed -> identical plan, different seed -> different plan" % id, h1 == h2 and str(BE.plan(c3)).md5_text() != h1, h1)

	print("== Obstacle clearance over real battles ==")
	var worst_fight := 1e9; var worst_rout := 1e9; var rout_hits := 0; var samples := 0; var nobs := 0
	
	var cases: Array = []   # [province id, seed]
	for id in reps:
		var pids: Array = reps[id].values()
		if id == "boreal":
			pids = [348, 328, 406]
		var n := 12 if id == "boreal" else 6
		for k in n:
			cases.append([int(pids[k % pids.size()]), k + 1])
	for cs in cases:
		var seed: int = cs[1]
		for mult in [1.0, 2.5]:
			var s := BattleSim.new()
			var roles := ["ranged", "inf", "ranged", "cav", "inf", "inf", "cav"] if mult > 2.0 else ["ranged", "inf", "ranged", "cav", "inf"]
			var era: String = ["medieval", "early_modern", "c19", "c20", "modern"][(seed + int(mult)) % 5]   # all eras get the env now
			s.setup([_units(era, roles, mult + 0.1 * (seed % 3)), _units(era, roles, mult)], ["plains", "hills", "forest"][seed % 3], [{"objective": BattleSim.OBJECTIVES[seed % BattleSim.OBJECTIVES.size()], "formation": "line"}, {"objective": "hold", "formation": "line"}], seed)
			s.record_events = false
			var pid: int = cs[0]
			var ctx := BE.layout(BE.profile(GameData.provinces[pid], str(GameData.provinces[pid]["terrain"]), seed), BE.regs_of(s))
			var obst: Array = BE.plan(ctx)["obstacles"]
			nobs += obst.size()
			while not s.done and s.t < 400.0:
				s.run_seconds(0.5)
				for r in s.regs:
					if float(r.get("men", 1.0)) <= 0.0:
						continue
					var half := Vector2(float(r["width"]), float(r["depth"])) * 0.5
					var cl := BE.clearance(obst, r["pos"], half)
					samples += 1
					if str(r.get("state", "")) == "rout":
						worst_rout = minf(worst_rout, cl)
						if cl < 0.0:
							rout_hits += 1
					else:
						worst_fight = minf(worst_fight, cl)
	check("no fighting regiment footprint ever meets an obstacle", worst_fight > 0.0, "min clearance %.1f m over %d samples, %d obstacles" % [worst_fight, samples, nobs])
	print("  [INFO] routing regiments: min clearance %.1f m, %d overlapping samples (props are render-only; no sim effect)" % [worst_rout, rout_hits])
	print("\n==== test_env: %d failures ====" % fails)
	get_tree().quit(fails)
