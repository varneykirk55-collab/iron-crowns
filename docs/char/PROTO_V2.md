# PROTO V2: c19 line infantry, sculpted-geometry prototype (branch proto/c19-line-v2)

Kirk brief, 23 Oct 2026, 11:32 AM EDT: soldiers must read as properly modelled people in their geometry, not only their textures.
Prototype scope: **one** 1800 French line fusilier (the c19_line model id). The other eras and kits stay untouched until Kirk approves.
Reference sheet: `ref/kirk_reference_sheet.png` (1800 column).

## Survey (main @ a3f4f35, v0.4.0)
- Current c19sr_* models come from `pipeline/blender/char_body.py` / `char_geo.py`. Each body part is a separate lofted tube or ellipsoid
  (arms and legs are separate tubes stuck into the torso, an 11-ring super-ellipse torso, a 14x10 ellipsoid head, box-ish hands),
  which is why they read as tube-built. The palette slot is per face in UV.x ((slot+0.5)/32), the material class is in UV.y, the VAT
  vertex id is in UV2.x and the team mask in UV2.y. There are no texture UVs.
- Rig: `char_rig.BONES` (22 bones incl. prop). Clips: `char_anim.CLIPS` = idle 96, walk 24, run 16, fire 48, melee 20, die 30, die_b 30
  (rows 0-263, 24 fps). The VAT is a float32 RGB .vat plus an RGBA8 .vatn normal file, rows = frames and columns = vertices.
- The LOD0 asset holds three vertex sets [near | mid | far] (json near_verts / mid_verts); char_vat.gdshaderinc picks one per instance
  by distance (char_lod / char_mid). LOD1 asset = far set only, drawn with char_vat_lod1.gdshader.
- battle_visuals.gd `_swap_char` swaps vat[id] in place for c19_line / c19_grenadier / c19_artillery (CHAR_MODEL).
  `_char_materials` builds a ShaderMaterial per multimesh with the per-side nation palette and team tint.

## Plan
1. **New body (pipeline/blender/char_v2.py)**: one continuous, watertight body built with Blender's Skin modifier plus Subdivision
   (no separate limb tubes), then shaped procedurally ("sculpt" offsets for the chest, shoulders/deltoids, shoulder blades, buttocks,
   calves, knees and elbows). The arms and legs come out of the torso as one surface, with extra edge loops at the shoulders, elbows,
   knees and hips. Modelled hands have a thumb and grouped fingers curled to grip. The head has a nose, brow, cheekbones, jaw, chin
   and ears, plus painted eyes and brows (palette slots).
   Clothing is modelled over the body: a coat with lapels, turnbacks and tails, collar, cuffs, thick crossbelts, gaiters with a
   button strip, shoes, a shako with peak, plate, cords and plume, a knapsack with rolled greatcoat, a cartridge box, and a musket
   with bayonet.
2. **Normal map plus AO**: a high-poly copy (one extra subdivision plus cloth folds and seams as displacement) is baked with Cycles
   onto the game mesh into one 1024^2 atlas (`c19v2_line_nrm.png`: RGB = tangent-space normal, A = AO).
   Atlas UVs go in a third UV set, which Godot imports as CUSTOM0 (verified on 4.7.2). The palette slot and material class
   stay per face in UV, so all 47 nation palettes keep working unchanged. The shader builds the tangent frame from screen-space
   derivatives (cotangent frame), so the VAT normals need no baked tangents.
3. **LODs**: LOD0 ~5-7k tris, mid ~2k and far ~600-800, made by Decimate from the same skinned mesh, so all sets keep the same
   weights and bones and the clips bake once. The far set skips the normal map.
4. **VAT bake**: the same rig, clips, rows, json keys and 3-set layout, as `c19v2_line_lod{0,1}.{vat,vatn,json}` plus
   `soldier_c19v2_line_lod{0,1}.glb` and `c19v2_line_nrm.png`.
5. **Godot**: `--vx-proto=1` (default **0** on this branch until Kirk approves) maps c19_line -> c19v2_line in `_swap_char`, and uses
   `char_vat_v2.gdshader` (char_vat.gdshaderinc + `CHAR_NMAP`). Grenadiers, artillery and officers stay c19sr. Render-only.
6. **Deliverables in out/proto/**: Blender and in-engine turntables, gameplay-distance views, compares vs c19sr and v0.2.1 blocky,
   an MP4 under 20 MB, tri counts, a q0/q1/q2 FPS bench (3 runs, medians vs same-build --vx-proto=0), tests plus outcome hash plus sim hashes.

## Animation interface (Rob)
Agreed with Rob (his branch is proto/anim-combat-v1 in /workspace/ic_anim; we don't touch it):
- `char_rig.BONES` names, parenting and rest pose are unchanged. Only leaf helper bones may be added.
- VAT layout unchanged; clip rows 0-263 (idle, walk, run, fire, melee, die, die_b) stay in this order. Rob appends `pk_*` / `mk_*` clips
  after row 264 through `pipeline/blender/char_anim_combat.py` (it appends to `char_anim.CLIPS`). The v2 bake iterates over
  `char_anim.CLIPS`, so appended clips are baked automatically.
- Leaf bone `weapon_tip` (child of `prop`, unweighted, at the bayonet tip, prop-local (0.02, 1.52, -0.006)) is on every LOD. Its per-frame
  position (Godot coordinates, same space as the VAT) is written into the VAT json as `weapon_tip: {clip: [[x,y,z], ...]}`.
- All LOD sets are skinned to the same bones (the mid and far sets are decimated copies that keep the LOD0 weights), so the clips bake once.

## As built (Oct 23, after Kirk's feedback + concept target ref/c19_line_target_concept.jpg)
- **Tris**: near (LOD0) ~10.7k, mid 1,999, far 691 (mid/far only past 20 m). Rebuild: `blender -b --python pipeline/blender/char_v2_build.py -- all`
  (~10 min; run it in the background with nohup).
- **Maps** (2048^2, stored as PNG bytes in `game/assets/vat/c19v2_line_{nrm,id}.vtex`, referenced from the lod0 json `maps` key):
  - `nrm`: RGB tangent normal (high-poly folds/seams/buttons/plate + bump-baked wool twill, fibre, leather grain, belt stitching),
    A = AO (hands moved out of the way while baking, so they don't stain the thighs).
  - `id`: r = slot * 8; **g = material * 16 + detail nibble** (skin: < 8 stubble/shadow, > 8 ruddy lips/cheeks/nose/ears;
    eye slot: 0 iris .. 15 sclera; brass/steel/leather: edge wear); **b = luminance detail** (128 neutral; wool fibre noise, worn leather,
    skin tone). Team colour = slot 0 (coat). The palette stays per nation, the detail only modulates it.
- The head and face get 3.4x and the hands 2.4x atlas density.
- **Export gap (for Rob/Kirk)**: export_presets.cfg include_filter only lists `*.vat`; `*.vatn` / `*.vtex` must be added before a
  packaged build can use v2 (the editor / --path runs are fine).
- Close-up tooling: `tools/hand_pos.py c19v2_line idle` -> `--hr/--hl`, then `tests/proto_shots.tscn -- --close=1 --tag=X`;
  `tools/beforeafter_sheet.py` builds the sheet.
- The idle / walk pose holds the musket shouldered in the left hand (Rob's animation). A concept-style order-arms pose would need a clip change.
