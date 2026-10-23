# Horse skeleton spec v1 (`hx` rig): the shared contract for the new horse

- Owners:
  - **Rob:** rig behaviour, locomotion, rider sync and cavalry combat animation (`pipeline/blender/horse_rig.py`, `horse_anim.py`, `game/scripts/battle/anim_combat.gd`).
  - **Bill** (horse mesh specialist, branch `agent/horse-visual-overhaul`): horse mesh, tack meshes and materials.
- **Status:** v1 proposal. The bone list below is final unless Bill and Rob agree a change. Neither side renames or reparents a bone on its own. New bones may only be added as **leaf helpers**.
- **Agreed with Bill (2026-10-23):**
  1. Bill builds the mesh on main (`agent/horse-visual-overhaul`). The v3 riders (proto/eras-v3) come in at integration.
  2. The horse has its own armature. The char_rig rider is parented to the `rider_seat` socket.
  3. A new bake pipeline for this rig re-bakes all clips, and the mesh arrives as layers (body, tack, barding). The old 144-frame path is the legacy fallback only.
  4. There are no new rider bones. `rein_hand.L/R` are horse sockets that the rider's `hand.L/R` snap to, and the reins run from `rein_bit` to `rein_hand`.
  - Scale: keep the current horse scale (withers about 1.55 m), with the seated hip at 1.488 m.
- **Source of truth in code:** `pipeline/blender/horse_rig.py` `HX_BONES`. This table mirrors it.
- **Legacy:** the legacy horse (`pipeline/blender/cavalry.py`, 2-segment legs, rows 0–569) stays untouched and is the **fallback**. The new rig lives in new model ids `hx_<variant>`. The runtime uses them only when the switch is on (see section 8).

## 1. Conventions
- **Units and axes:** metres, Blender axes. The horse faces **+Y**, **Z is up**, and **+X is the horse's RIGHT**. This matches `char_rig.py`: `.R` = +X and `.L` = −X.
- **Ground and origin:** the ground is Z = 0, and the `root` origin is on the ground under the barrel centre.
- **Size:** a riding horse of about 15 hands.
  - **Keep the current horse's scale:** withers (skin top) about 1.55 m (the 1.30 m figure in `cavalry.py` is the body bone, not the withers), croup about 1.50 m, poll about 1.86 m with the head carried.
  - The seated rider hip joint is at **1.488 m**, the v3 target (`rider_seat`).
  - Nose to point of buttock ~2.25 m, chest width ~0.42 m.
  - This scale is **presentation only**. The sim's positions, spacing and hitboxes are not touched, and the renderer only places instances.
- **Bones:** roll 0 (Blender roll-0 convention; the rest matrix is derived from head→tail like `char_rig._rest_matrix`). All bones are unconnected, so each pose may carry a translation.
- **Rest pose:** the horse stands square, the legs vertical under the joints, the neck at ~45°, and the tail hanging. The mesh is modelled and skinned in this pose.
- **Export:** the VAT bake writes `(x, z, −y)`, so the model front is **Godot −Z**. This is the same as every other VAT unit.

## 2. Bone hierarchy (head → tail, parent)
| bone | head | tail | parent | notes |
|---|---|---|---|---|
| root | (0,0,0) | (0,0.25,0) | – | ground motion only (never rotated by clips except the death roll) |
| body | (0,0,1.22) | (0,0.30,1.22) | root | centre of mass: bob, surge, pitch and roll of the trunk |
| pelvis | (0,-0.32,1.34) | (0,-0.80,1.30) | body | croup; hind legs and tail hang from it |
| spine_01 | (0,-0.32,1.34) | (0,0.02,1.30) | body | lumbar (loin) |
| spine_02 | (0,0.02,1.30) | (0,0.36,1.34) | spine_01 | thoracic (saddle area) |
| chest | (0,0.36,1.34) | (0,0.66,1.28) | spine_02 | withers (the skin top, 1.55, sits ~0.2 above the bone over the dorsal spines) and forehand; forelegs hang from it |
| neck_01 | (0,0.66,1.28) | (0,0.84,1.52) | chest | neck chain (3) |
| neck_02 | (0,0.84,1.52) | (0,0.97,1.72) | neck_01 | |
| neck_03 | (0,0.97,1.72) | (0,1.05,1.86) | neck_02 | ends at the poll |
| head | (0,1.05,1.86) | (0,1.40,1.44) | neck_03 | poll → muzzle |
| jaw | (0,1.10,1.72) | (0,1.36,1.41) | head | leaf, optional skinning |
| ear.L / ear.R | (∓0.06,1.04,1.89) | (∓0.07,1.02,2.04) | head | leaf |
| tail_01 … tail_05 | (0,-0.80,1.30) → (0,-0.89,1.21) → (0,-0.94,1.08) → (0,-0.97,0.94) → (0,-0.99,0.80) → (0,-1.00,0.63) | | pelvis → chain | tail chain (5). The hair skirt runs to about z 0.45 on tail_05 |
| scapula.R | (0.13,0.44,1.34) | (0.17,0.70,1.06) | chest | shoulder blade (swings with the leg) |
| humerus.R | (0.17,0.70,1.06) | (0.16,0.52,0.84) | scapula.R | point of shoulder → elbow |
| radius.R | (0.16,0.52,0.84) | (0.155,0.54,0.50) | humerus.R | forearm → knee (carpus) |
| cannon_f.R | (0.155,0.54,0.50) | (0.15,0.54,0.23) | radius.R | knee → fetlock |
| fetlock_f.R | (0.15,0.54,0.23) | (0.15,0.60,0.09) | cannon_f.R | **fetlock joint**: pastern (fetlock → coronet) |
| hoof_f.R | (0.15,0.60,0.09) | (0.15,0.68,0.0) | fetlock_f.R | coronet → toe (sole on Z = 0 at rest) |
| femur.R | (0.17,-0.50,1.18) | (0.19,-0.30,0.88) | pelvis | hip joint → stifle |
| tibia.R | (0.19,-0.30,0.88) | (0.16,-0.64,0.54) | femur.R | stifle → hock (gaskin) |
| cannon_h.R | (0.16,-0.64,0.54) | (0.15,-0.62,0.23) | tibia.R | hock → fetlock |
| fetlock_h.R | (0.15,-0.62,0.23) | (0.15,-0.57,0.09) | cannon_h.R | **fetlock joint**: hind pastern |
| hoof_h.R | (0.15,-0.57,0.09) | (0.15,-0.49,0.0) | fetlock_h.R | |
| *.L | mirrored, x → −x | | | the same for every leg bone |

**Sockets** (leaf bones; tack and rider attach here; never skinned to horse flesh):
| socket | head | tail | parent | use |
|---|---|---|---|---|
| saddle | (0,0.12,1.42) | (0,0.32,1.42) | spine_02 | saddle tree, at the lowest point of the seat on top of the pad. Saddle, pad, shabraque and caparison top are skinned here (and to the spine) |
| rider_seat | (0,0.10,1.488) | (0,0.10,1.60) | saddle | **rider hip joint** at the v3 seated hip height of 1.488 m. The rider `hips` head sits on this point (section 4) |
| stirrup.L / .R | (∓0.20,0.16,1.38) | (∓0.27,0.16,0.86) | saddle | stirrup bar → tread. Leathers and iron are skinned here. Per-era leather length is a pose-time Y scale (knight 1.10, long seat; hussar 0.90) |
| rein_bit | (0,1.30,1.44) | (0,1.30,1.52) | head | bit and mouth corner. The rings sit at ±0.07 x |
| bridle | (0,1.06,1.82) | (0,1.12,1.87) | head | headstall, browband, chanfron (knight) |
| rein_hand.L / .R | (∓0.09,0.40,1.66) | (∓0.09,0.50,1.66) | saddle | **horse-armature socket** where the rider's char_rig `hand.L/R` snap (IK target). Clips animate it |
| rein_01..04.L / .R | along rein_bit ring (∓0.07) → rein_hand | | saddle | **rein chain**: 4 bones a side, each about 0.2 m, posed every frame by the bake on the bit → hand line with a slight sag. Rein tack is weighted to these bones |
| lance | (0.12,0.30,1.60) | (0.12,3.30,1.70) | saddle | knight lance (head = grip, +Y = point). Posed every frame to follow the rider's right hand (couched), and dropped in melee. It is a horse-armature helper, so the rider stays pure char_rig |

- **Reins:** they run from the `rein_bit` rings to `rein_hand.*` along the `rein_01..04` chain, and the ends are weighted to rein_bit and rein_hand. This keeps the rein attached at both ends in every clip, because the rider's hand.L/R is snapped onto rein_hand.

## 3. Animation conventions
- **Format:** VAT, 24 fps. `.vat` is rgb float32 positions per vertex per frame (texture width = vertex count, height = rows). Json `clips` entries are `{start, count, loop, v_nom?}`.
- **Clip names:**
  - New rig clips use the prefix **`hz_`**. Death clips keep the names `cv_die_a/b/c`, so the renderer code is shared.
  - The hx VATs also carry the legacy names `idle walk run melee fire die`, as alias rows. These are only used if something reads the hx model without the AC path.
- **Row layout:**
  - Rows are **append-only per model**, and new clips go after the last row.
  - The rows of each clip are identical in every hx model (same names, counts and order), so one table holds for all of them.
- **Gait cycle phase 0** = right hind (`br`) footfall. Every loop starts and ends on it, and transitions join phase 0 to phase 0.
- **Locomotion is ground-truth stride:**
  - Every gait clip stores `v_nom` = 2·A / (duty · T), the speed at which the stance hooves are stationary on the ground.
  - The renderer plays a clip at speed/v_nom, so stride length × cadence matches the instance's ground speed.
- **Stance hooves are IK-planted:**
  - The `hoof_*` sole stays on Z = 0 and its toe does not slide during stance.
  - The fetlock drops (pastern extends) under load.
- **Mesh skinning expectations (Bill):**
  - Use linear blend skinning with at most 4 weights per vertex.
  - Joints should blend over about ±6 cm: elbow, stifle, hock, knee and fetlock.
  - The chest and scapula region blends scapula ↔ chest. The neck blends along neck_01..03.
  - Do not weight flesh to sockets.
- **Bake:**
  - `horse_anim.py` evaluates the poses in Python and skins the vertices with numpy LBS, using the mesh's own vertex groups. This is the same maths as Blender's Armature modifier without preserve volume.
  - A Bill mesh with vertex groups named after these bones therefore bakes with no code change.
- **Per-frame normals:** `.vatn` (rgba8, like c19sr) is **recommended for the final mesh**, because the smooth horse needs it for shading. The proxy bakes positions only (rest normals), the same as the legacy horse.

## 4. Rider
- **Skeleton:** the full infantry `char_rig.py` human skeleton (`root hips spine chest neck head clav.* upper_arm.* forearm.* hand.* thigh.* shin.* foot.* prop`), with **no renames**.
- **Attachment:** it is a separate armature `rider_rig`, parented to the horse bone `rider_seat`.
  - At bind, the rider armature is placed so that `hips.head` = `rider_seat.head`, giving a rider armature offset of (0,0,−0.95) in rider_seat space.
  - The rider's rest stays the standing char_rig rest. "Seated" is a pose, so the base human mesh and its weights are reused unchanged.
- **No new rider bones.** Weapons:
  - `prop` (char_rig, unparented) carries the hand weapon: the hussar's and cuirassier's sabre or broadsword, and the knight's sword. The knight's sword is scaled to 0 on `prop` until it is drawn, and a sheathed sword stays on the hips mesh.
  - The knight's lance is the horse-armature helper `lance` (section 2).
- **Hands:** the rider's `hand.L/R` snap to the horse sockets `rein_hand.L/R`. The weapon hand leaves its socket in combat.
- **Riders at integration:** the v3 riders (proto/eras-v3, BJORN) come in at integration. Until then the bake uses a capsule proxy rider on the same char_rig bones.
- **Driven by the clips:**
  - hips and spine follow the horse with a lag and counter-motion per gait;
  - thighs are on the flanks (abducted 10–14°);
  - the feet (ball of the foot) are IK-pinned on `stirrup.*` treads, with the heel down;
  - the hands are IK-pinned on `rein_hand.*` (left; right when unarmed);
  - the weapon hand holds the weapon steady;
  - the rider leans back on deceleration and forward on acceleration and in the charge.

## 5. Per-variant kit (one rig, many kits)
| model | era | rider | weapon | tack |
|---|---|---|---|---|
| hx_med_knight | 1300 | knight (mail, great helm, surcoat) | `lance` socket / sword on `prop` | war saddle with high cantle, long stirrups, team caparison (skirt cut at the forearm so the gait reads), chanfron |
| hx_c19_hussar | 1800 | hussar (dolman, pelisse, shako) | sabre / – | hussar saddle, sheepskin, shabraque with a pointed tail, shorter stirrups |
| hx_em_cuirassier | 1650 | cuirassier (cuirass, lobster pot) | broadsword / – | troop saddle, holsters |

## 6. Mesh layers, budgets (Bill's mesh) and VAT sizes
- **Mesh delivery:** Bill builds on main (`agent/horse-visual-overhaul`). The mesh comes as **separate layers**:
  - `body`: horse flesh, weighted to horse bones only;
  - `tack`: saddle, stirrups, reins, bridle, weighted to `saddle`, `stirrup.L/R`, `rein_01..04.*`, `rein_bit`, `bridle` and `head`;
  - `barding`: caparison, chanfron, shabraque, weighted to the trunk bones and `saddle`.
  - Bill's notes: `docs/horse_mesh_notes.md` on his branch.
- **Bake:** the new pipeline (`horse_anim.py`) re-bakes **all** clips for the hx rig. It takes any number of layers, each with its own vertex groups (horse bones, sockets and tack bones), plus the rider layer on the rider armature. The legacy 144-frame `cavalry_anim_combat.py` path is kept only as the legacy fallback.
- **Triangles:**
  - horse LOD0 6–8k tris, plus tack 2–3k per era;
  - LOD1 ~2.5k, LOD2 < 1k (LOD2 = far set inside LOD1, like c19sr's near/mid/far);
  - one shared coat material with parameter variants (shader `horse_coat`, class `MAT_HIDE` = 8).
- **VAT size check:**
  - Texture width = Blender vertex count. Keep each VAT ≤ **8192 vertices wide**: GL Compatibility guarantees 8192, and desktop is usually 16384.
  - LOD0 is about 4.5k horse verts + 1.5k tack + about 6k rider. That is over 8k if horse, tack and rider are combined, so the final asset must use **split VATs**:
    - `hx_horse_lod*`: horse flesh, shared by every era;
    - `hx_<variant>_tack_rider_lod*`: tack, rider and weapons.
    - They share the same row table and are drawn as two MultiMeshes with identical instance data (an integration task, Rob).
  - Rows: the current hx clip set is ~900 rows. At float32 that is LOD0 4.5k × 900 × 12 B ≈ 49 MB for the horse and ≈ 81 MB per rider kit. **Recommended:** half-float VATs (RGBH, 6 B), which give ~1 mm precision within ±4 m and halve this. This is a renderer switch on integration.
- The proxy used for development is small (about 4k tris and 2.3k verts total), so it bakes combined.

## 7. Clip table (hx models)
See `docs/cav/HX_CLIPS.md`, which is generated by the bake and lists names, rows, frames, loop, `v_nom` and event times (strike contact frame).

## 8. Runtime switch and fallback
- **On by default:** hx models are used when combat animation v1 is ON **and** the cav-v2 switch is on. The switch defaults to on, with precedence command line > env > setting:
  - `--cav-v2` / `--cav-v2=on`, `--no-cav-v2`;
  - `IRONCROWNS_CAV_V2=0/1`;
  - project setting `iron_crowns/battle/cav_v2`.
- **Fallback:** with anim v1 off, the legacy horse and the legacy loop are used, unchanged. A missing hx asset also falls back to the legacy model.
- **Presentation only:** BattleSim, rng order and outcomes are identical whichever horse is drawn.
