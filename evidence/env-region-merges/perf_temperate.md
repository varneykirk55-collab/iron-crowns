# Perf: legacy ground (--env=0) vs env/steppe

Method: `tests/env_shots.tscn`, 1600x900, the same seven scripted cameras as every other region (evidence/env-scandinavia/perf.md), Godot 4.7.2 GL Compatibility on llvmpipe on a shared box. CPU ms/frame is the main metric; min wall ms is contention-dominated. Before/after ran back-to-back per quality level. The rendered frames were measurement by-products only and are not committed (Kirk, 9:24 PM / 10:05 PM: no screenshots or videos).

## prov 64 temperate

| q | view | CPU ms before -> after | dCPU | min wall ms | draws | prims |
|---|---|---|---|---|---|---|
| q0 | overview | 410 -> 538 | +31% | 139 -> 133 | 63 -> 112 | 189020 -> 116769 |
| q0 | formation | 305 -> 425 | +39% | 108 -> 122 | 53 -> 90 | 184304 -> 111392 |
| q0 | forest_edge | 278 -> 448 | +62% | 107 -> 109 | 49 -> 95 | 183518 -> 117194 |
| q0 | rocky | 304 -> 422 | +38% | 104 -> 119 | 49 -> 88 | 183518 -> 115442 |
| q0 | water | 286 -> 311 | +9% | 91 -> 91 | 49 -> 79 | 183518 -> 110987 |
| q0 | horizon | 335 -> 460 | +37% | 128 -> 125 | 63 -> 108 | 189020 -> 116850 |
| q0 | top | 422 -> 430 | +2% | 155 -> 106 | 63 -> 79 | 189020 -> 114968 |
| q1 | overview | 1326 -> 2208 | +67% | 281 -> 379 | 85 -> 136 | 354978 -> 250131 |
| q1 | formation | 1152 -> 1816 | +58% | 225 -> 318 | 65 -> 120 | 345546 -> 251462 |
| q1 | forest_edge | 874 -> 4174 | +378% | 183 -> 673 | 59 -> 125 | 343974 -> 294742 |
| q1 | rocky | 890 -> 3616 | +306% | 180 -> 582 | 57 -> 108 | 343974 -> 276804 |
| q1 | water | 842 -> 1724 | +105% | 169 -> 326 | 57 -> 110 | 343974 -> 266241 |
| q1 | horizon | 1292 -> 2214 | +71% | 287 -> 395 | 85 -> 137 | 354978 -> 252216 |
| q1 | top | 1254 -> 1139 | -9% | 225 -> 234 | 85 -> 105 | 354978 -> 249780 |
| q2 | overview | 1303 -> 2510 | +93% | 274 -> 448 | 85 -> 143 | 354966 -> 253433 |
| q2 | formation | 1060 -> 2078 | +96% | 221 -> 373 | 65 -> 129 | 345534 -> 250508 |
| q2 | forest_edge | 865 -> 3270 | +278% | 183 -> 534 | 61 -> 125 | 343962 -> 253464 |
| q2 | rocky | 909 -> 2909 | +220% | 183 -> 476 | 57 -> 109 | 343962 -> 250010 |
| q2 | water | 794 -> 1810 | +128% | 164 -> 338 | 57 -> 117 | 343962 -> 251999 |
| q2 | horizon | 1406 -> 2582 | +84% | 279 -> 543 | 89 -> 141 | 354966 -> 252226 |
| q2 | top | 1312 -> 1185 | -10% | 250 -> 292 | 85 -> 106 | 354966 -> 250170 |

- q0 mean CPU over the 7 views: 334 -> 433 ms (+30%)
- q1 mean CPU over the 7 views: 1090 -> 2413 ms (+121%)
- q2 mean CPU over the 7 views: 1093 -> 2335 ms (+114%)

