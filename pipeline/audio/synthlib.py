"""Small, dependency-light (numpy only) synthesis/DSP toolkit used to build every Iron Crowns audio file.

Everything here is original procedural synthesis: oscillators, noise, envelopes, FFT filters,
an algorithmic reverb impulse response and a look-ahead limiter. No samples, no external audio.
"""
import numpy as np

SR = 44100
_TABLES = {}
TBL = 4096


def secs(n):
    return int(round(n * SR))


def midi_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def db(x):
    return 10 ** (x / 20.0)


# ------------------------------------------------------------------ oscillators
def _table(maxh, fc, tilt=1.0, odd=False, formants=None):
    """Band-limited single-cycle wavetable: harmonics 1/k^tilt, low-passed at harmonic number fc."""
    key = (maxh, round(fc, 2), tilt, odd, tuple(formants) if formants else None)
    t = _TABLES.get(key)
    if t is not None:
        return t
    ph = np.arange(TBL) / TBL
    out = np.zeros(TBL)
    for k in range(1, maxh + 1):
        if odd and k % 2 == 0:
            a = 0.18 / k ** tilt
        else:
            a = 1.0 / k ** tilt
        a /= 1.0 + (k / fc) ** 2
        if formants:
            for (fk, g, bw) in formants:
                a *= 1.0 + g * np.exp(-0.5 * ((k - fk) / bw) ** 2)
        out += a * np.sin(2 * np.pi * k * ph)
    out /= np.max(np.abs(out)) + 1e-9
    out = np.append(out, out[0])
    _TABLES[key] = out
    return out


def wt_osc(freq_t, table, phase0=0.0):
    """freq_t: per-sample frequency array (Hz). Linear-interpolated wavetable lookup."""
    ph = (phase0 + np.cumsum(freq_t) / SR) % 1.0
    idx = ph * TBL
    i0 = idx.astype(np.int64)
    fr = idx - i0
    return table[i0] * (1 - fr) + table[i0 + 1] * fr


def maxh_for(f, limit=16000.0):
    return int(max(1, min(80, limit // max(f, 20.0))))


# ------------------------------------------------------------------ envelopes
def adsr(n, a, d, s, r, sus_len=None):
    """n samples total; a/d/r in seconds; s sustain level. Release starts at n - r."""
    env = np.zeros(n)
    A, D, R = secs(a), secs(d), secs(r)
    A = max(A, 1)
    rs = max(n - R, 0)
    t = np.arange(n)
    env = np.where(t < A, t / A, 0.0)
    m = (t >= A) & (t < A + D)
    env[m] = 1.0 - (1.0 - s) * (t[m] - A) / max(D, 1)
    env[t >= A + D] = s
    if R > 0 and rs < n:
        lvl = env[rs] if rs < n else s
        rr = t >= rs
        env[rr] = lvl * (1.0 - (t[rr] - rs) / max(R, 1)) ** 2
    return np.clip(env, 0, None)


def expdec(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


# ------------------------------------------------------------------ noise & filters
def noise(n, rng):
    return rng.standard_normal(n)


def fft_filter(x, gain_fn):
    """Zero-phase static filter: gain_fn(freq_array) -> linear gain. Pads to avoid wrap."""
    n = len(x)
    N = 1 << int(np.ceil(np.log2(n + 2048)))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    y = np.fft.irfft(X * gain_fn(f), N)[:n]
    return y


def fft_filter_circ(x, gain_fn):
    """Zero-phase static filter applied circularly (no padding): for loop material, so the
    filter's response at the end wraps into the start and the loop seam stays continuous."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return np.fft.irfft(X * gain_fn(f), len(x))


def lp(fc, order=2):
    return lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def hp(fc, order=2):
    return lambda f: 1.0 / np.sqrt(1.0 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def bp(lo, hi, order=2):
    a, b = hp(lo, order), lp(hi, order)
    return lambda f: a(f) * b(f)


def peak(fc, gain_db, q=1.0):
    g = db(gain_db) - 1.0
    return lambda f: 1.0 + g * np.exp(-0.5 * (np.log2(np.maximum(f, 1e-3) / fc) * q * 2.0) ** 2)


def chain(*fs):
    def g(f):
        out = np.ones_like(f)
        for h in fs:
            out = out * h(f)
        return out
    return g


def tv_filter(x, gain_tf, frame=2048, hop=512):
    """Time-varying FFT filter (overlap-add). gain_tf(t_seconds, freq_array) -> gain array."""
    n = len(x)
    win = np.hanning(frame)
    pad = np.concatenate([np.zeros(frame), x, np.zeros(frame)])
    out = np.zeros(len(pad))
    norm = np.zeros(len(pad))
    f = np.fft.rfftfreq(frame, 1.0 / SR)
    for s in range(0, len(pad) - frame, hop):
        seg = pad[s:s + frame] * win
        t = (s - frame + frame / 2) / SR
        y = np.fft.irfft(np.fft.rfft(seg) * gain_tf(max(t, 0.0), f), frame) * win
        out[s:s + frame] += y
        norm[s:s + frame] += win ** 2
    out = out / np.maximum(norm, 1e-3)
    return out[frame:frame + n]


# ------------------------------------------------------------------ mixing helpers
def place(buf, sig, start, gain=1.0, wrap=False):
    """Add sig into buf at sample index start (mono or stereo buf). wrap=True: circular (loops)."""
    n = len(buf)
    if sig.ndim == 1 and buf.ndim == 2:
        sig = np.stack([sig, sig], 1)
    L = len(sig)
    if wrap:
        start %= n
        end = start + L
        if end <= n:
            buf[start:end] += sig * gain
        else:
            k = n - start
            buf[start:] += sig[:k] * gain
            rem = sig[k:]
            while len(rem):
                m = min(len(rem), n)
                buf[:m] += rem[:m] * gain
                rem = rem[m:]
    else:
        if start >= n:
            return
        if start < 0:
            sig = sig[-start:]; start = 0
        end = min(n, start + len(sig))
        buf[start:end] += sig[:end - start] * gain


def pan(sig, p):
    """Constant-power pan, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([sig * np.cos(a), sig * np.sin(a)], 1)


def fade(sig, fin=0.005, fout=0.02):
    s = sig.copy()
    a, b = secs(fin), secs(fout)
    if a > 0:
        s[:a] *= np.linspace(0, 1, a) if s.ndim == 1 else np.linspace(0, 1, a)[:, None]
    if b > 0:
        s[-b:] *= np.linspace(1, 0, b) if s.ndim == 1 else np.linspace(1, 0, b)[:, None]
    return s


# ------------------------------------------------------------------ reverb
def make_ir(length=2.8, decay=(2.6, 1.6, 0.7), early=None, rng=None, stereo=True, predelay=0.012, bright=7000.0):
    """Algorithmic IR: band-split exponentially decaying noise (low/mid/high RT) + early reflections."""
    rng = rng or np.random.default_rng(7)
    n = secs(length)
    chans = []
    for c in range(2 if stereo else 1):
        t = np.arange(n) / SR
        base = rng.standard_normal(n)
        lo = fft_filter(base, lp(400, 2)) * np.exp(-6.9 * t / decay[0])
        mid = fft_filter(base, bp(400, 3000, 2)) * np.exp(-6.9 * t / decay[1])
        hi = fft_filter(base, hp(3000, 2)) * np.exp(-6.9 * t / decay[2])
        ir = fft_filter(lo + mid + hi, lp(bright, 1))
        ir *= np.minimum(1.0, t / 0.03)  # diffuse build-up
        er = early or [(0.011, 0.5), (0.019, 0.35), (0.027, 0.3), (0.041, 0.25), (0.053, 0.2), (0.071, 0.15)]
        for (dt, g) in er:
            k = secs(dt * (1.0 + 0.07 * c))
            if k < n:
                ir[k] += g * 3.0 * (1 if rng.random() > 0.5 else -1)
        pd = secs(predelay)
        ir = np.concatenate([np.zeros(pd), ir])
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        chans.append(ir)
    return np.stack(chans, 1) if stereo else chans[0]


def convolve(x, ir):
    """FFT convolution. x mono or stereo; ir mono or stereo. Returns len(x)+len(ir)-1."""
    def conv1(a, b):
        N = 1 << int(np.ceil(np.log2(len(a) + len(b))))
        return np.fft.irfft(np.fft.rfft(a, N) * np.fft.rfft(b, N), N)[:len(a) + len(b) - 1]
    if x.ndim == 1 and ir.ndim == 1:
        return conv1(x, ir)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if ir.ndim == 1:
        ir = np.stack([ir, ir], 1)
    return np.stack([conv1(x[:, 0], ir[:, 0]), conv1(x[:, 1], ir[:, 1])], 1)


# ------------------------------------------------------------------ dynamics
def _sliding_max(a, w):
    """Max of |a| over a centered-forward window of w samples (block approximation, O(n))."""
    n = len(a)
    blk = max(1, w // 4)
    nb = int(np.ceil(n / blk))
    padded = np.zeros(nb * blk)
    padded[:n] = a
    bm = padded.reshape(nb, blk).max(1)
    k = 4
    bm2 = bm.copy()
    for j in range(1, k + 1):
        bm2[:-j] = np.maximum(bm2[:-j], bm[j:])
    for j in range(1, 2):
        bm2[j:] = np.maximum(bm2[j:], bm[:-j])
    return np.repeat(bm2, blk)[:n]


def limit(x, ceiling_db=-1.0, look=0.005, release=0.08):
    """Look-ahead peak limiter (gain computed from sliding peak, smoothed). Works on mono or stereo."""
    c = db(ceiling_db)
    mono = np.max(np.abs(x), 1) if x.ndim == 2 else np.abs(x)
    pk = _sliding_max(mono, secs(look) * 2)
    g = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    # smooth: fast attack already handled by look-ahead max; release via one-pole on blocks
    blk = 64
    nb = int(np.ceil(len(g) / blk))
    gb = np.ones(nb * blk); gb[:len(g)] = g
    gb = gb.reshape(nb, blk).min(1)
    a = np.exp(-blk / (release * SR))
    sm = np.empty(nb)
    cur = 1.0
    for i in range(nb):
        cur = gb[i] if gb[i] < cur else a * cur + (1 - a) * gb[i]
        sm[i] = cur
    gs = np.interp(np.arange(len(g)), np.arange(nb) * blk + blk / 2, sm)
    gs = np.minimum(gs, g + 0.0)  # never exceed instantaneous safe gain
    y = x * (gs[:, None] if x.ndim == 2 else gs)
    return np.clip(y, -c, c)


def normalize(x, peak_db=-1.0):
    p = np.max(np.abs(x)) + 1e-12
    return x * (db(peak_db) / p)


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def loop_crossfade(x, L, C):
    """x has at least L+C samples; returns L samples whose end flows into its start (equal-power)."""
    out = x[:L].copy()
    t = np.linspace(0, 1, C)
    fi, fo = np.sin(t * np.pi / 2), np.cos(t * np.pi / 2)
    if x.ndim == 2:
        fi, fo = fi[:, None], fo[:, None]
    out[:C] = x[:C] * fi + x[L:L + C] * fo
    return out


def write_wav(path, x):
    import wave
    x = np.clip(x, -1, 1)
    ch = 1 if x.ndim == 1 else x.shape[1]
    pcm = (x * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
