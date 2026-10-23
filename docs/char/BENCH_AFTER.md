# Character refinement - after-bench (1600x900, llvmpipe GL Compatibility, --demo=battle --nation=USA --reinforce=1 --vispass=1 --bench=1 --fixed-fps 30)

fps_mean per view; two after/ctl runs (r1, r2) averaged. ctl = same build with --vx-char=0 (main's c19 soldiers), run back to back with the
after runs, so it is the fair baseline. 'before' = the original stage-1 baseline (out/char/before, older base, box under heavy load from
other jobs, no --fixed-fps) and is only shown for reference. prims = visible primitives, dc = draw calls.

| q | view | before fps | ctl fps | after fps | after vs ctl | ctl prims | after prims | dc ctl/after |
|---|---|---|---|---|---|---|---|---|
| q0 | close | 3.08 | 8.29 | 7.01 | -16% | 123866 | 141546 | 30/30 |
| q0 | mid | 3.41 | 8.27 | 8.65 | +5% | 123390 | 141070 | 27/27 |
| q0 | wide | 3.12 | 6.95 | 5.07 | -27% | 135960 | 153640 | 60/60 |
| q0 | close_def | 3.78 | 7.69 | 6.75 | -12% | 123624 | 141304 | 31/31 |
| q1 | close | 3.38 | 2.58 | 2.59 | +1% | 123866 | 141546 | 61/61 |
| q1 | mid | 3.51 | 3.52 | 2.59 | -26% | 123390 | 141070 | 58/58 |
| q1 | wide | 2.94 | 3.06 | 2.12 | -31% | 135960 | 153640 | 103/103 |
| q1 | close_def | 3.35 | 3.50 | 2.52 | -28% | 123624 | 141304 | 69/69 |
| q2 | close | 1.36 | 3.67 | 2.21 | -40% | 123866 | 141546 | 65/65 |
| q2 | mid | 1.19 | 3.48 | 1.94 | -44% | 123390 | 141070 | 58/58 |
| q2 | wide | 1.01 | 3.11 | 2.08 | -33% | 135960 | 153640 | 117/117 |
| q2 | close_def | 0.95 | 2.45 | 2.08 | -15% | 123624 | 141304 | 75/75 |

Notes: ctl_r2 q1 close (1.34) is a load spike outlier (r1 3.81); it pulls the q1 close ctl mean down.
Primitives +14% (LOD0 ~3k tris vs ~2.6k; LOD1 ~1.1k, over the 500-800 target). Draw calls unchanged (in-place MultiMesh swap).
The q1/q2 gap is larger than q0, most likely because shadow + MSAA passes re-run the heavier VAT vertex shader (vatn normal fetch, palette, crossfade).

## Stage 7 (perf recovery: lean LOD1 581/629/573/512 tris, LOD1 shader variant, per-tier character LOD 20/30/45 m)
Same bench (1600x900, llvmpipe, --fixed-fps 30, --demo=battle --nation=USA --reinforce=1 --vispass=1 --bench=1). after and ctl
(same build, --vx-char=0 = main's c19 soldiers) interleaved per q, 3 runs each; runs done: 18/18. Raw: out/char/stage7/bench/r*/{after,ctl}/q*/perf.csv.
'mean' = fps_mean averaged over runs; 'med-fps' = 1000/median frame ms averaged over runs (robust to the box's one-off stalls,
e.g. r1 after q1 wide had a single multi-second frame: mean 0.72 fps, median 333 ms).
Complete (18/18). Read the med-fps columns: the fps_mean outliers (r1 after q1 wide 0.72, r2 ctl q1 mid 0.59, r1 ctl q2 wide 0.97, r3 after q0 close_def 4.13) are single multi-second stalls from other jobs on the shared box.

Result (median-based, vs ctl): q0 +2..+20% (all views at/above ctl); q1 -8..+5% (within 10%); q2 wide -2%, mid -11%, close -22%, close_def -14% (beyond 10%).
Remaining cost: q2 keeps the character LOD0 out to 45 m (its tier character) and adds 4x MSAA, so the close/close_def views draw
many 2.5-3.2k-tri LOD0 soldiers where ctl draws ~700-tri ones; LOD0 per-instance raster cost on llvmpipe is what is left.
Options (not taken, to keep each tier's character): q2 char_lod 30 m (= q1; profile at q1 says it lands within ~10%), or a
lighter mid LOD (LOD2-style: 1.2-1.5k tris for 15-45 m) which fits in the current near/far split without any battle_view change.
Wide views are at ctl at all tiers, so a battle_view LOD2 request is not needed.

| q | view | ctl fps (r1/r2/r3) | ctl mean | after fps (r1/r2/r3) | after mean | after vs ctl | med-fps ctl / after | med vs ctl |
|---|---|---|---|---|---|---|---|---|
| q0 | close | 8.09/8.43/7.97 | 8.16 | 9.21/8.53/8.89 | 8.88 | +9% | 8.24 / 9.04 | +10% |
| q0 | mid | 8.15/8.07/8.39 | 8.20 | 10.43/9.27/10.02 | 9.91 | +21% | 8.25 / 9.93 | +20% |
| q0 | wide | 6.99/6.96/6.73 | 6.89 | 7.61/6.70/6.67 | 6.99 | +1% | 6.92 / 7.08 | +2% |
| q0 | close_def | 7.56/7.81/7.19 | 7.52 | 8.45/8.02/4.13 | 6.87 | -9% | 8.13 / 8.73 | +7% |
| q1 | close | 3.75/3.90/3.64 | 3.76 | 3.72/3.79/3.59 | 3.70 | -2% | 3.79 / 3.75 | -1% |
| q1 | mid | 3.82/0.59/3.79 | 2.73 | 3.45/3.63/3.42 | 3.50 | +28% | 3.84 / 3.52 | -8% |
| q1 | wide | 3.15/2.89/2.97 | 3.00 | 0.72/3.23/3.15 | 2.37 | -21% | 3.02 / 3.14 | +4% |
| q1 | close_def | 3.63/3.28/3.38 | 3.43 | 3.45/3.70/3.60 | 3.58 | +4% | 3.57 / 3.74 | +5% |
| q2 | close | 3.90/3.51/3.60 | 3.67 | 3.08/2.78/2.71 | 2.86 | -22% | 3.72 / 2.90 | -22% |
| q2 | mid | 3.57/3.36/3.34 | 3.42 | 3.11/3.07/2.95 | 3.04 | -11% | 3.45 / 3.08 | -11% |
| q2 | wide | 0.97/3.18/2.95 | 2.37 | 2.98/3.07/3.02 | 3.02 | +28% | 3.12 / 3.04 | -2% |
| q2 | close_def | 3.10/3.27/3.31 | 3.23 | 2.89/2.76/2.73 | 2.79 | -13% | 3.35 / 2.88 | -14% |

## Stage 10 (character-refinement-2 on v0.3.2, HEAD 6424bfd tree): q2, same-build control
Rob's battle_shots harness (game/tests/battle_shots.gd), llvmpipe 1600x900, --quality=2 --frames=60 --perflog=1, frozen sim (1800 SWE t=14, USA t=6 --reinforce=1);
fps = 1000 / median frame ms, 3 interleaved runs, median of runs. ctl = same build with --vx-char=0 (pre-refinement c19 models). Raw: /workspace/iron-crowns-visual/out/char/stage10/bench_q2.

| battle | view | ctl --vx-char=0 fps (r1/r2/r3) | ctl median | after fps (r1/r2/r3) | after median | after vs ctl |
|---|---|---|---|---|---|---|
| 1800SWE q2 | close | 3.51/3.38/3.57 | 3.51 | 2.75/2.96/3.09 | 2.96 | -16% |
| 1800SWE q2 | close_def | 3.77/3.39/3.88 | 3.77 | 3.11/3.30/3.48 | 3.30 | -13% |
| 1800SWE q2 | mid | 3.16/3.12/3.37 | 3.16 | 2.92/3.12/3.36 | 3.12 | -1% |
| 1800SWE q2 | top | 3.57/3.55/3.57 | 3.57 | 2.92/3.40/3.70 | 3.40 | -5% |
| USA q2 | close | 3.50/3.75/3.75 | 3.75 | 3.16/3.00/3.23 | 3.16 | -16% |
| USA q2 | close_def | 3.30/3.44/3.43 | 3.43 | 2.76/2.80/2.87 | 2.80 | -18% |
| USA q2 | mid | 3.08/3.23/3.17 | 3.17 | 2.85/2.84/2.89 | 2.85 | -10% |
| USA q2 | top | 2.98/3.18/3.23 | 3.18 | 3.11/3.17/3.14 | 3.14 | -1% |

Team-tint cost A/B (1800SWE q2, 3 runs, med-fps; out/char/stage10/bench_b): mid after 3.23 / --vx-teamtint=0 3.21 / clean v0.3.2 3.46; top 3.69 / 3.67 / 3.75 -> tint ~free after 10b.
vs stage 7 q2 (other harness): close -22 -> -16 %, close_def -14 -> -13..-18 %, mid -11 -> -1..-10 %, wide/top -2 -> -1..-5 %. Remaining cost: LOD0 within 20 m + 4x MSAA at q2.
