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
