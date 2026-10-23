class_name UiKit
extends RefCounted
## Iron Crowns interface design system (v0.6): palette, typography, theme and small builders shared by the
## title screen, the campaign HUD and the battle HUD. Presentation only: nothing here reads or changes the
## simulation.
##
## Look: dark charcoal / aged-iron panels, muted navy for selected and active states, restrained brass accents.
## Semantic colours: MIL (war, alerts, attack orders), DIPLO (diplomacy), ECON (treasury, resources),
## GOOD (gains, peace, acceptance), DIM (secondary information).

# ---------------------------------------------------------------- palette
const INK := Color(0.055, 0.062, 0.072)            # deepest background (title screen, backdrops)
const PANEL := Color(0.085, 0.094, 0.108, 0.955)   # charcoal panel
const PANEL_2 := Color(0.118, 0.13, 0.148)         # raised card / row
const PANEL_3 := Color(0.155, 0.168, 0.188)        # hover
const NAVY := Color(0.105, 0.15, 0.215)            # selected / active
const IRON := Color(0.30, 0.32, 0.35)              # borders, rules
const IRON_DIM := Color(0.2, 0.215, 0.235)
const BRASS := Color(0.80, 0.66, 0.40)             # accents, titles
const BRASS_DIM := Color(0.52, 0.44, 0.30)
const TEXT := Color(0.91, 0.895, 0.86)             # body text (warm ivory)
const DIM := Color(0.63, 0.645, 0.66)              # secondary text (cool grey)
const FAINT := Color(0.46, 0.48, 0.5)
const MIL := Color(0.87, 0.38, 0.32)               # war, alerts, attack orders
const MIL_BG := Color(0.27, 0.105, 0.09)
const DIPLO := Color(0.5, 0.68, 0.9)               # diplomacy
const ECON := Color(0.9, 0.76, 0.44)               # treasury, resources
const GOOD := Color(0.55, 0.8, 0.5)                # gains, peace, accept
const WARN := Color(0.95, 0.67, 0.32)              # caution

# ---------------------------------------------------------------- typography
## Source Sans 3 (body, OFL) and Cormorant SC (titles, OFL); see assets/fonts/*-OFL.txt.
const FONT_BODY_PATH := "res://assets/fonts/SourceSans3-Regular.otf"
const FONT_SEMI_PATH := "res://assets/fonts/SourceSans3-Semibold.otf"
const FONT_BOLD_PATH := "res://assets/fonts/SourceSans3-Bold.otf"
const FONT_TITLE_PATH := "res://assets/fonts/CormorantSC-Bold.ttf"
const FONT_TITLE2_PATH := "res://assets/fonts/CormorantSC-SemiBold.ttf"
const SIZE_SMALL := 14      # smallest text anywhere (≈12 px at 1366×768)
const SIZE_BODY := 16
const SIZE_SUB := 18
const SIZE_TITLE := 24

static var _fonts := {}

static func font(kind: String = "body") -> Font:
	if _fonts.has(kind):
		return _fonts[kind]
	var path: String = {"body": FONT_BODY_PATH, "semi": FONT_SEMI_PATH, "bold": FONT_BOLD_PATH, "title": FONT_TITLE_PATH,
		"title2": FONT_TITLE2_PATH, "caption": FONT_SEMI_PATH}.get(kind, FONT_BODY_PATH)
	var f: Font = load(path) if ResourceLoader.exists(path) else ThemeDB.fallback_font
	if kind == "caption":
		# letter-spaced semibold for small-caps captions above values
		var fv := FontVariation.new()
		fv.base_font = f
		fv.spacing_glyph = 1
		f = fv
	_fonts[kind] = f
	return f

# ---------------------------------------------------------------- styleboxes
static func box(bg: Color, border: Color = Color(0, 0, 0, 0), bw: int = 0, radius: int = 3, margin := Vector4(12, 8, 12, 8)) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_corner_radius_all(radius)
	s.content_margin_left = margin.x; s.content_margin_top = margin.y; s.content_margin_right = margin.z; s.content_margin_bottom = margin.w
	s.anti_aliasing = true
	return s

static func _panel_box() -> StyleBoxFlat:
	var s := box(PANEL, IRON, 1, 4, Vector4(14, 12, 14, 12))
	s.border_width_top = 2
	s.border_color = IRON
	s.shadow_color = Color(0, 0, 0, 0.55); s.shadow_size = 10; s.shadow_offset = Vector2(0, 3)
	return s

## Theme for every UI root. large: touch-friendly sizes (Settings → Large touch targets).
static func make_theme(large: bool = false) -> Theme:
	var t := Theme.new()
	t.default_font = font("body")
	t.default_font_size = SIZE_BODY
	var k := 1.0 if not large else 1.15
	# panels
	t.set_stylebox("panel", "PanelContainer", _panel_box())
	t.set_stylebox("panel", "Panel", _panel_box())
	var win := _panel_box(); win.border_color = BRASS_DIM; win.shadow_size = 18; win.shadow_color = Color(0, 0, 0, 0.65)
	win.content_margin_left = 18; win.content_margin_right = 18; win.content_margin_top = 14; win.content_margin_bottom = 16
	t.set_type_variation("WindowPanel", "PanelContainer")
	t.set_stylebox("panel", "WindowPanel", win)
	t.set_type_variation("CardPanel", "PanelContainer")
	t.set_stylebox("panel", "CardPanel", box(PANEL_2, IRON_DIM, 1, 3, Vector4(12, 10, 12, 10)))
	t.set_type_variation("CardSelected", "PanelContainer")
	var cs := box(NAVY, BRASS, 2, 3, Vector4(12, 10, 12, 10)); t.set_stylebox("panel", "CardSelected", cs)
	t.set_type_variation("AlertPanel", "PanelContainer")
	var al := box(Color(0.13, 0.075, 0.07, 0.96), MIL, 1, 3, Vector4(12, 9, 10, 9)); al.border_width_left = 4
	al.shadow_color = Color(0, 0, 0, 0.5); al.shadow_size = 8
	t.set_stylebox("panel", "AlertPanel", al)
	t.set_type_variation("BarPanel", "PanelContainer")
	var bar := box(Color(0.07, 0.078, 0.09, 0.97), BRASS_DIM, 0, 0, Vector4(14, 6, 14, 6)); bar.border_width_bottom = 1
	bar.shadow_color = Color(0, 0, 0, 0.45); bar.shadow_size = 8
	t.set_stylebox("panel", "BarPanel", bar)
	t.set_type_variation("ToastPanel", "PanelContainer")
	t.set_stylebox("panel", "ToastPanel", box(Color(0.06, 0.07, 0.08, 0.9), BRASS_DIM, 1, 4, Vector4(18, 8, 18, 9)))
	# labels / rich text
	t.set_color("font_color", "Label", TEXT)
	t.set_font_size("font_size", "Label", int(SIZE_BODY * k))
	t.set_color("default_color", "RichTextLabel", TEXT)
	t.set_font("normal_font", "RichTextLabel", font("body"))
	t.set_font("bold_font", "RichTextLabel", font("semi"))
	t.set_font_size("normal_font_size", "RichTextLabel", int(15 * k))
	t.set_font_size("bold_font_size", "RichTextLabel", int(15 * k))
	# buttons
	var pad := Vector4(12, 6, 12, 7) if not large else Vector4(16, 12, 16, 12)
	_button_set(t, "Button", box(PANEL_3, IRON, 1, 3, pad), Color(0.205, 0.22, 0.245), BRASS_DIM, NAVY, BRASS, TEXT)
	var prim := box(Color(0.52, 0.41, 0.22), BRASS, 1, 3, pad)
	_button_set(t, "PrimaryButton", prim, Color(0.63, 0.5, 0.27), Color(0.95, 0.82, 0.55), Color(0.42, 0.33, 0.17), BRASS, Color(0.08, 0.07, 0.05))
	var dang := box(Color(0.33, 0.12, 0.1), Color(0.6, 0.25, 0.21), 1, 3, pad)
	_button_set(t, "DangerButton", dang, Color(0.45, 0.16, 0.13), MIL, Color(0.25, 0.08, 0.07), MIL, Color(1.0, 0.88, 0.84))
	var order := box(Color(0.15, 0.115, 0.105), Color(0.5, 0.25, 0.2), 1, 3, pad); order.border_width_left = 3; order.border_color = MIL
	_button_set(t, "OrderButton", order, Color(0.22, 0.14, 0.12), MIL, Color(0.3, 0.13, 0.11), MIL, TEXT)
	var ghost := box(Color(0, 0, 0, 0), Color(0, 0, 0, 0), 0, 3, Vector4(8, 4, 8, 4))
	_button_set(t, "GhostButton", ghost, Color(1, 1, 1, 0.07), Color(0, 0, 0, 0), Color(1, 1, 1, 0.12), Color(0, 0, 0, 0), DIM)
	var tab := box(PANEL_2, IRON_DIM, 1, 3, pad)
	_button_set(t, "ToggleButton", tab, PANEL_3, BRASS_DIM, NAVY, BRASS, TEXT)
	t.set_stylebox("pressed", "ToggleButton", box(NAVY, BRASS, 1, 3, pad))
	for ty in ["Button", "PrimaryButton", "DangerButton", "OrderButton", "GhostButton", "ToggleButton"]:
		t.set_font(("font"), ty, font("semi"))
		t.set_font_size("font_size", ty, int(SIZE_BODY * k))
	t.set_color("font_disabled_color", "Button", Color(0.46, 0.47, 0.48))
	# keyboard / gamepad focus ring
	var fr := StyleBoxFlat.new(); fr.draw_center = false; fr.border_color = Color(1.0, 0.84, 0.45); fr.set_border_width_all(2)
	fr.set_corner_radius_all(4); fr.expand_margin_left = 3; fr.expand_margin_right = 3; fr.expand_margin_top = 3; fr.expand_margin_bottom = 3
	for ty in ["Button", "OptionButton", "CheckButton", "PrimaryButton", "DangerButton", "OrderButton", "GhostButton", "ToggleButton"]:
		t.set_stylebox("focus", ty, fr)
	# option button / line edit
	_button_set(t, "OptionButton", box(PANEL_3, IRON, 1, 3, Vector4(12, 6, 30, 7)), Color(0.205, 0.22, 0.245), BRASS_DIM, NAVY, BRASS, TEXT)
	t.set_stylebox("normal", "LineEdit", box(INK, IRON, 1, 3, Vector4(10, 6, 10, 6)))
	t.set_stylebox("focus", "LineEdit", box(INK, BRASS, 1, 3, Vector4(10, 6, 10, 6)))
	t.set_color("font_color", "LineEdit", TEXT)
	# popup menus (OptionButton lists, context menus)
	t.set_stylebox("panel", "PopupMenu", box(PANEL, BRASS_DIM, 1, 3, Vector4(6, 6, 6, 6)))
	t.set_stylebox("hover", "PopupMenu", box(NAVY, Color(0, 0, 0, 0), 0, 2))
	t.set_color("font_color", "PopupMenu", TEXT); t.set_color("font_hover_color", "PopupMenu", Color(1, 0.95, 0.85))
	# tooltips
	t.set_stylebox("panel", "TooltipPanel", box(Color(0.075, 0.09, 0.115, 0.98), BRASS_DIM, 1, 3, Vector4(10, 7, 10, 8)))
	t.set_color("font_color", "TooltipLabel", TEXT)
	t.set_font_size("font_size", "TooltipLabel", 15)
	t.set_font("font", "TooltipLabel", font("body"))
	# separators
	var sep := StyleBoxLine.new(); sep.color = Color(IRON.r, IRON.g, IRON.b, 0.8); sep.thickness = 1
	t.set_stylebox("separator", "HSeparator", sep)
	t.set_constant("separation", "HSeparator", 10)
	var vsep := StyleBoxLine.new(); vsep.color = Color(IRON.r, IRON.g, IRON.b, 0.8); vsep.thickness = 1; vsep.vertical = true
	t.set_stylebox("separator", "VSeparator", vsep)
	# progress bars, sliders, scrollbars
	t.set_stylebox("background", "ProgressBar", box(Color(0.04, 0.045, 0.05), IRON_DIM, 1, 2, Vector4.ZERO))
	t.set_stylebox("fill", "ProgressBar", box(BRASS, Color(0, 0, 0, 0), 0, 2, Vector4.ZERO))
	t.set_font_size("font_size", "ProgressBar", 12)
	var sl := box(Color(0.04, 0.045, 0.05), IRON_DIM, 1, 3, Vector4(0, 3, 0, 3))
	t.set_stylebox("slider", "HSlider", sl)
	t.set_stylebox("grabber_area", "HSlider", box(BRASS_DIM, Color(0, 0, 0, 0), 0, 3, Vector4(0, 3, 0, 3)))
	t.set_stylebox("grabber_area_highlight", "HSlider", box(BRASS, Color(0, 0, 0, 0), 0, 3, Vector4(0, 3, 0, 3)))
	for sb in ["VScrollBar", "HScrollBar"]:
		t.set_stylebox("scroll", sb, box(Color(0, 0, 0, 0.25), Color(0, 0, 0, 0), 0, 3, Vector4(4, 4, 4, 4)))
		t.set_stylebox("grabber", sb, box(IRON, Color(0, 0, 0, 0), 0, 3))
		t.set_stylebox("grabber_highlight", sb, box(BRASS_DIM, Color(0, 0, 0, 0), 0, 3))
		t.set_stylebox("grabber_pressed", sb, box(BRASS, Color(0, 0, 0, 0), 0, 3))
	# containers
	t.set_constant("separation", "HBoxContainer", 8 if not large else 10)
	t.set_constant("separation", "VBoxContainer", 6 if not large else 8)
	t.set_constant("h_separation", "GridContainer", 10)
	t.set_constant("v_separation", "GridContainer", 6)
	return t

static func _button_set(t: Theme, ty: String, normal: StyleBoxFlat, hover_bg: Color, hover_border: Color, pressed_bg: Color, pressed_border: Color, fc: Color) -> void:
	if ty != "Button" and ty != "OptionButton":
		t.set_type_variation(ty, "Button")
	var h := normal.duplicate(); h.bg_color = hover_bg; h.border_color = hover_border
	var p := normal.duplicate(); p.bg_color = pressed_bg; p.border_color = pressed_border
	var d := normal.duplicate(); d.bg_color = Color(0.1, 0.105, 0.115, maxf(normal.bg_color.a, 0.6)); d.border_color = IRON_DIM
	t.set_stylebox("normal", ty, normal)
	t.set_stylebox("hover", ty, h)
	t.set_stylebox("pressed", ty, p)
	t.set_stylebox("hover_pressed", ty, p)
	t.set_stylebox("disabled", ty, d)
	t.set_color("font_color", ty, fc)
	t.set_color("font_hover_color", ty, fc.lightened(0.12) if fc.v < 0.5 else Color(1, 0.97, 0.9))
	t.set_color("font_pressed_color", ty, fc if fc.v < 0.5 else Color(1, 0.93, 0.75))
	t.set_color("font_hover_pressed_color", ty, fc if fc.v < 0.5 else Color(1, 0.93, 0.75))
	t.set_color("font_focus_color", ty, fc)
	t.set_color("font_disabled_color", ty, Color(0.46, 0.47, 0.48))

# ---------------------------------------------------------------- builders
static func label(text: String, size: int = SIZE_BODY, col: Color = TEXT, kind: String = "body") -> Label:
	var l := Label.new()
	l.text = text
	if size != SIZE_BODY:
		l.add_theme_font_size_override("font_size", maxi(size, 12))
	if col != TEXT:
		l.add_theme_color_override("font_color", col)
	if kind != "body":
		l.add_theme_font_override("font", font(kind))
	return l

## Wrapping paragraph at a fixed width.
static func para(text: String, width: float, size: int = 15, col: Color = DIM) -> Label:
	var l := label(text, size, col)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(width, 0)
	return l

## Small letter-spaced caption (above a value, or a section of a panel).
static func caption(text: String, col: Color = DIM) -> Label:
	var l := label(text.to_upper(), 13, col, "caption")
	return l

static func title(text: String, size: int = SIZE_TITLE, col: Color = BRASS) -> Label:
	return label(text, size, col, "title")

## variant: "" (standard), "primary", "danger", "order" (military order), "ghost", "toggle".
static func button(text: String, cb: Callable, variant: String = "", disabled: bool = false, tip: String = "") -> Button:
	var b := Button.new()
	b.text = text
	b.disabled = disabled
	b.tooltip_text = tip
	b.theme_type_variation = {"primary": "PrimaryButton", "danger": "DangerButton", "order": "OrderButton", "ghost": "GhostButton",
		"toggle": "ToggleButton"}.get(variant, "")
	if variant == "toggle":
		b.toggle_mode = true
	b.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	b.pressed.connect(cb)
	return b

## Section header: brass small caps title with a hairline under it.
static func section(text: String, col: Color = BRASS) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	v.add_child(label(text, 17, col, "title2"))
	var r := ColorRect.new(); r.color = Color(col.r, col.g, col.b, 0.35); r.custom_minimum_size = Vector2(0, 1)
	v.add_child(r)
	return v

## Value with a caption above it (top-bar statistics).
static func stat(cap: String, value: Label, tip: String = "") -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", -2)
	v.add_child(caption(cap))
	v.add_child(value)
	v.tooltip_text = tip
	v.mouse_filter = Control.MOUSE_FILTER_PASS
	value.mouse_filter = Control.MOUSE_FILTER_PASS
	value.tooltip_text = tip
	return v

## Coloured pill for a status or category (WAR, Trade, Peace ...).
static func chip(text: String, col: Color) -> PanelContainer:
	var p := PanelContainer.new()
	var s := box(Color(col.r, col.g, col.b, 0.16), Color(col.r, col.g, col.b, 0.7), 1, 9, Vector4(8, 1, 8, 2))
	p.add_theme_stylebox_override("panel", s)
	var l := label(text, 13, col.lightened(0.15), "caption")
	p.add_child(l)
	return p

static func hrow(items: Array, sep: int = 8) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	for it in items:
		h.add_child(it)
	return h

static func spacer() -> Control:
	var c := Control.new()
	c.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c

static func meter(v: float, col: Color, w: float = 140.0, h: float = 8.0) -> ProgressBar:
	var p := ProgressBar.new()
	p.min_value = 0; p.max_value = 1; p.value = clampf(v, 0.0, 1.0)
	p.custom_minimum_size = Vector2(w, h)
	p.show_percentage = false
	p.add_theme_stylebox_override("fill", box(col, Color(0, 0, 0, 0), 0, 2, Vector4.ZERO))
	p.mouse_filter = Control.MOUSE_FILTER_PASS
	return p

static func fmt_int(v: float) -> String:
	var n := int(round(absf(v)))
	var s := str(n)
	var out := ""
	while s.length() > 3:
		out = "," + s.substr(s.length() - 3) + out
		s = s.substr(0, s.length() - 3)
	return ("-" if v < 0 and n != 0 else "") + s + out

## 1,234 / 12.3k / 1.23M — compact numbers for tight places.
static func compact(v: float) -> String:
	var a := absf(v)
	var sgn := "-" if v < 0 else ""
	if a >= 1.0e6:
		return sgn + ("%.2fM" % (a / 1.0e6))
	if a >= 1.0e4:
		return sgn + ("%.1fk" % (a / 1000.0))
	return fmt_int(v)

## Era presentation (title screen cards, HUD era chip).
const ERA_INFO := {
	"medieval": {"short": "Medieval", "desc": "Levies, archers and armoured knights. Armies are slow, sieges long, and a battle is won in the press of melee.", "tint": Color(0.55, 0.42, 0.3)},
	"early_modern": {"short": "Pike & Shot", "desc": "Pike squares and musketeers, cuirassiers and culverins. Gunpowder arrives; fleets begin to reach across seas.", "tint": Color(0.45, 0.47, 0.32)},
	"c19": {"short": "Revolutions", "desc": "Line infantry, grenadiers, hussars and field guns. Faster marches, long-range fleets, decisive volleys.", "tint": Color(0.3, 0.38, 0.55)},
	"c20": {"short": "Mechanised War", "desc": "Riflemen, machine guns, howitzers and the first tanks. Railways and steamships put the world in reach.", "tint": Color(0.38, 0.4, 0.36)},
	"modern": {"short": "Modern", "desc": "Mechanised infantry, main battle tanks and rocket artillery, watched by radar. Wars are fast and costly.", "tint": Color(0.28, 0.36, 0.42)},
}
