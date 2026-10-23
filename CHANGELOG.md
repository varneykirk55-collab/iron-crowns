# Changelog

## v0.2 — 2026-10-22 (lead developer pass; BJORN's c19 graphics pass is integrated on lead-dev but not in this build, see COLLAB.md)
### Added
- **Save / load**: full simulation serialization (`Sim.serialize_state/apply_state`, `BattleSim.to_dict/from_dict`), binary saves with
  metadata in `user://saves`, F5 quicksave / F9 quickload, Esc game menu with named slots + saved-games list, Load on the title menu.
  Loading is exact (deep-equality test) and the game continues identically afterwards (180-day determinism test).
- **Cinematic battle camera**: event-driven director (establishing, tracking, flank, low-angle, pursuit, aftermath), 1.25 s smooth blend
  between the cinematic and the overhead rig, C / gamepad Y / HUD button toggle. Read-only on the sim (identical outcome with 27 toggles).
- **Controls**: `Controls` autoload with 37 InputMap actions (keyboard+mouse and gamepad for every gameplay action), gamepad map cursor,
  focus navigation in windows, touch gestures (tap, drag, pinch, twist, long-press). No virtual joysticks. Settings: UI scale, large touch
  targets, touch rotate, quality (Low/Medium/High: MSAA, battle LOD distance, sun shadows), perf overlay.
- **Performance tooling**: F3 overlay (fps, CPU script ms, sim tick, battle sim/units/fx, draw calls, primitives); `--perfout` per-frame JSON;
  `tools/perf_summary.py`; `tests/sim_hash.tscn` determinism fingerprint.
- **Era verification**: `--only=eras` (26 checks over all 5 eras), `BATTLERESULT` JSON summary printed by every battle (units, models,
  projectile classes, melee share, outcome), `tools/rec_eras.sh` + `tools/era_summary.py`; recorded battles for 1300/1500/1800/1914/1980.
- **Scripted gameplay test** `--only=gameplay`: real main scene — start campaign, march an army, declare war, watch a battle in 3D and
  toggle the camera, capture a province, save/load round trip, era advance 1913→1914.

### Changed / fixed
- CPU hotspots (simulation result bit-identical): HUD selection panel rebuilt only on change (116→9 ms per HUD process), monthly economy
  context tables, strength/alliance tables + cheap relation pre-filter in the AI war scan, unit-power memo, relations drift without string
  splitting, map markers stack index O(A) instead of O(A²). Headless frame time: map 20.2→9.3 ms, battle 20.1→7.7 ms; worst day 245→~102 ms.
- Battle camera: the aftermath shot never triggered (subject-less candidate was rejected) — fixed, now orbits the side holding the field.
- `Performance.TIME_PROCESS` replaced with an explicit script-time probe (it over-reported).

### Not done in v0.2
- Android export (no Android SDK / export templates on the build machine).
- BJORN's c19 graphics pass: merged on `graphics` and integrated and tested on `lead-dev`, but kept out of main and these builds until his revised READY (brightness).

## v0.1 — 2026-10-22
- First vertical slice (see `deliverables/` of v0.1 and the backup in `/workspace/backups/ironcrowns-v0.1-20261022-1905/`).
