# Changelog

## Unreleased (`audio` branch): music and military audio system
### Added
- **Audio system** (`game/scripts/audio/audio_manager.gd`, autoload `Audio`):
  - Five buses: Master with a limiter; Music (default 0.6, battle track -3 dB trim); SFX (default 0.85) with a gentle compressor (-8 dB, 2.5:1) and limiter; Ambience and UI routed into SFX.
  - Music moods with equal-power crossfades: campaign, tension (war or diplomacy) and battle. Stings for victory, defeat, war declared and new era, which duck the music.
  - Positional battle SFX driven read-only by BattleSim events, with era-correct weapons, per-category voice caps, density gain, distant variants, and ambience, march, melee and engine beds.
  - UI feedback sounds.
  - Music and SFX sliders in Settings, saved to `user://audio.cfg`.
  - `--audio=off` switch, and a synthesized fallback if a file is missing.
- **75 original procedural audio assets** (6.25 MiB Ogg Vorbis, 543 s) plus their generator `pipeline/audio/`, which is deterministic and byte-reproducible. QA lives in `analyze_audio.py`, and `make_preview.py` builds the preview mix. No samples and no AI audio were used. See `AUDIO_LICENSES.md`.
- `game/tests/test_audio.tscn`: 28 checks, including battle SFX vs music balance (SFX p90 must be at least 6 dB above the music median).
### Changed (minimal touches to lead-owned files)
- `game/project.godot`: `Audio` autoload added after `Controls`, plus `[audio] buses/default_bus_layout`.
- `game/scripts/ui/hud.gd`: one line in `build_settings()` adds the audio sliders.
### Verified
- test_audio 28/28; full suite 135/135 on both the baseline (fa2081b) and this branch.
- Sim hashes unchanged: SWE1800 e79839ca…, USA1914 45cf5510…, JPN1500 9bb2394d….
- Battle outcome identical with audio on and off.
### Not verified
- No human listening test (no subjective quality check).
- Exported builds not run with audio.

## v0.2.1 — 2026-10-22 (BJORN's c19 graphics pass merged)
### Added
- **c19 graphics pass** by BJORN (`game/scripts/battle/battle_visuals.gd`, visual-pass 116c310, final handoff): new 1800s line infantry
  and hussar kit (LOD0/LOD1/rigged + VAT regenerated; white pipeclay straps readable from behind, smaller mid-tone knapsack, short gaiters,
  brighter trousers), a separate c19 field gun (`art_field_gun_c19.glb`), material classes and adaptive team dye in `vat.gdshader`,
  FILMIC tonemap / sun 1.45 / contrast 1.08. Only the c19 era changes look; the other eras are unchanged (tested).
- `--quality=0|1|2` command-line override (this session only, not saved).
### Changed
- Quality Low/Medium/High: Controls still owns the setting and the Options UI, but the per-level render values now come from
  `battle_visuals.apply_quality(q)` (one owner): low = no MSAA, no sun shadows, LOD 45 m, glow off, 2x aniso; medium (default) =
  2x MSAA, shadows 260 m, LOD 75 m; high = 4x MSAA, shadows 300 m, LOD 120 m, 8x aniso. The lead-side stand-in and duplicate MSAA/LOD/shadow
  code were removed. `--debug --lod-dist=` still overrides LOD.
### Fixed
- **Exported builds did not render battle soldiers or cavalry.** The raw VAT animation files (`assets/vat/*.vat`) were not in the
  pck (`include_filter`), so every VAT texture was empty. This affected the v0.1 and v0.2 Windows/Linux zips; editor runs and all
  recordings were fine. `export_presets.cfg` now includes `assets/vat/*.vat` (pck 30 → 40 MB). Checked by running the exported
  Linux build (1800 battle: soldiers render, BATTLERESULT identical to the editor run).
### Verified
- 131/131 tests (`--only=visuals` now asserts q0/q1/q2), sim hashes unchanged (SWE1800/USA1914/JPN1500), 1800 SWE battle
  BATTLERESULT identical to v0.2 and across q0/q1/q2 (39.5 s, end men 5039/5166).
### Not done
- Android export; Windows build not run; graphics pass for the other 4 eras; top-down c19 haze; no GPU measurements.

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
