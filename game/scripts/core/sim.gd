extends Node
## Strategic simulation: calendar, economy, diplomacy, AI, armies, sieges, battles, eras.
## Runs on a fixed daily tick. Monthly: economy, AI recruitment and diplomacy.

signal game_started
signal day_passed(day: int)
signal month_passed
signal ownership_changed(pid: int, old_owner: String, new_owner: String)
signal event_logged(ev: Dictionary)
signal battle_started(bid: int)
signal battle_resolved(bid: int, result: Dictionary)
signal era_changed(era_idx: int)
signal armies_changed
signal player_offer(offer: Dictionary)
signal speed_changed(idx: int)
signal player_defeated(by: String)
signal hostilities_started(a: String, b: String, declared: bool)
signal invasion_warning(w: Dictionary)

const SPEEDS := [0.0, 2.0, 8.0, 30.0, 120.0, 365.0]
const SPEED_NAMES := ["Paused", "Slow", "Normal", "Fast", "Very fast", "Year/sec"]
const MONTH_DAYS := [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
const MONTH_NAMES := ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
const BATTLE_SECONDS_PER_DAY := 15.0
const WATCH_DAYS_PER_SEC := 1.0
const FOOD_RES := ["grain", "fish", "horses"]
const POP_CURVE := [[1300.0, 0.06], [1500.0, 0.09], [1800.0, 0.2], [1914.0, 0.42], [1980.0, 0.8], [2030.0, 1.0]]

var running := false
var speed_idx := 2
var day := 0
var start_year := 1800
var start_doy := 0
var era := 0
var player := ""
var nations := {}
var prov_owner := {}
var nation_provs := {}
var sieges := {}           # pid -> {by, army, progress}
var armies := {}
var next_army_id := 1
var battles := {}
var next_battle_id := 1
var relations := {}
var treaties := {}
var wars := {}
var event_log: Array = []
var rng := RandomNumberGenerator.new()
var slow_during_watch := true
var watching_battle := -1
var accum := 0.0
var stats := {}
var pending_offers: Array = []
var auto_respond_player := ""     # "", "accept", "decline" (tests / unattended runs)
var auto_deploy := false          # player battles start immediately with default orders (tests)
var ai_enabled := true
var _port_reach := {}             # era -> {pid: [{to, cost, path}]}
var _neighbors_cache := {}
var _path_cache := {}
var defeated := false             # the player's campaign is over (no land and no viable army)
var spotted := {}                 # army id -> province it was reported heading for (player warnings; saved)
var _seen_by_player := {}         # army id -> detected today (derived each day; not saved)
var _cores := {}                  # code -> [pid] provinces the nation held at the start (recapture targets; derived, not saved)
const VIABLE_ARMY_MEN := 150.0    # a landless nation fights on while it has an army at least this large

# ======================= setup =======================
func new_game(player_code: String, year: int, seed: int = 1, doy: int = 0) -> void:
	GameData.load_all()
	rng.seed = seed
	player = player_code
	start_year = year
	start_doy = doy
	day = 0
	era = GameData.era_for_year(year + doy / 365.0)
	nations.clear(); prov_owner.clear(); nation_provs.clear(); sieges.clear(); armies.clear(); battles.clear()
	relations.clear(); treaties.clear(); wars.clear(); event_log.clear(); pending_offers.clear()
	_port_reach.clear(); _neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
	next_army_id = 1; next_battle_id = 1; watching_battle = -1; accum = 0.0
	defeated = false; _cores.clear(); _reach_cache.clear(); spotted.clear(); _seen_by_player.clear()
	stats = {"wars_declared": 0, "ai_wars": 0, "peace": 0, "ai_peace": 0, "alliances": 0, "ai_alliances": 0, "trades": 0,
		"ai_trades": 0, "naps": 0, "ai_naps": 0, "gifts": 0, "captures": 0, "battles": 0, "eliminated": 0, "era_changes": 0,
		"ai_units_bought": 0, "ai_proposals": 0, "ai_rejections": 0, "invasions": 0, "undeclared": 0, "recaptures": 0}
	for code in GameData.countries.keys():
		var c: Dictionary = GameData.countries[code]
		var major := GameData.majors.has(code)
		var md: Dictionary = GameData.majors.get(code, {})
		nations[code] = {"code": code, "name": c["name"], "major": major, "ai": code != player, "color": GameData.nation_color(code),
			"funds": 0.0, "manpower": 0.0, "stability": 0.7, "tax": 1, "welfare": 0.5, "stock": {}, "capital": int(c["capital"]),
			"alive": true, "aggression": float(md.get("aggression", 0.0)), "diplomacy": float(md.get("diplomacy", 0.3)),
			"income": {}, "expense": {}, "needs": {"food": 0.6, "goods": 0.6, "security": 0.6}, "exhaustion": 0.0,
			"net": 0.0, "flag": md.get("flag", []), "continent": c["continent"]}
		nation_provs[code] = []
		for r in GameData.resources:
			nations[code]["stock"][r] = 5.0
	for pid in GameData.province_ids:
		var o: String = GameData.provinces[pid]["owner"]
		if not nations.has(o):
			continue
		prov_owner[pid] = o
		nation_provs[o].append(pid)
	for code in nations.keys():
		if nation_provs[code].is_empty():
			nations[code]["alive"] = false
		elif not nation_provs[code].has(nations[code]["capital"]):
			nations[code]["capital"] = nation_provs[code][0]
	_init_relations()
	for code in nations.keys():
		if not nations[code]["alive"]:
			continue
		_economy_month(code, true)
		var n: Dictionary = nations[code]
		n["funds"] = n["income"].get("total", 50.0) * (5.0 if n["major"] else 3.0)
		n["manpower"] = _pop_total(code) * 0.004
	for code in nations.keys():
		if nations[code]["alive"]:
			_initial_armies(code)
	running = true
	log_event("%s begins in %s, %d. The %s." % [nations[player]["name"] if nations.has(player) else player, date_string(), year, GameData.eras[era]["name"]], "info", [player])
	game_started.emit()

func _init_relations() -> void:
	var codes: Array = nations.keys()
	for a in codes:
		for b in codes:
			if a >= b:
				continue
			var base := rng.randf_range(-15.0, 20.0)
			if _shares_border(a, b):
				base -= 8.0
			relations[_key(a, b)] = base

func _initial_armies(code: String) -> void:
	var n: Dictionary = nations[code]
	var era_id: String = GameData.eras[era]["id"]
	var inc: float = n["income"].get("total", 30.0)
	var avg_up := 0.0
	for uid in GameData.units_by_era[era_id]:
		avg_up += float(GameData.units[uid]["upkeep"])
	avg_up /= GameData.units_by_era[era_id].size()
	var count := clampi(int(round(inc * (0.32 if n["major"] else 0.18) / avg_up)), 2, 16)
	var nprov: int = nation_provs[code].size()
	var n_armies := 1 if not n["major"] else clampi(nprov / 6, 1, 4)
	if code == player:
		n_armies = clampi(n_armies, 1, 3)
	var roles := ["ranged", "inf", "ranged", "cav", "art", "inf", "armor", "ranged", "cav", "art"]
	var provs: Array = nation_provs[code].duplicate()
	provs.sort_custom(func(x, y): return GameData.provinces[x]["population"] > GameData.provinces[y]["population"])
	for ai in n_armies:
		var pid: int = n["capital"] if ai == 0 else provs[mini(ai * 2, provs.size() - 1)]
		var units: Array = []
		for k in range(ai, count, n_armies):
			var uid := GameData.unit_for_role(era_id, roles[k % roles.size()])
			units.append(_make_unit(uid))
		if units.is_empty():
			units.append(_make_unit(GameData.unit_for_role(era_id, "ranged")))
		_spawn_army(code, pid, units)

func _make_unit(uid: String) -> Dictionary:
	var d: Dictionary = GameData.units[uid]
	return {"type": uid, "men": float(d["men"]), "max": float(d["men"]), "era": d["era"]}

func _spawn_army(code: String, pid: int, units: Array) -> int:
	var id := next_army_id
	next_army_id += 1
	armies[id] = {"id": id, "owner": code, "node": pid, "path": [], "progress": 0.0, "units": units, "state": "idle",
		"battle": -1, "ai_next": day + rng.randi_range(0, 6), "goal": -1, "invade": "", "resume": false, "name": _army_name(code)}
	armies_changed.emit()
	return id

func _army_name(code: String) -> String:
	var k := 0
	for a in armies.values():
		if a["owner"] == code:
			k += 1
	var ord := ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"]
	return "%s Army" % (ord[k] if k < ord.size() else str(k + 1) + "th")

# ======================= calendar =======================
func cur_year_f() -> float:
	return start_year + (start_doy + day) / 365.0

func date_parts() -> Array:
	var total := start_doy + day
	var y := start_year + total / 365
	var d := total % 365
	var m := 0
	while d >= MONTH_DAYS[m]:
		d -= MONTH_DAYS[m]; m += 1
	return [y, m, d + 1]

func date_string() -> String:
	var p := date_parts()
	return "%d %s %d" % [p[2], MONTH_NAMES[p[1]], p[0]]

var perf_tick_us := 0      # CPU time spent in campaign ticks this frame (not saved)
var perf_days := 0

func _process(delta: float) -> void:
	perf_tick_us = 0; perf_days = 0
	if not running or speed_idx == 0 or _awaiting_deploy():
		return
	var t0 := Time.get_ticks_usec()
	var spd: float = SPEEDS[speed_idx]
	if watching_battle >= 0 and slow_during_watch:
		spd = minf(spd, WATCH_DAYS_PER_SEC)
	accum += delta * spd
	var n := 0
	while accum >= 1.0 and n < 24:
		accum -= 1.0
		tick_day()
		n += 1
	perf_days = n
	perf_tick_us = Time.get_ticks_usec() - t0

func set_speed(i: int) -> void:
	speed_idx = clampi(i, 0, SPEEDS.size() - 1)
	speed_changed.emit(speed_idx)

func advance_days(n: int) -> void:
	for i in n:
		tick_day()

func _awaiting_deploy() -> bool:
	for b in battles.values():
		if b["awaiting"]:
			return true
	return false

func tick_day() -> void:
	day += 1
	var p := date_parts()
	_era_check()
	_move_armies()
	_step_battles()
	_step_sieges()
	if ai_enabled:
		_ai_military_daily()
	_scan_detection()
	if p[2] == 1:
		_month()
	day_passed.emit(day)

func _era_check() -> void:
	var e := GameData.era_for_year(cur_year_f())
	if e > era:
		era = e
		stats["era_changes"] += 1
		_port_reach.clear(); _neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
		log_event("A new era dawns: the %s. New equipment can be procured; existing armies keep their old kit until refitted." % GameData.eras[era]["name"], "era", [])
		era_changed.emit(era)

# ======================= economy =======================
func pop_factor(y: float = -1.0) -> float:
	if y < 0:
		y = cur_year_f()
	for i in range(1, POP_CURVE.size()):
		if y <= POP_CURVE[i][0]:
			var a: Array = POP_CURVE[i - 1]; var b: Array = POP_CURVE[i]
			return lerpf(a[1], b[1], clampf((y - a[0]) / (b[0] - a[0]), 0.0, 1.0))
	return 1.0

func prov_pop(pid: int) -> float:
	return float(GameData.provinces[pid]["population"]) * pop_factor()

func _pop_total(code: String) -> float:
	var s := 0.0
	for pid in nation_provs[code]:
		s += prov_pop(pid)
	return s

func productivity() -> float:
	return float(GameData.eras[era]["productivity"])

func army_upkeep(a: Dictionary) -> float:
	var s := 0.0
	for u in a["units"]:
		s += float(GameData.units[u["type"]]["upkeep"]) * (0.4 + 0.6 * u["men"] / u["max"])
	return s

func _economy_month(code: String, preview: bool = false, ctx: Dictionary = {}) -> void:
	var n: Dictionary = nations[code]
	var provs: Array = nation_provs[code]
	var prod := productivity()
	var tax_mult: float = [0.75, 1.0, 1.3][n["tax"]]
	var stab_mult: float = 0.55 + 0.45 * n["stability"]
	var tax := 0.0
	var food := 0; var produced := {}
	for pid in provs:
		var pm := prov_pop(pid) / 1.0e6
		tax += (3.0 + 2.6 * pow(maxf(pm, 0.01), 0.6)) * prod
		var r: String = GameData.provinces[pid]["resource"]
		produced[r] = produced.get(r, 0) + 1
		if r in FOOD_RES:
			food += 1
	if sieges.size() > 0:
		for pid in provs:
			if sieges.has(pid):
				tax -= (3.0 + 2.6 * pow(maxf(prov_pop(pid) / 1.0e6, 0.01), 0.6)) * prod * 0.8
	tax *= tax_mult * stab_mult
	var trade_partners := 0
	if ctx.has("trade"):
		trade_partners = ctx["trade"].get(code, 0)
	else:
		for other in nations.keys():
			if other != code and has_treaty(code, other, "trade"):
				trade_partners += 1
	var trade_bonus := tax * 0.06 * trade_partners
	# resource production; surplus above the strategic reserve is sold automatically
	var sales := 0.0
	if not preview:
		for r in produced.keys():
			n["stock"][r] = n["stock"].get(r, 0.0) + produced[r]
		for r in n["stock"].keys():
			if n["stock"][r] > 25.0:
				var extra: float = n["stock"][r] - 25.0
				sales += extra * GameData.resource_price * prod * 0.6
				n["stock"][r] = 25.0
	else:
		for r in produced.keys():
			sales += produced[r] * GameData.resource_price * prod * 0.3
	var upkeep := 0.0
	var army_men := 0.0
	if ctx.has("upkeep"):
		upkeep = ctx["upkeep"].get(code, 0.0)
		army_men = ctx["men"].get(code, 0.0)
	else:
		for a in armies.values():
			if a["owner"] == code:
				upkeep += army_upkeep(a)
				for u in a["units"]:
					army_men += u["men"]
	var admin := 0.45 * pow(float(provs.size()), 1.12) * prod
	var welfare: float = n["welfare"] * 0.25 * tax
	var interest: float = maxf(-n["funds"], 0.0) * 0.02
	var income_total := tax + trade_bonus + sales
	var expense_total := upkeep + admin + welfare + interest
	n["income"] = {"Taxes": tax, "Trade agreements": trade_bonus, "Resource exports": sales, "total": income_total}
	n["expense"] = {"Army upkeep": upkeep, "Administration": admin, "Citizens' welfare": welfare, "Debt interest": interest, "total": expense_total}
	n["net"] = income_total - expense_total
	if preview:
		return
	n["funds"] += n["net"]
	# citizens' needs -> stability (domestic life is automatic)
	var np := maxf(provs.size(), 1)
	var need_food := clampf(0.35 + float(food) / np * 1.1 + n["welfare"] * 0.35, 0.0, 1.0)
	var need_goods := clampf(0.3 + 0.12 * trade_partners + n["welfare"] * 0.3 + (0.15 if n["funds"] > 0 else -0.1), 0.0, 1.0)
	var garrison_need := np * 600.0 * (0.5 + pop_factor())
	var need_sec := clampf(0.3 + 0.5 * army_men / garrison_need - n["exhaustion"] * 0.4 - 0.1 * (ctx["inside"].get(code, 0) if ctx.has("inside") else _enemy_armies_inside(code)), 0.0, 1.0)
	n["needs"] = {"food": need_food, "goods": need_goods, "security": need_sec}
	var target = 0.25 * (need_food + need_goods + need_sec) + 0.25 - [0.0, 0.05, 0.15][n["tax"]] - n["exhaustion"] * 0.3 - (0.2 if n["funds"] < 0 else 0.0)
	n["stability"] = clampf(n["stability"] + (target - n["stability"]) * 0.15, 0.05, 1.0)
	var pop := _pop_total(code)
	n["manpower"] = minf(n["manpower"] + pop * 0.00004, maxf(pop * 0.012, 2000.0))
	if at_war_any(code):
		n["exhaustion"] = minf(n["exhaustion"] + 0.01, 1.0)
	else:
		n["exhaustion"] = maxf(n["exhaustion"] - 0.03, 0.0)
	if n["funds"] < -income_total * 2.0:
		for a in armies.values():
			if a["owner"] == code:
				for u in a["units"]:
					u["men"] *= 0.95
		if code == player:
			log_event("Treasury in deep debt: unpaid soldiers are deserting.", "economy", [code])

# perf: per-month tables so _economy_month doesn't rescan every army/nation for each of ~190 nations.
# Built in the same iteration order as the per-nation loops (identical float sums). Valid for the whole
# economy pass: it only changes a nation's own armies (desertion) after that nation's figures are read.
func _economy_ctx() -> Dictionary:
	var upkeep := {}; var men := {}; var inside := {}; var trade := {}
	for a in armies.values():
		var o: String = a["owner"]
		upkeep[o] = upkeep.get(o, 0.0) + army_upkeep(a)
		var m: float = men.get(o, 0.0)
		for u in a["units"]:
			m += u["men"]
		men[o] = m
		if a["node"] < GameData.SEA_NODE:
			var po: String = prov_owner.get(a["node"], "")
			if po != "" and at_war(o, po):
				inside[po] = inside.get(po, 0) + 1
	for k in treaties.keys():
		if treaties[k].get("trade", false):
			var p: PackedStringArray = k.split("|")
			if p[0] != p[1] and nations.has(p[0]) and nations.has(p[1]):
				trade[p[0]] = trade.get(p[0], 0) + 1
				trade[p[1]] = trade.get(p[1], 0) + 1
	return {"upkeep": upkeep, "men": men, "inside": inside, "trade": trade}

func _enemy_armies_inside(code: String) -> int:
	var k := 0
	for a in armies.values():
		if a["node"] < GameData.SEA_NODE and prov_owner.get(a["node"], "") == code and at_war(a["owner"], code):
			k += 1
	return k

func strength(code: String) -> float:
	var s := 0.0
	for a in armies.values():
		if a["owner"] == code:
			s += army_strength(a)
	return s

func _strength_table() -> Dictionary:
	var out := {}
	for a in armies.values():
		out[a["owner"]] = out.get(a["owner"], 0.0) + army_strength(a)
	return out

func _alliance_table() -> Dictionary:
	var out := {}
	for k in treaties.keys():
		if treaties[k].get("alliance", false):
			var p: PackedStringArray = k.split("|")
			if not out.has(p[0]): out[p[0]] = []
			if not out.has(p[1]): out[p[1]] = []
			out[p[0]].append(p[1]); out[p[1]].append(p[0])
	return out

func army_strength(a: Dictionary) -> float:
	var s := 0.0
	for u in a["units"]:
		s += u["men"] * unit_power(u["type"])
	return s

var _upow := {}   # perf: unit_power memo (unit stats are static data)
func unit_power(uid: String) -> float:
	var c = _upow.get(uid)
	if c != null:
		return c
	var d: Dictionary = GameData.units[uid]
	c = (float(d["melee"]) + float(d["defense"])) * 0.5 + float(d["lethality"]) * float(d["accuracy"]) * 40.0 + float(d["armor"]) * 25.0
	_upow[uid] = c
	return c

func army_men(a: Dictionary) -> float:
	var s := 0.0
	for u in a["units"]:
		s += u["men"]
	return s

# ======================= procurement =======================
func unit_cost(uid: String) -> float:
	return float(GameData.units[uid]["cost"])

func can_afford(code: String, uid: String) -> Dictionary:
	var n: Dictionary = nations[code]
	var d: Dictionary = GameData.units[uid]
	var cost := unit_cost(uid)
	var res_buy := 0.0
	for r in d["resources"].keys():
		var need := float(d["resources"][r])
		var have: float = n["stock"].get(r, 0.0)
		if have < need:
			res_buy += (need - have) * GameData.resource_price * productivity() * 1.5
	return {"ok": n["funds"] >= cost + res_buy and n["manpower"] >= float(d["men"]), "cost": cost, "res_buy": res_buy,
		"manpower_ok": n["manpower"] >= float(d["men"]), "funds_ok": n["funds"] >= cost + res_buy}

func buy_unit(code: String, uid: String, pid: int = -1) -> Dictionary:
	if not nations.has(code) or not GameData.units.has(uid):
		return {"ok": false, "msg": "invalid"}
	var d: Dictionary = GameData.units[uid]
	if d["era"] != GameData.eras[era]["id"]:
		return {"ok": false, "msg": "Only current-era equipment can be procured."}
	var n: Dictionary = nations[code]
	if pid < 0:
		pid = n["capital"]
	if prov_owner.get(pid, "") != code:
		return {"ok": false, "msg": "Units can only be raised in your own provinces."}
	if sieges.has(pid):
		return {"ok": false, "msg": "The province is under siege."}
	var c := can_afford(code, uid)
	if not c["ok"]:
		return {"ok": false, "msg": "Not enough funds" if not c["funds_ok"] else "Not enough manpower"}
	n["funds"] -= c["cost"] + c["res_buy"]
	for r in d["resources"].keys():
		n["stock"][r] = maxf(n["stock"].get(r, 0.0) - float(d["resources"][r]), 0.0)
	n["manpower"] -= float(d["men"])
	var target := -1
	for a in armies.values():
		if a["owner"] == code and a["node"] == pid and a["state"] == "idle" and a["units"].size() < 20:
			target = a["id"]
			break
	if target < 0:
		target = _spawn_army(code, pid, [_make_unit(uid)])
	else:
		armies[target]["units"].append(_make_unit(uid))
		armies_changed.emit()
	if code != player:
		stats["ai_units_bought"] += 1
	return {"ok": true, "army": target, "cost": c["cost"] + c["res_buy"]}

func refit_cost(a: Dictionary) -> float:
	var era_id: String = GameData.eras[era]["id"]
	var c := 0.0
	for u in a["units"]:
		if u["era"] != era_id:
			c += unit_cost(GameData.unit_for_role(era_id, GameData.units[u["type"]]["role"])) * 0.6
	return c

func refit_army(aid: int) -> Dictionary:
	if not armies.has(aid):
		return {"ok": false, "msg": "no army"}
	var a: Dictionary = armies[aid]
	var n: Dictionary = nations[a["owner"]]
	var cost := refit_cost(a)
	if cost <= 0.0:
		return {"ok": false, "msg": "Army already uses current-era equipment."}
	if n["funds"] < cost:
		return {"ok": false, "msg": "Not enough funds (%d needed)" % int(cost)}
	if a["state"] == "battle":
		return {"ok": false, "msg": "Army is in battle."}
	var era_id: String = GameData.eras[era]["id"]
	n["funds"] -= cost
	var changed := 0
	for i in a["units"].size():
		var u: Dictionary = a["units"][i]
		if u["era"] != era_id:
			var nu := GameData.unit_for_role(era_id, GameData.units[u["type"]]["role"])
			var frac: float = u["men"] / u["max"]
			var nd: Dictionary = GameData.units[nu]
			a["units"][i] = {"type": nu, "men": float(nd["men"]) * frac, "max": float(nd["men"]), "era": era_id}
			changed += 1
	armies_changed.emit()
	if a["owner"] == player:
		log_event("%s refitted %d units with %s equipment." % [a["name"], changed, GameData.eras[era]["name"]], "economy", [a["owner"]])
	return {"ok": true, "cost": cost, "changed": changed}

func disband_unit(aid: int, idx: int) -> void:
	if armies.has(aid) and idx < armies[aid]["units"].size():
		var a: Dictionary = armies[aid]
		nations[a["owner"]]["manpower"] += a["units"][idx]["men"] * 0.5
		a["units"].remove_at(idx)
		if a["units"].is_empty():
			armies.erase(aid)
		armies_changed.emit()

func merge_armies(into: int, other: int) -> bool:
	if not armies.has(into) or not armies.has(other) or into == other:
		return false
	var a: Dictionary = armies[into]; var b: Dictionary = armies[other]
	if a["node"] != b["node"] or a["owner"] != b["owner"] or a["state"] == "battle" or b["state"] == "battle":
		return false
	a["units"].append_array(b["units"])
	armies.erase(other)
	armies_changed.emit()
	return true

func set_tax(code: String, level: int) -> void:
	nations[code]["tax"] = clampi(level, 0, 2)
	_economy_month(code, true)

func set_welfare(code: String, w: float) -> void:
	nations[code]["welfare"] = clampf(w, 0.0, 1.0)
	_economy_month(code, true)

# ======================= diplomacy =======================
func _key(a: String, b: String) -> String:
	return a + "|" + b if a < b else b + "|" + a

func relation(a: String, b: String) -> float:
	return relations.get(_key(a, b), 0.0)

func add_relation(a: String, b: String, v: float) -> void:
	var k := _key(a, b)
	relations[k] = clampf(relations.get(k, 0.0) + v, -100.0, 100.0)

func has_treaty(a: String, b: String, t: String) -> bool:
	var tr: Dictionary = treaties.get(_key(a, b), {})
	if t == "nap" or t == "truce":
		return tr.get(t, -1) > day
	return tr.get(t, false)

func _set_treaty(a: String, b: String, t: String, v: Variant) -> void:
	var k := _key(a, b)
	if not treaties.has(k):
		treaties[k] = {}
	treaties[k][t] = v

func at_war(a: String, b: String) -> bool:
	return a != b and wars.has(_key(a, b))

func at_war_any(code: String) -> bool:
	for k in wars.keys():
		if k.begins_with(code + "|") or k.ends_with("|" + code):
			return true
	return false

func enemies_of(code: String) -> Array:
	var out: Array = []
	for k in wars.keys():
		var p: PackedStringArray = k.split("|")
		if p[0] == code:
			out.append(p[1])
		elif p[1] == code:
			out.append(p[0])
	return out

func allies_of(code: String) -> Array:
	var out: Array = []
	for k in treaties.keys():
		if treaties[k].get("alliance", false):
			var p: PackedStringArray = k.split("|")
			if p[0] == code:
				out.append(p[1])
			elif p[1] == code:
				out.append(p[0])
	return out

func is_friendly(a: String, b: String) -> bool:
	return a == b or has_treaty(a, b, "alliance")

## Hostilities exist between a and b but nobody has formally declared war (an undeclared invasion).
func is_undeclared(a: String, b: String) -> bool:
	var w: Dictionary = wars.get(_key(a, b), {})
	return not w.is_empty() and not w.get("declared", true)

func can_declare_war(a: String, b: String) -> Dictionary:
	if a == b or not nations.has(b) or not nations[b]["alive"]:
		return {"ok": false, "msg": "Invalid target"}
	if at_war(a, b):
		if is_undeclared(a, b):
			return {"ok": true, "msg": "", "upgrade": true}
		return {"ok": false, "msg": "Already at war"}
	if has_treaty(a, b, "alliance"):
		return {"ok": false, "msg": "You are allied; cancel the alliance first"}
	if has_treaty(a, b, "truce"):
		return {"ok": false, "msg": "A peace truce is in force"}
	return {"ok": true, "msg": ""}

func declare_war(a: String, b: String, by_ai: bool = false) -> bool:
	var chk := can_declare_war(a, b)
	if not chk["ok"]:
		return false
	if chk.get("upgrade", false):
		# an undeclared conflict becomes a formal war: the target's allies are now called to arms
		wars[_key(a, b)]["declared"] = true
		stats["wars_declared"] += 1
		if by_ai:
			stats["ai_wars"] += 1
		add_relation(a, b, -10.0)
		log_event("%s formally declares war on %s!" % [nations[a]["name"], nations[b]["name"]], "war", [a, b], by_ai)
		_call_allies(a, b)
		_neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
		hostilities_started.emit(a, b, true)
		return true
	var broke_nap := has_treaty(a, b, "nap")
	_start_war(a, b, true)
	stats["wars_declared"] += 1
	if by_ai:
		stats["ai_wars"] += 1
	add_relation(a, b, -45.0)
	_set_treaty(a, b, "trade", false)
	_set_treaty(a, b, "nap", -1)
	if broke_nap:
		nations[a]["stability"] = maxf(nations[a]["stability"] - 0.12, 0.05)
		for c in nations.keys():
			if c != a and nations[c]["major"]:
				add_relation(a, c, -6.0)
	log_event("%s declares war on %s!%s" % [nations[a]["name"], nations[b]["name"], " (breaking a non-aggression pact)" if broke_nap else ""], "war", [a, b], by_ai)
	_call_allies(a, b)
	_neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
	hostilities_started.emit(a, b, true)
	return true

## Defensive alliances: the target's allies are called to arms (formal declarations only).
func _call_allies(a: String, b: String) -> void:
	for c in allies_of(b):
		if c != a and not at_war(c, a) and not has_treaty(c, a, "alliance") and nations[c]["alive"]:
			_start_war(c, a, true)
			add_relation(c, a, -30.0)
			log_event("%s honours its alliance with %s and joins the war against %s." % [nations[c]["name"], nations[b]["name"], nations[a]["name"]], "war", [c, a, b], c != player)

func _start_war(a: String, b: String, declared: bool = true) -> void:
	wars[_key(a, b)] = {"start": day, "attacker": a, "score": {a: 0.0, b: 0.0}, "declared": declared}

## Whether `a` may attack `b` without a declaration. Alliances and peace truces still bind.
func can_invade(a: String, b: String) -> Dictionary:
	if a == b or not nations.has(b) or not nations[b]["alive"]:
		return {"ok": false, "msg": "Invalid target"}
	if at_war(a, b):
		return {"ok": true, "msg": "", "hostile": true}
	if has_treaty(a, b, "alliance"):
		return {"ok": false, "msg": "%s is our ally; cancel the alliance first" % nations[b]["name"]}
	if has_treaty(a, b, "truce"):
		return {"ok": false, "msg": "A peace truce with %s is in force" % nations[b]["name"]}
	return {"ok": true, "msg": "", "hostile": false}

## Undeclared conflict: fighting starts when an army crosses the border, without a declaration.
## The victim can fight back at once (it is a war in every military sense), but its allies are not
## called in. Consequences: heavy relation loss with the victim, a smaller one with every major power,
## and breaking a non-aggression pact costs stability as a declaration would.
func start_hostilities(a: String, b: String, by_ai: bool = false) -> bool:
	if at_war(a, b):
		return true
	if not can_invade(a, b)["ok"]:
		return false
	var broke_nap := has_treaty(a, b, "nap")
	_start_war(a, b, false)
	stats["undeclared"] += 1
	add_relation(a, b, -55.0)
	_set_treaty(a, b, "trade", false)
	_set_treaty(a, b, "nap", -1)
	if broke_nap:
		nations[a]["stability"] = maxf(nations[a]["stability"] - 0.12, 0.05)
	for c in nations.keys():
		if c != a and c != b and nations[c]["major"] and nations[c]["alive"]:
			add_relation(a, c, -4.0)
	log_event("%s invades %s without a declaration of war!%s" % [nations[a]["name"], nations[b]["name"], " (breaking a non-aggression pact)" if broke_nap else ""], "war", [a, b], by_ai)
	_neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
	hostilities_started.emit(a, b, false)
	return true

func make_peace(a: String, b: String, by_ai: bool = false) -> void:
	var k := _key(a, b)
	if not wars.has(k):
		return
	wars.erase(k)
	_set_treaty(a, b, "truce", day + 365 * 5)
	nations[a]["last_peace"] = day
	nations[b]["last_peace"] = day
	stats["peace"] += 1
	if by_ai:
		stats["ai_peace"] += 1
	for pid in sieges.keys().duplicate():
		var s: Dictionary = sieges[pid]
		if (s["by"] == a and prov_owner[pid] == b) or (s["by"] == b and prov_owner[pid] == a):
			sieges.erase(pid)
	log_event("Peace between %s and %s. Current borders are recognised." % [nations[a]["name"], nations[b]["name"]], "peace", [a, b], by_ai)
	_path_cache.clear(); _reach_cache.clear()

func war_score(code: String, other: String) -> float:
	var w: Dictionary = wars.get(_key(code, other), {})
	if w.is_empty():
		return 0.0
	return float(w["score"].get(code, 0.0)) - float(w["score"].get(other, 0.0))

func _add_war_score(code: String, other: String, v: float) -> void:
	var w: Dictionary = wars.get(_key(code, other), {})
	if not w.is_empty():
		w["score"][code] = float(w["score"].get(code, 0.0)) + v

## Evaluate a proposal from `a` to `b`. Returns score (accept if > 0) and an itemised breakdown.
func evaluate(a: String, b: String, kind: String) -> Dictionary:
	var br: Array = []
	var rel := relation(a, b)
	var sa := strength(a) + 1.0; var sb := strength(b) + 1.0
	match kind:
		"trade":
			if at_war(a, b):
				return {"score": -999.0, "breakdown": [["We are at war", -999]]}
			if has_treaty(a, b, "trade"):
				return {"score": -999.0, "breakdown": [["Agreement already exists", -999]]}
			br.append(["Base interest in commerce", 12])
			br.append(["Our relations", int(rel * 0.4)])
			var ra := _resources_of(a); var rb := _resources_of(b)
			var comp := 0
			for r in ra:
				if not rb.has(r):
					comp += 1
			br.append(["Goods we lack (%d)" % comp, comp * 4])
			if nations[b]["funds"] < 0:
				br.append(["Our treasury needs income", 10])
			if at_war_any(a) and enemies_of(a).any(func(e): return has_treaty(b, e, "alliance")):
				br.append(["They fight our allies", -40])
		"alliance":
			if at_war(a, b):
				return {"score": -999.0, "breakdown": [["We are at war", -999]]}
			if has_treaty(a, b, "alliance"):
				return {"score": -999.0, "breakdown": [["Already allied", -999]]}
			br.append(["Reluctance to be dragged into wars", -25])
			br.append(["Our relations", int(rel * 0.6)])
			var common := 0
			for e in enemies_of(a):
				if at_war(b, e):
					common += 1
			if common > 0:
				br.append(["Common enemies", 30 * common])
			var threat := 0.0
			for c in neighbors_of(b):
				if c != a and nations[c]["major"] and relation(b, c) < -10:
					threat += 1.0
			br.append(["Hostile neighbours (%d)" % int(threat), int(threat * 8)])
			br.append(["Their military strength", int(clampf(sa / sb * 6.0, 0.0, 20.0))])
			if not enemies_of(a).is_empty() and common == 0:
				br.append(["They are at war with others", -25])
			var dist := GameData.km_between(GameData.node_lonlat(nations[a]["capital"]), GameData.node_lonlat(nations[b]["capital"]))
			br.append(["Distance between capitals", -int(clampf(dist / 600.0, 0.0, 20.0))])
		"nap":
			if at_war(a, b) or has_treaty(a, b, "nap"):
				return {"score": -999.0, "breakdown": [["Not applicable", -999]]}
			br.append(["Base", 5])
			br.append(["Our relations", int(rel * 0.4)])
			if sa > sb * 1.3:
				br.append(["They are stronger than us", 20])
			elif sb > sa * 1.5:
				br.append(["We may want their land", -int(nations[b]["aggression"] * 30.0)])
			if _shares_border(a, b):
				br.append(["Shared border security", 8])
		"peace":
			if not at_war(a, b):
				return {"score": -999.0, "breakdown": [["Not at war", -999]]}
			var ws := war_score(b, a)
			br.append(["War score", -int(clampf(ws, -60.0, 60.0))])
			br.append(["Our war exhaustion", int(nations[b]["exhaustion"] * 60.0)])
			var months := (day - int(wars[_key(a, b)]["start"])) / 30
			br.append(["Length of the war (%d months)" % months, mini(months, 30)])
			if sa > sb * 1.4:
				br.append(["Their army is stronger", 15])
			elif sb > sa * 1.4:
				br.append(["We hold the military advantage", -15])
			if not nations[b]["major"]:
				br.append(["We are a minor power", 15])
			br.append(["Base", -5])
	var score := 0.0
	for it in br:
		score += float(it[1])
	return {"score": score, "breakdown": br}

func _resources_of(code: String) -> Array:
	var out: Array = []
	for pid in nation_provs[code]:
		var r: String = GameData.provinces[pid]["resource"]
		if not out.has(r):
			out.append(r)
	return out

## Propose a treaty. AI targets decide immediately; offers to the player are queued.
func propose(a: String, b: String, kind: String, by_ai: bool = false) -> Dictionary:
	var ev := evaluate(a, b, kind)
	if by_ai:
		stats["ai_proposals"] += 1
	if b == player and nations[b]["ai"] == false:
		var offer := {"from": a, "to": b, "kind": kind, "day": day, "eval": ev}
		if auto_respond_player == "accept":
			_apply_treaty(a, b, kind, by_ai)
			return {"accepted": true, "eval": ev}
		elif auto_respond_player == "decline":
			add_relation(a, b, -3.0)
			return {"accepted": false, "eval": ev}
		pending_offers.append(offer)
		player_offer.emit(offer)
		return {"accepted": false, "pending": true, "eval": ev}
	var accepted: bool = ev["score"] > 0.0
	if accepted:
		_apply_treaty(a, b, kind, by_ai)
	else:
		add_relation(a, b, -1.0)
		if by_ai:
			stats["ai_rejections"] += 1
		if a == player:
			log_event("%s rejects our %s proposal." % [nations[b]["name"], _kind_name(kind)], "diplo", [a, b])
	return {"accepted": accepted, "eval": ev}

func respond_offer(offer: Dictionary, accept: bool) -> void:
	pending_offers.erase(offer)
	if accept:
		_apply_treaty(offer["from"], offer["to"], offer["kind"], true)
	else:
		add_relation(offer["from"], offer["to"], -4.0)
		log_event("We declined the %s offered by %s." % [_kind_name(offer["kind"]), nations[offer["from"]]["name"]], "diplo", [offer["from"], offer["to"]])

func _kind_name(kind: String) -> String:
	return {"trade": "trade agreement", "alliance": "defensive alliance", "nap": "non-aggression pact", "peace": "peace"}.get(kind, kind)

func _apply_treaty(a: String, b: String, kind: String, by_ai: bool) -> void:
	match kind:
		"trade":
			_set_treaty(a, b, "trade", true); add_relation(a, b, 8.0); stats["trades"] += 1
			if by_ai: stats["ai_trades"] += 1
			log_event("%s and %s sign a trade agreement." % [nations[a]["name"], nations[b]["name"]], "diplo", [a, b], by_ai)
		"alliance":
			_set_treaty(a, b, "alliance", true); add_relation(a, b, 15.0); stats["alliances"] += 1
			if by_ai: stats["ai_alliances"] += 1
			log_event("%s and %s form a defensive alliance." % [nations[a]["name"], nations[b]["name"]], "diplo", [a, b], by_ai)
		"nap":
			_set_treaty(a, b, "nap", day + 365 * 10); add_relation(a, b, 6.0); stats["naps"] += 1
			if by_ai: stats["ai_naps"] += 1
			log_event("%s and %s sign a ten-year non-aggression pact." % [nations[a]["name"], nations[b]["name"]], "diplo", [a, b], by_ai)
		"peace":
			make_peace(a, b, by_ai)
	_neighbors_cache.clear(); _reach_cache.clear()

func cancel_treaty(a: String, b: String, kind: String) -> void:
	if kind == "nap":
		_set_treaty(a, b, "nap", -1)
	else:
		_set_treaty(a, b, kind, false)
	add_relation(a, b, -15.0)
	_reach_cache.clear()
	log_event("%s cancels the %s with %s." % [nations[a]["name"], _kind_name(kind), nations[b]["name"]], "diplo", [a, b], a != player)

func gift(a: String, b: String, amount: float) -> bool:
	if nations[a]["funds"] < amount or amount <= 0.0:
		return false
	nations[a]["funds"] -= amount
	nations[b]["funds"] += amount
	var inc: float = maxf(nations[b]["income"].get("total", 50.0), 10.0)
	add_relation(a, b, clampf(amount / inc * 12.0, 1.0, 25.0))
	stats["gifts"] += 1
	log_event("%s sends a gift of %d to %s." % [nations[a]["name"], int(amount), nations[b]["name"]], "diplo", [a, b], a != player)
	return true

func _shares_border(a: String, b: String) -> bool:
	for pid in nation_provs.get(a, []):
		for nb in GameData.provinces[pid]["neighbors"].keys():
			if prov_owner.get(nb, "") == b:
				return true
	return false

## Nations reachable by land border or by sea within the current era's naval range.
func neighbors_of(code: String) -> Array:
	if _neighbors_cache.has(code):
		return _neighbors_cache[code]
	var out := {}
	var reach := _ports()
	for pid in nation_provs[code]:
		for nb in GameData.provinces[pid]["neighbors"].keys():
			var o: String = prov_owner.get(nb, "")
			if o != "" and o != code:
				out[o] = true
		for r in reach.get(pid, []):
			var o2: String = prov_owner.get(r["to"], "")
			if o2 != "" and o2 != code:
				out[o2] = true
	var arr := out.keys()
	_neighbors_cache[code] = arr
	return arr

# ======================= movement / pathfinding =======================
func _ports() -> Dictionary:
	if _port_reach.has(era):
		return _port_reach[era]
	var rng_hops := int(GameData.eras[era]["naval_range"])
	var reach := {}
	for pid in GameData.province_ids:
		var p: Dictionary = GameData.provinces[pid]
		if p["seazones"].is_empty():
			continue
		# BFS over sea zones
		var prev := {}
		var dist := {}
		var q: Array = []
		for z in p["seazones"]:
			dist[z] = 0; prev[z] = -1; q.append(z)
		var qi := 0
		while qi < q.size():
			var z: int = q[qi]; qi += 1
			if dist[z] >= rng_hops:
				continue
			for nz in GameData.seazones[z]["neighbors"]:
				if not dist.has(nz):
					dist[nz] = dist[z] + 1; prev[nz] = z; q.append(nz)
		var lst: Array = []
		var seen := {}
		for z in q:
			for port in GameData.seazones[z]["ports"]:
				if port == pid or seen.has(port):
					continue
				seen[port] = true
				var path: Array = []
				var c: int = z
				while c != -1:
					path.push_front(GameData.SEA_NODE + c)
					c = prev[c]
				var cost := 0.0
				var last = pid
				for nd in path:
					cost += GameData.node_km(last, nd); last = nd
				cost += GameData.node_km(last, port)
				lst.append({"to": port, "cost": cost * 0.8 + 150.0, "path": path})
		reach[pid] = lst
	_port_reach[era] = reach
	return reach

## Land an army of `code` may enter: own, allied, enemy (any hostilities), or `invading` (the nation an
## invasion order is aimed at; hostilities start when the army crosses into it). Neutral land stays closed.
func passable(code: String, pid: int, invading: String = "") -> bool:
	var o: String = prov_owner.get(pid, "")
	if o == "":
		return false
	return o == code or (invading != "" and o == invading) or has_treaty(code, o, "alliance") or at_war(code, o)

## Dijkstra over provinces (+ sea crossings). Returns node list excluding start, or [] if unreachable.
func find_path(code: String, from_node: int, to_pid: int, invading: String = "") -> Array:
	if from_node == to_pid:
		return []
	if not GameData.provinces.has(to_pid) or not passable(code, to_pid, invading):
		return []
	var start := from_node
	var extra_head: Array = []
	if from_node >= GameData.SEA_NODE:
		# at sea: snap to the closest port
		var z: Dictionary = GameData.seazones[from_node - GameData.SEA_NODE]
		var best := -1; var bd := 1e9
		for port in z["ports"]:
			var d := GameData.node_km(from_node, port)
			if d < bd and passable(code, port, invading):
				bd = d; best = port
		if best < 0:
			return []
		extra_head = [best]
		start = best
	var reach := _ports()
	var dist := {start: 0.0}
	var prev := {}
	var via := {}
	var heap := [[0.0, start]]
	while not heap.is_empty():
		var top: Array = _heap_pop(heap)
		var u: int = top[1]
		if top[0] > dist.get(u, 1e18):
			continue
		if u == to_pid:
			break
		var p: Dictionary = GameData.provinces[u]
		for nb in p["neighbors"].keys():
			if not passable(code, nb, invading):
				continue
			var nd: float = dist[u] + GameData.node_km(u, nb)
			if nd < dist.get(nb, 1e18):
				dist[nb] = nd; prev[nb] = u; via.erase(nb)
				_heap_push(heap, [nd, nb])
		for r in reach.get(u, []):
			var v: int = r["to"]
			if not passable(code, v, invading):
				continue
			var nd2: float = dist[u] + r["cost"]
			if nd2 < dist.get(v, 1e18):
				dist[v] = nd2; prev[v] = u; via[v] = r["path"]
				_heap_push(heap, [nd2, v])
	if not dist.has(to_pid):
		return []
	var out: Array = []
	var c := to_pid
	while c != start:
		out.push_front(c)
		if via.has(c):
			var sp: Array = via[c]
			for k in range(sp.size() - 1, -1, -1):
				out.push_front(sp[k])
		c = prev[c]
	return extra_head + out

func path_km(code: String, from_node: int, path: Array) -> float:
	var s := 0.0
	var last := from_node
	for n in path:
		s += GameData.node_km(last, n); last = n
	return s

func _heap_push(h: Array, item: Array) -> void:
	h.append(item)
	var i := h.size() - 1
	while i > 0:
		var p := (i - 1) / 2
		if h[p][0] <= h[i][0]:
			break
		var t = h[p]; h[p] = h[i]; h[i] = t
		i = p

func _heap_pop(h: Array) -> Array:
	var top: Array = h[0]
	var last: Array = h.pop_back()
	if h.size() > 0:
		h[0] = last
		var i := 0
		while true:
			var l := i * 2 + 1; var r := l + 1; var m := i
			if l < h.size() and h[l][0] < h[m][0]: m = l
			if r < h.size() and h[r][0] < h[m][0]: m = r
			if m == i: break
			var t = h[m]; h[m] = h[i]; h[i] = t
			i = m
	return top

func order_move(aid: int, to_pid: int) -> Dictionary:
	if not armies.has(aid):
		return {"ok": false, "msg": "No army"}
	var a: Dictionary = armies[aid]
	if a["state"] == "battle":
		return {"ok": false, "msg": "Army is fighting"}
	if to_pid == a["node"]:
		a["path"] = []; a["progress"] = 0.0
		return {"ok": true, "path": []}
	var path := find_path(a["owner"], a["node"], to_pid)
	if path.is_empty():
		var o: String = prov_owner.get(to_pid, "")
		if o != "" and not passable(a["owner"], to_pid):
			var inv := can_invade(a["owner"], o)
			if inv["ok"]:
				return {"ok": false, "needs_invade": true, "target": o,
					"msg": "%s is not at war with us. Use Invade to attack without a declaration, or declare war." % nations[o]["name"]}
			return {"ok": false, "msg": "Cannot enter %s territory: %s" % [nations[o]["name"], inv["msg"]]}
		return {"ok": false, "msg": _no_route_msg(a, to_pid, "")}
	a["path"] = path
	a["progress"] = 0.0
	a["goal"] = to_pid
	a["invade"] = ""
	a["resume"] = false
	if a["state"] == "siege":
		a["state"] = "idle"
	armies_changed.emit()
	return {"ok": true, "path": path, "days": est_days(a, path)}

## Travel-time estimate for a path (a leg that starts at sea moves 2.2x faster, as in _move_armies).
func est_days(a: Dictionary, path: Array) -> int:
	var land := 0.0; var sea := 0.0
	var last: int = a["node"]
	for n in path:
		var km := GameData.node_km(last, n)
		if last >= GameData.SEA_NODE:
			sea += km
		else:
			land += km
		last = n
	var sp := army_speed(a)
	return maxi(1, int(ceil((land + sea / 2.2) / sp)))

func _no_route_msg(a: Dictionary, to_pid: int, invading: String) -> String:
	var name: String = GameData.provinces[to_pid]["name"] if GameData.provinces.has(to_pid) else "there"
	var blockers := {}
	for nb in GameData.provinces[to_pid]["neighbors"].keys():
		var o: String = prov_owner.get(nb, "")
		if o != "" and not passable(a["owner"], nb, invading):
			blockers[nations[o]["name"]] = true
	var txt := "No route to %s: neutral territory blocks the land route and no port is within this era's naval range (%d sea zones)." % [name, int(GameData.eras[era]["naval_range"])]
	if not blockers.is_empty():
		txt += " Neutral neighbours in the way: %s." % ", ".join(blockers.keys().slice(0, 3))
	return txt

## Player/AI invasion order: march on `to_pid` (an enemy province, or one held by a nation we are at
## peace with). Starts at once along the existing land/sea path-finding; nothing is teleported.
## No declaration is needed: hostilities begin when the army crosses the target's border. Passing
## through third-party neutral land is still forbidden (alliance or war needed). With dry_run the
## route and ETA are reported without giving the order.
func order_invade(aid: int, to_pid: int, dry_run: bool = false) -> Dictionary:
	if not armies.has(aid):
		return {"ok": false, "msg": "No army"}
	var a: Dictionary = armies[aid]
	if a["state"] == "battle":
		return {"ok": false, "msg": "Army is fighting"}
	if not GameData.provinces.has(to_pid):
		return {"ok": false, "msg": "Not a land province"}
	var code: String = a["owner"]
	var o: String = prov_owner.get(to_pid, "")
	if o == "":
		return {"ok": false, "msg": "Nobody holds that land"}
	if o == code:
		return {"ok": false, "msg": "%s is already ours" % GameData.provinces[to_pid]["name"]}
	var inv := can_invade(code, o)
	if not inv["ok"]:
		return {"ok": false, "msg": inv["msg"]}
	var hostile: bool = inv["hostile"]
	var tgt := "" if hostile else o
	var path := find_path(code, a["node"], to_pid, tgt) if a["node"] != to_pid else []
	if path.is_empty() and a["node"] != to_pid:
		return {"ok": false, "msg": _no_route_msg(a, to_pid, tgt)}
	var days := est_days(a, path) if not path.is_empty() else 0
	if dry_run:
		return {"ok": true, "path": path, "days": days, "undeclared": not hostile, "target": o}
	a["path"] = path
	a["progress"] = 0.0
	a["goal"] = to_pid
	a["invade"] = tgt
	a["resume"] = true      # an invasion presses on to its objective after winning a battle on the way
	if a["state"] == "siege":
		a["state"] = "idle"
	stats["invasions"] += 1
	if not hostile and a["node"] < GameData.SEA_NODE and prov_owner.get(a["node"], "") == o:
		start_hostilities(code, o, code != player)    # already standing on their soil
	if code == player:
		log_event("%s ordered to %s %s (~%d days)." % [a["name"], "attack" if hostile else "invade", GameData.provinces[to_pid]["name"], days], "battle", [code, o])
	armies_changed.emit()
	return {"ok": true, "path": path, "days": days, "undeclared": not hostile, "target": o}

func army_speed(a: Dictionary) -> float:
	var base := float(GameData.eras[era]["move_km_day"])
	var slow := 99.0
	for u in a["units"]:
		slow = minf(slow, float(GameData.units[u["type"]]["speed"]))
	return base * clampf(slow / 1.5, 0.6, 1.6)

func army_pos_lonlat(a: Dictionary) -> Vector2:
	var p0 := GameData.node_lonlat(a["node"])
	if a["path"].is_empty():
		return p0
	var p1 := GameData.node_lonlat(a["path"][0])
	var d := GameData.node_km(a["node"], a["path"][0])
	var f := clampf(a["progress"] / d, 0.0, 1.0)
	if absf(p1.x - p0.x) > 180.0:
		return p0 if f < 0.5 else p1
	return p0.lerp(p1, f)

func _move_armies() -> void:
	for aid in armies.keys():
		if not armies.has(aid):
			continue
		var a: Dictionary = armies[aid]
		if a["state"] == "battle" or a["path"].is_empty():
			continue
		var at_sea: bool = a["node"] >= GameData.SEA_NODE
		a["progress"] += army_speed(a) * (2.2 if at_sea else 1.0)
		var guard := 0
		while not a["path"].is_empty() and guard < 6:
			guard += 1
			var nxt: int = a["path"][0]
			var d := GameData.node_km(a["node"], nxt)
			if a["progress"] < d:
				break
			var inv: String = a.get("invade", "")
			if nxt < GameData.SEA_NODE and not passable(a["owner"], nxt, inv):
				if a["owner"] == player:
					var bo: String = prov_owner.get(nxt, "")
					log_event("%s halts: the way into %s is closed (%s territory)." % [a["name"], GameData.provinces[nxt]["name"], nations[bo]["name"] if nations.has(bo) else "foreign"], "battle", [a["owner"]])
				a["path"] = []; a["progress"] = 0.0; a["goal"] = -1
				break
			if nxt < GameData.SEA_NODE and inv != "" and prov_owner.get(nxt, "") == inv and not at_war(a["owner"], inv):
				if not start_hostilities(a["owner"], inv, a["owner"] != player):
					a["path"] = []; a["progress"] = 0.0; a["goal"] = -1; a["invade"] = ""
					break
			a["progress"] -= d
			a["node"] = nxt
			a["path"].pop_front()
			if a["path"].is_empty():
				a["progress"] = 0.0
				if a["goal"] == nxt:
					a["goal"] = -1
			if nxt < GameData.SEA_NODE:
				if _check_battle(aid, nxt):
					break

func armies_in(pid: int) -> Array:
	var out: Array = []
	for a in armies.values():
		if a["node"] == pid:
			out.append(a)
	return out

func _check_battle(aid: int, pid: int) -> bool:
	var a: Dictionary = armies[aid]
	var enemies: Array = []
	for o in armies_in(pid):
		if o["id"] != aid and at_war(a["owner"], o["owner"]) and o["state"] != "battle":
			enemies.append(o["id"])
	if enemies.is_empty():
		return false
	_start_battle(pid, [aid], enemies)
	return true

# ======================= battles =======================
func _start_battle(pid: int, att: Array, def: Array) -> int:
	var bid := next_battle_id
	next_battle_id += 1
	var att_code: String = armies[att[0]]["owner"]
	var def_code: String = armies[def[0]]["owner"]
	# friendly idle armies in the province join their side
	for o in armies_in(pid):
		if o["state"] == "battle" or att.has(o["id"]) or def.has(o["id"]):
			continue
		if is_friendly(o["owner"], att_code) and at_war(o["owner"], def_code):
			att.append(o["id"])
		elif is_friendly(o["owner"], def_code) and at_war(o["owner"], att_code):
			def.append(o["id"])
	var sides := [[], []]
	var lists := [att, def]
	for s in 2:
		for id in lists[s]:
			var ar: Dictionary = armies[id]
			ar["state"] = "battle"; ar["battle"] = bid; ar["path"] = []; ar["progress"] = 0.0
			for i in ar["units"].size():
				var u: Dictionary = ar["units"][i]
				if u["men"] >= 1.0:
					sides[s].append({"army_id": id, "unit_index": i, "type": u["type"], "men": u["men"]})
	var terr: String = GameData.provinces[pid]["terrain"]
	var player_side := -1
	if att_code == player or (att.any(func(x): return armies[x]["owner"] == player)):
		player_side = 0
	elif def_code == player or (def.any(func(x): return armies[x]["owner"] == player)):
		player_side = 1
	var b := {"id": bid, "prov": pid, "armies": [att, def], "codes": [att_code, def_code], "units": sides, "terrain": terr,
		"sim": null, "watched": false, "awaiting": false, "player_side": player_side, "start_day": day, "done": false,
		"orders": [BattleSim.ai_orders(sides[0], sides[1], false, terr), BattleSim.ai_orders(sides[1], sides[0], true, terr)],
		"seed": int(hash(str(bid) + str(day) + str(pid)) & 0x7fffffff)}
	battles[bid] = b
	stats["battles"] += 1
	if player_side >= 0 and not auto_deploy:
		b["awaiting"] = true
	else:
		_begin_sim(b)
	log_event("Battle of %s: %s against %s." % [GameData.provinces[pid]["name"], nations[att_code]["name"], nations[def_code]["name"]], "battle", [att_code, def_code])
	armies_changed.emit()
	battle_started.emit(bid)
	return bid

func _begin_sim(b: Dictionary) -> void:
	var s := BattleSim.new()
	s.side_names = [nations[b["codes"][0]]["name"], nations[b["codes"][1]]["name"]]
	s.record_events = b["watched"]
	s.setup(b["units"], b["terrain"], b["orders"], b["seed"])
	b["sim"] = s
	b["awaiting"] = false

## Player deployment decision: orders = {objective, formation}; watch = open the 3D battle.
func deploy_battle(bid: int, orders: Dictionary, watch: bool) -> void:
	var b: Dictionary = battles[bid]
	var ps: int = b["player_side"]
	if ps >= 0:
		b["orders"][ps] = orders
	b["watched"] = watch
	_begin_sim(b)
	if watch:
		watching_battle = bid

func set_watched(bid: int, watched: bool) -> void:
	if not battles.has(bid):
		return
	var b: Dictionary = battles[bid]
	b["watched"] = watched
	if b["sim"] != null:
		b["sim"].record_events = watched
	watching_battle = bid if watched else (-1 if watching_battle == bid else watching_battle)

## Real-time stepping from the battle view. Returns true when the battle has finished.
func step_watched(bid: int, real_dt: float, time_scale: float = 1.0) -> bool:
	if not battles.has(bid):
		return true
	var b: Dictionary = battles[bid]
	var s: BattleSim = b["sim"]
	if s == null:
		return false
	b["acc"] = b.get("acc", 0.0) + real_dt * time_scale
	while b["acc"] >= BattleSim.DT and not s.done:
		b["acc"] -= BattleSim.DT
		s.step()
	if s.done and not b["done"]:
		_resolve_battle(b)
	return s.done

func _step_battles() -> void:
	for bid in battles.keys():
		var b: Dictionary = battles[bid]
		if b["done"] or b["awaiting"] or b["sim"] == null or b["watched"]:
			continue
		b["sim"].run_seconds(BATTLE_SECONDS_PER_DAY)
		if b["sim"].done:
			_resolve_battle(b)

func _resolve_battle(b: Dictionary) -> void:
	b["done"] = true
	var s: BattleSim = b["sim"]
	var res := s.result()
	var regs := s.regs
	for i in regs.size():
		var r: Dictionary = regs[i]
		if armies.has(r["army_id"]):
			var ar: Dictionary = armies[r["army_id"]]
			if r["unit_index"] < ar["units"].size():
				ar["units"][r["unit_index"]]["men"] = r["men"]
	var w: int = res["winner"]
	var pid: int = b["prov"]
	var winners: Array = b["armies"][w]; var losers: Array = b["armies"][1 - w]
	var wc: String = b["codes"][w]; var lc: String = b["codes"][1 - w]
	for id in winners + losers:
		if not armies.has(id):
			continue
		var ar: Dictionary = armies[id]
		ar["state"] = "idle"; ar["battle"] = -1
		var keep: Array = []
		for u in ar["units"]:
			if u["men"] >= u["max"] * 0.08:
				keep.append(u)
		ar["units"] = keep
		if keep.is_empty():
			armies.erase(id)
	# losers retreat to a friendly neighbouring province or are destroyed
	for id in losers:
		if not armies.has(id):
			continue
		var ar: Dictionary = armies[id]
		var dest := -1; var bd := 1e9
		for nb in GameData.provinces[pid]["neighbors"].keys():
			var o: String = prov_owner.get(nb, "")
			if o != "" and is_friendly(ar["owner"], o):
				var hostile := false
				for x in armies_in(nb):
					if at_war(x["owner"], ar["owner"]):
						hostile = true
				if not hostile:
					var d := GameData.node_km(pid, nb)
					if d < bd:
						bd = d; dest = nb
		if dest < 0:
			log_event("%s is cut off and destroyed after the battle." % ar["name"], "battle", [ar["owner"]])
			armies.erase(id)
		else:
			ar["path"] = [dest]; ar["progress"] = 0.0; ar["goal"] = -1; ar["invade"] = ""; ar["resume"] = false
			if ar["owner"] == player:
				log_event("%s retreats to %s." % [ar["name"], GameData.provinces[dest]["name"]], "battle", [ar["owner"]])
	# winners on an invasion order (interrupted by defenders on the way) carry on to their objective
	for id in winners:
		if not armies.has(id):
			continue
		var ar: Dictionary = armies[id]
		var goal: int = ar.get("goal", -1)
		if ar.get("resume", false) and goal >= 0 and goal != ar["node"] and ar["path"].is_empty():
			var inv: String = ar.get("invade", "")
			if inv != "" and at_war(ar["owner"], inv):
				inv = ""
			var np := find_path(ar["owner"], ar["node"], goal, inv)
			if not np.is_empty():
				ar["path"] = np; ar["progress"] = 0.0
			else:
				ar["goal"] = -1
	var losses: Array = res["losses"]
	_add_war_score(wc, lc, 6.0 + losses[1 - w] / 300.0)
	for c in [wc, lc]:
		nations[c]["exhaustion"] = minf(nations[c]["exhaustion"] + losses[b["codes"].find(c)] / maxf(_pop_total(c) * 0.002, 2000.0) * 0.05, 1.0)
	b["result"] = res
	if watching_battle == b["id"]:
		watching_battle = -1
	log_event("%s wins the battle of %s (%.0f s). Losses: %s %d, %s %d." % [nations[wc]["name"], GameData.provinces[pid]["name"], res["time"],
		nations[b["codes"][0]]["name"], int(losses[0]), nations[b["codes"][1]]["name"], int(losses[1])], "battle", [wc, lc])
	armies_changed.emit()
	battle_resolved.emit(b["id"], res)
	var bid: int = b["id"]
	_check_landless()
	# keep finished battles briefly for UI/tests; prune old ones
	for k in battles.keys():
		if battles[k]["done"] and day - int(battles[k]["start_day"]) > 30 and k != bid:
			battles.erase(k)

# ======================= sieges / conquest =======================
func garrison(pid: int) -> float:
	var g := 300.0 + prov_pop(pid) / 1.0e6 * 120.0
	if nations[prov_owner[pid]]["capital"] == pid:
		g *= 1.5
	return g

func siege_days_needed(pid: int) -> float:
	var d := float(GameData.eras[era]["siege_days"])
	match GameData.provinces[pid]["terrain"]:
		"mountains": d *= 1.4
		"hills", "forest", "jungle": d *= 1.15
	if nations[prov_owner[pid]]["capital"] == pid:
		d *= 1.3
	return d

func _step_sieges() -> void:
	var besieged := {}
	for a in armies.values():
		if a["state"] == "battle" or not a["path"].is_empty() or a["node"] >= GameData.SEA_NODE:
			continue
		var pid: int = a["node"]
		var o: String = prov_owner.get(pid, "")
		if o == "" or not at_war(a["owner"], o):
			if a["state"] == "siege":
				a["state"] = "idle"
			continue
		var defended := false
		for x in armies_in(pid):
			if x["owner"] == o or (is_friendly(x["owner"], o) and at_war(x["owner"], a["owner"])):
				defended = true
		if defended:
			continue
		a["state"] = "siege"
		if not besieged.has(pid):
			besieged[pid] = []
		besieged[pid].append(a)
	for pid in sieges.keys().duplicate():
		if not besieged.has(pid):
			sieges.erase(pid)
	for pid in besieged.keys():
		var lst: Array = besieged[pid]
		var men := 0.0
		for a in lst:
			men += army_men(a)
		var lead: Dictionary = lst[0]
		if not sieges.has(pid) or sieges[pid]["by"] != lead["owner"]:
			sieges[pid] = {"by": lead["owner"], "army": lead["id"], "progress": 0.0, "start": day}
			if lead["owner"] == player or prov_owner[pid] == player:
				log_event("Siege of %s begins." % GameData.provinces[pid]["name"], "battle", [lead["owner"], prov_owner[pid]])
		var s: Dictionary = sieges[pid]
		s["progress"] += clampf(men / garrison(pid), 0.4, 3.0) / siege_days_needed(pid)
		if s["progress"] >= 1.0:
			sieges.erase(pid)
			transfer_province(pid, lead["owner"])
			for a in lst:
				a["state"] = "idle"

func transfer_province(pid: int, new_owner: String) -> void:
	var old: String = prov_owner.get(pid, "")
	if old == new_owner:
		return
	prov_owner[pid] = new_owner
	nation_provs[old].erase(pid)
	nation_provs[new_owner].append(pid)
	stats["captures"] += 1
	var recapture: bool = cores_of(new_owner).has(pid)
	if recapture:
		stats["recaptures"] += 1
	_add_war_score(new_owner, old, 15.0 if nations[old]["capital"] == pid else 8.0)
	_neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
	log_event("%s %s %s from %s." % [nations[new_owner]["name"], "recaptures" if recapture else "captures", GameData.provinces[pid]["name"], nations[old]["name"]], "capture", [new_owner, old], new_owner != player)
	# a nation that had lost all its land gets a seat of government back
	if not nation_provs[new_owner].has(nations[new_owner]["capital"]):
		nations[new_owner]["capital"] = pid
		log_event("%s re-establishes its government in %s." % [nations[new_owner]["name"], GameData.provinces[pid]["name"]], "info", [new_owner])
	if nations[old]["capital"] == pid and not nation_provs[old].is_empty():
		var best: int = nation_provs[old][0]
		for p in nation_provs[old]:
			if GameData.provinces[p]["population"] > GameData.provinces[best]["population"]:
				best = p
		nations[old]["capital"] = best
		log_event("%s moves its capital to %s." % [nations[old]["name"], GameData.provinces[best]["name"]], "info", [old])
	# the province's population, taxes and resource now count for the new owner; refresh both ledgers now
	_economy_month(new_owner, true)
	if not nation_provs[old].is_empty():
		_economy_month(old, true)
	ownership_changed.emit(pid, old, new_owner)
	if nation_provs[old].is_empty():
		nations[old]["conquered_by"] = new_owner
		if _has_viable_army(old):
			log_event("%s has lost all its land, but its armies fight on." % nations[old]["name"], "capture", [old, new_owner], old != player)
		else:
			_eliminate(old, new_owner)

## Provinces a nation held when the campaign began: what it will try to win back.
func cores_of(code: String) -> Array:
	if _cores.is_empty():
		for pid in GameData.province_ids:
			var o: String = GameData.provinces[pid]["owner"]
			if not _cores.has(o):
				_cores[o] = []
			_cores[o].append(pid)
	return _cores.get(code, [])

func _has_viable_army(code: String) -> bool:
	for a in armies.values():
		if a["owner"] == code and army_men(a) >= VIABLE_ARMY_MEN:
			return true
	return false

## Landless nations survive only while they still field a viable army.
func _check_landless() -> void:
	for code in nations.keys():
		var n: Dictionary = nations[code]
		if n["alive"] and nation_provs[code].is_empty() and not _has_viable_army(code):
			_eliminate(code, n.get("conquered_by", ""))

func _eliminate(code: String, by: String) -> void:
	nations[code]["alive"] = false
	stats["eliminated"] += 1
	for aid in armies.keys():
		if armies[aid]["owner"] == code:
			armies.erase(aid)
	for e in enemies_of(code):
		wars.erase(_key(code, e))
	for pid in sieges.keys().duplicate():
		if sieges[pid]["by"] == code:
			sieges.erase(pid)
	var by_name: String = nations[by]["name"] if nations.has(by) else "its enemies"
	log_event("%s has been conquered by %s and ceases to exist." % [nations[code]["name"], by_name], "capture", [code, by] if nations.has(by) else [code])
	armies_changed.emit()
	if code == player and not defeated:
		defeated = true
		running = false
		player_defeated.emit(by)

# ======================= monthly =======================
func _month() -> void:
	_check_landless()
	var ctx := _economy_ctx()
	for code in nations.keys():
		if nations[code]["alive"]:
			_economy_month(code, false, ctx)
	_relations_drift()
	if ai_enabled:
		var codes: Array = nations.keys()
		for code in codes:
			var n: Dictionary = nations[code]
			if n["alive"] and n["ai"]:
				_ai_recruit(code)
				if n["major"]:
					_ai_diplomacy(code)
				else:
					_ai_minor(code)
	month_passed.emit()

func _relations_drift() -> void:
	for k in relations.keys():
		var v: float = relations[k]
		var tr: Dictionary = treaties.get(k, {})
		var d := -v * 0.01
		if tr.get("alliance", false): d += 1.5
		if tr.get("trade", false): d += 0.7
		if wars.has(k): d -= 2.0
		relations[k] = clampf(v + d, -100.0, 100.0)

func _ai_recruit(code: String) -> void:
	var n: Dictionary = nations[code]
	var income: float = n["income"].get("total", 0.0)
	var upkeep: float = n["expense"].get("Army upkeep", 0.0)
	var war := at_war_any(code)
	var cap := (0.62 if war else 0.42) if n["major"] else (0.55 if war else 0.3)
	var era_id: String = GameData.eras[era]["id"]
	var bought := 0
	while bought < (3 if war else 1) and upkeep < income * cap and n["funds"] > income * 1.5:
		var roles := ["ranged", "inf", "ranged", "cav", "art", "armor", "ranged"]
		var role: String = roles[rng.randi_range(0, roles.size() - 1)]
		var uid := GameData.unit_for_role(era_id, role)
		var pid: int = n["capital"]
		if sieges.has(pid):
			break
		var r := buy_unit(code, uid, pid)
		if not r["ok"]:
			break
		upkeep += float(GameData.units[uid]["upkeep"])
		bought += 1
	# refit outdated armies when rich
	if n["funds"] > income * 4.0:
		for a in armies.values():
			if a["owner"] == code and a["state"] == "idle" and refit_cost(a) > 0.0 and refit_cost(a) < n["funds"] * 0.5:
				refit_army(a["id"])
				break

func _ai_minor(code: String) -> void:
	# minor polities never start wars; they sue for peace when beaten
	for e in enemies_of(code):
		if e == player:
			continue
		var ev := evaluate(code, e, "peace")
		if rng.randf() < 0.25:
			var r := propose(code, e, "peace", true)

func _ai_diplomacy(code: String) -> void:
	var n: Dictionary = nations[code]
	if day < 45:
		return
	# 1) peace when the war goes badly or drags on
	for e in enemies_of(code):
		var months := (day - int(wars[_key(code, e)]["start"])) / 30
		var ws := war_score(code, e)
		if ws < -10.0 or n["exhaustion"] > 0.3 or months > 24 or (ws > 22.0 and months > 4):
			if rng.randf() < 0.35:
				propose(code, e, "peace", true)
	if not n["alive"]:
		return
	# 2) treaties
	if rng.randf() < n["diplomacy"] * 0.5:
		var cands: Array = neighbors_of(code).duplicate()
		var majors: Array = GameData.majors.keys()
		cands.append(majors[rng.randi_range(0, majors.size() - 1)])
		var other: String = cands[rng.randi_range(0, cands.size() - 1)]
		if other != code and nations.has(other) and nations[other]["alive"] and not at_war(code, other):
			var rel := relation(code, other)
			var kind := "trade"
			if has_treaty(code, other, "trade"):
				kind = "alliance" if rel > 25.0 else ("nap" if rel > 0.0 else "")
			if kind == "alliance" and has_treaty(code, other, "alliance"):
				kind = ""
			if kind != "" and evaluate(code, other, kind)["score"] > -20.0:
				propose(code, other, kind, true)
	if rng.randf() < 0.08 and n["funds"] > n["income"].get("total", 0.0) * 5.0:
		var nb := neighbors_of(code)
		if not nb.is_empty():
			var t: String = nb[rng.randi_range(0, nb.size() - 1)]
			if not at_war(code, t) and nations[t]["alive"]:
				gift(code, t, n["income"].get("total", 0.0) * 0.5)
	# 3) war
	if not enemies_of(code).is_empty() or n["exhaustion"] > 0.15 or day < 60 or day - int(n.get("last_peace", -9999)) < 365 * 2:
		return
	# perf: one pass over armies/treaties instead of strength()/allies_of() per neighbour. Nothing changes
	# armies or treaties inside this scan and the per-owner sums keep army order, so values are bit-identical.
	var st_tab := _strength_table()
	var al_tab := _alliance_table()
	var my_s: float = st_tab.get(code, 0.0)
	var cands: Array = []   # [value, code, strength ratio]
	for t in neighbors_of(code):
		if not nations[t]["alive"] or not can_declare_war(code, t)["ok"] or has_treaty(code, t, "nap"):
			continue
		# cheap filter first: a target is only ever chosen when rel < 10, so skip the strength sums otherwise
		if relation(code, t) >= 10.0:
			continue
		var their: float = st_tab.get(t, 0.0)
		for al in al_tab.get(t, []):
			their += st_tab.get(al, 0.0) * 0.7
		var ratio := my_s / maxf(their, 1.0)
		var rel := relation(code, t)
		var v := ratio * 10.0 - rel * 0.3 + (8.0 if not nations[t]["major"] else 0.0)
		if t == player:
			v += 2.0
		if ratio > 1.8 and rel < 10.0 and v > 0.0:
			cands.append([v, t, ratio])
	if cands.is_empty() or rng.randf() >= n["aggression"] * 0.045:
		return
	# v0.5 geographic relevance (only evaluated once a war is actually on the table): our armies must be able
	# to get there. Border wars are preferred; an overseas war needs a short crossing and a clear strength edge.
	var mkd := float(GameData.eras[era]["move_km_day"])
	var best := ""; var best_v := 0.0
	for c in cands:
		var t: String = c[1]
		var crow := GameData.km_between(GameData.node_lonlat(n["capital"]), GameData.node_lonlat(nations[t]["capital"]))
		if crow / 2.2 / mkd > AI_MAX_CAMPAIGN_DAYS:
			continue    # even by the fastest sea route it is out of reach
		var border := _shares_border(code, t)
		var reach := crow / mkd
		if not border:
			var rm := _reach_map(code, n["capital"], AI_MAX_CAMPAIGN_DAYS * mkd, t)
			var tc: int = nations[t]["capital"]
			if not rm.has(tc):
				continue
			reach = rm[tc][0] / mkd
			if reach > AI_CAMPAIGN_DAYS or c[2] < 2.5:
				continue
		var v: float = c[0] + (6.0 if border else 0.0) - minf(reach, AI_MAX_CAMPAIGN_DAYS) / 10.0
		if v > best_v:
			best_v = v; best = t
	if best != "":
		declare_war(code, best, true)

func _ai_military_daily() -> void:
	for aid in armies.keys():
		if not armies.has(aid):
			continue
		var a: Dictionary = armies[aid]
		var code: String = a["owner"]
		if code == player or a["state"] == "battle" or day < a["ai_next"]:
			continue
		a["ai_next"] = day + 5 + rng.randi_range(0, 4)
		var n: Dictionary = nations[code]
		var enemies := enemies_of(code)
		var my_s := army_strength(a)
		# merge with other idle armies in the same province
		for o in armies_in(a["node"]):
			if o["id"] != aid and o["owner"] == code and o["state"] != "battle" and o["path"].is_empty() and a["path"].is_empty():
				merge_armies(aid, o["id"])
				my_s = army_strength(a)
		if enemies.is_empty() and nation_provs[code].is_empty() and a["path"].is_empty():
			# landless and at peace: the same invasion rules as the player, aimed at the lost homeland
			var home := -1; var hd := 1e18
			for pid in cores_of(code):
				var po: String = prov_owner.get(pid, "")
				if po == "" or po == code or not can_invade(code, po)["ok"]:
					continue
				var dh := GameData.node_km(a["node"], pid)
				if dh < hd:
					hd = dh; home = pid
			if home >= 0:
				order_invade(aid, home)
			continue
		if enemies.is_empty():
			if a["state"] == "idle" and a["path"].is_empty() and a["node"] >= GameData.SEA_NODE:
				order_move(aid, n["capital"])
			elif a["path"].is_empty() and prov_owner.get(a["node"], "") != code and not is_friendly(code, prov_owner.get(a["node"], "")):
				order_move(aid, n["capital"])
			continue
		if not a["path"].is_empty() or a["state"] == "siege":
			continue
		var decision := _ai_war_decision(aid, a, my_s, enemies)
		var target: int = decision["target"]
		if target >= 0 and target != a["node"]:
			order_move(aid, target)

## v0.5 strategic AI: every order an AI army gets in wartime is scored, not "nearest enemy province".
## Order of business: (1) beat enemy armies inside our land, (2) keep enough at home to meet any enemy
## army threatening it, (3) rest a battered army, (4) campaign: the best-value target we can reach,
## weighing travel time (overseas crossings cost more), the defenders around it, its worth (capital,
## population, our lost provinces, adjacency to our land) and the risk of a far-away front.
func _ai_war_decision(aid: int, a: Dictionary, my_s: float, enemies: Array) -> Dictionary:
	var code: String = a["owner"]
	var n: Dictionary = nations[code]
	# 1) defend: enemy armies inside our land that we can take on
	var target := -1; var best := 1e18
	for o in armies.values():
		if o["node"] >= GameData.SEA_NODE or not at_war(code, o["owner"]):
			continue
		if prov_owner.get(o["node"], "") == code and army_strength(o) < my_s * 1.25:
			var d := GameData.node_km(a["node"], o["node"])
			if d < best:
				best = d; target = o["node"]
	if target >= 0:
		return {"target": target, "why": "defend"}
	# 2) home defence: the threat to our land (enemy armies within reach of it) against what stays home
	var threat := _home_threat(code)
	var home_s := 0.0
	for o in armies.values():
		if o["owner"] == code and o["id"] != aid and o["path"].is_empty() and prov_owner.get(o["node"], "") == code:
			home_s += army_strength(o)
	var must_guard: bool = threat["strength"] > home_s * 1.1 and not nation_provs[code].is_empty()
	# 3) readiness: an army that has lost half its men does not start new offensives
	var ready := _readiness(a)
	# 4) campaign
	var camp := {}
	if ready >= AI_MIN_READINESS:
		camp = _best_campaign(aid, a, my_s, enemies, n["major"])
	if must_guard:
		# a short counterattack is fine (we can be back in time); a far expedition is not
		if not camp.is_empty() and camp["days"] <= AI_GUARD_DAYS:
			return {"target": camp["pid"], "why": "nearby attack while guarding"}
		var guard: int = threat["pid"] if threat["pid"] >= 0 else n["capital"]
		return {"target": guard, "why": "guard home"}
	if not camp.is_empty():
		return {"target": camp["pid"], "why": "campaign", "score": camp["score"]}
	if prov_owner.get(a["node"], "") != code and not nation_provs[code].is_empty():
		return {"target": n["capital"], "why": "regroup" if ready < AI_MIN_READINESS else "no worthwhile target"}
	return {"target": -1, "why": "hold"}

const AI_CAMPAIGN_DAYS := 45.0       # a normal campaign: reachable within about six weeks
const AI_MAX_CAMPAIGN_DAYS := 100.0  # beyond this no target is worth it
const AI_GUARD_DAYS := 15.0          # an army needed at home only strikes this close
const AI_MIN_READINESS := 0.5        # men / establishment below which no new offensive starts
const AI_THREAT_KM := 700.0          # enemy armies this close to our land count as a threat

func _readiness(a: Dictionary) -> float:
	var m := 0.0; var mx := 0.0
	for u in a["units"]:
		m += u["men"]; mx += u["max"]
	return m / maxf(mx, 1.0)

## Strength of enemy armies inside or near our land, and the province they threaten most.
func _home_threat(code: String) -> Dictionary:
	var s := 0.0; var pid := -1; var worst := 0.0
	var cap: int = nations[code]["capital"]
	for o in armies.values():
		if not at_war(code, o["owner"]):
			continue
		var on := int(o["node"])
		var near := false
		if on < GameData.SEA_NODE and prov_owner.get(on, "") == code:
			near = true
		elif GameData.node_km(on, cap) < AI_THREAT_KM:
			near = true
		elif o["goal"] >= 0 and prov_owner.get(o["goal"], "") == code and GameData.node_km(on, o["goal"]) < AI_THREAT_KM * 1.5:
			near = true
		if near:
			var st := army_strength(o)
			s += st
			if st > worst:
				worst = st
				var g: int = o["goal"]
				pid = g if g >= 0 and prov_owner.get(g, "") == code else cap
	return {"strength": s, "pid": pid}

## Route costs (km-equivalent: a sea leg counts at 1/2.2 of its length) from `from` to every province the
## nation's armies may enter, up to `max_km`. Value per province: [cost, needs_sea_transport].
## Cached until borders, wars or alliances change (every place that clears _path_cache clears it too).
var _reach_cache := {}
func _reach_map(code: String, from: int, max_km: float, invading: String = "", targets: Dictionary = {}) -> Dictionary:
	var ck := "%s|%d|%d|%s|%d" % [code, from, int(max_km), invading, targets.hash()]
	if _reach_cache.has(ck):
		return _reach_cache[ck]
	if _reach_cache.size() > 256:
		_reach_cache.clear()
	var out := {}
	var start := from
	var dist := {}
	var sea0 := false
	if from >= GameData.SEA_NODE:
		# at sea: start from the nearest port we may use
		var z: Dictionary = GameData.seazones[from - GameData.SEA_NODE]
		var bd := 1e18
		for port in z["ports"]:
			var dk := GameData.node_km(from, port)
			if dk < bd and passable(code, port, invading):
				bd = dk; start = port
		if start == from:
			_reach_cache[ck] = out
			return out
		sea0 = true
	var ports := _ports()
	var left := targets.size()
	dist[start] = [0.0, sea0]
	var heap := [[0.0, start]]
	while not heap.is_empty():
		var top: Array = _heap_pop(heap)
		var u: int = top[1]
		var du: Array = dist[u]
		if top[0] > du[0]:
			continue
		if top[0] > max_km:
			break
		out[u] = du
		if not targets.is_empty() and targets.has(u):
			left -= 1
			if left <= 0:
				break    # every province we asked about has been reached
		for nb in GameData.provinces[u]["neighbors"].keys():
			if not passable(code, nb, invading):
				continue
			var nd: float = du[0] + GameData.node_km(u, nb)
			if nd < dist.get(nb, [1e18])[0]:
				dist[nb] = [nd, du[1]]
				_heap_push(heap, [nd, nb])
		for r in ports.get(u, []):
			var v: int = r["to"]
			if not passable(code, v, invading):
				continue
			var nd2: float = du[0] + (r["cost"] - 150.0) / 0.8 / 2.2 + 30.0   # sea distance at sea speed + embarking
			if nd2 < dist.get(v, [1e18])[0]:
				dist[v] = [nd2, true]
				_heap_push(heap, [nd2, v])
	_reach_cache[ck] = out
	return out

## Campaign travel time from `from` to `to` (days, -1 when there is no route).
func _campaign_days(code: String, from: int, to: int, invading: String = "") -> float:
	var path := find_path(code, from, to, invading)
	if path.is_empty():
		return -1.0
	var land := 0.0; var sea := 0.0
	var last := from
	for nd in path:
		var km := GameData.node_km(last, nd)
		if last >= GameData.SEA_NODE:
			sea += km
		else:
			land += km
		last = nd
	return (land + sea / 2.2) / float(GameData.eras[era]["move_km_day"])

## Best offensive target for an AI army, or {} when nothing is worth the risk.
func _best_campaign(aid: int, a: Dictionary, my_s: float, enemies: Array, major: bool) -> Dictionary:
	var code: String = a["owner"]
	var cands := {}
	for pid in cores_of(code):
		var po: String = prov_owner.get(pid, "")
		if po != "" and po != code and at_war(code, po):
			cands[pid] = true
	if major:
		for e in enemies:
			for pid in nation_provs[e]:
				cands[pid] = true
	if cands.is_empty():
		return {}
	# one bounded route search from the army gives travel time to every candidate (and whether it needs ships)
	var speed := army_speed(a)
	var max_km := AI_MAX_CAMPAIGN_DAYS * speed
	var near := {}
	for pid in cands.keys():
		if GameData.node_km(a["node"], pid) / 2.2 <= max_km:
			near[pid] = true
	if near.is_empty():
		return {}
	cands = near
	var reach := _reach_map(code, int(a["node"]), max_km, "", cands)
	var foes: Array = []
	for o in armies.values():
		if at_war(code, o["owner"]) and o["node"] < GameData.SEA_NODE:
			foes.append([int(o["node"]), army_strength(o)])
	var best := {}; var best_score := 0.0
	for pid in cands.keys():
		if not reach.has(pid):
			continue
		var days: float = reach[pid][0] / speed
		var overseas: bool = reach[pid][1]
		# estimated cost: enemy armies at or around the objective, plus the garrison
		var danger := 0.0
		for f in foes:
			if GameData.node_km(f[0], pid) < 350.0:
				danger += f[1]
		var gar := garrison(pid) * 40.0
		if my_s < (danger + gar) * 1.3:
			continue
		var po: String = prov_owner[pid]
		var value := 10.0 + clampf(prov_pop(pid) / 1.0e6, 0.0, 10.0) * 2.0
		if nations[po]["capital"] == pid:
			value += 12.0
		if cores_of(code).has(pid):
			value += 25.0
		var adjacent := false
		for nb in GameData.provinces[pid]["neighbors"].keys():
			if prov_owner.get(nb, "") == code:
				adjacent = true
				break
		if adjacent:
			value += 10.0
		if nation_provs[po].size() <= 2:
			value += 6.0
		# cost: time on the road, an overseas expedition, and how contested the objective is
		var cost := days + (20.0 if overseas else 0.0) + danger / maxf(my_s, 1.0) * 30.0
		if days > AI_CAMPAIGN_DAYS:
			cost += (days - AI_CAMPAIGN_DAYS) * 1.5   # a far front needs a much better reason
		var score := value / (cost + 10.0)
		if score > best_score:
			best_score = score
			best = {"pid": pid, "days": days, "score": score, "overseas": overseas}
	if best.is_empty() or best_score < 0.12:
		return {}
	return best


# ======================= detection / invasion warnings (v0.5) =======================
## Era-appropriate detection: watch posts, scouts and observers (medieval, pike & shot), cavalry screens
## and coastal observation (1800s), reconnaissance (1914) and radar (modern). Range in km around every
## province a nation holds and every army it fields; at sea the range is scaled (little before coastal
## observation, more with radar).
const DETECT_KM := {"medieval": 60.0, "early_modern": 110.0, "c19": 180.0, "c20": 350.0, "modern": 900.0}
const DETECT_SEA := {"medieval": 0.5, "early_modern": 0.6, "c19": 1.0, "c20": 1.2, "modern": 1.5}
const DETECT_NAMES := {"medieval": "Scouts and watch posts", "early_modern": "Scouts", "c19": "Pickets and coastal observers",
	"c20": "Reconnaissance", "modern": "Radar"}
var _prov_r := {}

func detect_range(at_sea: bool = false) -> float:
	var eid: String = GameData.eras[era]["id"]
	return float(DETECT_KM.get(eid, 150.0)) * (float(DETECT_SEA.get(eid, 1.0)) if at_sea else 1.0)

## Rough radius of a province (half the typical distance to its neighbours): watch posts cover its edges too.
func _province_radius(pid: int) -> float:
	if _prov_r.has(pid):
		return _prov_r[pid]
	var ds: Array = []
	for nb in GameData.provinces[pid]["neighbors"].keys():
		ds.append(GameData.node_km(pid, nb))
	ds.sort()
	var r := 0.0 if ds.is_empty() else clampf(float(ds[ds.size() / 2]) * 0.5, 0.0, 400.0)
	_prov_r[pid] = r
	return r

## Can `code` see army `a` right now?
func detects(code: String, a: Dictionary) -> bool:
	if a["owner"] == code or is_friendly(code, a["owner"]):
		return true
	var pos := army_pos_lonlat(a)
	var at_sea: bool = a["node"] >= GameData.SEA_NODE
	var r := detect_range(at_sea)
	if not at_sea and prov_owner.get(a["node"], "") == code:
		return true      # on our soil
	for pid in nation_provs.get(code, []):
		if GameData.km_between(GameData.node_lonlat(pid), pos) < r + _province_radius(pid):
			return true
	for o in armies.values():
		if o["owner"] == code and GameData.km_between(army_pos_lonlat(o), pos) < r:
			return true
	return false

## Armies that concern the player: at war with us, or carrying an invasion order against us.
func _threatens_player(a: Dictionary) -> bool:
	var o: String = a["owner"]
	if o == player or is_friendly(player, o):
		return false
	if at_war(o, player) or a.get("invade", "") == player:
		return true
	var g: int = a.get("goal", -1)
	return g >= 0 and prov_owner.get(g, "") == player

## Map / panel rule: an army threatening the player is only shown while detected.
func hidden_from_player(a: Dictionary) -> bool:
	if not _threatens_player(a):
		return false
	var v = _seen_by_player.get(a["id"])
	if v == null:
		v = detects(player, a)
		_seen_by_player[a["id"]] = v
	return not v

## Daily: refresh what the player can see; warn once per army and objective as an approaching force is spotted.
func _scan_detection() -> void:
	_seen_by_player.clear()
	if not nations.has(player) or not nations[player]["alive"]:
		return
	for aid in spotted.keys().duplicate():
		if not armies.has(aid):
			spotted.erase(aid)
	for a in armies.values():
		if not _threatens_player(a):
			continue
		var seen := detects(player, a)
		_seen_by_player[a["id"]] = seen
		if not seen or a["state"] == "battle":
			continue
		# where is it heading? its objective if that is our land, otherwise our province it is in or about to enter
		var goal: int = a.get("goal", -1)
		var tgt := -1
		if goal >= 0 and prov_owner.get(goal, "") == player:
			tgt = goal
		elif a["node"] < GameData.SEA_NODE and prov_owner.get(a["node"], "") == player:
			tgt = a["node"]
		elif not a["path"].is_empty() and prov_owner.get(int(a["path"][0]), "") == player:
			tgt = int(a["path"][0])
		if tgt < 0:
			continue
		if spotted.get(a["id"], -1) == tgt:
			continue
		spotted[a["id"]] = tgt
		_warn(a, tgt)

func _approx_men(men: float) -> String:
	var eid: String = GameData.eras[era]["id"]
	var step: float = {"medieval": 1000.0, "early_modern": 1000.0, "c19": 500.0, "c20": 500.0, "modern": 100.0}.get(eid, 500.0)
	var v := maxf(step, round(men / step) * step)
	return ("about %s" if eid in ["medieval", "early_modern"] else "roughly %s") % _thousands(v)

static func _thousands(v: float) -> String:
	var n := int(v)
	var t := str(n)
	if n >= 1000:
		t = "%d,%03d" % [n / 1000, n % 1000]
	return t

func _warn(a: Dictionary, tgt: int) -> void:
	var path: Array = a["path"]
	var eta := -1
	if not path.is_empty() and path.has(tgt):
		# remaining travel: the legs up to the objective, less what is already covered on the current leg
		var km := 0.0; var sea_km := 0.0
		var last: int = a["node"]
		for nd in path.slice(0, path.find(tgt) + 1):
			var k := GameData.node_km(last, nd)
			if last >= GameData.SEA_NODE:
				sea_km += k
			else:
				km += k
			last = nd
		var done_km: float = a["progress"]
		if a["node"] >= GameData.SEA_NODE:
			sea_km = maxf(sea_km - done_km, 0.0)
		else:
			km = maxf(km - done_km, 0.0)
		eta = maxi(1, int(ceil((km + sea_km / 2.2) / army_speed(a))))
	elif a["node"] == tgt:
		eta = 0
	var ours := 0.0
	for o in armies.values():
		if o["owner"] == player and o["node"] < GameData.SEA_NODE and GameData.node_km(o["node"], tgt) < 250.0:
			ours += army_men(o)
	var men := army_men(a)
	var eid: String = GameData.eras[era]["id"]
	var who: String = nations[a["owner"]]["name"]
	var how := "at sea" if a["node"] >= GameData.SEA_NODE else ("inside our borders" if prov_owner.get(a["node"], "") == player else "on the march")
	var undeclared: bool = not at_war(a["owner"], player)
	var text := "%s report: %s army of %s men %s, heading for %s%s." % [DETECT_NAMES.get(eid, "Scouts"), who, _approx_men(men), how,
		GameData.provinces[tgt]["name"], (" — arrival in about %d days" % eta) if eta > 0 else (" — it is there now" if eta == 0 else "")]
	if undeclared:
		text += " No war has been declared."
	if ours < men * 0.8:
		text += " Our forces nearby are outnumbered (%s men)." % _thousands(ours)
	var w := {"army": a["id"], "owner": a["owner"], "province": tgt, "men": men, "approx": _approx_men(men), "eta": eta,
		"day": day, "undeclared": undeclared, "ours": ours, "text": text}
	log_event(text, "warning", [player, a["owner"]])
	invasion_warning.emit(w)

# ======================= log =======================
func log_event(text: String, kind: String = "info", codes: Array = [], by_ai: bool = false) -> void:
	var ev := {"day": day, "date": date_string(), "text": text, "kind": kind, "nations": codes, "ai": by_ai}
	event_log.append(ev)
	if event_log.size() > 400:
		event_log.pop_front()
	event_logged.emit(ev)

func player_relevant(ev: Dictionary) -> bool:
	if ev["kind"] == "era" or ev["nations"].is_empty():
		return true
	if ev["nations"].has(player):
		return true
	for c in ev["nations"]:
		if nations.has(c) and nations[c]["major"]:
			return ev["kind"] in ["war", "peace", "capture"]
	return false

# ======================= save / load =======================
const SAVE_VERSION := 1
const SAVE_DIR := "user://saves"
const SAVE_FIELDS := ["speed_idx", "day", "start_year", "start_doy", "era", "player", "nations", "prov_owner", "nation_provs",
	"sieges", "armies", "next_army_id", "battles", "next_battle_id", "relations", "treaties", "wars", "event_log", "accum",
	"stats", "pending_offers", "ai_enabled", "slow_during_watch", "defeated", "spotted"]
signal game_loaded

## Full campaign state as plain Variants (no objects). Battle sims are converted with BattleSim.to_dict().
func serialize_state() -> Dictionary:
	var d := {"version": SAVE_VERSION, "rng_seed": rng.seed, "rng_state": rng.state}
	for f in SAVE_FIELDS:
		if f == "battles":
			continue
		var v: Variant = get(f)
		d[f] = v.duplicate(true) if (v is Array or v is Dictionary) else v
	var bs := {}
	for bid in battles.keys():
		var b: Dictionary = battles[bid]
		var c := {}
		for k in b.keys():
			if k == "sim":
				c[k] = b[k].to_dict() if b[k] != null else null
			else:
				var v2: Variant = b[k]
				c[k] = v2.duplicate(true) if (v2 is Array or v2 is Dictionary) else v2
		bs[bid] = c
	d["battles"] = bs
	return d

func apply_state(d: Dictionary) -> void:
	GameData.load_all()
	defeated = false; _cores.clear(); _reach_cache.clear(); spotted.clear(); _seen_by_player.clear()
	for f in SAVE_FIELDS:
		if f == "battles" or not d.has(f):
			continue
		var v: Variant = d[f]
		set(f, v.duplicate(true) if (v is Array or v is Dictionary) else v)
	battles = {}
	for bid in d["battles"].keys():
		var c: Dictionary = d["battles"][bid].duplicate(true)
		if c["sim"] != null:
			c["sim"] = BattleSim.from_dict(c["sim"])
		battles[bid] = c
	rng.seed = d["rng_seed"]
	rng.state = d["rng_state"]
	_port_reach.clear(); _neighbors_cache.clear(); _path_cache.clear(); _reach_cache.clear()
	# A battle that was being watched continues off-screen after loading (no 3D view is open).
	watching_battle = -1
	for b in battles.values():
		if b["watched"]:
			b["watched"] = false
			if b["sim"] != null:
				b["sim"].record_events = false
	# saves from before v0.4 have no invasion fields: every war in them was formally declared
	for a in armies.values():
		if not a.has("invade"):
			a["invade"] = ""
		if not a.has("resume"):
			a["resume"] = false
	for w in wars.values():
		if not w.has("declared"):
			w["declared"] = true
	for k in ["invasions", "undeclared", "recaptures"]:
		if not stats.has(k):
			stats[k] = 0
	if not d.has("spotted"):
		spotted = {}
	_seen_by_player.clear()
	running = not defeated
	game_loaded.emit()

static func save_path(slot: String) -> String:
	return SAVE_DIR.path_join(slot.validate_filename() + ".save")

## Binary Variant file (FileAccess.store_var): exact floats, int keys and Vector2 survive, unlike JSON.
func save_game(slot: String = "quicksave") -> Dictionary:
	DirAccess.make_dir_recursive_absolute(SAVE_DIR)
	var path := save_path(slot)
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return {"ok": false, "msg": "Cannot write %s (%s)" % [path, error_string(FileAccess.get_open_error())]}
	var meta := {"magic": "IRONCROWNS", "version": SAVE_VERSION, "player": player,
		"nation": nations[player]["name"] if nations.has(player) else player, "date": date_string(),
		"era": GameData.eras[era]["name"], "saved_unix": int(Time.get_unix_time_from_system())}
	f.store_var(meta)
	f.store_var(serialize_state())
	f.close()
	return {"ok": true, "path": path, "msg": "Saved \"%s\" (%s)" % [slot, date_string()]}

static func read_meta(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var m: Variant = f.get_var()
	return m if m is Dictionary and m.get("magic", "") == "IRONCROWNS" else {}

func load_game(slot: String = "quicksave") -> Dictionary:
	var path := save_path(slot)
	if not FileAccess.file_exists(path):
		return {"ok": false, "msg": "No save named \"%s\"" % slot}
	var f := FileAccess.open(path, FileAccess.READ)
	var meta: Variant = f.get_var()
	if not (meta is Dictionary) or meta.get("magic", "") != "IRONCROWNS":
		return {"ok": false, "msg": "Not an Iron Crowns save"}
	if int(meta["version"]) > SAVE_VERSION:
		return {"ok": false, "msg": "Save is from a newer version"}
	var st: Variant = f.get_var()
	f.close()
	if not (st is Dictionary):
		return {"ok": false, "msg": "Save file is corrupt"}
	apply_state(st)
	return {"ok": true, "msg": "Loaded \"%s\" (%s)" % [slot, date_string()]}

static func list_saves() -> Array:
	var out: Array = []
	var da := DirAccess.open(SAVE_DIR)
	if da == null:
		return out
	for fn in da.get_files():
		if fn.ends_with(".save"):
			var m := read_meta(SAVE_DIR.path_join(fn))
			if not m.is_empty():
				m["slot"] = fn.get_basename()
				out.append(m)
	out.sort_custom(func(a, b): return a["saved_unix"] > b["saved_unix"])
	return out
