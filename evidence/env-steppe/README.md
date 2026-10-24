# Region: steppe (env/steppe)

The Eurasian and American grasslands, built in the Scandinavian design language: the same framework, corridor rules and quality/LOD tiers. Combat and sim are untouched. This round has no screenshots or videos (Kirk, 9:24 PM / 10:05 PM). The evidence is code, tests, the combat check and perf numbers.

## Sub-regions (`game/scripts/battle/biomes/steppe.gd`, from province lat/lon/elev)
| sub-region | where | look |
|---|---|---|
| kazakh | Kazakh steppe north of the semi-desert belt | feather-grass sea, birch/cottonwood colki (groves) in the north (tree_p 0.06 at lat >= 50), kurgans |
| semi | Caspian / Aral lowlands, lon < 50 | wormwood semi-desert, sparse cottonwood on water |
| mongol | Mongolian plateau (lon >= 88, lat >= 40) | short grass, granite tors and outcrops, larch/birch forest-steppe in the north |
| highland / moist_hi | elev >= 2.2 (Tibetan rim, Pamir foot) | thin alpine sward, tors, snowline from mountain height |
| prairie | the Great Plains (Americas, plains/hills terrain) | tallgrass, cottonwood on creeks |
| pampa | southern South America east of -65 | green pampa, lone ombu trees |
| monte | southern South America west of -65 | dry scrub steppe, pea-shrub, no spring flush |

The season comes from the battle month: spring (3-5), summer (6-9) or winter, shifted 6 months in the southern hemisphere. In winter the deciduous trees go bare and the larch turns gold in late summer. Continental winter adds snow (snow_h = mountain x 0.45, treeline = snow_h + 200). The open steppe stays open: about 38 near trees per field, versus 500-850 in the grove and forest-steppe sub-regions. Lone-tree count is per sub-region (`lone_n` 4-14; the only framework change is a `lone_n` key with the old default of 90).

Models: 11 procedural models from `pipeline/blender/env_steppe.py`. No external assets; see ASSETS.md.

## Results
- test_runner / test_audio / test_env: all pass (`tests/summary.txt`, tails). test_env reports 0 failures, every referenced model exists, the plan is deterministic, and the minimum fighting-footprint clearance is 74.8 m.
- Sim hashes equal main 41bdd75 (`tests/sim_hash.txt`): SWE 1800 0b3153c6..., USA 1914 a9beef57..., JPN 1500 563be302....
- Battle result is identical with env on and off (`battle_result/md5.txt`, `--demo=battle --year=1300 --nation=SWE`): prov 168 Atyrau (semi) and prov 229 Erdenet (mongol forest-steppe, heaviest plan, 704 trees) all give 1521b887c9d353430d51b7e6ab22815c.
- Plan smoke over all 37 steppe provinces x 3 seasons: `plan_smoke_all_provinces.txt`, no missing models.
- Perf: `perf.md`.
