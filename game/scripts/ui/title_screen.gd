## Title screen (v0.6): logo, main menu (Continue / New Campaign / Load / Settings / Credits / Quit) over a slowly
## drifting campaign map, and the New Campaign flow (five start eras, the playable nations, Start Campaign).
## Presentation only: campaigns still start through main._start_game() and load through main.load_slot().
class_name TitleScreen
extends Control

const VERSION := "v0.6.0 beta"
const NATION_TEXT := {
	"USA": "A continental power between two oceans. Vast land and resources, but every rival worth fighting lies across the sea.",
	"SWE": "A Baltic kingdom of forest, iron and fish. Norway, Denmark, Finland and Russia are all within a few days' march.",
	"JPN": "An island empire on the edge of Asia. Korea and China are close, but every campaign abroad begins with a sea crossing.",
}

var main: Node
var first_btn: Button
var menu_col: VBoxContainer
var page: PanelContainer
var page_body: VBoxContainer
var page_name := ""
var status: Label
var sel_year := 1800
var sel_nation := "SWE"
var nav_btns := {}
var _t := 0.0
var _drift_c := Vector3.ZERO

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = Hud.make_theme()
	var years: Array = GameData.start_years.map(func(y): return int(y))
	if not years.has(1800) and not years.is_empty():
		sel_year = years[0]
	if not GameData.playable.has(sel_nation) and not GameData.playable.is_empty():
		sel_nation = GameData.playable[0]
	_build_backdrop()
	_build_menu()
	_build_page()
	_build_footer()
	_drift_c = GameData.node_world(GameData.countries["SWE"]["capital"]) if GameData.countries.has("SWE") else Vector3(190, 0, 45)
	_drift_c += Vector3(-6, 0, 10)
	if main and main.cam:
		main.cam.look_at_world(_drift_c, 72.0, true)
		main.cam.yaw = -0.18; main.cam._t_yaw = -0.18

# ------------------------------------------------------------------ backdrop: shaded map + vignette
func _build_backdrop() -> void:
	var shade := ColorRect.new()
	shade.color = Color(0.03, 0.035, 0.05, 0.28)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)
	# left-to-right darkening behind the menu column
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.42, 1.0])
	g.colors = PackedColorArray([Color(0.025, 0.03, 0.04, 0.94), Color(0.03, 0.035, 0.05, 0.62), Color(0.03, 0.035, 0.05, 0.0)])
	var gt := GradientTexture2D.new()
	gt.gradient = g; gt.width = 256; gt.height = 4
	var side := TextureRect.new()
	side.texture = gt
	side.stretch_mode = TextureRect.STRETCH_SCALE
	side.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	side.offset_right = 720
	side.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(side)
	# soft top and bottom bands
	for top in [true, false]:
		var g2 := Gradient.new()
		g2.colors = PackedColorArray([Color(0.02, 0.025, 0.035, 0.75), Color(0.02, 0.025, 0.035, 0.0)])
		var t2 := GradientTexture2D.new()
		t2.gradient = g2; t2.width = 4; t2.height = 128
		t2.fill_from = Vector2(0, 0) if top else Vector2(0, 1)
		t2.fill_to = Vector2(0, 1) if top else Vector2(0, 0)
		var band := TextureRect.new()
		band.texture = t2; band.stretch_mode = TextureRect.STRETCH_SCALE
		band.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE if top else Control.PRESET_BOTTOM_WIDE)
		if top: band.offset_bottom = 120
		else: band.offset_top = -160
		band.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(band)

# ------------------------------------------------------------------ logo + main menu
func _build_menu() -> void:
	menu_col = VBoxContainer.new()
	menu_col.position = Vector2(88, 0)
	menu_col.set_anchors_and_offsets_preset(Control.PRESET_LEFT_WIDE)
	menu_col.offset_left = 88; menu_col.offset_right = 88 + 420
	menu_col.offset_top = 0; menu_col.offset_bottom = 0
	menu_col.alignment = BoxContainer.ALIGNMENT_CENTER
	menu_col.add_theme_constant_override("separation", 6)
	add_child(menu_col)
	menu_col.add_child(UiKit.caption("A GRAND STRATEGY OF FIVE AGES", UiKit.BRASS_DIM))
	var logo := UiKit.label("Iron Crowns", 86, UiKit.BRASS, "title")
	logo.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.6))
	logo.add_theme_constant_override("shadow_offset_y", 3)
	logo.add_theme_constant_override("shadow_outline_size", 6)
	menu_col.add_child(logo)
	menu_col.add_child(_ornament(380))
	menu_col.add_child(_gap(26))
	var latest: Dictionary = {}
	var saves := Sim.list_saves()
	if not saves.is_empty():
		latest = saves[0]
	var cont := _nav("Continue", func(): _continue(latest), latest.is_empty(),
		("Resume %s — %s (%s)" % [latest["nation"], latest["date"], latest["slot"]]) if not latest.is_empty() else "No saved campaign yet")
	if not latest.is_empty():
		menu_col.add_child(cont)
		var sub := UiKit.label("%s · %s" % [latest["nation"], latest["date"]], 15, UiKit.DIM)
		sub.custom_minimum_size = Vector2(0, 0)
		var m := MarginContainer.new(); m.add_theme_constant_override("margin_left", 22); m.add_theme_constant_override("margin_top", -8)
		m.add_child(sub)
		menu_col.add_child(m)
	var newb := _nav("New Campaign", func(): show_page("new"))
	menu_col.add_child(newb)
	menu_col.add_child(_nav("Load Campaign", func(): show_page("load"), saves.is_empty(), "" if not saves.is_empty() else "No saved campaigns yet"))
	menu_col.add_child(_nav("Settings", func(): show_page("settings")))
	menu_col.add_child(_nav("Credits", func(): show_page("credits")))
	menu_col.add_child(_gap(10))
	menu_col.add_child(_nav("Quit", func(): get_tree().quit()))
	first_btn = cont if not latest.is_empty() else newb
	status = UiKit.label("", 15, UiKit.MIL)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.custom_minimum_size = Vector2(380, 0)
	menu_col.add_child(status)

func _gap(h: float) -> Control:
	var c := Control.new(); c.custom_minimum_size = Vector2(0, h); c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c

## A thin brass rule with a small lozenge in the middle.
func _ornament(w: float) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(w, 12)
	c.draw.connect(func():
		var y := 6.0
		var col := Color(UiKit.BRASS.r, UiKit.BRASS.g, UiKit.BRASS.b, 0.75)
		c.draw_line(Vector2(0, y), Vector2(w * 0.5 - 12, y), col, 1.0)
		c.draw_line(Vector2(w * 0.5 + 12, y), Vector2(w, y), col, 1.0)
		var d := PackedVector2Array([Vector2(w * 0.5, y - 5), Vector2(w * 0.5 + 6, y), Vector2(w * 0.5, y + 5), Vector2(w * 0.5 - 6, y)])
		c.draw_colored_polygon(d, col))
	return c

## Main-menu entry: large serif text, left aligned; a brass marker shows the hovered / open entry.
func _nav(text: String, cb: Callable, disabled: bool = false, tip: String = "") -> Button:
	var b := Button.new()
	b.text = text
	b.flat = false
	b.theme_type_variation = "GhostButton"
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.disabled = disabled
	b.tooltip_text = tip
	b.add_theme_font_override("font", UiKit.font("title2"))
	b.add_theme_font_size_override("font_size", 30)
	b.add_theme_color_override("font_color", UiKit.TEXT)
	b.add_theme_color_override("font_hover_color", UiKit.BRASS.lightened(0.15))
	b.add_theme_color_override("font_focus_color", UiKit.BRASS.lightened(0.15))
	b.add_theme_color_override("font_pressed_color", UiKit.BRASS)
	b.add_theme_color_override("font_disabled_color", Color(UiKit.FAINT.r, UiKit.FAINT.g, UiKit.FAINT.b, 0.7))
	b.custom_minimum_size = Vector2(380, 50)
	var empty := StyleBoxEmpty.new(); empty.content_margin_left = 22; empty.content_margin_top = 4; empty.content_margin_bottom = 4
	var mark := StyleBoxFlat.new()
	mark.bg_color = Color(UiKit.BRASS.r, UiKit.BRASS.g, UiKit.BRASS.b, 0.07)
	mark.border_color = UiKit.BRASS
	mark.border_width_left = 3
	mark.content_margin_left = 22; mark.content_margin_top = 4; mark.content_margin_bottom = 4
	for st in ["normal", "disabled"]:
		b.add_theme_stylebox_override(st, empty)
	for st in ["hover", "pressed", "focus", "hover_pressed"]:
		b.add_theme_stylebox_override(st, mark)
	b.pressed.connect(cb)
	nav_btns[text] = b
	return b

func _build_footer() -> void:
	var f := UiKit.label("%s  ·  Godot %s" % [VERSION, Engine.get_version_info()["string"].split(".stable")[0]], 14, UiKit.FAINT)
	f.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	f.offset_left = 88; f.offset_top = -40; f.offset_bottom = -18; f.offset_right = 600
	add_child(f)
	var h := UiKit.label("Mouse, keyboard, gamepad and touch supported · F1 diplomacy · F2 economy · F5 / F9 quick save / load", 14, UiKit.FAINT)
	h.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	h.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	h.offset_left = -900; h.offset_right = -32; h.offset_top = -40; h.offset_bottom = -18
	add_child(h)

# ------------------------------------------------------------------ right-hand page (new campaign / load / settings / credits)
func _build_page() -> void:
	page = PanelContainer.new()
	page.theme_type_variation = "WindowPanel"
	page.visible = false
	add_child(page)
	var outer := VBoxContainer.new(); outer.add_theme_constant_override("separation", 10)
	page.add_child(outer)
	page_body = VBoxContainer.new(); page_body.add_theme_constant_override("separation", 10)
	page_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	outer.add_child(page_body)
	get_viewport().size_changed.connect(_place_page)

func _place_page() -> void:
	if not is_instance_valid(page):
		return
	var vs := get_viewport_rect().size
	var x0 := 640.0
	var w := clampf(vs.x - x0 - 40.0, 700.0, 1060.0)
	page.custom_minimum_size = Vector2(w, 0)
	page.size = Vector2.ZERO
	page.reset_size()
	page.position = Vector2(maxf(x0, vs.x - w - 48.0 - maxf(0.0, (vs.x - x0 - w - 48.0) * 0.5)), maxf(32.0, (vs.y - page.size.y) * 0.5)).floor()

func show_page(name: String) -> void:
	status.text = ""
	if page_name == name and page.visible:
		page.visible = false; page_name = ""
		_mark_nav()
		return
	page_name = name
	for c in page_body.get_children():
		page_body.remove_child(c); c.queue_free()
	match name:
		"new": _page_new()
		"load": _page_load()
		"settings": _page_settings()
		"credits": _page_credits()
	page.visible = true
	_mark_nav()
	_place_page()
	_place_page.call_deferred()
	if Controls.last_device == "joy":
		_focus_page.call_deferred()

func _focus_page() -> void:
	var b := _first_button(page_body)
	if b: b.grab_focus()

func _first_button(n: Node) -> Button:
	for c in n.get_children():
		if c is Button and not c.disabled and c.is_visible_in_tree():
			return c
		var r := _first_button(c)
		if r: return r
	return null

func _mark_nav() -> void:
	var names := {"new": "New Campaign", "load": "Load Campaign", "settings": "Settings", "credits": "Credits"}
	for k in nav_btns.keys():
		var b: Button = nav_btns[k]
		b.add_theme_color_override("font_color", UiKit.BRASS if page.visible and names.get(page_name, "") == k else UiKit.TEXT)

func _header(t: String, sub: String) -> void:
	var hb := HBoxContainer.new()
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", -2)
	tv.add_child(UiKit.title(t, 34))
	if sub != "":
		tv.add_child(UiKit.label(sub, 16, UiKit.DIM))
	tv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(tv)
	var x := UiKit.button("×", func(): show_page(page_name), "ghost", false, "Close (Esc)")
	x.add_theme_font_size_override("font_size", 26)
	hb.add_child(x)
	page_body.add_child(hb)
	var rule := ColorRect.new(); rule.color = Color(UiKit.BRASS.r, UiKit.BRASS.g, UiKit.BRASS.b, 0.35); rule.custom_minimum_size = Vector2(0, 1)
	page_body.add_child(rule)

# --- New campaign ------------------------------------------------------------
func _page_new() -> void:
	_header("New Campaign", "Choose an age and a nation. Everything else is decided on the map.")
	page_body.add_child(UiKit.section("1  ·  Starting age"))
	var eh := HBoxContainer.new(); eh.add_theme_constant_override("separation", 8)
	for y in GameData.start_years:
		eh.add_child(_era_card(int(y)))
	page_body.add_child(eh)
	var ei := GameData.era_for_year(sel_year)
	var ed: Dictionary = GameData.eras[ei]
	var info: Dictionary = UiKit.ERA_INFO.get(ed["id"], {})
	var unit_names: Array = []
	for uid in GameData.units_by_era.get(ed["id"], []):
		unit_names.append(GameData.units[uid]["name"])
	var dv := VBoxContainer.new(); dv.add_theme_constant_override("separation", 4)
	dv.add_child(UiKit.label("%s  ·  from %d" % [ed["name"], sel_year], 20, UiKit.TEXT, "semi"))
	dv.add_child(UiKit.para(info.get("desc", ""), 900, 16, UiKit.TEXT.darkened(0.08)))
	var g := GridContainer.new(); g.columns = 2
	g.add_theme_constant_override("h_separation", 16); g.add_theme_constant_override("v_separation", 2)
	g.add_child(UiKit.caption("Regiments")); g.add_child(UiKit.label(", ".join(unit_names), 15, UiKit.DIM))
	g.add_child(UiKit.caption("Marching")); g.add_child(UiKit.label("about %d km a day · fleets reach %d sea zones" % [int(ed["move_km_day"]), int(ed["naval_range"])], 15, UiKit.DIM))
	dv.add_child(g)
	var dcard := PanelContainer.new(); dcard.theme_type_variation = "CardPanel"; dcard.add_child(dv)
	page_body.add_child(dcard)
	page_body.add_child(UiKit.section("2  ·  Nation"))
	var nh := HBoxContainer.new(); nh.add_theme_constant_override("separation", 8)
	for code in GameData.playable:
		nh.add_child(_nation_card(code))
	page_body.add_child(nh)
	page_body.add_child(UiKit.label("Only these nations can be played in this build; every other country is run by the computer.", 14, UiKit.FAINT))
	page_body.add_child(HSeparator.new())
	var sum := VBoxContainer.new(); sum.add_theme_constant_override("separation", -2)
	sum.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sum.add_child(UiKit.caption("Your campaign"))
	sum.add_child(UiKit.label("%s  ·  %d  ·  %s" % [GameData.country_name(sel_nation), sel_year, ed["name"]], 22, UiKit.BRASS, "semi"))
	var f := FlagRect.new(); f.custom_minimum_size = Vector2(54, 36); f.set_nation_static(sel_nation); f.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var start := UiKit.button("Start Campaign", func(): _start(), "primary", false, "Begin as %s in %d" % [GameData.country_name(sel_nation), sel_year])
	start.custom_minimum_size = Vector2(250, 52)
	start.add_theme_font_size_override("font_size", 20)
	page_body.add_child(UiKit.hrow([f, sum, start], 14))

func _era_card(y: int) -> Button:
	var ei := GameData.era_for_year(y)
	var ed: Dictionary = GameData.eras[ei]
	var info: Dictionary = UiKit.ERA_INFO.get(ed["id"], {})
	var tint: Color = info.get("tint", UiKit.NAVY)
	var b := Button.new()
	b.toggle_mode = true
	b.button_pressed = y == sel_year
	b.custom_minimum_size = Vector2(0, 112)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.tooltip_text = "%s (%d)\n%s" % [ed["name"], y, info.get("desc", "")]
	var on := y == sel_year
	var sb := UiKit.box(tint.darkened(0.55) if on else Color(0.09, 0.1, 0.115, 0.92), UiKit.BRASS if on else UiKit.IRON_DIM, 2 if on else 1, 4, Vector4(10, 8, 10, 8))
	sb.border_width_top = 4
	sb.border_color = UiKit.BRASS if on else tint
	var hov := sb.duplicate() as StyleBoxFlat
	hov.bg_color = tint.darkened(0.45)
	for st in ["normal", "pressed", "hover_pressed"]:
		b.add_theme_stylebox_override(st, sb)
	b.add_theme_stylebox_override("hover", hov)
	var v := VBoxContainer.new(); v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 12; v.offset_top = 12; v.offset_right = -10
	v.add_theme_constant_override("separation", -2)
	var yl := UiKit.label(str(y), 36, UiKit.BRASS if on else UiKit.TEXT, "title")
	yl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(yl)
	var nl := UiKit.label(info.get("short", ed["name"]), 16, UiKit.TEXT if on else UiKit.DIM, "semi")
	nl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(nl)
	b.add_child(v)
	b.pressed.connect(func(): sel_year = y; _rebuild_new())
	return b

func _nation_card(code: String) -> Button:
	var on := code == sel_nation
	var b := Button.new()
	b.toggle_mode = true
	b.button_pressed = on
	b.custom_minimum_size = Vector2(0, 132)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var nm := GameData.country_name(code)
	b.tooltip_text = "Play as %s" % nm
	var sb := UiKit.box(Color(0.1, 0.12, 0.155, 0.95) if on else Color(0.09, 0.1, 0.115, 0.92), UiKit.BRASS if on else UiKit.IRON_DIM, 2 if on else 1, 4, Vector4(10, 8, 10, 8))
	var hov := sb.duplicate() as StyleBoxFlat
	hov.border_color = UiKit.BRASS_DIM if not on else UiKit.BRASS
	for st in ["normal", "pressed", "hover_pressed"]:
		b.add_theme_stylebox_override(st, sb)
	b.add_theme_stylebox_override("hover", hov)
	var v := VBoxContainer.new(); v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 14; v.offset_top = 12; v.offset_right = -12; v.offset_bottom = -8
	v.add_theme_constant_override("separation", 4)
	var f := FlagRect.new(); f.custom_minimum_size = Vector2(51, 34); f.set_nation_static(code); f.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", -3); tv.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var nl := UiKit.label(nm, 21, UiKit.BRASS if on else UiKit.TEXT, "semi"); nl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tv.add_child(nl)
	var c: Dictionary = GameData.countries.get(code, {})
	var cap_name: String = GameData.provinces[c["capital"]]["name"] if c.has("capital") and GameData.provinces.has(c["capital"]) else ""
	var sl := UiKit.label("%d provinces · capital %s" % [c.get("provinces", []).size(), cap_name], 14, UiKit.DIM); sl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	tv.add_child(sl)
	var hr := UiKit.hrow([f, tv], 10); hr.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(hr)
	var d := UiKit.label(NATION_TEXT.get(code, ""), 14, UiKit.TEXT.darkened(0.12))
	d.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	d.custom_minimum_size = Vector2(240, 0)
	d.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(d)
	b.add_child(v)
	b.pressed.connect(func(): sel_nation = code; _rebuild_new())
	return b

func _rebuild_new() -> void:
	var fo := get_viewport().gui_get_focus_owner()
	var had_focus := fo != null and page.is_ancestor_of(fo)
	for c in page_body.get_children():
		page_body.remove_child(c); c.queue_free()
	_page_new()
	_place_page.call_deferred()
	if had_focus:
		_focus_page.call_deferred()

func _start() -> void:
	main._start_game(sel_nation, sel_year)

func _continue(latest: Dictionary) -> void:
	if latest.is_empty():
		return
	_load(latest["slot"])

func _load(slot: String) -> void:
	var r: Dictionary = main.load_slot(slot)
	if not r.get("ok", false) and is_instance_valid(status):
		status.text = "Could not load \"%s\": %s" % [slot, r.get("msg", "unknown error")]

# --- Load --------------------------------------------------------------------
func _page_load() -> void:
	var saves := Sim.list_saves()
	_header("Load Campaign", "%d saved campaign%s · newest first" % [saves.size(), "" if saves.size() == 1 else "s"])
	var sc := ScrollContainer.new(); sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED; sc.follow_focus = true
	var lst := VBoxContainer.new(); lst.size_flags_horizontal = Control.SIZE_EXPAND_FILL; lst.add_theme_constant_override("separation", 6)
	sc.add_child(lst)
	for m in saves.slice(0, 30):
		var card := PanelContainer.new(); card.theme_type_variation = "CardPanel"
		card.add_child(Hud._save_row(m, func(slot: String): _load(slot)))
		lst.add_child(card)
	sc.custom_minimum_size = Vector2(0, minf(saves.slice(0, 30).size() * 66.0, 560.0))
	page_body.add_child(sc)

# --- Settings ----------------------------------------------------------------
func _page_settings() -> void:
	_header("Settings", "Saved automatically")
	var box := VBoxContainer.new(); box.add_theme_constant_override("separation", 8)
	Hud.build_settings_into(box, func(): (func(): if page_name == "settings": page_name = ""; show_page("settings")).call_deferred())
	page_body.add_child(box)
	page_body.add_child(UiKit.section("Controls"))
	var g := GridContainer.new(); g.columns = 2
	g.add_theme_constant_override("h_separation", 24); g.add_theme_constant_override("v_separation", 4)
	for row in [["Select", "Left-click · tap · gamepad A"], ["Move / attack / reinforce", "Right-click · long-press · gamepad X"],
			["Pan · zoom · rotate", "Drag or edge · wheel · Q / E or middle-drag"], ["Pause · speed", "Space · 1–5"],
			["Diplomacy · economy", "F1 · F2"], ["Quick save · load", "F5 · F9"], ["Menu · close", "Esc"]]:
		g.add_child(UiKit.caption(row[0])); g.add_child(UiKit.label(row[1], 15, UiKit.DIM))
	page_body.add_child(g)

# --- Credits -----------------------------------------------------------------
func _page_credits() -> void:
	_header("Credits", "Iron Crowns %s" % VERSION)
	var t := RichTextLabel.new(); t.bbcode_enabled = true; t.fit_content = true
	t.custom_minimum_size = Vector2(0, 0)
	t.add_theme_font_size_override("normal_font_size", 16); t.add_theme_font_size_override("bold_font_size", 16)
	t.text = """[color=#cba866][b]Game[/b][/color]
Design, code, art pipeline, music and sound: the Iron Crowns project. All music and sound effects are original and synthesised in code for this game (see AUDIO_LICENSES.md).

[color=#cba866][b]Engine[/b][/color]
Godot Engine — MIT licence, © Juan Linietsky, Ariel Manzur and contributors.

[color=#cba866][b]Map data[/b][/color]
Province and coastline geometry derived from Natural Earth (public domain).

[color=#cba866][b]Typefaces[/b][/color]
Cormorant SC — Christian Thalmann, SIL Open Font License 1.1.
Source Sans 3 — Adobe, SIL Open Font License 1.1.
Licence texts ship in assets/fonts/.

[color=#8a8f94]Historical nations, borders and eras are simplified for play and are not a statement about any real-world claim.[/color]"""
	page_body.add_child(t)

# ------------------------------------------------------------------ background motion and input
func _process(delta: float) -> void:
	_t += delta
	if main == null or main.cam == null or main.cam.is_flying():
		return
	# a slow Lissajous drift over Scandinavia and the Baltic (about two minutes per loop)
	var p := _drift_c + Vector3(sin(_t * 0.05) * 16.0, 0, sin(_t * 0.035 + 1.0) * 9.0)
	main.cam.look_at_world(p, 72.0 + sin(_t * 0.04) * 8.0)
	main.cam._t_yaw = -0.18 + sin(_t * 0.03) * 0.08

func _unhandled_input(ev: InputEvent) -> void:
	if ev.is_action_pressed("cancel") or ev.is_action_pressed("game_menu"):
		if page.visible:
			page.visible = false; page_name = ""
			_mark_nav()
			if Controls.last_device == "joy" and first_btn:
				first_btn.grab_focus()
			get_viewport().set_input_as_handled()
	elif page_name == "new" and page.visible and ev is InputEventKey and ev.pressed and not ev.echo and (ev.keycode == KEY_ENTER or ev.keycode == KEY_KP_ENTER):
		_start()
		get_viewport().set_input_as_handled()
