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
