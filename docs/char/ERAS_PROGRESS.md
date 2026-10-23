# Eras v3 — resume checklist (branch proto/eras-v3, from c2220ef)

Brief (Kirk, 2026-10-23 16:27 EDT + 16:28 correction): v3-quality models for all eras on the CHAR_SYSTEM.md base.
Shared across kits: MakeHuman base human (face, eyes, hands, skin textures, ear fix), frozen char_rig bones, VAT rows
0-263, weapon_tip on prop, one 2048 atlas per kit, slot numbering (append-only), material library, budgets LOD0 8-12k /
mid ~2k / far ~700. Garments and gear are built fresh per kit (era-correct cut); only the shell-building code is shared.
No gameplay / sim / AI change; outcome + sim hashes must match main. Hooked behind --vx-proto, unit ids / glb names kept.

## How to build a kit
    V3_KIT=kit_c19_grenadier nohup /workspace/tools/blender/blender -b --python pipeline/blender/char_v2_build.py -- all > /tmp/k.log 2>&1 &
Kit modules (pipeline/blender/kit_*.py) patch char_v2 (body_slot, tails, build_kit, KID, KIT_RULES, CLIP_STYLE ...);
with V3_KIT unset the build is the unchanged c19v2_line.
Stills: `tools/eras_shots.sh <kid> <kit>` -> deliverables/eras_v3/<kit>/.

## Checklist
- [x] infra: kit selector in char_v2_build.py (V3_KIT)
- [x] 1 grenadier (1800)          kid v3_c19_grenadier   unit c19_grenadier   tris 11984 / 1997 / 685
- [ ] 2 artillery crewman (1800)  kid v3_c19_artillery   unit c19_artillery (rammer clips)
- [ ] push + report (after 2 kits)
- [ ] 3 hussar rider (1800)       unit c19_hussar (cavalry rig: see blockers)
- [ ] 4 medieval pikeman (1300)   unit med_spear
- [ ] push + report
- [ ] 5 archer (1300)             unit med_archer
- [ ] 6 medieval cavalry (1300)   unit med_knight
- [ ] push + report
- [ ] 7 musketeer + pikeman (1500) units em_musket / em_pike
- [ ] 8 WWI infantry (1914)       unit c20_rifle (nation helmets)
- [ ] push + report
- [ ] 9 modern infantry (1980)    unit mod_rifle
- [ ] push + report; remove /tmp worktrees

## Log
- 16:59 EDT grenadier done: bearskin (brass plate w/ grenade relief, cords, plume, red top patch + cross), long-tailed habit w/ red
  turnbacks + grenade badges, red fringed epaulettes, sabre-briquet + bayonet frog, cartridge box, knapsack + greatcoat roll, moustache.
  Normals: v3 kits bake OBJECT space and re-express per texel in the runtime shader frame (char_v2_build.shader_frame_nrm);
  removes the uv-seam shards / decimation facets (the line model still uses the Mikk bake and keeps them). Bake cage 0.035 / ray 0.08 for v3.
  Known minor: a few dark flecks on the lower right crossbelt at close zoom; id-map staircase on waistcoat hem at extreme zoom.
