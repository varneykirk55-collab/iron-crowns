## Campaign HUD: top bar, command dock, selection panel, military alerts, dispatches, and the diplomacy, economy,
## inbox, deployment, game-menu and dialog windows. v0.6: rebuilt on the UiKit design system (presentation only;
## every order still goes through the same Sim / main calls as before).
class_name Hud
extends Control

signal deploy_chosen(bid: int, orders: Dictionary, watch: bool)
signal focus_world(pos: Vector3)

# Kept for other scripts (battle view, title screen): the design-system colours under their old names.
const GOLD := UiKit.BRASS
const PARCH := UiKit.TEXT
const DIM := UiKit.DIM
const GOOD := UiKit.GOOD
const BAD := UiKit.MIL

const TOP_H := 64.0        # top bar height (logical px; the UI is laid out in a 1600×900 canvas)
const SIDE_W := 392.0      # left selection panel and right column width
const MARGIN := 12.0

var main: Node
var top_bar: PanelContainer
var lbl_nation: Label
var flag: FlagRect
var lbl_funds: Label
var lbl_net: Label
var lbl_manpower: Label
var lbl_pop: Label
var lbl_stab: Label
var stab_meter: ProgressBar
var lbl_exh: Label
var war_stat: VBoxContainer
var lbl_era: Label
var lbl_date: Label
var lbl_speed: Label
var speed_btns: Array = []
var dock: HBoxContainer
var right_col: VBoxContainer
var alerts_box: VBoxContainer
var sel_panel: PanelContainer
var sel_scroll: ScrollContainer
var sel_box: VBoxContainer
var log_panel: PanelContainer
var log_text: RichTextLabel
var log_collapsed := false
var dim: ColorRect
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
var toast_panel: PanelContainer
var toast: Label
var toast_t := 0.0
var hint: Label
var sel_pid := -1
var sel_army := -1
var _refresh_t := 0.0
var theme_res: Theme

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	theme_res = make_theme()
	theme = theme_res
	_build_top_bar()
	_build_sel_panel()
	_build_right_column()
	_build_toast()
	_build_hint()
	_build_backdrop()
	_build_diplo()
	_build_econ()
	_build_deploy()
	_build_inbox()
	_build_game_menu()
	_build_popup()
	Sim.event_logged.connect(_on_event)
	Sim.era_changed.connect(_on_era)
	Sim.player_offer.connect(_on_offer)
	Sim.speed_changed.connect(func(_i): _refresh_speed())
	Sim.battle_resolved.connect(_on_battle_resolved)
	Sim.invasion_warning.connect(_on_invasion_warning)
	Controls.settings_changed.connect(_on_settings_changed)
	Controls.device_changed.connect(func(_k): _update_hint())
	_build_pad_cursor()
	_update_hint()

static func make_theme() -> Theme:
	var large := false
	var ml = Engine.get_main_loop()
	if ml and ml.root.has_node("Controls"):
		large = ml.root.get_node("Controls").large_targets
	return UiKit.make_theme(large)

# ------------------------------------------------------------------ helpers (thin wrappers over UiKit)
func L(text: String, size: int = 16, col: Color = PARCH) -> Label:
	return UiKit.label(text, size, col)

func B(text: String, cb: Callable, disabled: bool = false, tip: String = "", variant: String = "") -> Button:
	return UiKit.button(text, cb, variant, disabled, tip)

func title(text: String) -> Label:
	return UiKit.title(text, 24)

func bar(v: float, col: Color, w: float = 140.0) -> ProgressBar:
	return UiKit.meter(v, col, w)

func clear(c: Node) -> void:
	for ch in c.get_children():
		c.remove_child(ch)
		ch.queue_free()

func row(items: Array) -> HBoxContainer:
	return UiKit.hrow(items)

func _spacer() -> Control:
	return UiKit.spacer()

func money(v: float) -> String:
	return UiKit.compact(v)

func _w(c: Control, w: float) -> Control:
	c.custom_minimum_size.x = w
	return c

func _flag(code: String, w: float = 36.0) -> FlagRect:
	var f := FlagRect.new()
	f.custom_minimum_size = Vector2(w, roundf(w * 2.0 / 3.0))
	f.set_nation(code)
	return f

## Caption + value pair laid out as one row of a details grid.
func _kv(grid: GridContainer, k: String, v: String, col: Color = PARCH) -> void:
	grid.add_child(UiKit.caption(k))
	var l := L(v, 16, col)
	grid.add_child(l)

func _grid(cols: int = 2) -> GridContainer:
	var g := GridContainer.new()
	g.columns = cols
	g.add_theme_constant_override("h_separation", 14)
	g.add_theme_constant_override("v_separation", 3)
	return g

# ------------------------------------------------------------------ toast, hint, backdrop
func _build_toast() -> void:
	toast_panel = PanelContainer.new()
	toast_panel.theme_type_variation = "ToastPanel"
	toast_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	toast_panel.visible = false
	add_child(toast_panel)
	toast = L("", 18)
	toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	toast.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	toast_panel.add_child(toast)

func show_toast(text: String, dur: float = 3.5) -> void:
	toast.text = text
	toast_t = dur
	toast.add_theme_color_override("font_color", UiKit.MIL.lightened(0.25) if text.begins_with("⚠") else PARCH)
	toast_panel.visible = text != ""
	_place_toast.call_deferred()

func _place_toast() -> void:
	var vs := get_viewport_rect().size
	var maxw := clampf(vs.x - 2.0 * (SIDE_W + MARGIN * 3.0), 420.0, 760.0)
	var fw := toast.get_theme_font("font").get_string_size(toast.text, HORIZONTAL_ALIGNMENT_LEFT, -1, toast.get_theme_font_size("font_size")).x + 4.0
	var w := minf(fw, maxw)
	toast.autowrap_mode = TextServer.AUTOWRAP_OFF if fw <= maxw else TextServer.AUTOWRAP_WORD_SMART
	toast.custom_minimum_size = Vector2(w, 0)
	toast.size = Vector2(w, 0)
	toast_panel.size = Vector2.ZERO
	toast_panel.reset_size()
	toast_panel.position = Vector2(((vs.x - toast_panel.size.x) * 0.5), TOP_H + 14.0).floor()
	if not toast_panel.has_meta("pass2"):
		toast_panel.set_meta("pass2", true)
		(func(): toast_panel.size = Vector2.ZERO; toast_panel.reset_size(); toast_panel.remove_meta("pass2")).call_deferred()

func _build_hint() -> void:
	hint = L("", 14, Color(UiKit.DIM.r, UiKit.DIM.g, UiKit.DIM.b, 0.85))
	hint.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	hint.add_theme_constant_override("outline_size", 4)
	hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	hint.offset_left = MARGIN; hint.offset_top = -30; hint.offset_bottom = -8
	hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(hint)

## Dims the map while a window is open; clicking it closes the window (except decisions that must be made).
func _build_backdrop() -> void:
	dim = ColorRect.new()
	dim.color = Color(0.02, 0.025, 0.035, 0.5)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.visible = false
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	dim.gui_input.connect(func(ev):
		if ev is InputEventMouseButton and ev.pressed and ev.button_index == MOUSE_BUTTON_LEFT:
			close_windows())
	add_child(dim)

# ------------------------------------------------------------------ windows
## A framed window: brass-edged panel, header with title (and optional subtitle) and a close button, then a body.
## Returns [panel, body]. The header title can be changed later with _set_win_title().
func _window(w: float, h: float, wtitle: String = "", closable: bool = true) -> Array:
	var p := PanelContainer.new()
	p.theme_type_variation = "WindowPanel"
	p.custom_minimum_size = Vector2(w, h)
	p.size = Vector2(w, h)
	p.visible = false
	add_child(p)
	p.visibility_changed.connect(func():
		if p.visible:
			_center_win.call_deferred(p)
		_update_backdrop())
	p.resized.connect(func(): if p.visible: _center_win.call_deferred(p))
	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", 10)
	p.add_child(outer)
	var hdr := HBoxContainer.new()
	var tl := UiKit.title(wtitle, 28)
	var sub := L("", 15, DIM)
	sub.visible = false
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", -2)
	tv.add_child(tl); tv.add_child(sub)
	hdr.add_child(tv)
	hdr.add_child(_spacer())
	if closable:
		var cb := UiKit.button("×", func(): p.visible = false, "ghost", false, "Close (Esc)")
		cb.add_theme_font_size_override("font_size", 26)
		cb.custom_minimum_size = Vector2(40, 36)
		hdr.add_child(cb)
	outer.add_child(hdr)
	var rule := ColorRect.new(); rule.color = Color(UiKit.BRASS.r, UiKit.BRASS.g, UiKit.BRASS.b, 0.35); rule.custom_minimum_size = Vector2(0, 1)
	outer.add_child(rule)
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", 8)
	body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	outer.add_child(body)
	p.set_meta("title", tl); p.set_meta("subtitle", sub)
	return [p, body]

func _set_win_title(p: Control, t: String, subtitle: String = "") -> void:
	(p.get_meta("title") as Label).text = t
	var s: Label = p.get_meta("subtitle")
	s.text = subtitle
	s.visible = subtitle != ""

func _center_win(p: Control) -> void:
	var vs := get_viewport().get_visible_rect().size
	p.reset_size()
	p.position = ((vs - p.size) * 0.5).floor().max(Vector2(0, TOP_H + 6))

func _update_backdrop() -> void:
	if dim:
		dim.visible = any_window_open()

# ------------------------------------------------------------------ input helpers (gamepad focus, touch hit-tests, settings)
const HINTS := {
	"kbm": "Left-click select · Right-click move / attack / reinforce · Drag pan · Wheel zoom · Space pause · 1–5 speed · F1 diplomacy · F2 economy · F5/F9 save/load · Esc menu",
	"joy": "L-stick cursor · A select · X move here · LB/RB armies · D-pad ↑↓ provinces ←→ speed · Y pause · Back diplomacy · L3 economy · R3 panels · Start menu · B back",
	"touch": "Tap select · Drag pan · Pinch zoom · Twist rotate · Long-press to march, attack or reinforce with the selected army"}
var pad_cursor: Control
var _pad_focus_win: Control = null

func _update_hint() -> void:
	if hint:
		hint.text = HINTS.get(Controls.last_device, HINTS["kbm"])
	if pad_cursor:
		pad_cursor.visible = Controls.last_device == "joy"

func _build_pad_cursor() -> void:
	pad_cursor = PadCursor.new()
	pad_cursor.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pad_cursor.visible = false
	add_child(pad_cursor)

func _on_settings_changed() -> void:
	theme_res = make_theme()
	theme = theme_res

## Windows that take gamepad focus while open (topmost first).
func modal_windows() -> Array:
	return [popup, deploy_win, menu_win, inbox_win, diplo_win, econ_win]

func first_focusable(n: Node) -> Control:
	for c in n.get_children():
		if c is Control and not c.is_visible_in_tree():
			continue
		if c is BaseButton and not c.disabled and c.focus_mode != Control.FOCUS_NONE and c.theme_type_variation != "GhostButton":
			return c
		var r := first_focusable(c)
		if r != null:
			return r
	return null

func focus_first(n: Node) -> bool:
	var c := first_focusable(n)
	if c != null:
		c.grab_focus()
		return true
	return false

## Gamepad: keep focus inside the topmost open window; with no window open the stick drives the map cursor.
func _pad_focus() -> void:
	if Controls.last_device != "joy":
		return
	var fo := get_viewport().gui_get_focus_owner()
	for w in modal_windows():
		if w and w.visible:
			if fo == null or not fo.is_visible_in_tree() or not w.is_ancestor_of(fo):
				focus_first(w)
			return
	if fo != null and not fo.is_visible_in_tree():
		fo.release_focus()

func ui_has_focus() -> bool:
	var fo := get_viewport().gui_get_focus_owner()
	return fo != null and fo.is_visible_in_tree()

func focus_panels() -> void:
	## R3 / F6: jump into the selection panel (or the top bar) for gamepad navigation
	if not focus_first(sel_panel):
		focus_first(top_bar)

func close_windows() -> bool:
	var any := false
	for w in [diplo_win, econ_win, menu_win, popup, inbox_win]:
		if w and w.visible:
			w.visible = false; any = true
	return any

## True when a screen point lies on an interactive HUD element (touch taps there must not hit the map).
func is_point_over_ui(p: Vector2) -> bool:
	for c in get_children():
		if c is Control and c.visible and c.mouse_filter != Control.MOUSE_FILTER_IGNORE and c.get_global_rect().has_point(p):
			return true
	return false

## Settings rows shared by the campaign menu and the title screen.
func build_settings(box: VBoxContainer) -> void:
	Hud.build_settings_into(box, func(): refresh_game_menu.call_deferred())

static func build_settings_into(box: VBoxContainer, refresh: Callable) -> void:
	var lab := func(t: String, s: int = 16, c: Color = UiKit.TEXT) -> Label: return UiKit.label(t, maxi(s, 15), c)
	Audio.build_settings_rows(box, lab)
	var sc: float = Controls.ui_scale
	var cap := func(t: String) -> Label:
		var l := UiKit.label(t, 15); l.custom_minimum_size = Vector2(130, 0); return l
	box.add_child(UiKit.hrow([cap.call("Interface size"),
		UiKit.button("−", func(): Controls.set_setting("ui_scale", maxf(0.75, snappedf(sc - 0.125, 0.125))); refresh.call(), "", sc <= 0.75, "Smaller interface"),
		_w_static(UiKit.label("%d%%" % int(round(sc * 100)), 16), 56),
		UiKit.button("+", func(): Controls.set_setting("ui_scale", minf(2.0, snappedf(sc + 0.125, 0.125))); refresh.call(), "", sc >= 2.0, "Larger interface")]))
	var q := ["Low", "Medium", "High"]
	var qr: Array = [cap.call("Graphics quality")]
	for i in 3:
		var qi := i
		var qb := UiKit.button(q[i], func(): Controls.set_setting("quality", qi); refresh.call(), "toggle", false,
			["No anti-aliasing or sun shadows; fastest", "2× anti-aliasing and shadows (default)", "4× anti-aliasing, longer shadows and detail range"][i])
		qb.button_pressed = Controls.quality == i
		qr.append(qb)
	box.add_child(UiKit.hrow(qr))
	var tg := func(text: String, on: bool, key: String, tip: String) -> Button:
		var b := UiKit.button(text, func(): Controls.set_setting(key, not on); refresh.call(), "toggle", false, tip)
		b.button_pressed = on
		return b
	box.add_child(UiKit.hrow([cap.call("Options"),
		tg.call("Large touch targets", Controls.large_targets, "large_targets", "Bigger buttons and text for touch screens"),
		tg.call("Two-finger rotate", Controls.touch_rotate, "touch_rotate", "Twist with two fingers to rotate the map"),
		tg.call("Performance overlay (F3)", Controls.show_perf, "show_perf", "Frame-time overlay")]))

static func _w_static(c: Control, w: float) -> Control:
	c.custom_minimum_size.x = w
	return c

# ------------------------------------------------------------------ top bar
func _build_top_bar() -> void:
	top_bar = PanelContainer.new()
	top_bar.theme_type_variation = "BarPanel"
	top_bar.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top_bar.offset_bottom = TOP_H
	add_child(top_bar)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 22)
	top_bar.add_child(h)
	flag = FlagRect.new(); flag.custom_minimum_size = Vector2(45, 30)
	flag.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var nv := VBoxContainer.new(); nv.add_theme_constant_override("separation", -4)
	lbl_nation = UiKit.label("", 23, GOLD, "title")
	lbl_era = UiKit.caption("")
	nv.add_child(lbl_nation); nv.add_child(lbl_era)
	h.add_child(UiKit.hrow([flag, nv], 10))
	h.add_child(_vsep())
	lbl_funds = UiKit.label("", 19, UiKit.ECON, "semi")
	lbl_net = L("", 15)
	var tv := UiKit.stat("Treasury", lbl_funds, "Treasury, and the net change per month (income minus expenses). Details: Economy (F2).")
	tv.remove_child(lbl_funds)
	tv.add_child(UiKit.hrow([lbl_funds, lbl_net], 6))
	h.add_child(tv)
	lbl_manpower = UiKit.label("", 19, PARCH, "semi")
	h.add_child(UiKit.stat("Manpower", lbl_manpower, "Men available to raise new regiments. It grows each month with the population."))
	lbl_pop = UiKit.label("", 19, PARCH, "semi")
	h.add_child(UiKit.stat("Population", lbl_pop, "Population of all our provinces"))
	lbl_stab = UiKit.label("", 19, PARCH, "semi")
	stab_meter = UiKit.meter(0.5, UiKit.GOOD, 54, 6)
	stab_meter.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var sv := UiKit.stat("Stability", lbl_stab, "Stability: driven by citizens' needs, taxes and war exhaustion")
	sv.remove_child(lbl_stab)
	sv.add_child(UiKit.hrow([lbl_stab, stab_meter], 8))
	h.add_child(sv)
	lbl_exh = UiKit.label("", 19, PARCH, "semi")
	war_stat = UiKit.stat("War", lbl_exh, "")
	h.add_child(war_stat)
	h.add_child(_spacer())
	lbl_date = UiKit.label("", 20, PARCH, "semi")
	lbl_speed = UiKit.caption("")
	var dv := VBoxContainer.new(); dv.add_theme_constant_override("separation", -2)
	dv.add_child(lbl_speed); dv.add_child(lbl_date)
	dv.tooltip_text = "Campaign date. Space pauses; 1–5 set the speed."
	h.add_child(dv)
	var sb := HBoxContainer.new(); sb.add_theme_constant_override("separation", 3)
	sb.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var names := ["||", "1", "2", "3", "4", "5"]
	for i in names.size():
		var si := i
		var b := UiKit.button(names[i], func(): Sim.set_speed(si), "toggle", false,
			("Pause (Space)" if i == 0 else "%s (%d)" % [Sim.SPEED_NAMES[i], i]))
		b.custom_minimum_size = Vector2(36, 34)
		speed_btns.append(b)
		sb.add_child(b)
	h.add_child(sb)

func _vsep() -> VSeparator:
	var s := VSeparator.new()
	s.custom_minimum_size = Vector2(1, 36)
	return s

func _refresh_speed() -> void:
	for i in speed_btns.size():
		speed_btns[i].set_pressed_no_signal(i == Sim.speed_idx)
	if lbl_speed:
		lbl_speed.text = ("PAUSED" if Sim.speed_idx == 0 else Sim.SPEED_NAMES[Sim.speed_idx].to_upper())
		lbl_speed.add_theme_color_override("font_color", UiKit.WARN if Sim.speed_idx == 0 else DIM)

func refresh_top() -> void:
	if not Sim.nations.has(Sim.player):
		return
	var n: Dictionary = Sim.nations[Sim.player]
	flag.set_nation(Sim.player)
	lbl_nation.text = n["name"]
	lbl_era.text = GameData.eras[Sim.era]["name"].to_upper()
	var net: float = n["net"]
	lbl_funds.text = UiKit.fmt_int(n["funds"])
	lbl_funds.add_theme_color_override("font_color", UiKit.ECON if n["funds"] >= 0 else BAD)
	lbl_net.text = "%s%s/mo" % ["+" if net >= 0 else "", UiKit.fmt_int(net)]
	lbl_net.add_theme_color_override("font_color", GOOD if net >= 0 else BAD)
	lbl_manpower.text = UiKit.compact(n["manpower"])
	lbl_pop.text = UiKit.compact(Sim._pop_total(Sim.player))
	var st: float = n["stability"]
	lbl_stab.text = "%d%%" % int(st * 100)
	stab_meter.value = st
	stab_meter.add_theme_stylebox_override("fill", UiKit.box(GOOD if st > 0.6 else (UiKit.WARN if st > 0.35 else BAD), Color(0, 0, 0, 0), 0, 2, Vector4.ZERO))
	var foes := Sim.enemies_of(Sim.player)
	if foes.is_empty():
		lbl_exh.text = "At peace"
		lbl_exh.add_theme_color_override("font_color", DIM)
		war_stat.tooltip_text = "We are at peace with every nation."
	else:
		lbl_exh.text = "%d %s · %d%%" % [foes.size(), "enemy" if foes.size() == 1 else "enemies", int(n["exhaustion"] * 100)]
		lbl_exh.add_theme_color_override("font_color", BAD)
		var names: Array = []
		for c in foes:
			names.append(Sim.nations[c]["name"] + (" (undeclared)" if Sim.is_undeclared(Sim.player, c) else ""))
		war_stat.tooltip_text = "At war with: %s\nWar exhaustion %d%% (lowers stability)." % [", ".join(names), int(n["exhaustion"] * 100)]
	lbl_exh.tooltip_text = war_stat.tooltip_text
	lbl_date.text = Sim.date_string()
	_refresh_speed()
	if inbox_btn:
		var ic := Sim.inbox_counts()
		inbox_btn.text = "✉ Inbox (%d)" % ic["total"] if ic["total"] > 0 else "✉ Inbox"
		inbox_btn.add_theme_color_override("font_color", BAD if ic["urgent"] > 0 else (GOLD if ic["total"] > 0 else PARCH))
		inbox_btn.tooltip_text = "Diplomatic proposals and military reports" + ("\n%d need attention" % ic["urgent"] if ic["urgent"] > 0 else "")

# ------------------------------------------------------------------ right column: command dock, alerts, dispatches
func _build_right_column() -> void:
	right_col = VBoxContainer.new()
	right_col.add_theme_constant_override("separation", 8)
	right_col.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	right_col.offset_left = -SIDE_W - MARGIN; right_col.offset_right = -MARGIN
	right_col.offset_top = TOP_H + 10.0
	right_col.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	right_col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(right_col)
	dock = HBoxContainer.new()
	dock.alignment = BoxContainer.ALIGNMENT_END
	dock.add_theme_constant_override("separation", 6)
	dock.add_child(B("Diplomacy", func(): toggle_diplomacy(), false, "Relations, treaties, war and peace (F1)"))
	dock.add_child(B("Economy", func(): toggle_economy(), false, "Treasury, budget, provinces, procurement and armies (F2)"))
	inbox_btn = B("✉ Inbox", func(): toggle_inbox(), false, "Diplomatic proposals and military reports")
	dock.add_child(inbox_btn)
	dock.add_child(B("Menu", func(): toggle_game_menu(), false, "Save, load, settings, exit (Esc)"))
	right_col.add_child(dock)
	alerts_box = VBoxContainer.new()
	alerts_box.add_theme_constant_override("separation", 6)
	right_col.add_child(alerts_box)
	log_panel = PanelContainer.new()
	right_col.add_child(log_panel)
	var v := VBoxContainer.new(); v.add_theme_constant_override("separation", 4)
	log_panel.add_child(v)
	var collapse := UiKit.button("–", func(): pass, "ghost", false, "Collapse / expand the dispatches")
	collapse.pressed.connect(func():
		log_collapsed = not log_collapsed
		log_text.visible = not log_collapsed
		collapse.text = "+" if log_collapsed else "–")
	v.add_child(UiKit.hrow([UiKit.label("Dispatches", 18, GOLD, "title2"), _spacer(), collapse]))
	log_text = RichTextLabel.new()
	log_text.bbcode_enabled = true
	log_text.scroll_following = true
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_text.custom_minimum_size = Vector2(SIDE_W - 28.0, 210)
	v.add_child(log_text)

const LOG_COL := {"war": "#e07060", "peace": "#8fcf83", "battle": "#e2b35f", "capture": "#eaa15a", "era": "#e9cc8a",
	"diplo": "#88aee6", "economy": "#d9be78", "warning": "#ff9a52", "info": "#d8d2c4"}

func _log_event_line(ev: Dictionary) -> void:
	var col: String = LOG_COL.get(ev["kind"], "#d8d2c4")
	log_text.append_text("[color=#868b90]%s[/color]  [color=%s]%s[/color]\n" % [ev["date"], col, ev["text"]])

func _on_event(ev: Dictionary) -> void:
	if not Sim.player_relevant(ev):
		return
	_log_event_line(ev)
	if ev["kind"] in ["war", "peace", "capture"] and ev["nations"].has(Sim.player):
		show_toast(ev["text"])

func _log_line(bb: String) -> void:
	log_text.append_text("[color=#868b90]%s[/color]  %s\n" % [Sim.date_string(), bb])

## Military alert card (spotted invasion force, declarations of war): stays until dismissed or ~25 s pass.
func push_alert(head: String, text: String, focus_pid: int = -1, life: float = 25.0) -> void:
	var p := PanelContainer.new()
	p.theme_type_variation = "AlertPanel"
	var v := VBoxContainer.new(); v.add_theme_constant_override("separation", 3)
	p.add_child(v)
	var close := UiKit.button("×", func(): p.queue_free(), "ghost", false, "Dismiss")
	v.add_child(UiKit.hrow([UiKit.caption(head, UiKit.MIL.lightened(0.15)), _spacer(), close]))
	v.add_child(UiKit.para(text, SIDE_W - 44.0, 15, PARCH))
	if focus_pid > 0:
		var pid := focus_pid
		v.add_child(UiKit.hrow([_spacer(), B("Go to %s" % GameData.provinces[pid]["name"], func(): focus_world.emit(GameData.node_world(pid)); main.select_province(pid))]))
	alerts_box.add_child(p)
	alerts_box.move_child(p, 0)
	while alerts_box.get_child_count() > 3:
		var old := alerts_box.get_child(alerts_box.get_child_count() - 1)
		alerts_box.remove_child(old); old.queue_free()
	var tw := create_tween()
	tw.tween_interval(life)
	tw.tween_property(p, "modulate:a", 0.0, 0.8)
	tw.tween_callback(func(): if is_instance_valid(p): p.queue_free())

# ------------------------------------------------------------------ selection panel
func _build_sel_panel() -> void:
	sel_panel = PanelContainer.new()
	sel_panel.position = Vector2(MARGIN, TOP_H + 10.0)
	sel_panel.custom_minimum_size = Vector2(SIDE_W, 0)
	add_child(sel_panel)
	sel_scroll = ScrollContainer.new()
	sel_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sel_scroll.follow_focus = true
	sel_panel.add_child(sel_scroll)
	sel_box = VBoxContainer.new()
	sel_box.add_theme_constant_override("separation", 6)
	sel_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sel_box.custom_minimum_size = Vector2(SIDE_W - 40.0, 0)
	sel_scroll.add_child(sel_box)
	sel_panel.visible = false

## Fit the panel to its content, scrolling when it is taller than the screen allows.
func _fit_sel() -> void:
	if not is_instance_valid(sel_box):
		return
	var max_h := get_viewport_rect().size.y - TOP_H - 70.0
	var h := sel_box.get_combined_minimum_size().y
	sel_scroll.custom_minimum_size = Vector2(SIDE_W - 28.0, minf(h, max_h))
	sel_panel.reset_size()

func select_province(pid: int) -> void:
	sel_pid = pid; sel_army = -1
	refresh_selection()

func select_army(aid: int) -> void:
	sel_army = aid
	if Sim.armies.has(aid):
		sel_pid = Sim.armies[aid]["node"] if Sim.armies[aid]["node"] < GameData.SEA_NODE else -1
	refresh_selection()

# Cheap fingerprint of everything the selection panel shows; the periodic refresh only rebuilds the panel
# (≈100 ms for a large army under llvmpipe-era profiling) when this changes.
var _sel_sig := ""

func selection_signature() -> String:
	var parts: Array = [sel_army, sel_pid, Sim.era, Sim.player]
	if sel_army >= 0 and Sim.armies.has(sel_army):
		var a: Dictionary = Sim.armies[sel_army]
		parts.append_array([a["owner"], a["node"], a["state"], a["path"].size(), a["path"][-1] if a["path"].size() > 0 else -1, a.get("battle", -1)])
		for u in a["units"]:
			parts.append_array([u["type"], u["era"], int(u["men"])])
		if a["owner"] == Sim.player:
			var rc := Sim.refit_cost(a)
			parts.append_array([int(rc), Sim.nations[Sim.player]["funds"] >= rc])
			for o in Sim.armies_in(a["node"]):
				parts.append_array([o["id"], o["owner"], o["state"]])
			for bid in Sim.battles.keys():
				parts.append_array([bid, Sim.battles[bid]["done"]])
	elif sel_pid > 0 and GameData.provinces.has(sel_pid):
		var o: String = Sim.prov_owner.get(sel_pid, "")
		parts.append_array([o, money(Sim.prov_pop(sel_pid)), int(Sim.garrison(sel_pid))])
		if o != "" and o != Sim.player:
			parts.append_array([int(Sim.relation(Sim.player, o)), Sim.at_war(Sim.player, o), Sim.is_undeclared(Sim.player, o)])
			for a3 in Sim.armies.values():
				if a3["owner"] == Sim.player:
					parts.append_array([a3["id"], a3["node"], a3["state"]])
		if Sim.sieges.has(sel_pid):
			var sg: Dictionary = Sim.sieges[sel_pid]
			parts.append_array([sg["by"], snappedf(float(sg.get("progress", 0.0)) / maxf(Sim.siege_days_needed(sel_pid), 1.0), 0.003)])
		for a2 in Sim.armies_in(sel_pid):
			if not Sim.hidden_from_player(a2):
				parts.append_array([a2["id"], a2["owner"], int(Sim.army_men(a2))])
		if o == Sim.player:
			for uid in GameData.units_by_era[GameData.eras[Sim.era]["id"]]:
				var c := Sim.can_afford(Sim.player, uid)
				parts.append_array([c["ok"], int(c["cost"] + c["res_buy"])])
	return str(parts)

func refresh_selection() -> void:
	_sel_sig = selection_signature()
	clear(sel_box)
	sel_panel.visible = false
	if sel_army >= 0 and Sim.armies.has(sel_army):
		_army_panel(Sim.armies[sel_army])
		sel_panel.visible = true
	elif sel_pid > 0 and GameData.provinces.has(sel_pid):
		_province_panel(sel_pid)
		sel_panel.visible = true
	_fit_sel()
	_fit_sel.call_deferred()

func _panel_header(code: String, name_text: String, sub: String, sub_col: Color = DIM) -> void:
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", -3)
	var nl := UiKit.title(name_text, 26)
	nl.clip_text = true; nl.custom_minimum_size = Vector2(SIDE_W - 110, 0)
	tv.add_child(nl)
	tv.add_child(L(sub, 15, sub_col))
	var f := _flag(code, 45)
	f.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	sel_box.add_child(UiKit.hrow([f, tv], 12))

func _province_panel(pid: int) -> void:
	var p: Dictionary = GameData.provinces[pid]
	var o: String = Sim.prov_owner.get(pid, "")
	var owner_name: String = Sim.nations[o]["name"] if o != "" else "Unclaimed"
	var sub := "Owner: %s" % owner_name
	var sub_col := DIM
	if o == Sim.player:
		sub = "Owner: %s · our province" % owner_name
		sub_col = GOOD
	elif o != "" and Sim.at_war(Sim.player, o):
		sub = "%s · %s" % [owner_name, "UNDECLARED WAR" if Sim.is_undeclared(Sim.player, o) else "AT WAR"]
		sub_col = BAD
	_panel_header(o, p["name"], sub, sub_col)
	var chips: Array = []
	if o != "" and Sim.nations[o]["capital"] == pid:
		chips.append(UiKit.chip("Capital", GOLD))
	if o != "" and o != Sim.player:
		var rel := int(Sim.relation(Sim.player, o))
		chips.append(UiKit.chip("Relations %+d" % rel, GOOD if rel > 20 else (BAD if rel < -20 else DIM)))
		if Sim.has_treaty(Sim.player, o, "alliance"): chips.append(UiKit.chip("Ally", UiKit.DIPLO))
	if Sim.cores_of(Sim.player).has(pid) and o != Sim.player:
		chips.append(UiKit.chip("Our lost land", UiKit.WARN))
	if not chips.is_empty():
		sel_box.add_child(UiKit.hrow(chips, 6))
	var g := _grid(4)
	_kv(g, "Terrain", p["terrain"].capitalize())
	_kv(g, "Resource", p["resource"].capitalize(), UiKit.ECON)
	_kv(g, "Population", UiKit.compact(Sim.prov_pop(pid)))
	_kv(g, "Garrison", UiKit.fmt_int(Sim.garrison(pid)))
	sel_box.add_child(g)
	if Sim.sieges.has(pid):
		var s: Dictionary = Sim.sieges[pid]
		var prog := float(s.get("progress", 0.0)) / maxf(Sim.siege_days_needed(pid), 1.0)
		sel_box.add_child(UiKit.hrow([L("Under siege by %s" % Sim.nations[s["by"]]["name"], 15, BAD), _spacer(), L("%d%%" % int(clampf(prog, 0, 1) * 100), 15, BAD)]))
		sel_box.add_child(UiKit.meter(prog, BAD, SIDE_W - 40.0))
	var here := Sim.armies_in(pid).filter(func(x): return not Sim.hidden_from_player(x))
	if not here.is_empty():
		sel_box.add_child(UiKit.section("Armies here"))
		for a in here:
			var aid: int = a["id"]
			var b := B("%s — %s · %s men" % [Sim.nations[a["owner"]]["name"], a["name"], UiKit.fmt_int(Sim.army_men(a))], func(): main.select_army(aid), false, "Select this army")
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			if a["owner"] != Sim.player and Sim.at_war(Sim.player, a["owner"]):
				b.add_theme_color_override("font_color", BAD)
			sel_box.add_child(b)
	if o == Sim.player:
		sel_box.add_child(UiKit.section("Raise regiments here", UiKit.ECON))
		_procure_buttons(sel_box, pid)
	elif o != "":
		_invade_buttons(pid, o)
		var db := B("Diplomacy with %s" % owner_name, func(): open_diplomacy(o), false, "Relations, treaties, war and peace")
		sel_box.add_child(db)

## Offensive orders from a foreign province's panel: one button per available army (nearest first).
func _invade_buttons(pid: int, o: String) -> void:
	if Sim.has_treaty(Sim.player, o, "alliance") or Sim.defeated:
		return
	var mine: Array = Sim.armies.values().filter(func(x): return x["owner"] == Sim.player and x["state"] != "battle")
	if mine.is_empty():
		return
	mine.sort_custom(func(x, y): return GameData.node_km(x["node"], pid) < GameData.node_km(y["node"], pid))
	var hostile := Sim.at_war(Sim.player, o)
	var verb := "Retake" if Sim.cores_of(Sim.player).has(pid) else ("Attack" if hostile else "Invade")
	sel_box.add_child(UiKit.section("Military orders", BAD))
	if not hostile:
		sel_box.add_child(L("No declaration of war needed — you will be asked how to proceed.", 14, DIM))
	for a in mine.slice(0, 3):
		var aid: int = a["id"]
		var r := Sim.order_invade(aid, pid, true)
		var txt := "%s with %s (%s men)" % [verb, a["name"], UiKit.compact(Sim.army_men(a))]
		if r["ok"]:
			txt += " · ~%d days" % int(r["days"])
		var b := B(txt, func(): main.command_army(aid, pid), not r["ok"],
			("March %s on %s, about %d days away." % [a["name"], GameData.provinces[pid]["name"], int(r["days"])]) if r["ok"] else r["msg"], "order")
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		sel_box.add_child(b)
		if not r["ok"]:
			sel_box.add_child(UiKit.para(r["msg"], SIDE_W - 48.0, 14, DIM))

## Ask before an undeclared invasion (from right-click, long-press or the panel). Returns the dry-run result.
func confirm_invade(aid: int, pid: int) -> Dictionary:
	var r := Sim.order_invade(aid, pid, true)
	if not r["ok"]:
		show_toast(r["msg"], 4.0)
		return r
	var a: Dictionary = Sim.armies[aid]
	var o: String = r["target"]
	var nm: String = Sim.nations[o]["name"]
	var body := "[b]%s[/b] (%s men) will march on [b]%s[/b], about [b]%d days[/b] away.\n\n" % [a["name"], UiKit.fmt_int(Sim.army_men(a)), GameData.provinces[pid]["name"], int(r["days"])]
	body += "[color=#e2b35f][b]Invade without declaring war[/b][/color] — fighting starts when we cross the border. %s will defend itself, but its allies are not called in. Relations with %s collapse and other great powers will trust us less." % [nm, nm]
	if Sim.has_treaty(Sim.player, o, "nap"):
		body += " [color=#e07060]This breaks our non-aggression pact (stability −12%).[/color]"
	var allies := Sim.allies_of(o)
	if not allies.is_empty():
		var names: Array = []
		for x in allies:
			names.append(Sim.nations[x]["name"])
		body += "\n\n[color=#e07060][b]Declare war and invade[/b][/color] — a formal war: %s's allies (%s) will join against us." % [nm, ", ".join(names)]
	else:
		body += "\n\n[color=#e07060][b]Declare war and invade[/b][/color] — a formal war; %s has no allies to call." % nm
	var chk := Sim.can_declare_war(Sim.player, o)
	var buttons: Array = [["Cancel", func(): pass]]
	if chk["ok"]:
		buttons.append(["Declare war & invade", func(): _do_invade(aid, pid, true), "danger"])
	buttons.append(["Invade (undeclared)", func(): _do_invade(aid, pid, false), "order"])
	show_popup("Invade %s?" % nm, body, buttons)
	return r

func _do_invade(aid: int, pid: int, declare: bool) -> void:
	var o: String = Sim.prov_owner.get(pid, "")
	if declare and o != "":
		if Sim.declare_war(Sim.player, o):
			main.map.lut_dirty = true
	var r := Sim.order_invade(aid, pid)
	show_toast(("Invading %s: %s marches on %s (~%d days)" % [Sim.nations[o]["name"], Sim.armies[aid]["name"], GameData.provinces[pid]["name"], int(r["days"])]) if r["ok"] else r["msg"], 4.0)
	main.select_army(aid)

## Campaign lost: no land and no army left. Offers a reload or a new campaign instead of a dead map.
func show_defeat(by: String) -> void:
	for w in [diplo_win, econ_win, menu_win, deploy_win]:
		if w: w.visible = false
	var who: String = Sim.nations[by]["name"] if Sim.nations.has(by) else "our enemies"
	var body := "%s has lost its last province and its last army. The realm has fallen to %s on %s.\n\nThe campaign is over." % [Sim.nations[Sim.player]["name"], who, Sim.date_string()]
	var buttons: Array = []
	if FileAccess.file_exists(Sim.save_path("quicksave")):
		buttons.append(["Load quicksave", func(): main.load_slot("quicksave")])
	buttons.append(["Return to title", func(): main.return_to_title(), "primary"])
	buttons.append(["Quit", func(): get_tree().quit()])
	show_popup("DEFEAT", body, buttons, false)

func _unit_tip(uid: String, c: Dictionary) -> String:
	var d: Dictionary = GameData.units[uid]
	var res_txt := ""
	for r in d["resources"].keys():
		res_txt += " %s ×%d" % [r, d["resources"][r]]
	var why := ""
	if not c["ok"]:
		why = "\n\nCannot raise: " + ("not enough funds (need %d, have %d)" % [int(c["cost"] + c["res_buy"]), int(Sim.nations[Sim.player]["funds"])] if not c["funds_ok"] else "not enough manpower (need %d)" % int(d["men"]))
	return "%s — %s\n%d men · cost %d%s · upkeep %.1f/month\nMelee %d · Defence %d · Range %d m · Armour %d%%\nNeeds:%s%s" % [d["name"], d["role"], d["men"], d["cost"],
		(" (+%d to import resources)" % int(c["res_buy"])) if c["res_buy"] > 0 else "", d["upkeep"], d["melee"], d["defense"], d["range"], int(float(d["armor"]) * 100.0), res_txt if res_txt != "" else " —", why]

func _procure_buttons(box: Container, pid: int) -> void:
	var era_id: String = GameData.eras[Sim.era]["id"]
	if Sim.sieges.has(pid):
		box.add_child(L("No recruiting while the province is under siege.", 14, BAD))
		return
	var g := GridContainer.new(); g.columns = 2
	g.add_theme_constant_override("h_separation", 6); g.add_theme_constant_override("v_separation", 6)
	for uid in GameData.units_by_era[era_id]:
		var d: Dictionary = GameData.units[uid]
		var c := Sim.can_afford(Sim.player, uid)
		var id: String = uid
		var b := B("%s  ·  %d" % [d["name"], int(c["cost"] + c["res_buy"])], func(): _buy(id, pid), not c["ok"], _unit_tip(uid, c))
		b.custom_minimum_size = Vector2((SIDE_W - 50.0) * 0.5, 0)
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		g.add_child(b)
	box.add_child(g)
	box.add_child(L("Regiments join an idle army here, or form a new one.", 14, DIM))

func _buy(uid: String, pid: int) -> void:
	var r := Sim.buy_unit(Sim.player, uid, pid)
	if r["ok"]:
		show_toast("%s raised in %s (−%d)" % [GameData.units[uid]["name"], GameData.provinces[pid]["name"], int(r["cost"])])
	else:
		show_toast(r["msg"])
	refresh_selection()
	if econ_win.visible:
		refresh_econ()

## Current order of an army, as [verb, place, colour, detail].
func _army_status(a: Dictionary) -> Array:
	if a.get("reinforce", -1) >= 0 and Sim.battles.has(a["reinforce"]):
		return ["Reinforcing", "Battle of " + GameData.provinces[Sim.battles[a["reinforce"]]["prov"]]["name"], UiKit.WARN, "~%d days" % Sim.est_days(a, a["path"])]
	if a["state"] == "battle":
		return ["In battle", GameData.provinces[a["node"]]["name"] if a["node"] < GameData.SEA_NODE else "at sea", BAD, ""]
	if a["path"].size() > 0:
		var dest: int = a["path"][-1]
		var verb := "Marching to"
		var col := PARCH
		var dest_o: String = Sim.prov_owner.get(dest, "")
		if a.get("invade", "") != "" and not Sim.at_war(a["owner"], a["invade"]):
			verb = "Invading"; col = BAD
		elif dest_o != "" and Sim.at_war(a["owner"], dest_o):
			verb = "Attacking"; col = BAD
		return [verb, GameData.provinces[dest]["name"] if GameData.provinces.has(dest) else "sea", col, "~%d days · %d stops" % [Sim.est_days(a, a["path"]), a["path"].size()]]
	if a["state"] == "siege" and Sim.sieges.has(a["node"]):
		return ["Besieging", GameData.provinces[a["node"]]["name"], UiKit.WARN, "%d%%" % int(minf(float(Sim.sieges[a["node"]]["progress"]), 1.0) * 100)]
	return ["Holding", GameData.provinces[a["node"]]["name"] if a["node"] < GameData.SEA_NODE else "at sea", DIM, "awaiting orders"]

func _army_panel(a: Dictionary) -> void:
	var mine: bool = a["owner"] == Sim.player
	var men := Sim.army_men(a)
	var mx := 0.0
	for u in a["units"]:
		mx += u["max"]
	_panel_header(a["owner"], a["name"], "%s · %s men · %d regiments" % [Sim.nations[a["owner"]]["name"], UiKit.fmt_int(men), a["units"].size()])
	var ready := men / maxf(mx, 1.0)
	sel_box.add_child(UiKit.hrow([UiKit.caption("Strength"), UiKit.meter(ready, GOOD if ready > 0.66 else (UiKit.WARN if ready > 0.4 else BAD), SIDE_W - 160.0, 8), L("%d%%" % int(ready * 100), 15, DIM)], 10))
	var st := _army_status(a)
	var g := _grid(2)
	_kv(g, "Order", "%s %s" % [st[0], st[1]], st[2])
	if st[3] != "":
		_kv(g, "Detail", st[3], DIM)
	sel_box.add_child(g)
	sel_box.add_child(UiKit.section("Regiments"))
	var era_id: String = GameData.eras[Sim.era]["id"]
	for i in a["units"].size():
		var u: Dictionary = a["units"][i]
		var d: Dictionary = GameData.units[u["type"]]
		var old: bool = u["era"] != era_id
		var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 8)
		var nl := L("%s%s" % [d["name"], " (old kit)" if old else ""], 15, UiKit.WARN if old else PARCH)
		nl.custom_minimum_size = Vector2(150, 0); nl.clip_text = true
		nl.tooltip_text = "%s · %s · %d / %d men" % [d["name"], d["role"], int(u["men"]), int(u["max"])] + ("\nOutdated equipment: refit to the current era." if old else "")
		nl.mouse_filter = Control.MOUSE_FILTER_PASS
		h.add_child(nl)
		var fr: float = u["men"] / u["max"]
		var m := UiKit.meter(fr, GOOD if fr > 0.5 else BAD, 96, 7)
		m.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		h.add_child(m)
		h.add_child(_w(L(UiKit.fmt_int(u["men"]), 15, DIM), 52))
		if mine:
			var idx = i; var aid: int = a["id"]; var uname: String = d["name"]
			var db := UiKit.button("×", func(): confirm("Disband regiment?", "Disband [b]%s[/b] (%s men)? Half the men return to the manpower pool; the rest go home. This cannot be undone." % [uname, UiKit.fmt_int(u["men"])],
				"Disband", func(): Sim.disband_unit(aid, idx); refresh_selection()), "ghost", false, "Disband this regiment (asks first)")
			h.add_child(db)
		sel_box.add_child(h)
	if mine:
		var aid2: int = a["id"]
		var acts: Array = []
		var rc := Sim.refit_cost(a)
		if rc > 0:
			var poor: bool = Sim.nations[Sim.player]["funds"] < rc
			acts.append(B("Refit to %s (%d)" % [UiKit.ERA_INFO.get(era_id, {}).get("short", GameData.eras[Sim.era]["name"]), int(rc)], func(): _refit(aid2), poor,
				("Not enough funds: refit costs %d, treasury %d." % [int(rc), int(Sim.nations[Sim.player]["funds"])]) if poor else "Re-equip outdated regiments with current-era kit (keeps their strength)."))
		for o in Sim.armies_in(a["node"]):
			if o["id"] != a["id"] and o["owner"] == Sim.player and o["state"] != "battle":
				var oid: int = o["id"]
				acts.append(B("Merge %s into this army" % o["name"], func(): Sim.merge_armies(aid2, oid); refresh_selection(), false, "Combine the two armies in this province"))
		if not acts.is_empty():
			sel_box.add_child(UiKit.section("Actions"))
			for b in acts:
				sel_box.add_child(b)
		_reinforce_buttons(a)
		sel_box.add_child(L("Right-click: move · attack · reinforce", 14, DIM))
	if a["state"] == "battle" and Sim.battles.has(a["battle"]):
		var bid: int = a["battle"]
		sel_box.add_child(B("Watch this battle", func(): main.watch_battle(bid), false, "Open the 3D battle (the outcome does not change)", "primary"))

## v0.5: battles of ours (or an ally's) this army can still reach — march in directly, round a flank, or in support.
func _reinforce_buttons(a: Dictionary) -> void:
	if a["state"] == "battle":
		return
	var opts: Array = []
	for bid in Sim.battles.keys():
		var b: Dictionary = Sim.battles[bid]
		if b["done"] or Sim._reinforce_side(Sim.player, b) < 0:
			continue
		var r := Sim.order_reinforce(a["id"], bid, "direct", true)
		if r["ok"] and r["days"] <= 10:
			opts.append([r["days"], bid])
	opts.sort_custom(func(x, y): return x[0] < y[0])
	for o in opts.slice(0, 2):
		var bid: int = o[1]
		var aid: int = a["id"]
		var bn: String = GameData.provinces[Sim.battles[bid]["prov"]]["name"]
		sel_box.add_child(UiKit.section("Battle of %s" % bn, UiKit.WARN))
		sel_box.add_child(L("Under way · about %d days' march — it may end before we arrive." % int(o[0]), 14, DIM))
		var rb := B("Reinforce", func(): _reinforce(aid, bid, "direct"), false, "March straight in and join the fight from the direction we arrive", "order")
		var fb := B("Flank", func(): _reinforce(aid, bid, "flank"), false, "Swing round and enter on a flank of the enemy line", "order")
		var sb := B("Support", func(): _reinforce(aid, bid, "support"), false, "Form up behind our own line and hold it", "order")
		for x in [rb, fb, sb]:
			x.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		sel_box.add_child(UiKit.hrow([rb, fb, sb], 6))

func _reinforce(aid: int, bid: int, mode: String) -> void:
	var r := Sim.order_reinforce(aid, bid, mode)
	show_toast(("Reinforcing the battle of %s (~%d days)" % [GameData.provinces[Sim.battles[bid]["prov"]]["name"], int(r["days"])]) if r["ok"] else r["msg"], 3.0)
	refresh_selection()

func _refit(aid: int) -> void:
	var r := Sim.refit_army(aid)
	show_toast("Refitted %d units (−%d)" % [r["changed"], int(r["cost"])] if r["ok"] else r["msg"])
	refresh_selection()

# ------------------------------------------------------------------ game menu (save / load / settings / exit)
var menu_win: PanelContainer
var menu_box: VBoxContainer

func _build_game_menu() -> void:
	var w := _window(640, 300, "Campaign")
	menu_win = w[0]
	menu_box = w[1]

func toggle_game_menu() -> void:
	menu_win.visible = not menu_win.visible
	if menu_win.visible:
		refresh_game_menu()

func refresh_game_menu() -> void:
	clear(menu_box)
	_set_win_title(menu_win, "Campaign", "%s · %s · %s" % [Sim.nations[Sim.player]["name"], Sim.date_string(), GameData.eras[Sim.era]["name"]])
	menu_box.add_child(UiKit.section("Save"))
	var has_qs := FileAccess.file_exists(Sim.save_path("quicksave"))
	menu_box.add_child(row([B("Quick save (F5)", func(): main.save_slot("quicksave"); refresh_game_menu(), false, "", "primary"),
		B("Quick load (F9)", func(): confirm("Load the quicksave?", "Progress since the quicksave will be lost.", "Load", func(): menu_win.visible = false; main.load_slot("quicksave"), "primary"),
			not has_qs, "" if has_qs else "No quicksave yet — press F5 to make one"),
		B("Save to new slot", func(): main.save_slot("%s_%d" % [Sim.player, Time.get_unix_time_from_system()]); refresh_game_menu(), false, "Keep a separate save you can return to")]))
	menu_box.add_child(UiKit.section("Saved campaigns"))
	var saves := Sim.list_saves()
	if saves.is_empty():
		menu_box.add_child(L("No saves yet.", 15, DIM))
	var sc := ScrollContainer.new(); sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	var lst := VBoxContainer.new(); lst.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(lst)
	for m in saves.slice(0, 12):
		lst.add_child(_save_row(m, func(slot: String): confirm("Load %s?" % slot, "Unsaved progress in this campaign will be lost.", "Load", func(): menu_win.visible = false; main.load_slot(slot), "primary")))
	sc.custom_minimum_size = Vector2(600, minf(saves.slice(0, 12).size() * 44.0, 220.0))
	menu_box.add_child(sc)
	menu_box.add_child(UiKit.section("Settings"))
	build_settings(menu_box)
	menu_box.add_child(HSeparator.new())
	menu_box.add_child(row([_spacer(),
		B("Return to title", func(): confirm("Return to the title screen?", "Unsaved progress will be lost.", "Return to title", func(): main.return_to_title())),
		B("Quit to desktop", func(): confirm("Quit Iron Crowns?", "Unsaved progress will be lost.", "Quit", func(): get_tree().quit()), false, "", "danger")]))

## One saved campaign: flag, slot, nation and date, era, when it was saved, and a Load button.
static func _save_row(m: Dictionary, on_load: Callable) -> Control:
	var slot: String = m["slot"]
	var when := Time.get_datetime_string_from_unix_time(int(m["saved_unix"]) + int(Time.get_time_zone_from_system()["bias"]) * 60, true)
	var f := FlagRect.new(); f.custom_minimum_size = Vector2(30, 20)
	var code: String = m.get("player", "")
	if code != "": f.set_nation_static(code)
	f.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", -3)
	tv.add_child(UiKit.label("%s — %s" % [m["nation"], m["date"]], 16))
	tv.add_child(UiKit.label("%s · %s · saved %s" % [slot, m["era"], when], 14, UiKit.DIM))
	tv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var lb := UiKit.button("Load", func(): on_load.call(slot), "", false, "Load this campaign")
	return UiKit.hrow([f, tv, lb], 10)

func on_game_loaded() -> void:
	for w in [diplo_win, econ_win, popup, menu_win, deploy_win, inbox_win]:
		if w: w.visible = false
	log_text.clear()
	var evs: Array = Sim.event_log.filter(func(e): return Sim.player_relevant(e))
	for ev in evs.slice(maxi(0, evs.size() - 40)):
		_log_event_line(ev)
	for c in alerts_box.get_children():
		c.queue_free()
	sel_pid = -1; sel_army = -1
	refresh_top()

# ------------------------------------------------------------------ diplomacy
func _build_diplo() -> void:
	var w := _window(1120, 680, "Diplomacy")
	diplo_win = w[0]
	var v: VBoxContainer = w[1]
	var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 16)
	h.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(h)
	var sc := ScrollContainer.new(); sc.custom_minimum_size = Vector2(360, 590); sc.follow_focus = true
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	h.add_child(sc)
	diplo_list = VBoxContainer.new(); diplo_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	diplo_list.add_theme_constant_override("separation", 3)
	sc.add_child(diplo_list)
	h.add_child(VSeparator.new())
	var sc2 := ScrollContainer.new(); sc2.follow_focus = true; sc2.size_flags_horizontal = Control.SIZE_EXPAND_FILL; sc2.custom_minimum_size = Vector2(700, 590)
	sc2.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	h.add_child(sc2)
	diplo_detail = VBoxContainer.new(); diplo_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	diplo_detail.add_theme_constant_override("separation", 8)
	sc2.add_child(diplo_detail)

func toggle_diplomacy() -> void:
	if diplo_win.visible:
		diplo_win.visible = false
	else:
		open_diplomacy(diplo_target)

func open_diplomacy(code: String) -> void:
	econ_win.visible = false
	if inbox_win: inbox_win.visible = false
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
	if Sim.at_war(me, c): t.append("UNDECLARED WAR" if Sim.is_undeclared(me, c) else "WAR")
	if Sim.has_treaty(me, c, "alliance"): t.append("Ally")
	if Sim.has_treaty(me, c, "trade"): t.append("Trade")
	if Sim.has_treaty(me, c, "nap"): t.append("NAP")
	if Sim.has_treaty(me, c, "truce"): t.append("Truce")
	return ", ".join(t)

func _status_chips(c: String) -> Array:
	var me := Sim.player
	var out: Array = []
	if Sim.at_war(me, c): out.append(UiKit.chip("Undeclared war" if Sim.is_undeclared(me, c) else "War", BAD))
	if Sim.has_treaty(me, c, "alliance"): out.append(UiKit.chip("Ally", UiKit.DIPLO))
	if Sim.has_treaty(me, c, "trade"): out.append(UiKit.chip("Trade", UiKit.ECON))
	if Sim.has_treaty(me, c, "nap"): out.append(UiKit.chip("NAP", Color(0.5, 0.78, 0.74)))
	if Sim.has_treaty(me, c, "truce"): out.append(UiKit.chip("Truce", DIM))
	return out

func refresh_diplo() -> void:
	clear(diplo_list)
	var me := Sim.player
	var nb := Sim.neighbors_of(me)
	diplo_list.add_child(UiKit.caption("At war · neighbours · great powers"))
	for c in _diplo_candidates():
		var n: Dictionary = Sim.nations[c]
		var b := Button.new()
		b.theme_type_variation = "ToggleButton"
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		var rel := int(Sim.relation(me, c))
		var tags := _status_tags(c)
		b.text = "%s%s   %+d%s" % [n["name"], " ◆" if nb.has(c) else "", rel, ("  · " + tags) if tags != "" else ""]
		b.tooltip_text = "%s · relations %+d%s%s" % [n["name"], rel, " · neighbour" if nb.has(c) else "", ("\n" + tags) if tags != "" else ""]
		b.toggle_mode = true
		b.clip_text = true
		b.button_pressed = c == diplo_target
		b.add_theme_color_override("font_color", BAD if Sim.at_war(me, c) else (GOOD if rel > 25 else PARCH))
		var code: String = c
		b.pressed.connect(func(): diplo_target = code; refresh_diplo())
		var f := _flag(c, 30); f.size_flags_vertical = Control.SIZE_SHRINK_CENTER
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
	var rel := Sim.relation(me, c)
	var attitude := "Hostile" if rel < -30 else ("Unfriendly" if rel < -5 else ("Indifferent" if rel < 15 else ("Friendly" if rel < 45 else "Very friendly")))
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", 0)
	tv.add_child(UiKit.title(n["name"], 32))
	tv.add_child(L("%s · %s · %d provinces" % ["Great power" if n["major"] else "Minor state", n["continent"], Sim.nation_provs[c].size()], 16, DIM))
	var f := _flag(c, 72); f.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	diplo_detail.add_child(UiKit.hrow([f, tv], 14))
	var chips := _status_chips(c)
	chips.push_front(UiKit.chip("Relations %+d · %s" % [int(rel), attitude], GOOD if rel > 20 else (BAD if rel < -20 else DIM)))
	diplo_detail.add_child(UiKit.hrow(chips, 6))
	var sa := Sim.strength(me); var sb := Sim.strength(c)
	var g := _grid(6)
	_kv(g, "Their army", "%.1f× ours" % (sb / maxf(sa, 1.0)), BAD if sb > sa * 1.3 else (GOOD if sb < sa * 0.7 else PARCH))
	_kv(g, "Treasury", UiKit.compact(n["funds"]), UiKit.ECON)
	_kv(g, "Stability", "%d%%" % int(n["stability"] * 100))
	diplo_detail.add_child(g)
	if Sim.at_war(me, c):
		diplo_detail.add_child(L("War score %+.0f · our war exhaustion %d%%" % [Sim.war_score(me, c), int(Sim.nations[me]["exhaustion"] * 100)], 16, BAD))
	var allies := Sim.allies_of(c)
	if not allies.is_empty():
		var names: Array = []
		for x in allies:
			names.append(Sim.nations[x]["name"])
		diplo_detail.add_child(UiKit.para("Allies who would defend them in a declared war: " + ", ".join(names), 680, 15, UiKit.WARN))
	diplo_detail.add_child(UiKit.section("Proposals — how %s would answer" % n["name"], UiKit.DIPLO))
	var kinds := []
	if Sim.at_war(me, c):
		kinds = ["peace"]
	else:
		kinds = ["trade", "nap", "alliance"]
	for k in kinds:
		var ev := Sim.evaluate(me, c, k)
		var applicable: bool = ev["score"] > -900
		var card := PanelContainer.new(); card.theme_type_variation = "CardPanel"
		var box := VBoxContainer.new(); card.add_child(box)
		var ok: bool = ev["score"] > 0
		var kn: String = {"trade": "Trade agreement", "nap": "Non-aggression pact (10 years)", "alliance": "Defensive alliance", "peace": "White peace (5-year truce)"}[k]
		var verdict := ("Would accept (%+d)" % int(ev["score"])) if ok else ("Would refuse (%+d)" % int(ev["score"]))
		if not applicable:
			verdict = ev["breakdown"][0][0]
		var kind: String = k
		var pb := B("Propose", func(): _propose(kind), not applicable, ("Offer a %s to %s" % [Sim._kind_name(kind), n["name"]]) if applicable else verdict, "primary" if ok and applicable else "")
		box.add_child(row([L(kn, 17), _spacer(), L(verdict, 16, GOOD if ok else (DIM if not applicable else BAD)), pb]))
		if applicable:
			var gg := _grid(2)
			gg.add_theme_constant_override("h_separation", 30)
			for it in ev["breakdown"]:
				gg.add_child(L(str(it[0]), 15, DIM))
				var v := int(it[1])
				gg.add_child(L("%+d" % v, 15, GOOD if v > 0 else (BAD if v < 0 else DIM)))
			box.add_child(gg)
		diplo_detail.add_child(card)
	diplo_detail.add_child(UiKit.section("Actions"))
	var acts := HFlowContainer.new(); acts.add_theme_constant_override("h_separation", 8); acts.add_theme_constant_override("v_separation", 6)
	for k2 in ["trade", "nap", "alliance"]:
		if Sim.has_treaty(me, c, k2):
			var kk: String = k2
			acts.add_child(B("Cancel %s" % Sim._kind_name(k2), func(): confirm("Cancel the %s?" % Sim._kind_name(kk), "Relations with %s drop by 15." % n["name"], "Cancel treaty", func(): Sim.cancel_treaty(me, c, kk); refresh_diplo()), false, "Relations −15"))
	var inc: float = maxf(Sim.nations[me]["income"].get("total", 50.0), 10.0)
	var amt := snappedf(inc * 0.5, 10.0)
	var poor: bool = Sim.nations[me]["funds"] < amt
	acts.add_child(B("Send a gift of %d" % int(amt), func(): if Sim.gift(me, c, amt): refresh_diplo(), poor, ("Not enough funds (treasury %d)" % int(Sim.nations[me]["funds"])) if poor else "Improves relations"))
	if not Sim.at_war(me, c) or Sim.is_undeclared(me, c):
		var chk := Sim.can_declare_war(me, c)
		var warn := ""
		if Sim.has_treaty(me, c, "nap"):
			warn = " (breaks our pact)"
		var label := "Formally declare war (their allies join)" if Sim.is_undeclared(me, c) else "Declare war%s" % warn
		acts.add_child(B(label, func(): _confirm_declare(c), not chk["ok"], chk["msg"] if not chk["ok"] else "Asks for confirmation first", "danger"))
	diplo_detail.add_child(acts)
	if not Sim.at_war(me, c):
		diplo_detail.add_child(L("Tip: you can also invade without declaring war — select an army and right-click their land.", 14, DIM))

func _confirm_declare(c: String) -> void:
	var n: Dictionary = Sim.nations[c]
	var body := "A formal declaration of war on [b]%s[/b]." % n["name"]
	var allies := Sim.allies_of(c)
	if not allies.is_empty():
		var names: Array = []
		for x in allies: names.append(Sim.nations[x]["name"])
		body += "\n\n[color=#e07060]Their allies will join the war: %s.[/color]" % ", ".join(names)
	if Sim.has_treaty(Sim.player, c, "nap"):
		body += "\n\n[color=#e07060]This breaks our non-aggression pact: stability −12% and other powers will think less of us.[/color]"
	body += "\n\nRelations with %s fall sharply and trade between us ends." % n["name"]
	confirm("Declare war on %s?" % n["name"], body, "Declare war", func(): _declare(c))

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
	var w := _window(1120, 680, "Economy & Army")
	econ_win = w[0]
	var v: VBoxContainer = w[1]
	var sc := ScrollContainer.new(); sc.follow_focus = true; sc.size_flags_vertical = Control.SIZE_EXPAND_FILL; sc.custom_minimum_size = Vector2(1080, 590)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(sc)
	econ_box = VBoxContainer.new(); econ_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	econ_box.add_theme_constant_override("separation", 10)
	sc.add_child(econ_box)

func toggle_economy() -> void:
	diplo_win.visible = false
	if inbox_win: inbox_win.visible = false
	econ_win.visible = not econ_win.visible
	if econ_win.visible:
		refresh_econ()

func _card(title_text: String, col: Color = GOLD, w: float = 0.0) -> Array:
	var p := PanelContainer.new(); p.theme_type_variation = "CardPanel"
	if w > 0.0: p.custom_minimum_size.x = w
	p.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var v := VBoxContainer.new(); v.add_theme_constant_override("separation", 4)
	p.add_child(v)
	v.add_child(UiKit.label(title_text, 18, col, "title2"))
	return [p, v]

func _ledger(v: VBoxContainer, items: Dictionary, sign: String, col: Color, highlight: String = "") -> void:
	var g := _grid(2)
	g.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for k in items.keys():
		if k == "total":
			continue
		var kl := L(k, 15, PARCH if k != highlight else UiKit.WARN)
		kl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		g.add_child(kl)
		var vl := L("%s%s" % [sign, UiKit.fmt_int(items[k])], 15, col)
		vl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		g.add_child(vl)
	var tl := L("Total", 16, GOLD); tl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	g.add_child(tl)
	var tv := L(UiKit.fmt_int(items.get("total", 0.0)), 16, GOLD); tv.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	g.add_child(tv)
	v.add_child(g)

func refresh_econ() -> void:
	clear(econ_box)
	var me := Sim.player
	var n: Dictionary = Sim.nations[me]
	_set_win_title(econ_win, "Economy & Army", "%s · %s" % [n["name"], Sim.date_string()])
	# --- row 1: treasury, income, expenses, people
	var r1 := HBoxContainer.new(); r1.add_theme_constant_override("separation", 10)
	econ_box.add_child(r1)
	var tc := _card("Treasury", UiKit.ECON)
	var tl := UiKit.label(UiKit.fmt_int(n["funds"]), 34, UiKit.ECON if n["funds"] >= 0 else BAD, "semi")
	tc[1].add_child(tl)
	tc[1].add_child(L("%s%s per month" % ["+" if n["net"] >= 0 else "", UiKit.fmt_int(n["net"])], 17, GOOD if n["net"] >= 0 else BAD))
	var inc_t: float = n["income"].get("total", 0.0); var exp_t: float = n["expense"].get("total", 0.0)
	tc[1].add_child(UiKit.caption("Income vs expenses"))
	tc[1].add_child(UiKit.meter(inc_t / maxf(inc_t + exp_t, 1.0), GOOD, 200, 8))
	if n["funds"] < 0:
		tc[1].add_child(UiKit.para("In debt: interest is charged monthly, and deep debt makes unpaid soldiers desert.", 220, 14, BAD))
	r1.add_child(tc[0])
	var ic := _card("Monthly income", GOOD)
	_ledger(ic[1], n["income"], "+", GOOD)
	r1.add_child(ic[0])
	var ec := _card("Monthly expenses", BAD)
	_ledger(ec[1], n["expense"], "−", BAD, "Army upkeep")
	r1.add_child(ec[0])
	var pc := _card("People", PARCH)
	var pg := _grid(2)
	_kv(pg, "Population", UiKit.fmt_int(Sim._pop_total(me)))
	_kv(pg, "Provinces", str(Sim.nation_provs[me].size()))
	_kv(pg, "Manpower", UiKit.fmt_int(n["manpower"]))
	pc[1].add_child(pg)
	for k in ["food", "goods", "security"]:
		var nv: float = n["needs"][k]
		pc[1].add_child(UiKit.hrow([_w(L(k.capitalize(), 15), 76), UiKit.meter(nv, GOOD if nv > 0.6 else (UiKit.WARN if nv > 0.35 else BAD), 120, 8), L("%d%%" % int(nv * 100), 14, DIM)]))
	pc[1].add_child(UiKit.hrow([_w(L("Stability", 15), 76), UiKit.meter(n["stability"], GOLD, 120, 8), L("%d%%" % int(n["stability"] * 100), 14, DIM)]))
	r1.add_child(pc[0])
	# --- row 2: policy and stockpile
	var r2 := HBoxContainer.new(); r2.add_theme_constant_override("separation", 10)
	econ_box.add_child(r2)
	var polc := _card("Policy")
	var th := HBoxContainer.new(); th.add_theme_constant_override("separation", 6)
	th.add_child(_w(L("Taxes", 15), 70))
	var tnames := ["Low", "Normal", "High"]
	var ttips := ["Less income, stability rises", "Balanced", "More income, stability falls"]
	for i in 3:
		var lvl := i
		var b := B(tnames[i], func(): Sim.set_tax(me, lvl); refresh_econ(); refresh_top(), false, ttips[i], "toggle")
		b.button_pressed = n["tax"] == i
		th.add_child(b)
	polc[1].add_child(th)
	var sl := HSlider.new(); sl.min_value = 0; sl.max_value = 1; sl.step = 0.05; sl.value = n["welfare"]; sl.custom_minimum_size = Vector2(200, 24)
	sl.tooltip_text = "Welfare spending raises citizens' needs (and stability) at the cost of income"
	var wl := L("%d%%" % int(n["welfare"] * 100), 15)
	sl.value_changed.connect(func(v): Sim.set_welfare(me, v); wl.text = "%d%%" % int(v * 100))
	sl.drag_ended.connect(func(_c): refresh_econ())
	polc[1].add_child(UiKit.hrow([_w(L("Welfare", 15), 70), sl, wl]))
	r2.add_child(polc[0])
	var stc := _card("Strategic stockpile", UiKit.ECON)
	var sg := GridContainer.new(); sg.columns = 4
	sg.add_theme_constant_override("h_separation", 22)
	for r in GameData.resources:
		var have := int(n["stock"].get(r, 0.0))
		var l := L("%s  %d" % [r.capitalize(), have], 15, PARCH if have > 0 else DIM)
		sg.add_child(l)
	stc[1].add_child(sg)
	stc[1].add_child(L("Surplus above 25 is exported; missing resources are imported at a premium when procuring.", 14, DIM))
	r2.add_child(stc[0])
	# --- procurement
	var era_id: String = GameData.eras[Sim.era]["id"]
	econ_box.add_child(UiKit.section("Procurement — %s equipment, raised at %s" % [GameData.eras[Sim.era]["name"], GameData.provinces[n["capital"]]["name"]], UiKit.ECON))
	var g := GridContainer.new(); g.columns = 8
	g.add_theme_constant_override("h_separation", 18); g.add_theme_constant_override("v_separation", 4)
	for hname in ["Unit", "Role", "Men", "Cost", "Upkeep", "Attack / Def.", "Range", ""]:
		g.add_child(UiKit.caption(hname))
	for uid in GameData.units_by_era[era_id]:
		var d: Dictionary = GameData.units[uid]
		var c := Sim.can_afford(me, uid)
		g.add_child(L(d["name"], 16)); g.add_child(L(d["role"], 15, DIM)); g.add_child(L(UiKit.fmt_int(d["men"]), 15))
		g.add_child(L("%d%s" % [int(c["cost"]), (" +%d" % int(c["res_buy"])) if c["res_buy"] > 0 else ""], 15, UiKit.ECON))
		g.add_child(L("%.1f" % d["upkeep"], 15)); g.add_child(L("%d / %d" % [d["melee"], d["defense"]], 15)); g.add_child(L("%d m" % int(d["range"]) if d["range"] > 0 else "—", 15))
		var id: String = uid
		g.add_child(B("Buy", func(): _buy(id, n["capital"]), not c["ok"], _unit_tip(uid, c), "primary" if c["ok"] else ""))
	econ_box.add_child(g)
	econ_box.add_child(L("Only current-era equipment can be bought. Eras change with the calendar (1500, 1800, 1914, 1980), never by buying.", 14, DIM))
	# --- armies
	econ_box.add_child(UiKit.section("Armies"))
	var ag := GridContainer.new(); ag.columns = 6
	ag.add_theme_constant_override("h_separation", 18); ag.add_theme_constant_override("v_separation", 4)
	for hname in ["Army", "Location", "Men", "Upkeep / mo", "", ""]:
		ag.add_child(UiKit.caption(hname))
	var any := false
	for a in Sim.armies.values():
		if a["owner"] != me:
			continue
		any = true
		var old := 0
		for u in a["units"]:
			if u["era"] != era_id:
				old += 1
		var aid: int = a["id"]
		var where: String = GameData.provinces[a["node"]]["name"] if a["node"] < GameData.SEA_NODE else "at sea"
		ag.add_child(L("%s%s" % [a["name"], "  · %d outdated" % old if old > 0 else ""], 16, UiKit.WARN if old > 0 else PARCH))
		ag.add_child(L(where, 15, DIM)); ag.add_child(L(UiKit.fmt_int(Sim.army_men(a)), 15)); ag.add_child(L("%.1f" % Sim.army_upkeep(a), 15, BAD))
		ag.add_child(B("Select", func(): econ_win.visible = false; main.select_army(aid), false, "Show this army on the map"))
		var rc := Sim.refit_cost(a)
		ag.add_child(B("Refit (%d)" % int(rc), func(): _refit(aid); refresh_econ(), rc <= 0 or n["funds"] < rc,
			"Equipment is already current" if rc <= 0 else (("Not enough funds (need %d)" % int(rc)) if n["funds"] < rc else "Re-equip outdated regiments")))
	if any:
		econ_box.add_child(ag)
	else:
		econ_box.add_child(L("No armies. Raise regiments from a province panel or above.", 15, DIM))
	# --- provinces
	econ_box.add_child(UiKit.section("Provinces (%d)" % Sim.nation_provs[me].size()))
	var pg2 := GridContainer.new(); pg2.columns = 4
	pg2.add_theme_constant_override("h_separation", 22); pg2.add_theme_constant_override("v_separation", 3)
	for hname in ["Province", "Population", "Resource", "Status"]:
		pg2.add_child(UiKit.caption(hname))
	var provs: Array = Sim.nation_provs[me].duplicate()
	provs.sort_custom(func(x, y): return Sim.prov_pop(x) > Sim.prov_pop(y))
	for pid in provs:
		var pb := B(GameData.provinces[pid]["name"] + ("  ★" if n["capital"] == pid else ""), func(): econ_win.visible = false; main.select_province(pid); focus_world.emit(GameData.node_world(pid)), false, "Show on the map", "ghost")
		pb.alignment = HORIZONTAL_ALIGNMENT_LEFT
		pg2.add_child(pb)
		pg2.add_child(L(UiKit.fmt_int(Sim.prov_pop(pid)), 15))
		pg2.add_child(L(GameData.provinces[pid]["resource"].capitalize(), 15, UiKit.ECON))
		pg2.add_child(L("Under siege" if Sim.sieges.has(pid) else "—", 15, BAD if Sim.sieges.has(pid) else DIM))
	econ_box.add_child(pg2)

# ------------------------------------------------------------------ deployment
func _build_deploy() -> void:
	var w := _window(860, 560, "Battle", false)
	deploy_win = w[0]
	deploy_box = w[1]

func show_deploy(bid: int) -> void:
	deploy_bid = bid
	var b: Dictionary = Sim.battles[bid]
	var ps: int = b["player_side"]
	deploy_orders = b["orders"][ps].duplicate()
	_deploy_refresh()
	deploy_win.visible = true

const OBJ_DESC := {"assault": "Advance and engage", "hold": "Defend the line, fire from cover", "flank": "Cavalry sweeps the wings", "bombard": "Artillery first, then advance"}
const FORM_DESC := {"line": "Balanced firepower and cohesion", "deep": "Fewer muskets, stronger in melee and steadier", "wide": "Most firepower, weaker against charges"}

func _deploy_refresh() -> void:
	clear(deploy_box)
	var b: Dictionary = Sim.battles[deploy_bid]
	var ps: int = b["player_side"]
	var p: Dictionary = GameData.provinces[b["prov"]]
	_set_win_title(deploy_win, "Battle of %s" % p["name"], "%s attacks %s · %s · we are the %s" % [Sim.nations[b["codes"][0]]["name"], Sim.nations[b["codes"][1]]["name"], p["terrain"].capitalize(), "attacker" if ps == 0 else "defender"])
	var cols := HBoxContainer.new(); cols.add_theme_constant_override("separation", 12)
	var men_s := [0.0, 0.0]
	for s in 2:
		for u in b["units"][s]:
			men_s[s] += u["men"]
	for s in [ps, 1 - ps]:
		var card := _card(("Our forces" if s == ps else "Enemy forces"), GOOD if s == ps else BAD)
		card[1].add_child(UiKit.hrow([_flag(b["codes"][s], 30), UiKit.label("%s men" % UiKit.fmt_int(men_s[s]), 22, PARCH, "semi")], 10))
		var cnt := {}
		for u in b["units"][s]:
			var nm: String = GameData.units[u["type"]]["name"]
			cnt[nm] = cnt.get(nm, 0) + 1
		for k in cnt.keys():
			card[1].add_child(L("%d × %s" % [cnt[k], k], 15, DIM))
		cols.add_child(card[0])
	deploy_box.add_child(cols)
	var ratio: float = men_s[ps] / maxf(men_s[0] + men_s[1], 1.0)
	deploy_box.add_child(UiKit.hrow([UiKit.caption("Balance of forces"), UiKit.meter(ratio, GOOD if ratio >= 0.5 else BAD, 600, 8), L("%d%% ours" % int(ratio * 100), 15, DIM)], 10))
	deploy_box.add_child(UiKit.section("Objective — your generals fight the battle; you set the plan"))
	var oh := HBoxContainer.new(); oh.add_theme_constant_override("separation", 6)
	for o in BattleSim.OBJECTIVES:
		var oo: String = o
		var bt := B(o.capitalize(), func(): deploy_orders["objective"] = oo; _deploy_refresh(), false, OBJ_DESC[o], "toggle")
		bt.button_pressed = deploy_orders["objective"] == o
		bt.custom_minimum_size = Vector2(120, 38)
		oh.add_child(bt)
	oh.add_child(L("  " + OBJ_DESC[deploy_orders["objective"]], 15, DIM))
	deploy_box.add_child(oh)
	deploy_box.add_child(UiKit.section("Formation"))
	var fh := HBoxContainer.new(); fh.add_theme_constant_override("separation", 6)
	for fname in BattleSim.FORMATIONS.keys():
		var ff: String = fname
		var bt2 := B(fname.capitalize(), func(): deploy_orders["formation"] = ff; _deploy_refresh(), false, FORM_DESC.get(fname, ""), "toggle")
		bt2.button_pressed = deploy_orders["formation"] == fname
		bt2.custom_minimum_size = Vector2(120, 38)
		fh.add_child(bt2)
	fh.add_child(L("  " + FORM_DESC.get(deploy_orders["formation"], ""), 15, DIM))
	deploy_box.add_child(fh)
	deploy_box.add_child(HSeparator.new())
	var bid := deploy_bid
	var wb := B("Deploy and watch the battle", func(): deploy_win.visible = false; deploy_chosen.emit(bid, deploy_orders.duplicate(), true), false, "Open the 3D battle", "primary")
	wb.custom_minimum_size = Vector2(320, 46); wb.add_theme_font_size_override("font_size", 18)
	var ab := B("Deploy and continue (resolve off-screen)", func(): deploy_win.visible = false; deploy_chosen.emit(bid, deploy_orders.duplicate(), false), false, "Same outcome as watching; the map keeps running")
	ab.custom_minimum_size = Vector2(0, 46)
	deploy_box.add_child(row([wb, ab]))
	deploy_box.add_child(L("The outcome is decided by the same simulation whether you watch or not.", 14, DIM))

# ------------------------------------------------------------------ dialogs
func _build_popup() -> void:
	var w := _window(640, 200, "", false)
	popup = w[0]
	popup_box = w[1]
	# dialogs carry their title inside the body (first child), so hide the empty window header and rule
	var outer: VBoxContainer = popup.get_child(0)
	outer.get_child(0).visible = false
	outer.get_child(1).visible = false

## buttons: [[text, callable], ...] or [text, callable, "primary"|"danger"|"order"]. Without a variant the last
## button is the primary choice.
func show_popup(t: String, body: String, buttons: Array, _closable: bool = true) -> void:
	clear(popup_box)
	var tl := UiKit.title(t, 30, BAD if t == "DEFEAT" else GOLD)
	popup_box.add_child(tl)
	var rule := ColorRect.new(); rule.color = Color(UiKit.BRASS.r, UiKit.BRASS.g, UiKit.BRASS.b, 0.35); rule.custom_minimum_size = Vector2(0, 1)
	popup_box.add_child(rule)
	var rt := RichTextLabel.new(); rt.bbcode_enabled = true; rt.fit_content = true; rt.text = body
	rt.custom_minimum_size = Vector2(600, 0)
	rt.add_theme_font_size_override("normal_font_size", 16); rt.add_theme_font_size_override("bold_font_size", 16)
	popup_box.add_child(rt)
	popup_box.add_child(HSeparator.new())
	var h := HBoxContainer.new(); h.alignment = BoxContainer.ALIGNMENT_END; h.add_theme_constant_override("separation", 8)
	var any_variant := false
	for b in buttons:
		if b.size() > 2: any_variant = true
	for i in buttons.size():
		var b: Array = buttons[i]
		var cb: Callable = b[1]
		var variant: String = b[2] if b.size() > 2 else ("primary" if not any_variant and i == buttons.size() - 1 and buttons.size() > 1 else "")
		var bt := B(b[0], func(): popup.visible = false; cb.call(), false, "", variant)
		bt.custom_minimum_size = Vector2(110, 40)
		h.add_child(bt)
	popup_box.add_child(h)
	popup.visible = true
	popup.reset_size()
	popup.position = ((get_viewport_rect().size - popup.size) * 0.5).floor()

## Standard confirmation: Cancel / <confirm_text>. variant: "danger" (default) or "primary".
func confirm(t: String, body: String, confirm_text: String, cb: Callable, variant: String = "danger") -> void:
	show_popup(t, body, [["Cancel", func(): pass], [confirm_text, cb, variant]])

func _on_era(e: int) -> void:
	var ed: Dictionary = GameData.eras[e]
	var names: Array = []
	for uid in GameData.units_by_era[ed["id"]]:
		names.append(GameData.units[uid]["name"])
	show_popup("A New Age: %s" % ed["name"],
		"The world enters the [b]%s[/b] (%d).\n\nNew equipment available: [color=#e9cc8a]%s[/color].\nProductivity ×%.1f · armies march %d km a day · naval reach %d sea zones.\n\nExisting regiments keep their old equipment until refitted (army panel → Refit)." % [ed["name"], int(ed["start"]), ", ".join(names), ed["productivity"], ed["move_km_day"], ed["naval_range"]],
		[["Continue", func(): pass, "primary"]])

## v0.5: offers go to the inbox instead of a popup each. Urgent ones (peace while at war, alliance while at war)
## get a one-line notice; routine ones only update the Inbox counter.
func _on_offer(offer: Dictionary) -> void:
	var from: String = offer["from"]
	var kn := Sim._kind_name(offer["kind"])
	if offer.get("urgent", false):
		show_toast("✉ %s offers %s — see the Inbox" % [Sim.nations[from]["name"], kn], 5.0)
	_log_line("[color=#88aee6]%s proposes a %s (in the Inbox).[/color]" % [Sim.nations[from]["name"], kn])
	if inbox_win and inbox_win.visible:
		refresh_inbox()

# ------------------------------------------------------------------ diplomatic inbox (v0.5, restyled v0.6)
var inbox_btn: Button
var inbox_win: PanelContainer
var inbox_box: VBoxContainer

const KIND_STYLE := {"peace": ["Peace", Color(0.55, 0.8, 0.5)], "alliance": ["Alliance", Color(0.5, 0.68, 0.9)],
	"nap": ["Non-aggression", Color(0.5, 0.78, 0.74)], "trade": ["Trade", Color(0.9, 0.76, 0.44)]}

func _build_inbox() -> void:
	var w := _window(880, 600, "Inbox")
	inbox_win = w[0]
	var v: VBoxContainer = w[1]
	var sc := ScrollContainer.new(); sc.follow_focus = true; sc.custom_minimum_size = Vector2(840, 520); sc.size_flags_vertical = Control.SIZE_EXPAND_FILL
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(sc)
	inbox_box = VBoxContainer.new(); inbox_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inbox_box.add_theme_constant_override("separation", 6)
	sc.add_child(inbox_box)
	Sim.inbox_changed.connect(func(): if inbox_win.visible: refresh_inbox.call_deferred())

func toggle_inbox() -> void:
	diplo_win.visible = false; econ_win.visible = false
	inbox_win.visible = not inbox_win.visible
	if inbox_win.visible:
		refresh_inbox()

func refresh_inbox() -> void:
	clear(inbox_box)
	var offers: Array = Sim.pending_offers
	var urgent: Array = offers.filter(func(o): return o.get("urgent", Sim.is_urgent_offer(o)))
	var routine: Array = offers.filter(func(o): return not o.get("urgent", Sim.is_urgent_offer(o)))
	_set_win_title(inbox_win, "Inbox", "%d proposal%s waiting%s" % [offers.size(), "" if offers.size() == 1 else "s", (" · %d need attention" % urgent.size()) if not urgent.is_empty() else ""])
	# military reports: declarations of war against us and spotted invasion forces (last 60 days)
	var mil: Array = Sim.event_log.filter(func(e): return Sim.day - int(e["day"]) <= 60 and ((e["kind"] == "warning") or (e["kind"] == "war" and e["nations"].has(Sim.player))))
	if not mil.is_empty():
		inbox_box.add_child(UiKit.section("Military reports", BAD))
		for e in mil.slice(maxi(0, mil.size() - 6)):
			var head := "Scouts' report" if e["kind"] == "warning" else "War"
			var card := PanelContainer.new(); card.theme_type_variation = "AlertPanel"
			var cv := VBoxContainer.new(); cv.add_theme_constant_override("separation", 2); card.add_child(cv)
			cv.add_child(UiKit.hrow([UiKit.caption(head, BAD.lightened(0.15)), _spacer(), L(e["date"], 14, DIM)]))
			cv.add_child(UiKit.para(e["text"], 780, 15, PARCH))
			inbox_box.add_child(card)
	if offers.is_empty():
		inbox_box.add_child(UiKit.para("No proposals waiting. Envoys' offers collect here instead of interrupting you; unanswered ones lapse after %d days." % Sim.OFFER_TTL, 800, 15, DIM))
	if not urgent.is_empty():
		inbox_box.add_child(UiKit.section("Needs attention (%d)" % urgent.size(), BAD))
		for o in urgent:
			_offer_row(o, true)
	if not routine.is_empty():
		inbox_box.add_child(UiKit.hrow([UiKit.label("Routine proposals (%d)" % routine.size(), 18, GOLD, "title2"), _spacer(),
			B("Set aside all routine", func(): Sim.respond_all("", false); refresh_inbox(), false, "Politely decline every routine proposal (small relations cost; they will not be repeated for a while)")]))
		var kinds := {}
		for o in routine:
			if not kinds.has(o["kind"]): kinds[o["kind"]] = []
			kinds[o["kind"]].append(o)
		for k in ["alliance", "nap", "trade"]:
			if not kinds.has(k):
				continue
			var kk: String = k
			var hdr: String = {"trade": "Trade agreements", "nap": "Non-aggression pacts", "alliance": "Defensive alliances"}[k]
			inbox_box.add_child(row([UiKit.chip(KIND_STYLE[k][0], KIND_STYLE[k][1]), L("%s (%d)" % [hdr, kinds[k].size()], 16, PARCH), _spacer(),
				B("Accept all", func(): Sim.respond_all(kk, true); main.map.lut_dirty = true; refresh_inbox(), false, "Accept every %s on the list" % Sim._kind_name(kk)),
				B("Decline all", func(): Sim.respond_all(kk, false); refresh_inbox())]))
			for o in kinds[k]:
				_offer_row(o, false)

func _offer_row(o: Dictionary, urgent: bool) -> void:
	var from: String = o["from"]
	var ev: Dictionary = Sim.evaluate(from, Sim.player, o["kind"])
	var extra := ""
	if o["kind"] == "peace" and Sim.at_war(from, Sim.player):
		extra = " · war score %+.0f" % Sim.war_score(Sim.player, from)
	var card := PanelContainer.new(); card.theme_type_variation = "CardPanel"
	var st: Array = KIND_STYLE.get(o["kind"], ["Offer", DIM])
	var tv := VBoxContainer.new(); tv.add_theme_constant_override("separation", -2); tv.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	tv.add_child(L("%s — %s" % [Sim.nations[from]["name"], Sim._kind_name(o["kind"])], 16, BAD if urgent else PARCH))
	tv.add_child(L("relations %+d%s · waiting %d days" % [int(Sim.relation(from, Sim.player)), extra, Sim.day - int(o["day"])], 14, DIM))
	var still: bool = ev["score"] > -900.0
	var f := _flag(from, 33); f.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var ch := UiKit.chip(st[0], st[1]); ch.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	card.add_child(row([f, ch, tv,
		B("Accept", func(): Sim.respond_offer(o, true); main.map.lut_dirty = true; refresh_inbox(), not still, "Accept the %s" % Sim._kind_name(o["kind"]) if still else "No longer applies — the situation has changed", "primary"),
		B("Decline", func(): Sim.respond_offer(o, false); refresh_inbox(), false, "Refuse (relations −4; they will not ask again for months)"),
		B("…", func(): inbox_win.visible = false; open_diplomacy(from), false, "Open diplomacy with %s" % Sim.nations[from]["name"])]))
	inbox_box.add_child(card)

func _on_battle_resolved(bid: int, res: Dictionary) -> void:
	var b: Dictionary = Sim.battles.get(bid, {})
	if b.is_empty() or b["player_side"] < 0:
		return
	var won: bool = res["winner"] == b["player_side"]
	show_toast("%s at %s! Losses: ours %s, theirs %s" % ["Victory" if won else "Defeat", GameData.provinces[b["prov"]]["name"], UiKit.fmt_int(res["losses"][b["player_side"]]), UiKit.fmt_int(res["losses"][1 - b["player_side"]])], 5.0)

## v0.5: an approaching force has been spotted. Show it, and slow a fast clock to Normal so there is time to act.
func _on_invasion_warning(w: Dictionary) -> void:
	show_toast("⚠ " + w["text"], 7.0)
	push_alert("Enemy force spotted", w["text"], int(w.get("province", -1)))
	if Sim.speed_idx > 2:
		Sim.set_speed(2)

func _process(delta: float) -> void:
	if toast_t > 0:
		toast_t -= delta
		toast_panel.modulate.a = clampf(toast_t, 0.0, 1.0)
		if toast_t <= 0:
			toast_panel.visible = false
	_refresh_t -= delta
	if _refresh_t <= 0:
		_refresh_t = 0.25
		refresh_top()
		_update_backdrop()
		hint.visible = not any_window_open()
		var fo := get_viewport().gui_get_focus_owner()
		if sel_panel.visible and not get_viewport().gui_get_hovered_control() in _descendants(sel_panel) and not (fo != null and sel_panel.is_ancestor_of(fo)) \
				and selection_signature() != _sel_sig:
			refresh_selection()
	_pad_focus()

func _descendants(n: Node) -> Array:
	var out: Array = []
	var st := [n]
	while st.size() > 0:
		var x: Node = st.pop_back()
		out.append(x)
		st.append_array(x.get_children())
	return out

func any_window_open() -> bool:
	return diplo_win.visible or econ_win.visible or deploy_win.visible or popup.visible or menu_win.visible or inbox_win.visible
