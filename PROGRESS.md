# PROGRESS (executor notes)
## Done
- Core sim (game/scripts/core/sim.gd, battle_sim.gd, game_data.gd), data, map data. Test suite 61/61 (test_results.txt).
- Blender pipeline + assets (glb, VAT). Team mask in UV2.y (team = 1-UV2.y). Blender: /workspace/tools/blender/blender
- Written, untested: shaders/map.gdshader, scripts/map/world_map.gd, map_camera.gd, shaders/team_prop, vat, particle(_add), tracer, ground, banner; scripts/ui/flag.gd, hud.gd
## Next
1. scripts/battle/battle_view.gd (VAT crowds, particles, camera, HUD, result)
2. scripts/main.gd (menu, map, input, battle transition, demo modes)
3. compile (tools/fix_infer.py), render PNG/MP4, fix visuals
4. rerun tests, exports, README, FEATURE_STATUS, ZIP

## Session 3 (2026-10-22 afternoon)
- FIXED: black VAT soldiers -> GL Compatibility gives COLOR=0 for MultiMesh without instance colours. All battle/map MultiMeshes now use_colors (white); buffer stride 16/20.
- FIXED: battle "horizon skirt" plane floated 7 m above the field and buried the armies from any camera above ~7 m (the cause of empty engage/top shots and dark shadowed ground). Now placed below min field height.
- FIXED: deploy window centring (_center_win), map trees/cities white (vc material + instance colours).
- Demo: --reinforce=N buys N of each era unit for the defender and stages that army on the first province of the invasion route (documented demo staging). Battle of Pennsylvania now 10 v 10 regiments, ~25 s sim, legit DEFEAT result.
- Verified shots: shots/battle_USA_close0/close1/top/engage/melee/result.png all show armies.
- NEXT: campaign demo re-render, diplomacy/era demos (+ era step bug), MP4s, tests, export, docs, zip.
- Session 4 (16:50): map markers decluttered at world zoom (only player/enemy/battle/siege armies when cam_dist>100), marker scale cap 3.2, province labels bigger, ocean wave moire fade (map.gdshader). Battle ground darkened x0.82, engage cam dist 80.
- Plan now: battle MP4 -> deliverables first draft (README, FEATURE_STATUS, ZIP) -> then campaign/diplo/era.
- 16:55 export_presets.cfg created; Linux + Windows exports OK in build/ (Linux build verified rendering menu under xvfb). Battle movie recording -> rec/battle.avi (in progress).
- 17:00 README.md + FEATURE_STATUS.md drafted (root; copy to deliverables).
- 17:03 tools/package.py builds deliverables/ (project zip 11.8MB, linux 39MB, win 49MB zips, screenshots). First deliverables in place; videos pending.
- 16:58 battle MP4 recorded: rec/battle_USA_full.mp4 (38 s, 13 MB) -> deliverables/videos. Result panel only ~1 s on screen; todo hold longer.
- 17:05 diplomacy/economy + era demos render OK (era wait bug no longer reproduces). Fixed: Nordic inner cross flags, toast offscreen, int formatting, era 'after' shot timing (shot same frame as hide), demo holds for deploy/result, marker scale 0.02.
- 17:20 toast fixed (manual centring in _process); recording all 4 demo MP4s via tools/record_all.sh (bg). NEXT: inspect, tests, export, package.
- 17:33 all 4 MP4s recorded+inspected (campaign 17s, diplomacy 12s, era 8.5s, battle 44s w/ result panel). Tests 61/61. NEXT: export, docs, package.
- 17:40 exports rebuilt (build/ had vanished) + Linux smoke OK; FEATURE_STATUS updated; packaging.
- 17:42 DONE: deliverables repackaged (all 4 MP4s, 25 PNGs, 3 zips).

# v0.2 phase (lead dev) — started 2026-10-22 19:05 EDT
- Step 0 DONE: git repo (main, tag v0.1), branches lead-dev + graphics, worktree /workspace/ironcrowns-lead (lead-dev). COLLAB.md committed. Graphics = BJORN at /workspace/iron-crowns-visual (do not edit).
- NEXT: import worktree, task 1 save/load.
- [x] Task 1 save/load: Sim.serialize_state/apply_state, binary Variant saves in user://saves (meta + state), BattleSim.to_dict/from_dict.
  - Test `--only=save` 8/8 PASS (deep equality + 180-day forward determinism, missing slot, list).
  - UI: F5 quicksave, F9 quickload, ☰ Menu (Esc) window with quick save/load, new slot, saved games list; title menu lists saves with Load.
  - Demo `--demo=saveload` verified (shots/v02/saveload_*.png): saved 31 Jan 1800 -> advanced to 1 May -> F9 -> 31 Jan 1800.
  - Watched battles load as unwatched; awaiting (deploy) battles re-show the deploy window.

## v0.2 — Task 2 cinematic camera (DONE, tested)
- battle_view.gd: two rigs (overhead/cinematic) blended over 1.25 s smoothstep; event-driven director (establishing, tracking on charge, flank on first volleys, low_angle at melee start, rout, aftermath); deterministic, read-only on sim.
- C key / joy Y (InputMap `camera_toggle`) + HUD button; wheel/drag/stick returns to overhead.
- test `--only=camera` 5/5 PASS (27 toggles + zoom → identical battle, 365/365 steps).
- tools/rec.sh records demos (movie maker 30 fps) → rec/<name>_demo.mp4.

## v0.2 — Task 3 controls (DONE, tested headless)
- core/controls.gd autoload `Controls`: 37 InputMap actions (kbm + joypad), settings (ui_scale, large_targets, touch_rotate, quality, show_perf) persisted in user://settings.cfg.
- main.gd input is action-based; gamepad map cursor reticle (ui/pad_cursor.gd), A select / X move at cursor, LB/RB armies, D-pad ↑↓ provinces ←→ speed, Y pause, Back diplomacy, L3 economy, R3 panels, Start menu, B back.
- HUD: visible focus ring, gamepad focus auto-grabbed in open windows, follow_focus scroll, settings rows in game menu, device-specific hint text.
- Touch (map_camera.gd): tap select, drag pan, pinch zoom, twist rotate, long-press move; emulated mouse ignored; taps on HUD ignored. Battle view: pinch/drag/twist, sticks, RB speed, Back leave.
- No virtual joysticks/overlays (checked in test).
- test `--only=controls` 19/19 PASS with synthesized InputEventJoypadButton/Motion, ScreenTouch, ScreenDrag.
- Task 4 groundwork: ui/perf_overlay.gd (F3), Sim.perf_tick_us, BattleView.perf timings, quality setting (MSAA + battle LOD/sun shadow).

## v0.2 — Task 4 performance (DONE, measured)
- Profiling: `--perfout=<json>` per-frame samples (frame ms, FrameProbe script ms, sim tick, battle sim/units/fx, render cpu/gpu, draw calls,
  primitives, instances) + `tools/perf_summary.py`. FrameProbe replaces Performance.TIME_PROCESS (it over-reported). F3 overlay shows the same.
- Fixes (all CPU): HUD selection panel rebuilt only when a signature changes (was ~110 ms every 0.25 s); month tick: per-month economy
  tables, strength/alliance tables in AI war scan, cheap relation filter first, unit_power memo, drift w/o string split; map markers stack index
  O(A) instead of O(A²). Sim result bit-identical: tests/sim_hash.tscn hashes serialize_state after 3×800 AI days — same md5 before/after.
- Headless (pure CPU) SWE 1800 battle demo: map frame 20.2→9.3 ms (p95 115→12.7), battle 20.1→7.7 ms (p95 113→9.7).
  Bench: month parts econ 48→5 ms, diplomacy 180→65 ms, worst day 245→~105 ms, hud._process 116→9 ms, update_markers 6→2 ms.
- xvfb/llvmpipe 1280x720 is render-bound (~2 fps, render_cpu 185–300 ms): software rasteriser, no GPU; not fixable in game code.
## v0.2 — Task 5 era verification (DONE: tests + 5 era recordings)
- `--only=eras` 26 checks: roster/models per era, full battle per era (30–34 s, era-only units), projectile classes per era, melee share
  falls with era, medieval armour (knights) and modern armour (MBT) effects, USA/SWE/JPN start armies in all 5 start years.
- Battle view prints `BATTLERESULT {json}` (units, models, projectiles, melee share, outcome) on the result panel.
- Recordings rec/era_{1300_SWE,1500_JPN,1800_SWE,1914_USA,1914_USA_reinf,1980_USA}_demo.mp4: era-only units, battle 33.4/32.3/39.5/17.8/28.8/31.0 s
  (1914 without reinforce is a 9.7:1 mismatch). Fixed: aftermath shot never fired; P/W model names in BATTLERESULT.
## v0.2 — Task 7 full pass (DONE)
- `--only=gameplay` 7 checks (Sweden 1913: march, war, watch battle + camera toggle, capture, save/load, 1914 era advance). Full run 127/127 (pre-graphics).
## v0.2 — Task 6 graphics (BJORN c19 handoff)
- Patch + binaries applied on `graphics` (6b58baf, binary sha256 verified). Merged into lead-dev-gfx, hooks d1c8a22: apply(self) at end of setup,
  apply_quality forwarding (only once his apply_quality exists), apply_viewport NOT called (Controls quality owns MSAA). 131/131, sim hashes unchanged.
- NOT on main: parent asked to wait for BJORN's revised READY (brightness/readability). main = v0.2 without visuals.
- v0.2 shipped from main without visuals (deliverables/v0.2).
## v0.2.1 — BJORN FINAL c19 handoff (116c310) MERGED
- `graphics` 42998e4: old 6b58baf content reverted to c0b0d8d, final patch + 14 binaries applied (sha256/size verified); tree identical to 116c310
  except his PREVIEW-ONLY main.gd (2a36972, excluded per R4). lead-dev 173e70c merge, 8ebdb95 wiring: BattleView.apply_quality() and
  main.apply_quality() forward Controls.quality to BattleVisuals.apply_quality(q) (single owner; stand-in + QUALITY_LOD + MSAA line removed),
  `--quality=` session override. 131/131, sim hashes unchanged, rendered 1800 SWE battle at q0/q1/q2 with identical BATTLERESULT.
- main f28ce42 merge, tag v0.2.1, deliverables/v0.2.1.

## v0.3 — eras batch + polish pass (DONE)
- [x] graphics 1f7f279 (BJORN eras 1c951b9) + 882366e (BJORN polish 5adecc2, main.gd excluded per R4) merged to lead-dev (1ccdc1c, b190120)
- [x] R5 map_visuals hook + marker click/selection tests, R6 medieval test update (fa2081b)
- [x] Polish requests: grenadiers model c19_grenadier (make_gamedata.py/units.json), CREW_MODEL per-era crews, --import new glbs (0 errors) (670335a)
- [x] Full suite 140/140; gameplay outcome hash 0e814dda… matches; sim hashes USA/JPN match, SWE1800 changes to f7255ebb… only because the serialized regiment "model" string changed (state dumps differ only in those 2 lines)
- [x] Polish re-renders: 5 eras q1, BATTLERESULT identical to pre-polish recordings; c19 grenadier/gun-crew close-ups + tundra/forest/hills overhead (harness on production BattleView.setup); campaign world/region/close for 5 starts
- [x] main merge (0dcaa7b), main 140/140 twice, gameplay hash 0e814dda match, sim hashes as lead-dev; exports Linux+Windows; Linux export smoke (1800 SWE battle: 39.5 s, [5039,5166], winner 1, soldiers render); tag v0.3; deliverables/v0.3 + laptop_xfer

## v0.3.1 — graphics-map (53b3dcd) integration (IN PROGRESS, started 01:17 EDT)
- [x] merge graphics-map into lead-dev: 6db2728 (COLLAB conflict only; world_map.gd auto-merged, R5 hook kept after apply_era)
- [x] --import 0 errors; full suite 140/140 (out/tests_v031.log); SIMHASH SWE f7255ebb USA 45cf5510 JPN 9bb2394d all match
- [x] map_shots.gd: +3 views europe_world, borders_close, usa_world (streak check); before shots from v0.3 tag worktree /workspace/ic_v03_before -> out/v031/before
- [x] after shots (merge 6db2728) picks 15/15 views identical to v0.3 and 12/12 to v0.2.1 baseline (out/v031/picks_compare.log)
- [x] STREAKS: still present after terrain merge; cause = z-fighting of deep-ocean backdrop plane (y -0.12) with ocean (-0.06) at world zoom (depth res ~0.1 at 300 u, near 0.05). Fix: backdrop to y -1.5 in world_map.gd (not a shader issue; mipmapped bathymetry tried, no effect). Verified out/v031/exp/expB_usa_world.png
- [x] 3012eab: after re-rendered, picks 15/15 + 12/12 match; tests 140/140 (out/tests_v031b.log), SIMHASH all 3 match, gameplay hash 0e814dda match; compares out/v031/compare/
- [x] perf q0/q1/q2 -> out/v031/perf_table.md (mean Low -47%, Med -29%, High -34%; close mountains Med/High +16..+28%)
- [x] docs (CHANGELOG, FEATURE_STATUS, README, COLLAB MERGED v0.3.1, MAP_PROGRESS)
- [x] main merge 7afd10b + 5bffeb0 (docs timestamps); main --import 0 errors
- [x] main 140/140, sim hashes + gameplay hash match; tag v0.3.1 -> 5bffeb0
- [x] flyover out/v031/map_flyover_v031.mp4 (23.5 s, 1600x900)
- [x] exports Linux+Windows (build/), Linux smoke OK (out/v031/smoke: campaign map + terrain, battle MM vis>0)
- [x] deliverables/v0.3.1 packaged (120 files, SHA256SUMS ok); laptop_xfer w031.part00-06 + p031.part00-02 + join031.ps1 (tested with pwsh 7.4: OK path + HASH MISMATCH path); ic_v03_before worktree removed
- DONE v0.3.1 (02:05 EDT). Parent to copy deliverables/v0.3.1 to laptop.

## v0.3.2 — BJORN character-refinement (d93f576) integration (IN PROGRESS, started 05:25 EDT)
- [x] 456aa8d (author BJORN) patch sha 17475580 + tarball f7b0dfc4 (28 files); tree == d93f576 minus hooks; --import 0 errors (out/import_v032.log)
- [x] ffcafd3 R1 + R2. R3 skipped (officer has no vat id/material path without battle_visuals change), R4 skipped (ids pinned by tests + serialized model string -> SWE hash)
- [x] ffcafd3: 140/140 (out/tests_v032.log), gameplay hash 0e814dda, SIMHASH SWE f7255ebb USA 45cf5510 JPN 9bb2394d, 0 SHADER ERROR
- [x] delta check 05:45: none in iron-crowns-visual/out -> v0.3.2 without delta
- [x] docs (CHANGELOG, README, FEATURE_STATUS, COLLAB BJORN READY copied from main worktree + MERGED v0.3.2 note w/ readability request)
- [x] main merge 21bbfe1; main --import 0 errors, 140/140, gameplay hash 0e814dda, SIMHASH SWE f7255ebb USA 45cf5510 JPN 9bb2394d, 0 SHADER ERROR; tag v0.3.2 (annotated)
- [x] exports Linux+Windows (build/); Linux export smoke 1800 SWE battle (--closeup --vispass): 39.5 s, winner 1, [5039,5166] = v0.3.1, MM vis>0, c19_line col non-white (xfade), 0 script/shader errors
- [x] battle video rec/battle_SWE1800_v032_demo.mp4 (62 s, 1280x720)
- [x] delta re-check ~06:10 EDT: still none -> BJORN delta goes to v0.3.3 on main@v0.3.2
- [x] deliverables/v0.3.2 + laptop_xfer (w032/p032, join032.ps1) via out/v032/pkg/package_v032.py
- [x] harness game/tests/battle_shots.{gd,tscn} (untracked yet): main --demo=battle, freeze at sim t=14 (time_scale 0), views close/close_def/mid/top, shot + 30-frame median. before worktree /workspace/ic_v031_before (v0.3.1 + harness copy)
- [x] out/v032/run_shots.sh done -> out/v032/shots, compare/, perf_table.md; other eras q1 unchanged visually
- [x] 1800 SWE q0/q1/q2 before/after shots + perf -> out/v032/compare/, out/v032/perf_table.md (q0 -11 %, q1 +4 %, q2 -17 % mean; noise ~+/-15 % per view)
- [!] READABILITY: 1800 NOR(attacker, HUD red) vs SWE: new uniforms are both blue (NOR 3a5f95 light blue, SWE 2a3d6e navy) + white trousers on snow -> sides hard to tell apart at mid/top; v0.3.1 read red vs blue. Request to BJORN.

## v0.3.3 (BJORN character-refinement-2 + R3 officer + crew xfade) — started 07:35 EDT
- [x] lead-dev ff to main 2b9f73b; 2a7c5ae = BJORN 667e980 (patch f932a795…, binaries c7c709a5…, 16 files); tree == refs/bjorn/char2 except PROGRESS.md (main post-tag); --import 0 errors
- [x] 6f2e530 R3 officer (one c19sr officer per c19_line/c19_grenadier regiment, right of front rank, own xf_off state; render only) + crew xfade_crew (sr crews only)
- [x] 140/140 (out/tests_v033.log), outcome 0e814dda, SIMHASH SWE f7255ebb USA 45cf5510 JPN 9bb2394d, 0 SHADER/SCRIPT ERROR; c19 polish test now "20 == 20" multimeshes (+4 officer mms; line 81, outside the 61-line outcome hash)
- [x] out/v033/run_shots.sh (before = /workspace/ic_v032_before @v0.3.2, after = lead-dev; v0.3.1 shots reused from out/v032/shots) -> 3-way compares + perf vs v0.3.2
- [x] 3-way compares out/v033/compare/ (sheet_1800SWE_q{0,1,2}, crop_*, other eras); perf out/v033/perf_table.md (q0 +3 %, q1 -1 %, q2 first pass +16 % from noisy top +62 %; re-run out/v033/rerun/perf_q2.log -> parity)
- [x] readability gate PASSED (viewed myself): NOR red vs SWE blue at close/mid/top q0/q1/q2; close_def SWE blue not black; officer visible (bicorne, left of SWE line in close_def); 1300/1500/1914/1980 unchanged
- [x] audio bot merged audio into lead-dev 07:45 (a526478, Kirk-approved) -> re-verified lead-dev: import 0 err, 140/140, 0e814dda, simhash same, test_audio 28/28 -> ships in v0.3.3
- [ ] docs commit -> main merge --no-ff, tag v0.3.3, verify on main, exports, smoke, video, deliverables, laptop_xfer w033/p033
