## Campaign HUD: top bar, selection panel, event log, diplomacy, economy & procurement, deployment, era & offer popups.
class_name Hud
extends Control

signal deploy_chosen(bid: int, orders: Dictionary, watch: bool)
signal focus_world(pos: Vector3)

const GOLD := Color(0.86, 0.72, 0.42)
const PARCH := Color(0.93, 0.88, 0.76)
const DIM := Color(0.68, 0.64, 0.56)
const GOOD := Color(0.55, 0.85, 0.45)
const BAD := Color(0.95, 0.42, 0.35)

var main: Node
var top_bar: PanelContainer
var lbl_nation: Label
var flag: FlagRect
var lbl_funds: Label
var lbl_manpower: Label
var lbl_stab: Label
var lbl_exh: Label
var lbl_era: Label
var lbl_date: Label
var speed_btns: Array = []
var sel_panel: PanelContainer
var sel_box: VBoxContainer
var log_panel: PanelContainer
var log_text: RichTextLabel
var diplo_win: PanelContainer
var diplo_list: VBoxContainer
var diplo_detail: VBoxContainer
var diplo_target := ""
var econ_win: PanelContainer
var econ_box: VBoxContainer
var deploy_win: PanelContainer
var deploy_box: VBoxContainer
var deploy_bid := -1
var deploy_orders := {"objective": "assault", "formation": "line"}
var popup: PanelContainer
var popup_box: VBoxContainer
var toast: Label
var toast_t := 0.0
var hint: Label
var sel_pid := -1
var sel_army := -1
var _refresh_t := 0.0
var theme_res: Theme

func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	theme_res = make_theme()
	theme = theme_res
	_build_top_bar()
	_build_sel_panel()
	_build_log()
	_build_diplo()
	_build_econ()
	_build_deploy()
	_build_popup()
	_build_game_menu()
	toast = Label.new()
	toast.add_theme_font_size_override("font_size", 22)
	toast.add_theme_color_override("font_color", PARCH)
	toast.add_theme_color_override("font_outline_color", Color.BLACK)
	toast.add_theme_constant_override("outline_size", 6)
	toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	toast.size = Vector2(800, 40)
	toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(toast)
	hint = Label.new()
	hint.text = "LMB select · drag to pan · wheel zoom · MMB/Q/E orbit · RMB move army · Space pause · 1-5 speed · F1 diplomacy · F2 economy"
	hint.add_theme_font_size_override("font_size", 13)
	hint.add_theme_color_override("font_color", Color(0.9, 0.86, 0.75, 0.75))
	hint.add_theme_color_override("font_outline_color", Color.BLACK)
	hint.add_theme_constant_override("outline_size", 4)
	hint.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	hint.position = Vector2(12, -24)
	hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(hint)
	Sim.event_logged.connect(_on_event)
	Sim.era_changed.connect(_on_era)
	Sim.player_offer.connect(_on_offer)
	Sim.speed_changed.connect(func(_i): _refresh_speed())
	Sim.battle_resolved.connect(_on_battle_resolved)

static func make_theme() -> Theme:
	var t := Theme.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.11, 0.09, 0.07, 0.92)
	sb.border_color = Color(0.62, 0.5, 0.3)
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(3)
	sb.content_margin_left = 10; sb.content_margin_right = 10; sb.content_margin_top = 8; sb.content_margin_bottom = 8
	sb.shadow_color = Color(0, 0, 0, 0.5); sb.shadow_size = 6
	t.set_stylebox("panel", "PanelContainer", sb)
	var bn := StyleBoxFlat.new()
	bn.bg_color = Color(0.25, 0.19, 0.12)
	bn.border_color = Color(0.7, 0.56, 0.32)
	bn.set_border_width_all(1)
	bn.set_corner_radius_all(2)
	bn.content_margin_left = 8; bn.content_margin_right = 8; bn.content_margin_top = 3; bn.content_margin_bottom = 3
	var bh := bn.duplicate(); bh.bg_color = Color(0.38, 0.28, 0.15)
	var bp := bn.duplicate(); bp.bg_color = Color(0.5, 0.36, 0.16)
	var bd := bn.duplicate(); bd.bg_color = Color(0.16, 0.14, 0.12); bd.border_color = Color(0.35, 0.3, 0.25)
	t.set_stylebox("normal", "Button", bn)
	t.set_stylebox("hover", "Button", bh)
	t.set_stylebox("pressed", "Button", bp)
	t.set_stylebox("disabled", "Button", bd)
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	t.set_color("font_color", "Button", PARCH)
	t.set_color("font_disabled_color", "Button", Color(0.5, 0.47, 0.42))
	t.set_color("font_hover_color", "Button", Color(1, 0.95, 0.8))
	t.set_color("font_pressed_color", "Button", Color(1, 0.9, 0.6))
	t.set_color("font_color", "Label", PARCH)
	t.set_font_size("font_size", "Label", 15)
	t.set_font_size("font_size", "Button", 15)
	t.set_color("default_color", "RichTextLabel", PARCH)
	t.set_font_size("normal_font_size", "RichTextLabel", 14)
	t.set_font_size("bold_font_size", "RichTextLabel", 14)
	var sep := StyleBoxLine.new(); sep.color = Color(0.55, 0.45, 0.28, 0.7); sep.thickness = 1
	t.set_stylebox("separator", "HSeparator", sep)
	var pbg := StyleBoxFlat.new(); pbg.bg_color = Color(0.05, 0.05, 0.05); pbg.set_corner_radius_all(2)
	var pfg := StyleBoxFlat.new(); pfg.bg_color = GOLD; pfg.set_corner_radius_all(2)
	t.set_stylebox("background", "ProgressBar", pbg)
	t.set_stylebox("fill", "ProgressBar", pfg)
	t.set_font_size("font_size", "ProgressBar", 11)
	var sl := StyleBoxFlat.new(); sl.bg_color = Color(0.05, 0.05, 0.05); sl.content_margin_top = 3; sl.content_margin_bottom = 3
	t.set_stylebox("slider", "HSlider", sl)
	var scb := StyleBoxFlat.new(); scb.bg_color = Color(0.2, 0.16, 0.1)
	t.set_stylebox("scroll", "VScrollBar", scb)
	var scg := StyleBoxFlat.new(); scg.bg_color = Color(0.55, 0.45, 0.28)
	t.set_stylebox("grabber", "VScrollBar", scg)
	return t

# ------------------------------------------------------------------ helpers
func L(text: String, size: int = 15, col: Color = PARCH) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", col)
	return l

func B(text: String, cb: Callable, disabled: bool = false, tip: String = "") -> Button:
	var b := Button.new()
	b.text = text
	b.disabled = disabled
	b.tooltip_text = tip
	b.pressed.connect(cb)
	return b

func title(text: String) -> Label:
	var l := L(text, 20, GOLD)
	return l

func bar(v: float, col: Color, w: float = 140.0) -> ProgressBar:
	var p := ProgressBar.new()
	p.min_value = 0; p.max_value = 1; p.value = v
	p.custom_minimum_size = Vector2(w, 12)
	p.show_percentage = false
	var f := StyleBoxFlat.new(); f.bg_color = col; f.set_corner_radius_all(2)
	p.add_theme_stylebox_override("fill", f)
	return p

func clear(c: Node) -> void:
	for ch in c.get_children():
		c.remove_child(ch)
		ch.queue_free()

func row(items: Array) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 8)
	for it in items:
		h.add_child(it)
	return h

func money(v: float) -> String:
	if absf(v) >= 10000:
		return "%.1fk" % (v / 1000.0)
	return str(int(round(v)))

func show_toast(text: String, dur: float = 3.5) -> void:
	toast.text = text
	toast_t = dur

func _window(w: float, h: float) -> Array:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(w, h)
	p.size = Vector2(w, h)
	p.visible = false
	add_child(p)
	p.visibility_changed.connect(func(): if p.visible: _center_win.call_deferred(p))
	p.resized.connect(func(): if p.visible: _center_win.call_deferred(p))
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 6)
	p.add_child(v)
	return [p, v]

func _center_win(p: Control) -> void:
	var vs := get_viewport().get_visible_rect().size
	p.reset_size()
	p.position = ((vs - p.size) * 0.5).floor().max(Vector2(0, 50))

# ------------------------------------------------------------------ top bar
func _build_top_bar() -> void:
	top_bar = PanelContainer.new()
	top_bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top_bar.offset_bottom = 46
	add_child(top_bar)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 18)
	top_bar.add_child(h)
	flag = FlagRect.new(); flag.custom_minimum_size = Vector2(42, 28)
	h.add_child(flag)
	lbl_nation = L("", 20, GOLD); h.add_child(lbl_nation)
	lbl_funds = L("", 16); lbl_funds.tooltip_text = "Treasury (monthly net)"; lbl_funds.mouse_filter = Control.MOUSE_FILTER_PASS; h.add_child(lbl_funds)
	lbl_manpower = L("", 16); lbl_manpower.tooltip_text = "Manpower available for new regiments"; lbl_manpower.mouse_filter = Control.MOUSE_FILTER_PASS; h.add_child(lbl_manpower)
	lbl_stab = L("", 16); lbl_stab.tooltip_text = "Stability: driven by citizens' needs, taxes and war"; lbl_stab.mouse_filter = Control.MOUSE_FILTER_PASS; h.add_child(lbl_stab)
	lbl_exh = L("", 16); lbl_exh.tooltip_text = "War exhaustion"; lbl_exh.mouse_filter = Control.MOUSE_FILTER_PASS; h.add_child(lbl_exh)
	var sp := Control.new(); sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL; h.add_child(sp)
	h.add_child(B("☰ Menu", func(): toggle_game_menu(), false, "Save, load, settings (Esc)"))
	h.add_child(B("Diplomacy (F1)", func(): toggle_diplomacy()))
	h.add_child(B("Economy & Army (F2)", func(): toggle_economy()))
	lbl_era = L("", 16, GOLD); h.add_child(lbl_era)
	lbl_date = L("", 18); lbl_date.custom_minimum_size = Vector2(120, 0); h.add_child(lbl_date)
	var sb := HBoxContainer.new(); sb.add_theme_constant_override("separation", 2)
	var names := ["⏸", "▶", "▶▶", "▶▶▶", "x120", "x365"]
	for i in names.size():
		var b := B(names[i], func(): Sim.set_speed(i), false, Sim.SPEED_NAMES[i])
		b.toggle_mode = true
		b.custom_minimum_size = Vector2(36, 0)
		speed_btns.append(b)
		sb.add_child(b)
	h.add_child(sb)

func _refresh_speed() -> void:
	for i in speed_btns.size():
		speed_btns[i].set_pressed_no_signal(i == Sim.speed_idx)

func refresh_top() -> void:
	if not Sim.nations.has(Sim.player):
		return
	var n: Dictionary = Sim.nations[Sim.player]
	flag.set_nation(Sim.player)
	lbl_nation.text = n["name"]
	var net: float = n["net"]
	lbl_funds.text = "💰 %s (%s%s/mo)" % [money(n["funds"]), "+" if net >= 0 else "", money(net)]
	lbl_funds.add_theme_color_override("font_color", PARCH if n["funds"] >= 0 else BAD)
	lbl_manpower.text = "👥 %s" % money(n["manpower"])
	lbl_stab.text = "⚖ %d%%" % int(n["stability"] * 100)
	lbl_stab.add_theme_color_override("font_color", GOOD if n["stability"] > 0.6 else (PARCH if n["stability"] > 0.35 else BAD))
	lbl_exh.text = "War %d%%" % int(n["exhaustion"] * 100) if Sim.at_war_any(Sim.player) else "At peace"
	lbl_era.text = GameData.eras[Sim.era]["name"]
	lbl_date.text = Sim.date_string()
	_refresh_speed()

# ------------------------------------------------------------------ selection panel
func _build_sel_panel() -> void:
	sel_panel = PanelContainer.new()
	sel_panel.position = Vector2(12, 58)
	sel_panel.custom_minimum_size = Vector2(330, 0)
	add_child(sel_panel)
	sel_box = VBoxContainer.new()
	sel_box.add_theme_constant_override("separation", 5)
	sel_panel.add_child(sel_box)
	sel_panel.visible = false

func select_province(pid: int) -> void:
	sel_pid = pid; sel_army = -1
	refresh_selection()

func select_army(aid: int) -> void:
	sel_army = aid
	if Sim.armies.has(aid):
		sel_pid = Sim.armies[aid]["node"] if Sim.armies[aid]["node"] < GameData.SEA_NODE else -1
	refresh_selection()

func refresh_selection() -> void:
	clear(sel_box)
	sel_panel.visible = false
	if sel_army >= 0 and Sim.armies.has(sel_army):
		_army_panel(Sim.armies[sel_army])
		sel_panel.visible = true
	elif sel_pid > 0 and GameData.provinces.has(sel_pid):
		_province_panel(sel_pid)
		sel_panel.visible = true
	sel_panel.reset_size()

func _province_panel(pid: int) -> void:
	var p: Dictionary = GameData.provinces[pid]
	var o: String = Sim.prov_owner.get(pid, "")
	var f := FlagRect.new(); f.custom_minimum_size = Vector2(36, 24); f.set_nation(o)
	sel_box.add_child(row([f, title(p["name"])]))
	if o != "":
		var rel := "" if o == Sim.player else "  (relation %+d%s)" % [int(Sim.relation(Sim.player, o)), ", AT WAR" if Sim.at_war(Sim.player, o) else ""]
		sel_box.add_child(L("Owner: %s%s" % [Sim.nations[o]["name"], rel], 14, BAD if Sim.at_war(Sim.player, o) else PARCH))
	sel_box.add_child(L("Terrain: %s · Resource: %s" % [p["terrain"].capitalize(), p["resource"].capitalize()], 14, DIM))
	sel_box.add_child(L("Population: %s · Garrison: %d" % [money(Sim.prov_pop(pid)), int(Sim.garrison(pid))], 14, DIM))
	if o != "" and Sim.nations[o]["capital"] == pid:
		sel_box.add_child(L("★ Capital", 14, GOLD))
	if Sim.sieges.has(pid):
		var s: Dictionary = Sim.sieges[pid]
		sel_box.add_child(L("Under siege by %s" % Sim.nations[s["by"]]["name"], 14, BAD))
		sel_box.add_child(bar(float(s.get("progress", 0.0)) / maxf(Sim.siege_days_needed(pid), 1.0), BAD, 300))
	var here := Sim.armies_in(pid)
	if not here.is_empty():
		sel_box.add_child(HSeparator.new())
		for a in here:
			var aid: int = a["id"]
			sel_box.add_child(B("%s — %s (%s men)" % [Sim.nations[a["owner"]]["name"], a["name"], money(Sim.army_men(a))], func(): main.select_army(aid)))
	if o == Sim.player:
		sel_box.add_child(HSeparator.new())
		sel_box.add_child(L("Raise regiments here:", 14, GOLD))
		_procure_buttons(sel_box, pid)
	elif o != "":
		sel_box.add_child(B("Diplomacy with %s" % Sim.nations[o]["name"], func(): open_diplomacy(o)))

func _procure_buttons(box: Container, pid: int) -> void:
	var era_id: String = GameData.eras[Sim.era]["id"]
	var g := GridContainer.new(); g.columns = 2
	g.add_theme_constant_override("h_separation", 6); g.add_theme_constant_override("v_separation", 4)
	for uid in GameData.units_by_era[era_id]:
		var d: Dictionary = GameData.units[uid]
		var c := Sim.can_afford(Sim.player, uid)
		var res_txt := ""
		for r in d["resources"].keys():
			res_txt += " %s×%d" % [r, d["resources"][r]]
		var tip := "%s (%s)\nMen %d · Cost %d (+%d to import missing resources) · Upkeep %.1f/mo\nMelee %d · Defence %d · Range %d · Armour %.0f%%\nNeeds:%s" % [d["name"], d["role"], d["men"], d["cost"], int(c["res_buy"]), d["upkeep"], d["melee"], d["defense"], d["range"], float(d["armor"]) * 100.0, res_txt if res_txt != "" else " —"]
		var id: String = uid
		var b := B("%s  %d" % [d["name"], int(c["cost"] + c["res_buy"])], func(): _buy(id, pid), not c["ok"], tip)
		b.custom_minimum_size = Vector2(150, 0)
		g.add_child(b)
	box.add_child(g)

func _buy(uid: String, pid: int) -> void:
	var r := Sim.buy_unit(Sim.player, uid, pid)
	if r["ok"]:
		show_toast("%s raised in %s (−%d)" % [GameData.units[uid]["name"], GameData.provinces[pid]["name"], int(r["cost"])])
	else:
		show_toast(r["msg"])
	refresh_selection()
	if econ_win.visible:
		refresh_econ()

func _army_panel(a: Dictionary) -> void:
	var f := FlagRect.new(); f.custom_minimum_size = Vector2(36, 24); f.set_nation(a["owner"])
	sel_box.add_child(row([f, title(a["name"])]))
	var where: String = GameData.provinces[a["node"]]["name"] if a["node"] < GameData.SEA_NODE else "at sea"
	sel_box.add_child(L("%s · %s · %s men" % [Sim.nations[a["owner"]]["name"], where, money(Sim.army_men(a))], 14, DIM))
	var st: String = a["state"]
	if a["path"].size() > 0:
		var dest: int = a["path"][-1]
		st = "marching to %s (%d stops)" % [GameData.provinces[dest]["name"] if GameData.provinces.has(dest) else "sea", a["path"].size()]
	sel_box.add_child(L("Status: %s" % st, 14, GOLD if a["state"] == "idle" else BAD))
	var era_id: String = GameData.eras[Sim.era]["id"]
	var mine: bool = a["owner"] == Sim.player
	for i in a["units"].size():
		var u: Dictionary = a["units"][i]
		var d: Dictionary = GameData.units[u["type"]]
		var old: bool = u["era"] != era_id
		var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 6)
		var nl := L("%s%s" % [d["name"], " (old)" if old else ""], 13, BAD if old else PARCH); nl.custom_minimum_size = Vector2(150, 0)
		h.add_child(nl)
		h.add_child(bar(u["men"] / u["max"], GOOD if u["men"] / u["max"] > 0.5 else BAD, 90))
		h.add_child(L(str(int(u["men"])), 12, DIM))
		if mine:
			var idx = i; var aid: int = a["id"]
			var db := B("✕", func(): Sim.disband_unit(aid, idx); refresh_selection(), false, "Disband (returns half the men to manpower)")
			db.add_theme_font_size_override("font_size", 11)
			h.add_child(db)
		sel_box.add_child(h)
	if mine:
		sel_box.add_child(HSeparator.new())
		var aid2: int = a["id"]
		var rc := Sim.refit_cost(a)
		if rc > 0:
			sel_box.add_child(B("Refit to %s equipment (%d)" % [GameData.eras[Sim.era]["name"], int(rc)], func(): _refit(aid2), Sim.nations[Sim.player]["funds"] < rc))
		for o in Sim.armies_in(a["node"]):
			if o["id"] != a["id"] and o["owner"] == Sim.player and o["state"] != "battle":
				var oid: int = o["id"]
				sel_box.add_child(B("Merge %s into this army" % o["name"], func(): Sim.merge_armies(aid2, oid); refresh_selection()))
		sel_box.add_child(L("Right-click a province to march there.", 13, DIM))
	if a["state"] == "battle" and Sim.battles.has(a["battle"]):
		var bid: int = a["battle"]
		sel_box.add_child(B("Watch this battle", func(): main.watch_battle(bid)))

func _refit(aid: int) -> void:
	var r := Sim.refit_army(aid)
	show_toast("Refitted %d units (−%d)" % [r["changed"], int(r["cost"])] if r["ok"] else r["msg"])
	refresh_selection()

# ------------------------------------------------------------------ event log
func _build_log() -> void:
	log_panel = PanelContainer.new()
	log_panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	log_panel.offset_left = -400; log_panel.offset_right = -12; log_panel.offset_top = 58; log_panel.offset_bottom = 330
	add_child(log_panel)
	var v := VBoxContainer.new(); log_panel.add_child(v)
	v.add_child(L("Dispatches", 16, GOLD))
	log_text = RichTextLabel.new()
	log_text.bbcode_enabled = true
	log_text.scroll_following = true
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_text.custom_minimum_size = Vector2(370, 230)
	v.add_child(log_text)

func _on_event(ev: Dictionary) -> void:
	if not Sim.player_relevant(ev):
		return
	var col = {"war": "#f07060", "peace": "#90d070", "battle": "#e8b060", "capture": "#f0a050", "era": "#ffd880", "diplo": "#a0c8f0", "economy": "#d0c090"}.get(ev["kind"], "#e8e0c8")
	log_text.append_text("[color=#9a9080]%s[/color]  [color=%s]%s[/color]\n" % [ev["date"], col, ev["text"]])
	if ev["kind"] in ["war", "peace", "capture"] and ev["nations"].has(Sim.player):
		show_toast(ev["text"])

# ------------------------------------------------------------------ game menu (save / load / settings)
var menu_win: PanelContainer
var menu_box: VBoxContainer

func _build_game_menu() -> void:
	var w := _window(560, 300)
	menu_win = w[0]
	menu_box = w[1]

func toggle_game_menu() -> void:
	menu_win.visible = not menu_win.visible
	if menu_win.visible:
		refresh_game_menu()

func refresh_game_menu() -> void:
	clear(menu_box)
	var hdr := row([title("Campaign Menu")])
	var sp := Control.new(); sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL; hdr.add_child(sp)
	hdr.add_child(B("Close", func(): menu_win.visible = false))
	menu_box.add_child(hdr)
	menu_box.add_child(L("%s · %s · %s" % [Sim.nations[Sim.player]["name"], Sim.date_string(), GameData.eras[Sim.era]["name"]], 14, DIM))
	var sv := row([B("Quick save (F5)", func(): main.save_slot("quicksave"); refresh_game_menu()),
		B("Quick load (F9)", func(): menu_win.visible = false; main.load_slot("quicksave"), not FileAccess.file_exists(Sim.save_path("quicksave"))),
		B("Save to new slot", func(): main.save_slot("%s_%d" % [Sim.player, Time.get_unix_time_from_system()]); refresh_game_menu())])
	menu_box.add_child(sv)
	menu_box.add_child(HSeparator.new())
	menu_box.add_child(L("Saved games", 16, GOLD))
	var saves := Sim.list_saves()
	if saves.is_empty():
		menu_box.add_child(L("No saves yet.", 14, DIM))
	for m in saves.slice(0, 8):
		var slot: String = m["slot"]
		var when := Time.get_datetime_string_from_unix_time(int(m["saved_unix"]) + int(Time.get_time_zone_from_system()["bias"]) * 60, true)
		menu_box.add_child(row([L("%s — %s, %s" % [slot, m["nation"], m["date"]], 14), L(when, 12, DIM),
			B("Load", func(): menu_win.visible = false; main.load_slot(slot))]))
	if main.has_method("build_settings_rows"):
		menu_box.add_child(HSeparator.new())
		main.build_settings_rows(menu_box, self)
	menu_box.add_child(HSeparator.new())
	menu_box.add_child(row([B("Quit to desktop", func(): get_tree().quit())]))

func on_game_loaded() -> void:
	for w in [diplo_win, econ_win, popup, menu_win, deploy_win]:
		if w: w.visible = false
	log_text.clear()
	var evs: Array = Sim.event_log.filter(func(e): return Sim.player_relevant(e))
	for ev in evs.slice(maxi(0, evs.size() - 40)):
		var col = {"war": "#f07060", "peace": "#90d070", "battle": "#e8b060", "capture": "#f0a050", "era": "#ffd880", "diplo": "#a0c8f0", "economy": "#d0c090"}.get(ev["kind"], "#e8e0c8")
		log_text.append_text("[color=#9a9080]%s[/color]  [color=%s]%s[/color]\n" % [ev["date"], col, ev["text"]])
	sel_pid = -1; sel_army = -1
	refresh_top()

# ------------------------------------------------------------------ diplomacy
func _build_diplo() -> void:
	var w := _window(1040, 640)
	diplo_win = w[0]
	var v: VBoxContainer = w[1]
	var hdr := row([title("Diplomacy"), _spacer(), B("Close", func(): diplo_win.visible = false)])
	v.add_child(hdr)
	var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 12)
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(h)
	var sc := ScrollContainer.new(); sc.custom_minimum_size = Vector2(330, 560)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	h.add_child(sc)
	diplo_list = VBoxContainer.new(); diplo_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(diplo_list)
	var sc2 := ScrollContainer.new(); sc2.size_flags_horizontal = Control.SIZE_EXPAND_FILL; sc2.custom_minimum_size = Vector2(660, 560)
	h.add_child(sc2)
	diplo_detail = VBoxContainer.new(); diplo_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	diplo_detail.add_theme_constant_override("separation", 6)
	sc2.add_child(diplo_detail)

func _spacer() -> Control:
	var c := Control.new(); c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return c

func toggle_diplomacy() -> void:
	if diplo_win.visible:
		diplo_win.visible = false
	else:
		open_diplomacy(diplo_target)

func open_diplomacy(code: String) -> void:
	econ_win.visible = false
	diplo_win.visible = true
	var cands := _diplo_candidates()
	if code == "" or not Sim.nations.has(code) or code == Sim.player:
		code = cands[0] if not cands.is_empty() else ""
	diplo_target = code
	refresh_diplo()

func _diplo_candidates() -> Array:
	var me := Sim.player
	var nb := Sim.neighbors_of(me)
	var out: Array = []
	for c in Sim.nations.keys():
		var n: Dictionary = Sim.nations[c]
		if c == me or not n["alive"]:
			continue
		if nb.has(c) or n["major"] or Sim.at_war(me, c) or Sim.has_treaty(me, c, "alliance") or Sim.has_treaty(me, c, "trade"):
			out.append(c)
	out.sort_custom(func(a, b):
		var ka := (0 if Sim.at_war(me, a) else (1 if nb.has(a) else 2))
		var kb := (0 if Sim.at_war(me, b) else (1 if nb.has(b) else 2))
		if ka != kb:
			return ka < kb
		return Sim.strength(a) > Sim.strength(b))
	return out

func _status_tags(c: String) -> String:
	var me := Sim.player
	var t: Array = []
	if Sim.at_war(me, c): t.append("WAR")
	if Sim.has_treaty(me, c, "alliance"): t.append("Ally")
	if Sim.has_treaty(me, c, "trade"): t.append("Trade")
	if Sim.has_treaty(me, c, "nap"): t.append("NAP")
	if Sim.has_treaty(me, c, "truce"): t.append("Truce")
	return ", ".join(t)

func refresh_diplo() -> void:
	clear(diplo_list)
	var me := Sim.player
	var nb := Sim.neighbors_of(me)
	for c in _diplo_candidates():
		var n: Dictionary = Sim.nations[c]
		var b := Button.new()
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		var rel := int(Sim.relation(me, c))
		var tags := _status_tags(c)
		b.text = "  %s%s   %+d %s" % [n["name"], " ◆" if nb.has(c) else "", rel, ("[" + tags + "]") if tags != "" else ""]
		b.toggle_mode = true
		b.button_pressed = c == diplo_target
		b.add_theme_color_override("font_color", BAD if Sim.at_war(me, c) else (GOOD if rel > 25 else PARCH))
		var code: String = c
		b.pressed.connect(func(): diplo_target = code; refresh_diplo())
		var f := FlagRect.new(); f.custom_minimum_size = Vector2(26, 17); f.set_nation(c)
		var h := row([f, b]); b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		diplo_list.add_child(h)
	_diplo_detail()

func _diplo_detail() -> void:
	clear(diplo_detail)
	var c := diplo_target
	if c == "" or not Sim.nations.has(c):
		return
	var me := Sim.player
	var n: Dictionary = Sim.nations[c]
	var f := FlagRect.new(); f.custom_minimum_size = Vector2(66, 44); f.set_nation(c)
	var nm := L(n["name"], 26, GOLD)
	diplo_detail.add_child(row([f, nm]))
	var rel := Sim.relation(me, c)
	var attitude := "Hostile" if rel < -30 else ("Unfriendly" if rel < -5 else ("Indifferent" if rel < 15 else ("Friendly" if rel < 45 else "Very friendly")))
	var tags := _status_tags(c)
	diplo_detail.add_child(L("%s · %s · %d provinces · Relations %+d (%s)%s" % ["Major power" if n["major"] else "Minor state", n["continent"], Sim.nation_provs[c].size(), int(rel), attitude, ("  ·  " + tags) if tags != "" else ""], 15))
	var sa := Sim.strength(me); var sb := Sim.strength(c)
	diplo_detail.add_child(L("Military strength: theirs %s vs ours %s (%.1f×) · Treasury %s · Stability %d%%" % [money(sb / 1000.0), money(sa / 1000.0), sb / maxf(sa, 1.0), money(n["funds"]), int(n["stability"] * 100)], 14, DIM))
	if Sim.at_war(me, c):
		diplo_detail.add_child(L("War score: %+.0f · Our exhaustion %d%%" % [Sim.war_score(me, c), int(Sim.nations[me]["exhaustion"] * 100)], 15, BAD))
	var allies := Sim.allies_of(c)
	if not allies.is_empty():
		var names: Array = []
		for x in allies:
			names.append(Sim.nations[x]["name"])
		diplo_detail.add_child(L("Allies (will defend them): " + ", ".join(names), 14, BAD))
	diplo_detail.add_child(HSeparator.new())
	diplo_detail.add_child(L("Proposals — how %s would view each offer:" % n["name"], 16, GOLD))
	var kinds := []
	if Sim.at_war(me, c):
		kinds = ["peace"]
	else:
		kinds = ["trade", "nap", "alliance"]
	for k in kinds:
		var ev := Sim.evaluate(me, c, k)
		var applicable: bool = ev["score"] > -900
		var box := VBoxContainer.new()
		var ok: bool = ev["score"] > 0
		var kn: String = {"trade": "Trade agreement", "nap": "Non-aggression pact (10 yrs)", "alliance": "Defensive alliance", "peace": "White peace (5-yr truce)"}[k]
		var verdict := ("Would ACCEPT (%+d)" % int(ev["score"])) if ok else ("Would REFUSE (%+d)" % int(ev["score"]))
		if not applicable:
			verdict = ev["breakdown"][0][0]
		var kind: String = k
		var pb := B("Propose", func(): _propose(kind), not applicable)
		box.add_child(row([L(kn, 16), _spacer(), L(verdict, 15, GOOD if ok else BAD), pb]))
		if applicable:
			var g := GridContainer.new(); g.columns = 2
			g.add_theme_constant_override("h_separation", 30)
			for it in ev["breakdown"]:
				g.add_child(L("   " + str(it[0]), 13, DIM))
				var v := int(it[1])
				g.add_child(L("%+d" % v, 13, GOOD if v > 0 else (BAD if v < 0 else DIM)))
			box.add_child(g)
		diplo_detail.add_child(box)
		diplo_detail.add_child(HSeparator.new())
	# treaties we hold that can be cancelled
	for k2 in ["trade", "nap", "alliance"]:
		if Sim.has_treaty(me, c, k2):
			var kk: String = k2
			diplo_detail.add_child(B("Cancel %s (relations −15)" % Sim._kind_name(k2), func(): Sim.cancel_treaty(me, c, kk); refresh_diplo()))
	var inc: float = maxf(Sim.nations[me]["income"].get("total", 50.0), 10.0)
	var amt := snappedf(inc * 0.5, 10.0)
	diplo_detail.add_child(B("Send a gift of %d (improves relations)" % int(amt), func(): if Sim.gift(me, c, amt): refresh_diplo(), Sim.nations[me]["funds"] < amt))
	if not Sim.at_war(me, c):
		var chk := Sim.can_declare_war(me, c)
		var warn := ""
		if Sim.has_treaty(me, c, "nap"):
			warn = " — breaks our pact (stability −12%)"
		var wb := B("⚔ Declare war%s" % warn, func(): _declare(c), not chk["ok"], chk["msg"])
		wb.add_theme_color_override("font_color", BAD)
		diplo_detail.add_child(wb)
		if not chk["ok"]:
			diplo_detail.add_child(L(chk["msg"], 13, DIM))

func _propose(kind: String) -> void:
	var r := Sim.propose(Sim.player, diplo_target, kind)
	show_toast("%s %s our proposal." % [Sim.nations[diplo_target]["name"], "accepts" if r["accepted"] else "rejects"])
	refresh_diplo()

func _declare(c: String) -> void:
	if Sim.declare_war(Sim.player, c):
		main.map.lut_dirty = true
	refresh_diplo()

# ------------------------------------------------------------------ economy & procurement
func _build_econ() -> void:
	var w := _window(980, 620)
	econ_win = w[0]
	var v: VBoxContainer = w[1]
	v.add_child(row([title("Economy, Administration & Procurement"), _spacer(), B("Close", func(): econ_win.visible = false)]))
	var sc := ScrollContainer.new(); sc.size_flags_vertical = Control.SIZE_EXPAND_FILL; sc.custom_minimum_size = Vector2(940, 560)
	v.add_child(sc)
	econ_box = VBoxContainer.new(); econ_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	econ_box.add_theme_constant_override("separation", 6)
	sc.add_child(econ_box)

func toggle_economy() -> void:
	diplo_win.visible = false
	econ_win.visible = not econ_win.visible
	if econ_win.visible:
		refresh_econ()

func refresh_econ() -> void:
	clear(econ_box)
	var me := Sim.player
	var n: Dictionary = Sim.nations[me]
	var cols := HBoxContainer.new(); cols.add_theme_constant_override("separation", 40)
	econ_box.add_child(cols)
	var c1 := VBoxContainer.new(); cols.add_child(c1)
	c1.add_child(L("Monthly income", 17, GOLD))
	for k in n["income"].keys():
		if k != "total":
			c1.add_child(row([_w(L(k, 14), 200), L("+%s" % money(n["income"][k]), 14, GOOD)]))
	c1.add_child(row([_w(L("Total", 15, GOLD), 200), L(money(n["income"].get("total", 0.0)), 15, GOLD)]))
	var c2 := VBoxContainer.new(); cols.add_child(c2)
	c2.add_child(L("Monthly expenses", 17, GOLD))
	for k in n["expense"].keys():
		if k != "total":
			c2.add_child(row([_w(L(k, 14), 200), L("−%s" % money(n["expense"][k]), 14, BAD)]))
	c2.add_child(row([_w(L("Total", 15, GOLD), 200), L(money(n["expense"].get("total", 0.0)), 15, GOLD)]))
	var c3 := VBoxContainer.new(); cols.add_child(c3)
	c3.add_child(L("Citizens' needs (automatic)", 17, GOLD))
	for k in ["food", "goods", "security"]:
		var v: float = n["needs"][k]
		c3.add_child(row([_w(L(k.capitalize(), 14), 90), bar(v, GOOD if v > 0.6 else (GOLD if v > 0.35 else BAD), 160), L("%d%%" % int(v * 100), 13, DIM)]))
	c3.add_child(row([_w(L("Stability", 14), 90), bar(n["stability"], GOLD, 160), L("%d%%" % int(n["stability"] * 100), 13, DIM)]))
	econ_box.add_child(L("Net: %s%s per month · Treasury %s · Provinces %d · Population %s" % ["+" if n["net"] >= 0 else "", money(n["net"]), money(n["funds"]), Sim.nation_provs[me].size(), money(Sim._pop_total(me))], 15, GOOD if n["net"] >= 0 else BAD))
	econ_box.add_child(HSeparator.new())
	var th := HBoxContainer.new(); th.add_theme_constant_override("separation", 8)
	th.add_child(L("Tax policy:", 15, GOLD))
	var tnames := ["Low (stability +)", "Normal", "High (stability −)"]
	for i in 3:
		var lvl := i
		var b := B(tnames[i], func(): Sim.set_tax(me, lvl); refresh_econ(); refresh_top())
		b.toggle_mode = true; b.button_pressed = n["tax"] == i
		th.add_child(b)
	th.add_child(L("   Welfare spending:", 15, GOLD))
	var sl := HSlider.new(); sl.min_value = 0; sl.max_value = 1; sl.step = 0.05; sl.value = n["welfare"]; sl.custom_minimum_size = Vector2(160, 20)
	sl.value_changed.connect(func(v): Sim.set_welfare(me, v))
	sl.drag_ended.connect(func(_c): refresh_econ())
	th.add_child(sl)
	th.add_child(L("%d%%" % int(n["welfare"] * 100), 14))
	econ_box.add_child(th)
	var stock := HBoxContainer.new(); stock.add_theme_constant_override("separation", 14)
	stock.add_child(L("Strategic stockpile:", 15, GOLD))
	for r in GameData.resources:
		stock.add_child(L("%s %d" % [r.capitalize(), int(n["stock"].get(r, 0.0))], 14))
	econ_box.add_child(stock)
	econ_box.add_child(L("Surplus above 25 is exported automatically; missing resources are imported at a premium when procuring.", 12, DIM))
	econ_box.add_child(HSeparator.new())
	var era_id: String = GameData.eras[Sim.era]["id"]
	econ_box.add_child(L("Procurement — %s equipment (raised at the capital, %s)" % [GameData.eras[Sim.era]["name"], GameData.provinces[n["capital"]]["name"]], 17, GOLD))
	var g := GridContainer.new(); g.columns = 8
	g.add_theme_constant_override("h_separation", 14)
	for hname in ["Unit", "Role", "Men", "Cost", "Upkeep", "Atk/Def", "Range", ""]:
		g.add_child(L(hname, 13, GOLD))
	for uid in GameData.units_by_era[era_id]:
		var d: Dictionary = GameData.units[uid]
		var c := Sim.can_afford(me, uid)
		g.add_child(L(d["name"], 14)); g.add_child(L(d["role"], 13, DIM)); g.add_child(L(str(int(d["men"])), 13))
		g.add_child(L("%d%s" % [int(c["cost"]), (" +%d" % int(c["res_buy"])) if c["res_buy"] > 0 else ""], 13))
		g.add_child(L("%.1f" % d["upkeep"], 13)); g.add_child(L("%d/%d" % [d["melee"], d["defense"]], 13)); g.add_child(L(str(int(d["range"])), 13))
		var id: String = uid
		g.add_child(B("Buy", func(): _buy(id, n["capital"]), not c["ok"], "" if c["ok"] else ("Not enough funds" if not c["funds_ok"] else "Not enough manpower")))
	econ_box.add_child(g)
	econ_box.add_child(L("Only current-era equipment can be bought. Buying never advances the era — eras change with the calendar (1500, 1800, 1914, 1980).", 12, DIM))
	econ_box.add_child(HSeparator.new())
	econ_box.add_child(L("Armies", 17, GOLD))
	for a in Sim.armies.values():
		if a["owner"] != me:
			continue
		var old := 0
		for u in a["units"]:
			if u["era"] != era_id:
				old += 1
		var aid: int = a["id"]
		var where: String = GameData.provinces[a["node"]]["name"] if a["node"] < GameData.SEA_NODE else "at sea"
		econ_box.add_child(row([_w(L("%s — %d units, %s men, %s%s" % [a["name"], a["units"].size(), money(Sim.army_men(a)), where, (" · %d outdated" % old) if old > 0 else ""], 14), 520),
			B("Select", func(): econ_win.visible = false; main.select_army(aid)),
			B("Refit (%d)" % int(Sim.refit_cost(a)), func(): _refit(aid); refresh_econ(), Sim.refit_cost(a) <= 0)]))

func _w(c: Control, w: float) -> Control:
	c.custom_minimum_size.x = w
	return c

# ------------------------------------------------------------------ deployment
func _build_deploy() -> void:
	var w := _window(760, 520)
	deploy_win = w[0]
	deploy_box = w[1]

func show_deploy(bid: int) -> void:
	deploy_bid = bid
	var b: Dictionary = Sim.battles[bid]
	var ps: int = b["player_side"]
	deploy_orders = b["orders"][ps].duplicate()
	_deploy_refresh()
	deploy_win.visible = true

func _deploy_refresh() -> void:
	clear(deploy_box)
	var b: Dictionary = Sim.battles[deploy_bid]
	var ps: int = b["player_side"]
	var p: Dictionary = GameData.provinces[b["prov"]]
	deploy_box.add_child(title("Battle of %s" % p["name"]))
	deploy_box.add_child(L("%s attacks %s · Terrain: %s · We are the %s" % [Sim.nations[b["codes"][0]]["name"], Sim.nations[b["codes"][1]]["name"], p["terrain"].capitalize(), "attacker" if ps == 0 else "defender"], 15, DIM))
	var cols := HBoxContainer.new(); cols.add_theme_constant_override("separation", 30)
	for s in [ps, 1 - ps]:
		var v := VBoxContainer.new()
		var men := 0.0
		for u in b["units"][s]:
			men += u["men"]
		v.add_child(L(("Our forces" if s == ps else "Enemy forces") + " — %s men" % money(men), 16, GOOD if s == ps else BAD))
		var cnt := {}
		for u in b["units"][s]:
			var nm: String = GameData.units[u["type"]]["name"]
			cnt[nm] = cnt.get(nm, 0) + 1
		for k in cnt.keys():
			v.add_child(L("  %d × %s" % [cnt[k], k], 14))
		cols.add_child(v)
	deploy_box.add_child(cols)
	deploy_box.add_child(HSeparator.new())
	deploy_box.add_child(L("Battle objective (your generals fight the battle; you set the plan):", 15, GOLD))
	var oh := HBoxContainer.new()
	var odesc := {"assault": "Assault — advance and engage", "hold": "Hold — defend the line, fire from cover", "flank": "Flank — cavalry sweeps the wings", "bombard": "Bombard — artillery first, then advance"}
	for o in BattleSim.OBJECTIVES:
		var oo: String = o
		var bt := B(o.capitalize(), func(): deploy_orders["objective"] = oo; _deploy_refresh(), false, odesc[o])
		bt.toggle_mode = true; bt.button_pressed = deploy_orders["objective"] == o
		oh.add_child(bt)
	deploy_box.add_child(oh)
	deploy_box.add_child(L(odesc[deploy_orders["objective"]], 13, DIM))
	deploy_box.add_child(L("Formation:", 15, GOLD))
	var fh := HBoxContainer.new()
	for fname in BattleSim.FORMATIONS.keys():
		var ff: String = fname
		var bt2 := B(fname.capitalize(), func(): deploy_orders["formation"] = ff; _deploy_refresh())
		bt2.toggle_mode = true; bt2.button_pressed = deploy_orders["formation"] == fname
		fh.add_child(bt2)
	deploy_box.add_child(fh)
	deploy_box.add_child(HSeparator.new())
	var bid := deploy_bid
	var wb := B("⚔  Deploy and watch the battle", func(): deploy_win.visible = false; deploy_chosen.emit(bid, deploy_orders.duplicate(), true))
	wb.custom_minimum_size = Vector2(320, 44); wb.add_theme_font_size_override("font_size", 18)
	var ab := B("Deploy and continue (resolve off-screen)", func(): deploy_win.visible = false; deploy_chosen.emit(bid, deploy_orders.duplicate(), false))
	ab.custom_minimum_size = Vector2(0, 44)
	deploy_box.add_child(row([wb, ab]))
	deploy_box.add_child(L("The campaign clock keeps running during the battle; other battles resolve with the same model.", 12, DIM))

# ------------------------------------------------------------------ popups
func _build_popup() -> void:
	var w := _window(620, 300)
	popup = w[0]
	popup_box = w[1]

func show_popup(t: String, body: String, buttons: Array) -> void:
	clear(popup_box)
	popup_box.add_child(title(t))
	var rt := RichTextLabel.new(); rt.bbcode_enabled = true; rt.fit_content = true; rt.text = body
	rt.custom_minimum_size = Vector2(580, 0)
	popup_box.add_child(rt)
	var h := HBoxContainer.new(); h.alignment = BoxContainer.ALIGNMENT_END
	for b in buttons:
		var cb: Callable = b[1]
		h.add_child(B(b[0], func(): popup.visible = false; cb.call()))
	popup_box.add_child(h)
	popup.visible = true
	popup.reset_size()
	popup.position = (get_viewport_rect().size - popup.size) * 0.5

func _on_era(e: int) -> void:
	var ed: Dictionary = GameData.eras[e]
	var names: Array = []
	for uid in GameData.units_by_era[ed["id"]]:
		names.append(GameData.units[uid]["name"])
	show_popup("A New Age: %s" % ed["name"],
		"The world enters the [b]%s[/b] (%d).\n\nNew equipment available for procurement: [color=#ffd880]%s[/color].\nProductivity ×%.1f · Armies march %d km/day · Naval reach %d sea zones.\n\nExisting regiments keep their old equipment until refitted (Army panel → Refit)." % [ed["name"], int(ed["start"]), ", ".join(names), ed["productivity"], ed["move_km_day"], ed["naval_range"]],
		[["Continue", func(): pass]])

func _on_offer(offer: Dictionary) -> void:
	var from: String = offer["from"]
	var kn := Sim._kind_name(offer["kind"])
	show_popup("Envoy from %s" % Sim.nations[from]["name"], "%s proposes a [b]%s[/b].\nRelations: %+d." % [Sim.nations[from]["name"], kn, int(Sim.relation(from, Sim.player))],
		[["Decline", func(): Sim.respond_offer(offer, false)], ["Accept", func(): Sim.respond_offer(offer, true); main.map.lut_dirty = true]])

func _on_battle_resolved(bid: int, res: Dictionary) -> void:
	var b: Dictionary = Sim.battles.get(bid, {})
	if b.is_empty() or b["player_side"] < 0:
		return
	var won: bool = res["winner"] == b["player_side"]
	show_toast("%s at %s! Losses: ours %d, theirs %d" % ["Victory" if won else "Defeat", GameData.provinces[b["prov"]]["name"], int(res["losses"][b["player_side"]]), int(res["losses"][1 - b["player_side"]])], 5.0)

func _process(delta: float) -> void:
	toast.position = Vector2((get_viewport().get_visible_rect().size.x - 800.0) * 0.5, 70.0)
	if toast_t > 0:
		toast_t -= delta
		toast.modulate.a = clampf(toast_t, 0.0, 1.0)
	_refresh_t -= delta
	if _refresh_t <= 0:
		_refresh_t = 0.25
		refresh_top()
		if sel_panel.visible and not get_viewport().gui_get_hovered_control() in _descendants(sel_panel):
			refresh_selection()

func _descendants(n: Node) -> Array:
	var out: Array = []
	var st := [n]
	while st.size() > 0:
		var x: Node = st.pop_back()
		out.append(x)
		st.append_array(x.get_children())
	return out

func any_window_open() -> bool:
	return diplo_win.visible or econ_win.visible or deploy_win.visible or popup.visible or menu_win.visible
