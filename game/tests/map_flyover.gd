## Map flyover for --write-movie captures (graphics-map branch). Not part of the game.
## xvfb-run -a tools/godot --path game --resolution 1280x720 --fixed-fps 30 --write-movie /abs/fly.avi res://tests/map_flyover.tscn
extends Node

const KEYS := [
	# lon, lat, dist, yaw, seconds to reach next key
	[15.0, 28.0, 200.0, 0.0, 3.0],
	[12.0, 50.0, 70.0, 0.0, 2.5],
	[9.5, 46.3, 22.0, 0.0, 2.5],
	[8.0, 46.4, 8.0, 0.6, 3.0],
	[15.5, 59.5, 12.0, 0.3, 3.0],
	[60.0, 40.0, 60.0, 0.0, 3.0],
	[86.0, 29.5, 30.0, 0.0, 3.0],
	[137.5, 37.0, 25.0, -0.3, 2.5],
	[138.6, 35.6, 7.0, -0.4, 1.0],
]
var main: Node

func _ready() -> void:
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)
	await get_tree().process_frame
	main._start_game("SWE", 1800, 7)
	Sim.set_speed(0)
	if main.hud_layer:
		main.hud_layer.visible = false
	for i in 10:
		_set(KEYS[0][0], KEYS[0][1], KEYS[0][2], KEYS[0][3])
		await get_tree().process_frame
	var fps := 30.0
	for k in KEYS.size() - 1:
		var a: Array = KEYS[k]; var b: Array = KEYS[k + 1]
		var n := int(a[4] * fps)
		for f in n:
			var t := float(f) / n
			t = t * t * (3.0 - 2.0 * t)
			_set(lerpf(a[0], b[0], t), lerpf(a[1], b[1], t), exp(lerpf(log(a[2]), log(b[2]), t)), lerpf(a[3], b[3], t))
			await get_tree().process_frame
	for i in 20:
		await get_tree().process_frame
	get_tree().quit()

func _set(lon: float, lat: float, dist: float, yaw: float) -> void:
	var cam: MapCamera = main.cam
	cam.fly_t = -1.0
	var w: Vector2 = GameData.lonlat_to_world(lon, lat)
	cam._t_yaw = yaw; cam.yaw = yaw
	cam.look_at_world(Vector3(w.x, 0, w.y), dist, true)
	main.map.cam_dist = cam.dist
