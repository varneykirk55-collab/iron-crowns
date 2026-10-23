# INTEGRATION

## Character refinement 2 (branch character-refinement-2, base gs main@v0.3.2 21bbfe1)
Delta on top of v0.3.2 (which already contains character-refinement d93f576 + Rob's R1 sr-xfade in `_put` and R2 debug node).
The old PREVIEW-ONLY hook patches are obsolete and dropped. Render-only: battle_visuals.gd, char_vat shaders, c19sr assets and
the Blender pipeline. No core/, ui/, main.gd, battle_view.gd, tests/ or data/ change; ids, MultiMeshes and units.json unchanged.

Commits (on 21bbfe1): 5ebe944 9a mid LOD, b6c0989 9b coat lift, dccd3aa 10a team tint / SWE coat / clash pick / R3 + crew helpers,
2a6f12a 10b per-instance tint (perf), docs commits after.

### Deliverables (/workspace/ic_rebase/out, mirrored in /workspace/iron-crowns-visual/out)
- `character-refinement-2.patch`: all text changes vs v0.3.2. Apply at the repo root:
  `git apply character-refinement-2.patch && tar xzf character-refinement-2-binaries.tar.gz`
- `character-refinement-2-binaries.tar.gz`: re-baked blend/soldier_c19sr_*.blend, game/assets/models/soldier_c19sr_*_lod0.glb,
  game/assets/vat/c19sr_*_lod0.{vat,vatn} (LOD0 asset now carries the mid set).
- Scripts: out/pkg_v032.sh (build), out/verify_v032.sh (clean v0.3.2 check).

### What's in it
1. **Team readability at mid / top zoom (Rob's v0.3.2 request: 1800 NOR light blue vs SWE navy, white kit on snow).**
   - char_vat distance team tint, per instance in vertex(): from 25 m to 90 m the coat (palette coat slots + UV2.y team mask)
     blends to the BattleView side colour (`team_color`, = HUD / banner) up to 0.85; trousers, crossbelts, shako, plume,
     knapsack, roll, cartbox and fur up to 0.75. From 90 m to 200 m (overhead) everything except skin goes towards 0.95
     (rest x0.7). The team colour is luma-normalised to 0.32 so it reads on snow and on grass. Below 25 m (LOD0 close-ups) the
     historical uniforms are unchanged. Uniforms team_tint / team_tint_acc / team_near / team_far / team_top / team_tint_top;
     debug `--vx-teamtint=<0..1>`.
   - `_side_palettes` clash pick: if the two coats are closer than 0.22 it now recolours the side whose coat is furthest from its own
     side colour (1800: Norway -> red, a plausible Dano-Norwegian red; before, Sweden was shifted and both stayed blue).
   - Swedish coat lightened: NATION_UNIFORM SWE coat 2a3d6e -> 3a5a9a (fixes "SWE navy goes quite dark in close_def").
2. **q2 mid LOD (option B from the v0.3.1 notes, done in stage 9).** The LOD0 asset stores LOD0 | mid | LOD1 sets; the shader picks one per
   instance by distance. Tris LOD0 / mid / LOD1: line 3034 / 1368 / 581, grenadier 3238 / 1470 / 629, artillery 2742 / 1352 / 573,
   officer 2464 / 1198 / 512. QUALITY: q2 char_lod 20 m / char_mid 45 m (LOD0 to 20 m, mid to 45 m, LOD1 beyond); q0 20/20 and q1
   30/30 (no mid band). BattleView LOD_DIST 45/75/120 untouched. Debug `--vx-charlod=<m>`, `--vx-charmid=<m>`.
3. **Coat lift on mid / far sets (CHAR_FAR):** dark coat slots are lifted towards palette luminance 0.28 (gain cap 2.0) on the mid set
   and LOD1 so navy / dark green don't go black at distance. Debug `--vx-coatlift=<0..1>`.
4. **Helpers for Rob (no battle_view change made by us):** `BattleVisuals.OFFICER_MODEL`, `officer_vat()`, `sr_vat(sr)`,
   `xfade_crew(...)`; see Requests.

### Verification
- character-refinement-2 HEAD after `godot --import`: tests 140/140, gameplay outcome hash 0e814dda14fe56255efbd18ab3b3ad6d1ad3c87061652b3aca200109bfdfc8b8 (out/hash.sh),
  SIMHASH (game/tests/sim_hash.tscn, as in Rob's COLLAB notes) SWE1800 f7255ebb0f2a4f8d7a2c55ffc65f4d79, USA1914 45cf5510a28c2f2f02a3e79c8cbb6ffc,
  JPN1500 9bb2394dbff429a57cf2d87297a212b7, all identical to v0.3.2; 0 SHADER ERROR lines.
- Clean v0.3.2 (21bbfe1) + patch + tarball: checked with out/verify_v032.sh (apply --check, tree == branch HEAD, --import, 140/140, both hashes, shader errors); result in out/verify_v032.log.
- Compares (Rob's battle_shots harness, q1, 1600x900, v0.3.2 vs HEAD): /workspace/iron-crowns-visual/out/char/stage10/teams/compare/
  sheet_1800SWE_q1.png (close / close_def / mid / top, as Rob's sheet), sheet_USA_q1.png, crop_1800SWE_q1_{close,close_def,mid,top}.png.
- q2 perf (battle_shots, 3 runs, median fps vs same-build ctl --vx-char=0; docs/char/BENCH_AFTER.md "Stage 10"):
  1800SWE close -16 / close_def -13 / mid -1 / top -5 %; USA close -16 / close_def -18 / mid -10 / top -1 %. The team tint itself costs ~0.

### Requests for Rob (battle_view.gd is his; nothing here is required for the delta to work)
- **R3 officer (optional, render-only, no sim change):** one officer per c19 infantry regiment.
  1. vat setup (where c19_line is registered): `var ov := BattleVisuals.officer_vat(); if not ov.is_empty(): vat[BattleVisuals.OFFICER_MODEL] = ov`
     (id "c19_officer"; entry has mesh / tex / json per LOD + "sr" = "c19sr_officer", same layout as the swapped c19_line entry).
  2. MultiMeshes `"c19_officer|<side>|<lod>"` (lod 0/1, mesh `vat["c19_officer"]["mesh"][lod]`, same format as the other VAT
     mms: colours + custom data on) created before `BattleVisuals.apply()`; `_char_materials` then dresses them (nation palette,
     team tint, LOD sets, die / die_b) like any sr id. Clip names = c19_line (idle, walk, run, fire, melee, die, die_b).
  3. In `_update_units`, per c19 infantry regiment one `_put(mms["c19_officer|%d|%d" % [side, lod]], ...)` at e.g. the front-centre
     of the block (just ahead of the banner), clip from the regiment state; for the crossfade use `BattleVisuals.xfade` with a
     separate state dict per regiment set (e.g. `v["xf_off"] = {"n": 1}`, index 0) so it doesn't collide with the soldiers' k.
  Instance count +1 per regiment; officer LOD0 2464 / mid 1198 / LOD1 512 tris.
- **Gun-crew crossfade (optional):** in the `crew_model` loop (`for q in 3:`), pass as the last `_put` argument
  `BattleVisuals.xfade_crew(v, k, q, cur, cc, cct, 1.0, vt) if vat[cm].has("sr") else Color(1, 1, 1, 1)` with
  cur = 5 (dead), 2 (run), 4 (melee) or 0 (idle) matching the clip picked there. State lives in `v["xf_crew"]` keyed by k*3+q, so it
  does not collide with R1's per-soldier state. Without it, crew clip changes hard-cut as now.
- **COLLAB entry:** please add the v0.3.2 delta entry (we do not write to grand_strategy).

### Known follow-ups (our side)
- q2 close / close_def still ~13-18 % under ctl (LOD0 within 20 m + 4x MSAA); q2 char_lod 15 m would trade a little close-up detail for it.
- R4 (direct c19sr ids) stays out: it would change the serialized regiment `model` string and the SWE1800 sim hash.
