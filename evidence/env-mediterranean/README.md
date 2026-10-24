# Evidence: env/mediterranean (summer-dry hill country)

This branch is cut from `main` at 41bdd75. It uses the Scandinavian build as its design language and quality bar. It keeps the same tiled MultiMesh scatter, LOD and quality tiers, engagement-corridor rules and ground shader. The species, rocks, ground and light are new and Mediterranean. The Nordic models reused are reeds (shores) and juniper.

## Look (driven by province data, see `game/scripts/battle/biomes/mediterranean.gd`)
- **Which provinces:** the framework's `mediterranean` zone: the Med basin at lat 30..45 / lon -10..45 (after the savanna, arid, east_asia and tropical rules), California, central Chile and southern Australia. In the census that is 31 provinces.
- **Sub-regions:**
  - **coast** (Iberian, Provençal, Italian, Greek, Albanian, Levantine, Cypriot and Maltese lowland, and the Aegean side of Anatolia): olive groves, umbrella pine, Italian cypress lines, holm-oak woods, Aleppo pine; maquis and garrigue; karst limestone on red terra rossa.
  - **interior** (sub-Mediterranean: Atlantic N Spain, the Pyrenees and Andorra, the Balkan interior from ~41.4 N): deciduous downy / Turkey oak woods with black pine, a little holm oak, juniper scrub; browner soil.
  - **anatolia** (the Anatolian, Armenian and Caucasus plateau: lat >= 37, lon >= 30, elev >= 0.9): open dry upland with scrub oak, juniper and pine patches, cushion steppe, paler soil.
  - **california**: coast live oak, valley oak and grey pine over golden grass, chaparral and sage. The high Great Basin side (elev >= 1.4) gets a sparse pinyon-juniper scatter instead.
  - **chile**: matorral of peumo / quillay evergreens with roble, and dense sclerophyll scrub.
  - **australia**: open eucalypt woodland over golden grass, grey mallee / saltbush scrub, red soil.
- **Season:** wet or dry from the battle month and hemisphere (north: dry Jun-Oct; south: dry Dec-Apr). Override with `--env-season=wet|dry` (summer / autumn map to dry).
  - **Wet:** a green winter-spring flush under a crisp, deep-blue sky and a lower sun.
  - **Dry:** sun-bleached golden grass, dusty leaves, warm haze and a high, hard sun.
- **Rock:** pale fissured limestone on the basin and plateau; tinted warmer (granite / sandstone) in California, Chile and Australia.
- **Previews** (`out/pv1`, `out/pv2`, not in git): Rome 482, Athens 536, California 43, Victoria 157, Ankara 339.

## Files
- `compare_p482_q{0,1,2}.jpg`: Rome, Italy, coast sub-region (wet in the demo's February). BEFORE (legacy `--env=0`) and AFTER side by side, from the seven identical scripted cameras at battle t = 14 s.
- `compare_p43_q{0,1,2}.jpg`: California (wet).
- `compare_p157_q{0,1,2}.jpg`: Victoria, Australia (dry: February is southern summer).
- `before/`, `after/`: every shot as a 1200 px jpg.
- `perf.md`: CPU ms per frame before and after, at q0, q1 and q2.
- `battle_result/`: `BATTLERESULT` from headless env1 and env0 runs of the demo battle on the same code.
- `tests/`: test_runner, test_audio, test_env and sim_hash results.
- `ASSETS.md`: provenance (all procedural and original).
- **No season sheet and no battle video**, per Kirk's 9:24 PM directive (implementation and testing first; no image or video deliverables unless asked).

## Method
The demo battle (`--demo=battle --year=1300 --nation=SWE`) is run with `--env-prov=<id>`. Cameras, units and battle time therefore match between before and after. The HUD still names the demo's Danish battle site.

## Combat / sim untouched
- `BATTLERESULT` from a headless env1 run (`--env-prov=482 --env=1`) is **byte-identical** to a legacy `--env=0` run on the same code: md5 `1521b887c9d353430d51b7e6ab22815c` (`battle_result/`). This is the same value as env/arid's and env/savanna's runs of the demo battle. The environment is built in headless runs too, since `battle_view.gd` has no headless guard.
- sim_hash is identical to main 41bdd75: SWE 1800 `0b3153c6f9fb7c454686cb49f19cb866`, USA 1914 `a9beef573f5922b7eb83ba8f2beb5e63`, JPN 1500 `563be302cdf34e56b4a33a873230ebf1`.
- test_runner (216/216), test_audio (28/28) and test_env (0 failures; min fighting-regiment clearance 77.5 m) all pass (`tests/`). The first test_runner run was killed by my own abort, exit 143. It was rerun and passed; see `tests/summary.txt`.
- No morale, pathfinding, combat, soldier-model or rules files are touched. The only code change is the new `biomes/mediterranean.gd` (plus the procedural models and their Blender script). No shader changes.

## Perf reading (`perf.md`)
- **Overview / formation / horizon:** +9..+45 % CPU.
- **Forest-edge / rocky / water views:** +11..+98 % CPU. These views show the most scatter, and Victoria's eucalypt woodland at q2 is the heaviest case: forest_edge 852 -> 1684 ms.
- **Top-down view:** cheaper (-3..-17 %).
- **Comparison:** the heavy-view cost is in line with savanna (q2 forest_edge 1503-1684 ms, versus 1526-1916 ms for savanna and about 2300-3200 ms for temperate).
- **Outlier:** one before-sample (California q1 rocky, 2525 ms) is contention noise.
- **Caveat:** these are llvmpipe numbers on a shared box (load avg ~14-20). Use them as relative comparisons, not absolute fps.
