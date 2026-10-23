# Perf: legacy ground (--env=0) vs env/east_asia

Same method as evidence/env-scandinavia/perf.md: `tests/env_shots.tscn`, 1600x900, same seven cameras, Godot 4.7.2 GL Compatibility on llvmpipe on a heavily shared box (load avg ~20-26 on 8 cores). CPU ms/frame is the main metric; min wall ms is contention-dominated and shown only for completeness. Before/after ran back-to-back per quality level.

## prov 474 Tokyo

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 427 -> 566 | +32% | 268 -> 236 | 63 -> 116 |
| q0 | formation | 316 -> 434 | +38% | 231 -> 194 | 53 -> 92 |
| q0 | forest_edge | 285 -> 430 | +51% | 205 -> 209 | 49 -> 103 |
| q0 | rocky | 305 -> 422 | +39% | 219 -> 225 | 49 -> 89 |
| q0 | water | 300 -> 336 | +12% | 198 -> 170 | 49 -> 82 |
| q0 | horizon | 361 -> 456 | +26% | 257 -> 242 | 63 -> 110 |
| q0 | top | 434 -> 438 | +1% | 300 -> 216 | 63 -> 76 |
| q1 | overview | 1370 -> 2268 | +65% | 673 -> 1421 | 85 -> 139 |
| q1 | formation | 1100 -> 1865 | +70% | 505 -> 992 | 63 -> 108 |
| q1 | forest_edge | 890 -> 2897 | +225% | 467 -> 1316 | 57 -> 137 |
| q1 | rocky | 888 -> 2312 | +160% | 678 -> 1064 | 57 -> 123 |
| q1 | water | 825 -> 1562 | +89% | 670 -> 732 | 57 -> 118 |
| q1 | horizon | 1313 -> 2285 | +74% | 799 -> 1010 | 87 -> 140 |
| q1 | top | 1308 -> 1224 | -6% | 847 -> 629 | 83 -> 101 |
| q2 | overview | 1527 -> 2543 | +67% | 354 -> 1298 | 85 -> 141 |
| q2 | formation | 1164 -> 1970 | +69% | 286 -> 913 | 61 -> 106 |
| q2 | forest_edge | 942 -> 3356 | +256% | 259 -> 718 | 59 -> 139 |
| q2 | rocky | 1026 -> 2780 | +171% | 249 -> 601 | 57 -> 127 |
| q2 | water | 851 -> 1773 | +108% | 225 -> 356 | 57 -> 119 |
| q2 | horizon | 1401 -> 2642 | +89% | 320 -> 440 | 87 -> 140 |
| q2 | top | 1338 -> 1312 | -2% | 302 -> 277 | 85 -> 103 |

## prov 586 Taipei

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 436 -> 572 | +31% | 139 -> 171 | 63 -> 114 |
| q0 | formation | 314 -> 451 | +44% | 118 -> 135 | 53 -> 91 |
| q0 | forest_edge | 278 -> 462 | +66% | 109 -> 135 | 49 -> 102 |
| q0 | rocky | 294 -> 450 | +53% | 104 -> 134 | 49 -> 90 |
| q0 | water | 294 -> 365 | +24% | 99 -> 146 | 49 -> 81 |
| q0 | horizon | 354 -> 520 | +47% | 118 -> 172 | 63 -> 111 |
| q0 | top | 419 -> 450 | +8% | 125 -> 156 | 63 -> 77 |
| q1 | overview | 1548 -> 2258 | +46% | 295 -> 413 | 85 -> 137 |
| q1 | formation | 1210 -> 1924 | +59% | 253 -> 392 | 63 -> 107 |
| q1 | forest_edge | 1032 -> 3066 | +197% | 209 -> 671 | 57 -> 137 |
| q1 | rocky | 1034 -> 2430 | +135% | 204 -> 420 | 57 -> 119 |
| q1 | water | 919 -> 1598 | +74% | 184 -> 287 | 57 -> 113 |
| q1 | horizon | 1445 -> 2414 | +67% | 293 -> 409 | 87 -> 141 |
| q1 | top | 1370 -> 1254 | -8% | 267 -> 249 | 83 -> 101 |
| q2 | overview | 1456 -> 2616 | +80% | 306 -> 464 | 85 -> 139 |
| q2 | formation | 1120 -> 2138 | +91% | 246 -> 408 | 61 -> 105 |
| q2 | forest_edge | 900 -> 3562 | +296% | 190 -> 530 | 59 -> 141 |
| q2 | rocky | 924 -> 2804 | +203% | 180 -> 474 | 57 -> 125 |
| q2 | water | 854 -> 1772 | +107% | 164 -> 362 | 57 -> 116 |
| q2 | horizon | 1368 -> 2649 | +94% | 278 -> 472 | 87 -> 141 |
| q2 | top | 1330 -> 1294 | -3% | 256 -> 274 | 85 -> 103 |

