"""Iron Crowns battlefield & UI sound effects: original procedural synthesis (numpy), no recordings or samples.

Weapon sounds follow the projectile classes the battle renderer actually uses (battle_view.projectile_class):
  arrow (medieval archers) · stone_shot (bombards) · musket_ball (early-modern musketeers, c19 line/grenadiers)
  round_shot (culverins, c19 field guns) · rifle_tracer (c20/modern rifle infantry: bolt-action style volleys,
  no automatic fire) · shell (howitzers/rocket artillery) · tank_round (c20/modern vehicles)
"""
import numpy as np
from synthlib import (SR, secs, place, fft_filter, fft_filter_circ, lp, hp, bp, peak, chain, expdec, make_ir, convolve,
                      normalize, limit, loop_crossfade, tv_filter, db, wt_osc, _table, maxh_for, midi_hz, fade)
import instruments as I

OUT_IR = None


def outdoor_ir(rng, far=False):
    """Open-field 'reverb': sparse terrain/treeline slapbacks + short diffuse tail."""
    er = [(0.09, 0.25), (0.17, 0.18), (0.31, 0.14), (0.47, 0.1), (0.66, 0.07)] if not far else [(0.2, 0.3), (0.45, 0.25), (0.8, 0.2), (1.2, 0.15)]
    return make_ir(2.2 if not far else 3.5, (1.6, 1.0, 0.4) if not far else (2.8, 1.6, 0.6), early=er, rng=rng, stereo=False,
                   predelay=0.0, bright=5000 if not far else 1800)


def wetdry(x, rng, wet=0.35, far=False):
    ir = outdoor_ir(rng, far)
    y = convolve(x, ir)
    out = np.zeros(len(y)); out[:len(x)] += x
    return out + y * wet


def finish(x, peak_db=-1.0, fin=0.0005, fout=0.05, thr=-62):
    a = np.abs(x)
    idx = np.where(a > db(thr) * a.max())[0]
    x = x[:idx[-1] + 1] if len(idx) else x
    x = fade(x, fin, min(fout, len(x) / SR / 3))
    return normalize(x, peak_db)


def thump(n, f0, f1, tau, rng):
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / (tau * 0.4))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)


def burst(n, tau, band, rng, attack=0.0005):
    t = np.arange(n) / SR
    return fft_filter(rng.standard_normal(n), band) * np.exp(-t / tau) * np.minimum(1, t / attack)


# ---------------------------------------------------------------- black-powder small arms
def musket_shot(rng, far=False):
    n = secs(1.6)
    x = np.zeros(n)
    # flintlock: cock/frizzen click, then pan flash 'fsst', then main charge
    click = burst(secs(0.02), 0.002, bp(2500, 9000), rng) * 0.25
    pan_ = burst(secs(0.08), 0.02, bp(1500, 7000), rng) * 0.35
    d = secs(rng.uniform(0.04, 0.09))
    place(x, click, 0); place(x, pan_, secs(0.012))
    crack = burst(secs(0.05), 0.0035, hp(900), rng) * 1.3
    boom = burst(secs(0.6), 0.07, lp(1600), rng) * 1.1 + thump(secs(0.6), 160, 55, 0.08, rng) * 0.9
    body = crack[:len(boom)] if len(crack) >= len(boom) else np.pad(crack, (0, len(boom) - len(crack)))
    place(x, body + boom, d)
    x = wetdry(x, rng, 0.45)
    if far:
        x = farify(x, rng)
    return finish(x)


def farify(x, rng, cutoff=700, smear=0.04):
    y = fft_filter(x, chain(lp(cutoff, 2), hp(60, 1)))
    y = wetdry(y, rng, 0.8, far=True)
    pre = np.zeros(secs(rng.uniform(0.0, smear)))
    return np.concatenate([pre, y])


def volley(rng, shot_fn, count=(9, 14), spread=0.45, far=False, crackle=True):
    n = secs(3.2)
    x = np.zeros(n)
    k = rng.integers(*count)
    for i in range(k):
        s = shot_fn(rng, False) * rng.uniform(0.45, 0.9)
        st = secs(abs(rng.normal(0, spread / 2.2)))
        place(x, s, st)
    if crackle:  # ragged late shots
        for i in range(rng.integers(1, 4)):
            place(x, shot_fn(rng, False) * rng.uniform(0.25, 0.45), secs(rng.uniform(spread, spread * 2.0)))
    if far:
        x = farify(x, rng, 600, 0.0)
    return finish(limit(x / max(1.0, np.max(np.abs(x))) , -0.5, look=0.002, release=0.05))


def rifle_shot(rng, far=False):
    """Smokeless bolt-action rifle: supersonic crack, tighter report, less boom than black powder."""
    n = secs(1.3)
    x = np.zeros(n)
    crack = burst(secs(0.03), 0.0018, hp(1800), rng) * 1.6
    rep = burst(secs(0.4), 0.035, bp(200, 3500), rng) * 0.9 + thump(secs(0.4), 220, 80, 0.04, rng) * 0.5
    place(x, crack, 0); place(x, rep, secs(0.003))
    x = wetdry(x, rng, 0.5)
    if far:
        x = farify(x, rng, 900)
    return finish(x)


def pistol_shot(rng, far=False):
    n = secs(1.0); x = np.zeros(n)
    place(x, burst(secs(0.3), 0.04, lp(2500), rng) * 0.9 + thump(secs(0.3), 200, 90, 0.05, rng) * 0.4, 0)
    place(x, burst(secs(0.03), 0.003, hp(1200), rng), 0)
    x = wetdry(x, rng, 0.4)
    return finish(farify(x, rng) if far else x)


# ---------------------------------------------------------------- artillery
def cannon(rng, far=False, size=1.0, kind="field"):
    """Muzzle-loading cannon: low thump + broadband blast + long rolling echoes."""
    n = secs(4.5 * size)
    x = np.zeros(n)
    blast = burst(secs(1.2 * size), 0.18 * size, lp(900 / size ** 0.5, 2), rng) * 1.3
    hi = burst(secs(0.15), 0.012, hp(700), rng) * 0.8
    low = thump(secs(1.5 * size), 90 / size, 32, 0.35 * size, rng) * 1.4
    place(x, blast, 0); place(x, hi, 0); place(x, low, 0)
    if kind == "bombard":   # stone shot: heavier, duller, crumbling rumble
        place(x, burst(secs(2.0), 0.6, lp(300), rng) * 0.5, secs(0.05))
    # rolling echo
    t = np.arange(n) / SR
    roll = fft_filter(rng.standard_normal(n), lp(260)) * np.exp(-t / (0.9 * size)) * np.clip(t / 0.15, 0, 1) * 0.35
    x += roll
    x = wetdry(x, rng, 0.55, far=False)
    if far:
        x = farify(x, rng, 380, 0.0)
    return finish(x)


def howitzer(rng, far=False):
    x = cannon(rng, False, 1.15)
    n = len(x)
    # sharper modern charge: added supersonic shock
    place(x, burst(secs(0.05), 0.004, hp(1500), rng) * 0.9, 0)
    if far:
        x = farify(x, rng, 380, 0.0)
    return finish(x)


def tank_gun(rng, far=False):
    x = howitzer(rng, False) * 0.9
    # breech/turret mechanical clank after firing
    for dt, f in [(0.55, 1800), (0.72, 1200), (1.05, 900)]:
        clk = metal_hit(rng, f, 0.08, 0.25)
        place(x, clk * 0.25, secs(dt))
    if far:
        x = farify(x, rng, 420, 0.0)
    return finish(x)


def explosion(rng, far=False, size=1.0):
    n = secs(4.0 * size)
    x = np.zeros(n)
    t = np.arange(n) / SR
    place(x, burst(secs(1.6), 0.25 * size, lp(1200, 2), rng) * 1.4, 0)
    place(x, thump(secs(1.4), 70, 28, 0.4 * size, rng) * 1.5, 0)
    place(x, burst(secs(0.1), 0.01, hp(900), rng) * 0.7, 0)
    # debris patter: soil and stones falling
    for i in range(int(40 * size)):
        st = rng.uniform(0.25, 1.6)
        g = burst(secs(0.05), 0.008, bp(600, 5000), rng) * rng.uniform(0.04, 0.14) * np.exp(-(st - 0.25))
        place(x, g, secs(st))
    x += fft_filter(rng.standard_normal(n), lp(200)) * np.exp(-t / 1.2) * np.clip(t / 0.2, 0, 1) * 0.3
    x = wetdry(x, rng, 0.5)
    if far:
        x = farify(x, rng, 350, 0.0)
    return finish(x)


def ball_impact(rng):
    """Round shot striking earth: heavy dull thud + soil spray."""
    n = secs(1.2); x = np.zeros(n)
    place(x, thump(secs(0.5), 110, 45, 0.09, rng) * 1.2, 0)
    place(x, burst(secs(0.4), 0.06, lp(700), rng), 0)
    for i in range(14):
        place(x, burst(secs(0.04), 0.006, bp(700, 4500), rng) * rng.uniform(0.05, 0.15), secs(rng.uniform(0.05, 0.6)))
    return finish(wetdry(x, rng, 0.3))


def incoming_whistle(rng):
    """Shell passing overhead (c20/modern artillery only): descending airy whistle."""
    d = 1.4
    n = secs(d)
    nz = rng.standard_normal(n)
    def g(t, f):
        fc = 2400 - 1300 * (t / d)
        return np.exp(-0.5 * ((f - fc) / 220) ** 2)
    x = tv_filter(nz, g)
    t = np.arange(n) / SR
    x *= np.clip(t / (d * 0.8), 0, 1) ** 2 * np.exp(-np.clip(t - d * 0.9, 0, None) / 0.05)
    return finish(x, -6)


# ---------------------------------------------------------------- medieval
def bow_volley(rng, far=False):
    n = secs(2.2); x = np.zeros(n)
    for i in range(rng.integers(10, 16)):
        st = abs(rng.normal(0, 0.12))
        f = rng.uniform(140, 220)
        t = np.arange(secs(0.25)) / SR
        tw = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.05) * 0.5 + burst(len(t), 0.01, bp(300, 3000), rng) * 0.4
        place(x, tw * rng.uniform(0.4, 0.8), secs(st))
    # swarm of arrows in flight: modulated airy noise swelling then fading
    m = secs(1.8)
    t = np.arange(m) / SR
    air = fft_filter(rng.standard_normal(m), bp(1200, 6000, 1)) * np.sin(np.pi * np.clip(t / 1.7, 0, 1)) ** 2 * 0.45
    place(x, air, secs(0.15))
    if far:
        x = farify(x, rng, 1500)
    return finish(wetdry(x, rng, 0.25))


def metal_hit(rng, f0=900, tau=0.25, noise_amt=0.5):
    n = secs(tau * 4)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for r, a in [(1.0, 1.0), (2.76, 0.6), (5.4, 0.4), (8.93, 0.25), (13.3, 0.15)]:
        x += a * np.sin(2 * np.pi * f0 * r * rng.uniform(0.98, 1.02) * t) * np.exp(-t / (tau / r ** 0.5))
    x += burst(n, 0.004, hp(2000), rng) * noise_amt
    return x / np.max(np.abs(x))


def sword_clash(rng):
    n = secs(1.0); x = np.zeros(n)
    for i in range(rng.integers(1, 3)):
        place(x, metal_hit(rng, rng.uniform(700, 1400), rng.uniform(0.12, 0.3)) * rng.uniform(0.5, 1.0), secs(rng.uniform(0, 0.15)))
    place(x, burst(secs(0.1), 0.02, bp(200, 2000), rng) * 0.4, 0)   # shield/body thud
    return finish(wetdry(x, rng, 0.25))


# ---------------------------------------------------------------- crowds (nonverbal)
VOWELS = {"a": [(800, 1.0, 80), (1150, 0.6, 90), (2900, 0.25, 120)],
          "o": [(450, 1.0, 70), (800, 0.6, 80), (2830, 0.15, 100)],
          "u": [(325, 1.0, 50), (700, 0.3, 60), (2530, 0.1, 100)]}


def voice(rng, dur, f0, vowel="a", rise=0.15, vib=0.02):
    n = secs(dur)
    t = np.arange(n) / SR
    contour = f0 * (1 + rise * np.sin(np.pi * np.clip(t / dur, 0, 1))) * (1 + vib * np.sin(2 * np.pi * rng.uniform(4, 7) * t))
    fm = f0 * (1 + rise * 0.5)
    form = VOWELS[vowel]
    maxh = maxh_for(fm, 5000)
    ph = np.arange(4096) / 4096
    tbl = np.zeros(4096)
    for k in range(1, maxh + 1):
        fk = k * fm
        a = sum(g * np.exp(-0.5 * ((fk - fc) / bw) ** 2) for (fc, g, bw) in form) + 0.02
        tbl += a / k ** 0.6 * np.sin(2 * np.pi * k * ph)
    tbl /= np.max(np.abs(tbl)); tbl = np.append(tbl, tbl[0])
    x = wt_osc(contour, tbl, rng.random())
    x += fft_filter(rng.standard_normal(n), bp(500, 3000)) * 0.15   # breath
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.6
    return x * env


def crowd(rng, dur, voices=36, vowel="a", f0=(95, 190), rise=0.18, spread=0.5, far=False):
    n = secs(dur + 1.5); x = np.zeros(n)
    for i in range(voices):
        d = rng.uniform(dur * 0.5, dur)
        st = rng.uniform(0, spread)
        place(x, voice(rng, d, rng.uniform(*f0), vowel if rng.random() > 0.3 else rng.choice(list(VOWELS)), rise) * rng.uniform(0.3, 1.0), secs(st))
    x = fft_filter(x, chain(hp(120), lp(4000 if not far else 1400)))
    return finish(wetdry(x, rng, 0.45, far))


def melee_loop(rng, L=8.0):
    """Hand-to-hand fighting bed: scattered steel clashes, thuds and low crowd effort (loopable)."""
    n = secs(L); x = np.zeros(n)
    for i in range(int(L * 6)):
        place(x, sword_clash(rng) * rng.uniform(0.2, 0.6), secs(rng.uniform(0, L)), wrap=True)
    for i in range(int(L * 3)):
        place(x, burst(secs(0.15), 0.03, lp(600), rng) * rng.uniform(0.2, 0.5), secs(rng.uniform(0, L)), wrap=True)
    murmur = np.zeros(n)
    for i in range(18):
        v = voice(rng, rng.uniform(0.6, 1.8), rng.uniform(90, 160), rng.choice(["a", "o", "u"]), 0.08) * rng.uniform(0.15, 0.4)
        place(murmur, v, secs(rng.uniform(0, L)), wrap=True)
    x += fft_filter(murmur, chain(hp(150), lp(2500)))
    return normalize(x, -3)


# ---------------------------------------------------------------- movement
def step(rng):
    n = secs(0.18)
    return burst(n, 0.03, bp(250, 3500), rng) * (0.6 + 0.4 * np.abs(rng.standard_normal(n)) ** 0.5) + thump(n, 90, 60, 0.03, rng) * 0.4


def march_loop(rng, L=4.0, men=60, cadence=1.0):
    """Column of infantry marching in step (~120 paces/min), with kit rattle. Loop length = whole bars."""
    n = secs(L); x = np.zeros(n)
    period = 0.5 / cadence
    for m in range(men):
        off = rng.normal(0, 0.03)
        g = rng.uniform(0.15, 0.4)
        t = 0.0
        while t < L:
            place(x, step(rng) * g * rng.uniform(0.7, 1.0), secs(t + off + rng.normal(0, 0.008)), wrap=True)
            t += period
        if rng.random() < 0.5:
            for k in range(int(L / period)):
                if rng.random() < 0.4:
                    place(x, metal_hit(rng, rng.uniform(2500, 4500), 0.03, 0.2) * 0.04, secs(k * period + rng.uniform(0.05, 0.2)), wrap=True)
    x = fft_filter(x, chain(hp(80), lp(6000)))
    return normalize(x, -3)


def hooves(rng, dur=3.0, horses=20, far=False):
    n = secs(dur + 1.0); x = np.zeros(n)
    for h in range(horses):
        rate = rng.uniform(1.9, 2.3)   # gallop strides per second
        t = rng.uniform(0, 0.5)
        g = rng.uniform(0.2, 0.5)
        while t < dur:
            for dt in (0.0, 0.09, 0.17):   # three-beat gallop
                hit = thump(secs(0.12), 140, 70, 0.025, rng) * 0.8 + burst(secs(0.12), 0.015, bp(200, 2500), rng) * 0.6
                place(x, hit * g, secs(t + dt))
            t += 1.0 / rate
    tt = np.arange(n) / SR
    x *= np.clip(tt / 0.8, 0, 1) * np.clip((dur + 0.5 - tt) / 0.8, 0, 1)
    x += fft_filter(rng.standard_normal(n), lp(150)) * 0.15 * np.clip(tt / 1.0, 0, 1) * np.clip((dur + 0.5 - tt) / 1.0, 0, 1)
    if far:
        x = farify(x, rng)
    return finish(wetdry(x, rng, 0.3))


def engine_loop(rng, L=4.0, rpm_hz=28.0, tracks=True):
    """Tracked vehicle idle/drive rumble (c20/modern vehicles only), seamless loop."""
    n = secs(L)
    t = np.arange(n) / SR
    cyc = rpm_hz
    # integer cycles per loop so the firing pulse train wraps cleanly
    cyc = round(cyc * L) / L
    ph = (cyc * t) % 1.0
    pulses = np.exp(-ph / 0.18) * (1 + 0.15 * np.sin(2 * np.pi * (cyc / 2) * t))
    tone = fft_filter_circ(pulses - pulses.mean(), lp(400, 2))
    rumble = fft_filter(np.random.default_rng(5).standard_normal(n + secs(1)), bp(40, 300))
    rumble = loop_crossfade(rumble, n, secs(1)) * 0.4
    x = tone * 0.9 + rumble
    if tracks:
        k = round(9 * L)
        for i in range(k):
            place(x, metal_hit(rng, rng.uniform(600, 1100), 0.04, 0.6) * 0.12, secs((i + 0.5) * L / k + rng.uniform(0, 0.01)), wrap=True)
    return normalize(x, -3)


# ---------------------------------------------------------------- ambience beds (loops)
def amb_battle(rng, L=24.0, era="powder"):
    """Distant battle: scattered far volleys/shots and cannon (or rifles & shells), faint crowd swell."""
    n = secs(L); x = np.zeros(n)
    if era == "powder":
        for i in range(int(L * 0.9)):
            place(x, musket_shot(rng, True) * rng.uniform(0.15, 0.45), secs(rng.uniform(0, L)), wrap=True)
        for i in range(int(L / 4)):
            place(x, volley(rng, musket_shot, (6, 10), far=True) * rng.uniform(0.25, 0.5), secs(rng.uniform(0, L)), wrap=True)
        for i in range(int(L / 5)):
            place(x, cannon(rng, True) * rng.uniform(0.35, 0.7), secs(rng.uniform(0, L)), wrap=True)
    elif era == "modern":
        for i in range(int(L * 2.2)):
            place(x, rifle_shot(rng, True) * rng.uniform(0.12, 0.4), secs(rng.uniform(0, L)), wrap=True)
        for i in range(int(L / 5)):
            place(x, explosion(rng, True) * rng.uniform(0.3, 0.6), secs(rng.uniform(0, L)), wrap=True)
        for i in range(int(L / 7)):
            place(x, howitzer(rng, True) * rng.uniform(0.3, 0.55), secs(rng.uniform(0, L)), wrap=True)
    else:  # medieval: distant clash and shouting
        for i in range(int(L * 4)):
            place(x, farify(sword_clash(rng), rng, 1500) * rng.uniform(0.1, 0.3), secs(rng.uniform(0, L)), wrap=True)
        for i in range(int(L / 6)):
            place(x, crowd(rng, rng.uniform(1.5, 3.0), 20, "a", far=True) * rng.uniform(0.2, 0.4), secs(rng.uniform(0, L)), wrap=True)
    wind = wind_loop(rng, L) * 0.25
    x = x + wind
    return normalize(x, -4)


def wind_loop(rng, L=20.0):
    n = secs(L)
    m = n + secs(2)
    nz = rng.standard_normal(m)
    lfo_r = rng.uniform(0.07, 0.12)
    def g(t, f):
        fc = 350 + 250 * np.sin(2 * np.pi * lfo_r * t) + 120 * np.sin(2 * np.pi * 0.31 * t)
        return 1.0 / np.sqrt(1 + (f / fc) ** 4) * (f > 40)
    x = tv_filter(nz, g)
    x *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * np.arange(m) / SR)
    x = loop_crossfade(x, n, secs(2))
    return normalize(x, -6)


# ---------------------------------------------------------------- signals (nonverbal commands)
def bugle_call(rng):
    """Original short cavalry/infantry-style bugle call on natural harmonics (G, C, E, G)."""
    seq = [("G4", 0.18), ("C5", 0.18), ("E5", 0.18), ("G5", 0.45), ("E5", 0.18), ("G5", 0.7)]
    out = np.zeros(secs(3.2)); t = 0.0
    for nm, d in seq:
        import music
        m = music.N(nm)
        s = I.brass(m, d, 0.8, rng, "trumpet", 1, "legato")
        place(out, s, secs(t)); t += d + 0.03
    return finish(wetdry(fft_filter(out, chain(hp(300), peak(1500, 3))), rng, 0.55), -3)


def war_horn(rng):
    """Low signalling horn for medieval/early-modern battle starts."""
    out = np.zeros(secs(3.5))
    import music
    s1 = I.brass(music.N("D3"), 1.0, 0.7, rng, "horn", 2, "legato")
    s2 = I.brass(music.N("A3"), 1.3, 0.8, rng, "horn", 2, "legato")
    place(out, s1, 0); place(out, s2, secs(1.1))
    return finish(wetdry(out, rng, 0.7, far=True), -3)


def whistle(rng):
    """Officer's pea whistle (c20/modern advance signal): two blasts."""
    out = np.zeros(secs(1.6))
    for st, d in [(0.0, 0.25), (0.35, 0.6)]:
        n = secs(d); t = np.arange(n) / SR
        f = 2900 * (1 + 0.03 * np.sign(np.sin(2 * np.pi * 28 * t)))   # pea trill
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * fade(np.ones(n), 0.01, 0.03)
        place(out, x + burst(n, 1.0, bp(2000, 6000), rng) * 0.1, secs(st))
    return finish(wetdry(out, rng, 0.4), -6)


def drum_cadence(rng):
    """Marching order on the campaign map: short field-drum cadence + a few marching steps."""
    out = np.zeros(secs(2.4))
    for (t, v) in [(0, 1.0), (0.12, 0.5), (0.24, 0.8), (0.48, 1.0), (0.6, 0.5), (0.72, 0.6), (0.84, 0.7), (0.96, 1.0)]:
        place(out, I.snare(v, rng), secs(t))
    place(out, I.bass_drum(0.7, rng), 0); place(out, I.bass_drum(0.7, rng), secs(0.96))
    m = march_loop(rng, 1.0, 20) * 0.35
    place(out, fade(m, 0.2, 0.3), secs(1.1))
    return finish(wetdry(out, rng, 0.35), -3)


# ---------------------------------------------------------------- UI
def ui_click(rng):
    """Wooden map-table tap."""
    n = secs(0.12); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in [(820, 1.0, 0.012), (1930, 0.5, 0.008), (3400, 0.3, 0.005)])
    x += burst(n, 0.003, bp(1500, 8000), rng) * 0.3
    return finish(x, -6)


def ui_select(rng):
    n = secs(0.25); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in [(520, 1.0, 0.03), (1040, 0.4, 0.02), (1560, 0.2, 0.015)])
    x += burst(n, 0.004, bp(800, 6000), rng) * 0.25
    return finish(x, -6)


def ui_paper(rng, close=False):
    """Map/parchment rustle for opening/closing panels."""
    d = 0.35
    n = secs(d); nz = rng.standard_normal(n)
    grain = (np.abs(rng.standard_normal(n)) > 1.6).astype(float)
    grain = np.convolve(grain, np.ones(60) / 60, "same")
    t = np.arange(n) / SR
    env = np.sin(np.pi * t / d) ** (0.7 if not close else 1.5)
    x = fft_filter(nz, bp(1200 if not close else 900, 9000, 1)) * (0.35 + grain * 2.0) * env
    return finish(x, -8)


def ui_confirm(rng):
    """Seal stamp + soft brass chime (proposal sent / purchase confirmed)."""
    out = np.zeros(secs(1.2))
    place(out, thump(secs(0.2), 150, 80, 0.03, rng) + burst(secs(0.2), 0.015, lp(1500), rng) * 0.6, 0)
    t = np.arange(secs(1.0)) / SR
    bell = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in [(880, 0.4, 0.5), (1320, 0.25, 0.35), (2210, 0.12, 0.2)])
    place(out, bell * 0.6, secs(0.06))
    return finish(out, -6)


def ui_error(rng):
    n = secs(0.35); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 140 * t) + 0.4 * np.sin(2 * np.pi * 210 * t)) * np.exp(-t / 0.08) + burst(n, 0.02, lp(800), rng) * 0.5
    return finish(x, -6)


def ui_coins(rng):
    out = np.zeros(secs(0.9))
    for i in range(6):
        place(out, metal_hit(rng, rng.uniform(2800, 4200), 0.06, 0.3) * rng.uniform(0.4, 1.0), secs(i * 0.05 + rng.uniform(0, 0.03)))
    return finish(out, -6)


def ui_order(rng):
    """Short two-stroke drum tap: army order acknowledged."""
    out = np.zeros(secs(0.7))
    place(out, I.snare(0.9, rng), 0); place(out, I.snare(1.0, rng), secs(0.11))
    return finish(out, -6)
