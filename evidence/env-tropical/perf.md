# Perf: legacy ground (--env=0) vs env/tropical

Same method as evidence/env-scandinavia/perf.md: `tests/env_shots.tscn`, 1600x900, same seven cameras, Godot 4.7.2 GL Compatibility on llvmpipe on a heavily shared box (load avg ~20-26 on 8 cores). CPU ms/frame is the main metric; min wall ms is contention-dominated and shown only for completeness. Before/after ran back-to-back per quality level.

## prov 517 Manila

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 435 -> 590 | +36% | 201 -> 221 | 63 -> 116 |
| q0 | formation | 319 -> 443 | +39% | 130 -> 184 | 53 -> 93 |
| q0 | forest_edge | 276 -> 480 | +74% | 128 -> 219 | 49 -> 99 |
| q0 | rocky | 302 -> 456 | +51% | 114 -> 180 | 49 -> 92 |
| q0 | water | 287 -> 358 | +25% | 119 -> 167 | 49 -> 80 |
| q0 | horizon | 358 -> 504 | +41% | 144 -> 280 | 63 -> 112 |
| q0 | top | 432 -> 465 | +8% | 164 -> 177 | 63 -> 77 |
| q1 | overview | 1358 -> 2768 | +104% | 640 -> 1020 | 85 -> 140 |
| q1 | formation | 1106 -> 2174 | +97% | 536 -> 801 | 63 -> 111 |
| q1 | forest_edge | 860 -> 4031 | +369% | 332 -> 1605 | 57 -> 125 |
| q1 | rocky | 864 -> 3038 | +251% | 368 -> 1213 | 57 -> 115 |
| q1 | water | 816 -> 1880 | +130% | 305 -> 656 | 57 -> 108 |
| q1 | horizon | 1283 -> 2774 | +116% | 591 -> 1070 | 87 -> 140 |
| q1 | top | 1238 -> 1376 | +11% | 477 -> 624 | 83 -> 100 |
| q2 | overview | 1327 -> 2786 | +110% | 644 -> 1269 | 85 -> 142 |
| q2 | formation | 1056 -> 2218 | +110% | 519 -> 1031 | 61 -> 109 |
| q2 | forest_edge | 847 -> 4529 | +435% | 308 -> 1538 | 59 -> 127 |
| q2 | rocky | 855 -> 3422 | +300% | 335 -> 1289 | 57 -> 117 |
| q2 | water | 785 -> 1970 | +151% | 312 -> 1014 | 57 -> 108 |
| q2 | horizon | 1293 -> 2914 | +125% | 569 -> 1464 | 87 -> 140 |
| q2 | top | 1232 -> 1344 | +9% | 480 -> 780 | 85 -> 103 |

## prov 518 Iloilo

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 396 -> 518 | +31% | 211 -> 232 | 63 -> 115 |
| q0 | formation | 294 -> 403 | +37% | 178 -> 146 | 53 -> 92 |
| q0 | forest_edge | 261 -> 448 | +72% | 146 -> 168 | 49 -> 99 |
| q0 | rocky | 291 -> 414 | +42% | 160 -> 168 | 49 -> 89 |
| q0 | water | 276 -> 320 | +16% | 134 -> 163 | 49 -> 80 |
| q0 | horizon | 328 -> 454 | +39% | 210 -> 191 | 63 -> 112 |
| q0 | top | 414 -> 420 | +2% | 213 -> 156 | 63 -> 77 |
| q1 | overview | 1308 -> 2460 | +88% | 389 -> 684 | 85 -> 138 |
| q1 | formation | 1065 -> 2064 | +94% | 376 -> 490 | 63 -> 107 |
| q1 | forest_edge | 860 -> 3758 | +337% | 491 -> 683 | 57 -> 128 |
| q1 | rocky | 920 -> 2718 | +195% | 422 -> 636 | 57 -> 115 |
| q1 | water | 824 -> 1598 | +94% | 398 -> 462 | 57 -> 107 |
| q1 | horizon | 1296 -> 2516 | +94% | 561 -> 667 | 87 -> 141 |
| q1 | top | 1252 -> 1292 | +3% | 492 -> 396 | 83 -> 100 |
| q2 | overview | 1362 -> 2756 | +102% | 797 -> 1061 | 85 -> 140 |
| q2 | formation | 1092 -> 2228 | +104% | 703 -> 847 | 61 -> 105 |
| q2 | forest_edge | 894 -> 4754 | +432% | 506 -> 1568 | 59 -> 130 |
| q2 | rocky | 914 -> 3340 | +265% | 584 -> 1132 | 57 -> 117 |
| q2 | water | 926 -> 1810 | +95% | 498 -> 772 | 57 -> 108 |
| q2 | horizon | 1403 -> 2842 | +103% | 760 -> 1055 | 87 -> 141 |
| q2 | top | 1306 -> 1310 | +0% | 756 -> 580 | 85 -> 103 |

## Reading
- q0 (Low): +2% to +74% CPU, in the same range as Scandinavia (+10% to +34%) apart from the forest-facing views.
- q1/q2: the forest-facing views (forest_edge, rocky) cost about 2-3x more than Scandinavia's increase. The multi-layer jungle wall is the reason: canopy, emergents, palms, a 3200-instance thicket, ferns and bananas, all shadow-casting at q1/q2, are fill-bound on llvmpipe. Wide views are +90% to +125%. Top-down is unchanged.
- I could not measure on a GPU. On a real GPU this overdraw cost is far smaller.
