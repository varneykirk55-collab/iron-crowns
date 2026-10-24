# Cavalry animation overhaul: results (branch `rob/cavalry-animation-overhaul`)

Specification: `HORSE_SKELETON_SPEC.md` (v1.2). Clip table: `docs/cav/HX_CLIPS.md`.
Baseline: clean main **41bdd75** (worktree `/workspace/ic_cav_base`). This branch's merge-base with main is also 41bdd75.

## 1. Regression (presentation only: outcomes must equal main)
Run on the code of d51e69e (a263833 changes the spec only). Logs are in `out/br_*` (gitignored).

| check | main 41bdd75 | branch, cav v2 ON (default) | `--no-cav-v2` | `--no-anim-v1` |
|---|---|---|---|---|
| test_runner | 216/216 | **220/220** (216 + 4 new cav-v2 checks) | – | – |
| SIMHASH SWE 1800 | 0b3153c6f9fb7c454686cb49f19cb866 | 0b3153c6f9fb7c454686cb49f19cb866 | – | – |
| SIMHASH USA 1914 | a9beef573f5922b7eb83ba8f2beb5e63 | a9beef573f5922b7eb83ba8f2beb5e63 | – | – |
| SIMHASH JPN 1500 | 563be302cdf34e56b4a33a873230ebf1 | 563be302cdf34e56b4a33a873230ebf1 | – | – |
| audio | 28/28 | **28/28** | – | – |
| BATTLERESULT SWE 1300 | 1521b887c9d3 | 1521b887c9d3 | 1521b887c9d3 | 1521b887c9d3 |
| BATTLERESULT SWE 1650 | 82bf6eaeda42 | 82bf6eaeda42 | 82bf6eaeda42 | 82bf6eaeda42 |
| BATTLERESULT SWE 1800 | dc1fd7648864 | dc1fd7648864 | dc1fd7648864 | dc1fd7648864 |
| BATTLERESULT USA 1914 | a030d0a0572c | a030d0a0572c | a030d0a0572c | a030d0a0572c |
| reinforce | a5fdd04a36e6 | a5fdd04a36e6 | a5fdd04a36e6 | a5fdd04a36e6 |

(BATTLERESULT = first 12 hex of the md5 of the whole BATTLERESULT line, which includes `render_models`. The HX assets load under the legacy model keys, so that list is unchanged.)

## 2. Performance vs main (`perf_raw.txt`)
`anim_demo --scene=cav`, 1280x720, 40 s, xvfb + llvmpipe (software GL). Each scene and mode was run twice, interleaved.
- `units_us` is the CPU time of BattleView's unit update per frame (AnimCombat cavalry driving included).
- `frame ms` is the whole frame on llvmpipe. The box was shared with other agents' Godot jobs (load 12–17 on 8 cores), so frame ms is **noisy** (±50% between repeats of the same run). Read it as a trend only.

| scene | mode | units_us median (vs main) | units_us p95 | frame ms median (rep 1, rep 2) |
|---|---|---|---|---|
| 6 knight regts (2,400 riders) + 5 spear | main | 2,682 | 7,444 | 854, 369 |
| | branch `--no-cav-v2` (legacy horse) | 2,917 (+9%) | 7,765 | 550, 710 |
| | branch HX (default) | 3,158 (+18%) | 9,406 | 1,062, 807 |
| 6 hussar regts (2,400) + 5 line inf | main | 2,415 | 6,588 | 200, 463 |
| | branch `--no-cav-v2` | 2,434 (+1%) | 5,582 | 235, 413 |
| | branch HX | 2,602 (+8%) | 5,030 | 205, 551 |
| 1 knight regt (400) + 1 spear | main | 643 | 792 | 225, 233 |
| | branch `--no-cav-v2` | 650 (+1%) | 808 | 267, 202 |
| | branch HX | 730 (+14%) | 1,166 | 220, 262 |

- **CPU:** HX driving costs +0.1 to +0.5 ms per frame for 400–2,400 riders. It comes from the extra per-rider work: lean/pitch, hit detection, melee strike timing and the tilted transform.
- **Vertices:** the proxy HX bakes have 2.7–3.1× the legacy vertex count (knight LOD0 1,548 vs 583, LOD1 905 vs 468; hussar 1,412 vs 452, 856 vs 317). On llvmpipe, vertex work is CPU work, so with 6 knight regiments close to the camera the frame trends +50% (both repeats were the slowest). On a real GPU this is ≈ 3.7 M VAT vertices per frame at LOD0 for 2,400 riders. That is expected to be small but **not measured here**, and it should be measured on hardware before release. Bill's final mesh will be larger (spec section 6 budget). LOD1/LOD2 (spec v1.2) and the LOD distance are the levers.
- `--no-cav-v2` (legacy horse) is within noise of main, as expected (same code path).

## 3. Videos (normal speed, 30 fps, 1280x720, `tools/cav/rec_cav.sh`)

The demo scene is `game/tests/anim_demo.tscn --scene=cav`. The sim never makes cavalry walk or trot (it advances at def speed, then ×1.8), so the gait clips use the demo-only `--prof`, which sets the attacker speed over time. Battle code is not touched.

| File | What it shows |
|---|---|
| `knight_gaits_side.mp4` / `hussar_gaits_side.mp4` | Side tracking cam on a front-rank horse: stand → walk (≈4–13 s) → trot (≈15–24 s) → canter (≈26–31 s) → gallop (≈33–38 s) → decelerate to stand (≈39–48 s). Filmed from the sun-lit flank (`anim_demo --sideflip`, demo-only camera flag) |
| `knight_walk.mp4`, `knight_trot.mp4`, `knight_gallop.mp4` (and `hussar_*`) | Clips cut from the gaits_side videos: walk 4–13 s, trot 15–24 s, gallop 32–39 s |
| `knight_turn_stop.mp4` / `hussar_turn_stop.mp4` | The formation wheels at a trot, then halts at about 24 s |
| `knight_combat.mp4` / `hussar_combat.mp4` | Charge into infantry, melee, horse and rider deaths |
| `knight_multi.mp4` / `hussar_multi.mp4` | 4 cavalry regiments vs 3 infantry regiments |

## 4. Known issues

- The horse is still Rob's **proxy mesh**, flat-shaded. These wait on Bill's mesh (see `HORSE_SKELETON_SPEC.md`): the real bake through `horse_anim.py`, `.vatn` normals plus `hx_vat.gdshader`, the LOD2 far set, the JSON layer ranges, and re-measured perf.
- Perf was measured on shared llvmpipe (load 12–17), so frame times are noisy. The GPU cost has not been measured on real hardware. The HX vertex count is about 2.7–3.1× the legacy count.
- The legacy (`--no-cav-v2`) hv cavalry never returns to the stand clip (threshold −0.05). This is **out of scope and not fixed**; it is only noted here.
- Demo HUD text ("Battle of Moscow", Russia vs Canada) is a demo placeholder.
- In `knight_multi` the battle ends at about 27 s, so the last seconds show the post-battle state. `hussar_multi` is trimmed to 0–19 s: the hussars rout off-frame at about 18 s.
