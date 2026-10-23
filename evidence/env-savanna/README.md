# Evidence: env/savanna (tropical grassland and open woodland)

This branch is built on `env/biome-framework` and contains `main` at 41bdd75. It uses the Scandinavian build as its design language and quality bar. It keeps the same tiled MultiMesh scatter, LOD and quality tiers, engagement-corridor rules and ground shader. The species, rocks, ground and light are new and savanna. The only Nordic model reused is reeds (shores).

## Look (driven by province data, see `game/scripts/battle/biomes/savanna.gd`)
- **Which provinces:** Africa lon -26..55 / lat -36..24, India lon 60..88 / lat 5..30, and the Americas lat -30..-8, wherever the framework does not already pick rainforest or desert.
- **Sub-regions:**
  - **bushveld** (Africa south of ~20 S): umbrella thorn, candelabra euphorbia, thorn scrub, the odd baobab, granite kopjes.
  - **miombo** (8-20 S: Zambia, Angola, Malawi, N Mozambique): denser open Brachystegia woodland, many termite mounds.
  - **sudan / sahel** (north of the equatorial belt): umbrella thorn and baobab over tall grass. Drier and paler towards the Sahel.
  - **deccan** (India): dry-deciduous woodland, thorn scrub, Deccan granite tors, darker black-cotton soil.
  - **campos** (South America): rolling grass with scattered gnarled cerrado trees. No baobab or euphorbia.
  - **highland** (Ethiopia, Lesotho, Malagasy highlands; elev >= 1.4 or mountains): greener montane grass, few trees.
  - **madagascar**: miombo-type woodland with more euphorbia.
- **Ground:** red-brown laterite soil showing through tall bunchgrass.
- **Season:** wet or dry from the battle month and hemisphere (north: dry Nov-Apr; south: dry May-Oct). Override with `--env-season=wet|dry`.
  - **Dry:** golden straw, grey-olive leaves, dust haze, pale sky.
  - **Wet:** olive-green flush under a clear blue sky.
- **Rock:** rounded exfoliating granite kopjes and boulders.
- **Previews** (`out/pv2`, `out/pv3`, not in git): Rio Grande do Sul 133 (campos), Maharashtra 185 (deccan), Abuja 363 (sudan), Lusaka 395 (miombo), Maseru 589 (highland), Johannesburg 271 and 276.

## Files
- `compare_p271_q{0,1,2}.jpg`: Johannesburg bushveld (prov 271, wet in the demo's March). BEFORE (legacy `--env=0`) and AFTER side by side, from the seven identical scripted cameras at battle t = 14 s.
- `compare_p276_q{0,1,2}.jpg`: Sudan savanna (prov 276, dry in March).
- `compare_p395_q{0,1,2}.jpg`: Lusaka miombo (prov 395, wet).
- `seasons_q1.jpg` and `seasons/`: provs 271 and 276, each forced wet and dry (q1).
- `before/`, `after/`: every shot as a 1200 px jpg.
- `perf.md`: CPU ms per frame before and after, at q0, q1 and q2.
- `keyframes/`: frames from the battle video.
- `battle_result/`: the `BATTLERESULT` line from the video run and from a legacy `--env=0` run on the same code, plus `sim_hash.txt`.
- `tests/`: test_runner, test_audio and test_env results after merging main 41bdd75.
- `ASSETS.md`: provenance (all procedural and original).
- VIDEOLINE

## Method
The demo battle (`--demo=battle --year=1300 --nation=SWE`) is run with `--env-prov=<id>`. Cameras, units and battle time therefore match between before and after. The HUD still names the demo's Danish battle site.

## Combat / sim untouched
- RESULTLINE
- HASHLINE
- TESTLINE
- No morale, pathfinding, combat, soldier-model or rules files are touched. The only code change is the new `biomes/savanna.gd` (plus the procedural models and their Blender script). No shader changes.

## Perf reading
- **Forest-edge / rocky / water views:** +31..+130 % CPU. These views show the most scatter, and Lusaka's miombo woodland is the densest case.
- **Overview / formation / horizon:** +11..+57 %. The top-down view is cheaper (-7..-14 %).
- **Comparison:** savanna is cheaper than temperate on the heavy views (q2 forest_edge 1526-1916 ms versus about 2300-3200 ms for temperate).
- **Caveat:** these are llvmpipe numbers on a shared box. Use them as relative comparisons, not absolute fps.
