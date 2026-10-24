# Cavalry integration (Rob) — progress
Branch rob/cavalry-integration = rob/cavalry-animation-overhaul + Bill's frozen horse v3 (origin/agent/horse-visual-overhaul ab70c61, read-only).

## 2026-10-23 21:50 EDT — merge + real-mesh bake
- 2e271f6: merge of ab70c61 (Bill's files untouched).
- bf565a0: pipeline/blender/horse_v3_bake.py (new, Rob) loads horse_v3.blend read-only → horse_anim bake (`--mesh=v3`).
  - Rig check: Bill's armature = HX_BONES (57 bones, max head/tail diff 1.3e-7 m, same parents).
  - med_knight (1300): horse_body + tail + eyes + tack_1300 + barding_1300. Mane (horse_hair part_id 0) is hidden under the crinet. LOD0 5666 v / 10682 tris, LOD1 1572 v / 2701 tris (incl. proxy rider + lance).
  - c19_hussar (1800): horse_body + mane + tail + eyes + tack_1800. LOD0 5965 v / 11122 tris, LOD1 1646 v / 2716 tris (incl. proxy rider).
  - Coat specks: covered hide verts pushed in (1300: 2.2 cm, front curtain 4.5 cm; 1800: 1.4 cm). tools/cav/hx_clip.py (coat outside cloth, all clips, LOD0): knight 68 → 29 vert-clip hits (rest are hind gaskin vs caparison hem in walk/trot), hussar 26 → 0.
  - .vatn per-frame normals + game/shaders/hx_vat.gdshader (new): v3 coats per instance from Bill's COATS (points mask = UVMap.u), smooth shading. Proxy/legacy VATs keep vat.gdshader.
- 4713c8d: merged the lit gait videos from the proxy branch.
