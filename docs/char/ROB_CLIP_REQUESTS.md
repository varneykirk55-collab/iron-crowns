# Clip requests for Rob (eras v3)

The v3 kits keep the existing clips (VAT rows 0-263, clip names and order unchanged); nothing has been animated
here. These are the props that the existing clips only approximate, with the clips needed to fit them properly.
All the props hang on the existing `prop` bone with `weapon_tip` at the working end, so new clips can be added as
new rows after 263 without breaking the current ones.

## c19_artillery (v3_c19_artillery): rammer / sponge staff
Prop: a 2.82 m staff on the prop bone, rammer head at prop-local +y 1.55..1.70 (weapon_tip at (0, 1.70, 0)),
sheepskin sponge at -0.95..-1.12. It currently uses the existing 'rammer' style clips (order / carry / run / work).
Needed:
- `art_sponge`: sponge in and out of the bore, two twists, from the muzzle side
- `art_ram`: reverse the staff, ram the charge home (two pushes), withdraw
- `art_stand_clear`: step back off the muzzle line with the staff upright (between shots)
- `art_handspike`: traverse the trail with a handspike (optional; it would need a handspike prop variant)
- the idle should rest the sponge end on the ground beside the right foot (the current idle is close)

## Coming with later kits (filled in as each kit lands)
- pike (1300 pikeman, 1500 pikeman): port, charge (level at shoulder and at hip), brace against cavalry (butt to the foot)
- bow (1300 archer): nock, draw, loose, and an idle with the arrow in the bow; the left hand holds the bow grip
- carbine (1800 hussar, if the rider moves onto char_rig): carry slung, present, fire from the saddle
