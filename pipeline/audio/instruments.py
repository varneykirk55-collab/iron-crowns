"""Procedural orchestral instruments (original synthesis, no samples).

Each function returns a mono float64 numpy array for one note/hit at SR.
"""
import numpy as np
from synthlib import (SR, secs, midi_hz, wt_osc, _table, maxh_for, adsr, expdec, fft_filter,
                      lp, hp, bp, peak, chain)


def _vib(n, rate, depth, delay, rng):
    t = np.arange(n) / SR
    ramp = np.clip((t - delay) / 0.4, 0, 1)
    r = rate * (1 + 0.04 * rng.standard_normal())
    return 1.0 + depth * ramp * np.sin(2 * np.pi * r * t + rng.random() * 6.28)


def strings(m, dur, vel, rng, art="legato", voices=5, bright=1.0, section="vln"):
    """Bowed string section. art: legato | marcato | spiccato | tremolo | pizz | swell"""
    f0 = midi_hz(m)
    rel = {"legato": 0.45, "swell": 0.6, "tremolo": 0.35, "marcato": 0.25, "spiccato": 0.08}.get(art, 0.3)
    if art == "pizz":
        return pizz(m, vel, rng)
    n = secs(dur + rel)
    fc_h = max(2.0, (1800 + 3200 * vel * bright) / f0)        # brightness follows dynamics
    body = [(max(1.0, 280 / f0), 0.8, 1.2), (max(1.0, 1100 / f0), 0.6, 2.5), (max(1.0, 2600 / f0), 0.35, 4.0)]
    tbl = _table(maxh_for(f0), fc_h, 1.0, False, body)
    out = np.zeros(n)
    for v in range(voices):
        det = 2 ** ((rng.uniform(-7, 7)) / 1200)
        fr = f0 * det * _vib(n, 5.3, 0.0028 if section != "bass" else 0.0015, 0.25, rng)
        out += wt_osc(fr, tbl, rng.random())
    out /= voices ** 0.7
    # bow noise
    out += fft_filter(rng.standard_normal(n), bp(f0 * 2, 6000)) * 0.03
    if art == "legato":
        env = adsr(n, 0.22, 0.3, 0.85, rel)
    elif art == "swell":
        t = np.arange(n) / SR
        env = np.sin(np.pi * np.clip(t / (dur + rel), 0, 1)) ** 1.5
    elif art == "marcato":
        env = adsr(n, 0.03, 0.18, 0.55, rel) * (1 + 0.4 * expdec(n, 0.06))
    elif art == "spiccato":
        env = adsr(n, 0.008, 0.07, 0.25, rel) * (1 + 0.6 * expdec(n, 0.03))
    elif art == "tremolo":
        t = np.arange(n) / SR
        trem = 0.55 + 0.45 * np.abs(np.sin(np.pi * 13.0 * t + rng.random()))
        env = adsr(n, 0.12, 0.2, 0.8, rel) * trem
    else:
        env = adsr(n, 0.1, 0.2, 0.8, rel)
    return out * env * vel


def pizz(m, vel, rng):
    f0 = midi_hz(m)
    n = secs(1.4 if m < 55 else 0.9)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, maxh_for(f0, 9000) + 1):
        a = (1.0 / k) * np.sin(np.pi * k * 0.23) ** 2
        out += a * np.sin(2 * np.pi * f0 * k * t * (1 + 0.0004 * k * k)) * np.exp(-t * (3.5 + 1.6 * k))
    out += fft_filter(rng.standard_normal(n), bp(200, 3000)) * np.exp(-t / 0.006) * 0.3
    return out / (np.max(np.abs(out)) + 1e-9) * vel * 0.7


def brass(m, dur, vel, rng, kind="trumpet", voices=3, art="legato"):
    """Brass section: brightness envelope tied to loudness (key to a brassy timbre)."""
    f0 = midi_hz(m)
    cfg = {"trumpet": (1.4, 6.5, 0.05), "horn": (0.9, 3.0, 0.09), "trombone": (1.1, 4.5, 0.07), "tuba": (0.8, 2.6, 0.1)}[kind]
    tilt, bright_h, att = cfg
    rel = 0.25 if art != "stab" else 0.15
    n = secs(dur + rel)
    form = [(max(1.0, 1200 / f0), 1.2, 2.0)] if kind == "trumpet" else [(max(1.0, 500 / f0), 1.0, 1.5)]
    dark = _table(maxh_for(f0), 1.6, tilt + 0.4, False, form)
    brt = _table(maxh_for(f0), bright_h * (0.6 + 0.6 * vel), tilt, False, form)
    if art == "stab":
        env = adsr(n, att * 0.6, 0.15, 0.35, rel) * (1 + 0.5 * expdec(n, 0.05))
    elif art == "swell":
        t = np.arange(n) / SR
        env = np.sin(np.pi * np.clip(t / (dur + rel), 0, 1)) ** 1.3
    else:
        env = adsr(n, att, 0.2, 0.82, rel) * (1 + 0.25 * expdec(n, 0.08))
    env = env / (env.max() + 1e-9)
    mix = np.clip(env * vel * 1.15, 0, 1) ** 1.3
    out = np.zeros(n)
    t = np.arange(n) / SR
    for v in range(voices):
        det = 2 ** (rng.uniform(-5, 5) / 1200)
        scoop = 1.0 - 0.012 * np.exp(-t / 0.035)
        fr = f0 * det * scoop * _vib(n, 4.8, 0.0018, 0.35, rng)
        ph = rng.random()
        out += wt_osc(fr, dark, ph) * (1 - mix) + wt_osc(fr, brt, ph) * mix
    out /= voices ** 0.7
    out += fft_filter(rng.standard_normal(n), bp(800, 5000)) * 0.015 * env
    return out * env * vel


def timpani(m, vel, rng, length=2.4):
    f0 = midi_hz(m)
    n = secs(length)
    t = np.arange(n) / SR
    ratios = [1.0, 1.504, 1.742, 2.0, 2.245, 2.494, 2.80, 0.5]
    amps = [1.0, 0.55, 0.3, 0.32, 0.18, 0.14, 0.09, 0.25]
    decs = [1.6, 0.9, 0.7, 0.6, 0.45, 0.35, 0.3, 0.5]
    glide = 1.0 + 0.018 * np.exp(-t / 0.08) * vel
    out = np.zeros(n)
    for r, a, d in zip(ratios, amps, decs):
        ph = 2 * np.pi * np.cumsum(f0 * r * glide) / SR
        out += a * np.sin(ph + rng.random()) * np.exp(-t / (d * (0.7 + 0.5 * (1 - vel))))
    thump = fft_filter(rng.standard_normal(n), lp(180 + 500 * vel)) * np.exp(-t / 0.025) * 1.5
    out += thump + fft_filter(rng.standard_normal(n), bp(500, 4000)) * np.exp(-t / 0.008) * 0.3 * vel
    out *= np.minimum(1, t / 0.0015)
    return out / 2.2 * vel


def timp_roll(m, dur, v0, v1, rng):
    n = secs(dur + 2.0)
    out = np.zeros(n)
    t = 0.0
    while t < dur:
        v = v0 + (v1 - v0) * (t / dur)
        h = timpani(m, v * rng.uniform(0.85, 1.0), rng, 1.6)
        s = secs(t)
        out[s:s + len(h)] += h[:n - s]
        t += rng.uniform(0.055, 0.07)
    return out * 0.55


def snare(vel, rng, field=True):
    n = secs(0.6 if field else 0.35)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 180 * t) * 0.6 + np.sin(2 * np.pi * 332 * t) * 0.3) * np.exp(-t / 0.05)
    wires = fft_filter(rng.standard_normal(n), bp(1500, 9000, 1)) * np.exp(-t / (0.16 if field else 0.09))
    hit = fft_filter(rng.standard_normal(n), bp(300, 3000)) * np.exp(-t / 0.012)
    out = tone + wires * 0.9 + hit * 0.8
    return out * np.minimum(1, t / 0.0008) * vel * 0.45


def snare_roll(dur, v0, v1, rng):
    n = secs(dur + 0.6)
    out = np.zeros(n)
    t = 0.0
    while t < dur:
        v = v0 + (v1 - v0) * t / dur
        h = snare(v * rng.uniform(0.7, 1.0), rng)
        s = secs(t)
        out[s:s + len(h)] += h[:n - s] * 0.6
        t += rng.uniform(0.032, 0.042)
    return out


def bass_drum(vel, rng):
    n = secs(1.2)
    t = np.arange(n) / SR
    f = 46 + 34 * np.exp(-t / 0.06)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.42)
    beater = fft_filter(rng.standard_normal(n), lp(600)) * np.exp(-t / 0.02)
    return (body + beater * 0.6) * vel * 0.8


def cymbal(vel, rng, length=3.5):
    n = secs(length)
    t = np.arange(n) / SR
    out = fft_filter(rng.standard_normal(n), bp(2500, 14000, 1)) * np.exp(-t / 1.1)
    for k in range(30):
        f = rng.uniform(400, 7000)
        out += 0.08 * np.sin(2 * np.pi * f * t + rng.random() * 6.28) * np.exp(-t / rng.uniform(0.3, 1.4))
    out *= np.minimum(1, t / 0.004)
    return out * vel * 0.25


def cymbal_swell(dur, vel, rng):
    n = secs(dur + 0.5)
    t = np.arange(n) / SR
    out = fft_filter(rng.standard_normal(n), bp(3000, 13000, 1))
    env = np.clip(t / dur, 0, 1) ** 2.5 * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.08))
    return out * env * vel * 0.2
