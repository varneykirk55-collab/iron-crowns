# Perf: legacy ground (--env=0) vs env/steppe

Method: `tests/env_shots.tscn`, 1600x900, the same seven scripted cameras as every other region (evidence/env-scandinavia/perf.md), Godot 4.7.2 GL Compatibility on llvmpipe on a shared box. CPU ms/frame is the main metric; min wall ms is contention-dominated. Before/after ran back-to-back per quality level. The rendered frames were measurement by-products only and are not committed (Kirk, 9:24 PM / 10:05 PM: no screenshots or videos).

## prov 482 mediterranean (Rome)

| q | view | CPU ms before -> after | dCPU | min wall ms | draws | prims |
|---|---|---|---|---|---|---|
| q0 | overview | 456 -> 524 | +15% | 112 -> 120 | 63 -> 112 | 189040 -> 100982 |
| q0 | formation | 346 -> 419 | +21% | 91 -> 107 | 53 -> 91 | 184324 -> 95904 |
| q0 | forest_edge | 300 -> 377 | +25% | 78 -> 96 | 49 -> 96 | 183538 -> 99130 |
| q0 | rocky | 304 -> 410 | +35% | 78 -> 102 | 49 -> 85 | 183538 -> 104672 |
| q0 | water | 304 -> 354 | +16% | 76 -> 90 | 49 -> 80 | 183538 -> 95054 |
| q0 | horizon | 366 -> 474 | +29% | 100 -> 110 | 63 -> 108 | 189040 -> 108726 |
| q0 | top | 460 -> 465 | +1% | 123 -> 111 | 63 -> 77 | 189040 -> 99920 |
| q1 | overview | 1472 -> 1753 | +19% | 280 -> 308 | 85 -> 132 | 354980 -> 176698 |
| q1 | formation | 1112 -> 1460 | +31% | 212 -> 276 | 65 -> 117 | 345548 -> 171996 |
| q1 | forest_edge | 936 -> 1450 | +55% | 180 -> 270 | 59 -> 128 | 343976 -> 174476 |
| q1 | rocky | 938 -> 1448 | +54% | 175 -> 268 | 57 -> 107 | 343976 -> 186394 |
| q1 | water | 911 -> 1170 | +28% | 162 -> 230 | 57 -> 98 | 343976 -> 167872 |
| q1 | horizon | 1360 -> 1744 | +28% | 284 -> 314 | 85 -> 133 | 354980 -> 193118 |
| q1 | top | 1316 -> 1184 | -10% | 238 -> 238 | 85 -> 99 | 354980 -> 176408 |
| q2 | overview | 1468 -> 1782 | +21% | 287 -> 310 | 85 -> 135 | 354954 -> 177502 |
| q2 | formation | 1230 -> 1492 | +21% | 227 -> 286 | 65 -> 119 | 345522 -> 172228 |
| q2 | forest_edge | 982 -> 1554 | +58% | 188 -> 285 | 61 -> 130 | 343950 -> 174204 |
| q2 | rocky | 1018 -> 1516 | +49% | 189 -> 281 | 57 -> 106 | 343950 -> 185866 |
| q2 | water | 862 -> 1226 | +42% | 164 -> 234 | 57 -> 101 | 343950 -> 168726 |
| q2 | horizon | 1472 -> 1920 | +31% | 281 -> 359 | 89 -> 138 | 354954 -> 193118 |
| q2 | top | 1357 -> 1229 | -9% | 245 -> 242 | 85 -> 100 | 354954 -> 184248 |

- q0 mean CPU over the 7 views: 363 -> 432 ms (+19%)
- q1 mean CPU over the 7 views: 1150 -> 1458 ms (+27%)
- q2 mean CPU over the 7 views: 1199 -> 1532 ms (+28%)

