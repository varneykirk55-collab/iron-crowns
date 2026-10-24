# Perf: legacy ground (--env=0) vs env/arid

Same method as evidence/env-scandinavia/perf.md: `tests/env_shots.tscn`, 1600x900, same seven cameras, Godot 4.7.2 GL Compatibility on llvmpipe on a heavily shared box (load avg ~20-26 on 8 cores). CPU ms/frame is the main metric; min wall ms is contention-dominated and shown only for completeness. Before/after ran back-to-back per quality level.

## prov 46 Arizona (Sonoran)

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 429 -> 555 | +29% | 200 -> 118 | 63 -> 111 |
| q0 | formation | 314 -> 408 | +30% | 179 -> 106 | 53 -> 93 |
| q0 | forest_edge | 272 -> 366 | +35% | 151 -> 88 | 49 -> 86 |
| q0 | rocky | 280 -> 392 | +40% | 162 -> 96 | 49 -> 83 |
| q0 | water | 282 -> 359 | +28% | 145 -> 86 | 49 -> 86 |
| q0 | horizon | 338 -> 473 | +40% | 199 -> 97 | 63 -> 110 |
| q0 | top | 410 -> 430 | +5% | 250 -> 100 | 63 -> 77 |
| q1 | overview | 1290 -> 1478 | +15% | 270 -> 575 | 85 -> 135 |
| q1 | formation | 1050 -> 1232 | +17% | 215 -> 500 | 65 -> 119 |
| q1 | forest_edge | 872 -> 972 | +11% | 181 -> 210 | 59 -> 107 |
| q1 | rocky | 944 -> 1057 | +12% | 179 -> 227 | 57 -> 102 |
| q1 | water | 794 -> 989 | +25% | 162 -> 210 | 57 -> 107 |
| q1 | horizon | 1242 -> 1440 | +16% | 272 -> 271 | 85 -> 138 |
| q1 | top | 1241 -> 1122 | -10% | 235 -> 217 | 85 -> 108 |
| q2 | overview | 1330 -> 1494 | +12% | 621 -> 273 | 85 -> 140 |
| q2 | formation | 1081 -> 1320 | +22% | 515 -> 263 | 65 -> 121 |
| q2 | forest_edge | 859 -> 1060 | +23% | 426 -> 223 | 61 -> 109 |
| q2 | rocky | 909 -> 1183 | +30% | 406 -> 238 | 57 -> 102 |
| q2 | water | 784 -> 1068 | +36% | 362 -> 243 | 57 -> 107 |
| q2 | horizon | 1320 -> 1583 | +20% | 319 -> 703 | 89 -> 145 |
| q2 | top | 1228 -> 1133 | -8% | 286 -> 493 | 85 -> 108 |

## prov 242 Riyadh (Arabia)

| q | view | CPU ms before -> after | dCPU | min wall ms before -> after | draws before -> after |
|---|---|---|---|---|---|
| q0 | overview | 390 -> 440 | +13% | 110 -> 130 | 63 -> 107 |
| q0 | formation | 299 -> 334 | +12% | 93 -> 95 | 53 -> 87 |
| q0 | forest_edge | 256 -> 298 | +17% | 75 -> 85 | 49 -> 83 |
| q0 | rocky | 284 -> 332 | +17% | 78 -> 92 | 49 -> 85 |
| q0 | water | 293 -> 274 | -6% | 77 -> 80 | 49 -> 75 |
| q0 | horizon | 320 -> 375 | +17% | 99 -> 114 | 63 -> 108 |
| q0 | top | 396 -> 410 | +4% | 119 -> 112 | 63 -> 74 |
| q1 | overview | 1306 -> 1348 | +3% | 301 -> 318 | 85 -> 129 |
| q1 | formation | 1050 -> 1132 | +8% | 239 -> 252 | 65 -> 112 |
| q1 | forest_edge | 892 -> 952 | +7% | 203 -> 206 | 59 -> 107 |
| q1 | rocky | 960 -> 1040 | +8% | 200 -> 213 | 57 -> 101 |
| q1 | water | 848 -> 934 | +10% | 184 -> 196 | 57 -> 90 |
| q1 | horizon | 1322 -> 1410 | +7% | 322 -> 309 | 85 -> 134 |
| q1 | top | 1274 -> 1104 | -13% | 272 -> 241 | 85 -> 100 |
| q2 | overview | 1287 -> 1405 | +9% | 303 -> 591 | 85 -> 135 |
| q2 | formation | 1037 -> 1183 | +14% | 238 -> 548 | 65 -> 113 |
| q2 | forest_edge | 878 -> 960 | +9% | 180 -> 452 | 61 -> 109 |
| q2 | rocky | 931 -> 1043 | +12% | 208 -> 490 | 57 -> 101 |
| q2 | water | 811 -> 958 | +18% | 169 -> 434 | 57 -> 92 |
| q2 | horizon | 1483 -> 1488 | +0% | 300 -> 674 | 89 -> 138 |
| q2 | top | 1212 -> 1156 | -5% | 236 -> 468 | 85 -> 101 |

