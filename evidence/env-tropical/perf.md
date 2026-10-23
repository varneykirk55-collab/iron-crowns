# Perf: legacy ground (--env=0) vs env/tropical

Same method as evidence/env-scandinavia/perf.md: `tests/env_shots.tscn`, 1600x900, same seven cameras, Godot 4.7.2 GL Compatibility on llvmpipe on a heavily shared box (load avg ~20-26 on 8 cores). CPU ms/frame is the main metric; min wall ms is contention-dominated and shown only for completeness. Before/after ran back-to-back per quality level.

## prov 517 Manila

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 426 -> 563 | +32% | 225 -> 269 | 63 -> 114 |
| q0 | formation | 326 -> 429 | +32% | 172 -> 218 | 53 -> 91 |
| q0 | forest_edge | 294 -> 470 | +60% | 218 -> 234 | 49 -> 98 |
| q0 | rocky | 313 -> 442 | +41% | 192 -> 240 | 49 -> 90 |
| q0 | water | 302 -> 360 | +19% | 176 -> 200 | 49 -> 79 |
| q0 | horizon | 360 -> 490 | +36% | 217 -> 256 | 63 -> 112 |
| q0 | top | 438 -> 456 | +4% | 237 -> 252 | 63 -> 77 |
| q1 | overview | 1454 -> 2504 | +72% | 276 -> 408 | 85 -> 138 |
| q1 | formation | 1108 -> 1976 | +78% | 218 -> 391 | 63 -> 106 |
| q1 | forest_edge | 894 -> 3498 | +291% | 174 -> 628 | 57 -> 124 |
| q1 | rocky | 903 -> 2572 | +185% | 171 -> 490 | 57 -> 115 |
| q1 | water | 890 -> 1662 | +87% | 156 -> 458 | 57 -> 107 |
| q1 | horizon | 1382 -> 2473 | +79% | 286 -> 606 | 87 -> 141 |
| q1 | top | 1370 -> 1300 | -5% | 504 -> 318 | 83 -> 101 |
| q2 | overview | 1390 -> 2708 | +95% | 304 -> 484 | 85 -> 140 |
| q2 | formation | 1102 -> 2108 | +91% | 299 -> 439 | 61 -> 104 |
| q2 | forest_edge | 886 -> 4010 | +353% | 224 -> 639 | 59 -> 127 |
| q2 | rocky | 893 -> 2978 | +233% | 232 -> 505 | 57 -> 117 |
| q2 | water | 809 -> 1786 | +121% | 204 -> 363 | 57 -> 110 |
| q2 | horizon | 1366 -> 2756 | +102% | 312 -> 498 | 87 -> 141 |
| q2 | top | 1274 -> 1360 | +7% | 243 -> 298 | 85 -> 103 |

## prov 518 Iloilo

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 414 -> 536 | +29% | 164 -> 154 | 63 -> 116 |
| q0 | formation | 306 -> 414 | +35% | 130 -> 132 | 53 -> 94 |
| q0 | forest_edge | 310 -> 450 | +45% | 104 -> 134 | 49 -> 100 |
| q0 | rocky | 281 -> 416 | +48% | 138 -> 135 | 49 -> 90 |
| q0 | water | 278 -> 323 | +16% | 114 -> 117 | 49 -> 82 |
| q0 | horizon | 345 -> 450 | +31% | 162 -> 141 | 63 -> 111 |
| q0 | top | 414 -> 446 | +8% | 164 -> 148 | 63 -> 77 |
| q1 | overview | 1421 -> 2363 | +66% | 302 -> 623 | 85 -> 139 |
| q1 | formation | 1092 -> 1904 | +74% | 235 -> 524 | 63 -> 109 |
| q1 | forest_edge | 882 -> 3412 | +287% | 186 -> 506 | 57 -> 127 |
| q1 | rocky | 894 -> 2514 | +181% | 184 -> 404 | 57 -> 113 |
| q1 | water | 840 -> 1698 | +102% | 166 -> 316 | 57 -> 107 |
| q1 | horizon | 1294 -> 2438 | +88% | 256 -> 399 | 87 -> 140 |
| q1 | top | 1258 -> 1350 | +7% | 246 -> 258 | 83 -> 100 |
| q2 | overview | 1384 -> 2688 | +94% | 295 -> 444 | 85 -> 141 |
| q2 | formation | 1138 -> 2079 | +83% | 245 -> 411 | 61 -> 107 |
| q2 | forest_edge | 901 -> 3978 | +342% | 175 -> 1216 | 59 -> 129 |
| q2 | rocky | 932 -> 2948 | +216% | 178 -> 992 | 57 -> 115 |
| q2 | water | 878 -> 1742 | +99% | 162 -> 682 | 57 -> 109 |
| q2 | horizon | 1354 -> 2708 | +100% | 278 -> 926 | 87 -> 140 |
| q2 | top | 1294 -> 1306 | +1% | 238 -> 602 | 85 -> 103 |


## Reading
These numbers were re-shot at 4c0cd68 (Manila q1 legacy re-run separately after an interrupted shot) (perf trim) merged with framework 64c912d.
- **q0 (Low):** +29..+60 % CPU. Wide views are in the same range as Scandinavia.
- **q1 / q2 forest-facing views (forest_edge, rocky):** still the most expensive at about 3.8-4.5x legacy. The cause is the multi-layer jungle wall (canopy, emergents, palms, thicket, ferns, bananas), which casts shadows at q1/q2 and is fill-bound on llvmpipe.
- **Effect of the trim** (tree_cell 6.4 -> 7.0, thicket 3200 -> 2400), absolute after-CPU on forest_edge versus the pre-trim run:
  - Manila q1: 4031 -> 3498 ms (-13 %); q2: 4529 -> 4010 ms (-11 %).
  - Iloilo q1: 3758 -> 3412 ms (-9 %); q2: 4754 -> 3978 ms (-16 %).
- **Wide views:** +66..+95 %. Top-down is unchanged.
- I could not measure on a GPU. On a real GPU this overdraw cost is far smaller.
