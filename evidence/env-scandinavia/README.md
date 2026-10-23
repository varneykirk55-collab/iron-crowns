# Evidence: env/scandinavia-medieval (battlefield environment prototype)

Battle used: `--demo=battle --year=1300 --nation=SWE`, the Battle of Malmö (province 348, Sweden, terrain forest, medieval).
Renderer: Godot 4.7.2, GL Compatibility, on llvmpipe (software rendering on a shared, heavily loaded box), at 1600x900.

## Files
- `compare_q0.jpg`, `compare_q1.jpg`, `compare_q2.jpg`: BEFORE (legacy, `--env=0`) and AFTER side by side, from five identical scripted cameras (overview, formation, forest_edge, rocky, water) at the same battle time (t = 14 s).
- `before/` and `after/`: the full-resolution shots per quality (including the horizon and top views) and `qN_report.json`.
- `keyframes/`: frames from the full battle video.
- `perf.md`: frame cost before and after at q0, q1 and q2.
- `ASSETS.md`: asset provenance and licence. Everything is procedural and original.
- Video (not in git, it is too large): `/workspace/ic_env/out/video/env-scandinavia-battle.mp4`.

## Reproduce
```
out/shots.sh <outdir> <0|1|2> q<N> [--env=0] [--frames=8]          # wraps tests/env_shots.tscn under xvfb
tools/godot --headless --path game res://tests/test_env.tscn         # biome / determinism / obstacle clearance
tools/godot --headless --path game res://tests/sim_hash.tscn         # must match main
```
Debug flags: `--env=0` gives the legacy look, `--env=1` forces the biome, and `--env-prov=<id>` previews another province's dressing (for example 328 = Oslo).

## How the biome is chosen from data
`BattleEnvironment.biome_for(b, era)` reads `GameData.provinces[b.prov]`. When the region is Norway, Sweden, Denmark or Finland, the era is medieval, and the terrain is forest, tundra, plains, hills or mountains, it returns the `scandinavia_boreal` profile. In every other case the legacy ground is untouched. `profile()` derives every parameter from the province fields:

| Parameter | Driven by |
|---|---|
| relief | terrain and `elev` |
| forest density, rockiness, dryness | terrain, plus `elev` and region (Norway and Finland are rockier) |
| birch share | latitude, plus Denmark |
| pine share | tundra and `elev` |
| distant mountains | Scandes rule (Norway, or lat > 59 and lon < 16.5, or lat > 64, or high elev) gives 560 m plus; Sweden south gives 180 m ridges; Finland 120 m; Denmark 70 m |
| snowline and treeline | latitude |
| lake | coastal, or seed |

Malmö therefore gets low forested ridges and no snow, which is honest to the data. Oslo gets 918 m snow-capped ranges.

## Obstacle rules
See the header of `battle_environment.gd` and the Claude note in `COLLAB.md`. In short:
- Solid props stay outside an engagement corridor derived from the deployed regiments, plus their own radius plus 10 m.
- Only knee-high cover is allowed inside the corridor.
- `test_env` checks this over 24 real battles: minimum clearance 73 m, 0 overlaps.

## Tests
- sim_hash is identical to main: SWE 1800 `417a53009d4b9c30b4c938a756b33f78`, USA 1914 `4679c5a24c8d055f95c9ea95ff868193`, JPN 1500 `e104d558aa9370b28c02ca58db54ae33`.
- test_runner 163/163, test_audio 28/28, and test_env 7/7.
