# PROTO V2 progress (resume from the first unchecked item)
- [x] 0 clone /workspace/ic_proto from origin/main a3f4f35, branch proto/c19-line-v2, ref sheet in ref/
- [x] 1 survey + docs/char/PROTO_V2.md (incl. Animation interface (Rob))
- [x] 2a body (skin+subsurf+sculpt) pipeline/blender/char_v2.py
- [x] 2b uniform + kit + head + hands
- [x] 2c early Blender stills out/proto/early/
- [x] 2d high-poly bake: normal + AO + slot-id atlas (92c3f98)
- [x] 2e LODs + skinning + VAT bake (weapon_tip in json) (92c3f98; prop-deform fix 654ff93)
- [x] 3 Godot: char_vat_v2 shader, --vx-proto flag (212b534); stills renderer tests/proto_shots.tscn (5766d15), sheet tool tools/proto_sheet.py (b5ec79e)
- [x] 3b Kirk feedback + steering 12:31-12:33 + concept target: shako 1.716-1.866 with red pompom + raised plate; separate collar shell, finer belts;
      face planes (brow, bridge, cheek/jaw, mouth, ears) + painted eyes/stubble/ruddy/sideburns; knuckled grip hands; hi folds/seams/buttons/
      stitching/pack flap; knee gaiters; LOD0 10.7k / mid 1,999 / far 691; re-baked (5ae020a, iterate 997a4c6)
- [x] 4a in-engine stills (2fffbed)
- [x] 4b compare + distance sheets, before/after close-ups (e4509cf, refreshed 997a4c6)
- [x] 4c gameplay MP4 deliverables/proto_v2/proto_v2_gameplay.mp4 (00a4be3)
- [x] 4d bench q0/q1/q2 x3 vs same-build --vx-proto=0 (FRA 1800 battle): docs/char/PROTO_BENCH.md (llvmpipe, shared-box contention noted; same draws, +17k prims, q1 close ~-40%)
- [x] 4e tests 163/163, outcome hash 553cc500... = main; sim hashes = main (SWE1800 417a5300..., USA1914 4679c5a2..., JPN1500 e104d558...)
- [x] 4f push proto/c19-line-v2 (origin, branch only)
- [x] 5a v3 body/head/hands on MakeHuman CC0 base (prep a81a1b7, painted albedo ba3c724); kit, LODs, bake, VAT re-bake (rig/rows/weapon_tip frozen) — v3 kit 6e9941b, LOD0 11,670 / mid 1,998 / far 693
- [x] 5b cloth: folds, wool twill micro-normal, desaturated navy, roughness separation, realistic collar — c8f2e9f
- [x] 5c era-generic system docs/char/CHAR_SYSTEM.md (b5a951c)
- [x] 5d stills (front/side/back/3-4/bust/hand, gameplay distance), compare blocky/c19sr/v2/v3, slow-orbit idle video <20 MB — stills/compare 65b5e49, deliverables/proto_v3/video/proto_v3_idle_orbit.mp4 (24 s, 3.4 MB)

## 2a-2c notes (Oct 23, ~11:50 EDT)
- Body: torso/neck/collar + arms (built spread +-6 cm) + legs/gaiters + shoes, unioned by 5 mm voxel remesh (hi ~92k verts);
  game body = symmetric decimate of the remesh (~3.0k tris). Arms are moved back with a distance-blended field.
  (QuadriFlow refused the remesh as non-manifold; decimate is used instead.)
- Head: parametric (nose, brow ridge, eye sockets, cheekbones, lips, chin, ears); hi 192x144 for the bake, game 18x13.
  Painted eyes/brows/mouth/hair by region (will live in the baked id map).
- Hands: palm + thumb + grouped fingers (game); four separate fingers in the bake source.
- Kit: closed stand collar, lapels, coat tails with turnbacks, two crossbelts projected onto the torso, knapsack + greatcoat roll,
  cartridge box, bayonet scabbard + briquet hilt, shako (bands, peak, brass lozenge plate, cockade, plume), musket + bayonet + sling.
- Early stills (committed copies in deliverables/proto_v2/early/): out/proto/early/{hi,lod0}_{front,side,back,34,bust}.png, sheet early_sheet.png. LOD0 currently 5,139 tris.

## 2d-3 notes (Oct 23, ~12:20 EDT)
- Bake: per-part 'exploded' bake (name-group pid, 4 m x offset) for normal + id; AO baked in place. Cage 0.025, ray 0.06.
  Maps: 2048^2 nrm (a = AO) + id (r slot, g mat, b team) stored as PNG bytes in c19v2_line_{nrm,id}.vtex.
- Low cage: coarse voxel remesh (0.013) of the fused parts + corrective smooth, then joint-preserving decimate (fixed waistcoat folds).
- LODs: near 5,740 / mid 2,000 / far 695 tris; all skinned to char_rig.BONES + unweighted leaf 'weapon_tip' (child of prop).
- Shader: CHAR_NMAP path in char_vat.gdshaderinc; id-slot edges blended bilinearly (4 vmat taps on edge texels only).
- Fix 654ff93: the game rig had prop set non-deforming, so the musket stayed at rest pose in the VAT; prop deforms again.
