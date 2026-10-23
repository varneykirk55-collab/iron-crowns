extends Node3D
# PROTO v2 debug render (docs/char/PROTO_V2.md): c19v2_line (sculpted prototype) next to c19sr_line (current main) and the
# v0.2.1 blocky c19_line, with the real crowd shaders / FRA palette, in a battle-like light. Camera only, no sim.
#   godot --path game res://tests/proto_shots.tscn -- --out=<dir> [--quality=2] [--clip=idle] [--t=0.4]
const BV := preload("res://scripts/battle/battle_visuals.gd")
const MODELS := ["c19_line", "c19sr_line", "c19v2_line"]   # blocky v0.2.1 / c19sr (main) / proto v2
var groups := {}   # name -> {"solo": mmi, "block": mmi}
var cam: Camera3D
var out := "res://../out/proto/engine"
var args := {}
var labels := {}   # shot -> {model: screen x 0..1}, for the compare-sheet captions

func _arg(k: String, d: String) -> String:
	return str(args.get(k, d))

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	out = _arg("out", out)
	DirAccess.make_dir_recursive_absolute(out)
	BV._quality = int(_arg("quality", "2"))
	var pal := BV._palette_tex(BV._nation_palette("FRA", Color("#2d4f9e")))
	var xs := [-1.25, 0.0, 1.25]
	for i in MODELS.size():
		var m: String = MODELS[i]
		groups[m] = {"solo": _make(m, pal, [Transform3D(Basis(), Vector3(xs[i], 0, 0))]),
					 "block": _make(m, pal, _block(Vector3((i - 1) * 9.0, 0, -200.0))),
					 "c_solo": Vector3(xs[i], 1.0, 0), "c_block": Vector3((i - 1) * 9.0, 0.9, -199.0)}
	cam = Camera3D.new(); add_child(cam); cam.fov = 40.0; cam.near = 0.05; cam.make_current()
	var l := DirectionalLight3D.new(); l.rotation_degrees = Vector3(-38, 35, 0); l.light_energy = 1.25; l.shadow_enabled = true
	l.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS; l.directional_shadow_max_distance = 120.0
	add_child(l)
	var we := WorldEnvironment.new(); var e := Environment.new()
	var sky := Sky.new(); sky.sky_material = ProceduralSkyMaterial.new(); e.sky = sky
	e.background_mode = Environment.BG_SKY; e.ambient_light_source = Environment.AMBIENT_SOURCE_SKY; e.ambient_light_energy = 0.75
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	we.environment = e; add_child(we)
	var g := MeshInstance3D.new(); var pm := PlaneMesh.new(); pm.size = Vector2(600, 600); g.mesh = pm
	var gm := StandardMaterial3D.new(); gm.albedo_color = Color(0.13, 0.17, 0.08); gm.roughness = 1.0; g.material_override = gm
	add_child(g)
	get_viewport().msaa_3d = Viewport.MSAA_4X
	_run()

func _block(c: Vector3) -> Array:
	var r := []
	for rank in 3:
		for f in 6:
			r.append(Transform3D(Basis(), c + Vector3((f - 2.5) * 0.72, 0, rank * 1.05)))
	return r

func _mesh(path: String) -> Mesh:
	var n: Node = (load(path) as PackedScene).instantiate()
	var st: Array = [n]; var m: Mesh = null
	while not st.is_empty() and m == null:
		var x: Node = st.pop_back()
		if x is MeshInstance3D: m = (x as MeshInstance3D).mesh
		st.append_array(x.get_children())
	n.free()
	return m

func _make(m: String, pal: Texture2D, xf: Array) -> MultiMeshInstance3D:
	var j: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/vat/%s_lod0.json" % m))
	var mat := ShaderMaterial.new()
	var vt := ImageTexture.create_from_image(Image.create_from_data(int(j["vertices"]), int(j["frames"]), false, Image.FORMAT_RGBF, FileAccess.get_file_as_bytes("res://assets/vat/%s_lod0.vat" % m)))
	if m == "c19_line":   # v0.2.1 blocky model + vat.gdshader
		mat.shader = load("res://shaders/vat.gdshader")
		mat.set_shader_parameter("team_color", Color("#2d4f9e"))
	else:
		mat.shader = load("res://shaders/char_vat_v2.gdshader" if m.begins_with("c19v2") else "res://shaders/char_vat.gdshader")
		mat.set_shader_parameter("palette", pal)
		mat.set_shader_parameter("team_color", Color("#2d4f9e"))
		var nt := BV._vatn_tex(m, 0, int(j["vertices"]), int(j["frames"]))
		mat.set_shader_parameter("has_normals", 1.0 if nt != null else 0.0)
		if nt != null: mat.set_shader_parameter("vat_nrm", nt)
		if j.has("near_verts"):
			mat.set_shader_parameter("near_verts", int(j["near_verts"]))
			mat.set_shader_parameter("char_lod_dist", BV.char_lod_dist())
			mat.set_shader_parameter("mid_verts", int(j.get("mid_verts", -1)))
			mat.set_shader_parameter("char_mid_dist", BV.char_mid_dist())
		if j.has("maps"):
			var mt := BV._v2_maps(j["maps"])
			if mt.size() == 2:
				mat.set_shader_parameter("v2_nmap", mt[0]); mat.set_shader_parameter("v2_idmap", mt[1])
				mat.set_shader_parameter("nmap_strength", float(_arg("nmap", "1"))); mat.set_shader_parameter("nmap_ao", float(_arg("nao", "0.85")))
		mat.set_shader_parameter("team_tint", float(_arg("teamtint", "0")))
	mat.set_shader_parameter("vat_tex", vt)
	mat.set_shader_parameter("vat_verts", int(j["vertices"]))
	mat.set_shader_parameter("vat_fps", float(j["fps"]))
	var mm := MultiMesh.new(); mm.transform_format = MultiMesh.TRANSFORM_3D; mm.use_custom_data = true; mm.use_colors = true
	mm.mesh = _mesh("res://assets/models/soldier_%s_lod0.glb" % m); mm.instance_count = xf.size()
	var cn := _arg("clip", "idle")
	var c: Dictionary = j["clips"][cn] if j["clips"].has(cn) else j["clips"]["idle"]
	for i in xf.size():
		mm.set_instance_transform(i, xf[i])
		mm.set_instance_color(i, Color(1, 1, 1, 1))
		var t0 := -float(_arg("t", "0.4")) - 0.37 * i
		var spd := 0.0 if _arg("close", "0") == "1" else 1.0   # close-ups: frozen on the clip's first frame (hand positions from tools/hand_pos.py)
		mm.set_instance_custom_data(i, Color(float(c["start"]), float(c["count"]) * (1.0 if c["loop"] else -1.0), t0, spd))
	var mmi := MultiMeshInstance3D.new(); mmi.multimesh = mm; mmi.material_override = mat
	add_child(mmi)
	return mmi

func _show(which: Array, kind: String) -> void:
	for m in MODELS:
		groups[m]["solo"].visible = kind == "solo" and m in which
		groups[m]["block"].visible = kind == "block" and m in which

func _look(target: Vector3, yaw_deg: float, dist: float, h: float) -> void:
	var y := deg_to_rad(yaw_deg)
	cam.position = target + Vector3(sin(y) * dist, h, -cos(y) * dist)   # model faces -z
	cam.look_at(target)

func _snap(name: String) -> void:
	for i in 4: await get_tree().process_frame
	get_viewport().get_texture().get_image().save_png(out.path_join(name + ".png"))
	var lab := {}
	for m in MODELS:
		for k in ["solo", "block"]:
			if groups[m][k].visible:
				var c: Vector3 = groups[m]["c_" + k]
				if not cam.is_position_behind(c): lab[m] = cam.unproject_position(c).x / get_viewport().get_visible_rect().size.x
	labels[name] = lab
	print("SHOT ", name)

func _run() -> void:
	var views := [["front", 0.0], ["34", 35.0], ["side", 90.0], ["back", 180.0]]
	var xs := {"c19_line": -1.25, "c19sr_line": 0.0, "c19v2_line": 1.25}
	if _arg("close", "0") == "1":   # before/after close-ups only (v2): bust both sides + both hands
		var tg := _arg("tag", "")
		_show(["c19v2_line"], "solo")
		_look(Vector3(1.25, 1.62, 0), 25.0, 0.95, 0.04); await _snap("close_bust%s" % tg)
		_look(Vector3(1.25, 1.62, 0), -25.0, 0.95, 0.04); await _snap("close_bust_l%s" % tg)
		for hs in [["r", 1.0, "0.21,0.95,-0.02"], ["l", -1.0, "-0.21,0.95,-0.02"]]:
			var q: PackedStringArray = _arg("h" + hs[0], hs[2]).split(",")
			var hp := Vector3(1.25 + float(q[0]), float(q[1]), float(q[2]))
			_look(hp, 55.0 * float(hs[1]), 0.42, 0.06); await _snap("close_hand_%s%s" % [hs[0], tg])
		get_tree().quit()
		return
	# solo v2 views + bust
	for m in ["c19v2_line", "c19sr_line", "c19_line"]:
		_show([m], "solo")
		var x: float = xs[m]
		for v in views:
			_look(Vector3(x, 1.0, 0), v[1], 3.4, 0.25); await _snap("%s_%s" % [m, v[0]])
		_look(Vector3(x, 1.62, 0), 25.0, 0.95, 0.04); await _snap("%s_bust" % m)
		_look(Vector3(x, 1.62, 0), -25.0, 0.95, 0.04); await _snap("%s_bust_l" % m)
	# three-model compares, per view
	_show(MODELS, "solo")
	for v in views:
		_look(Vector3(0, 1.0, 0), v[1], 6.2, 0.35); await _snap("cmp_%s" % v[0])
	_look(Vector3(0, 1.45, 0), 20.0, 3.0, 0.1); await _snap("cmp_upper")
	# gameplay distances: each model as a 3x6 block, 9 m apart
	_show(MODELS, "block")
	for d in [[12.0, -0.30], [22.0, -0.33], [40.0, -0.42], [75.0, -0.55]]:
		var dist: float = d[0]
		cam.position = Vector3(0, 0.0, -199.0) + Vector3(0, dist * sin(-d[1]), -dist * cos(d[1]))
		cam.look_at(Vector3(0, 0.9, -199.0)); await _snap("game_%dm" % int(dist))
	var f := FileAccess.open(out.path_join("labels.json"), FileAccess.WRITE); f.store_string(JSON.stringify(labels)); f.close()
	get_tree().quit()
