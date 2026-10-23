#!/usr/bin/env python3
"""Objective checks on the *encoded* game audio (decoded back from Ogg with ffmpeg):
  - decoded true sample peak (no clipping after Vorbis encoding)
  - loop seams: high-frequency click energy across the wrap point vs. the same measure at
    200 random interior points (a seamless loop's seam is indistinguishable from interior audio)
  - level jump across the seam (RMS 100 ms before/after) vs. the largest such jump at 400 interior points
Usage: python3 pipeline/audio/analyze_audio.py [--json out.json]
Exit code 1 if any check fails."""
import json, os, subprocess, sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAME = os.path.join(ROOT, "game")
SR = 44100


def decode(path, ch):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64).reshape(-1, ch)


def hf_click(seg):
    # second difference emphasises clicks/discontinuities; energy in a 256-sample window
    d2 = np.diff(seg, 2)
    return float(np.sqrt(np.mean(d2 ** 2)))


def seam_stats(a, rng):
    w = 128
    seam = np.concatenate([a[-w:], a[:w]])
    s = hf_click(seam)
    pos = rng.integers(w, len(a) - w, 200)
    inner = np.array([hf_click(a[p - w:p + w]) for p in pos])
    pct = float((inner < s).mean() * 100.0)   # percentile of seam among interior points
    r = int(0.1 * SR)
    jump = lambda x, p: 20 * np.log10((np.sqrt(np.mean(x[p:p + r] ** 2)) + 1e-9) / (np.sqrt(np.mean(x[p - r:p] ** 2)) + 1e-9))
    lvl = jump(np.concatenate([a[-r:], a[:r]]), r)
    ijump = max(abs(jump(a, p)) for p in rng.integers(r, len(a) - r, 400))
    return s, float(np.percentile(inner, 50)), float(inner.max()), pct, float(lvl), float(ijump)


def main():
    man = json.load(open(os.path.join(GAME, "audio", "audio_manifest.json")))
    rng = np.random.default_rng(1)
    out = {}; fails = []
    for name, m in sorted(man.items()):
        st = decode(os.path.join(GAME, m["file"].replace("res://", "")), m["channels"])
        pk = float(np.abs(st).max()); a = st.mean(axis=1)
        info = {"decoded_peak_dbfs": round(20 * np.log10(pk + 1e-12), 2), "seconds": round(len(a) / SR, 3)}
        if pk >= 0.999:
            fails.append(f"{name}: decoded peak {pk:.3f}")
        if m["loop"]:
            s, med, mx, pct, lvl, ijump = seam_stats(a, rng)
            info.update({"seam_click": round(s, 5), "interior_median": round(med, 5), "interior_max": round(mx, 5),
                         "seam_percentile": round(pct, 1), "seam_level_jump_db": round(lvl, 2),
                         "interior_max_jump_db": round(ijump, 2)})
            # seam must look like ordinary interior audio: no stronger click and no bigger level step
            ok = s <= mx and abs(lvl) <= max(3.0, ijump)
            info["seam_ok"] = ok
            if not ok:
                fails.append(f"{name}: seam click {s:.4f} (interior max {mx:.4f}), level jump {lvl:.1f} dB (interior max {ijump:.1f})")
            print(f"{name:22s} loop seam: click pct {pct:5.1f}  jump {lvl:+5.1f} dB (interior max {ijump:4.1f})  peak {info['decoded_peak_dbfs']:6.2f} dBFS  {'OK' if ok else 'FAIL'}")
        out[name] = info
    print(f"{len(out)} files decoded; max decoded peak {max(v['decoded_peak_dbfs'] for v in out.values()):.2f} dBFS")
    if "--json" in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    if fails:
        print("FAILURES:\n  " + "\n  ".join(fails)); sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
