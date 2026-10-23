## Iron Crowns visual pass: rendering-only hooks for battles (owned by the visual-dev workspace).
## Never reads or writes simulation state except to *observe* (sim.t, finished, result) for the debug logger.
##
## Intended integration (lead dev): at the end of BattleView.setup() call
##     preload("res://scripts/battle/battle_visuals.gd").apply(self)
## and from the game's quality setting:  preload(...).apply_quality(q)   # 0 low, 1 medium, 2 high (any order)
##
## Debug-only: when instanced as a Node under main.gd with --perflog / --bench / --vispass on the command line,
## it applies the pass to the live BattleView (if --vispass=1), logs frame times and render stats, and
## (with --bench) holds three fixed cameras for N frames each to measure identical views before/after.
extends Node

const VERSION := 2   # 0 = measurement only (baseline); 1 = c19 visual pass; 2 = + other eras (added one by one)
const ERAS := ["c19", "medieval", "early_modern", "c20", "modern"]  # eras with the reviewed pass; any era not listed keeps the legacy look untouched

## Per-era light / sky on top of the shared (c19-reviewed) setup. Only the keys listed differ from c19; the
## readability settings (FILMIC, exposure, sun energy / angle, contrast) stay identical across eras.
const ERA_ENV := {
	"c19": {},
	"medieval": {"sky_top": Color(0.27, 0.45, 0.7), "sky_horizon": Color(0.7, 0.73, 0.76), "sun_color": Color(1.0, 0.94, 0.82), "fog": 0.0005},
	"early_modern": {"sky_horizon": Color(0.68, 0.71, 0.75), "sun_color": Color(1.0, 0.95, 0.85)},
	"c20": {"sky_top": Color(0.33, 0.43, 0.58), "sky_horizon": Color(0.66, 0.68, 0.7), "sun_color": Color(1.0, 0.96, 0.9), "fog": 0.00055},
	"modern": {"sky_top": Color(0.24, 0.43, 0.72), "sky_horizon": Color(0.68, 0.73, 0.8), "sun_color": Color(1.0, 0.97, 0.92)},
}

# ------------------------------------------------------------------ static API
## Quality presets (rendering only). q = 0 low, 1 medium (= shipped defaults), 2 high.
## Applies to every era (MSAA / shadows / LOD / effects are cost knobs, not part of the c19 look).
const QUALITY := [
	{"name": "low", "msaa": Viewport.MSAA_DISABLED, "shadows": false, "shadow_dist": 260.0, "atlas": 2048,
		"soft": RenderingServer.SHADOW_QUALITY_HARD, "lod": 45.0, "char_lod": 20.0, "char_mid": 20.0, "glow": false, "aniso": Viewport.ANISOTROPY_2X},
	{"name": "medium", "msaa": Viewport.MSAA_2X, "shadows": true, "shadow_dist": 260.0, "atlas": 4096,
		"soft": RenderingServer.SHADOW_QUALITY_SOFT_LOW, "lod": 75.0, "char_lod": 30.0, "char_mid": 30.0, "glow": true, "aniso": Viewport.ANISOTROPY_4X},
	{"name": "high", "msaa": Viewport.MSAA_4X, "shadows": true, "shadow_dist": 300.0, "atlas": 4096,
		"soft": RenderingServer.SHADOW_QUALITY_SOFT_LOW, "lod": 120.0, "char_lod": 20.0, "char_mid": 45.0, "glow": true, "aniso": Viewport.ANISOTROPY_8X},
]
static var _quality := 1          # medium until apply_quality() is called
static var _bv_ref: WeakRef = null # last BattleView passed to apply(); weak so a freed battle is simply skipped
static var proto_v2 := false       # PROTO v2 (--vx-proto=1): c19_line draws the sculpted c19v2_line bake (docs/char/PROTO_V2.md)
static var char_sr := true         # character refinement: semi-realistic c19 soldiers (c19sr_*); --vx-char=0 = previous blocky models
static var polish := true          # polish pass (terrain-aware light, snow ground, grenadier / gun-crew models); false = v0.2.1 look
static var terrain_preview := ""   # PREVIEW-ONLY (--vx-terrain=<t>, bench logger): light / ground as if b.terrain were <t>

## Rendering-only tweaks for a freshly set-up BattleView. Touches environment, sun, materials, LOD distance,
## nothing else. Idempotent; may be called before or after apply_quality().
static func apply(bv: Node) -> void:
	if bv == null:
		return
	_bv_ref = weakref(bv)
	var era := str(bv.get("era_id"))
	if era in ERAS:
		var terr := _terrain(bv)
		_apply_environment(bv.get("environment"), bv.get("sun"), ERA_ENV.get(era, {}), terr if polish else "")
		if polish:
			_swap_models(bv, era)
		if char_sr:
			_swap_char(bv)
		_apply_materials(bv, era)
		if char_sr:
			_char_materials(bv)
		if polish or terrain_preview != "":
			_apply_ground_polish(bv, terr)
	_apply_scene_quality(bv)

static func _terrain(bv: Node) -> String:
	if terrain_preview != "":
		return terrain_preview
	var b = bv.get("b")
	return str(b.get("terrain", "")) if b is Dictionary else ""

## Store the quality level and apply it now to the root viewport and (if one was passed to apply() and is
## still alive) the current BattleView. Idempotent and order-independent with apply().
static func apply_quality(q: int) -> void:
	_quality = clampi(q, 0, QUALITY.size() - 1)
	var tree := Engine.get_main_loop() as SceneTree
	if tree != null and tree.root != null:
		apply_viewport(tree.root)
	var bv: Node = _bv_ref.get_ref() if _bv_ref != null else null
	if bv != null and is_instance_valid(bv) and bv.is_inside_tree():
		_apply_scene_quality(bv)

static func get_quality() -> int:
	return _quality

## Viewport part of the current quality level: MSAA, anisotropy, shadow atlas; never FXAA/TAA, native 3D scale.
static func apply_viewport(vp: Viewport) -> void:
	if vp == null:
		return
	var Q: Dictionary = QUALITY[_quality]
	vp.msaa_3d = Q["msaa"]
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
	vp.use_taa = false
	vp.scaling_3d_scale = 1.0
	vp.anisotropic_filtering_level = Q["aniso"]
	RenderingServer.directional_shadow_atlas_set_size(Q["atlas"], true)
	RenderingServer.directional_soft_shadow_filter_set_quality(Q["soft"])

## LOD switch distance for the current quality level. Debug / profiling: --vx-lod=<m> overrides it.
static var lod_override := -1.0
static func lod_dist(_bv: Node = null) -> float:
	if lod_override >= 0.0:
		return lod_override
	return float(QUALITY[_quality]["lod"])

## char_lod (stage 7): the refined c19 soldiers switch to their LOD1 geometry closer than BattleView's LOD_DIST
## (which stays 45 / 75 / 120: main's tests pin it). The LOD0 asset carries the LOD1 set too and char_vat.gdshader
## draws one of the two per instance by camera distance (the other collapses to a degenerate point), so this needs no
## BattleView change. Stage 9: char_lod = end of the LOD0 band (20 / 30 / 20 m; high adds a mid band, see char_mid).
## Debug: --vx-charlod=<m>.
static var char_lod_override := -1.0
static func char_lod_dist() -> float:
	if char_lod_override >= 0.0:
		return char_lod_override
	return float(QUALITY[_quality]["char_lod"])

## char_mid (stage 9): past char_lod the c19sr soldiers draw a ~1.3k-tri mid set (stored in the LOD0 asset between the
## LOD0 and LOD1 sets) out to char_mid, then the LOD1 set. char_mid <= char_lod = no mid band (stage 7 behaviour).
## high: LOD0 to 20 m, mid to 45 m, LOD1 beyond (BattleView LOD_DIST stays 120). Debug: --vx-charmid=<m>.
static var char_mid_override := -1.0
## Stage 9: mid / far sets (and the LOD1 material) lift dark coat wool towards the old c19 mid-distance read
## (char_vat coat_lift, 0..1; the close LOD0 set keeps its colours). Debug: --vx-coatlift=<0..1>.
static var coat_lift_override := -1.0
## Stage 9: distance team tint (char_vat team_tint / team_near / team_far): beyond ~25 m coats (and, weaker, trousers,
## belts, shako) blend towards the BattleView side colour, full at ~90 m, so the sides separate at mid / top zoom.
## Close-up uniforms keep their nation colours. Debug: --vx-teamtint=<0..1> (0 = off).
static var team_tint_override := -1.0
static func char_mid_dist() -> float:
	if char_mid_override >= 0.0:
		return char_mid_override
	return float(QUALITY[_quality]["char_mid"])

static func _char_lod_uniforms(bv: Node) -> void:
	var mms = bv.get("mms")
	if not (mms is Dictionary):
		return
	for key in mms.keys():
		var mmi = mms[key].get("mmi") if mms[key] is Dictionary else null
		if mmi is MultiMeshInstance3D and mmi.material_override is ShaderMaterial and str(key).ends_with("|0") \
				and (mmi.material_override as ShaderMaterial).get_shader_parameter("near_verts") != null:
			(mmi.material_override as ShaderMaterial).set_shader_parameter("char_lod_dist", char_lod_dist())
			(mmi.material_override as ShaderMaterial).set_shader_parameter("char_mid_dist", char_mid_dist())

## Scene part of the current quality level: sun shadows + distance, LOD switch distance, glow.
static func _apply_scene_quality(bv: Node) -> void:
	var Q: Dictionary = QUALITY[_quality]
	var sun = bv.get("sun")
	if sun is DirectionalLight3D:
		sun.shadow_enabled = Q["shadows"]
		sun.directional_shadow_max_distance = Q["shadow_dist"]
	var env = bv.get("environment")
	if env is Environment:
		env.glow_enabled = Q["glow"] and not ("--noglow" in OS.get_cmdline_user_args())
	if "LOD_DIST" in bv:
		bv.set("LOD_DIST", lod_dist(bv))
	_char_lod_uniforms(bv)

## Polish pass: per-terrain light on top of the era setup. snow = how much of the terrain-specific winter grade
## to apply (tundra 1, mountains partial). Only exposure / sun / sky tint / contrast; team dye is untouched.
const TERRAIN_ENV := {
	"tundra": {"snow": 1.0},
	"mountains": {"snow": 0.4},
}

static func _apply_environment(env: Environment, sun: DirectionalLight3D, e: Dictionary = {}, terrain: String = "") -> void:
	_apply_environment_v021(env, sun, e)
	if terrain == "" and not polish:
		return
	var k: float = float(TERRAIN_ENV.get(terrain, {}).get("snow", 0.0))
	if env != null:
		# Distance fog -> depth-range fog: the exponential fog put ~10 % haze over the whole field at the 230 m
		# top-down camera (and more over snow, whose albedo is close to the fog colour). Depth fog leaves the
		# battlefield (< ~260 m from the camera) clear and keeps the aerial perspective on the horizon / far hills.
		# (Godot's height fog is a per-fragment world-height term, not integrated along the view ray, so it would
		# haze troops standing in hollows at every distance; it is deliberately left off.)
		env.fog_mode = Environment.FOG_MODE_DEPTH
		env.fog_depth_begin = 260.0
		env.fog_depth_end = 2400.0
		env.fog_depth_curve = 0.8
		env.fog_density = lerpf(0.75, 0.6, k)   # ~ the v0.2.1 haze at 1-2 km, none on the field
		env.fog_height_density = 0.0
		env.fog_light_color = Color(0.68, 0.72, 0.78).lerp(Color(0.7, 0.75, 0.83), k)
		env.fog_sky_affect = 0.3
		# snow: a little less exposure + a touch more contrast so the near-white ground keeps texture and does not
		# flatten the light accents (pipeclay, plumes) of the troops standing on it
		env.tonemap_exposure = lerpf(1.08, 0.98, k)
		env.adjustment_contrast = lerpf(1.08, 1.12, k)
		env.ambient_light_energy = lerpf(0.75, 0.68, k)
		var sm: ProceduralSkyMaterial = env.sky.sky_material as ProceduralSkyMaterial if env.sky != null else null
		if sm != null and k > 0.0:
			sm.sky_horizon_color = sm.sky_horizon_color.lerp(Color(0.72, 0.75, 0.8), k)
			sm.ground_horizon_color = sm.ground_horizon_color.lerp(Color(0.7, 0.73, 0.77), k)
			sm.ground_bottom_color = sm.ground_bottom_color.lerp(Color(0.36, 0.36, 0.36), k)  # cool bounce off snow
	if sun != null and k > 0.0:
		sun.light_energy = lerpf(1.45, 1.32, k)
		sun.light_color = sun.light_color.lerp(Color(1.0, 0.96, 0.9), k)

static func _apply_ground_polish(bv: Node, terrain: String) -> void:
	for n in bv.find_children("*", "MeshInstance3D", true, false):
		var gm := (n as MeshInstance3D).material_override as ShaderMaterial
		if gm == null or gm.shader == null or not gm.shader.resource_path.ends_with("ground.gdshader"):
			continue
		if terrain_preview != "" and PREVIEW_TERRAIN.has(terrain_preview):
			var tp: Dictionary = PREVIEW_TERRAIN[terrain_preview]
			gm.set_shader_parameter("grass_a", tp["a"]); gm.set_shader_parameter("grass_b", tp["b"])
			gm.set_shader_parameter("dirt", tp["dirt"]); gm.set_shader_parameter("snow", tp["snow"])
		gm.set_shader_parameter("polish", 1.0 if polish else 0.0)

## PREVIEW-ONLY copy of BattleView._terrain_params() colours (ground colours only; relief and scenery stay those of
## the demo province) so a winter battle can be looked at from the demo / bench without touching battle data.
const PREVIEW_TERRAIN := {
	"tundra": {"a": Color(0.5, 0.52, 0.4), "b": Color(0.62, 0.6, 0.5), "dirt": Color(0.45, 0.42, 0.36), "snow": 0.75},
	"mountains": {"a": Color(0.36, 0.42, 0.26), "b": Color(0.46, 0.46, 0.36), "dirt": Color(0.42, 0.38, 0.32), "snow": 0.25},
}

## Polish pass: separate VAT models for units that share a glb with another unit (grenadiers = c19_line) and era
## gun-crew uniforms (BattleView.CREW_MODEL uses the era's line infantry). Same rig, clips, frame layout and UV2.y
## mask as the model they replace, so BattleView._update_units animates them unchanged. Adds the multimeshes the
## new model needs and repoints rv[i].model / rv[i].crew_model; idempotent; a missing asset keeps the legacy model.
## Becomes a no-op once units.json / CREW_MODEL name these models directly (Requests in out/INTEGRATION.md).
const UNIT_MODEL := {"c19": {"grenadiers": "c19_grenadier"}}   # era -> unit id -> VAT model
const CREW_UNIFORM := {"c19": "c19_artillery", "early_modern": "em_gunner"}   # c20 / modern crews wore infantry field dress

static func _has_vat(name: String) -> bool:
	for lod in 2:
		if not ResourceLoader.exists("res://assets/models/soldier_%s_lod%d.glb" % [name, lod]) \
				or not FileAccess.file_exists("res://assets/vat/%s_lod%d.json" % [name, lod]):
			return false
	return true

static func _add_vat_mms(bv: Node, model: String, side: int, cap: int) -> void:
	var vat: Dictionary = bv.call("_vat_model", model)
	for lod in 2:
		var e: Dictionary = bv.call("_mm", "%s|%d|%d" % [model, side, lod], vat["mesh"][lod], bv.call("_vat_mat", model, lod, side), cap, true)
		(e["mm"] as MultiMesh).instance_count = e["cap"]   # BattleView sized its multimeshes before apply(); size the new / grown ones
		e["buf"].resize(e["cap"] * e["stride"])

static func _swap_models(bv: Node, era: String) -> void:
	var rv = bv.get("rv"); var sim = bv.get("sim")
	if not (rv is Array) or sim == null or not bv.has_method("_vat_model") or not bv.has_method("_mm") or not bv.has_method("_vat_mat"):
		return
	var ok := {}
	for v in rv:
		var i: int = int(v.get("i", -1))
		if i < 0 or i >= sim.regs.size():
			continue
		var d: Dictionary = sim.regs[i]["def"]
		var side := int(v["side"])
		var ue := str(d.get("era", era))   # per unit, like BattleView.CREW_MODEL (mixed-era battles)
		var by_unit: Dictionary = UNIT_MODEL.get(ue, {})
		var crew: String = CREW_UNIFORM.get(ue, "")
		var want: String = by_unit.get(str(d.get("id", "")), "")
		if want != "" and str(v.get("kind", "")) == "vat" and v.get("model", "") != want:
			if not ok.has(want): ok[want] = _has_vat(want)
			if ok[want]:
				_add_vat_mms(bv, want, side, int(v["n"]) * 2)   # same capacity BattleView reserves (alive + dead rows)
				v["model"] = want
		if crew != "" and v.has("crew_model") and v["crew_model"] != crew:
			if not ok.has(crew): ok[crew] = _has_vat(crew)
			if ok[crew]:
				_add_vat_mms(bv, crew, side, int(v["n"]) * 3)
				v["crew_model"] = crew

# ------------------------------------------------------------------ character refinement (c19sr_*)
## Semi-realistic Napoleonic soldiers (pipeline/blender/char_*.py): same instance layout / clip names as the blocky
## c19 models they replace, so BattleView animates them unchanged. Swapped per model id (all c19 line infantry,
## grenadiers and gun crews); colours from a per-side nation palette texture (char_vat.gdshader).
const CHAR_MODEL := {"c19_line": "c19sr_line", "c19_grenadier": "c19sr_grenadier", "c19_artillery": "c19sr_artillery"}
## palette slots (order = pipeline/blender/char_body.SLOT_NAMES; UV.x = (slot + 0.5) / 32)
const CHAR_SLOTS := ["coat", "lapel", "collar", "cuff", "turnback", "waist", "breeches", "gaiter", "shoe", "plume", "felt",
	"metal", "belt", "cartbox", "knapsack", "roll", "skin", "hair", "eye", "mouth", "wood", "steel",
	"epaulette", "fur", "stock", "button", "gold", "sash", "boot", "sponge", "scabbard", "piping"]
## default = French line infantry 1810 (identical to char_body.PALETTE)
const CHAR_PALETTE := {
	"coat": "24408a", "lapel": "e9e6dc", "collar": "b5261f", "cuff": "b5261f", "turnback": "b5261f",
	"waist": "e9e6dc", "breeches": "e4e0d4", "gaiter": "1c1c1e", "shoe": "161515", "plume": "c8302a",
	"felt": "19191b", "metal": "b8913a", "belt": "eeede6", "cartbox": "1b1817", "knapsack": "80603e",
	"roll": "77716a", "skin": "d8a587", "hair": "3a291d", "eye": "1a1311", "mouth": "8c4c45",
	"wood": "5e3d24", "steel": "a2a8ae", "epaulette": "b5261f", "fur": "141313", "stock": "111111",
	"button": "c9a54a", "gold": "d2ab45", "sash": "b5261f", "boot": "121212", "sponge": "d8cfbf",
	"scabbard": "1f1b18", "piping": "b5261f"}
## Nation uniforms (overrides on CHAR_PALETTE). "facing" sets collar / cuff / turnback / epaulette / sash / piping.
## Nations not listed get a coat derived from their map colour (see _nation_palette).
const NATION_UNIFORM := {
	"FRA": {},
	"USA": {"coat": "1f2a4f", "lapel": "1f2a4f", "facing": "a8242a", "turnback": "e9e6dc", "plume": "e8e6df", "metal": "c9c9c4", "button": "d0d0cc"},
	"GBR": {"coat": "b3262a", "lapel": "b3262a", "facing": "d8b440", "turnback": "eeede6", "breeches": "8f8f8c", "plume": "eeede6", "epaulette": "eeede6"},
	"CAN": {"coat": "a92a2a", "lapel": "a92a2a", "facing": "1f3a6b", "turnback": "eeede6", "breeches": "8f8f8c", "plume": "2f6a3a", "epaulette": "eeede6"},
	"SWE": {"coat": "3a5a9a", "lapel": "e0b934", "facing": "e0b934", "plume": "e0b934", "metal": "c9c9c4"},
	"JPN": {"coat": "1b1f2b", "lapel": "1b1f2b", "facing": "a32020", "turnback": "a32020", "breeches": "e4e0d4", "plume": "e8e6df", "piping": "d2ab45"},
	"RUS": {"coat": "24452e", "lapel": "24452e", "facing": "b1302a", "plume": "141313", "breeches": "e4e0d4"},
	"AUT": {"coat": "e6e2d6", "lapel": "e6e2d6", "facing": "9b2232", "breeches": "e4e0d4", "plume": "d2ab45", "belt": "c9c3b2"},
	"DEU": {"coat": "1d2547", "lapel": "1d2547", "facing": "b1302a", "turnback": "b1302a", "breeches": "6f6f6c", "plume": "141313", "metal": "c9c9c4"},
	"ESP": {"coat": "e3dccb", "lapel": "6b2a6b", "facing": "6b2a6b", "plume": "b5261f", "belt": "c9c3b2"},
	"MEX": {"coat": "20306a", "lapel": "20306a", "facing": "a8242a", "plume": "2f7a3d"},
	"POL": {"coat": "20305e", "lapel": "b0203a", "facing": "b0203a", "plume": "eeede6", "metal": "c9c9c4"},
	"ITA": {"coat": "2c5a3a", "lapel": "e9e6dc", "facing": "b1302a", "plume": "e9e6dc"},
	"NLD": {"coat": "22325e", "lapel": "e9e6dc", "facing": "e07830", "plume": "e07830"},
	"PRT": {"coat": "1f2b55", "lapel": "1f2b55", "facing": "c0392b", "breeches": "1f2b55", "plume": "1f2b55"},
	"TUR": {"coat": "2b3f78", "lapel": "2b3f78", "facing": "b3262a", "breeches": "2b3f78", "plume": "b3262a"},
	# remaining majors (nations.json): period-flavoured c19 uniforms, kept apart from their neighbours' coats
	"BRA": {"coat": "1f2b55", "lapel": "1f2b55", "facing": "e0b934", "plume": "3a8a4a", "metal": "d2ab45"},
	"ARG": {"coat": "1f2a55", "lapel": "1f2a55", "facing": "78aee0", "plume": "e9e6dc", "turnback": "e9e6dc"},
	"COL": {"coat": "22306a", "lapel": "22306a", "facing": "c0392b", "plume": "e0c040", "metal": "d2ab45"},
	"PER": {"coat": "23305e", "lapel": "e9e6dc", "facing": "c0504d", "plume": "c0504d"},
	"CHL": {"coat": "1e2a52", "lapel": "1e2a52", "facing": "b1302a", "plume": "e9e6dc", "turnback": "e9e6dc"},
	"VEN": {"coat": "233a6a", "lapel": "233a6a", "facing": "e0b934", "plume": "c0392b"},
	"NOR": {"coat": "3a5f95", "lapel": "3a5f95", "facing": "b1302a", "plume": "b1302a", "metal": "c9c9c4"},
	"FIN": {"coat": "3d4a5c", "lapel": "3d4a5c", "facing": "e9e6dc", "breeches": "3d4a5c", "plume": "e9e6dc", "metal": "c9c9c4"},
	"DNK": {"coat": "b3262a", "lapel": "b3262a", "facing": "eeede6", "breeches": "8fa0b8", "plume": "eeede6", "metal": "c9c9c4"},
	"UKR": {"coat": "2a4a7a", "lapel": "2a4a7a", "facing": "e8d34a", "breeches": "2a4a7a", "plume": "e8d34a"},
	"GRC": {"coat": "233a70", "lapel": "233a70", "facing": "e9e6dc", "plume": "5f8ed0", "metal": "c9c9c4"},
	"ROU": {"coat": "22306a", "lapel": "22306a", "facing": "b1302a", "plume": "d0b040", "breeches": "8f8f8c"},
	"CHN": {"coat": "30395c", "lapel": "b3262a", "facing": "d8b030", "breeches": "30395c", "plume": "b3262a"},
	"IND": {"coat": "b3262a", "lapel": "b3262a", "facing": "e0b934", "breeches": "e9e6dc", "plume": "e09050", "epaulette": "eeede6"},
	"KOR": {"coat": "2a3f6a", "lapel": "2a3f6a", "facing": "c0392b", "plume": "1c1c1e"},
	"IDN": {"coat": "2c4a3a", "lapel": "2c4a3a", "facing": "e9e6dc", "breeches": "2c4a3a", "plume": "b05050"},
	"IRN": {"coat": "2a4a7a", "lapel": "2a4a7a", "facing": "c0392b", "breeches": "e9e6dc", "plume": "4a9a6a", "felt": "3a2a22"},
	"SAU": {"coat": "e3ddc8", "lapel": "e3ddc8", "facing": "2e7d32", "breeches": "e3ddc8", "plume": "2e7d32", "belt": "b49a6a"},
	"PAK": {"coat": "2a5a3a", "lapel": "2a5a3a", "facing": "e9e6dc", "plume": "e9e6dc", "metal": "c9c9c4"},
	"THA": {"coat": "2a3a7a", "lapel": "e9e6dc", "facing": "e9e6dc", "breeches": "e9e6dc", "plume": "6a5acd"},
	"VNM": {"coat": "a8302a", "lapel": "a8302a", "facing": "1c1c1e", "breeches": "1c1c1e", "plume": "e0b934", "turnback": "e0b934"},
	"PHL": {"coat": "e3dccb", "lapel": "2a4a8a", "facing": "2a4a8a", "plume": "5a7ab8", "belt": "c9c3b2"},
	"KAZ": {"coat": "2f6f88", "lapel": "2f6f88", "facing": "d0b040", "breeches": "3a2f28", "plume": "d0b040", "felt": "3a2f28"},
	"EGY": {"coat": "e3dccb", "lapel": "e3dccb", "facing": "a8242a", "breeches": "e3dccb", "felt": "a8242a", "plume": "1c1c1e", "belt": "b49a6a"},
	"NGA": {"coat": "2a5a3a", "lapel": "2a5a3a", "facing": "e0b934", "breeches": "e9e6dc", "plume": "e0b934"},
	"ZAF": {"coat": "8a7a55", "lapel": "8a7a55", "facing": "3a2f28", "breeches": "8a7a55", "plume": "2e5a2e", "belt": "6a4a2e", "felt": "4a3a28"},
	"ETH": {"coat": "e3dccb", "lapel": "e3dccb", "facing": "7aa040", "breeches": "e3dccb", "plume": "e0b934", "belt": "8a6a42"},
	"DZA": {"coat": "23305e", "lapel": "23305e", "facing": "b1302a", "breeches": "b1302a", "plume": "4a8a50"},
	"MAR": {"coat": "8a2a2a", "lapel": "8a2a2a", "facing": "2e6a3a", "breeches": "e3dccb", "felt": "8a2a2a", "plume": "2e6a3a"},
	"AUS": {"coat": "b3262a", "lapel": "b3262a", "facing": "1f2b55", "breeches": "1f2b55", "plume": "e9e6dc", "epaulette": "eeede6"},
	"NZL": {"coat": "1e2638", "lapel": "1e2638", "facing": "b3262a", "breeches": "1e2638", "plume": "e9e6dc"},
}
static var _pal_cache := {}

static func _hex(h: String) -> Color:
	return Color.html("#" + h)

static func _nation_palette(code: String, map_col: Color) -> Dictionary:
	var p := {}
	for k in CHAR_PALETTE: p[k] = _hex(CHAR_PALETTE[k])
	var u: Dictionary = {}
	if NATION_UNIFORM.has(code):
		u = NATION_UNIFORM[code]
	else:   # derived uniform: coat = darkened map colour, contrasting white / red facings
		var c := map_col
		var coat := Color.from_hsv(c.h, minf(c.s, 0.75), clampf(c.v * 0.62, 0.12, 0.6))
		if c.s < 0.15: coat = Color(0.88, 0.86, 0.8) if c.v > 0.7 else Color(0.25, 0.26, 0.28)
		u = {"coat": coat.to_html(false), "lapel": coat.to_html(false),
			"facing": ("e9e6dc" if coat.get_luminance() < 0.35 else "8a2222"), "plume": c.to_html(false)}
	for k in u:
		if k == "facing":
			for f in ["collar", "cuff", "turnback", "epaulette", "sash", "piping"]:
				if not u.has(f): p[f] = _hex(u[k])
		else:
			p[k] = _hex(u[k])
	return p

static func _palette_tex(p: Dictionary) -> ImageTexture:
	var img := Image.create(32, 1, false, Image.FORMAT_RGBA8)
	for i in CHAR_SLOTS.size():
		img.set_pixel(i, 0, p.get(CHAR_SLOTS[i], Color.MAGENTA))
	return ImageTexture.create_from_image(img)

## per-side palettes; when the two coats would read alike (mirror match, blue vs blue) one side wears its
## BattleView side colour (already contrast-adjusted against side 0) as the coat: the side whose nation coat is
## farther from its own side colour (so the coat agrees with the HUD / banner, e.g. 1800 NOR red vs SWE blue).
## Stage 9: the distance team tint in char_vat (team_tint) separates the sides at mid / top zoom on top of this.
static func _side_palettes(bv: Node) -> Array:
	var b = bv.get("b"); var sc = bv.get("side_col")
	var codes := ["FRA", "GBR"]
	if b is Dictionary and b.has("codes"): codes = [str(b["codes"][0]), str(b["codes"][1])]
	var cols := [Color(0.3, 0.4, 0.8), Color(0.8, 0.3, 0.3)]
	if sc is Array and sc.size() >= 2: cols = [sc[0], sc[1]]
	var ps := [_nation_palette(codes[0], cols[0]), _nation_palette(codes[1], cols[1])]
	var a: Color = ps[0]["coat"]; var c: Color = ps[1]["coat"]
	if _cdist(a, c) < 0.22:
		var i := 1 if _cdist(c, cols[1]) >= _cdist(a, cols[0]) else 0
		var t: Color = cols[i]
		ps[i]["coat"] = Color.from_hsv(t.h, minf(t.s, 0.8), clampf(t.v * 0.7, 0.15, 0.75)) if t.s > 0.15 else (Color(0.86, 0.85, 0.8) if t.v > 0.5 else Color(0.2, 0.2, 0.22))
		if NATION_UNIFORM.get(codes[i], {}).get("lapel", "") == NATION_UNIFORM.get(codes[i], {}).get("coat", "-"): ps[i]["lapel"] = ps[i]["coat"]
	return ps

static func _cdist(a: Color, c: Color) -> float:
	return Vector3(a.r - c.r, a.g - c.g, a.b - c.b).length()

## In-place swap: the regiments keep their model ids (c19_line / c19_grenadier / c19_artillery, as units.json and
## BattleView.CREW_MODEL name them) and their multimeshes; only the VAT data behind the id (bv.vat[id]: mesh, position
## texture, clip table) and the multimesh meshes are replaced by the c19sr_* bake. No new multimeshes, no instance or
## gameplay state touched. vat[id]["sr"] marks a swapped id (idempotent).
static func _swap_char(bv: Node) -> void:
	var vat = bv.get("vat"); var mms = bv.get("mms")
	if not (vat is Dictionary) or not (mms is Dictionary):
		return
	for orig in CHAR_MODEL:
		if not vat.has(orig) or vat[orig].has("sr"):
			continue
		var d := sr_vat(_char_model(orig))
		if d.is_empty():
			continue
		var ok := true
		for c in vat[orig]["json"][0]["clips"]:   # BattleView only asks for clips the old model had
			if not d["json"][0]["clips"].has(c): ok = false
		if not ok:
			continue
		vat[orig] = d
		for key in mms.keys():
			var parts := str(key).split("|")
			if parts.size() == 3 and parts[0] == orig:
				(mms[key]["mm"] as MultiMesh).mesh = d["mesh"][int(parts[2])]

## Proto v2: only c19_line is swapped (to c19v2_line, if baked); everything else keeps its c19sr_* model.
## The flag is read from the command line directly too, so it also works without the debug node (normal play).
static var _proto_cmd := -1
static func proto_on() -> bool:
	if _proto_cmd < 0:
		_proto_cmd = 0
		for a in OS.get_cmdline_user_args() + OS.get_cmdline_args():
			if a == "--vx-proto" or (a.begins_with("--vx-proto=") and a.substr(11) != "0"): _proto_cmd = 1
	return proto_v2 or _proto_cmd == 1

static func _char_model(orig: String) -> String:
	if proto_on() and orig == "c19_line" and _has_vat("c19v2_line"):
		return "c19v2_line"
	return CHAR_MODEL[orig]

## vat entry (BattleView vat[id] layout: mesh / tex / json per LOD, plus "sr") for a c19sr_* bake; {} if missing.
static func sr_vat(sr: String) -> Dictionary:
	if not _has_vat(sr):
		return {}
	var d := {"mesh": [], "tex": [], "json": [], "sr": sr}
	for lod in 2:
		d["mesh"].append(_sr_mesh("res://assets/models/soldier_%s_lod%d.glb" % [sr, lod]))
		var j: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/vat/%s_lod%d.json" % [sr, lod]))
		var bytes := FileAccess.get_file_as_bytes("res://assets/vat/%s_lod%d.vat" % [sr, lod])
		d["tex"].append(ImageTexture.create_from_image(Image.create_from_data(int(j["vertices"]), int(j["frames"]), false, Image.FORMAT_RGBF, bytes)))
		d["json"].append(j)
	if d["mesh"][0] == null or d["mesh"][1] == null:
		return {}
	return d

## Officer (for Rob's R3, render-only): OFFICER_MODEL is the model id BattleView would use for one officer per c19
## infantry regiment. BattleView side: `vat[BattleVisuals.OFFICER_MODEL] = BattleVisuals.officer_vat()` (skip if {}),
## then create the multimeshes "c19_officer|<side>|<lod>" with mesh vat[id]["mesh"][lod] (same layout / clip names
## as c19_line; die / die_b included) before BattleVisuals.apply(); _char_materials dresses them like any sr id
## (nation palette, team tint, LOD sets). No sim / units.json change.
const OFFICER_MODEL := "c19_officer"
static func officer_vat() -> Dictionary:
	return sr_vat("c19sr_officer")

static var _sr_meshes := {}
static func _sr_mesh(path: String) -> Mesh:
	if _sr_meshes.has(path):
		return _sr_meshes[path]
	var m: Mesh = null
	var ps = load(path)
	if ps is PackedScene:
		var n: Node = (ps as PackedScene).instantiate()
		var st: Array = [n]
		while not st.is_empty() and m == null:
			var x: Node = st.pop_back()
			if x is MeshInstance3D: m = (x as MeshInstance3D).mesh
			st.append_array(x.get_children())
		n.free()
	_sr_meshes[path] = m
	return m

## Stage 7: LOD0 = char_vat.gdshader (full), LOD1 = char_vat_lod1.gdshader (cheap compile-time variant, see
## char_vat.gdshaderinc). Debug / profiling only: --vx-charlite<lod>=NRM1,NOXF,... builds the variant from those defines.
static var char_lite_override := ["", ""]   # per-LOD define list from --vx-charlite0= / --vx-charlite1= ("" = shipped file)
static var _char_shaders := {}
static func _char_shader(lod: int) -> Shader:
	var ov: String = char_lite_override[lod]
	var k := "%d|%s" % [lod, ov]
	if _char_shaders.has(k):
		return _char_shaders[k]
	var sh: Shader
	if ov == "":
		sh = load("res://shaders/char_vat.gdshader" if lod == 0 else "res://shaders/char_vat_lod1.gdshader")
	else:
		var code := "shader_type spatial;\nrender_mode cull_disabled;\n"
		for d in ov.split(",", false):
			if d != "none": code += "#define CHAR_%s\n" % d.strip_edges().to_upper()
		sh = Shader.new()
		sh.code = code + "#include \"res://shaders/char_vat.gdshaderinc\"\n"
	_char_shaders[k] = sh
	return sh

static func _char_materials(bv: Node) -> void:
	var mms: Dictionary = bv.get("mms"); var vat: Dictionary = bv.get("vat")
	if mms == null or vat == null:
		return
	var pals := _side_palettes(bv)
	var ptex := [_palette_tex(pals[0]), _palette_tex(pals[1])]
	var sc = bv.get("side_col")
	var shaders := [_char_shader(0), _char_shader(1)]
	var v2_shader: Shader = null
	for key in mms.keys():
		var parts := str(key).split("|")
		if parts.size() != 3 or not vat.has(parts[0]) or not vat[parts[0]].has("sr"):
			continue
		var mmi: MultiMeshInstance3D = mms[key]["mmi"]
		var name := parts[0]; var side := int(parts[1]); var lod := int(parts[2])
		var shader: Shader = shaders[clampi(lod, 0, 1)]
		var v2 := str(vat[name]["sr"]).begins_with("c19v2_") and lod == 0
		if v2:
			if v2_shader == null: v2_shader = load("res://shaders/char_vat_v2.gdshader")
			shader = v2_shader
		if mmi.material_override is ShaderMaterial and (mmi.material_override as ShaderMaterial).shader == shader:
			continue   # idempotent
		var d: Dictionary = vat[name]
		var j: Dictionary = d["json"][lod]
		var m := ShaderMaterial.new()
		m.shader = shader
		m.set_shader_parameter("vat_tex", d["tex"][lod])
		m.set_shader_parameter("vat_verts", int(j["vertices"]))
		m.set_shader_parameter("vat_fps", float(j["fps"]))
		m.set_shader_parameter("palette", ptex[side])
		if sc is Array and side < sc.size(): m.set_shader_parameter("team_color", sc[side])
		var nt := _vatn_tex(str(d["sr"]), lod, int(j["vertices"]), int(j["frames"]))
		m.set_shader_parameter("has_normals", 1.0 if nt != null else 0.0)
		if nt != null: m.set_shader_parameter("vat_nrm", nt)
		var cl: Dictionary = j["clips"]
		if lod == 0 and j.has("near_verts"):   # stage 7: near / far geometry sets in one LOD0 mesh
			m.set_shader_parameter("near_verts", int(j["near_verts"]))
			m.set_shader_parameter("char_lod_dist", char_lod_dist())
			m.set_shader_parameter("mid_verts", int(j.get("mid_verts", -1)))
			m.set_shader_parameter("char_mid_dist", char_mid_dist())
		if coat_lift_override >= 0.0: m.set_shader_parameter("coat_lift", coat_lift_override)
		if team_tint_override >= 0.0: m.set_shader_parameter("team_tint", team_tint_override)
		if cl.has("die") and cl.has("die_b"):
			m.set_shader_parameter("die_row", float(cl["die"]["start"]))
			m.set_shader_parameter("die_b_row", float(cl["die_b"]["start"]))
		if v2 and j.has("maps"):
			var mt := _v2_maps(j["maps"])
			if mt.size() == 2:
				m.set_shader_parameter("v2_nmap", mt[0]); m.set_shader_parameter("v2_idmap", mt[1])
		mmi.material_override = m

## Clip crossfade for the c19sr_* shader (char_vat.gdshader reads instance COLOR = prev clip + weight). Call once per
## drawn soldier with the clip BattleView is about to draw (cur: 0-4 = idle/walk/run/fire/melee, 5 = dead) and use the
## returned Color as the instance colour; (1,1,1,1) = no blend. Per-soldier state lives in v["xf_*"]. Needs a one-line
## BattleView hook (see INTEGRATION.md Requests); without it the shader simply never blends.
const XFADE := 0.25   # s
static var xfade_on := true   # debug / profiling: --vx-xfade=0 disables the crossfade bookkeeping
static func xfade(v: Dictionary, k: int, cur: int, c: Vector2, ct: float, spd: float, vt: float, fps: float = 24.0) -> Color:
	if not xfade_on:
		return Color(1, 1, 1, 1)
	if not v.has("xf_id"):
		var n: int = int(v.get("n", 0))
		var ids := PackedInt32Array(); ids.resize(n); ids.fill(-1)
		var tt := PackedFloat32Array(); tt.resize(n); tt.fill(-100.0)
		var la := PackedFloat32Array(); la.resize(n * 4)
		var pr := PackedFloat32Array(); pr.resize(n * 4)
		v["xf_id"] = ids; v["xf_t"] = tt; v["xf_last"] = la; v["xf_prev"] = pr
	if k < 0 or k >= (v["xf_id"] as PackedInt32Array).size():
		return Color(1, 1, 1, 1)
	var ids2: PackedInt32Array = v["xf_id"]; var t2: PackedFloat32Array = v["xf_t"]
	var last: PackedFloat32Array = v["xf_last"]; var prev: PackedFloat32Array = v["xf_prev"]
	var j := k * 4
	var changed := ids2[k] != cur or absf(last[j + 2] - ct) > 0.02   # new clip, or the same one-shot clip restarted
	if changed:
		if ids2[k] >= 0:
			for q in 4: prev[j + q] = last[j + q]
			t2[k] = vt
		ids2[k] = cur
	last[j] = c.x; last[j + 1] = c.y; last[j + 2] = ct; last[j + 3] = spd
	if changed:
		v["xf_id"] = ids2; v["xf_t"] = t2; v["xf_prev"] = prev
	v["xf_last"] = last
	var w := clampf((vt - t2[k]) / XFADE, 0.0, 1.0)
	if w >= 1.0:
		return Color(1, 1, 1, 1)
	var e := maxf(vt - prev[j + 2], 0.0) * prev[j + 3]
	if prev[j + 1] > 0.0:
		e = fmod(e, prev[j + 1] / fps)
	else:
		e = minf(e, (absf(prev[j + 1]) - 1.0) / fps)
	return Color(prev[j], prev[j + 1], e, w)

## Gun-crew variant (Rob's R1 note): crews are several soldiers per gun, so xfade's per-soldier index k would collide.
## xfade_crew keys the state by (k, q) (gun k, crew member q < per) in its own sub-dictionary v["xf_crew"].
## BattleView: `_put(..., BattleVisuals.xfade_crew(v, k, q, cur, c, ct, spd, vt))` in the crew_model loop.
static func xfade_crew(v: Dictionary, k: int, q: int, cur: int, c: Vector2, ct: float, spd: float, vt: float, per: int = 3, fps: float = 24.0) -> Color:
	if not v.has("xf_crew"):
		v["xf_crew"] = {"n": int(v.get("n", 0)) * per}
	if q < 0 or q >= per:
		return Color(1, 1, 1, 1)
	return xfade(v["xf_crew"], k * per + q, cur, c, ct, spd, vt, fps)

## Proto v2 maps: PNG bytes (.vtex, not imported) for the normal + AO map and the slot-id map (c19v2_line_lod0.json "maps").
static var _v2_cache := {}
static func _v2_maps(mj: Dictionary) -> Array:
	var k := "%s|%s" % [mj.get("nrm", ""), mj.get("id", "")]
	if _v2_cache.has(k):
		return _v2_cache[k]
	var out := []
	var ni := Image.new(); var ii := Image.new()
	if ni.load_png_from_buffer(FileAccess.get_file_as_bytes("res://assets/vat/%s" % str(mj.get("nrm", "")))) == OK \
			and ii.load_png_from_buffer(FileAccess.get_file_as_bytes("res://assets/vat/%s" % str(mj.get("id", "")))) == OK:
		ni.convert(Image.FORMAT_RGBA8); ii.convert(Image.FORMAT_RGBA8)
		ni.generate_mipmaps()
		out = [ImageTexture.create_from_image(ni), ImageTexture.create_from_image(ii)]
	_v2_cache[k] = out
	return out

static var _vatn := {}
static func _vatn_tex(name: String, lod: int, verts: int, frames: int) -> ImageTexture:
	var k := "%s_%d" % [name, lod]
	if _vatn.has(k):
		return _vatn[k]
	var path := "res://assets/vat/%s_lod%d.vatn" % [name, lod]
	var t: ImageTexture = null
	if FileAccess.file_exists(path):
		var bytes := FileAccess.get_file_as_bytes(path)
		if bytes.size() == verts * frames * 4:
			t = ImageTexture.create_from_image(Image.create_from_data(verts, frames, false, Image.FORMAT_RGBA8, bytes))
	_vatn[k] = t
	return t

static func _apply_environment_v021(env: Environment, sun: DirectionalLight3D, e: Dictionary = {}) -> void:
	if env != null:
		var sm: ProceduralSkyMaterial = null
		if env.sky != null:
			sm = env.sky.sky_material as ProceduralSkyMaterial
		if sm != null:
			sm.sky_top_color = e.get("sky_top", Color(0.25, 0.42, 0.68))
			sm.sky_horizon_color = e.get("sky_horizon", Color(0.66, 0.71, 0.77))
			sm.ground_horizon_color = Color(0.62, 0.66, 0.66)
			sm.ground_bottom_color = Color(0.22, 0.23, 0.19)   # earthy bounce light from below
		env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
		env.ambient_light_energy = 0.75         # legacy value (0.62 measured as no visible change under GL Compatibility)
		env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
		# readability pass: FILMIC (as legacy) instead of ACES. ACES (exp 1.12, white 6) crushed the dark blue coats
		# and black kit towards black and over-saturated mid-tones; contrast now comes from the adjustment below.
		env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
		env.tonemap_exposure = 1.08
		env.tonemap_white = 1.0
		env.fog_light_color = Color(0.68, 0.72, 0.78)
		env.fog_density = e.get("fog", 0.00045)               # a touch more aerial perspective to separate distant lines
		env.fog_sky_affect = 0.3
		env.glow_enabled = true                  # glow only for HDR hot spots (muzzle flashes / fire), no full-screen haze
		env.glow_intensity = 0.3
		env.glow_bloom = 0.0
		env.glow_hdr_threshold = 1.1
		env.adjustment_enabled = true
		env.adjustment_contrast = 1.08
		env.adjustment_saturation = 1.0
	if sun != null:
		sun.rotation_degrees = Vector3(-36, 35, 0)
		sun.light_energy = 1.45                  # was 1.75: lower key/fill ratio so the shaded (camera-facing) backs read
		sun.light_color = e.get("sun_color", Color(1.0, 0.95, 0.86))
		sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL   # one pass; the 4096 atlas does the sharpening
		sun.shadow_bias = 0.1
		sun.shadow_normal_bias = 1.8
		sun.shadow_blur = 0.5
		sun.shadow_opacity = 0.92

## Per-era replacement meshes for props whose glb is shared between eras (art_cannon = early_modern culverins +
## c19 field guns; art_howitzer = c20 howitzers + modern rocket_art). Same groups / UV conventions / footprint, so
## the swap is purely visual. Becomes a no-op once units.json points those units at the era glbs directly
## (see Requests in out/INTEGRATION.md). Era-exclusive props (art_bombard) are rebuilt in place instead.
const PROP_SWAP := {
	"c19": {"art_cannon": "res://assets/models/art_field_gun_c19.glb"},
	"early_modern": {"art_cannon": "res://assets/models/art_culverin_em.glb"},
	"c20": {"art_howitzer": "res://assets/models/art_howitzer_c20.glb"},
	"modern": {"art_howitzer": "res://assets/models/art_howitzer_mod.glb"},
}

static func _glb_mesh(path: String) -> Mesh:
	var ps = load(path)
	if ps == null:
		return null
	var sc: Node = ps.instantiate()
	var stack := [sc]
	var out: Mesh = null
	while stack.size() > 0 and out == null:
		var n: Node = stack.pop_front()
		if n is MeshInstance3D:
			out = n.mesh
		stack.append_array(n.get_children())
	sc.free()
	return out

static func _swap_props(mms: Dictionary, era: String) -> void:
	var swap: Dictionary = PROP_SWAP.get(era, {})
	var cache := {}
	for key in mms.keys():
		var k := str(key)
		if not (k.begins_with("P") or k.begins_with("W")):
			continue
		var model := k.substr(1).get_slice("|", 0)
		if not swap.has(model):
			continue
		if not cache.has(model):
			cache[model] = _glb_mesh(swap[model]) if ResourceLoader.exists(swap[model]) else null
		if cache[model] != null:
			(mms[key]["mm"] as MultiMesh).mesh = cache[model]

static func _apply_materials(bv: Node, era: String = "c19") -> void:
	var mms: Dictionary = bv.get("mms")
	_swap_props(mms, era)
	for key in mms.keys():
		var mmi: MultiMeshInstance3D = mms[key]["mmi"]
		var mat := mmi.material_override as ShaderMaterial
		if mat == null or mat.shader == null:
			continue
		var path := mat.shader.resource_path
		if path.ends_with("vat.gdshader"):
			mat.set_shader_parameter("vis_pass", 1.0)
		elif path.ends_with("team_prop.gdshader") and str(key).begins_with("P"):
			# battle props share WorldMap.team_material's cached instance with the overworld: duplicate first
			if not mat.has_meta("vis_dup"):   # idempotent: duplicate only once
				mat = mat.duplicate() as ShaderMaterial
				mat.set_meta("vis_dup", true)
				mmi.material_override = mat
			mat.set_shader_parameter("vis_pass", 1.0)
	for n in bv.find_children("*", "MeshInstance3D", true, false):
		var gm := (n as MeshInstance3D).material_override as ShaderMaterial
		if gm != null and gm.shader != null and gm.shader.resource_path.ends_with("ground.gdshader"):
			gm.set_shader_parameter("vis_pass", 1.0)
			gm.set_shader_parameter("noise_tex_aniso", gm.get_shader_parameter("noise_tex"))
	var vc = bv.get("_vc_mat")
	if vc is StandardMaterial3D:
		vc.roughness = 0.88
		vc.albedo_color = Color(0.92, 0.92, 0.9)  # scenery slightly down so the troops carry the contrast

# ------------------------------------------------------------------ debug logger / bench
var args := {}
var applied := false
var t_prev := 0
var frame_i := 0
var bench_on := false
var bench_started := false
var bench_view := -1
var bench_frame := 0
var bench_frames := 60
var bench_warm := 8
var samples := {}        # view -> Array of [ms, prims, draws, objs]
var free_samples: Array = []
var result_printed := false
var log_path := ""
const VIEWS := [
	# name, reg selector (0 = first attacker vat reg, 1 = first defender vat reg, -1 = centroid), dist, pitch, yaw_off
	["close", 0, 30.0, -0.25, 0.4],
	["mid", 0, 80.0, -0.30, -0.7],
	["wide", -1, 230.0, -0.85, 0.0],
	["close_def", 1, 30.0, -0.25, 2.8],
]

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "1"
	bench_on = args.has("bench")
	bench_frames = int(args.get("bench-frames", "60"))
	log_path = args.get("perflog", "")
	if log_path == "1": log_path = ""
	process_priority = 1000   # run after main.gd and BattleView each frame
	# polish pass toggles (debug / before-after only): --vx-polish=0 = v0.2.1 look from the same build;
	# --vx-terrain=tundra|mountains = PREVIEW-ONLY winter ground + light on the demo battle (see PREVIEW_TERRAIN)
	polish = args.get("vx-polish", "1") != "0"
	char_sr = args.get("vx-char", "1") != "0"
	proto_v2 = args.get("vx-proto", "0") != "0"
	char_lite_override = [args.get("vx-charlite0", ""), args.get("vx-charlite1", "")]
	xfade_on = args.get("vx-xfade", "1") != "0"
	lod_override = float(args.get("vx-lod", "-1"))
	char_lod_override = float(args.get("vx-charlod", "-1"))
	char_mid_override = float(args.get("vx-charmid", "-1"))
	coat_lift_override = float(args.get("vx-coatlift", "-1"))
	team_tint_override = float(args.get("vx-teamtint", "-1"))
	terrain_preview = args.get("vx-terrain", "")
	# preview of the overworld markers (the real wiring is the one-line Request in out/INTEGRATION.md)
	if args.get("vispass", "0") == "1" and get_parent() != null and "map" in get_parent() and get_parent().map != null \
			and get_parent().map.get_node_or_null("MapVisuals") == null:
		get_parent().map.add_child.call_deferred(load("res://scripts/map/map_visuals.gd").new())
	t_prev = Time.get_ticks_usec()

## Debug-only look ablation: --vx-<shader uniform>=v (vat + battle team_prop materials), --vx-tonemap=filmic|aces,
## --vx-exposure / --vx-white / --vx-ambient / --vx-sun / --vx-shadow-opacity.
func _debug_overrides(bv: Node) -> void:
	var env: Environment = bv.get("environment")
	var sun: DirectionalLight3D = bv.get("sun")
	for k in args.keys():
		if not str(k).begins_with("vx-"):
			continue
		var n := str(k).substr(3)
		var v := float(args[k])
		match n:
			"tonemap": env.tonemap_mode = {"filmic": Environment.TONE_MAPPER_FILMIC, "agx": Environment.TONE_MAPPER_AGX, "linear": Environment.TONE_MAPPER_LINEAR}.get(args[k], Environment.TONE_MAPPER_ACES)
			"contrast": env.adjustment_contrast = v
			"saturation": env.adjustment_saturation = v
			"exposure": env.tonemap_exposure = v
			"white": env.tonemap_white = v
			"ambient": env.ambient_light_energy = v
			"sun": sun.light_energy = v
			"shadow-opacity": sun.shadow_opacity = v
			"polish", "terrain": pass   # read in _ready (must be set before apply())
			_:
				var mms: Dictionary = bv.get("mms")
				for key in mms.keys():
					var mat := (mms[key]["mmi"] as MultiMeshInstance3D).material_override as ShaderMaterial
					if mat != null and mat.shader != null and (mat.shader.resource_path.ends_with("vat.gdshader") or str(key).begins_with("P")):
						mat.set_shader_parameter(n, v)
		print("VX ", n, "=", args[k])

func _bv() -> Node:
	var p := get_parent()
	if p == null or not ("battle_view" in p):
		return null
	var bv = p.get("battle_view")
	if bv == null or not is_instance_valid(bv) or not bv.visible or bv.get("sim") == null:
		return null
	if not bool(p.get("in_battle")) or bool(p.get("transitioning")):
		return null
	return bv

func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	var ms := (now - t_prev) / 1000.0
	t_prev = now
	frame_i += 1
	var bv := _bv()
	if bv == null:
		return
	if not applied:
		applied = true
		if args.get("vispass", "0") == "1":
			var q := int(args.get("quality", "2"))   # previews default to high (matches earlier 4x-MSAA previews)
			if args.get("quality-order", "") == "first":
				apply_quality(q); apply(bv)
			else:
				apply(bv); apply_quality(q)
			if args.has("apply-twice"):
				apply(bv); apply_quality(q)
			print("VISPASS applied v", VERSION, " quality=", q, " lod=", bv.get("LOD_DIST"), " msaa=", get_viewport().msaa_3d)
			_debug_overrides(bv)
		if args.has("msaa"):   # debug override for perf attribution: --msaa=0|2|4|8
			get_viewport().msaa_3d = {"0": Viewport.MSAA_DISABLED, "2": Viewport.MSAA_2X, "4": Viewport.MSAA_4X, "8": Viewport.MSAA_8X}.get(args["msaa"], get_viewport().msaa_3d)
	var vp := get_viewport()
	var prims := vp.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_PRIMITIVES_IN_FRAME)
	var draws := vp.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_DRAW_CALLS_IN_FRAME)
	var objs := vp.get_render_info(Viewport.RENDER_INFO_TYPE_VISIBLE, Viewport.RENDER_INFO_OBJECTS_IN_FRAME)
	var sim = bv.get("sim")
	if args.has("vx-closeshots"):
		_closeshot_tick(bv, sim)
	if args.has("vx-closecam"):
		_closecam_tick(bv, sim)
	elif args.has("vx-widecam"):
		_widecam_tick(bv, sim)
	if bench_on:
		_bench_tick(bv, sim, ms, prims, draws, objs)
	else:
		free_samples.append([ms, prims, draws, objs])
	if bool(bv.get("finished")) and not result_printed:
		result_printed = true
		var res: Dictionary = sim.result()
		print("BATTLE_RESULT winner=%s time=%.3f losses=%s start=%s" % [str(res.get("winner")), float(res.get("time", 0.0)), str(res.get("losses")), str(res.get("start"))])
		if not bench_on:
			_report({"free": free_samples})

func _bench_tick(bv: Node, sim, ms: float, prims: int, draws: int, objs: int) -> void:
	if not bench_started:
		if float(sim.t) < float(args.get("bench-at", "4.0")):
			return
		bench_started = true
		bench_view = 0; bench_frame = 0
		_snap(bv, 0)
		return
	if bench_view >= VIEWS.size():
		return
	# frame time measured here belongs to the frame rendered with the camera set on the previous tick
	if bench_frame >= bench_warm:
		var k: String = VIEWS[bench_view][0]
		if not samples.has(k): samples[k] = []
		samples[k].append([ms, prims, draws, objs])
	if bench_frame == bench_frames + bench_warm - 1 and args.get("shots", "") != "":
		# grab the frame rendered with this view's camera (identical framing before/after)
		var img := get_viewport().get_texture().get_image()
		img.save_png(args["shots"].path_join("bench_%s.png" % VIEWS[bench_view][0]))
	bench_frame += 1
	if bench_frame >= bench_frames + bench_warm:
		bench_view += 1; bench_frame = 0
		if bench_view < VIEWS.size():
			_snap(bv, bench_view)
		else:
			bv.set("cam_auto", true)
			_report(samples)
			if args.has("bench-quit"):
				get_tree().quit()
			return
	else:
		_hold(bv, bench_view)

## Debug-only character close-ups: --vx-closeshots=<dir> saves fixed close / mid framings of the first infantry
## regiment of each side at a few battle times (idle / advance / volley / melee). Camera only; no sim access.
const CLOSE_SHOTS := [[1.0, 0, 6.0, -0.10, 0.5, "a_idle_close"], [1.0, 1, 6.0, -0.10, 2.6, "d_idle_close"],
	[1.0, 0, 16.0, -0.2, 0.9, "a_idle_mid"], [6.0, 0, 7.0, -0.12, 0.35, "a_t6_close"], [6.0, 1, 7.0, -0.12, 2.8, "d_t6_close"],
	[12.0, 0, 7.0, -0.12, 0.6, "a_t12_close"], [12.0, 1, 7.0, -0.12, 2.7, "d_t12_close"], [12.0, 0, 18.0, -0.2, 1.0, "a_t12_mid"],
	[12.0, 0, 34.0, -0.24, 1.0, "a_t12_lod1"],
	[18.0, 0, 7.0, -0.12, 0.4, "a_t18_close"], [18.0, 1, 8.0, -0.12, 2.9, "d_t18_close"],
	[24.0, 0, 8.0, -0.14, 0.5, "a_t24_close"], [24.0, 1, 8.0, -0.14, 2.6, "d_t24_close"], [30.0, 0, 9.0, -0.16, 0.7, "a_t30_close"]]
var cs_i := 0
var cs_wait := -1
func _closeshot_tick(bv: Node, sim) -> void:
	if cs_i >= CLOSE_SHOTS.size():
		return
	var c: Array = CLOSE_SHOTS[cs_i]
	if cs_wait < 0:
		if float(sim.t) < float(c[0]):
			return
		cs_wait = 0
	bv.call("snap_cam", bv.call("first_reg", int(c[1])), float(c[2]), float(c[3]), float(c[4]))
	cs_wait += 1
	if cs_wait >= 3:
		var img := get_viewport().get_texture().get_image()
		img.save_png(str(args["vx-closeshots"]).path_join("%s.png" % c[5]))
		cs_i += 1; cs_wait = -1
		if cs_i >= CLOSE_SHOTS.size():
			bv.set("cam_auto", true)

## Debug-only (--vx-closecam): slow close orbit around the first infantry regiment, cutting between the sides every
## 7 s of battle time, for the character MP4 (tools/rec.sh). Camera only.
var cc_seg := -1
func _closecam_tick(bv: Node, sim) -> void:
	var t := float(sim.t)
	var seg := int(t / 7.0)
	var side := seg % 2
	var reg: int = bv.call("first_reg", side)
	if reg < 0:
		return
	var dist := 8.5 + 2.5 * sin(t * 0.35)
	var yaw := (0.55 if side == 0 else 2.75) + 0.3 * sin(t * 0.22)
	if seg != cc_seg:
		cc_seg = seg
		bv.call("snap_cam", reg, dist, -0.12, yaw)
		return
	var c: Vector2 = sim.regs[reg]["pos"]
	bv.set("cam_target", Vector3(c.x, 0, c.y)); bv.set("cam_dist", dist); bv.set("cam_pitch", -0.12)
	bv.set("cam_yaw", (0.0 if int(bv.get("player_side")) == 0 else PI) + yaw)

## Debug-only (--vx-widecam[=dist]): elevated slow orbit around the first infantry regiment of each side (cut every
## 9 s of battle time) at ~40 m, so several regiments fighting are in frame, for the wide MP4.
func _widecam_tick(bv: Node, sim) -> void:
	var t := float(sim.t)
	var dist := float(args.get("vx-widecam", "1"))
	if dist <= 1.0:
		dist = 40.0
	var seg := int(t / 9.0)
	var side := seg % 2
	var reg: int = bv.call("first_reg", side)
	if reg < 0:
		return
	var yaw := (0.35 if side == 0 else 2.8) + 0.25 * sin(t * 0.15)
	if seg != cc_seg:
		cc_seg = seg
		bv.call("snap_cam", reg, dist, -0.3, yaw)
		return
	var c: Vector2 = sim.regs[reg]["pos"]
	bv.set("cam_target", Vector3(c.x, 0, c.y)); bv.set("cam_dist", dist); bv.set("cam_pitch", -0.3)
	bv.set("cam_yaw", (0.0 if int(bv.get("player_side")) == 0 else PI) + yaw)

func _snap(bv: Node, vi: int) -> void:
	var v: Array = VIEWS[vi]
	var reg := -1
	if int(v[1]) >= 0:
		reg = bv.call("first_reg", int(v[1]))
	if int(v[1]) == 0 and args.get("bench-focus", "") != "":   # --bench-focus=<unit id | kind>: aim the attacker views at it
		var f: String = args["bench-focus"]
		var regs: Array = bv.get("sim").regs
		for i in regs.size():
			if str(regs[i]["def"]["id"]) == f or str(regs[i]["kind"]) == f:
				reg = i
				break
	bv.call("snap_cam", reg, float(v[2]), float(v[3]), float(v[4]))

func _hold(bv: Node, vi: int) -> void:
	# re-snap every frame so the demo script's own camera steps can't move the bench camera
	# (deterministic under --fixed-fps, so before/after runs see identical views)
	_snap(bv, vi)

func _report(data: Dictionary) -> void:
	var lines: Array = []
	var vp := get_viewport()
	lines.append("# perf log  renderer=%s  adapter=%s  size=%s  msaa=%d  scale=%.2f  version=%d  quality=%d" % [
		RenderingServer.get_current_rendering_method(), RenderingServer.get_video_adapter_name(), str(vp.get_visible_rect().size), vp.msaa_3d, vp.scaling_3d_scale, VERSION, _quality])
	lines.append("view,frames,mean_ms,median_ms,p95_ms,fps_mean,primitives,draw_calls,objects")
	for k in data.keys():
		var arr: Array = data[k]
		if arr.is_empty(): continue
		var t: Array = arr.map(func(s): return float(s[0]))
		t.sort()
		var sum := 0.0
		for x in t: sum += x
		var mean := sum / t.size()
		var med: float = t[t.size() / 2]
		var p95: float = t[mini(int(t.size() * 0.95), t.size() - 1)]
		var mid: Array = arr[arr.size() / 2]
		lines.append("%s,%d,%.1f,%.1f,%.1f,%.2f,%d,%d,%d" % [k, t.size(), mean, med, p95, 1000.0 / mean, mid[1], mid[2], mid[3]])
	var txt := "\n".join(lines)
	print("PERF\n" + txt)
	if log_path != "":
		var f := FileAccess.open(log_path, FileAccess.WRITE)
		if f:
			f.store_string(txt + "\n"); f.close()
