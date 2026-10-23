# Map visual refinement progress (branch graphics-map, worktree /workspace/ironcrowns-map)
Base: v0.2.1 (5f3ea72). Do not touch /workspace/grand_strategy working tree, main, lead-dev, graphics, or BJORN's workspace.
Symlinks (untracked): tools/godot, tools/venv, data_src -> /workspace/grand_strategy/...
## Log
- 23:35 worktree created; harness game/tests/map_shots.{gd,tscn} (views, perf, picks, interact).
- box rebooted once mid-test (processes killed) -> run long jobs with setsid nohup.
- 00:05 EDT: snow now prominence-based (Tibet plateau no longer white, Alps/Himalaya peaks snowed); political tint stronger at region zoom (min 0.46, tint 0.72+0.5*lum). Commit dd26ce8.
- Interact harness metric -> changed-pixel fraction (centre patch sat on city marker). before: select 17.5%, conquest 40.5%; after: 13.8% / 28.4%; both pick 328, zoom 4/230 ok.
- Picks: 12/12 views identical to baseline (out/picks_compare.log).
- Tests after: 131/131; SIMHASH identical for SWE1800/USA1914/JPN1500 (out/tests_after.log, out/simhash_after.log).
- Perf table: out/perf_table.md (Low -22..-57%, Medium -7..-50%, High -53..+23%; worst close_alps High +23%).
- Flyover: game/tests/map_flyover.{gd,tscn} + --write-movie -> out/map_flyover.mp4.
- 00:40 EDT: readability pass per lead review (country tint 0.80, close min 0.30 by cam 7..55, national 1.7px vs province 0.5px lighter; close-zoom world-min widths reduced).
