# Horse mesh notes (DRAFT, uncommitted; section 6 records Rob's 19:21 decisions): mesh-side requirements for the v3 horse

Status: draft, branch `agent/horse-visual-overhaul`, base main 41bdd75.
This is NOT a skeleton spec. Rob owns the rig, clips and bake conventions
(HORSE_SKELETON_SPEC.md on `rob/cavalry-animation-overhaul`). This file lists what
the mesh/tack side needs from the rig, and facts about the current rig that matter to it.

## 1. Current rig facts (pipeline/blender/cavalry.py, Bjorn, legacy)
- Axes: Blender +Y forward, +Z up, metres. Bake converts (x,y,z) -> Godot (x, z, -y), so the model front is Godot -Z (ANIM_INTERFACE.md).
- There is one combined armature for horse and rider, 19 bones:
  root, body, neck, head, tail,
  fl/fr/bl/br _up and _lo (2 segments per leg, hoof tip at z 0.05),
  r_spine, r_head, r_arm.L/R, r_fore.L/R.
  There are no rider leg or hand bones, and no saddle, stirrup or rein bones.
- Key heights (Blender z):
  - `body` bone runs from y -0.55 to 0.6 at z 1.30; this is the barrel centre line, not the withers.
  - Body box 0.46 x 1.25 x 0.50 is centred at z 1.30, so the top of the back is about 1.55.
  - Neck base z 1.38 at y 0.60. Poll about 1.85.
  - Saddle top about 1.60.
  - Rider r_spine runs from 1.62 to 1.98, r_head from 2.00 to 2.24.
  - In practice the legacy horse is about 1.55 m at the back/withers. "~1.3" is the body-bone height.
- Skinning is rigid, one bone per box part.
- Horse geometry is copied separately in med_kit.knight, em_kit.cuirassier and c19_kit.hussar. There is no shared horse module.
- Vertex counts (horse + rider): med_knight 583/468, c19_hussar 452/317 (LOD0/LOD1).
  Legacy normals are rest-pose: vat.gdshader has no VAT normals for cavalry.

## 2. Constraints from Rob's combat bake (pipeline/blender/cavalry_anim_combat.py, read-only)
- Rows 0-143 are the legacy clips. Rows 144-569 are appended: hv_* gaits, transitions, and cv_die_a/b/c at rows 426, 474 and 522.
- The script asserts:
  - BASE_FRAMES == 144
  - the vertex count equals the stored json
  - a legacy re-evaluation matches the stored rows to within 1e-4
  
  So the order is always cavalry.py, then cavalry_anim_combat.py.
- IK leg lengths and PIVOT (-0.55, 1.30) are read from cavalry.BONES. Any new skeleton or withers change must go through Rob's code, not ours.
- `rider_leg_verts()` treats any component that meets all of these as a rider leg (it detaches in death clips):
  - weighted to `body`
  - centre |x| = 0.2 +/- 0.02
  - y 0.06..0.295
  - z 1.10..1.66
  
  The new horse, saddle flaps and stirrup leathers must not match this unless they are meant to be rider legs. Better: Rob replaces the heuristic with explicit vertex groups or tags.

## 3. Mesh-side requirements for the new skeleton (asks for Rob)
1. Sockets as bones or empties in the armature, so tack deforms or moves rigidly with them:
   - saddle (seat centre, on the spine)
   - stirrup.L/R (leather hang point plus tread)
   - rein.L/R (bit ring and hand end, or a hand target)
   - bit/bridle (head)
   - breastplate and crupper anchors (chest and tail root)
   - barding anchors (neck, chest, croup)
2. Spine, neck and tail chains: we need smooth multi-bone weights (up to 4 per vertex) across the withers, shoulder/elbow, stifle and the neck base. We will author the weights; the bone placement must match the anatomy, as in section 5.
3. Normals: deforming smooth skin needs baked normals (.vatn plus the char_vat shader path, as used by v3 humans). Rest-pose normals will look wrong. Please confirm the VAT format and shader the horse will use.
4. Vertex budget: VAT size is verts x frames x 12 B.
   - LOD0 at a ~12k-tri ceiling (Kirk) is about 6-7k horse verts. At 570 rows that is about 45 MB per variant per LOD.
   - Please confirm the row count and a vertex budget per LOD.
5. Rider seating: v3 riders are seated with fixed constants (below). The saddle socket height defines where the rider sits. Keep it as one source of truth: rig socket, then rider seat.
6. Layers: horse body, tack (saddle, bridle, reins, stirrups) and barding (caparison and crinet for med_knight) are separate kit layers on one skeleton. The caparison hides the legs, so leg poses can't be checked on the knight.
7. Rider-leg tagging: explicit vertex groups (rider_leg.L/R), not a position heuristic.

## 4. Asset contract (COLLAB.md, unchanged)
- Keep these names, paths and formats:
  - glb names: `cavalry_<vid>_{lod0,lod1,rigged}.glb`
  - VAT paths: `game/assets/vat/<vid>_lod{0,1}.{vat,json}`
  - unit ids: med_knight, em_cuirassier, c19_hussar
  - VAT layout: float32 xyz, rows = frames, cols = verts, 24 fps
- Material class lives in UV.y: mat = (1 - UV.y) * 16. Hide = 8, hair/mane = 11.
- UV2.x holds the vertex id; UV2.y holds the team mask.
- Vertex colour holds albedo.
- The per-instance coat comes from `horse_coat()` in vat.gdshader (bay, chestnut, dark bay, black, grey) and keys off mat 8/11. A new mesh must keep hide and mane on those classes, or have the shader updated with it.
- Sim hashes and the 210/210 tests must stay unchanged.

## 5. Rider heights (v3, proto/eras-v3, measured) and withers
- v3 standing human (char_rig.BONES):
  - hips 0.95, chest 1.26-1.47, neck 1.47-1.575, head bone 1.575-1.77
  - head centre 1.672 (char_v2 HEAD_C)
  - crown about 1.79, so stature is about 1.78-1.80 m
  - top of the kettle hat on the v3_med_pike idle frame is 1.885
  - shako 1.716-1.866
- v3 hussar seated (v3_rider.py), heights above the ground:
  - Z_HIP 1.488, Y_SEAT -0.05
  - torso scaled by K_TORSO 0.92
  - shoulders (+/-0.188, -0.056, 1.925)
  - knee (0.295, 0.22, 1.213)
  - head centre about 2.15; crown about 2.26 (computed: 1.488 + (1.79 - 0.95) x 0.92)
  - top of the shako plume in the idle frame is about 2.62
- Proposed withers 1.50-1.55 m (14.3-15.1 hh) suits a ~1.78 m rider: about 0.85 x stature. It matches period light cavalry and medieval coursers.
  - It is about the same as the legacy back top (~1.55). The rider's seat would therefore stay near the current r_spine 1.62 and v3 Z_HIP 1.488, and the seating constants would not need large changes.
  - Destrier/knight variant: up to ~1.60 if Rob wants a larger horse, but that changes the seat and IK.
- Check: hip 1.488 sits about 0.07 below the legacy back top 1.55. The seat must be authored with the new saddle; the hip joint sits roughly 0.08-0.10 above the seat surface.

## 6. Rob's decisions (2026-10-23 19:21 EDT); these supersede sections 2-3 where they conflict
1. Base branch is main.
2. The horse gets its own armature, separate from the rider. The v3 rider (char_rig) parents to a `rider_seat` socket on the horse.
3. Rob re-bakes everything on the new rig. The old 144-frame path is a legacy fallback only, so:
   - there is no need to match the old vertex counts;
   - the legacy-equality asserts and the `rider_leg_verts()` heuristic no longer constrain the new mesh.
4. Mesh layers stay separate: horse body, tack and barding.
5. Tack is weighted to real bones: `saddle`, `stirrup.L/R` and a rein bone chain. Nothing should detach in death clips.
6. No new rider bones. The rider's existing `hand.L/R` snap to the horse sockets `rein_hand.L/R`. The reins run from `rein_bit` to `rein_hand`.
7. Seat height stays where it is now. The saddle seat must be shaped so the v3 seated hip lands at z = 1.488 m. A hip joint about 0.08-0.10 above the seat surface puts the seat surface at about z 1.39-1.41.

Mesh-side consequences:
- The withers sit at 1.50-1.55. The saddle tree sits on the back behind the withers, and the seat dips below the pommel and cantle.
- The saddle panels must not push the rider's thighs out past KNEE x 0.295.
- Rein geometry: a strip or tube weighted along the rein bone chain, with the bit ring at `rein_bit` and the hand end at `rein_hand.L/R`.
- Stirrup leathers and treads are weighted to `stirrup.L/R`.
- Barding (med_knight caparison and crinet) is its own layer, weighted to the horse body, neck and leg bones.

## 7. Remaining open questions
- Exact socket names and positions, and the bone list: waiting for HORSE_SKELETON_SPEC.md (not pushed as of 19:21 EDT).
- VAT format and normals (.vatn plus char_vat?). Vertex and row budget per LOD.
- How the separate horse and rider VATs are combined at runtime: two MultiMeshes, or one merged bake? This affects battle_view.gd `_vat_model` and the asset contract.
