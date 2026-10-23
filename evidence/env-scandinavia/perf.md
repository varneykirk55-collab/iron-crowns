# Perf: legacy ground vs env/scandinavia-medieval

Setup: `tests/env_shots.tscn`, Battle of Malmö at t = 14 s, 1600x900, the same seven cameras, 8 timed frames per view after settling. Godot 4.7.2 GL Compatibility on **llvmpipe** (CPU rasteriser, no GPU), on a shared box with load average 6 to 19 while I measured. Each before/after pair ran back-to-back. q1 was re-run as a quieter interleaved pair, and that re-run is what the table shows.

- **CPU ms/frame** is process CPU time (all llvmpipe threads) per frame. It measures how much rendering work there is and barely depends on box load, so it is the main metric here.
- **min wall ms** is the best frame-to-frame time. It is dominated by contention from other agents and is shown for completeness only. Some "after" walls are lower simply because the box was quieter.
- **draws** is RenderingServer draw calls per frame. Primitive counts are not comparable: the legacy path's MultiMesh scatter is counted per instance, so they are omitted.

| q | view | CPU ms/frame before → after | Δ CPU | min wall ms before → after | draws before → after |
|---|---|---|---|---|---|
| q0 | overview | 431 → 494 | +15% | 187 → 212 | 63 → 113 |
| q0 | formation | 330 → 378 | +14% | 113 → 152 | 53 → 90 |
| q0 | forest_edge | 265 → 355 | +34% | 102 → 164 | 49 → 94 |
| q0 | rocky | 282 → 379 | +34% | 106 → 164 | 49 → 86 |
| q0 | water | 272 → 299 | +10% | 99 → 130 | 49 → 75 |
| q0 | horizon | 349 → 418 | +20% | 164 → 196 | 63 → 107 |
| q0 | top | 429 → 406 | -5% | 147 → 156 | 63 → 75 |
| q1 | overview | 1339 → 1959 | +46% | 667 → 552 | 85 → 137 |
| q1 | formation | 1116 → 1568 | +40% | 649 → 476 | 63 → 110 |
| q1 | forest_edge | 912 → 2014 | +121% | 457 → 391 | 57 → 116 |
| q1 | rocky | 899 → 1845 | +105% | 484 → 284 | 57 → 109 |
| q1 | water | 856 → 1339 | +56% | 466 → 235 | 57 → 100 |
| q1 | horizon | 1321 → 1934 | +46% | 667 → 311 | 87 → 136 |
| q1 | top | 1276 → 1111 | -13% | 674 → 206 | 83 → 99 |
| q2 | overview | 1332 → 2118 | +59% | 708 → 382 | 85 → 139 |
| q2 | formation | 1109 → 1702 | +54% | 632 → 325 | 61 → 110 |
| q2 | forest_edge | 865 → 2349 | +172% | 486 → 391 | 59 → 119 |
| q2 | rocky | 940 → 2102 | +124% | 525 → 360 | 57 → 113 |
| q2 | water | 858 → 1485 | +73% | 464 → 319 | 57 → 102 |
| q2 | horizon | 1371 → 2059 | +50% | 656 → 520 | 87 → 136 |
| q2 | top | 1236 → 1138 | -8% | 337 → 232 | 85 → 101 |

## Reading
- **q0 (Low):** +10% to +34% CPU. No shadows, and only tier-0 instances (about a third of the cover and far trees).
- **q1 (Medium) and q2 (High):** +40% to +60% CPU on wide views and +100% to +170% on the views that look into the forest (forest_edge, rocky). Profiling with debug toggles put most of it on the forest: the far conifer belt (the biggest single item), detail-tree shadows, and then the terrain shader. Draw calls rise from about 57–87 to about 100–139. The env uses one MultiMesh per model per tile, with LOD by visibility range.
- The top-down view is cheaper than legacy (−5% to −13%).
- On a real GPU this fill-rate-type cost is far smaller than on llvmpipe, but **I could not measure on a GPU**.

## Levers that were already applied
- Far forest belt: fewer, larger impostor-like `env_conifer_far` instances.
- Detail trees: 125 m tiles that switch to the LOD conifer at 190 m.
- Cover: visible to 150 m only, and casts no shadows.
- Quality tiers: `visible_instance_count`.
- Terrain shader: branches skip noise samples at distance.

## Levers still available
- Detail trees could stop casting shadows at q1.
- The detail tree distance could shrink from 190 m to 140 m.
- Cover density could be lower at q1.
