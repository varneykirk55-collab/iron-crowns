extends Node
## Diagnostic: medieval battles, per-regiment morale budget (ranged vs melee vs shock) and rout timing.
func _ready() -> void:
	call_deferred("_run")

func _units(era: String, roles: Array, side: int, aid: int) -> Array:
	var out := []
	for k in roles.size():
		var uid := GameData.unit_for_role(era, roles[k])
		out.append({"army_id": aid, "unit_index": k, "type": uid, "men": float(GameData.units[uid]["men"])})
	return out

func _run() -> void:
	GameData.load_all()
	var mode := "starting"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mode="): mode = a.substr(7)
	var stats := {"routs_before_contact": 0, "inf_regs": 0, "inf_contact": 0, "battles": 0, "ranged_kill_share": 0.0, "dur": 0.0, "att_wins": 0}
	for seed in 40:
		var sides := []
		if mode == "starting":
			Sim.new_game("SWE", 1300, seed + 1)
			var as_: Array = []
			for c in ["SWE", "NOR"]:
				var best := {}
				for x in Sim.armies.values():
					if x["owner"] == c and (best.is_empty() or Sim.army_men(x) > Sim.army_men(best)): best = x
				var lst := []
				for i in best["units"].size():
					var u: Dictionary = best["units"][i]
					lst.append({"army_id": best["id"], "unit_index": i, "type": u["type"], "men": u["men"]})
				sides.append(lst)
		else:
			sides = [_units("medieval", ["inf", "ranged", "inf", "cav", "ranged"], 0, 1), _units("medieval", ["inf", "ranged", "inf", "cav", "ranged"], 1, 2)]
		var s := BattleSim.new()
		var ords := [BattleSim.ai_orders(sides[0], sides[1], false, "plains"), BattleSim.ai_orders(sides[1], sides[0], true, "plains")]
		s.setup(sides, "plains", ords, 1000 + seed)
		var src := {}   # reg -> {ranged, melee, other}
		var prev := []
		for r in s.regs: prev.append(r["morale"])
		var rkills := 0.0; var mkills := 0.0
		while not s.done:
			var ev0 := s.events.size()
			var m0 := []
			for r in s.regs: m0.append(r["morale"])
			s.step()
			var ranged_hit := {}
			for k in range(ev0, s.events.size()):
				var e: Dictionary = s.events[k]
				if e["k"] == "volley": ranged_hit[e["d"]] = true; rkills += e["kills"]
			for i in s.regs.size():
				var dm: float = m0[i] - s.regs[i]["morale"]
				if dm <= 0: continue
				if not src.has(i): src[i] = {"ranged": 0.0, "melee": 0.0, "other": 0.0}
				var cat := "ranged" if ranged_hit.has(i) else ("melee" if s.regs[i]["state"] == "melee" or s.regs[i]["contact_t"] >= 0 else "other")
				src[i][cat] += dm
		for r in s.regs: mkills += r.get("mkills", 0.0)
		stats["battles"] += 1; stats["dur"] += s.t
		stats["ranged_kill_share"] += rkills / maxf(rkills + mkills, 1.0)
		if s.winner == 0: stats["att_wins"] += 1
		for i in s.regs.size():
			var r: Dictionary = s.regs[i]
			if r["role"] != "inf": continue
			stats["inf_regs"] += 1
			if r["contact_t"] >= 0: stats["inf_contact"] += 1
			if r["rout_t"] >= 0 and r["contact_t"] < 0:
				stats["routs_before_contact"] += 1
				if seed < 6:
					print("  seed %d side %d %s routed t=%.1f men %d/%d morale0 %d  budget %s  orders %s" % [seed, r["side"], r["type"], r["rout_t"], int(r["men"]), int(r["men0"]), int(r["morale0"]), str(src.get(i, {})), str(ords[r["side"]])])
	stats["ranged_kill_share"] /= stats["battles"]; stats["dur"] /= stats["battles"]
	print("MEDIEVAL %s: " % mode, stats)
	get_tree().quit()
