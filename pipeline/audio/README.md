# Audio pipeline (music + SFX)

All game audio is original and procedurally synthesized here (numpy DSP). No samples and no AI models
are used. See `AUDIO_LICENSES.md` at the repo root.

| File | Role |
|---|---|
| `synthlib.py` | DSP core: envelopes, FFT filters (zero-phase, linear or circular for loops), algorithmic reverb IR, convolution, look-ahead limiter, loop crossfade, WAV writer |
| `instruments.py` | strings/brass/horn/woodwind voices, timpani, snare, bass drum, cymbal |
| `music.py` | the score: `music_campaign` (66 bpm), `music_tension` (56 bpm), `music_battle` (132 bpm), plus stings `sting_victory`, `sting_defeat`, `sting_war`, `sting_era`. Loops are rendered circularly, so reverb tails wrap into the loop start |
| `sfx.py` | weapons (by era), impacts, explosions, crowds (non-verbal), hooves, melee, signals, ambience beds, loops, UI |
| `build_audio.py` | registry (name → category, generator, fixed seed, loop flag). Renders WAVs to `build/audio_wav/` (gitignored), encodes Ogg Vorbis (music q5 stereo, SFX q4 mono) to `game/audio/{music,sfx}/`, writes `game/audio/audio_manifest.json` |
| `analyze_audio.py` | objective QA on the *encoded* files: decoded peak < 0 dBFS, and loop seams (click energy + level step at the wrap vs. interior audio) |
| `make_preview.py` | offline < 2 min preview mix (campaign → tension → battle → victory) to `out/audio_preview.ogg` |

```bash
python3 pipeline/audio/build_audio.py            # all assets (~30 s with 8 procs); deterministic
python3 pipeline/audio/build_audio.py cannon      # only names containing "cannon"
python3 pipeline/audio/analyze_audio.py           # exit 1 on clipping or a bad loop seam
python3 pipeline/audio/make_preview.py
tools/godot --headless --path game --import       # refresh .import after re-rendering
tools/godot --headless --path game res://tests/test_audio.tscn   # 28 runtime checks
```
Requires python3, numpy and ffmpeg (libvorbis). If they aren't available, the committed Oggs are used as they are.

## Runtime (`game/scripts/audio/audio_manager.gd`, autoload `Audio`)
- **Buses** (`game/audio/default_bus_layout.tres`; `ensure_buses()` recreates them if missing):
  - Master has a HardLimiter.
  - Music → Master.
  - SFX → Master, with a gentle Compressor (threshold -8 dB, ratio 2.5, 3 ms attack, 220 ms release) and a HardLimiter at -1.5 dB. A harder setting (-16 dB / 3:1) took about 5 dB off every single volley and buried the battle SFX under the music.
  - Ambience → SFX and UI → SFX, so a single SFX slider controls all three.
- **Settings:** Music and SFX sliders live in the in-game Settings menu (`hud.gd` → `Audio.build_settings_rows`) and are saved to `user://audio.cfg`. Bus dB = base + 20·log10(v²), and 0 mutes the bus. Base is -2 dB for Music and 0 dB for SFX. Defaults are music 0.6 and SFX 0.85, so at default settings the Music bus sits about 8 dB below the SFX bus.
- **Music:**
  - The mood is chosen automatically: *battle* while a BattleView is shown; *tension* for 30 s after a war involving the player, or while the diplomacy, deploy or popup windows are open; *campaign* otherwise.
  - Moods switch with an equal-power crossfade between two players. A mood is held for at least 6 s, except that switching into or out of battle is immediate.
  - Campaign and tension resume from where they left off.
  - Stings play on top and duck the music by 9 dB.
  - Per-track trim `TRACK_DB` (battle -3 dB) is applied on top of the crossfade, so the dense battle score leaves room for gunfire.
- **SFX:**
  - Battle sounds come from the BattleSim event list, read-only through the manager's own cursor. Weapon sounds are chosen by unit kind and era (`weapon_for`): bows, then bombards and muskets, then cannon, then rifles only from the c20 era, then tank guns and howitzers. There are no automatic weapons.
  - Positional `AudioStreamPlayer3D` pool of 24 (`unit_size` 110 m, matching the battle camera distance), plus a 2D pool of 8. Density gain: −2 dB per doubling of recent sounds (window of 6).
  - Each category has a voice cap and a minimum retrigger gap (musket 6 voices, cannon 4, …). At the cap, the oldest voice in the category is stolen; when the pool is full, voices are stolen by priority.
  - Dense gunfire is turned down by up to -3·log2(1+n/4) dB, and each play gets a random ±8% pitch and ±2 dB level.
  - Beyond 260 m, the distant variant of a sound is used.
  - Ambience beds play by era, along with march, melee and engine loops that scale with unit counts.
- **Campaign UI:** clicks, window open/close, selection, march orders, errors, coins and confirmations, plus stings for war and era changes.
- **`--audio=off`** disables the whole system. Tests confirm that battle outcomes are identical with audio on and off.
