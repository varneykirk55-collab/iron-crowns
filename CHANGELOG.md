# Changelog

## Combat animations v1 ON by default (main 2026-10-23, Kirk approved)
- The combat animation layer (`anim_combat.gd`: spear melee, all-at-once retreat, musket march/aim/fire/reload, bow release, horse gaits, cavalry death) is now enabled by default. It was previously off unless `--anim-v1`.
- Troubleshooting switch: `--no-anim-v1` / `--anim-v1=off`, env var `IRONCROWNS_ANIM_V1=0`, or project setting `iron_crowns/battle/anim_v1=false` (override.cfg). `--anim-v1` is still accepted. Presentation only: SIMHASH and BATTLERESULT are identical on and off. New test_runner checks cover the default and the switches.

## Battlefield environment: biome framework + regions (merged to main 2026-10-23, Kirk approved)
- The battlefield environment engine is now biome-driven. Every province maps to one of nine biome profiles (boreal, tundra, temperate, east_asia, tropical, savanna, arid, mediterranean, steppe) from its terrain and lat / lon. Each profile lives in its own file, `game/scripts/battle/biomes/<id>.gd`, and supplies species, rocks, ground cover, palette, water and light. A biome without a file keeps the legacy ground. This branch ships only `boreal.gd`, which reproduces the merged Scandinavian look and now also covers the taiga of Russia and Canada. Other biomes land on their own `env/<biome>` branches.
- The environment is now enabled in every era, not only medieval, so modern battles in North America and elsewhere get it too.
- `test_env` covers every present biome: selection, model existence, determinism, and obstacle clearance in all eras. `tests/biome_census.tscn` prints the province-to-biome census. See `docs/BIOMES.md`. It is rendering only: sim hashes are unchanged.
- Mongolia and Inner Mongolia (lon 100–116, lat 42–50) are classified as `steppe`, not `east_asia`.
- `BattleVisuals.apply()` re-applies the biome look when a biome is active, so calling the graphics pass again (as the visuals test does) keeps the regional light instead of reverting to the era look. Rendering only.

### Region: tropical (env/tropical)
- New `tropical` biome (Philippines, Indonesia, Amazon, Congo, Caribbean, Central America, Hawaii; 174 provinces). It has an open cogon-grass clearing on red laterite, multi-layer rainforest walls outside the fighting corridor (buttressed canopy trees, emergents, coconut palms, banana / fern / thicket understorey), mossy basalt and humid hazy light. All assets are procedural (`pipeline/blender/env_tropical.py`). Evidence: `evidence/env-tropical/`. Rendering only: sim hashes and BATTLERESULT are unchanged.

### Region: east_asia (env/east_asia)
- New `east_asia` biome: East Asian hill-country biome (Japan, Taiwan, Korea, eastern / southern China): sugi, red pine, evergreen broadleaf, maple, bamboo, sasa, azalea, susuki, mossy andesite, humid light; latitude gradient Hokkaido -> Okinawa / Taiwan. Render only. Evidence: evidence/env-east_asia/.

## v0.6.0 — 2026-10-23 (UI and main menu refinement)
Presentation only: battle logic, movement, reinforcement, AI, economy and diplomacy calculations are unchanged (`sim_hash` fingerprints are identical to v0.5.0).
### Design system
- New `scripts/ui/ui_kit.gd`: one palette (charcoal and aged iron, muted navy for selection, brass accents; red for military, blue for diplomacy, ochre for economy, green / amber for good / warning), one Theme (window, card, alert, bar and toast panels; primary, danger, order, ghost and toggle buttons; tooltips, scrollbars, sliders, focus ring) and shared builders. Typefaces: Cormorant SC for titles, Source Sans 3 for text (both SIL OFL 1.1, licences in `game/assets/fonts/`). The smallest text is 14 px in the 1600×900 layout, so it stays readable at 1366×768.
### Title screen and new campaign
- The dev-style start box is replaced by a title screen over a slowly drifting campaign map: Continue (newest save), New Campaign, Load Campaign, Settings, Credits and Quit.
- New Campaign presents the five starting ages as cards with descriptions, the era's regiments and march speed, and only the playable nations (USA, Sweden, Japan) with their size and capital, then a clear summary and **Start Campaign**. The start years now come from `eras.json` (the old menu offered 1913, which started in the Age of Revolutions).
### Campaign HUD
- Top bar: nation and era, treasury with monthly net, manpower, population, stability meter, war status (enemies and exhaustion in the tooltip), date and pause / speed buttons.
- Right column: command dock (Diplomacy, Economy, ✉ Inbox, Menu), military alert cards for spotted invasion forces (with *Go to*), and the Dispatches log, which was previously anchored off-screen together with the Inbox button.
- Selection panel: fixed width and scrollable. Armies show strength, current order and destination with ETA; foreign provinces show owner, relations and nearest armies' Invade / Attack / Retake orders with days to arrive; own provinces show recruitment.
- Windows have a frame with title and close button and dim the map behind them; clicking the map closes them (but not decisions such as deployment).
- Confirmations for disbanding a regiment, declaring war, cancelling a treaty, loading, returning to the title and quitting. Disabled buttons explain why in their tooltip.
- Diplomacy, Economy (treasury, income, expenses with upkeep highlighted, people, policy, stockpile, procurement, armies, provinces), Inbox (Military reports section, coloured category chips) and the deployment window were restyled.
- The battle result is a framed card with engaged / losses / remaining for both sides.
### Tests
- New `ui` suite (6 checks): the title screen lists the right menu entries, ages and only playable nations; a campaign starts by mouse in every era; speed buttons and dock windows work by click; disbanding asks first; long panels scroll on screen; saving shows a notice and Continue resumes it.
- `tests/ui_shots.tscn` captures the UI at any resolution; `tests/ui_demo.tscn` is a scripted walkthrough used for the demo video.

## v0.5.0 — 2026-10-23 (gameplay & AI refinement)
### Medieval combat: no more panic routs just before contact
- **Diagnosis** (Sweden vs Norway 1300, real starting armies, 40 seeds): 15 of 80 spear regiments routed without ever reaching melee, and attackers won 40/40. The battle model has **no obstacles**; rocks are scenery only. The real causes were that a melee-only regiment on "hold" had no response to being shot, morale never recovered under the 4-second arrow cadence, and the 28-second "decisive phase" doubled arrow casualties right as the lines met. The Norwegian spearmen routed at a 4 m gap, wherever a rock happened to be.
- **Counter-charge:** holding melee regiments under missile fire counter-charge within 75 m, or within 150 m once fire has cost them 60% of their morale. A regiment that leaves its line loses the "hold" defence bonus.
- **Élan:** regiments running in to close take missile morale shock at ×0.7.
- **Rocks:** battlefield rocks are placed outside the fighting area. This is a placement rule only; the assets are unchanged.
- **Result:** 0/80 pre-contact routs, missiles still 83% of kills, mirror-army attacker wins 23/40 (unchanged), and a lone charge into massed archers can still be shot apart. c19/c20/modern battles are numerically unchanged.
### Strategic AI targeting
- **Diagnosis:** the median AI attack target was 3,600 km away in 1800, 2,200 km in 1300 and 11,600 km in 1914 (Egypt → Barbados, Saudi Arabia → Tokyo). In 75–94% of attack orders the attacker left under 10% of its strength at home.
- **War declarations:** need geographic reach. Border wars are preferred; an overseas war needs a crossing of about 45 days at most and a 2.5× strength edge; nothing beyond about 100 days' travel.
- **Army orders:** priorities are, in order:
  1. Reinforce a battle in progress nearby.
  2. Beat enemy armies inside our land.
  3. Guard home when an enemy army threatens it.
  4. Rest armies below 50% strength.
  5. Otherwise campaign against the best-value target in reach, weighing travel time, sea crossings, defenders within 350 km, capital/population/lost-province/border value and a penalty for far fronts.
- **Result:** median attack distance is about 1,150 km (1800) and 1,390 km (1300). Saudi Arabia at war with Japan sends no one to Tokyo; Britain still crosses to France; a strong AI still attacks a weak player.
### Invasion detection and warnings
- **Detection ranges** around your provinces and armies: 60 km (medieval scouts and watch posts), 110 km (pike & shot), 180 km (pickets and coastal observers), 350 km (1914 reconnaissance), 900 km (modern radar). At sea the range is smaller before coastal observation and larger with radar.
- **Hidden forces:** hostile armies, and armies on an undeclared invasion order against you, are hidden on the map and in province panels until detected. Other armies show as before.
- **Warnings:** one warning per approaching army and objective, naming the threatened province, approximate strength (rounded more coarsely in early eras), ETA, whether war was declared and whether you are outnumbered nearby. It goes to the toast and the dispatch log, and a fast clock drops to Normal so you have time to respond.
### Mid-battle reinforcements
- **Orders:** armies can be sent to a battle in progress (army panel: Reinforce / Flank / Support, or right-click the battle). They march by the normal rules and join if they arrive before it ends, entering from the direction they marched in from. Support forms up behind its own line and holds.
- **AI:** AI armies use the same order and re-plan as soon as a nearby battle starts.
- **Battle-time scheduling:** joins happen at the battle time matching the arrival day, so watched, off-screen and saved/loaded battles resolve identically. Late arrivals never count toward the result; if enemies remain they start a fresh engagement. Same units and casualty bookkeeping: nothing is duplicated and losses persist.
- **Pacing change:** battles now advance 5 battle-seconds per campaign day (was 15), so a battle spans about a week on the map and a neighbouring army can arrive. Outcomes are unchanged because the simulation runs the same seconds.
- **3D view:** builds visuals for regiments that arrive mid-battle, with the same graphics pass.
### Diplomatic inbox
- **Diagnosis:** every envoy opened a blocking popup, unanswered offers stacked duplicates (Poland's peace offer queued 6 times) and a declined offer could come straight back.
- **Inbox:** offers collect in an Inbox (button on the Dispatches panel, with count; red when urgent) instead of popping up.
- **Throttling:** one pending offer per nation and kind; declined offers are not repeated for 120–300 days; unanswered ones lapse after 90 days.
- **Urgent offers** (peace or alliance while at war) get a one-line notice and a "Needs attention" section. Routine offers are grouped with Accept all / Decline all / Set aside all routine. Recent warnings are listed in the Inbox too.
### Verified
- Full suite 205/205 after merging main's Scandinavian battle environment (`test_results.txt`), including the new suites `--only=medieval|aistrategy|detection|reinforce|inbox`; test_audio 28/28; test_env 0 failures.
- Demos: `deliverables/videos/reinforce_JPN_demo.mp4` (the 2nd Army arrives on the Sapporo battlefield, 15 → 19 regiments) and `alerts_SWE_demo.mp4`; screenshots `deliverables/screenshots/reinf_*`, `alert_*`.
- **Saves:** new fields `spotted`, `offer_block`, per-army `prev`/`reinforce`/`rmode`, battle `axis`/`late`, BattleSim `pending`. Older saves load.
- **Sim hashes change** as expected, because the AI and battle pacing changed. Determinism is unchanged.
### Not done / limitations
- AI nations tend to campaign with one merged army, so AI reinforcement of AI battles is rare in practice (it works when a second army is near: tested with Germany vs France 1914).
- The AI's own threat assessment still sees every enemy army; detection limits what the player sees.
- The Windows build is exported but not run on Windows.

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
