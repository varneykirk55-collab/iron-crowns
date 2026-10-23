#!/usr/bin/env python3
"""Build every Iron Crowns audio asset from source (procedural synthesis -> WAV -> Ogg Vorbis).

Usage (from the checkout root):
  python3 pipeline/audio/build_audio.py            # build all
  python3 pipeline/audio/build_audio.py musket     # only assets whose name contains 'musket'
Outputs: game/audio/music/*.ogg, game/audio/sfx/*.ogg, game/audio/audio_manifest.json
Intermediate WAVs: build/audio_wav/ (git-ignored). Deterministic: fixed seeds per asset.
Requires: python3 + numpy, ffmpeg with libvorbis. No network, no samples, no AI models.
"""
import hashlib, json, os, subprocess, sys
from multiprocessing import Pool
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synthlib as S
import music as M
import sfx as X

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WAV = os.path.join(ROOT, "build", "audio_wav")
GAME = os.path.join(ROOT, "game", "audio")


def R(seed):
    return np.random.default_rng(seed)


# name -> (category, builder(seed) -> np.array, seed, loop, description)
A = {}


def reg(name, cat, fn, seed, loop=False, desc=""):
    A[name] = (cat, fn, seed, loop, desc)


for k, f in M.TRACKS.items():
    reg(k, "music", lambda s, f=f: f(), 0, True, f.__doc__ or "")
for k, f in M.STINGS.items():
    reg(k, "music", lambda s, f=f: f(), 0, False, "")

for i in range(3):
    reg(f"musket_shot_{i+1}", "sfx", lambda s: X.musket_shot(R(s)), 100 + i, desc="flintlock musket, single shot")
    reg(f"musket_volley_{i+1}", "sfx", lambda s: X.volley(R(s), X.musket_shot), 110 + i, desc="company musket volley (black powder)")
    reg(f"rifle_volley_{i+1}", "sfx", lambda s: X.volley(R(s), X.rifle_shot, (6, 11), 0.6), 120 + i, desc="bolt-action rifle section volley (no automatic fire)")
    reg(f"cannon_{i+1}", "sfx", lambda s: X.cannon(R(s)), 130 + i, desc="muzzle-loading field gun")
    reg(f"explosion_{i+1}", "sfx", lambda s: X.explosion(R(s)), 140 + i, desc="shell burst with debris")
    reg(f"ball_impact_{i+1}", "sfx", lambda s: X.ball_impact(R(s)), 150 + i, desc="round shot striking earth")
for i in range(2):
    reg(f"musket_volley_far_{i+1}", "sfx", lambda s: X.volley(R(s), X.musket_shot, far=True), 160 + i, desc="distant musket volley")
    reg(f"rifle_volley_far_{i+1}", "sfx", lambda s: X.volley(R(s), X.rifle_shot, (6, 11), 0.6, far=True), 165 + i, desc="distant rifle volley")
    reg(f"cannon_far_{i+1}", "sfx", lambda s: X.cannon(R(s), True), 170 + i, desc="distant cannon")
    reg(f"bombard_{i+1}", "sfx", lambda s: X.cannon(R(s), False, 1.35, "bombard"), 175 + i, desc="medieval bombard (stone shot)")
    reg(f"howitzer_{i+1}", "sfx", lambda s: X.howitzer(R(s)), 180 + i, desc="howitzer / modern field artillery")
    reg(f"tank_gun_{i+1}", "sfx", lambda s: X.tank_gun(R(s)), 185 + i, desc="tank main gun with breech clank")
    reg(f"explosion_far_{i+1}", "sfx", lambda s: X.explosion(R(s), True), 190 + i, desc="distant explosion")
    reg(f"shell_whistle_{i+1}", "sfx", lambda s: X.incoming_whistle(R(s)), 195 + i, desc="shell in flight (c20/modern)")
    reg(f"bow_volley_{i+1}", "sfx", lambda s: X.bow_volley(R(s)), 200 + i, desc="longbow volley")
    reg(f"pistol_{i+1}", "sfx", lambda s: X.pistol_shot(R(s)), 205 + i, desc="cavalry pistol/carbine")
    reg(f"crowd_charge_{i+1}", "sfx", lambda s: X.crowd(R(s), 2.6, 40, "a", (100, 200), 0.3, 0.6), 210 + i, desc="nonverbal charge shout")
    reg(f"hooves_charge_{i+1}", "sfx", lambda s: X.hooves(R(s), 3.0, 22), 215 + i, desc="cavalry gallop")
for i in range(4):
    reg(f"sword_clash_{i+1}", "sfx", lambda s: X.sword_clash(R(s)), 220 + i, desc="melee steel clash")
reg("howitzer_far_1", "sfx", lambda s: X.howitzer(R(s), True), 230, desc="distant howitzer")
reg("crowd_cheer_1", "sfx", lambda s: X.crowd(R(s), 3.4, 48, "o", (110, 210), 0.25, 0.4), 231, desc="nonverbal victory cheer")
reg("crowd_rout_1", "sfx", lambda s: X.crowd(R(s), 2.8, 30, "u", (120, 230), -0.15, 1.0), 232, desc="nonverbal cry of a breaking unit")
reg("bugle_call", "sfx", lambda s: X.bugle_call(R(s)), 240, desc="original bugle call (c19 battle start)")
reg("war_horn", "sfx", lambda s: X.war_horn(R(s)), 241, desc="signal horn (medieval/early-modern battle start)")
reg("whistle", "sfx", lambda s: X.whistle(R(s)), 242, desc="officer's whistle (c20/modern battle start)")
reg("march_loop", "sfx", lambda s: X.march_loop(R(s)), 250, True, "infantry column marching in step")
reg("melee_loop", "sfx", lambda s: X.melee_loop(R(s)), 251, True, "hand-to-hand fighting bed")
reg("engine_loop", "sfx", lambda s: X.engine_loop(R(s)), 252, True, "tracked vehicle engine")
reg("amb_battle_powder", "sfx", lambda s: X.amb_battle(R(s), 24.0, "powder"), 253, True, "distant black-powder battle bed")
reg("amb_battle_modern", "sfx", lambda s: X.amb_battle(R(s), 24.0, "modern"), 254, True, "distant 20th-century battle bed")
reg("amb_battle_medieval", "sfx", lambda s: X.amb_battle(R(s), 24.0, "medieval"), 255, True, "distant medieval melee bed")
reg("amb_wind", "sfx", lambda s: X.wind_loop(R(s), 20.0), 256, True, "open-field wind")
reg("ui_click", "ui", lambda s: X.ui_click(R(s)), 300, desc="button tap")
reg("ui_select", "ui", lambda s: X.ui_select(R(s)), 301, desc="province/army selected")
reg("ui_open", "ui", lambda s: X.ui_paper(R(s)), 302, desc="panel open (parchment)")
reg("ui_close", "ui", lambda s: X.ui_paper(R(s), True), 303, desc="panel close")
reg("ui_confirm", "ui", lambda s: X.ui_confirm(R(s)), 304, desc="seal + chime: action confirmed")
reg("ui_error", "ui", lambda s: X.ui_error(R(s)), 305, desc="action refused")
reg("ui_coins", "ui", lambda s: X.ui_coins(R(s)), 306, desc="purchase")
reg("ui_order", "ui", lambda s: X.ui_order(R(s)), 307, desc="order acknowledged")
reg("ui_march", "ui", lambda s: X.drum_cadence(R(s)), 308, desc="march order: drum cadence + steps")


def build_one(name):
    cat, fn, seed, loop, desc = A[name]
    x = fn(seed)
    x = np.asarray(x, dtype=np.float64)
    if cat != "music" and x.ndim == 2:
        x = x.mean(1)
    os.makedirs(WAV, exist_ok=True)
    wav = os.path.join(WAV, name + ".wav")
    S.write_wav(wav, x)
    sub = "music" if cat == "music" else "sfx"
    os.makedirs(os.path.join(GAME, sub), exist_ok=True)
    ogg = os.path.join(GAME, sub, name + ".ogg")
    q = "5" if cat == "music" else "4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", q,
                    "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", ogg], check=True)
    pk = float(np.max(np.abs(x)))
    info = {"file": f"res://audio/{sub}/{name}.ogg", "category": cat, "loop": loop, "seconds": round(len(x) / S.SR, 3),
            "channels": 1 if x.ndim == 1 else 2, "peak_dbfs": round(20 * np.log10(pk + 1e-12), 2),
            "rms_dbfs": round(S.rms_db(x), 2), "bytes": os.path.getsize(ogg),
            "sha256": hashlib.sha256(open(ogg, "rb").read()).hexdigest(), "seed": seed, "desc": desc.strip().split("\n")[0],
            "source": "original procedural synthesis, pipeline/audio (no samples)"}
    if loop:
        a = x if x.ndim == 1 else x.mean(1)
        w = 256
        jump = float(np.abs(a[0] - a[-1]))
        typ = float(np.median(np.abs(np.diff(a))))
        e_end = float(np.sqrt(np.mean(a[-S.secs(0.25):] ** 2))); e_start = float(np.sqrt(np.mean(a[:S.secs(0.25)] ** 2)))
        info["loop_check"] = {"boundary_step": round(jump, 5), "median_step": round(typ, 5),
                              "rms_end_db": round(20 * np.log10(e_end + 1e-12), 1), "rms_start_db": round(20 * np.log10(e_start + 1e-12), 1)}
    print(f"{name:24s} {info['seconds']:7.2f}s  peak {info['peak_dbfs']:6.2f} dBFS  {info['bytes']/1024:7.1f} KiB", flush=True)
    return name, info


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    names = [n for n in A if flt in n]
    man_path = os.path.join(GAME, "audio_manifest.json")
    man = json.load(open(man_path)) if os.path.exists(man_path) else {}
    with Pool(min(8, os.cpu_count() or 2)) as p:
        for name, info in p.imap_unordered(build_one, sorted(names, key=lambda n: A[n][0] != "music")):
            man[name] = info
    man = {k: man[k] for k in sorted(man) if k in A}
    json.dump(man, open(man_path, "w"), indent=1)
    tot = sum(v["bytes"] for v in man.values())
    print(f"{len(man)} assets, {tot/1024/1024:.2f} MiB total")


if __name__ == "__main__":
    main()
