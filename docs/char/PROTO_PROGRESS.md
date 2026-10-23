# PROTO V2 progress (resume from the first unchecked item)
- [x] 0 clone /workspace/ic_proto from origin/main a3f4f35, branch proto/c19-line-v2, ref sheet in ref/
- [x] 1 survey + docs/char/PROTO_V2.md (incl. Animation interface (Rob))
- [x] 2a body (skin+subsurf+sculpt) pipeline/blender/char_v2.py
- [x] 2b uniform + kit + head + hands
- [x] 2c early Blender stills out/proto/early/
- [ ] 2d high-poly bake: normal + AO atlas
- [ ] 2e LODs + skinning + VAT bake (weapon_tip in json)
- [ ] 3 Godot: char_vat_v2 shader, --vx-proto flag
- [ ] 4 shots / compares / MP4 / bench / tests+hashes

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
