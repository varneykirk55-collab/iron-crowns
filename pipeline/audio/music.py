"""Iron Crowns original score: procedural orchestral rendering of hand-written, original compositions.

Tracks (loops render circularly so the last bar flows sample-continuously into the first):
  music_campaign  "Map of Empires"   D minor, 66 bpm, 28 bars  — strings, horn/trumpet melodies, soft timpani & field drum
  music_tension   "Council of War"   D pedal, 56 bpm, 15 bars  — tremolo strings, muted horn swells, heartbeat timpani
  music_battle    "Field of Iron"    D minor, 132 bpm, 36 bars — spiccato ostinato, march snare, bass drum, brass melody
Stings (one-shot): sting_victory, sting_defeat, sting_war, sting_era
All melodies/progressions were written for this project; no existing melodies are quoted.
"""
import numpy as np
from synthlib import SR, secs, place, pan, make_ir, convolve, limit, db, rms_db, fft_filter, hp, lp, peak, chain
import instruments as I

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def N(s):
    """'C#4' / 'Bb3' -> midi"""
    n = NOTE[s[0]]
    i = 1
    while i < len(s) and s[i] in "#b":
        n += 1 if s[i] == "#" else -1
        i += 1
    return n + 12 * (int(s[i:]) + 1)


# chord: (bass midi, [cello/viola tones], [violin II tones])
CH = {
    "Dm": (N("D2"), [N("D3"), N("A3"), N("F4")], [N("A4"), N("D5"), N("F5")], [0, 3, 7]),
    "Bb": (N("Bb1"), [N("Bb2"), N("F3"), N("D4")], [N("F4"), N("Bb4"), N("D5")], [0, 4, 7]),
    "F": (N("F2"), [N("F3"), N("C4"), N("A3")], [N("A4"), N("C5"), N("F5")], [0, 4, 7]),
    "C": (N("C2"), [N("C3"), N("G3"), N("E4")], [N("G4"), N("C5"), N("E5")], [0, 4, 7]),
    "Gm": (N("G1"), [N("G2"), N("D3"), N("Bb3")], [N("G4"), N("Bb4"), N("D5")], [0, 3, 7]),
    "A": (N("A1"), [N("A2"), N("E3"), N("C#4")], [N("E4"), N("A4"), N("C#5")], [0, 4, 7]),
    "Eb": (N("Eb2"), [N("Eb3"), N("Bb3"), N("G3")], [N("G4"), N("Bb4"), N("Eb5")], [0, 4, 7]),
}

# instrument placement: pan, reverb send
SEAT = {"vln1": (-0.45, 0.32), "vln2": (-0.15, 0.32), "vla": (0.2, 0.34), "vc": (0.4, 0.3), "cb": (0.6, 0.3),
        "hn": (-0.35, 0.5), "tpt": (0.15, 0.45), "tbn": (0.35, 0.45), "tuba": (0.45, 0.4),
        "timp": (-0.1, 0.45), "snare": (0.1, 0.32), "bd": (0.0, 0.35), "cym": (0.05, 0.5), "pizz": (0.35, 0.35)}


class Score:
    def __init__(self, bpm, bars, beats_per_bar=4, seed=1, tail=6.0):
        self.beat = 60.0 / bpm
        self.bpb = beats_per_bar
        self.L = secs(bars * beats_per_bar * self.beat)
        self.dry = np.zeros((self.L + secs(tail), 2))
        self.wet = np.zeros_like(self.dry)
        self.rng = np.random.default_rng(seed)
        self.loop = True

    def t(self, bar, beat=0.0):
        return (bar * self.bpb + beat) * self.beat

    def add(self, sig, seat, bar, beat=0.0, gain=1.0, humanize=0.008):
        p, rv = SEAT[seat]
        st = secs(self.t(bar, beat) + self.rng.uniform(0, humanize))
        s = pan(sig, p)
        place(self.dry, s, st, gain, wrap=self.loop)
        place(self.wet, s, st, gain * rv, wrap=self.loop)

    # convenience wrappers ----------------------------------------------------
    def str_(self, seat, bar, beat, dur_b, m, vel, art="legato", gain=1.0, bright=1.0):
        sec = "bass" if seat == "cb" else seat
        voices = 4 if seat in ("vln1", "vln2") else 3
        sig = I.strings(m, dur_b * self.beat, vel, self.rng, art, voices, bright, sec)
        self.add(sig, seat, bar, beat, gain)

    def br(self, seat, bar, beat, dur_b, m, vel, art="legato", gain=1.0):
        kind = {"hn": "horn", "tpt": "trumpet", "tbn": "trombone", "tuba": "tuba"}[seat]
        sig = I.brass(m, dur_b * self.beat, vel, self.rng, kind, 3 if seat != "tuba" else 1, art)
        self.add(sig, seat, bar, beat, gain)

    def mel(self, seat, notes, vel, fn=None, art="legato", gain=1.0, octave=0):
        for (bar, beat, dur, name) in notes:
            m = N(name) + 12 * octave
            if seat.startswith("v"):
                self.str_(seat, bar, beat, dur, m, vel, art, gain)
            else:
                self.br(seat, bar, beat, dur, m, vel, art, gain)

    def render(self, rev_len=3.2, target_rms=-19.0, ceiling=-3.0, ir_seed=3):
        ir = make_ir(rev_len, (rev_len * 0.9, rev_len * 0.6, rev_len * 0.3), rng=np.random.default_rng(ir_seed))
        wet = convolve(self.wet, ir)
        out = np.zeros((len(wet), 2))
        out[:len(self.dry)] += self.dry
        out += wet * 0.55
        # gentle orchestral EQ: remove sub rumble, soften harshness
        for c in range(2):
            out[:, c] = fft_filter(out[:, c], chain(hp(32, 2), peak(3200, -2.5, 0.8), lp(14000, 1)))
        if self.loop:
            L = self.L
            body = out[:L].copy()
            rem = out[L:]
            k = 0
            while k < len(rem):
                m = min(L, len(rem) - k)
                body[:m] += rem[k:k + m]
                k += m
            out = body
        g = db(target_rms - rms_db(out))
        out = out * g
        return limit(out, ceiling, look=0.004, release=0.25)


def triad_tones(ch, octave_base):
    root = CH[ch][0] % 12
    return [octave_base + root + iv for iv in CH[ch][3]]


# =========================================================================== campaign map
def campaign():
    s = Score(66, 28, seed=11)
    prog = ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "A", "A",
            "Dm", "F", "C", "Gm", "Bb", "F", "Gm", "A",
            "Bb", "F", "Gm", "Dm", "Bb", "C", "A", "Dm",
            "Dm", "Bb", "Gm", "A"]
    for bar, ch in enumerate(prog):
        bass, low, up, _ = CH[ch]
        sec = bar // 8 if bar < 24 else 3
        dyn = [0.42, 0.55, 0.72, 0.38][sec]
        s.str_("cb", bar, 0, 4.15, bass + 12 if bass < N("C2") else bass, dyn * 0.9)
        s.str_("vc", bar, 0, 4.15, low[0], dyn * 0.8)
        s.str_("vla", bar, 0, 4.15, low[1], dyn * 0.7)
        s.str_("vla", bar, 0, 4.15, low[2], dyn * 0.6)
        if sec in (1, 2):
            art = "tremolo" if sec == 2 else "legato"
            for m in up[:2]:
                s.str_("vln2", bar, 0, 4.15, m, dyn * 0.45, art, bright=0.8)
        if sec == 1:   # cello 8th-note arpeggio adds motion
            tones = [low[0], low[1], low[0] + 12, low[1]]
            for k in range(8):
                s.str_("vc", bar, k * 0.5, 0.45, tones[k % 4], 0.33, "spiccato", 0.8)
        if sec == 2:   # brass chorale
            s.br("tbn", bar, 0, 4.0, low[0], 0.45, gain=0.7)
            s.br("hn", bar, 0, 4.0, low[1] + 12 if low[1] < N("G3") else low[1], 0.4, gain=0.6)
            s.br("hn", bar, 0, 4.0, low[2], 0.38, gain=0.55)
        # timpani: heartbeat in A/D, beats 1+3 in B/C
        tm = bass % 12 + N("C2")
        if tm < N("F2") - 3:
            tm += 12
        if sec in (0, 3) and bar % 2 == 0:
            s.add(I.timpani(tm, 0.4, s.rng), "timp", bar, 0)
        elif sec in (1, 2):
            s.add(I.timpani(tm, 0.45 if sec == 1 else 0.6, s.rng), "timp", bar, 0)
            s.add(I.timpani(tm, 0.3 if sec == 1 else 0.45, s.rng), "timp", bar, 2)
        if (sec == 1 and bar >= 10) or sec == 2:     # distant field drum, march figure
            v = 0.22 if sec == 1 else 0.38
            for (b, a) in [(0, 1.0), (1, 0.6), (1.5, 0.5), (2, 0.8), (3, 0.6), (3.5, 0.45), (3.75, 0.5)]:
                s.add(I.snare(v * a, s.rng), "snare", bar, b)
        if sec == 2:
            s.add(I.bass_drum(0.4, s.rng), "bd", bar, 0)
            s.add(I.bass_drum(0.3, s.rng), "bd", bar, 2)
    s.add(I.cymbal_swell(s.beat * 4, 0.6, s.rng), "cym", 15, 0)
    s.add(I.cymbal(0.45, s.rng), "cym", 16, 0)
    s.add(I.timp_roll(N("A2") - 12 + 12, s.beat * 3.6, 0.15, 0.55, s.rng), "timp", 15, 0)
    s.add(I.timp_roll(N("A2"), s.beat * 4, 0.1, 0.35, s.rng), "timp", 27, 0)
    horn = [(1, 3, 1, "A3"), (2, 0, 2.5, "D4"), (2, 2.5, .5, "C4"), (2, 3, 1, "D4"),
            (3, 0, 2, "F4"), (3, 2, 1, "D4"), (3, 3, 1, "Bb3"), (4, 0, 2, "G4"), (4, 2, 1, "F4"), (4, 3, 1, "D4"),
            (5, 0, 3, "Bb3"), (5, 3, .5, "A3"), (5, 3.5, .5, "Bb3"), (6, 0, 2, "A3"), (6, 2, 1, "C#4"), (6, 3, 1, "E4"), (7, 0, 3.5, "A3")]
    s.mel("hn", horn, 0.5, gain=0.9)
    vln = [(8, 0, 1.5, "D5"), (8, 1.5, .5, "E5"), (8, 2, 2, "F5"), (9, 0, 2, "A5"), (9, 2, 1, "G5"), (9, 3, 1, "F5"),
           (10, 0, 1.5, "E5"), (10, 1.5, .5, "D5"), (10, 2, 1, "C5"), (10, 3, 1, "G5"), (11, 0, 1.5, "G5"), (11, 1.5, .5, "F5"), (11, 2, 2, "D5"),
           (12, 0, 1.5, "F5"), (12, 1.5, .5, "G5"), (12, 2, 1, "A5"), (12, 3, 1, "Bb5"), (13, 0, 2, "C6"), (13, 2, 1, "A5"), (13, 3, 1, "F5"),
           (14, 0, 1, "Bb5"), (14, 1, 1, "A5"), (14, 2, 1, "G5"), (14, 3, 1, "D5"), (15, 0, 2, "E5"), (15, 2, 1, "C#5"), (15, 3, 1, "E5")]
    s.mel("vln1", vln, 0.6, gain=0.85)
    s.mel("vln1", vln, 0.4, gain=0.35, octave=-1)
    tpt = [(16, 0, 2, "D5"), (16, 2, 1, "F5"), (16, 3, 1, "D5"), (17, 0, 3, "C5"), (17, 3, 1, "A4"),
           (18, 0, 2, "Bb4"), (18, 2, 1, "D5"), (18, 3, 1, "G5"), (19, 0, 4, "F5"),
           (20, 0, 1.5, "F5"), (20, 1.5, .5, "G5"), (20, 2, 1, "F5"), (20, 3, 1, "D5"), (21, 0, 2, "E5"), (21, 2, 2, "G5"),
           (22, 0, 2, "E5"), (22, 2, 2, "C#5"), (23, 0, 4, "D5")]
    s.mel("tpt", tpt, 0.62, gain=0.8)
    s.mel("vln1", tpt, 0.5, gain=0.45, art="legato")
    echo = [(24, 0, 1.5, "A3"), (24, 1.5, .5, "D4"), (24, 2, 2, "F4"), (25, 0, 2, "F4"), (25, 2, 2, "D4"),
            (26, 0, 1.5, "D4"), (26, 1.5, .5, "Bb3"), (26, 2, 2, "G3"), (27, 0, 3.5, "A3")]
    s.mel("hn", echo, 0.38, gain=0.8)
    return s.render(3.4, -20.0)


# =========================================================================== tension / diplomacy
def tension():
    s = Score(56, 15, seed=23)
    D2, D3 = N("D2"), N("D3")
    upper = [("A4", "E5"), ("A4", "F5"), ("Bb4", "G5"), ("Bb4", "D5"), ("Bb4", "Eb5"), ("G4", "Eb5"), ("G4", "C#5"), ("A4", "C#5"),
             ("A4", "F5"), ("Bb4", "F5"), ("Bb4", "Eb5"), ("G4", "E5"), ("A4", "F5"), ("Bb4", "Eb5"), ("A4", "C#5")]
    high = ["A5", "A5", "Bb5", "Bb5", "G5", "G5", "G#5", "A5", "A5", "Bb5", "Bb5", "G5", "F5", "Eb5", "E5"]
    for bar in range(15):
        s.str_("cb", bar, 0, 4.2, D2, 0.32, "tremolo")
        s.str_("vc", bar, 0, 4.2, D3, 0.26, "legato")
        a, b = upper[bar]
        s.str_("vla", bar, 0, 4.2, N(a) - 12, 0.3, "tremolo", bright=0.6)
        s.str_("vla", bar, 0, 4.2, N(b) - 12, 0.25, "tremolo", bright=0.6)
        s.str_("vln2", bar, 0, 4.3, N(high[bar]), 0.22, "swell", 0.7, bright=0.45)
        if bar % 4 != 3:   # heartbeat
            s.add(I.timpani(D2, 0.38, s.rng, 1.8), "timp", bar, 0)
            s.add(I.timpani(D2, 0.26, s.rng, 1.8), "timp", bar, 0.55)
        if bar % 2 == 1:
            s.br("hn", bar, 0.5, 3.2, N(b) - 12, 0.3, "swell", gain=0.75)
            s.br("hn", bar, 0.5, 3.2, N(a) - 12, 0.28, "swell", gain=0.6)
        if bar % 4 == 0 and bar > 0:
            for (bt, nm) in [(1, "D3"), (1.5, "F3"), (2, "E3"), (2.5, "D3"), (3, "C#3")]:
                s.add(I.pizz(N(nm), 0.45, s.rng), "pizz", bar, bt)
        if bar in (6, 13):
            s.add(I.cymbal_swell(s.beat * 4, 0.35, s.rng), "cym", bar, 0)
    s.br("tbn", 7, 0, 4, N("A2"), 0.25, "swell", gain=0.6)
    s.br("tbn", 14, 0, 4, N("A2"), 0.25, "swell", gain=0.6)
    return s.render(3.0, -22.0)


# =========================================================================== battle
def battle():
    s = Score(132, 36, seed=37)
    prog = ["Dm", "Dm", "Bb", "Bb", "C", "C", "A", "A",
            "Dm", "Dm", "Gm", "Gm", "Bb", "C", "A", "A",
            "Bb", "Bb", "F", "F", "Gm", "Gm", "A", "A",
            "Dm", "Dm", "Bb", "Bb", "Gm", "A", "Dm", "A",
            "Dm", "Dm", "Eb", "A"]
    pat = [0, 0, 2, 0, 1, 0, 2, 1]
    for bar, ch in enumerate(prog):
        bass, low, up, iv = CH[ch]
        sec = min(bar // 8, 4)
        tones = triad_tones(ch, N("C3"))
        if tones[0] > N("F3"):
            tones = [t - 12 for t in tones]
        tutti = sec == 3
        build = sec == 4
        ov = 0.5 + 0.1 * sec if not build else 0.45 + 0.12 * (bar - 32)
        for k in range(8):
            m = tones[pat[k]]
            s.str_("vc", bar, k * 0.5, 0.45, m, ov * (1.15 if k % 2 == 0 else 0.9), "spiccato", 0.8)
            s.str_("vla", bar, k * 0.5, 0.45, m + 12, ov * (1.05 if k % 2 == 0 else 0.85), "spiccato", 0.6)
        bm = bass + 12 if bass < N("C2") else bass
        for b in (0, 2):
            s.str_("cb", bar, b, 1.6, bm, 0.6 + 0.08 * tutti, "marcato")
        # brass by section
        if sec == 0:
            for b in (1.5, 3.5):
                for m in low[1:]:
                    s.br("hn", bar, b, 0.45, m + 12 if m < N("A3") else m, 0.5, "stab", gain=0.7)
            if bar % 2 == 0:
                s.br("tbn", bar, 0, 7.6, low[0], 0.42, gain=0.6)
        if sec == 3 or build:
            for m in low:
                s.br("tbn", bar, 0, 1.7, m, 0.6, "stab", gain=0.55)
                s.br("tbn", bar, 2, 1.7, m, 0.55, "stab", gain=0.5)
            s.br("tuba", bar, 0, 1.8, bm - 12 if bm > N("A1") else bm, 0.5, "stab", gain=0.6)
        if sec == 2:
            for m in up:
                s.str_("vln2", bar, 0, 4.1, m + 12, 0.42, "tremolo", 0.6)
        if tutti:
            for m in up[1:]:
                s.str_("vln2", bar, 0, 4.1, m, 0.5, "tremolo", 0.6)
        # percussion
        acc = {0: 1.0, 8: 0.85, 12: 0.8}
        hits = [0, 3, 4, 6, 8, 10, 11, 12, 14, 15] if not build else list(range(16))
        sv = [0.3, 0.42, 0.45, 0.55, 0.5][sec] if not build else 0.3 + 0.12 * (bar - 32)
        for h in hits:
            a = acc.get(h, 0.55 if not build else 0.4 + 0.035 * h)
            s.add(I.snare(sv * a, s.rng), "snare", bar, h * 0.25, humanize=0.004)
        for b in ([0, 2] if not tutti else [0, 1, 2, 3]):
            s.add(I.bass_drum(0.55 if b in (0, 2) else 0.4, s.rng), "bd", bar, b, humanize=0.003)
        tm = bass % 12 + N("C2")
        if tm < N("F2") - 3:
            tm += 12
        if bar % 2 == 0 or build:
            s.add(I.timpani(tm, 0.65, s.rng), "timp", bar, 0)
        if bar % 8 == 7 and not build:
            for j, b in enumerate([3.0, 3 + 1 / 3, 3 + 2 / 3]):
                s.add(I.timpani(N("A2") if j < 2 else N("D3") - 12 + 12, 0.55 + 0.1 * j, s.rng), "timp", bar, b)
    for b in (0, 8, 16, 24):
        s.add(I.cymbal(0.55 if b else 0.4, s.rng), "cym", b, 0)
    s.add(I.cymbal_swell(s.beat * 4, 0.7, s.rng), "cym", 23, 0)
    s.add(I.cymbal_swell(s.beat * 8, 0.8, s.rng), "cym", 34, 0)
    s.add(I.timp_roll(N("A2"), s.beat * 7.5, 0.2, 0.8, s.rng), "timp", 34, 0)
    s.add(I.snare_roll(s.beat * 3.8, 0.2, 0.6, s.rng), "snare", 35, 0)
    m2 = [(8, 0, 1, "D5"), (8, 1, .5, "D5"), (8, 1.5, .5, "E5"), (8, 2, 1, "F5"), (8, 3, 1, "A5"),
          (9, 0, 1.5, "G5"), (9, 1.5, .5, "F5"), (9, 2, 2, "E5"),
          (10, 0, 1, "G5"), (10, 1, 1, "D5"), (10, 2, 1, "Bb4"), (10, 3, 1, "D5"), (11, 0, 3, "G5"), (11, 3, 1, "A5"),
          (12, 0, 1.5, "Bb5"), (12, 1.5, .5, "A5"), (12, 2, 2, "F5"), (13, 0, 1, "E5"), (13, 1, 1, "G5"), (13, 2, 1.5, "C6"), (13, 3.5, .5, "Bb5"),
          (14, 0, 2, "A5"), (14, 2, 1, "E5"), (14, 3, 1, "C#5"), (15, 0, 1, "E5"), (15, 1, .5, "A4"), (15, 1.5, .5, "C#5"), (15, 2, 2, "E5")]
    s.mel("tpt", m2, 0.7, gain=0.75, octave=-1)
    s.mel("hn", [(b, bt, d, n) for (b, bt, d, n) in m2], 0.55, gain=0.45, octave=-2)
    cm = [(16, 0, 2, "Bb3"), (16, 2, 1, "D4"), (16, 3, 1, "F4"), (17, 0, 1.5, "F4"), (17, 1.5, .5, "Eb4"), (17, 2, 2, "D4"),
          (18, 0, 2, "C4"), (18, 2, 1, "F4"), (18, 3, 1, "A4"), (19, 0, 1.5, "G4"), (19, 1.5, .5, "F4"), (19, 2, 2, "C4"),
          (20, 0, 2, "D4"), (20, 2, 1, "G4"), (20, 3, 1, "Bb4"), (21, 0, 1.5, "A4"), (21, 1.5, .5, "G4"), (21, 2, 2, "D4"),
          (22, 0, 2, "E4"), (22, 2, 1, "A4"), (22, 3, 1, "C#5"), (23, 0, 4, "A4")]
    s.mel("hn", cm, 0.65, gain=0.75)
    s.mel("tbn", cm, 0.55, gain=0.5, octave=-1)
    m4 = [(24, 0, 1, "D5"), (24, 1, .5, "D5"), (24, 1.5, .5, "E5"), (24, 2, 1, "F5"), (24, 3, 1, "A5"),
          (25, 0, 1.5, "G5"), (25, 1.5, .5, "F5"), (25, 2, 2, "E5"),
          (26, 0, 1, "F5"), (26, 1, 1, "D5"), (26, 2, 1, "Bb4"), (26, 3, 1, "D5"), (27, 0, 3, "F5"), (27, 3, 1, "G5"),
          (28, 0, 1.5, "Bb5"), (28, 1.5, .5, "A5"), (28, 2, 2, "G5"), (29, 0, 1, "A5"), (29, 1, 1, "E5"), (29, 2, 1.5, "C#6"), (29, 3.5, .5, "Bb5"),
          (30, 0, 2, "A5"), (30, 2, 1, "F5"), (30, 3, 1, "D5"), (31, 0, 1, "E5"), (31, 1, .5, "A4"), (31, 1.5, .5, "C#5"), (31, 2, 2, "E5")]
    s.mel("tpt", m4, 0.8, gain=0.75, octave=-1)
    s.mel("vln1", m4, 0.7, gain=0.6)
    s.mel("hn", m4, 0.6, gain=0.45, octave=-2)
    return s.render(2.6, -18.0)


# =========================================================================== stings (one-shot, not looped)
def _oneshot(bpm, bars, seed):
    s = Score(bpm, bars, seed=seed, tail=5.0)
    s.loop = False
    return s


def _trim(x, thr_db=-60):
    a = np.max(np.abs(x), 1)
    idx = np.where(a > db(thr_db))[0]
    end = idx[-1] + secs(0.1) if len(idx) else len(x)
    y = x[:end].copy()
    f = secs(0.4)
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    return y


def sting_victory():
    s = _oneshot(100, 4, 41)
    s.add(I.timp_roll(N("A2"), s.beat * 2, 0.2, 0.7, s.rng), "timp", 0, 0)
    fan = [(0, 2, .5, "D4"), (0, 2.5, .25, "D4"), (0, 2.75, .25, "D4"), (0, 3, 1, "A4"), (1, 0, 1.5, "F#4"), (1, 1.5, .5, "A4"), (1, 2, 2, "D5")]
    s.mel("tpt", fan, 0.85, gain=0.8)
    s.mel("hn", [(b, bt, d, n) for (b, bt, d, n) in fan], 0.6, gain=0.5, octave=-1)
    for m in ["D3", "F#3", "A3", "D4"]:
        s.br("tbn" if N(m) < N("A3") else "hn", 1, 2, 6, N(m), 0.7, gain=0.55)
    for m in ["A4", "D5", "F#5"]:
        s.str_("vln1", 1, 2, 6, N(m), 0.6, "tremolo")
    s.str_("cb", 1, 2, 6, N("D2"), 0.7)
    s.str_("vc", 1, 2, 6, N("D3"), 0.7)
    s.add(I.timpani(N("D2") + 12, 0.9, s.rng), "timp", 1, 2)
    s.add(I.cymbal(0.7, s.rng), "cym", 1, 2)
    s.add(I.bass_drum(0.8, s.rng), "bd", 1, 2)
    return _trim(s.render(3.0, -16.0))


def sting_defeat():
    s = Score(60, 4, beats_per_bar=2, seed=43, tail=5.0)
    s.loop = False
    seq = [("Dm", 0), ("Bb", 1), ("Gm", 2), ("A", 3)]
    for ch, bar in seq:
        bass, low, up, _ = CH[ch]
        d = 2.2 if bar < 3 else 4.0
        s.str_("cb", bar, 0, d, bass + 12 if bass < N("C2") else bass, 0.45)
        for m in low:
            s.str_("vla", bar, 0, d, m, 0.35, bright=0.6)
    s.mel("hn", [(0, 0.5, 1, "F4"), (0, 1.5, .5, "E4"), (1, 0, 2, "D4"), (2, 0, 1, "Bb3"), (2, 1, 1, "G3"), (3, 0, 3.5, "A3")], 0.4)
    s.add(I.timpani(N("D2"), 0.35, s.rng, 3.0), "timp", 0, 0)
    s.add(I.timpani(N("A2"), 0.25, s.rng, 3.0), "timp", 3, 0)
    return _trim(s.render(3.0, -21.0), -50)


def sting_war():
    s = _oneshot(80, 3, 47)
    s.add(I.timp_roll(N("D2"), s.beat * 2.0, 0.15, 0.95, s.rng), "timp", 0, 0)
    s.add(I.snare_roll(s.beat * 2.0, 0.1, 0.6, s.rng), "snare", 0, 0)
    for m in ["D2", "A2", "D3", "Eb3"]:
        s.br("tbn" if N(m) > N("C2") else "tuba", 0, 2, 3.5, N(m), 0.85, gain=0.6)
    for m in ["A3", "D4", "Eb4"]:
        s.br("hn", 0, 2, 3.5, N(m), 0.8, gain=0.5)
    s.add(I.timpani(N("D2"), 1.0, s.rng, 3.0), "timp", 0, 2)
    s.add(I.bass_drum(1.0, s.rng), "bd", 0, 2)
    s.add(I.cymbal(0.6, s.rng), "cym", 0, 2)
    s.str_("cb", 0, 2, 5, N("D2"), 0.6, "tremolo")
    s.str_("vc", 0, 2, 5, N("D3"), 0.55, "tremolo")
    return _trim(s.render(2.8, -16.0))


def sting_era():
    s = _oneshot(72, 4, 53)
    for i, nm in enumerate(["A3", "D4", "G4", "C5"]):
        s.br("hn", 0, i * 0.75, 3.0 - i * 0.6, N(nm), 0.45 + 0.08 * i, gain=0.7)
    s.add(I.cymbal_swell(s.beat * 3, 0.5, s.rng), "cym", 0, 0)
    for m in ["F3", "A3", "C4", "F4"]:
        s.br("tbn" if N(m) < N("A3") else "hn", 0, 3, 5, N(m), 0.6, gain=0.5)
    for m in ["A4", "C5", "F5", "A5"]:
        s.str_("vln1", 0, 3, 6, N(m), 0.5, "legato")
    s.str_("cb", 0, 3, 6, N("F2"), 0.55)
    s.str_("vc", 0, 3, 6, N("C3"), 0.5)
    s.add(I.timpani(N("F2"), 0.7, s.rng), "timp", 0, 3)
    s.add(I.cymbal(0.5, s.rng), "cym", 0, 3)
    return _trim(s.render(3.4, -18.0))


TRACKS = {"music_campaign": campaign, "music_tension": tension, "music_battle": battle}
STINGS = {"sting_victory": sting_victory, "sting_defeat": sting_defeat, "sting_war": sting_war, "sting_era": sting_era}
