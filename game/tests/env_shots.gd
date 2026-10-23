extends Node
## Battlefield environment harness (env/scandinavia-medieval). Runs the production main scene with --demo=battle, waits
## until the battle sim reaches --at=<s>, freezes time (Engine.time_scale = 0, so before/after builds show the same sim
## state), then for each view sets a fixed overhead-rig pose, settles, screenshots, and times --frames=N frames
## (min / median / p95 wall ms; min is the most robust on a shared CPU + draw calls / primitives / objects from RenderingServer).
## Views are either formation-relative (sim regiment positions are identical before/after) or world-fixed (absolute
## field coordinates), so the same camera is used on the old and the new terrain.
## Usage: godot --path game --resolution 1600x900 res://tests/env_shots.tscn -- --demo=battle --year=1300 --nation=SWE
##        --quality=1 --out=<dir> --tag=<name> [--at=14] [--frames=20] [--views=a,b,c] [--env=0|1]
var main: Node
var out := ""; var tag := ""; var at := 14.0; var frames := 20
var views: PackedStringArray
var state := 0; var vi := 0; var fc := 0; var times := []; var draws := []; var prims := []; var objs := []; var last_us := 0
var report := {}
# name: [anchor, x, z, dist, pitch, yaw]   anchor: "c" = battle centroid + (x, z), "a" / "d" = first attacker / defender
# regiment + (x, z), "w" = world point (x, z). yaw is absolute (0 = camera south of the target looking north, +z).
const VIEWS := {
	"overview":   ["c", 60.0, 120.0, 360.0, -0.22, 0.35],
	"formation":  ["a", 0.0, 0.0, 34.0, -0.20, 0.45],
	"forest_edge": ["w", 215.0, 40.0, 75.0, -0.16, 1.75],
	"rocky":      ["w", -256.0, -215.0, 90.0, -0.24, -2.5],
	"water":      ["w", 360.0, 300.0, 170.0, -0.20, 0.9],
	"horizon":    ["c", 0.0, 0.0, 120.0, -0.06, 3.14159],
	"top":        ["c", 0.0, 0.0, 230.0, -0.85, 0.0],
}

func _ready() -> void:
	var a := {}
	for s in OS.get_cmdline_user_args():
		if s.begins_with("--"):
			var kv := s.substr(2).split("=", true, 1)
			a[kv[0]] = kv[1] if kv.size() > 1 else "1"
	out = a.get("out", "/tmp/envshots"); tag = a.get("tag", "x"); at = float(a.get("at", "14")); frames = int(a.get("frames", "20"))
	views = str(a.get("views", ",".join(VIEWS.keys()))).split(",")
	DirAccess.make_dir_recursive_absolute(out)
	main = load("res://scenes/main.tscn").instantiate()
	add_child(main)

func _pose(bv: Node, v: Array) -> void:
	var anchor := Vector2.ZERO
	match str(v[0]):
		"c": anchor = bv._centroid(-1)
		"a": anchor = bv.sim.regs[bv.first_reg(0)]["pos"]
		"d": anchor = bv.sim.regs[bv.first_reg(1)]["pos"]
	var t := anchor + Vector2(float(v[1]), float(v[2]))
	bv.cam_auto = false
	bv.blend_w = 0.0
	bv.cam_target = Vector3(t.x, 0, t.y); bv.cam_dist = float(v[3]); bv.cam_pitch = float(v[4]); bv.cam_yaw = float(v[5])
	bv._ct = Vector3(t.x, bv.h_at(t.x, t.y), t.y); bv._cd = float(v[3]); bv._cp = float(v[4]); bv._cy = float(v[5])
	bv._apply_cam()

func _process(_d: float) -> void:
	var bv = main.get("battle_view")
	match state:
		0:
			if main.get("in_battle") and not main.get("transitioning") and bv != null and float(bv.sim.t) >= at:
				Engine.time_scale = 0.0
				var b: Dictionary = bv.b
				var p: Dictionary = GameData.provinces[b["prov"]]
				report["battle"] = {"prov": b["prov"], "name": p["name"], "region": p["region"], "terrain": b["terrain"], "lat": p["lat"], "lon": p["lon"],
					"elev": p["elev"], "coastal": p["coastal"], "codes": b["codes"], "era": bv.era_id, "t": bv.sim.t, "biome": str(bv.get("biome"))}
				var ev = bv.get("env")
				if ev is Dictionary and ev.has("corridor"):
					report["battle"]["layout"] = {"corridor": str(ev["corridor"]), "lake_c": str(ev["lake_c"]), "rock_c": str(ev["rock_c"]), "water_h": ev["water_h"], "ms_ground": ev.get("ms_ground", 0), "ms_scenery": ev.get("ms_scenery", 0), "mmis": (ev.get("mmis", []) as Array).size(),
						"n_trees": (ev["plan"]["trees"] as Array).size(), "n_far": (ev["plan"]["far"] as Array).size(), "n_rocks": (ev["plan"]["rocks"] as Array).size(), "n_cover": (ev["plan"]["cover"] as Array).size()}
				print("ENVSHOT freeze ", JSON.stringify(report["battle"]))
				state = 1; vi = 0; fc = 0
		1:
			if vi >= views.size():
				var f := FileAccess.open(out.path_join("%s_report.json" % tag), FileAccess.WRITE)
				f.store_string(JSON.stringify(report, "  ")); f.close()
				print("ENVSHOT done"); get_tree().quit(); state = 9; return
			_pose(bv, VIEWS[views[vi]])
			state = 2; fc = 0
		2:
			_pose(bv, VIEWS[views[vi]])
			fc += 1
			if fc == 8:
				var img: Image = get_viewport().get_texture().get_image()
				img.save_png(out.path_join("%s_%s.png" % [tag, views[vi]]))
				times = []; draws = []; prims = []; objs = []; last_us = Time.get_ticks_usec(); cpu0 = _cpu_ms()
			elif fc > 8:
				var now := Time.get_ticks_usec(); times.append((now - last_us) / 1000.0); last_us = now
				draws.append(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME))
				prims.append(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME))
				objs.append(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME))
				if times.size() >= frames:
					var s := times.duplicate(); s.sort()
					var r := {"cpu_ms": (_cpu_ms() - cpu0) / frames, "min_ms": s[0], "median_ms": s[s.size() / 2], "p95_ms": s[int(s.size() * 0.95)], "draws": draws[-1], "prims": prims[-1], "objects": objs[-1]}
					report[views[vi]] = r
					print("ENVPERF tag=%s view=%s cpu_ms=%.1f min_ms=%.1f median_ms=%.1f p95_ms=%.1f draws=%d prims=%d objs=%d" % [tag, views[vi], r["cpu_ms"], r["min_ms"], r["median_ms"], r["p95_ms"], r["draws"], r["prims"], r["objects"]])
					vi += 1; state = 1

var cpu0 := 0.0
## process CPU time (all threads incl. llvmpipe rasteriser workers), ms: robust on a shared, loaded box where
## wall-clock frame time depends on what other jobs are running
func _cpu_ms() -> float:
	var f := FileAccess.open("/proc/self/stat", FileAccess.READ)
	if f == null:
		return 0.0
	var parts := f.get_line().get_slice(")", 1).strip_edges().split(" ")
	return (float(parts[11]) + float(parts[12])) * 10.0
