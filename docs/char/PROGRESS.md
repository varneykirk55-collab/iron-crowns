# PROGRESS (character refinement)  -- resume from the first unchecked stage
Branch character-refinement in /workspace/ic_rebase (base visual-pass-polish 5adecc2).
- [x] 1 survey + plan (docs/char/PLAN.md, 48586ae); baseline bench q0/q1/q2 -> out/char/before/qQ/perf.csv
- [x] 2 body + skeleton + kits (line/grenadier/artillery/officer) + musket: pipeline/blender/char_{geo,body,rig,anim,build}.py (ff288bf)
- [x] 3 clips + bake (fbdf457 code, 7cc07cf binaries); shader/swap/footslide 231d59e: `blender -b --python pipeline/blender/char_build.py -- bake`
      -> game/assets/models/soldier_c19sr_<kit>_lod{0,1}.glb, game/assets/vat/c19sr_<kit>_lod{0,1}.{json,vat,vatn}, blend/soldier_c19sr_<kit>.blend
      clips idle96 walk24 run16 fire48 melee20 die30 die_b30 (rows 0..263), max IK reach 1.005
      231d59e: game/shaders/char_vat.gdshader (palette, vatn normals, die_b, crossfade via inst COLOR), battle_visuals _swap_char/_char_materials,
      NATION_UNIFORM (16 nations + derived fallback), pipeline/blender/char_footslide.py (walk mean 0.07 m/s vs old 1.43), --vx-closeshots
- [x] 3b rebased onto gs main 0dcaa7b (clean, no conflicts; commits d79bf63 3d6a121 b2a70fa d94d522 13678d8), 3ba8853 in-place swap (keeps model ids for main's polish test) -> 140/140, hash 0e814dda OK (out/hash.sh recreated)
- [x] 3c EARLY 1109334: out/char/turn/line_turntable_sheet.png, line_pose_sheet.png, line_bust_*.png (docs/char/EARLY_LOOK.md)
- NOTE v0.3 main.gd no longer adds the BattleVisuals debug node for --perflog/--bench/--vispass -> PREVIEW-ONLY hook commit needed for bench/closeshots
- [x] 4 nation palettes 4e984e0: NATION_UNIFORM all 47 majors + derived fallback for minors; pipeline/blender/char_nations.py -> out/char/nations/nations_{line,grenadier}.png
- [x] 4b 6e0efe7 PREVIEW-ONLY main.gd debug hook; 4f5b1d6 BattleVisuals.xfade (per-soldier clip crossfade 0.25 s, shader uses elapsed time in COLOR.b);
      5c14c8c PREVIEW-ONLY battle_view hook (_put colour arg + xfade call); 029261b --vx-closecam (MP4 camera)
- [x] 5a stills + compares vs main 0dcaa7b -> out/char/compare/cmp_*.png (docs/char/STAGE5.md); 539bc39 --vx-widecam
- [x] 5b MP4s out/char/char_closecam.mp4 (16.1 MB), char_wide.mp4 (11.6 MB)
- [x] 5c after-bench q0/q1/q2 (2 runs each + same-build ctl --vx-char=0) -> out/char/BENCH_AFTER.md, docs/char/BENCH_AFTER.md
- [x] 5 integration (battle_visuals c19 swap) + demo shots/mp4 + after bench
- [x] 6 bed31c8: tests 140/140, hash 0e814dda OK (HEAD and clean 0dcaa7b+patch+tarball); out/character-refinement.patch, out/character-refinement-binaries.tar.gz, out/character-refinement-PREVIEW-ONLY-hooks.patch, out/INTEGRATION.md (Requests 1-4). DONE.
Tris LOD0/LOD1: line 3034/1112, gren 3238/1186, art 2742/1080, off 2464/940.
Debug: poses sheet `-- poses c19sr_line idle,walk,...` -> /workspace/iron-crowns-visual/out/char/turn/
Notes: out/INTEGRATION.md + hash.sh lost on box restore ~23:33 EDT; recreate.
- [ ] 7 PERF RECOVERY (target within ~10% of ctl at q0/q1/q2; started 02:49 EDT Oct 23)
  - [x] 7a 4a0e2da lean LOD1 (char_body LODS[1].lean): tris LOD1 line 749, gren 781, art 703, off 596 (was 1112/1186/1080/940); LOD0 unchanged. preview out/char/stage7/turn/*_lod1.png
  - [x] 7a2 40e25d9 LOD1 lean pass 2: line 581, gren 629, art 573, off 512 tris (verts 432/478/409/352)
  - [x] 7b ba6e55f shader: char_vat.gdshaderinc + char_vat_lod1 (NRM1 one normal fetch, NOXF no xfade fetch, VPAL per-vertex palette).
        Profile q1 (out/char/stage7/prof): shader variants and xfade CPU ~noise (<=9% wide only); --vx-lod=0 (all LOD1) -> close/mid = ctl.
        => cost is LOD0 instances (3034 tris vs old 700) -> 7c LOD distance
  - [x] 7c af27f2f per-tier character LOD switch: QUALITY char_lod 20/30/45 m (q0<q1<q2, scaled from LOD 45/75/120; MSAA/shadow tiers unchanged).
        BattleView LOD_DIST must stay 45/75/120 (test_visuals_hook pins it), so the LOD0 asset now stores near (LOD0) + far (LOD1) sets
        (line 2513 verts = 2081 + 432) and char_vat.gdshader collapses the other set per instance by camera distance. --vx-charlod=<m> debug.
        Tests 140/140, hash 0e814dda.
  - [x] 7d
        - [x] bench 18/18 -> BENCH_AFTER.md stage 7 (1bf03a3): med-fps vs ctl q0 +2..+20%, q1 -8..+5%, q2 wide -2 mid -11 close -22 close_def -14
        - [x] tests 140/140, hash 0e814dda (HEAD 1bf03a3, out/tests_7d.log)
        - [x] packages regenerated (out/character-refinement.patch, -binaries.tar.gz, -PREVIEW-ONLY-hooks.patch); clean 0dcaa7b + patch + tarball: 140/140, hash 0e814dda; INTEGRATION updated (a227dde)
        - [x] close compare q1 before/after (13 shots incl. a_t12_lod1 at 34 m = LOD1 set): out/char/stage7/close/cmp/cmp_*.png, raw before/ after/
        Stage 7 result: q0/q1 within 10% of ctl at every view; q2 close -22 / close_def -14 / mid -11 (q2 keeps LOD0 to 45 m; options in BENCH_AFTER/INTEGRATION, not taken).
- [x] 8 REBASE onto gs main@v0.3.1 (5bffeb0, tag obj ce4351c; 23 Oct ~05:16 EDT): `git rebase v0.3.1` 31/31 commits, NO conflicts (v0.3.1 only touches map terrain/world_map/map.gdshader/map tests/docs; zero file overlap).
      backup branch backup/character-refinement-pre-v031 = 7da7641. PREVIEW-ONLY hooks now cabb42b (main.gd, was 6e0efe7) and 41eb3e1 (battle_view, was 5c14c8c).
      godot --import + tests on rebased HEAD: 140/140, hash 0e814dda, 0 shader errors (out/tests_v031.log).
      packages vs v0.3.1 (out/pkg_v031.sh, verify out/verify_v031.sh): patch 36 files, tarball 28 binaries, hooks patch; clean v0.3.1 + patch + tarball: 140/140, hash 0e814dda, 0 shader errors (out/tests_v031_clean.log).
      INTEGRATION: base v0.3.1, q2 option note (A: q2 char_lod 30 m / B: mid LOD ~1.2-1.5k; Kirk's call), Requests 1-4 with rebased shas. COLLAB entry: Kirk adds it (we do not write to grand_strategy).
- [ ] 9 FOLLOW-UP on d93f576 (handed to Rob at d93f576; started 05:19 EDT Oct 23; new commits on top, no grand_strategy writes)
  - [x] 9a dd6157f option B mid LOD: char_body LODS[2] (torso 8, limb/leg 6, no feat/detail); LOD0 asset stores LOD0 | mid | LOD1 sets
        (json mid_verts, tris_mid/tris_far); shader 3-band split by distance. Tris LOD0/mid/LOD1: line 3034/1368/581, gren 3238/1470/629,
        art 2742/1352/573, off 2464/1198/512 (line verts 3378 = 2081 + 865 + 432). QUALITY q2 char_lod 20 / char_mid 45; q0 20/20, q1 30/30 (no mid band); LOD_DIST 45/75/120 untouched.
  - [x] 9b coat lift on mid + far sets and LOD1 material (CHAR_FAR): coat slots (m==1, slot<=4) scaled toward palette luminance 0.28 (palette texelFetch is sRGB-coded on GL Compat), gain cap 2.0; LOD0 set unchanged.
        A/B a_idle_mid all-far (--vx-charlod=1, q1): coat blue mean RGB ctl(old) 60/95/167, lift0 38/56/103, lift 52/78/142. Debug --vx-coatlift=<0..1>.
  (stage 9 superseded by the v0.3.2 rebase below; the 4/18-run stage 9 bench on the old base was stopped, out/char/stage9/bench is partial)
- [x] 9R REBASE onto gs main@v0.3.2 (21bbfe1; Rob merged d93f576 + his own R1 sr-xfade in _put and R2 debug node): new branch
      character-refinement-2 from v0.3.2; PREVIEW-ONLY hook commits dropped (obsolete). 9a -> 5ebe944 (binaries re-baked), 9b -> b6c0989.
      Backup: branch character-refinement (b3a9531) and backup/character-refinement-pre-v031 kept.
- [ ] 10 TEAM READABILITY (Rob's v0.3.2 COLLAB request: 1800 NOR light blue vs SWE navy, white kit on snow, unreadable at mid/top)
  - [x] 10a dccd3aa: distance team tint in char_vat (UV2.y team mask + coat slots): 25 -> 90 m coats to team_tint 0.85, trousers / belts /
        shako / plume / knapsack / roll / cartbox / fur to 0.75; overhead range 90 -> 200 m everything but skin towards 0.95 (rest x0.7);
        team colour = BattleView side colour (HUD / banner), luma-normalised to 0.32 (reads on snow and grass). LOD0 close-ups (<25 m) stay historical.
        _side_palettes clash pick: when coats are closer than 0.22 it recolours the side whose coat is furthest from its own side colour
        (1800: NOR -> red, historically plausible Dano-Norwegian red; was: SWE shifted, both still blue). SWE coat lightened 2a3d6e -> 3a5a9a.
        Optional (d): OFFICER_MODEL "c19_officer" + officer_vat() (sr_vat refactor) for Rob's R3; xfade_crew(v,k,q,...) for gun crews. Debug --vx-teamtint=<0..1>.
  - [x] 10b: tint colour + weights computed per instance in vertex() (no per-fragment pow). A/B 1800SWE q2, 3 runs med-fps
        (out/char/stage10/bench_b): mid after 3.23 / notint 3.21 / v0.3.2 3.46; top 3.69 / 3.67 / 3.75 -> tint cost ~0.
        Tests 140/140, hash 0e814dda, SIMHASH SWE f7255ebb USA 45cf5510 JPN 9bb2394d, 0 shader errors (out/tests_10b.log, out/simhash_10b.log).
  - [x] 10f compares (Rob's battle_shots harness, 1600x900, q1, views close/close_def/mid/top; before = clean v0.3.2 /tmp/ic_v032, after = 2a6f12a):
        /workspace/iron-crowns-visual/out/char/stage10/teams/{before,after}/ raw, compare/: sheet_1800SWE_q1.png (as Rob's sheet), sheet_USA_q1.png,
        *_before_after.png per view, crop_1800SWE_q1_{close,close_def,mid,top}.png. Mid: NOR red vs SWE blue (was light blue vs navy-white);
        top: blue vs red lines; close_def: lighter SWE blue, LOD0 uniforms historical. USA/CAN unchanged at close, slightly more saturated at mid/top.
  - [x] 10g q2 bench vs same-build ctl (--vx-char=0), battle_shots, 3 runs, medians (docs/char/BENCH_AFTER.md "Stage 10"):
        1800SWE close -16 / close_def -13 / mid -1 / top -5 %; USA close -16 / close_def -18 / mid -10 / top -1 %.
  - [x] 10h packages vs v0.3.2 (out/pkg_v032.sh): out/character-refinement-2.patch + out/character-refinement-2-binaries.tar.gz (16 binaries; no hooks patch).
        Clean v0.3.2 + patch + tarball (out/verify_v032.sh -> out/verify_v032.log): apply OK, tree == branch HEAD, 140/140, hash 0e814dda,
        SIMHASH SWE f7255ebb USA 45cf5510 JPN 9bb2394d, 0 shader errors. INTEGRATION updated (R3 officer via OFFICER_MODEL / officer_vat, crew xfade_crew, q2 mid LOD).
        COLLAB entry: Rob / Kirk add it (we do not write to grand_strategy).
