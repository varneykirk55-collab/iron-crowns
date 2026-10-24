# Perf: legacy ground (--env=0) vs env/mediterranean

Same method as evidence/env-scandinavia/perf.md: `tests/env_shots.tscn`, 1600x900, same seven cameras, Godot 4.7.2 GL Compatibility on llvmpipe on a heavily shared box (load avg ~20-26 on 8 cores). CPU ms/frame is the main metric; min wall ms is contention-dominated and shown only for completeness. Before/after ran back-to-back per quality level.

## prov 482 Rome, Italy (coast, wet Feb)

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 397 -> 494 | +24% | 106 -> 172 | 63 -> 112 |
| q0 | formation | 293 -> 392 | +34% | 104 -> 135 | 53 -> 91 |
| q0 | forest_edge | 264 -> 349 | +32% | 87 -> 102 | 49 -> 96 |
| q0 | rocky | 278 -> 376 | +36% | 90 -> 110 | 49 -> 85 |
| q0 | water | 261 -> 314 | +20% | 87 -> 110 | 49 -> 80 |
| q0 | horizon | 318 -> 420 | +32% | 108 -> 115 | 63 -> 108 |
| q0 | top | 390 -> 426 | +9% | 125 -> 143 | 63 -> 76 |
| q1 | overview | 1354 -> 1554 | +15% | 713 -> 314 | 85 -> 132 |
| q1 | formation | 1098 -> 1306 | +19% | 520 -> 302 | 65 -> 117 |
| q1 | forest_edge | 884 -> 1337 | +51% | 471 -> 326 | 59 -> 128 |
| q1 | rocky | 894 -> 1325 | +48% | 504 -> 358 | 57 -> 107 |
| q1 | water | 846 -> 1077 | +27% | 454 -> 315 | 57 -> 98 |
| q1 | horizon | 1293 -> 1592 | +23% | 788 -> 576 | 85 -> 133 |
| q1 | top | 1264 -> 1106 | -13% | 715 -> 591 | 85 -> 99 |
| q2 | overview | 1310 -> 1677 | +28% | 281 -> 767 | 85 -> 135 |
| q2 | formation | 1065 -> 1450 | +36% | 231 -> 754 | 65 -> 119 |
| q2 | forest_edge | 868 -> 1503 | +73% | 196 -> 758 | 61 -> 130 |
| q2 | rocky | 904 -> 1496 | +65% | 266 -> 660 | 57 -> 106 |
| q2 | water | 818 -> 1198 | +46% | 251 -> 611 | 57 -> 101 |
| q2 | horizon | 1382 -> 1773 | +28% | 286 -> 520 | 89 -> 138 |
| q2 | top | 1254 -> 1108 | -12% | 250 -> 259 | 85 -> 100 |

## prov 43 California (live oak / chaparral, wet Feb)

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 387 -> 562 | +45% | 93 -> 116 | 63 -> 112 |
| q0 | formation | 288 -> 397 | +38% | 81 -> 100 | 53 -> 89 |
| q0 | forest_edge | 259 -> 374 | +44% | 68 -> 92 | 49 -> 87 |
| q0 | rocky | 319 -> 380 | +19% | 75 -> 93 | 49 -> 83 |
| q0 | water | 287 -> 318 | +11% | 80 -> 80 | 49 -> 76 |
| q0 | horizon | 348 -> 463 | +33% | 110 -> 111 | 63 -> 109 |
| q0 | top | 426 -> 414 | -3% | 262 -> 100 | 63 -> 75 |
| q1 | overview | 1336 -> 1682 | +26% | 809 -> 949 | 85 -> 134 |
| q1 | formation | 1083 -> 1464 | +35% | 625 -> 780 | 65 -> 115 |
| q1 | forest_edge | 878 -> 1493 | +70% | 550 -> 812 | 59 -> 108 |
| q1 | rocky | 2525 -> 1486 | -41% | 570 -> 943 | 57 -> 101 |
| q1 | water | 1328 -> 1169 | -12% | 508 -> 764 | 57 -> 94 |
| q1 | horizon | 1434 -> 1816 | +27% | 1017 -> 1117 | 85 -> 133 |
| q1 | top | 1376 -> 1146 | -17% | 809 -> 703 | 85 -> 100 |
| q2 | overview | 1346 -> 1694 | +26% | 350 -> 909 | 85 -> 136 |
| q2 | formation | 1068 -> 1504 | +41% | 286 -> 743 | 65 -> 115 |
| q2 | forest_edge | 886 -> 1586 | +79% | 238 -> 727 | 61 -> 110 |
| q2 | rocky | 946 -> 1662 | +76% | 213 -> 822 | 57 -> 101 |
| q2 | water | 841 -> 1202 | +43% | 217 -> 353 | 57 -> 97 |
| q2 | horizon | 1398 -> 1924 | +38% | 392 -> 570 | 89 -> 137 |
| q2 | top | 1286 -> 1174 | -9% | 339 -> 288 | 85 -> 101 |

## prov 157 Victoria, Australia (eucalypt, dry Feb)

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 427 -> 468 | +9% | 148 -> 140 | 63 -> 113 |
| q0 | formation | 296 -> 370 | +25% | 110 -> 114 | 53 -> 91 |
| q0 | forest_edge | 268 -> 351 | +31% | 88 -> 104 | 49 -> 86 |
| q0 | rocky | 288 -> 362 | +26% | 117 -> 111 | 49 -> 80 |
| q0 | water | 288 -> 312 | +9% | 115 -> 99 | 49 -> 79 |
| q0 | horizon | 336 -> 417 | +24% | 132 -> 179 | 63 -> 108 |
| q0 | top | 410 -> 431 | +5% | 176 -> 130 | 63 -> 76 |
| q1 | overview | 1304 -> 1582 | +21% | 447 -> 896 | 85 -> 132 |
| q1 | formation | 1095 -> 1342 | +23% | 344 -> 637 | 65 -> 114 |
| q1 | forest_edge | 868 -> 1613 | +86% | 303 -> 884 | 59 -> 104 |
| q1 | rocky | 887 -> 1494 | +68% | 297 -> 508 | 57 -> 93 |
| q1 | water | 806 -> 1091 | +35% | 275 -> 376 | 57 -> 93 |
| q1 | horizon | 1308 -> 1627 | +24% | 524 -> 555 | 85 -> 132 |
| q1 | top | 1308 -> 1125 | -14% | 516 -> 445 | 85 -> 100 |
| q2 | overview | 1316 -> 1652 | +26% | 690 -> 431 | 85 -> 136 |
| q2 | formation | 1070 -> 1406 | +31% | 511 -> 407 | 65 -> 114 |
| q2 | forest_edge | 852 -> 1684 | +98% | 491 -> 419 | 61 -> 107 |
| q2 | rocky | 870 -> 1630 | +87% | 522 -> 376 | 57 -> 93 |
| q2 | water | 807 -> 1172 | +45% | 492 -> 266 | 57 -> 94 |
| q2 | horizon | 1392 -> 1800 | +29% | 806 -> 439 | 89 -> 137 |
| q2 | top | 1236 -> 1088 | -12% | 440 -> 293 | 85 -> 100 |

