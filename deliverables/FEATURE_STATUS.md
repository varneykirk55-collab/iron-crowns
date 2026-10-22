# Feature status: honest accounting

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
| Camera pan / zoom / orbit, smooth fly-to | VERIFIED (scripted) | The demo uses fly-to and zoom. Mouse and keyboard input is wired up, but it was only tested by code paths, not by a human. |
| 3 playable nations (USA, SWE, JPN), data-driven | VERIFIED | Per-nation headless playtests (19 checks each). Nations are defined in `data/nations.json`. Adding more playable nations is a data edit. |
| Real-time clock, pause, 5 speeds | VERIFIED | Tests and the HUD clock in screenshots. |
| Economy: funds, income, upkeep, resources, needs, administration | VERIFIED (sim) / PARTIAL (depth) | The monthly economy is tested. Domestic activity is automatic. The model is simple and not balanced in depth. |
| Instant procurement, current-era units only, no build waits | VERIFIED | Tests: "buy units", "older-era equipment cannot be procured". |
| Army movement, path-finding, naval transport | VERIFIED | Tests (JPN route uses naval transport) and `campaign_USA_march.png`. |
| Sieges and territory capture | VERIFIED | Tests (provinces change hands). |
| AI: recruit, expand, declare war, negotiate trade/alliance/NAP, make peace | VERIFIED (sim) | Per-nation test counts (hundreds of proposals, dozens of wars). The AI is rule-based and simple, and peace is rare. |
| Diplomacy UI (F1) and Economy/Army UI (F2) | VERIFIED | `diplomacy_SWE*.png`, `economy_SWE*.png`, `diplomacy_demo.mp4` (proposal sent, unit bought, treasury drops by unit cost). |
| Era progression (global, calendar-driven), refit, old armies keep old kit | VERIFIED (sim) | Tests: 1913 → 1914 advance, refit, buying does not change the era. |
| Save/load | MISSING | |
| Sound / music | MISSING | |
| Naval combat | MISSING | Fleets are only transport markers. |

## Battles
| Feature | Status | Evidence / notes |
|---|---|---|
| Player only deploys (formation + objective); fully AI-simulated | VERIFIED | Deploy window (`battle_deploy_USA.png`). |
| Deterministic sim; the same sim drives the outcome and the visuals | VERIFIED | Test: watched and unwatched battles give the same outcome. |
| Smooth map → battle transition | VERIFIED (video) | Battle MP4. |
| 3D formations, volleys, smoke, impacts, casualties, routs, result | VERIFIED | `battle_USA_close0/close1/top/engage/melee/result.png` and the MP4. |
| Battle length about 30–40 s | VERIFIED (balance test) / PARTIAL | Mean 36–42 s across eras in the 8-seed test. The recorded demo battle lasted about 25 s. |
| Strategic sim keeps running while a battle is watched | VERIFIED | Tests, plus the clock advances in the HUD during the battle. |
| Era-specific armies (5 eras of soldier/cavalry/artillery models) | PARTIAL | All models exist and pass a VAT preview check. Only the c19 battle has been rendered end to end. |
| Blender glTF assets, MultiMesh instancing, VAT animation, 2 LODs | VERIFIED | Scripts in `pipeline/blender/`. LOD switching is distance-based (75 m). |
| Terrain/sieges as 3D battles, naval battles | MISSING | Sieges resolve on the map only. |

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
| Linux x86_64 export | VERIFIED. Exported, and launched under xvfb (menu rendered, data loaded). |
| Windows x86_64 export | PARTIAL. Exported with the official templates, but not run, because no Windows machine was available. |

## Known issues / simplifications
- The battle demo uses `--reinforce=1`, a scripted scenario that gives the defender an army on the invasion path.
- The battle visual runs at about 2–7 fps under software rendering. A real GPU should be far faster, but this was not measured.
- Unit balance and the economy are first-pass numbers.
