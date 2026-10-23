# Combat animation interface v1 (Rob, branch `proto/anim-combat-v1`)

This is the contract between the combat animation layer (Rob) and the character rigs and VAT bakes (BJORN, `proto/c19-line-v2`).
It is presentation only. Nothing here changes BattleSim, stats, rng order or outcomes.

## 1. Runtime switch
- `game/scripts/battle/anim_combat.gd` (`AC`) is preloaded by `battle_view.gd` and is **off by default**. Turn it on with the command-line user arg `--anim-v1` (`AC.on = true`).
- Flag off, the legacy code path runs unchanged. AC is never called.
- Flag on, there are only 2 hooks:
  1. `_update_units`: `AC.update_soldiers()` replaces the per-soldier VAT loop for regiments whose model has the new clips (`ac_kind` 1 = spear, 2 = musket).
     - It draws **no rng**. The legacy per-soldier loop draws none either, so the rng order is preserved.
     - Any other regiment returns `false` and stays on the legacy loop.
  2. `_fx_volley`: `AC.volley()` makes the same `rng` draws in the same order as the legacy branch. It only moves where and when the effects appear (shots are queued and flushed at the weapon tip on the fire frame).

## 2. Skeletons (source of truth, never renamed or reparented)
- **c19 line (c19sr):** `pipeline/blender/char_rig.py` `BONES`.
  - `prop` is unparented, with local +Y = barrel.
  - BJORN will add `weapon_tip` as a child of `prop`.
- **1300 spear (med_spear):** the legacy 15-bone rig `pipeline/blender/soldiers.py` `BONES`. The spear is in `hand.R`, and the blade point at rest is `hand.R + (0.24, 0, -1.305)` (Blender).
- **Orientation:** characters face Blender +Y. The VAT bake writes `(x, z, -y)` (`rigkit.py:72`), so the model front is **Godot −Z**. All `weapon_tip` / `prop_tip` values are in that space.

## 3. VAT layout
- `.vat` (rgb float32 positions) plus `.vatn` (rgba8 normals, c19sr only), 24 fps.
- The json `clips` entries are `{start, count, loop}`. LOD0 keeps the near/mid/far vertex sets.
- **Rows are append-only:**
  - c19sr: rows 0–263 are BJORN's (`idle walk run fire melee die die_b`). New rows start at 264.
  - med_spear: rows 0–161 are the original (`idle walk run fire melee die`). New rows start at 162. `base_frames: 162` marks the cut.
  - The old rows are byte-identical to `origin/main` a3f4f35. This was checked.
- `INSTANCE_CUSTOM` is unchanged: `(start, signed count (negative = play once), start time, speed)`. `COLOR.b` is the crossfade elapsed time (c19sr), so AC never uses it for phase. AC puts per-soldier phase into the start time (a constant per loop, so a crossfade is never restarted).

| model | clip | start | frames | loop | use |
|---|---|---|---|---|---|
| c19sr_line | mk_march | 264 | 24 | yes | march step (weight transfer) |
| c19sr_line | mk_aim | 288 | 16 | no | shoulder → make ready → present |
| c19sr_line | mk_fire | 304 | 12 | no | shot on frame 1, recoil, lower to prime |
| c19sr_line | mk_reload | 316 | 62 | no | prime, ram ×2, shoulder |
| med_spear | pk_advance | 162 | 24 | yes | levelled-pike advance |
| med_spear | pk_charge | 186 | 16 | yes | run with the pike levelled |
| med_spear | pk_guard | 202 | 48 | yes | front-rank guard/hold, weight shifting |
| med_spear | pk_thrust | 250 | 14 | no | thrust, contact at 0.30 s (`events.pk_thrust.contact`) |
| med_spear | pk_recover | 264 | 12 | no | recover to guard |
| med_spear | pk_hit | 276 | 14 | no | hit reaction (stagger) |
| med_spear | pk_collapse | 290 | 38 | no | knee buckle → fall (alternative to `die`) |
| med_spear | pk_withdraw | 328 | 24 | yes | retreat at normal pace: forward-facing walk, same leg cycle/cadence as pk_advance, spear sloped on the shoulder |
| med_spear | pk_flee | 352 | 16 | yes | full run. Row kept, no longer used by the renderer (the retreat never exceeds normal pace) |
| med_spear | pk_withdraw_look | 368 | 24 | yes | retreat walk with a glance back over the left shoulder |

## 4. Weapon tip socket
- Per-clip json `weapon_tip` or `prop_tip` is a list of `[x, y, z]`, one per frame, in Godot model space.
- AC reads `weapon_tip` first and falls back to `prop_tip`.
  - c19sr has `prop_tip` = prop bone origin + local +Y × muzzle length (written by `char_anim_combat.py`).
  - med_spear has `weapon_tip`.
- The muzzle flash, smoke and tracer spawn at `mk_fire` frame 1 tip, transformed with the soldier's yaw and position.

## 5. Bake
- `pipeline/blender/char_anim_combat.py` appends the `mk_*` clips to `char_anim.CLIPS` on import. `char_anim.py` is not edited.
  - `blender -b --python pipeline/blender/char_anim_combat.py -- bake` registers the clips, runs `char_build.bake()` unchanged, and then writes `prop_tip`.
- `pipeline/blender/soldier_anim_combat.py -- bake` appends the `pk_*` rows to `med_spear_lod{0,1}`. It checks the vertex count and that re-evaluated `idle` reproduces rows 0–23. The glb, blend and soldiers.py are untouched.

## 6. Requests and questions for BJORN (`proto/c19-line-v2`)
1. **Bake entry point.** The agreed command is `blender -b --python pipeline/blender/char_build.py -- bake`. For that to include the mk_* clips, `char_build.py` needs one line: `import char_anim_combat  # noqa` (idempotent), before `CLIPS` is read. That file is yours, so I did not add it. OK to add it on your branch?
2. **`weapon_tip` bone.** Once it exists, please write a per-frame `weapon_tip` into each clip json (same frame count as the clip, Godot model space). AC picks it up with no code change. `prop_tip` stays as the fallback. Please confirm the muzzle offset: I used the `prop` +Y length up to the muzzle (−1.526 z in `mk_fire` f1). The bayonet tip reaches −1.93.
3. **Grenadier/officer variants** (`c19sr_*` other than `line`) were not rebaked. If they share the line's clip list, their regiments stay on the legacy loop (AC requires `mk_aim` and `mk_reload`). Should they get the mk_* rows in your v2 rebake?
4. **v2 glb rewrite.** If v2 changes the vertex order or count, the mk_* rows have to be rebaked from v2 (run the bake above). Nothing in AC depends on the vertex count.
5. **Pre-existing facing bug (legacy path, not changed).** `battle_view._put` uses `yaw = atan2(face.x, face.y)`. Its basis maps model −Z to −facing, so on `main` **every VAT soldier renders facing away from the enemy** (spears and muskets point backwards, and marching is a moonwalk). AC uses `atan2(-face.x, -face.y)` on the flag-on path only.
   - Fixing the legacy path changes the flag-off look, so it is a separate decision for Kirk and the lead.
   - Officers (`off_yaw`) and cavalry are still on the legacy yaw.

## 7. Rout presentation (flag on)
- When the sim sets `rout`, each soldier first holds a staggered moment: 0.1–0.95 s, with rear ranks going first.
- He then turns ~180° in 0.3–0.6 s (per-soldier turn rate π/turn_d, turning left or right by hash) and **walks** away at the regiment's normal marching speed `def.speed`, with the normal cadence (`pk_advance` leg cycle, playback `speed/1.4` like the advance). His yaw follows his rendered velocity.
- Speed: ±3 % per soldier around normal; stragglers 4–8 % slower; never faster. Each step is hard-capped at 1.02 × the soldier's own pace. The ease from rest is 0.35 s; there is no build-up beyond normal. Measured in the spear demo (`ANIMSPEED`, def.speed 1.40 m/s): mean 1.39, p95 1.44, max 1.47 m/s. Flag off (legacy, following the sim's 2.4× rout): mean 5.2, max 9.8 m/s.
- The view no longer follows the sim's 2.4× rout centre. A visual centre starts where the line broke and walks away at `def.speed`. Soldiers keep their pre-rout slots around it. The banner and officer follow that centre (`v.ac_vis_c`, 2-line hook in battle_view). Hiding uses the visual centre (fled and > 260 m).
- The formation loosens: up to ±1.2 m lateral scatter, growing over 8 s (adds < 1 % speed).
- About 12 % of soldiers are stragglers: they start 0.6–1.3 s late and walk slower. About 18 % (45 % of stragglers) use `pk_withdraw_look`. `pk_flee` is no longer used: the panicked share is remapped to `pk_withdraw`.
- Muskets use the same timing with `mk_march` at the normal march cadence.
- All of this is hash-driven (no rng). The sim is only read, so outcomes are unchanged.

## 8. Known limits
- Only `med_spear` (1300 spear levy) and `c19sr_line` (line_inf) have the new clips. Archers keep the legacy clips, but the arrow now leaves the bow hand at the release frame (0.9 s into `fire`).
- The melee contact gap is visual only (2.7 m, shared half and half when both sides are spears). The sim still uses its own `_front_gap ≤ 1.6`.
- The retreat is visual-time driven, so it carries on after the battle ends. Because it walks at normal pace, the rendered rout lags the sim's (faster) rout centre.

## 9. Cavalry gaits (flag on) — motion only

Horse look is unchanged: no GLB, texture, material, shader or coat changes. `cavalry.py` is not edited.
New clips come from `pipeline/blender/cavalry_anim_combat.py`. That script imports `cavalry.py` read-only and **appends** VAT rows 144–425 to the six cav VATs
(`med_knight`, `em_cuirassier`, `c19_hussar`, lod0/lod1). Rows 0–143 are byte-identical to before, and the bake asserts that.
The legacy clips (idle/walk/run/melee/fire/die) are unchanged.

| clip | frames | footfall phase (br, fr, bl, fl) | duty | v_nom m/s |
|---|---|---|---|---|
| hv_stand | 48 loop | weight shift, resting hind, breathing, tail | – | 0 |
| hv_walk | 24 loop | 0, .25, .5, .75 (4-beat lateral) | .62 | 0.84 |
| hv_trot | 16 loop | .875, .375, .375, .875 (diagonal pairs) | .42 | 2.14 |
| hv_canter | 14 loop | .125, .375, .375, .625 (3-beat, leading fl) | .33 | 3.53 |
| hv_gallop | 12 loop | .125, .475, .225, .575 (4-beat transverse) | .25 | 6.08 |
| hv_melee | 24 loop | standing horse + legacy rider strike | – | – |
| hv_idle_walk, hv_walk_idle, hv_walk_trot, hv_trot_walk, hv_trot_canter, hv_canter_trot, hv_canter_gallop, hv_gallop_canter | play-once | gait parameters blended A→B, phase 0 → phase 0 | | |

The head and neck nod with the gait: two nods per stride at walk and gallop, and a steady head at trot. Body pitch, bob, surge and roll are keyed to the footfalls.
The rider counter-moves, and the lance lowers toward the gallop. Every JSON clip carries `v_nom`.

Renderer (`anim_combat.gd`, `_update_cav`):
- Each horse runs a velocity follower with accel/decel/turn limits. The yaw follows the velocity.
- A gait state machine picks the gait from speed (thresholds 0.25/1.35/2.8/6.2 m/s, with 0.3 hysteresis and 0.4 s dwell). It moves one gait step at a time.
- A transition starts at the cycle wrap, so the phase stays continuous.
- Playback rate is speed/v_nom, clamped to 0.7–1.45 (1.6 for gallop), so hooves do not skate.
- Determinism: instance order, coat (INSTANCE_ID) and the legacy dust `rng.randf()` draw are kept exactly. Sim hashes are identical with the flag on or off.
- Limit: a routed cav regiment still hides by the legacy sim-centre test, so the rng sequence stays the same.
