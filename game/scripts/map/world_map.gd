## 3D strategic world map: terrain chunks + political shader, army/battle markers, labels, trees, picking.
class_name WorldMap
extends Node3D

const CHUNKS_X := 8
const CHUNKS_Z := 4
const LUT_W := 1024

signal province_clicked(pid: int, button: int)

var mat: ShaderMaterial
var lut_img: Image
var lut_tex: ImageTexture
var lut_dirty := true
var selected_pid := -1
var hover_code := ""
var camera: Camera3D
var cam_dist := 60.0

var army_nodes := {}       # aid -> Node3D
var battle_nodes := {}     # bid -> Node3D
var siege_nodes := {}      # pid -> Node3D
var country_labels := {}   # code -> Label3D
var prov_labels: Array = []
var labels_dirty := true
var path_mesh: MeshInstance3D
var path_army := -1
var selected_army := -1
var _std_scene: PackedScene
var _battle_scene: PackedScene
var _star_scene: PackedScene
var _ship_sail: PackedScene
var _ship_steel: PackedScene
var _font: Font
var _time := 0.0
var trees: Array = []
var cities_root: Node3D

func build() -> void:
	GameData.load_all()
	mat = ShaderMaterial.new()
	mat.shader = load("res://shaders/map.gdshader")
	var htex := ImageTexture.create_from_image(GameData.height_image)
	var ptex := ImageTexture.create_from_image(GameData.prov_image)
	lut_img = Image.create(LUT_W, 2, false, Image.FORMAT_RGBA8)
	lut_tex = ImageTexture.create_from_image(lut_img)
	mat.set_shader_parameter("height_tex", htex)
	mat.set_shader_parameter("albedo_tex", GameData.albedo_texture)
	mat.set_shader_parameter("prov_tex", ptex)
	mat.set_shader_parameter("lut_tex", lut_tex)
	mat.set_shader_parameter("prov_size", Vector2(GameData.raster_w, GameData.raster_h))
	mat.set_shader_parameter("height_scale", GameData.HEIGHT_SCALE)
	var cw := GameData.MAP_W / CHUNKS_X
	var ch := GameData.MAP_H / CHUNKS_Z
	for cx in CHUNKS_X:
		for cz in CHUNKS_Z:
			var pm := PlaneMesh.new()
			pm.size = Vector2(cw, ch)
			pm.subdivide_width = int(cw * 2.2)
			pm.subdivide_depth = int(ch * 2.2)
			pm.custom_aabb = AABB(Vector3(-cw / 2, -1.0, -ch / 2), Vector3(cw, 6.0, ch))
			var mi := MeshInstance3D.new()
			mi.mesh = pm
			mi.material_override = mat
			mi.position = Vector3(cx * cw + cw / 2, 0, cz * ch + ch / 2)
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			add_child(mi)
	# deep ocean backdrop beyond the map edges
	var back := MeshInstance3D.new()
	var bp := PlaneMesh.new(); bp.size = Vector2(1400, 900)
	back.mesh = bp
	var bm := StandardMaterial3D.new(); bm.albedo_color = Color(0.03, 0.09, 0.17); bm.roughness = 0.5
	back.material_override = bm
	back.position = Vector3(180, -0.12, 90)
	add_child(back)
	_std_scene = load("res://assets/models/army_standard.glb")
	_battle_scene = load("res://assets/models/battle_marker.glb")
	_star_scene = load("res://assets/models/capital_star.glb")
	_ship_sail = load("res://assets/models/ship_sail.glb")
	_ship_steel = load("res://assets/models/ship_steel.glb")
	path_mesh = MeshInstance3D.new()
	path_mesh.mesh = ImmediateMesh.new()
	var pmat := StandardMaterial3D.new()
	pmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	pmat.vertex_color_use_as_albedo = true
	pmat.no_depth_test = true
	pmat.render_priority = 2
	path_mesh.material_override = pmat
	add_child(path_mesh)
	cities_root = Node3D.new(); add_child(cities_root)
	_build_trees()
	_build_cities()
	_build_prov_labels()
	Sim.ownership_changed.connect(func(_p, _o, _n): lut_dirty = true; labels_dirty = true)
	Sim.armies_changed.connect(func(): pass)
	Sim.era_changed.connect(func(_e): apply_era(); _refresh_ships())
	Sim.game_started.connect(func(): lut_dirty = true; labels_dirty = true; apply_era())
	apply_era()

# ---------------- political LUT ----------------
func refresh_lut() -> void:
	lut_img.fill(Color(0, 0, 0, 0))
	var enemies: Array = Sim.enemies_of(Sim.player) if Sim.player != "" else []
	for pid in GameData.province_ids:
		if pid >= LUT_W:
			continue
		var o: String = Sim.prov_owner.get(pid, "")
		if o == "":
			continue
		var c: Color = Sim.nations[o]["color"] if Sim.nations.has(o) else GameData.nation_color(o)
		lut_img.set_pixel(pid, 0, Color(c.r, c.g, c.b, 1.0))
		var f := Color(0, 0, 0, 0)
		if pid == selected_pid:
			f.r = 1.0
		if o == hover_code:
			f.g = 1.0
		if enemies.has(o):
			f.b = 1.0
		lut_img.set_pixel(pid, 1, f)
	lut_tex.update(lut_img)
	lut_dirty = false

func set_selected_province(pid: int) -> void:
	selected_pid = pid
	lut_dirty = true

func set_hover_country(code: String) -> void:
	if code != hover_code:
		hover_code = code
		lut_dirty = true

func apply_era() -> void:
	var tints := [Vector3(1.04, 0.97, 0.85), Vector3(1.03, 0.98, 0.88), Vector3(1.02, 1.0, 0.94), Vector3(1.0, 1.0, 0.98), Vector3(0.98, 1.0, 1.03)]
	var sep := [0.42, 0.3, 0.16, 0.06, 0.0]
	var e := clampi(Sim.era, 0, 4)
	mat.set_shader_parameter("era_tint", tints[e])
	mat.set_shader_parameter("era_sepia", sep[e])

# ---------------- decoration ----------------
func _build_trees() -> void:
	var rng := RandomNumberGenerator.new(); rng.seed = 7
	var kinds := {"forest": ["tree_conifer", "tree_broadleaf"], "jungle": ["tree_palm", "tree_broadleaf"], "plains": ["tree_broadleaf"], "hills": ["tree_conifer"], "tundra": ["tree_conifer"]}
	var dens := {"forest": 1.0, "jungle": 1.0, "plains": 0.12, "hills": 0.25, "tundra": 0.15}
	var buckets := {}
	for pid in GameData.province_ids:
		var p: Dictionary = GameData.provinces[pid]
		var terr: String = p["terrain"]
		if not kinds.has(terr):
			continue
		var w := GameData.lonlat_to_world(p["lon"], p["lat"])
		var radius := clampf(sqrt(float(p["area"])) / 111.0 * 0.6, 0.6, 9.0)
		var n := int(clampf(float(p["area"]) / 2500.0, 4.0, 160.0) * dens[terr])
		for i in n:
			var x := w.x + rng.randf_range(-radius, radius)
			var z := w.y + rng.randf_range(-radius, radius) * 0.8
			if GameData.province_at_world(x, z) != pid:
				continue
			var kind: String = kinds[terr][rng.randi() % kinds[terr].size()]
			if not buckets.has(kind):
				buckets[kind] = []
			var s := rng.randf_range(0.05, 0.085)
			var tr := Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s, s)), Vector3(x, GameData.surface_y(x, z) - 0.01, z))
			buckets[kind].append(tr)
	for kind in buckets.keys():
		var mesh := _first_mesh(load("res://assets/models/%s.glb" % kind))
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true  # GL Compatibility: vertex COLOR is black without instance colours
		mm.mesh = mesh
		mm.instance_count = buckets[kind].size()
		for i in buckets[kind].size():
			mm.set_instance_transform(i, buckets[kind][i])
			mm.set_instance_color(i, Color.WHITE)
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.material_override = vc_material()
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mmi.visibility_range_end = 70.0
		mmi.visibility_range_end_margin = 10.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		add_child(mmi)
		trees.append(mmi)

func _build_cities() -> void:
	for pid in GameData.province_ids:
		var p: Dictionary = GameData.provinces[pid]
		var pop := float(p.get("city_pop", 0))
		if pop <= 0 and not p.get("capital_city", false):
			continue
		var lvl := 0
		if pop > 2.0e6 or p.get("capital_city", false):
			lvl = 2
		elif pop > 5.0e5:
			lvl = 1
		var c: Node3D = load("res://assets/models/city_%d.glb" % lvl).instantiate()
		apply_vc(c)
		var w := GameData.lonlat_to_world(p["lon"], p["lat"])
		c.position = Vector3(w.x, GameData.surface_y(w.x, w.y), w.y)
		c.scale = Vector3.ONE * 0.1
		c.set_meta("pid", pid)
		cities_root.add_child(c)

func _build_prov_labels() -> void:
	for pid in GameData.province_ids:
		var p: Dictionary = GameData.provinces[pid]
		var l := Label3D.new()
		l.text = p["name"]
		l.font_size = 40
		l.pixel_size = 0.0065
		l.outline_size = 10
		l.modulate = Color(1, 0.97, 0.88, 0.9)
		l.outline_modulate = Color(0, 0, 0, 0.8)
		l.billboard = BaseMaterial3D.BILLBOARD_DISABLED
		l.rotation = Vector3(-PI / 2, 0, 0)
		var w := GameData.lonlat_to_world(p["lon"], p["lat"])
		l.position = Vector3(w.x, GameData.surface_y(w.x, w.y) + 0.12, w.y + 0.35)
		l.no_depth_test = false
		l.visible = false
		add_child(l)
		prov_labels.append(l)

func refresh_country_labels() -> void:
	labels_dirty = false
	var seen := {}
	for code in Sim.nation_provs.keys():
		var provs: Array = Sim.nation_provs[code]
		if provs.is_empty() or not Sim.nations[code]["alive"]:
			continue
		# area-weighted centroid of the largest connected-ish cluster (approximate: weight by area near capital)
		var cap: int = Sim.nations[code]["capital"]
		var cpos := GameData.lonlat_to_world(GameData.provinces[cap]["lon"], GameData.provinces[cap]["lat"]) if GameData.provinces.has(cap) else Vector2.ZERO
		var sum := Vector2.ZERO; var wsum := 0.0; var area := 0.0
		var minx := 1e9; var maxx := -1e9
		for pid in provs:
			var p: Dictionary = GameData.provinces[pid]
			var w := GameData.lonlat_to_world(p["lon"], p["lat"])
			if w.distance_to(cpos) > 40.0:
				continue
			var a := float(p["area"])
			sum += w * a; wsum += a; area += a
			minx = minf(minx, w.x); maxx = maxf(maxx, w.x)
		if wsum <= 0:
			continue
		var c := sum / wsum
		seen[code] = true
		var l: Label3D = country_labels.get(code)
		if l == null:
			l = Label3D.new()
			l.font_size = 96
			l.outline_size = 18
			l.billboard = BaseMaterial3D.BILLBOARD_DISABLED
			l.rotation = Vector3(-PI / 2, 0, 0)
			l.modulate = Color(1, 0.96, 0.85, 0.95)
			l.outline_modulate = Color(0.05, 0.04, 0.03, 0.85)
			l.uppercase = true
			add_child(l)
			country_labels[code] = l
		l.text = Sim.nations[code]["name"]
		var size_u := clampf(sqrt(area) / 111.0, 0.8, 22.0)
		l.pixel_size = clampf(size_u * 0.0035, 0.004, 0.05)
		l.set_meta("size", size_u)
		l.position = Vector3(c.x, GameData.surface_y(c.x, c.y) + 0.3, c.y)
	for code in country_labels.keys():
		if not seen.has(code):
			country_labels[code].queue_free()
			country_labels.erase(code)

# ---------------- markers ----------------
func _first_mesh(scene: PackedScene) -> Mesh:
	var n: Node = scene.instantiate()
	var stack := [n]
	while stack.size() > 0:
		var x: Node = stack.pop_back()
		if x is MeshInstance3D:
			var m: Mesh = x.mesh
			n.free()
			return m
		stack.append_array(x.get_children())
	n.free()
	return null

static var _vc_mat: StandardMaterial3D = null
static func vc_material() -> StandardMaterial3D:
	if _vc_mat == null:
		_vc_mat = StandardMaterial3D.new()
		_vc_mat.vertex_color_use_as_albedo = true
		_vc_mat.roughness = 0.9
	return _vc_mat

static func apply_vc(node: Node) -> void:
	var stack := [node]
	while stack.size() > 0:
		var x: Node = stack.pop_back()
		stack.append_array(x.get_children())
		if x is MeshInstance3D:
			x.material_override = vc_material()

static var _team_mats := {}
static func team_material(col: Color) -> ShaderMaterial:
	var k := col.to_html()
	if not _team_mats.has(k):
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/team_prop.gdshader")
		m.set_shader_parameter("team_color", col)
		_team_mats[k] = m
	return _team_mats[k]

func _tint(node: Node, col: Color) -> void:
	var stack := [node]
	while stack.size() > 0:
		var x: Node = stack.pop_back()
		stack.append_array(x.get_children())
		if x is MeshInstance3D:
			x.material_override = team_material(col)

func _make_army_node(a: Dictionary) -> Node3D:
	var root := Node3D.new()
	var std: Node3D = _std_scene.instantiate()
	var col: Color = Sim.nations[a["owner"]]["color"]
	_tint(std, col.lightened(0.15))
	std.name = "Standard"
	root.add_child(std)
	var ship := Node3D.new(); ship.name = "Ship"
	root.add_child(ship)
	var lab := Label3D.new()
	lab.name = "Label"
	lab.font_size = 44
	lab.outline_size = 12
	lab.pixel_size = 0.01
	lab.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	lab.no_depth_test = true
	lab.render_priority = 3
	lab.position = Vector3(0, 3.4, 0)
	lab.modulate = Color(1, 1, 1)
	lab.outline_modulate = col.darkened(0.6)
	root.add_child(lab)
	var ring := MeshInstance3D.new()
	ring.name = "Ring"
	var tm := TorusMesh.new(); tm.inner_radius = 0.9; tm.outer_radius = 1.15; tm.rings = 24; tm.ring_segments = 6
	ring.mesh = tm
	var rm := StandardMaterial3D.new(); rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; rm.albedo_color = Color(1, 0.9, 0.4)
	ring.material_override = rm
	ring.scale = Vector3(1, 0.2, 1)
	ring.visible = false
	root.add_child(ring)
	add_child(root)
	return root

func _refresh_ships() -> void:
	for aid in army_nodes.keys():
		var ship: Node3D = army_nodes[aid].get_node("Ship")
		for c in ship.get_children():
			c.queue_free()
		ship.set_meta("built", false)

func update_markers() -> void:
	var s := clampf(cam_dist * 0.02, 0.3, 2.6)
	var far_view := cam_dist > 100.0
	var seen := {}
	for aid in Sim.armies.keys():
		var a: Dictionary = Sim.armies[aid]
		seen[aid] = true
		var n: Node3D = army_nodes.get(aid)
		if n == null:
			n = _make_army_node(a)
			army_nodes[aid] = n
		var ll := Sim.army_pos_lonlat(a)
		var w := GameData.lonlat_to_world(ll.x, ll.y)
		var at_sea = a["node"] >= GameData.SEA_NODE or (a["path"].size() > 0 and int(a["path"][0]) >= GameData.SEA_NODE and a["progress"] > 0.5)
		var y := 0.0 if at_sea else GameData.surface_y(w.x, w.y)
		# fan out stacked armies in one province
		var k := 0
		for o in Sim.armies_in(a["node"]):
			if o["id"] == aid:
				break
			k += 1
		var off := Vector2(cos(k * 2.1), sin(k * 2.1)) * 0.5 * k * s
		n.position = Vector3(w.x + off.x, y, w.y + off.y)
		n.scale = Vector3.ONE * s
		var ship: Node3D = n.get_node("Ship")
		ship.visible = at_sea
		if at_sea and not ship.get_meta("built", false):
			var sh: Node3D = (_ship_sail if Sim.era <= 2 else _ship_steel).instantiate()
			apply_vc(sh)
			sh.scale = Vector3.ONE * 0.35
			ship.add_child(sh)
			ship.set_meta("built", true)
		# strategic declutter: at world zoom only show armies that matter to the player
		n.visible = not far_view or a["owner"] == Sim.player or Sim.at_war(a["owner"], Sim.player) or a["state"] == "battle" or a["state"] == "siege"
		n.get_node("Standard").visible = true
		var lab: Label3D = n.get_node("Label")
		var men := Sim.army_men(a)
		lab.text = "%s %s" % [_fmt_men(men), "⚔" if a["state"] == "battle" else ("⛫" if a["state"] == "siege" else "")]
		lab.modulate = Color(1, 0.95, 0.6) if a["owner"] == Sim.player else Color(1, 1, 1)
		lab.visible = cam_dist < 140.0
		n.get_node("Ring").visible = aid == selected_army
	for aid in army_nodes.keys():
		if not seen.has(aid):
			army_nodes[aid].queue_free()
			army_nodes.erase(aid)
	# battles
	var bseen := {}
	for bid in Sim.battles.keys():
		var b: Dictionary = Sim.battles[bid]
		if b["done"]:
			continue
		bseen[bid] = true
		var bn: Node3D = battle_nodes.get(bid)
		if bn == null:
			bn = _battle_scene.instantiate()
			apply_vc(bn)
			add_child(bn)
			battle_nodes[bid] = bn
		var p: Dictionary = GameData.provinces[b["prov"]]
		var w2 := GameData.lonlat_to_world(p["lon"], p["lat"])
		bn.position = Vector3(w2.x, GameData.surface_y(w2.x, w2.y) + 0.2 * s, w2.y)
		bn.scale = Vector3.ONE * s * 1.3
		bn.rotation.y = _time * 1.5
	for bid in battle_nodes.keys():
		if not bseen.has(bid):
			battle_nodes[bid].queue_free()
			battle_nodes.erase(bid)
	# sieges
	var sseen := {}
	for pid in Sim.sieges.keys():
		sseen[pid] = true
		var sn: Node3D = siege_nodes.get(pid)
		if sn == null:
			sn = MeshInstance3D.new()
			var tm := TorusMesh.new(); tm.inner_radius = 1.3; tm.outer_radius = 1.6; tm.rings = 32; tm.ring_segments = 4
			sn.mesh = tm
			var m := StandardMaterial3D.new(); m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; m.albedo_color = Color(0.9, 0.2, 0.1)
			sn.material_override = m
			add_child(sn)
			siege_nodes[pid] = sn
		var p2: Dictionary = GameData.provinces[pid]
		var w3 := GameData.lonlat_to_world(p2["lon"], p2["lat"])
		sn.position = Vector3(w3.x, GameData.surface_y(w3.x, w3.y) + 0.05, w3.y)
		var prog: float = Sim.sieges[pid].get("progress", 0.0) / maxf(Sim.siege_days_needed(pid), 1.0)
		sn.scale = Vector3(s, 0.15, s) * (1.0 + 0.3 * sin(_time * 4.0))
		sn.get_meta("x", 0)
		(sn as MeshInstance3D).material_override.albedo_color = Color(0.9, 0.2 + prog * 0.6, 0.1)
	for pid in siege_nodes.keys():
		if not sseen.has(pid):
			siege_nodes[pid].queue_free()
			siege_nodes.erase(pid)

func _fmt_men(m: float) -> String:
	if m >= 1000.0:
		return "%.1fk" % (m / 1000.0)
	return str(int(m))

func update_path() -> void:
	var im: ImmediateMesh = path_mesh.mesh
	im.clear_surfaces()
	if selected_army < 0 or not Sim.armies.has(selected_army):
		return
	var a: Dictionary = Sim.armies[selected_army]
	if a["path"].is_empty():
		return
	var pts: Array = []
	var ll := Sim.army_pos_lonlat(a)
	var w := GameData.lonlat_to_world(ll.x, ll.y)
	pts.append(Vector3(w.x, GameData.surface_y(w.x, w.y) + 0.15, w.y))
	for nd in a["path"]:
		pts.append(GameData.node_world(int(nd)) + Vector3(0, 0.15, 0))
	im.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var hw := clampf(cam_dist * 0.002, 0.05, 0.4)
	var col := Color(1.0, 0.85, 0.3) if a["owner"] == Sim.player else Color(0.9, 0.3, 0.2)
	for i in pts.size() - 1:
		var p0: Vector3 = pts[i]; var p1: Vector3 = pts[i + 1]
		var d := (p1 - p0); d.y = 0
		if d.length() < 0.001:
			continue
		var side := Vector3(-d.z, 0, d.x).normalized() * hw
		# dashed
		var segs := int(d.length() / (hw * 6.0)) + 1
		for k in segs:
			if k % 2 == 1:
				continue
			var a0 := p0.lerp(p1, float(k) / segs); var a1 := p0.lerp(p1, float(k + 1) / segs)
			im.surface_set_color(col)
			im.surface_add_vertex(a0 - side); im.surface_add_vertex(a0 + side); im.surface_add_vertex(a1 + side)
			im.surface_add_vertex(a0 - side); im.surface_add_vertex(a1 + side); im.surface_add_vertex(a1 - side)
	im.surface_end()

func _process(delta: float) -> void:
	_time += delta
	if mat == null:
		return
	mat.set_shader_parameter("time_s", _time)
	mat.set_shader_parameter("cam_dist", cam_dist)
	if lut_dirty:
		refresh_lut()
	if labels_dirty and Sim.running:
		refresh_country_labels()
	update_markers()
	update_path()
	# label LOD
	for code in country_labels.keys():
		var l: Label3D = country_labels[code]
		var sz: float = l.get_meta("size", 1.0)
		var show := sz * 9.0 > cam_dist * 0.35 and sz * 9.0 < cam_dist * 6.0
		l.visible = show
	var show_prov := cam_dist < 26.0
	for l in prov_labels:
		l.visible = show_prov

# ---------------- picking ----------------
func ray_to_world(screen: Vector2) -> Variant:
	if camera == null:
		return null
	var o := camera.project_ray_origin(screen)
	var d := camera.project_ray_normal(screen)
	if absf(d.y) < 1e-4:
		return null
	var y := 0.0
	var p := Vector3.ZERO
	for i in 4:
		var t := (y - o.y) / d.y
		if t < 0:
			return null
		p = o + d * t
		y = GameData.surface_y(p.x, p.z)
	return p

func province_at_screen(screen: Vector2) -> int:
	var p = ray_to_world(screen)
	if p == null:
		return 0
	var pid := GameData.province_at_world(p.x, p.z)
	return pid if GameData.provinces.has(pid) else 0

func army_at_screen(screen: Vector2) -> int:
	var best := -1; var bd := 28.0
	for aid in army_nodes.keys():
		var n: Node3D = army_nodes[aid]
		var top := n.global_position + Vector3(0, 1.6 * n.scale.y, 0)
		if camera.is_position_behind(top):
			continue
		var sp := camera.unproject_position(top)
		var sp2 := camera.unproject_position(n.global_position)
		var dd := minf(sp.distance_to(screen), sp2.distance_to(screen))
		if dd < bd:
			bd = dd; best = aid
	return best
