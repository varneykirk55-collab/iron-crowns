# Changelog

## Unreleased (branch env/biome-framework, not on main, awaiting Kirk's approval)
- env/east_asia: East Asian hill-country biome (Japan, Taiwan, Korea, eastern / southern China): sugi, red pine, evergreen broadleaf, maple, bamboo, sasa, azalea, susuki, mossy andesite, humid light; latitude gradient Hokkaido -> Okinawa / Taiwan. Render only. Evidence: evidence/env-east_asia/.
- The battlefield environment engine is now biome-driven. Every province maps to one of nine biome profiles (boreal, tundra, temperate, east_asia, tropical, savanna, arid, mediterranean, steppe) from its terrain and lat / lon. Each profile lives in its own file, `game/scripts/battle/biomes/<id>.gd`, and supplies species, rocks, ground cover, palette, water and light. A biome without a file keeps the legacy ground. This branch ships only `boreal.gd`, which reproduces the merged Scandinavian look and now also covers the taiga of Russia and Canada. Other biomes land on their own `env/<biome>` branches.
- The environment is now enabled in every era, not only medieval, so modern battles in North America and elsewhere get it too.
- `test_env` covers every present biome: selection, model existence, determinism, and obstacle clearance in all eras. `tests/biome_census.tscn` prints the province-to-biome census. See `docs/BIOMES.md`. It is rendering only: sim hashes are unchanged.
- Mongolia and Inner Mongolia (lon 100–116, lat 42–50) are classified as `steppe`, not `east_asia`.

## env/scandinavia-medieval (merged to main in 8f2681f)
- Medieval battles in Scandinavian provinces (Norway, Sweden, Denmark, Finland) get a data-driven boreal battlefield. It has rolling relief that stays flat in the engagement corridor, multi-layer terrain (grass, dry grass, earth, rock, scree, snow, shore), spruce, pine and birch forest edges with a far forest belt, natural rocks kept out of the formation lanes, ground cover, an optional lake, distant mountains driven by the data, and a warm summer sun with aerial fog. It is rendering only: sim hashes are unchanged. Evidence is in `evidence/env-scandinavia/`.

## v0.4.0 — 2026-10-23 (offensive warfare and territorial conquest)
### Why
The player could declare war but could not really go on the offensive. Reproduced on v0.3.3 with the real right-click path in all five eras: `Sim.passable()` only allowed entry into land of nations already at war or allied, so every order into foreign land failed with "Cannot enter … without war or alliance"; there was no Invade control; a formal declaration was the only way in and immediately brought in the target's allies; an army whose march was interrupted by a battle never resumed; and a nation was deleted the moment it lost its last province, so lost land could not be won back. The passing `gameplay` test drove the sim through a demo helper with a cash grant, not through the player controls.
### Added
- **Invade order** (`Sim.order_invade`): any army can be sent against any foreign province. Right-click / gamepad X / long-press on foreign land, or the new province-panel buttons (**Invade / Attack / Retake with <army> · ~N days**). The march starts at once on the existing path-finding and naval transport; nothing teleports.
- **Undeclared conflicts**: for a nation we are at peace with, a dialog offers *Invade (undeclared)* or *Declare war & invade*. Hostilities start when the army crosses the border (`Sim.start_hostilities`); the victim defends and counterattacks at once, but its allies are not called in. A later formal declaration (F1, "Formally declare war") upgrades the conflict and calls the allies. Wars now carry `declared`; the HUD shows UNDECLARED WAR.
- **Recapture**: AI majors *and minors* send armies to win back provinces they held at the start; the player gets a Retake button. Captures of your own former land log as "recaptures".
- **Landless nations and defeat**: a nation with no provinces survives while it fields an army of ≥150 men, can retake land (its government returns to the first province it wins back), and is eliminated otherwise. A landless AI at peace invades its old homeland under the same rules. The player gets a DEFEAT screen (Load quicksave / Return to title / Quit) and the clock stops.
- Invasion demo `--demo=invasion --nation=SWE|JPN|USA [--year=…]`, and `test_offensive` (`--only=offensive`, 23 checks).
### Changed
- Winners of a battle on an **invasion** order re-path to their objective; plain march orders behave as before.
- Captured provinces update both nations' income/expense ledgers immediately (the province's population, taxes and resource count for the new owner at once).
- Travel estimates count sea legs at sea speed (they were too short for overseas moves).
- Clearer order feedback: ally/truce refusals, "no route" with the blocking neutral neighbours and the era's naval range, and a dispatch when a march is halted by a closed border.
- Army panel status shows invading / attacking / besieging (with siege %).
- Saves: new fields `defeated`, per-army `invade`/`resume`, per-war `declared`. Older saves load with every war treated as declared.
### Verified
- Full suite 163/163 (140 existing + 23 new), test_audio 28/28.
- Sim hashes change as expected (the AI now goes after lost provinces): SWE1800 417a5300…, USA1914 4679c5a2…, JPN1500 e104d558…; determinism is unchanged (save/load and 40-day replay identical).
### Not done / limitations
- No naval combat (fleets are still transport only). Passing through third-party neutral land still requires war or an alliance (no military-access treaty yet).
- The AI still opens wars with formal declarations; it uses undeclared invasion only to retake its homeland when landless and at peace.
- The Windows build was exported but not run on Windows.

## v0.3.3 — 2026-10-23 (team readability for the 1800s soldiers, officers, music and audio)
### Added
- **Team readability at distance** (BJORN `character-refinement-2` 667e980, applied as 2a7c5ae). This is render-only. The coat area, marked by the UV2.y mask, is tinted toward the side colour as the camera moves away: up to 0.85 at 25–90 m and up to 0.95 at 90–200 m. When both sides would read the same, the clash pick recolours one of them; in 1800, Norway now reads red against Sweden's blue, matching the HUD and banners. The Swedish coat changes from 2a3d6e to 3a5a9a, so it is no longer near-black in the close defender view.
- High quality gets a mid LOD (20/45 m), and the mid and far sets get a coat lift.
- **One officer per c19 line or grenadier regiment** (R3, battle_view `6f2e530`). It stands to the right of the front rank and uses the `c19sr_officer` VAT model with its own 0.25 s crossfade. It is render-only: no RNG and no sim writes. It is turned off automatically if the c19sr swap is unavailable.
- Artillery gun crews now crossfade between clips via `BattleVisuals.xfade_crew` (state keyed per crew member and gun).
- **Music and military audio system**, merged into lead-dev from the `audio` branch (see the section below).
### Verified
- 140/140 tests, plus test_audio 28/28.
- Outcome hash `0e814dda…` and sim hashes SWE1800 `f7255ebb…`, USA1914 `45cf5510…`, JPN1500 `9bb2394d…` are unchanged. 0 shader errors.
- In the 1800 SWE battle, the two sides read red vs blue at close, mid and overhead on Low, Medium and High (3-way compare against v0.3.1 and v0.3.2 in `screenshots/compare/`). Other eras look the same as in v0.3.2.
- Frame time on llvmpipe (1800 SWE, mean of 4 views) vs v0.3.2: Low +3 %, Medium −1 %, High at parity after a re-run (the first pass showed a noisy +62 % on the High overhead view).
### Not done / limitations
- The Windows build is exported but not run. The audio has not been listened to by a human.

## Audio system (`audio` branch, merged into lead-dev 2026-10-23 07:45 EDT, ships in v0.3.3): music and military audio system
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
- `--demo=battle --nation=SWE` (1800) gives the same BATTLERESULT as the baseline (39.5 s, end_men 5039/5166). Its `--write-movie` recording carries the mixed audio: 62.1 s, peak -2.0 dBFS, no clipped samples, battle-section 100 ms RMS p50 about -20 dBFS with p90 about -15.5 dBFS.
- `analyze_audio.py`: all 75 files pass (max decoded peak -0.71 dBFS, every loop seam within the interior range). Rebuilding the assets is byte-identical.
- `test_audio` snapshots and restores `user://audio.cfg`, so test runs never change a player's saved volumes.
### Not verified
- No human listening test (no subjective quality check).
- Exported builds not run with audio.
- Known issue: when the demo is recorded with `--write-movie`, Godot reports at exit that 8 ObjectDB instances leaked and 4 resources were still in use (`music_tension.ogg`, `sting_victory.ogg`). The movie writer stops mixing audio on the frame the demo calls `quit()`, so playbacks that were just stopped are never released. Normal runs (the demo without movie, the main scene, the tests) exit clean, and the baseline has no such warning.

## v0.3.2 — 2026-10-23 (BJORN's semi-realistic Napoleonic c19 soldiers)
### Added
- **New 1800s soldiers** (BJORN `character-refinement` d93f576, applied as 456aa8d): semi-realistic Napoleonic line infantry (shako),
  grenadiers (bearskin) and artillery crews with musket + bayonet, built on a shared rigged body and baked to VAT (idle, walk, run, fire with
  recoil, reload, melee, two death variants). Nation uniforms for all 47 major nations. Two LODs per model plus an in-shader near/far
  split at 20/30/45 m (Low/Medium/High). In-place swap: model ids, multimeshes and units.json are unchanged; other eras untouched.
- 0.25 s animation crossfade between clips for the new soldiers (battle_view `_put` instance colour + `BattleVisuals.xfade`, ffcafd3).
  Artillery crews still switch clips without a crossfade.
- Debug-only BattleVisuals node restored for `--bench`, `--perflog`, `--vispass` (main.gd; no effect without those flags).
- `game/tests/battle_shots` harness: battle screenshots and frame timing at fixed camera views on the production battle.
### Verified
- 140/140 tests; gameplay outcome hash `0e814dda…`; sim hashes SWE1800 `f7255ebb…`, USA1914 `45cf5510…`, JPN1500 `9bb2394d…` unchanged;
  0 shader errors. Other eras render as in v0.3.1.
- Battle frame time on llvmpipe (1800 SWE, mean of 4 views): Low −11 %, Medium +4 %, High −17 % vs v0.3.1 (single runs; ±15 % noise per view).
### Not done / limitations
- Readability: in the 1800 Norway-vs-Sweden battle both armies wear blue coats, so at mid range and overhead on snow the sides are hard to tell
  apart (v0.3.1 read red vs blue). Sent to BJORN; his brighter-far-coats / mid-LOD delta was not ready and comes in v0.3.3.
- No officer per regiment yet (model is built; needs battle_visuals support). Windows build exported but not run.

## v0.3.1 — 2026-10-23 (overworld terrain refinement, Victoria-style map)
### Added
- **New campaign-map look** (`game/shaders/map.gdshader` rewritten; branch `graphics-map` 53b3dcd): relief shading from baked
  normal/cavity maps, a natural biome albedo with forests, rock on steep slopes and snow on high peaks (prominence-based, so the Tibetan
  plateau is not white), depth-shaded oceans with shallows, waves, shore foam and fresnel, light haze at oblique views, smooth antialiased
  coasts. Borders come from a signed distance field: national borders are thicker and darker than province lines and keep a constant
  pixel width across zoom. The political tint is strong at world/region zoom and fades so terrain dominates close up.
- **Terrain LOD**: the map is 16x8 chunks with 3 LODs and skirts (`world_map.gd`); Low quality hides the finest LOD and uses a simpler
  shader path. Quality follows `Controls.settings_changed`.
- `pipeline/build_map_visuals.py` regenerates the 5 terrain textures in `game/assets/map_terrain/`. Harnesses `game/tests/map_shots`
  (screenshots, perf, province-pick grid, selection/conquest/zoom checks) and `game/tests/map_flyover` (movie capture).
### Fixed
- Horizontal streaks over the open ocean at world zoom (v0.2–v0.3). Cause: the deep-ocean backdrop plane sat 0.06 units under the
  ocean surface, below the depth-buffer resolution at world-zoom distances, so the two z-fought. The backdrop now sits at y −1.5.
### Unchanged (verified)
- Picking, the political LUT, army markers (`map_visuals.gd`, R5), labels, sim and battles. 641 provinces, 186 AI nations.
### Verified
- 140/140 tests including the marker click/selection tests; gameplay outcome hash `0e814dda…` unchanged; sim hashes USA1914 `45cf5510…`,
  JPN1500 `9bb2394d…`, SWE1800 `f7255ebb…` unchanged from v0.3. Province picks identical to v0.3 on 15 views x 576 screen points (and to
  v0.2.1 on the original 12). Selection highlight, conquest recolour (Oslo → Sweden, re-pick 328) and zoom extremes 4/230 OK.
- Map frame time on llvmpipe (mean of 8 views): Low −47 %, Medium −29 %, High −34 % vs v0.3; close mountain views at Medium/High are
  up to +28 % slower (more triangles in the finest LOD). Not measured on a GPU.
### Not done / limitations
- At region and close zoom the national colours are deliberately muted (terrain first, like the reference); some neighbours with similar
  colours are told apart mainly by the dark border line. No cities, fleets or gameplay changes. The terrain is shaded, not re-meshed:
  mountain height still uses the existing height scale (picking depends on it). Windows build exported but not run.

## v0.3 — 2026-10-23 (BJORN's eras batch + polish pass merged)
### Added
- **Battle graphics for every era** by BJORN (`battle_visuals.gd`, eras batch 1c951b9): medieval, pike & shot, c20 and modern now get
  the material classes, team dye and lighting the c19 pass introduced in v0.2.1.
- **Overworld army markers** (`map_visuals.gd`, hooked into `world_map.gd`, R5): era-specific standard meshes on the campaign map.
  Cosmetic only; clicking, selecting and moving armies are unchanged (new tests click a marker through the real input path).
- **Polish pass** by BJORN (5adecc2): depth-range fog (the field inside 260 m stays clear) and a winter grade for tundra/mountain battles
  (lower exposure, more contrast, deeper snow ground), which removes the pale haze of the overhead view; a c19 grenadier model
  (bearskin cap); artillery-uniform gun crews (`c19_artillery`, `em_gunner`).
### Changed
- `units.json` (generated by `pipeline/make_gamedata.py`): c19 grenadiers use `c19_grenadier`. `battle_view.gd` `CREW_MODEL`:
  c19 → `c19_artillery`, early modern → `em_gunner`. BJORN's runtime swaps for these are now no-ops (tested).
- Test "eras outside the pass keep the legacy look" now checks medieval is in the pass (R6).
### Verified
- 140/140 tests (new: marker click/selection, polish models, idempotent re-apply, winter fog/grade). The original 61 gameplay checks
  give the same outcome hash as v0.2.1 (`0e814dda…`). Sim hashes: USA1914 and JPN1500 unchanged; SWE1800 changes only because the
  saved regiment data now carries the `c19_grenadier` model name (the full state dumps differ in exactly those 2 lines).
- One q1 battle per era re-rendered with the polish pass: BATTLERESULT identical to the earlier recordings in all 5 eras, no script errors.
### Not done
- R3 (era artillery models in `units.json`) not applied; c20/modern still use `art_howitzer`. Team colour in the overhead view is
  still weak for c20/modern and for pale nation colours (Japan). Android export; Windows build not run; no GPU measurements.

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
