## Total-War-style campaign camera: drag pan, wheel zoom (auto-tilt), orbit with middle/right drag or Q/E.
class_name MapCamera
extends Camera3D

var target := Vector3(180, 0, 60)
var dist := 60.0
var yaw := 0.0
var tilt_offset := 0.0
var _t_target := target
var _t_dist := dist
var _t_yaw := yaw
var _t_tilt := 0.0
var min_dist := 4.0
var max_dist := 230.0
var input_enabled := true
var _dragging := false
var _drag_moved := false
var _drag_start := Vector2.ZERO
var _orbiting := false
var fly_t := -1.0
var _fly_from := {}
var _fly_to := {}
var _fly_dur := 1.0

func _ready() -> void:
	fov = 40.0
	near = 0.05
	far = 2000.0
	_apply()

func pitch_for(d: float) -> float:
	# close up: low, cinematic angle; far out: near top-down
	var k := clampf((d - min_dist) / 120.0, 0.0, 1.0)
	return deg_to_rad(lerpf(-34.0, -72.0, sqrt(k))) + _t_tilt * 0 + tilt_offset

func look_at_world(p: Vector3, d: float = -1.0, instant: bool = false) -> void:
	_t_target = Vector3(p.x, 0, p.z)
	if d > 0:
		_t_dist = d
	if instant:
		target = _t_target; dist = _t_dist
		_apply()

func fly_to(p: Vector3, d: float, dur: float, y: float = INF) -> void:
	_fly_from = {"t": target, "d": dist, "y": yaw}
	_fly_to = {"t": Vector3(p.x, 0, p.z), "d": d, "y": yaw if y == INF else y}
	_fly_dur = dur
	fly_t = 0.0

func is_flying() -> bool:
	return fly_t >= 0.0

func handle_input(ev: InputEvent) -> bool:
	## returns true when the event was consumed as a camera drag (so it is not a click)
	if not input_enabled:
		return false
	if ev is InputEventMouseButton:
		var mb := ev as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
			_t_dist = clampf(_t_dist * 0.88, min_dist, max_dist)
			# zoom towards cursor
			return true
		if mb.button_index == MOUSE_BUTTON_WHEEL_DOWN and mb.pressed:
			_t_dist = clampf(_t_dist * 1.13, min_dist, max_dist)
			return true
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_dragging = true; _drag_moved = false; _drag_start = mb.position
			else:
				_dragging = false
				if _drag_moved:
					_drag_moved = false
					return true
		if mb.button_index == MOUSE_BUTTON_MIDDLE:
			_orbiting = mb.pressed
			return true
	elif ev is InputEventMouseMotion:
		var mm := ev as InputEventMouseMotion
		if _orbiting:
			_t_yaw -= mm.relative.x * 0.006
			tilt_offset = clampf(tilt_offset - mm.relative.y * 0.004, -0.35, 0.3)
			return true
		if _dragging:
			if mm.position.distance_to(_drag_start) > 6.0:
				_drag_moved = true
			if _drag_moved:
				var k := dist * 0.0016
				var right := Vector3(cos(yaw), 0, -sin(yaw))
				var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
				_t_target -= right * mm.relative.x * k
				_t_target -= fwd * -mm.relative.y * k
				target = _t_target
				return true
	return false

func _process(delta: float) -> void:
	if fly_t >= 0.0:
		fly_t += delta / _fly_dur
		var k := smoothstep(0.0, 1.0, minf(fly_t, 1.0))
		target = (_fly_from["t"] as Vector3).lerp(_fly_to["t"], k)
		dist = exp(lerpf(log(_fly_from["d"]), log(_fly_to["d"]), k))
		yaw = lerp_angle(_fly_from["y"], _fly_to["y"], k)
		_t_target = target; _t_dist = dist; _t_yaw = yaw
		if fly_t >= 1.0:
			fly_t = -1.0
		_apply()
		return
	if input_enabled:
		var mv := Vector2.ZERO
		if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP): mv.y -= 1
		if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN): mv.y += 1
		if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT): mv.x -= 1
		if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): mv.x += 1
		if Input.is_key_pressed(KEY_Q): _t_yaw += delta * 1.2
		if Input.is_key_pressed(KEY_E): _t_yaw -= delta * 1.2
		if mv != Vector2.ZERO:
			var right := Vector3(cos(yaw), 0, -sin(yaw))
			var fwd := Vector3(-sin(yaw), 0, -cos(yaw))
			_t_target += (right * mv.x - fwd * mv.y) * dist * 0.9 * delta
	_t_target.x = clampf(_t_target.x, 0.0, 360.0)
	_t_target.z = clampf(_t_target.z, 8.0, 172.0)
	var a := 1.0 - exp(-delta * 9.0)
	target = target.lerp(_t_target, a)
	dist = lerpf(dist, _t_dist, a)
	yaw = lerp_angle(yaw, _t_yaw, a)
	_apply()

func _apply() -> void:
	var p := pitch_for(dist)
	var dir := Vector3(sin(yaw) * cos(p), sin(p), cos(yaw) * cos(p))
	# dir points from camera towards target (downwards); camera sits opposite
	var ground_y := GameData.surface_y(target.x, target.z) if GameData.loaded else 0.0
	var look := Vector3(target.x, ground_y, target.z)
	global_position = look - Vector3(-sin(yaw) * cos(p), sin(p), -cos(yaw) * cos(p)) * dist
	look_at(look, Vector3.UP)
