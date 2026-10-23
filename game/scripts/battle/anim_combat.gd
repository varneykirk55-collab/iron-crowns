extends RefCounted
## Combat animation v1 (Rob, proto/anim-combat-v1). PRESENTATION ONLY: reads BattleSim state, never writes it, never
## draws from BattleView.rng except exactly where the legacy code already did (volley), so the outcome and the view's
## random sequence are unchanged. Off by default: BattleView enables it with the user arg --anim-v1 (or AnimCombat.on).
##
## Uses the clips baked by pipeline/blender/soldier_anim_combat.py (legacy rig: pk_*) and char_anim_combat.py
## (c19sr: mk_*). A model without those clips falls back to the legacy per-soldier loop untouched.
##  * 1300 spears: formation stops at a contact gap (no interpenetration), front two ranks run a per-soldier
##    guard -> thrust -> recover cycle (hash-desynced), neighbours of a casualty flinch (pk_hit), deaths alternate
##    die / pk_collapse, a broken regiment holds for a staggered moment, each soldier turns ~180 deg in 0.3-0.6 s and
##    whole regiment turns at once and walks away as one body at the normal pace and cadence (pk_withdraw; no stagger,
##    stragglers or glance-backs; the view no longer follows the sim's 2.4x rout speed); advance = pk_advance (no foot slide at 1.4 m/s), charge = pk_charge.
##  * c19 muskets: front ranks bring the musket up (mk_aim) as the sim's fire cooldown runs out, each shot plays
##    mk_fire with the flash / smoke / ball spawned from the baked muzzle position at the shot frame, then mk_reload
##    (speed fitted to the unit's fire interval) and back to shoulder arms; march = mk_march.
##  * medieval archers: arrow leaves from the bow hand at the release moment of the existing fire clip.

const BattleVisuals := preload("res://scripts/battle/battle_visuals.gd")

static var on := false
static var dbg_k := -1        # demo/debug only: record what instance dbg_k of regiment 0 is fed (clip row, time, LOD, buffer slot)
static var dbg := {}

const G_SPEAR := 2.7        # m between the two front ranks in melee (spear reach), sim engages at <= 1.6
const TURN_RATE := 3.2      # rad/s, soldiers turn instead of snapping
const THRUST_S := 14.0 / 24.0
const RECOVER_S := 12.0 / 24.0
const HIT_S := 14.0 / 24.0
const AIM_S := 16.0 / 24.0
const FIRE_S := 12.0 / 24.0
const RELOAD_S := 62.0 / 24.0
const BOW_RELEASE := 0.9    # s into the legacy bow fire clip
const MAX_FLASH := 24
const MAX_SMOKE := 14

# per-soldier action ids (v["ac_act"])
enum {A_NONE, A_THRUST, A_HIT, A_AIM, A_FIRE}

static func h(a: float, b: float) -> float:
	return fposmod(sin(a * 12.9898 + b * 78.233) * 43758.5453, 1.0)

static func clips_of(bv, model: String) -> Dictionary:
	return bv.vat[model]["json"][0]["clips"]

static func kind_of(bv, v: Dictionary) -> int:
	## 1 = spear (pk_*), 2 = musket (mk_*), 3 = cavalry (hv_* gaits), 0 = not handled
	if v.has("ac_kind"):
		return v["ac_kind"]
	var k := 0
	if v["kind"] == "vat":
		var c := clips_of(bv, v["model"])
		if c.has("pk_guard") and c.has("pk_thrust"):
			k = 1
		elif c.has("mk_aim") and c.has("mk_reload"):
			k = 2
	elif v["kind"] == "cav":
		if clips_of(bv, v["model"]).has("hv_walk"):
			k = 3
	v["ac_kind"] = k
	return k

static func _init_state(v: Dictionary) -> void:
	if v.has("ac_act"):
		return
	var n: int = v["n"]
	var a := PackedInt32Array(); a.resize(n)
	var t := PackedFloat32Array(); t.resize(n); t.fill(-100.0)
	var nx := PackedFloat32Array(); nx.resize(n); nx.fill(-1.0)
	var hit := PackedFloat32Array(); hit.resize(n); hit.fill(-100.0)
	var seen := PackedFloat32Array(); seen.resize(n); seen.fill(-1.0)
	v["ac_act"] = a; v["ac_t"] = t; v["ac_next"] = nx; v["ac_hit"] = hit; v["ac_seen"] = seen
	v["ac_shift"] = Vector2.ZERO; v["ac_rout_t"] = -1.0; v["ac_cyc"] = PackedInt32Array(); v["ac_cyc"].resize(n)
	v["ac_turn"] = PackedFloat32Array(); v["ac_turn"].resize(n)
	v["ac_shots"] = []

static func _clip(bv, model: String, name: String) -> Vector2:
	return bv._clip(model, name)

## model-space point -> world, the exact transform BattleView._put gives the instance (yaw a, origin o)
static func to_world(a: float, o: Vector3, l: Vector3) -> Vector3:
	var c := cos(a); var s := sin(a)
	return Vector3(c * l.x + s * l.z + o.x, l.y + o.y, -s * l.x + c * l.z + o.z)

static func tip_local(bv, model: String, clip: String, frame: int, fallback: Vector3) -> Vector3:
	var c: Dictionary = clips_of(bv, model).get(clip, {})
	for key in ["weapon_tip", "prop_tip"]:   # BJORN's weapon_tip bone data first, then our prop-axis bake
		if c.has(key):
			var arr: Array = c[key]
			var p: Array = arr[clampi(frame, 0, arr.size() - 1)]
			return Vector3(p[0], p[1], p[2])
	return fallback

## Per-regiment update replacing BattleView's per-soldier loop. Returns false if the model is not handled.
static func update_soldiers(bv, i: int, v: Dictionary, r: Dictionary, dt: float, vt: float, cpos: Vector3) -> bool:
	var kind := kind_of(bv, v)
	if v.has("ac_shots"):
		_flush_shots(bv, v, r, vt)
	if kind == 0:
		return false
	if kind == 3:
		_update_cav(bv, i, v, r, dt, vt, cpos)
		return true
	_init_state(v)
	var n: int = v["n"]
	var files: int = v["files"]
	var model: String = v["model"]
	var facing: Vector2 = r["facing"]
	var center: Vector2 = r["pos"]
	var st: String = r["state"]
	var routing := st == "rout" or st == "fled"
	# the sim flips a broken regiment's facing at once; keep the pre-rout layout (no ranks walking through each other)
	if not routing:
		v["ac_face"] = facing
	elif v.has("ac_face"):
		facing = v["ac_face"]
	var hidden: bool = st == "fled" and center.length() > 260.0
	var spd_base: float = float(r["def"]["speed"]) * (2.6 if r["running"] else 1.0)
	var enemy_pos := center + facing * 3.0
	var tgt: int = r["target"]
	if tgt >= 0:
		enemy_pos = bv.sim.regs[tgt]["pos"]
	var toward := (enemy_pos - center).normalized() if (enemy_pos - center).length() > 0.1 else facing
	if routing:
		toward = facing
	var pos: PackedVector2Array = v["pos"]; var yaw: PackedFloat32Array = v["yaw"]
	var clip: PackedInt32Array = v["clip"]; var clip_t: PackedFloat32Array = v["clip_t"]
	var phase: PackedFloat32Array = v["phase"]; var dead: PackedFloat32Array = v["dead"]
	var act: PackedInt32Array = v["ac_act"]; var act_t: PackedFloat32Array = v["ac_t"]; var nxt: PackedFloat32Array = v["ac_next"]
	var turn: PackedFloat32Array = v["ac_turn"]
	var hit_t: PackedFloat32Array = v["ac_hit"]; var seen: PackedFloat32Array = v["ac_seen"]; var cyc: PackedInt32Array = v["ac_cyc"]
	var side: int = r["side"]
	var sr: bool = bv.vat[model].has("sr")
	var fi := float(i)
	# ---- melee contact gap: shift the whole block so the two front ranks stand a spear's length apart
	var shift_want := Vector2.ZERO
	if kind == 1 and st == "melee" and tgt >= 0:
		var e: Dictionary = bv.sim.regs[tgt]
		var gap: float = center.distance_to(e["pos"]) - (float(r["depth"]) + float(e["depth"])) * 0.5
		var share := 0.5 if kind_of(bv, bv.rv[tgt]) == 1 else 1.0
		shift_want = toward * clampf((gap - G_SPEAR) * share, -12.0, 0.0)
	var shift: Vector2 = v["ac_shift"]
	shift = shift.lerp(shift_want, minf(dt * 2.5, 1.0))
	v["ac_shift"] = shift
	# ---- rout bookkeeping
	if routing and float(v["ac_rout_t"]) < 0.0:
		v["ac_rout_t"] = vt
		v["ac_rc"] = v.get("ac_lastc", center); v["ac_rshift"] = shift
	elif not routing:
		v["ac_rout_t"] = -1.0; v["ac_lastc"] = center
		v.erase("ac_vis_c"); v.erase("ac_vis_f")
	var rt: float = vt - float(v["ac_rout_t"])
	# retreat at the regiment's NORMAL marching pace (the sim's rout runs at 2.4x; the view does not follow it):
	# a visual centre walks away from where the line broke at def.speed, soldiers keep their slots around it
	var walk_v: float = float(r["def"]["speed"])
	var rc: Vector2 = v.get("ac_rc", center)
	var rshift: Vector2 = v.get("ac_rshift", Vector2.ZERO)
	if routing:
		var vis_c := rc - facing * walk_v * maxf(rt - 0.9, 0.0)
		v["ac_vis_c"] = vis_c; v["ac_vis_f"] = -facing
		hidden = st == "fled" and vis_c.length() > 260.0
		v["ac_vis_hidden"] = hidden
	# ---- casualties seen this frame -> neighbours flinch
	if kind == 1:
		for k in n:
			if dead[k] >= 0.0 and seen[k] < 0.0:
				seen[k] = dead[k]
				for nb in [k - 1, k + 1, k - files, k + files]:
					if nb >= 0 and nb < n and dead[nb] < 0.0 and (nb / files == k / files or nb % files == k % files):
						if act[nb] != A_THRUST or vt - act_t[nb] > THRUST_S * 0.6:
							hit_t[nb] = dead[k] + 0.05
	# ---- reload speed so aim + fire + reload fit inside the fire interval
	var fint := maxf(float(r["def"].get("fire_interval", 4.0)), 1.0)
	var reload_spd := clampf(RELOAD_S / maxf(fint * 0.9 - AIM_S - FIRE_S - 0.35, 0.8), 0.85, 2.2)
	for k in n:
		var p: Vector2 = pos[k]
		var dk := dead[k]
		var cname := ""; var ct := 0.0; var spd := 1.0; var cur := 0
		if dk < 0.0:
			var rank := k / files
			var slot: Vector2 = bv._slot_world(r, v, k, center, facing) + shift
			var dv := slot - p
			var dist := dv.length()
			var maxs := maxf(spd_base, 1.0) * 1.35 * dt
			var face := facing
			var hk := h(fi * 131.0 + float(k), 1.0)
			if routing:
				# all-or-nothing retreat at normal pace (Kirk): the whole regiment turns at the same moment (one turn time,
				# no rear-first order, no stragglers, no late starts), then walks off together at the regiment's normal
				# speed and cadence; only a slight per-soldier phase in the walk cycle so it is not robotic
				var delay := 0.15
				var turn_d := 0.45
				var away := -facing
				var et := rt - delay   # time since this soldier started to turn
				var vs := walk_v   # one pace for the whole body
				if et < 0.0:
					face = toward if toward.length() > 0.5 else facing
					cname = "pk_guard" if kind == 1 else "idle"; ct = -phase[k] * 2.0; cur = 12 if kind == 1 else 0
				else:
					# distance walked: starts as the turn completes, short ease from rest (0.35 s), then constant vs
					var tw := et - turn_d * 0.7
					var dist_w := 0.0
					if tw > 0.0:
						dist_w = vs * (tw * tw / 0.7 if tw < 0.35 else tw - 0.175)
					var lat := Vector2(-away.y, away.x)
					var loosen := clampf(et / 10.0, 0.0, 1.0) * 0.35   # the block stays a block
					var slot0: Vector2 = bv._slot_world(r, v, k, rc, facing) + rshift
					var tgt_p := slot0 + away * dist_w + lat * (h(float(k), fi + 51.0) - 0.5) * 2.4 * loosen
					var dv2 := tgt_p - p
					var d2v := dv2.length()
					var p0 := p
					if d2v > 0.001:
						p += dv2 / d2v * minf(d2v, vs * 1.02 * dt)   # hard cap: never above this soldier's pace
					var vel := (p - p0) / maxf(dt, 1e-4)
					var sp := vel.length()
					# heading: the flight direction (with a per-soldier bias so they turn both ways), then the velocity
					face = away.rotated(0.12)   # everyone wheels the same way
					if et > turn_d and sp > 0.3:
						face = vel / sp
					var cad := clampf(vs / 1.4, 0.6, 1.8)   # same cadence law as the normal advance (pk_advance / mk_march)
					if kind == 2:
						cname = "mk_march"; ct = -phase[k] * 3.0; spd = cad; cur = 20
						if sp < 0.2:
							cname = "idle"; spd = 1.0; cur = 0
					else:
						# pk_flee is no longer used for the retreat (it read as a sprint): everyone walks
						cname = "pk_withdraw"; cur = 17   # no glance-backs (read as hesitation)
						ct = -phase[k]; spd = cad
						if sp < 0.2:
							cname = "pk_guard"; ct = -phase[k] * 2.0; spd = 1.0; cur = 12
				turn[k] = PI / turn_d
			else:
				var moving := dist > 0.35
				if dist > 0.001:
					p += dv / dist * minf(dist, maxs if dist < 8.0 else maxs * 2.0)
				if moving and dist > 1.0:
					face = dv.normalized()
				if st == "melee":
					face = toward
				var walk := moving and dist > 0.6
				var spd_w := clampf(spd_base / 1.4, 0.6, 1.8) * (0.96 + 0.08 * hk)
				if walk:
					var run: bool = r["running"] or dist > 4.0
					if kind == 1:
						cname = "pk_charge" if run else "pk_advance"; cur = 11 if run else 10
						spd = (1.0 + phase[k] * 0.12) if run else spd_w
					else:
						cname = "run" if run else "mk_march"; cur = 2 if run else 20
						spd = (1.0 + phase[k] * 0.15) if run else spd_w
					ct = -phase[k] * 3.0
				elif kind == 1 and st == "melee":
					# per-soldier fight cycle: guard (hash-random 0.4-2 s) -> thrust -> recover; flinch on nearby losses
					if nxt[k] < 0.0:
						nxt[k] = vt + h(float(k), fi + 3.0) * 1.6
					if vt >= nxt[k] and rank < 2:
						cyc[k] += 1
						var hc := h(float(k) + float(cyc[k]) * 0.37, fi + 11.0)
						if hc < 0.8:
							act[k] = A_THRUST; act_t[k] = vt
							nxt[k] = vt + THRUST_S + RECOVER_S + 0.4 + h(float(k), float(cyc[k]) + 5.0) * 1.6
						else:
							hit_t[k] = vt
							nxt[k] = vt + HIT_S + 0.3 + hc
					var eh := vt - hit_t[k]
					var ea := vt - act_t[k]
					if eh >= 0.0 and eh < HIT_S:
						cname = "pk_hit"; ct = hit_t[k]; cur = 15
					elif act[k] == A_THRUST and ea < THRUST_S:
						cname = "pk_thrust"; ct = act_t[k]; cur = 13
					elif act[k] == A_THRUST and ea < THRUST_S + RECOVER_S:
						cname = "pk_recover"; ct = act_t[k] + THRUST_S; cur = 14
					else:
						cname = "pk_guard"; ct = -phase[k] * 2.0; cur = 12
				elif kind == 1:
					cname = "pk_guard" if (st == "hold" or st == "advance" or st == "fire") and rank < 2 and _near(center, enemy_pos, 40.0) else "idle"
					ct = -phase[k] * 3.0; cur = 12 if cname == "pk_guard" else 0
				elif st == "melee":
					cname = "melee"; ct = -phase[k] * 3.0; cur = 4
				else:
					# muskets: aim as the volley comes due, fire (scheduled by volley()), reload, shoulder
					var ea2 := vt - act_t[k]
					if act[k] == A_FIRE and ea2 < FIRE_S:
						cname = "mk_fire"; ct = act_t[k]; cur = 22
					elif act[k] == A_FIRE and ea2 < FIRE_S + RELOAD_S / reload_spd:
						cname = "mk_reload"; ct = act_t[k] + FIRE_S; spd = reload_spd; cur = 23
					elif st == "fire" and rank < 2 and float(r["fire_cd"]) < AIM_S + 0.1 + h(float(k), fi) * 0.15:
						if act[k] != A_AIM:
							act[k] = A_AIM; act_t[k] = vt
						cname = "mk_aim"; ct = act_t[k]; cur = 21
					else:
						if act[k] == A_AIM and st == "fire":
							cname = "mk_aim"; ct = act_t[k]; cur = 21   # stay levelled until the shot
						else:
							act[k] = A_NONE
							cname = "idle"; ct = -phase[k] * 3.0; cur = 0
			pos[k] = p
			# models face local -Z (VAT bake writes Blender (x, z, -y)); _put maps local -Z to -(sin a, cos a), so the
			# heading that points the model's front along `face` is atan2(-x, -y). (The legacy loop uses atan2(x, y).)
			var want := atan2(-face.x, -face.y)
			yaw[k] = rotate_toward(yaw[k], want, (turn[k] if routing else TURN_RATE) * dt)
		if hidden and dk < 0.0:
			continue
		var y: float = bv.h_at(p.x, p.y)
		var d2 := cpos.distance_to(Vector3(p.x, y, p.y))
		var lod := 1 if d2 > bv.LOD_DIST else 0
		var c := Vector2.ZERO
		if dk >= 0.0:
			var collapse := kind == 1 and h(float(k), fi + 21.0) < 0.5
			c = _clip(bv, model, "pk_collapse" if collapse else "die"); ct = dk; spd = 1.0; cur = 5
		else:
			c = _clip(bv, model, cname)
		var xc := Color(1, 1, 1, 1)
		if sr:
			xc = BattleVisuals.xfade(v, k, cur, c, ct, spd, vt)
		bv._put(bv.mms["%s|%d|%d" % [model, side, lod]], yaw[k], Vector3(p.x, y, p.y), 1.0, Vector4(c.x, c.y, ct, spd), xc)
	v["pos"] = pos; v["yaw"] = yaw; v["clip"] = clip; v["clip_t"] = clip_t
	v["ac_act"] = act; v["ac_t"] = act_t; v["ac_next"] = nxt; v["ac_hit"] = hit_t; v["ac_seen"] = seen; v["ac_cyc"] = cyc
	return true

static func _near(a: Vector2, b: Vector2, d: float) -> bool:
	return a.distance_to(b) < d

## Volley event (flag on). Same BattleView.rng draws as the legacy code, in the same order; the effects are deferred
## to the shot moment and spawned at the weapon tip. Returns false if the legacy path should run.
static func volley(bv, si: int, r: Dictionary, v: Dictionary, tv: Dictionary, targets: Array, era: String, powder: float) -> bool:
	var kind := kind_of(bv, v)
	var bow: bool = era == "medieval" and kind == 0 and v["kind"] == "vat"
	if kind != 2 and not bow:
		return false
	_init_state(v)
	var rng: RandomNumberGenerator = bv.rng
	var alive: Array = bv._alive_idx(v)
	var nshoot := mini(alive.size(), 14)
	var files: int = v["files"]
	var front: Array = alive.filter(func(k): return k / files < 2)
	if front.is_empty(): front = alive
	var vt: float = bv.vis_t
	var shots: Array = v["ac_shots"]
	var picked := {}
	for q in nshoot:
		var k: int = front[rng.randi() % front.size()]
		var delay := rng.randf_range(0.0, 0.35)
		var tp: Vector3 = bv._soldier_pos3(tv, targets[rng.randi() % targets.size()], 1.0)
		var smoke := rng.randf_range(3.0, 5.0) if (not bow and powder > 0.5) else 0.0
		if picked.has(k):
			continue
		picked[k] = true
		shots.append({"k": k, "t": vt + delay, "tp": tp, "smoke": smoke, "tracer": true})
	if not bow:
		# every other front-rank musket fires too (flash + smoke only, no extra tracer), staggered by hash
		var fi := float(si)
		for k in front:
			if picked.has(k):
				continue
			shots.append({"k": k, "t": vt + h(float(k), fi + 31.0) * 0.45, "tp": Vector3.ZERO, "smoke": 3.0 + h(float(k), fi) * 2.0, "tracer": false})
	var act: PackedInt32Array = v["ac_act"]; var act_t: PackedFloat32Array = v["ac_t"]
	for s in shots:
		var k: int = s["k"]
		if bow:
			v["clip"][k] = 3; v["clip_t"][k] = float(s["t"]) - BOW_RELEASE
		else:
			act[k] = A_FIRE; act_t[k] = float(s["t"]) - 1.0 / 24.0
	v["ac_act"] = act; v["ac_t"] = act_t
	v["ac_shots"] = shots
	return true

static func _flush_shots(bv, v: Dictionary, r: Dictionary, vt: float) -> void:
	var shots: Array = v["ac_shots"]
	if shots.is_empty():
		return
	var keep: Array = []
	var flashes := 0; var smokes := 0
	var model: String = v["model"]
	var era: String = r["def"]["era"]
	for s in shots:
		if vt < float(s["t"]):
			keep.append(s)
			continue
		var k: int = s["k"]
		if v["dead"][k] >= 0.0:
			continue
		var p: Vector2 = v["pos"][k]
		var o := Vector3(p.x, bv.h_at(p.x, p.y), p.y)
		var a: float = v["yaw"][k]
		if era == "medieval":
			var bp := to_world(a, o, Vector3(-0.15, 1.45, -0.6))   # bow hand (left) at full draw
			if s["tracer"]:
				bv.shoot(bp, s["tp"], 42.0, 0.35, Color(0.18, 0.14, 0.1), 0.05, 0.9, "dust")
			continue
		var tip := to_world(a, o, tip_local(bv, model, "mk_fire", 1, Vector3(0.0, 1.45, -1.5)))
		var fwd := Vector3(-sin(a), 0, -cos(a))
		var muzzle_dir := fwd
		if flashes < MAX_FLASH:
			bv.puff("add", tip + muzzle_dir * 0.15, Vector3.ZERO, 0.09, 0.45, 0.9, Color(1.0, 0.8, 0.4, 1.0))
			flashes += 1
		if float(s["smoke"]) > 0.0 and smokes < MAX_SMOKE:
			bv.puff("mix", tip + muzzle_dir * 0.4, muzzle_dir * 1.5 + Vector3(0, 0.4, 0), float(s["smoke"]), 0.9, 3.4, Color(0.86, 0.86, 0.84, 0.55))
			smokes += 1
		if s["tracer"]:
			bv.shoot(tip, s["tp"], 150.0, 0.0, Color(0.3, 0.3, 0.3), 0.04, 1.6, "dust")
	v["ac_shots"] = keep

# ---------------- cavalry (kind 3): gaits from pipeline/blender/cavalry_anim_combat.py ----------------
## Gait ladder; hv_<a>_<b> transition clips join phase 0 of one gait to phase 0 of the next.
const GAITS := ["stand", "walk", "trot", "canter", "gallop"]
const GAIT_UP := [0.25, 1.35, 2.8, 5.6]   # m/s: switch up above, down below (minus GAIT_HYST); 5.6 so a knight charge (cap ~6.1) reaches the gallop
const GAIT_HYST := 0.3
const GAIT_DWELL := 0.4
const CAV_ACC := 3.0      # m/s^2 speeding up
const CAV_DEC := 6.0      # m/s^2 slowing down
const CAV_TURN := 2.0     # rad/s

static func _gait_want(cur: int, s: float) -> int:
	var g := cur
	while g < 4 and s > GAIT_UP[g]:
		g += 1
	while g > 0 and s < GAIT_UP[g - 1] - GAIT_HYST:
		g -= 1
	return g

static func _tr_name(a: int, b: int) -> String:
	return "hv_%s_%s" % ["idle" if a == 0 else GAITS[a], "idle" if b == 0 else GAITS[b]]

static func _init_cav(v: Dictionary, r: Dictionary) -> void:
	if v.has("ac_g"):
		return
	var n: int = v["n"]
	var vel := PackedVector2Array(); vel.resize(n)
	var g := PackedInt32Array(); g.resize(n)
	var tr := PackedInt32Array(); tr.resize(n); tr.fill(-1)
	var f := PackedFloat32Array(); f.resize(n)
	v["ac_vel"] = vel; v["ac_g"] = g; v["ac_tr"] = tr
	v["ac_ph"] = f.duplicate(); v["ac_trt"] = f.duplicate(); v["ac_trs"] = f.duplicate(); v["ac_dw"] = f.duplicate(); v["ac_sf"] = f.duplicate()
	v["ac_rout_t"] = -1.0; v["ac_cv"] = Vector2.ZERO; v["ac_pc"] = r["pos"]; v["ac_pct"] = 0.0
	var yaw: PackedFloat32Array = v["yaw"]
	var fc: Vector2 = r["facing"]
	for k in n:
		yaw[k] = atan2(-fc.x, -fc.y)   # model front along the facing (see update_soldiers)
	v["yaw"] = yaw

## Horse + rider per-soldier update. Same instance order / set and the same BattleView.rng draws (dust) as the
## legacy loop: hidden = the legacy test on the SIM centre, one draw per visible living rider while r.moving.
static func _update_cav(bv, i: int, v: Dictionary, r: Dictionary, dt: float, vt: float, cpos: Vector3) -> void:
	_init_cav(v, r)
	var n: int = v["n"]; var files: int = v["files"]; var model: String = v["model"]
	var cl := clips_of(bv, model)
	var facing: Vector2 = r["facing"]
	var center: Vector2 = r["pos"]
	var st: String = r["state"]
	var routing := st == "rout" or st == "fled"
	if not routing:
		v["ac_face"] = facing
	elif v.has("ac_face"):
		facing = v["ac_face"]
	var hidden: bool = st == "fled" and center.length() > 260.0   # legacy test (keeps the rng sequence)
	var spd_base: float = float(r["def"]["speed"]) * (2.6 * 1.8 if r["running"] else 1.0)
	var enemy_pos := center + facing * 3.0
	var tgt: int = r["target"]
	if tgt >= 0:
		enemy_pos = bv.sim.regs[tgt]["pos"]
	var toward := (enemy_pos - center).normalized() if (enemy_pos - center).length() > 0.1 else facing
	# regiment ground velocity (the sim moves the centre in 0.1 s steps; measure per step, then smooth)
	var pc: Vector2 = v["ac_pc"]
	var raw: Vector2 = v.get("ac_cvraw", Vector2.ZERO)
	if center.distance_squared_to(pc) > 1e-8:
		raw = (center - pc) / maxf(vt - float(v["ac_pct"]), 0.03)
		v["ac_pc"] = center; v["ac_pct"] = vt
	elif vt - float(v["ac_pct"]) > 0.25:
		raw = Vector2.ZERO
	v["ac_cvraw"] = raw
	var cv: Vector2 = (v["ac_cv"] as Vector2).lerp(raw, minf(dt * 5.0, 1.0))
	v["ac_cv"] = cv
	# rout (Kirk): broken cavalry do NOT turn and ride away. They rein in where they broke and mill about; the moment the
	# sim takes them off the field (state "fled", or the legacy far-away hidden test; sim timing unchanged) is shown as their DEATH: each rider is thrown / falls and
	# each horse stumbles, buckles at the front knees and rolls onto its side, staggered 0-1.5 s per instance; the
	# bodies stay on the field (drawn until the view is freed; no BattleView.rng draws for them)
	if routing and float(v["ac_rout_t"]) < 0.0:
		v["ac_rout_t"] = vt; v["ac_rc"] = v.get("ac_lastc", center)
	elif not routing:
		v["ac_rout_t"] = -1.0; v["ac_lastc"] = center
		v.erase("ac_vis_c"); v.erase("ac_vis_f")
	var rt: float = vt - float(v["ac_rout_t"])
	var rc: Vector2 = v.get("ac_rc", center)
	if routing:
		v["ac_vis_c"] = rc; v["ac_vis_f"] = facing; v["ac_vis_hidden"] = hidden
	if (hidden or st == "fled") and float(v.get("ac_die_t", -1.0)) < 0.0:   # the sim has taken them off the field
		v["ac_die_t"] = vt
	var die_t0: float = v.get("ac_die_t", -1.0)
	var pos: PackedVector2Array = v["pos"]; var yaw: PackedFloat32Array = v["yaw"]
	var phase: PackedFloat32Array = v["phase"]; var dead: PackedFloat32Array = v["dead"]
	var vel: PackedVector2Array = v["ac_vel"]; var g: PackedInt32Array = v["ac_g"]; var tr: PackedInt32Array = v["ac_tr"]
	var ph: PackedFloat32Array = v["ac_ph"]; var trt: PackedFloat32Array = v["ac_trt"]; var trs: PackedFloat32Array = v["ac_trs"]
	var dw: PackedFloat32Array = v["ac_dw"]; var sf: PackedFloat32Array = v["ac_sf"]
	var side: int = r["side"]
	var fi := float(i)
	var vmax := maxf(spd_base, 1.0) * 1.35
	for k in n:
		var p: Vector2 = pos[k]
		var dk := dead[k]
		var c := Vector2.ZERO; var ct := 0.0; var spd := 1.0
		if dk < 0.0 and die_t0 >= 0.0 and vt >= die_t0 + h(float(k), fi + 131.0) * 1.5:
			# dying / dead horse + rider: play the collapse once from its own start time, then hold the body
			var dtk := die_t0 + h(float(k), fi + 131.0) * 1.5
			var hv := h(float(k), fi + 137.0)
			c = _clip(bv, model, "cv_die_a" if hv < 0.34 else ("cv_die_b" if hv < 0.67 else "cv_die_c"))
			ct = dtk; spd = 0.85 + h(float(k), fi + 139.0) * 0.3
			vel[k] = Vector2.ZERO
		elif dk < 0.0:
			var face := facing
			var vd := Vector2.ZERO
			if routing:
				# broken: rein in near where the regiment broke, ranks loosen, horses mill (no turning away)
				var slot0: Vector2 = bv._slot_world(r, v, k, rc, facing)
				var lat := Vector2(-facing.y, facing.x)
				var mill := clampf(rt / 4.0, 0.0, 1.0)
				var tp := slot0 + lat * (h(float(k), fi + 51.0) - 0.5) * 1.6 * mill + facing * (h(float(k), fi + 53.0) - 0.5) * 1.2 * mill
				vd = (tp - p) * 0.8
				if vd.length() > 1.2:
					vd = vd.normalized() * 1.2
				face = facing.rotated((h(float(k), fi + 81.0) - 0.5) * 1.2 * mill + sin(vt * 0.7 + phase[k] * 6.0) * 0.15 * mill)
			else:
				var slot: Vector2 = bv._slot_world(r, v, k, center, facing)
				if st == "melee" and k / files < 3:   # same press / sway as the legacy loop
					slot += toward * (1.2 + sin(vt * 1.7 + phase[k] * 6.0) * 0.6) + Vector2(sin(vt * 1.3 + phase[k] * 9.0), 0) * 0.5
				vd = cv + (slot - p) * 1.2
				if vd.length() > vmax:
					vd = vd.normalized() * vmax
				if st == "melee":
					face = (enemy_pos - p).normalized() if (enemy_pos - p).length() > 0.1 else facing
			var v0: Vector2 = vel[k]
			var dvv := vd - v0
			var lim := (CAV_ACC if vd.length() > v0.length() else CAV_DEC) * dt
			if dvv.length() > lim:
				dvv = dvv.normalized() * lim
			var v1 := v0 + dvv
			vel[k] = v1
			p += v1 * dt
			var sp := v1.length()
			sf[k] = lerpf(sf[k], sp, minf(dt * 4.0, 1.0))
			if sp > 0.6 and st != "melee":
				face = v1 / sp
			pos[k] = p
			yaw[k] = rotate_toward(yaw[k], atan2(-face.x, -face.y), CAV_TURN * dt)
			# ---- gait state machine (phase-continuous, transitions at the cycle wrap)
			var s := sf[k]
			if st == "melee" and s < 1.5 and tr[k] < 0:
				g[k] = 0
				c = _clip(bv, model, "hv_melee"); ct = -phase[k] * 3.0
			else:
				var want := _gait_want(g[k], s)
				dw[k] = (dw[k] + dt) if want != g[k] else 0.0
				if tr[k] >= 0:
					var tn := _tr_name(g[k], tr[k])
					var dur := (float(cl[tn]["count"]) - 1.0) / 24.0 / trs[k]
					if vt - trt[k] >= dur:
						var over := vt - trt[k] - dur
						g[k] = tr[k]; tr[k] = -1
						ph[k] = 0.0
						if g[k] > 0:
							var cg: Dictionary = cl["hv_" + GAITS[g[k]]]
							ph[k] = fposmod(over * trs[k] * 24.0 / float(cg["count"]), 1.0)
					else:
						c = _clip(bv, model, tn); ct = trt[k]; spd = trs[k]
				if tr[k] < 0:
					if g[k] == 0:
						c = _clip(bv, model, "hv_stand"); ct = -phase[k] * 4.0
						if want > 0 and dw[k] > 0.15:
							tr[k] = 1; trt[k] = vt; trs[k] = 1.0; dw[k] = 0.0
							c = _clip(bv, model, _tr_name(0, 1)); ct = vt
					else:
						var cg: Dictionary = cl["hv_" + GAITS[g[k]]]
						var cnt := float(cg["count"])
						spd = clampf(s / float(cg["v_nom"]), 0.7, 1.6 if g[k] == 4 else 1.45)
						var nph := ph[k] + dt * spd * 24.0 / cnt
						if nph >= 1.0 and want != g[k] and dw[k] >= GAIT_DWELL:
							var to := g[k] + (1 if want > g[k] else -1)
							tr[k] = to; trt[k] = vt; dw[k] = 0.0
							var s2 := 1.0
							if to > 0:
								s2 = clampf(s / float(cl["hv_" + GAITS[to]]["v_nom"]), 0.7, 1.6 if to == 4 else 1.45)
							trs[k] = (spd + s2) * 0.5 if to > 0 else spd
							c = _clip(bv, model, _tr_name(g[k], to)); ct = vt; spd = trs[k]
						else:
							ph[k] = fposmod(nph, 1.0)
							c = _clip(bv, model, "hv_" + GAITS[g[k]])
							ct = vt - ph[k] * cnt / (24.0 * spd)
		if hidden and dk < 0.0 and die_t0 < 0.0:
			continue
		var y: float = bv.h_at(p.x, p.y)
		var d2 := cpos.distance_to(Vector3(p.x, y, p.y))
		var lod := 1 if d2 > bv.LOD_DIST else 0
		if dk >= 0.0:
			c = _clip(bv, model, "die"); ct = dk; spd = 1.0
		var mmk := "%s|%d|%d" % [model, side, lod]
		if i == 0 and k == dbg_k:
			dbg = {"key": mmk, "slot": int(bv.mms[mmk]["n"]), "start": c.x, "cnt": c.y, "ct": ct, "spd": spd, "g": g[k], "tr": tr[k], "s": sf[k], "pos": p}
		bv._put(bv.mms[mmk], yaw[k], Vector3(p.x, y, p.y), 1.0, Vector4(c.x, c.y, ct, spd), Color(1, 1, 1, 1))
		# dust under fast cavalry: the legacy draw, same condition and order
		if dk < 0.0 and not hidden and r["moving"] and bv.rng.randf() < dt * 0.6:
			bv.puff("mix", Vector3(p.x, y + 0.4, p.y), Vector3(0, 0.6, 0), 2.5, 1.0, 3.5, Color(0.55, 0.47, 0.36, 0.45))
	v["pos"] = pos; v["yaw"] = yaw; v["ac_vel"] = vel; v["ac_g"] = g; v["ac_tr"] = tr
	v["ac_ph"] = ph; v["ac_trt"] = trt; v["ac_trs"] = trs; v["ac_dw"] = dw; v["ac_sf"] = sf
