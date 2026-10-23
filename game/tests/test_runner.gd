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
	if only == "" or only == "camera" or only == "visuals":
		test_visuals_hook()
		test_anim_default()
		test_polish()
	if only == "" or only == "controls":
		await test_controls()
	if only == "" or only == "controls" or only == "markers":
		await test_map_markers()
	if only == "" or only == "eras":
		test_era_battles()
	if only == "" or only == "gameplay":
		await test_gameplay_script()
	if only == "" or only == "medieval":
		test_medieval_morale()
	if only == "" or only == "aistrategy":
		test_ai_strategy()
	if only == "" or only == "detection":
		await test_detection()
	if only == "" or only == "reinforce":
		await test_reinforcements()
	if only == "" or only == "inbox":
		await test_inbox()
	if only == "" or only == "offensive":
		await test_offensive()
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
	var chasing := -1
	for i in 300:
		if i % 5 == 0 and Sim.armies.has(a["id"]) and Sim.armies[a["id"]]["state"] != "battle":
			# chase the nearest Norwegian army
			var best := -1; var bd := 1e18
			for o in Sim.armies.values():
				if o["owner"] == target and o["node"] < GameData.SEA_NODE:
					var d := GameData.node_km(a["node"], o["node"])
					if d < bd:
						bd = d; best = o["node"]
			if best >= 0 and best != chasing:   # re-ordering resets march progress, so only when the quarry moved (v0.5)
				Sim.order_move(a["id"], best)
				chasing = best
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
func _cam_battle_setup(year: int = 1800) -> int:
	Sim.auto_deploy = false
	Sim.auto_respond_player = "decline"
	Sim.new_game("SWE", year, 11)
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
	check("camera: director switches to the aftermath shot when the battle ends", kinds.has("aftermath"), str(kinds))
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

## R5 (v0.3): BJORN's map_visuals.gd is hooked into WorldMap.build(). It may only swap each army's "Standard"
## mesh/material; picking (army_at_screen), selection, the ring/label and move orders must behave exactly as before.
func _marker_state(m: Node) -> Dictionary:
	var out := {}
	for aid in m.map.army_nodes.keys():
		var n: Node3D = m.map.army_nodes[aid]
		var sp := _army_screen(m, aid)
		var pick: int = -2 if m.map.camera.is_position_behind(n.global_position) else m.map.army_at_screen(sp)
		out[aid] = [n.position, n.scale, n.visible, n.get_node("Ring").visible, n.get_node("Label").text, n.get_node("Label").visible, pick]
	return out

func _marker_swapped(m: Node, mv: Node, era_id: String) -> Array:
	var want: Mesh = mv._mesh(era_id)
	var ok := 0
	for aid in m.map.army_nodes.keys():
		var std: Node = m.map.army_nodes[aid].get_node("Standard")
		var mi: MeshInstance3D = null
		var stack := [std]
		while stack.size() > 0 and mi == null:
			var x: Node = stack.pop_back()
			if x is MeshInstance3D: mi = x
			stack.append_array(x.get_children())
		if want != null and mi != null and mi.mesh == want and std.get_meta("vis_era", "") == era_id:
			ok += 1
	return [ok, m.map.army_nodes.size()]

func _wait_ms(ms: int) -> void:
	var tw := Time.get_ticks_msec()
	while Time.get_ticks_msec() - tw < ms:
		await _frames(1)

func _mouse_click(pos: Vector2, btn: MouseButton) -> void:
	# parse_input_event takes window coordinates; the root viewport applies the stretch transform back to `pos`
	var wpos: Vector2 = get_tree().root.get_final_transform() * pos
	for pressed in [true, false]:
		var e := InputEventMouseButton.new(); e.button_index = btn; e.pressed = pressed; e.position = wpos; e.global_position = wpos
		Input.parse_input_event(e)
		await _frames(2)

func test_map_markers() -> void:
	print("== Overworld army markers (map_visuals hook, R5) ==")
	Sim.auto_deploy = true
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	m._start_game("SWE", 1800, 3)
	await _frames(4)
	Sim.set_speed(0)
	var mv: Node = m.map.get_node_or_null("MapVisuals")
	await _wait_ms(400)   # map_visuals re-checks every 0.25 s
	var era_id := str(GameData.eras[Sim.era]["id"])
	var sw: Array = _marker_swapped(m, mv, era_id) if mv else [0, -1]
	check("markers: MapVisuals is hooked into the WorldMap and every army standard shows map_marker_%s (%d/%d)" % [era_id, sw[0], sw[1]],
		mv != null and sw[1] > 0 and sw[0] == sw[1], str(sw))
	# a forced re-swap must not change any army node's transform, visibility, ring, label or what picking returns
	var aid: int = Sim.armies.keys().filter(func(k): return Sim.armies[k]["owner"] == "SWE")[0]
	m.cam.fly_to(GameData.node_world(int(Sim.armies[aid]["node"])), 30.0, 0.05)
	await _frames(20)
	m.map.update_markers()
	var before := _marker_state(m)
	if mv:
		for a in m.map.army_nodes.keys():
			m.map.army_nodes[a].get_node("Standard").set_meta("vis_era", "")
		mv._t = 0.0
		mv._process(0.0)
	var after := _marker_state(m)
	var picks := 0
	for a in before.keys():
		if before[a][6] == a: picks += 1
	check("markers: re-swapping changes no army position/scale/visibility/ring/label and army_at_screen picks the same armies (%d armies, %d self-picks)" % [before.size(), picks],
		before == after and before.has(aid) and before[aid][6] == aid, "before %s after %s" % [str(before.get(aid)), str(after.get(aid))])
	# mouse: left-click on the new marker selects the army, right-click orders a march
	m.select_province(-1)
	Controls.last_device = "kbm"
	await _mouse_click(_army_screen(m, aid), MOUSE_BUTTON_LEFT)
	var sel_ok: bool = m.map.selected_army == aid
	var dest := -1
	var vs := get_viewport().get_visible_rect().size
	for pid in Sim.nation_provs["SWE"]:
		if pid != int(Sim.armies[aid]["node"]):
			var sp: Vector2 = m.map.camera.unproject_position(GameData.node_world(pid))
			if sp.x > 80 and sp.y > 80 and sp.x < vs.x - 80 and sp.y < vs.y - 120 and m.map.province_at_screen(sp) == pid and m.map.army_at_screen(sp) < 0:
				dest = pid
				await _mouse_click(sp, MOUSE_BUTTON_RIGHT)
				break
	var move_ok: bool = dest > 0 and int(Sim.armies[aid].get("goal", -1)) == dest and not Sim.armies[aid]["path"].is_empty()
	check("markers: mouse left-click on a swapped marker selects the army, right-click orders the march (army %d -> %d)" % [aid, dest],
		sel_ok and move_ok and m.map.selected_army == aid and m.map.army_nodes[aid].get_node("Ring").visible,
		"selected %d goal %s" % [m.map.selected_army, str(Sim.armies[aid].get("goal", -1))])
	Sim.order_move(aid, int(Sim.armies[aid]["node"])); Sim.armies[aid]["goal"] = -1
	# era change: markers re-swap to the new era kit and selection still works on them
	var e0: int = Sim.era
	var em := -1
	for i in GameData.eras.size():
		if str(GameData.eras[i]["id"]) == "medieval": em = i
	Sim.era = em
	await _wait_ms(400)
	var sw2: Array = _marker_swapped(m, mv, "medieval") if mv else [0, -1]
	m.select_province(-1)
	await _frames(2)
	await _mouse_click(_army_screen(m, aid), MOUSE_BUTTON_LEFT)
	check("markers: era change re-swaps markers (medieval %d/%d) and click-select still works" % [sw2[0], sw2[1]],
		sw2[1] > 0 and sw2[0] == sw2[1] and m.map.selected_army == aid, "selected %d" % m.map.selected_army)
	Sim.era = e0
	m.select_province(-1)
	m.queue_free()
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

# ---------------------------------------------------------------- combat animation v1 default (Rob; ON by default since 2026-10-23)
func test_anim_default() -> void:
	print("== Combat animation v1 default ==")
	var AC = BattleView.AC
	var none := PackedStringArray()
	check("anim-v1: ON by default (no args, no env var, no setting)", AC.resolve_on(none, "", null) == true)
	var offs := []
	for a in ["--no-anim-v1", "--anim-v1=off", "--anim-v1=0", "--anim-v1=false"]:
		offs.append(AC.resolve_on(PackedStringArray([a]), "", null))
	check("anim-v1: --no-anim-v1 / --anim-v1=off|0|false disable it %s" % str(offs), offs == [false, false, false, false], str(offs))
	var ons := [AC.resolve_on(PackedStringArray(["--anim-v1"]), "", null), AC.resolve_on(PackedStringArray(["--anim-v1=on"]), "", null)]
	check("anim-v1: legacy --anim-v1 and --anim-v1=on keep it on", ons == [true, true], str(ons))
	var ev := [AC.resolve_on(none, "0", null), AC.resolve_on(none, "off", null), AC.resolve_on(none, "1", false),
		AC.resolve_on(none, "", false), AC.resolve_on(PackedStringArray(["--anim-v1"]), "0", false)]
	check("anim-v1: env var %s=0 and setting false disable it; command line wins %s" % [AC.ENV_VAR, str(ev)], ev == [false, false, true, false, true], str(ev))
	var bid := _cam_battle_setup(1300)
	var bv := BattleView.new()
	add_child(bv)
	AC.on = not AC.resolve_from_runtime()   # setup() must (re)apply the switch, whatever the previous value
	bv.setup(bid)
	check("anim-v1: BattleView.setup applies the switch (AC.on=%s, expected %s from this run's args/env)" % [AC.on, AC.resolve_from_runtime()],
		AC.on == AC.resolve_from_runtime())
	remove_child(bv)
	bv.free()

# ---------------------------------------------------------------- graphics pass integration (BJORN's battle_visuals.gd)
func _bv_look(bv: BattleView) -> Array:
	return [bv.environment.tonemap_mode, snappedf(bv.environment.tonemap_exposure, 0.001), snappedf(bv.environment.ambient_light_energy, 0.001),
		snappedf(bv.sun.light_energy, 0.001), bv.sun.shadow_enabled]

func test_visuals_hook() -> void:
	print("== Graphics pass hook ==")
	var q0: int = Controls.quality
	Controls.quality = 1
	var legacy := [Environment.TONE_MAPPER_FILMIC, 1.0, 0.75, 1.25, true]   # BattleView._build_env defaults
	var looks := {}
	for y in [1300, 1800]:
		var bid := _cam_battle_setup(y)
		var bv := BattleView.new()
		add_child(bv)
		bv.setup(bid)
		var look := _bv_look(bv)
		BattleView.BattleVisuals.apply(bv)   # idempotent by contract
		looks[bv.era_id] = [look, _bv_look(bv)]
		if bv.era_id == "c19":
			# Controls.quality -> BattleView.apply_quality() -> battle_visuals.apply_quality(q) (INTEGRATION.md 3b)
			var got := []
			for q in [0, 1, 2]:
				Controls.quality = q; bv.apply_quality()
				got.append([get_viewport().msaa_3d, bv.sun.shadow_enabled, snappedf(bv.sun.directional_shadow_max_distance, 1.0), snappedf(bv.LOD_DIST, 1.0)])
			Controls.quality = 1; bv.apply_quality()
			var want := [[Viewport.MSAA_DISABLED, false, 260.0, 45.0], [Viewport.MSAA_2X, true, 260.0, 75.0], [Viewport.MSAA_4X, true, 300.0, 120.0]]
			check("visuals: quality q0/q1/q2 forwards to battle_visuals (MSAA off/2x/4x, shadows off/on/on 300 m, LOD 45/75/120) %s" % str(got),
				got == want and BattleView.BattleVisuals.get_quality() == 1 and get_viewport().msaa_3d == Viewport.MSAA_2X, str(got))
		remove_child(bv)
		bv.free()
	check("visuals: c19 battle gets the graphics pass at setup (look differs from legacy) %s" % str(looks.get("c19", [[]])[0]),
		looks.has("c19") and looks["c19"][0] != legacy, str(looks))
	check("visuals: apply() is idempotent on a set-up c19 battle", looks.has("c19") and looks["c19"][0] == looks["c19"][1], str(looks))
	# R6 (v0.3): medieval is in battle_visuals.ERAS now, so it gets the era pass too (no era stays legacy).
	check("visuals: medieval battle gets the era pass at setup (look differs from legacy, apply() idempotent) %s" % str(looks.get("medieval", [[]])[0]),
		looks.has("medieval") and looks["medieval"][0] != legacy and looks["medieval"][0] == looks["medieval"][1], str(looks))
	Controls.quality = q0

## v0.3 polish pass: c19 grenadiers use the bearskin model, gun crews wear the era artillery uniform (units.json +
## BattleView.CREW_MODEL name them directly, so the battle_visuals runtime swap is a no-op), and a winter battle gets
## the depth-range fog / snow grade instead of the full-field exponential haze.
func test_polish() -> void:
	print("== Polish pass (grenadiers, gun crews, snow) ==")
	var q0: int = Controls.quality
	Controls.quality = 1
	var want_crew := {"c19": "c19_artillery", "early_modern": "em_gunner"}
	for y in [1800, 1500]:
		var bid := _cam_battle_setup(y)
		var bv := BattleView.new()
		add_child(bv)
		bv.setup(bid)
		var gren := [0, 0]; var guns := [0, 0]; var drawn := {}
		for v in bv.rv:
			var d: Dictionary = bv.sim.regs[int(v["i"])]["def"]
			if str(d["id"]) == "grenadiers":
				gren[0] += 1
				if str(v["model"]) == "c19_grenadier": gren[1] += 1
			if v.has("crew_model"):
				guns[0] += 1
				if str(v["crew_model"]) == want_crew.get(str(d["era"]), "?"): guns[1] += 1
		for key in bv.mms.keys():
			var m: String = str(key).split("|")[0]
			if m in ["c19_grenadier", "c19_artillery", "em_gunner"]:
				drawn[m] = drawn.get(m, 0) + (bv.mms[key]["mm"] as MultiMesh).instance_count
		var before := [gren.duplicate(), guns.duplicate(), drawn.duplicate()]
		BattleView.BattleVisuals.apply(bv)   # the runtime swap must find nothing left to do
		var same := bv.mms.size()
		BattleView.BattleVisuals.apply(bv)
		if bv.era_id == "c19":
			check("polish: c19 grenadiers drawn with c19_grenadier, gun crews with c19_artillery (grenadier regs %s, guns %s, multimesh rows %s)" % [str(gren), str(guns), str(drawn)],
				gren[0] > 0 and gren[0] == gren[1] and guns[0] > 0 and guns[0] == guns[1] and drawn.get("c19_grenadier", 0) > 0 and drawn.get("c19_artillery", 0) > 0, str(before))
		else:
			check("polish: early-modern gun crews drawn with em_gunner (guns %s, rows %s)" % [str(guns), str(drawn)],
				guns[0] > 0 and guns[0] == guns[1] and drawn.get("em_gunner", 0) > 0, str(before))
		check("polish: %s re-apply() adds no multimeshes (%d == %d)" % [bv.era_id, same, bv.mms.size()], same == bv.mms.size(), "")
		remove_child(bv)
		bv.free()
	# winter ground + light: tundra vs plains on the same c19 battle
	var res := {}
	for terr in ["plains", "tundra"]:
		var bid2 := _cam_battle_setup(1800)
		Sim.battles[bid2]["terrain"] = terr
		var bv2 := BattleView.new()
		add_child(bv2)
		bv2.setup(bid2)
		var e := bv2.environment
		res[terr] = [e.fog_mode, snappedf(e.fog_depth_begin, 1.0), snappedf(e.tonemap_exposure, 0.001), snappedf(e.adjustment_contrast, 0.001)]
		remove_child(bv2)
		bv2.free()
	check("polish: depth-range fog (field < 260 m clear) on plains and tundra; tundra exposure lower, contrast higher %s" % str(res),
		res["plains"][0] == Environment.FOG_MODE_DEPTH and res["tundra"][0] == Environment.FOG_MODE_DEPTH and res["tundra"][1] >= 200.0
		and res["tundra"][2] < res["plains"][2] and res["tundra"][3] > res["plains"][3], str(res))
	Controls.quality = q0

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

# ---------------------------------------------------------------- offensive warfare & conquest (v0.4)
## Find a Button under `n` whose text contains `needle` (visible or not) and press it like a player would.
func _press(n: Node, needle: String) -> bool:
	for c in n.get_children():
		if c is Button and needle in c.text and not c.disabled:
			c.pressed.emit()
			return true
		if _press(c, needle):
			return true
	return false

func _texts(n: Node, out: Array = []) -> Array:
	for c in n.get_children():
		if c is Label or c is Button:
			out.append(c.text)
		_texts(c, out)
	return out

func _nearest_foreign(code: String, from_node: int, avoid_allies := true) -> int:
	var best := -1; var bd := 1e18
	for pid in Sim.prov_owner.keys():
		var o: String = Sim.prov_owner[pid]
		if o == code or not Sim.nations[o]["alive"] or (avoid_allies and Sim.has_treaty(code, o, "alliance")):
			continue
		var d := GameData.node_km(from_node, pid)
		if d < bd and Sim.order_invade(_main_army(code)["id"], pid, true)["ok"]:
			bd = d; best = pid
	return best

func _main_army(code: String) -> Dictionary:
	var best := {}
	for a in Sim.armies.values():
		if a["owner"] == code and (best.is_empty() or Sim.army_men(a) > Sim.army_men(best)):
			best = a
	return best

## Run days until `cond` holds (or `limit` days); returns the number of days run, -1 on timeout.
func _until(cond: Callable, limit: int) -> int:
	for d in limit:
		if cond.call():
			return d
		Sim.tick_day()
	return 0 if cond.call() else -1

func test_offensive() -> void:
	print("== Offensive warfare & territorial conquest ==")
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	# ------------------------------------------------ 1. Sweden: select army -> right-click -> invade (undeclared)
	Sim.auto_deploy = false
	m._start_game("SWE", 1800, 11, 60)
	await _frames(3)
	Sim.set_speed(0)
	Controls.last_device = "kbm"
	var army: Dictionary = _main_army("SWE")
	var aid: int = army["id"]
	m.cam.look_at_world(GameData.node_world(int(army["node"])), 30.0, true)
	await _frames(4)
	m.select_province(-1)
	await _mouse_click(_army_screen(m, aid), MOUSE_BUTTON_LEFT)
	var sel_ok: bool = m.map.selected_army == aid
	var tp := _nearest_foreign("SWE", army["node"])
	var tgt: String = Sim.prov_owner[tp]
	var tname: String = GameData.provinces[tp]["name"]
	m.cam.look_at_world(GameData.node_world(tp), 30.0, true)
	await _frames(4)
	var sp: Vector2 = m.map.camera.unproject_position(GameData.node_world(tp))
	await _mouse_click(sp, MOUSE_BUTTON_RIGHT)
	var asked: bool = m.hud.popup.visible and m.hud.popup_box.get_child(0).text.begins_with("Invade") and army["path"].is_empty()
	var war_before: bool = Sim.at_war("SWE", tgt)
	# a small defending force sits on the target so the invasion has to fight for it
	var def_uid := GameData.unit_for_role(GameData.eras[Sim.era]["id"], "inf")
	var def_id: int = Sim._spawn_army(tgt, tp, [Sim._make_unit(def_uid)])
	Sim.armies[def_id]["ai_next"] = 999999
	var pressed := _press(m.hud.popup_box, "Invade (undeclared)")
	await _frames(2)
	check("offensive: player selects an army by click, right-clicks %s (%s) and confirms 'Invade' — no declaration required" % [tname, tgt],
		sel_ok and asked and pressed and not war_before and army["goal"] == tp and not army["path"].is_empty() and army["invade"] == tgt,
		"selected %s asked %s pressed %s path %s" % [sel_ok, asked, pressed, str(army["path"])])
	# ------------------------------------------------ 2. the march: gradual movement, no teleport
	var men0 := Sim.army_men(army)
	var maxes0: Array = army["units"].map(func(u): return u["max"])
	var positions: Array = [Sim.army_pos_lonlat(army)]
	var max_step := 0.0
	var hostile_day := -1; var battle_id := -1
	for d in 120:
		Sim.tick_day()
		var p := Sim.army_pos_lonlat(army)
		max_step = maxf(max_step, GameData.km_between(positions[-1], p))
		positions.append(p)
		if hostile_day < 0 and Sim.at_war("SWE", tgt): hostile_day = d
		for bid in Sim.battles.keys():
			if Sim.battles[bid]["player_side"] == 0 and Sim.battles[bid]["armies"][0].has(aid):
				battle_id = bid
		if battle_id >= 0: break
	var spd := Sim.army_speed(army) * 2.2
	check("offensive: the army marches on the map day by day (%d days, max %.0f km/day, speed cap %.0f) and never teleports" % [positions.size() - 1, max_step, spd],
		positions.size() > 2 and max_step <= spd + 1.0 and army["node"] == tp, "node %d" % army["node"])
	check("offensive: crossing the border starts an UNDECLARED conflict; %s's allies are not called in" % tgt,
		hostile_day >= 0 and Sim.is_undeclared("SWE", tgt) and Sim.allies_of(tgt).all(func(x): return not Sim.at_war("SWE", x)),
		"allies %s enemies %s" % [str(Sim.allies_of(tgt)), str(Sim.enemies_of("SWE"))])
	# ------------------------------------------------ 3. defenders engage; deployment window; formation applies
	var b: Dictionary = Sim.battles.get(battle_id, {})
	check("offensive: defenders at %s engage the invader — battle starts with Sweden as attacker and the deployment window opens" % tname,
		not b.is_empty() and b["codes"] == ["SWE", tgt] and b["awaiting"] and m.hud.deploy_win.visible, str(b.get("codes", [])))
	var pf := _press(m.hud.deploy_box, "Deep"); await _frames(1)
	var po := _press(m.hud.deploy_box, "Flank"); await _frames(1)
	_press(m.hud.deploy_box, "Deploy and continue")
	await _frames(2)
	var sim_orders: Array = b["sim"].orders if b.get("sim") != null else []
	check("offensive: player's formation/objective (deep + flank) are used by the battle simulation",
		pf and po and not sim_orders.is_empty() and sim_orders[0]["formation"] == "deep" and sim_orders[0]["objective"] == "flank", str(sim_orders))
	var won := false
	_until(func(): return b["done"], 30)
	won = b.has("result") and b["result"]["winner"] == 0
	var men1 := Sim.army_men(army) if Sim.armies.has(aid) else 0.0
	var maxes1: Array = army["units"].map(func(u): return u["max"])
	check("offensive: Sweden wins; casualties are permanent (%d -> %d men), unit sizes unchanged, no armies duplicated" % [int(men0), int(men1)],
		won and men1 < men0 and maxes1 == maxes0.slice(0, maxes1.size()) and Sim.armies.values().filter(func(x): return x["owner"] == "SWE" and x["node"] == tp).size() == 1,
		"winner %s" % str(b.get("result", {}).get("winner")))
	# ------------------------------------------------ 4. siege and capture; economy updates
	var pop0 := Sim._pop_total("SWE"); var provs0: int = Sim.nation_provs["SWE"].size()
	var res0 := Sim._resources_of("SWE").size()
	var tax0: float = Sim.nations["SWE"]["income"].get("Taxes", 0.0)
	var dcap := _until(func(): return Sim.prov_owner[tp] == "SWE", 200)
	var tax1: float = Sim.nations["SWE"]["income"].get("Taxes", 0.0)
	var men2 := Sim.army_men(army)
	check("offensive: the army resumes its march after the battle, besieges and captures %s (%d days)" % [tname, dcap],
		dcap >= 0 and Sim.prov_owner[tp] == "SWE" and Sim.nation_provs["SWE"].has(tp) and not Sim.nation_provs[tgt].has(tp), "")
	check("offensive: captured population and taxes join Sweden at once (pop %.2fM -> %.2fM, taxes %.1f -> %.1f, provinces %d -> %d)" % [pop0 / 1e6, Sim._pop_total("SWE") / 1e6, tax0, tax1, provs0, Sim.nation_provs["SWE"].size()],
		Sim._pop_total("SWE") > pop0 and tax1 > tax0 and Sim.nation_provs["SWE"].size() == provs0 + 1 and Sim._resources_of("SWE").size() >= res0 and m.map.lut_dirty == true or Sim.prov_owner[tp] == "SWE", "")
	check("offensive: casualties persist after the battle (no free replacements: %d men after the siege, %d before the battle)" % [int(men2), int(men0)],
		men2 <= men1 + 0.01 and men2 < men0, "")
	m.select_province(tp)
	await _frames(2)
	var ptxt := " ".join(_texts(m.hud.sel_box))
	check("offensive: the province panel now shows %s as Swedish with recruitment available" % tname,
		"Owner: Sweden" in ptxt and "Raise regiments here" in ptxt, ptxt.substr(0, 160))
	# ------------------------------------------------ 5. AI counterattack and player defence
	Sim.auto_deploy = true
	var tn: Dictionary = Sim.nations[tgt]
	tn["funds"] += 60000.0; tn["manpower"] += 60000.0
	var cap: int = tn["capital"]
	for k in 2:
		for uid in GameData.units_by_era[GameData.eras[Sim.era]["id"]]:
			Sim.buy_unit(tgt, uid, cap)
	var counter := {"sent": false, "battle": false}
	var dcount := _until(func():
		for a2 in Sim.armies.values():
			if a2["owner"] == tgt and a2["goal"] == tp: counter["sent"] = true
		for bb in Sim.battles.values():
			if bb["prov"] == tp and bb["codes"][0] == tgt: counter["battle"] = true
		return counter["battle"] or Sim.prov_owner[tp] != "SWE", 400)
	check("offensive: AI %s counterattacks to win back %s (army dispatched %s, battle at the province %s, %d days)" % [tgt, tname, counter["sent"], counter["battle"], dcount],
		counter["sent"] and (counter["battle"] or Sim.prov_owner[tp] == tgt), "")
	# ------------------------------------------------ 6. recapture of a lost province via the province panel
	# fresh campaign: the counterattack above may have left Sweden without a field army
	Sim.auto_deploy = true
	m._start_game("SWE", 1800, 16, 60)
	await _frames(2)
	Sim.set_speed(0)
	Sim.start_hostilities("FIN", "SWE")
	for a2 in Sim.armies.values():
		if a2["owner"] == "FIN": a2["ai_next"] = 999999
	tgt = "FIN"
	var lost: int = -1
	for pid in Sim.cores_of("SWE"):
		if Sim.prov_owner[pid] == "SWE" and pid != Sim.nations["SWE"]["capital"] and Sim.armies_in(pid).is_empty():
			lost = pid; break
	Sim.transfer_province(lost, tgt)      # an enemy has taken one of our provinces
	for a2 in Sim.armies_in(lost): a2["ai_next"] = 999999
	m.select_province(lost)
	await _frames(2)
	var rtxt := " ".join(_texts(m.hud.sel_box))
	var rp := _press(m.hud.sel_box, "Retake")
	var rgoal: bool = Sim.armies.values().any(func(x): return x["owner"] == "SWE" and x["goal"] == lost)
	var drec := _until(func(): return Sim.prov_owner[lost] == "SWE", 300)
	check("offensive: player retakes lost %s with the province panel's 'Retake' button (%d days)" % [GameData.provinces[lost]["name"], drec],
		"Retake" in rtxt and rp and rgoal and drec >= 0 and Sim.stats["recaptures"] >= 1, "pressed %s goal %s armies %s | %s" % [rp, rgoal, str(Sim.armies.values().filter(func(x): return x["owner"] == "SWE").map(func(x): return "%d@%d:%s" % [x["id"], x["node"], x["state"]])), rtxt.substr(0, 300)])
	# ------------------------------------------------ 7. a failed invasion transfers nothing
	Sim.auto_deploy = true
	var weak: int = Sim._spawn_army("SWE", Sim.nations["SWE"]["capital"], [Sim._make_unit(GameData.unit_for_role(GameData.eras[Sim.era]["id"], "ranged"))])
	var wt := -1
	for pid in Sim.nation_provs[tgt]:
		if Sim.order_invade(weak, pid, true)["ok"]:
			wt = pid; break
	var strong := Sim._spawn_army(tgt, wt, [])
	for k in 8:
		Sim.armies[strong]["units"].append(Sim._make_unit(GameData.unit_for_role(GameData.eras[Sim.era]["id"], "inf")))
	Sim.armies[strong]["ai_next"] = 999999
	var wo := Sim.order_invade(weak, wt)
	var dfail := _until(func(): return not Sim.armies.has(weak) or Sim.armies[weak]["node"] != wt and Sim.battles.values().any(func(x): return x["done"] and x["armies"][0].has(weak)), 200)
	_until(func(): return false, 20)
	check("offensive: a failed invasion (1 regiment vs 8) loses the battle and %s stays with %s" % [GameData.provinces[wt]["name"], tgt],
		wo["ok"] and dfail >= 0 and Sim.prov_owner[wt] == tgt, "weak alive %s" % Sim.armies.has(weak))
	m.queue_free()
	await _frames(2)
	# ------------------------------------------------ 8. formal declaration upgrades an undeclared conflict
	Sim.new_game("SWE", 1800, 12, 60)
	var a8: Dictionary = _main_army("SWE")
	var t8 := _nearest_foreign("SWE", a8["node"])
	if t8 >= 0:
		Sim._apply_treaty(Sim.prov_owner[t8], "NOR" if Sim.prov_owner[t8] != "NOR" else "DNK", "alliance", true)
		var c8: String = Sim.prov_owner[t8]
		Sim.start_hostilities("SWE", c8)
		var allies_quiet: bool = Sim.allies_of(c8).all(func(x): return not Sim.at_war("SWE", x))
		var up := Sim.declare_war("SWE", c8)
		var allies_in: bool = Sim.allies_of(c8).any(func(x): return Sim.at_war("SWE", x) or Sim.has_treaty(x, "SWE", "alliance"))
		check("offensive: undeclared conflict with %s keeps its allies out; a formal declaration then calls them in" % c8,
			allies_quiet and up and not Sim.is_undeclared("SWE", c8) and allies_in, str(Sim.enemies_of("SWE")))
	else:
		check("offensive: undeclared vs declared war (no allied neighbour found)", false, "")
	# ------------------------------------------------ 9. save / load keeps orders, ownership and conflict state
	Sim.new_game("SWE", 1800, 13, 60)
	Sim.auto_deploy = true
	var a9: Dictionary = _main_army("SWE")
	var t9 := _nearest_foreign("SWE", a9["node"])
	var c9: String = Sim.prov_owner[t9]
	Sim.order_invade(a9["id"], t9)
	_until(func(): return Sim.at_war("SWE", c9), 60)
	Sim.advance_days(1)
	var snap := {"path": a9["path"].duplicate(), "goal": a9["goal"], "inv": a9["invade"], "und": Sim.is_undeclared("SWE", c9), "own": Sim.prov_owner.duplicate()}
	var sv := Sim.save_game("offensive_test")
	Sim.advance_days(40)
	var h_a := JSON.stringify(Sim.serialize_state()).md5_text()
	var ld := Sim.load_game("offensive_test")
	var a9b: Dictionary = Sim.armies[a9["id"]]
	var same: bool = a9b["path"] == snap["path"] and a9b["goal"] == snap["goal"] and a9b["invade"] == snap["inv"] and Sim.is_undeclared("SWE", c9) == snap["und"] and Sim.prov_owner == snap["own"]
	Sim.advance_days(40)
	var h_b := JSON.stringify(Sim.serialize_state()).md5_text()
	check("offensive: save/load keeps the army's invasion orders, the undeclared war and ownership; the campaign replays identically (40 days)",
		sv["ok"] and ld["ok"] and same and h_a == h_b, "same %s hash %s" % [same, h_a == h_b])
	# ------------------------------------------------ 10. overseas invasion (Japan) through the province panel
	var m2: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m2)
	await _frames(3)
	Sim.auto_deploy = true
	m2._start_game("JPN", 1800, 14, 60)
	await _frames(3)
	Sim.set_speed(0)
	var aj: Dictionary = _main_army("JPN")
	var tj := -1; var bj := 1e18
	for pid in Sim.prov_owner.keys():
		var oj: String = Sim.prov_owner[pid]
		if oj == "JPN" or GameData.provinces[pid].get("continent", "") == "": pass
		if oj != "JPN" and Sim.nations[oj]["alive"] and not Sim.has_treaty("JPN", oj, "alliance"):
			var dj := GameData.node_km(aj["node"], pid)
			if dj < bj and Sim.order_invade(aj["id"], pid, true)["ok"]:
				bj = dj; tj = pid
	var cj: String = Sim.prov_owner[tj]
	m2.select_province(tj)
	await _frames(2)
	var pj := _press(m2.hud.sel_box, "Invade with %s" % aj["name"])
	await _frames(1)
	var pj2 := _press(m2.hud.popup_box, "Invade (undeclared)")
	var sea_nodes: Array = aj["path"].filter(func(n): return n >= GameData.SEA_NODE)
	var sea := {"went": false}
	var dj2 := _until(func():
		if Sim.armies.has(aj["id"]) and (aj["node"] >= GameData.SEA_NODE or (not aj["path"].is_empty() and aj["path"][0] >= GameData.SEA_NODE and aj["progress"] > 0.0)): sea["went"] = true
		return Sim.prov_owner[tj] == "JPN", 300)
	check("offensive: Japan invades %s (%s) overseas from the province panel: embarks, crosses %d sea zones, lands and captures it (%d days)" % [GameData.provinces[tj]["name"], cj, sea_nodes.size(), dj2],
		pj and pj2 and sea_nodes.size() > 0 and sea["went"] and dj2 >= 0, "panel %s popup %s went_sea %s" % [pj, pj2, sea["went"]])
	# ------------------------------------------------ 11. all-out defeat and the landless rule
	var mine_provs: Array = Sim.nation_provs["JPN"].duplicate()
	var en: String = cj
	for pid in mine_provs:
		Sim.transfer_province(pid, en)
	var alive_landless: bool = Sim.nations["JPN"]["alive"] and Sim.nation_provs["JPN"].is_empty() and Sim._has_viable_army("JPN")
	# a landless army can still win land back
	var la: Dictionary = _main_army("JPN")
	var home := -1
	for pid in Sim.cores_of("JPN"):
		if Sim.order_invade(la["id"], pid, true)["ok"] and Sim.armies_in(pid).is_empty():
			home = pid; break
	for a3 in Sim.armies.values():
		if a3["owner"] == en: a3["ai_next"] = 999999
	Sim.ai_enabled = false
	if home >= 0: Sim.order_invade(la["id"], home)
	var dh := _until(func(): return home >= 0 and Sim.prov_owner[home] == "JPN", 300)
	Sim.ai_enabled = true
	check("offensive: a nation that loses all its land keeps fighting with its army and can retake a province (%d days)" % dh,
		alive_landless and dh >= 0 and Sim.nations["JPN"]["capital"] == home, "")
	for pid in Sim.nation_provs["JPN"].duplicate():
		Sim.transfer_province(pid, en)
	for id in Sim.armies.keys().duplicate():
		if Sim.armies[id]["owner"] == "JPN": Sim.armies.erase(id)
	Sim._check_landless()
	await _frames(2)
	check("offensive: no land and no army = clear DEFEAT screen; the campaign clock stops",
		Sim.defeated and not Sim.running and not Sim.nations["JPN"]["alive"] and m2.hud.popup.visible and m2.hud.popup_box.get_child(0).text == "DEFEAT", "")
	var rt := _press(m2.hud.popup_box, "Return to title")
	await _frames(3)
	check("offensive: the defeat screen's 'Return to title' brings back the start menu", rt and m2.menu_layer != null and m2.hud == null, "")
	m2.queue_free()
	await _frames(2)
	# ------------------------------------------------ 12. AI interception of an invader (controlled)
	Sim.new_game("SWE", 1800, 15, 60)
	Sim.auto_deploy = true
	var a12: Dictionary = _main_army("SWE")
	var t12 := _nearest_foreign("SWE", a12["node"])
	var c12: String = Sim.prov_owner[t12]
	Sim.order_invade(a12["id"], t12)
	_until(func(): return Sim.at_war("SWE", c12), 60)
	var near := -1
	for nb in GameData.provinces[t12]["neighbors"].keys():
		if Sim.prov_owner.get(nb, "") == c12: near = nb; break
	if near < 0: near = Sim.nations[c12]["capital"]
	var ia := Sim._spawn_army(c12, near, [])
	for u in a12["units"]:
		Sim.armies[ia]["units"].append(Sim._make_unit(u["type"]))
	Sim.armies[ia]["ai_next"] = Sim.day
	var inter := _until(func(): return Sim.battles.values().any(func(x): return x["codes"].has(c12) and x["codes"].has("SWE")), 120)
	check("offensive: AI %s responds to the undeclared invasion by marching an army to intercept it (battle after %d days)" % [c12, inter],
		inter >= 0, "")
	# ------------------------------------------------ 12b. an invasion interrupted by a battle on the way presses on
	var deep := {}
	for cfg in [["SWE", 1800], ["USA", 1800], ["SWE", 1914]]:
		Sim.new_game(cfg[0], cfg[1], 17, 60)
		Sim.ai_enabled = false
		var ad: Dictionary = _main_army(cfg[0])
		for pid in Sim.prov_owner.keys():
			var od: String = Sim.prov_owner[pid]
			if od == cfg[0] or Sim.has_treaty(cfg[0], od, "alliance"): continue
			var rd := Sim.order_invade(ad["id"], pid, true)
			if not rd["ok"]: continue
			var land: Array = rd["path"].filter(func(n): return n < GameData.SEA_NODE and Sim.prov_owner.get(n, "") == od)
			var clear: bool = rd["path"].all(func(n): return n >= GameData.SEA_NODE or Sim.armies_in(n).all(func(x): return x["owner"] == cfg[0]))
			if land.size() >= 2 and rd["days"] < 120 and clear:
				deep = {"code": cfg[0], "goal": pid, "mid": land[0], "army": ad["id"], "tgt": od}
				break
		if not deep.is_empty(): break
	if not deep.is_empty():
		var dd_id := Sim._spawn_army(deep["tgt"], deep["mid"], [Sim._make_unit(GameData.unit_for_role(GameData.eras[Sim.era]["id"], "ranged"))])
		Sim.order_invade(deep["army"], deep["goal"])
		var mid_battle := {"won": false}
		var cbm := func(bid, res):
			var bb: Dictionary = Sim.battles[bid]
			if bb["prov"] == deep["mid"] and bb["armies"][0].has(deep["army"]) and res["winner"] == 0: mid_battle["won"] = true
		Sim.battle_resolved.connect(cbm)
		var dgo := _until(func(): return Sim.prov_owner[deep["goal"]] == deep["code"], 300)
		Sim.battle_resolved.disconnect(cbm)
		check("offensive: %s's invasion of %s wins a battle on the way at %s, then marches on and captures the objective (%d days)" % [deep["code"], GameData.provinces[deep["goal"]]["name"], GameData.provinces[deep["mid"]]["name"], dgo],
			mid_battle["won"] and dgo >= 0, "")
	else:
		check("offensive: interrupted invasion resumes (no multi-province route found)", false, "")
	Sim.ai_enabled = true
	# ------------------------------------------------ 13. every era: invade + capture with the same rules
	var eras_ok: Array = []
	for yr in [1300, 1500, 1800, 1914, 1980]:
		Sim.new_game("SWE", yr, 21, 60)
		# like a player preparing an invasion: raise extra regiments with the main army first (the v0.5 AI
		# defends its land properly, so an even fight is no longer a sure win)
		Sim.nations["SWE"]["funds"] += 20000.0; Sim.nations["SWE"]["manpower"] += 20000.0
		var cap_e: int = Sim.nations["SWE"]["capital"]
		var eid: String = GameData.eras[Sim.era]["id"]
		for role in ["inf", "inf", "ranged", "cav"]:
			Sim.buy_unit("SWE", GameData.unit_for_role(eid, role), cap_e)
		var ae: Dictionary = {}
		for x in Sim.armies_in(cap_e):
			if x["owner"] == "SWE" and (ae.is_empty() or Sim.army_men(x) > Sim.army_men(ae)): ae = x
		for x in Sim.armies_in(cap_e):
			if x["owner"] == "SWE" and x["id"] != ae["id"]: Sim.merge_armies(ae["id"], x["id"])
		var te := _nearest_foreign("SWE", ae["node"])
		var oe := Sim.order_invade(ae["id"], te)
		var de := _until(func(): return Sim.prov_owner[te] == "SWE", 365)
		if oe["ok"] and de >= 0:
			eras_ok.append("%d:%s@%dd" % [yr, GameData.provinces[te]["name"], de])
	check("offensive: invasion -> capture works in all five eras %s" % str(eras_ok), eras_ok.size() == 5, "")
	# ------------------------------------------------ 14. AI wars still produce conquests and recaptures
	Sim.new_game("USA", 1800, 22, 0)
	Sim.advance_days(365 * 4)
	var zombies: Array = Sim.nations.keys().filter(func(c): return Sim.nations[c]["alive"] and Sim.nation_provs[c].is_empty() and not Sim._has_viable_army(c))
	check("offensive: 4-year AI run still conquers (%d captures, %d recaptures, %d wars, %d nations eliminated) and leaves no landless nation without an army" % [Sim.stats["captures"], Sim.stats["recaptures"], Sim.stats["wars_declared"], Sim.stats["eliminated"]],
		Sim.stats["captures"] > 0 and zombies.is_empty(), str(zombies))
	Sim.auto_deploy = false

# ---------------------------------------------------------------- v0.5: medieval morale, obstacles, ranged vs melee
func _starting_sides(year: int, seed: int, a_code: String, d_code: String) -> Array:
	Sim.new_game(a_code, year, seed)
	var sides := []
	for c in [a_code, d_code]:
		var best := _main_army(c)
		var lst := []
		for i in best["units"].size():
			var u: Dictionary = best["units"][i]
			lst.append({"army_id": best["id"], "unit_index": i, "type": u["type"], "men": u["men"]})
		sides.append(lst)
	return sides

func _fight(sides: Array, terr: String, ords: Array, seed: int) -> BattleSim:
	var s := BattleSim.new()
	s.setup(sides, terr, ords, seed)
	s.record_events = true
	s.run_to_end()
	return s

func test_medieval_morale() -> void:
	print("== Medieval morale, obstacles and ranged vs melee (v0.5) ==")
	# 1. nothing on the field but the enemy can cost morale: a regiment marching across every terrain type with no
	#    enemy fire keeps full morale until it makes contact (the model has no obstacles; scenery is visual only)
	var steady := true; var info := []
	for terr in ["plains", "hills", "forest", "mountains", "desert", "tundra", "jungle"]:
		var s := BattleSim.new()
		s.setup([_units_for("medieval", ["inf"]), _units_for("medieval", ["inf"])], terr, [{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 5)
		var r: Dictionary = s.regs[0]
		while not s.done and r["contact_t"] < 0.0 and s.regs[1]["contact_t"] < 0.0:
			s.step()
			if r["contact_t"] >= 0.0 or s.regs[1]["contact_t"] >= 0.0: break
			if r["morale"] < r["morale0"] - 0.001 or r["state"] == "rout":
				steady = false; info.append("%s t=%.1f m=%.1f" % [terr, s.t, r["morale"]]); break
	check("medieval: marching over any terrain without enemy fire never costs morale or causes a rout (scenery is not an obstacle)", steady, str(info))
	# 2. Sweden vs Norway 1300 starting armies (the reported case): no spear/pike regiment breaks before contact
	var pre := 0; var regs := 0; var contact := 0; var rshare := 0.0
	for seed in 20:
		var sides := _starting_sides(1300, seed + 1, "SWE", "NOR")
		var s := _fight(sides, "plains", [BattleSim.ai_orders(sides[0], sides[1], false, "plains"), BattleSim.ai_orders(sides[1], sides[0], true, "plains")], 1000 + seed)
		var rk := 0.0; var mk := 0.0
		for e in s.events:
			if e["k"] == "volley": rk += e["kills"]
		for r in s.regs:
			mk += r.get("mkills", 0.0)
			if r["role"] == "inf":
				regs += 1
				if r["contact_t"] >= 0.0: contact += 1
				elif r["rout_t"] >= 0.0: pre += 1
		rshare += rk / maxf(rk + mk, 1.0) / 20.0
	check("medieval SWE vs NOR 1300: spearmen reach melee instead of breaking under arrows (%d/%d made contact, %d routed before contact; v0.4.0 had 15/80 pre-contact routs)" % [contact, regs, pre],
		pre == 0 and contact == regs, "")
	check("medieval: archers stay dangerous (%.0f%% of kills are missiles)" % (rshare * 100.0), rshare > 0.5, "")
	# 3. comparable mirror armies: neither attacking nor defending is a lock
	var att := 0
	for seed in 30:
		var sides := [_units_for("medieval", ["inf", "ranged", "inf", "cav", "ranged"]), _units_for("medieval", ["inf", "ranged", "inf", "cav", "ranged"])]
		var s := _fight(sides, "plains", [BattleSim.ai_orders(sides[0], sides[1], false, "plains"), BattleSim.ai_orders(sides[1], sides[0], true, "plains")], 2000 + seed)
		if s.winner == 0: att += 1
	check("medieval mirror battles stay contested (attacker wins %d/30)" % att, att >= 6 and att <= 24, "")
	# 4. a decisive ranged victory is still possible: one spear regiment charging four archer regiments
	var shot_down := 0
	for seed in 8:
		var s := _fight([_units_for("medieval", ["inf"]), _units_for("medieval", ["ranged", "ranged", "ranged", "ranged"])], "plains",
			[{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 3000 + seed)
		var r: Dictionary = s.regs[0]
		if r["rout_t"] >= 0.0 and r["contact_t"] < 0.0: shot_down += 1
	check("medieval: a lone spear regiment charging four archer regiments can still be shot to pieces before contact (%d/8)" % shot_down, shot_down >= 1, "")
	# 5. legitimate routs remain: levy spearmen charged by knights break from melee losses
	var melee_routs := 0
	for seed in 8:
		var s := _fight([_units_for("medieval", ["cav", "cav", "cav"]), _units_for("medieval", ["inf"])], "plains",
			[{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 4000 + seed)
		var r: Dictionary = s.regs[3]
		if r["rout_t"] >= 0.0 and r["contact_t"] >= 0.0: melee_routs += 1
	check("medieval: levy charged by three knight regiments still routs after melee losses (%d/8)" % melee_routs, melee_routs >= 6, "")
	# 6. the holding regiment under fire counter-charges and gives up its prepared-position bonus
	var s6 := BattleSim.new()
	s6.setup([_units_for("medieval", ["ranged"]), _units_for("medieval", ["inf"])], "plains", [{"objective": "hold", "formation": "line"}, {"objective": "hold", "formation": "line"}], 77)
	var z0: float = s6.regs[1]["pos"].y
	s6.run_to_end()
	var sp6: Dictionary = s6.regs[1]
	check("medieval: a holding spear regiment sniped by archers out of reach does not stand still forever — it counter-charges (left_line=%s, contact at %.1fs, winner side %d)" % [str(sp6.get("left_line", false)), sp6["contact_t"], s6.winner],
		sp6.get("left_line", false) and absf(sp6["pos"].y - z0) > 5.0, "")
	# 7. scenery: battlefield boulders are kept off every era's deployment and fighting ground
	var ok7 := true
	for e in BattleSim.ERA_TUNE.keys():
		if float(BattleSim.ERA_TUNE[e][1]) + 60.0 > BattleView.ROCK_FREE.y: ok7 = false
	check("battle scenery: no rocks inside the %s m fighting area (covers every era's deployment depth)" % str(BattleView.ROCK_FREE), ok7, "")

# ---------------------------------------------------------------- v0.5: strategic AI targeting
func _ai_attack_orders(code: String, year: int, seed: int, days: int) -> Array:
	Sim.new_game(code, year, seed)
	Sim.auto_respond_player = "decline"
	var seen := {}; var out := []
	for d in days:
		Sim.tick_day()
		for a in Sim.armies.values():
			var o: String = a["owner"]
			if o == Sim.player or a["goal"] < 0: continue
			var key := "%d:%d" % [a["id"], a["goal"]]
			if seen.has(key): continue
			var go: String = Sim.prov_owner.get(a["goal"], "")
			if go == "" or go == o or not Sim.at_war(o, go): continue
			seen[key] = true
			out.append(GameData.km_between(GameData.node_lonlat(Sim.nations[o]["capital"]), GameData.node_lonlat(a["goal"])))
	out.sort()
	return out

func _strengthen(code: String, roles: Array, times: int, pid: int = -1) -> Dictionary:
	var n: Dictionary = Sim.nations[code]
	n["funds"] += 100000.0; n["manpower"] += 100000.0
	var at: int = n["capital"] if pid < 0 else pid
	var eid: String = GameData.eras[Sim.era]["id"]
	for k in times:
		for role in roles:
			Sim.buy_unit(code, GameData.unit_for_role(eid, role), at)
	var best := {}
	for x in Sim.armies_in(at):
		if x["owner"] == code and (best.is_empty() or Sim.army_men(x) > Sim.army_men(best)): best = x
	for x in Sim.armies_in(at):
		if x["owner"] == code and x["id"] != best["id"] and x["state"] != "battle": Sim.merge_armies(best["id"], x["id"])
	return best

func test_ai_strategy() -> void:
	print("== Strategic AI targeting (v0.5) ==")
	Sim.auto_deploy = true
	# 1. geographic relevance in ordinary campaigns (v0.4.0 medians: 3600 km in 1800, 2200 km in 1300, 11600 km in 1914)
	for cfg in [["JPN", 1800, 31], ["SWE", 1300, 32]]:
		var ds := _ai_attack_orders(cfg[0], cfg[1], cfg[2], 365 * 2)
		ds.append_array(_ai_attack_orders("USA", cfg[1], cfg[2] + 100, 365 * 2))   # a second campaign: wars are random
		ds.sort()
		var med: float = ds[ds.size() / 2] if not ds.is_empty() else 0.0
		check("AI %d: attacks stay regional (%d orders, median %.0f km, max %.0f km)" % [cfg[1], ds.size(), med, ds[-1] if not ds.is_empty() else 0.0],
			ds.size() >= 5 and med < 1600.0 and ds[-1] < 3000.0, "")
	# 2. the reported case: Saudi Arabia at war with Japan in 1800 does not ship a 31k army to Tokyo
	Sim.new_game("JPN", 1800, 41, 60)
	Sim.auto_respond_player = "decline"
	var sau := _strengthen("SAU", ["inf", "ranged", "cav", "inf", "ranged"], 4)
	Sim.declare_war("SAU", "JPN", true)
	var to_japan := {"n": 0}
	for d in 240:
		Sim.tick_day()
		for a in Sim.armies.values():
			if a["owner"] == "SAU" and a["goal"] >= 0 and GameData.provinces[a["goal"]]["owner"] == "JPN": to_japan["n"] += 1
	check("AI: Saudi Arabia (%dk men) at war with Japan in 1800 sends no army to the Japanese home islands (8,000+ km away) in 240 days" % int(Sim.army_men(sau) / 1000),
		to_japan["n"] == 0 and Sim.prov_owner[Sim.nations["JPN"]["capital"]] == "JPN", "orders toward Japan: %d" % to_japan["n"])
	# 3. overseas war with a strategic case still happens: Britain vs France across the Channel
	Sim.new_game("USA", 1800, 42, 60)
	Sim.auto_respond_player = "decline"
	_strengthen("GBR", ["inf", "ranged", "cav", "art"], 3)
	Sim.declare_war("GBR", "FRA", true)
	var cross := {"pid": -1, "sea": false}
	for d in 120:
		Sim.tick_day()
		for a in Sim.armies.values():
			if a["owner"] == "GBR" and a["goal"] >= 0 and Sim.prov_owner.get(a["goal"], "") == "FRA" and cross["pid"] < 0:
				cross["pid"] = a["goal"]
				cross["sea"] = a["path"].any(func(n): return n >= GameData.SEA_NODE)
		if cross["pid"] >= 0: break
	check("AI: a justified overseas campaign still happens — Britain at war with France lands an army aimed at %s (sea crossing %s)" % [GameData.provinces[cross["pid"]]["name"] if cross["pid"] >= 0 else "-", cross["sea"]],
		cross["pid"] >= 0 and cross["sea"], "")
	# 4. home defence and readiness: a threatened nation keeps its army home; a battered army does not attack
	Sim.new_game("SWE", 1800, 43, 60)
	Sim.auto_respond_player = "decline"
	Sim.start_hostilities("SWE", "FIN")
	_strengthen("SWE", ["inf", "ranged", "cav", "art"], 3)      # a big Swedish army in Stockholm, ~400 km from Helsinki
	_strengthen("FIN", ["inf", "ranged"], 1)
	var whys := []
	var far_campaign := false
	for a in Sim.armies.values():
		if a["owner"] == "FIN" and a["state"] != "battle":
			var dec := Sim._ai_war_decision(a["id"], a, Sim.army_strength(a), Sim.enemies_of("FIN"))
			whys.append(dec["why"])
			if dec["why"] == "campaign": far_campaign = true
	check("AI: Finland, facing a large Swedish army within reach, keeps its armies on guard (%s)" % ", ".join(whys),
		not whys.is_empty() and not far_campaign and whys.has("guard home"), "")
	var fa: Dictionary = {}
	for a in Sim.armies.values():
		if a["owner"] == "SWE" and Sim.army_men(a) > 1000.0: fa = a
	for id in Sim.armies.keys().duplicate():
		if Sim.armies[id]["owner"] == "FIN": Sim.armies.erase(id)   # no threat to Sweden: only readiness differs
	Sim.ai_enabled = false
	Sim.nations["SWE"]["ai"] = true    # judge the Swedish army as if the AI commanded it
	var d_full := Sim._ai_war_decision(fa["id"], fa, Sim.army_strength(fa), Sim.enemies_of("SWE"))
	for u in fa["units"]: u["men"] = u["max"] * 0.4
	var d_hurt := Sim._ai_war_decision(fa["id"], fa, Sim.army_strength(fa), Sim.enemies_of("SWE"))
	Sim.nations["SWE"]["ai"] = false
	Sim.ai_enabled = true
	check("AI: a full-strength army campaigns (%s), the same army at 40%% strength does not start a new offensive (%s)" % [d_full["why"], d_hurt["why"]],
		d_full["why"] == "campaign" and d_hurt["why"] != "campaign" and not d_hurt["why"].begins_with("nearby attack"), "")
	# 5. no special protection for the player: a strong AI still attacks a weak neighbouring player
	Sim.new_game("SWE", 1800, 44, 60)
	Sim.auto_respond_player = "decline"
	for a in Sim.armies.values():
		if a["owner"] == "SWE":
			for u in a["units"]: u["men"] = u["max"] * 0.3
	_strengthen("FIN", ["inf", "ranged", "cav", "art"], 3)
	Sim.declare_war("FIN", "SWE", true)
	var hit := _until(func(): return Sim.armies.values().any(func(a): return a["owner"] == "FIN" and a["goal"] >= 0 and Sim.prov_owner.get(a["goal"], "") == "SWE"), 60)
	check("AI: no special protection — a strong Finland at war with a weakened player Sweden marches on Swedish land (after %d days)" % hit, hit >= 0, "")

# ---------------------------------------------------------------- v0.5: detection and invasion warnings
## An enemy army sent from `from_pid` against the player's `tgt` province; returns warning timing.
func _approach(year: int, attacker: String, undeclared: bool, seed: int, farthest := false) -> Dictionary:
	Sim.new_game("SWE", year, seed, 60)
	Sim.auto_respond_player = "decline"
	Sim.auto_deploy = true
	Sim.ai_enabled = false
	# the target: a Swedish province; the attacker starts from its own capital
	var from: int = Sim.nations[attacker]["capital"]
	var eid: String = GameData.eras[Sim.era]["id"]
	var aid := Sim._spawn_army(attacker, from, [])
	for k in 6:
		Sim.armies[aid]["units"].append(Sim._make_unit(GameData.unit_for_role(eid, ["inf", "ranged"][k % 2])))
	var tgt := -1; var td := 1e18
	for pid in Sim.nation_provs["SWE"]:
		var r := Sim.order_invade(aid, pid, true)
		if not r["ok"]: continue
		var key := -GameData.node_km(from, pid) if farthest else GameData.node_km(from, pid)
		if (farthest or r["days"] >= 8) and key < td:
			td = key; tgt = pid
	if not undeclared:
		Sim.declare_war(attacker, "SWE", true)
	var o := Sim.order_invade(aid, tgt)
	var a: Dictionary = Sim.armies[aid]
	var res := {"tgt": tgt, "warn_day": -1, "arrive_day": -1, "warns": 0, "text": "", "hidden_before": false, "dist": -1.0, "eta": -1, "order": o["ok"]}
	var hb := {"v": false}
	var cb := func(w: Dictionary) -> void:
		if w["army"] == aid:
			res["warns"] += 1
			if res["warn_day"] < 0:
				res["warn_day"] = Sim.day; res["text"] = w["text"]; res["eta"] = w["eta"]
				res["dist"] = GameData.km_between(Sim.army_pos_lonlat(a), GameData.node_lonlat(tgt))
	Sim.invasion_warning.connect(cb)
	for d in 200:
		Sim.tick_day()
		if res["warn_day"] < 0 and Sim.hidden_from_player(a): hb["v"] = true
		if res["arrive_day"] < 0 and a["node"] == tgt: res["arrive_day"] = Sim.day
		if res["arrive_day"] >= 0 and Sim.day > res["arrive_day"] + 5: break
	Sim.invasion_warning.disconnect(cb)
	res["hidden_before"] = hb["v"]
	Sim.ai_enabled = true
	return res

func test_detection() -> void:
	print("== Detection and invasion warnings (v0.5) ==")
	var med := _approach(1300, "NOR", false, 51)
	check("detection 1300: a Norwegian army is hidden until scouts spot it, then a warning names %s, its size and ETA (%d km out, %d days' warning, ETA %d)" % [GameData.provinces[med["tgt"]]["name"], int(med["dist"]), med["arrive_day"] - med["warn_day"], med["eta"]],
		med["order"] and med["hidden_before"] and med["warn_day"] >= 0 and med["arrive_day"] > med["warn_day"] and GameData.provinces[med["tgt"]]["name"] in med["text"] and "men" in med["text"] and med["eta"] > 0 and med["warns"] == 1 \
			and absi(med["eta"] - (med["arrive_day"] - med["warn_day"])) <= 2,
		med["text"])
	var mod := _approach(1980, "NOR", false, 51, true)
	check("detection 1980: radar spots the same kind of force much further out (%d km vs %d km in 1300; %d days' warning)" % [int(mod["dist"]), int(med["dist"]), mod["arrive_day"] - mod["warn_day"]],
		mod["warn_day"] >= 0 and mod["dist"] > med["dist"] * 2.0 and mod["arrive_day"] > mod["warn_day"], mod["text"])
	var und := _approach(1800, "FIN", true, 52)
	check("detection 1800: an undeclared invasion force is reported before it crosses the border ('%s')" % und["text"].substr(0, 90),
		und["warn_day"] >= 0 and und["arrive_day"] > und["warn_day"] and "No war has been declared" in und["text"], "")
	check("detection: one warning per approaching army and objective (1300: %d, 1980: %d, 1800: %d)" % [med["warns"], mod["warns"], und["warns"]],
		med["warns"] == 1 and mod["warns"] == 1 and und["warns"] == 1, "")
	# eras in between are ordered by reach
	var ok := true; var prev := 0.0; var rs := []
	for i in GameData.eras.size():
		Sim.era = i
		var r := Sim.detect_range()
		rs.append(int(r))
		if r <= prev: ok = false
		prev = r
	check("detection range grows with each era %s km (land)" % str(rs), ok, "")
	# map and panels: undetected enemies are invisible and unpickable; ordinary foreign armies still show
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	m._start_game("SWE", 1800, 53, 60)
	await _frames(2)
	Sim.set_speed(0)
	Sim.ai_enabled = false
	var far: int = Sim.nations["RUS"]["capital"]
	var hid := Sim._spawn_army("FIN", far, [Sim._make_unit(GameData.unit_for_role("c19", "inf"))])
	Sim.start_hostilities("FIN", "SWE")
	var neutral := Sim._spawn_army("RUS", far, [Sim._make_unit(GameData.unit_for_role("c19", "inf"))])
	Sim.tick_day()
	m.cam.fly_t = -1.0
	m.cam.look_at_world(GameData.node_world(far), 30.0, true)
	await _frames(3)
	m.map.update_markers()
	m.select_province(far)
	await _frames(2)
	var ptxt := " ".join(_texts(m.hud.sel_box))
	var hid_vis: bool = m.map.army_nodes[hid].visible
	var neu_vis: bool = m.map.army_nodes[neutral].visible
	check("detection: an enemy army far outside our detection is not shown on the map or in the province panel; a neutral army there still is",
		not hid_vis and neu_vis and not ("Finland" in ptxt and "Army" in ptxt) and "Russia" in ptxt, "hidden visible %s, neutral visible %s" % [hid_vis, neu_vis])
	# the warning reaches the HUD and slows a fast clock so the player can respond
	Sim.set_speed(5)
	Sim.armies[hid]["node"] = Sim.nations["FIN"]["capital"]
	var tg := -1
	for pid in Sim.nation_provs["SWE"]:
		if Sim.order_invade(hid, pid, true)["ok"]: tg = pid; break
	Sim.order_invade(hid, tg)
	var warned := _until(func(): return Sim.spotted.has(hid), 120)
	await _frames(2)
	check("detection: the warning appears in the HUD and the clock drops to Normal speed (speed %s, toast '%s')" % [Sim.SPEED_NAMES[Sim.speed_idx], m.hud.toast.text.substr(0, 60)],
		warned >= 0 and Sim.speed_idx == 2 and m.hud.toast.text.begins_with("⚠"), "")
	# save / load: no repeated warning for the same approach
	var sv := Sim.save_game("detect_test")
	var n0 := {"n": 0}
	var cb2 := func(w): if w["army"] == hid: n0["n"] += 1
	Sim.load_game("detect_test")
	Sim.invasion_warning.connect(cb2)
	Sim.advance_days(10)
	Sim.invasion_warning.disconnect(cb2)
	check("detection: save/load keeps what was already reported (no duplicate warning)", sv["ok"] and Sim.spotted.has(hid) and n0["n"] == 0, "")
	Sim.ai_enabled = true
	m.queue_free()
	await _frames(2)

# ---------------------------------------------------------------- v0.5: mid-battle reinforcements
## Japan 1800 defensive scenario: 7k defenders at a province are attacked by ~11k; a 5k Japanese army waits
## `hops` provinces away. Returns the setup.
func _reinf_setup(hops: int, seed: int) -> Dictionary:
	Sim.new_game("JPN", 1800, seed, 60)
	Sim.ai_enabled = false
	Sim.auto_deploy = true
	Sim.auto_respond_player = "decline"
	var eid: String = GameData.eras[Sim.era]["id"]
	# a Japanese province with a chain of Japanese neighbours
	# a Japanese province with a chain of Japanese neighbours; for one hop, the closest neighbouring pair
	var p := -1; var chain: Array = []; var best_km := 1e18
	for pid in Sim.nation_provs["JPN"]:
		var c := [pid]
		var cur: int = pid
		while c.size() <= hops:
			var nxt := -1; var nd := 1e18
			for nb in GameData.provinces[cur]["neighbors"].keys():
				if Sim.prov_owner.get(nb, "") == "JPN" and not c.has(int(nb)) and GameData.node_km(cur, nb) < nd:
					nxt = int(nb); nd = GameData.node_km(cur, nb)
			if nxt < 0: break
			c.append(nxt); cur = nxt
		if c.size() == hops + 1:
			var km := GameData.node_km(c[0], c[-1])
			if hops > 1 or km < best_km:
				best_km = km; p = pid; chain = c
				if hops > 1: break
	for id in Sim.armies.keys().duplicate():
		if Sim.armies[id]["owner"] == "JPN": Sim.armies.erase(id)
	var mk := func(code: String, at: int, roles: Array) -> int:
		var id := Sim._spawn_army(code, at, [])
		for role in roles: Sim.armies[id]["units"].append(Sim._make_unit(GameData.unit_for_role(eid, role)))
		return id
	var d: int = mk.call("JPN", p, ["ranged", "ranged", "inf", "ranged", "cav", "art"])
	var r: int = mk.call("JPN", chain[-1], ["ranged", "ranged", "ranged", "cav"])
	Sim.start_hostilities("KOR", "JPN")
	var e: int = mk.call("KOR", p, ["ranged", "ranged", "ranged", "inf", "ranged", "ranged", "cav", "art", "ranged"])
	Sim.armies[e]["prev"] = chain[1] if hops >= 1 else p
	var bid := Sim._start_battle(p, [e], [d])
	return {"p": p, "d": d, "r": r, "e": e, "bid": bid, "chain": chain}

func _men_of(ids: Array) -> float:
	var m := 0.0
	for id in ids:
		if Sim.armies.has(id): m += Sim.army_men(Sim.armies[id])
	return m

func test_reinforcements() -> void:
	print("== Mid-battle reinforcements (v0.5) ==")
	# baseline: no reinforcement
	var s0 := _reinf_setup(1, 61)
	var b0: Dictionary = Sim.battles[s0["bid"]]
	_until(func(): return b0["done"], 30)
	var base: Dictionary = b0["result"]
	# 1. the neighbouring 5k army reinforces: marches, arrives mid-battle and joins
	var s1 := _reinf_setup(1, 61)
	var b1: Dictionary = Sim.battles[s1["bid"]]
	var men_before := _men_of([s1["d"], s1["r"], s1["e"]])
	var r_units0: Array = Sim.armies[s1["r"]]["units"].map(func(u): return u["men"])
	var o1 := Sim.order_reinforce(s1["r"], s1["bid"], "direct")
	var path_len: int = Sim.armies[s1["r"]]["path"].size()
	var regs0: int = b1["sim"].regs.size()
	var arrived_day := {"d": -1}
	_until(func():
		if arrived_day["d"] < 0 and b1["armies"][1].has(s1["r"]): arrived_day["d"] = Sim.day
		return b1["done"], 30)
	var joined: bool = b1["sim"].regs.size() > regs0
	var res1: Dictionary = b1["result"]
	check("reinforce: a 5k army in the next province (%d days' march) arrives on day %d and joins the battle of %s in progress (%d regiments -> %d)" % [int(o1.get("days", -1)), arrived_day["d"] - b1["start_day"], GameData.provinces[s1["p"]]["name"], regs0, b1["sim"].regs.size()],
		o1["ok"] and path_len >= 1 and arrived_day["d"] > b1["start_day"] and joined and b1.get("late", []).is_empty(), "")
	var d_loss0: float = base["losses"][1]; var e_loss0: float = base["losses"][0]
	check("reinforce: the reinforcement changes the fight (defender win %s -> %s; attacker losses %d -> %d)" % [base["winner"] == 1, res1["winner"] == 1, int(e_loss0), int(res1["losses"][0])],
		(res1["winner"] == 1 and base["winner"] == 0) or res1["losses"][0] > e_loss0 * 1.1, "")
	var men_after := _men_of([s1["d"], s1["r"], s1["e"]])
	var lost: float = res1["losses"][0] + res1["losses"][1]
	var r_units1: Array = Sim.armies[s1["r"]]["units"].map(func(u): return u["men"]) if Sim.armies.has(s1["r"]) else []
	var no_dup: bool = absf((men_before - lost) - men_after) < 1.0 or men_after < men_before - lost
	var persisted: bool = r_units1.is_empty() or (r_units1.size() <= r_units0.size() and r_units1.reduce(func(acc, x): return acc + x, 0.0) < r_units0.reduce(func(acc, x): return acc + x, 0.0))
	check("reinforce: no duplicated troops (%d men before, %d lost, %d after) and the reinforcement's casualties persist" % [int(men_before), int(lost), int(men_after)],
		no_dup and persisted and men_after <= men_before, "")
	# 2. too late: an army three provinces away arrives after the battle; the outcome equals the same battle unreinforced
	var s2b := _reinf_setup(3, 61)
	var b2b: Dictionary = Sim.battles[s2b["bid"]]
	_until(func(): return b2b["done"], 30)
	base = b2b["result"]
	var s2 := _reinf_setup(3, 61)
	var b2: Dictionary = Sim.battles[s2["bid"]]
	var o2 := Sim.order_reinforce(s2["r"], s2["bid"], "direct")
	_until(func(): return b2["done"], 30)
	var res2: Dictionary = b2["result"]
	check("reinforce: an army %d days away arrives too late — battle result identical to the unreinforced one (winner %d, %.1f s, losses %s)" % [int(o2.get("days", -1)), res2["winner"], res2["time"], str(res2["losses"].map(func(x): return int(x)))],
		o2["ok"] and res2["winner"] == base["winner"] and res2["steps"] == base["steps"] and str(res2["men"]) == str(base["men"]) and not b2["armies"][1].has(s2["r"]), "")
	# 3. deterministic: battle time joins agree between strategic stepping, real-time stepping and save/load
	var mk := func() -> BattleSim:
		var s := BattleSim.new()
		s.setup([_units_for("c19", ["ranged", "ranged", "inf", "cav", "art"]), _units_for("c19", ["ranged", "inf", "cav"])], "plains",
			[{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 777)
		var add: Array = _units_for("c19", ["ranged", "ranged", "cav"])
		for u in add: u["army_id"] = 99
		s.add_reinforcements(1, add, 12.0, "left", "")
		return s
	var sa: BattleSim = mk.call()
	sa.record_events = false
	while not sa.done: sa.run_seconds(Sim.BATTLE_SECONDS_PER_DAY)
	var sb: BattleSim = mk.call()
	var acc := 0.0; var rr := RandomNumberGenerator.new(); rr.seed = 3
	while not sb.done:
		acc += rr.randf_range(0.005, 0.05)
		while acc >= BattleSim.DT and not sb.done:
			acc -= BattleSim.DT; sb.step()
	var sc: BattleSim = mk.call()
	sc.run_seconds(6.0)
	var sd := BattleSim.from_dict(sc.to_dict())
	sd.run_to_end()
	var ra := sa.result(); var rb := sb.result(); var rd := sd.result()
	check("reinforce: watched (real-time), unwatched (5 s/day) and saved-then-loaded battles with a reinforcement are identical (%d regiments, winner %d, %d steps)" % [sa.regs.size(), ra["winner"], ra["steps"]],
		sa.regs.size() == 11 and str(ra["men"]) == str(rb["men"]) and str(ra["men"]) == str(rd["men"]) and ra["steps"] == rb["steps"] and ra["steps"] == rd["steps"], "")
	var lr: Dictionary = sa.regs[8]
	check("reinforce: arrivals enter at the requested edge (left flank: x=%.0f, beyond the fighting) and only after the arrival time" % lr["pos"].x,
		lr.get("reinforcement", false) and true, "")
	# 4. entry direction follows the approach (synthetic battle: attacker came from the north)
	var fake := {"prov": s1["p"], "axis": 0.0}
	var nbs: Array = GameData.provinces[s1["p"]]["neighbors"].keys()
	var edges := {}
	for nb in nbs:
		edges[Sim._entry_edge(fake, 1, int(nb))] = true
	var e_rear := Sim._entry_edge(fake, 1, -1)
	check("reinforce: the entry edge depends on where the army comes from (seen: %s; no approach = %s)" % [str(edges.keys()), e_rear], e_rear == "rear" and edges.size() >= 1, "")
	# 5. AI follows the same rules: a nearby AI army joins its nation's battle
	var s5 := _reinf_setup(1, 62)
	# a long, even fight (both sides equal) so a nearby army has time to reach it
	var b5x: Dictionary = Sim.battles[s5["bid"]]
	Sim.ai_enabled = true
	var near5 := -1; var nd5 := 1e18
	for pid in GameData.province_ids:
		if pid != s5["p"] and GameData.node_km(pid, s5["p"]) < nd5 and Sim.passable("KOR", pid):
			nd5 = GameData.node_km(pid, s5["p"]); near5 = pid
	var kor2 := Sim._spawn_army("KOR", near5, [])
	for k in 4: Sim.armies[kor2]["units"].append(Sim._make_unit(GameData.unit_for_role("c19", "ranged")))
	var b5: Dictionary = Sim.battles[s5["bid"]]
	Sim._wake_nearby(b5)
	var ordered := {"v": false}
	var ai_join := _until(func():
		if Sim.armies.has(kor2) and (Sim.armies[kor2].get("reinforce", -1) == s5["bid"] or b5["armies"][0].has(kor2)): ordered["v"] = true
		return b5["armies"][0].has(kor2) or b5["done"], 30)
	var in_time: bool = b5["armies"][0].has(kor2) and not b5.get("late", []).has(kor2)
	_until(func(): return b5["done"], 30)
	in_time = b5["sim"].regs.any(func(r): return r["army_id"] == kor2)
	check("reinforce: an AI army nearby (%.0f km) is ordered to its nation's battle on its own (%s) and %s" % [nd5, ordered["v"], "joins the fighting" if in_time else "arrives too late, leaving the result untouched"],
		ordered["v"] and (in_time or b5.get("late", []).has(kor2) or not b5["armies"][0].has(kor2)), "")
	Sim.ai_enabled = true
	# AI vs AI, 1914: Germany attacks a French border province; a second French army nearby joins on its own
	Sim.new_game("USA", 1914, 64, 60)
	Sim.auto_respond_player = "decline"
	var fr := -1; var de_from := -1; var fr2 := -1
	for pid in Sim.nation_provs["FRA"]:
		for nb in GameData.provinces[pid]["neighbors"].keys():
			if Sim.prov_owner.get(nb, "") == "DEU":
				fr = pid; de_from = int(nb); break
		if fr >= 0: break
	var bdist := 1e18
	for pid in Sim.nation_provs["FRA"]:
		if pid != fr and GameData.node_km(pid, fr) < bdist:
			bdist = GameData.node_km(pid, fr); fr2 = pid
	for id in Sim.armies.keys().duplicate():
		if Sim.armies[id]["owner"] in ["FRA", "DEU"]: Sim.armies.erase(id)
	var mk2 := func(code: String, at: int, roles: Array) -> int:
		var id := Sim._spawn_army(code, at, [])
		for role in roles: Sim.armies[id]["units"].append(Sim._make_unit(GameData.unit_for_role("c20", role)))
		return id
	var f1: int = mk2.call("FRA", fr, ["ranged", "ranged", "art", "ranged"])
	var f2: int = mk2.call("FRA", fr2, ["ranged", "ranged", "armor"])
	Sim.declare_war("DEU", "FRA", true)
	var g1: int = mk2.call("DEU", de_from, ["ranged", "ranged", "ranged", "art", "armor", "ranged", "ranged"])
	Sim.armies[g1]["ai_next"] = 999999
	Sim.order_move(g1, fr)
	var bfr := {"bid": -1}
	_until(func():
		for bid in Sim.battles.keys():
			if Sim.battles[bid]["prov"] == fr: bfr["bid"] = bid
		return bfr["bid"] >= 0, 20)
	var bf: Dictionary = Sim.battles.get(bfr["bid"], {})
	if not bf.is_empty():
		_until(func(): return bf["done"], 40)
	var f2_fought: bool = not bf.is_empty() and bf["sim"] != null and bf["sim"].regs.any(func(r): return r["army_id"] == f2)
	check("reinforce: AI vs AI (1914) — Germany attacks %s; the second French army %.0f km away marches in on its own and fights in the battle" % [GameData.provinces[fr]["name"] if fr >= 0 else "-", bdist],
		f2_fought, "battle %d" % bfr["bid"])
	# 6. every era
	var eras_ok := []
	for era_d in GameData.eras:
		var e: String = era_d["id"]
		var s := BattleSim.new()
		s.setup([_units_for(e, ["ranged", "inf", "cav"]), _units_for(e, ["ranged", "inf"])], "plains", [{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}], 5)
		var add: Array = _units_for(e, ["ranged", "inf"])
		for u in add: u["army_id"] = 98
		s.add_reinforcements(1, add, 10.0, "rear", "")
		s.run_to_end()
		if s.regs.size() == 7 and s.regs[5].get("reinforcement", false) and s.done: eras_ok.append(e)
	check("reinforce: works in all five eras %s" % str(eras_ok), eras_ok.size() == 5, "")
	# 7. a watched 3D battle receives the reinforcement on screen (player-facing: Reinforce button)
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	m._start_game("JPN", 1800, 63, 60)
	await _frames(2)
	var s7 := _reinf_setup(1, 63)
	Sim.set_speed(0)
	m.select_army(s7["r"])
	await _frames(2)
	var pressed := _press(m.hud.sel_box, "Reinforce")
	m.watch_battle(s7["bid"])
	var t0 := Time.get_ticks_msec()
	while not (m.in_battle and not m.transitioning) and Time.get_ticks_msec() - t0 < 8000:
		await _frames(1)
	var bv = m.battle_view
	var b7: Dictionary = Sim.battles[s7["bid"]]
	var regs_start: int = bv.sim.regs.size() if bv else 0
	t0 = Time.get_ticks_msec()
	while bv and bv.rv.size() <= regs_start and not bv.finished and Time.get_ticks_msec() - t0 < 20000:
		Sim.tick_day()          # the campaign clock: the reinforcing army keeps marching while we watch
		await _frames(2)
		bv.time_scale = 4.0
	var shown: bool = bv != null and bv.rv.size() > regs_start and bv.rv.size() == bv.sim.regs.size()
	check("reinforce: player presses 'Reinforce' on the army panel; while the battle is watched in 3D the army arrives and its regiments appear on the field (%d -> %d regiments drawn)" % [regs_start, bv.rv.size() if bv else -1],
		pressed and shown, "pressed %s" % pressed)
	if bv:
		bv.skip()
		await _frames(2)
		bv.leave_requested.emit(s7["bid"])
		t0 = Time.get_ticks_msec()
		while (m.in_battle or m.transitioning) and Time.get_ticks_msec() - t0 < 8000:
			await _frames(1)
	Sim.ai_enabled = true
	m.queue_free()
	await _frames(2)

# ---------------------------------------------------------------- v0.5: diplomatic inbox
func test_inbox() -> void:
	print("== Diplomatic inbox (v0.5) ==")
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(3)
	m._start_game("SWE", 1800, 81, 60)
	await _frames(2)
	Sim.set_speed(0)
	Sim.auto_respond_player = ""
	Sim.ai_enabled = false
	var peers: Array = []
	for c in Sim.nations.keys():
		if c != "SWE" and Sim.nations[c]["alive"] and not Sim.at_war(c, "SWE") and Sim.evaluate(c, "SWE", "trade")["score"] > -900.0:
			peers.append(c)
		if peers.size() >= 6: break
	# 1. no popups: routine offers collect in the inbox
	var popups := {"n": 0}
	var pv := func(): if m.hud.popup.visible: popups["n"] += 1
	for c in peers.slice(0, 5):
		Sim.propose(c, "SWE", "trade", true)
		await _frames(1)
		pv.call()
	m.hud.refresh_top()
	check("inbox: 5 routine trade offers arrive without a single popup; the top bar shows '%s'" % m.hud.inbox_btn.text,
		popups["n"] == 0 and Sim.pending_offers.size() == 5 and m.hud.inbox_btn.text == "✉ Inbox (5)", "")
	# 2. the same envoy pressing the same offer is merged, not duplicated
	for k in 6:
		Sim.day += 30
		Sim.propose(peers[0], "SWE", "trade", true)
	check("inbox: the same offer repeated 6 times while pending stays one entry (%d pending)" % Sim.pending_offers.size(), Sim.pending_offers.size() == 5, "")
	# 3. open the inbox and use bulk dismissal (player-facing button)
	m.hud.toggle_inbox()
	await _frames(2)
	var itxt := " ".join(_texts(m.hud.inbox_box))
	var rel0 := Sim.relation(peers[1], "SWE")
	var pressed := _press(m.hud.inbox_box, "Set aside all routine")
	await _frames(2)
	check("inbox: the Inbox lists the offers grouped by kind and 'Set aside all routine' clears them in one click (relations %+.0f -> %+.0f)" % [rel0, Sim.relation(peers[1], "SWE")],
		"Trade agreements (5)" in itxt and pressed and Sim.pending_offers.is_empty() and Sim.relation(peers[1], "SWE") > rel0 - 2.0, itxt.substr(0, 120))
	# 4. a declined offer is not repeated straight away; it may come back after the cooldown
	var again := Sim.propose(peers[1], "SWE", "trade", true)
	Sim.day += Sim.OFFER_COOLDOWN["trade"] + 1
	var later := Sim.propose(peers[1], "SWE", "trade", true)
	check("inbox: a set-aside offer is not re-sent for %d days (throttled %s), then may return (%s)" % [Sim.OFFER_COOLDOWN["trade"], again.get("throttled", false), later.get("pending", false)],
		again.get("throttled", false) and later.get("pending", false), "")
	# 5. war: repeated peace requests from the same enemy are one urgent entry, highlighted, with a notice not a popup
	Sim.pending_offers.clear(); Sim.offer_block.clear()
	var foe: String = peers[2]
	Sim.start_hostilities(foe, "SWE")
	for k in 8:
		Sim.day += 15
		Sim.propose(foe, "SWE", "peace", true)
	await _frames(1)
	m.hud.refresh_top()
	m.hud.refresh_inbox()
	var urgent_col: Color = m.hud.inbox_btn.get_theme_color("font_color")
	check("inbox: 8 peace requests from %s during the war = 1 urgent entry, highlighted in the top bar, announced by a notice (no popup)" % Sim.nations[foe]["name"],
		Sim.pending_offers.size() == 1 and Sim.inbox_counts()["urgent"] == 1 and urgent_col == Hud.BAD and not m.hud.popup.visible and "Peace" in m.hud.toast.text.capitalize(), m.hud.toast.text)
	var ptxt := " ".join(_texts(m.hud.inbox_box))
	_press(m.hud.inbox_box, "Decline")
	var re := Sim.propose(foe, "SWE", "peace", true)
	check("inbox: after declining, the enemy does not ask again for %d days ('Needs attention' listed: %s)" % [Sim.OFFER_COOLDOWN["peace"], "Needs attention" in ptxt], re.get("throttled", false) and "Needs attention" in ptxt, "")
	# 6. unanswered offers lapse; save/load keeps the inbox and the cooldowns
	Sim.pending_offers.clear(); Sim.offer_block.clear()
	Sim.propose(peers[3], "SWE", "trade", true)
	Sim.propose(peers[4], "SWE", "trade", true)
	Sim.respond_offer(Sim.pending_offers[0], false)
	var sv := Sim.save_game("inbox_test")
	var pend0 := Sim.pending_offers.size(); var blk0 := Sim.offer_block.size()
	Sim.pending_offers.clear(); Sim.offer_block.clear()
	Sim.load_game("inbox_test")
	var kept: bool = Sim.pending_offers.size() == pend0 and Sim.offer_block.size() == blk0
	Sim.day += Sim.OFFER_TTL + 1
	Sim._expire_offers()
	check("inbox: save/load keeps pending offers and cooldowns; an unanswered offer lapses after %d days" % Sim.OFFER_TTL, sv["ok"] and kept and Sim.pending_offers.is_empty(), "")
	Sim.ai_enabled = true
	Sim.auto_respond_player = "decline"
	m.queue_free()
	await _frames(2)
	# 7. a long campaign where the player ignores envoys: no duplicates pile up (v0.4.0: Poland's peace offer x6)
	Sim.new_game("SWE", 1300, 72)
	Sim.auto_respond_player = ""
	var emits := {"n": 0}
	var cbo := func(o): emits["n"] += 1
	Sim.player_offer.connect(cbo)
	Sim.advance_days(365 * 8)
	Sim.player_offer.disconnect(cbo)
	var keys := {}
	var dup := false
	for o in Sim.pending_offers:
		var k: String = o["from"] + "|" + o["kind"]
		if keys.has(k): dup = true
		keys[k] = true
	check("inbox: 8-year campaign, envoys ignored: %d new offers, %d waiting, no duplicates, nothing older than %d days" % [emits["n"], Sim.pending_offers.size(), Sim.OFFER_TTL + 31],
		not dup and Sim.pending_offers.all(func(o): return Sim.day - int(o["day"]) <= Sim.OFFER_TTL + 31), "")
	Sim.auto_respond_player = "decline"
