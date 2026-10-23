# Character refinement: early look (checkpoint)

Line infantryman `c19sr_line` (French line fusilier, default palette). LOD0 3034 tris / LOD1 1112 tris.
Blender Workbench previews with palette colours, no in-game shader yet. Regenerate them with:
`blender -b --python pipeline/blender/char_build.py -- turn c19sr_line`.

Files are in `/workspace/iron-crowns-visual/out/char/turn/`, with a copy in `/workspace/ic_rebase/out/char/turn/`.

- Turntable sheet: `line_turntable_sheet.png` (front, 3/4, side, back)
  - singles: `line_turn_front.png`, `line_turn_34.png`, `line_turn_side.png`, `line_turn_back.png`
- Close-ups: `line_bust_front.png`, `line_bust_34.png`
- Pose sheet: `line_pose_sheet.png` (idle, aim, fire + recoil, reload: prime, reload: ram, reload: return)
  - singles: `line_pose_*.png`
  - all poses come straight from the baked clips; max reach is 1.0 in every pose (no stretched arms)
