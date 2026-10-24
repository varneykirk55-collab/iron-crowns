# HX cavalry clips (pipeline/blender/horse_anim.py)

Baked at 24 fps into `game/assets/vat/hx_<model>_lod{0,1}.{vat,json}` (float32 x,z,-y per vertex per frame).
Rows = start row in the VAT texture (lod0 and lod1 share rows). Loops end where they start; transitions `hz_<a>_<b>` start on phase 0 of gait A and land on phase 0 of gait B. `v_nom` = ground speed (m/s) at playback 1.0; the game plays gaits at speed / v_nom, so stance hooves do not slide.

Aliases kept for the legacy names: `idle`, `walk`, `run`, `melee`, `fire`, `die`.

## med_knight (697 frames, lod0 1548 verts / 2598 tris, lod1 905 verts / 1421 tris)

| clip | rows | frames | loop | v_nom | max reach err (m) | content |
|---|---|---|---|---|---|---|
| hz_stand | 0-95 | 96 | yes |  | 0.0 | idle: breathing, head bob/turn, weight shift, tail swish (rider at rest) |
| hz_walk | 96-121 | 26 | yes | 1.1 | 0.0 | four-beat walk (LH-LF-RH-RF), head nod |
| hz_trot | 122-138 | 17 | yes | 2.2 | 0.0 | diagonal trot with suspension bounce, rider rising |
| hz_canter | 139-152 | 14 | yes | 4.0 | 0.0 | three-beat canter, back extension/compression + pitch |
| hz_gallop | 153-164 | 12 | yes | 6.0 | 0.0 | four-beat gallop with suspension, full extension |
| hz_charge | 165-176 | 12 | yes | 6.0 | 0.0 | gallop at the charge: lance couched / sabre forward, rider forward seat |
| hz_idle_walk | 177-202 | 26 | no | 0.55 | 0.0 | transition |
| hz_walk_idle | 203-228 | 26 | no | 0.55 | 0.0 | transition |
| hz_walk_trot | 229-249 | 21 | no | 1.65 | 0.0 | transition |
| hz_trot_walk | 250-270 | 21 | no | 1.65 | 0.0 | transition |
| hz_trot_canter | 271-285 | 15 | no | 3.1 | 0.0 | transition |
| hz_canter_trot | 286-300 | 15 | no | 3.1 | 0.0 | transition |
| hz_canter_gallop | 301-313 | 13 | no | 5.0 | 0.0 | transition |
| hz_gallop_canter | 314-326 | 13 | no | 5.0 | 0.0 | transition |
| hz_gallop_charge | 327-338 | 12 | no | 6.0 | 0.0 | transition |
| hz_charge_gallop | 339-350 | 12 | no | 6.0 | 0.0 | transition |
| hz_melee_ready | 351-398 | 48 | yes |  | 0.0 | stopped at the ready, weapon up, horse shifting |
| hz_draw | 399-434 | 36 | no |  | 0.0 | weapon to the ready on contact (knight: lance to sword) |
| hz_ready_idle | 435-462 | 28 | no |  | 0.0 | weapon back to rest after combat |
| hz_strike_a | 463-498 | 36 | no |  | 0.0 | cut: prep / strike / follow-through / recovery, horse lunges |
| hz_strike_b | 499-534 | 36 | no |  | 0.0 | second strike (hussar: thrust; knight/cuirassier: backhand) |
| hz_hit | 535-552 | 18 | no |  | 0.0 | hit reaction: rider flinches, horse shies |
| cv_die_a | 553-600 | 48 | no |  | 0.0 | horse stumbles, buckles at the front knees and rolls onto its side; rider thrown forward |
| cv_die_b | 601-648 | 48 | no |  | 0.0 | horse rears, sinks on the hocks and rolls the other way; rider slides off behind |
| cv_die_c | 649-696 | 48 | no |  | 0.0 | hindquarters give way, horse collapses sideways; rider falls to the side |

## c19_hussar (673 frames, lod0 1412 verts / 2395 tris, lod1 856 verts / 1360 tris)

| clip | rows | frames | loop | v_nom | max reach err (m) | content |
|---|---|---|---|---|---|---|
| hz_stand | 0-95 | 96 | yes |  | 0.0 | idle: breathing, head bob/turn, weight shift, tail swish (rider at rest) |
| hz_walk | 96-121 | 26 | yes | 1.1 | 0.0 | four-beat walk (LH-LF-RH-RF), head nod |
| hz_trot | 122-138 | 17 | yes | 2.2 | 0.0 | diagonal trot with suspension bounce, rider rising |
| hz_canter | 139-152 | 14 | yes | 4.0 | 0.0 | three-beat canter, back extension/compression + pitch |
| hz_gallop | 153-164 | 12 | yes | 6.0 | 0.0 | four-beat gallop with suspension, full extension |
| hz_charge | 165-176 | 12 | yes | 6.0 | 0.0 | gallop at the charge: lance couched / sabre forward, rider forward seat |
| hz_idle_walk | 177-202 | 26 | no | 0.55 | 0.0 | transition |
| hz_walk_idle | 203-228 | 26 | no | 0.55 | 0.0 | transition |
| hz_walk_trot | 229-249 | 21 | no | 1.65 | 0.0 | transition |
| hz_trot_walk | 250-270 | 21 | no | 1.65 | 0.0 | transition |
| hz_trot_canter | 271-285 | 15 | no | 3.1 | 0.0 | transition |
| hz_canter_trot | 286-300 | 15 | no | 3.1 | 0.0 | transition |
| hz_canter_gallop | 301-313 | 13 | no | 5.0 | 0.0 | transition |
| hz_gallop_canter | 314-326 | 13 | no | 5.0 | 0.0 | transition |
| hz_gallop_charge | 327-338 | 12 | no | 6.0 | 0.0 | transition |
| hz_charge_gallop | 339-350 | 12 | no | 6.0 | 0.0 | transition |
| hz_melee_ready | 351-398 | 48 | yes |  | 0.0 | stopped at the ready, weapon up, horse shifting |
| hz_draw | 399-422 | 24 | no |  | 0.0 | weapon to the ready on contact (knight: lance to sword) |
| hz_ready_idle | 423-438 | 16 | no |  | 0.0 | weapon back to rest after combat |
| hz_strike_a | 439-474 | 36 | no |  | 0.0 | cut: prep / strike / follow-through / recovery, horse lunges |
| hz_strike_b | 475-510 | 36 | no |  | 0.0 | second strike (hussar: thrust; knight/cuirassier: backhand) |
| hz_hit | 511-528 | 18 | no |  | 0.0 | hit reaction: rider flinches, horse shies |
| cv_die_a | 529-576 | 48 | no |  | 0.0 | horse stumbles, buckles at the front knees and rolls onto its side; rider thrown forward |
| cv_die_b | 577-624 | 48 | no |  | 0.0 | horse rears, sinks on the hocks and rolls the other way; rider slides off behind |
| cv_die_c | 625-672 | 48 | no |  | 0.0 | hindquarters give way, horse collapses sideways; rider falls to the side |

## em_cuirassier (673 frames, lod0 1387 verts / 2356 tris, lod1 824 verts / 1313 tris)

| clip | rows | frames | loop | v_nom | max reach err (m) | content |
|---|---|---|---|---|---|---|
| hz_stand | 0-95 | 96 | yes |  | 0.0 | idle: breathing, head bob/turn, weight shift, tail swish (rider at rest) |
| hz_walk | 96-121 | 26 | yes | 1.1 | 0.0 | four-beat walk (LH-LF-RH-RF), head nod |
| hz_trot | 122-138 | 17 | yes | 2.2 | 0.0 | diagonal trot with suspension bounce, rider rising |
| hz_canter | 139-152 | 14 | yes | 4.0 | 0.0 | three-beat canter, back extension/compression + pitch |
| hz_gallop | 153-164 | 12 | yes | 6.0 | 0.0 | four-beat gallop with suspension, full extension |
| hz_charge | 165-176 | 12 | yes | 6.0 | 0.0 | gallop at the charge: lance couched / sabre forward, rider forward seat |
| hz_idle_walk | 177-202 | 26 | no | 0.55 | 0.0 | transition |
| hz_walk_idle | 203-228 | 26 | no | 0.55 | 0.0 | transition |
| hz_walk_trot | 229-249 | 21 | no | 1.65 | 0.0 | transition |
| hz_trot_walk | 250-270 | 21 | no | 1.65 | 0.0 | transition |
| hz_trot_canter | 271-285 | 15 | no | 3.1 | 0.0 | transition |
| hz_canter_trot | 286-300 | 15 | no | 3.1 | 0.0 | transition |
| hz_canter_gallop | 301-313 | 13 | no | 5.0 | 0.0 | transition |
| hz_gallop_canter | 314-326 | 13 | no | 5.0 | 0.0 | transition |
| hz_gallop_charge | 327-338 | 12 | no | 6.0 | 0.0 | transition |
| hz_charge_gallop | 339-350 | 12 | no | 6.0 | 0.0 | transition |
| hz_melee_ready | 351-398 | 48 | yes |  | 0.0 | stopped at the ready, weapon up, horse shifting |
| hz_draw | 399-422 | 24 | no |  | 0.0 | weapon to the ready on contact (knight: lance to sword) |
| hz_ready_idle | 423-438 | 16 | no |  | 0.0 | weapon back to rest after combat |
| hz_strike_a | 439-474 | 36 | no |  | 0.0 | cut: prep / strike / follow-through / recovery, horse lunges |
| hz_strike_b | 475-510 | 36 | no |  | 0.0 | second strike (hussar: thrust; knight/cuirassier: backhand) |
| hz_hit | 511-528 | 18 | no |  | 0.0 | hit reaction: rider flinches, horse shies |
| cv_die_a | 529-576 | 48 | no |  | 0.0 | horse stumbles, buckles at the front knees and rolls onto its side; rider thrown forward |
| cv_die_b | 577-624 | 48 | no |  | 0.0 | horse rears, sinks on the hocks and rolls the other way; rider slides off behind |
| cv_die_c | 625-672 | 48 | no |  | 0.0 | hindquarters give way, horse collapses sideways; rider falls to the side |


## Driving (game/scripts/battle/anim_combat.gd `_update_cav`, hz_ path)

* Gait ladder stand / walk / trot / canter / gallop by smoothed per-rider ground speed (up thresholds 0.25 / 1.35 / 2.8 / 5.6 m/s, 0.3 hysteresis, back to the stand below 0.2), `charge` while the sim charges (`r.running`) at gallop speed. One rung per change, switched at the cycle wrap through the `hz_<a>_<b>` clip, so phase is continuous.
* Gait playback = speed / v_nom (clamped 0.7..1.45, gallop/charge 1.6).
* Turn lean = 0.8 * atan(v * yaw_rate / g) (max 0.2 rad) about the hooves; fore-aft accel pitch 0.012 rad per m/s^2 (sits back on a stop); both smoothed, instance transform only.
* Stopped in melee: `hz_draw` once on contact, then `hz_melee_ready` with per-rider strikes (front two ranks, period 2.0-3.8 s, `hz_strike_a` / `hz_strike_b` by hash), `hz_hit` when a file/rank neighbour falls, `hz_ready_idle` when contact ends.
* Death: killed riders play `cv_die_a/b/c` by hash; a regiment the sim takes off the field plays them staggered (unchanged v1 rule).
* No BattleView.rng draws added or reordered (the legacy dust draw is the only one, same condition and order).
