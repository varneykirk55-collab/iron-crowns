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

## c19_hussar (v3_c19_hussar): rider on the existing cavalry rig
The rider is skinned to the existing cavalry rig (bones and clips untouched). That rig has no rider hand or leg bones,
so hands ride rigidly on the forearm bones and legs on the body bone. Needed (only if Rob wants them):
- carbine: a slung carbine prop + `cav_carbine_present` / `cav_carbine_fire` from the saddle (there is no carbine clip now)
- rider hand bones (or a hand pose per clip) so the bridle hand can close on the reins and the sabre hand can turn the blade
- a rider-arm rest pose with less elbow bend (the current ~140deg bend pinches the dolman sleeve under LBS)

## Coming with later kits (filled in as each kit lands)
- pike (1300 pikeman, 1500 pikeman): port, charge (level at shoulder and at hip), brace against cavalry (butt to the foot)
  - v3_med_pike (kit 4) currently plays the musket clips: idle / walk shoulder the pike fine and melee (charge thrust)
    reads as a pike thrust, but `fire` (prime / ram) makes no sense for a pikeman. Please give pike units a fire-row
    replacement (e.g. `pike_brace` or a second thrust) and a pike `port` for run. Pike prop is 3.57 m (prop-local y
    -0.45..3.12, tip 3.12), so the levelled pose needs the rear hand near the butt.
- bow (1300 archer): nock, draw, loose, and an idle with the arrow in the bow; the left hand holds the bow grip
