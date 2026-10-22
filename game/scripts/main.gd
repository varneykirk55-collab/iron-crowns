## Game shell: main menu, campaign map + HUD, input, campaign<->battle transitions and scripted demo/recording modes.
extends Node

var env_node: WorldEnvironment
var map_env: Environment
var map_light: DirectionalLight3D
var map: WorldMap
var cam: MapCamera
var hud: Hud
var hud_layer: CanvasLayer
var menu_layer: CanvasLayer
var fade: ColorRect
var fade_layer: CanvasLayer
var battle_view: BattleView = null
var dbg_t := 0.0
var in_battle := false
var transitioning := false
var hover_t := 0.0
var args := {}
var demo := ""
var demo_t := 0.0
var demo_steps: Array = []
var demo_state := {}
var shot_dir := "res://../shots"
var _press_pos := Vector2.ZERO
var _cam_was_drag := false

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	shot_dir = args.get("shots", OS.get_executable_path().get_base_dir() if OS.has_feature("template") else ProjectSettings.globalize_path("res://").path_join("../shots"))
	DirAccess.make_dir_recursive_absolute(shot_dir)
	GameData.load_all()
	_build_env()
	map = WorldMap.new()
	add_child(map)
	map.build()
	cam = MapCamera.new()
	add_child(cam)
	map.camera = cam
	cam.make_current()
	_build_fade()
	Sim.battle_started.connect(_on_battle_started)
	Sim.era_changed.connect(func(_e): map.apply_era(); map.lut_dirty = true)
	Sim.ownership_changed.connect(func(_p, _o, _n): map.lut_dirty = true; map.labels_dirty = true)
	demo = args.get("demo", "")
	if demo != "":
		_start_demo(demo)
	else:
		_build_menu()

# ------------------------------------------------------------------ scene setup
func _build_env() -> void:
	map_env = Environment.new()
	map_env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sky_top_color = Color(0.16, 0.24, 0.38); sm.sky_horizon_color = Color(0.5, 0.56, 0.62)
	sm.ground_horizon_color = Color(0.5, 0.56, 0.62); sm.ground_bottom_color = Color(0.1, 0.14, 0.2)
	sky.sky_material = sm
	map_env.sky = sky
	map_env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	map_env.ambient_light_energy = 0.7
	map_env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	map_env.fog_enabled = true
	map_env.fog_light_color = Color(0.55, 0.6, 0.66)
	map_env.fog_density = 0.0006
	map_env.fog_sky_affect = 0.0
	map_env.glow_enabled = true
	map_env.glow_intensity = 0.3
	env_node = WorldEnvironment.new()
	env_node.environment = map_env
	add_child(env_node)
	map_light = DirectionalLight3D.new()
	map_light.rotation_degrees = Vector3(-50, -30, 0)
	map_light.light_energy = 1.15
	map_light.light_color = Color(1.0, 0.96, 0.88)
	add_child(map_light)

func _build_fade() -> void:
	fade_layer = CanvasLayer.new(); fade_layer.layer = 50
	add_child(fade_layer)
	fade = ColorRect.new(); fade.color = Color(0, 0, 0, 0)
	fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade_layer.add_child(fade)

func _build_menu() -> void:
	menu_layer = CanvasLayer.new(); menu_layer.layer = 20
	add_child(menu_layer)
	var root := Control.new(); root.set_anchors_preset(Control.PRESET_FULL_RECT); root.theme = Hud.make_theme()
	menu_layer.add_child(root)
	var shade := ColorRect.new(); shade.color = Color(0.03, 0.03, 0.04, 0.55); shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(shade)
	var pc := PanelContainer.new(); pc.set_anchors_preset(Control.PRESET_CENTER); pc.custom_minimum_size = Vector2(620, 0); pc.position = Vector2(-310, -230)
	root.add_child(pc)
	var v := VBoxContainer.new(); v.add_theme_constant_override("separation", 12); pc.add_child(v)
	var t := Label.new(); t.text = "IRON CROWNS"; t.add_theme_font_size_override("font_size", 46); t.add_theme_color_override("font_color", Hud.GOLD); t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t)
	var st := Label.new(); st.text = "Real-time grand strategy · vertical slice"; st.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER; st.add_theme_color_override("font_color", Hud.DIM)
	v.add_child(st)
	var yl := Label.new(); yl.text = "Start year"; v.add_child(yl)
	var years := OptionButton.new()
	for y in [1300, 1500, 1800, 1913, 1980]:
		var ei := GameData.era_for_year(y)
		years.add_item("%d — %s" % [y, GameData.eras[ei]["name"]], y)
	years.select(2)
	v.add_child(years)
	var nl := Label.new(); nl.text = "Choose your nation"; v.add_child(nl)
	var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 10); h.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_child(h)
	for code in GameData.playable:
		var c: String = code
		var b := Button.new(); b.custom_minimum_size = Vector2(180, 110)
		var bv := VBoxContainer.new(); bv.alignment = BoxContainer.ALIGNMENT_CENTER; bv.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bv.set_anchors_preset(Control.PRESET_FULL_RECT)
		var f = FlagRect.new(); f.custom_minimum_size = Vector2(72, 46); f.set_nation_static(c); f.size_flags_horizontal = Control.SIZE_SHRINK_CENTER; f.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bv.add_child(f)
		var l := Label.new(); l.text = GameData.country_name(c); l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER; l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bv.add_child(l)
		b.add_child(bv)
		b.pressed.connect(func(): _start_game(c, years.get_selected_id()))
		h.add_child(b)
	var saves := Sim.list_saves()
	if not saves.is_empty():
		var ll := Label.new(); ll.text = "Load a saved campaign"; v.add_child(ll)
		for m in saves.slice(0, 4):
			var slot: String = m["slot"]
			var lb := Button.new(); lb.text = "Load  %s — %s, %s (%s)" % [slot, m["nation"], m["date"], m["era"]]
			lb.pressed.connect(func(): load_slot(slot))
			v.add_child(lb)
	var help := Label.new()
	help.text = "Left-drag pan · wheel zoom · middle-drag or Q/E orbit · left-click select · right-click move army\nSpace pause · 1-5 speed · F1 diplomacy · F2 economy · Esc close windows"
	help.add_theme_font_size_override("font_size", 12); help.add_theme_color_override("font_color", Hud.DIM); help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(help)
	cam.look_at_world(Vector3(180 + 10, 0, 90 - 45), 200.0, true)
	cam.input_enabled = false

func _start_game(code: String, year: int, seed: int = 1, doy: int = 0) -> void:
	if menu_layer:
		menu_layer.queue_free(); menu_layer = null
	Sim.new_game(code, year, seed, doy)
	map.lut_dirty = true; map.labels_dirty = true
	map.apply_era()
	_ensure_hud()
	cam.input_enabled = true
	var cp := GameData.node_world(Sim.nations[code]["capital"])
	cam.look_at_world(cp, 160.0, true)
	cam.fly_to(cp, 42.0, 2.0)
	select_province(Sim.nations[code]["capital"])

func _ensure_hud() -> void:
	if hud_layer == null:
		hud_layer = CanvasLayer.new(); hud_layer.layer = 10
		add_child(hud_layer)
		hud = Hud.new(); hud.main = self
		hud_layer.add_child(hud)
		hud.deploy_chosen.connect(_on_deploy_chosen)
		hud.focus_world.connect(func(p): cam.fly_to(p, 24.0, 1.0))

# ------------------------------------------------------------------ save / load
func save_slot(slot: String = "quicksave") -> Dictionary:
	if menu_layer != null or not Sim.running:
		return {"ok": false, "msg": "No campaign to save"}
	var r := Sim.save_game(slot)
	if hud: hud.show_toast(r["msg"], 2.5)
	return r

func load_slot(slot: String = "quicksave") -> Dictionary:
	if in_battle or transitioning:
		var r0 := {"ok": false, "msg": "Leave the battle before loading"}
		if hud: hud.show_toast(r0["msg"], 2.5)
		return r0
	var r := Sim.load_game(slot)
	if not r["ok"]:
		if hud: hud.show_toast(r["msg"], 2.5)
		return r
	if menu_layer:
		menu_layer.queue_free(); menu_layer = null
	map.reset_markers()
	map.lut_dirty = true; map.labels_dirty = true
	map.apply_era()
	_ensure_hud()
	hud.on_game_loaded()
	cam.input_enabled = true
	var cp := GameData.node_world(Sim.nations[Sim.player]["capital"])
	cam.look_at_world(cp, 42.0, true)
	select_province(Sim.nations[Sim.player]["capital"])
	hud.show_toast(r["msg"], 2.5)
	for bid in Sim.battles.keys():
		if Sim.battles[bid]["awaiting"]:
			_on_battle_started(bid)
			break
	return r

# ------------------------------------------------------------------ selection / commands
func select_province(pid: int) -> void:
	map.selected_army = -1; map.path_army = -1
	map.set_selected_province(pid)
	if hud: hud.select_province(pid)

func select_army(aid: int) -> void:
	if not Sim.armies.has(aid):
		return
	map.selected_army = aid; map.path_army = aid
	map.set_selected_province(-1)
	if hud: hud.select_army(aid)

func _unhandled_input(ev: InputEvent) -> void:
	if in_battle or transitioning or menu_layer != null or hud == null:
		return
	if ev is InputEventKey and ev.pressed and not ev.echo:
		match ev.keycode:
			KEY_SPACE: Sim.set_speed(0 if Sim.speed_idx > 0 else 2)
			KEY_1, KEY_2, KEY_3, KEY_4, KEY_5: Sim.set_speed(ev.keycode - KEY_0)
			KEY_F1: hud.toggle_diplomacy()
			KEY_F2: hud.toggle_economy()
			KEY_F5: save_slot("quicksave")
			KEY_F9: load_slot("quicksave")
			KEY_ESCAPE:
				if hud.any_window_open():
					hud.diplo_win.visible = false; hud.econ_win.visible = false; hud.menu_win.visible = false
				else:
					hud.toggle_game_menu()
	if ev is InputEventMouseButton and ev.pressed:
		_press_pos = ev.position
	var consumed = cam.handle_input(ev)
	if ev is InputEventMouseButton and not ev.pressed and not consumed and _press_pos.distance_to(ev.position) < 6.0:
		if ev.button_index == MOUSE_BUTTON_LEFT:
			var aid := map.army_at_screen(ev.position)
			if aid >= 0:
				select_army(aid)
			else:
				var pid := map.province_at_screen(ev.position)
				if pid > 0:
					select_province(pid)
		elif ev.button_index == MOUSE_BUTTON_RIGHT and map.selected_army >= 0 and Sim.armies.has(map.selected_army):
			var a: Dictionary = Sim.armies[map.selected_army]
			if a["owner"] == Sim.player:
				var pid2 := map.province_at_screen(ev.position)
				if pid2 > 0:
					var r := Sim.order_move(map.selected_army, pid2)
					hud.show_toast(("Marching to %s (~%d days)" % [GameData.provinces[pid2]["name"], int(r.get("days", 0))]) if r["ok"] else r["msg"], 2.5)
					hud.select_army(map.selected_army)

func _process(delta: float) -> void:
	map.cam_dist = cam.dist
	if demo != "":
		_demo_tick(delta)
		dbg_t += delta
		if dbg_t > 3.0:
			dbg_t = 0.0
			print("DBG t=%.1f fps=%d battle_t=%s day=%s" % [demo_t, Engine.get_frames_per_second(), str(battle_view.sim.t) if battle_view != null else "-", str(Sim.day)] + ((" cam=%s ct=%s auto=%s shot=%d hs=%s" % [battle_view.cam.global_position, battle_view._ct, battle_view.cam_auto, battle_view.shot_i, battle_view._hot_spot()] + " mms=" + str(battle_view.mms.keys().map(func(k): return "%s:%d/%d" % [k, battle_view.mms[k]["n"], battle_view.mms[k]["cap"]]))) if battle_view != null and battle_view.visible and battle_view.sim != null else ""))
	if in_battle or menu_layer != null:
		return
	hover_t -= delta
	if hover_t <= 0.0 and hud != null:
		hover_t = 0.1
		var mp := get_viewport().get_mouse_position()
		var pid := map.province_at_screen(mp)
		map.set_hover_country(Sim.prov_owner.get(pid, "") if pid > 0 else "")

# ------------------------------------------------------------------ battles
func _on_battle_started(bid: int) -> void:
	var b: Dictionary = Sim.battles[bid]
	if b["player_side"] >= 0 and b["awaiting"] and hud != null:
		if not in_battle:
			cam.fly_to(GameData.node_world(b["prov"]), 20.0, 1.2)
		hud.show_deploy(bid)

func _on_deploy_chosen(bid: int, orders: Dictionary, watch: bool) -> void:
	Sim.deploy_battle(bid, orders, watch)
	if watch:
		watch_battle(bid)

func watch_battle(bid: int) -> void:
	if in_battle or transitioning or not Sim.battles.has(bid) or Sim.battles[bid]["done"] or Sim.battles[bid]["sim"] == null:
		return
	Sim.set_watched(bid, true)
	transitioning = true
	var p := GameData.node_world(Sim.battles[bid]["prov"])
	cam.fly_to(p, cam.min_dist, 1.3)
	var tw := create_tween()
	tw.tween_interval(0.9)
	tw.tween_property(fade, "color:a", 1.0, 0.5)
	tw.tween_callback(func(): _enter_battle(bid))
	tw.tween_property(fade, "color:a", 0.0, 0.7)
	tw.tween_callback(func(): transitioning = false)

func _enter_battle(bid: int) -> void:
	battle_view = BattleView.new()
	add_child(battle_view)
	battle_view.setup(bid)
	battle_view.leave_requested.connect(_leave_battle)
	env_node.environment = battle_view.environment
	map.visible = false; map_light.visible = false
	if hud_layer: hud_layer.visible = false
	battle_view.activate()
	in_battle = true

func _leave_battle(bid: int) -> void:
	if transitioning:
		return
	transitioning = true
	var tw := create_tween()
	tw.tween_property(fade, "color:a", 1.0, 0.45)
	tw.tween_callback(func(): _exit_battle(bid))
	tw.tween_property(fade, "color:a", 0.0, 0.6)
	tw.tween_callback(func(): transitioning = false)

func _exit_battle(bid: int) -> void:
	Sim.set_watched(bid, false)
	if battle_view:
		battle_view.queue_free(); battle_view = null
	env_node.environment = map_env
	map.visible = true; map_light.visible = true
	if hud_layer: hud_layer.visible = true
	cam.make_current()
	in_battle = false
	map.lut_dirty = true
	if Sim.battles.has(bid):
		var p := GameData.node_world(Sim.battles[bid]["prov"])
		cam.look_at_world(p, 10.0, true)
		cam.fly_to(p, 36.0, 1.5)

# ------------------------------------------------------------------ demo / recording modes
func shot(name: String) -> void:
	var img := get_viewport().get_texture().get_image()
	var path := shot_dir.path_join(name + ".png")
	img.save_png(path)
	print("SHOT ", path)

func _start_demo(kind: String) -> void:
	var code: String = args.get("nation", "USA")
	var year := int(args.get("year", "1800"))
	Sim.auto_respond_player = "decline"
	match kind:
		"menu":
			_build_menu()
			demo_steps = [[1.5, func(): shot("menu")], [2.0, func(): get_tree().quit()]]
		"campaign":
			_start_game(code, year, 7)
			Sim.set_speed(0)
			var cap: int = Sim.nations[code]["capital"]
			var cp := GameData.node_world(cap)
			demo_steps = [
				[0.1, func(): cam.fly_t = -1.0; cam.look_at_world(cp + Vector3(10, 0, 8), 190.0, true)],
				[2.0, func(): shot("campaign_%s_world" % code)],
				[2.2, func(): cam.fly_to(cp, 45.0, 2.5)],
				[5.5, func(): shot("campaign_%s_region" % code); Sim.set_speed(3)],
				[6.0, func(): cam.fly_to(cp, 14.0, 2.0, cam.yaw + 0.5)],
				[9.0, func(): _demo_select_main_army(code); shot("campaign_%s_close" % code)],
				[9.5, func(): _demo_march(code)],
				[12.0, func(): shot("campaign_%s_march" % code)],
				[12.5, func(): cam.fly_to(cp, 70.0, 3.0, cam.yaw - 0.8)],
				[16.5, func(): shot("campaign_%s_ai" % code)],
				[17.0, func(): get_tree().quit()]]
		"diplomacy":
			_start_game(code, year, 7)
			Sim.advance_days(45)
			Sim.set_speed(0)
			var cp2 := GameData.node_world(Sim.nations[code]["capital"])
			demo_steps = [
				[0.1, func(): cam.fly_t = -1.0; cam.look_at_world(cp2, 55.0, true)],
				[1.0, func(): hud.open_diplomacy(_demo_target(code))],
				[2.5, func(): shot("diplomacy_%s" % code)],
				[3.0, func(): hud._propose("trade")],
				[4.0, func(): shot("diplomacy_%s_proposal" % code)],
				[4.5, func(): hud.diplo_win.visible = false; hud.popup.visible = false; hud.toggle_economy()],
				[6.0, func(): shot("economy_%s" % code)],
				[7.0, func(): hud._buy(GameData.units_by_era[GameData.eras[Sim.era]["id"]][0], Sim.nations[code]["capital"]); hud.refresh_econ()],
				[8.0, func(): shot("economy_%s_bought" % code)],
				[8.5, func(): hud.econ_win.visible = false; Sim.set_speed(3)],
				[11.5, func(): shot("diplomacy_%s_running" % code)],
				[12.0, func(): get_tree().quit()]]
		"era":
			_start_game(code, 1913, 3, 345)
			Sim.set_speed(2)
			var cp3 := GameData.node_world(Sim.nations[code]["capital"])
			demo_state["era0"] = Sim.era
			demo_steps = [
				[0.1, func(): cam.fly_t = -1.0; cam.look_at_world(cp3 + Vector3(-9, 0, 2), 40.0, true)],
				[1.5, func(): shot("era_before_%s" % code); Sim.set_speed(4)],
				[-1.0, func(): return Sim.era != demo_state["era0"]],
				[0.8, func(): shot("era_change_popup_%s" % code)],
				[2.5, func(): hud.popup.visible = false; Sim.set_speed(1)],
				[1.0, func(): shot("era_after_%s" % code)],
				[0.5, func(): hud.toggle_economy()],
				[1.5, func(): shot("era_procurement_%s" % code)],
				[0.5, func(): get_tree().quit()]]
			for i in range(3, demo_steps.size()):
				demo_steps[i][0] = -demo_steps[i][0] - 100.0   # relative-delay markers after the wait
		"saveload":
			_start_game(code, year, 5)
			Sim.advance_days(30)
			Sim.set_speed(0)
			var cp4 := GameData.node_world(Sim.nations[code]["capital"])
			demo_steps = [
				[0.1, func(): cam.fly_t = -1.0; cam.look_at_world(cp4, 55.0, true)],
				[1.0, func(): demo_state["saved_date"] = Sim.date_string(); _demo_key(KEY_F5)],
				[1.6, func(): shot("saveload_%s_quicksave" % code)],
				[2.0, func(): Sim.advance_days(90); demo_state["later_date"] = Sim.date_string()],
				[2.5, func(): _demo_key(KEY_ESCAPE)],
				[3.5, func(): shot("saveload_%s_menu" % code)],
				[4.0, func(): _demo_key(KEY_F9)],
				[5.0, func(): shot("saveload_%s_loaded" % code); print("SAVELOAD saved=%s later=%s after_load=%s ok=%s" % [demo_state["saved_date"], demo_state["later_date"], Sim.date_string(), str(Sim.date_string() == demo_state["saved_date"])])],
				[5.5, func(): get_tree().quit()]]
		"battle":
			_start_game(code, year, int(args.get("seed", "7")))
			Sim.set_speed(0)
			demo_state["code"] = code
			var tgt := _demo_war(code)
			demo_state["tgt"] = tgt
			demo_steps = [
				[0.2, func(): cam.fly_t = -1.0; cam.look_at_world(GameData.node_world(Sim.nations[code]["capital"]), 40.0, true)],
				[1.5, func(): Sim.set_speed(4)],
				[-1.0, func(): return hud.deploy_win.visible],
				[-101.5, func(): Sim.set_speed(0); shot("battle_deploy_%s" % code)],
				[-102.5, func(): _demo_deploy(); Sim.set_speed(2)],
				[-1.0, func(): return in_battle and not transitioning],
				[-102.0, func(): shot("battle_%s_deploy_view" % code)],
				[-100.01, func(): if args.has("closeup"): battle_view.snap_cam(0, 30.0, -0.25, 0.4)],
				[-100.3, func(): if args.has("closeup"): shot("battle_%s_close0" % code)],
				[-100.01, func(): if args.has("closeup"): battle_view.snap_cam(battle_view.first_reg(1), 30.0, -0.25, 2.8)],
				[-100.3, func(): if args.has("closeup"): shot("battle_%s_close1" % code)],
				[-100.01, func(): if args.has("closeup"): battle_view.snap_cam(-1, 230.0, -0.85, 0.0)],
				[-100.3, func(): if args.has("closeup"): shot("battle_%s_top" % code); battle_view.cam_auto = true],
				[-1.0, func(): return in_battle and battle_view != null and (battle_view.sim.t > 12.0 or battle_view.finished)],
				[-100.01, func(): shot("battle_%s_engage" % code)],
				[-1.0, func(): return in_battle and battle_view != null and (battle_view.sim.t > 22.0 or battle_view.finished)],
				[-100.01, func(): shot("battle_%s_melee" % code)],
				[-1.0, func(): return battle_view != null and battle_view.result_shown],
				[-100.6, func(): shot("battle_%s_result" % code)],
				[-104.0, func(): battle_view.leave_requested.emit(battle_view.bid)],
				[-1.0, func(): return not in_battle and not transitioning],
				[-102.5, func(): shot("battle_%s_after_map" % code)],
				[-100.3, func(): get_tree().quit()]]
	demo_state["i"] = 0
	demo_state["t0"] = 0.0

func _demo_tick(delta: float) -> void:
	demo_t += delta
	var i: int = demo_state.get("i", 0)
	if i >= demo_steps.size():
		return
	var st: Array = demo_steps[i]
	var at: float = st[0]
	var fire := false
	if at == -1.0:
		if st[1].call():
			demo_state["i"] = i + 1; demo_state["t0"] = demo_t
		elif demo_t > float(args.get("timeout", "240")):
			print("DEMO TIMEOUT at step ", i); get_tree().quit(3)
		return
	elif at <= -100.0:
		fire = demo_t - demo_state["t0"] >= (-at - 100.0)
	else:
		fire = demo_t >= at
	if fire:
		st[1].call()
		demo_state["i"] = i + 1
		demo_state["t0"] = demo_t

func _demo_key(k: Key) -> void:
	for pressed in [true, false]:
		var e := InputEventKey.new(); e.keycode = k; e.physical_keycode = k; e.pressed = pressed
		Input.parse_input_event(e)

func _demo_target(code: String) -> String:
	var best := ""; var bs := 1e18
	for o in Sim.neighbors_of(code):
		if Sim.nations[o]["alive"]:
			var s := Sim.strength(o) + (0.0 if Sim._shares_border(code, o) else 1e7)
			if s < bs:
				bs = s; best = o
	return best

func _demo_main_army(code: String) -> Dictionary:
	var best := {}
	for a in Sim.armies.values():
		if a["owner"] == code and (best.is_empty() or Sim.army_men(a) > Sim.army_men(best)):
			best = a
	return best

func _demo_select_main_army(code: String) -> void:
	var a := _demo_main_army(code)
	if not a.is_empty():
		select_army(a["id"])

func _demo_march(code: String) -> void:
	var a := _demo_main_army(code)
	if a.is_empty():
		return
	var best := -1; var bd := 1e18
	for n in Sim.neighbors_of(code):
		for pid in Sim.nation_provs[n]:
			var d := GameData.node_km(a["node"], pid)
			if d < bd and d > 1.0:
				bd = d; best = pid
	# march to the nearest own border province instead of an illegal move
	var own := -1; var od := 0.0
	for pid in Sim.nation_provs[code]:
		var d2 := GameData.node_km(a["node"], pid)
		if d2 > od and d2 < 1500.0:
			od = d2; own = pid
	if own >= 0:
		Sim.order_move(a["id"], own)
		select_army(a["id"])

func _demo_war(code: String) -> String:
	var cap: int = Sim.nations[code]["capital"]
	for uid in GameData.units_by_era[GameData.eras[Sim.era]["id"]]:
		Sim.buy_unit(code, uid, cap)
	var tgt := _demo_target(code)
	if tgt == "":
		return ""
	Sim.declare_war(code, tgt)
	var strike := {}
	for a in Sim.armies_in(cap):
		if a["owner"] == code and (strike.is_empty() or a["units"].size() > strike["units"].size()):
			strike = a
	for a in Sim.armies_in(cap):
		if a["owner"] == code and a["id"] != strike["id"]:
			Sim.merge_armies(strike["id"], a["id"])
	if not strike.is_empty():
		Sim.order_move(strike["id"], Sim.nations[tgt]["capital"])
		select_army(strike["id"])
		if args.has("reinforce"):
			print("DEMO path ", Sim.armies[strike["id"]]["path"])
			# demo scenario: give the defender a field army at the first province on the invasion path
			var a: Dictionary = Sim.armies[strike["id"]]
			for pid in a["path"]:
				if Sim.prov_owner.get(int(pid), "") == tgt:
					var tn: Dictionary = Sim.nations[tgt]
					tn["funds"] += 50000.0; tn["manpower"] += 50000.0
					for k in int(args.get("reinforce", "1")):
						for uid in GameData.units_by_era[GameData.eras[Sim.era]["id"]]:
							var res: Dictionary = Sim.buy_unit(tgt, uid, int(pid))
							if not res["ok"]:
								print("DEMO reinforce failed: ", uid, " ", res["msg"])
					# demo staging: place the new defender army on the first province of the invasion route
					var stage: int = int(a["path"][0])
					for a2 in Sim.armies_in(int(pid)):
						if a2["owner"] == tgt and a2["state"] == "idle":
							a2["node"] = stage
					print("DEMO reinforced ", tgt, " at ", pid, " staged at ", stage)
					break
	return tgt

func _demo_deploy() -> void:
	var bid: int = hud.deploy_bid
	var b: Dictionary = Sim.battles[bid]
	var o: Dictionary = b["orders"][b["player_side"]].duplicate()
	o["objective"] = args.get("objective", o.get("objective", "assault"))
	o["formation"] = args.get("formation", o.get("formation", "line"))
	hud.deploy_win.visible = false
	_on_deploy_chosen(bid, o, true)
