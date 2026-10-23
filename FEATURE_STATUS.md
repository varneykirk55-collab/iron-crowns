# Feature status (v0.4.0): honest accounting

Status labels:
- **VERIFIED**: exercised by an automated test (`game/tests/test_runner.gd` → `test_results.txt`), seen in a rendered screenshot or video, or both.
- **PARTIAL**: works, but is simplified or only partly checked.
- **MISSING**: not implemented.

All testing ran under Linux on Mesa llvmpipe, a software renderer, using xvfb.

## Campaign / strategic layer
| Feature | Status | Evidence / notes |
|---|---|---|
| 3D world map with real coastlines, relief and political colouring | VERIFIED | `campaign_*_world/region/close.png`. Built from Natural Earth 50m data. |
| Selectable countries and provinces, with borders | VERIFIED | Province panel and highlight in screenshots. 641 provinces. Small countries are a single province. |
| Camera pan / zoom / orbit, smooth fly-to | VERIFIED (scripted) | Demo fly-to/zoom; `--only=controls` drives keyboard, gamepad and touch with synthesized input events. Not played by a human. |
| Controls: kbm + gamepad + touch, rebindable InputMap, settings | VERIFIED (synthetic input) | `--only=controls` 19/19: 37 actions all with gamepad bindings, pad cursor select/move, touch tap/drag/pinch/twist/long-press, no virtual joystick nodes. No physical gamepad or touchscreen was available. |
| F3 performance overlay, quality Low/Medium/High | VERIFIED | Overlay values come from the same probes as `--perfout`. Controls owns the setting (saved; `--quality=0/1/2` session override); the per-level render values are owned by `battle_visuals.apply_quality(q)`: low = no MSAA, no sun shadows, LOD 45 m, no glow; medium (default) = 2x MSAA, shadows 260 m, LOD 75 m; high = 4x MSAA, shadows 300 m, LOD 120 m. `--only=visuals` asserts all three levels; c19 battle rendered at q0/q1/q2 (`screenshots/c19_q0..q2/`). |
| 3 playable nations (USA, SWE, JPN), data-driven | VERIFIED | Per-nation headless playtests (19 checks each). Nations are defined in `data/nations.json`. Adding more playable nations is a data edit. |
| Real-time clock, pause, 5 speeds | VERIFIED | Tests and the HUD clock in screenshots. |
| Economy: funds, income, upkeep, resources, needs, administration | VERIFIED (sim) / PARTIAL (depth) | The monthly economy is tested. Domestic activity is automatic. The model is simple and not balanced in depth. |
| Instant procurement, current-era units only, no build waits | VERIFIED | Tests: "buy units", "older-era equipment cannot be procured". |
| Army movement, path-finding, naval transport | VERIFIED | Tests (JPN route uses naval transport) and `campaign_USA_march.png`. |
| Sieges and territory capture | VERIFIED | Tests (provinces change hands). |
| **Player invasions (v0.4)**: select army → Invade/Attack/Retake on any foreign province, no declaration needed | VERIFIED (real click path + recorded demo) | `--only=offensive` 23/23. The test clicks the army marker, right-clicks the target, confirms "Invade (undeclared)" in the dialog, and presses the province panel's Retake / Invade buttons. Demos: `--demo=invasion --nation=SWE` and `--nation=JPN` (`deliverables/videos/invasion_*_demo.mp4`, `deliverables/screenshots/invade_*`). |
| Undeclared conflict vs formal war | VERIFIED | Crossing the border starts hostilities: the defender fights back at once, but its allies are only called in by a formal declaration (which can still be made later from F1). Relations with the victim −55 and −4 with every great power; breaking a NAP costs stability. Alliances and peace truces still block an invasion. |
| Interrupted invasions press on | VERIFIED | An invasion order that wins a battle on the way re-paths to its objective (tested with a two-province route). Plain march orders keep the old behaviour (stop where the battle was). |
| Recapture of lost provinces (player and AI) | VERIFIED | Player: province panel "Retake" (test). AI: majors and minors now send armies to win back provinces they held at the start (test: Finland counterattacks Mariehamn). |
| Landless nations fight on; clear defeat | VERIFIED | A nation that loses its last province survives while it has an army of ≥150 men and can retake land (test). No land and no army → DEFEAT screen (Load quicksave / Return to title / Quit) and the clock stops. |
| Overseas invasion | VERIFIED | Japan → Busan via the existing embark / sea-zone / landing path (test + demo). Uses the era's naval range; there is still no naval combat. |
| Invalid routes explained | VERIFIED | Orders that cannot be carried out say why (ally, truce, neutral land in the way plus naval range, halted mid-march by a closed border). |
| AI: recruit, expand, declare war, negotiate trade/alliance/NAP, make peace | VERIFIED (sim) | Per-nation test counts (hundreds of proposals, dozens of wars). The AI is rule-based and simple, and peace is rare. |
| Diplomacy UI (F1) and Economy/Army UI (F2) | VERIFIED | `diplomacy_SWE*.png`, `economy_SWE*.png`, `diplomacy_demo.mp4` (proposal sent, unit bought, treasury drops by unit cost). |
| Era progression (global, calendar-driven), refit, old armies keep old kit | VERIFIED | Tests: 1913 → 1914 advance, refit, buying does not change the era; gameplay test sees the era change on 1 Jan 1914 in the real main scene. USA/SWE/JPN start armies use the right era's units in all 5 start years. |
| Scripted end-to-end gameplay | VERIFIED (headless) | `--only=gameplay` 7/7: start as Sweden 1913, march, declare war, watch a battle + camera toggle, capture a province, save/load, era advance. The test grants extra funds so the invasion reliably succeeds. Note: this test drives the sim through a demo helper, not the player controls; the v0.4 `--only=offensive` suite covers the real controls. |
| Save/load (F5/F9, named slots, title-menu load) | VERIFIED | `--only=save` 8/8 (deep equality, 180-day forward determinism, missing slot, list); gameplay test round trip; `shots/v02/saveload_*.png`. Watched battles load as unwatched. |
| Music (campaign / tension / battle + 4 stings), instrumental, original | VERIFIED (playback, mixing, transitions) / not listened to by a human | `res://tests/test_audio.tscn` 28/28. These checks confirm that music plays through the mixer (Master capture is non-silent), the crossfade is equal-power and completes, campaign resumes, loops wrap, stings duck the music, and the battle mood comes back to campaign afterwards. `pipeline/audio/analyze_audio.py` checks loop seams and decoded peaks. The battle demo recording (`--write-movie`) carries the real mixed output: peak -2.0 dBFS and no clipped samples over 62 s. Musical quality is not verified, because no subjective listening was possible. |
| Battle & UI sound effects (era-correct weapons, cannon, explosions, impacts, crowds, hooves, melee, signals, ambience beds, UI) | VERIFIED (triggering, voice limits, no clipping) | test_audio: a watched c19 battle triggers volleys, cannon, impacts, crowd and signals; era→weapon mapping has no rifles before c20 and no automatic fire; musket voices are capped at 6 with 900 requests; global cap 24; mass gunfire (900 requests) peaks at -3.4 dBFS on Master and does not clip. Mix balance: in a watched battle at default volumes, SFX-only p90 is -18.4 dBFS against a battle-music median of -31.3 dBFS (the test requires a margin of at least 6 dB). Outcome is identical with `--audio=off`. Sound quality and realism are not verified by ear. |
| Separate Music / SFX volume, saved | VERIFIED | test_audio: sliders → bus dB, 0 = mute, `user://audio.cfg` round trip. The sliders are in the in-game Settings menu only (the title menu has no settings screen). |
| Naval combat | MISSING | Fleets are only transport markers. |

## Battles
| Feature | Status | Evidence / notes |
|---|---|---|
| Player only deploys (formation + objective); fully AI-simulated | VERIFIED | Deploy window (`battle_deploy_USA.png`). |
| Deterministic sim; the same sim drives the outcome and the visuals | VERIFIED | Test: watched and unwatched battles give the same outcome. |
| Smooth map → battle transition | VERIFIED (video) | Battle MP4. |
| 3D formations, volleys, smoke, impacts, casualties, routs, result | VERIFIED | `battle_USA_close0/close1/top/engage/melee/result.png` and the MP4. |
| Battle length about 30–40 s | VERIFIED (mostly) | `--only=eras`: one battle per era 30–35 s; camera test battle 36.5 s. Recorded campaign battles (table below): 1300 33.4 s, 1500 32.3 s, 1800 39.5 s, 1980 31.0 s; 1914 28.8 s with `--reinforce=1`, and only 17.8 s without it (9.7:1 mismatch, USA vs a weak Canadian force). Length depends on the armies that meet. |
| Cinematic battle camera + overhead toggle (C) | VERIFIED | `--only=camera` 6/6 (identical outcome with 27 toggles, both blend ends reached, ≥4 event-driven cuts incl. aftermath, no NaN); `rec/camera_demo.mp4`. |
| Strategic sim keeps running while a battle is watched | VERIFIED | Tests, plus the clock advances in the HUD during the battle. |
| Era-specific armies (5 eras of soldier/cavalry/artillery models) | VERIFIED | `--only=eras`: each era's battle uses only that era's units and model files (lod0/lod1 glb); projectile classes per era (arrow/stone shot → musket ball/round shot → rifle tracer/shell/tank round); armour matters (medieval knights vs levy, MBT vs rifles). All 5 eras recorded end to end (`videos/era_*`, table below). |
| Melee | PARTIAL | Melee decides medieval battles (10–38 % of kills); from 1500 on it is ≤0.4 % and 0 % in c20/modern — fire dominates. That is plausible but means pike/bayonet units rarely fight hand to hand. |
| Blender glTF assets, MultiMesh instancing, VAT animation, 2 LODs | VERIFIED | Scripts in `pipeline/blender/`. LOD switching is distance-based (45/75/120 m by quality). |
| c19 graphics pass (BJORN, `battle_visuals.gd`, handoff 116c310) | VERIFIED (rendered, llvmpipe only) | New c19 line/hussar kit (white pipeclay straps readable from behind, smaller knapsack, short gaiters), own c19 field gun, material classes in the VAT shader, adaptive team dye, FILMIC lighting. c19 only; other eras keep the legacy look (tested). Rendering only: sim hashes and the BATTLERESULT of the recorded 1800 battle are identical to v0.2 and identical at q0/q1/q2. `videos/c19_battle_v021_q1.mp4`, `screenshots/c19_compare/`. Not measured on a GPU. |
| All-era graphics + polish pass (BJORN, eras 1c951b9 + polish 5adecc2) | VERIFIED (rendered, llvmpipe only) | All 5 eras in the pass; depth-range fog and winter grade (overhead view no longer washed out, `screenshots/polish_closeups_and_snow/`); c19 grenadiers in bearskins, artillery-uniform gun crews (c19, early modern). Rendering only: BATTLERESULT of the 5 recorded era battles identical before and after (`evidence/battleresults_vs_baseline.md`). Overhead team colour still weak for c20/modern and pale colours. |
| Campaign army markers (`map_visuals.gd`) | VERIFIED | Tests click a marker and select/move the army; world/region/close zoom shots in `screenshots/campaign_*`. |
| Victoria-style campaign map (terrain relief, biomes, snow, oceans, SDF borders, adaptive political tint, 3 terrain LODs) | VERIFIED (rendered, llvmpipe only) | v0.3.1. `screenshots/compare/` before/after for Alps, Rockies, Japan, Scandinavia, Himalayas, Europe world zoom, border close-up; picks identical to v0.3 on 15 views; selection/conquest/zoom checks; `perf_table.md` (q0/q1/q2). Region/close-zoom nation colours are muted by design. Not measured on a GPU. |
| World-zoom ocean streaks | FIXED (v0.3.1) | Backdrop plane z-fighting; `screenshots/compare/compare_usa_world.png`. |
| Semi-realistic Napoleonic c19 soldiers (line, grenadier, artillery crew, one officer per line/grenadier regiment; 47 nation uniforms; 0.25 s clip crossfade incl. gun crews; distance team tint) | VERIFIED (rendered, llvmpipe only) | v0.3.2/v0.3.3. `screenshots/compare/` 1800 SWE q0/q1/q2 close/close_def/mid/top, 3-way v0.3.1/v0.3.2/v0.3.3; `perf_table.md`. Team readability: NOR red vs SWE blue at close/mid/overhead on all quality levels (v0.3.3). |
| Terrain/sieges as 3D battles, naval battles | MISSING | Sieges resolve on the map only. |

## Recorded era battles (v0.2, 960x540, `tools/rec_eras.sh`, summaries from `tools/era_summary.py`)
| Start | Battle | Winner | Length | Projectiles seen | Models rendered | Melee share |
|---|---|---|---|---|---|---|
| 1300 SWE | Denmark vs Sweden | Sweden (defender) | 33.4 s | arrow | med_archer, med_spear | 0.379 |
| 1500 JPN | Russia vs Japan | Japan | 32.3 s | musket_ball, round_shot | em_musket, em_cuirassier, em_pike, art_cannon | 0.004 |
| 1800 SWE | Norway vs Sweden | Sweden | 39.5 s | musket_ball, round_shot | c19_line, c19_hussar, art_cannon | 0.048 |
| 1914 USA | USA vs Canada | USA | 17.8 s | rifle_tracer, shell, tank_round | c20_rifle, tank_c20, art_howitzer | 0 |
| 1914 USA `--reinforce=1` | USA vs Canada | Canada | 28.8 s | rifle_tracer, shell, tank_round | c20_rifle, tank_c20, art_howitzer | 0 |
| 1980 USA | Canada vs USA | USA | 31.0 s | rifle_tracer, shell, tank_round | mod_rifle, mbt_modern, ifv_modern, art_howitzer | 0 |

Every battle used only its era's units. No script errors in any recording log. The 1300 demo army has no knights or bombards, so those models
appear only in tests, not in this video. One weakness seen in the 1914 shots: a flank shot can frame empty ground between the lines.

## Rendered demos
| Demo | Status |
|---|---|
| Campaign map | VERIFIED (PNG + MP4, `campaign_demo.mp4`, 17 s) |
| Battle | VERIFIED (PNG + MP4, `battle_USA_full.mp4`, 44 s: deploy → transition → battle → result panel → back to campaign) |
| Diplomacy/economy | VERIFIED (PNG + MP4, `diplomacy_demo.mp4`, 12 s) |
| Era change | VERIFIED (PNG + MP4, `era_demo.mp4`, 8.5 s: 1913 → 1914 Age of Mechanised War popup → refit panel). The demo runs the clock at ×365 to reach the date. |
| Invasion (v0.4) | VERIFIED (PNG + MP4, `invasion_SWE_demo.mp4` and `invasion_JPN_demo.mp4`: army selected → Invade dialog → march → border crossed → deployment → capture → diplomacy shows UNDECLARED WAR). The demo stages a one-regiment garrison on the objective so a battle is fought. |

## Builds
| Build | Status |
|---|---|
| Linux x86_64 export | VERIFIED (xvfb/llvmpipe). The v0.3 export was run with the 1800 battle demo: it completed with no script errors, soldiers rendered (grenadier and gun-crew models included), and BATTLERESULT matched the editor run (39.5 s, end men [5039, 5166], Sweden wins). v0.1/v0.2 exports lacked the VAT data; fixed in v0.2.1. |
| Windows x86_64 export | PARTIAL. v0.4.0 exported with the official 4.7.2 templates as `IronCrowns_v0.4.0_windows_x86_64.zip` (shared outside the repo; GitHub releases could not be created from the build session); not run (no Windows machine / wine). The matching Linux export was run under xvfb and completed `--demo=invasion` (Mariehamn captured, undeclared). |
| Android | MISSING. No Android SDK or Android export templates on the build machine; touch input is implemented and tested with synthesized events. |

## Known issues / simplifications
- The battle demo uses `--reinforce=1`, a scripted scenario that gives the defender an army on the invasion path.
- Performance (v0.2, measured): CPU frame time headless — map 9.3 ms (p95 12.7), battle 7.7 ms (p95 9.7), i.e. >100 fps worth of CPU.
  Rendered under xvfb/llvmpipe 1280x720 the game is render-bound: ~3.5 fps battle / ~4 fps map (render_cpu ~250 ms per frame in the
  software rasteriser). No GPU was available, so real-hardware fps is unmeasured.
- c19 graphics pass: top-down / very wide views still read pale and hazy (worse on the snowy 1800 Oslo field); next step per BJORN is height fog.
  llvmpipe frame cost (BJORN's bench, mid view): q0 144 ms, q1 279 ms, q2 293 ms vs v0.2 225 ms; the shadow pass dominates. Unmeasured on real GPUs.
  Grenadiers share the line model; artillery crews wear line uniform. The four other eras do not have a graphics pass yet.
- Unit balance and the economy are first-pass numbers.
