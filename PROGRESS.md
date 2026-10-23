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
NEXT: merge pre-graphics lead-dev to main, export, deliverables/v0.2; on revised READY: re-apply on graphics, retest, merge to main.
