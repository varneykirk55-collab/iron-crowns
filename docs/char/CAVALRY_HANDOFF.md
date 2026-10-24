# Cavalry v3 handoff (Oct 23 2026, 19:15 EDT)

Kirk's decision (19:11 EDT): all horse and cavalry work moves to another bot. BJORN (the eras-v3 bot) is not
continuing it. This file is the starting point for the next bot.

## What exists
- **Kit 3, 1800 hussar rider: `v3_c19_hussar`** (unit `c19_hussar`, behind `--vx-proto` via `V3_MODEL` in
  `game/scripts/battle/battle_visuals.gd`).
  - v3 base human, fresh hussar garments: dolman, pelisse, shako, sabretache, tooth-band shabraque, sabre, ring bit.
  - Seated on the EXISTING cavalry rig (`pipeline/blender/cavalry.py` bones and clips, unchanged).
  - Tris: LOD0 12007 (7 over the 12k ceiling), mid 1983, far 678.
- **Code**
  - `pipeline/blender/kit_c19_hussar.py`: the kit module.
  - `pipeline/blender/v3_rider.py`: seats the standing v3 human onto the cavalry rig, sets the cavalry weights and
    bakes the cavalry clips into the v3 VAT layout.
  - Rider hooks in `pipeline/blender/char_v2_build.py`: `PID_KEYS`, `AO_AWAY_KEYS`, `HAND_BOX_Y`, `UV_SCALES` and the
    `C.RIDER` bake path (around line 761).
  - Helpers `ribbon` and `surf` in `pipeline/blender/v3_parts.py`.
  - The cavalry/zoom/depth options in `game/tests/eras_shots.gd`.
- **Assets**
  - `blend/soldier_v3_c19_hussar.blend`
  - `game/assets/models/soldier_v3_c19_hussar_lod{0,1}.glb`
  - `game/assets/vat/v3_c19_hussar_*` (vat, vatn, json, alb/nrm/id vtex)
- **Stills:** `deliverables/eras_v3/hussar/`, with front, side, back, 34, close_bust, close_bust_l, close_back,
  cmp_old_new, game_22m and game_22m_cmp.
- **Clip requests for Rob:** the `c19_hussar` section of `docs/char/ROB_CLIP_REQUESTS.md` (carbine prop and clips,
  rider hand bones/pose, an arm rest pose with less elbow bend).
- **No 1300 cavalry work exists.** Kit 6 (`med_knight`) was never started, and there is no v3 horse. `med_knight`
  is not in `V3_MODEL`.

## Branch / SHA
- Branch `proto/eras-v3` on github.com/varneykirk55-collab/iron-crowns.
- Hussar content commits:
  - `9fe775e`: rider hooks
  - `2c498f6`: hussar kit, assets and stills
  - `c85fe7d`: docs
- The handoff snapshot commit is labelled "HANDOFF SNAPSHOT: v3 hussar rider + cavalry-rig work…". Later commits
  on this branch are infantry only.

## Rebuild
```
cd /workspace/ic_proto
V3_KIT=kit_c19_hussar timeout 1500 /workspace/tools/blender/blender -b --python pipeline/blender/char_v2_build.py -- all > /tmp/hus.log 2>&1
grep -n "Error\|tris near" /tmp/hus.log          # ~4-5 min
cd game && /workspace/grand_strategy/tools/godot --headless --path . --import
xvfb-run -a -s "-screen 0 1600x1600x24" /workspace/grand_strategy/tools/godot --path . --resolution 1200x1200 \
  res://tests/eras_shots.tscn -- --model=v3_c19_hussar --old=c19_hussar --out=../deliverables/eras_v3/hussar \
  --h=1.3 --bustz=2.15 --sx=1.4 --sz=3.0 --oldx=-1.6
```
- For a close-up zoom, add `--zoom=x,z,yaw,dist[,depth]`, which writes zoom.png. The horse head uses
  `0,1.65,-50,1.2,-1.1`.
- Run the tests with `godot --headless --path game res://tests/test_runner.tscn`. Expected: 163 PASS. The outcome
  and sim hashes must match main.

## Known issues
- **The horse is still the old low-poly blocky legacy horse.** Next to the smooth v3 rider it clashes (Kirk,
  18:52). Kirk wanted a smooth, semi-realistic v3 horse with muscle forms, head, hooves, mane and tail, at the same
  budgets as the riders, shared by the hussar and the medieval knight, with medieval barding as a separate kit
  layer. None of that has been built.
- LOD0 is 12007 tris, 7 over budget. The lo bit/stirrup loops (`nl` 6 in lo) or the horse share are the places to
  trim.
- The rig has no rider leg or hand bones. The legs ride on `body` and the hands are posed statically (see the
  ROB requests).

## Rules
- **The EXISTING cavalry rig and animation must stay untouched:** `cavalry.py` BONES, Rob's horse and rider bones,
  and all clips. No re-rig.
  - New clips are requested in `docs/char/ROB_CLIP_REQUESTS.md`. Don't animate anything yourself.
- VAT rows 0-263 unchanged, weapon_tip on the prop, one 2048 atlas per kit, slot numbering append-only.
- Keep unit ids and glb names, and keep the kits behind `--vx-proto`.
- No gameplay, sim or AI changes.
- Never push to main.
