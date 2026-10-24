"""Eras v3 kit 5: English / Welsh longbowman, c.1300 (Falkirk 1298 era) (docs/char/ERAS_PROGRESS.md).
Patches char_v2 (loaded by char_v2_build.py when V3_KIT=kit_med_archer). Only the base human (MakeHuman head / eyes /
hands, ear fix), body cage, rig and material library are shared; every garment / item is built fresh here:
  * plain wool cote (tunic) in the team colour: short sleeves ending above the elbow, knee-length skirt split front and
    back with gathered folds; undyed linen shirt sleeves below
  * dyed (moss green) wool chaperon hood: fitted hood framing the face, shoulder cape, long liripipe down the back
  * narrow leather belt with a brass buckle; small knife at the right hip; steel buckler hung at the left hip
  * linen arrow bag slung across the back (leather spacer at the mouth, white goose fletchings over the right shoulder),
    leather strap over the right shoulder to the left hip
  * leather bracer on the left forearm
  * grey-brown wool hose; matte worn-leather ankle shoes
  * yew longbow (~1.78 m, braced, horn nocks, leather grip, linen string), held in the left hand (musket clip slot;
    bow-specific clips requested from Rob in docs/char/ROB_CLIP_REQUESTS.md)"""
import math, bpy
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_med_archer'
C.CLIP_STYLE = 'musket'                 # bow carried in the left hand (shoulder_arms grip) until bow clips exist
BOW_G, BOW_L = -0.31, 0.89              # grip at the left-hand hold of shoulder_arms (prop-local y), half length
C.TIP_LOCAL = (0.0, BOW_G + BOW_L, 0.05)   # upper nock (weapon_tip on the prop)
C.SLOT_MAT.update({'stock': 'canvas', 'felt': 'wool', 'roll': 'canvas', 'cartbox': 'worn_leather', 'shoe': 'worn_leather',
                   'breeches': 'wool', 'scabbard': 'wood', 'sash': 'canvas', 'piping': 'canvas', 'epaulette': 'hide'})
C.BODY_TRIS = 4600
HM.FIST['.L'] = 0.007
C.KIT_PAL = {'stock': '#d9d0bb', 'felt': '#58622f', 'roll': '#c9bb98', 'cartbox': '#4f3722', 'shoe': '#4a3424',
             'breeches': '#6b6352', 'metal': '#b8913a', 'steel': '#a5abb1', 'wood': '#8a5a32', 'scabbard': '#c2a070',
             'sash': '#ece8de', 'piping': '#cfc4a2', 'epaulette': '#cdb98e'}
C.KIT_RULES = [(('arhood', 'arlirip'), 'head'), (('arcape', 'arbelt', 'arsleeve', 'arbracer', 'arstrap', 'arshoe'), 'transfer'),
               (('arskirt',), 'tail'), (('arbag', 'arrow', 'arfl'), 'chest'), (('arbuck', 'arknife', 'arbuckler'), 'hips'),
               (('arbow',), 'prop')]

C.LEG_PROF = [(0.0, 0.086, 0.086, 0.086), (0.10, 0.088, 0.088, 0.092), (0.30, 0.074, 0.078, 0.070, 0.005), (0.45, 0.056, 0.058, 0.055),
              (0.52, 0.053, 0.055, 0.052), (0.60, 0.056, 0.054, 0.062, -0.003), (0.68, 0.058, 0.052, 0.067, -0.006),
              (0.85, 0.044, 0.042, 0.047), (0.95, 0.038, 0.040, 0.040), (1.0, 0.042, 0.046, 0.044)]
SLEEVE_Z = 1.175
SHOE_Z = 0.125

def body_slot(p, part):
    x, y, z = p
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'coat'
    if part == 'arm': return 'coat' if z > SLEEVE_Z - 0.004 else 'stock'
    if part == 'leg': return 'shoe' if z < SHOE_Z else 'breeches'
    if z > 1.586: return 'skin'
    return 'coat'
C.body_slot = body_slot

# ------------------------------------------------------------------ cote skirt (knee length, split front + back, gathered)
SK = [(1.035, .158, .106, .112, 0.000), (0.98, .170, .112, .126, -0.004), (0.92, .181, .120, .146, -0.008),
      (0.82, .187, .128, .152, -0.006), (0.68, .192, .136, .154, -0.002), (0.555, .197, .142, .156, 0.0)]
SK_Z0, SK_Z1 = SK[0][0], SK[-1][0]

def _sk(z):
    for a, b in zip(SK, SK[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0]); return [lerp(a[k], b[k], t) for k in range(1, 5)]
    return list((SK[0] if z > SK_Z0 else SK[-1])[1:])

def skirt(hi=False):
    out = []
    nz, na = (56, 120) if hi else (6, 8)
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            t = i / nz; z = lerp(SK_Z0, SK_Z1, t)
            rx, rf, rb, off = _sk(z)
            dl = math.radians(7.0) * ss(0.74, SK_Z1, z)
            outer, inner = [], []
            for j in range(na + 1):
                a = lerp(math.pi / 2 - dl, -math.pi / 2 + dl, j / na)
                ca, sa = math.cos(a), math.sin(a)
                f = lambda q: math.copysign(abs(q) ** (2.0 / 2.3), q)
                r = 1.0
                if hi:   # soft gathered folds falling from the belt, deepening to the hem; turned hem
                    g = ss(SK_Z0 - 0.02, SK_Z1, z)
                    r += 0.020 * g * math.sin(a * 9.0 + 0.6 * math.sin(a * 3.0)) + 0.008 * g * math.sin(a * 17.0 + 1.3)
                    r += 0.012 * math.exp(-((z - SK_Z1 - 0.012) / 0.008) ** 2)
                px, py = f(ca) * rx * r, f(sa) * (rf if sa > 0 else rb) * r
                p = V(s * px, py + off, z)
                d = V(s * f(ca), f(sa), 0).normalized()
                outer.append(p); inner.append(p - d * 0.006)
            secs.append(outer + inner[::-1])
        out.append(grid_sweep('arskirt' + ('R' if s > 0 else 'L'), secs, cap0=True, cap1=True, slot='coat'))
    return out

# ------------------------------------------------------------------ sleeve hems, bracer, shoe tops
def bands(tree, hi=False):
    out = []
    for s in (1, -1):
        out.append(V3P.hem_band(tree, (s * 0.205, -0.010, SLEEVE_Z - 0.01), lambda x, y: SLEEVE_Z, hi, depth=0.018, off=0.0035,
                                name='arsleeve.' + ('R' if s > 0 else 'L'), slot='coat', n=72 if hi else 12))
        out.append(V3P.hem_band(tree, (s * 0.10, -0.005, SHOE_Z - 0.01), lambda x, y: SHOE_Z + 0.006 * ss(-0.02, 0.06, y), hi,
                                depth=0.010, off=0.0025, name='arshoe.' + ('R' if s > 0 else 'L'), slot='shoe', n=60 if hi else 10))
    out.append(V3P.hem_band(tree, (-0.214, -0.004, 1.06), lambda x, y: 1.075, hi, depth=0.115, off=0.0045,
                            name='arbracer', slot='cartbox', n=64 if hi else 10))
    return out

# ------------------------------------------------------------------ belt, buckle, knife, buckler
BELT_TOP = 1.046

def belt(tree, hi=False):
    out = [V3P.hem_band(tree, (0.0, 0.0, BELT_TOP - 0.01), lambda x, y: BELT_TOP + 0.008 * ss(0.0, 0.10, y), hi, depth=0.022,
                        off=0.011, name='arbelt', slot='cartbox', n=120 if hi else 22)]
    fr = V3P.surf(tree, (-0.02, 0.5, BELT_TOP - 0.006), (0, -1, 0), 0.013)
    c = fr[0] if fr else V(-0.02, 0.11, BELT_TOP - 0.006)
    out.append(superellipsoid('arbuck', c + V(0, 0.003, 0), (0.019, 0.005, 0.017), e=(2.2, 2.6), n=(12, 6) if hi else (8, 3), slot='metal'))
    # small knife at the right hip, hilt up-forward
    a = V(0.150, 0.060, 1.035); b = V(0.175, 0.040, 0.860); d = (b - a).normalized()
    out.append(limb('arknife', [(0, a), (1, b)], [(0, 0.013, 0.007, 0.007), (0.8, 0.010, 0.006, 0.006), (1, 0.003, 0.003, 0.003)],
                    6 if hi else 2, 10 if hi else 5, fwd=V(1, 0, 0), slot='cartbox', e=2.4))
    out.append(limb('arknife.hilt', [(0, a), (1, a - d * 0.085)], [(0, 0.010, 0.010, 0.010), (0.85, 0.011, 0.011, 0.011), (1, 0.008, 0.008, 0.008)],
                    3 if hi else 1, 8 if hi else 5, fwd=V(1, 0, 0), slot='wood'))
    # steel buckler hung by its grip from the belt at the left hip (domed, central boss, rolled rim)
    n = V(-0.93, 0.30, -0.10).normalized(); bc = V(-0.215, 0.050, 0.865)
    prof = [(0.0, 0.004, 0.004, 0.004), (0.02, 0.140, 0.140, 0.140), (0.18, 0.142, 0.142, 0.142), (0.30, 0.132, 0.132, 0.132),
            (0.55, 0.100, 0.100, 0.100), (0.70, 0.052, 0.052, 0.052), (0.78, 0.046, 0.046, 0.046), (0.92, 0.030, 0.030, 0.030),
            (1.0, 0.004, 0.004, 0.004)]
    out.append(limb('arbuckler', [(0, bc - n * 0.006), (1, bc + n * 0.040)], prof, 18 if hi else 4, 40 if hi else 10,
                    fwd=V(0, 0, 1), slot='steel', cap0=True, cap1=True))
    out.append(limb('arbuck.strap', [(0, bc + V(0.010, 0.0, 0.10)), (1, V(-0.150, 0.060, BELT_TOP - 0.004))], [(0, 0.009, 0.0025, 0.0025)],
                    3 if hi else 1, 4, fwd=V(-1, 0.3, 0), slot='cartbox', e=4.0))
    return out

# ------------------------------------------------------------------ arrow bag on the back + shoulder strap
BAG0, BAG1 = V(-0.075, 0.0, 0.98), V(0.135, 0.0, 1.50)   # x, z of the bag axis (bottom -> mouth); y fitted to the back

def _back_y(tree, x, z, off):
    h = V3P.surf(tree, (x, -0.6, z), (0, 1, 0), 0.0)
    return (h[0].y if h else -0.12) - off

def arrow_bag(tree, hi=False):
    out = []
    R0, R1 = 0.046, 0.052
    pts = []
    for k in range(7):
        t = k / 6; p = BAG0.lerp(BAG1, t)
        pts.append((t, V(p.x, _back_y(tree, p.x, p.z, lerp(R0, R1, t) * 0.92 + 0.004), p.z)))
    # smooth the fitted y (the shoulder blades / belt shouldn't kink the bag)
    ys = [p.y for _, p in pts]; ys = [sum(ys[max(i - 1, 0):i + 2]) / len(ys[max(i - 1, 0):i + 2]) for i in range(len(ys))]
    pts = [(t, V(p.x, y, p.z)) for (t, p), y in zip(pts, ys)]
    top = pts[-1][1]; ax = (pts[-1][1] - pts[0][1]).normalized()
    prof = [(0.0, 0.010, 0.010, 0.010), (0.04, 0.040, 0.040, 0.040), (0.12, R0, R0, R0), (0.80, R1, R1, R1),
            (0.93, R1 * 0.90, R1 * 0.90, R1 * 0.90), (1.0, R1 * 0.96, R1 * 0.96, R1 * 0.96)]
    if hi:   # linen creases
        prof = [(t, rx * (1 + 0.05 * math.sin(t * 31)), rf * (1 + 0.05 * math.sin(t * 23 + 1)), rb) for t, rx, rf, rb in
                [(i / 24, *C.interp_prof(prof, i / 24)[:3]) for i in range(25)]]
    out.append(limb('arbag', pts, prof, 24 if hi else 5, 16 if hi else 7, fwd=V(0, -1, 0), slot='roll', cap0=True, cap1=False))
    out.append(limb('arbag.sp', [(0, top - ax * 0.018), (1, top + ax * 0.004)], [(0, R1 * 1.02, R1 * 1.02, R1 * 1.02)],
                    2 if hi else 1, 16 if hi else 7, fwd=V(0, -1, 0), slot='cartbox'))
    # arrows: nocks + white goose fletching standing out of the bag mouth
    u = ax.cross(V(0, -1, 0)).normalized(); w = ax.cross(u).normalized()
    na = 9 if hi else 6
    for k in range(na):
        a = 2 * math.pi * k / na + 0.3
        rr = 0.030 if k % 2 else 0.016
        b = top + (u * math.cos(a) + w * math.sin(a)) * rr
        d = (ax + u * 0.05 * math.cos(a) + w * 0.05 * math.sin(a)).normalized()
        L = 0.20 + 0.025 * ((k * 7) % 3)
        out.append(limb('arrow', [(0, b - d * 0.05), (1, b + d * L)], [(0, 0.0048, 0.0048, 0.0048)], 1, 6 if hi else 3, fwd=w,
                        slot='scabbard', cap0=False))
        for v in range(3 if hi else 2):
            av = a + v * (2 * math.pi / (3 if hi else 2)) + 0.4
            fd = (u * math.cos(av) + w * math.sin(av))
            fd = (fd - d * fd.dot(d)).normalized()
            out.append(limb('arfl', [(0, b + d * (L - 0.15)), (1, b + d * (L - 0.012))],
                            [(0.0, 0.0012, 0.0005, 0.0005, 0.004), (0.15, 0.0012, 0.011, 0.0005, 0.004), (0.85, 0.0012, 0.014, 0.0005, 0.004),
                             (1.0, 0.0012, 0.0005, 0.0005, 0.004)], 4 if hi else 1, 4, fwd=fd, slot='sash', e=2.0))
    return out

def strap(tree, hi=False):
    """bag strap: from the bag mouth over the right shoulder, diagonally down the chest to the left hip, round to the bag foot."""
    pn = []
    N = 30 if hi else 9
    # front run: right shoulder top -> left hip (cast from the front)
    for k in range(N + 1):
        t = k / N
        x = lerp(0.105, -0.150, t); z = lerp(1.455, 1.000, t)
        h = V3P.surf(tree, (x, 0.6, z), (0, -1, 0), 0.0045) if t > 0.08 else V3P.surf(tree, (x, -0.02 + 0.6 * 0, 1.9), (0, 0, -1), 0.0045)
        if h: pn.append(h)
    out = [V3P.ribbon('arstrap', pn, 0.030, hi, th=0.003, slot='cartbox')]
    pn = []
    for k in range(N // 2 + 1):   # top of the shoulder, front -> back (cast from above)
        t = k / (N // 2)
        y = lerp(0.03, -0.10, t)
        h = V3P.surf(tree, (0.105, y, 1.9), (0, 0, -1), 0.0045)
        if h: pn.append(h)
    if len(pn) > 1: out.append(V3P.ribbon('arstrap.sh', pn, 0.030, hi, th=0.003, slot='cartbox'))
    return out

# ------------------------------------------------------------------ chaperon: fitted hood + shoulder cape + liripipe
HC = V(0, 0.004, 1.664)
_FIT = {}

def _hood_dirs(nb, na):
    rows = []
    for i in range(nb + 1):
        be = math.radians(lerp(-38.0, 87.0, i / nb))
        A = math.radians(180.0 - 60.0 * ss(math.radians(38.0), math.radians(14.0), be) - 12.0 * ss(math.radians(-8), math.radians(-38), be))
        rows.append([V(math.sin(al) * math.cos(be), -math.cos(al) * math.cos(be), math.sin(be))
                     for al in [lerp(-A, A, j / na) for j in range(na + 1)]])
    return rows

def _fit_hood(htree, nb, na):
    dirs = _hood_dirs(nb, na)
    R = np.zeros((nb + 1, na + 1))
    for i, row in enumerate(dirs):
        for j, d in enumerate(row):
            h = htree.ray_cast(HC + d * 0.35, -d)
            R[i, j] = (h[0] - HC).length if h[0] is not None and h[0].z > 1.54 else np.nan
    for i in range(nb + 1):
        m = np.isnan(R[i])
        if m.all(): R[i] = np.nanmean(R) if not np.isnan(R).all() else 0.1
        elif m.any(): R[i, m] = np.nanmax(R[i])
    raw = R.copy()
    k = max(1, (na + 1) // 14)
    D = R.copy()
    for di in (-1, 0, 1):
        for dj in range(-k, k + 1):
            D = np.maximum(D, np.roll(np.roll(R, di, 0), dj, 1))
    for _ in range(4):
        D = (D + np.roll(D, 1, 0) + np.roll(D, -1, 0) + np.roll(D, 1, 1) + np.roll(D, -1, 1)) / 5.0
        D[0], D[-1] = (D[0] + D[1]) / 2, (D[-1] + D[-2]) / 2
    D = np.maximum(D, raw + 0.004)
    # loose wool: a little bag at the crown / back of the head
    for i, row in enumerate(dirs):
        for j, d in enumerate(row):
            D[i, j] += 0.010 * ss(0.1, 0.8, d.z) * ss(0.2, -0.6, d.y) + 0.004
    return dirs, D

def hood(hi=False):
    dirs, R = _FIT['hood_hi' if hi else 'hood_lo']
    secs = []
    for i, row in enumerate(dirs):
        outer = [HC + d * (R[i, j] + 0.0085) for j, d in enumerate(row)]
        inner = [HC + d * (R[i, j] + 0.0035) for j, d in enumerate(row)]
        secs.append(outer + inner[::-1])
    out = [grid_sweep('arhood', secs, closed_u=True, cap0=False, cap1=True, slot='felt')]
    # turned-back face edge (rolled hem round the face opening)
    op = [i for i, row in enumerate(dirs) if (row[0] - row[-1]).length > 0.02]   # rows with a face opening only
    edge = [HC + dirs[i][0] * (R[i, 0] + 0.006) for i in op] + [HC + dirs[i][-1] * (R[i, -1] + 0.006) for i in reversed(op)]
    path = [(k / (len(edge) - 1), p) for k, p in enumerate(edge)]
    out.append(limb('arhood.roll', path, [(0, 0.0055 if hi else 0.0068, 0.0055 if hi else 0.0068, 0.0055 if hi else 0.0068)], len(edge) - 1, 6 if hi else 4, fwd=V(0, 1, 0),
                    slot='felt', cap0=True, cap1=True))
    # liripipe: long tail from the crown hanging down the back
    p0 = HC + V(0, -0.86, 0.50).normalized() * 0.112
    lp = [(0, p0), (0.2, V(0.0, -0.118, 1.640)), (0.5, V(0.004, -0.128, 1.575)), (0.8, V(0.009, -0.122, 1.515)), (1, V(0.012, -0.112, 1.480))]
    out.append(limb('arlirip', lp, [(0, 0.013, 0.008, 0.008), (0.3, 0.010, 0.006, 0.006), (0.85, 0.007, 0.0045, 0.0045), (1, 0.004, 0.003, 0.003)],
                    16 if hi else 4, 8 if hi else 4, fwd=V(0, -1, 0), slot='felt'))
    return out

CAPE_NR, CAPE_NA = 30, 96   # hi grid; lo takes every 6th row / column (same fitted surface)
def _cape_z(a, t):
    fr = 0.5 + 0.5 * math.sin(a)                       # 1 at the front (+y), 0 at the back
    ztop = lerp(1.630, 1.556, fr ** 1.5)
    zhem = 1.330 + 0.060 * abs(math.cos(a)) ** 1.5   # shorter over the upper arms (arm swings stay under it)
    return lerp(ztop, zhem, t)

def _fit_cape(trees):
    R = np.full((CAPE_NR + 1, CAPE_NA), np.nan)
    cy = -0.004
    for i in range(CAPE_NR + 1):
        t = i / CAPE_NR
        for j in range(CAPE_NA):
            a = 2 * math.pi * j / CAPE_NA
            d = V(math.cos(a), math.sin(a), 0); z = _cape_z(a, t)
            c = V(0, cy, z); best = None
            for tr in trees:
                h = tr.ray_cast(c + d * 0.6, -d)
                if h[0] is not None:
                    r = (V(h[0].x, h[0].y, 0) - V(0, cy, 0)).length
                    best = r if best is None else max(best, r)
            R[i, j] = best if best is not None else np.nan
    for i in range(CAPE_NR + 1):
        m = np.isnan(R[i])
        if m.any(): R[i, m] = np.nanmax(R[i]) if not m.all() else 0.15
    for i in range(CAPE_NR + 1):   # surface clearance growing to the hem
        R[i] += 0.006 + 0.014 * ss(0.0, 0.5, i / CAPE_NR) + 0.012 * ss(0.3, 1.0, i / CAPE_NR) * np.abs(np.cos(2 * np.pi * np.arange(CAPE_NA) / CAPE_NA))
    for i in range(1, CAPE_NR + 1):   # cloth hangs: never tucks back in below a ledge (shoulders)
        R[i] = np.maximum(R[i], R[i - 1] - 0.002)
    for _ in range(6):
        S = (R + np.roll(R, 1, 1) + np.roll(R, -1, 1)) / 3.0
        S[1:-1] = (S[1:-1] + R[:-2] + R[2:]) / 3.0
        R = np.maximum(S, R - 0.002)
    return R, cy

def cape(hi=False):
    R, cy = _FIT['cape']
    rs = range(0, CAPE_NR + 1, 1 if hi else 6); cs = range(0, CAPE_NA, 1 if hi else 6)
    secs = []
    for i in rs:
        t = i / CAPE_NR
        outer, inner = [], []
        for j in cs:
            a = 2 * math.pi * j / CAPE_NA
            r = R[i, j]
            if not hi:   # lo: padded local max of the hi fit (shoulders / hood bib between samples stay inside, no bake bleed)
                r = float(R[max(0, i - 3):i + 4, [(j + k) % CAPE_NA for k in range(-3, 4)]].max()) + 0.006 + 0.010 * abs(math.cos(a)) * ss(0.25, 0.75, t) + 0.006 * ss(0.4, 1.0, t)
            if hi: r += 0.010 * ss(0.4, 1.0, t) * math.sin(a * 11.0 + 0.8) + 0.010 * math.exp(-((t - 1.0) / 0.03) ** 2)
            z = _cape_z(a, t)
            outer.append(V(math.cos(a) * r, cy + math.sin(a) * r, z))
            inner.append(V(math.cos(a) * (r - 0.005), cy + math.sin(a) * (r - 0.005), z))
        secs.append(outer)
    ins = [[V(p.x - (p.x) / max(1e-6, math.hypot(p.x, p.y - cy)) * 0.005, p.y - (p.y - cy) / max(1e-6, math.hypot(p.x, p.y - cy)) * 0.005, p.z)
            for p in s] for s in secs]
    return [V3P.orient_out(grid_sweep('arcape', secs + ins[::-1], closed_u=True, cap0=False, cap1=False, slot='felt'))]

def fit(htree, body_tree):
    _FIT['hood_hi'] = _fit_hood(htree, 40, 72)
    dirs, D = _FIT['hood_hi']   # lo hood: subsample of the hi fit, padded by the local max (ears / hair between samples stay inside)
    ri = list(range(0, 41, 5)); cj = list(range(0, 73, 6))
    Dl = np.array([[D[max(0, i - 3):i + 4, max(0, j - 4):j + 5].max() + 0.0055 for j in cj] for i in ri])
    _FIT['hood_lo'] = ([[dirs[i][j] for j in cj] for i in ri], Dl)
    _FIT['cape'] = _fit_cape([body_tree, htree])
    print('[archer] cape radius range', round(float(_FIT['cape'][0].min()), 3), round(float(_FIT['cape'][0].max()), 3))

# ------------------------------------------------------------------ yew longbow (prop frame: stave along +y, string on +z)
def bow(hi=False):
    import char_rig as Rg
    T = lambda p: Rg.REST['prop'] @ V(p)
    up = Rg.REST['prop'].to_3x3() @ V(0, 0, 1)
    def z_of(y): u = (y - BOW_G) / BOW_L; return -0.05 + 0.10 * u * u
    n = 40 if hi else 8
    path = [(k / n, T((0, lerp(BOW_G - BOW_L, BOW_G + BOW_L, k / n), z_of(lerp(BOW_G - BOW_L, BOW_G + BOW_L, k / n))))) for k in range(n + 1)]
    prof = [(0.0, 0.0075, 0.0065, 0.0055), (0.08, 0.010, 0.009, 0.007), (0.40, 0.0145, 0.0150, 0.0105), (0.47, 0.0155, 0.0165, 0.0120),
            (0.53, 0.0155, 0.0165, 0.0120), (0.60, 0.0145, 0.0150, 0.0105), (0.92, 0.010, 0.009, 0.007), (1.0, 0.0075, 0.0065, 0.0055)]
    out = [limb('arbow', path, prof, n, 12 if hi else 5, fwd=up, slot='wood', e=2.3)]
    gp = [(k / 4, T((0, BOW_G + lerp(-0.065, 0.065, k / 4), z_of(BOW_G + lerp(-0.065, 0.065, k / 4))))) for k in range(5)]
    out.append(limb('arbow.grip', gp, [(0, 0.0175, 0.019, 0.0140)], 4 if hi else 1, 12 if hi else 5, fwd=up, slot='cartbox', e=2.3, cap0=False, cap1=False))
    ends = []
    for sg in (1, -1):   # horn nocks
        y0 = BOW_G + sg * (BOW_L - 0.012); y1 = BOW_G + sg * (BOW_L + 0.040)
        a, b = T((0, y0, z_of(y0))), T((0, y1, z_of(BOW_G + sg * BOW_L) + 0.004))
        out.append(limb('arbow.nock', [(0, a), (1, b)], [(0, 0.0085, 0.0085, 0.0085), (0.6, 0.0065, 0.0065, 0.0065), (1, 0.0025, 0.0025, 0.0025)],
                        4 if hi else 1, 8 if hi else 4, fwd=up, slot='epaulette'))
        yn = BOW_G + sg * (BOW_L + 0.012); ends.append(T((0, yn, z_of(BOW_G + sg * BOW_L) + 0.010)))
    out.append(limb('arbow.str', [(0, ends[1]), (1, ends[0])], [(0, 0.0019, 0.0019, 0.0019)], 1, 5 if hi else 3, fwd=up, slot='piping'))
    return out

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi or not _FIT:
        fit(C.surface_tools([head]), body_tree)
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'coat'); parts.append(cb)
    parts += skirt(hi) + bands(body_tree, hi) + belt(body_tree, hi) + arrow_bag(body_tree, hi) + strap(body_tree, hi)
    parts += hood(hi) + cape(hi) + bow(hi)
    return parts
C.build_kit = build_kit
