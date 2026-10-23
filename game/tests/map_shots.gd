## Map visual + perf + picking harness (graphics-map branch). Not part of the game.
## xvfb-run -a -s "-screen 0 1600x900x24" tools/godot --path game --resolution 1600x900 res://tests/map_shots.tscn -- --out=/abs/dir [--tag=after] [--quality=1] [--perf=1] [--pick=1] [--hud=0] [--only=alps,japan]
extends Node

const VIEWS := [
	# name, lon, lat, dist, yaw(rad)
	["world", 15.0, 28.0, 200.0, 0.0],
	["europe", 12.0, 50.0, 70.0, 0.0],
	["alps", 9.5, 46.3, 22.0, 0.0],
	["rockies", -110.0, 43.0, 40.0, 0.0],
	["japan", 137.5, 37.0, 30.0, 0.0],
	["scandinavia", 15.0, 63.0, 45.0, 0.0],
	["himalaya", 86.0, 29.5, 40.0, 0.0],
	["close_alps", 8.0, 46.4, 8.0, 0.6],
	["close_japan", 138.6, 35.6, 7.0, -0.4],
	["close_sweden", 15.5, 59.5, 9.0, 0.3],
	["andes", -70.0, -22.0, 45.0, 0.0],
	["min_zoom", 18.0, 59.3, 4.0, 0.0],
]

var args := {}
var main: Node
var out := ""
var tag := "shot"

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	out = args.get("out", ProjectSettings.globalize_path("res://").path_join("../out/shots"))
	tag = args.get("tag", "shot")
	DirAccess.make_dir_recursive_absolute(out)
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._start_game(args.get("nation", "SWE"), int(args.get("year", "1800")), 7)
	Sim.set_speed(0)
	await _run()
	get_tree().quit()

func _wait(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func _set_view(v: Array) -> void:
	var cam: MapCamera = main.cam
	cam.fly_t = -1.0
	var w := GameData.lonlat_to_world(v[1], v[2])
	cam._t_yaw = v[4]; cam.yaw = v[4]
	cam.look_at_world(Vector3(w.x, 0, w.y), v[3], true)
	main.map.cam_dist = cam.dist

func _run() -> void:
	var only: Array = args.get("only", "").split(",", false) if args.has("only") else []
	var hud_on: bool = args.get("hud", "0") == "1"
	if main.hud_layer:
		main.hud_layer.visible = hud_on
	main.map.set_selected_province(-1)
	var perf := {}
	var picks := {}
	await _wait(5)
	for v in VIEWS:
		if not only.is_empty() and not only.has(v[0]):
			continue
		_set_view(v)
		await _wait(8)
		var img := get_viewport().get_texture().get_image()
		img.save_png(out.path_join("%s_%s.png" % [tag, v[0]]))
		print("MAPSHOT ", v[0])
		if args.get("perf", "0") == "1":
			RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
			await _wait(3)
			var n := int(args.get("frames", "20"))
			var t0 := Time.get_ticks_usec()
			var rc := 0.0; var rg := 0.0; var pr := 0.0
			for i in n:
				await get_tree().process_frame
				var d := PerfOverlay.snapshot(get_viewport())
				rc += d["render_cpu_ms"]; rg += d["render_gpu_ms"]; pr += d["engine_process_ms"]
			var ms := (Time.get_ticks_usec() - t0) / 1000.0 / n
			perf[v[0]] = {"frame_ms": ms, "fps": 1000.0 / ms, "render_cpu_ms": rc / n, "render_gpu_ms": rg / n, "process_ms": pr / n,
				"prims": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME), "draws": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)}
			print("MAPPERF ", v[0], " ", JSON.stringify(perf[v[0]]))
		if args.get("pick", "0") == "1":
			var vs := get_viewport().get_visible_rect().size
			var ids := []
			for gy in 18:
				for gx in 32:
					ids.append(main.map.province_at_screen(Vector2((gx + 0.5) / 32.0 * vs.x, (gy + 0.5) / 18.0 * vs.y)))
			picks[v[0]] = ids
	if not perf.is_empty():
		var f := FileAccess.open(out.path_join("%s_perf_q%d.json" % [tag, Controls.quality]), FileAccess.WRITE)
		f.store_string(JSON.stringify(perf, " ")); f.close()
	if not picks.is_empty():
		var f2 := FileAccess.open(out.path_join("%s_picks.json" % tag), FileAccess.WRITE)
		f2.store_string(JSON.stringify(picks)); f2.close()
	if args.get("interact", "0") == "1":
		await _interact()

## Selection highlight + conquest recolour + zoom extremes, with screenshots.
func _interact() -> void:
	var cam: MapCamera = main.cam
	var swe_cap: int = Sim.nations["SWE"]["capital"]
	_set_view(["sel", GameData.provinces[swe_cap]["lon"], GameData.provinces[swe_cap]["lat"], 14.0, 0.0])
	await _wait(6)
	var vs := get_viewport().get_visible_rect().size
	var c := vs / 2.0
	var pid: int = main.map.province_at_screen(c)
	main.select_province(pid)
	await _wait(6)
	get_viewport().get_texture().get_image().save_png(out.path_join("%s_interact_selected.png" % tag))
	print("INTERACT selected pid=%d (%s) map.selected_pid=%d" % [pid, GameData.provinces[pid]["name"] if pid > 0 else "-", main.map.selected_pid])
	# conquest recolour: hand a Norwegian province to Sweden
	var tgt := -1
	for p in GameData.province_ids:
		if Sim.prov_owner.get(p, "") == "NOR":
			tgt = p; break
	var tw := GameData.lonlat_to_world(GameData.provinces[tgt]["lon"], GameData.provinces[tgt]["lat"])
	_set_view(["conq", GameData.provinces[tgt]["lon"], GameData.provinces[tgt]["lat"], 20.0, 0.0])
	main.map.set_selected_province(-1)
	await _wait(6)
	var before := get_viewport().get_texture().get_image()
	before.save_png(out.path_join("%s_interact_conquest_before.png" % tag))
	var sp: Vector2 = cam.unproject_position(Vector3(tw.x, GameData.surface_y(tw.x, tw.y), tw.y))
	var cb := before.get_pixelv(Vector2i(sp))
	Sim.transfer_province(tgt, "SWE")
	main.map.lut_dirty = true; main.map.labels_dirty = true
	await _wait(6)
	var after := get_viewport().get_texture().get_image()
	after.save_png(out.path_join("%s_interact_conquest_after.png" % tag))
	var ca := after.get_pixelv(Vector2i(sp))
	print("INTERACT conquest pid=%d %s owner now %s colour %s -> %s changed=%s pick=%d" % [tgt, GameData.provinces[tgt]["name"], Sim.prov_owner.get(tgt, ""), cb.to_html(false), ca.to_html(false), str(cb.to_html(false) != ca.to_html(false)), main.map.province_at_screen(sp)])
	# zoom extremes
	for d in [cam.min_dist, cam.max_dist]:
		_set_view(["z", 15.0, 59.0, d, 0.0])
		await _wait(6)
		get_viewport().get_texture().get_image().save_png(out.path_join("%s_interact_zoom_%d.png" % [tag, int(d)]))
		print("INTERACT zoom dist=%.1f cam_y=%.2f pick_center=%d" % [cam.dist, cam.global_position.y, main.map.province_at_screen(get_viewport().get_visible_rect().size / 2.0)])

