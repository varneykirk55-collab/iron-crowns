extends Node
func _ready() -> void:
	for f in ["res://assets/models/soldier_c19_line_lod0.glb", "res://assets/models/cavalry_med_knight_lod0.glb", "res://assets/models/tank_c20.glb", "res://assets/models/army_standard.glb", "res://assets/models/art_cannon.glb", "res://assets/models/city_2.glb", "res://assets/models/battle_marker.glb", "res://assets/models/ship_sail.glb", "res://assets/models/tree_conifer.glb"]:
		var sc: Node = load(f).instantiate()
		var stack := [sc]
		while stack.size() > 0:
			var n: Node = stack.pop_back()
			stack.append_array(n.get_children())
			if n is MeshInstance3D:
				var arr: Array = n.mesh.surface_get_arrays(0)
				var uv2 = arr[Mesh.ARRAY_TEX_UV2]
				var hist := {}
				if uv2 != null:
					for u in uv2:
						var k := "%.2f" % u.y
						hist[k] = hist.get(k, 0) + 1
				print(f.get_file(), " aabb=", n.mesh.get_aabb(), " team hist=", hist)
	get_tree().quit()
