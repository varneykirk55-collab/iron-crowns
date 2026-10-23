# INTEGRATION

## Character refinement (branch character-refinement, base gs main@v0.3.1 5bffeb0)
Rebased 23 Oct 2026 ~05:20 EDT from 0dcaa7b onto tag v0.3.1 (5bffeb05fc5e59efdce34a6d820c2a9868dbadd0; tag object ce4351c): 31 commits kept, no conflicts
(v0.3.1 touches map terrain / world_map / map.gdshader / map tests / docs only; no file overlaps this branch).
Semi-realistic Napoleonic c19 soldiers (simplified Holdfast look) replace the blocky c19 line / grenadier / artillery-crew
models. This is a render-only change: the same model ids, MultiMeshes and units.json are used (in-place swap in
BattleVisuals._swap_char), and no gameplay code or data is touched.

### Deliverables (all in /workspace/ic_rebase/out, mirrored in /workspace/iron-crowns-visual/out)
- `character-refinement.patch`: all non-binary changes, with the PREVIEW-ONLY hook commits (main.gd, battle_view.gd) excluded.
  Apply with `git apply character-refinement.patch && tar xzf character-refinement-binaries.tar.gz` at the repo root.
- `character-refinement-binaries.tar.gz` (32 MB): blend/soldier_c19sr_*.blend, game/assets/models/soldier_c19sr_*_lod{0,1}.glb,
  game/assets/vat/c19sr_*_lod{0,1}.{vat,vatn}
- `character-refinement-PREVIEW-ONLY-hooks.patch`: the two hooks below, for reference only. Not for merge as-is.
- Look: out/char/turn/line_turntable_sheet.png, line_pose_sheet.png; nations: out/char/nations/nations_{line,grenadier}.png;
  battle: out/char/compare/cmp_*.png; MP4s: out/char/char_closecam.mp4, out/char/char_wide.mp4; perf: docs/char/BENCH_AFTER.md

### What's in it
- pipeline/blender/char_{geo,body,rig,anim,build,footslide,nations}.py: shared body + skeleton, swappable kits (line: shako;
  grenadier: bearskin; artillery; officer: bicorne), musket + bayonet, clips (idle, walk, run, fire with recoil, reload, melee,
  die, die_b), and the VAT bake. Rebuild with `blender -b --python pipeline/blender/char_build.py -- bake`.
- game/shaders/char_vat.gdshaderinc (shared body) + char_vat.gdshader (LOD0) + char_vat_lod1.gdshader (LOD1 variant: one
  normal fetch, no crossfade fetch, per-vertex palette): VAT positions + .vatn normals, nation palette, team mask (UV2.y),
  die_b variant, and an optional clip crossfade read from instance COLOR (it does nothing while COLOR is white, as main's _put writes it).
- Stage 7 character LOD: BattleView's LOD_DIST stays 45/75/120 (test_visuals_hook pins it). The c19sr LOD0 asset stores the
  LOD0 set plus the LOD1 set after it (json `near_verts`); char_vat.gdshader draws one set per instance by camera distance and
  collapses the other to a degenerate point. Switch distance = QUALITY `char_lod` in battle_visuals: 20 / 30 / 45 m for
  q0 / q1 / q2 (debug override --vx-charlod=<m>). No battle_view change.
- game/scripts/battle/battle_visuals.gd: _swap_char / _char_materials, NATION_UNIFORM (all 47 majors + derived fallback for
  minors), the xfade() helper, plus debug-only --vx-char=0, --vx-closeshots, --vx-closecam and --vx-widecam.
- Tris LOD0/LOD1 (drawn per instance): line 3034/581, grenadier 3238/629, artillery 2742/573, officer 2464/512. LOD0 is within
  the 1.5-3k target (+/-8%), LOD1 within 500-800. The LOD0 file stores both sets (line 3615 tris / 2513 verts) but only draws one.

### Verification
- character-refinement HEAD (rebased on v0.3.1, after `godot --import`): tests 140/140, no shader errors, outcome hash 0e814dda14fe56255efbd18ab3b3ad6d1ad3c87061652b3aca200109bfdfc8b8 (out/hash.sh)
- clean v0.3.1 (5bffeb0) + patch + binaries tarball (no hooks): `git apply --check` OK, 140/140, same hash, no shader errors
  (verified 23 Oct 2026 05:18 EDT: patch 36 files + tarball 28 binaries, `godot --import`, 140/140, hash 0e814dda, 0 SHADER ERROR lines; hooks patch also applies cleanly on v0.3.1)
- earlier, clean 0dcaa7b + patch + binaries tarball: `git apply --check` OK, 140/140, same hash
  (re-verified at stage 7d, 23 Oct 2026 05:05 EDT: patch 36 files + tarball 28 binaries, 140/140, hash 0e814dda, no shader errors)
- before/after battle stills are frame-identical in sim state (same casualties and positions).
- Perf after stage 7 (llvmpipe, 1600x900, 3 runs, median-frame fps vs same-build control --vx-char=0, docs/char/BENCH_AFTER.md):
  q0 +2..+20%, q1 -8..+5%, q2 wide -2% / mid -11% / close -22% / close_def -14%. Draw calls unchanged.
  (Stage 6 was q0 -16..+5% (wide -27%), q1 -26..-31%, q2 -15..-44%.)

### q2 option (Kirk's call)
q2 close/mid is still 11-22% under the same-build control because q2 keeps character LOD0 out to 45 m (plus 4x MSAA). Two options,
neither taken yet; both are battle_visuals/asset-only (no battle_view change, tests unaffected):
- **A: q2 char_lod 30 m** (same as q1): one-line QUALITY change; expected to bring q2 close/mid roughly to q1's -8..+5%;
  cost: LOD1 pop at 30 m instead of 45 m at the top tier.
- **B: mid LOD** (~1.2-1.5k tris) inserted in the same in-shader near/far split (e.g. LOD0 <20 m, mid 20-45 m, LOD1 beyond):
  keeps q2's look closer to now at mid range; cost: one more bake set, larger LOD0 asset, extra shader branch.
Current state keeps q2 at 45 m (look first). **Kirk to decide A or B (or leave as is).**

### Requests for Rob
1. **battle_view.gd: clip crossfade colour hook** (owner: battle_view; PREVIEW-ONLY commit 41eb3e1 after rebase; was 5c14c8c). Give `_put()` an optional
   `col: Color = Color(1,1,1,1)` that is written into buf[i+12..15] instead of the constant 1.0s. In the VAT branch of
   `_update_units` (`_put(mms["%s|%d|%d" % [model, side, lod]], ...)`), pass
   `BattleVisuals.xfade(v, k, 5 if dk >= 0.0 else clip[k], c, ct, spd, vt)` when `vat[model].has("sr")`.
   Without this hook clip changes still work, but they hard-cut instead of crossfading over 0.25 s. The patch is
   character-refinement-PREVIEW-ONLY-hooks.patch.
2. **main.gd: BattleVisuals debug node** (PREVIEW-ONLY commit cabb42b after rebase; was 6e0efe7). v0.3 dropped
   `if args.has("perflog") or args.has("bench") or args.has("vispass"): add_child(load("res://scripts/battle/battle_visuals.gd").new())`.
   Without it, --bench, --perflog, --vx-closeshots, --vx-closecam and --vx-widecam do nothing. Please restore it (debug flags only).
3. **Officer instance (optional):** the officer kit (bicorne, sword) is built and baked (c19sr_officer) but has no regiment
   slot. One officer per infantry regiment would need a battle_view change (an extra instance per regiment), so it is not included.
4. **Naming (optional):** units.json / CREW_MODEL could name the c19sr models directly instead of relying on the in-place swap.
   Main's polish tests currently assert c19_grenadier / c19_artillery, which is why the swap keeps the ids.

### Known follow-ups (our side)
- q2 close/mid is still 11-22% under control: q2 keeps character LOD0 out to 45 m (4x MSAA too). Options: q2 char_lod 30 m, or a
  ~1.2-1.5k-tri mid set in the same near/far split (no battle_view change needed). Not done, to keep q2's look; Kirk to decide (see "q2 option" above).
- No battle_view LOD2 request is needed: wide views are at control at every tier.
- Visual cost of stage 7: lean LOD1 (fewer rings, no thumbs/nose/linings), character LOD switch at 20/30/45 m (pop at that
  distance, same as BattleView's own LOD pop), LOD1 uses nearest-frame normals and no clip crossfade.
