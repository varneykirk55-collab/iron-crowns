# Evidence: env/arid (deserts and semi-arid margins)

This branch is built on `env/biome-framework` and now contains `main` at e7964f8 (v0.5.0 plus the merged framework, tropical and east_asia regions). It uses the Scandinavian build as its design language and quality bar. It keeps the same tiled MultiMesh scatter, LOD and quality tiers, engagement-corridor rules and ground shader. The species, rocks, ground and light are new and arid. The only Nordic models reused are juniper (re-tinted as pinyon-type juniper), dry grass and reeds. There are no pines, no heather and no grass carpet.

## Look (driven by province data, see `game/scripts/battle/biomes/arid.gd`)
- **Which provinces:** every province the game data tags `desert`, plus Arabia and the Mexican plateau.
- **The `core` gradient:** a 0..1 value from lat / lon separates true deserts (Sahara, Arabia, Sonora, Gobi, Atacama, Australian interior) from the semi-arid margins the data also marks desert (Great Plains, N China / Gangetic plains, Sahel, Iberian meseta, Ethiopian highlands). As `core` falls there is more bunchgrass, more and greener trees, and softer, less dusty light.
- **Ground:** a dry earth / gravel-pavement mosaic. Pale drift sand appears only on crests and open flats.
- **Soil palette by region:**
  - red earth: Sonora, Colorado plateau, Hejaz, Australia;
  - buff sandstone / limestone: Sahara, Arabia;
  - grey-brown gravel: Gobi, Iran, Central Asia.
- **Species by region:**
  - **Americas:** creosote, prickly pear and mesquite. Saguaro grows only in the Sonoran desert, and pinyon-type juniper on the Colorado plateau.
  - **N Africa / Arabia / Mesopotamia:** umbrella acacia, date palm (coasts, rivers, oases), tamarisk and saltbush.
  - **Iran / Central Asia / Gobi:** saxaul, tamarisk, poplar oases, and juniper on the highlands.
  - **India / Pakistan:** khejri-type acacia and tamarisk.
  - **Southern Africa:** camelthorn acacia.
  - **Australia:** spinifex hummocks and mulga acacia on red earth.
- **Rock:** wind-rounded sandstone boulders and layered butte / mesa outcrops. The terrain `lichen` uniform becomes desert varnish and crust.
- **Light:** a harsh high sun under a pale, dusty sky, with warm haze on the distant ranges. Snow appears only on very high ranges (snowline 4600 m, or 3800 m on the high plateaus).
- **Water:** follows province data. Coastal provinces get a sea / estuary. Inland provinces get a rare oasis pool.
- **Previews** (`out/try4`, `out/try5`, not in git): Arizona 46, Sahara 302, Riyadh 242, Xinjiang 93, Northern Territory 154 and Kansas 55. Kansas is tagged `desert` by the game data, so it renders as the semi-arid prairie variant.

## Files
- `compare_p46_q{0,1,2}.jpg`: Arizona / Sonoran (prov 46). BEFORE (legacy `--env=0`) and AFTER side by side, from the seven identical scripted cameras at battle t = 14 s.
- `compare_p242_q{0,1,2}.jpg`: Riyadh / Arabia (prov 242), the same layout.
- `before/`, `after/`: every shot as a 1200 px jpg (`p<prov>_q<N>_<view>.jpg`).
- `perf.md`: CPU ms per frame before and after, at q0, q1 and q2.
- `keyframes/`: frames from the battle video at video time NN s.
- `battle_result/`: the `BATTLERESULT` line from the video run and from a legacy `--env=0` run on the same code, plus `sim_hash.txt`.
- `tests/`: test_runner, test_audio and test_env results after merging main.
- `ASSETS.md`: provenance (all procedural and original).
- **Video** (not in git): `/workspace/ic_env_arid/out/video/env-arid-battle.mp4`, 33.5 MB, H.264 1600x900 at 30 fps, 54.4 s. It shows the demo battle with Arizona (prov 46) dressing.

## Method
The demo battle (`--demo=battle --year=1300 --nation=SWE`) is run with `--env-prov=<id>`. Cameras, units and battle time therefore match between before and after. The HUD still names the demo's Danish battle site.

## Combat / sim untouched
- `BATTLERESULT` from the video run is **byte-identical** to a legacy `--env=0` run on the same code (v0.5.0 combat): md5 `1521b887c9d353430d51b7e6ab22815c`. The old `f0921013…` reference predates v0.5.0's combat changes.
- sim_hash is identical to `main` 644174c / e7964f8: SWE 1800 `0b3153c6f9fb7c454686cb49f19cb866`, USA 1914 `a9beef573f5922b7eb83ba8f2beb5e63`, JPN 1500 `563be302cdf34e56b4a33a873230ebf1`.
- test_runner (205/205), test_audio (28/28) and test_env (0 failures) all pass after merging main (`tests/`).
- No morale, pathfinding, combat, soldier-model or rules files are touched. The only code changes are `biomes/arid.gd`, plus two defaulted uniforms in `battle_terrain.gdshader` whose defaults equal the old hard-coded lichen, so every other biome renders as before.

## Perf reading
- **q0:** +4..+40 % CPU (mostly +12..+40 %).
- **q1 / q2:** +0..+36 %. The top-down view is cheaper (-5..-13 %).
- **Why it's cheap:** arid scatter is sparse by design, so it is the cheapest region so far, well under tropical and east_asia.
- **Caveat:** these are llvmpipe numbers on a heavily loaded box. Use them as relative comparisons, not absolute fps.
