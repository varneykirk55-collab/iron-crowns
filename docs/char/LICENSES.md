# Character asset licences

Everything the character pipeline ships or bakes from is either authored in this repo (procedural Blender
scripts under `pipeline/blender`, `pipeline/human`) or comes from the sources below.

## MakeHuman system assets (CC0 1.0)

Source: MakeHuman community "system assets" pack, `makehuman_system_assets_cc0.zip`
(files2.makehumancommunity.org), the same data MPFB2 ships. MakeHuman relicensed its base mesh, targets
and system assets as **CC0 1.0 (public domain dedication)** in 2020; no attribution is required. We credit
it anyway.

Base mesh, targets, rig and weights come from the MPFB2 repository's bundled data (`src/mpfb/data`, covered by its
`LICENSE.ASSETS.md` = CC0 1.0); skins, eyes and eyebrows from the system-assets zip.
Copied under `pipeline/assets/mh/` (unchanged unless noted):

| file(s) | what | used for |
|---|---|---|
| `base.obj` | hm08 base mesh (13,380 verts) with UVs | head, neck and hands of the human base (stage 5a); body proxy later |
| `targets/` (macrodetails, universal, height) | morph targets | build: race / gender / age / muscle / weight / height |
| `rig.default.json`, `weights.default.json` | default skeleton + skin weights | weights, summed onto our frozen `char_rig.BONES` (`mh_pose.mh_to_ic_bone`) |
| `skin_middleage_caucasian_male.png` | skin albedo | base of the baked skin albedo |
| `skin_soldier.png` | **derived**: the skin above with the `eyebrow002` proxy texture composited into the skin UV (`pipeline/human/skin_prep.py`), plus painted cropped hair / sideburns | baked skin albedo |
| `eye_lowpoly.obj/.mhclo`, `eye_brown.png` | low-poly eye proxy + iris texture | eyes |
| `eyebrow002.obj/.mhclo/.png` | eyebrow card proxy | composited into `skin_soldier.png` only (no card geometry ships) |

The skin texture carries a small "PUBLICDOMAIN makehuman.org" mark (outside the face area).

## MPFB2

The MPFB2 Blender add-on's **assets** are CC0 (same pack as above). Its **code is GPLv3**: none of it is
copied, imported or run. The loaders here (`pipeline/human/mh_base.py`, `mh_clo.py`, `mh_pose.py`) are our
own minimal readers of the documented OBJ / target / .mhclo / rig JSON formats.

## Everything else

Uniform kit, materials, rig, animation and bakes: authored in this repo (same licence as the project).
