class_name BattleSim
extends RefCounted
## Deterministic regiment-level battle model. Fixed 0.1 s step, seeded RNG.
## The same model is stepped either by the strategic clock (unwatched) or in real time by the
## 3D battle view (watched); the visuals only read state + events, they never change the outcome.

const DT := 0.1
const MAX_TIME := 80.0
const KF := 0.33          # ranged kill factor
const MK := 0.028         # melee kill factor
const MORALE_PER_LOSS := 230.0
const CHARGE_ELAN := 0.7      # morale shock from missiles while a regiment is running in to close (v0.5)
const COUNTER_CHARGE_GAP := 75.0     # a holding melee regiment under missile fire counter-charges within this gap (v0.5)
const COUNTER_CHARGE_FAR := 150.0    # ...and from as far as bow/musket range once fire has cost it 60% of its morale (v0.5)

const FORMATIONS := {
	"line": {"ranks": 3, "fire": 1.0, "melee_def": 1.0, "morale": 0.0, "label": "Line"},
	"deep": {"ranks": 6, "fire": 0.7, "melee_def": 1.25, "morale": 10.0, "label": "Deep column"},
	"wide": {"ranks": 2, "fire": 1.12, "melee_def": 0.85, "morale": -6.0, "label": "Wide screen"},
}
const OBJECTIVES := ["assault", "hold", "flank", "bombard"]
## Per-era pacing: [kill scale, deployment half-distance m]. Tuned so typical battles last ~30-40 s.
static var ERA_TUNE := {"medieval": [3.27, 42.0], "early_modern": [4.03, 48.0], "c19": [2.38, 60.0], "c20": [0.49, 90.0], "modern": [0.185, 120.0]}
var kill_scale := 1.0
var deploy_z := 42.0

var t := 0.0
var steps := 0
var rng := RandomNumberGenerator.new()
var regs: Array = []
var done := false
var winner := -1
var events: Array = []
var record_events := true
var terrain := "plains"
var seed_value := 0
var orders: Array = [{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}]
var side_names := ["Attacker", "Defender"]
var start_men := [0.0, 0.0]

## sides: Array of 2 Arrays of {army_id, unit_index, type, men}
func setup(sides: Array, terr: String, ord: Array, seed: int) -> void:
	terrain = terr
	orders = ord
	seed_value = seed
	rng.seed = seed
	regs.clear()
	for side in 2:
		var lst: Array = sides[side]
		var form: Dictionary = FORMATIONS[orders[side].get("formation", "line")]
		for u in lst:
			var d: Dictionary = GameData.units[u["type"]]
			var men := float(u["men"])
			var nvis := clampi(int(round(float(d["visual_men"]) * men / float(d["men"]))), 2 if d["kind"] in ["veh", "gun"] else 6, int(d["visual_men"]))
			var ranks := 1
			var sp := Vector2(1.3, 1.3)
			match d["kind"]:
				"vat":
					ranks = int(form["ranks"]); sp = Vector2(1.25, 1.35)
				"cav":
					ranks = maxi(2, int(form["ranks"]) - 1); sp = Vector2(2.2, 3.4)
				"gun":
					ranks = 1; sp = Vector2(9.0, 4.0)
				"veh":
					ranks = 1 if nvis <= 4 else 2; sp = Vector2(11.0, 10.0)
			var files := int(ceil(float(nvis) / ranks))
			regs.append({
				"side": side, "army_id": u["army_id"], "unit_index": u["unit_index"], "type": u["type"], "def": d,
				"role": d["role"], "kind": d["kind"], "men": men, "men0": men, "nvis": nvis, "ranks": ranks, "files": files,
				"spacing": sp, "width": files * sp.x, "depth": ranks * sp.y,
				"morale": float(d["morale"]) + float(form["morale"]), "morale0": float(d["morale"]) + float(form["morale"]),
				"pos": Vector2.ZERO, "facing": Vector2(0, -1 if side == 0 else 1), "state": "idle", "target": -1,
				"fire_cd": 0.0, "last_hit": -10.0, "contact_t": -1.0, "rout_t": -1.0, "moving": false, "running": false,
				"kills": 0.0, "fired": 0, "charged": false})
		start_men[side] = 0.0
	for r in regs:
		start_men[r["side"]] += r["men"]
	var era_votes := {}
	for r in regs:
		era_votes[r["def"]["era"]] = era_votes.get(r["def"]["era"], 0.0) + r["men"]
	var main_era := "c19"; var bv := -1.0
	for e in era_votes.keys():
		if era_votes[e] > bv:
			bv = era_votes[e]; main_era = e
	kill_scale = ERA_TUNE.get(main_era, [1.0, 42.0])[0]
	deploy_z = ERA_TUNE.get(main_era, [1.0, 42.0])[1]
	# lopsided battles are slowed down so the weaker side still makes a fight of it (pacing, not outcome)
	var lo := minf(start_men[0], start_men[1]); var hi := maxf(maxf(start_men[0], start_men[1]), 1.0)
	kill_scale *= clampf(pow(lo / hi, 0.5), 0.4, 1.0)
	_deploy()

func _deploy() -> void:
	for side in 2:
		var zdir := 1.0 if side == 0 else -1.0
		var front: Array = []; var cav: Array = []; var rear: Array = []
		for i in regs.size():
			var r: Dictionary = regs[i]
			if r["side"] != side:
				continue
			match r["role"]:
				"cav": cav.append(i)
				"art": rear.append(i)
				_: front.append(i)
		var base_z := deploy_z * zdir
		var gap := 6.0
		var total := -gap
		for i in front:
			total += regs[i]["width"] + gap
		var x := -total / 2.0
		for i in front:
			var r: Dictionary = regs[i]
			r["pos"] = Vector2(x + r["width"] / 2.0, base_z + r["depth"] / 2.0 * zdir)
			x += r["width"] + gap
		var left := -total / 2.0 - 10.0; var right := total / 2.0 + 10.0
		for k in cav.size():
			var r: Dictionary = regs[cav[k]]
			if k % 2 == 0:
				r["pos"] = Vector2(right + r["width"] / 2.0, base_z + 8.0 * zdir); right += r["width"] + gap
			else:
				r["pos"] = Vector2(left - r["width"] / 2.0, base_z + 8.0 * zdir); left -= r["width"] + gap
		var rtotal := -gap
		for i in rear:
			rtotal += regs[i]["width"] + gap
		var rx := -rtotal / 2.0
		for i in rear:
			var r: Dictionary = regs[i]
			r["pos"] = Vector2(rx + r["width"] / 2.0, base_z + 34.0 * zdir); rx += r["width"] + gap

func active(r: Dictionary) -> bool:
	return r["state"] != "rout" and r["state"] != "fled" and r["state"] != "dead"

func side_active(side: int) -> int:
	var n := 0
	for r in regs:
		if r["side"] == side and active(r):
			n += 1
	return n

func side_men(side: int) -> float:
	var m := 0.0
	for r in regs:
		if r["side"] == side:
			m += r["men"]
	return m

func side_morale(side: int) -> float:
	var m := 0.0; var w := 0.0
	for r in regs:
		if r["side"] == side and active(r):
			m += maxf(r["morale"], 0.0) / r["morale0"] * r["men"]; w += r["men"]
	return m / w if w > 0 else 0.0

func _ev(e: Dictionary) -> void:
	if record_events:
		e["t"] = t
		events.append(e)

func run_seconds(sec: float) -> void:
	var n := int(round(sec / DT))
	for i in n:
		if done:
			return
		step()

func run_to_end() -> void:
	while not done:
		step()

func step() -> void:
	if done:
		return
	steps += 1
	t = steps * DT
	var retarget := steps % 10 == 1
	for i in regs.size():
		var r: Dictionary = regs[i]
		if r["state"] == "rout":
			_step_rout(i, r)
			continue
		if not active(r):
			continue
		if retarget or r["target"] < 0 or not active(regs[r["target"]]):
			r["target"] = _pick_target(i, r)
		if r["target"] < 0:
			r["state"] = "idle"; r["moving"] = false
			continue
		_step_reg(i, r)
	_separate()
	_morale_and_rout()
	_check_end()

func _pick_target(i: int, r: Dictionary) -> int:
	var best := -1; var bd := 1e9
	var obj: String = orders[r["side"]].get("objective", "assault")
	for j in regs.size():
		var e: Dictionary = regs[j]
		if e["side"] == r["side"] or not active(e):
			continue
		var d: float = r["pos"].distance_to(e["pos"])
		if r["role"] == "cav" and obj == "flank":
			# prefer exposed flanks and artillery
			if e["role"] == "art":
				d *= 0.5
			d -= absf(e["pos"].x) * 0.6
		if r["role"] == "art" and _in_melee_with_friend(j, r["side"]):
			d *= 3.0
		if d < bd:
			bd = d; best = j
	return best

func _in_melee_with_friend(j: int, side: int) -> bool:
	var e: Dictionary = regs[j]
	for f in regs:
		if f["side"] == side and f["state"] == "melee" and f["target"] == j:
			return true
	return false

func _front_gap(r: Dictionary, e: Dictionary) -> float:
	return r["pos"].distance_to(e["pos"]) - (r["depth"] + e["depth"]) * 0.5

func _step_reg(i: int, r: Dictionary) -> void:
	var e: Dictionary = regs[r["target"]]
	var d: Dictionary = r["def"]
	var side: int = r["side"]
	var obj: String = orders[side].get("objective", "assault")
	if obj == "hold" and side == 0 and t > 15.0:
		obj = "assault"  # the attacker cannot wait forever
	var gap := _front_gap(r, e)
	var to_e: Vector2 = (e["pos"] - r["pos"]).normalized()
	# face the target (turn rate limited)
	var ang: float = r["facing"].angle_to(to_e)
	r["facing"] = r["facing"].rotated(clampf(ang, -1.6 * DT, 1.6 * DT))
	var rng_m := float(d["range"])
	var can_fire = rng_m > 0.0 and r["role"] != "cav"
	r["moving"] = false; r["running"] = false
	# enemy in contact with us forces melee
	var engaged := gap <= 1.6
	if not engaged:
		for j in regs.size():
			var o: Dictionary = regs[j]
			if o["side"] != side and active(o) and o["state"] == "melee" and o["target"] == i:
				engaged = true; r["target"] = j; e = o; gap = _front_gap(r, e)
				break
	if engaged and r["role"] != "art":
		if r["state"] != "melee":
			r["contact_t"] = t
			if r["role"] == "cav" and not r["charged"]:
				r["charged"] = true
				e["morale"] -= 12.0
				_ev({"k": "charge", "s": i, "d": r["target"]})
		r["state"] = "melee"
		_melee(i, r, e)
		return
	if engaged and r["role"] == "art":
		r["state"] = "melee"
		_melee(i, r, e)
		return
	if can_fire and gap <= rng_m:
		r["state"] = "fire"
		var advancing := false
		# melee-capable infantry under assault keeps closing while firing only if it is a melee unit
		if r["role"] == "armor" and obj == "assault" and gap > rng_m * 0.45:
			advancing = true
		if advancing:
			_move_towards(r, e["pos"], float(d["speed"]) * 0.8, gap - rng_m * 0.4)
		r["fire_cd"] -= DT
		if r["fire_cd"] <= 0.0:
			r["fire_cd"] = float(d["fire_interval"]) * rng.randf_range(0.9, 1.1)
			_volley(i, r, e, gap, 0.75 if advancing else 1.0)
		return
	# out of range / melee unit: decide whether to advance
	var go := true
	if obj == "hold" and r["role"] != "cav":
		# a melee-only regiment holds its ground, but does not stand still to be shot down: when missiles are
		# landing on it and the shooters are within charge distance, it counter-charges (v0.5)
		var under_fire: bool = t - float(r["last_hit"]) < 4.5 and float(r["last_hit"]) > 0.0
		var worn: bool = float(r["morale"]) < float(r["morale0"]) * 0.4
		go = (gap < 22.0 or (under_fire and (gap < COUNTER_CHARGE_GAP or (worn and gap < COUNTER_CHARGE_FAR)))) and r["role"] != "art" and not can_fire
		if go and gap >= 22.0:
			r["left_line"] = true      # it gave up its prepared position: no "hold" defence bonus any more
	elif obj == "bombard" and r["role"] in ["inf", "cav"]:
		go = t > 16.0 or side_morale(1 - side) < 0.6
	if r["role"] == "art":
		go = false
	if go:
		var spd := float(d["speed"])
		var target_pos: Vector2 = e["pos"]
		if r["role"] == "cav" and obj == "flank" and not r["charged"] and e["role"] != "cav" and t < 30.0:
			var flank_pt: Vector2 = e["pos"] + Vector2(signf(r["pos"].x - e["pos"].x + 0.01) * (e["width"] * 0.5 + 18.0), 0)
			if r["pos"].distance_to(flank_pt) > 12.0:
				target_pos = flank_pt
		var charge_dist := 70.0 if r["role"] != "cav" else 90.0
		if gap < charge_dist and obj != "hold":
			spd *= 1.8 if r["role"] == "cav" else 2.6
			r["running"] = true
		r["state"] = "advance"
		_move_towards(r, target_pos, spd, gap - 1.0)
	else:
		r["state"] = "hold"

func _move_towards(r: Dictionary, p: Vector2, spd: float, max_dist: float) -> void:
	var v: Vector2 = p - r["pos"]
	var dist := minf(spd * DT, maxf(max_dist, 0.0))
	if v.length() < 0.01 or dist <= 0.0:
		return
	r["pos"] += v.normalized() * dist
	r["moving"] = true

func _terrain_fire_mod() -> float:
	match terrain:
		"forest", "jungle": return 0.72
		"hills": return 0.9
		"mountains": return 0.82
	return 1.0

func _volley(i: int, r: Dictionary, e: Dictionary, gap: float, eff: float) -> void:
	var d: Dictionary = r["def"]
	var form: Dictionary = FORMATIONS[orders[r["side"]].get("formation", "line")]
	var shooters: float = r["men"] * (float(form["fire"]) if r["kind"] == "vat" else 1.0) * eff
	var rng_m := float(d["range"])
	var dist_f := clampf(1.25 - 0.75 * gap / rng_m, 0.35, 1.2)
	var pen := clampf(float(d["lethality"]) / 4.0, 0.0, 1.0)
	var armor_f := 1.0 - float(e["def"]["armor"]) * (1.0 - pen)
	var cover := 1.0
	if e["side"] == 1 and orders[1].get("objective", "") == "hold" and not e.get("left_line", false):
		cover = 0.85
	var density := 1.0
	if r["role"] == "art":
		density = 1.0 + 0.08 * float(e["ranks"])
	var kills := shooters * float(d["accuracy"]) * dist_f * _terrain_fire_mod() * armor_f * float(d["lethality"]) * KF * kill_scale * _ramp() * cover * density * rng.randf_range(0.8, 1.2)
	kills = minf(kills, e["men"])
	e["men"] -= kills
	# troops running in to close the distance take the morale shock of missile losses with some élan (v0.5)
	var shock: float = kills / e["men0"] * MORALE_PER_LOSS * (1.2 if r["role"] == "art" else 1.0)
	if e["running"] and e["state"] == "advance":
		shock *= CHARGE_ELAN
	e["morale"] -= shock
	e["last_hit"] = t
	r["kills"] += kills
	r["fired"] += 1
	_ev({"k": "volley", "s": i, "d": r["target"], "kills": kills})

func _melee(i: int, r: Dictionary, e: Dictionary) -> void:
	var d: Dictionary = r["def"]
	var ed: Dictionary = e["def"]
	var def_mod := float(FORMATIONS[orders[e["side"]].get("formation", "line")]["melee_def"])
	if e["side"] == 1:
		if orders[1].get("objective", "") == "hold" and not e.get("left_line", false):
			def_mod *= 1.2
		if terrain in ["hills", "mountains"]:
			def_mod *= 1.15
	var charge_f := 1.0
	var since := t - float(r["contact_t"])
	if since < 2.5:
		charge_f = 2.3 if r["role"] == "cav" else 1.4
	var flank_f := 1.0
	var dirv: Vector2 = (r["pos"] - e["pos"]).normalized()
	var dp: float = e["facing"].dot(dirv)
	if dp < -0.5:
		flank_f = 2.0
	elif dp < 0.3:
		flank_f = 1.5
	var atk := float(d["melee"])
	var kps: float = r["men"] * atk / (atk + float(ed["defense"]) * def_mod) * MK * kill_scale * _ramp() * charge_f * flank_f
	var armor_f := 1.0 - float(ed["armor"]) * (0.5 if r["kind"] in ["veh"] else 0.85)
	var kills := minf(kps * armor_f * DT * rng.randf_range(0.8, 1.2), e["men"])
	e["men"] -= kills
	e["morale"] -= kills / e["men0"] * MORALE_PER_LOSS + (0.8 * DT if flank_f > 1.0 else 0.0)
	e["last_hit"] = t
	r["kills"] += kills
	r["mkills"] = r.get("mkills", 0.0) + kills   # melee share (era verification)

func _step_rout(i: int, r: Dictionary) -> void:
	var away := Vector2(0, 1 if r["side"] == 0 else -1)
	r["facing"] = away
	r["pos"] += away * float(r["def"]["speed"]) * 2.4 * DT
	r["running"] = true; r["moving"] = true
	r["men"] -= r["men"] * 0.006 * DT * 10.0 * DT
	if t - float(r["rout_t"]) > 9.0:
		r["state"] = "fled"; r["moving"] = false

func _separate() -> void:
	for a in regs.size():
		var ra: Dictionary = regs[a]
		if not active(ra):
			continue
		for b in range(a + 1, regs.size()):
			var rb: Dictionary = regs[b]
			if rb["side"] != ra["side"] or not active(rb):
				continue
			var dv: Vector2 = rb["pos"] - ra["pos"]
			var need: float = (ra["width"] + rb["width"]) * 0.5 + 2.0
			if absf(dv.x) < need and absf(dv.y) < (ra["depth"] + rb["depth"]) * 0.5:
				var push := (need - absf(dv.x)) * 0.1
				var sx := signf(dv.x) if absf(dv.x) > 0.01 else (1.0 if b % 2 == 0 else -1.0)
				ra["pos"].x -= sx * push; rb["pos"].x += sx * push

func _morale_and_rout() -> void:
	var lost := [0, 0]; var tot := [0, 0]
	for r in regs:
		tot[r["side"]] += 1
		if not active(r):
			lost[r["side"]] += 1
	for i in regs.size():
		var r: Dictionary = regs[i]
		if not active(r):
			continue
		if t - float(r["last_hit"]) > 3.0 and r["state"] != "melee":
			r["morale"] = minf(r["morale"] + 1.0 * DT, r["morale0"])
		if tot[r["side"]] > 0 and float(lost[r["side"]]) / tot[r["side"]] > 0.55:
			r["morale"] -= 2.0 * DT
		if r["men"] <= 1.0:
			r["men"] = 0.0; r["state"] = "dead"
			_ev({"k": "destroyed", "s": i})
			continue
		if r["morale"] <= 0.0 or r["men"] < r["men0"] * 0.22:
			r["state"] = "rout"; r["rout_t"] = t; r["target"] = -1
			_ev({"k": "rout", "s": i})
			for f in regs:
				if f["side"] == r["side"] and active(f) and f["pos"].distance_to(r["pos"]) < 60.0:
					f["morale"] -= 6.0

## Decisive phase: after 28 s fighting intensifies (fatigue, commitment of reserves) so battles conclude.
func _ramp() -> float:
	return 1.0 + maxf(t - 28.0, 0.0) * 0.12

func _active_men(side: int) -> float:
	var m := 0.0
	for r in regs:
		if r["side"] == side and active(r):
			m += r["men"]
	return m

func _check_end() -> void:
	# a broken remnant facing a much larger force withdraws from the field
	for sd in 2:
		var mine := _active_men(sd); var theirs := _active_men(1 - sd)
		if mine > 0.0 and mine < start_men[sd] * 0.25 and theirs > mine * 2.0 and t > 16.0:
			for i in regs.size():
				var r: Dictionary = regs[i]
				if r["side"] == sd and active(r):
					r["state"] = "rout"; r["rout_t"] = t; r["target"] = -1
					_ev({"k": "rout", "s": i})
	var a := side_active(0); var b := side_active(1)
	if a == 0 or b == 0 or t >= MAX_TIME:
		done = true
		if a == 0 and b == 0:
			winner = 1
		elif a == 0:
			winner = 1
		elif b == 0:
			winner = 0
		else:
			var p0 := side_men(0) * side_morale(0)
			var p1 := side_men(1) * side_morale(1) * 1.1
			winner = 0 if p0 > p1 else 1
		_ev({"k": "end", "winner": winner})

func result() -> Dictionary:
	var men := []
	for r in regs:
		men.append(r["men"])
	return {"winner": winner, "time": t, "men": men, "steps": steps,
		"losses": [start_men[0] - side_men(0), start_men[1] - side_men(1)], "start": start_men.duplicate()}

static func ai_orders(my_units: Array, enemy_units: Array, defending: bool, terr: String) -> Dictionary:
	var mine := 0.0; var theirs := 0.0; var cav := 0.0; var art := 0.0
	for u in my_units:
		var d: Dictionary = GameData.units[u["type"]]
		var p := float(u["men"]) * (float(d["melee"]) + float(d["defense"]) + float(d["lethality"]) * 10.0)
		mine += p
		if d["role"] == "cav": cav += p
		if d["role"] == "art": art += p
	for u in enemy_units:
		var d: Dictionary = GameData.units[u["type"]]
		theirs += float(u["men"]) * (float(d["melee"]) + float(d["defense"]) + float(d["lethality"]) * 10.0)
	var obj := "assault"
	if defending and (mine < theirs * 1.1 or terr in ["hills", "mountains"]):
		obj = "hold"
	elif art > mine * 0.3:
		obj = "bombard"
	elif cav > mine * 0.3:
		obj = "flank"
	var form := "line"
	if mine < theirs * 0.7:
		form = "deep"
	return {"objective": obj, "formation": form}

# ======================= save / load =======================
const STATE_FIELDS := ["kill_scale", "deploy_z", "t", "steps", "regs", "done", "winner", "events", "record_events",
	"terrain", "seed_value", "orders", "side_names", "start_men"]

func to_dict() -> Dictionary:
	var d := {"rng_seed": rng.seed, "rng_state": rng.state}
	for f in STATE_FIELDS:
		var v: Variant = get(f)
		d[f] = v.duplicate(true) if (v is Array or v is Dictionary) else v
	return d

static func from_dict(d: Dictionary) -> BattleSim:
	var s := BattleSim.new()
	for f in STATE_FIELDS:
		var v: Variant = d[f]
		s.set(f, v.duplicate(true) if (v is Array or v is Dictionary) else v)
	s.rng.seed = d["rng_seed"]
	s.rng.state = d["rng_state"]
	return s
