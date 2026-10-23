# Iron Crowns — Collaboration Guide

## People and workspaces
| Role | Who | Workspace | Branch |
|---|---|---|---|
| Lead developer (gameplay, sim, UI, input, save/load, tests, battle camera, merges) | Lead bot | `/workspace/ironcrowns-lead` (git worktree of `/workspace/grand_strategy`) | `lead-dev` |
| Graphics specialist (models, uniforms, textures/materials, lighting/shadows, contrast, AA, map army markers) | **BJORN** | `/workspace/iron-crowns-visual` (his own isolated snapshot + own git, branch `visual-pass`) | merged into `graphics` here |

- `/workspace/grand_strategy` on branch **`main`** is the playable build. Only merge into `main` after the test suite passes.
- v0.1 is tagged `v0.1`. A verified backup lives in `/workspace/backups/ironcrowns-v0.1-20261022-1905/`; nobody touches it.
- The lead never edits BJORN's workspace. BJORN never edits `/workspace/grand_strategy` or `/workspace/ironcrowns-lead` directly.

## File ownership
| Area | Owner |
|---|---|
| `pipeline/blender/**`, `blend/**`, `game/assets/**`, `game/shaders/**` | Graphics (BJORN) |
| Lighting / environment resources (WorldEnvironment, sun, sky, fog, AA/quality *visual* settings) | Graphics |
| `game/scripts/battle/battle_visuals.gd` (new, optional code hooks for materials/meshes/effects) | Graphics |
| `game/scripts/core/**`, `game/scripts/ui/**`, `game/scripts/main.gd`, input (InputMap in `project.godot`), save/load, `game/tests/**`, battle camera | Lead |
| `game/scripts/battle/battle_view.gd`, `game/scripts/map/world_map.gd` | **Shared-risk**: lead edits camera/input/logic. Graphics requests material/mesh changes via `battle_visuals.gd` hooks or a note under *Requests* below rather than editing these files directly. |
| `game/data/*.json` | Lead (graphics may request new fields, e.g. model/material ids) |

## Asset contract (do not break without a documented migration)
- Keep the glb file names in `game/assets/models/` and their node structure (one mesh per unit type, LOD meshes as currently named).
- Keep the VAT (vertex animation texture) layout in `game/assets/vat/` (rows = frames, columns = vertices; same animation clip order and frame counts).
- Team colour mask lives in **UV2.y** (1 = team-coloured, 0 = not). Keep it.
- Unit ids in `game/data/units.json` are the keys battle/sim code uses; keep them and their `model` field values.
- MultiMesh quirks: `use_colors = true` with white instance colours is needed for vertex colours; buffer stride 16 floats (20 with custom data). glTF materials are overridden in code (`battle_view.gd`), so new materials should be exposed via `battle_visuals.gd`.
- If a change needs a migration (renamed glb, new VAT layout…), describe it in the Handoff entry: old → new, and which code must change.

## Handoff process
1. BJORN works in his workspace, then delivers a patch/branch that applies to `graphics` (based on `main` at tag `v0.1` or later).
2. He adds a **READY** entry below: date, commit/patch path, what changed, files touched, how he verified, screenshots.
3. Lead reviews, applies to `graphics`, merges into `lead-dev`, runs tests + demos, then merges to `main` and marks the entry **MERGED** (or **BLOCKED** with a reason).

## How to run things (from a checkout root, e.g. `/workspace/ironcrowns-lead`)
- Godot binary: `/workspace/grand_strategy/tools/godot` (4.7.2; symlinked as `tools/godot` in worktrees; not in git).
- First time in a new checkout: `tools/godot --headless --path game --import` (builds `.godot/`).
- Compile check: `python3 tools/fix_infer.py res://scenes/main.tscn`
- Tests: `tools/godot --headless --path game res://tests/test_runner.tscn` → results in `user://test_results.json` (copied to `test_results.txt`). Must be all-pass before merging to main.
- Demos (screenshots into `shots/`):
  `xvfb-run -a -s "-screen 0 1600x900x24" tools/godot --path game --resolution 1600x900 --fixed-fps 10 -- --demo=<menu|campaign|diplomacy|era|battle> --nation=<USA|SWE|JPN> [--reinforce=1] [--closeup] [--shots=/abs/dir]`
- Video: add `--fixed-fps 30 --write-movie /ABSOLUTE/path.avi`, then `ffmpeg -i x.avi -c:v libx264 -crf 24 -pix_fmt yuv420p x.mp4`. `tools/record_all.sh campaign diplomacy era battle` does all four.
- Renderer: GL Compatibility. The box has no GPU (llvmpipe), so fps numbers are software-rendering numbers.

## Requests (graphics → lead or lead → graphics)
- **2026-10-22 lead → BJORN (FYI, lead-dev 6a9b04c, not yet on main):** heads-up on shared-risk files so your patch rebases cleanly:
  - `battle_view.gd`: camera fully rewritten (`_update_cam`, `_cine_pose`, `overhead_pose`, `_apply_cam`, director). Please don't touch camera code; if you need a fixed bench camera, keep it in `battle_visuals.gd` (calling `snap_cam`/setting `cam_*` is fine).
  - New `apply_quality()` in `battle_view.gd` (Controls.quality 0/1/2): Low turns `sun.shadow_enabled` off and LOD_DIST 45; Medium = shipped defaults (LOD 75, shadows on); High LOD 120. `main.gd apply_quality()` sets viewport MSAA off/2x/4x. If you want different per-quality visuals (shadow distance, AA mode, etc.), expose a `battle_visuals.apply_quality(q)` hook and tell me — I'll call it and drop my values.
  - `battle_view.gd` now `add_to_group("battle_view")` and has `perf` dict timings (sim/units/fx µs) shown in the F3 overlay — feel free to read them for your bench.
  - `main.gd` input handling changed a lot (actions via `Controls` autoload). Your PREVIEW-ONLY hook in `main.gd` (2a36972) will conflict; prefer a one-line hook I add myself — just say which call you need.

## Handoffs
- **MERGED to `main` 2026-10-23 ~16:20 EDT (Kirk approved, 15:49 EDT): environment bot, biome framework + tropical + east_asia battlefield regions**
  - Merge commits (no force push, no rebase) onto `origin/main` 644174c (v0.5.0): `4f7f1e2` env/biome-framework, `93c9988` env/tropical, `b853c98` env/east_asia.
  - After each merge: test_runner 205/205, test_audio 28/28, test_env 0 failures. sim_hash is identical to pre-merge 644174c every time (SWE 1800 0b3153c6…, USA 1914 a9beef57…, JPN 1500 563be302…).
  - The only conflicts were in CHANGELOG.md. I kept every side (v0.5.0 notes intact) and put the env notes under "Battlefield environment: biome framework + regions".
  - Scope: rendering only. Data-driven biome profiles are in `game/scripts/battle/biomes/` and battle_environment.gd chooses them from the battle's province. BattleVisuals.apply() re-applies the biome look so era passes stay idempotent.
  - **Note for Claude / BJORN:** no sim, morale, pathfinding, combat, AI or unit code was touched. The engagement-corridor rules and `plan(ctx)["obstacles"]` behave exactly as described below. env/arid and env/temperate stay on their branches and are NOT on main.
- **READY (review only, NOT for main until Kirk approves): 2026-10-23 13:30 EDT, environment bot, Scandinavian medieval battlefield prototype**
  - **MERGED to `main` 2026-10-23 ~13:45 EDT (Kirk approved).** `origin/main` had not moved past a3f4f35, so there were no conflicts. Before merging I re-ran the checks on 774aee5: test_runner 163/163, test_audio 28/28, test_env 0 failures, and sim_hash identical to a fresh origin/main worktree (SWE 417a5300…, USA 4679c5a2…, JPN e104d558…). Only Scandinavia (medieval) is covered; other regions go on separate `env/<biome>` branches and wait for approval.
  - Branch `env/scandinavia-medieval` (from `main` a3f4f35). Worktree `/workspace/ic_env`. Evidence is in `evidence/env-scandinavia/` (README, perf, ASSETS.md, before/after compare, key frames). The MP4 is in `/workspace/ic_env/out/video/`.
  - Scope: rendering only. The new `game/scripts/battle/battle_environment.gd` and the shaders `battle_terrain`, `env_foliage` and `env_water` add procedural env glbs (`pipeline/blender/env_nordic.py`). `battle_view.gd` gets +17 lines of hooks. The province must be in Norway, Sweden, Denmark or Finland, and the era must be medieval. Everything else keeps the legacy ground.
  - Verified: sim_hash is identical to main (SWE 417a5300…, USA 4679c5a2…, JPN e104d558…); test_runner 163/163, test_audio 28/28 and the new `tests/test_env.tscn` all pass.
  - **Note for Claude (offensive warfare / battle sim), on obstacles and collision.** I did not touch your branch or any sim code.
    - None of the environment props (trees, boulders, outcrops, junipers, logs, lake) have collision. They do not feed `BattleSim`, which stays 2-D, and the sim inputs (`b.terrain`, seed, units) are unchanged.
    - The legacy `_scatter` placed rocks at up to 3.5x scale anywhere, including under formations. The new placement keeps every solid prop out of an *engagement corridor*. The corridor is the deployed x extent of both lines + 70 m (clamped 160 to 430 m half-width) by the z extent + 220 m (clamped 260 to 360 m half-depth). A prop is only placed if `|x| > cw + r + 10` or `|z| > cz + r + 10`, where `r` is its footprint radius. Only knee-high cover (grass, heather, pebbles) appears inside the corridor.
    - `BattleEnvironment.plan(ctx)["obstacles"]` returns `[Vector2 pos, radius]` for every solid prop, and `BattleEnvironment.clearance(obst, pos, half_extents)` gives regiment-vs-obstacle clearance. If you ever want sim-side obstacles (forest slowing movement, blocked lanes), use that list as the single source of truth. That would change battle results and hashes, so it needs its own approval.
    - `tests/test_env.gd` runs 24 real BattleSims (5 or 7 regiments a side, x1 and x2.5 men, all objectives, routs included) and checks every regiment footprint every 0.5 s: minimum clearance 73 m, 0 overlaps.
    - If your offensive-warfare work enlarges battle deployments past about 360 m half-width or 140 m depth, the corridor clamps will need raising. That is one line in `layout()`; tell me and I will change it.

- **READY: 2026-10-22 20:45 EDT, BJORN, c19 visual pass (initial target, review before other eras)**
  - Branch `visual-pass` HEAD `580e1ee` in `/workspace/iron-crowns-visual`, based on `32fb914` (byte copy of v0.1).
  - Patch: `/workspace/iron-crowns-visual/out/visual-pass-c19.patch` (text only, excludes the PREVIEW-ONLY `main.gd` commit 2a36972, do NOT merge that). Binaries: 14 assets listed in `out/binary_assets.md`, packed in `out/visual-pass-c19-binaries.tar.gz`.
  - Full notes: `/workspace/iron-crowns-visual/out/INTEGRATION.md` (diff stat, Requests with exact code, risks, perf, 5-era + map marker plan).
  - What changed: c19 line infantry, hussar, and field gun rebuilt via the pipeline (contract kept: glb names, nodes, VAT layout, UV2.y mask, unit ids); material classes (wool/leather/steel/brass/etc.) in `vat`/`team_prop` shaders; contact darkening; horse coats; battle-only dye deepening for pastel nation colours; ground tones; lighting/env (ACES, lower ambient, no bloom, single-pass shadows); 4x MSAA, scale 1.0, 8x aniso. All gated in `battle_visuals.gd` (c19 only; legacy look otherwise). New asset `art_field_gun_c19.glb` (`art_cannon.glb` untouched since it's shared with early-modern).
  - Verified: 61/61 tests on baseline and HEAD, result outputs hash-identical; same-seed demo battle identical (winner 1, t=25.6). Before/after shots: `out/before`, `out/after`, `out/compare/`. MP4s: `out/visual-pass-c19.mp4`, `out/visual-pass-c19-closeup.mp4`.
  - Perf (llvmpipe, 1600x900, box shared/noisy): full demo 267 ms/frame to 302 ms (+13%), mostly 4x MSAA; draw calls unchanged, tris +3-4%. Not measured on a GPU.
  - Requests: (1) call `battle_visuals.apply(self)` at end of `battle_view.gd setup()` (and again if units are added after setup); (2) viewport sharpness settings: I see your new `apply_quality()` sets MSAA per quality, so I'll expose `battle_visuals.apply_quality(q)` for shadows/AA if you want me to own those values, your call; (3) optional: point c19 `field_guns` at `art_field_gun_c19` in `units.json` instead of the runtime swap.
  - Known open issues: top-down view still pale/hazy (next: height fog); grenadiers share line model; gun crews wear line uniform.
  - **UPDATE 2026-10-22 21:35 EDT:** HEAD now `116c310`, which adds the readability fix from your review (FILMIC, brighter sun, AO on feet only, pipeclay never darkened, no dye-darkening on saturated colours, white straps) and `battle_visuals.apply_quality(q)` (0 = no MSAA, no shadows, LOD 45; 1 = 2x MSAA, shadows, LOD 75; 2 = 4x MSAA, shadows 300 m, LOD 120). It's idempotent and works in either order with apply(). Re-tested: 61/61, outcome hash identical to baseline. Patch, tarball and INTEGRATION.md refreshed; `git apply --check` is clean on 32fb914. Compares: `out/compare/cmp3_*.png`.
  - **Lead status (2026-10-22 ~21:10 EDT): MERGED to `graphics` (6b58baf; binary sha256 checked against `binary_assets.md`) and integrated on `lead-dev-gfx` → `lead-dev` (d1c8a22). NOT on `main` / v0.2 builds yet**, held until the brightness/readability revision (uniforms too dark at distance) gets a new READY entry here.
    - R1 done: `BattleVisuals.apply(self)` right after `_build_hud()` in `BattleView.setup()`, before `apply_quality()`, so Controls quality wins (low = no sun shadows).
    - Quality: `BattleView.apply_quality()` forwards `Controls.quality` (0/1/2) to `battle_visuals.apply_quality(q)` as soon as your script has it (checked via the script method list; static func is fine). Controls keeps the setting and UI.
    - R2 not wired: `apply_viewport()` would force 4x MSAA and a 4096 shadow atlas regardless of quality, which conflicts with `main.apply_quality()` (MSAA off/2x/4x by quality). Put the viewport and shadow values per quality into `apply_quality(q)` instead.
    - R3 not done (optional): the runtime `PROP_SWAP` still handles `field_guns`. `units.json` is unchanged, so sim hashes stay identical.
    - Tests on lead-dev with your patch: 131/131, including 4 new `--only=visuals` checks (hook applied on c19, idempotent, medieval keeps the legacy look, quality owns shadows). Sim hashes are unchanged.
    - FYI: the aftermath camera shot now actually fires (it orbits the winner). Untouched reads: `era_id`, `environment`, `sun`, `mms`, `_vc_mat`.
  - **MERGED v0.2.1 (lead, 2026-10-22 ~22:00 EDT):** your FINAL handoff 116c310 is on `main` and tagged `v0.2.1` (`graphics` 42998e4 → `lead-dev` → main). The 14 binaries were checked against `binary_assets.md`, and the tree matches 116c310 except for the excluded PREVIEW-ONLY `main.gd` (R4).
    - R1 is kept.
    - R2 is done: `main.apply_quality()` and `BattleView.apply_quality()` both forward `Controls.quality` to `BattleVisuals.apply_quality(q)`. Yours is now the only owner of MSAA, shadows, LOD, glow and aniso. My stand-in and my duplicate MSAA/LOD/shadow lines are removed. `--debug --lod-dist=` still overrides LOD, and `--quality=0|1|2` is a new session-only override.
    - R3 is still not done, so `PROP_SWAP` stays.
    - Results: 131/131 tests, sim hashes unchanged, and the 1800 SWE battle gives an identical BATTLERESULT at q0, q1 and q2.
    - FYI: exported builds were missing `assets/vat/*.vat` (no soldiers in v0.1/v0.2 exports). This is fixed in v0.2.1 `export_presets.cfg`. Raw files you add for FileAccess need an `include_filter` entry.
    - **@BJORN: base all your next work on `main@v0.2.1`** (rebase or re-branch `visual-pass` from it). Hand off patches against that commit as before.
- **READY: 2026-10-22 22:45 EDT, BJORN, eras batch (med, em, c20, mod) + overworld army markers**
  - Branch `visual-pass-v0.2.1` HEAD `1c951b9` (worktree `/workspace/ic_rebase`), based on main v0.2.1 `5f3ea72`. No lead-owned files changed.
  - Patch: `/workspace/iron-crowns-visual/out/visual-pass-eras.patch` (`git apply --check` clean on 5f3ea72; leaves out PREVIEW-ONLY f62ae41). Binaries: `out/visual-pass-eras-binaries.tar.gz` (65 files, sha256 in `out/binary_assets.md`). Patch plus tarball on clean 5f3ea72 reproduces HEAD exactly, except main.gd.
  - Notes: `out/INTEGRATION.md` section E1–E6. Zoom compares `out/compare/zoom_{med,em,c20,mod}.png`, markers `out/compare/markers_*.png`, MP4s `out/visual-pass-{med,em,c20,mod}.mp4`.
  - Tests: 130/131. The only failure is your "eras outside the pass keep the legacy look (medieval)" check, which is expected now that medieval is in the pass (see R6). The original 61 gameplay checks give an identical outcome hash `0e814dda…`.
  - Requests (exact code in INTEGRATION.md E3): **R5** one line in `world_map.gd` to add `map_visuals.gd` (needed for the new markers; it only swaps each army's "Standard" mesh/material, so selection and movement are untouched); **R6** update that legacy-look test; **R3** optional: point `units.json` at the era artillery models; **R4** don't merge f62ae41.
  - Open: c20/mod team colour is on accents only (team dye could go 0.55 to 0.7 if you want more); perf on llvmpipe is noise-dominated (draw calls unchanged, tris +2–4%); era demos were short bench runs, not full battles to a result.
- **MERGED v0.3 (lead, 2026-10-23 00:20 EDT):** your eras batch 1c951b9 and polish pass 5adecc2 are on `main` and tagged `v0.3` (`graphics` 1f7f279 + 882366e → `lead-dev` → main). The tree matches 5adecc2 except the PREVIEW-ONLY `main.gd` (R4 still excluded, so `--vx-terrain` / `--bench-focus` / `--vispass` don't work in the lead build; production uses `BattleView.setup()` → `apply()`).
  - R5 done: one line in `world_map.gd` adds `map_visuals.gd`; new tests click a marker through the real input path and check selection + move orders still work.
  - R6 done: the legacy-look test now expects medieval in the pass.
  - Polish requests done: `make_gamedata.py` sets grenadiers → `c19_grenadier` (units.json regenerated; only that one line changed); `CREW_MODEL` c19 → `c19_artillery`, early_modern → `em_gunner`; `--import` run for the new glbs (0 errors). Your runtime swaps are now no-ops (tested: re-apply adds no multimeshes).
  - Results: 140/140 tests; 61-check gameplay outcome hash `0e814dda…` unchanged; sim hashes USA1914/JPN1500 unchanged, SWE1800 changes only through the regiment `model` string (state dumps differ in exactly 2 lines). One q1 battle per era re-rendered: BATTLERESULT identical in all 5 eras. Overhead views are no longer washed out (snow included).
  - R3 still not applied: c20/modern keep `art_howitzer`.
  - Note: your `out/` directory (INTEGRATION.md incl. the Polish section, hash.sh, MP4s, compares) was gone after a box restart, and there is no polish READY entry here; I worked from the commits and code comments. Please re-post the polish notes if anything there needs action.
  - Requests for you: (1) overhead team colour is still weak for c20/modern (dye on accents only) and pale nation colours (Japan white vs Russia green at 230 m); (2) `map_visuals._mesh()` calls `load(path).instantiate()` without a null check, so a marker glb that exists but isn't imported crashes; (3) pre-existing horizontal streaks over the western ocean at world zoom (`campaign_USA_world.png`, also in v0.2) — map terrain/shader, so it may belong to the `graphics-map` work.
  - **@BJORN: base all your next work on `main@v0.3`.**

## MAP READY: overworld visual refinement (Rob, branch `graphics-map`, 2026-10-23 ~01:10 EDT)
Base `5f3ea72` (v0.2.1). Worktree `/workspace/ironcrowns-map`. Victoria-style geographic map: terrain relief from normal and cavity maps, a biome albedo, snow on peaks, depth-shaded oceans with shallows, waves, foam and fresnel, haze, and smooth antialiased coasts. Borders are crisp and scale with zoom (signed distance field), and the political tint is adaptive: strong at world and region zoom, with terrain taking over close up. There are no new cities, fleets or gameplay.
- **Changed files:**
  - `game/shaders/map.gdshader` (rewritten)
  - `game/scripts/map/world_map.gd`: loads 5 terrain textures; 16x8 chunked terrain with 3 LODs and skirts; `_apply_map_quality` on `Controls.settings_changed`. Low hides LOD0 and uses the simple shader path. Picking, LUT, markers and labels are untouched.
  - `game/assets/map_terrain/*` (5 textures + .import)
  - `pipeline/build_map_visuals.py` (regenerates the textures)
  - `game/tests/map_shots.{gd,tscn}` (screenshot/perf/pick/interact harness)
  - `game/tests/map_flyover.{gd,tscn}` (movie capture)
  - `MAP_PROGRESS.md`
  - Untouched: `map_visuals.gd`, the battle files, `update_markers`, sim/data, and `main.gd`.
- **Verified:**
  - Tests: 131/131.
  - SIMHASH identical (SWE 1800, USA 1914, JPN 1500).
  - Picking: 12/12 views return the same ids as the baseline.
  - Selection highlight, conquest recolour (Oslo→SWE, re-pick 328) and zoom extremes 4/230 all OK.
- **Perf, pck and outputs:**
  - Perf (llvmpipe): `out/perf_table.md`.
  - Outputs: `out/compare/`, `out/before|after/`, `out/map_flyover.mp4`.
- **MERGED v0.3.1 (lead, 2026-10-23 ~01:50 EDT):** the overworld terrain refinement (`graphics-map` 53b3dcd) is on `main` and tagged `v0.3.1` (`graphics-map` → `lead-dev` 6db2728 + streak fix 3012eab → main).
  - Files: `map.gdshader` (rewritten), the terrain parts of `world_map.gd` (chunked LOD terrain, `_apply_map_quality`), `game/assets/map_terrain/*`, `pipeline/build_map_visuals.py`, `game/tests/map_shots*`, `game/tests/map_flyover*`. These stay lead-owned.
  - Your R5 hook in `world_map.gd` is kept and unchanged (`add_child(map_visuals.gd)` at the end of `build()`); marker click/selection tests pass. `map_visuals.gd` and all battle files are untouched.
  - Fix for your request (3) from the v0.3 note: the world-zoom ocean streaks were z-fighting between the deep-ocean backdrop plane and the ocean surface; the backdrop now sits at y −1.5. Fixed and verified.
  - Results: 140/140 tests; gameplay outcome hash `0e814dda…`; sim hashes USA1914 `45cf5510…`, JPN1500 `9bb2394d…`, SWE1800 `f7255ebb…` (all unchanged from v0.3); province picks identical on 15 views.
  - Visual note for marker work: the map is now darker/more natural and the political tint is muted at region/close zoom, so check marker team colours against it.
  - **@BJORN: base all your next work on `main@v0.3.1`** (rebase `character-refinement` onto it). Hand off patches against that commit as before.
- **READY: 2026-10-23 05:25 EDT, BJORN, character-refinement (Kirk-directed: semi-realistic Napoleonic c19 soldiers + skeletal-authored anims)**
  - Branch `character-refinement` HEAD `d93f576` in `/workspace/ic_rebase`, based on main@v0.3.1 `5bffeb0` (no conflicts).
  - Patch: `/workspace/iron-crowns-visual/out/character-refinement.patch` (36 files, excludes PREVIEW-ONLY). Binaries: `out/character-refinement-binaries.tar.gz` (28 files, 32 MB). Hooks (NOT for merge, see Requests): `out/character-refinement-PREVIEW-ONLY-hooks.patch`.
  - Verified on clean v0.3.1 + patch + tarball: `--import` clean, 140/140, outcome hash `0e814dda...`, 0 shader errors. Model ids, multimesh names and units.json unchanged (in-place VAT/mesh swap, c19 only; other eras untouched).
  - Kits line/grenadier/artillery/officer, tris LOD0 ~2.5-3.2k / LOD1 512-629; clips idle/walk/run/fire/melee/die/die_b; nation uniforms for all 47 majors. Perf vs same-build control: q0/q1 within 10%, q2 close/mid -11..-22% (follow-up in progress: mid LOD + brighter far coats).
  - Docs: `out/INTEGRATION.md` (Requests 1-4: battle_view `_put` colour + `BattleVisuals.xfade` hook; restore main.gd debug node; optional officer instance; optional naming). Bench `out/char/BENCH_AFTER.md`, compares `out/char/compare/`, `out/char/stage7/close/cmp/`, MP4s `out/char/char_closecam.mp4`, `out/char/char_wide.mp4`.
  - **Lead status / MERGED v0.3.2 (lead, 2026-10-23 ~05:50 EDT):** applied as `456aa8d` (author BJORN; patch sha256 `17475580…`, tarball `f7b0dfc4…`, tree == `d93f576` minus the two PREVIEW-ONLY hook commits; hooks patch NOT applied) → lead-dev → main, tag `v0.3.2`.
    - R1 DONE (`ffcafd3`, battle_view.gd): `_put(..., col: Color = Color(1,1,1,1))` writes the instance colour; the VAT branch passes `BattleVisuals.xfade(v, k, 5 if dk >= 0.0 else clip[k], c, ct, spd, vt)` when `vat[model].has("sr")`, white otherwise (non-sr eras byte-identical). Artillery crews (`crew_model` loop) still pass white: `xfade` keys state by soldier index `k` in `v`, and 3 crew per gun would collide, so crews hard-cut. If you want crews crossfaded, give me an xfade variant keyed by (k, q).
    - R2 DONE (`ffcafd3`, main.gd): `if args.has("perflog") or args.has("bench") or args.has("vispass"): add_child(load("res://scripts/battle/battle_visuals.gd").new())` after the Sim signal connects. No flag = no node.
    - R3 NOT DONE: `c19sr_officer` has no vat id; `_swap_char` only swaps CHAR_MODEL ids that BattleView already loaded, and `_char_materials` only dresses `sr` ids, so an officer instance needs battle_visuals support first. If you add a `c19_officer` → `c19sr_officer` entry that `_swap_char`/`_char_materials` handle (I would create the multimesh `c19_officer|side|lod` from a stub vat entry, 1 instance per c19 infantry regiment next to the banner, render-only), send it as a READY request and I will do the battle_view side.
    - R4 NOT DONE: renaming ids would change the serialized regiment `model` string (SWE1800 sim hash) and the polish tests; not worth it for v0.3.2.
    - Verified on lead-dev and main: `--import` 0 errors, 140/140, outcome hash `0e814dda…`, SIMHASH SWE1800 `f7255ebb…` USA1914 `45cf5510…` JPN1500 `9bb2394d…`, 0 SHADER ERROR. Renders: `deliverables/v0.3.2/screenshots/compare/` (1800 SWE q0/q1/q2 close/close_def/mid/top + other eras q1). Perf vs v0.3.1 (llvmpipe, 1600x900): 1800 SWE mean q0 −11 %, q1 +4 %, q2 −17 % (`perf_table.md`).
    - **@BJORN readability request (please address in the delta):** in the default 1800 Norway-vs-Sweden battle both sides now read blue: NOR `coat 3a5f95` (light blue) vs SWE `2a3d6e` (navy), with white trousers/crossbelts on snow. At mid (70 m) and overhead the two lines are hard to tell apart and neither matches the HUD/banner colours (Norway red, Sweden blue); v0.3.1 read red vs blue. The `_side_palettes` separation check (coat distance < 0.22) does fire here but only darkens/shifts the defender, which doesn't help on snow. Ask: guarantee a minimum side contrast at distance (e.g. tint the coat toward `side_col` beyond `char_lod`, or a stronger team accent on shako/crossbelts at LOD1). See `compare_1800SWE_q2_mid.png`, `crop_1800SWE_q2_close.png`. Swedish navy coats also go quite dark in the close defender view.
    - Your delta (mid LOD + brighter far coats) was not in `out/` when v0.3.2 was cut; it goes in v0.3.3. Base it on `main@v0.3.2`.
- **READY: 2026-10-23 07:35 EDT, BJORN, character-refinement-2 (team readability blocker + q2 mid LOD + far-coat lift) -> for v0.3.3**
  - Branch `character-refinement-2` HEAD `667e980` in `/workspace/ic_rebase`, based on main@v0.3.2 `21bbfe1`. battle_visuals/assets/shaders only.
  - Patch: `/workspace/iron-crowns-visual/out/character-refinement-2.patch` (12 files). Binaries: `out/character-refinement-2-binaries.tar.gz` (16 files, 37 MB).
  - Verified on clean v0.3.2 + patch + tarball: 140/140, outcome hash `0e814dda...`, sim hashes SWE1800 `f7255ebb...`, USA1914 `45cf5510...`, JPN1500 `9bb2394d...` unchanged, 0 shader errors.
  - Fixes: distance-scaled team tint via UV2.y mask (1800 SWE now red vs blue at mid/top), SWE coat 2a3d6e -> 3a5a9a, mid LOD (~1.2-1.5k tris) at q2, coat lift on mid/far sets. q2 vs control: close -13..-18%, mid/top -1..-10%.
  - Compares (your battle_shots harness, q1): `out/char/stage10/teams/compare/sheet_1800SWE_q1.png`, `sheet_USA_q1.png`, `crop_1800SWE_q1_*.png`. Bench: `docs/char/BENCH_AFTER.md` "Stage 10".
  - Optional for you (see `out/INTEGRATION.md`): R3 officer via `BattleVisuals.OFFICER_MODEL` / `officer_vat()`; gun-crew crossfade via `BattleVisuals.xfade_crew(...)` as the last `_put` arg in the crew loop.
  - **Lead status / MERGED v0.3.3 (lead, 2026-10-23 ~08:05 EDT):** applied as `2a7c5ae` (author BJORN; patch sha256 `f932a795…`, tarball `c7c709a5…`; tree == `667e980` except PROGRESS.md) + `6f2e530` (lead) → lead-dev (which also carries the audio merge 1cd066e/a526478) → main, tag `v0.3.3`.
    - R3 DONE (`6f2e530`, battle_view.gd): one `c19_officer|side|lod` multimesh pair per side; one officer per `c19_line`/`c19_grenadier` regiment, right of the front rank (`center + right*((files-1)*0.5*sp.x + 1.3) + facing*((ranks-1)*0.5*sp.y + 0.4)`), smoothed like soldiers, clips idle/walk/run/melee/rout/die, own crossfade state `v.xf_off`. Render only (no rng, no sim writes); disabled if the officer mmis have no ShaderMaterial after `BattleVisuals.apply` (no c19sr swap). c19 polish test line 81 now reads `20 == 20` multimeshes (+4 officer mms; outside the outcome hash).
    - Crew xfade DONE: crew loop passes `BattleVisuals.xfade_crew(v, k, q, cur, cc, cct, 1.0, vt)` as the last `_put` arg for sr crews (cur: 5 dead, 2 rout/fled, 4 firing, else 0); non-sr crews stay white.
    - Verified on lead-dev and main: `--import` 0 errors, 140/140 + test_audio 28/28, outcome hash `0e814dda…`, SIMHASH SWE1800 `f7255ebb…` USA1914 `45cf5510…` JPN1500 `9bb2394d…`, 0 SHADER ERROR.
    - Readability gate PASSED: 1800 NOR red vs SWE blue at close/mid/top on q0/q1/q2 (`deliverables/v0.3.3/screenshots/compare/sheet_1800SWE_q{0,1,2}.png`, 3-way v0.3.1/v0.3.2/v0.3.3). Close defender view: SWE coats read blue (no longer near-black). Other eras q1 unchanged.
    - Perf vs v0.3.2 (llvmpipe, 1600x900): 1800 SWE mean q0 +3 %, q1 −1 %, q2 at parity after re-run (first pass q2 top +62 % was noise; re-run 294/303 vs 315/296 ms).
    - @BJORN (low priority): at overhead the red/blue is right but the figures are only a few pixels, so the lines still read mostly as white specks on snow (white trousers/crossbelts dominate). If cheap, push the tint onto trousers/shako at >90 m too.
- **READY: 2026-10-23 01:00 EDT, audio bot, music and military audio system**
  - Branch `audio` (worktree `/workspace/ic_audio`), based on `lead-dev` fa2081b. Not pushed and not merged.
  - What changed:
    - 75 original procedurally synthesized Ogg files (6.25 MiB) in `game/audio/`, with their generator in `pipeline/audio/`.
    - The `Audio` autoload `game/scripts/audio/audio_manager.gd` and the bus layout `game/audio/default_bus_layout.tres`.
    - `game/tests/test_audio.tscn` (28 checks).
    - `AUDIO_LICENSES.md`.
  - Lead-owned touches (minimal):
    - `project.godot`: the autoload line and `[audio] buses/default_bus_layout`.
    - `hud.gd`: one line in `build_settings()`.
    - `FEATURE_STATUS.md` and `CHANGELOG.md` rows.
  - The sim, combat, models and terrain are untouched. Audio only reads BattleSim events.
  - Verified:
    - test_audio 28/28. Full suite 135/135.
    - Sim hashes are identical to fa2081b.
    - The battle demo BATTLERESULT is identical with audio on and off.
    - `fix_infer` is clean.
  - Not verified: human listening, exported builds.
  - Known issue: exit leak warnings appear only under `--write-movie` (see CHANGELOG).
  - Preview mix: `/workspace/ic_audio/out/audio_preview.ogg` (not in git).
- **MERGED into `lead-dev` (audio bot, 2026-10-23 07:45 EDT, approved by Kirk):** `lead-dev` 6f2e530 was merged into `audio` (merge 1cd066e; conflicts only in CHANGELOG.md and COLLAB.md, both sides kept), then `lead-dev` was fast-forwarded to `audio`. Not on `main` and not tagged.
  - Verified on the merged tree:
    - 140/140 tests and test_audio 28/28.
    - SIMHASH SWE1800 `f7255ebb…`, USA1914 `45cf5510…` and JPN1500 `9bb2394d…`, identical to lead-dev 6f2e530.
    - The main scene boots with `Audio` (5 buses; campaign music playing).
  - @Lead: no lead-owned code changed beyond the earlier two lines (`project.godot` autoload and `[audio]` bus layout; `hud.gd` `build_settings()`). PROGRESS.md was left alone, and your uncommitted edit in the worktree is untouched. `.gitignore` now ignores `out/`. Exports need re-exporting to include `game/audio/` (the imported `.ogg` files are picked up by `all_resources`, so no `include_filter` change is needed).
- **READY: 2026-10-23 13:30 EDT, Rob (lead dev), combat animation prototype v1**
  - Branch `proto/anim-combat-v1` (worktree `/workspace/ic_anim`), based on `origin/main` a3f4f35. Pushed. Not merged into `main`.
  - Commits: 87dad4f (renderer and clips, WIP), 3099085 (real retreat), plus this one (deliverables and docs).
  - Behind the flag `--anim-v1`, which is **off by default**. With the flag off, the render path is byte-for-byte the legacy one.
  - Interface: `ANIM_INTERFACE.md` covers the hooks, the VAT layout, the clip table, the weapon tip, the bake, the rout and the known limits.
  - Clips are appended after the reserved rows, in `pipeline/blender/soldier_anim_combat.py`. `char_anim.py` is untouched.
    - med_spear: rows 162 to 392.
    - c19sr_line: mk_*.
  - Horses and cavalry are untouched (their motion, textures and materials are unchanged).
  - What it does:
    - Spear melee: a contact gap, front ranks thrusting and recovering, hits, collapse, and pk_guard.
    - Real retreat: a staggered turn of about 180°, a forward jog, glances over the shoulder, stragglers, and loosening.
    - Muskets: march, aim, fire and reload, with the flash and smoke at prop_tip.
    - Bows: the arrow leaves at the release frame.
    - Flag-on facing fix.
  - Verified (flag off, compared with the baseline):
    - Tests 163/163 and audio 28/28. 0 SCRIPT ERROR.
    - Outcome hash `553cc500…`.
    - SIMHASH SWE1800 `417a5300…`, USA1914 `4679c5a2…` and JPN1500 `e104d558…`, all identical.
    - Demo hashes are identical with the flag off and on: spear `ae9064e0…`, musket `7da20616…`.
  - Perf (llvmpipe 1280x720; a concurrent Godot from another agent added noise):
    - units_us median: spear 1303→1458, retreat 1318→1456, musket 958→1069 (+10 to 12 %).
    - Frame times are dominated by contention.
  - Footage, at normal speed: `deliverables/anim-proto-v1/{spear,musket,retreat}_{on,off,before_after}.mp4`. Stills are in `deliverables/anim-proto-v1/stills/`.
  - @BJORN:
    - Please add a `weapon_tip` bone. We currently fall back to prop +Y.
    - Should the grenadier and officer mk_* rows be appended in your bake or in mine?
    - Can the combat clips be hooked into `char_build.py bake`?
    - The legacy VAT yaw renders soldiers facing away from the enemy (atan2 sign). It is fixed only on the flag-on path. Should we fix it in legacy as well?
- 2026-10-23 13:50 EDT (Rob, `proto/anim-combat-v1`):
  - The retreat now walks at normal pace (be61c6c), and the footage was re-recorded (a2ee9d8).
  - Horse gaits are motion only (74b9053):
    - walk is a 4-beat gait, trot moves diagonal pairs, canter is 3-beat and gallop is a transverse 4-beat;
    - there are transition clips between gaits;
    - the head nods in sync with the gait.
  - The appended VAT rows are 144–425. Legacy rows 0–143 are byte-identical, and no GLB, texture or material changed.
  - Hash check: see `deliverables/anim-proto-v1/HASH_CHECK.md`. Results are identical to clean a3f4f35 with the flag off and with it on.
  - @BJORN: if you re-bake cav from `cavalry.py`, please re-run `pipeline/blender/cavalry_anim_combat.py bake` afterwards. It appends the hv_* rows.
- 2026-10-23 15:05 EDT (Rob, `proto/anim-combat-v1`, commits 3c2474b, 0a460c7, a010167, 6d914ba, plus this one):
  - Horse gaits v2 (3c2474b). Root cause of "gaits look the same": the hv_* rows did play, but the legs barely moved (hoof travel 0.5–0.8 m vs 1.72 m for the legacy run, legs near full extension so the body bob dominated, upper legs hidden by the caparison), and knights (vmax ~6.07) never reached GAIT_UP 6.2, so the gallop never showed. Fix: larger swing overreach/lift/fold per gait, body lowered 3–9 cm so stance legs flex, GAIT_UP now [0.25, 1.35, 2.8, 5.6]. Stance amplitude unchanged, so cadence and v_nom are unchanged. Motion only; no horse GLB, texture or material changed.
  - Cavalry death (3c2474b): when the sim marks a cav unit fled (or hides it), each horse plays cv_die_a/b/c (VAT rows 426–569, play-once, 48 frames), staggered 0–1.5 s per instance; riders fall, horses go down and stay. No ride-away. Sim timing untouched. Note: the sim freezes a fled unit's pos, so the legacy >260 hide is rarely reached; the trigger is the "fled" state.
  - Infantry retreat is all-at-once: one turn moment for the whole regiment, walk pace (ANIMSPEED p50=p99=1.40 = walk), no fighting or glances after the turn.
  - Footage: `deliverables/anim-proto-v1/{horse_side,charge,cavdie,retreat}_{on,off,before_after}.mp4`; strips in `stills/`.
  - Checks @3c2474b: tests 163/163 (flag off and on), audio 28/28, SIMHASH and BattleView BATTLERESULT identical to a3f4f35 with the flag off and on. See HASH_CHECK.md.
  - VAT total is now 570 rows; legacy rows 0–143 are md5-identical. @BJORN: if you re-bake cav, re-run `pipeline/blender/cavalry_anim_combat.py bake` afterwards.
- **MERGED to `main` 2026-10-23 ~17:25 EDT (Rob, Kirk approved): `proto/anim-combat-v1` @5488984 merged into main e7964f8 (after the biome-framework/tropical/east_asia merges).** `--anim-v1` stays OFF by default.
  - One conflict, in `battle_view.gd` (the preload block): kept both main's `BattleEnvironment`/`biome`/`env`/`_scatter_dry` and the `AC` preload. Everything else auto-merged; anim state is lazy per regiment, so v0.5 reinforcements (`_build_reg`/`_sync_regs`) work with the flag on.
  - Checks on the merge vs a clean e7964f8 worktree: test_runner 205/205 (flag off and on), test_audio 28/28, test_env 0 failures (off and on), 0 SCRIPT ERROR in the suites. SIMHASH SWE1800 0b3153c6…, USA1914 a9beef57…, JPN1500 563be302…, identical (off and on). BattleView BATTLERESULT for SWE 1300/1650/1800 and USA 1914 and `--demo=reinforce`: identical to main (off and on).
  - Flag-on anim demos (spear, musket, cav, cavdie with `--env=1 --env-prov=328`) run without script errors; the boreal biome renders with the new clips.
- **2026-10-23 ~18:15 EDT (Rob, main, Kirk approved): combat animations v1 are now ON by default.** `AC.on` defaults to true and `BattleView.setup()` applies `AC.resolve_from_runtime()`.
  - Disable for troubleshooting: `--no-anim-v1` or `--anim-v1=off|0|false` (user arg, after `--`), env var `IRONCROWNS_ANIM_V1=0`, or project setting `iron_crowns/battle/anim_v1=false` (override.cfg). Precedence: command line > env var > setting > ON. `--anim-v1` is still accepted (= on).
  - New test_runner checks (5): default on, the off switches, legacy flag, env/setting precedence, and that setup() applies the switch. test_runner 210/210 (default and `--no-anim-v1`), audio 28/28, test_env 0 failures, 0 SCRIPT ERROR in the suites.
  - SIMHASH (SWE1800 0b3153c6…, USA1914 a9beef57…, JPN1500 563be302…) and BATTLERESULT (SWE 1300/1650/1800, USA 1914, `--demo=reinforce`) identical to clean main f04d0aa, both with the default and with `--no-anim-v1`.
  - No Windows build was exported (Kirk: wait for the full-playtest build).
