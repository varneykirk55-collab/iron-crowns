# Perf: legacy ground (--env=0) vs env/steppe

Method: `tests/env_shots.tscn`, 1600x900, the same seven scripted cameras as every other region (evidence/env-scandinavia/perf.md), Godot 4.7.2 GL Compatibility on llvmpipe on a shared box. CPU ms/frame is the main metric; min wall ms is contention-dominated. Before/after ran back-to-back per quality level. The rendered frames were measurement by-products only and are not committed (Kirk, 9:24 PM / 10:05 PM: no screenshots or videos).

## prov 46 arid (Arizona; q2 'after' re-measured once because the first run had a 62 s stall in forest_edge)

| q | view | CPU ms before -> after | dCPU | min wall ms | draws | prims |
|---|---|---|---|---|---|---|
| q0 | overview | 424 -> 520 | +23% | 111 -> 126 | 63 -> 111 | 189020 -> 123111 |
| q0 | formation | 322 -> 397 | +23% | 93 -> 112 | 53 -> 93 | 184304 -> 112636 |
| q0 | forest_edge | 290 -> 376 | +29% | 83 -> 101 | 49 -> 86 | 183518 -> 108191 |
| q0 | rocky | 306 -> 403 | +32% | 84 -> 107 | 49 -> 83 | 183518 -> 108906 |
| q0 | water | 289 -> 387 | +34% | 83 -> 100 | 49 -> 86 | 183518 -> 108120 |
| q0 | horizon | 361 -> 483 | +34% | 107 -> 131 | 63 -> 110 | 189020 -> 118138 |
| q0 | top | 445 -> 470 | +6% | 131 -> 119 | 63 -> 77 | 189020 -> 97858 |
| q1 | overview | 1416 -> 1532 | +8% | 281 -> 266 | 85 -> 137 | 354956 -> 211335 |
| q1 | formation | 1123 -> 1242 | +11% | 229 -> 222 | 65 -> 119 | 345524 -> 197609 |
| q1 | forest_edge | 1006 -> 1040 | +3% | 204 -> 211 | 59 -> 107 | 343952 -> 189423 |
| q1 | rocky | 929 -> 1086 | +17% | 188 -> 218 | 57 -> 102 | 343952 -> 190255 |
| q1 | water | 840 -> 998 | +19% | 169 -> 207 | 57 -> 107 | 343952 -> 187641 |
| q1 | horizon | 1341 -> 1560 | +16% | 292 -> 290 | 85 -> 138 | 354956 -> 205587 |
| q1 | top | 1342 -> 1294 | -4% | 260 -> 260 | 85 -> 108 | 354956 -> 174862 |
| q2 | overview | 1453 -> 1638 | +13% | 292 -> 314 | 85 -> 140 | 354966 -> 225060 |
| q2 | formation | 1196 -> 1330 | +11% | 233 -> 348 | 65 -> 121 | 345534 -> 207765 |
| q2 | forest_edge | 944 -> 1071 | +13% | 199 -> 309 | 61 -> 109 | 343962 -> 199747 |
| q2 | rocky | 1036 -> 1151 | +11% | 191 -> 300 | 57 -> 102 | 343962 -> 198440 |
| q2 | water | 890 -> 1110 | +25% | 179 -> 287 | 57 -> 107 | 343962 -> 196440 |
| q2 | horizon | 1408 -> 1600 | +14% | 297 -> 403 | 89 -> 145 | 354966 -> 217406 |
| q2 | top | 1370 -> 1154 | -16% | 252 -> 285 | 85 -> 108 | 354966 -> 177372 |

- q0 mean CPU over the 7 views: 348 -> 434 ms (+25%)
- q1 mean CPU over the 7 views: 1142 -> 1250 ms (+9%)
- q2 mean CPU over the 7 views: 1185 -> 1293 ms (+9%)

