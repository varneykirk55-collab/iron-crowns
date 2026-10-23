# Battlefield biomes (env framework)

The Scandinavian battlefield (env/scandinavia-medieval, merged in 8f2681f) is the **design language and quality bar**:
data-driven ground relief / palette, instanced vegetation with per-tier density and LODs, a clean battle corridor where
only knee-high cover may stand, and dressing (forest edges, outcrops, a lake or pond, distant relief) outside it. Every
other region gets its **own** profile: species, rocks, ground cover, palette and light that fit the province's climate.
It never copies the Nordic content.

## How it works

* `game/scripts/battle/battle_environment.gd` is the generic engine (relief, scatter, corridor rules, tiers / LODs,
  materials, light). It has no biome-specific content.
* `biome_id(province, terrain)` maps every province to one of 9 biome profiles using only data fields (terrain tag,
  lat / lon, region). The rules are below.
* `game/scripts/battle/biomes/<id>.gd` provides `static func make(p, terr, base) -> Dictionary`. It receives the generic
  numbers from `_base()` (relief, forest density, rockiness, dryness, distant relief height, snowline, lake) and adds
  species `trees` (model, weight, edge bias), `lone`, `far_model`, `outcrop`/`boulders`, `cover_main` + `accents`,
  `shrubs`, `shore`, `palette` (terrain shader colours), `tints`, `look` (sky / fog / sun / tonemap) and `water`.
* **If a biome file is missing, that biome keeps the legacy ground**, so each biome can land on its own branch and be
  merged independently. On the framework branch only `boreal.gd` (the merged Scandinavian look) exists.
* Era gating: a profile may set `eras` (empty means all). All biomes are now enabled for every era. This is a change
  from the medieval-only Scandinavian prototype, made so that modern North America and similar regions get the
  environment as well.
* Combat, morale, pathfinding, units and sim are untouched. The env is render-only, uses its own RNG
  (`hash([seed, "env-plan"])`) and keeps BattleView's RNG in step. `sim_hash` must stay identical.
* `--env-prov=<id>` previews any province's biome on the demo battle (evidence only). `--env=0` forces the legacy look.
* Census: `godot --headless --path game res://tests/biome_census.tscn`. Tests: `res://tests/test_env.tscn` checks every
  present biome (selection, model existence, determinism, obstacle clearance over real battles in all eras).

## Classifier rules (first match wins)

1. Nordic regions (Norway, Sweden, Denmark, Finland, Åland) → `boreal` (Scandes / Denmark rules inside boreal.gd)
2. terrain `desert` → `arid` (the game data's own tag wins, e.g. Arizona, Sahara, Gobi, and N. China plain / Bihar,
   which the data marks as desert)
3. |lat| ≥ 64, Greenland / Iceland / Faeroe, lat < −46 → `tundra`
4. terrain `tundra` (below 64°) → `boreal` (taiga)
5. terrain `jungle` → `tropical`
6. SE Asia / Pacific / Hawaii (lon ≥ 88 or ≤ −140, |lat| < 22.5, excluding the East Asian block) → `tropical`
7. Bengal / Assam / Burma lowlands (lon 88–100, lat < 29, not mountains) → `tropical`
8. Mongolian plateau / Inner Mongolia (lon 100–116, lat 42–50) → `steppe`
8b. lon 100–146, lat 20–46 (E. China, Korea, Japan, Taiwan) → `east_asia`
9. |lat| < 8, Caribbean / Central America (Americas, |lat| < 26, lon > −95) → `tropical`
10. Arabia / Gulf (lon 34–62, lat 12–32) → `arid`
11. Americas lat 14–33 (Mexican plateau) → `arid`
12. Africa (lon −26..55, lat −36..24), Indian subcontinent (lon 60–88, lat 5–30), cerrado / chaco (Americas lat −30..−8) → `savanna`
13. Mediterranean basin (lat 30–45, lon −10..45), California, central Chile, S. Australia → `mediterranean`
14. Central Asia / Tibet (lat 30–55, lon 45–120), US Great Plains (plains / hills, lon −106..−97), pampas / Patagonia → `steppe`
15. Atlantic / central Europe (lon −12..30): ≥ 57° → `boreal`, else `temperate`
16. |lat| ≥ 52 (or ≥ 50 forest) → `boreal` (Russia, Canada, Siberia)
17. otherwise → `temperate` (eastern / northern US, Europe, NZ ...)

## Proposed biome profiles

| profile | look (design intent) | key regions |
|---|---|---|
| `boreal` | spruce / pine / birch, granite + lichen, heather, juniper, reed lake, cool light (merged Scandinavian look; Canada / Russia taiga get the same family with non-Scandes relief) | Scandinavia, Finland, Baltic north, Russia, Canada |
| `tropical` | dense rainforest walls outside the fighting area (emergent + canopy trees, palms, banana / fern undergrowth), red laterite soil, basalt, humid hazy light, saturated greens | Philippines, Indonesia, Brazil, Congo, Caribbean, Hawaii |
| `east_asia` | varied greenery and hills: Japanese red pine, sugi cedar, broadleaf, bamboo groves, mossy dark volcanic rock, terraced-green palette, soft humid light | Japan, Taiwan, Korea, E. China |
| `temperate` | oak / beech / maple broadleaf with mixed conifers, meadow grass, hedgerow shrubs, limestone / grey rock, warm clear light; seasonal (summer / autumn tint by seed) | North America (east, midwest), central & western Europe |
| `arid` | dry earth, sparse scrub, sandstone / red rock outcrops, no grass carpet, saguaro only in the Americas, harsh high sun and pale sky | US Southwest, Mexico, Sahara, Arabia, Iran, Gobi, Australia |
| `savanna` | tall golden grass, flat-topped acacias, termite mounds, ochre soil, hot hazy light | Sub-Saharan Africa, Deccan, cerrado |
| `mediterranean` | olive, cypress, stone pine, maquis shrub, pale limestone, dry gold grass, bright light | Med basin, California, central Chile |
| `steppe` | open short grass, few trees (poplar / elm in hollows), low shrubs, wide horizon, big sky | Kazakhstan, Mongolia, Great Plains, pampas |
| `tundra` | no trees; moss, sedge, dwarf willow, frost-shattered rock, cold flat light | Arctic Russia / Canada, Alaska, Greenland, Iceland, Patagonia south |

## Census (from biome_census.tscn)

| profile | provinces | by region |
|---|---|---|
| `boreal` | 42 | Russia 10, Canada 8, Sweden 8, Norway 5, Finland 5, Denmark 2, United States of America 1, Åland 1, United Kingdom 1, Estonia 1 |
| `tundra` | 28 | Russia 12, Greenland 4, Canada 2, Chile 2, United States of America 1, Heard I. and McDonald Is. 1, Faeroe Is. 1, Argentina 1, Fr. S. Antarctic Lands 1, Falkland Is. 1, … |
| `temperate` | 91 | United States of America 30, Germany 6, Ukraine 5, United Kingdom 4, France 4, Poland 4, Canada 3, Romania 2, Belarus 2, New Zealand 2, Italy 2, India 2, Russia 2, … |
| `east_asia` | 34 | China 18, Japan 9, North Korea 3, South Korea 3, Taiwan 1 |
| `tropical` | 174 | Brazil 25, Indonesia 12, India 8, Venezuela 5, Bolivia 5, Dem. Rep. Congo 5, Philippines 4, Tanzania 4, Colombia 4, Peru 4, Central African Rep. 3, Thailand 3, Myanmar 2, … |
| `savanna` | 56 | India 10, Angola 5, Zambia 4, Mozambique 4, Madagascar 3, South Africa 3, Zimbabwe 2, Argentina 2, Brazil 2, Comoros 1, Cabo Verde 1, Gambia 1, eSwatini 1, Djibouti 1, … |
| `arid` | 148 | United States of America 11, China 9, India 7, Mexico 7, Niger 6, Mali 6, Mauritania 5, Chad 5, Iran 5, Saudi Arabia 5, Algeria 5, Australia 5, Libya 4, Sudan 4, Ethiopia 4, … |
| `mediterranean` | 31 | Turkey 4, Spain 3, Italy 3, United States of America 2, Malta 1, Andorra 1, N. Cyprus 1, Cyprus 1, Lebanon 1, Montenegro 1, North Macedonia 1, Albania 1, Armenia 1, … |
| `steppe` | 37 | Kazakhstan 7, Mongolia 5, Argentina 4, India 4, United States of America 3, Russia 2, China 2, Afghanistan 2, Siachen Glacier 1, Iran 1, Pakistan 1, Uzbekistan 1, Kyrgyzstan 1, … |

## Branches

* `env/biome-framework`: the generic engine + `boreal.gd` (same Scandinavian look), tests, census. **Merge first.**
* `env/<biome>` (stacked on the framework): one `biomes/<biome>.gd`, its `pipeline/blender/env_<biome>.py` models
  (procedural, original) and `evidence/env-<biome>/`. Each branch touches only its own files, so they can merge in any
  order once the framework is in.
