extends Node
## Scripted UI walkthrough for a short demo video (real scene, real clicks; a drawn cursor shows where).
## tools: godot --path game --resolution 1600x900 --fixed-fps 30 --write-movie out.avi res://tests/ui_demo.tscn
var m: Node
var cur: Control
var cpos := Vector2(800, 450)

class Cursor extends Control:
	var down := false
	func _draw() -> void:
		var pts := PackedVector2Array([Vector2(0, 0), Vector2(0, 22), Vector2(6, 17), Vector2(10, 26), Vector2(14, 24), Vector2(10, 16), Vector2(17, 16)])
		draw_colored_polygon(pts, Color(0.95, 0.93, 0.88) if not down else Color(0.85, 0.7, 0.42))
		draw_polyline(pts + PackedVector2Array([Vector2(0, 0)]), Color(0, 0, 0, 0.9), 1.5)

func _ready() -> void:
	call_deferred("_run")

func _wait(s: float) -> void:
	await get_tree().create_timer(s).timeout

func _move(to: Vector2, dur: float = 0.6) -> void:
	var tw := create_tween()
	tw.tween_property(self, "cpos", to, dur).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	while tw.is_running():
		cur.position = cpos
		await get_tree().process_frame
	cur.position = cpos

func _click_at(p: Vector2) -> void:
	await _move(p)
	cur.down = true; cur.queue_redraw()
	var wpos: Vector2 = get_tree().root.get_final_transform() * p
	for pressed in [true, false]:
		var e := InputEventMouseButton.new(); e.button_index = MOUSE_BUTTON_LEFT; e.pressed = pressed; e.position = wpos; e.global_position = wpos
		Input.parse_input_event(e)
		await get_tree().process_frame
		await get_tree().process_frame
	cur.down = false; cur.queue_redraw()

func _click(c: Control) -> void:
	if c != null:
		await _click_at(c.get_global_rect().get_center())

func _btn(n: Node, needle: String) -> Button:
	for c in n.get_children():
		if c is Button and c.is_visible_in_tree():
			if needle in c.text: return c
			for l in c.find_children("*", "Label", true, false):
				if l.text == needle: return c
		var r := _btn(c, needle)
		if r: return r
	return null

func _run() -> void:
	GameData.load_all()
	Sim.auto_respond_player = ""
	m = load("res://scenes/main.tscn").instantiate()
	add_child(m)
	var cl := CanvasLayer.new(); cl.layer = 100; add_child(cl)
	cur = Cursor.new(); cur.mouse_filter = Control.MOUSE_FILTER_IGNORE; cl.add_child(cur)
	cur.position = cpos
	await _wait(4.0)
	var ts: TitleScreen = m.menu_layer.get_child(0)
	await _click(ts.nav_btns["New Campaign"]); await _wait(1.8)
	for y in ["1300", "1914", "1980", "1800"]:
		await _click(_btn(ts.page_body, y)); await _wait(1.1)
	await _click(_btn(ts.page_body, "Japan")); await _wait(1.0)
	await _click(_btn(ts.page_body, "Sweden")); await _wait(1.2)
	await _click(_btn(ts.page_body, "Start Campaign")); await _wait(3.0)
	var h: Hud = m.hud
	Sim.set_speed(0)
	var a: Dictionary = {}
	for x in Sim.armies.values():
		if x["owner"] == "SWE" and (a.is_empty() or Sim.army_men(x) > Sim.army_men(a)): a = x
	await _move(m.map.camera.unproject_position(GameData.node_world(a["node"])))
	m.select_army(a["id"]); await _wait(2.5)
	var tp := -1; var bd := 1e18
	for pid in Sim.prov_owner.keys():
		if Sim.prov_owner[pid] != "SWE" and GameData.node_km(a["node"], pid) < bd and Sim.order_invade(a["id"], pid, true)["ok"]:
			bd = GameData.node_km(a["node"], pid); tp = pid
	await _move(m.map.camera.unproject_position(GameData.node_world(tp)))
	m.select_province(tp); await _wait(2.0)
	await _click(_btn(h.sel_box, "Invade with")); await _wait(3.0)
	await _click(_btn(h.popup_box, "Invade (undeclared)")); await _wait(1.0)
	await _click(h.speed_btns[3]); await _wait(4.0)
	await _click(h.speed_btns[0]); await _wait(0.8)
	await _click(_btn(h.dock, "Diplomacy")); await _wait(3.0)
	await _click_at(Vector2(60, 860)); await _wait(0.6)
	await _click(_btn(h.dock, "Economy")); await _wait(3.0)
	await _click_at(Vector2(60, 860)); await _wait(0.6)
	var peers := 0
	for c in Sim.nations.keys():
		if peers < 4 and c != "SWE" and Sim.nations[c]["alive"] and not Sim.at_war(c, "SWE") and Sim.evaluate(c, "SWE", "trade")["score"] > -900.0:
			Sim.propose(c, "SWE", ["trade", "alliance", "nap", "trade"][peers], true); peers += 1
	h.refresh_top(); await _wait(1.2)
	await _click(h.inbox_btn); await _wait(3.0)
	await _click(_btn(h.inbox_box, "Accept all")); await _wait(1.5)
	await _click_at(Vector2(60, 860)); await _wait(0.6)
	h._on_invasion_warning({"text": "Pickets and coastal observers report: an enemy army of roughly 6,500 men is on the march, heading for Northeastern Sweden — arrival in about 10 days.", "army": 0})
	await _wait(3.5)
	await _click(_btn(h.dock, "Menu")); await _wait(2.5)
	get_tree().quit()
