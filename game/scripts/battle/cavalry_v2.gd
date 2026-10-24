extends RefCounted
## Cavalry animation overhaul (Rob, rob/cavalry-animation-overhaul). PRESENTATION ONLY.
## Swaps the three cavalry VATs (med_knight, c19_hussar, em_cuirassier) for the HX bakes of pipeline/blender/horse_anim.py
## (separate hx horse armature + char_rig rider on rider_seat, docs/cav/HORSE_SKELETON_SPEC.md). The assets keep the
## legacy model key, so multimesh keys / render_models / every sim read are unchanged; AnimCombat._update_cav drives the
## hz_* clips (gaits, charge, transitions, mounted melee, hit, death). ON by default; needs combat animation v1 (the
## hz_* clips are only driven by AnimCombat). Missing HX files -> legacy cavalry_<model> VAT, untouched.

static var on := true

const ENV_VAR := "IRONCROWNS_CAV_V2"                 # env var: 0/off/false disables, 1/on/true enables
const SETTING := "iron_crowns/battle/cav_v2"         # optional project setting (override.cfg)
const MODELS := ["med_knight", "em_cuirassier", "c19_hussar"]

## Precedence: command-line user arg > env var > setting > ON.  off: --no-cav-v2, --cav-v2=off|0|false|no
static func resolve_on(args: PackedStringArray, env: String, setting: Variant) -> bool:
	var res := true
	if setting is bool:
		res = setting
	var e := env.strip_edges().to_lower()
	if e in ["0", "off", "false", "no"]: res = false
	elif e in ["1", "on", "true", "yes"]: res = true
	for a in args:
		if a == "--no-cav-v2": res = false
		elif a == "--cav-v2": res = true
		elif a.begins_with("--cav-v2="):
			res = not (a.substr(9).to_lower() in ["off", "0", "false", "no"])
	return res

static func resolve_from_runtime() -> bool:
	return resolve_on(OS.get_cmdline_user_args(), OS.get_environment(ENV_VAR), ProjectSettings.get_setting(SETTING, null))

static func has_assets(name: String) -> bool:
	for lod in 2:
		if not ResourceLoader.exists("res://assets/models/cavalry_hx_%s_lod%d.glb" % [name, lod]) \
				or not FileAccess.file_exists("res://assets/vat/hx_%s_lod%d.json" % [name, lod]) \
				or not FileAccess.file_exists("res://assets/vat/hx_%s_lod%d.vat" % [name, lod]):
			return false
	return true

## file stems for a model: [glb prefix+name, vat name]. HX when the switch (and anim v1) is on and the bake exists.
static func files_for(name: String, anim_v1: bool) -> Array:
	if name in MODELS:
		if on and anim_v1 and has_assets(name):
			return ["cavalry_hx_" + name, "hx_" + name]
		return ["cavalry_" + name, name]
	return ["soldier_" + name, name]

## Horse v3 bakes (cavalry integration): "<vat>_lod<l>.vatn" RGBA8 per-frame normals when the json says "normals": "vatn".
## Returns null for every other VAT (legacy / proxy -> vat.gdshader with rest normals, unchanged).
static func nrm_tex(vat_name: String, lod: int, j: Dictionary) -> Texture2D:
	if str(j.get("normals", "")) != "vatn":
		return null
	var path := "res://assets/vat/%s_lod%d.vatn" % [vat_name, lod]
	if not FileAccess.file_exists(path):
		return null
	var b := FileAccess.get_file_as_bytes(path)
	if b.size() != int(j["vertices"]) * int(j["frames"]) * 4:
		return null
	return ImageTexture.create_from_image(Image.create_from_data(int(j["vertices"]), int(j["frames"]), false, Image.FORMAT_RGBA8, b))
