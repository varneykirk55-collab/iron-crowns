extends Node
## Combat animation v1 demo (Rob, proto/anim-combat-v1). Builds one small watched battle directly (no campaign), runs it
## through a real BattleView at normal speed with a scripted camera, takes stills and prints frame timing.
## godot --path game --resolution 1280x720 res://tests/anim_demo.tscn -- --scene=spear|musket|cav [--anim-v1] --out=<dir>
##   --tag=<name> [--dur=60] [--pre=0]
## The battle outcome does not depend on --anim-v1 (prints ANIMDEMO result + state hash for the comparison).
var a := {}
var bv: BattleView
var t := 0.0
var out := ""; var tag := ""; var scene := "spear"; var dur := 60.0
var shots: Array = []
var ft: Array = []
var units_us: Array = []
var last := 0
var cam_c := Vector2.ZERO
var sp_prev := PackedVector2Array()
var gait_log := {}
var side_k := -1
var sp_log := {"rout": [], "walk": []}   # rendered ground speed (m/s) of the --focus regiment's living soldiers

func _ready() -> void:
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--"):
			var kv := s.substr(2).split("=", true, 1)
			a[kv[0]] = kv[1] if kv.size() > 1 else "1"
	scene = a.get("scene", "spear"); out = a.get("out", "/tmp/anim_demo"); tag = a.get("tag", scene)
	dur = float(a.get("dur", "60"))
	DirAccess.make_dir_recursive_absolute(out)
	# cav: --cav=knights|cuirassiers|hussars (default knights), --regs=N cavalry regiments (cavalry overhaul, Rob)
	var cav_t: String = a.get("cav", "knights")
	var year := 1300 if scene in ["spear", "cav", "cavdie"] else 1800
	if scene == "cav":
		year = {"knights": 1300, "cuirassiers": 1500, "hussars": 1800}.get(cav_t, 1300)
	Sim.new_game("FRA" if Sim.nations.has("FRA") else "SWE", year, 7)
	Sim.set_speed(0)
	var codes: Array = ["FRA", "ENG"] if (Sim.nations.has("FRA") and Sim.nations.has("ENG")) else Sim.nations.keys().slice(0, 2)
	var ut := "levy_spear" if scene == "spear" else "line_inf"
	var sides := []
	if scene == "spear":   # two blocks a side; the weaker defender block breaks first while the other pair still fights
		sides = [[{"army_id": -1, "unit_index": 0, "type": ut, "men": 1000.0}, {"army_id": -1, "unit_index": 1, "type": ut, "men": 1000.0}],
			[{"army_id": -2, "unit_index": 0, "type": ut, "men": 1000.0}, {"army_id": -2, "unit_index": 1, "type": ut, "men": 650.0}]]
	elif scene == "cavdie":   # demo only: a small knight squadron charges a deep spear block, breaks, flees and is lost (vanish)
		sides = [[{"army_id": -1, "unit_index": 0, "type": "knights", "men": float(a.get("men", "120"))}, {"army_id": -1, "unit_index": 1, "type": "levy_spear", "men": 1000.0}],
			[{"army_id": -2, "unit_index": 0, "type": "levy_spear", "men": 1600.0}, {"army_id": -2, "unit_index": 1, "type": "levy_spear", "men": 1000.0}]]
	elif scene == "cav":   # mounted knights ride at a spear block: stand -> walk -> trot -> canter -> gallop charge -> melee
		var foe: String = {1300: "levy_spear", 1500: "pike", 1800: "line_inf"}[year]
		var cs := []
		for q in int(a.get("regs", "1")):
			cs.append({"army_id": -1, "unit_index": q, "type": cav_t, "men": float(a.get("men", "400"))})
		var fs := []
		for q in maxi(1, int(a.get("regs", "1")) - 1):
			fs.append({"army_id": -2, "unit_index": q, "type": foe, "men": float(a.get("foe", "600"))})
		sides = [cs, fs]
	else:
		sides = [[{"army_id": -1, "unit_index": 0, "type": ut, "men": 1200.0}], [{"army_id": -2, "unit_index": 0, "type": ut, "men": 1200.0}]]
	var orders := [{"objective": "assault", "formation": "line"}, {"objective": "hold", "formation": "line"}]
	var s := BattleSim.new()
	s.setup(sides, "plains", orders, 1234)
	s.record_events = true
	if a.has("gap"):   # demo only: deploy the defender further back so the attacker marches before it is in range
		for r in s.regs:
			if int(r["side"]) == 1:
				r["pos"] -= r["facing"] * float(a["gap"])
	s.run_seconds(float(a.get("pre", "0")))
	var bid := 9001
	Sim.battles[bid] = {"id": bid, "prov": Sim.nations[codes[0]]["capital"], "armies": [-1, -2], "codes": codes, "units": sides,
		"terrain": "plains", "sim": s, "watched": true, "awaiting": false, "player_side": 0, "start_day": 0, "done": true,
		"orders": orders, "seed": 77, "acc": 0.0}
	bv = BattleView.new()
	add_child(bv)
	bv.setup(bid)
	if scene == "spear":
		shots = [[3.0, "advance"], [6.6, "charge"], [8.4, "contact"], [9.6, "fight"], [10.6, "fight2"], [11.8, "rout_hold"], [13.0, "withdraw"], [15.0, "flee"], [18.0, "flee2"]]
	elif scene == "cav":
		shots = [[1.0, "stand"], [3.0, "move"], [6.0, "canter"], [9.0, "gallop"], [12.0, "contact"], [16.0, "melee"]]
	else:
		shots = [[3.0, "march"], [7.0, "march2"], [13.0, "aim"], [15.0, "fire"], [16.0, "reload"], [19.0, "reload2"], [23.0, "volley2"]]
	if a.has("shots"):
		shots = []
		for x in str(a["shots"]).split(","):
			shots.append([float(x), "t%s" % x])
	last = Time.get_ticks_usec()
	print("ANIMDEMO start scene=", scene, " anim_v1=", bv.AC.on, " regs=", s.regs.size(), " t0=", s.t)

func _cam() -> void:
	var r0: Dictionary = bv.sim.regs[0]
	bv.cam_auto = false
	if bv.finished: bv.result_shown = true   # demo only: keep the field visible (no result panel)
	if scene == "cav" and a.has("side"):   # close side-on shot of one horse (front rank, camera-side flank)
		var v: Dictionary = bv.rv[0]; var pv: PackedVector2Array = v["pos"]
		var f: Vector2 = v.get("ac_face", bv.sim.regs[0]["facing"])
		var sd := Vector2(-f.y, f.x)   # camera side
		var c0: Vector2 = bv.sim.regs[0]["pos"]
		if side_k < 0:
			var best := -1e9
			for k in pv.size():
				var sc := (pv[k] - c0).dot(sd) + 0.8 * (pv[k] - c0).dot(f)
				if sc > best: best = sc; side_k = k
			bv.AC.dbg_k = side_k
		var hp: Vector2 = pv[side_k]
		bv.cam_target = Vector3(hp.x, 0, hp.y)
		var dir := -Vector3(sd.x, 0, sd.y)
		bv.cam_yaw = atan2(dir.x, dir.z); bv.cam_pitch = -0.06; bv.cam_dist = float(a.get("side", "8"))
		if float(a.get("side", "8")) <= 1.0: bv.cam_dist = 8.0
	elif scene == "cav":
		var c3: Vector2 = r0["pos"]
		if cam_c == Vector2.ZERO: cam_c = c3
		cam_c = cam_c.lerp(c3, 0.05)
		bv.cam_target = Vector3(cam_c.x, 0, cam_c.y)
		bv.cam_dist = float(a.get("cdist", "26")); bv.cam_pitch = float(a.get("cpitch", "-0.2")); bv.cam_yaw = float(a.get("cyaw", "1.75"))
	elif scene == "cavdie":   # fixed camera on the spot where the squadron breaks (same framing with and without --anim-v1)
		var tg: PackedStringArray = str(a.get("tgt", "17.7,-60")).split(",")
		bv.cam_target = Vector3(float(tg[0]), 0, float(tg[1]))
		bv.cam_dist = 34.0; bv.cam_pitch = -0.26; bv.cam_yaw = 1.75
	elif scene == "spear":
		var c: Vector2 = (bv.sim.regs[1]["pos"] + bv.sim.regs[3]["pos"]) * 0.5
		if not cam_c.is_finite() or cam_c == Vector2.ZERO: cam_c = c
		cam_c = cam_c.lerp(c, 0.02)
		bv.cam_target = Vector3(cam_c.x, 0, cam_c.y)
		bv.cam_dist = 40.0; bv.cam_pitch = -0.24; bv.cam_yaw = 0.95
	else:
		var c2: Vector2 = r0["pos"] + r0["facing"] * (float(r0["depth"]) * 0.5)
		bv.cam_target = Vector3(c2.x + 3.0, 0, c2.y)
		bv.cam_dist = 13.0; bv.cam_pitch = -0.16; bv.cam_yaw = 2.35
	if a.has("focus"):   # follow the rendered soldiers of one regiment (e.g. the routing one)
		var pv: PackedVector2Array = bv.rv[int(a["focus"])]["pos"]
		var m := Vector2.ZERO
		for q in pv: m += q
		m /= maxf(float(pv.size()), 1.0)
		if cam_c == Vector2.ZERO: cam_c = m
		cam_c = cam_c.lerp(m, 0.04)
		bv.cam_target = Vector3(cam_c.x, 0, cam_c.y)
	if a.has("cam"):
		var cv: PackedStringArray = str(a["cam"]).split(",")
		bv.cam_dist = float(cv[0]); bv.cam_pitch = float(cv[1]); bv.cam_yaw = float(cv[2])
		if cv.size() > 3: bv.cam_target += Vector3(float(cv[3]), 0, float(cv[4]))

func _speed_log(delta: float) -> void:
	if not a.has("focus") or delta <= 0.0:
		return
	var fi := int(a["focus"])
	var v: Dictionary = bv.rv[fi]; var r: Dictionary = bv.sim.regs[fi]
	var pv: PackedVector2Array = v["pos"]; var dead: PackedFloat32Array = v["dead"]
	var st: String = r["state"]
	var key := "rout" if (st == "rout" or st == "fled") else ("walk" if st == "advance" and not r["running"] else "")
	if sp_prev.size() == pv.size() and key != "":
		for k in pv.size():
			var d := (pv[k] - sp_prev[k]).length() / delta
			if dead[k] < 0.0 and d > 0.15:   # moving soldiers only
				sp_log[key].append(d)
	sp_prev = pv.duplicate()
	if v.has("ac_g"):   # cavalry: time spent per gait / in transitions (soldier-frames)
		var gg: PackedInt32Array = v["ac_g"]; var tt: PackedInt32Array = v["ac_tr"]
		for k in gg.size():
			if dead[k] < 0.0:
				var key2 := ("tr>%d" % tt[k]) if tt[k] >= 0 else str(gg[k])
				gait_log[key2] = int(gait_log.get(key2, 0)) + 1

func _process(delta: float) -> void:
	if bv == null:
		return
	t += delta
	if a.has("shift") and not a.has("_shifted"):   # demo only: sidestep the defenders at sim time T by DX m (the cavalry wheel)
		var sp2: PackedStringArray = str(a["shift"]).split(":")
		if bv.sim.t >= float(sp2[0]):
			a["_shifted"] = "1"
			for r in bv.sim.regs:
				if int(r["side"]) == 1:
					var fc: Vector2 = r["facing"]
					r["pos"] += Vector2(-fc.y, fc.x) * float(sp2[1])
	_cam()
	var now := Time.get_ticks_usec()
	if t > 1.0:
		ft.append((now - last) / 1000.0); units_us.append(float(bv.perf.get("units_us", 0)))
	last = now
	_speed_log(delta)
	if a.has("statelog") and int(t * 2.0) != int((t - delta) * 2.0):
		var r0: Dictionary = bv.sim.regs[0]
		var hv: bool = bv.rv[0].get("ac_vis_hidden", false)
		print("STATELOG t=%.1f st=%s pos=%s len=%.0f men=%.0f finished=%s ac_die_t=%s vis_hidden=%s" % [t, r0["state"], r0["pos"], (r0["pos"] as Vector2).length(), float(r0["men"]), bv.finished, bv.rv[0].get("ac_die_t", -1.0), hv])
	if a.has("vatlog") and not bv.AC.dbg.is_empty():
		var d: Dictionary = bv.AC.dbg
		var m: Dictionary = bv.mms[d["key"]]
		var mm: MultiMesh = m["mm"]
		var cd: Color = mm.get_instance_custom_data(int(d["slot"])) if int(d["slot"]) < mm.visible_instance_count else Color(-1, -1, -1, -1)
		var mat: ShaderMaterial = m["mmi"].material_override
		var tex: Texture2D = mat.get_shader_parameter("vat_tex")
		print("VATLOG t=%.2f k=%d key=%s slot=%d row=%d cnt=%d ct=%.3f spd=%.2f g=%d tr=%d v=%.2f gpu_custom=(%.0f,%.0f,%.3f,%.2f) tex_h=%d btime=%.2f" % [t, side_k, d["key"], d["slot"], int(d["start"]), int(d["cnt"]), d["ct"], d["spd"], d["g"], d["tr"], d["s"], cd.r, cd.g, cd.b, cd.a, tex.get_height(), float(mat.get_shader_parameter("battle_time"))])
	if not shots.is_empty() and t >= float(shots[0][0]):
		var sh: Array = shots.pop_front()
		get_viewport().get_texture().get_image().save_png(out.path_join("%s_%s.png" % [tag, sh[1]]))
		print("ANIMDEMO shot ", sh[1], " t=", snappedf(bv.sim.t, 0.1), " states=", bv.sim.regs[0]["state"], "/", bv.sim.regs[1]["state"])
	if t >= dur:
		var s := ft.duplicate(); s.sort()
		var u := units_us.duplicate(); u.sort()
		if s.size() > 0:
			print("ANIMPERF tag=%s frames=%d median_ms=%.2f p95_ms=%.2f units_us_median=%.0f units_us_p95=%.0f" % [tag, s.size(), s[s.size() / 2], s[int(s.size() * 0.95)], u[u.size() / 2], u[int(u.size() * 0.95)]])
		if a.has("focus"):
			var r: Dictionary = bv.sim.regs[int(a["focus"])]
			for key in sp_log:
				var l: Array = sp_log[key]; l.sort()
				if l.size() > 0:
					print("ANIMSPEED reg=%s %s def_speed=%.2f n=%d mean=%.2f p50=%.2f p95=%.2f p99=%.2f max=%.2f" % [a["focus"], key, float(r["def"]["speed"]), l.size(),
						l.reduce(func(x, y): return x + y, 0.0) / l.size(), l[l.size() / 2], l[int(l.size() * 0.95)], l[int(l.size() * 0.99)], l[l.size() - 1]])
		if not gait_log.is_empty():
			print("ANIMGAIT ", gait_log)
		var st: Dictionary = bv.sim.to_dict()
		print("ANIMDEMO result=", bv.sim.result(), " t=", bv.sim.t, " hash=", str(st["regs"] if st.has("regs") else st).md5_text())
		get_tree().quit()
		bv = null
