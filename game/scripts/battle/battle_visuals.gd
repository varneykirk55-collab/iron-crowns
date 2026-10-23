## Iron Crowns visual pass: rendering-only hooks for battles (owned by the visual-dev workspace).
## Never reads or writes simulation state except to *observe* (sim.t, finished, result) for the debug logger.
##
## Intended integration (lead dev): at the end of BattleView.setup() call
##     preload("res://scripts/battle/battle_visuals.gd").apply(self)
## and optionally once at startup:  preload(...).apply_viewport(get_viewport())
##
## Debug-only: when instanced as a Node under main.gd with --perflog / --bench / --vispass on the command line,
## it applies the pass to the live BattleView (if --vispass=1), logs frame times and render stats, and
## (with --bench) holds three fixed cameras for N frames each to measure identical views before/after.
extends Node

const VERSION := 1   # 0 = measurement only (baseline); 1 = c19 visual pass
const ERAS := ["c19"]  # scope of the pass until review; other eras keep the legacy look untouched

# ------------------------------------------------------------------ static API
## Rendering-only tweaks for a freshly set-up BattleView. Touches environment, sun, materials, nothing else.
static func apply(bv: Node) -> void:
	if not (str(bv.get("era_id")) in ERAS):
		return
	_apply_environment(bv.get("environment"), bv.get("sun"))
	_apply_materials(bv)

## Viewport sharpness: 4x MSAA, no FXAA/TAA, native 3D scale, higher anisotropy. (Project-setting equivalents
## are listed as a request in out/INTEGRATION.md; this runtime version is what the previews use.)
static func apply_viewport(vp: Viewport) -> void:
	if vp == null:
		return
	vp.msaa_3d = Viewport.MSAA_4X
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	vp.use_taa = false
	vp.scaling_3d_scale = 1.0
	vp.anisotropic_filtering_level = Viewport.ANISOTROPY_8X
	RenderingServer.directional_shadow_atlas_set_size(4096, true)
	RenderingServer.directional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_LOW)

static func _apply_environment(env: Environment, sun: DirectionalLight3D) -> void:
	if env != null:
		var sm: ProceduralSkyMaterial = null
		if env.sky != null:
			sm = env.sky.sky_material as ProceduralSkyMaterial
		if sm != null:
			sm.sky_top_color = Color(0.25, 0.42, 0.68)
			sm.sky_horizon_color = Color(0.66, 0.71, 0.77)
			sm.ground_horizon_color = Color(0.62, 0.66, 0.66)
			sm.ground_bottom_color = Color(0.22, 0.23, 0.19)   # earthy bounce light from below
		env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
		env.ambient_light_energy = 0.62         # was 0.75: the main cause of the washed-out, low-contrast figures
		env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
		env.tonemap_mode = Environment.TONE_MAPPER_ACES
		env.tonemap_exposure = 1.12
		env.tonemap_white = 6.0
		env.fog_light_color = Color(0.68, 0.72, 0.78)
		env.fog_density = 0.00045                # a touch more aerial perspective to separate distant lines
		env.fog_sky_affect = 0.3
		env.glow_enabled = true                  # glow only for HDR hot spots (muzzle flashes / fire), no full-screen haze
		env.glow_intensity = 0.3
		env.glow_bloom = 0.0
		env.glow_hdr_threshold = 1.1
		env.adjustment_enabled = true
		env.adjustment_contrast = 1.04
		env.adjustment_saturation = 1.0
	if sun != null:
		sun.rotation_degrees = Vector3(-36, 35, 0)
		sun.light_energy = 1.75
		sun.light_color = Color(1.0, 0.95, 0.86)
		sun.shadow_enabled = true
		sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL   # one pass; the 4096 atlas does the sharpening
		sun.directional_shadow_max_distance = 260.0
		sun.shadow_bias = 0.1
		sun.shadow_normal_bias = 1.8
		sun.shadow_blur = 0.5
		sun.shadow_opacity = 0.92

## c19-only replacement meshes for props whose glb is shared with other eras (art_cannon = early_modern culverins too).
## Same groups / UV conventions / footprint, so the swap is purely visual. Becomes a no-op once units.json points
## field_guns at art_field_gun_c19 directly (see Requests in out/INTEGRATION.md).
const PROP_SWAP := {"art_cannon": "res://assets/models/art_field_gun_c19.glb"}

static func _glb_mesh(path: String) -> Mesh:
	var ps = load(path)
	if ps == null:
		return null
	var sc: Node = ps.instantiate()
	var stack := [sc]
	var out: Mesh = null
	while stack.size() > 0 and out == null:
		var n: Node = stack.pop_front()
		if n is MeshInstance3D:
			out = n.mesh
		stack.append_array(n.get_children())
	sc.free()
	return out

static func _swap_props(mms: Dictionary) -> void:
	var cache := {}
	for key in mms.keys():
		var k := str(key)
		if not (k.begins_with("P") or k.begins_with("W")):
			continue
		var model := k.substr(1).get_slice("|", 0)
		if not PROP_SWAP.has(model):
			continue
		if not cache.has(model):
			cache[model] = _glb_mesh(PROP_SWAP[model])
		if cache[model] != null:
			(mms[key]["mm"] as MultiMesh).mesh = cache[model]

static func _apply_materials(bv: Node) -> void:
	var mms: Dictionary = bv.get("mms")
	_swap_props(mms)
	for key in mms.keys():
		var mmi: MultiMeshInstance3D = mms[key]["mmi"]
		var mat := mmi.material_override as ShaderMaterial
		if mat == null or mat.shader == null:
			continue
		var path := mat.shader.resource_path
		if path.ends_with("vat.gdshader"):
			mat.set_shader_parameter("vis_pass", 1.0)
		elif path.ends_with("team_prop.gdshader") and str(key).begins_with("P"):
			# battle props share WorldMap.team_material's cached instance with the overworld: duplicate first
			var m2 := mat.duplicate() as ShaderMaterial
			m2.set_shader_parameter("vis_pass", 1.0)
			mmi.material_override = m2
	for n in bv.find_children("*", "MeshInstance3D", true, false):
		var gm := (n as MeshInstance3D).material_override as ShaderMaterial
		if gm != null and gm.shader != null and gm.shader.resource_path.ends_with("ground.gdshader"):
			gm.set_shader_parameter("vis_pass", 1.0)
			gm.set_shader_parameter("noise_tex_aniso", gm.get_shader_parameter("noise_tex"))
	var vc = bv.get("_vc_mat")
	if vc is StandardMaterial3D:
		vc.roughness = 0.88
		vc.albedo_color = Color(0.92, 0.92, 0.9)  # scenery slightly down so the troops carry the contrast

# ------------------------------------------------------------------ debug logger / bench
var args := {}
var applied := false
var t_prev := 0
var frame_i := 0
var bench_on := false
var bench_started := false
var bench_view := -1
var bench_frame := 0
var bench_frames := 60
var bench_warm := 8
var samples := {}        # view -> Array of [ms, prims, draws, objs]
var free_samples: Array = []
var result_printed := false
var log_path := ""
const VIEWS := [
	# name, reg selector (0 = first attacker vat reg, 1 = first defender vat reg, -1 = centroid), dist, pitch, yaw_off
	["close", 0, 30.0, -0.25, 0.4],
	["mid", 0, 80.0, -0.30, -0.7],
	["wide", -1, 230.0, -0.85, 0.0],
	["close_def", 1, 30.0, -0.25, 2.8],
]

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	bench_on = args.has("bench")
	bench_frames = int(args.get("bench-frames", "60"))
	log_path = args.get("perflog", "")
	if log_path == "1": log_path = ""
	process_priority = 1000   # run after main.gd and BattleView each frame
	t_prev = Time.get_ticks_usec()

func _bv() -> Node:
	var p := get_parent()
	if p == null or not ("battle_view" in p):
		return null
	var bv = p.get("battle_view")
	if bv == null or not is_instance_valid(bv) or not bv.visible or bv.get("sim") == null:
		return null
	if not bool(p.get("in_battle")) or bool(p.get("transitioning")):
		return null
	return bv

func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	var ms := (now - t_prev) / 1000.0
	t_prev = now
	frame_i += 1
	var bv := _bv()
	if bv == null:
		return
	if not applied:
		applied = true
		if args.get("vispass", "0") == "1":
			apply(bv)
			apply_viewport(get_viewport())
			print("VISPASS applied v", VERSION)
		if args.has("msaa"):   # debug override for perf attribution: --msaa=0|2|4|8
			get_viewport().msaa_3d = {"0": Viewport.MSAA_DISABLED, "2": Viewport.MSAA_2X, "4": Viewport.MSAA_4X, "8": Viewport.MSAA_8X}.get(args["msaa"], get_viewport().msaa_3d)
	var vp := get_viewport()
	var prims := vp.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_PRIMITIVES_IN_FRAME)
	var draws := vp.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)
	var objs := vp.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_OBJECTS_IN_FRAME)
	var sim = bv.get("sim")
	if bench_on:
		_bench_tick(bv, sim, ms, prims, draws, objs)
	else:
		free_samples.append([ms, prims, draws, objs])
	if bool(bv.get("finished")) and not result_printed:
		result_printed = true
		var res: Dictionary = sim.result()
		print("BATTLE_RESULT winner=%s time=%.3f losses=%s start=%s" % [str(res.get("winner")), float(res.get("time", 0.0)), str(res.get("losses")), str(res.get("start"))])
		if not bench_on:
			_report({"free": free_samples})

func _bench_tick(bv: Node, sim, ms: float, prims: int, draws: int, objs: int) -> void:
	if not bench_started:
		if float(sim.t) < float(args.get("bench-at", "4.0")):
			return
		bench_started = true
		bench_view = 0; bench_frame = 0
		_snap(bv, 0)
		return
	if bench_view >= VIEWS.size():
		return
	# frame time measured here belongs to the frame rendered with the camera set on the previous tick
	if bench_frame >= bench_warm:
		var k: String = VIEWS[bench_view][0]
		if not samples.has(k): samples[k] = []
		samples[k].append([ms, prims, draws, objs])
	if bench_frame == bench_frames + bench_warm - 1 and args.get("shots", "") != "":
		# grab the frame rendered with this view's camera (identical framing before/after)
		var img := get_viewport().get_texture().get_image()
		img.save_png(args["shots"].path_join("bench_%s.png" % VIEWS[bench_view][0]))
	bench_frame += 1
	if bench_frame >= bench_frames + bench_warm:
		bench_view += 1; bench_frame = 0
		if bench_view < VIEWS.size():
			_snap(bv, bench_view)
		else:
			bv.set("cam_auto", true)
			_report(samples)
			if args.has("bench-quit"):
				get_tree().quit()
			return
	else:
		_hold(bv, bench_view)

func _snap(bv: Node, vi: int) -> void:
	var v: Array = VIEWS[vi]
	var reg := -1
	if int(v[1]) >= 0:
		reg = bv.call("first_reg", int(v[1]))
	bv.call("snap_cam", reg, float(v[2]), float(v[3]), float(v[4]))

func _hold(bv: Node, vi: int) -> void:
	# re-snap every frame so the demo script's own camera steps can't move the bench camera
	# (deterministic under --fixed-fps, so before/after runs see identical views)
	_snap(bv, vi)

func _report(data: Dictionary) -> void:
	var lines: Array = []
	var vp := get_viewport()
	lines.append("# perf log  renderer=%s  adapter=%s  size=%s  msaa=%d  scale=%.2f  version=%d" % [
		RenderingServer.get_current_rendering_method(), RenderingServer.get_video_adapter_name(), str(vp.get_visible_rect().size), vp.msaa_3d, vp.scaling_3d_scale, VERSION])
	lines.append("view,frames,mean_ms,median_ms,p95_ms,fps_mean,primitives,draw_calls,objects")
	for k in data.keys():
		var arr: Array = data[k]
		if arr.is_empty(): continue
		var t: Array = arr.map(func(s): return float(s[0]))
		t.sort()
		var sum := 0.0
		for x in t: sum += x
		var mean := sum / t.size()
		var med: float = t[t.size() / 2]
		var p95: float = t[mini(int(t.size() * 0.95), t.size() - 1)]
		var mid: Array = arr[arr.size() / 2]
		lines.append("%s,%d,%.1f,%.1f,%.1f,%.2f,%d,%d,%d" % [k, t.size(), mean, med, p95, 1000.0 / mean, mid[1], mid[2], mid[3]])
	var txt := "\n".join(lines)
	print("PERF\n" + txt)
	if log_path != "":
		var f := FileAccess.open(log_path, FileAccess.WRITE)
		if f:
			f.store_string(txt + "\n"); f.close()
