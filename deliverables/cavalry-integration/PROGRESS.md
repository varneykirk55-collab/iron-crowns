# Cavalry integration (Rob) — progress
Branch rob/cavalry-integration = rob/cavalry-animation-overhaul + Bill's frozen horse v3 (origin/agent/horse-visual-overhaul ab70c61, read-only).

## 2026-10-23 21:50 EDT — merge + real-mesh bake
- 2e271f6: merge of ab70c61 (Bill's files untouched).
- bf565a0: pipeline/blender/horse_v3_bake.py (new, Rob) loads horse_v3.blend read-only → horse_anim bake (`--mesh=v3`).
  - Rig check: Bill's armature = HX_BONES (57 bones, max head/tail diff 1.3e-7 m, same parents).
  - med_knight (1300): horse_body + tail + eyes + tack_1300 + barding_1300. Mane (horse_hair part_id 0) is hidden under the crinet. LOD0 5666 v / 10682 tris, LOD1 1572 v / 2701 tris (incl. proxy rider + lance).
  - c19_hussar (1800): horse_body + mane + tail + eyes + tack_1800. LOD0 5965 v / 11122 tris, LOD1 1646 v / 2716 tris (incl. proxy rider).
  - Coat specks: covered hide verts pushed in (1300: 2.2 cm, front curtain 4.5 cm; 1800: 1.4 cm). tools/cav/hx_clip.py (coat outside cloth, all clips, LOD0): knight 68 → 29 vert-clip hits (rest are hind gaskin vs caparison hem in walk/trot), hussar 26 → 0.
  - .vatn per-frame normals + game/shaders/hx_vat.gdshader (new): v3 coats per instance from Bill's COATS (points mask = UVMap.u), smooth shading. Proxy/legacy VATs keep vat.gdshader.
- 4713c8d: merged the lit gait videos from the proxy branch.

## 2026-10-23 22:05 EDT — fixes, visuals stopped, suite running
- 834f1ad: white team base on Bill's team-masked cloth (he paints a preview red, horse_v3_config.TEAM_RGB; runtime dyes base × team colour). Disabled Godot's Blender importer in project.godot: horse_v3.blend in game/ aborted the whole headless import. .import/.uid files added.
- Real-mesh render check (Godot, knight side cam): mesh, smooth normals, rider seat and gait OK. Team cloth was dark before the team-base fix.
- Kirk's order: all video and screenshot work stopped. The real-mesh demo videos were NOT recorded.
- Running: full suite (test_runner, audio, test_env, 3 SIMHASH, BATTLERESULT ×4, reinforce) on this branch vs clean origin/main 41bdd75 (already contained in this branch).

## 2026-10-23 22:15 EDT — suite PASS vs clean origin/main 41bdd75 → merging to main
- test_runner 220/220 (main 216/216 + 4 new cavalry checks), audio 28/28, test_env 0 failures (same as main).
- SIMHASH SWE1800 0b3153c6…, USA1914 a9beef57…, JPN1500 563be302…: identical to main.
- BATTLERESULT SWE1300/1650/1800/USA1914 and reinforce lines are byte-identical to clean main.
- Open: no real-mesh videos (stopped by order). Knight hem/gaskin clipping (29 hits) remains in walk/trot. Cuirassier still uses the proxy. Real-mesh LOD2 isn't wired. The rider is a proxy. Perf not re-measured.
