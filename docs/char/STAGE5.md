# Character refinement - stage 5 (real c19 battle integration)
All images live in /workspace/iron-crowns-visual/out/char/ (copied to out/char/ in this workspace, untracked).

## (a) c19 demo battle stills + before/after (`--demo=battle --nation=USA --reinforce=1 --closeup=1`, 1280x720, --fixed-fps 30)
- BEFORE = gs main 0dcaa7b (detached worktree, unmodified): out/char/compare/main_0dcaa7b/*.png
- AFTER  = character-refinement (no debug flags, i.e. exact in-game path): out/char/compare/char/*.png
- side-by-side: out/char/compare/cmp_{overview,top,mid_attacker,mid_defender,engage,melee,result}.png
- close-ups (--vx-closeshots, BEFORE = same build with --vx-char=0, i.e. main's c19 models): out/char/compare/close/*.png,
  out/char/compare/cmp_close_*.png (idle, t6 advance, t12 volley, t18/t24 melee + deaths, both sides)
- The battle state is frame-identical before/after (same casualties, smoke, positions): render-only change.

## (b) MP4s (tools/rec.sh, 1280x720 @30 fps, --fixed-fps 30, quality 2, trimmed to the battle with ffmpeg -ss 7.5, crf 23)
- out/char/char_closecam.mp4 - 36.3 s, 16.1 MB: `--vx-closecam` close orbit on the first infantry regiment, cutting sides every 7 s
  (idle, advance, volleys + reload, deaths, melee, result)
- out/char/char_wide.mp4 - 36.3 s, 11.6 MB: `--vx-widecam=40` elevated orbit, several regiments + hussars + guns fighting
- command: `RES=1280x720 tools/rec.sh char_wide 2400 -- --demo=battle --nation=USA --reinforce=1 --vispass=1 --quality=2 --vx-widecam=40`
