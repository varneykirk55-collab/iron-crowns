extends Node
## Battle render/perf harness (Rob). Runs the production main scene with --demo=battle, waits until the battle sim
## reaches --at=<s>, freezes time (Engine.time_scale = 0, so before/after builds show the same sim state), then for each
## camera view: snap_cam, settle frames, screenshot, then time --frames=N frames (median/p95 wall ms).
## Usage: godot --path game --resolution 1600x900 res://tests/battle_shots.tscn -- --demo=battle --year=1800 --nation=SWE
##        --quality=1 --out=<dir> --tag=<name> [--at=14] [--frames=30] [--views=close,close_def,mid,top]
var main: Node
var out := ""; var tag := ""; var at := 14.0; var frames := 30
var views: PackedStringArray
var state := 0; var vi := 0; var fc := 0; var times := []; var last_us := 0
const VIEWS := {   # name: [side (0 attacker first reg / 1 defender first reg / -1 centroid), dist, pitch, yaw_off]
	"close": [0, 30.0, -0.25, 0.4], "close_def": [1, 30.0, -0.25, 2.8], "mid": [0, 70.0, -0.4, 0.4], "top": [-1, 230.0, -0.85, 0.0]}

func _ready() -> void:
	var a := {}
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--"):
			var kv := s.substr(2).split("=", true, 1)
			a[kv[0]] = kv[1] if kv.size() > 1 else "1"
	out = a.get("out", "/tmp/bshots"); tag = a.get("tag", "x"); at = float(a.get("at", "14")); frames = int(a.get("frames", "30"))
	views = str(a.get("views", "close,close_def,mid,top")).split(",")
	DirAccess.make_dir_recursive_absolute(out)
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)

func _process(_d: float) -> void:
	var bv = main.get("battle_view")
	match state:
		0:
			if main.get("in_battle") and not main.get("transitioning") and bv != null and float(bv.sim.t) >= at:
				Engine.time_scale = 0.0
				print("BSHOT freeze t=", bv.sim.t)
				state = 1; vi = 0; fc = 0
		1:
			if vi >= views.size():
				print("BSHOT done"); get_tree().quit(); state = 9; return
			var v: Array = VIEWS[views[vi]]
			var reg: int = int(v[0]) if int(v[0]) < 0 else bv.first_reg(int(v[0]))
			bv.snap_cam(reg, float(v[1]), float(v[2]), float(v[3]))
			state = 2; fc = 0
		2:
			fc += 1
			if fc == 8:
				var img: Image = get_viewport().get_texture().get_image()
				img.save_png(out.path_join("%s_%s.png" % [tag, views[vi]]))
				times = []; last_us = Time.get_ticks_usec()
			elif fc > 8:
				var now := Time.get_ticks_usec(); times.append((now - last_us) / 1000.0); last_us = now
				if times.size() >= frames:
					var s := times.duplicate(); s.sort()
					print("BPERF tag=%s view=%s median_ms=%.1f p95_ms=%.1f fps=%.2f" % [tag, views[vi], s[s.size() / 2], s[int(s.size() * 0.95)], 1000.0 / s[s.size() / 2]])
					vi += 1; state = 1
