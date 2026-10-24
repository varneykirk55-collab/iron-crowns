# Cavalry overhaul progress log (Rob)
Times are America/New_York.

- 2026-10-23 ~19:30 — 511bc5c M1: hx rig, proxy horses and bakes (knight, hussar, cuirassier).
- 2026-10-23 ~20:00 — d51e69e M2: CavV2 switch, hz_ driving, tests, demo/rec tools. a263833: spec v1.2 (sent to Bill).
- 2026-10-23 20:42 — dbc1b65 M3: regression (220/220, SIMHASH ×3 = main, audio 28/28, BATTLERESULT/reinforce = main in 3 modes) + perf vs main (README sections 1–2).
- 2026-10-23 21:06 — videos 1/8: knight_gaits_side, knight_turn_stop. Running in the background (nohup out/rec_all.sh, logs in /tmp/cavrec/*.log, done-list /tmp/cavrec/rec.log): knight_combat, knight_multi, then hussar ×4.
- 2026-10-23 21:08 — knight_combat.mp4 recorded + self-checked (charge, melee, horse fall/death, rider down OK). Side-cam gaits footage was backlit → added demo-only `--sideflip` (anim_demo.gd) to film the sun-lit flank; knight/hussar gaits_side will be re-recorded lit (out/rec_flip.sh queued after rec_all).
- 2026-10-23 21:10 — knight_multi.mp4 (4 knight regts vs 3 levies) recorded + checked: 4 units charge/melee/pursue, no rig pops; battle ends ~27 s so the tail is post-battle. Hussar set recording.
- 2026-10-23 21:23 — hussar_turn_stop.mp4 recorded + checked (the wheel turns, the trot is clean, the halt is square with riders seated). README now has the videos and known-issues sections.
