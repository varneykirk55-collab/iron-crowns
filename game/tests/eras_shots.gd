extends Node3D
# Eras v3 stills (docs/char/ERAS_PROGRESS.md): one v3 kit (--model=v3_*) solo front / 3-4 / side / back, close busts,
# and a 3x6 block at 22 m gameplay distance (optionally next to the model it replaces, --old=<id>). FRA palette, crowd
# shaders, battle-like light. Camera only, no sim.
#   godot --path game --resolution 1200x1200 res://tests/eras_shots.tscn -- --model=v3_c19_grenadier --out=<abs dir> [--old=c19sr_grenadier]
#   mounted kits: --sx=1.3 --sz=3.0 (block file / rank spacing) --oldx=-1.3 (old solo offset)
const BV := preload("res://scripts/battle/battle_visuals.gd")
var cam: Camera3D
var args := {}
var groups := {}

func _arg(k: String, d: String) -> String:
	return str(args.get(k, d))

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	DirAccess.make_dir_recursive_absolute(_arg("out", "/tmp/eras"))
	BV._quality = 2
	var pal: Dictionary = BV._nation_palette(_arg("nation", "FRA"), Color("#2d4f9e"))
	var m := _arg("model", "v3_c19_grenadier")
	groups["new"] = {"solo": _make(m, pal, [Transform3D(Basis(), Vector3.ZERO)]), "block": _make(m, pal, _block(Vector3(0, 0, -200.0)))}
	var old := _arg("old", "")
	if old != "":
		groups["old"] = {"solo": _make(old, pal, [Transform3D(Basis(), Vector3(float(_arg("oldx", "-1.3")), 0, 0))]), "block": _make(old, pal, _block(Vector3(_oldbx(), 0, -200.0)))}
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

func _oldbx() -> float:
	return -(6.0 * float(_arg("sx", "0.72")) + 2.18)

func _block(c: Vector3) -> Array:
	var r := []
	var sx := float(_arg("sx", "0.72")); var sz := float(_arg("sz", "1.05"))
	for rank in 3:
		for f in 6:
			r.append(Transform3D(Basis(), c + Vector3((f - 2.5) * sx, 0, rank * sz)))
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

func _make(m: String, pal: Dictionary, xf: Array) -> MultiMeshInstance3D:
	var j: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/vat/%s_lod0.json" % m))
	var mat := ShaderMaterial.new()
	var vt := ImageTexture.create_from_image(Image.create_from_data(int(j["vertices"]), int(j["frames"]), false, Image.FORMAT_RGBF, FileAccess.get_file_as_bytes("res://assets/vat/%s_lod0.vat" % m)))
	var glb := "res://assets/models/soldier_%s_lod0.glb" % m
	if not j.has("kit"):   # blocky v0.2.x model + vat.gdshader
		mat.shader = load("res://shaders/vat.gdshader")
		mat.set_shader_parameter("team_color", Color("#2d4f9e"))
		if m in ["med_knight", "em_cuirassier", "c19_hussar"]: glb = "res://assets/models/cavalry_%s_lod0.glb" % m
	else:
		var v2 := m.begins_with("c19v2") or m.begins_with("v3_")
		mat.shader = load("res://shaders/char_vat_v2.gdshader" if v2 else "res://shaders/char_vat.gdshader")
		mat.set_shader_parameter("palette", BV._palette_tex(BV.kit_palette(pal, j)))
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
			if mt.size() >= 2:
				mat.set_shader_parameter("v2_nmap", mt[0]); mat.set_shader_parameter("v2_idmap", mt[1])
				if mt.size() > 2: mat.set_shader_parameter("v2_albmap", mt[2])
		mat.set_shader_parameter("team_tint", float(_arg("teamtint", "0")))
	mat.set_shader_parameter("vat_tex", vt)
	mat.set_shader_parameter("vat_verts", int(j["vertices"]))
	mat.set_shader_parameter("vat_fps", float(j["fps"]))
	var mm := MultiMesh.new(); mm.transform_format = MultiMesh.TRANSFORM_3D; mm.use_custom_data = true; mm.use_colors = true
	mm.mesh = _mesh(glb); mm.instance_count = xf.size()
	var cn := _arg("clip", "idle")
	var c: Dictionary = j["clips"][cn] if j["clips"].has(cn) else j["clips"]["idle"]
	for i in xf.size():
		mm.set_instance_transform(i, xf[i])
		mm.set_instance_color(i, Color(1, 1, 1, 1))
		mm.set_instance_custom_data(i, Color(float(c["start"]), float(c["count"]) * (1.0 if c["loop"] else -1.0), -0.37 * i, 0.0))
	var mmi := MultiMeshInstance3D.new(); mmi.multimesh = mm; mmi.material_override = mat
	add_child(mmi)
	return mmi

func _show(kind: String, which: Array) -> void:
	for k in groups:
		groups[k]["solo"].visible = kind == "solo" and k in which
		groups[k]["block"].visible = kind == "block" and k in which

func _look(target: Vector3, yaw_deg: float, dist: float, h: float) -> void:
	var y := deg_to_rad(yaw_deg)
	cam.position = target + Vector3(sin(y) * dist, h, -cos(y) * dist)   # model faces -z
	cam.look_at(target)

func _snap(name: String) -> void:
	for i in 4: await get_tree().process_frame
	get_viewport().get_texture().get_image().save_png(_arg("out", "/tmp/eras").path_join(name + ".png"))
	print("SHOT ", name)

func _run() -> void:
	var ht := float(_arg("h", "1.0"))
	_show("solo", ["new"])
	for v in [["front", 0.0], ["34", 35.0], ["side", 90.0], ["back", 180.0]]:
		_look(Vector3(0, ht, 0), v[1], 3.4 * ht, 0.25); await _snap(v[0])
	var bz := float(_arg("bustz", "1.62"))
	_look(Vector3(0, bz, 0), 25.0, 0.95, 0.04); await _snap("close_bust")
	_look(Vector3(0, bz, 0), -25.0, 0.95, 0.04); await _snap("close_bust_l")
	_look(Vector3(0, bz, 0), 160.0, 0.95, 0.04); await _snap("close_back")
	if args.has("zoom"):   # --zoom=x,z,yaw,dist[,depth] (inspection close-up, not a deliverable still)
		var zz := _arg("zoom", "").split(",")
		_look(Vector3(float(zz[0]), float(zz[1]), float(zz[4]) if zz.size() > 4 else 0.0), float(zz[2]), float(zz[3]), 0.02); await _snap("zoom")
		get_tree().quit(); return
	if groups.has("old"):
		_show("solo", ["new", "old"])
		_look(Vector3(-0.65, ht, 0), 20.0, 4.6 * ht, 0.3); await _snap("cmp_old_new")
	_show("block", ["new"])
	cam.position = Vector3(0, 22.0 * sin(0.33), -200.0 + 1.0 - 22.0 * cos(0.33)); cam.look_at(Vector3(0, 0.9, -199.0)); await _snap("game_22m")
	if groups.has("old"):
		_show("block", ["new", "old"])
		var hx := _oldbx() / 2.0
		cam.position = Vector3(hx, 22.0 * sin(0.33), -199.0 - 22.0 * cos(0.33)); cam.look_at(Vector3(hx, 0.9, -199.0)); await _snap("game_22m_cmp")
	get_tree().quit()
