# Audio licenses — Iron Crowns

**Summary: every audio file shipped with Iron Crowns is original work created for this project.
No third-party recordings, samples, sample libraries, sound fonts, impulse responses, or
AI audio-generation models/services were used. No melody, motif or arrangement was taken from any
existing piece, film, or game.** There are no external assets, so there are no attribution,
share-alike, or non-commercial obligations.

## How the audio was made
- All 75 files (543 s, 6.25 MiB of Ogg Vorbis) are synthesized from code in
  `pipeline/audio/` (Python + numpy DSP): oscillators, filtered noise, physical-style envelopes,
  additive/subtractive "instruments" (strings, brass, horns, timpani, snare, bass drum), and a
  procedurally generated reverb impulse (decaying noise) — see `synthlib.py`, `instruments.py`,
  `music.py`, `sfx.py`.
- The music was composed note-by-note in code for this project (chord progressions, melodies and
  drum patterns are written out in `music.py`). It is instrumental only (no vocals) and does not quote
  any existing tune, anthem, march, or bugle call. Signals (`bugle_call`, `war_horn`, `whistle`) are
  original figures, not historical regulation calls.
- Crowd sounds are non-verbal: synthesized vowel-formant "voices" (shouts, cheers, groans), with no words and no speech recordings.
- Encoding: ffmpeg's libvorbis encoder (a tool, not a content source; its output carries no license
  restrictions). Metadata is stripped.
- Rendering is deterministic (fixed seeds per asset): `python3 pipeline/audio/build_audio.py`
  reproduces byte-identical files (sha256 values are recorded in `game/audio/audio_manifest.json`).
  This was checked on 2026-10-22: 75/75 hashes identical after a rebuild.

## License of the audio
Owned by the Iron Crowns project, like the rest of its original code and art. It may be redistributed
and used commercially as part of the game. No third-party rights are involved.

## External assets
None. If an external asset is ever added, it must be listed here with: file path, original URL,
author, license (CC0 preferred; attribution licenses only if the attribution is shipped in credits),
date retrieved, and any modifications. AI-generated audio must not be assumed to be rights-free.

## Fallback
If the generation pipeline can't be run (for example, no Python or numpy), the committed Ogg files are the
source of truth and the game uses them as they are. If an Ogg file is missing at runtime, `audio_manager.gd`
substitutes a short synthesized placeholder (silence for music) and logs it, so the game never
crashes on missing audio.

## Inventory
| File | Category | Seconds | Loop | KiB | Seed | Description |
|---|---|---:|:-:|---:|---:|---|
| `game/audio/music/music_battle.ogg` | music | 65.45 | yes | 1034.1 | 0 |  |
| `game/audio/music/music_campaign.ogg` | music | 101.82 | yes | 1564.9 | 0 |  |
| `game/audio/music/music_tension.ogg` | music | 64.29 | yes | 961.1 | 0 |  |
| `game/audio/music/sting_defeat.ogg` | music | 11.48 | no | 174.3 | 0 |  |
| `game/audio/music/sting_era.ogg` | music | 9.90 | no | 163.6 | 0 |  |
| `game/audio/music/sting_victory.ogg` | music | 9.37 | no | 151.7 | 0 |  |
| `game/audio/music/sting_war.ogg` | music | 7.22 | no | 112.2 | 0 |  |
| `game/audio/sfx/amb_battle_medieval.ogg` | sfx | 24.00 | yes | 188.4 | 255 | distant medieval melee bed |
| `game/audio/sfx/amb_battle_modern.ogg` | sfx | 24.00 | yes | 173.1 | 254 | distant 20th-century battle bed |
| `game/audio/sfx/amb_battle_powder.ogg` | sfx | 24.00 | yes | 172.1 | 253 | distant black-powder battle bed |
| `game/audio/sfx/amb_wind.ogg` | sfx | 20.00 | yes | 158.6 | 256 | open-field wind |
| `game/audio/sfx/ball_impact_1.ogg` | sfx | 1.64 | no | 16.7 | 150 | round shot striking earth |
| `game/audio/sfx/ball_impact_2.ogg` | sfx | 1.60 | no | 16.1 | 151 | round shot striking earth |
| `game/audio/sfx/ball_impact_3.ogg` | sfx | 1.69 | no | 17.3 | 152 | round shot striking earth |
| `game/audio/sfx/bombard_1.ogg` | sfx | 5.38 | no | 41.3 | 175 | medieval bombard (stone shot) |
| `game/audio/sfx/bombard_2.ogg` | sfx | 5.07 | no | 38.9 | 176 | medieval bombard (stone shot) |
| `game/audio/sfx/bow_volley_1.ogg` | sfx | 2.34 | no | 24.2 | 200 | longbow volley |
| `game/audio/sfx/bow_volley_2.ogg` | sfx | 2.33 | no | 24.1 | 201 | longbow volley |
| `game/audio/sfx/bugle_call.ogg` | sfx | 3.09 | no | 30.5 | 240 | original bugle call (c19 battle start) |
| `game/audio/sfx/cannon_1.ogg` | sfx | 3.91 | no | 31.3 | 130 | muzzle-loading field gun |
| `game/audio/sfx/cannon_2.ogg` | sfx | 3.90 | no | 30.8 | 131 | muzzle-loading field gun |
| `game/audio/sfx/cannon_3.ogg` | sfx | 4.06 | no | 31.8 | 132 | muzzle-loading field gun |
| `game/audio/sfx/cannon_far_1.ogg` | sfx | 4.33 | no | 28.0 | 170 | distant cannon |
| `game/audio/sfx/cannon_far_2.ogg` | sfx | 4.67 | no | 30.3 | 171 | distant cannon |
| `game/audio/sfx/crowd_charge_1.ogg` | sfx | 3.76 | no | 31.9 | 210 | nonverbal charge shout |
| `game/audio/sfx/crowd_charge_2.ogg` | sfx | 3.68 | no | 31.3 | 211 | nonverbal charge shout |
| `game/audio/sfx/crowd_cheer_1.ogg` | sfx | 4.31 | no | 35.6 | 231 | nonverbal victory cheer |
| `game/audio/sfx/crowd_rout_1.ogg` | sfx | 4.39 | no | 35.5 | 232 | nonverbal cry of a breaking unit |
| `game/audio/sfx/engine_loop.ogg` | sfx | 4.00 | yes | 38.6 | 252 | tracked vehicle engine |
| `game/audio/sfx/explosion_1.ogg` | sfx | 4.06 | no | 35.3 | 140 | shell burst with debris |
| `game/audio/sfx/explosion_2.ogg` | sfx | 4.06 | no | 34.9 | 141 | shell burst with debris |
| `game/audio/sfx/explosion_3.ogg` | sfx | 4.17 | no | 35.8 | 142 | shell burst with debris |
| `game/audio/sfx/explosion_far_1.ogg` | sfx | 4.45 | no | 29.5 | 190 | distant explosion |
| `game/audio/sfx/explosion_far_2.ogg` | sfx | 4.70 | no | 30.8 | 191 | distant explosion |
| `game/audio/sfx/hooves_charge_1.ogg` | sfx | 4.25 | no | 38.4 | 215 | cavalry gallop |
| `game/audio/sfx/hooves_charge_2.ogg` | sfx | 4.46 | no | 39.4 | 216 | cavalry gallop |
| `game/audio/sfx/howitzer_1.ogg` | sfx | 3.63 | no | 29.1 | 180 | howitzer / modern field artillery |
| `game/audio/sfx/howitzer_2.ogg` | sfx | 3.90 | no | 30.9 | 181 | howitzer / modern field artillery |
| `game/audio/sfx/howitzer_far_1.ogg` | sfx | 4.49 | no | 29.6 | 230 | distant howitzer |
| `game/audio/sfx/march_loop.ogg` | sfx | 4.00 | yes | 30.7 | 250 | infantry column marching in step |
| `game/audio/sfx/melee_loop.ogg` | sfx | 8.00 | yes | 78.6 | 251 | hand-to-hand fighting bed |
| `game/audio/sfx/musket_shot_1.ogg` | sfx | 1.50 | no | 14.7 | 100 | flintlock musket, single shot |
| `game/audio/sfx/musket_shot_2.ogg` | sfx | 1.52 | no | 15.3 | 101 | flintlock musket, single shot |
| `game/audio/sfx/musket_shot_3.ogg` | sfx | 1.65 | no | 15.9 | 102 | flintlock musket, single shot |
| `game/audio/sfx/musket_volley_1.ogg` | sfx | 2.11 | no | 21.3 | 110 | company musket volley (black powder) |
| `game/audio/sfx/musket_volley_2.ogg` | sfx | 1.86 | no | 19.3 | 111 | company musket volley (black powder) |
| `game/audio/sfx/musket_volley_3.ogg` | sfx | 2.01 | no | 20.7 | 112 | company musket volley (black powder) |
| `game/audio/sfx/musket_volley_far_1.ogg` | sfx | 3.69 | no | 25.0 | 160 | distant musket volley |
| `game/audio/sfx/musket_volley_far_2.ogg` | sfx | 3.48 | no | 23.5 | 161 | distant musket volley |
| `game/audio/sfx/pistol_1.ogg` | sfx | 1.34 | no | 13.5 | 205 | cavalry pistol/carbine |
| `game/audio/sfx/pistol_2.ogg` | sfx | 1.31 | no | 13.4 | 206 | cavalry pistol/carbine |
| `game/audio/sfx/rifle_volley_1.ogg` | sfx | 2.35 | no | 23.2 | 120 | bolt-action rifle section volley (no automatic fire) |
| `game/audio/sfx/rifle_volley_2.ogg` | sfx | 1.95 | no | 20.4 | 121 | bolt-action rifle section volley (no automatic fire) |
| `game/audio/sfx/rifle_volley_3.ogg` | sfx | 1.95 | no | 20.1 | 122 | bolt-action rifle section volley (no automatic fire) |
| `game/audio/sfx/rifle_volley_far_1.ogg` | sfx | 3.62 | no | 25.0 | 165 | distant rifle volley |
| `game/audio/sfx/rifle_volley_far_2.ogg` | sfx | 3.69 | no | 25.8 | 166 | distant rifle volley |
| `game/audio/sfx/shell_whistle_1.ogg` | sfx | 1.40 | no | 8.9 | 195 | shell in flight (c20/modern) |
| `game/audio/sfx/shell_whistle_2.ogg` | sfx | 1.40 | no | 8.6 | 196 | shell in flight (c20/modern) |
| `game/audio/sfx/sword_clash_1.ogg` | sfx | 1.54 | no | 14.1 | 220 | melee steel clash |
| `game/audio/sfx/sword_clash_2.ogg` | sfx | 1.47 | no | 13.5 | 221 | melee steel clash |
| `game/audio/sfx/sword_clash_3.ogg` | sfx | 1.40 | no | 12.6 | 222 | melee steel clash |
| `game/audio/sfx/sword_clash_4.ogg` | sfx | 1.42 | no | 13.4 | 223 | melee steel clash |
| `game/audio/sfx/tank_gun_1.ogg` | sfx | 3.76 | no | 30.1 | 185 | tank main gun with breech clank |
| `game/audio/sfx/tank_gun_2.ogg` | sfx | 3.77 | no | 30.1 | 186 | tank main gun with breech clank |
| `game/audio/sfx/war_horn.ogg` | sfx | 4.90 | no | 37.8 | 241 | signal horn (medieval/early-modern battle start) |
| `game/audio/sfx/whistle.ogg` | sfx | 1.88 | no | 18.5 | 242 | officer's whistle (c20/modern battle start) |
| `game/audio/sfx/ui_click.ogg` | ui | 0.08 | no | 4.3 | 300 | button tap |
| `game/audio/sfx/ui_close.ogg` | ui | 0.35 | no | 6.8 | 303 | panel close |
| `game/audio/sfx/ui_coins.ogg` | ui | 0.49 | no | 7.8 | 306 | purchase |
| `game/audio/sfx/ui_confirm.ogg` | ui | 1.06 | no | 8.2 | 304 | seal + chime: action confirmed |
| `game/audio/sfx/ui_error.ogg` | ui | 0.35 | no | 5.5 | 305 | action refused |
| `game/audio/sfx/ui_march.ogg` | ui | 2.83 | no | 27.1 | 308 | march order: drum cadence + steps |
| `game/audio/sfx/ui_open.ogg` | ui | 0.35 | no | 6.8 | 302 | panel open (parchment) |
| `game/audio/sfx/ui_order.ogg` | ui | 0.70 | no | 10.0 | 307 | order acknowledged |
| `game/audio/sfx/ui_select.ogg` | ui | 0.20 | no | 4.9 | 301 | province/army selected |
