extends Node
## Prints which biome profile every province maps to (docs/BIOMES.md census). Run:
##   godot --headless --path game res://tests/biome_census.tscn
const BE := preload("res://scripts/battle/battle_environment.gd")

func _ready() -> void:
	var by := {}
	for pid in GameData.provinces:
		var p: Dictionary = GameData.provinces[pid]
		var id := BE.biome_id(p, str(p.get("terrain", "plains")))
		if not by.has(id): by[id] = {}
		var c := str(p.get("region", "?"))
		by[id][c] = int(by[id].get(c, 0)) + 1
		print("CENSUSP %s %s | %s | %s | %s" % [pid, id, c, p.get("name", ""), p.get("terrain", "")])
	for id in BE.BIOMES:
		var d: Dictionary = by.get(id, {})
		var n := 0
		for k in d: n += d[k]
		var ks := d.keys(); ks.sort_custom(func(a, b): return d[a] > d[b])
		var parts: Array = []
		for k in ks: parts.append("%s %d" % [k, d[k]])
		print("CENSUS %s %d: %s" % [id, n, ", ".join(parts)])
	get_tree().quit()
