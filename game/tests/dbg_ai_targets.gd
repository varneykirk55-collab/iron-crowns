extends Node
## Diagnostic: how far AI armies go to attack, and how much they leave at home.
func _ready() -> void:
	call_deferred("_run")
func _run() -> void:
	GameData.load_all()
	Sim.auto_deploy = true
	Sim.auto_respond_player = "decline"
	var cfgs := [["JPN", 1800, 31], ["SWE", 1300, 32], ["USA", 1914, 33]]
	for c in cfgs:
		Sim.new_game(c[0], c[1], c[2])
		var seen := {}
		var long := []
		var bare_home := 0; var samples := 0
		var dists := []
		for d in 365 * 3:
			Sim.tick_day()
			for a in Sim.armies.values():
				var o: String = a["owner"]
				if o == Sim.player or a["goal"] < 0 or seen.has(str(a["id"]) + ":" + str(a["goal"])): continue
				var go: String = Sim.prov_owner.get(a["goal"], "")
				if go == "" or go == o or not Sim.at_war(o, go): continue
				seen[str(a["id"]) + ":" + str(a["goal"])] = true
				var km := GameData.km_between(GameData.node_lonlat(Sim.nations[o]["capital"]), GameData.node_lonlat(a["goal"]))
				dists.append(km)
				# does this nation keep anything at home?
				var home := 0.0; var tot := 0.0
				for b in Sim.armies.values():
					if b["owner"] != o: continue
					tot += Sim.army_strength(b)
					if b["path"].is_empty() and Sim.prov_owner.get(b["node"], "") == o: home += Sim.army_strength(b)
				samples += 1
				if home < tot * 0.1: bare_home += 1
				if km > 3000.0:
					long.append("%s %dk men -> %s (%s) %.0f km, border=%s" % [o, int(Sim.army_men(a) / 1000), GameData.provinces[a["goal"]]["name"], go, km, Sim._shares_border(o, go)])
		dists.sort()
		var n := dists.size()
		print("AIDBG %s %d: %d attack orders, median %.0f km, p90 %.0f km, max %.0f km, >3000km %d, home left <10%% strength in %d/%d" % [c[0], c[1], n, dists[n / 2] if n else 0.0, dists[int(n * 0.9)] if n else 0.0, dists[-1] if n else 0.0, long.size(), bare_home, samples])
		for l in long.slice(0, 6): print("   ", l)
	get_tree().quit()
