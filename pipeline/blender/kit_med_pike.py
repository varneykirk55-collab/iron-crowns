"""Eras v3 kit 4: Flemish communal militia pikeman, c.1300 (Courtrai 1302 era) (docs/char/ERAS_PROGRESS.md).
Patches char_v2 (loaded by char_v2_build.py when V3_KIT=kit_med_pike). Only the base human (MakeHuman head / eyes /
hands, ear fix), body cage, rig and material library are shared; every garment / item is built fresh here:
  * quilted gambeson (aketon) in the town / team colour: vertical quilting channels on the body, horizontal on the
    sleeves, low round collar; skirt to mid-thigh split front and back (quilted, rolled hem)
  * long narrow leather belt with a brass buckle and hanging strap end; leather purse; ballock dagger at the back
  * russet wool hose (chausses); low leather turnshoes
  * white linen coif (bonnet tied under the chin) under an iron kettle hat (chapel de fer: domed crown with a
    raised comb, wide sloping brim, riveted crown band)
  * ash pike (~3.5 m) with a socketed leaf head and iron langets (held with the musket clips: shouldered / levelled)"""
import math, bpy
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, gauss, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_med_pike'
C.CLIP_STYLE = 'musket'                 # shouldered at idle / walk, levelled for the charge (melee)
C.TIP_LOCAL = (0.0, 3.12, 0.0)          # pike point (weapon_tip on the prop)
C.SLOT_MAT.update({'waist': 'canvas', 'cartbox': 'leather', 'scabbard': 'leather', 'shoe': 'leather', 'breeches': 'wool',
                   'felt': 'iron'})
C.BODY_TRIS = 4800
HM.FIST['.L'] = 0.007                   # empty left hand: relaxed fist
C.HEAD_BOX = (0.20, -0.20, 0.21, 1.90)  # kettle hat brim gets head-level texel density
C.KIT_PAL = {'breeches': '#7a5236', 'shoe': '#2c2119', 'cartbox': '#3a2a1c', 'waist': '#e6dfcc', 'felt': '#55595e',
             'steel': '#a5abb1', 'metal': '#b8913a', 'scabbard': '#2a1f17', 'wood': '#9a7a52'}
C.KIT_RULES = [(('pkcoif', 'pkhat', 'pktie'), 'head'), (('pkbelt', 'pkgart'), 'transfer'), (('pkskirt',), 'tail'),
               (('pkbuck', 'pkstrap', 'pkpurse', 'pkdag'), 'hips'), (('pkshaft', 'pkhead', 'pklang'), 'prop')]

GART_Z = 0.455   # garter (below the knee)
# hose are skin-tight: smooth calf, no gaiter-top step in the leg cage (char_v2.LEG_PROF is read at build time)
C.LEG_PROF = [(0.0, 0.086, 0.086, 0.086), (0.10, 0.088, 0.088, 0.092), (0.30, 0.074, 0.078, 0.070, 0.005), (0.45, 0.056, 0.058, 0.055),
              (0.52, 0.053, 0.055, 0.052), (0.60, 0.056, 0.054, 0.062, -0.003), (0.68, 0.058, 0.052, 0.067, -0.006),
              (0.85, 0.044, 0.042, 0.047), (0.95, 0.038, 0.040, 0.040), (1.0, 0.042, 0.046, 0.044)]

def body_slot(p, part):
    x, y, z = p
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'coat'
    if part == 'arm': return 'coat'
    if part == 'leg': return 'breeches'
    if z > 1.586: return 'skin'
    return 'coat'
C.body_slot = body_slot

# ------------------------------------------------------------------ quilting (bake source): wraps the cloth folds
_add_folds = C.add_folds
def add_folds(o, spread):
    _add_folds(o, spread)
    me = o.data; me.update()
    n = len(me.vertices)
    P = np.zeros(n * 3); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    N = np.zeros(n * 3); me.vertices.foreach_get('normal', N); N = N.reshape(-1, 3)
    slot = np.zeros(len(me.polygons), np.int32); me.attributes['slot'].data.foreach_get('value', slot)
    lt = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lt)
    tot = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', tot)
    fs = np.repeat(slot, tot)
    coat = np.zeros(n, bool); coat[lt[fs == C.S['coat']]] = True
    x, y, z = P[:, 0], P[:, 1], P[:, 2]; ax = np.abs(x)
    def puff(u): return np.abs(np.sin(np.pi * u)) ** 0.45 - 0.62   # padded channels, sharp stitched creases
    arm = (ax > 0.172 + spread * 0.6) & (z > 0.86) & (z < 1.44)
    tor = ~arm & (z > 0.78) & (z < 1.50)
    phi = np.arctan2(y * 1.35, x)
    d = np.zeros(n)
    d += tor * 0.0046 * puff(phi / math.radians(13.0)) * ss_np(1.50, 1.44, z)
    d += arm * 0.0038 * puff((z - 0.90) / 0.042)
    P = P + N * (d * coat)[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
def ss_np(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
C.add_folds = add_folds

# ------------------------------------------------------------------ gambeson skirt (split front + back, quilted)
SK = [(1.035, .160, .108, .114, 0.000), (0.98, .174, .114, .130, -0.004), (0.92, .186, .123, .152, -0.008),
      (0.84, .192, .132, .158, -0.006), (0.72, .197, .142, .160, -0.002), (0.625, .201, .150, .162, 0.0)]
SK_Z0, SK_Z1 = SK[0][0], SK[-1][0]

def _sk(z):
    for a, b in zip(SK, SK[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0]); return [lerp(a[k], b[k], t) for k in range(1, 5)]
    return list((SK[0] if z > SK_Z0 else SK[-1])[1:])

def skirt(hi=False):
    out = []
    nz, na = (60, 132) if hi else (6, 8)
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            t = i / nz; z = lerp(SK_Z0, SK_Z1, t)
            rx, rf, rb, off = _sk(z)
            dl = math.radians(9.0) * ss(0.80, SK_Z1, z)          # front / back slits open towards the hem
            hem = ss(0.06, 0.0, (z - SK_Z1)) if hi else 0.0       # rolled hem (bake source)
            outer, inner = [], []
            for j in range(na + 1):
                a = lerp(math.pi / 2 - dl, -math.pi / 2 + dl, j / na)   # front -> side -> back, right half
                ca, sa = math.cos(a), math.sin(a)
                f = lambda q: math.copysign(abs(q) ** (2.0 / 2.3), q)
                r = 1.0
                if hi:
                    u = (a + math.pi / 2) / math.radians(13.0)
                    r += (0.014 * (abs(math.sin(math.pi * u)) ** 0.45 - 0.62)) * ss(SK_Z0, SK_Z0 - 0.03, z)
                    r += 0.030 * math.exp(-((z - SK_Z1 - 0.010) / 0.010) ** 2)
                px, py = f(ca) * rx * r, f(sa) * (rf if sa > 0 else rb) * r
                p = V(s * px, py + off, z)
                d = V(s * f(ca), f(sa), 0).normalized() if (abs(ca) + abs(sa)) > 0 else V(0, 1, 0)
                outer.append(p); inner.append(p - d * 0.010)
            secs.append(outer + inner[::-1])
        o = grid_sweep('pkskirt' + ('R' if s > 0 else 'L'), secs, cap0=True, cap1=True, slot='coat')
        out.append(o)
    return out

# ------------------------------------------------------------------ belt, buckle, strap end, purse, dagger
BELT_TOP = 1.048

def belt(tree, hi=False):
    b = V3P.hem_band(tree, (0.0, 0.0, BELT_TOP - 0.01), lambda x, y: BELT_TOP + 0.010 * ss(0.0, 0.10, y), hi, depth=0.026,
                     off=0.0145, name='pkbelt', slot='cartbox', n=120 if hi else 22)
    out = [b]
    fr = V3P.surf(tree, (0.012, 0.5, BELT_TOP - 0.005), (0, -1, 0), 0.016)
    c = fr[0] if fr else V(0.012, 0.115, BELT_TOP - 0.005)
    out.append(superellipsoid('pkbuck', c + V(0, 0.003, 0), (0.024, 0.006, 0.020), e=(2.6, 2.6), n=(12, 6) if hi else (8, 3), slot='metal'))
    # long strap end, hanging down from the buckle (c.1300 fashion), metal chape at the tip
    p0 = c + V(0.020, 0.004, -0.006)
    path = [(0, p0), (0.4, p0 + V(0.010, 0.010, -0.090)), (1, p0 + V(0.016, 0.010, -0.230))]
    out.append(limb('pkstrap', path, [(0, 0.012, 0.0025, 0.0025)], 8 if hi else 2, 4, fwd=V(0, 1, 0), slot='cartbox', e=4.0))
    tp = path[-1][1]
    out.append(limb('pkstrap.ch', [(0, tp + V(0, 0, 0.022)), (1, tp + V(0, 0, -0.004))], [(0, 0.0135, 0.0035, 0.0035)], 1, 4,
                    fwd=V(0, 1, 0), slot='metal', e=4.0))
    # purse on the left hip
    pc = V(-0.135, 0.085, 0.965)
    rot = Matrix.Rotation(math.radians(-30), 3, 'Z')
    out.append(superellipsoid('pkpurse', pc, (0.052, 0.020, 0.058), e=(3.2, 2.4), n=(14, 8) if hi else (8, 4), rot=rot, slot='cartbox'))
    out.append(limb('pkpurse.st', [(0, pc + V(0.012, 0.0, 0.05)), (1, V(-0.120, 0.105, BELT_TOP - 0.004))], [(0, 0.008, 0.0025, 0.0025)],
                    2 if hi else 1, 4, fwd=rot @ V(0, 1, 0), slot='cartbox'))
    return out

def dagger(hi=False):
    """ballock dagger worn at the back of the belt, grip up to the right."""
    a = V(0.055, -0.150, 1.040); b = V(0.135, -0.122, 0.740)
    d = (b - a).normalized()
    out = [limb('pkdag', [(0, a), (1, b)], [(0, 0.016, 0.009, 0.009), (0.85, 0.012, 0.007, 0.007), (1, 0.004, 0.003, 0.003)],
                8 if hi else 2, 10 if hi else 5, fwd=V(0, 1, 0), slot='scabbard', e=2.4)]
    g0 = a - d * 0.004; g1 = g0 - d * 0.105
    out.append(limb('pkdag.grip', [(0, g0), (1, g1)], [(0, 0.011, 0.011, 0.011), (0.9, 0.012, 0.012, 0.012), (1, 0.007, 0.007, 0.007)],
                    4 if hi else 1, 8 if hi else 5, fwd=V(0, 1, 0), slot='wood'))
    side = d.cross(V(0, 1, 0)).normalized()
    for sg in (1, -1):   # the two lobes at the guard
        out.append(superellipsoid('pkdag.lobe', g0 + side * sg * 0.017, (0.014, 0.014, 0.014), e=(2, 2), n=(10, 6) if hi else (6, 3), slot='wood'))
    return out

def garters(tree, hi=False):
    return V3P.leg_hems(tree, lambda x, y: GART_Z + 0.008 * ss(0.03, -0.05, y), hi, z0=GART_Z - 0.01, slot='cartbox',
                        depth=0.014, off=0.003)

# ------------------------------------------------------------------ linen coif + kettle hat (fitted on the hi head)
HC = V(0, 0.004, 1.664)
_FIT = {}

def _coif_dirs(nb, na):
    rows = []
    for i in range(nb + 1):
        be = math.radians(lerp(-40.0, 86.0, i / nb))
        A = math.radians(180.0 - 52.0 * ss(math.radians(36.0), math.radians(18.0), be) - 6.0 * ss(math.radians(-10), math.radians(-40), be))
        row = []
        for j in range(na + 1):
            al = lerp(-A, A, j / na)                   # 0 = back of the head (-y)
            row.append(V(math.sin(al) * math.cos(be), -math.cos(al) * math.cos(be), math.sin(be)))
        rows.append(row)
    return rows

def _fit_coif(htree, nb, na):
    dirs = _coif_dirs(nb, na)
    R = np.zeros((nb + 1, na + 1))
    for i, row in enumerate(dirs):
        for j, d in enumerate(row):
            h = htree.ray_cast(HC + d * 0.35, -d)
            R[i, j] = (h[0] - HC).length if h[0] is not None and h[0].z > 1.54 else np.nan
    for i in range(nb + 1):   # fill misses from the row
        m = np.isnan(R[i])
        if m.all(): R[i] = np.nanmean(R) if not np.isnan(R).all() else 0.1
        elif m.any(): R[i, m] = np.nanmax(R[i])
    raw = R.copy()
    k = max(1, (na + 1) // 18)
    D = R.copy()
    for di in (-1, 0, 1):
        for dj in range(-k, k + 1):
            D = np.maximum(D, np.roll(np.roll(R, di, 0), dj, 1))
    for _ in range(3):
        D = (D + np.roll(D, 1, 0) + np.roll(D, -1, 0) + np.roll(D, 1, 1) + np.roll(D, -1, 1)) / 5.0
        D[0], D[-1] = (D[0] + D[1]) / 2, (D[-1] + D[-2]) / 2
    return dirs, np.maximum(D, raw + 0.003)

def coif(hi=False):
    dirs, R = _FIT['coif_hi' if hi else 'coif_lo']
    secs = []
    for i, row in enumerate(dirs):
        outer = [HC + d * (R[i, j] + 0.0065) for j, d in enumerate(row)]
        inner = [HC + d * (R[i, j] + 0.0025) for j, d in enumerate(row)]
        secs.append(outer + inner[::-1])
    o = grid_sweep('pkcoif', secs, closed_u=True, cap0=False, cap1=True, slot='waist')
    out = [o]
    # linen ties from the lower front corners, knotted under the chin
    for s in (1, -1):
        d0 = dirs[0][-1 if s > 0 else 0]; p0 = HC + d0 * (R[0, -1 if s > 0 else 0] + 0.005)
        chin = V(s * 0.006, 0.062, 1.555)
        out.append(limb('pktie', [(0, p0), (0.5, (p0 + chin) / 2 + V(0, 0.004, -0.008)), (1, chin)], [(0, 0.008, 0.0018, 0.0018)],
                        8 if hi else 2, 4, fwd=V(s, 0, 0), slot='waist', e=4.0))
    return out

HAT_Z = 1.712
def _hat_r():
    return _FIT['hat']

def kettle_hat(hi=False):
    Rx, Ry, H, cy = _hat_r()
    out = []
    nu = 72 if hi else 16
    nv = 26 if hi else 5
    secs = []
    for i in range(nv):
        t = i / nv; be = t * math.pi / 2 * 0.97
        rr = math.cos(be); zz = HAT_Z + H * math.sin(be)
        band = 0.0025 * ss(0.0, 0.02, t) * ss(0.16, 0.13, t) if hi else 0.0      # riveted crown band
        rx, ry = Rx * rr + band, Ry * rr + band
        sec = ring(V(0, cy, zz), V(1, 0, 0), V(0, 1, 0), rx, ry, ry, nu, 2.0, 0.5)
        if hi:   # raised comb running front to back over the crown
            sec = [p + V(0, 0, 0.006 * math.exp(-(p.x / 0.010) ** 2) * ss(0.25, 0.6, t)) for p in sec]
        secs.append(sec)
    out.append(grid_sweep('pkhat', secs, cap0=False, cap1=True, slot='felt'))
    # brim: wide, sloping down, rolled edge; 4-sided section (same in hi + lo)
    nb = 4 if hi else 1
    rings_ = []
    W = 0.068
    for k in range(nb + 1):
        t = k / nb
        rr = [V(p.x * (1 + W * t / Rx), cy + (p.y - cy) * (1 + W * t / Ry), HAT_Z - 0.036 * t ** 1.3) for p in
              ring(V(0, cy, HAT_Z), V(1, 0, 0), V(0, 1, 0), Rx, Ry, Ry, nu, 2.0, 0.5)]
        rings_.append(rr)
    top = rings_; bot = [[p + V(0, 0, -0.0035) for p in r] for r in rings_]
    secs = top + bot[::-1]
    out.append(grid_sweep('pkhat.brim', secs, closed_u=True, cap0=False, cap1=False, slot='felt'))
    e = rings_[-1]
    path = [(j / nu, e[j % nu]) for j in range(nu + 1)]
    out.append(limb('pkhat.roll', path, [(0, 0.0045, 0.0045, 0.0045)], nu, 6 if hi else 3, fwd=V(0, 0, 1), slot='felt'))
    if hi:
        for j in range(16):   # rivets on the band
            a = 2 * math.pi * (j + 0.5) / 16
            p = V(math.cos(a) * (Rx + 0.002), cy + math.sin(a) * (Ry + 0.002), HAT_Z + 0.010)
            n_ = V(math.cos(a) / Rx, math.sin(a) / Ry, 0).normalized()
            out.append(superellipsoid('pkhat.riv', p, (0.0035, 0.0035, 0.002), e=(2, 2), n=(8, 4), rot=n_.to_track_quat('Z', 'Y').to_matrix(),
                                      slot='felt'))
    return out

def fit_head(htree):
    _FIT['coif_hi'] = _fit_coif(htree, 40, 72)
    _FIT['coif_lo'] = _fit_coif(htree, 7, 14)
    dirs, R = _FIT['coif_hi']
    pts = [HC + d * (R[i, j] + 0.0065) for i, row in enumerate(dirs) for j, d in enumerate(row)]
    Rx, Ry, H, cy = 0.104, 0.118, 0.138, 0.010
    k = max([math.sqrt((p.x / Rx) ** 2 + ((p.y - cy) / Ry) ** 2 + ((p.z - HAT_Z) / H) ** 2) for p in pts if p.z > HAT_Z] + [0.0])
    sc = max(1.0, k * 1.025)
    _FIT['hat'] = (Rx * sc, Ry * sc, H * sc, cy)
    print('[pike] coif rows', len(dirs), 'hat scale', round(sc, 3), 'radii', [round(v, 3) for v in _FIT['hat']])

# ------------------------------------------------------------------ pike
def pike(hi=False):
    import char_rig as R
    T = lambda p: R.REST['prop'] @ V(p)
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    out = [limb('pkshaft', [(0, T((0, -0.42, 0))), (0.5, T((0, 1.2, 0))), (1, T((0, 2.86, 0)))],
                [(0, 0.0165, 0.0165, 0.0165), (0.25, 0.0175, 0.0175, 0.0175), (1, 0.0150, 0.0150, 0.0150)],
                10 if hi else 3, 10 if hi else 6, fwd=up, slot='wood')]
    out.append(limb('pkhead.sock', [(0, T((0, 2.84, 0))), (0.8, T((0, 2.93, 0))), (1, T((0, 2.95, 0)))],
                    [(0, 0.0175, 0.0175, 0.0175), (0.8, 0.0135, 0.0135, 0.0135), (1, 0.010, 0.010, 0.010)], 4 if hi else 1, 10 if hi else 6,
                    fwd=up, slot='steel'))
    out.append(limb('pkhead', [(0, T((0, 2.93, 0))), (0.35, T((0, 3.00, 0))), (1, T((0, 3.12, 0)))],
                    [(0, 0.008, 0.005, 0.005), (0.35, 0.024, 0.0045, 0.0045), (0.75, 0.014, 0.0035, 0.0035), (1, 0.0006, 0.0006, 0.0006)],
                    12 if hi else 3, 10 if hi else 4, fwd=up, slot='steel', cap1=False))
    for sg in (1, -1):   # langets nailed down the shaft
        side = R.REST['prop'].to_3x3() @ V(sg, 0, 0)
        out.append(limb('pklang', [(0, T((0, 2.62, 0)) + side * 0.0158), (1, T((0, 2.85, 0)) + side * 0.0158)],
                        [(0, 0.0012, 0.0045, 0.0045), (1, 0.0016, 0.0055, 0.0055)], 3 if hi else 1, 4, fwd=up, slot='steel', e=4.0))
    return out

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi or not _FIT:
        fit_head(C.surface_tools([head]))
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'coat'); parts.append(cb)
    parts += skirt(hi) + belt(body_tree, hi) + dagger(hi)
    parts += coif(hi) + kettle_hat(hi) + pike(hi)
    return parts
C.build_kit = build_kit
