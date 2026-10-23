#!/usr/bin/env python3
"""Offline preview mix (< 2 min) of the Iron Crowns audio set, mimicking the in-game flow:
campaign map music -> diplomatic tension (war declared sting) -> battle (signal, volleys, cannon,
charge, melee, ambience beds) -> victory sting -> back to campaign.
Uses the rendered WAVs in build/audio_wav (run build_audio.py first). Output: out/audio_preview.ogg
This is a listening aid only; in-game mixing is done live by scripts/audio/audio_manager.gd."""
import os, subprocess, wave
import numpy as np
from synthlib import SR, limit

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WAV = os.path.join(ROOT, "build", "audio_wav")
OUT = os.path.join(ROOT, "out")
T = 112.0
mix = np.zeros((int(T * SR), 2))
rng = np.random.default_rng(7)


def load(name):
    with wave.open(os.path.join(WAV, name + ".wav")) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32767
        return a.reshape(-1, w.getnchannels())


def stereo(a, pan=0.0):
    if a.shape[1] == 2:
        return a
    th = (pan + 1) * np.pi / 4
    return np.hstack([a * np.cos(th), a * np.sin(th)])


def add(name, t, gain_db=0.0, pan=0.0, length=None, fade_in=0.0, fade_out=0.0, loop=False, offset=0.0):
    a = stereo(load(name), pan) * 10 ** (gain_db / 20)
    if offset:
        a = np.roll(a, -int(offset * SR), axis=0)
    if length is not None:
        n = int(length * SR)
        a = np.tile(a, (n // len(a) + 1, 1))[:n] if loop else a[:n]
    a = a.copy()
    if fade_in:
        k = min(len(a), int(fade_in * SR)); a[:k] *= np.sin(np.linspace(0, np.pi / 2, k))[:, None]
    if fade_out:
        k = min(len(a), int(fade_out * SR)); a[-k:] *= np.cos(np.linspace(0, np.pi / 2, k))[:, None]
    s = int(t * SR); e = min(len(mix), s + len(a))
    mix[s:e] += a[:e - s]


MUS = -2.0  # music level for music-only sections (the preview is normalised for listening)
# In game the Music bus sits about 8 dB under the SFX bus at default volumes (music 0.6, SFX 0.85), and the battle
# track has a further -3 dB trim. The battle section reproduces that relative balance against the SFX.
BATTLE_MUS = MUS - 3.0 - 8.0
# --- campaign map (0-28 s) with UI feedback
add("music_campaign", 0.0, MUS, length=28.0, fade_in=2.0, fade_out=3.0)
for t, n in [(6.0, "ui_select"), (8.5, "ui_open"), (9.6, "ui_click"), (10.4, "ui_coins"), (11.5, "ui_close"),
             (14.0, "ui_select"), (15.2, "ui_order"), (16.0, "ui_march"), (20.0, "ui_confirm")]:
    add(n, t, -4.0)
add("march_loop", 16.0, -20.0, length=6.0, fade_in=1.0, fade_out=2.0, loop=True)
# --- diplomacy / war declared (25-50 s): tension music, war sting with ducking
add("music_tension", 25.0, MUS, length=26.5, fade_in=2.5, fade_out=1.4)
add("ui_open", 27.0, -4.0); add("ui_click", 30.0, -4.0); add("ui_confirm", 31.0, -4.0)
add("sting_war", 32.0, -1.0)
add("ui_order", 42.0, -4.0); add("ui_march", 43.0, -4.0)
# --- battle (50-98 s)
B = 50.0
add("music_battle", B, BATTLE_MUS, length=48.0, fade_in=1.4, fade_out=2.0)
add("amb_wind", B, -16.0, length=48.0, fade_in=2.0, fade_out=3.0, loop=True)
add("amb_battle_powder", B + 2, -10.0, length=46.0, fade_in=3.0, fade_out=3.0, loop=True)
add("bugle_call", B + 1.0, -4.0, pan=-0.3)
add("march_loop", B + 2.0, -12.0, length=14.0, fade_in=1.5, fade_out=2.0, loop=True)
t = B + 8.0
while t < B + 44:
    side = rng.choice([-0.6, 0.5])
    if rng.random() < 0.55:
        add(f"musket_volley_{rng.integers(1, 4)}", t, -3.0 + rng.uniform(-2, 1), pan=side)
        add(f"ball_impact_{rng.integers(1, 4)}", t + 0.35, -12.0, pan=-side * 0.7)
    else:
        add(f"musket_volley_far_{rng.integers(1, 3)}", t, -5.0, pan=side * 0.8)
    if rng.random() < 0.4:
        add(f"cannon_{rng.integers(1, 4)}", t + rng.uniform(0.3, 1.5), -4.0, pan=rng.uniform(-0.8, 0.8))
        add(f"ball_impact_{rng.integers(1, 4)}", t + 2.0, -9.0, pan=rng.uniform(-0.5, 0.5))
    if rng.random() < 0.25:
        add(f"cannon_far_{rng.integers(1, 3)}", t + rng.uniform(0, 2), -6.0, pan=rng.uniform(-1, 1))
    if rng.random() < 0.3:
        add(f"musket_shot_{rng.integers(1, 4)}", t + rng.uniform(0, 2), -8.0, pan=rng.uniform(-1, 1))
    t += rng.uniform(1.6, 3.2)
add("whistle", B + 24.0, -10.0, pan=0.4)
add("crowd_charge_1", B + 26.0, -3.0, pan=0.3); add("hooves_charge_1", B + 26.5, -4.0, pan=0.5)
add("melee_loop", B + 29.0, -8.0, length=12.0, fade_in=1.0, fade_out=2.5, loop=True)
for k in range(8):
    add(f"sword_clash_{rng.integers(1, 5)}", B + 29.5 + k * 1.3 + rng.uniform(0, 0.6), -8.0, pan=rng.uniform(-0.6, 0.6))
add("explosion_1", B + 36.0, -4.0, pan=-0.4)
add("crowd_rout_1", B + 40.0, -6.0, pan=-0.5)
add("crowd_cheer_1", B + 44.5, -5.0, pan=0.2)
# --- victory sting, then campaign returns
add("sting_victory", 97.5, -1.0)
add("music_campaign", 104.0, MUS, length=8.0, fade_in=3.0, fade_out=3.5, offset=30.0)

y = limit(mix, -1.0, look=0.004, release=0.2)
os.makedirs(OUT, exist_ok=True)
raw = (np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()
dst = os.path.join(OUT, "audio_preview.ogg")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                "-c:a", "libvorbis", "-q:a", "5", "-map_metadata", "-1", "-fflags", "+bitexact", dst], input=raw, check=True)
print(dst, f"{len(y) / SR:.1f} s", f"{os.path.getsize(dst) / 1024:.0f} KiB",
      f"peak {20 * np.log10(np.abs(y).max()):.2f} dBFS")
