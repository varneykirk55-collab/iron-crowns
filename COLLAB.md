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
