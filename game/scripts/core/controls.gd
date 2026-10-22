## Input actions (InputMap) for keyboard/mouse, gamepad and touch, plus persisted player settings
## (UI scale, touch hit targets, quality, perf overlay). Autoload "Controls".
extends Node

signal settings_changed
signal device_changed(kind: String)

const SETTINGS_PATH := "user://settings.cfg"
const JA := JOY_AXIS_LEFT_X

## action -> list of bindings. "k:<keycode>", "ks:<keycode>" (with shift), "j:<button>", "a:<axis>:<sign>"
const ACTIONS := {
	"pan_up": ["k:%d" % KEY_W, "k:%d" % KEY_UP],
	"pan_down": ["k:%d" % KEY_S, "k:%d" % KEY_DOWN],
	"pan_left": ["k:%d" % KEY_A, "k:%d" % KEY_LEFT],
	"pan_right": ["k:%d" % KEY_D, "k:%d" % KEY_RIGHT],
	"cursor_up": ["a:%d:-1" % JOY_AXIS_LEFT_Y],
	"cursor_down": ["a:%d:1" % JOY_AXIS_LEFT_Y],
	"cursor_left": ["a:%d:-1" % JOY_AXIS_LEFT_X],
	"cursor_right": ["a:%d:1" % JOY_AXIS_LEFT_X],
	"orbit_left": ["k:%d" % KEY_Q, "a:%d:-1" % JOY_AXIS_RIGHT_X],
	"orbit_right": ["k:%d" % KEY_E, "a:%d:1" % JOY_AXIS_RIGHT_X],
	"zoom_in": ["k:%d" % KEY_EQUAL, "k:%d" % KEY_KP_ADD, "a:%d:-1" % JOY_AXIS_RIGHT_Y, "a:%d:1" % JOY_AXIS_TRIGGER_RIGHT],
	"zoom_out": ["k:%d" % KEY_MINUS, "k:%d" % KEY_KP_SUBTRACT, "a:%d:1" % JOY_AXIS_RIGHT_Y, "a:%d:1" % JOY_AXIS_TRIGGER_LEFT],
	"select": ["j:%d" % JOY_BUTTON_A],
	"command_move": ["k:%d" % KEY_M, "j:%d" % JOY_BUTTON_X],
	"cancel": ["k:%d" % KEY_BACKSPACE, "j:%d" % JOY_BUTTON_B],
	"pause": ["k:%d" % KEY_SPACE, "j:%d" % JOY_BUTTON_Y],
	"speed_up": ["k:%d" % KEY_PERIOD, "j:%d" % JOY_BUTTON_DPAD_RIGHT],
	"speed_down": ["k:%d" % KEY_COMMA, "j:%d" % JOY_BUTTON_DPAD_LEFT],
	"speed_1": ["k:%d" % KEY_1], "speed_2": ["k:%d" % KEY_2], "speed_3": ["k:%d" % KEY_3], "speed_4": ["k:%d" % KEY_4], "speed_5": ["k:%d" % KEY_5],
	"cycle_army_next": ["k:%d" % KEY_TAB, "j:%d" % JOY_BUTTON_RIGHT_SHOULDER],
	"cycle_army_prev": ["ks:%d" % KEY_TAB, "j:%d" % JOY_BUTTON_LEFT_SHOULDER],
	"cycle_province_next": ["k:%d" % KEY_BRACKETRIGHT, "j:%d" % JOY_BUTTON_DPAD_DOWN],
	"cycle_province_prev": ["k:%d" % KEY_BRACKETLEFT, "j:%d" % JOY_BUTTON_DPAD_UP],
	"toggle_diplomacy": ["k:%d" % KEY_F1, "j:%d" % JOY_BUTTON_BACK],
	"toggle_economy": ["k:%d" % KEY_F2, "j:%d" % JOY_BUTTON_LEFT_STICK],
	"focus_hud": ["k:%d" % KEY_F6, "j:%d" % JOY_BUTTON_RIGHT_STICK],
	"game_menu": ["k:%d" % KEY_ESCAPE, "j:%d" % JOY_BUTTON_START],
	"perf_overlay": ["k:%d" % KEY_F3],
	"quick_save": ["k:%d" % KEY_F5],
	"quick_load": ["k:%d" % KEY_F9],
	"camera_toggle": ["k:%d" % KEY_C, "j:%d" % JOY_BUTTON_Y],
	"battle_speed": ["k:%d" % KEY_T, "j:%d" % JOY_BUTTON_RIGHT_SHOULDER],
	"battle_leave": ["k:%d" % KEY_L, "j:%d" % JOY_BUTTON_BACK],
}

var ui_scale := 1.0
var large_targets := false
var touch_rotate := true
var quality := 1          # 0 low, 1 medium, 2 high
var show_perf := false
var last_device := "kbm"  # kbm | joy | touch

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	register_actions()
	load_settings()
	large_targets = large_targets or DisplayServer.is_touchscreen_available()
	apply_settings.call_deferred()

func register_actions() -> void:
	for act in ACTIONS.keys():
		if not InputMap.has_action(act):
			InputMap.add_action(act, 0.25)
		for b in ACTIONS[act]:
			var parts: PackedStringArray = b.split(":")
			var ev: InputEvent
			match parts[0]:
				"k", "ks":
					var k := InputEventKey.new(); k.physical_keycode = int(parts[1]) as Key; k.keycode = int(parts[1]) as Key
					k.shift_pressed = parts[0] == "ks"
					ev = k
				"j":
					var j := InputEventJoypadButton.new(); j.button_index = int(parts[1]) as JoyButton; j.device = -1
					ev = j
				"a":
					var m := InputEventJoypadMotion.new(); m.axis = int(parts[1]) as JoyAxis; m.axis_value = float(parts[2]); m.device = -1
					ev = m
			if not InputMap.action_has_event(act, ev):
				InputMap.action_add_event(act, ev)
	# gamepad focus navigation for menus/panels: ui_* already carry d-pad and left stick; add A/B explicitly
	for pair in [["ui_accept", JOY_BUTTON_A], ["ui_cancel", JOY_BUTTON_B]]:
		var jb := InputEventJoypadButton.new(); jb.button_index = pair[1]; jb.device = -1
		if not InputMap.action_has_event(pair[0], jb):
			InputMap.action_add_event(pair[0], jb)

func _input(ev: InputEvent) -> void:
	var kind := last_device
	if ev is InputEventJoypadButton or (ev is InputEventJoypadMotion and absf(ev.axis_value) > 0.4):
		kind = "joy"
	elif ev is InputEventScreenTouch or ev is InputEventScreenDrag:
		kind = "touch"
	elif ev is InputEventKey or (ev is InputEventMouseButton and ev.device != InputEvent.DEVICE_ID_EMULATION):
		kind = "kbm"
	if kind != last_device:
		last_device = kind
		device_changed.emit(kind)

## True for mouse events synthesized from touch (the touch handlers deal with those gestures).
static func is_emulated(ev: InputEvent) -> bool:
	return (ev is InputEventMouse) and ev.device == InputEvent.DEVICE_ID_EMULATION

func load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(SETTINGS_PATH) != OK:
		return
	ui_scale = clampf(float(cf.get_value("ui", "scale", 1.0)), 0.75, 2.0)
	large_targets = bool(cf.get_value("ui", "large_targets", false))
	touch_rotate = bool(cf.get_value("input", "touch_rotate", true))
	quality = clampi(int(cf.get_value("video", "quality", 1)), 0, 2)
	show_perf = bool(cf.get_value("video", "show_perf", false))

func save_settings() -> void:
	var cf := ConfigFile.new()
	cf.set_value("ui", "scale", ui_scale)
	cf.set_value("ui", "large_targets", large_targets)
	cf.set_value("input", "touch_rotate", touch_rotate)
	cf.set_value("video", "quality", quality)
	cf.set_value("video", "show_perf", show_perf)
	cf.save(SETTINGS_PATH)

func apply_settings() -> void:
	get_tree().root.content_scale_factor = ui_scale
	settings_changed.emit()

func set_setting(key: String, value) -> void:
	set(key, value)
	save_settings()
	apply_settings()
