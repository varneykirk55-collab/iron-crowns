# c19v2_line: crowd bench (stage 4d)

**Setup.** Run on Fri 2026-10-23, 13:2x to 14:31 EDT, on branch proto/c19-line-v2 at 990a1f7. Both arms use the same
build and the same command; only `--vx-proto` changes:

```
godot --path game --resolution 1600x900 --fixed-fps 30 -- --demo=battle --nation=FRA --year=1800 --reinforce=1 \
      --vispass=1 --bench=1 --bench-quit --quality=Q --vx-proto=P
```

* ctl = `--vx-proto=0`: the shipping FRA 1800 c19sr_* soldiers.
* proto = `--vx-proto=1`: c19v2_line with the 10,715 / 1,999 / 691 tri LOD sets and the 2048 normal / AO / id atlas.

Each arm ran 3 times at q0, q1 and q2, interleaved r1 to r3 (ctl then proto per quality). The bench's own PERF block
records the same four camera views every run, at 60 frames per view. **fps = 1000 / median frame ms** per run,
and the table shows the **median of the 3 runs**, with every run listed.

Renderer: Godot 4.7.2 GL Compatibility on **llvmpipe** (software raster, 8 cores, xvfb). There is no GPU, so
the absolute numbers say little about real hardware. Fragment cost is CPU cost here.

| q | view | FRA 1800 vx-proto=0 (median fps) | c19v2 vx-proto=1 (median fps) | Δ | ctl runs r1/r2/r3 | proto runs r1/r2/r3 | prims ctl → proto | draws |
|---|---|---|---|---|---|---|---|---|
| q0 | close | 6.90 | 5.45 | -21% | 5.31 / 8.74 / 6.90 | 3.91 / 5.91 / 5.45 | 167,248 → 184,312 | 30 / 30 |
| q0 | mid | 7.67 | 7.67 | +0% | 5.59 / 10.58 / 7.67 | 6.91 / 9.15 / 7.67 | 166,986 → 184,050 | 27 / 27 |
| q0 | wide | 6.19 | 5.24 | -15% | 4.28 / 6.56 / 6.19 | 4.84 / 5.64 / 5.24 | 175,624 → 192,688 | 49 / 49 |
| q0 | close_def | 8.00 | 5.32 | -34% | 5.12 / 8.00 / 8.20 | 4.95 / 5.32 / 5.48 | 166,968 → 184,032 | 30 / 30 |
| q1 | close | 3.53 | 2.09 | -41% | 3.54 / 3.53 / 3.45 | 2.09 / 2.15 / 0.95 | 167,248 → 184,312 | 59 / 59 |
| q1 | mid | 3.16 | 1.96 | -38% | 3.22 / 3.16 / 2.83 | 2.00 / 1.96 / 0.82 | 166,986 → 184,050 | 64 / 64 |
| q1 | wide | 1.96 | 2.62 | +33% | 1.80 / 3.52 / 1.96 | 2.62 / 2.81 / 0.90 | 175,624 → 192,688 | 85 / 85 |
| q1 | close_def | 3.32 | 1.83 | -45% | 3.50 / 3.32 / 1.95 | 1.83 / 2.04 / 0.81 | 166,968 → 184,032 | 63 / 63 |
| q2 | close | 1.64 | 1.65 | +1% | 2.91 / 1.64 / 1.08 | 1.70 / 1.65 / 0.92 | 167,248 → 184,312 | 65 / 65 |
| q2 | mid | 1.40 | 1.38 | -1% | 2.55 / 1.40 / 0.99 | 1.38 / 1.40 / 0.81 | 166,986 → 184,050 | 54 / 54 |
| q2 | wide | 2.10 | 2.92 | +39% | 2.81 / 2.10 / 1.00 | 2.92 / 2.98 / 1.13 | 175,624 → 192,688 | 95 / 95 |
| q2 | close_def | 1.78 | 1.42 | -21% | 2.26 / 1.78 / 0.90 | 1.42 / 1.44 / 0.79 | 166,968 → 184,032 | 61 / 61 |

**Contamination.** The box is shared with other agents.
* From about 14:04 EDT, three or four other Godot jobs ran at the same time as this one (env / anim
  recordings, unrelated to this branch). That covers r3 q1 proto, r3 q2 ctl and r3 q2 proto: those runs are
  2-3x slower across the board (the 0.8-1.1 fps values).
* A 280 MB asset download overlapped r2 q2 ctl (about 13:50 to 13:52).
* Short numpy jobs of a few seconds overlapped r2 q2 proto and r3 q0 ctl.

The median-of-3 removes a single bad run per cell, but not two. At q2 both r2 and r3 are suspect, so the
**q2 row is unreliable**. The cleanest pair is **q1 r1 / r2**.

**Reading.**
* **Deterministic:** the same draw calls in every view (30 / 27 / 49 / 30 at q0, the same at q1 and q2).
  The proto adds +17,064 primitives per view, about +10%: v2 near sets of 10.7k tris against c19sr, with
  the same LOD switch distances.
* **Measured, at clean q1:** proto close / mid / close_def run about 40% slower than ctl
  (3.5 → 2.1 fps; 3.2 → 2.0; 3.3 → 1.8). The wide view is equal or faster, inside the noise.
  Under llvmpipe this is mostly the near-set fragment shader: 4 id-map taps, a slot-edge blend and a
  normal-map TBN from derivatives. The extra vertices matter less.
* **Measured, at q0:** a 15-30% drop at close range; the mid view is equal.
* **On a real GPU,** expect the gap to shrink a lot: the extra triangles are about 10% and the texture taps
  are cheap. That needs re-measuring on Kirk's machine.

Raw logs: `out/proto/bench/r{1,2,3}/{ctl,proto}/q{0,1,2}.log` (not committed; the PERF blocks are summarised above).
Parser: the median over runs of 1000/median_ms per view.
