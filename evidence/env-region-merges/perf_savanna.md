# Perf: legacy ground (--env=0) vs env/steppe

Method: `tests/env_shots.tscn`, 1600x900, the same seven scripted cameras as every other region (evidence/env-scandinavia/perf.md), Godot 4.7.2 GL Compatibility on llvmpipe on a shared box. CPU ms/frame is the main metric; min wall ms is contention-dominated. Before/after ran back-to-back per quality level. The rendered frames were measurement by-products only and are not committed (Kirk, 9:24 PM / 10:05 PM: no screenshots or videos).

## prov 271 savanna

| q | view | CPU ms before -> after | dCPU | min wall ms | draws | prims |
|---|---|---|---|---|---|---|
| q0 | overview | 434 -> 471 | +9% | 118 -> 114 | 63 -> 113 | 189008 -> 103170 |
| q0 | formation | 296 -> 380 | +28% | 94 -> 106 | 53 -> 92 | 184292 -> 98898 |
| q0 | forest_edge | 262 -> 348 | +33% | 77 -> 92 | 49 -> 89 | 183506 -> 103504 |
| q0 | rocky | 292 -> 373 | +28% | 81 -> 98 | 49 -> 85 | 183506 -> 104572 |
| q0 | water | 278 -> 374 | +35% | 77 -> 100 | 49 -> 89 | 183506 -> 110864 |
| q0 | horizon | 323 -> 414 | +28% | 98 -> 108 | 63 -> 113 | 189008 -> 104498 |
| q0 | top | 399 -> 435 | +9% | 117 -> 108 | 63 -> 78 | 189008 -> 101110 |
| q1 | overview | 1328 -> 1715 | +29% | 285 -> 280 | 85 -> 137 | 354964 -> 205492 |
| q1 | formation | 1104 -> 1463 | +33% | 210 -> 273 | 65 -> 116 | 345532 -> 202134 |
| q1 | forest_edge | 903 -> 1365 | +51% | 180 -> 262 | 59 -> 118 | 343960 -> 209602 |
| q1 | rocky | 913 -> 1418 | +55% | 177 -> 263 | 57 -> 104 | 343960 -> 209218 |
| q1 | water | 824 -> 1537 | +87% | 160 -> 278 | 57 -> 121 | 343960 -> 225298 |
| q1 | horizon | 1389 -> 1637 | +18% | 296 -> 308 | 85 -> 139 | 354964 -> 209290 |
| q1 | top | 1247 -> 1164 | -7% | 239 -> 223 | 85 -> 104 | 354964 -> 203342 |
| q2 | overview | 1394 -> 1691 | +21% | 296 -> 315 | 85 -> 139 | 354966 -> 206984 |
| q2 | formation | 1142 -> 1451 | +27% | 236 -> 300 | 65 -> 117 | 345534 -> 203644 |
| q2 | forest_edge | 956 -> 1486 | +55% | 203 -> 291 | 61 -> 120 | 343962 -> 213476 |
| q2 | rocky | 966 -> 1470 | +52% | 196 -> 288 | 57 -> 106 | 343962 -> 213116 |
| q2 | water | 918 -> 1642 | +79% | 180 -> 314 | 57 -> 122 | 343962 -> 234212 |
| q2 | horizon | 1441 -> 1774 | +23% | 298 -> 366 | 89 -> 143 | 354966 -> 210776 |
| q2 | top | 1315 -> 1153 | -12% | 256 -> 241 | 85 -> 105 | 354966 -> 203384 |

- q0 mean CPU over the 7 views: 326 -> 400 ms (+22%)
- q1 mean CPU over the 7 views: 1101 -> 1471 ms (+34%)
- q2 mean CPU over the 7 views: 1162 -> 1524 ms (+31%)

