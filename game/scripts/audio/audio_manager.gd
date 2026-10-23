extends Node
## Iron Crowns audio system (autoload "Audio").
## Music state machine with equal-power crossfades, pooled/voice-limited SFX, ambience beds and
## Music/SFX volume settings (persisted in user://audio.cfg).
## Strictly read-only towards the simulation: it listens to Sim signals and *reads* the watched
## BattleView's event list with its own cursor and its own RNG, so sim results/hashes are unaffected.

const CFG_PATH := "user://audio.cfg"
const MUSIC_DIR := "res://audio/music/"
const SFX_DIR := "res://audio/sfx/"
const TRACKS := {"campaign": "music_campaign", "tension": "music_tension", "battle": "music_battle"}
const TRACK_DB := {"campaign": 0.0, "tension": 0.0, "battle": -3.0}   # battle music sits under the gunfire
const XFADE := {"campaign": 3.0, "tension": 2.5, "battle": 1.4}
const MIN_HOLD := 6.0            # seconds a mood is held before leaving it (no ping-pong)
const MAX_VOICES := 24           # global positional+2D one-shot voice cap
const FAR_DIST := 260.0          # metres: beyond this the distant variant is used
const SILENT_DB := -60.0
const BOOT_FRAMES := 10
const BOOT_DELAY := 0.4          # s before music starts: smoother start, and runs that quit within a
                                 # few frames (compile checks) don't leave a playback in the AudioServer
# category -> max simultaneous voices, min gap between starts (s), base gain (dB), priority
const CAT := {
	"musket": [6, 0.05, 0.0, 2], "rifle": [6, 0.05, -1.0, 2], "bow": [4, 0.08, -4.0, 2],
	"cannon": [4, 0.10, 1.0, 3], "explosion": [4, 0.08, -1.0, 3], "impact": [4, 0.06, -7.0, 1],
	"whistle": [2, 0.3, -9.0, 1], "pistol": [3, 0.05, -6.0, 1], "melee": [3, 0.12, -8.0, 1],
	"crowd": [2, 0.8, -7.0, 2], "hooves": [2, 0.8, -6.0, 2], "signal": [1, 2.0, -4.0, 4], "ui": [4, 0.03, -4.0, 5],
}
const VARIANTS := {
	"musket_volley": 3, "musket_volley_far": 2, "rifle_volley": 3, "rifle_volley_far": 2, "cannon": 3, "cannon_far": 2,
	"bombard": 2, "howitzer": 2, "howitzer_far": 1, "tank_gun": 2, "explosion": 3, "explosion_far": 2, "ball_impact": 3,
	"shell_whistle": 2, "bow_volley": 2, "pistol": 2, "crowd_charge": 2, "hooves_charge": 2, "sword_clash": 4,
	"crowd_cheer": 1, "crowd_rout": 1, "musket_shot": 3,
}

var enabled := true
const DEFAULT_MUSIC := 0.6       # music sits under the battle SFX by default (see test "mix balance")
const DEFAULT_SFX := 0.85
var music_volume := DEFAULT_MUSIC
var sfx_volume := DEFAULT_SFX
var rng := RandomNumberGenerator.new()
var streams := {}
var missing := {}                # names that fell back to synthesized placeholders
var mood := ""
var mood_t := 0.0
var _want := "campaign"
var mood_override := ""          # forces a mood (tests, trailers); "" = automatic
var last_played := ""            # name of the most recent one-shot (tests)
var _mp: Array[AudioStreamPlayer] = []
var _cur := 0
var _xf := 1.0                   # 0..1 progress of current crossfade
var _xf_len := 2.0
var _resume := {}                # track -> playback position to resume from
var _duck := 0.0                 # dB applied to music under stings
var _sting: AudioStreamPlayer
var tension_until := -1.0
var _clock := 0.0
var _pool3: Array[AudioStreamPlayer3D] = []
var _pool2: Array[AudioStreamPlayer] = []
var _voices: Array = []          # [{p, cat, t0, pri}]
var _last := {}                  # cat -> last start time
var _recent: Array = []          # start times of gunfire, for density gain
var _beds := {}                  # name -> AudioStreamPlayer (looped ambience)
var stats := {"played": 0, "dropped": 0, "stolen": 0, "by_cat": {}}
# battle tracking
var _bv: Node = null
var _bv_idx := 0
var _bv_result := false
var _pending: Array = []         # delayed positional sounds [time, name, cat, pos, db]
# campaign tracking
var _arm_goal := {}
var _win_vis := {}
var _toast := ""
var _sel := ""
var _poll := 0.0
var _gain := [0.0, 0.0]          # per music player: the TRACK_DB trim of the track it holds
var _frames := 0
var _main: Node = null            # the running main scene (found via node_added / current_scene)
var _views: Array = []           # BattleView instances seen (weak refs)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	rng.seed = 0x1C0A5D
	var args := OS.get_cmdline_user_args()
	if "--audio=off" in args:
		enabled = false
	ensure_buses()
	load_settings()
	for i in 2:
		var p := AudioStreamPlayer.new(); p.bus = &"Music"; p.volume_db = SILENT_DB
		add_child(p); _mp.append(p)
	_sting = AudioStreamPlayer.new(); _sting.bus = &"Music"; add_child(_sting)
	for i in MAX_VOICES:
		var p3 := AudioStreamPlayer3D.new()
		p3.bus = &"SFX"; p3.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
		p3.unit_size = 110.0; p3.max_distance = 2200.0; p3.panning_strength = 0.8
		p3.attenuation_filter_cutoff_hz = 9000.0; p3.attenuation_filter_db = -10.0
		p3.doppler_tracking = AudioStreamPlayer3D.DOPPLER_TRACKING_DISABLED
		add_child(p3); _pool3.append(p3)
	for i in 8:
		var p2 := AudioStreamPlayer.new(); p2.bus = &"UI"; add_child(p2); _pool2.append(p2)
	if not enabled:
		return
	Sim.event_logged.connect(_on_event)
	Sim.era_changed.connect(func(_e = null): sting("sting_era"))
	Sim.battle_resolved.connect(_on_battle_resolved)
	Sim.armies_changed.connect(_on_armies_changed)
	get_tree().node_added.connect(_on_node_added)
	# music starts from _process after BOOT_DELAY / BOOT_FRAMES (short fade-in)

# ---------------------------------------------------------------- buses
## Builds Master/Music/SFX(+Ambience, UI) if the project's bus layout did not provide them.
func ensure_buses() -> void:
	if AudioServer.get_bus_index(&"Master") >= 0 and AudioServer.get_bus_effect_count(0) == 0:
		var ml := AudioEffectHardLimiter.new(); ml.ceiling_db = -0.3
		AudioServer.add_bus_effect(0, ml)
	for spec in [["Music", "Master"], ["SFX", "Master"], ["Ambience", "SFX"], ["UI", "SFX"]]:
		if AudioServer.get_bus_index(StringName(spec[0])) < 0:
			AudioServer.add_bus()
			var i := AudioServer.bus_count - 1
			AudioServer.set_bus_name(i, spec[0]); AudioServer.set_bus_send(i, StringName(spec[1]))
			if spec[0] == "SFX":
				var c := AudioEffectCompressor.new(); c.threshold = -8.0; c.ratio = 2.5; c.attack_us = 3000.0; c.release_ms = 220.0
				AudioServer.add_bus_effect(i, c)
				var hl := AudioEffectHardLimiter.new(); hl.ceiling_db = -1.5
				AudioServer.add_bus_effect(i, hl)
			elif spec[0] == "Music":
				AudioServer.set_bus_volume_db(i, -2.0)

func _bus_base_db(bus: String) -> float:
	return -2.0 if bus == "Music" else 0.0

func set_volume(which: String, v: float, save := true) -> void:
	v = clampf(v, 0.0, 1.0)
	if which == "music": music_volume = v
	else: sfx_volume = v
	_apply_volumes()
	if save:
		save_settings()

func _apply_volumes() -> void:
	for spec in [["Music", music_volume], ["SFX", sfx_volume]]:
		var i := AudioServer.get_bus_index(StringName(spec[0]))
		if i < 0: continue
		var v: float = spec[1]
		AudioServer.set_bus_mute(i, v <= 0.001)
		# perceptual curve: slider^2 ~ loudness
		AudioServer.set_bus_volume_db(i, _bus_base_db(spec[0]) + linear_to_db(maxf(v * v, 0.00001)))

func load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(CFG_PATH) == OK:
		music_volume = clampf(float(cf.get_value("audio", "music", music_volume)), 0.0, 1.0)
		sfx_volume = clampf(float(cf.get_value("audio", "sfx", sfx_volume)), 0.0, 1.0)
	_apply_volumes()

func save_settings() -> void:
	var cf := ConfigFile.new()
	cf.set_value("audio", "music", music_volume)
	cf.set_value("audio", "sfx", sfx_volume)
	cf.save(CFG_PATH)

## Settings rows for the in-game menu (called from Hud.build_settings).
func build_settings_rows(box: VBoxContainer, label_fn: Callable) -> void:
	for spec in [["Music", "music"], ["Sound effects", "sfx"]]:
		var h := HBoxContainer.new(); h.add_theme_constant_override("separation", 8)
		var l: Label = label_fn.call(spec[0], 14); l.custom_minimum_size = Vector2(130, 0); h.add_child(l)
		var s := HSlider.new(); s.min_value = 0; s.max_value = 100; s.step = 5
		s.custom_minimum_size = Vector2(240, 28); s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		s.value = round((music_volume if spec[1] == "music" else sfx_volume) * 100.0)
		s.name = "Vol_" + spec[1]
		var pct: Label = label_fn.call("%d%%" % int(s.value), 14)
		var key: String = spec[1]
		s.value_changed.connect(func(v: float): set_volume(key, v / 100.0, false); pct.text = "%d%%" % int(v))
		s.drag_ended.connect(func(_c: bool): save_settings(); if key == "sfx": ui("ui_click"))
		s.focus_exited.connect(save_settings)
		h.add_child(s); h.add_child(pct)
		box.add_child(h)

# ---------------------------------------------------------------- streams
func stream(name: String) -> AudioStream:
	if streams.has(name):
		return streams[name]
	var path := (MUSIC_DIR if name.begins_with("music_") or name.begins_with("sting_") else SFX_DIR) + name + ".ogg"
	var s: AudioStream = null
	if ResourceLoader.exists(path):
		s = load(path)
	if s == null:
		s = _fallback(name)
		missing[name] = true
	if s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = name.begins_with("music_") or name.ends_with("_loop") or name.begins_with("amb_")
	streams[name] = s
	return s

## Runtime fallback if an asset is missing (e.g. stripped build): tiny synthesized placeholder so
## gameplay feedback still works. Music falls back to silence.
func _fallback(name: String) -> AudioStream:
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS; w.mix_rate = 22050; w.stereo = false
	var n := 0; var boom := false
	if name.begins_with("music_") or name.begins_with("sting_"):
		n = 2205
	elif name.begins_with("ui_"):
		n = 1300
	else:
		n = 11025; boom = true
	var data := PackedByteArray(); data.resize(n * 2)
	var r := RandomNumberGenerator.new(); r.seed = hash(name)
	var lp := 0.0
	for i in n:
		var t := float(i) / 22050.0
		var v := 0.0
		if name.begins_with("music_") or name.begins_with("sting_"):
			v = 0.0
		elif boom:
			lp += (r.randf_range(-1, 1) - lp) * 0.08
			v = (lp * 2.5 + sin(TAU * 55.0 * t) * 0.6) * exp(-t * 7.0)
		else:
			v = sin(TAU * 1400.0 * t) * exp(-t * 90.0) * 0.5
		data.encode_s16(i * 2, int(clampf(v, -1, 1) * 30000))
	w.data = data
	if name.ends_with("_loop") or name.begins_with("amb_"):
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD; w.loop_end = n
	return w

# ---------------------------------------------------------------- music
func set_mood(m: String, fade := -1.0) -> void:
	if m == mood or not TRACKS.has(m):
		return
	var old := _mp[_cur]
	if mood != "" and old.playing:
		_resume[mood] = old.get_playback_position()
	var nxt := 1 - _cur
	var p := _mp[nxt]
	p.stream = stream(TRACKS[m])
	p.volume_db = SILENT_DB
	var from: float = 0.0
	if m != "battle" and _resume.has(m):
		from = float(_resume[m])     # campaign/tension resume where they left off; battle always opens at the top
	var len := p.stream.get_length() if p.stream != null else 0.0
	p.play(fmod(from, len) if len > 1.0 else 0.0)
	_gain[nxt] = float(TRACK_DB.get(m, 0.0))
	_cur = nxt
	_xf = 0.0
	_xf_len = maxf(XFADE.get(m, 2.0) if fade < 0.0 else fade, 0.001)
	mood = m
	mood_t = 0.0

func _update_music(delta: float) -> void:
	mood_t += delta
	if _xf < 1.0:
		_xf = minf(1.0, _xf + delta / _xf_len)
	var duck_target := -9.0 if _sting.playing else 0.0
	_duck = move_toward(_duck, duck_target, delta * (30.0 if duck_target < _duck else 6.0))
	var a := _mp[_cur]; var b := _mp[1 - _cur]
	# equal-power crossfade
	a.volume_db = maxf(SILENT_DB, linear_to_db(maxf(sin(_xf * PI * 0.5), 0.0001))) + _duck + float(_gain[_cur])
	b.volume_db = maxf(SILENT_DB, linear_to_db(maxf(cos(_xf * PI * 0.5), 0.0001))) + _duck + float(_gain[1 - _cur])
	if _xf >= 1.0 and b.playing:
		b.stop()
	if _want != mood and (mood_t > MIN_HOLD or _want == "battle" or mood == "battle"):
		set_mood(_want)

func sting(name: String) -> void:
	if not enabled:
		return
	_sting.stream = stream(name)
	_sting.volume_db = -1.0
	_sting.play()

func main_node() -> Node:
	if _main != null and is_instance_valid(_main) and _main.is_inside_tree():
		return _main
	var cs := get_tree().current_scene
	return cs if cs != null and "hud" in cs else null

## The BattleView currently on screen (visible, set up), or null.
func battle_view() -> Node:
	var keep: Array = []
	var found: Node = null
	for w in _views:
		var v: Variant = w.get_ref()
		if v == null or not is_instance_valid(v):
			continue
		keep.append(w)
		if v.is_inside_tree() and v.is_visible_in_tree() and v.get("sim") != null:
			found = v
	_views = keep
	return found

func _decide_mood() -> String:
	if mood_override != "":
		return mood_override
	if battle_view() != null:
		return "battle"
	var main := main_node()
	if main == null:
		return "campaign"
	if _clock < tension_until:
		return "tension"
	var hud: Variant = main.get("hud") if "hud" in main else null
	if hud != null and is_instance_valid(hud):
		for wn in ["diplo_win", "deploy_win"]:
			var w: Variant = hud.get(wn)
			if w is Control and (w as Control).visible:
				return "tension"
		var pop: Variant = hud.get("popup")
		if pop is Control and (pop as Control).visible:
			return "tension"
	return "campaign"

# ---------------------------------------------------------------- sfx core
func _cat_cfg(cat: String) -> Array:
	return CAT.get(cat, [4, 0.05, -6.0, 1])

func pick(base: String) -> String:
	var n: int = VARIANTS.get(base, 0)
	return base if n <= 0 else "%s_%d" % [base, rng.randi_range(1, n)]

func _claim(cat: String, pool: Array) -> Node:
	var cfg := _cat_cfg(cat)
	var now := _clock
	if now - float(_last.get(cat, -99.0)) < float(cfg[1]):
		stats["dropped"] += 1
		return null
	# drop finished voices
	_voices = _voices.filter(func(v): return is_instance_valid(v["p"]) and v["p"].playing)
	var same := _voices.filter(func(v): return v["cat"] == cat)
	if same.size() >= int(cfg[0]):
		var oldest: Dictionary = same[0]
		oldest["p"].stop(); _voices.erase(oldest); stats["stolen"] += 1
	for p in pool:
		if not p.playing:
			return p
	# pool exhausted (global cap): steal the oldest voice of lower-or-equal priority in this pool
	var best: Dictionary = {}
	for v in _voices:
		if v["p"] in pool and int(v["pri"]) <= int(cfg[3]):
			best = v; break
	if best.is_empty():
		stats["dropped"] += 1
		return null
	best["p"].stop(); _voices.erase(best); stats["stolen"] += 1
	return best["p"]

func _start(p: Node, name: String, cat: String, db: float, pitch_jit := 0.08) -> void:
	var cfg := _cat_cfg(cat)
	p.stream = stream(name)
	last_played = name
	p.pitch_scale = rng.randf_range(1.0 - pitch_jit, 1.0 + pitch_jit)
	p.volume_db = float(cfg[2]) + db + rng.randf_range(-2.0, 2.0)
	p.play()
	_last[cat] = _clock
	_voices.append({"p": p, "cat": cat, "t0": _clock, "pri": cfg[3]})
	stats["played"] += 1
	stats["by_cat"][cat] = int(stats["by_cat"].get(cat, 0)) + 1

## 2D (non-positional) one-shot on the UI bus.
func ui(name: String, db := 0.0) -> void:
	if not enabled:
		return
	var p := _claim("ui", _pool2)
	if p != null:
		p.bus = &"UI"
		_start(p, name, "ui", db, 0.03)

func play2d(name: String, cat: String, db := 0.0) -> void:
	if not enabled:
		return
	var p := _claim(cat, _pool2)
	if p != null:
		p.bus = &"SFX"
		_start(p, name, cat, db)

## Positional one-shot (battle). `far_base` is used instead of `base` beyond FAR_DIST.
func play3d(base: String, cat: String, pos: Vector3, db := 0.0, far_base := "") -> void:
	if not enabled:
		return
	var d := _listener_dist(pos)
	var name := base
	if far_base != "" and d > FAR_DIST:
		name = far_base
	# density gain: many shots in a short window should not sum into a wall of distortion
	if cat in ["musket", "rifle", "cannon", "explosion", "bow", "pistol"]:
		_recent = _recent.filter(func(t): return _clock - t < 1.0)
		_recent.append(_clock)
		db -= 2.0 * log(1.0 + _recent.size() / 6.0) / log(2.0)
	var p := _claim(cat, _pool3)
	if p == null:
		return
	(p as AudioStreamPlayer3D).global_position = pos
	_start(p, pick(name), cat, db)

func _listener_dist(pos: Vector3) -> float:
	var cam := get_viewport().get_camera_3d()
	return cam.global_position.distance_to(pos) if cam != null else 0.0

func active_voices(cat := "") -> int:
	var n := 0
	for v in _voices:
		if is_instance_valid(v["p"]) and v["p"].playing and (cat == "" or v["cat"] == cat):
			n += 1
	return n

# ---------------------------------------------------------------- ambience beds
func bed(name: String, target_db: float, delta: float, rate := 6.0) -> void:
	var p: AudioStreamPlayer = _beds.get(name)
	if p == null:
		if target_db <= SILENT_DB + 1.0:
			return
		p = AudioStreamPlayer.new(); p.bus = &"Ambience"; p.stream = stream(name); p.volume_db = SILENT_DB
		add_child(p); _beds[name] = p
		var len := p.stream.get_length()
		p.play(rng.randf_range(0.0, maxf(len - 0.1, 0.0)))
	p.volume_db = move_toward(p.volume_db, target_db, delta * rate * 8.0)
	if p.volume_db <= SILENT_DB + 0.5 and target_db <= SILENT_DB + 1.0:
		p.stop(); p.queue_free(); _beds.erase(name)

func _beds_off(delta: float) -> void:
	for k in _beds.keys():
		bed(k, SILENT_DB, delta, 3.0)

# ---------------------------------------------------------------- main loop
func _process(delta: float) -> void:
	_clock += delta
	_frames += 1
	if not enabled or _clock < BOOT_DELAY or _frames < BOOT_FRAMES:
		return
	if mood == "":
		set_mood(mood_override if mood_override != "" else _decide_mood(), 1.0)
	_poll -= delta
	if _poll <= 0.0:
		_poll = 0.2
		_want = _decide_mood()
		_poll_ui()
	_update_music(delta)
	_update_battle(delta)

func _update_battle(delta: float) -> void:
	var bv := battle_view()
	if bv != _bv:
		_bv = bv
		_pending.clear()
		if bv != null:
			_bv_idx = bv.sim.events.size()     # only sound new events; never replay history
			_bv_result = false
			_battle_start_signal(bv)
	if _bv == null:
		_beds_off(delta)
		return
	var sim: Variant = _bv.sim
	var evs: Array = sim.events
	while _bv_idx < evs.size():
		_battle_event(evs[_bv_idx])
		_bv_idx += 1
	# delayed impacts
	var i := 0
	while i < _pending.size():
		var q: Array = _pending[i]
		if _clock >= float(q[0]):
			play3d(q[1], q[2], q[3], q[4], q[5]); _pending.remove_at(i)
		else:
			i += 1
	if _bv.get("result_shown") == true and not _bv_result:
		_bv_result = true
		var ps: int = int(_bv.b.get("player_side", -1)) if _bv.get("b") is Dictionary else -1
		var res: Dictionary = sim.result() if sim.has_method("result") else {}
		if ps >= 0 and res.has("winner"):
			sting("sting_victory" if int(res["winner"]) == ps else "sting_defeat")
	# continuous beds
	var era: String = str(_bv.get("era_id"))
	var moving := 0; var melee := 0; var veh := 0; var alive := 0
	for r in sim.regs:
		var st: String = r["state"]
		if st in ["dead", "fled"]: continue
		alive += 1
		if st == "melee": melee += 1
		if r["kind"] == "veh": veh += 1
		elif r["moving"] and st != "rout": moving += 1
	var fin: bool = _bv.get("finished") == true
	var amb := "amb_battle_medieval" if era == "medieval" else ("amb_battle_modern" if era in ["c20", "modern"] else "amb_battle_powder")
	for a in ["amb_battle_medieval", "amb_battle_modern", "amb_battle_powder"]:
		bed(a, (-14.0 if not fin else -24.0) if a == amb else SILENT_DB, delta, 2.0)
	bed("amb_wind", -16.0, delta, 2.0)
	bed("march_loop", SILENT_DB if moving == 0 or fin else clampf(-20.0 + 3.0 * log(moving) / log(2.0), -20.0, -9.0), delta, 3.0)
	bed("melee_loop", SILENT_DB if melee == 0 or fin else clampf(-16.0 + 3.0 * log(melee) / log(2.0), -16.0, -7.0), delta, 3.0)
	bed("engine_loop", SILENT_DB if veh == 0 or fin else clampf(-18.0 + 2.0 * log(veh) / log(2.0), -18.0, -10.0), delta, 2.0)
	if melee > 0 and rng.randf() < delta * minf(melee, 6) * 1.2:
		var hs: Vector2 = _bv._hot_spot() if _bv.has_method("_hot_spot") else Vector2.ZERO
		play3d("sword_clash" if era in ["medieval", "early_modern", "c19"] else "pistol", "melee", Vector3(hs.x + rng.randf_range(-20, 20), 1.5, hs.y + rng.randf_range(-20, 20)), -2.0)

func _reg_pos(r: Dictionary) -> Vector3:
	var p: Vector2 = r["pos"]
	var h := 0.0
	if _bv.has_method("h_at"):
		h = _bv.h_at(p.x, p.y)
	return Vector3(p.x, h + 1.6, p.y)

func _battle_start_signal(bv: Node) -> void:
	var era: String = str(bv.get("era_id"))
	var name := "war_horn" if era in ["medieval", "early_modern"] else ("bugle_call" if era == "c19" else "whistle")
	play2d(name, "signal", -3.0)

## Weapon sound for a firing regiment, chosen strictly from its era + kind (no automatic weapons pre-1900).
static func weapon_for(r: Dictionary) -> Array:
	var era: String = r["def"]["era"]
	match r["kind"]:
		"vat":
			if era == "medieval": return ["bow_volley", "", "bow"]
			if era in ["early_modern", "c19"]: return ["musket_volley", "musket_volley_far", "musket"]
			return ["rifle_volley", "rifle_volley_far", "rifle"]
		"gun":
			if era == "medieval": return ["bombard", "cannon_far", "cannon"]
			if era in ["early_modern", "c19"]: return ["cannon", "cannon_far", "cannon"]
			return ["howitzer", "howitzer_far", "cannon"]
		"veh":
			return ["tank_gun", "cannon_far", "cannon"]
		"cav":
			if era in ["early_modern", "c19"]: return ["pistol", "", "pistol"]
	return []

func _battle_event(e: Dictionary) -> void:
	var sim: Variant = _bv.sim
	var k: String = str(e.get("k", ""))
	var si: int = int(e.get("s", -1))
	if si < 0 or si >= sim.regs.size():
		if k == "end": play2d("crowd_cheer", "crowd", -4.0)
		return
	var r: Dictionary = sim.regs[si]
	var pos := _reg_pos(r)
	match k:
		"volley":
			var w := weapon_for(r)
			if w.is_empty(): return
			play3d(w[0], w[2], pos, 0.0, w[1])
			var di: int = int(e.get("d", -1))
			if r["kind"] in ["gun", "veh"] and di >= 0 and di < sim.regs.size():
				var tp := _reg_pos(sim.regs[di])
				var era: String = r["def"]["era"]
				var spd := 400.0 if r["kind"] == "veh" else (160.0 if era in ["medieval", "early_modern", "c19"] else 260.0)
				var dt := clampf(pos.distance_to(tp) / spd / maxf(float(_bv.get("time_scale")), 1.0), 0.15, 4.0)
				if era in ["c20", "modern"]:
					if r["kind"] == "gun": _pending.append([_clock + dt * 0.6, "shell_whistle", "whistle", tp, 0.0, ""])
					_pending.append([_clock + dt, "explosion", "explosion", tp, 0.0, "explosion_far"])
				else:
					_pending.append([_clock + dt, "ball_impact", "impact", tp, 0.0, ""])
		"charge":
			play3d("crowd_charge", "crowd", pos, 0.0)
			if r["kind"] == "cav": play3d("hooves_charge", "hooves", pos, 0.0)
		"rout":
			play3d("crowd_rout", "crowd", pos, -2.0)
		"destroyed":
			if r["kind"] == "veh": play3d("explosion", "explosion", pos, 0.0, "explosion_far")
		"end":
			play2d("crowd_cheer", "crowd", -4.0)

# ---------------------------------------------------------------- campaign / UI hooks
func _on_node_added(n: Node) -> void:
	if n is BattleView:
		_views.append(weakref(n))
	elif n.scene_file_path == "res://scenes/main.tscn":
		_main = n
	if n is BaseButton and not (n as BaseButton).pressed.is_connected(_on_button):
		(n as BaseButton).pressed.connect(_on_button)

func _on_button() -> void:
	ui("ui_click")

func _on_event(ev: Variant) -> void:
	if not (ev is Dictionary):
		return
	var kind: String = str(ev.get("kind", ""))
	if kind == "war":
		if Sim.player in (ev.get("nations", []) as Array):
			sting("sting_war"); tension_until = _clock + 30.0

func _on_battle_resolved(bid: int, res: Dictionary) -> void:
	var b: Dictionary = Sim.battles.get(bid, {})
	if b.is_empty() or int(b.get("player_side", -1)) < 0 or _bv != null:
		return
	ui("ui_confirm" if int(res.get("winner", -1)) == int(b["player_side"]) else "ui_error", -2.0)

func _on_armies_changed(_a = null) -> void:
	for aid in Sim.armies:
		var a: Dictionary = Sim.armies[aid]
		if a.get("owner") != Sim.player:
			continue
		var g: int = int(a.get("goal", -1)) if not (a.get("path", []) as Array).is_empty() else -1
		if g >= 0 and _arm_goal.get(aid, -1) != g:
			ui("ui_march", -3.0)
		_arm_goal[aid] = g

func _poll_ui() -> void:
	var main := main_node()
	if main == null:
		return
	var hud: Variant = main.get("hud")
	if hud == null or not is_instance_valid(hud):
		return
	for wn in ["diplo_win", "econ_win", "deploy_win", "menu_win", "popup"]:
		var w: Variant = hud.get(wn)
		if not (w is Control):
			continue
		var vis := (w as Control).is_visible_in_tree()
		if _win_vis.has(wn) and _win_vis[wn] != vis:
			ui("ui_open" if vis else "ui_close", -2.0)
		_win_vis[wn] = vis
	var t: Variant = hud.get("toast")
	if t is Label and float(hud.get("toast_t")) > 3.0 and (t as Label).text != _toast:
		_toast = (t as Label).text
		var low := _toast.to_lower()
		if low.contains("not enough") or low.contains("cannot") or low.contains("no route") or low.contains("only ") or low.contains("invalid"):
			ui("ui_error")
	var mp: Variant = main.get("map") if "map" in main else null
	if mp != null and is_instance_valid(mp):
		var sel := "%s/%s" % [str(mp.get("selected_pid")), str(mp.get("selected_army"))]
		if sel != _sel and _sel != "" and sel != "-1/-1":
			ui("ui_select", -3.0)
		_sel = sel


## Stop every player and drop cached streams on shutdown, so no AudioStreamPlayback is still
## registered with the AudioServer when the engine exits (avoids "leaked instance" warnings).
func shutdown() -> void:
	for c in get_children():
		if c is AudioStreamPlayer or c is AudioStreamPlayer3D:
			c.stop()
			c.stream = null
	_beds.clear()
	streams.clear()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		shutdown()


func _exit_tree() -> void:
	shutdown()
