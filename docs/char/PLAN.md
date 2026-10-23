# Character refinement: plan (stage 1)

Branch `character-refinement` in `/workspace/ic_rebase`, from `visual-pass-polish` 5adecc2 (main is not tagged v0.3 yet:
`/workspace/grand_strategy` tags = v0.1, v0.2.1; COLLAB has no MERGED v0.3). Rebase onto main@v0.3 once it exists.
Kirk's new direction supersedes "keep the blocky style": semi-realistic Napoleonic soldiers (reference: Holdfast).

## What the sim exposes per soldier (read from battle_view.gd, read-only)
`BattleView._update_units` keeps per-soldier `clip` (0 idle, 1 walk, 2 run, 3 fire, 4 melee) + `clip_t` and `dead[k]`
(death time). Per frame each VAT soldier is written to its multimesh `model|side|lod` with
INSTANCE_CUSTOM = (clip start row, ±frame count (negative = play once), clip start time, playback speed), and a
white instance colour. Selection:
- rout / visible fled -> run (2); moving (slot dist > 0.6) -> run if `running` or dist > 4 else walk (1);
  melee state -> melee (4) loop; fire event -> fire (3), play once, held < 2.0 s, clip_t = shot time + delay - 0.4,
  so the muzzle flash lands at clip time 0.05-0.4 s; otherwise idle (0). dead -> `die`, once, from death time.
- Walk speed = clamp(speed_base / 1.4, 0.6, 1.8) -> the walk clip must cover 1.4 m per second of clip time
  (24 frames = 1 cycle = 2 steps of 0.7 m). Run speed = 1 + phase*0.15; run in sim = speed*2.6 (line 1.5 -> 3.9 m/s),
  rout 2.4x -> the run clip is authored at ~3.6 m/s (16 frames = 0.667 s cycle -> 2.4 m/cycle).
- Gun crews: idle / melee(=working the gun) / run / die on the crew model.
- No per-soldier hit state exists (only per-regiment `last_hit`), no officer / light-infantry unit in c19
  (c19 units: line_inf -> c19_line, grenadiers -> c19_line (swapped to c19_grenadier by battle_visuals), hussars
  (cav), field_guns + crew). So: no hit-reaction clip is driven; two death variants instead (picked in the shader
  from the death time, which is stable per soldier). No new mechanics.
- On a clip switch the new clip starts at a random phase (clip_t = vt - phase*3): hard snap today.

## Tech choice
- Keep MultiMesh + VAT for crowds (proven, contract layout: rows = frames, cols = vertices, RGBF positions).
  Animations are authored on a real Blender armature (21 bones, smooth 2-bone weights at joints), baked to VAT.
  Bone-texture GPU skinning was considered: it needs bone ids/weights as extra vertex attributes (no free slots in the
  glb path: UV.y = material, UV2 = VID + team mask, COLOR = albedo) and 2 bones x 3 texels x 2 frames x 2 clips =
  24 fetches/vertex vs 8 for VAT. On llvmpipe and for ~3-5k soldiers VAT is cheaper and bakes any skinning for free.
- New: a normal VAT (`*.vatn`, RGBA8 octa-free xyz*0.5+0.5, same layout) so smooth limbs shade correctly when posed
  (the old VAT shaded with rest-pose normals, fine for boxes, wrong for a smooth raised arm).
- Crossfade: instance COLOR carries (prev row0, prev row1, prev frac, blend weight) computed on the CPU. COLOR is
  free because the new character takes its albedo from a palette lookup (UV.x = colour slot), not vertex colour.
  Needs a small battle_view.gd change (track previous clip + switch time, write the colour): Request, applied only in a
  PREVIEW-ONLY commit. Without the hook (white colour) weight = 1 -> plays exactly like today (graceful fallback).
- Reusable character + uniform system (`pipeline/blender/char_kit.py`): one shared body mesh (skin-modifier sculpt,
  continuous, smooth) + one skeleton + one clip set for every c19 foot model; kit parts (coat tails, lapels, cuffs,
  collar, crossbelts, cartridge box, knapsack, shako / bearskin / bicorne, musket + bayonet, rammer) are swappable
  per unit type. Colour slots: coat, facings, trousers, gaiters, plume, lace, ... -> per-nation palettes are DATA in
  battle_visuals.gd (`NATION_UNIFORM`), set as shader uniforms per side material. Team mask stays in UV2.y.
- New model ids `c19sr_line`, `c19sr_grenadier`, `c19sr_artillery` (+ `c19sr_officer` asset, not used by the sim);
  old glbs untouched. battle_visuals swaps c19 regiments to them (existing `_swap_models` mechanism), gated to the c19
  era; other eras unchanged.

## Budgets
- LOD0 ~2.5k tris, LOD1 ~600-800 tris (LOD switch = existing LOD_DIST per quality). LOD2/impostor would need a third
  LOD band in battle_view (Request, not done).
- One material per model per side (as today), so draw calls unchanged. VAT memory ~ verts x frames x (12 + 4) B.
- Clips @24 fps: idle 96 (4 s, breathing + weight shift), walk 24, run 16, fire 48 (present/fire/recoil/reload),
  melee 20 (bayonet thrust), die 30 + die_b 30.
