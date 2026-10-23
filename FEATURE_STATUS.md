# Feature status (v0.3): honest accounting

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
| AI: recruit, expand, declare war, negotiate trade/alliance/NAP, make peace | VERIFIED (sim) | Per-nation test counts (hundreds of proposals, dozens of wars). The AI is rule-based and simple, and peace is rare. |
| Diplomacy UI (F1) and Economy/Army UI (F2) | VERIFIED | `diplomacy_SWE*.png`, `economy_SWE*.png`, `diplomacy_demo.mp4` (proposal sent, unit bought, treasury drops by unit cost). |
| Era progression (global, calendar-driven), refit, old armies keep old kit | VERIFIED | Tests: 1913 → 1914 advance, refit, buying does not change the era; gameplay test sees the era change on 1 Jan 1914 in the real main scene. USA/SWE/JPN start armies use the right era's units in all 5 start years. |
| Scripted end-to-end gameplay | VERIFIED (headless) | `--only=gameplay` 7/7: start as Sweden 1913, march, declare war, watch a battle + camera toggle, capture a province, save/load, era advance. The test grants extra funds so the invasion reliably succeeds. |
| Save/load (F5/F9, named slots, title-menu load) | VERIFIED | `--only=save` 8/8 (deep equality, 180-day forward determinism, missing slot, list); gameplay test round trip; `shots/v02/saveload_*.png`. Watched battles load as unwatched. |
| Sound / music | MISSING | |
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

## Builds
| Build | Status |
|---|---|
| Linux x86_64 export | VERIFIED (xvfb/llvmpipe). The v0.3 export was run with the 1800 battle demo: it completed with no script errors, soldiers rendered (grenadier and gun-crew models included), and BATTLERESULT matched the editor run (39.5 s, end men [5039, 5166], Sweden wins). v0.1/v0.2 exports lacked the VAT data; fixed in v0.2.1. |
| Windows x86_64 export | PARTIAL. Exported with the official templates; not run (no Windows machine / wine). |
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
