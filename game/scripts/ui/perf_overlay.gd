## F3 performance overlay: CPU frame time (process + campaign tick + battle sim/units) reported separately
## from rendered fps and the renderer's CPU-side submit time. No GPU on the dev box (llvmpipe), so "GPU" ms
## here is really software rasterisation and is shown only for reference.
class_name PerfOverlay
extends PanelContainer

var lbl: Label
var _t := 0.0
var _hist: PackedFloat32Array = PackedFloat32Array()
var _vp_measured := false

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	position = Vector2(8, 54)
	var sb := StyleBoxFlat.new(); sb.bg_color = Color(0, 0, 0, 0.62); sb.set_content_margin_all(8); sb.set_corner_radius_all(4)
	add_theme_stylebox_override("panel", sb)
	lbl = Label.new()
	lbl.add_theme_font_size_override("font_size", 13)
	lbl.add_theme_color_override("font_color", Color(0.75, 1.0, 0.75))
	add_child(lbl)
	visible = Controls.show_perf
	Controls.settings_changed.connect(func(): visible = Controls.show_perf; _measure())
	_measure()

func _measure() -> void:
	if visible and not _vp_measured:
		RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
		_vp_measured = true

static func snapshot(vp: Viewport) -> Dictionary:
	var rid := vp.get_viewport_rid()
	var d := {
		"fps": Engine.get_frames_per_second(),
		"process_ms": FrameProbe.script_us / 1000.0,
		"engine_process_ms": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		"physics_ms": Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		"render_cpu_ms": RenderingServer.viewport_get_measured_render_time_cpu(rid) + RenderingServer.get_frame_setup_time_cpu(),
		"render_gpu_ms": RenderingServer.viewport_get_measured_render_time_gpu(rid),
		"draw_calls": Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"objects": Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
		"primitives": Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"nodes": Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
		"static_mem_mb": Performance.get_monitor(Performance.MEMORY_STATIC) / 1048576.0,
		"video_mem_mb": Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0,
		"sim_tick_ms": Sim.perf_tick_us / 1000.0,
		"sim_days": Sim.perf_days,
	}
	return d

func _process(delta: float) -> void:
	if not visible:
		return
	_hist.append(delta * 1000.0)
	if _hist.size() > 120:
		_hist = _hist.slice(_hist.size() - 120)
	_t -= delta
	if _t > 0.0:
		return
	_t = 0.25
	var d := snapshot(get_viewport())
	var worst := 0.0
	var avg := 0.0
	for x in _hist:
		worst = maxf(worst, x); avg += x
	avg /= maxf(1.0, _hist.size())
	var txt := "FPS %d   frame %.1f ms avg / %.1f worst (2 s)\n" % [d["fps"], avg, worst]
	txt += "CPU  scripts %.2f ms  (campaign tick %.2f ms, %d days)\n" % [d["process_ms"], d["sim_tick_ms"], d["sim_days"]]
	var bv = get_tree().get_first_node_in_group("battle_view")
	if bv and bv.visible and "perf" in bv:
		txt += "CPU  battle sim %.2f ms · units/MultiMesh %.2f ms · fx %.2f ms · %d instances\n" % [bv.perf["sim_us"] / 1000.0, bv.perf["units_us"] / 1000.0, bv.perf["fx_us"] / 1000.0, bv.perf.get("instances", 0)]
	txt += "Render CPU %.2f ms · raster %.2f ms (llvmpipe=software)\n" % [d["render_cpu_ms"], d["render_gpu_ms"]]
	txt += "Draw calls %d · objects %d · prims %dk · nodes %d\n" % [d["draw_calls"], d["objects"], int(d["primitives"] / 1000), d["nodes"]]
	txt += "Mem %.0f MB · VRAM %.0f MB · quality %s" % [d["static_mem_mb"], d["video_mem_mb"], ["Low", "Medium", "High"][Controls.quality]]
	lbl.text = txt
