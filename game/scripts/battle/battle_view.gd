## Watched 3D battle. Reads BattleSim state/events only (never changes the outcome) and steps it through
## Sim.step_watched in real time, so the strategic clock keeps running underneath.
class_name BattleView
extends Node3D

signal leave_requested(bid: int)

const FIELD := 1000.0
const GRID := 161
var LOD_DIST := 75.0
var _lod_forced := false
var _lod_forced_dist := 75.0

## Quality setting (Controls.quality owns the value + UI). The rendering values per level (MSAA, sun shadows +
## distance, LOD distance, glow, anisotropy) are owned by the graphics pass: battle_visuals.apply_quality(q).
func apply_quality() -> void:
	BattleVisuals.apply_quality(Controls.quality)
	if _lod_forced:
		LOD_DIST = _lod_forced_dist   # debug --lod-dist= overrides the preset

const BattleVisuals := preload("res://scripts/battle/battle_visuals.gd")
const CREW_MODEL := {"medieval": "med_archer", "early_modern": "em_musket", "c19": "c19_line", "c20": "c20_rifle", "modern": "mod_rifle"}
const POWDER := {"medieval": 0.0, "early_modern": 1.0, "c19": 1.0, "c20": 0.35, "modern": 0.2}

var bid := -1
var b: Dictionary
var sim: BattleSim
var era_id := "c19"
var environment: Environment
var sun: DirectionalLight3D
var cam: Camera3D
var heights := PackedFloat32Array()
var vat := {}          # model -> {mesh:[m0,m1], tex:[t0,t1], json:[j0,j1]}
var mms := {}          # key -> {mmi, mm, buf, n, cap}
var props := {}        # model -> Mesh
var rv: Array = []     # per-reg visual state
var banners: Array = []
var particles := {"mix": [], "add": []}
var pmm := {}
var projectiles: Array = []
var proj_stats := {}   # projectile class -> visual shots fired (era verification / tests)
var tracer_mm: MultiMesh
var ev_idx := 0
var time_scale := 1.0
var vis_t := 0.0
var finished := false
var result_shown := false
var hud: Control
var hud_bars := {}
var hud_time: Label
var hud_date: Label
var hud_feed: RichTextLabel
var result_panel: PanelContainer
var cam_auto := true
var cam_target := Vector3.ZERO
var cam_dist := 220.0
var cam_yaw := 0.0
var cam_pitch := -0.6
var _ct := Vector3.ZERO
var _cd := 220.0
var _cy := 0.0
var _cp := -0.6
var shot_t := 0.0
var shot_i := 0
var _drag := -1
var intro_t := 0.0
var rng := RandomNumberGenerator.new()
var side_col := [Color.RED, Color.BLUE]
var player_side := 0

# ======================================================================== setup
func setup(battle_id: int) -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--lod-dist="): LOD_DIST = float(a.substr(11)); _lod_forced = true; _lod_forced_dist = LOD_DIST
	add_to_group("battle_view")
	bid = battle_id
	b = Sim.battles[bid]
	sim = b["sim"]
	rng.seed = int(b["seed"])
	player_side = maxi(b["player_side"], 0)
	era_id = GameData.eras[Sim.era]["id"]
	if sim.regs.size() > 0:
		era_id = sim.regs[0]["def"]["era"]
	for s in 2:
		side_col[s] = Sim.nations[b["codes"][s]]["color"]
	if _too_close(side_col[0], side_col[1]):
		side_col[1] = Color(0.85, 0.85, 0.8) if side_col[0].v < 0.7 else Color(0.2, 0.2, 0.25)
	_build_env()
	_build_ground()
	_build_scenery()
	_build_units()
	_build_fx()
	_build_camera()
	_build_hud()
	BattleVisuals.apply_quality(Controls.quality)   # store the level first: apply() uses it even if we're not in the tree yet
	BattleVisuals.apply(self)   # graphics pass (rendering only; idempotent; c19 look only, quality presets all eras)
	apply_quality()
	Controls.settings_changed.connect(apply_quality)

func _too_close(a: Color, c: Color) -> bool:
	return absf(a.r - c.r) + absf(a.g - c.g) + absf(a.b - c.b) < 0.35

func _build_env() -> void:
	environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	var warm := {"medieval": Color(0.62, 0.7, 0.82), "early_modern": Color(0.6, 0.68, 0.8), "c19": Color(0.62, 0.68, 0.76), "c20": Color(0.6, 0.63, 0.66), "modern": Color(0.55, 0.66, 0.82)}
	sm.sky_top_color = Color(0.28, 0.45, 0.7)
	sm.sky_horizon_color = warm.get(era_id, Color(0.6, 0.68, 0.8))
	sm.ground_horizon_color = sm.sky_horizon_color
	sm.ground_bottom_color = Color(0.3, 0.3, 0.28)
	sm.sun_angle_max = 20.0
	sky.sky_material = sm
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.75
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.tonemap_exposure = 1.0
	environment.fog_enabled = true
	environment.fog_light_color = sm.sky_horizon_color
	environment.fog_density = 0.0006
	environment.fog_sky_affect = 0.3
	environment.glow_enabled = true
	environment.glow_intensity = 0.5
	environment.glow_bloom = 0.05
	if "--nofog" in OS.get_cmdline_user_args(): environment.fog_enabled = false
	if "--noglow" in OS.get_cmdline_user_args(): environment.glow_enabled = false
	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-38, 35, 0)
	sun.light_energy = 1.25
	sun.light_color = Color(1.0, 0.95, 0.86)
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.directional_shadow_max_distance = 260.0
	add_child(sun)

func _terrain_params() -> Dictionary:
	match b["terrain"]:
		"desert": return {"amp": 6.0, "freq": 0.006, "a": Color(0.72, 0.6, 0.4), "b": Color(0.8, 0.68, 0.46), "dirt": Color(0.6, 0.5, 0.36), "snow": 0.0}
		"hills": return {"amp": 16.0, "freq": 0.004, "a": Color(0.36, 0.44, 0.2), "b": Color(0.5, 0.5, 0.27), "dirt": Color(0.44, 0.36, 0.25), "snow": 0.0}
		"mountains": return {"amp": 24.0, "freq": 0.0035, "a": Color(0.36, 0.42, 0.26), "b": Color(0.46, 0.46, 0.36), "dirt": Color(0.42, 0.38, 0.32), "snow": 0.25}
		"forest": return {"amp": 5.0, "freq": 0.005, "a": Color(0.24, 0.36, 0.15), "b": Color(0.34, 0.42, 0.2), "dirt": Color(0.36, 0.3, 0.2), "snow": 0.0}
		"jungle": return {"amp": 5.0, "freq": 0.006, "a": Color(0.18, 0.36, 0.12), "b": Color(0.28, 0.44, 0.16), "dirt": Color(0.38, 0.3, 0.2), "snow": 0.0}
		"tundra": return {"amp": 6.0, "freq": 0.005, "a": Color(0.5, 0.52, 0.4), "b": Color(0.62, 0.6, 0.5), "dirt": Color(0.45, 0.42, 0.36), "snow": 0.75}
	return {"amp": 3.5, "freq": 0.005, "a": Color(0.33, 0.45, 0.18), "b": Color(0.48, 0.5, 0.25), "dirt": Color(0.43, 0.35, 0.24), "snow": 0.0}

func _build_ground() -> void:
	var tp := _terrain_params()
	var nz := FastNoiseLite.new()
	nz.seed = int(b["seed"]) % 100000
	nz.frequency = tp["freq"]
	nz.fractal_octaves = 4
	heights.resize(GRID * GRID)
	var cell := FIELD / (GRID - 1)
	for j in GRID:
		for i in GRID:
			var x := -FIELD / 2 + i * cell; var z := -FIELD / 2 + j * cell
			var h: float = nz.get_noise_2d(x, z) * tp["amp"]
			# keep the central field gentler, rising terrain at the edges
			var edge := clampf((absf(x) - 160.0) / 300.0, 0.0, 1.0)
			h = h * (0.55 + 0.45 * edge) + edge * edge * tp["amp"] * 2.5
			heights[j * GRID + i] = h
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in GRID:
		for i in GRID:
			st.set_uv(Vector2(float(i) / (GRID - 1), float(j) / (GRID - 1)))
			st.add_vertex(Vector3(-FIELD / 2 + i * cell, heights[j * GRID + i], -FIELD / 2 + j * cell))
	for j in GRID - 1:
		for i in GRID - 1:
			var a := j * GRID + i
			st.add_index(a); st.add_index(a + 1); st.add_index(a + GRID)
			st.add_index(a + 1); st.add_index(a + GRID + 1); st.add_index(a + GRID)
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/ground.gdshader")
	m.set_shader_parameter("grass_a", tp["a"]); m.set_shader_parameter("grass_b", tp["b"]); m.set_shader_parameter("dirt", tp["dirt"])
	m.set_shader_parameter("snow", tp["snow"])
	var nt := NoiseTexture2D.new()
	nt.width = 512; nt.height = 512; nt.seamless = true; nt.generate_mipmaps = true
	var n2 := FastNoiseLite.new(); n2.frequency = 0.012; n2.fractal_octaves = 3
	nt.noise = n2
	m.set_shader_parameter("noise_tex", nt)
	mi.material_override = m
	add_child(mi)
	var far := MeshInstance3D.new()
	var fp := PlaneMesh.new(); fp.size = Vector2(6000, 6000)
	far.mesh = fp
	# horizon skirt: must sit BELOW the battlefield mesh (it used to float above and bury the armies)
	var hmin := 1e9
	for hv in heights: hmin = minf(hmin, hv)
	far.position.y = hmin - 0.4
	far.material_override = m
	add_child(far)

func h_at(x: float, z: float) -> float:
	var cell := FIELD / (GRID - 1)
	var fx := clampf((x + FIELD / 2) / cell, 0.0, GRID - 1.001)
	var fz := clampf((z + FIELD / 2) / cell, 0.0, GRID - 1.001)
	var i := int(fx); var j := int(fz)
	var tx := fx - i; var tz := fz - j
	var a := heights[j * GRID + i]; var c := heights[j * GRID + i + 1]
	var d := heights[(j + 1) * GRID + i]; var e := heights[(j + 1) * GRID + i + 1]
	return lerpf(lerpf(a, c, tx), lerpf(d, e, tx), tz)

func _mesh_of(path: String) -> Mesh:
	if props.has(path):
		return props[path]
	var sc: Node = load(path).instantiate()
	var stack := [sc]
	var out: Mesh = null
	while stack.size() > 0 and out == null:
		var n: Node = stack.pop_front()
		if n is MeshInstance3D:
			out = n.mesh
		stack.append_array(n.get_children())
	sc.free()
	props[path] = out
	return out

var _vc_mat: StandardMaterial3D = null

func _scatter(model: String, count: int, scale_rng: Vector2, accept: Callable, shadow: bool = true) -> void:
	var mesh := _mesh_of("res://assets/models/%s.glb" % model)
	if mesh == null or count <= 0:
		return
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = mesh
	var xs: Array = []
	var tries := 0
	while xs.size() < count and tries < count * 20:
		tries += 1
		var p := Vector2(rng.randf_range(-FIELD / 2 + 10, FIELD / 2 - 10), rng.randf_range(-FIELD / 2 + 10, FIELD / 2 - 10))
		if accept.call(p):
			xs.append(p)
	mm.instance_count = xs.size()
	for k in xs.size():
		var p: Vector2 = xs[k]
		var s := rng.randf_range(scale_rng.x, scale_rng.y)
		var tr := Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * s), Vector3(p.x, h_at(p.x, p.y) - 0.1, p.y))
		mm.set_instance_transform(k, tr)
		mm.set_instance_color(k, Color.WHITE)
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	if _vc_mat == null:
		_vc_mat = StandardMaterial3D.new()
		_vc_mat.vertex_color_use_as_albedo = true
		_vc_mat.roughness = 0.9
		_vc_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	mmi.material_override = _vc_mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mmi)

func _build_scenery() -> void:
	var ter: String = b["terrain"]
	var clear_zone := func(p: Vector2) -> bool: return absf(p.x) > 140.0 or absf(p.y) > 230.0
	var flank := func(p: Vector2) -> bool: return absf(p.x) > 150.0 and absf(p.x) < 470.0
	match ter:
		"forest":
			_scatter("tree_conifer", 700, Vector2(1.6, 2.6), flank)
			_scatter("tree_broadleaf", 400, Vector2(1.5, 2.4), clear_zone)
		"jungle":
			_scatter("tree_palm", 600, Vector2(1.6, 2.4), clear_zone)
			_scatter("tree_broadleaf", 600, Vector2(1.8, 2.8), flank)
		"desert":
			_scatter("rock", 160, Vector2(0.8, 2.6), func(p): return true)
			_scatter("tree_palm", 30, Vector2(1.4, 2.0), clear_zone)
		"tundra", "mountains":
			_scatter("tree_conifer", 420, Vector2(1.4, 2.4), clear_zone)
			_scatter("rock", 220, Vector2(1.0, 3.5), func(p): return true)
		_:
			_scatter("tree_broadleaf", 260, Vector2(1.5, 2.5), func(p): return absf(p.x) > 170.0 and fmod(absf(p.y) + 40.0, 160.0) < 40.0)
			_scatter("tree_conifer", 80, Vector2(1.4, 2.2), clear_zone)
			_scatter("house", 7, Vector2(1.6, 1.8), func(p): return absf(p.x) > 160.0 and absf(p.x) < 260.0 and absf(p.y) < 120.0)
			_scatter("fence", 40, Vector2(1.5, 1.6), func(p): return absf(p.x) > 150.0 and absf(p.x) < 280.0 and absf(p.y) < 160.0)
			_scatter("rock", 40, Vector2(0.6, 1.5), func(p): return true)
	_scatter("bush", 500 if ter != "desert" else 60, Vector2(0.5, 1.1), func(p): return true, false)

# ======================================================================== units
func _vat_model(name: String) -> Dictionary:
	if vat.has(name):
		return vat[name]
	var prefix := "cavalry_" if name in ["med_knight", "em_cuirassier", "c19_hussar"] else "soldier_"
	var d := {"mesh": [], "tex": [], "json": []}
	for lod in 2:
		d["mesh"].append(_mesh_of("res://assets/models/%s%s_lod%d.glb" % [prefix, name, lod]))
		var j: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/vat/%s_lod%d.json" % [name, lod]))
		var bytes := FileAccess.get_file_as_bytes("res://assets/vat/%s_lod%d.vat" % [name, lod])
		var img := Image.create_from_data(int(j["vertices"]), int(j["frames"]), false, Image.FORMAT_RGBF, bytes)
		d["tex"].append(ImageTexture.create_from_image(img))
		d["json"].append(j)
	vat[name] = d
	return d

func _mm(key: String, mesh: Mesh, mat: Material, cap: int, custom: bool) -> Dictionary:
	if mms.has(key):
		var e: Dictionary = mms[key]
		e["cap"] += cap
		return e
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = custom
	mm.use_colors = true  # GL Compatibility: without instance colours, COLOR (vertex colour) reads as black
	mm.mesh = mesh
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.custom_aabb = AABB(Vector3(-FIELD, -100, -FIELD), Vector3(FIELD * 2, 300, FIELD * 2))
	add_child(mmi)
	var e2 := {"mmi": mmi, "mm": mm, "buf": PackedFloat32Array(), "n": 0, "cap": cap, "stride": 20 if custom else 16}
	mms[key] = e2
	return e2

func _vat_mat(name: String, lod: int, side: int, bright: float = 1.0) -> ShaderMaterial:
	var d := _vat_model(name)
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/vat.gdshader")
	m.set_shader_parameter("vat_tex", d["tex"][lod])
	m.set_shader_parameter("vat_verts", int(d["json"][lod]["vertices"]))
	m.set_shader_parameter("vat_fps", float(d["json"][lod]["fps"]))
	m.set_shader_parameter("team_color", side_col[side])
	m.set_shader_parameter("brightness", bright)
	return m

func _clip(name: String, clip: String) -> Vector2:
	var c: Dictionary = vat[name]["json"][0]["clips"][clip]
	return Vector2(float(c["start"]), float(c["count"]) * (1.0 if c["loop"] else -1.0))

func _build_units() -> void:
	for i in sim.regs.size():
		var r: Dictionary = sim.regs[i]
		var d: Dictionary = r["def"]
		var v := {"i": i, "kind": r["kind"], "side": r["side"], "n": int(r["nvis"]), "files": int(r["files"]), "ranks": int(r["ranks"]),
			"sp": r["spacing"], "model": d["model"], "alive": int(r["nvis"]), "fire_t": -10.0}
		var n: int = v["n"]
		var pos := PackedVector2Array(); var yaw := PackedFloat32Array(); var dead := PackedFloat32Array(); var jit := PackedVector2Array()
		var clip := PackedInt32Array(); var clip_t := PackedFloat32Array(); var phase := PackedFloat32Array()
		var rows := n
		for k in rows:
			jit.append(Vector2(rng.randf_range(-0.22, 0.22), rng.randf_range(-0.22, 0.22)))
			phase.append(rng.randf())
			dead.append(-1.0)
			clip.append(0); clip_t.append(-rng.randf() * 3.0)
		v["jit"] = jit; v["phase"] = phase; v["dead"] = dead; v["clip"] = clip; v["clip_t"] = clip_t
		for k in rows:
			var wp := _slot_world(r, v, k, r["pos"], r["facing"])
			pos.append(wp)
			yaw.append(atan2(r["facing"].x, r["facing"].y))
		v["pos"] = pos; v["yaw"] = yaw
		if r["kind"] in ["vat", "cav"]:
			_vat_model(d["model"])
			for lod in 2:
				for alive in 2:
					_mm("%s|%d|%d" % [d["model"], r["side"], lod], vat[d["model"]]["mesh"][lod], _vat_mat(d["model"], lod, r["side"]), n, true)
		else:
			var mesh := _mesh_of("res://assets/models/%s.glb" % d["model"])
			_mm("P%s|%d" % [d["model"], r["side"]], mesh, WorldMap.team_material(side_col[r["side"]]), n, false)
			var wm := WorldMap.team_material(Color(0.12, 0.11, 0.1)).duplicate()
			wm.set_shader_parameter("brightness", 0.3)
			_mm("W%s" % d["model"], mesh, wm, n, false)
			v["recoil"] = PackedFloat32Array(); v["recoil"].resize(n)
			if r["kind"] == "gun":
				var cm: String = CREW_MODEL.get(d["era"], "c19_line")
				v["crew_model"] = cm
				_vat_model(cm)
				for lod in 2:
					_mm("%s|%d|%d" % [cm, r["side"], lod], vat[cm]["mesh"][lod], _vat_mat(cm, lod, r["side"]), n * 3, true)
		rv.append(v)
		# banner
		var bn := Node3D.new()
		var pole := MeshInstance3D.new(); var cy := CylinderMesh.new(); cy.top_radius = 0.05; cy.bottom_radius = 0.05; cy.height = 6.0
		pole.mesh = cy; pole.position.y = 3.0
		var pm := StandardMaterial3D.new(); pm.albedo_color = Color(0.3, 0.22, 0.14); pole.material_override = pm
		bn.add_child(pole)
		var cloth := MeshInstance3D.new(); var pl := PlaneMesh.new(); pl.size = Vector2(2.2, 1.4); pl.subdivide_width = 8; pl.orientation = PlaneMesh.FACE_Z
		cloth.mesh = pl; cloth.position = Vector3(1.15, 5.2, 0)
		var bm := ShaderMaterial.new(); bm.shader = load("res://shaders/banner.gdshader"); bm.set_shader_parameter("team_color", side_col[r["side"]])
		cloth.material_override = bm
		bn.add_child(cloth)
		bn.set_meta("mat", bm)
		add_child(bn)
		banners.append(bn)
	for e in mms.values():
		e["mm"].instance_count = e["cap"]
		e["buf"].resize(e["cap"] * e["stride"])

func _slot_local(r: Dictionary, v: Dictionary, k: int) -> Vector2:
	var files: int = v["files"]; var ranks: int = v["ranks"]
	var f := k % files; var rk := k / files
	var sp: Vector2 = v["sp"]
	return Vector2((f - (files - 1) * 0.5) * sp.x, (rk - (ranks - 1) * 0.5) * sp.y) + v["jit"][k]

func _slot_world(r: Dictionary, v: Dictionary, k: int, center: Vector2, facing: Vector2) -> Vector2:
	var l := _slot_local(r, v, k)
	var right := Vector2(facing.y, -facing.x)
	return center + right * l.x - facing * l.y

# ======================================================================== FX
func _build_fx() -> void:
	var q := QuadMesh.new(); q.size = Vector2(1, 1)
	for kind in ["mix", "add"]:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = q
		mm.instance_count = 3000 if kind == "mix" else 900
		var mmi := MultiMeshInstance3D.new(); mmi.multimesh = mm
		var m := ShaderMaterial.new(); m.shader = load("res://shaders/particle.gdshader" if kind == "mix" else "res://shaders/particle_add.gdshader")
		mmi.material_override = m
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mmi.custom_aabb = AABB(Vector3(-FIELD, -100, -FIELD), Vector3(FIELD * 2, 300, FIELD * 2))
		add_child(mmi)
		pmm[kind] = mm
	tracer_mm = MultiMesh.new()
	tracer_mm.transform_format = MultiMesh.TRANSFORM_3D
	tracer_mm.use_custom_data = true
	var bx := BoxMesh.new(); bx.size = Vector3(1, 1, 1)
	tracer_mm.mesh = bx
	tracer_mm.instance_count = 800
	var tmi := MultiMeshInstance3D.new(); tmi.multimesh = tracer_mm
	var tm := ShaderMaterial.new(); tm.shader = load("res://shaders/tracer.gdshader"); tmi.material_override = tm
	tmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	tmi.custom_aabb = AABB(Vector3(-FIELD, -100, -FIELD), Vector3(FIELD * 2, 400, FIELD * 2))
	add_child(tmi)

func puff(kind: String, p: Vector3, vel: Vector3, life: float, s0: float, s1: float, col: Color) -> void:
	var arr: Array = particles[kind]
	if arr.size() >= (2900 if kind == "mix" else 880):
		arr.pop_front()
	arr.append([p, vel, 0.0, life, s0, s1, col])

func shoot(p0: Vector3, p1: Vector3, speed: float, arc: float, col: Color, thick: float, length: float, impact: String) -> void:
	if projectiles.size() >= 780:
		return
	var dur := maxf(p0.distance_to(p1) / speed, 0.05)
	projectiles.append([p0, p1, 0.0, dur, arc, col, thick, length, impact])

func _impact(p: Vector3, kind: String) -> void:
	match kind:
		"dust":
			puff("mix", p + Vector3(0, 0.3, 0), Vector3(rng.randf_range(-0.5, 0.5), 1.0, rng.randf_range(-0.5, 0.5)), 1.2, 0.5, 1.8, Color(0.55, 0.46, 0.34, 0.55))
		"shell", "big":
			var big := 1.0 if kind == "shell" else 1.6
			puff("add", p + Vector3(0, 1.0, 0), Vector3.ZERO, 0.25, 3.0 * big, 6.0 * big, Color(1.0, 0.65, 0.25, 1.0))
			for k in 6:
				puff("mix", p + Vector3(rng.randf_range(-1, 1), 0.5, rng.randf_range(-1, 1)), Vector3(rng.randf_range(-2, 2), rng.randf_range(4, 9) * big, rng.randf_range(-2, 2)), rng.randf_range(1.2, 2.0), 1.2, 3.5 * big, Color(0.36, 0.29, 0.2, 0.9))
			for k in 4:
				puff("mix", p + Vector3(rng.randf_range(-2, 2), 1.5, rng.randf_range(-2, 2)), Vector3(rng.randf_range(-0.6, 0.6), 1.6, rng.randf_range(-0.6, 0.6)), rng.randf_range(4.0, 7.0), 2.0, 8.0 * big, Color(0.3, 0.28, 0.26, 0.6))
		"arrow":
			pass

# ======================================================================== camera & HUD
func _build_camera() -> void:
	cam = Camera3D.new()
	cam.fov = 50.0
	cam.far = 3000.0
	cam.near = 0.3
	add_child(cam)
	var c := _centroid(-1)
	cam_yaw = 0.0 if player_side == 0 else PI
	cam_target = Vector3(c.x, 0, c.y)
	cam_dist = 170.0; cam_pitch = -0.42
	_ct = cam_target + Vector3(0, 0, 0); _cd = 320.0; _cy = cam_yaw + 0.6; _cp = -0.8
	var o := overhead_pose()
	cine_pos = o[0]; cine_look = o[1]; _cine_init = true   # intro: glide from a high overview into the first shot
	_apply_cam()

func first_reg(side: int) -> int:
	for i in sim.regs.size():
		if sim.regs[i]["side"] == side and sim.regs[i]["kind"] == "vat":
			return i
	return 0

func snap_cam(reg_i: int, dist: float, pitch: float, yaw_off: float) -> void:
	cam_auto = false
	var c: Vector2 = sim.regs[reg_i]["pos"] if reg_i >= 0 else _centroid(-1)
	cam_target = Vector3(c.x, 0, c.y); cam_dist = dist; cam_pitch = pitch
	cam_yaw = (0.0 if player_side == 0 else PI) + yaw_off
	_ct = Vector3(c.x, h_at(c.x, c.y), c.y); _cd = dist; _cp = pitch; _cy = cam_yaw
	blend_w = 0.0
	_update_cam_ui()
	_apply_cam()
	print("CAM pos=", cam.global_position, " target=", _ct, " reg=", reg_i, " regs=", sim.regs.size())
	for k in mms.keys():
		var m: Dictionary = mms[k]
		var b: PackedFloat32Array = m["mm"].buffer
		var st: int = m["stride"]
		if m["mm"].visible_instance_count > 0:
			print("  MM ", k, " vis=", m["mm"].visible_instance_count, " ic=", m["mm"].instance_count, " buflen=", b.size(), " st=", st, " o0=", Vector3(b[3], b[7], b[11]), " col=", Vector4(b[12], b[13], b[14], b[15]), (" cust=" + str(Vector4(b[16], b[17], b[18], b[19]))) if st == 20 else "", " vis_node=", m["mmi"].is_visible_in_tree())

func activate() -> void:
	cam.make_current()

func _centroid(side: int) -> Vector2:
	var s := Vector2.ZERO; var n := 0.0
	for r in sim.regs:
		if (side < 0 or r["side"] == side) and sim.active(r):
			s += r["pos"]; n += 1.0
	return s / n if n > 0 else Vector2.ZERO

func _hot_spot() -> Vector2:
	var s := Vector2.ZERO; var n := 0.0
	for r in sim.regs:
		if r["state"] == "melee":
			s += r["pos"] * 3.0; n += 3.0
		elif r["state"] == "fire" or r["running"]:
			s += r["pos"]; n += 1.0
	return s / n if n > 0 else _centroid(-1)

## ---- Camera: two rigs (player overhead + event-driven cinematic director) blended smoothly.
## Read-only with respect to the BattleSim: no sim calls, no shared RNG (choices are deterministic).
const BLEND_TIME := 1.25
var blend_w := 1.0            # 0 = overhead rig, 1 = cinematic rig
var shot_kind := "establishing"
var shot_subj := -1           # regiment index the shot is about
var shot_obj := -1            # second regiment (engagement partner)
var shot_point := Vector2.ZERO
var shot_seq := 0             # number of cuts so far (debug/test)
var cine_pos := Vector3.ZERO
var cine_look := Vector3.ZERO
var _cine_init := false
var _cands: Array = []        # pending shot candidates {kind, s, d, pri, t}
var _prev_state: Array = []
var cam_label: Label
var cam_btn: Button
const SHOT_MIN := 3.5
const SHOT_MAX := 8.5
const SHOT_NAMES := {"establishing": "Establishing", "tracking": "Tracking", "flank": "Flank", "low_angle": "Low angle", "rout": "Pursuit", "aftermath": "Aftermath"}

func toggle_camera() -> void:
	set_cinematic(not cam_auto)

func set_cinematic(on: bool) -> void:
	if on == cam_auto:
		return
	cam_auto = on
	if on:
		shot_t = SHOT_MAX   # pick a fresh shot immediately
	else:
		# overhead rig takes over centred on the current action, keeping the player's zoom/orbit
		var hs := _hot_spot()
		cam_target = Vector3(hs.x, 0, hs.y)
		if cam_pitch > -0.5: cam_pitch = -0.75
		cam_dist = maxf(cam_dist, 140.0)
	_update_cam_ui()

func _update_cam_ui() -> void:
	if cam_btn:
		cam_btn.text = "Camera: %s (C)" % ("Cinematic" if cam_auto else "Overhead")
	if cam_label:
		cam_label.text = ("🎥 %s shot" % SHOT_NAMES.get(shot_kind, shot_kind)) if cam_auto else ("Overhead camera — L-stick pan · R-stick orbit/zoom · Y cinematic · RB speed · Back leave" if Controls.last_device == "joy" else ("Overhead camera — drag to pan · pinch to zoom · twist to rotate" if Controls.last_device == "touch" else "Overhead camera — drag to pan, wheel to zoom, right-drag to orbit · C cinematic · T speed · L leave"))

func _cand(kind: String, s_i: int, d_i: int, pri: float) -> void:
	if (s_i < 0 and kind != "aftermath") or s_i >= sim.regs.size():   # aftermath is the only subject-less candidate
		return
	for c in _cands:
		if c["kind"] == kind and c["s"] == s_i:
			c["t"] = sim.t; c["pri"] = maxf(c["pri"], pri)
			return
	_cands.append({"kind": kind, "s": s_i, "d": d_i, "pri": pri, "t": sim.t})

## Called for every BattleSim event the view consumes.
func _director_event(e: Dictionary) -> void:
	match e["k"]:
		"charge": _cand("tracking", int(e["s"]), int(e["d"]), 3.0)
		"volley":
			var si := int(e["s"])
			if int(sim.regs[si]["fired"]) <= 3:   # first exchanges of a firing line are the interesting ones
				_cand("flank", si, int(e["d"]), 1.5)
		"rout": _cand("rout", int(e["s"]), -1, 2.0)
		"end": _cand("aftermath", -1, -1, 9.0)

func _director_poll() -> void:
	if _prev_state.size() != sim.regs.size():
		_prev_state.resize(sim.regs.size())
	for i in sim.regs.size():
		var st: String = sim.regs[i]["state"]
		if st == "melee" and _prev_state[i] != "melee":
			_cand("low_angle", i, int(sim.regs[i]["target"]), 4.0)
		_prev_state[i] = st

func _pick_shot() -> void:
	# drop stale candidates and those about dead/fled regiments
	var best := {}
	var keep: Array = []
	for c in _cands:
		if sim.t - float(c["t"]) > 6.0:
			continue
		if c["s"] >= 0 and c["kind"] != "rout" and not sim.active(sim.regs[c["s"]]):
			continue
		keep.append(c)
		var score: float = c["pri"] - (0.8 if c["kind"] == shot_kind else 0.0) - (sim.t - float(c["t"])) * 0.2
		if best.is_empty() or score > best["score"]:
			best = c.duplicate(); best["score"] = score
	_cands = keep
	if best.is_empty():
		shot_kind = "establishing" if shot_kind != "establishing" or shot_t > 20.0 else shot_kind
		shot_subj = -1; shot_obj = -1
	else:
		shot_kind = best["kind"]; shot_subj = best["s"]; shot_obj = best["d"]
		_cands.erase(_cands.filter(func(c): return c["kind"] == best["kind"] and c["s"] == best["s"])[0])
	if shot_kind == "aftermath":
		shot_subj = -1
	shot_t = 0.0
	shot_seq += 1
	_update_cam_ui()

func _reg_pos(i: int) -> Vector2:
	return sim.regs[i]["pos"] if i >= 0 and i < sim.regs.size() else _hot_spot()

## Desired cinematic camera position + look point for the current shot.
func _cine_pose() -> Array:
	var base_yaw := 0.0 if player_side == 0 else PI
	match shot_kind:
		"tracking", "rout":
			var r: Dictionary = sim.regs[shot_subj]
			var p: Vector2 = r["pos"]
			var f: Vector2 = r["facing"]
			if shot_kind == "rout": f = -f
			if f.length() < 0.01: f = Vector2(0, -1)
			f = f.normalized()
			var side := Vector2(-f.y, f.x)
			var off := -f * 28.0 + side * 22.0
			var cp := p + off
			var look := p + f * 18.0
			return [Vector3(cp.x, h_at(cp.x, cp.y) + 9.0, cp.y), Vector3(look.x, h_at(look.x, look.y) + 2.0, look.y)]
		"flank":
			var a := _reg_pos(shot_subj); var d := _reg_pos(shot_obj)
			var mid := (a + d) * 0.5
			var ax := (d - a); if ax.length() < 1.0: ax = Vector2(0, 1)
			var perp := Vector2(-ax.y, ax.x).normalized()
			var dist := clampf(ax.length() * 0.55, 45.0, 140.0)
			var cp2 := mid + perp * dist + ax.normalized() * dist * 0.15
			return [Vector3(cp2.x, h_at(cp2.x, cp2.y) + 11.0 + shot_t * 0.6, cp2.y), Vector3(mid.x, h_at(mid.x, mid.y) + 1.5, mid.y)]
		"low_angle":
			var m := _reg_pos(shot_subj)
			if shot_obj >= 0: m = (m + _reg_pos(shot_obj)) * 0.5
			var ang := base_yaw + 0.9 + shot_t * 0.07
			var cp3 := m + Vector2(sin(ang), cos(ang)) * 26.0
			return [Vector3(cp3.x, h_at(cp3.x, cp3.y) + 1.6, cp3.y), Vector3(m.x, h_at(m.x, m.y) + 4.5, m.y)]
		"aftermath":
			# slow orbit around the side holding the field, sized to its spread
			var ws: int = sim.winner if sim.winner >= 0 else -1
			var c := _centroid(ws)
			var spread := 0.0
			for r in sim.regs:
				if (ws < 0 or r["side"] == ws) and sim.active(r):
					spread = maxf(spread, (r["pos"] - c).length())
			var dist2 := clampf(spread * 1.3 + 40.0, 70.0, 170.0)
			var ang2 := base_yaw + 0.4 + shot_t * 0.05
			return [Vector3(c.x + sin(ang2) * dist2, h_at(c.x, c.y) + dist2 * 0.42, c.y + cos(ang2) * dist2), Vector3(c.x, h_at(c.x, c.y) + 1.0, c.y)]
	# establishing: wide, slow orbit over the whole field
	var c2 := _centroid(-1)
	var ang3 := base_yaw + 0.35 + shot_t * 0.025
	return [Vector3(c2.x + sin(ang3) * 170.0, h_at(c2.x, c2.y) + 95.0, c2.y + cos(ang3) * 170.0), Vector3(c2.x, h_at(c2.x, c2.y), c2.y)]

func _pad_cam(delta: float) -> void:
	## gamepad sticks / keyboard keys move the overhead camera (and leave cinematic mode)
	if get_viewport().gui_get_focus_owner() != null:
		return
	var mv := Input.get_vector("cursor_left", "cursor_right", "cursor_up", "cursor_down") + Input.get_vector("pan_left", "pan_right", "pan_up", "pan_down")
	var orb := Input.get_action_strength("orbit_right") - Input.get_action_strength("orbit_left")
	var z := Input.get_action_strength("zoom_in") - Input.get_action_strength("zoom_out")
	if mv.length() < 0.05 and absf(orb) < 0.05 and absf(z) < 0.05:
		return
	set_cinematic(false)
	var right := Vector3(cos(_cy), 0, -sin(_cy)); var fwd := Vector3(sin(_cy), 0, cos(_cy))
	cam_target += (right * mv.x + fwd * mv.y) * cam_dist * 0.9 * delta
	cam_yaw -= orb * 1.4 * delta
	cam_dist = clampf(cam_dist * exp(-z * 1.6 * delta), 12.0, 500.0)

func _update_cam(delta: float) -> void:
	_pad_cam(delta)
	shot_t += delta
	_director_poll()
	# ---- cinematic director (always runs so the blend has a live target)
	var shot_valid = shot_subj < 0 or (shot_subj < sim.regs.size() and (sim.active(sim.regs[shot_subj]) or shot_kind == "rout") and sim.regs[shot_subj]["state"] != "fled")
	var better := false
	for c in _cands:
		if c["pri"] > 3.5 and shot_kind != "low_angle" and shot_kind != "aftermath":
			better = true
	if (shot_t > SHOT_MAX) or (not shot_valid) or (shot_t > SHOT_MIN and (better or not _cands.is_empty() and shot_kind == "establishing")) or (finished and shot_kind != "aftermath" and shot_t > 1.5):
		if finished and shot_kind != "aftermath":
			_cand("aftermath", -1, -1, 9.0)
		_pick_shot()
	var pose := _cine_pose()
	if not _cine_init:
		cine_pos = pose[0]; cine_look = pose[1]; _cine_init = true
	var kc := 1.0 - exp(-delta * 2.2)
	cine_pos = cine_pos.lerp(pose[0], kc)
	cine_look = cine_look.lerp(pose[1], 1.0 - exp(-delta * 3.0))
	# ---- overhead rig (player controlled)
	var tt := Vector3(cam_target.x, h_at(cam_target.x, cam_target.z), cam_target.z)
	var k := 1.0 - exp(-delta * 8.0)
	_ct = _ct.lerp(tt, k); _cd = lerpf(_cd, cam_dist, k); _cy = lerp_angle(_cy, cam_yaw, k); _cp = lerpf(_cp, cam_pitch, k)
	# ---- blend
	blend_w = move_toward(blend_w, 1.0 if cam_auto else 0.0, delta / BLEND_TIME)
	_apply_cam()

func overhead_pose() -> Array:
	var dir := Vector3(sin(_cy) * cos(_cp), sin(_cp), cos(_cy) * cos(_cp))
	var p := _ct - dir * _cd
	p.y = maxf(p.y, h_at(p.x, p.z) + 2.0)
	return [p, _ct + Vector3(0, 1.5, 0)]

func _apply_cam() -> void:
	var o := overhead_pose()
	var f := smoothstep(0.0, 1.0, blend_w)
	if not _cine_init:
		f = 0.0
	var p: Vector3 = (o[0] as Vector3).lerp(cine_pos, f)
	var look: Vector3 = (o[1] as Vector3).lerp(cine_look, f)
	p.y = maxf(p.y, h_at(p.x, p.z) + 1.2)
	cam.global_position = p
	if p.distance_to(look) > 0.01:
		cam.look_at(look, Vector3.UP)

var _touches := {}
var _pinch_d := 0.0
var _pinch_a := 0.0
const BATTLE_SPEEDS := [1.0, 2.0, 4.0]

func _pinch() -> Array:
	var ps: Array = _touches.values()
	var d: Vector2 = ps[1] - ps[0]
	return [d.length(), d.angle()]

func _unhandled_input(ev: InputEvent) -> void:
	if not visible:
		return
	if ev.is_action_pressed("battle_speed"):
		var i := BATTLE_SPEEDS.find(time_scale)
		time_scale = BATTLE_SPEEDS[(i + 1) % BATTLE_SPEEDS.size()]
		get_viewport().set_input_as_handled(); return
	if ev.is_action_pressed("battle_leave"):
		leave_requested.emit(bid)
		get_viewport().set_input_as_handled(); return
	if ev is InputEventScreenTouch:
		if ev.pressed:
			_touches[ev.index] = ev.position
			if _touches.size() == 2:
				var p := _pinch(); _pinch_d = p[0]; _pinch_a = p[1]
		else:
			_touches.erase(ev.index)
		return
	if ev is InputEventScreenDrag:
		_touches[ev.index] = ev.position
		set_cinematic(false)
		if _touches.size() == 1:
			var right := Vector3(cos(_cy), 0, -sin(_cy)); var fwd := Vector3(sin(_cy), 0, cos(_cy))
			cam_target -= (right * -ev.relative.x + fwd * -ev.relative.y) * cam_dist * 0.0018
		elif _touches.size() >= 2:
			var p := _pinch()
			if _pinch_d > 1.0 and p[0] > 1.0:
				cam_dist = clampf(cam_dist * _pinch_d / p[0], 12.0, 500.0)
			if Controls.touch_rotate:
				cam_yaw -= angle_difference(_pinch_a, p[1])
			_pinch_d = p[0]; _pinch_a = p[1]
		return
	if Controls.is_emulated(ev):
		return
	if ev is InputEventMouseButton:
		if ev.button_index == MOUSE_BUTTON_WHEEL_UP and ev.pressed:
			set_cinematic(false); cam_dist = maxf(cam_dist * 0.88, 12.0)
		elif ev.button_index == MOUSE_BUTTON_WHEEL_DOWN and ev.pressed:
			set_cinematic(false); cam_dist = minf(cam_dist * 1.13, 500.0)
		elif ev.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_MIDDLE, MOUSE_BUTTON_RIGHT]:
			_drag = ev.button_index if ev.pressed else -1
	elif ev is InputEventMouseMotion and _drag >= 0 and ev.relative.length() > 0.5:
		set_cinematic(false)
		if _drag == MOUSE_BUTTON_LEFT:
			var right := Vector3(cos(_cy), 0, -sin(_cy)); var fwd := Vector3(sin(_cy), 0, cos(_cy))
			cam_target -= (right * -ev.relative.x + fwd * -ev.relative.y) * cam_dist * 0.0018
		else:
			cam_yaw -= ev.relative.x * 0.006
			cam_pitch = clampf(cam_pitch - ev.relative.y * 0.004, -1.4, -0.08)
	if ev.is_action_pressed("camera_toggle", false, true):
		toggle_camera()
		get_viewport().set_input_as_handled()

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Control.new()
	hud.set_anchors_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.theme = Hud.make_theme()
	layer.add_child(hud)
	var top := PanelContainer.new()
	top.set_anchors_preset(Control.PRESET_CENTER_TOP)
	top.position = Vector2(-470, 10); top.custom_minimum_size = Vector2(940, 0)
	hud.add_child(top)
	var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 14)
	top.add_child(h)
	for s in 2:
		var v := VBoxContainer.new(); v.custom_minimum_size = Vector2(330, 0)
		var f := FlagRect.new(); f.custom_minimum_size = Vector2(36, 24); f.set_nation(b["codes"][s])
		var nm := Label.new(); nm.text = "%s  (%s)" % [Sim.nations[b["codes"][s]]["name"], "attacker" if s == 0 else "defender"]
		nm.add_theme_color_override("font_color", Hud.GOLD); nm.add_theme_font_size_override("font_size", 17)
		var hb := HBoxContainer.new(); hb.add_child(f); hb.add_child(nm)
		if s == 1: hb.alignment = BoxContainer.ALIGNMENT_END
		v.add_child(hb)
		var men := ProgressBar.new(); men.max_value = 1.0; men.show_percentage = false; men.custom_minimum_size = Vector2(330, 14)
		var fs := StyleBoxFlat.new(); fs.bg_color = side_col[s]; men.add_theme_stylebox_override("fill", fs)
		men.fill_mode = ProgressBar.FILL_BEGIN_TO_END if s == 0 else ProgressBar.FILL_END_TO_BEGIN
		v.add_child(men)
		var mor := ProgressBar.new(); mor.max_value = 1.0; mor.show_percentage = false; mor.custom_minimum_size = Vector2(330, 8)
		var fm := StyleBoxFlat.new(); fm.bg_color = Color(0.9, 0.8, 0.4); mor.add_theme_stylebox_override("fill", fm)
		mor.fill_mode = men.fill_mode
		v.add_child(mor)
		var lbl := Label.new(); lbl.add_theme_font_size_override("font_size", 13)
		if s == 1: lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		v.add_child(lbl)
		hud_bars[s] = [men, mor, lbl]
		if s == 0:
			h.add_child(v)
			var mid := VBoxContainer.new(); mid.custom_minimum_size = Vector2(220, 0)
			var bt := Label.new(); bt.text = "Battle of %s" % GameData.provinces[b["prov"]]["name"]; bt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			bt.add_theme_font_size_override("font_size", 18); bt.add_theme_color_override("font_color", Hud.GOLD)
			mid.add_child(bt)
			hud_time = Label.new(); hud_time.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER; hud_time.add_theme_font_size_override("font_size", 22)
			mid.add_child(hud_time)
			hud_date = Label.new(); hud_date.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER; hud_date.add_theme_font_size_override("font_size", 12)
			hud_date.add_theme_color_override("font_color", Hud.DIM)
			mid.add_child(hud_date)
			h.add_child(mid)
		else:
			h.add_child(v)
	var bot := PanelContainer.new()
	bot.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	bot.position = Vector2(-430, -62); bot.custom_minimum_size = Vector2(860, 0)
	hud.add_child(bot)
	var bh := HBoxContainer.new(); bh.add_theme_constant_override("separation", 8); bot.add_child(bh)
	var ps: int = b["player_side"]
	var ord: Dictionary = b["orders"][maxi(ps, 0)]
	var ol := Label.new(); ol.text = "Orders: %s, %s formation" % [str(ord.get("objective", "")).capitalize(), str(ord.get("formation", "")).capitalize()]
	ol.add_theme_font_size_override("font_size", 14)
	bh.add_child(ol)
	var sp := Control.new(); sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL; bh.add_child(sp)
	for s2 in [1.0, 2.0, 4.0]:
		var sv: float = s2
		var bb := Button.new(); bb.text = "%d×" % int(s2); bb.pressed.connect(func(): time_scale = sv)
		bh.add_child(bb)
	cam_btn = Button.new(); cam_btn.focus_mode = Control.FOCUS_NONE; cam_btn.pressed.connect(toggle_camera); bh.add_child(cam_btn)
	cam_label = Label.new(); cam_label.set_anchors_preset(Control.PRESET_BOTTOM_LEFT); cam_label.position = Vector2(16, -96)
	cam_label.add_theme_font_size_override("font_size", 15); cam_label.add_theme_color_override("font_outline_color", Color.BLACK); cam_label.add_theme_constant_override("outline_size", 5)
	cam_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(cam_label)
	_update_cam_ui()
	var sk := Button.new(); sk.text = "Skip to result"; sk.pressed.connect(skip); bh.add_child(sk)
	var lv := Button.new(); lv.text = "Leave (battle continues)"; lv.pressed.connect(func(): leave_requested.emit(bid)); bh.add_child(lv)
	hud_feed = RichTextLabel.new()
	hud_feed.bbcode_enabled = true; hud_feed.scroll_following = true
	hud_feed.position = Vector2(14, 150); hud_feed.size = Vector2(420, 200)
	hud_feed.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_feed.add_theme_color_override("font_outline_color", Color.BLACK); hud_feed.add_theme_constant_override("outline_size", 4)
	hud.add_child(hud_feed)

func _reg_name(i: int) -> String:
	var r: Dictionary = sim.regs[i]
	return "%s %s" % [Sim.nations[b["codes"][r["side"]]]["name"], r["def"]["name"]]

func _feed(t: String) -> void:
	hud_feed.append_text("[color=#9a9080]%02d:%02d[/color] %s\n" % [int(sim.t) / 60, int(sim.t) % 60, t])

func _update_hud() -> void:
	for s in 2:
		var bars: Array = hud_bars[s]
		var m0: float = maxf(sim.start_men[s], 1.0)
		bars[0].value = sim.side_men(s) / m0
		bars[1].value = clampf(sim.side_morale(s), 0.0, 1.0)
		var act := sim.side_active(s); var tot := 0
		for r in sim.regs:
			if r["side"] == s: tot += 1
		bars[2].text = "%d / %d men · %d/%d regiments fighting · morale %d%%" % [int(sim.side_men(s)), int(m0), act, tot, int(sim.side_morale(s) * 100)]
	hud_time.text = "%02d:%02d" % [int(sim.t) / 60, int(sim.t) % 60]
	hud_date.text = "Campaign clock: %s (running)" % Sim.date_string()

func skip() -> void:
	if finished:
		return
	while not Sim.step_watched(bid, 1.0, 10.0):
		pass
	finished = true

func _show_result() -> void:
	result_shown = true
	var res: Dictionary = b.get("result", sim.result())
	print("BATTLERESULT ", JSON.stringify(verification_summary()))
	result_panel = PanelContainer.new()
	result_panel.set_anchors_preset(Control.PRESET_CENTER)
	result_panel.custom_minimum_size = Vector2(560, 0)
	result_panel.position = Vector2(-280, -150)
	hud.add_child(result_panel)
	var v := VBoxContainer.new(); v.add_theme_constant_override("separation", 8); result_panel.add_child(v)
	var w: int = res["winner"]
	var ps: int = b["player_side"]
	var t := Label.new()
	t.text = ("VICTORY" if w == ps else "DEFEAT") if ps >= 0 else "%s VICTORIOUS" % Sim.nations[b["codes"][w]]["name"].to_upper()
	t.add_theme_font_size_override("font_size", 42)
	t.add_theme_color_override("font_color", Hud.GOLD if (ps < 0 or w == ps) else Hud.BAD)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var l := Label.new()
	l.text = "Battle of %s — %s wins after %d s of fighting.\n%s losses: %d of %d\n%s losses: %d of %d" % [GameData.provinces[b["prov"]]["name"], Sim.nations[b["codes"][w]]["name"], int(res["time"]),
		Sim.nations[b["codes"][0]]["name"], int(res["losses"][0]), int(res["start"][0]), Sim.nations[b["codes"][1]]["name"], int(res["losses"][1]), int(res["start"][1])]
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(l)
	var l2 := Label.new(); l2.text = "The defeated army retreats; casualties are applied to the campaign armies."
	l2.add_theme_font_size_override("font_size", 12); l2.add_theme_color_override("font_color", Hud.DIM); l2.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(l2)
	var bt := Button.new(); bt.text = "Return to campaign"; bt.custom_minimum_size = Vector2(0, 40)
	bt.pressed.connect(func(): leave_requested.emit(bid))
	v.add_child(bt)

# ======================================================================== per-frame
var perf := {"sim_us": 0, "units_us": 0, "fx_us": 0, "instances": 0}

func _process(delta: float) -> void:
	if sim == null:
		return
	var t0 := Time.get_ticks_usec()
	if not finished:
		if Sim.step_watched(bid, delta, time_scale):
			finished = true
	var t1 := Time.get_ticks_usec()
	vis_t += delta * (time_scale if not finished else 1.0)
	_process_events()
	_update_units(delta * (time_scale if not finished else 1.0))
	var t2 := Time.get_ticks_usec()
	_update_fx(delta * (time_scale if not finished else 1.0))
	perf["sim_us"] = t1 - t0; perf["units_us"] = t2 - t1; perf["fx_us"] = Time.get_ticks_usec() - t2
	var ni := 0
	for m in mms.values():
		ni += int(m["n"])
	perf["instances"] = ni
	_update_cam(delta)
	_update_hud()
	for m in mms.values():
		var mat: ShaderMaterial = m["mmi"].material_override
		if m["stride"] == 20:
			mat.set_shader_parameter("battle_time", vis_t)
	if finished and not result_shown:
		intro_t += delta
		if intro_t > 2.5:
			_show_result()

func _alive_idx(v: Dictionary) -> Array:
	var out: Array = []
	var dead: PackedFloat32Array = v["dead"]
	for k in dead.size():
		if dead[k] < 0.0:
			out.append(k)
	return out

func _soldier_pos3(v: Dictionary, k: int, up: float = 0.0) -> Vector3:
	var p: Vector2 = v["pos"][k]
	return Vector3(p.x, h_at(p.x, p.y) + up, p.y)

func _process_events() -> void:
	var evs: Array = sim.events
	while ev_idx < evs.size():
		var e: Dictionary = evs[ev_idx]
		ev_idx += 1
		_director_event(e)
		match e["k"]:
			"volley": _fx_volley(int(e["s"]), int(e["d"]))
			"charge":
				var v: Dictionary = rv[int(e["s"])]
				var c: Vector2 = sim.regs[int(e["s"])]["pos"]
				for k in 10:
					puff("mix", Vector3(c.x + rng.randf_range(-8, 8), h_at(c.x, c.y) + 0.5, c.y + rng.randf_range(-4, 4)), Vector3(0, 1.0, 0), 2.5, 1.5, 5.0, Color(0.55, 0.47, 0.36, 0.5))
				_feed("[color=#ffd880]%s charge %s![/color]" % [_reg_name(int(e["s"])), _reg_name(int(e["d"]))])
			"rout": _feed("[color=#f08060]%s break and flee![/color]" % _reg_name(int(e["s"])))
			"destroyed": _feed("[color=#f08060]%s destroyed.[/color]" % _reg_name(int(e["s"])))
			"end": _feed("[color=#ffd880]%s hold the field.[/color]" % Sim.nations[b["codes"][int(e["winner"])]]["name"])

func _fx_volley(si: int, di: int) -> void:
	var r: Dictionary = sim.regs[si]
	var v: Dictionary = rv[si]
	var tv: Dictionary = rv[di]
	var d: Dictionary = r["def"]
	var era: String = d["era"]
	var targets := _alive_idx(tv)
	if targets.is_empty():
		return
	var powder: float = POWDER.get(era, 0.5)
	v["fire_t"] = vis_t
	var pcls := projectile_class(r)
	proj_stats[pcls] = proj_stats.get(pcls, 0) + 1
	var alive := _alive_idx(v)
	if r["kind"] == "vat":
		var nshoot := mini(alive.size(), 14)
		var files: int = v["files"]
		var front: Array = alive.filter(func(k): return k / files < 2)
		if front.is_empty(): front = alive
		for q in nshoot:
			var k: int = front[rng.randi() % front.size()]
			var delay := rng.randf_range(0.0, 0.35)
			v["clip"][k] = 3; v["clip_t"][k] = vis_t + delay - 0.4
			var fwd: Vector2 = r["facing"]
			var mp := _soldier_pos3(v, k, 1.5) + Vector3(fwd.x, 0, fwd.y) * 0.9
			var tp := _soldier_pos3(tv, targets[rng.randi() % targets.size()], 1.0)
			if era == "medieval":
				shoot(mp + Vector3(0, 0.4, 0), tp, 42.0, 0.35, Color(0.18, 0.14, 0.1), 0.05, 0.9, "dust")
			else:
				puff("add", mp, Vector3.ZERO, 0.09, 0.5, 0.9, Color(1.0, 0.8, 0.4, 1.0))
				if powder > 0.5:
					puff("mix", mp, Vector3(fwd.x * 1.5, 0.4, fwd.y * 1.5), rng.randf_range(3.0, 5.0), 0.9, 3.4, Color(0.86, 0.86, 0.84, 0.55))
				else:
					puff("mix", mp, Vector3(fwd.x, 0.3, fwd.y), 1.2, 0.3, 1.1, Color(0.8, 0.8, 0.78, 0.3))
				shoot(mp, tp, 260.0 if era in ["c20", "modern"] else 150.0, 0.0, Color(1.0, 0.85, 0.5) if era in ["c20", "modern"] else Color(0.3, 0.3, 0.3), 0.04, 1.6, "dust")
	else:
		var heavy = r["kind"] == "gun"
		for k in alive:
			var fwd2: Vector2 = r["facing"]
			var mp2 := _soldier_pos3(v, k, 1.2 if heavy else 2.0) + Vector3(fwd2.x, 0, fwd2.y) * (2.8 if heavy else 4.0)
			v["recoil"][k] = 1.0
			puff("add", mp2, Vector3.ZERO, 0.15, 2.0, 4.0, Color(1.0, 0.7, 0.3, 1.0))
			for q in 3:
				puff("mix", mp2, Vector3(fwd2.x * 2.0 + rng.randf_range(-1, 1), 0.8, fwd2.y * 2.0 + rng.randf_range(-1, 1)), rng.randf_range(4.0, 7.0), 2.0, 7.0, Color(0.85, 0.85, 0.82, 0.55 if powder > 0.5 else 0.35))
			var tp2 := _soldier_pos3(tv, targets[rng.randi() % targets.size()], 0.5) + Vector3(rng.randf_range(-4, 4), 0, rng.randf_range(-4, 4))
			var spd := 140.0 if heavy else 400.0
			shoot(mp2, tp2, spd, 0.12 if heavy else 0.0, Color(1.0, 0.8, 0.45) if not heavy or era in ["c20", "modern"] else Color(0.12, 0.12, 0.12), 0.18 if heavy else 0.1, 1.2 if heavy else 4.0, "shell" if heavy else "big")

func verification_summary() -> Dictionary:
	var units := []
	var kills := 0.0; var mk := 0.0
	for i in sim.regs.size():
		var r: Dictionary = sim.regs[i]
		units.append({"side": r["side"], "id": r["def"]["id"], "era": r["def"]["era"], "model": r["def"]["model"], "role": r["role"],
			"armor": r["def"]["armor"], "men0": int(r["men0"]), "men": int(r["men"]), "kills": int(r["kills"]), "mkills": int(r.get("mkills", 0.0))})
		kills += r["kills"]; mk += r.get("mkills", 0.0)
	var defs := {}
	for r in sim.regs:
		defs[r["def"]["model"]] = true
	var models := {}
	for k in mms.keys():
		var nm: String = str(k).split("|")[0]
		if (nm.begins_with("P") or nm.begins_with("W")) and defs.has(nm.substr(1)):
			nm = nm.substr(1)   # gun/vehicle team-coloured part (P) and wheels/base (W) multimeshes
		models[nm] = true
	return {"era": GameData.eras[Sim.era]["id"], "codes": b["codes"], "winner": sim.winner, "battle_s": snappedf(sim.t, 0.1),
		"start_men": sim.start_men, "end_men": [int(sim.side_men(0)), int(sim.side_men(1))], "melee_share": snappedf(mk / maxf(kills, 1.0), 0.001),
		"projectiles": proj_stats, "render_models": models.keys(), "units": units}

static func projectile_class(r: Dictionary) -> String:
	var era: String = r["def"]["era"]
	match r["kind"]:
		"vat":
			if era == "medieval": return "arrow"
			return "rifle_tracer" if era in ["c20", "modern"] else "musket_ball"
		"gun":
			if era == "medieval": return "stone_shot"
			return "shell" if era in ["c20", "modern"] else "round_shot"
	return "tank_round" if era in ["c20", "modern"] else "pistol"

func _update_units(dt: float) -> void:
	for m in mms.values():
		m["n"] = 0
	var cpos := cam.global_position
	var vt := vis_t
	for i in rv.size():
		var v: Dictionary = rv[i]
		var r: Dictionary = sim.regs[i]
		var n: int = v["n"]
		var men0: float = maxf(r["men0"], 1.0)
		var want := int(ceil(float(n) * clampf(r["men"] / men0, 0.0, 1.0) - 0.001))
		if r["state"] == "dead":
			want = 0
		var dead: PackedFloat32Array = v["dead"]
		var alive := _alive_idx(v)
		# casualties: soldiers fall when the simulation removes men (front ranks first, with jitter)
		var excess := alive.size() - want
		var files: int = v["files"]
		var fallen := 0
		while excess > 0 and fallen < 4:
			var best := -1; var bs := 1e9
			for k in alive:
				var sc := float(k / files) + rng.randf() * 2.5
				if r["state"] == "rout": sc = rng.randf()
				if sc < bs:
					bs = sc; best = k
			if best < 0:
				break
			dead[best] = vt + rng.randf_range(0.0, 0.25)
			alive.erase(best)
			excess -= 1; fallen += 1
			if v["kind"] == "veh" or v["kind"] == "gun":
				var p3 := _soldier_pos3(v, best, 1.0)
				_impact(p3, "big")
				for q in 5:
					puff("add", p3 + Vector3(0, 1.5, 0), Vector3(0, 2, 0), rng.randf_range(0.6, 1.2), 1.0, 2.5, Color(1.0, 0.5, 0.15, 0.9))
		v["dead"] = dead
		var facing: Vector2 = r["facing"]
		var center: Vector2 = r["pos"]
		var st: String = r["state"]
		var hidden := st == "fled" and center.length() > 260.0
		var spd_base: float = float(r["def"]["speed"]) * (2.6 if r["running"] else 1.0) * (1.8 if r["kind"] == "cav" and r["running"] else 1.0)
		var enemy_pos := center + facing * 3.0
		if r["target"] >= 0:
			enemy_pos = sim.regs[r["target"]]["pos"]
		var pos: PackedVector2Array = v["pos"]
		var yaw: PackedFloat32Array = v["yaw"]
		var clip: PackedInt32Array = v["clip"]
		var clip_t: PackedFloat32Array = v["clip_t"]
		var phase: PackedFloat32Array = v["phase"]
		var model: String = v["model"]
		var is_vat: bool = v["kind"] == "vat" or v["kind"] == "cav"
		var side: int = r["side"]
		for k in n:
			var p: Vector2 = pos[k]
			var dk := dead[k]
			if dk < 0.0:
				var slot := _slot_world(r, v, k, center, facing)
				if st == "melee" and is_vat and k / files < 3:
					# front ranks press into the enemy line and sway
					var toward := (enemy_pos - center).normalized()
					slot += toward * (1.2 + sin(vt * 1.7 + phase[k] * 6.0) * 0.6) + Vector2(sin(vt * 1.3 + phase[k] * 9.0), 0) * 0.5
				var dv := slot - p
				var dist := dv.length()
				var maxs := maxf(spd_base, 1.0) * 1.35 * dt
				var moving := dist > 0.35
				if dist > 0.001:
					p += dv / dist * minf(dist, maxs if dist < 8.0 else maxs * 2.0)
				pos[k] = p
				var face := facing
				if moving and dist > 1.0:
					face = dv.normalized()
				if st == "melee":
					face = (enemy_pos - p).normalized() if (enemy_pos - p).length() > 0.1 else facing
				yaw[k] = lerp_angle(yaw[k], atan2(face.x, face.y), minf(dt * 6.0, 1.0))
				var want_clip := 0
				if st == "rout" or (st == "fled" and not hidden):
					want_clip = 2
				elif moving and dist > 0.6:
					want_clip = 2 if (r["running"] or dist > 4.0) else 1
				elif st == "melee":
					want_clip = 4
				elif st == "fire" and clip[k] == 3 and vt - clip_t[k] < 2.0:
					want_clip = 3
				else:
					want_clip = 0
				if want_clip != clip[k]:
					clip[k] = want_clip
					clip_t[k] = vt - phase[k] * 3.0 if want_clip != 3 else clip_t[k]
			if hidden and dk < 0.0:
				continue
			if dk >= 0.0 and v["kind"] != "vat" and v["kind"] != "cav":
				pass
			var y := h_at(p.x, p.y)
			var d2 := cpos.distance_to(Vector3(p.x, y, p.y))
			if is_vat:
				var lod := 1 if d2 > LOD_DIST else 0
				var c := Vector2.ZERO; var ct := 0.0; var spd := 1.0
				if dk >= 0.0:
					c = _clip(model, "die"); ct = dk; spd = 1.0
				else:
					var cname: String = ["idle", "walk", "run", "fire", "melee"][clip[k]]
					c = _clip(model, cname); ct = clip_t[k]
					if clip[k] == 1: spd = clampf(spd_base / (3.0 if v["kind"] == "cav" else 1.4), 0.6, 1.8)
					elif clip[k] == 2: spd = 1.0 + phase[k] * 0.15
					elif clip[k] == 3: c = Vector2(c.x, -c.y)
				_put(mms["%s|%d|%d" % [model, side, lod]], yaw[k], Vector3(p.x, y, p.y), 1.0, Vector4(c.x, c.y, ct, spd))
			else:
				var rec: PackedFloat32Array = v["recoil"]
				var back := Vector2(sin(yaw[k]), cos(yaw[k])) * rec[k] * -0.8
				rec[k] = maxf(rec[k] - dt * 2.0, 0.0)
				var key := ("W%s" % model) if dk >= 0.0 else ("P%s|%d" % [model, side])
				_put(mms[key], yaw[k], Vector3(p.x + back.x, y, p.y + back.y), 1.0, Vector4.ZERO)
				if dk >= 0.0 and rng.randf() < dt * 3.0 and vt - dk < 25.0:
					puff("mix", Vector3(p.x, y + 2.0, p.y), Vector3(0.6, 2.5, 0.2), 5.0, 1.0, 5.0, Color(0.12, 0.11, 0.1, 0.55))
					puff("add", Vector3(p.x + rng.randf_range(-0.6, 0.6), y + 1.2, p.y), Vector3(0, 1.5, 0), 0.5, 0.8, 1.4, Color(1.0, 0.45, 0.1, 0.8))
				if v.has("crew_model"):
					var cm: String = v["crew_model"]
					for q in 3:
						var off := Vector2([-1.4, 1.4, 0.0][q], [-1.6, -1.8, -3.2][q])
						var f := Vector2(sin(yaw[k]), cos(yaw[k]))
						var rt := Vector2(f.y, -f.x)
						var cp := p + rt * off.x + f * off.y
						var cy := h_at(cp.x, cp.y)
						var lod2 := 1 if d2 > LOD_DIST else 0
						var cc := Vector2.ZERO; var cct := 0.0
						if dk >= 0.0 or st == "dead":
							cc = _clip(cm, "die"); cct = dk if dk >= 0.0 else vt
						elif st == "rout" or st == "fled":
							if hidden: continue
							cc = _clip(cm, "run"); cct = phase[k]
						else:
							cc = _clip(cm, "idle" if vt - float(v["fire_t"]) > 1.5 or q == 2 else "melee"); cct = phase[k] * 2.0 + q
						_put(mms["%s|%d|%d" % [cm, side, lod2]], yaw[k], Vector3(cp.x, cy, cp.y), 1.0, Vector4(cc.x, cc.y, cct, 1.0))
			# dust under fast cavalry / vehicles
			if dk < 0.0 and (v["kind"] == "cav" or v["kind"] == "veh") and r["moving"] and rng.randf() < dt * (0.6 if v["kind"] == "cav" else 2.0):
				puff("mix", Vector3(p.x, y + 0.4, p.y), Vector3(0, 0.6, 0), 2.5, 1.0, 3.5, Color(0.55, 0.47, 0.36, 0.45))
		v["pos"] = pos; v["yaw"] = yaw; v["clip"] = clip; v["clip_t"] = clip_t
		# banner follows the regiment's centre
		var bn: Node3D = banners[i]
		var show_b := st != "dead" and not hidden and alive.size() > 0
		bn.visible = show_b
		if show_b:
			var bp = center - facing * (float(v["ranks"]) * 0.5 * v["sp"].y + 0.8)
			bn.position = Vector3(bp.x, h_at(bp.x, bp.y), bp.y)
			bn.rotation.y = atan2(facing.x, facing.y) + PI * 0.5
			bn.get_meta("mat").set_shader_parameter("time_s", vt)
	for m in mms.values():
		var mm: MultiMesh = m["mm"]
		mm.buffer = m["buf"]
		mm.visible_instance_count = m["n"]

func _put(m: Dictionary, a: float, o: Vector3, s: float, custom: Vector4) -> void:
	var k: int = m["n"]
	if k >= m["cap"]:
		return
	var st: int = m["stride"]
	var buf: PackedFloat32Array = m["buf"]
	var c := cos(a) * s; var sn := sin(a) * s
	var i := k * st
	buf[i] = c; buf[i + 1] = 0.0; buf[i + 2] = sn; buf[i + 3] = o.x
	buf[i + 4] = 0.0; buf[i + 5] = s; buf[i + 6] = 0.0; buf[i + 7] = o.y
	buf[i + 8] = -sn; buf[i + 9] = 0.0; buf[i + 10] = c; buf[i + 11] = o.z
	buf[i + 12] = 1.0; buf[i + 13] = 1.0; buf[i + 14] = 1.0; buf[i + 15] = 1.0
	if st == 20:
		buf[i + 16] = custom.x; buf[i + 17] = custom.y; buf[i + 18] = custom.z; buf[i + 19] = custom.w
	m["buf"] = buf
	m["n"] = k + 1

func _update_fx(dt: float) -> void:
	# projectiles
	var keep: Array = []
	var tb := PackedFloat32Array(); tb.resize(800 * 16)
	var tn := 0
	for pr in projectiles:
		pr[2] += dt
		var u: float = pr[2] / pr[3]
		if u >= 1.0:
			_impact(pr[1], pr[8])
			continue
		keep.append(pr)
		var p0: Vector3 = pr[0]; var p1: Vector3 = pr[1]
		var arc: float = pr[4] * p0.distance_to(p1)
		var p := p0.lerp(p1, u) + Vector3(0, 4.0 * arc * u * (1.0 - u), 0)
		var pn := p0.lerp(p1, minf(u + 0.02, 1.0)) + Vector3(0, 4.0 * arc * minf(u + 0.02, 1.0) * (1.0 - minf(u + 0.02, 1.0)), 0)
		var dir := (pn - p).normalized()
		if dir.length() < 0.5: dir = Vector3.FORWARD
		var zx := dir; var xx := zx.cross(Vector3.UP).normalized()
		if xx.length() < 0.5: xx = Vector3.RIGHT
		var yx := xx.cross(zx).normalized()
		var th: float = pr[6]; var ln: float = pr[7]
		var bx := xx * th; var by := yx * th; var bz := zx * ln
		var i := tn * 16
		tb[i] = bx.x; tb[i + 1] = by.x; tb[i + 2] = bz.x; tb[i + 3] = p.x
		tb[i + 4] = bx.y; tb[i + 5] = by.y; tb[i + 6] = bz.y; tb[i + 7] = p.y
		tb[i + 8] = bx.z; tb[i + 9] = by.z; tb[i + 10] = bz.z; tb[i + 11] = p.z
		var col: Color = pr[5]
		tb[i + 12] = col.r; tb[i + 13] = col.g; tb[i + 14] = col.b; tb[i + 15] = 1.0
		tn += 1
		if pr[6] > 0.15 and rng.randf() < 0.5:
			puff("mix", p, Vector3.ZERO, 1.2, 0.4, 1.0, Color(0.8, 0.8, 0.8, 0.25))
	projectiles = keep
	tracer_mm.buffer = tb
	tracer_mm.visible_instance_count = tn
	# particles (camera-facing; size and alpha over lifetime)
	for kind in ["mix", "add"]:
		var arr: Array = particles[kind]
		var mm: MultiMesh = pmm[kind]
		var cap := mm.instance_count
		var buf := PackedFloat32Array(); buf.resize(cap * 16)
		var out: Array = []
		var n := 0
		for pa in arr:
			pa[2] += dt
			if pa[2] >= pa[3]:
				continue
			out.append(pa)
			var vel: Vector3 = pa[1]
			pa[0] += vel * dt
			pa[1] = vel * (1.0 - minf(dt * 0.8, 1.0)) + Vector3(0.35, 0.0, 0.1) * dt
			var u: float = pa[2] / pa[3]
			var s: float = lerpf(pa[4], pa[5], sqrt(u))
			var col: Color = pa[6]
			var a: float = col.a * (1.0 - u) * minf(u * 8.0 + 0.3, 1.0)
			var p: Vector3 = pa[0]
			var i := n * 16
			buf[i] = s; buf[i + 3] = p.x; buf[i + 5] = s; buf[i + 7] = p.y; buf[i + 10] = s; buf[i + 11] = p.z
			buf[i + 12] = col.r; buf[i + 13] = col.g; buf[i + 14] = col.b; buf[i + 15] = a
			n += 1
			if n >= cap:
				break
		particles[kind] = out
		mm.buffer = buf
		mm.visible_instance_count = n
