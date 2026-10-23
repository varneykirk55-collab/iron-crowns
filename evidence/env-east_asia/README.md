# Evidence: env/east_asia (Japan, Taiwan, Korea, eastern / southern China)

This branch is built on `env/biome-framework` and uses the Scandinavian build as its design language and quality bar. It keeps the same tiled MultiMesh scatter, LOD and quality tiers, obstacle-corridor rules and ground shader. The species, rocks, ground and light are all new and East Asian, with no Nordic pines or heather. The only Nordic models reused are spruce and birch, and they appear only in Hokkaido and Manchuria, as Ezo spruce and white birch.

## Look (driven by province data, see `game/scripts/battle/biomes/east_asia.gd`)
- **Hills:** varied green hill country. Sugi cedar and Japanese red pine grow on the slopes. Lower down there is evergreen broadleaf (camphor / evergreen oak) and maple, with bamboo groves at the forest edge. The understorey is sasa dwarf bamboo and azalea, and susuki silver grass grows on the knolls.
- **Rock:** mossy grey andesite outcrops and boulders.
- **Latitude gradient:**
  - Hokkaido and Manchuria (>= 41 N) add Ezo spruce and white birch, plus more sasa.
  - Okinawa, Taiwan and Guangdong / Fujian (< 28-30 N) are broadleaf- and bamboo-dominated, with lusher greens.
  - Korea is red-pine country.
  - The Yangtze / North China plain gets farmland with groves (less forest).
- **Light:** soft, humid and slightly hazy, with paddy-green fields.

## Files
- `compare_p474_q{0,1,2}.jpg`: Tokyo (prov 474). BEFORE (legacy `--env=0`) and AFTER side by side, from the seven identical scripted cameras at battle t = 14 s.
- `compare_p586_q{0,1,2}.jpg`: Taipei (prov 586), the same layout.
- `before/`, `after/`: every shot as a 1200 px jpg (`p<prov>_q<N>_<view>.jpg`).
- `perf.md`: CPU ms per frame before and after, at q0, q1 and q2.
- `keyframes/`: frames from the battle video at video time NN s.
- `battle_result/`: the `BATTLERESULT` line from the video run, the legacy `--env=0` reference, and `sim_hash.txt`.
- `ASSETS.md`: provenance (all procedural and original).
- **Video** (not in git, 34 MB, H.264 1600x900 at 30 fps, 51.6 s): `/workspace/ic_env_eastasia/out/video/env-east_asia-battle.mp4`. This is the demo battle with Japanese (Tokyo) dressing.

## Method
The demo battle (`--demo=battle --year=1300 --nation=SWE`, Battle of Malmö) is run with `--env-prov=<id>`. Cameras, units and battle time therefore match between before and after. The HUD still says "Malmö".

## Combat / sim untouched
- `BATTLERESULT` from the video run is **byte-identical** to the legacy `--env=0` run: md5 `f09210137aaecedfefe8512f38e7d609`.
- sim_hash matches main: SWE 1800 `417a53009d4b9c30b4c938a756b33f78`, USA 1914 `4679c5a24c8d055f95c9ea95ff868193`, JPN 1500 `e104d558aa9370b28c02ca58db54ae33`.
- test_runner (163/163), test_audio (28/28) and test_env all pass, re-run after merging framework 64c912d (`tests/`).
- No morale, pathfinding, combat, soldier-model or rules files are touched.

## Perf reading
- **q0:** +1..+66 % CPU.
- **q1 / q2:** most views cost +65..+110 %. `forest_edge` and `rocky` cost roughly 2.6–3.5x, because the camera looks straight into the dense sugi / broadleaf belt plus understorey. They stay at the same order of magnitude as the Scandinavian forest_edge numbers on this box.
- **Top-down view:** unchanged.
- **Caveat:** these are llvmpipe numbers on a heavily loaded box. Use them as relative comparisons, not absolute fps.
