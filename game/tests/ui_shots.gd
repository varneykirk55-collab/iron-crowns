extends Node
## UI screenshot tour of the real main scene (menu, campaign HUD, military, diplomacy, economy, inbox, deploy).
## xvfb-run -a godot --path game --resolution 1920x1080 res://tests/ui_shots.tscn -- --out=/abs/dir [--tag=name]
var out := "user://ui_shots"
var tag := ""

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="): out = a.substr(6)
		if a.begins_with("--tag="): tag = a.substr(6) + "_"
	DirAccess.make_dir_recursive_absolute(out)
	call_deferred("_run")

func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame

func shot(name: String) -> void:
	await _frames(4)
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out.path_join(tag + name + ".png"))
	print("UISHOT ", name)

func _press(n: Node, needle: String) -> bool:
	for c in n.get_children():
		if c is BaseButton and c.is_visible_in_tree() and ("text" in c) and needle in str(c.text) and not c.disabled:
			c.pressed.emit()
			return true
		if _press(c, needle):
			return true
	return false

func _run() -> void:
	GameData.load_all()
	Sim.auto_respond_player = ""
	var m: Node = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	await _frames(20)
	await shot("01_main_menu")
	if m.has_method("ui_tour_new_game"):
		await m.ui_tour_new_game(self)
	m._start_game("SWE", 1800, 11, 60)
	m.cam.fly_t = -1.0
	m.cam.look_at_world(GameData.node_world(Sim.nations["SWE"]["capital"]), 42.0, true)
	Sim.set_speed(0)
	Sim.advance_days(31)
	await _frames(10)
	await shot("03_campaign_province")
	var a: Dictionary = {}
	for x in Sim.armies.values():
		if x["owner"] == "SWE" and (a.is_empty() or Sim.army_men(x) > Sim.army_men(a)): a = x
	m.select_army(a["id"])
	await shot("04_army_panel")
	# foreign province with invade buttons
	var tp := -1; var bd := 1e18
	for pid in Sim.prov_owner.keys():
		if Sim.prov_owner[pid] != "SWE" and GameData.node_km(a["node"], pid) < bd and Sim.order_invade(a["id"], pid, true)["ok"]:
			bd = GameData.node_km(a["node"], pid); tp = pid
	m.select_province(tp)
	await shot("05_foreign_province")
	m.hud.confirm_invade(a["id"], tp)
	await shot("06_invade_confirm")
	m.hud.popup.visible = false
	m.hud._do_invade(a["id"], tp, false)
	m.select_army(a["id"])
	await shot("07_army_invading")
	# diplomacy, economy
	m.hud.open_diplomacy(Sim.prov_owner[tp])
	await shot("08_diplomacy")
	m.hud.diplo_win.visible = false
	m.hud.toggle_economy()
	await shot("09_economy")
	m.hud.econ_win.visible = false
	# inbox with offers + a warning
	var peers := 0
	for c in Sim.nations.keys():
		if peers < 4 and c != "SWE" and Sim.nations[c]["alive"] and not Sim.at_war(c, "SWE") and Sim.evaluate(c, "SWE", "trade")["score"] > -900.0:
			Sim.propose(c, "SWE", ["trade", "alliance", "nap", "trade"][peers], true); peers += 1
	Sim.propose(Sim.prov_owner[tp], "SWE", "peace", true)
	m.hud.refresh_top()
	m.hud.toggle_inbox()
	await shot("10_inbox")
	m.hud.inbox_win.visible = false
	# a player battle: deployment window
	Sim.auto_deploy = false
	Sim.ai_enabled = false
	var e := Sim._spawn_army(Sim.prov_owner[tp], a["node"], [])
	for k in 5: Sim.armies[e]["units"].append(Sim._make_unit(GameData.unit_for_role("c19", ["inf", "ranged"][k % 2])))
	var bid := Sim._start_battle(a["node"], [e], [a["id"]])
	await _frames(4)
	await shot("11_deploy")
	# reinforce controls: second army nearby
	var r := Sim._spawn_army("SWE", Sim.nations["SWE"]["capital"], [Sim._make_unit(GameData.unit_for_role("c19", "inf")), Sim._make_unit(GameData.unit_for_role("c19", "ranged"))])
	m.hud.deploy_win.visible = false
	m.select_army(r)
	await shot("12_reinforce_controls")
	# game menu
	m.hud.toggle_game_menu()
	await shot("13_game_menu")
	m.hud.menu_win.visible = false
	# warning toast
	m.hud._on_invasion_warning({"text": "Pickets and coastal observers report: Finland army of roughly 6,500 men on the march, heading for Northeastern Sweden — arrival in about 10 days.", "army": 0})
	await shot("14_warning")
	# watch the battle: live overlay, then the result card
	m._on_deploy_chosen(bid, {"objective": "assault", "formation": "line"}, true)
	for k in 60:
		await get_tree().create_timer(0.1).timeout
		if m.battle_view != null and m.in_battle and not m.transitioning: break
	if m.battle_view != null:
		await get_tree().create_timer(3.0).timeout
		await shot("15_battle")
		m.battle_view.skip()
		for k in 50:
			await get_tree().create_timer(0.1).timeout
			if m.battle_view.result_shown: break
		await get_tree().create_timer(0.5).timeout
		await shot("16_battle_result")
	get_tree().quit()
