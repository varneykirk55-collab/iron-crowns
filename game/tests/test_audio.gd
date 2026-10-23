extends Node
## Headless audio-system checks. Run:
##   tools/godot --headless --path game res://tests/test_audio.tscn -- --results=/path/audio_results.json
## Exit code = number of failures. Real mixing is verified with an AudioEffectCapture on Master
## (the headless Dummy driver still runs the mixer).

var results: Array = []
var fails := 0
var out_path := "user://audio_test_results.json"
var cap: AudioEffectCapture
var env_on := false
var env: Array[float] = []      # short-window RMS (dBFS) of each drained capture chunk
var cap_peak := 0.0
var cap_sq := 0.0
var cap_n := 0

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--results="):
			out_path = a.substr(10)
	call_deferred("_run")

func check(name: String, ok: bool, detail: String = "") -> bool:
	results.append({"test": name, "pass": ok, "detail": detail})
	if not ok:
		fails += 1
	print(("  [PASS] " if ok else "  [FAIL] ") + name + ("  -- " + detail if detail != "" else ""))
	return ok

func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
		_drain()

func _secs(t: float) -> void:
	var t0 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t0 < int(t * 1000.0):
		await get_tree().process_frame
		_drain()

func _drain() -> void:
	if cap == null:
		return
	var n := cap.get_frames_available()
	if n <= 0:
		return
	var buf := cap.get_buffer(n)
	for v in buf:
		var m := maxf(absf(v.x), absf(v.y))
		cap_peak = maxf(cap_peak, m)
		cap_sq += v.x * v.x + v.y * v.y
	cap_n += buf.size() * 2
	if env_on:
		var sq := 0.0
		for v in buf:
			sq += v.x * v.x + v.y * v.y
		env.append(linear_to_db(sqrt(sq / (buf.size() * 2)) + 1e-9))

func _cap_reset() -> void:
	_drain(); cap_peak = 0.0; cap_sq = 0.0; cap_n = 0

func _cap_rms_db() -> float:
	return linear_to_db(sqrt(cap_sq / maxf(cap_n, 1)) + 1e-9)

func _run() -> void:
	var t0 := Time.get_ticks_msec()
	GameData.load_all()
	var A: Node = get_node("/root/Audio")
	print("== Audio: buses & assets ==")
	var bnames := []
	for i in AudioServer.bus_count: bnames.append(str(AudioServer.get_bus_name(i)))
	check("buses Master/Music/SFX/Ambience/UI exist", bnames.has("Music") and bnames.has("SFX") and bnames.has("Ambience") and bnames.has("UI"), str(bnames))
	var sfx_i := AudioServer.get_bus_index(&"SFX")
	var fx := []
	for j in AudioServer.get_bus_effect_count(sfx_i): fx.append(AudioServer.get_bus_effect(sfx_i, j).get_class())
	var mfx := []
	for j in AudioServer.get_bus_effect_count(0): mfx.append(AudioServer.get_bus_effect(0, j).get_class())
	check("SFX bus has compressor + hard limiter, Master has limiter", fx.has("AudioEffectCompressor") and fx.has("AudioEffectHardLimiter") and mfx.has("AudioEffectHardLimiter"), "SFX %s, Master %s" % [fx, mfx])
	check("Ambience and UI buses route into SFX (one SFX slider)", AudioServer.get_bus_send(AudioServer.get_bus_index(&"Ambience")) == &"SFX" and AudioServer.get_bus_send(AudioServer.get_bus_index(&"UI")) == &"SFX")
	var man: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://audio/audio_manifest.json"))
	var bad := []; var loops := 0; var total_b := 0; var secs := 0.0
	for k in man:
		var m: Dictionary = man[k]
		var s: AudioStream = A.stream(k)
		total_b += int(m["bytes"]); secs += float(m["seconds"])
		if not (s is AudioStreamOggVorbis): bad.append(k + ":type"); continue
		if absf(s.get_length() - float(m["seconds"])) > 0.06: bad.append("%s:len %.2f/%.2f" % [k, s.get_length(), m["seconds"]])
		if bool(s.loop) != bool(m["loop"]): bad.append(k + ":loop")
		if float(m["peak_dbfs"]) > -0.9: bad.append(k + ":peak")
		if m["loop"]: loops += 1
	check("all %d manifest assets load as Ogg Vorbis with correct length/loop flag/peak" % man.size(), bad.is_empty() and A.missing.is_empty(), "%d loops, %.1f s audio, %.2f MiB; bad %s" % [loops, secs, total_b / 1048576.0, str(bad)])
	var need := ["music_campaign", "music_tension", "music_battle", "sting_victory", "sting_defeat", "sting_war", "sting_era", "war_horn", "bugle_call", "whistle",
		"march_loop", "melee_loop", "engine_loop", "amb_battle_powder", "amb_battle_modern", "amb_battle_medieval", "amb_wind", "ui_click", "ui_select", "ui_open", "ui_close", "ui_confirm", "ui_error", "ui_march"]
	for base in A.VARIANTS:
		for v in int(A.VARIANTS[base]): need.append("%s_%d" % [base, v + 1])
	var miss := need.filter(func(n): return not man.has(n))
	check("every sound the manager references is shipped", miss.is_empty(), str(miss))

	print("== Audio: era-correct weapon mapping ==")
	var wrong := []
	var mapped := []
	for uid in GameData.units:
		var d: Dictionary = GameData.units[uid]
		if float(d["range"]) <= 0.0: continue
		var w: Array = A.weapon_for({"def": d, "kind": d["kind"]})
		var e: String = d["era"]
		var snd: String = w[0] if not w.is_empty() else "none"
		mapped.append("%s:%s" % [uid, snd])
		var okk := true
		if e in ["medieval", "early_modern", "c19"] and (snd.begins_with("rifle") or snd in ["howitzer", "tank_gun", "explosion"]): okk = false
		if e in ["c20", "modern"] and (snd.begins_with("musket") or snd in ["bow_volley", "bombard"]): okk = false
		if e == "medieval" and d["kind"] == "vat" and snd != "bow_volley": okk = false
		if not okk or w.is_empty(): wrong.append("%s(%s)->%s" % [uid, e, snd])
	check("ranged units map to era-correct weapon sounds (no rifles/automatic fire before 1900)", wrong.is_empty(), "bad %s; %s" % [str(wrong), ", ".join(mapped)])

	print("== Audio: volume settings ==")
	var mv0: float = A.music_volume; var sv0: float = A.sfx_volume
	A.set_volume("music", 0.5); A.set_volume("sfx", 0.3)
	var mi := AudioServer.get_bus_index(&"Music")
	check("music slider -> Music bus dB", absf(AudioServer.get_bus_volume_db(mi) - (-2.0 + linear_to_db(0.25))) < 0.01, "%.2f dB" % AudioServer.get_bus_volume_db(mi))
	check("sfx slider -> SFX bus dB", absf(AudioServer.get_bus_volume_db(sfx_i) - linear_to_db(0.09)) < 0.01, "%.2f dB" % AudioServer.get_bus_volume_db(sfx_i))
	A.set_volume("music", 0.0)
	check("volume 0 mutes the bus", AudioServer.is_bus_mute(mi))
	A.set_volume("music", 0.4)
	var cf := ConfigFile.new(); cf.load(A.CFG_PATH)
	check("settings persisted to %s" % A.CFG_PATH, absf(float(cf.get_value("audio", "music", -1)) - 0.4) < 1e-6 and absf(float(cf.get_value("audio", "sfx", -1)) - 0.3) < 1e-6, "music %s sfx %s" % [cf.get_value("audio", "music"), cf.get_value("audio", "sfx")])
	A.music_volume = 0.9; A.sfx_volume = 0.9
	A.load_settings()
	check("settings reload restores saved values", absf(A.music_volume - 0.4) < 1e-6 and absf(A.sfx_volume - 0.3) < 1e-6 and not AudioServer.is_bus_mute(mi))
	var box := VBoxContainer.new(); add_child(box)
	A.build_settings_rows(box, func(t: String, _sz: int): var l := Label.new(); l.text = t; return l)
	var sl: HSlider = box.find_child("Vol_music", true, false)
	var ss: HSlider = box.find_child("Vol_sfx", true, false)
	var ok_ui := sl != null and ss != null and is_equal_approx(sl.value, 40.0) and is_equal_approx(ss.value, 30.0)
	if ok_ui:
		sl.value = 80.0; ss.value = 65.0
		ss.drag_ended.emit(true)
	var cf2 := ConfigFile.new(); cf2.load(A.CFG_PATH)
	check("settings sliders drive and persist Music/SFX volume", ok_ui and absf(A.music_volume - 0.8) < 1e-6 and absf(A.sfx_volume - 0.65) < 1e-6 and absf(float(cf2.get_value("audio", "sfx", -1)) - 0.65) < 1e-6, "music %.2f sfx %.2f" % [A.music_volume, A.sfx_volume])
	box.queue_free()
	A.set_volume("music", 1.0); A.set_volume("sfx", 1.0)

	print("== Audio: music playback & crossfades ==")
	cap = AudioEffectCapture.new(); cap.buffer_length = 2.0
	AudioServer.add_bus_effect(0, cap)
	await _secs(0.3)
	A.set_mood("campaign", 0.0)
	_cap_reset()
	await _secs(1.5)
	var p: AudioStreamPlayer = A._mp[A._cur]
	check("campaign music plays and advances", A.mood == "campaign" and p.playing and p.get_playback_position() > 0.8, "pos %.2f s" % p.get_playback_position())
	check("mixer output is audible (Master capture)", cap_n > 20000 and _cap_rms_db() > -45.0, "%d samples, RMS %.1f dBFS, peak %.3f" % [cap_n, _cap_rms_db(), cap_peak])
	var old_p := p
	A.mood_override = "battle"
	A.set_mood("battle")
	await _secs(A.XFADE["battle"] * 0.5)
	var np: AudioStreamPlayer = A._mp[A._cur]
	# remove the per-track trims (TRACK_DB) to look at the crossfade law itself
	var ga := db_to_linear(np.volume_db - float(A._gain[A._cur])); var gb := db_to_linear(old_p.volume_db - float(A._gain[1 - A._cur]))
	check("crossfade mid-point: both tracks playing, equal power", np.playing and old_p.playing and ga > 0.3 and gb > 0.3 and absf(ga * ga + gb * gb - 1.0) < 0.12, "in %.2f out %.2f (sum sq %.2f)" % [ga, gb, ga * ga + gb * gb])
	await _secs(A.XFADE["battle"] * 0.6 + 0.2)
	check("crossfade completes: old track stopped, battle at full level", not old_p.playing and np.playing and absf(np.volume_db - float(A.TRACK_DB["battle"])) < 0.5 and A.mood == "battle", "battle %.1f dB (track trim %.1f)" % [np.volume_db, A.TRACK_DB["battle"]])
	A.mood_override = "campaign"
	A.set_mood("campaign", 0.3)
	await _secs(0.6)
	check("campaign resumes where it left off", A._mp[A._cur].get_playback_position() > 1.2, "pos %.2f" % A._mp[A._cur].get_playback_position())
	var lp: AudioStreamPlayer = A._mp[A._cur]
	var L := lp.stream.get_length()
	lp.seek(L - 0.4)
	await _secs(0.9)
	check("music loops seamlessly past the end", lp.playing and lp.get_playback_position() < 1.0, "pos after wrap %.2f of %.1f" % [lp.get_playback_position(), L])
	A.sting("sting_war")
	await _secs(0.4)
	check("sting plays and ducks music", A._sting.playing and A._duck < -5.0, "duck %.1f dB" % A._duck)
	A._sting.stop()
	A.mood_override = ""

	print("== Audio: SFX polyphony & limiting ==")
	A.set_volume("music", 0.0)
	await _secs(0.3)
	var cam := Camera3D.new(); add_child(cam); cam.position = Vector3(0, 40, 80); cam.current = true
	_cap_reset()
	var max_m := 0; var max_all := 0; var req := 0
	for f in 90:
		for k in 6:
			A.play3d("musket_volley", "musket", Vector3(randf_range(-60, 60), 0, randf_range(-60, 60)), 0.0, "musket_volley_far"); req += 1
		for k in 3:
			A.play3d("cannon", "cannon", Vector3(randf_range(-80, 80), 0, randf_range(-80, 80)), 0.0, "cannon_far"); req += 1
		A.play3d("explosion", "explosion", Vector3(0, 0, 0)); req += 1
		await get_tree().process_frame
		_drain()
		max_m = maxi(max_m, A.active_voices("musket")); max_all = maxi(max_all, A.active_voices())
	await _secs(0.5)
	check("musket voices capped (%d requested)" % req, max_m <= int(A.CAT["musket"][0]) and max_m >= 2, "max musket %d / cap %d" % [max_m, A.CAT["musket"][0]])
	check("global voice cap holds", max_all <= A.MAX_VOICES, "max %d / %d" % [max_all, A.MAX_VOICES])
	check("mass gunfire does not clip (limiters)", cap_peak <= 1.0 and cap_peak > 0.05, "peak %.3f (%.2f dBFS), RMS %.1f dBFS" % [cap_peak, linear_to_db(cap_peak), _cap_rms_db()])
	A._last.clear()
	A.play3d("musket_volley", "musket", Vector3.ZERO, 0.0, "musket_volley_far")
	var near_name: String = A.last_played
	cam.position = Vector3(0, 300, 600)
	await get_tree().process_frame
	A._last.clear()
	A.play3d("musket_volley", "musket", Vector3.ZERO, 0.0, "musket_volley_far")
	var far_name: String = A.last_played
	check("distant variant chosen beyond %.0f m" % A.FAR_DIST, near_name.begins_with("musket_volley_") and not near_name.contains("far") and far_name.begins_with("musket_volley_far_"), "%s / %s" % [near_name, far_name])
	cam.queue_free()

	print("== Audio: live battle hookup (read-only) ==")
	A.set_volume("music", 1.0)
	A.stats["by_cat"] = {}
	var r1 := await _battle(true)
	var by: Dictionary = A.stats["by_cat"].duplicate()
	check("watched c19 battle drives SFX (volleys, cannon, signal)", int(by.get("musket", 0)) > 3 and int(by.get("cannon", 0)) > 0 and int(by.get("signal", 0)) == 1, str(by))
	check("battle music during battle, ambience beds ran", r1["mood_battle"] and r1["beds"] >= 2, "beds seen %d" % r1["beds"])
	var mix := await _battle_mix()
	check("battle SFX stand out over battle music (mix balance)", mix["sfx_p90"] >= mix["music_med"] + 6.0 and mix["sfx_max"] <= 0.0,
		"SFX-only p90 %.1f / max %.1f dBFS vs battle music median %.1f dBFS (%d / %d windows)" % [mix["sfx_p90"], mix["sfx_max"], mix["music_med"], mix["n_sfx"], mix["n_mus"]])
	A.enabled = false
	var r2 := await _battle(false)
	A.enabled = true
	check("battle outcome identical with audio on/off", r1["res"]["winner"] == r2["res"]["winner"] and r1["res"]["steps"] == r2["res"]["steps"] and str(r1["res"]["men"]) == str(r2["res"]["men"]),
		"winner %d/%d steps %d/%d" % [r1["res"]["winner"], r2["res"]["winner"], r1["res"]["steps"], r2["res"]["steps"]])
	await _secs(0.5)
	check("music returns to campaign after battle", A._want == "campaign", A._want)

	var summary := {"passed": results.size() - fails, "failed": fails, "total": results.size(), "seconds": (Time.get_ticks_msec() - t0) / 1000.0, "results": results}
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f: f.store_string(JSON.stringify(summary, "  "))
	print("\n==== %d / %d audio checks passed (%.1f s) ====" % [summary["passed"], summary["total"], summary["seconds"]])
	A.set_volume("music", mv0); A.set_volume("sfx", sv0)
	get_tree().quit(fails)

func _pct(a: Array[float], q: float) -> float:
	if a.is_empty():
		return -200.0
	var b := a.duplicate(); b.sort()
	return b[clampi(int(q * (b.size() - 1)), 0, b.size() - 1)]

## Real-time mix balance in a watched battle seen through the BattleView camera: SFX bus alone
## (Music muted) vs. battle music alone (SFX muted). Same volumes as the shipped defaults.
func _battle_mix() -> Dictionary:
	var A: Node = get_node("/root/Audio")
	var mv: float = A.music_volume; var sv: float = A.sfx_volume
	A.set_volume("music", A.DEFAULT_MUSIC, false); A.set_volume("sfx", A.DEFAULT_SFX, false)
	var mi := AudioServer.get_bus_index("Music"); var si := AudioServer.get_bus_index("SFX")
	Sim.auto_deploy = false
	Sim.auto_respond_player = "decline"
	Sim.new_game("SWE", 1800, 11)
	var tgt := ""
	for o in Sim.neighbors_of("SWE"):
		if Sim.can_declare_war("SWE", o)["ok"]:
			tgt = o; break
	Sim.declare_war("SWE", tgt)
	var mine: Dictionary = {}; var theirs: Dictionary = {}
	for a in Sim.armies.values():
		if a["owner"] == "SWE" and (mine.is_empty() or Sim.army_strength(a) > Sim.army_strength(mine)): mine = a
		if a["owner"] == tgt and (theirs.is_empty() or Sim.army_strength(a) > Sim.army_strength(theirs)): theirs = a
	var bid := Sim._start_battle(int(theirs["node"]), [mine["id"]], [theirs["id"]])
	Sim.deploy_battle(bid, {"objective": "assault", "formation": "line"}, true)
	var bv := BattleView.new()
	add_child(bv)
	bv.setup(bid)
	bv.time_scale = 1.0
	AudioServer.set_bus_mute(mi, true)
	await _secs(6.0)              # approach / first contact
	_cap_reset(); env.clear(); env_on = true
	await _secs(14.0)
	env_on = false
	var sfx_env: Array[float] = env.duplicate()
	AudioServer.set_bus_mute(mi, false); AudioServer.set_bus_mute(si, true)
	await _secs(1.0)
	_cap_reset(); env.clear(); env_on = true
	await _secs(6.0)
	env_on = false
	var mus_env: Array[float] = env.duplicate()
	AudioServer.set_bus_mute(si, false)
	remove_child(bv)
	bv.free()
	A.set_volume("music", mv, false); A.set_volume("sfx", sv, false)
	print("   SFX env p50 %.1f p90 %.1f max %.1f | music p50 %.1f p90 %.1f" % [_pct(sfx_env, 0.5), _pct(sfx_env, 0.9), _pct(sfx_env, 1.0), _pct(mus_env, 0.5), _pct(mus_env, 0.9)])
	return {"sfx_p90": _pct(sfx_env, 0.9), "sfx_max": _pct(sfx_env, 1.0), "music_med": _pct(mus_env, 0.5), "n_sfx": sfx_env.size(), "n_mus": mus_env.size()}

func _battle(audio_on: bool) -> Dictionary:
	var A: Node = get_node("/root/Audio")
	Sim.auto_deploy = false
	Sim.auto_respond_player = "decline"
	Sim.new_game("SWE", 1800, 11)
	var tgt := ""
	for o in Sim.neighbors_of("SWE"):
		if Sim.can_declare_war("SWE", o)["ok"]:
			tgt = o; break
	Sim.declare_war("SWE", tgt)
	var mine: Dictionary = {}; var theirs: Dictionary = {}
	for a in Sim.armies.values():
		if a["owner"] == "SWE" and (mine.is_empty() or Sim.army_strength(a) > Sim.army_strength(mine)): mine = a
		if a["owner"] == tgt and (theirs.is_empty() or Sim.army_strength(a) > Sim.army_strength(theirs)): theirs = a
	var bid := Sim._start_battle(int(theirs["node"]), [mine["id"]], [theirs["id"]])
	Sim.deploy_battle(bid, {"objective": "assault", "formation": "line"}, true)
	var bv := BattleView.new()
	add_child(bv)
	bv.setup(bid)
	bv.time_scale = 4.0
	var mood_b := false; var beds := 0
	var f := 0
	while not bv.result_shown and f < 4000:
		await get_tree().process_frame
		f += 1
		if audio_on:
			if A.mood == "battle": mood_b = true
			beds = maxi(beds, A._beds.size())
	var res: Dictionary = bv.sim.result()
	remove_child(bv)
	bv.free()
	return {"res": res, "mood_battle": mood_b, "beds": beds}
