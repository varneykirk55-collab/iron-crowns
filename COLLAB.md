# Iron Crowns — Collaboration Guide

## People and workspaces
| Role | Who | Workspace | Branch |
|---|---|---|---|
| Lead developer (gameplay, sim, UI, input, save/load, tests, battle camera, merges) | Lead bot | `/workspace/ironcrowns-lead` (git worktree of `/workspace/grand_strategy`) | `lead-dev` |
| Graphics specialist (models, uniforms, textures/materials, lighting/shadows, contrast, AA, map army markers) | **BJORN** | `/workspace/iron-crowns-visual` (his own isolated snapshot + own git, branch `visual-pass`) | merged into `graphics` here |

- `/workspace/grand_strategy` on branch **`main`** is the playable build. Only merge into `main` after the test suite passes.
- v0.1 is tagged `v0.1`. A verified backup lives in `/workspace/backups/ironcrowns-v0.1-20261022-1905/`; nobody touches it.
- The lead never edits BJORN's workspace. BJORN never edits `/workspace/grand_strategy` or `/workspace/ironcrowns-lead` directly.

## File ownership
| Area | Owner |
|---|---|
| `pipeline/blender/**`, `blend/**`, `game/assets/**`, `game/shaders/**` | Graphics (BJORN) |
| Lighting / environment resources (WorldEnvironment, sun, sky, fog, AA/quality *visual* settings) | Graphics |
| `game/scripts/battle/battle_visuals.gd` (new, optional code hooks for materials/meshes/effects) | Graphics |
| `game/scripts/core/**`, `game/scripts/ui/**`, `game/scripts/main.gd`, input (InputMap in `project.godot`), save/load, `game/tests/**`, battle camera | Lead |
| `game/scripts/battle/battle_view.gd`, `game/scripts/map/world_map.gd` | **Shared-risk**: lead edits camera/input/logic. Graphics requests material/mesh changes via `battle_visuals.gd` hooks or a note under *Requests* below rather than editing these files directly. |
| `game/data/*.json` | Lead (graphics may request new fields, e.g. model/material ids) |

## Asset contract (do not break without a documented migration)
- Keep the glb file names in `game/assets/models/` and their node structure (one mesh per unit type, LOD meshes as currently named).
- Keep the VAT (vertex animation texture) layout in `game/assets/vat/` (rows = frames, columns = vertices; same animation clip order and frame counts).
- Team colour mask lives in **UV2.y** (1 = team-coloured, 0 = not). Keep it.
- Unit ids in `game/data/units.json` are the keys battle/sim code uses; keep them and their `model` field values.
- MultiMesh quirks: `use_colors = true` with white instance colours is needed for vertex colours; buffer stride 16 floats (20 with custom data). glTF materials are overridden in code (`battle_view.gd`), so new materials should be exposed via `battle_visuals.gd`.
- If a change needs a migration (renamed glb, new VAT layout…), describe it in the Handoff entry: old → new, and which code must change.

## Handoff process
1. BJORN works in his workspace, then delivers a patch/branch that applies to `graphics` (based on `main` at tag `v0.1` or later).
2. He adds a **READY** entry below: date, commit/patch path, what changed, files touched, how he verified, screenshots.
3. Lead reviews, applies to `graphics`, merges into `lead-dev`, runs tests + demos, then merges to `main` and marks the entry **MERGED** (or **BLOCKED** with a reason).

## How to run things (from a checkout root, e.g. `/workspace/ironcrowns-lead`)
- Godot binary: `/workspace/grand_strategy/tools/godot` (4.7.2; symlinked as `tools/godot` in worktrees; not in git).
- First time in a new checkout: `tools/godot --headless --path game --import` (builds `.godot/`).
- Compile check: `python3 tools/fix_infer.py res://scenes/main.tscn`
- Tests: `tools/godot --headless --path game res://tests/test_runner.tscn` → results in `user://test_results.json` (copied to `test_results.txt`). Must be all-pass before merging to main.
- Demos (screenshots into `shots/`):
  `xvfb-run -a -s "-screen 0 1600x900x24" tools/godot --path game --resolution 1600x900 --fixed-fps 10 -- --demo=<menu|campaign|diplomacy|era|battle> --nation=<USA|SWE|JPN> [--reinforce=1] [--closeup] [--shots=/abs/dir]`
- Video: add `--fixed-fps 30 --write-movie /ABSOLUTE/path.avi`, then `ffmpeg -i x.avi -c:v libx264 -crf 24 -pix_fmt yuv420p x.mp4`. `tools/record_all.sh campaign diplomacy era battle` does all four.
- Renderer: GL Compatibility. The box has no GPU (llvmpipe), so fps numbers are software-rendering numbers.

## Requests (graphics → lead or lead → graphics)
- (none yet)

## Handoffs
- (none yet)
