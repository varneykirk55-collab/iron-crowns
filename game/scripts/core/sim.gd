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
	_port_reach.clear(); _neighbors_cache.clear(); _path_cache.clear()
	next_army_id = 1; next_battle_id = 1; watching_battle = -1; accum = 0.0
	stats = {"wars_declared": 0, "ai_wars": 0, "peace": 0, "ai_peace": 0, "alliances": 0, "ai_alliances": 0, "trades": 0,
		"ai_trades": 0, "naps": 0, "ai_naps": 0, "gifts": 0, "captures": 0, "battles": 0, "eliminated": 0, "era_changes": 0,
		"ai_units_bought": 0, "ai_proposals": 0, "ai_rejections": 0}
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
		"battle": -1, "ai_next": day + rng.randi_range(0, 6), "goal": -1, "name": _army_name(code)}
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

func _process(delta: float) -> void:
	if not running or speed_idx == 0 or _awaiting_deploy():
		return
	var spd: float = SPEEDS[speed_idx]
	if watching_battle >= 0 and slow_during_watch:
		spd = minf(spd, WATCH_DAYS_PER_SEC)
	accum += delta * spd
	var n := 0
	while accum >= 1.0 and n < 24:
		accum -= 1.0
		tick_day()
		n += 1

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
	if p[2] == 1:
		_month()
	day_passed.emit(day)

func _era_check() -> void:
	var e := GameData.era_for_year(cur_year_f())
	if e > era:
		era = e
		stats["era_changes"] += 1
		_port_reach.clear(); _neighbors_cache.clear(); _path_cache.clear()
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

func _economy_month(code: String, preview: bool = false) -> void:
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
	var need_sec := clampf(0.3 + 0.5 * army_men / garrison_need - n["exhaustion"] * 0.4 - 0.1 * _enemy_armies_inside(code), 0.0, 1.0)
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

func army_strength(a: Dictionary) -> float:
	var s := 0.0
	for u in a["units"]:
		s += u["men"] * unit_power(u["type"])
	return s

func unit_power(uid: String) -> float:
	var d: Dictionary = GameData.units[uid]
	return (float(d["melee"]) + float(d["defense"])) * 0.5 + float(d["lethality"]) * float(d["accuracy"]) * 40.0 + float(d["armor"]) * 25.0

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

func can_declare_war(a: String, b: String) -> Dictionary:
	if a == b or not nations.has(b) or not nations[b]["alive"]:
		return {"ok": false, "msg": "Invalid target"}
	if at_war(a, b):
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
	var broke_nap := has_treaty(a, b, "nap")
	_start_war(a, b)
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
	# defensive alliances: the target's allies are called to arms
	for c in allies_of(b):
		if c != a and not at_war(c, a) and not has_treaty(c, a, "alliance") and nations[c]["alive"]:
			_start_war(c, a)
			add_relation(c, a, -30.0)
			log_event("%s honours its alliance with %s and joins the war against %s." % [nations[c]["name"], nations[b]["name"], nations[a]["name"]], "war", [c, a, b], c != player)
	_neighbors_cache.clear(); _path_cache.clear()
	return true

func _start_war(a: String, b: String) -> void:
	wars[_key(a, b)] = {"start": day, "attacker": a, "score": {a: 0.0, b: 0.0}}

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
	_path_cache.clear()

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
	_neighbors_cache.clear()

func cancel_treaty(a: String, b: String, kind: String) -> void:
	if kind == "nap":
		_set_treaty(a, b, "nap", -1)
	else:
		_set_treaty(a, b, kind, false)
	add_relation(a, b, -15.0)
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

func passable(code: String, pid: int) -> bool:
	var o: String = prov_owner.get(pid, "")
	if o == "":
		return false
	return o == code or has_treaty(code, o, "alliance") or at_war(code, o)

## Dijkstra over provinces (+ sea crossings). Returns node list excluding start, or [] if unreachable.
func find_path(code: String, from_node: int, to_pid: int) -> Array:
	if from_node == to_pid:
		return []
	if not GameData.provinces.has(to_pid) or not passable(code, to_pid):
		return []
	var start := from_node
	var extra_head: Array = []
	if from_node >= GameData.SEA_NODE:
		# at sea: snap to the closest port
		var z: Dictionary = GameData.seazones[from_node - GameData.SEA_NODE]
		var best := -1; var bd := 1e9
		for port in z["ports"]:
			var d := GameData.node_km(from_node, port)
			if d < bd and passable(code, port):
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
			if not passable(code, nb):
				continue
			var nd: float = dist[u] + GameData.node_km(u, nb)
			if nd < dist.get(nb, 1e18):
				dist[nb] = nd; prev[nb] = u; via.erase(nb)
				_heap_push(heap, [nd, nb])
		for r in reach.get(u, []):
			var v: int = r["to"]
			if not passable(code, v):
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
		var why := "No route" if o == "" or passable(a["owner"], to_pid) else "Cannot enter %s territory without war or alliance" % nations[o]["name"]
		return {"ok": false, "msg": why}
	a["path"] = path
	a["progress"] = 0.0
	a["goal"] = to_pid
	if a["state"] == "siege":
		a["state"] = "idle"
	armies_changed.emit()
	return {"ok": true, "path": path, "days": int(ceil(path_km(a["owner"], a["node"], path) / army_speed(a)))}

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
			if nxt < GameData.SEA_NODE and not passable(a["owner"], nxt):
				a["path"] = []; a["progress"] = 0.0
				break
			a["progress"] -= d
			a["node"] = nxt
			a["path"].pop_front()
			if a["path"].is_empty():
				a["progress"] = 0.0
			if nxt < GameData.SEA_NODE:
				if sieges.has(nxt) and sieges[nxt]["army"] == aid:
					pass
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
			ar["path"] = [dest]; ar["progress"] = 0.0
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
	_add_war_score(new_owner, old, 15.0 if nations[old]["capital"] == pid else 8.0)
	_neighbors_cache.clear(); _path_cache.clear()
	log_event("%s captures %s from %s." % [nations[new_owner]["name"], GameData.provinces[pid]["name"], nations[old]["name"]], "capture", [new_owner, old], new_owner != player)
	ownership_changed.emit(pid, old, new_owner)
	if nations[old]["capital"] == pid and not nation_provs[old].is_empty():
		var best: int = nation_provs[old][0]
		for p in nation_provs[old]:
			if GameData.provinces[p]["population"] > GameData.provinces[best]["population"]:
				best = p
		nations[old]["capital"] = best
		log_event("%s moves its capital to %s." % [nations[old]["name"], GameData.provinces[best]["name"]], "info", [old])
	if nation_provs[old].is_empty():
		_eliminate(old, new_owner)

func _eliminate(code: String, by: String) -> void:
	nations[code]["alive"] = false
	stats["eliminated"] += 1
	for aid in armies.keys():
		if armies[aid]["owner"] == code:
			armies.erase(aid)
	for e in enemies_of(code):
		wars.erase(_key(code, e))
	log_event("%s has been conquered by %s and ceases to exist." % [nations[code]["name"], nations[by]["name"]], "capture", [code, by])
	armies_changed.emit()

# ======================= monthly =======================
func _month() -> void:
	for code in nations.keys():
		if nations[code]["alive"]:
			_economy_month(code)
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
		var p: PackedStringArray = k.split("|")
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
	var my_s := strength(code)
	var best := ""; var best_v := 0.0
	for t in neighbors_of(code):
		if not nations[t]["alive"] or not can_declare_war(code, t)["ok"] or has_treaty(code, t, "nap"):
			continue
		var their := strength(t)
		for al in allies_of(t):
			their += strength(al) * 0.7
		var ratio := my_s / maxf(their, 1.0)
		var rel := relation(code, t)
		var v := ratio * 10.0 - rel * 0.3 + (8.0 if not nations[t]["major"] else 0.0)
		if t == player:
			v += 2.0
		if ratio > 1.8 and rel < 10.0 and v > best_v:
			best_v = v; best = t
	if best != "" and rng.randf() < n["aggression"] * 0.045:
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
		if enemies.is_empty():
			if a["state"] == "idle" and a["path"].is_empty() and a["node"] >= GameData.SEA_NODE:
				order_move(aid, n["capital"])
			elif a["path"].is_empty() and prov_owner.get(a["node"], "") != code and not is_friendly(code, prov_owner.get(a["node"], "")):
				order_move(aid, n["capital"])
			continue
		if not a["path"].is_empty() or a["state"] == "siege":
			continue
		# defend: enemy armies inside our land
		var target := -1; var best := 1e18
		for o in armies.values():
			if o["node"] >= GameData.SEA_NODE or not at_war(code, o["owner"]):
				continue
			if prov_owner.get(o["node"], "") == code and army_strength(o) < my_s * 1.25:
				var d := GameData.node_km(a["node"], o["node"])
				if d < best:
					best = d; target = o["node"]
		if target < 0 and n["major"]:
			# attack: nearest enemy province that is not defended by a much stronger army
			for e in enemies:
				for pid in nation_provs[e]:
					var danger := 0.0
					for o in armies_in(pid):
						if at_war(code, o["owner"]):
							danger += army_strength(o)
					if danger > my_s * 1.1:
						continue
					var d := GameData.node_km(a["node"], pid) * (0.7 if nations[e]["capital"] == pid else 1.0)
					if d < best:
						best = d; target = pid
		if target < 0 and not n["major"] and a["node"] != n["capital"]:
			target = n["capital"]
		if target >= 0 and target != a["node"]:
			order_move(aid, target)

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
	"stats", "pending_offers", "ai_enabled", "slow_during_watch"]
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
	_port_reach.clear(); _neighbors_cache.clear(); _path_cache.clear()
	# A battle that was being watched continues off-screen after loading (no 3D view is open).
	watching_battle = -1
	for b in battles.values():
		if b["watched"]:
			b["watched"] = false
			if b["sim"] != null:
				b["sim"].record_events = false
	running = true
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
