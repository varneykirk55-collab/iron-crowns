# Hash check: proto/anim-combat-v1 vs clean main a3f4f35 (2026-10-23, Rob)

**Trees**
- Clean `a3f4f35` is the worktree `/workspace/ic_anim_base`.
- The branch was checked at commit `74b9053` (horse gaits).
- The branch was run twice, once with the flag off (default) and once with `--anim-v1`.

**How it was run**
- `out/run_suite.sh` runs the test_runner, sim_hash and audio tests.
- `out/hash_demo.sh` runs the headless rendered BattleView demo battles, with `--fixed-fps 30`.

## Results

| check | a3f4f35 clean | branch, flag off | branch, `--anim-v1` |
|---|---|---|---|
| test_runner | 163/163 | 163/163 | 163/163 |
| audio | 28/28 | 28/28 | – |
| SIMHASH SWE 1800 | 417a53009d4b9c30b4c938a756b33f78 | same | same |
| SIMHASH USA 1914 | 4679c5a24c8d055f95c9ea95ff868193 | same | same |
| SIMHASH JPN 1500 | e104d558aa9370b28c02ca58db54ae33 | same | same |
| BattleView SWE 1300 (medieval) BATTLERESULT md5 | f09210137aae | same | same |
| BattleView SWE 1650 (early modern, cuirassiers) | e8cdfb7ffed4 | same | same |
| BattleView SWE 1800 (c19, hussars) | 572031327ebe | same | same |
| BattleView USA 1914 (c20) | a030d0a0572c | same | same |
| anim_demo cav (knights vs levy, gap 80) | – | 6408573137f4e17a9de42d0fb8325fb1 | same |
| anim_demo spear / retreat | – | ae9064e0… | same |

**BATTLERESULT**
- Each BATTLERESULT line contains battle time, end men, per-unit kills and projectile counts. The whole line is byte-identical in every run.
- SWE 1300: 33.4 s, [1232, 4176].
- SWE 1650: 37.8 s, [4437, 3117].
- SWE 1800: 39.5 s, [5039, 5166].
- USA 1914: 17.8 s, [8547, 607].

**Test log lines that differ only by wall clock**
These lines differ in every run, including two runs of the same tree:
- the save `saved_unix` timestamp;
- Godot Button object ids;
- the frame-delta-dependent gamepad-cursor distance;
- the F3 FPS readout.

**Script errors**
- Each headless demo log has 6 `SCRIPT ERROR: save_png on null`.
- They come from screenshots that cannot be taken headless.
- The same 6 errors appear on clean a3f4f35.

## Why the baseline changed: `git log 8de2921..a3f4f35`

All four commits are authored by `Claude <noreply@anthropic.com>` on 2026-10-23 (EDT):

| commit | time | subject |
|---|---|---|
| fcea68b | 10:04 | Offensive warfare: invade orders, undeclared conflicts, recapture, landless nations, defeat screen |
| 0090b1b | 10:04 | Track generated battle_shots.gd.uid |
| 805dd2f | 10:22 | v0.4.0 docs, test results, invasion demo videos and screenshots |
| a3f4f35 | 10:22 | Docs: Windows zip is shared outside the repo |

**What fcea68b changed**
- It changes gameplay: `sim.gd` +318, `main.gd` +83, `hud.gd` +106 and `test_runner.gd` +368.
- It adds invade/resume fields to the serialized state and changes AI invasion behaviour.
- The SIMHASH values therefore changed legitimately:

| | 8de2921 | a3f4f35 |
|---|---|---|
| SWE 1800 | f7255ebb… | 417a5300… |
| USA 1914 | 45cf5510… | 4679c5a2… |
| JPN 1500 | 9bb2394d… | e104d558… |

- It also added 23 tests, so the suite went from 140 to 163.

The branch is based on a3f4f35, so a3f4f35 is the correct baseline. None of the branch's commits touch sim, AI or tests.
