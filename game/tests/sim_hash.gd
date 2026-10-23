extends Node
# Regression aid for perf work: hash of the full sim state after long AI-driven runs.
# Run: tools/godot --headless --path game res://tests/sim_hash.tscn   (compare output across commits)
func _ready() -> void:
	for cfg in [["SWE", 1800, 7], ["USA", 1914, 3], ["JPN", 1500, 5]]:
		Sim.new_game(cfg[0], cfg[1], cfg[2])
		for d in 800:
			Sim.tick_day()
		print("SIMHASH %s %d: %s wars %d armies %d" % [cfg[0], cfg[1], JSON.stringify(Sim.serialize_state()).md5_text(), Sim.wars.size(), Sim.armies.size()])
	get_tree().quit()
