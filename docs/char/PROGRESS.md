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
