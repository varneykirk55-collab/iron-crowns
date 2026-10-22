extends Node
func _units(e: String, roles: Array, mult: float) -> Array:
	var out: Array = []
	for i in roles.size():
		var uid := GameData.unit_for_role(e, roles[i])
		out.append({"army_id": 0, "unit_index": i, "type": uid, "men": float(GameData.units[uid]["men"]) * mult})
	return out
func mean_for(e: String, ks: float, dz: float) -> Array:
	BattleSim.ERA_TUNE[e] = [ks, dz]
	var ds: Array = []
	var w0 := 0
	for seed in range(1, 13):
		var s := BattleSim.new()
		s.record_events = false
		var comp: Array = [["ranged", "inf", "ranged", "cav", "art"], ["ranged", "ranged", "inf"], ["inf", "ranged", "cav", "cav", "art", "ranged"]][seed % 3]
		s.setup([_units(e, comp, 1.0 + 0.1 * (seed % 3)), _units(e, ["ranged", "inf", "ranged", "cav", "art"], 1.0)], ["plains", "hills", "forest"][seed % 3],
			[{"objective": BattleSim.OBJECTIVES[seed % 4], "formation": ["line", "deep", "wide"][seed % 3]}, {"objective": "hold", "formation": "line"}], seed)
		s.run_to_end()
		ds.append(s.t)
		if s.winner == 0: w0 += 1
	ds.sort()
	var m := 0.0
	for x in ds: m += x
	return [m / ds.size(), ds[0], ds[-1], w0]
func _ready() -> void:
	GameData.load_all()
	for e in ["medieval", "early_modern", "c19", "c20", "modern"]:
		var dz: float = BattleSim.ERA_TUNE[e][1]
		var lo := 0.02; var hi := 12.0
		var best := []
		for it in 12:
			var mid := sqrt(lo * hi)
			var r := mean_for(e, mid, dz)
			best = [mid, r]
			if r[0] > 35.0: lo = mid
			else: hi = mid
		print("%s ks=%.3f mean=%.1f min=%.1f max=%.1f att_wins=%d/12" % [e, best[0], best[1][0], best[1][1], best[1][2], best[1][3]])
	get_tree().quit()
