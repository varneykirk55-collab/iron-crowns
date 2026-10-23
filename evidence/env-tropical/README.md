# Evidence: env/tropical (Philippines, Indonesia, Malaysia, Amazon, Congo, Caribbean, Central America, Hawaii)

Built on `env/biome-framework`. It uses the Scandinavian build as the design language and quality bar: the same tiled MultiMesh scatter, LOD and quality tiers, obstacle-corridor rules and ground shader. Every asset and parameter is new and tropical. There are no pines, heather or granite.

## Look (driven by province data, see `game/scripts/battle/biomes/tropical.gd`)
- **Fighting ground:** an open clearing of cogon / guinea grass on red laterite soil, with little straw (`dry` ×0.35).
- **Outside the corridor:** dense multi-layer rainforest walls on every terrain (forest ≥ 0.92). The layers are canopy trees with buttress roots, emergents above the canopy, coconut palms on the fringes (twice as many on coastal provinces), and a banana, fern and thicket understorey (fern 1600, thicket 3200, banana 500 per field).
- **Rock:** dark, mossy basalt (volcanic islands).
- **Light:** humid and hazy, with a high sun, saturated greens and pale haze-blue distant ranges. These are haze, not snow: the snowline is 3600 m.

## Files
- `compare_p517_q{0,1,2}.jpg`: Manila (prov 517). BEFORE (legacy `--env=0`) and AFTER side by side, from the seven identical scripted cameras at battle t = 14 s.
- `compare_p518_q{0,1,2}.jpg`: Iloilo (prov 518), the same layout.
- `before/`, `after/`: every shot as a 1200 px jpg (`p<prov>_q<N>_<view>.jpg`).
- `perf.md`: CPU ms per frame before and after, at q0, q1 and q2, for both provinces.
- `keyframes/`: frames from the battle video at video time NN s.
- `battle_result/`: the `BATTLERESULT` line from the video run, plus the legacy `--env=0` reference from `env-scandinavia`.
- `ASSETS.md`: provenance (all procedural and original).
- **Video** (not in git, 34 MB, H.264 1600x900 at 30 fps, 51.6 s): `/workspace/ic_env_tropical/out/video/env-tropical-battle.mp4`. The demo battle was recorded with `--env-prov=517` (Manila dressing). The video and keyframes were recorded at 14:34 EDT, before the 4c0cd68 perf trim, which put about 25 % fewer thicket and slightly fewer trees outside the corridor. The compare images and perf numbers are post-trim.

## How the previews were made
The demo battle (`--demo=battle --year=1300 --nation=SWE`, Battle of Malmö) is used with `--env-prov=<id>`, which dresses the same battle with another province's environment. Cameras, units and battle time are therefore identical between before and after, and between regions. The HUD still says "Malmö"; only the scenery is from the named province.

## Combat / sim untouched
- `BATTLERESULT` from the tropical video run is **byte-identical** to the legacy `--env=0` run: md5 `f09210137aaecedfefe8512f38e7d609`, 33.4 s, winner 1, end men 1232 / 4176.
- sim_hash matches main: SWE 1800 `417a53009d4b9c30b4c938a756b33f78`, USA 1914 `4679c5a24c8d055f95c9ea95ff868193`, JPN 1500 `e104d558aa9370b28c02ca58db54ae33`.
- test_runner (163/163), test_audio (28/28) and test_env (0 failures; includes corridor clearance over 24 real battles) all pass, re-run at 4c0cd68 + framework 64c912d (`tests/`).
- No morale, pathfinding, combat, soldier-model or rules files are touched. The diff is limited to `biomes/tropical.gd`, the Blender script, the generated models and the docs.
