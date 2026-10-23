# Red/pink "flash" check — retreat_before_after.mp4 (2026-10-23, at 3c2474b/3bb4a41)

Report: the right half (flag on) shows every soldier glowing red/pink for ~2 s from HUD 00:31.

Result: we could not reproduce it as a rendering fault. No instance-colour, VAT or shader fault was found.

- Shader: `git diff a3f4f35 -- game/shaders` is empty.
- Instance COLOR: every anim-v1 `_put` passes white for the non-"sr" (vat.gdshader) models.
  Only "sr" models get BattleVisuals.xfade data, which matches legacy.
- Tabard colour (median RGB of the red mask, retreat_on vs retreat_off, t=0.5/1.4/1.8/2.6/4/8):
  - on: 195,67,57 / 196,69,57 / 195,69,57 / 198,69,55 / 195,69,57 / 177,58,44
  - off: 196,68,58 / 195,66,55 / 195,65,54 / 192,65,53 / 189,66,55 / 189,66,55
  - Same material response, so nothing is emissive or tinted.
- Pink-pixel count (r>200, b>140, g<190), per frame at 10 fps:
  - At most 15 px out of 90k in any *_on.mp4 (spear 11, musket 0, cavalry 6, charge 5, cavdie 42 vs 51 with the flag off).
  - There is no spike anywhere.
- What changes at ~00:31 is the number of red/green pixels. The right half has about 2x more,
  because flag-on soldiers face the enemy and the camera, so their lit tabard fronts show.
  Legacy soldiers face backwards and show dark backs.
  - At t≈1.9 s the green regiment does its all-at-once turn, so its bright fronts become dark backs.
    That is the "returns to normal" moment.
  - See stills/retreat_flashcheck_right_t0.6-3.4.png and stills/retreat_ba_t{1.4,3.0}_band.png.
- No code change was made, so hashes and tests are unchanged from HASH_CHECK.md.
