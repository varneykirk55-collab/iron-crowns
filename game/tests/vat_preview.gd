extends Node3D
# Debug render: soldier models with the VAT shader (lod0, lod1) next to a plain vertex-colour material.
func _ready() -> void:
	var models := ["c19_line", "c20_rifle", "c19_hussar"]
	var x := -6.0
	for m in models:
		var prefix := "cavalry_" if m in ["med_knight", "em_cuirassier", "c19_hussar"] else "soldier_"
		for lod in 2:
			var sc: PackedScene = load("res://assets/models/%s%s_lod%d.glb" % [prefix, m, lod])
			var n := sc.instantiate()
			var mesh: Mesh = null
			var st := [n]
			while st.size() > 0:
				var q: Node = st.pop_back()
				if q is MeshInstance3D: mesh = q.mesh
				st.append_array(q.get_children())
			var j: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/vat/%s_lod%d.json" % [m, lod]))
			var img := Image.create_from_data(int(j["vertices"]), int(j["frames"]), false, Image.FORMAT_RGBF, FileAccess.get_file_as_bytes("res://assets/vat/%s_lod%d.vat" % [m, lod]))
			var mat := ShaderMaterial.new(); mat.shader = load("res://shaders/vat.gdshader")
			mat.set_shader_parameter("vat_tex", ImageTexture.create_from_image(img))
			mat.set_shader_parameter("vat_verts", int(j["vertices"]))
			mat.set_shader_parameter("team_color", Color("#3d5a9e"))
			var mm := MultiMesh.new(); mm.transform_format = MultiMesh.TRANSFORM_3D; mm.use_custom_data = true; mm.use_colors = "--colors" in OS.get_cmdline_user_args(); mm.mesh = mesh; mm.instance_count = 1
			if mm.use_colors: mm.set_instance_color(0, Color.WHITE)
			mm.set_instance_transform(0, Transform3D(Basis(), Vector3(x, 0, 0)))
			var c: Dictionary = j["clips"]["idle"] if j["clips"].has("idle") else j["clips"].values()[0]
			if "--die" in OS.get_cmdline_user_args() and j["clips"].has("die"): c = j["clips"]["die"]
			mm.set_instance_custom_data(0, Color(float(c["start"]), float(c["count"]) * (1.0 if c["loop"] else -1.0), -100.0, 1.0))
			var mmi := MultiMeshInstance3D.new(); mmi.multimesh = mm; mmi.material_override = mat
			add_child(mmi)
			var plain := MeshInstance3D.new(); plain.mesh = mesh
			var sm := StandardMaterial3D.new(); sm.vertex_color_use_as_albedo = true
			plain.material_override = sm; plain.position = Vector3(x, 0, 3)
			add_child(plain)
			print(m, " lod", lod, " verts=", j["vertices"], " surf_fmt=", mesh.surface_get_format(0), " clips=", j["clips"].keys())
			x += 2.2
	var cam := Camera3D.new(); add_child(cam); cam.position = Vector3(0, 2.5, 11); cam.look_at(Vector3(0, 1, 1.5)); cam.make_current()
	var l := DirectionalLight3D.new(); l.rotation_degrees = Vector3(-40, 30, 0); add_child(l)
	var we := WorldEnvironment.new(); var e := Environment.new(); e.background_mode = Environment.BG_COLOR; e.background_color = Color(0.5, 0.6, 0.7); e.ambient_light_color = Color(0.6, 0.6, 0.6); e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; we.environment = e; add_child(we)
	if "--battle-env" in OS.get_cmdline_user_args():
		var sky := Sky.new(); var sm := ProceduralSkyMaterial.new(); sky.sky_material = sm; e.sky = sky
		e.background_mode = Environment.BG_SKY; e.ambient_light_source = Environment.AMBIENT_SOURCE_SKY; e.ambient_light_energy = 0.75
		e.tonemap_mode = Environment.TONE_MAPPER_FILMIC; e.glow_enabled = true; e.fog_enabled = true; e.fog_density = 0.0006
		l.rotation_degrees = Vector3(-38, 35, 0); l.light_energy = 1.25; l.shadow_enabled = true
		l.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL; l.directional_shadow_max_distance = 260.0
	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().process_frame
	get_viewport().get_texture().get_image().save_png("res://../shots/debug_vat.png")
	get_tree().quit()
