extends Node
## Battlefield-environment checks (env/scandinavia-medieval). Run:
##   godot --headless --path game res://tests/test_env.tscn
## 1. biome selection is data-driven (Scandinavian provinces -> biome, others / non-medieval -> legacy {})
## 2. the env plan is deterministic per battle seed
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

func _run() -> void:
	print("== Biome selection ==")
	var scand := 0; var scand_ok := 0; var other_empty := true
	for pid in GameData.provinces:
		var p: Dictionary = GameData.provinces[pid]
		var bi := BE.biome_for({"prov": pid, "terrain": p.get("terrain", "plains"), "seed": 7}, "medieval")
		if str(p.get("region", "")) in BE.REGIONS:
			scand += 1
			if not bi.is_empty():
				scand_ok += 1
		elif not bi.is_empty():
			other_empty = false
	check("every Scandinavian province (Norway/Sweden/Denmark/Finland) gets the boreal biome", scand > 0 and scand_ok == scand, "%d/%d" % [scand_ok, scand])
	check("non-Scandinavian provinces keep the legacy ground", other_empty)
	check("non-medieval eras keep the legacy ground", BE.biome_for({"prov": 348, "terrain": "forest", "seed": 1}, "c19").is_empty())
	var malmo := BE.biome_for({"prov": 348, "terrain": "forest", "seed": 1}, "medieval")
	var oslo := BE.biome_for({"prov": 328, "terrain": "tundra", "seed": 1}, "medieval")
	check("profile follows the data (Oslo: higher mountains than Malmö)", float(oslo.get("mtn", 0)) > float(malmo.get("mtn", 0)), "malmo %s oslo %s" % [malmo.get("mtn"), oslo.get("mtn")])

	print("== Determinism ==")
	var sim := BattleSim.new()
	sim.setup([_units("medieval", ["ranged", "inf", "ranged", "cav", "inf"], 1.0), _units("medieval", ["ranged", "inf", "ranged", "cav", "inf"], 1.0)], "forest", [{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 11)
	var c1 := BE.layout(BE.profile(GameData.provinces[348], "forest", 11), BE.regs_of(sim))
	var c2 := BE.layout(BE.profile(GameData.provinces[348], "forest", 11), BE.regs_of(sim))
	var h1 := str(BE.plan(c1)).md5_text(); var h2 := str(BE.plan(c2)).md5_text()
	var c3 := BE.layout(BE.profile(GameData.provinces[348], "forest", 12), BE.regs_of(sim))
	check("same seed -> identical plan", h1 == h2, h1)
	check("different seed -> different plan", str(BE.plan(c3)).md5_text() != h1)

	print("== Obstacle clearance over real battles ==")
	var worst_fight := 1e9; var worst_rout := 1e9; var rout_hits := 0; var samples := 0; var nobs := 0
	
	for seed in range(1, 13):
		for mult in [1.0, 2.5]:
			var s := BattleSim.new()
			var roles := ["ranged", "inf", "ranged", "cav", "inf", "inf", "cav"] if mult > 2.0 else ["ranged", "inf", "ranged", "cav", "inf"]
			s.setup([_units("medieval", roles, mult + 0.1 * (seed % 3)), _units("medieval", roles, mult)], ["plains", "hills", "forest"][seed % 3], [{"objective": BattleSim.OBJECTIVES[seed % BattleSim.OBJECTIVES.size()], "formation": "line"}, {"objective": "hold", "formation": "line"}], seed)
			s.record_events = false
			var pid: int = [348, 328, 406][seed % 3]
			var ctx := BE.layout(BE.profile(GameData.provinces[pid], s.terrain, seed), BE.regs_of(s))
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
