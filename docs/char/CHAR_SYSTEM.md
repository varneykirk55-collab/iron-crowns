# Character system: one human, many eras

Status: stage 5 of the c19v2 prototype (branch `proto/c19-line-v2`). Only the **1800 French line fusilier**
(`c19v2_line`) is built. The other eras below are **kit lists only** (from `ref/kirk_reference_sheet.png`), so
that the architecture is checked against them before anything else gets modelled.

## Layers

```
base human (era-independent)        uniform kit (per era / nation / role)        material library (shared)
--------------------------------    -----------------------------------------    -----------------------------
MakeHuman CC0 hm08 mesh + targets   garment shells: coat / tunic / doublet ...   wool, linen, canvas, leather,
  macro build (muscle, weight,      headgear, footwear, legwear                    hide, pipeclay, brass, steel,
  height, age, race)                load-bearing: belts, straps, pouches, packs    iron, wood, skin, eye, hair,
posed into OUR frozen rest pose      weapon (prop bone; weapon_tip)                 fur, felt, horn, cotton-camo
skinned to OUR frozen BONES         what the kit hides of the body (mask)        each = slot palette + roughness /
head, eyes, hands = real geometry   kit slots -> material ids                      metal / bump / detail recipe
skin / eye albedo (CC0) + brows     per-kit fold / seam / wear recipe              (detail_nodes + shader vmat)
```

* **Rig and animation are shared by every era.** All kits skin to `char_rig.BONES` (names + rest pose frozen,
  leaf helpers only); VAT rows 0-263 keep their order and clips are only appended (Rob's interface,
  docs/char/PROTO_V2.md). A pikeman, an archer and a rifleman differ in kit and in the `prop` mesh, not in the
  skeleton. Two-handed props (pike, bow, rifle) use the same `prop` bone and need their own clips from Rob.
* **Base human** (`pipeline/human/`): `mh_base.Human(muscle, weight, height, ...)` applies the MakeHuman
  targets. `mh_pose.PosedHuman` re-aims the MakeHuman skeleton onto our joint positions (arms down, fists
  closed round a 35 mm grip, upright neck), skins it with MakeHuman's own weights and sums those onto our bones.
  `human_mh.py` turns this into Blender parts: `head` (cut inside the collar line), `eyes` (proxy) and `hands`
  (cut inside the cuff). An era kit chooses **which body parts stay visible**. For example, 1300 mail
  hides the arms but shows the hands, while 1980 gloves replace the hands with a glove part that uses the same
  weights.
* **Uniform kit** (`pipeline/blender/char_v2.py` today, one module per kit later): garment shells built
  round the base body. Today the coat, breeches and gaiters are still the parametric v2 sweep; stage 5 phase 2
  derives them from the MakeHuman body as offset shells. Each kit provides `build_kit(hi)` (bake-only detail
  on the high-poly copy), a `RULES` table (part -> weight rule: `own` MakeHuman weights / rigid bone /
  transfer from the body / tail), `body_slot` (where each slot sits on the shell) and fold / seam recipes.
* **Material library** (`char_body.SLOT_NAMES / PALETTE`, `char_v2.SLOT_MAT`, `detail_nodes`, shader `vmat`):
  32 slots map to 16 materials. Slot colours are per nation (team colour = slot 0). Materials are
  era-agnostic. New eras add slots and materials, but never renumber existing ones.
* **Bake / runtime** stay identical: one 2048 atlas per kit with normal + AO, slot-id + detail, and painted
  albedo (skin / eyes, later camo / heraldry). LOD0 is 8-12k tris, mid ~2k, far ~700, all on the same bones.

## Per-era kit lists (from the reference sheet)

Legend: **base** = base-human parts left visible; **new** = slots or materials the library does not have yet.

### 1300: medieval infantry (pikemen)
* base: head (bearded), hands; legs inside hose and boots
* kettle hat / bascinet (steel) with mail aventail over the shoulders
* padded gambeson / quilted aketon, knee length (linen, **new: quilting fold recipe**)
* surcoat or tabard in livery (blue / yellow halves), with a yellow sash or baldric (team colour = surcoat)
* plate or splinted vambraces and spaulders on the upper arm (steel), leather gauntlets
* belt with pouch and dagger, knife at the hip
* woollen hose and turn-over leather boots
* weapon: pike or spear ~3-5 m (`prop`; **needs new clips**: pike-stand / level)

### 1300: medieval archers
* base: head, hands (no gloves on the draw hand), forearms in bracers
* kettle hat, padded jack (gambeson) in blue or grey wool, with a crossed baldric and quiver belt
* bracer (leather), leg-hose with ankle boots, belt pouch
* quiver on the back or hip with arrows (**new: fletching card**), longbow ~1.8 m (`prop`; **needs bow clips**)

### 1500: pike and shot
* base: head (moustache), hands
* morion or kettle helmet (steel), soft bonnet variant
* slashed doublet and puffed breeches in mixed livery colours (red / yellow / blue; **new: slashing / puff
  fold recipe**), shirt collar
* crossed bandolier ("twelve apostles" powder flasks, **new: small-prop instancing**), sword belt with hanger
* hose / stockings, knee boots
* weapon: arquebus / musket with matchcord (`prop`, existing musket clips are close), or pike

### 1800: Napoleonic line infantry (**built: c19v2_line**)
* base: head (sideburns, cropped hair), hands
* shako with plate, cockade, pompom / plume; habit-veste coat with white lapels, red collar / cuffs / turnbacks,
  coat tails
* white waistcoat, white breeches, black knee gaiters, shoes
* pipeclayed crossbelts, cartridge box, briquet sabre + bayonet scabbard
* calfskin knapsack with greatcoat roll
* Charleville musket with bayonet (`prop`, `weapon_tip`)

### 1914: industrial infantry
* base: head (moustache), hands
* steel helmet (Brodie / Adrian / Stahlhelm silhouettes per nation)
* wool service tunic with patch pockets, stand-and-fall collar, trousers
* puttees wound round the lower leg (**new: spiral wrap recipe**), ankle boots
* leather or webbing Y-straps, ammunition pouches on the belt, haversack, entrenching tool, water bottle, small pack
* bolt-action rifle with bayonet (`prop`; existing musket clips are close)

### 1980: modern infantry
* base: head (stubble, beard), hands **inside gloves** (glove part, same weights)
* kevlar helmet with camo cover and NVG mount
* camo field jacket and trousers (**new: printed camo albedo**, so the albedo bake is used beyond skin),
  knee pads
* plate carrier / load-bearing vest with magazine pouches (**new: nylon / cordura material**), backpack
* combat boots
* assault rifle with optic and sling (`prop`; **needs carbine clips**: ready / aim; `weapon_tip` = muzzle)

## What a new era costs

1. A kit module (garment shells + gear) and its `RULES` / `body_slot` / fold recipe.
2. Any new slots or materials appended to the library.
3. The visible base-human parts chosen (head variant via targets: age, beard via albedo, moustache).
4. Clips from Rob if the prop handling differs (appended rows only).

The base human, rig, VAT layout, bake and shader are reused unchanged.
