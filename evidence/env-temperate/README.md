# Evidence: env/temperate (deciduous / mixed temperate forest, prairie, Rockies)

This branch is built on `env/biome-framework` and contains `main` at 77306f4 (v0.5.0, the merged framework / tropical / east_asia regions, and combat animations v1 on by default). It uses the Scandinavian build as its design language and quality bar. It keeps the same tiled MultiMesh scatter, LOD and quality tiers, engagement-corridor rules and ground shader. The species, understorey, ground palette and seasonal light are new and temperate. Nordic models are reused only where the species is genuinely shared (spruce / pine in the Rockies and Cascades, Scots pine in Europe, granite in the Rockies, reeds on shores), and are re-tinted.

## Look (driven by province data, see `game/scripts/battle/biomes/temperate.gd`)
- **Which provinces:** eastern / midwestern North America, Atlantic and central Europe below 57 N, New Zealand and the other mid-latitude provinces that are not boreal, steppe, mediterranean or east_asia.
- **Forest:** white oak, sugar maple and ash with eastern white pine (Americas) or Scots pine (Europe). Hazel and bracken understorey; meadow grass and wildflowers in the open; buff limestone ledges and boulders.
- **Sub-regions from the data:**
  - **Rockies / Cascades** (Americas west of 100 W on hills / mountains): spruce / fir / pine conifer forest on granite.
  - **Prairie / farm belt** (Americas plains, 100..85 W): open tall-grass country, oak groves, few woods.
  - **Europe:** oak / ash / maple woods with Scots pine.
- **Seasons:** the battle date's month (`Sim.date_parts`, hemisphere-aware) sets foliage tints, grass dryness and the sun: spring fresh green, summer full green, autumn red / gold canopy, winter brown dormant hardwoods with green pines. Preview override: `--env-season=spring|summer|autumn|winter`.
- **Light:** soft mid-latitude sun; lower and warmer in autumn, low and cold in winter.

## Files
- `compare_p64_q{0,1,2}.jpg`: New York (prov 64, forest), summer. BEFORE (legacy `--env=0`) and AFTER side by side from the seven identical scripted cameras at battle t = 14 s.
- `compare_p62_q{0,1,2}.jpg`: Illinois (prov 62, plains: prairie sub-region), same layout.
- `compare_p49_q{0,1,2}.jpg`: Colorado (prov 49, mountains: Rockies conifer sub-region), same layout.
- `seasons_p64_q1.jpg`: New York at q1 in spring, summer, autumn and winter (overview, formation and forest_edge cameras). The raw shots are in `seasons/`.
- `before/`, `after/`: every shot as a 1200 px jpg (`p<prov>_q<N>_<view>.jpg`).
- `perf.md`: CPU ms per frame before and after at q0, q1 and q2 for all three provinces.
- `keyframes/`: frames from the battle video at video time NN s.
- `battle_result/`: the `BATTLERESULT` line from the video run and from a legacy `--env=0` run on the same code, plus `sim_hash.txt`.
- `tests/`: test_runner, test_audio and test_env results after merging main.
- `ASSETS.md`: provenance (all procedural and original) with triangle counts.
- **Video** (not in git): `/workspace/ic_env_temperate/out/video/env-temperate-battle.mp4`, 18.2 MB, H.264 1600x900 at 30 fps, 39.9 s. The 1914 demo battle (USA vs Canada) dressed as New York (prov 64) in **winter**: dormant brown hardwoods, green white pines, faded grass, low cold sun. Recorded on e1e1643 (before the 77306f4 main merge).

## Method
All evidence runs use the 1914 demo battle (`--demo=battle --year=1914 --nation=USA`) with `--env-prov=<id>`, so cameras, units and battle time match between before and after. The compares are summer (`--env-season=summer`); the battle video is winter (`--env-season=winter`).

## Combat / sim untouched
- `BATTLERESULT` from the video run (env on, winter) is **byte-identical** to a legacy `--env=0` run on the same code: md5 `a030d0a0572cd9bc24b790d159537bf9` (`battle_result/`). Re-checked after merging main 77306f4: env1 and `--env=0` still match each other and the pre-merge run (`a030d0a0…`, `battle_result/post77_*`).
- sim_hash after merging main 77306f4 is identical to main 77306f4: SWE 1800 `0b3153c6f9fb7c454686cb49f19cb866`, USA 1914 `a9beef573f5922b7eb83ba8f2beb5e63`, JPN 1500 `563be302cdf34e56b4a33a873230ebf1`.
- test_runner (210/210), test_audio (28/28) and test_env (0 failures) all pass after merging main 77306f4 (`tests/`).
- No morale, pathfinding, combat, soldier-model or rules files are touched. The only code change is the new `biomes/temperate.gd` (plus the procedural models and their Blender script).

## Perf reading
- **q0:** +10..+45 % CPU on open views, +27..+57 % looking into the forest (forest_edge, rocky). Top view -9..+6 %.
- **q1:** +33..+78 % on open views, +59..+203 % into the forest. Top view -7..-15 %.
- **q2:** +47..+92 % on open views, +112..+273 % into the forest. Top view -10..-16 %.
- **Why:** temperate is a forest biome like Scandinavia, so the cost sits in the same place: the shadow-casting forest wall seen at close range at q1 / q2. The figures are in the same band as the merged Scandinavian build (forest_edge +121 % / +172 % at q1 / q2) and below tropical (+290 % / +350 %). The open battle views stay under +100 % at every tier.
- **Caveat:** llvmpipe numbers on a heavily loaded shared box (load ~20 on 8 cores). Use them as relative comparisons, not absolute fps.
