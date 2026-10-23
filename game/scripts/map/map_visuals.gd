## Visual pass (graphics-owned): overworld army markers built from the era's battle-kit soldiers.
## Add as a child of the WorldMap (one line, see out/INTEGRATION.md Requests):
##     map.add_child(preload("res://scripts/map/map_visuals.gd").new())
## Swaps the mesh of each army node's "Standard" child for res://assets/models/map_marker_<era>.glb with a per-nation
## team_prop material (vis_pass on, so material classes + light accents read; team colour never darkened).
## Purely cosmetic: does not touch Sim, army positions, scale, the selection ring/label or world_map.gd's picking
## (army_at_screen uses node position/scale only). Re-swaps when Sim.era changes. Missing glb -> legacy standard kept.
extends Node

const CHECK_EVERY := 0.25
var _meshes := {}      # era id -> Mesh (or null when the asset is missing)
var _mats := {}        # color html -> ShaderMaterial
var _t := 0.0

func _ready() -> void:
	name = "MapVisuals"

func _era_id() -> String:
	var e := clampi(Sim.era, 0, GameData.eras.size() - 1)
	return str(GameData.eras[e]["id"])

func _mesh(era: String) -> Mesh:
	if not _meshes.has(era):
		var m: Mesh = null
		var path := "res://assets/models/map_marker_%s.glb" % era
		if ResourceLoader.exists(path):
			var n: Node = load(path).instantiate()
			var stack := [n]
			while stack.size() > 0 and m == null:
				var x: Node = stack.pop_back()
				if x is MeshInstance3D:
					m = x.mesh
				stack.append_array(x.get_children())
			n.free()
		_meshes[era] = m
	return _meshes[era]

func _mat(col: Color) -> ShaderMaterial:
	var k := col.to_html()
	if not _mats.has(k):
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/team_prop.gdshader")
		m.set_shader_parameter("team_color", col)
		m.set_shader_parameter("vis_pass", 1.0)
		m.set_shader_parameter("brightness", 1.08)
		_mats[k] = m
	return _mats[k]

func _process(delta: float) -> void:
	_t -= delta
	if _t > 0.0:
		return
	_t = CHECK_EVERY
	var map = get_parent()
	if map == null or not ("army_nodes" in map):
		return
	var era := _era_id()
	var mesh := _mesh(era)
	if mesh == null:
		return
	for aid in map.army_nodes.keys():
		var n: Node3D = map.army_nodes[aid]
		if not is_instance_valid(n) or not Sim.armies.has(aid):
			continue
		var std: Node = n.get_node_or_null("Standard")
		if std == null or std.get_meta("vis_era", "") == era:
			continue
		var col: Color = Sim.nations[Sim.armies[aid]["owner"]]["color"]
		var mi: MeshInstance3D = null
		var stack := [std]
		while stack.size() > 0:
			var x: Node = stack.pop_back()
			if x is MeshInstance3D:
				if mi == null:
					mi = x
				else:
					x.visible = false   # army_standard is a single mesh; hide any extra parts if that ever changes
			stack.append_array(x.get_children())
		if mi == null:
			continue
		mi.mesh = mesh
		mi.material_override = _mat(col.lightened(0.15))   # same tint as world_map.gd's legacy standard
		std.set_meta("vis_era", era)
