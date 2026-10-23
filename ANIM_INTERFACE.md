# Combat animation interface v1 (Rob, branch `proto/anim-combat-v1`)

This is the contract between the combat animation layer (Rob) and the character rigs and VAT bakes (BJORN, `proto/c19-line-v2`).
It is presentation only. Nothing here changes BattleSim, stats, rng order or outcomes.

## 1. Runtime switch
- `game/scripts/battle/anim_combat.gd` (`AC`) is preloaded by `battle_view.gd` and is **ON by default** (since 2026-10-23, Kirk approved). `BattleView.setup()` sets `AC.on = AC.resolve_from_runtime()`.
- Disable it for troubleshooting (precedence: command line > env var > project setting > default ON):
  - command-line user arg `--no-anim-v1` or `--anim-v1=off` (also `=0` / `=false`), e.g. `IronCrowns.exe -- --no-anim-v1`;
  - environment variable `IRONCROWNS_ANIM_V1=0` (or `off` / `false`);
  - project setting `iron_crowns/battle/anim_v1 = false` (e.g. in an `override.cfg` next to the executable: `[iron_crowns]` / `battle/anim_v1=false`).
  - The old `--anim-v1` flag is still accepted (it just means on). `--anim-v1=on` / `IRONCROWNS_ANIM_V1=1` force it on.
- Disabled, the legacy code path runs unchanged. AC is never called. Outcomes are identical either way.
- Enabled, there are only 2 hooks:
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
- **All or nothing (Kirk, 13:51):** when the sim sets `rout`, the whole regiment turns at the same moment, 0.15 s after the break, using one turn time (0.45 s) and one turn direction. There is no rear-first order, no stagger, no stragglers and no late starts.
- The regiment then walks away **as one body** at its normal marching speed `def.speed`, with the normal cadence (`pk_withdraw` for spears, `mk_march` for muskets; playback `speed/1.4`, like the advance).
- The only per-soldier difference is the walk-cycle phase, so the legs are not in lockstep.
- Once turned, a soldier never fights again: there are no thrusts, no hits and no flinches. Glance-backs (`pk_withdraw_look`) are dropped; the row is kept but not used.
- Each step is hard-capped at 1.02 × pace, so the rout never runs faster than normal.
- The formation loosens only slightly (up to ±0.4 m over 10 s), so it stays a block.
- A visual centre starts where the line broke and walks at `def.speed`. The banner and officer follow it (`v.ac_vis_c`). Hiding uses that visual centre (fled and > 260 m).
- All of this is hash-driven (no rng). The sim is only read, so outcomes are unchanged.
- Sim notes (read-only, not changed):
  - `battle_sim.active()` excludes `rout`, and `_pick_target` skips non-active regiments, so a routing unit is never fought again.
  - There is no rally. `_step_rout` applies attrition, and the unit becomes `fled` after 9 s.

## 8. Known limits
- Only `med_spear` (1300 spear levy) and `c19sr_line` (line_inf) have the new clips. Archers keep the legacy clips, but the arrow now leaves the bow hand at the release frame (0.9 s into `fire`).
- The melee contact gap is visual only (2.7 m, shared half and half when both sides are spears). The sim still uses its own `_front_gap ≤ 1.6`.
- The retreat is visual-time driven, so it carries on after the battle ends. Because it walks at normal pace, the rendered rout lags the sim's (faster) rout centre.

## 9. Cavalry gaits (flag on) — motion only

Horse look is unchanged: no GLB, texture, material, shader or coat changes. `cavalry.py` is not edited.
New clips come from `pipeline/blender/cavalry_anim_combat.py`. That script imports `cavalry.py` read-only and **appends** VAT rows 144–569 to the six cav VATs
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
- A gait state machine picks the gait from speed (thresholds 0.25/1.35/2.8/5.6 m/s, with 0.3 hysteresis and 0.4 s dwell). It moves one gait step at a time.
- A transition starts at the cycle wrap, so the phase stays continuous.
- Playback rate is speed/v_nom, clamped to 0.7–1.45 (1.6 for gallop), so hooves do not skate.
- Determinism: instance order, coat (INSTANCE_ID) and the legacy dust `rng.randf()` draw are kept exactly. Sim hashes are identical with the flag on or off.
- Limit: a routed cav regiment still hides by the legacy sim-centre test, so the rng sequence stays the same.

### 9a. Gait readability v2 (13:49 fix)
- **What was wrong.** The hv rows *were* playing. A VATLOG of instance custom data on the GPU shows rows 144+ with the right start, count and time, and the VAT texture is 426 rows high. There is no procedural bob override.
- **Why it still looked rigid.** The legs barely moved:
  - The stance sweep was ±0.26–0.38 m. Hoof travel was 0.5–0.8 m per stride, against 1.7 m for the legacy `run`.
  - The legs stayed near full extension, so the body bob dominated what you saw.
  - The med_knight caparison hides the upper legs.
  - Gallop was never reached: the knights' speed cap is ~6.07 m/s, below the 6.2 threshold.
- **Fix (motion only).**
  - Each gait now has a swing overreach `E` (fore, hind): walk .16/.12, trot .26/.22, canter .36/.32, gallop .48/.44 m.
  - Swing lift is larger, the swing has a forearm/hock fold, and the body is lowered 3–9 cm so the stance legs are flexed.
  - The stance sweep is unchanged, so `v_nom` and the cadence are unchanged and hooves do not skate.
  - The gallop threshold is now 5.6 m/s.
  - Both LODs play the same rows. LOD1 is the same rig with fewer vertices, so mid and far horses also cycle their legs.

## 10. Cavalry rout and death (flag on) — motion only
- Broken cavalry **do not turn and ride away**. They rein in where the squadron broke and mill: up to ±0.8 m lateral and ±0.6 m fore/aft, at ≤ 1.2 m/s, with small heading sways.
- The moment the sim takes them off the field (state `fled`, or the legacy far-away hidden test) is shown as their **death**. Sim timing is unchanged.
  - Each instance starts its own death 0–1.5 s after that moment (hash stagger).
  - Each instance plays one of three play-once clips at 0.85–1.15× speed, then holds the last frame.
  - The bodies stay on the field for the rest of the battle view.

| clip | rows | frames | what happens |
|---|---|---|---|
| cv_die_a | 426 | 48 once | horse stumbles, its front knees buckle, the hind legs fold, and it rolls onto one side with a few last kicks; the rider is thrown forward over the neck |
| cv_die_b | 474 | 48 once | the same collapse, rolling onto the other side; the rider slides off sideways |
| cv_die_c | 522 | 48 once | the same collapse as a; the rider falls backwards over the croup |

- Rider legs are weighted to the horse body in the kits, so the bake moves them with the rider (per-vertex override in the bake only).
- No `BattleView.rng` draws change: the legacy dust draw happens under the same condition and in the same order, and hidden instances draw nothing, as in the legacy code.
- Demo: `anim_demo.tscn -- --scene=cavdie [--anim-v1] --gap=30 --pre=15 --tgt=19,-66 --cam=16,-0.2,1.75` (120 knights against a deep spear block, with a second regiment per side so the battle continues).

