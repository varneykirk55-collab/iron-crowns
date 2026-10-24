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
Stills: `xvfb-run -a -s "-screen 0 1600x1600x24" $G --path game --resolution 1200x1200 res://tests/eras_shots.tscn -- --model=<kid> --old=<old kid> --out=$PWD/deliverables/eras_v3/<kit>`
(add `--zoom=x,z,yaw,dist` for an inspection close-up, zoom.png).

## Checklist
- [x] infra: kit selector in char_v2_build.py (V3_KIT)
- [x] 1 grenadier (1800)          kid v3_c19_grenadier   unit c19_grenadier   tris 11946 / 1996 / 685
- [x] 2 artillery crewman (1800)  kid v3_c19_artillery   unit c19_artillery (rammer clips)   tris 11993 / 1995 / 692
- [x] push + report (after 2 kits): 9076875, tests 163/163, outcome + 3 sim hashes = main
- [x] 5:11 decisions (c): grenadier left fist closed (relaxed v3 fist on the free hand), smooth hem bands on all kits,
      fix_folds for decimation folds; (d) c19v2_line rebaked with the normal-bake fix (eras-v3 + proto/c19-line-v2)
- [~] 3 hussar rider (1800)       kid v3_c19_hussar      unit c19_hussar (existing cavalry rig)   tris 12007 / 1983 / 678  ** HANDED OFF TO ANOTHER BOT (Kirk 19:11), see CAVALRY_HANDOFF.md **
- [x] 4 medieval pikeman (1300)   unit med_spear -> v3_med_pike (kit_med_pike.py): Flemish militia c.1302: quilted team-colour
      gambeson w/ split skirt, belt + strap end, purse, ballock dagger, russet hose, turnshoes, linen coif, kettle hat, ash pike.
      tris 11333 / 1993 / 694. Stills deliverables/eras_v3/pikeman/. Smooth hose leg (kit overrides LEG_PROF, no gaiter step).
- [x] push + report (kits 3-4): c2cda55 + this docs commit; tests 163/163, outcome hash + 3 sim hashes = main
- [~] 6a v3 horse (18:52 decision): smooth semi-realistic horse (muscle forms, head, hooves, mane, tail) on the EXISTING  ** DROPPED here: handed off to another bot (Kirk 19:11) **
      horse bones/anim, shared by hussar + knight; barding is a separate kit layer; rebuild hussar on it
- [ ] 5 archer (1300)             unit med_archer
- [x] 6 medieval cavalry rider (1300) kid v3_med_knight  unit med_knight (kit_med_knight.py; rider only per Kirk 21:01):
      mail hauberk + chausses + coif (ring-row relief), aketon implied, team surcoat with cream chevron and riding slits,
      great helm (slits, breaths, brass cross), heater shield on the left forearm, sword at the left hip, poleyns, prick
      spurs, couched lance + swallowtail pennon (weapon_tip at the lance point), war saddle + team saddle cloth. Seated on
      the existing cavalry rig via v3_rider.py (variant med_knight lance clips, no rig/clip changes). Horse body/mane/tail
      and generic tack = the shared kit-3 horse code unchanged (horses are Bill's; no barding). tris 9399 / 1989 / 686
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
- 17:08 EDT artillery done: French foot artillery (all-blue habit, blue lapels / collar piped red, red cuffs + blue flaps,
  red turnbacks w/ blue grenades, blue breeches + waistcoat via kit pal, short black gaiters, red epaulettes, 1806 bell-top
  shako w/ lozenge plate + crossed cannons, red cords + plume), sabre-briquet crossbelt, small pouch, rammer / sponge (TIP (0,1.70,0)).
  Clip needs in docs/char/ROB_CLIP_REQUESTS.md.
- 17:10 EDT pushed proto/eras-v3 at 9076875 (tests 163/163, outcome 553cc500..., SWE1800/USA1914/JPN1500 sim hashes = main). Next: kit 3 hussar.
- 17:55 EDT (c) fixes: free left hand = v3 relaxed fist (HM.FIST per side, '.L' 0.007); breeches/gaiter edge is now a real
  hem band (v3_parts.hem_band / leg_hems, slot boundary tucked under it) on grenadier + artillery, and every later kit uses
  hem bands for garment edges; fix_folds (char_v2_build) relaxes folded decimation faces (removed the grenadier chest wedge).
  Separate crossbelt group 'beltx' so the two belts bake apart. Residual: a few small grey/blue flecks on the skirt turnbacks
  and crossbelts at close zoom (time-boxed; noted for later).
  (d) c19v2_line rebaked with the shader-frame normal bake (tris 11670 / 2000 / 693).
- 18:52 EDT hussar committed (2c498f6): v3 rider on the existing cavalry rig (no re-rig): v3 head/hands/skin, fresh dolman
  w/ gold frogging, fur-trimmed pelisse slung on the left shoulder (torso-only weights, 'transfer_torso'), barrel sash,
  shako w/ cords + plume, sabretache, Hungarian boots, tooth-band (geometric) shabraque edge + sheepskin, valise, ring bit.
  Cavalry-rig constraints: rider torso squashed ~8% by the rig proportions, no rider hand/leg bones (hands rigid on the
  forearm bones, legs rigid on the body), elbow bends ~140deg under LBS, sabre axis a compromise, no carbine clip.
  Horse still the legacy low-poly mesh -> Kirk 18:52: build a v3 horse before kit 6 (after kit 4 push).
- 19:xx kit 4 pikeman done (11333 tris). Clips: uses the musket style (shoulder / port / charge thrust); fire clip unsuitable,
  pike clips requested in ROB_CLIP_REQUESTS. Hussar committed at 12007 tris (7 over); it gets rebuilt on the v3 horse anyway.
- 19:11 Kirk: all horse / cavalry work handed off to another bot (kits 3, 6, 6a). Handoff snapshot + docs/char/CAVALRY_HANDOFF.md,
  copy in /workspace/handoff/iron-crowns-cavalry-v3/. Continuing infantry only: kits 4, 5, 7, 8, 9.
