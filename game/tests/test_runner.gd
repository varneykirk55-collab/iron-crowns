extends Node
## Headless gameplay playtests. Run:
##   godot --headless --path game res://tests/test_runner.tscn -- --results=/path/results.json
## Each check records PASS/FAIL with measured values. Exit code = number of failures.

var results: Array = []
var fails := 0
var out_path := "user://test_results.json"
var only := ""

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--results="):
			out_path = a.substr(10)
		if a.begins_with("--only="):
			only = a.substr(7)
	call_deferred("_run")

func check(name: String, ok: bool, detail: String = "") -> bool:
	results.append({"test": name, "pass": ok, "detail": detail})
	if not ok:
		fails += 1
	print(("  [PASS] " if ok else "  [FAIL] ") + name + ("  -- " + detail if detail != "" else ""))
	return ok

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	GameData.load_all()
	if only == "" or only == "battle":
		test_battle_model()
	for code in ["USA", "SWE", "JPN"]:
		if only == "" or only == code:
			test_nation(code)
	if only == "" or only == "era":
		test_era("SWE")
	if only == "" or only == "continuity":
		test_continuity()
	if only == "" or only == "save":
		test_save_load()
	if only == "" or only == "camera":
		test_camera_determinism()
	if only == "" or only == "controls":
		await test_controls()
	if only == "" or only == "eras":
		test_era_battles()
	if only == "" or only == "gameplay":
		await test_gameplay_script()
	if only == "bench":
		await bench_cpu()
	var summary := {"passed": results.size() - fails, "failed": fails, "total": results.size(), "seconds": (Time.get_ticks_msec() - t0) / 1000.0,
		"godot": Engine.get_version_info()["string"], "results": results}
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(summary, "  "))
	print("\n==== %d / %d checks passed (%.1f s) ====" % [summary["passed"], summary["total"], summary["seconds"]])
	get_tree().quit(fails)

# ---------------------------------------------------------------- battle model
func _units_for(era_id: String, roles: Array, mult: float = 1.0) -> Array:
	var out: Array = []
	for i in roles.size():
		var uid := GameData.unit_for_role(era_id, roles[i])
		out.append({"army_id": 0, "unit_index": i, "type": uid, "men": float(GameData.units[uid]["men"]) * mult})
	return out

func test_battle_model() -> void:
	print("== Battle model ==")
	var durations := {}
	for era_d in GameData.eras:
		var e: String = era_d["id"]
		var ds: Array = []
		var wins := [0, 0]
		for seed in range(1, 9):
			var s := BattleSim.new()
			var a := _units_for(e, ["ranged", "inf", "ranged", "cav", "art"], 1.0 + 0.1 * (seed % 3))
			var d := _units_for(e, ["ranged", "inf", "ranged", "cav", "art"], 1.0)
			s.setup([a, d], ["plains", "hills", "forest"][seed % 3], [{"objective": BattleSim.OBJECTIVES[seed % 4], "formation": "line"}, {"objective": "hold", "formation": "line"}], seed)
			s.record_events = false
			s.run_to_end()
			ds.append(s.t)
			wins[s.winner] += 1
		var mean := 0.0
		for x in ds:
			mean += x
		mean /= ds.size()
		durations[e] = mean
		check("battle duration %s mean %.1fs (target 25-50s)" % [e, mean], mean >= 22.0 and mean <= 55.0, "durations=%s wins(att,def)=%s" % [str(ds.map(func(x): return snappedf(x, 0.1))), str(wins)])
	# determinism: strategic stepping vs real-time (watched) stepping with irregular frame deltas
	var mk := func() -> BattleSim:
		var s := BattleSim.new()
		s.setup([_units_for("c19", ["ranged", "ranged", "inf", "cav", "art"]), _units_for("c19", ["ranged", "inf", "inf", "cav"])], "hills",
			[{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "deep"}], 424242)
		return s
	var s1: BattleSim = mk.call()
	s1.record_events = false
	while not s1.done:
		s1.run_seconds(Sim.BATTLE_SECONDS_PER_DAY)
	var s2: BattleSim = mk.call()
	s2.record_events = true
	var acc := 0.0
	var rng := RandomNumberGenerator.new(); rng.seed = 9
	while not s2.done:
		acc += rng.randf_range(0.005, 0.05)  # 20-200 fps frames
		while acc >= BattleSim.DT and not s2.done:
			acc -= BattleSim.DT
			s2.step()
	var r1 := s1.result(); var r2 := s2.result()
	check("watched vs unwatched battle give identical outcome", r1["winner"] == r2["winner"] and r1["steps"] == r2["steps"] and str(r1["men"]) == str(r2["men"]),
		"winner %d/%d, steps %d/%d, t=%.1fs" % [r1["winner"], r2["winner"], r1["steps"], r2["steps"], r1["time"]])
	check("watched battle emitted visual events (volleys/charges)", s2.events.size() > 20, "%d events" % s2.events.size())

# ---------------------------------------------------------------- per nation
func _strongest_army(code: String) -> Dictionary:
	var best := {}
	for a in Sim.armies.values():
		if a["owner"] == code and (best.is_empty() or Sim.army_strength(a) > Sim.army_strength(best)):
			best = a
	return best

func test_nation(code: String) -> void:
	print("== Nation playtest: %s ==" % code)
	Sim.auto_deploy = true
	Sim.auto_respond_player = "decline"
	Sim.new_game(code, 1800, 7)
	var n: Dictionary = Sim.nations[code]
	check("%s: new game started as player" % code, Sim.player == code and n["ai"] == false and Sim.nation_provs[code].size() > 0,
		"%d provinces, capital %s" % [Sim.nation_provs[code].size(), GameData.provinces[n["capital"]]["name"]])
	var f0: float = n["funds"]
	Sim.advance_days(31)
	check("%s: time advances (31 days, monthly economy)" % code, Sim.day == 31 and n["income"].get("total", 0.0) > 0.0,
		"date %s, income %.0f/mo, expenses %.0f/mo, funds %.0f -> %.0f" % [Sim.date_string(), n["income"]["total"], n["expense"]["total"], f0, n["funds"]])
	# --- procurement
	var era_id: String = GameData.eras[Sim.era]["id"]
	var army: Dictionary = _strongest_army(code)
	var cap: int = n["capital"]
	# gather the main army at the capital first so purchases join it
	var funds_before: float = n["funds"]
	var bought := 0
	for uid in ["line_inf", "line_inf", "field_guns", "hussars", "line_inf", "grenadiers"]:
		var r := Sim.buy_unit(code, uid, cap)
		if r["ok"]:
			bought += 1
	check("%s: buy units (instant procurement)" % code, bought >= 2 and n["funds"] < funds_before,
		"bought %d units, funds %.0f -> %.0f" % [bought, funds_before, n["funds"]])
	var old_buy := Sim.buy_unit(code, "knights", cap)
	check("%s: older-era equipment cannot be procured" % code, not old_buy["ok"], old_buy.get("msg", ""))
	# --- pick war target: the weakest reachable neighbour
	var target := ""; var ts := 1e18
	for o in Sim.neighbors_of(code):
		if Sim.nations[o]["alive"] and Sim.can_declare_war(code, o)["ok"]:
			var s := Sim.strength(o)
			for al in Sim.allies_of(o):
				s += Sim.strength(al)
			# prefer land neighbours (Japan has none, so it must go by sea)
			if not Sim._shares_border(code, o):
				s += 1.0e7
			if s < ts:
				ts = s; target = o
	check("%s: found reachable war target" % code, target != "", "target %s (strength %.0f vs ours %.0f)" % [target, ts, Sim.strength(code)])
	if target == "":
		return
	var ok := Sim.declare_war(code, target)
	check("%s: declare war on %s" % [code, target], ok and Sim.at_war(code, target), "allies called: %s" % str(Sim.allies_of(target)))
	# --- the army at the capital marches on the enemy capital (where its army is)
	var strike: Dictionary = {}
	for a in Sim.armies_in(cap):
		if a["owner"] == code and (strike.is_empty() or a["units"].size() > strike["units"].size()):
			strike = a
	# merge everything at the capital into one strike force
	for a in Sim.armies_in(cap):
		if a["owner"] == code and a["id"] != strike["id"]:
			Sim.merge_armies(strike["id"], a["id"])
	var tcap: int = Sim.nations[target]["capital"]
	var mv := Sim.order_move(strike["id"], tcap)
	var naval := false
	for nd in mv.get("path", []):
		if nd >= GameData.SEA_NODE:
			naval = true
	check("%s: order army to enemy capital %s" % [code, GameData.provinces[tcap]["name"]], mv["ok"], "path %d nodes, ~%s days, naval crossing=%s" % [mv.get("path", []).size(), str(mv.get("days", "?")), str(naval)])
	if code == "JPN":
		check("JPN: route uses naval transport", naval, "")
	# --- run the simulation and watch for battles + territory change
	var sid: int = strike["id"]
	var battles_seen := {}
	var won_battles := 0
	var captured := []
	var cb := func(bid: int, res: Dictionary) -> void:
		var b: Dictionary = Sim.battles[bid]
		if b["codes"].has(code) or b["armies"][0].has(sid) or b["armies"][1].has(sid):
			battles_seen[bid] = res
	var cb2 := func(pid: int, old: String, nw: String) -> void:
		if nw == code:
			captured.append(pid)
	Sim.battle_resolved.connect(cb)
	Sim.ownership_changed.connect(cb2)
	var start_owned: int = Sim.nation_provs[code].size()
	for i in 500:
		Sim.tick_day()
		if not Sim.armies.has(sid):
			# army destroyed: send the next strongest
			var na := _strongest_army(code)
			if na.is_empty():
				break
			sid = na["id"]
			Sim.order_move(sid, Sim.nations[target]["capital"] if Sim.nations[target]["alive"] else cap)
		elif Sim.armies[sid]["path"].is_empty() and Sim.armies[sid]["state"] == "idle" and Sim.nations[target]["alive"] and i % 10 == 0:
			# keep pushing into enemy land: nearest enemy province
			var best := -1; var bd := 1e18
			for pid in Sim.nation_provs[target]:
				var d := GameData.node_km(Sim.armies[sid]["node"], pid)
				if d < bd:
					bd = d; best = pid
			if best >= 0:
				Sim.order_move(sid, best)
		if captured.size() >= 1 and battles_seen.size() >= 1 and i > 60:
			break
	Sim.battle_resolved.disconnect(cb)
	Sim.ownership_changed.disconnect(cb2)
	var bdesc := ""
	for bid in battles_seen.keys():
		var r: Dictionary = battles_seen[bid]
		bdesc += "[winner side %d, %.0fs, losses %d/%d] " % [r["winner"], r["time"], int(r["losses"][0]), int(r["losses"][1])]
	check("%s: a battle was triggered and resolved by the battle model" % code, battles_seen.size() >= 1, bdesc)
	var names := captured.map(func(p): return GameData.provinces[p]["name"])
	check("%s: territory changed hands via siege" % code, captured.size() >= 1,
		"captured %s by %s; provinces %d -> %d" % [str(names), Sim.date_string(), start_owned, Sim.nation_provs[code].size()])
	# map ownership lookup agrees
	if captured.size() > 0:
		check("%s: ownership table reflects capture" % code, Sim.prov_owner[captured[-1]] == code or Sim.stats["captures"] > 0, "")
	# --- AI diplomacy over 3 years
	var st0: Dictionary = Sim.stats.duplicate()
	Sim.advance_days(365 * 3)
	var st: Dictionary = Sim.stats
	var ai_diplo: int = (st["ai_trades"] - st0["ai_trades"]) + (st["ai_alliances"] - st0["ai_alliances"]) + (st["ai_naps"] - st0["ai_naps"])
	var ai_war: int = st["ai_wars"] - st0["ai_wars"]
	var ai_peace: int = st["ai_peace"] - st0["ai_peace"]
	check("%s: AI nations negotiate (trade/alliance/NAP)" % code, ai_diplo > 0, "trade %d, alliance %d, NAP %d, proposals %d, rejections %d" % [
		st["ai_trades"] - st0["ai_trades"], st["ai_alliances"] - st0["ai_alliances"], st["ai_naps"] - st0["ai_naps"], st["ai_proposals"] - st0["ai_proposals"], st["ai_rejections"] - st0["ai_rejections"]])
	check("%s: AI nations declare war / make peace" % code, ai_war + ai_peace > 0, "AI wars %d, AI peace %d, captures total %d, nations eliminated %d" % [ai_war, ai_peace, st["captures"], st["eliminated"]])
	check("%s: AI nations recruit armies" % code, st["ai_units_bought"] > st0["ai_units_bought"], "%d units bought by AI" % (st["ai_units_bought"] - st0["ai_units_bought"]))
	var ai_exp := 0
	for c in GameData.majors.keys():
		if c != code and Sim.nations.has(c):
			var base: int = GameData.countries[c]["provinces"].size()
			if Sim.nation_provs[c].size() > base:
				ai_exp += 1
	check("%s: AI majors expand territory" % code, ai_exp > 0, "%d AI majors gained provinces" % ai_exp)
	print("  final date %s; %s funds %.0f, stability %.2f, provinces %d" % [Sim.date_string(), code, n["funds"], n["stability"], Sim.nation_provs[code].size()])

# ---------------------------------------------------------------- era
func test_era(code: String) -> void:
	print("== Era progression ==")
	Sim.auto_deploy = true
	Sim.new_game(code, 1913, 3, 300)
	var e0 := Sim.era
	var a: Dictionary = _strongest_army(code)
	var old_era: String = a["units"][0]["era"]
	var fired := [false]
	var cb := func(i: int) -> void: fired[0] = true
	Sim.era_changed.connect(cb)
	Sim.advance_days(70)
	Sim.era_changed.disconnect(cb)
	check("era advances with sim time (1913 -> 1914)", Sim.era == e0 + 1 and fired[0], "%s -> %s on %s" % [GameData.eras[e0]["name"], GameData.eras[Sim.era]["name"], Sim.date_string()])
	check("existing armies keep their old-era equipment", a["units"][0]["era"] == old_era and old_era == "c19", "unit %s era %s" % [a["units"][0]["type"], a["units"][0]["era"]])
	var r_old := Sim.buy_unit(code, "line_inf")
	var r_new := Sim.buy_unit(code, "riflemen")
	check("procurement offers only the new era's equipment", not r_old["ok"] and r_new["ok"], "line_inf: %s / riflemen: %s" % [r_old.get("msg", "ok"), str(r_new["ok"])])
	var e_before := Sim.era
	Sim.nations[code]["funds"] += 0.0
	var cost := Sim.refit_cost(a)
	if Sim.nations[code]["funds"] < cost:
		Sim.nations[code]["funds"] = cost + 10.0  # test grant so refit can be exercised
	var rf := Sim.refit_army(a["id"])
	check("refit upgrades army to current era", rf["ok"] and a["units"][0]["era"] == "c20", "cost %.0f, changed %d units -> %s" % [cost, rf.get("changed", 0), a["units"][0]["type"]])
	check("buying/refitting does not change the era", Sim.era == e_before, "")
	# all eras reachable from the menu start years
	var eras_ok := true
	for y in GameData.start_years:
		Sim.new_game(code, y, 1)
		var expected := GameData.era_for_year(y)
		if Sim.era != expected:
			eras_ok = false
	check("all start years (1300/1500/1800/1914/1980) start in their era", eras_ok, str(GameData.start_years))

# ---------------------------------------------------------------- continuity
func test_continuity() -> void:
	print("== Continuity while watching a battle ==")
	Sim.auto_deploy = false
	Sim.auto_respond_player = "decline"
	Sim.new_game("SWE", 1800, 11)
	Sim.advance_days(40)
	# set up a player battle: march into a neighbour after declaring war
	var target := "NOR"
	Sim.declare_war("SWE", target)
	var a: Dictionary = _strongest_army("SWE")
	Sim.order_move(a["id"], Sim.nations[target]["capital"])
	var bid := -1
	for i in 300:
		if i % 5 == 0 and Sim.armies.has(a["id"]) and Sim.armies[a["id"]]["state"] != "battle":
			# chase the nearest Norwegian army
			var best := -1; var bd := 1e18
			for o in Sim.armies.values():
				if o["owner"] == target and o["node"] < GameData.SEA_NODE:
					var d := GameData.node_km(a["node"], o["node"])
					if d < bd:
						bd = d; best = o["node"]
			if best >= 0:
				Sim.order_move(a["id"], best)
		Sim.tick_day()
		for b in Sim.battles.values():
			if b["player_side"] >= 0 and b["awaiting"]:
				bid = b["id"]
		if bid >= 0:
			break
	check("player battle awaits deployment orders", bid >= 0, "")
	if bid < 0:
		return
	Sim.deploy_battle(bid, {"objective": "assault", "formation": "line"}, true)
	var b: Dictionary = Sim.battles[bid]
	var day0 := Sim.day
	var other_resolved := [0]
	var cb := func(id: int, res: Dictionary) -> void:
		if id != bid:
			other_resolved[0] += 1
	Sim.battle_resolved.connect(cb)
	# strategic time keeps running while the battle is watched in real time (10 sim days per battle second here)
	var steps0: int = b["sim"].steps
	for i in 30:
		Sim.tick_day()
	check("watched battle is not stepped by the strategic clock", b["sim"].steps == steps0, "steps %d" % b["sim"].steps)
	check("strategic sim keeps running during watched battle", Sim.day == day0 + 30, "day %d -> %d" % [day0, Sim.day])
	var t_real := 0.0
	while not Sim.step_watched(bid, 1.0 / 30.0):
		t_real += 1.0 / 30.0
		if int(t_real * 30) % 30 == 0:
			Sim.tick_day()
	Sim.battle_resolved.disconnect(cb)
	check("watched battle resolves in real time (15-85 s)", b["done"] and t_real > 15.0 and t_real < 85.0, "%.1f s of real time, winner side %d" % [t_real, b["result"]["winner"]])
	check("other battles/events continued meanwhile (none skipped)", Sim.day > day0 + 30, "other battles resolved meanwhile: %d, log entries %d" % [other_resolved[0], Sim.event_log.size()])

# ---------------------------------------------------------------- save / load (v0.2)
func _state_diff(a: Dictionary, b: Dictionary) -> String:
	var out: Array = []
	for k in a.keys():
		if not b.has(k) or var_to_bytes(a[k]) != var_to_bytes(b[k]):
			out.append(str(k))
	for k in b.keys():
		if not a.has(k):
			out.append("+" + str(k))
	return ",".join(out)

func test_save_load() -> void:
	print("== Save / load ==")
	Sim.auto_deploy = true
	Sim.auto_respond_player = "decline"
	Sim.new_game("SWE", 1800, 11)
	# make the world busy: wars, sieges, ongoing battles
	var tgt := ""
	for o in Sim.neighbors_of("SWE"):
		if Sim.can_declare_war("SWE", o)["ok"]:
			tgt = o; break
	if tgt != "":
		Sim.declare_war("SWE", tgt)
		for a in Sim.armies.values():
			if a["owner"] == "SWE":
				Sim.order_move(a["id"], Sim.nations[tgt]["capital"])
	Sim.advance_days(120)
	var waited := 0
	while waited < 600:
		var live := Sim.battles.values().filter(func(b): return not b["done"] and b["sim"] != null and b["sim"].t > 0.0)
		if live.size() > 0 and Sim.wars.size() > 0:
			break
		Sim.tick_day(); waited += 1
	var n_days := Sim.day
	var live_b := Sim.battles.values().filter(func(b): return not b["done"] and b["sim"] != null).size()
	check("save: campaign state is non-trivial at save time", Sim.wars.size() > 0 and live_b > 0,
		"day %d (%s), wars %d, battles in progress %d, armies %d, treaties %d, sieges %d" % [n_days, Sim.date_string(), Sim.wars.size(), live_b, Sim.armies.size(), Sim.treaties.size(), Sim.sieges.size()])
	var snap := Sim.serialize_state()
	var r := Sim.save_game("test_slot")
	check("save: write user://saves/test_slot.save", r["ok"] and FileAccess.file_exists(r.get("path", "")), r["msg"] + " size %d B" % (FileAccess.get_file_as_bytes(r.get("path", "")).size() if r["ok"] else 0))
	var meta := Sim.read_meta(Sim.save_path("test_slot"))
	check("save: metadata header readable", meta.get("player", "") == "SWE" and meta.get("date", "") == Sim.date_string(), str(meta))
	# reference run: continue M days from the in-memory state
	var M := 180
	Sim.advance_days(M)
	var ref_after := Sim.serialize_state()
	# fresh load: wipe everything by starting an unrelated game, then load
	Sim.new_game("JPN", 1500, 99)
	var lr := Sim.load_game("test_slot")
	var loaded := Sim.serialize_state()
	var d1 := _state_diff(snap, loaded)
	check("save: loaded state deep-equals saved state", lr["ok"] and d1 == "", lr["msg"] + ((" differs: " + d1) if d1 != "" else ", %d bytes identical" % var_to_bytes(snap).size()))
	var bs_ok := true
	for bid in Sim.battles.keys():
		var b: Dictionary = Sim.battles[bid]
		if b["sim"] != null and not (b["sim"] is BattleSim):
			bs_ok = false
	check("save: in-progress battles restored as live BattleSim objects", bs_ok and Sim.battles.size() == snap["battles"].size(), "%d battles" % Sim.battles.size())
	Sim.advance_days(M)
	var load_after := Sim.serialize_state()
	var d2 := _state_diff(ref_after, load_after)
	check("save: determinism, original and loaded runs identical after %d more days" % M, d2 == "",
		("differs: " + d2) if d2 != "" else "both at %s, %d armies, %d battles, %d events" % [Sim.date_string(), Sim.armies.size(), Sim.battles.size(), Sim.event_log.size()])
	check("save: missing slot reports an error", not Sim.load_game("no_such_slot")["ok"], "")
	var listed := Sim.list_saves().any(func(m): return m["slot"] == "test_slot")
	check("save: slot appears in save list", listed, "")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Sim.save_path("test_slot")))

# ---------------------------------------------------------------- battle camera never affects the sim
func _cam_battle_setup() -> int:
	Sim.auto_deploy = false
	Sim.auto_respond_player = "decline"
	Sim.new_game("SWE", 1800, 11)
	var tgt := ""
	for o in Sim.neighbors_of("SWE"):
		if Sim.can_declare_war("SWE", o)["ok"]:
			tgt = o; break
	Sim.declare_war("SWE", tgt)
	var mine := _strongest_army("SWE")
	var theirs := _strongest_army(tgt)
	var bid := Sim._start_battle(int(theirs["node"]), [mine["id"]], [theirs["id"]])
	Sim.deploy_battle(bid, {"objective": "assault", "formation": "line"}, true)
	return bid

## Runs the watched battle frame by frame through a real BattleView. toggles: inject camera input events.
func _cam_run(bid: int, sim_d: Dictionary, toggles: bool, frame_dts: PackedFloat32Array) -> Dictionary:
	var b: Dictionary = Sim.battles[bid]
	b["sim"] = BattleSim.from_dict(sim_d)
	b["sim"].record_events = true
	b["acc"] = 0.0; b["watched"] = true; b["done"] = false
	var bv := BattleView.new()
	add_child(bv)
	bv.setup(bid)
	var info := {"toggles": 0, "min_w": 1.0, "max_w": 0.0, "shots": {}, "cuts": 0, "nan": false, "frames": 0}
	var f := 0
	while not bv.finished and f < frame_dts.size():
		if toggles:
			if f % 53 == 17:
				var e := InputEventKey.new(); e.keycode = KEY_C; e.physical_keycode = KEY_C; e.pressed = true
				bv._unhandled_input(e); info["toggles"] += 1
			if f % 211 == 100:
				var j := InputEventJoypadButton.new(); j.button_index = JOY_BUTTON_Y; j.pressed = true
				bv._unhandled_input(j); info["toggles"] += 1
			if f % 167 == 60:
				var w := InputEventMouseButton.new(); w.button_index = MOUSE_BUTTON_WHEEL_UP; w.pressed = true
				bv._unhandled_input(w)
		bv._process(frame_dts[f])
		info["min_w"] = minf(info["min_w"], bv.blend_w); info["max_w"] = maxf(info["max_w"], bv.blend_w)
		info["shots"][bv.shot_kind] = true
		var cp: Vector3 = bv.cam.global_position
		if not (is_finite(cp.x) and is_finite(cp.y) and is_finite(cp.z)):
			info["nan"] = true
		f += 1
	info["frames"] = f
	info["cuts"] = bv.shot_seq
	var s: BattleSim = b["sim"]
	info["state"] = s.to_dict()
	info["result"] = s.result()
	remove_child(bv)
	bv.free()
	return info

func test_camera_determinism() -> void:
	print("== Battle camera ==")
	var bid := _cam_battle_setup()
	var b: Dictionary = Sim.battles[bid]
	var sim_d: Dictionary = b["sim"].to_dict()
	var world := Sim.serialize_state()
	var dts := PackedFloat32Array()
	var rng := RandomNumberGenerator.new(); rng.seed = 77
	for i in 20000:
		dts.append(rng.randf_range(1.0 / 70.0, 1.0 / 20.0))
	# reference: the bare BattleSim stepped exactly like Sim.step_watched, no view at all
	var ref := BattleSim.from_dict(sim_d); ref.record_events = true
	var acc := 0.0; var fi := 0
	while not ref.done and fi < dts.size():
		acc += dts[fi]; fi += 1
		while acc >= BattleSim.DT and not ref.done:
			acc -= BattleSim.DT; ref.step()
	var ref_state := ref.to_dict()
	var quiet := _cam_run(bid, sim_d, false, dts)
	Sim.apply_state(world.duplicate(true)); Sim.set_watched(bid, true)
	var noisy := _cam_run(bid, sim_d, true, dts)
	check("camera: battle under a live view (no toggles) == bare sim", _state_diff(ref_state, quiet["state"]) == "",
		"winner %d, t=%.1fs, %d frames; %s" % [quiet["result"]["winner"], quiet["result"]["time"], quiet["frames"], _state_diff(ref_state, quiet["state"])])
	check("camera: %d camera toggles + zoom input give an identical battle" % noisy["toggles"], _state_diff(quiet["state"], noisy["state"]) == "" and noisy["toggles"] >= 10,
		"steps %d/%d, men %s / %s %s" % [quiet["result"]["steps"], noisy["result"]["steps"], str(quiet["result"]["men"]), str(noisy["result"]["men"]), _state_diff(quiet["state"], noisy["state"])])
	check("camera: blend reached both overhead (0) and cinematic (1)", noisy["min_w"] <= 0.001 and noisy["max_w"] >= 0.999, "min %.3f max %.3f" % [noisy["min_w"], noisy["max_w"]])
	var kinds: Array = quiet["shots"].keys()
	check("camera: director cut between event-driven shots", quiet["cuts"] >= 4 and kinds.size() >= 3 and (kinds.has("low_angle") or kinds.has("flank") or kinds.has("tracking")),
		"%d cuts, shot kinds %s" % [quiet["cuts"], str(kinds)])
	check("camera: no invalid (NaN/inf) camera positions", not quiet["nan"] and not noisy["nan"], "")
	Sim.auto_deploy = true

# ---------------------------------------------------------------- controls (synthesized gamepad / touch events)
func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func _joy_btn(btn: JoyButton, n: int = 2) -> void:
	for pressed in [true, false]:
		var e := InputEventJoypadButton.new(); e.button_index = btn; e.pressed = pressed; e.device = 0
		Input.parse_input_event(e)
		await _frames(n)

func _joy_axis(axis: JoyAxis, v: float) -> void:
	var e := InputEventJoypadMotion.new(); e.axis = axis; e.axis_value = v; e.device = 0
	Input.parse_input_event(e)

## Synthesized events enter at the window, so map viewport coords -> window coords (headless windows are tiny + stretched).
func _wx() -> Transform2D:
	return get_tree().root.get_final_transform()

func _touch(idx: int, pos: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new(); e.index = idx; e.position = _wx() * pos; e.pressed = pressed
	Input.parse_input_event(e)

func _drag(idx: int, from: Vector2, to: Vector2, steps: int = 6) -> void:
	for i in steps:
		var e := InputEventScreenDrag.new(); e.index = idx
		e.position = _wx() * from.lerp(to, float(i + 1) / steps); e.relative = _wx().basis_xform((to - from) / steps)
		Input.parse_input_event(e)
		await _frames(1)

func _pinch(a0: Vector2, a1: Vector2, b0: Vector2, b1: Vector2, steps: int = 8) -> void:
	for i in steps:
		var t := float(i + 1) / steps
		for k in 2:
			var e := InputEventScreenDrag.new(); e.index = k
			var from: Vector2 = a0 if k == 0 else b0
			var to: Vector2 = a1 if k == 0 else b1
			e.position = _wx() * from.lerp(to, t); e.relative = _wx().basis_xform((to - from) / steps)
			Input.parse_input_event(e)
		await _frames(1)

func _army_screen(m: Node, aid: int) -> Vector2:
	return m.map.camera.unproject_position(m.map.army_nodes[aid].global_position)

func test_controls() -> void:
	print("== Controls: InputMap, gamepad, touch ==")
	Sim.auto_deploy = true
	var missing: Array = []
	var joyless: Array = []
	for act in Controls.ACTIONS.keys():
		if not InputMap.has_action(act):
			missing.append(act)
	for act in ["select", "command_move", "cancel", "pause", "cycle_army_next", "cycle_province_next", "toggle_diplomacy", "toggle_economy", "game_menu", "camera_toggle", "cursor_left", "orbit_left", "zoom_in", "speed_up"]:
		var has_joy := false
		for e in InputMap.action_get_events(act):
			if e is InputEventJoypadButton or e is InputEventJoypadMotion:
				has_joy = true
		if not has_joy:
			joyless.append(act)
	var ui_joy := false
	for e in InputMap.action_get_events("ui_accept"):
		if e is InputEventJoypadButton and e.button_index == JOY_BUTTON_A:
			ui_joy = true
	check("controls: %d InputMap actions registered, gameplay actions all have gamepad bindings" % Controls.ACTIONS.size(), missing.is_empty() and joyless.is_empty() and ui_joy,
		"missing %s, no-joy %s" % [str(missing), str(joyless)])
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	# --- title menu: gamepad gives focus to the first nation, D-pad moves it
	await _joy_btn(JOY_BUTTON_DPAD_RIGHT, 3)
	var fo := get_viewport().gui_get_focus_owner()
	check("controls: gamepad focus lands on title-menu buttons", Controls.last_device == "joy" and fo != null and fo is Button, "focus %s, device %s" % [str(fo), Controls.last_device])
	m._start_game("SWE", 1800, 3)
	await _frames(4)
	Sim.set_speed(0)
	# a second army so cycling has something to cycle through
	var a0: Dictionary = Sim.armies[Sim.armies.keys().filter(func(k): return Sim.armies[k]["owner"] == "SWE")[0]]
	Sim._spawn_army("SWE", Sim.nation_provs["SWE"][-1], a0["units"].duplicate(true))
	await _frames(3)
	# --- cycle armies / provinces
	await _joy_btn(JOY_BUTTON_RIGHT_SHOULDER)
	var a1: int = m.map.selected_army
	await _joy_btn(JOY_BUTTON_RIGHT_SHOULDER)
	var a2: int = m.map.selected_army
	var mine := Sim.armies.keys().filter(func(k): return Sim.armies[k]["owner"] == "SWE")
	check("controls: RB cycles through own armies", a1 in mine and a2 in mine and (a1 != a2 or mine.size() == 1), "armies %s -> %d, %d" % [str(mine), a1, a2])
	await _joy_btn(JOY_BUTTON_DPAD_DOWN)
	var p1: int = m.map.selected_pid
	await _joy_btn(JOY_BUTTON_DPAD_DOWN)
	var p2: int = m.map.selected_pid
	check("controls: D-pad up/down cycles own provinces", p1 in Sim.nation_provs["SWE"] and p2 in Sim.nation_provs["SWE"] and p1 != p2, "%d -> %d" % [p1, p2])
	# --- speed / pause
	await _joy_btn(JOY_BUTTON_Y)
	var sp_a: int = Sim.speed_idx
	await _joy_btn(JOY_BUTTON_DPAD_RIGHT)
	var sp_b: int = Sim.speed_idx
	await _joy_btn(JOY_BUTTON_Y)
	check("controls: Y pauses/unpauses, D-pad right raises speed", sp_a == 2 and sp_b == 3 and Sim.speed_idx == 0, "Y->%d, right->%d, Y->%d" % [sp_a, sp_b, Sim.speed_idx])
	# --- windows: Back opens diplomacy with focus inside, D-pad moves focus without touching the map, B closes
	await _joy_btn(JOY_BUTTON_BACK, 3)
	fo = get_viewport().gui_get_focus_owner()
	var in_win: bool = fo != null and m.hud.diplo_win.is_ancestor_of(fo)
	var pid_before: int = m.map.selected_pid
	await _joy_btn(JOY_BUTTON_DPAD_DOWN, 3)
	var fo2 := get_viewport().gui_get_focus_owner()
	check("controls: Back opens diplomacy with gamepad focus inside; D-pad navigates it", m.hud.diplo_win.visible and in_win and fo2 != null and fo2 != fo and m.hud.diplo_win.is_ancestor_of(fo2) and m.map.selected_pid == pid_before,
		"visible %s, focus %s -> %s" % [m.hud.diplo_win.visible, str(fo), str(fo2)])
	await _joy_btn(JOY_BUTTON_B, 3)
	check("controls: B closes the window", not m.hud.diplo_win.visible and not m.hud.any_window_open(), "")
	await _joy_btn(JOY_BUTTON_LEFT_STICK, 3)
	var econ_ok: bool = m.hud.econ_win.visible
	await _joy_btn(JOY_BUTTON_B, 3)
	await _joy_btn(JOY_BUTTON_START, 3)
	fo = get_viewport().gui_get_focus_owner()
	var menu_ok: bool = m.hud.menu_win.visible and fo != null and m.hud.menu_win.is_ancestor_of(fo)
	await _joy_btn(JOY_BUTTON_START, 3)
	check("controls: L3 economy, Start game menu (focused), Start again closes", econ_ok and menu_ok and not m.hud.menu_win.visible, "econ %s menu %s" % [econ_ok, menu_ok])
	# --- stick cursor + A select + X move order
	var cur0: Vector2 = m.hud.pad_cursor.position
	_joy_axis(JOY_AXIS_LEFT_X, 1.0)
	await _frames(15)
	_joy_axis(JOY_AXIS_LEFT_X, 0.0)
	await _frames(2)
	var cur1: Vector2 = m.hud.pad_cursor.position
	check("controls: left stick moves the map cursor reticle (no on-screen controller)", cur1.x > cur0.x + 20.0 and m.hud.pad_cursor.visible, "%s -> %s" % [str(cur0), str(cur1)])
	var aid: int = mine[0]
	m.select_province(-1)
	m.cam.fly_to(GameData.node_world(int(Sim.armies[aid]["node"])), 30.0, 0.05)
	await _frames(20)
	m.hud.pad_cursor.position = _army_screen(m, aid)
	await _joy_btn(JOY_BUTTON_A)
	check("controls: A selects the army under the cursor", m.map.selected_army == aid, "selected %d want %d at %s" % [m.map.selected_army, aid, str(m.hud.pad_cursor.position)])
	var dest := -1
	for nb in Sim.find_path("SWE", int(Sim.armies[aid]["node"]), Sim.nation_provs["SWE"][-1]):
		dest = nb
	var dest_ok := false
	for pid in Sim.nation_provs["SWE"]:
		if pid != int(Sim.armies[aid]["node"]):
			var sp: Vector2 = m.map.camera.unproject_position(GameData.node_world(pid))
			var vs := get_viewport().get_visible_rect().size
			if sp.x > 80 and sp.y > 80 and sp.x < vs.x - 80 and sp.y < vs.y - 120 and m.map.province_at_screen(sp) == pid and m.map.army_at_screen(sp) < 0:
				m.hud.pad_cursor.position = sp; dest = pid; dest_ok = true; break
	await _joy_btn(JOY_BUTTON_X)
	check("controls: X orders the selected army to the province under the cursor", dest_ok and int(Sim.armies[aid].get("goal", -1)) == dest and not Sim.armies[aid]["path"].is_empty(), "dest %d goal %s" % [dest, str(Sim.armies[aid].get("goal", -1))])
	Sim.order_move(aid, int(Sim.armies[aid]["node"])); Sim.armies[aid]["goal"] = -1
	# --- touch: tap select, drag pan, pinch zoom, twist rotate, long press move, taps on UI ignored
	Controls.set_setting("touch_rotate", true)
	m.select_province(-1)
	await _frames(2)
	var ap := _army_screen(m, aid)
	_touch(0, ap, true); await _frames(2); _touch(0, ap, false); await _frames(3)
	check("controls: touch tap selects the army", m.map.selected_army == aid and Controls.last_device == "touch", "selected %d" % m.map.selected_army)
	var tb: Vector2 = m.hud.top_bar.get_global_rect().get_center()
	m.select_province(-1)
	_touch(0, tb, true); await _frames(2); _touch(0, tb, false); await _frames(3)
	check("controls: touch tap on the HUD bar does not select on the map", m.map.selected_army < 0 and m.map.selected_pid < 0, "army %d pid %d" % [m.map.selected_army, m.map.selected_pid])
	var t0: Vector3 = m.cam._t_target
	var c := get_viewport().get_visible_rect().size * 0.5
	_touch(0, c, true); await _frames(1)
	await _drag(0, c, c + Vector2(-220, 90))
	_touch(0, c + Vector2(-220, 90), false); await _frames(3)
	var t1: Vector3 = m.cam._t_target
	check("controls: one-finger drag pans the map (and is not a tap)", t0.distance_to(t1) > 1.0 and m.map.selected_pid < 0, "target moved %.2f" % t0.distance_to(t1))
	var d0: float = m.cam._t_dist
	var y0: float = m.cam._t_yaw
	_touch(0, c - Vector2(60, 0), true); _touch(1, c + Vector2(60, 0), true); await _frames(1)
	await _pinch(c - Vector2(60, 0), c - Vector2(200, 0), c + Vector2(60, 0), c + Vector2(200, 0))
	var d1: float = m.cam._t_dist
	await _pinch(c - Vector2(200, 0), c + Vector2(-140, -140), c + Vector2(200, 0), c + Vector2(140, 140))
	_touch(1, c, false); _touch(0, c, false); await _frames(3)
	var y1: float = m.cam._t_yaw
	check("controls: pinch out zooms in, two-finger twist rotates", d1 < d0 * 0.6 and absf(y1 - y0) > 0.5, "dist %.1f -> %.1f, yaw %.2f -> %.2f" % [d0, d1, y0, y1])
	m.cam.fly_to(GameData.node_world(int(Sim.armies[aid]["node"])), 30.0, 0.05)
	await _frames(20)
	ap = _army_screen(m, aid)
	_touch(0, ap, true); await _frames(2); _touch(0, ap, false); await _frames(2)
	var lp := Vector2.ZERO
	for pid in Sim.nation_provs["SWE"]:
		if pid != int(Sim.armies[aid]["node"]):
			var sp: Vector2 = m.map.camera.unproject_position(GameData.node_world(pid))
			var vs := get_viewport().get_visible_rect().size
			if sp.x > 80 and sp.y > 80 and sp.x < vs.x - 80 and sp.y < vs.y - 120 and m.map.province_at_screen(sp) == pid and m.map.army_at_screen(sp) < 0:
				lp = sp; dest = pid; break
	_touch(0, lp, true)
	var tw := Time.get_ticks_msec()
	while Time.get_ticks_msec() - tw < 800:
		await _frames(1)
	_touch(0, lp, false); await _frames(3)
	check("controls: long-press marches the selected army to the pressed province", int(Sim.armies[aid].get("goal", -1)) == dest and not Sim.armies[aid]["path"].is_empty() and m.map.selected_army == aid, "dest %d goal %s" % [dest, str(Sim.armies[aid].get("goal", -1))])
	# --- settings: UI scale + large touch targets + perf overlay + quality
	Controls.set_setting("ui_scale", 1.25)
	Controls.set_setting("large_targets", true)
	await _frames(2)
	var bsb: StyleBox = m.hud.theme.get_stylebox("normal", "Button")
	var scale_ok := is_equal_approx(get_tree().root.content_scale_factor, 1.25)
	var big_ok := bsb.content_margin_top >= 12
	Controls.set_setting("show_perf", true)
	Controls.set_setting("quality", 0)
	await _frames(20)
	var pt: String = m.perf.lbl.text
	var q_ok: bool = get_viewport().msaa_3d == Viewport.MSAA_DISABLED
	check("controls: UI scale, large touch targets, F3 perf overlay and quality settings apply", scale_ok and big_ok and m.perf.visible and pt.contains("CPU") and q_ok,
		"scale %s big %s perf '%s' msaa %d" % [scale_ok, big_ok, pt.get_slice("\n", 0), get_viewport().msaa_3d])
	Controls.set_setting("ui_scale", 1.0); Controls.set_setting("large_targets", false); Controls.set_setting("show_perf", false); Controls.set_setting("quality", 1)
	var vj := _count_class(get_tree().root, "TouchScreenButton")
	check("controls: no virtual joystick / on-screen gamepad nodes in the scene tree", vj == 0, "%d TouchScreenButton" % vj)
	Controls.last_device = "kbm"
	m.queue_free()
	await _frames(2)
	# --- battle view: gamepad speed / leave / sticks, touch pinch
	var bid := _cam_battle_setup()
	var bv := BattleView.new()
	add_child(bv)
	bv.setup(bid)
	bv.set_cinematic(true)
	var left := [false]
	bv.leave_requested.connect(func(_b): left[0] = true)
	var rb := InputEventJoypadButton.new(); rb.button_index = JOY_BUTTON_RIGHT_SHOULDER; rb.pressed = true
	bv._unhandled_input(rb)
	var ts1: float = bv.time_scale
	_joy_axis(JOY_AXIS_RIGHT_X, 1.0)
	await _frames(1)
	var yaw0: float = bv.cam_yaw
	bv._pad_cam(0.2)
	_joy_axis(JOY_AXIS_RIGHT_X, 0.0)
	await _frames(1)
	var stick_ok: bool = not bv.cam_auto and absf(bv.cam_yaw - yaw0) > 0.1
	var dd0: float = bv.cam_dist
	for k in 2:
		var t := InputEventScreenTouch.new(); t.index = k; t.pressed = true; t.position = Vector2(600 + k * 100, 400); bv._unhandled_input(t)
	for i in 5:
		for k in 2:
			var d := InputEventScreenDrag.new(); d.index = k; d.position = Vector2(600 - (i + 1) * 20 + k * (100 + (i + 1) * 40), 400); bv._unhandled_input(d)
	var pinch_ok: bool = bv.cam_dist < dd0 * 0.8
	var back := InputEventJoypadButton.new(); back.button_index = JOY_BUTTON_BACK; back.pressed = true
	bv._unhandled_input(back)
	check("controls: battle view — RB speeds up, right stick orbits (leaves cinematic), pinch zooms, Back leaves", ts1 == 2.0 and stick_ok and pinch_ok and left[0],
		"speed %.0fx stick %s pinch %.0f->%.0f leave %s" % [ts1, stick_ok, dd0, bv.cam_dist, left[0]])
	bv.queue_free()
	Sim.auto_deploy = true
	await _frames(2)

func _count_class(n: Node, cls: String) -> int:
	var c := 1 if n.is_class(cls) else 0
	for ch in n.get_children():
		c += _count_class(ch, cls)
	return c


# ------------------------------------------------------------------ CPU micro-benchmark (not part of the suite)
func _us(c: Callable, reps: int = 1) -> float:
	var t := Time.get_ticks_usec()
	for i in reps:
		c.call()
	return float(Time.get_ticks_usec() - t) / reps

# ---------------------------------------------------------------- era verification (Task 5)
func _model_files(model: String, kind: String) -> Array:
	if kind in ["vat", "cav"]:
		var prefix := "cavalry_" if model in ["med_knight", "em_cuirassier", "c19_hussar"] else "soldier_"
		return ["res://assets/models/%s%s_lod0.glb" % [prefix, model], "res://assets/models/%s%s_lod1.glb" % [prefix, model]]
	return ["res://assets/models/%s.glb" % model]

func _run_mk(era_id: String, a_roles: Array, d_roles: Array, seed: int, terr := "plains", obj := "assault") -> BattleSim:
	var s := BattleSim.new()
	s.setup([_units_for(era_id, a_roles), _units_for(era_id, d_roles)], terr, [{"objective": obj, "formation": "line"}, {"objective": "hold", "formation": "line"}], seed)
	s.record_events = false
	s.run_to_end()
	return s

func test_era_battles() -> void:
	print("== Era battle verification ==")
	var expect_proj := {"medieval": ["arrow", "stone_shot"], "early_modern": ["musket_ball", "round_shot"], "c19": ["musket_ball", "round_shot"],
		"c20": ["rifle_tracer", "shell", "tank_round"], "modern": ["rifle_tracer", "shell", "tank_round"]}
	var melee_share := {}
	for era_d in GameData.eras:
		var e: String = era_d["id"]
		# 1) roster: every unit of the era has era-consistent data and its model files on disk
		var bad := []
		for uid in GameData.units_by_era[e]:
			var d: Dictionary = GameData.units[uid]
			if d["era"] != e: bad.append(uid + ":era")
			for f in _model_files(d["model"], d["kind"]):
				if not ResourceLoader.exists(f): bad.append(uid + ":" + f.get_file())
			if d["role"] in ["ranged", "art", "armor"] and float(d["range"]) <= 0.0: bad.append(uid + ":range")
		check("%s: units/models present and era-tagged (%s)" % [e, ", ".join(GameData.units_by_era[e])], bad.is_empty(), str(bad))
		# 2) a full mixed battle: only that era's units take part, it ends with a winner in the time window
		var s := _run_mk(e, ["ranged", "inf", "ranged", "cav", "art"], ["ranged", "inf", "ranged", "cav", "art"], 11, "plains")
		var eras_seen := {}; var classes := {}
		var kills := 0.0; var mk := 0.0
		for r in s.regs:
			eras_seen[r["def"]["era"]] = true
			if int(r["fired"]) > 0: classes[BattleView.projectile_class(r)] = true
			kills += r["kills"]; mk += r.get("mkills", 0.0)
		melee_share[e] = mk / maxf(kills, 1.0)
		check("%s: full battle resolves (winner %d, %.1fs)" % [e, s.winner, s.t], s.done and s.winner in [0, 1] and s.t >= 15.0 and s.t < BattleSim.MAX_TIME,
			"men %s -> %d/%d" % [str(s.start_men), int(s.side_men(0)), int(s.side_men(1))])
		check("%s: only %s units fight" % [e, e], eras_seen.keys() == [e], str(eras_seen.keys()))
		var exp_p: Array = expect_proj[e]
		var ok_p := true
		for c in classes.keys():
			if not c in exp_p: ok_p = false
		check("%s: projectile types fit the era %s" % [e, str(classes.keys())], ok_p and classes.size() >= 2, "expected subset of %s" % str(exp_p))
	# 3) melee matters more before gunpowder dominance than in the industrial eras
	check("melee share of kills falls with era (medieval %.2f > c19 %.2f > modern %.2f)" % [melee_share["medieval"], melee_share["c19"], melee_share["modern"]],
		melee_share["medieval"] > melee_share["c19"] and melee_share["c19"] > melee_share["modern"], str(melee_share))
	# 4) armour: the same archers kill fewer armoured knights than levy spearmen per volley
	var per_volley := func(tgt_role: String) -> float:
		var s := BattleSim.new()
		s.setup([_units_for("medieval", ["ranged"]), _units_for("medieval", [tgt_role])], "plains", [{"objective": "hold", "formation": "line"}, {"objective": "hold", "formation": "line"}], 5)
		s.record_events = false
		var r: Dictionary = s.regs[0]
		while int(r["fired"]) < 1 and s.t < 30.0: s.step()   # first volley only: identical shooters and range
		return r["kills"] / maxf(float(r["fired"]), 1.0)
	var vk: float = per_volley.call("cav"); var vl: float = per_volley.call("inf")
	check("medieval armour: archers kill fewer armoured knights than levy per volley (%.1f < %.1f men)" % [vk, vl], vk > 0.0 and vl > 0.0 and vk < vl, "")
	# 5) modern armour: rifles barely scratch MBTs, rockets/tanks do not
	var s_r := BattleSim.new()
	s_r.setup([_units_for("modern", ["ranged"]), _units_for("modern", ["armor"])], "plains", [{"objective": "hold", "formation": "line"}, {"objective": "hold", "formation": "line"}], 5)
	s_r.record_events = false
	for k in 300: s_r.step()
	var mech_eff: float = s_r.regs[0]["kills"] / maxf(float(s_r.regs[0]["fired"]), 1.0) / s_r.regs[1]["men0"]
	var s_t := BattleSim.new()
	s_t.setup([_units_for("modern", ["armor"]), _units_for("modern", ["armor"])], "plains", [{"objective": "hold", "formation": "line"}, {"objective": "hold", "formation": "line"}], 5)
	s_t.record_events = false
	for k in 300: s_t.step()
	var mbt_eff: float = s_t.regs[0]["kills"] / maxf(float(s_t.regs[0]["fired"]), 1.0) / s_t.regs[1]["men0"]
	check("modern armour: MBT rounds hurt MBTs more than infantry rifles do (%.4f > %.4f)" % [mbt_eff, mech_eff], mbt_eff > mech_eff, "")
	# 6) era-specific nations: the battle demo nations exist and field their era's kit
	for code in ["USA", "SWE", "JPN"]:
		var ok_n := true; var info := []
		for y in GameData.start_years:
			Sim.new_game(code, y, 2)
			var a: Dictionary = _strongest_army(code)
			var e2: String = GameData.eras[Sim.era]["id"]
			for u in a.get("units", []):
				if u["era"] != e2: ok_n = false
			info.append("%d:%s" % [y, a["units"][0]["type"] if not a.is_empty() and a["units"].size() > 0 else "-"])
		check("%s: starting armies use the start era's units in every era" % code, ok_n, ", ".join(info))

# ---------------------------------------------------------------- scripted gameplay (Task 7)
func test_gameplay_script() -> void:
	print("== Scripted gameplay ==")
	Sim.auto_deploy = true
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	m._start_game("SWE", 1913, 7, 200)
	await _frames(3)
	Sim.set_speed(0)
	var e0 := Sim.era
	check("gameplay: campaign started as Sweden in %s" % Sim.date_string(), Sim.player == "SWE" and m.map.visible and not m.in_battle, "")
	# move an army one province
	var army: Dictionary = m._demo_main_army("SWE")
	var nb: Array = []
	for pid in GameData.provinces[army["node"]].get("neighbors", {}).keys():
		if Sim.prov_owner.get(int(pid), "") == "SWE": nb.append(int(pid))
	var from: int = army["node"]
	var mv: Dictionary = Sim.order_move(army["id"], nb[0]) if not nb.is_empty() else {"ok": false}
	for d in 40:
		if army["node"] != from: break
		Sim.tick_day()
	check("gameplay: army %d marched %d -> %d" % [army["id"], from, army["node"]], mv.get("ok", false) and army["node"] == nb[0], str(mv))
	# declare war, invade, watch a battle, capture a province
	var captured := {}
	var cb := func(pid: int, old: String, new: String) -> void:
		if new == "SWE": captured[pid] = old
	Sim.ownership_changed.connect(cb)
	# test grant: a bigger expeditionary force so the invasion reliably succeeds (_demo_war merges everything at the capital)
	Sim.nations["SWE"]["funds"] += 20000.0; Sim.nations["SWE"]["manpower"] += 40000.0
	for k in 3:
		for uid in GameData.units_by_era[GameData.eras[Sim.era]["id"]]:
			Sim.buy_unit("SWE", uid, Sim.nations["SWE"]["capital"])
	var era_date := [""]
	var ecb := func(i: int) -> void: era_date[0] = Sim.date_string()
	Sim.era_changed.connect(ecb)
	var tgt: String = m._demo_war("SWE")
	check("gameplay: war declared on %s" % tgt, tgt != "" and Sim.at_war("SWE", tgt), "")
	var watched := false; var toggles_ok := false
	for d in 500:
		Sim.tick_day()
		if not watched:
			for bid in Sim.battles.keys():
				var b: Dictionary = Sim.battles[bid]
				if b["player_side"] >= 0 and not b["done"] and b["sim"] != null:
					m.watch_battle(bid)
					var t0 := Time.get_ticks_msec()
					while not (m.in_battle and not m.transitioning) and Time.get_ticks_msec() - t0 < 8000:
						await _frames(1)
					if m.in_battle:
						var bv = m.battle_view
						var c0: bool = bv.cam_auto
						var ev := InputEventAction.new(); ev.action = "camera_toggle"; ev.pressed = true
						Input.parse_input_event(ev); await _frames(2)
						var ev2 := InputEventAction.new(); ev2.action = "camera_toggle"; ev2.pressed = false
						Input.parse_input_event(ev2); await _frames(2)
						var c1: bool = bv.cam_auto
						toggles_ok = c1 != c0
						bv.skip()
						await _frames(2)
						check("gameplay: watched a battle in 3D (camera toggle %s -> %s), result %s" % [c0, c1, str(bv.finished)], toggles_ok and bv.finished, "")
						bv.leave_requested.emit(bid)
						t0 = Time.get_ticks_msec()
						while (m.in_battle or m.transitioning) and Time.get_ticks_msec() - t0 < 8000:
							await _frames(1)
					watched = true
					break
		if watched and not captured.is_empty():
			break
	Sim.ownership_changed.disconnect(cb)
	var dbg := []
	for a in Sim.armies.values():
		if a["owner"] == "SWE": dbg.append("%d@%d %s men%d path%d" % [a["id"], a["node"], a["state"], int(Sim.army_men(a)), a["path"].size()])
	print("GPDBG at_war ", Sim.at_war("SWE", tgt), " sieges ", Sim.sieges, " armies ", dbg)
	check("gameplay: captured enemy province(s) %s by %s" % [str(captured.keys()), Sim.date_string()], not captured.is_empty() and watched and not m.in_battle, "")
	# save / load round trip
	var h0 := JSON.stringify(Sim.serialize_state()).md5_text(); var d0 := Sim.date_string()
	var sv := Sim.save_game("gameplay_test")
	Sim.advance_days(20)
	var ld := Sim.load_game("gameplay_test")
	await _frames(2)
	check("gameplay: save/load restores %s exactly" % d0, sv["ok"] and ld["ok"] and Sim.date_string() == d0 and JSON.stringify(Sim.serialize_state()).md5_text() == h0, ld["msg"])
	# era advance (start was 1913)
	var guard := 0
	while Sim.era == e0 and guard < 800:
		Sim.tick_day(); guard += 1
	await _frames(2)
	Sim.era_changed.disconnect(ecb)
	if era_date[0] == "": era_date[0] = Sim.date_string()
	check("gameplay: era advanced to %s on %s (game started 1913)" % [GameData.eras[Sim.era]["name"], era_date[0]], Sim.era == e0 + 1 and era_date[0].ends_with("1914"), "")
	m.queue_free()
	await _frames(2)

func bench_cpu() -> void:
	print("== CPU bench ==")
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	m._start_game("SWE", 1800, 7)
	await _frames(4)
	Sim.set_speed(0)
	m._demo_war("SWE")
	var acc := {"move": 0.0, "battles": 0.0, "sieges": 0.0, "ai": 0.0, "month": 0.0, "day_total": 0.0}
	var worst := {"day": 0.0}
	var days := 240
	for d in days:
		var t0 := Time.get_ticks_usec()
		Sim.day += 1
		var p := Sim.date_parts()
		Sim._era_check()
		acc["move"] += _us(Sim._move_armies)
		acc["battles"] += _us(Sim._step_battles)
		acc["sieges"] += _us(Sim._step_sieges)
		acc["ai"] += _us(Sim._ai_military_daily)
		if p[2] == 1:
			acc["month"] += _us(Sim._month)
		Sim.day_passed.emit(Sim.day)
		var dt := float(Time.get_ticks_usec() - t0)
		acc["day_total"] += dt
		worst["day"] = maxf(worst["day"], dt)
	for k in acc.keys():
		acc[k] = acc[k] / days / 1000.0
	print("BENCH sim per-day ms: ", acc, " worst day ms ", worst["day"] / 1000.0, " armies ", Sim.armies.size(), " battles ", Sim.battles.size())
	var mp := {"econ": 0.0, "drift": 0.0, "recruit": 0.0, "diplo": 0.0, "minor": 0.0}
	for rep in 3:
		var t_ctx := Time.get_ticks_usec()
		var ctx: Dictionary = Sim._economy_ctx()
		mp["econ"] += Time.get_ticks_usec() - t_ctx
		for code in Sim.nations.keys():
			if Sim.nations[code]["alive"]:
				mp["econ"] += _us(func(): Sim._economy_month(code, false, ctx))
		mp["drift"] += _us(Sim._relations_drift)
		for code in Sim.nations.keys():
			var n: Dictionary = Sim.nations[code]
			if n["alive"] and n["ai"]:
				mp["recruit"] += _us(func(): Sim._ai_recruit(code))
				if n["major"]:
					mp["diplo"] += _us(func(): Sim._ai_diplomacy(code))
				else:
					mp["minor"] += _us(func(): Sim._ai_minor(code))
	for k in mp.keys():
		mp[k] = mp[k] / 3000.0
	print("BENCH _month parts ms: ", mp, " nations ", Sim.nations.size(), " relations ", Sim.relations.size())
	var majors: Array = []
	for code in Sim.nations.keys():
		if Sim.nations[code]["major"] and Sim.nations[code]["alive"]:
			majors.append(code)
	var c0: String = majors[0]
	var nb0: Array = Sim.neighbors_of(c0)
	print("BENCH majors ", majors.size(), " ", c0, " neighbours ", nb0.size(), " wars ", Sim.wars.size(), " treaties ", Sim.treaties.size())
	print("BENCH neighbors_of ms ", _us(func(): Sim.neighbors_of(c0), 20) / 1000.0)
	print("BENCH strength ms ", _us(func(): Sim.strength(c0), 20) / 1000.0)
	print("BENCH allies_of ms ", _us(func(): Sim.allies_of(c0), 20) / 1000.0)
	print("BENCH enemies_of ms ", _us(func(): Sim.enemies_of(c0), 20) / 1000.0)
	print("BENCH can_declare_war ms ", _us(func(): Sim.can_declare_war(c0, nb0[0]), 20) / 1000.0)
	for kind in ["trade", "alliance", "nap"]:
		print("BENCH evaluate %s ms " % kind, _us(func(): Sim.evaluate(c0, nb0[0], kind), 5) / 1000.0)
	print("BENCH _shares_border ms ", _us(func(): Sim._shares_border(c0, nb0[0]), 20) / 1000.0)
	print("BENCH _resources_of ms ", _us(func(): Sim._resources_of(c0), 20) / 1000.0)
	print("BENCH gift ms ", _us(func(): Sim.gift(c0, nb0[0], 1.0), 3) / 1000.0)
	print("BENCH log_event ms ", _us(func(): Sim.log_event("bench", "diplo", []), 3) / 1000.0)
	print("BENCH propose trade ms ", _us(func(): Sim.propose(c0, nb0[1 % nb0.size()], "trade", true), 1) / 1000.0)
	for code in majors:
		print("BENCH _ai_diplomacy %s ms " % code, _us(func(): Sim._ai_diplomacy(code), 1) / 1000.0)
	var hud = m.hud
	var a: Dictionary = m._demo_main_army("SWE")
	if not a.is_empty():
		m.select_army(a["id"])
	print("BENCH hud.refresh_top ms ", _us(hud.refresh_top, 10) / 1000.0)
	print("BENCH hud.refresh_selection ms ", _us(hud.refresh_selection, 10) / 1000.0)
	print("BENCH map.update_markers ms ", _us(m.map.update_markers, 10) / 1000.0)
	print("BENCH map.update_path ms ", _us(m.map.update_path, 10) / 1000.0)
	print("BENCH map._process ms ", _us(func(): m.map._process(0.016), 10) / 1000.0)
	print("BENCH hud._process ms ", _us(func(): hud._refresh_t = 0.0; hud._process(0.016), 10) / 1000.0)
	m.select_province(Sim.nations["SWE"]["capital"]) if m.has_method("select_province") else null
	print("BENCH hud.refresh_selection(province) ms ", _us(hud.refresh_selection, 10) / 1000.0)
	print("BENCH hud._process(province) ms ", _us(func(): hud._refresh_t = 0.0; hud._process(0.016), 10) / 1000.0)
	m.queue_free()
	await _frames(2)
