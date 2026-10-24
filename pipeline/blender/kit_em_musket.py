"""Eras v3 kit 7b: Landsknecht arquebusier (Hakenschuetze), c.1500-1520 (docs/char/ERAS_PROGRESS.md).
Patches char_v2 (loaded by char_v2_build.py when V3_KIT=kit_em_musket). Only the base human (MakeHuman head / eyes /
hands, ear fix), body cage, rig and material library are shared; every garment / item is built fresh here (none of
the em_pike garments are reused):
  * doublet in the team colour: sleeves in three stacked slashed puffs down to the elbow, spiral-slashed forearms,
    chevron slashes across the chest; deep square neck over a gathered white linen shirt with a frilled band
  * paned upper hose to above the knee: team panes with the pale lining bulging out between them; saffron lower hose,
    black knee bands
  * low round-toed latchet shoes
  * broad-brimmed felt hat (low round crown, cord band, one long trailing feather)
  * narrow belt with a cow-horn powder flask, a leather ball bag, a coil of slow match and a Bauernwehr knife
  * matchlock arquebus: straight club butt, octagonal barrel, serpentine + pan, ramrod (musket clips)"""
import math, bpy
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, gauss, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_em_musket'
C.CLIP_STYLE = 'musket'
C.TIP_LOCAL = (0.0, 1.04, 0.015)        # muzzle (weapon_tip on the prop)
C.SLOT_MAT.update({'sash': 'wool', 'waist': 'canvas', 'piping': 'wool', 'felt': 'wool', 'plume': 'fur', 'cartbox': 'worn_leather',
                   'scabbard': 'worn_leather', 'shoe': 'worn_leather', 'breeches': 'wool', 'roll': 'canvas', 'stock': 'wood',
                   'epaulette': 'hide'})
C.BODY_TRIS = 4700
HM.FIST['.L'] = 0.007
C.HEAD_BOX = (0.21, -0.21, 0.22, 1.92)
C.KIT_PAL = {'sash': '#e2d6b0', 'waist': '#ece7da', 'piping': '#24211f', 'felt': '#4a4038', 'plume': '#3a3430',
             'breeches': '#c79a3a', 'shoe': '#3d2d22', 'cartbox': '#55402a', 'scabbard': '#2e2219', 'roll': '#9c8a64',
             'steel': '#8f959b', 'metal': '#b8913a', 'wood': '#6e4b2c', 'stock': '#6e4b2c', 'epaulette': '#d8c69c'}
C.KIT_RULES = [(('lmhat',), 'head'), (('lmbelt', 'lmknee', 'lmfrill'), 'transfer'),
               (('lmhorn', 'lmbag', 'lmmatch', 'lmknife'), 'hips'),
               (('lmstock', 'lmbarrel', 'lmserp', 'lmpan', 'lmrod', 'lmbutt'), 'prop')]

C.ARM_PROF = [(0.0, 0.050, 0.050, 0.050), (0.07, 0.057, 0.060, 0.060), (0.12, 0.054, 0.055, 0.055), (0.135, 0.050, 0.051, 0.051),
              (0.20, 0.057, 0.062, 0.060), (0.265, 0.050, 0.052, 0.050), (0.33, 0.054, 0.058, 0.055, 0.003), (0.41, 0.047, 0.050, 0.047),
              (0.50, 0.041, 0.040, 0.046, -0.003), (0.60, 0.045, 0.046, 0.044), (0.74, 0.042, 0.041, 0.041), (0.855, 0.036, 0.034, 0.034),
              (0.87, 0.042, 0.040, 0.040), (0.98, 0.040, 0.036, 0.036), (1.0, 0.030, 0.026, 0.026)]
C.LEG_PROF = [(0.0, 0.090, 0.094, 0.096), (0.12, 0.093, 0.099, 0.103), (0.28, 0.086, 0.090, 0.084, 0.005), (0.40, 0.068, 0.070, 0.066),
              (0.46, 0.056, 0.058, 0.055), (0.52, 0.053, 0.055, 0.052), (0.60, 0.056, 0.054, 0.062, -0.003), (0.68, 0.058, 0.052, 0.067, -0.006),
              (0.85, 0.044, 0.042, 0.047), (0.95, 0.038, 0.040, 0.040), (1.0, 0.042, 0.046, 0.044)]
C.SHOE_PROF = [(0.0, 0.034, 0.030, 0.030), (0.15, 0.040, 0.050, 0.040), (0.45, 0.044, 0.038, 0.035), (0.8, 0.045, 0.025, 0.025),
               (1.0, 0.030, 0.016, 0.016)]

KNEE_Z = 0.565
PUFFS = ((0.035, 0.125), (0.14, 0.26), (0.275, 0.43))   # stacked sleeve puffs (arm path param)
N_PANE, W_LIN = 9, 0.40

def _arm_t(p, s):
    pts = C.arm_path(s, True)
    best = None
    for (t0, a), (t1, b) in zip(pts, pts[1:]):
        ab = b - a; u = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared)); q = a + ab * u
        dd = (p - q).length
        if best is None or dd < best[0]: best = (dd, lerp(t0, t1, u), q, ab.normalized())
    dd, t, q, d = best
    v = (V(0, 1, 0) - d * d.y).normalized(); u = v.cross(d).normalized()
    r = p - q
    return t, math.atan2(r.dot(v), s * r.dot(u))

def _frac(a, n): return (a / (2 * math.pi) * n) % 1.0

def zone(p, part):
    """(slot, relief kind, phase): kind 'puff' = team cloth puffed between slashes, 'lin' = lining bulging out."""
    x, y, z = p; ax = abs(x); s = 1.0 if x >= 0 else -1.0
    if part == 'arm':
        t, a = _arm_t(V(p), s)
        for k, (t0, t1) in enumerate(PUFFS):
            if t0 < t < t1:
                f = _frac(a + 0.3 * k, 7)
                return ('sash', None, 0) if f < 0.24 else ('coat', 'puff', (f - 0.24) / 0.76)
        if 0.53 < t < 0.84 and ((a / (2 * math.pi)) * 5 + (t - 0.53) * 9.0) % 1.0 < 0.17:
            return ('sash', None, 0)
        return ('coat', None, 0)
    if part in ('leg', 'torso') and KNEE_Z < z < 0.985 and not (part == 'torso' and z > 0.96 and y > 0.02):
        a = math.atan2(y, s * (x - s * 0.092))
        f = _frac(a + 0.2, N_PANE)
        return ('sash', 'lin', f / W_LIN) if f < W_LIN else ('coat', None, 0)
    if part == 'leg': return ('breeches', None, 0)
    if z > 1.586: return ('skin', None, 0)
    neck = 1.448 + 0.035 * ss(0.06, 0.12, ax) if y > 0 else 1.52
    if z > neck: return ('waist', None, 0)
    if y > 0.03 and 1.16 < z < 1.42 and 0.025 < ax < 0.13:      # chevron slashes across the chest
        u = (ax * 0.8 + (z - 1.16) * 0.6) / 0.034
        if u % 1.0 < 0.2 and ((z - 1.16) / 0.065) % 1.0 > 0.15: return ('sash', None, 0)
    return ('coat', None, 0)

def body_slot(p, part):
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'waist'
    return zone(p, part)[0]
C.body_slot = body_slot

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
    lin = np.zeros(n, bool); lin[lt[fs == C.S['sash']]] = True
    coat = np.zeros(n, bool); coat[lt[fs == C.S['coat']]] = True
    d = np.zeros(n)
    for i in range(n):
        if not (lin[i] or coat[i]): continue
        x, y, z = P[i]; ax = abs(x)
        part = 'arm' if (ax > 0.172 + spread * 0.6 and 0.86 < z < 1.44) else ('leg' if z < 0.985 else 'torso')
        sl, kind, ph = zone((x, y, z), part)
        if kind == 'puff' and coat[i] and not lin[i]: d[i] = 0.0065 * math.sin(math.pi * ph) ** 0.55
        elif kind == 'lin': d[i] = 0.0095 * math.sin(math.pi * min(1.0, ph)) ** 0.6   # lining puffs out between the panes
        elif lin[i] and not coat[i]: d[i] = -0.003
    P = P + N * d[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
C.add_folds = add_folds

# ------------------------------------------------------------------ shirt frill, knee bands, belt + gear
def frill(tree, hi=False):
    """gathered shirt band round the neck: a small ruffled stand above the doublet's square neck."""
    n = 120 if hi else 22
    secs = []
    for zz, off in ((1.535, 0.0), (1.560, 0.004), (1.572, 0.010)):
        ring_ = []
        for j in range(n):
            a = 2 * math.pi * j / n; d = V(math.cos(a), math.sin(a), 0)
            c = V(0, 0.020, zz)
            h = tree.ray_cast(c + d * 0.3, -d)
            r = ((V(h[0].x, h[0].y, 0) - V(0, 0.02, 0)).length if h[0] is not None else 0.06) + 0.004 + off
            if hi and zz > 1.55: r += 0.004 * abs(math.sin(a * 22))
            ring_.append(V(math.cos(a) * r, 0.020 + math.sin(a) * r, zz))
        secs.append(ring_)
    secs = secs + [[V(p.x * 0.93, 0.02 + (p.y - 0.02) * 0.93, p.z) for p in secs[-1]]]
    return [V3P.orient_out(grid_sweep('lmfrill', secs, closed_u=True, cap0=False, cap1=False, slot='waist'))]

def knee_bands(tree, hi=False):
    out = V3P.leg_hems(tree, lambda x, y: KNEE_Z + 0.006, hi, z0=KNEE_Z - 0.01, slot='piping', depth=0.020, off=0.004)
    for o in out: o.name = 'lmknee' + o.name[3:]
    return out

BELT_Z = 0.975

def belt(tree, hi=False):
    out = [V3P.hem_band(tree, (0.0, 0.0, BELT_Z - 0.01), lambda x, y: BELT_Z - 0.008 * ss(-0.02, -0.12, y), hi, depth=0.017,
                        off=0.0085, name='lmbelt', slot='cartbox', n=110 if hi else 20)]
    fr = V3P.surf(tree, (0.0, 0.5, BELT_Z - 0.008), (0, -1, 0), 0.010)
    c = fr[0] if fr else V(0.0, 0.13, BELT_Z - 0.008)
    out.append(superellipsoid('lmbelt.buck', c + V(0, 0.002, 0), (0.017, 0.005, 0.014), e=(2.2, 2.2), n=(10, 6) if hi else (6, 3), slot='metal'))
    return out

def powder_horn(hi=False):
    """cow horn flask on a cord at the right hip: curved cone, wooden base plug, brass nozzle."""
    base = V(0.175, 0.055, 0.880); tipp = V(0.150, 0.150, 0.800)
    mid = (base + tipp) / 2 + V(0.025, -0.01, -0.03)
    path = [(0, base), (0.5, mid), (1, tipp)]
    out = [limb('lmhorn', path, [(0, 0.032, 0.030, 0.030), (0.5, 0.022, 0.021, 0.021), (1, 0.008, 0.008, 0.008)], 10 if hi else 3,
                12 if hi else 6, fwd=V(1, 0, 0), slot='epaulette')]
    dd = (base - mid).normalized()
    out.append(limb('lmhorn.plug', [(0, base - dd * 0.004), (1, base + dd * 0.014)], [(0, 0.033, 0.031, 0.031)], 1, 12 if hi else 6,
                    fwd=V(1, 0, 0), slot='wood'))
    dt = (tipp - mid).normalized()
    out.append(limb('lmhorn.noz', [(0, tipp - dt * 0.006), (1, tipp + dt * 0.03)], [(0, 0.0085, 0.0085, 0.0085), (1, 0.005, 0.005, 0.005)],
                    2 if hi else 1, 8 if hi else 4, fwd=V(1, 0, 0), slot='metal'))
    # cord up to the belt
    for p in (base + V(0, 0, 0.03), tipp + V(0, 0, 0.02)):
        out.append(limb('lmhorn.cord', [(0, p), (1, V(0.150, 0.075 if p.y < 0.1 else 0.11, BELT_Z - 0.01))], [(0, 0.0028, 0.0028, 0.0028)],
                        2 if hi else 1, 4, fwd=V(1, 0, 0), slot='roll'))
    return out

def ball_bag(hi=False):
    c = V(-0.118, 0.118, 0.905)
    rot = Matrix.Rotation(math.radians(38), 3, 'Z')
    out = [superellipsoid('lmbag', c, (0.040, 0.020, 0.048), e=(2.2, 2.0), n=(14, 8) if hi else (8, 4), rot=rot, slot='cartbox')]
    out.append(limb('lmbag.tie', [(0, c + V(0, 0, 0.040)), (1, c + V(0.004, 0.004, 0.062))], [(0, 0.018, 0.012, 0.012), (1, 0.011, 0.008, 0.008)],
                    2 if hi else 1, 8 if hi else 4, slot='cartbox'))
    out.append(limb('lmbag.st', [(0, c + V(0.004, 0.004, 0.058)), (1, V(-0.104, 0.112, BELT_Z - 0.005))], [(0, 0.007, 0.0022, 0.0022)],
                    1, 4, fwd=rot @ V(0, 1, 0), slot='cartbox'))
    return out

def match_coil(hi=False):
    """coil of slow match hanging from the belt at the left hip (looped hemp cord, lit end loose)."""
    c = V(-0.205, -0.020, 0.835)
    n = 90 if hi else 18
    pts = []
    for k in range(n + 1):
        u = k / n; a = u * 2 * math.pi * 3.0
        r = 0.058 + 0.004 * math.sin(a * 0.5)
        pts.append((u, c + V(0.010 * math.sin(a * 1.5) - 0.012 * (u - 0.5), math.cos(a) * r, math.sin(a) * r * 1.25)))
    out = [limb('lmmatch', pts, [(0, 0.0046, 0.0046, 0.0046)], n, 6 if hi else 3, fwd=V(1, 0, 0), slot='roll')]
    out.append(limb('lmmatch.tie', [(0, c + V(0, 0, 0.062)), (1, V(-0.180, -0.020, BELT_Z - 0.01))], [(0, 0.0045, 0.0045, 0.0045)], 2, 4,
                    fwd=V(1, 0, 0), slot='roll'))
    return out

def knife(hi=False):
    """Bauernwehr (long knife) worn at the right back hip, grip forward."""
    a = V(0.118, -0.135, 0.935); b = V(0.170, -0.130, 0.700)
    d = (b - a).normalized()
    out = [limb('lmknife', [(0, a), (1, b)], [(0, 0.020, 0.008, 0.008), (0.85, 0.016, 0.007, 0.007), (1, 0.006, 0.004, 0.004)],
                6 if hi else 2, 10 if hi else 4, fwd=V(0, 1, 0), slot='scabbard', e=3.0)]
    g0 = a - d * 0.004; g1 = g0 - d * 0.10
    out.append(limb('lmknife.grip', [(0, g0), (1, g1)], [(0, 0.011, 0.012, 0.012), (1, 0.013, 0.013, 0.013)], 3 if hi else 1, 8 if hi else 4,
                    fwd=V(0, 1, 0), slot='wood'))
    out.append(superellipsoid('lmknife.guard', g0 + d * 0.002, (0.026, 0.010, 0.006), e=(2, 2), n=(10, 6) if hi else (6, 3),
                              rot=V(d).to_track_quat('Z', 'Y').to_matrix(), slot='steel'))
    return out

# ------------------------------------------------------------------ broad-brimmed felt hat
HAT_B = V(0.0, 0.004, 1.736)
HAT_R = Matrix.Rotation(math.radians(6), 3, 'X')   # brim tipped slightly up at the front
_FIT = {}

def _fit_band(htree, nu):
    rs = []
    for j in range(nu):
        a = 2 * math.pi * j / nu; d = HAT_R @ V(math.cos(a), math.sin(a), 0)
        best = None
        for dz in (0.0, -0.010, 0.012):
            o = HAT_B + HAT_R @ V(0, 0, dz)
            h = htree.ray_cast(o + d * 0.3, -d)
            if h[0] is not None:
                r = (h[0] - o).dot(d); best = r if best is None else max(best, r)
        rs.append((best if best is not None else 0.08) + 0.005)
    return rs

def hat(hi=False):
    nu = 96 if hi else 20
    rb = _FIT['band_hi' if hi else 'band_lo']
    L = lambda r, a, h: HAT_B + HAT_R @ V(math.cos(a) * r, math.sin(a) * r, h)
    out = []
    # crown: low, round-topped; band ring slightly flared
    crown = []
    for k, (dr, h) in enumerate(((0.0, -0.004), (0.004, 0.030), (0.004, 0.060), (-0.010, 0.082), (-0.040, 0.094))):
        crown.append([L(rb[j] + dr, 2 * math.pi * j / nu, h) for j in range(nu)])
    out.append(V3P.orient_out(grid_sweep('lmhat', crown, closed_u=True, cap0=False, cap1=True, slot='felt')))
    # brim: flat, drooping a little at the sides, rolled edge
    W = 0.088
    def brim_r(j, f): return lerp(rb[j] - 0.004, rb[j] + W * (1 + 0.06 * math.cos(2 * 2 * math.pi * j / nu)), f)
    def brim_h(j, f): return -0.002 - 0.020 * f ** 1.6 * (0.5 + 0.5 * math.cos(2 * (2 * math.pi * j / nu)))   # sides droop
    nb = 5 if hi else 2
    top = [[L(brim_r(j, k / nb), 2 * math.pi * j / nu, brim_h(j, k / nb)) for j in range(nu)] for k in range(nb + 1)]
    bot = [[p - HAT_R @ V(0, 0, 0.004) for p in r_] for r_ in top]
    out.append(V3P.orient_out(grid_sweep('lmhat.brim', top + bot[::-1], closed_u=True, cap0=False, cap1=False, slot='felt')))
    e = top[-1]
    out.append(limb('lmhat.roll', [(j / nu, e[j % nu]) for j in range(nu + 1)], [(0, 0.0035, 0.0035, 0.0035)], nu, 6 if hi else 3,
                    fwd=V(0, 0, 1), slot='felt'))
    # cord band round the crown
    band = [L(rb[j] + 0.0045, 2 * math.pi * j / nu, 0.006) for j in range(nu)]
    out.append(limb('lmhat.cord', [(j / nu, band[j % nu]) for j in range(nu + 1)], [(0, 0.0042, 0.0042, 0.0042)], nu, 6 if hi else 3,
                    fwd=V(0, 0, 1), slot='piping'))
    # one long feather tucked into the band at the left back, trailing
    pth = []
    for m in range(9):
        u = m / 8; a = math.radians(205 + 40 * u)
        r = lerp(rb[int(nu * 205 / 360)] + 0.006, rb[int(nu * 205 / 360)] + 0.20, u)
        pth.append((u, L(r, a, 0.02 + 0.07 * math.sin(math.pi * u * 0.7) - 0.05 * ss(0.7, 1.0, u))))
    ns = 32 if hi else 6
    prof = []
    for m in range(ns + 1):
        u = m / ns
        w = 0.004 + 0.013 * math.sin(math.pi * min(1.0, u * 1.08)) ** 0.8
        if hi: w *= 1.0 + 0.18 * abs(math.sin(u * 70.0))
        prof.append((u, w, 0.0025, 0.0025))
    out.append(limb('lmhat.plume', pth, prof, ns, 6 if hi else 4, fwd=HAT_R @ V(0, 0, 1), slot='plume', e=2.6))
    return out

# ------------------------------------------------------------------ matchlock arquebus (prop frame: barrel along +y)
def arquebus(hi=False):
    import char_rig as R
    T = lambda p: R.REST['prop'] @ V(p)
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    side = R.REST['prop'].to_3x3() @ V(1, 0, 0)
    stock = [(-0.31, 0.022, -0.082, 0.014), (-0.22, 0.021, -0.072, 0.014), (-0.10, 0.018, -0.052, 0.013), (-0.02, 0.016, -0.036, 0.011),
             (0.08, 0.017, -0.031, 0.010), (0.30, 0.016, -0.027, 0.007), (0.88, 0.014, -0.022, 0.006), (0.92, 0.012, -0.018, 0.004)]
    nu = 12 if hi else 6
    secs = []
    for y, hw, zb, zt in stock:
        zc, hz = (zb + zt) / 2, (zt - zb) / 2
        secs.append(ring(T((0, y, zc)), side, up, hw, hz, hz, nu, 3.2))
    out = [grid_sweep('lmstock', secs, slot='stock')]
    out.append(limb('lmbutt', [(0, T((0, -0.318, -0.034))), (1, T((0, -0.300, -0.034)))], [(0, 0.0235, 0.050, 0.050)], 1, nu, fwd=up,
                    slot='steel', e=3.2))
    out.append(limb('lmbarrel', [(0, T((0, 0.0, 0.015))), (1, T((0, 1.04, 0.015)))], [(0, 0.0125, 0.0125, 0.0125), (1, 0.0105, 0.0105, 0.0105)],
                    3 if hi else 2, 8, fwd=up, slot='steel', e=2.0))   # 8 sides: octagonal barrel
    out.append(limb('lmbarrel.muz', [(0, T((0, 1.00, 0.015))), (1, T((0, 1.04, 0.015)))], [(0, 0.0135, 0.0135, 0.0135)], 1, 8, fwd=up,
                    slot='steel', cap0=False))
    out.append(limb('lmrod', [(0, T((0, 0.12, -0.025))), (1, T((0, 1.02, -0.022)))], [(0, 0.0045, 0.0045, 0.0045)], 2, 6 if hi else 3, fwd=up,
                    slot='wood'))
    # pan + flash shield on the right side, serpentine (S lever) holding the match
    out.append(superellipsoid('lmpan', T((0.021, 0.075, 0.012)), (0.008, 0.016, 0.005), e=(3, 3), n=(8, 4), rot=R.REST['prop'].to_3x3(), slot='steel'))
    out.append(superellipsoid('lmpan.plate', T((0.0185, 0.04, -0.002)), (0.004, 0.06, 0.013), e=(4, 4), n=(8, 4), rot=R.REST['prop'].to_3x3(),
                              slot='steel'))
    sp = [(0, T((0.024, 0.005, -0.050))), (0.3, T((0.026, -0.010, -0.015))), (0.65, T((0.026, 0.020, 0.020))), (1, T((0.024, 0.060, 0.032)))]
    out.append(limb('lmserp', sp, [(0, 0.0035, 0.0045, 0.0045), (1, 0.0040, 0.0050, 0.0050)], 8 if hi else 3, 6 if hi else 3, fwd=side,
                    slot='steel'))
    out.append(limb('lmserp.match', [(0, T((0.024, 0.055, 0.034))), (0.5, T((0.03, 0.02, 0.06))), (1, T((0.03, -0.04, 0.05)))],
                    [(0, 0.0035, 0.0035, 0.0035)], 4 if hi else 2, 5 if hi else 3, fwd=side, slot='roll'))
    return out

def fit(htree):
    _FIT['band_hi'] = _fit_band(htree, 96)
    hb = _FIT['band_hi']
    _FIT['band_lo'] = [max(hb[(j * 96 // 20 + k) % 96] for k in range(-3, 4)) + 0.002 for j in range(20)]
    print('[em_musket] band r', round(min(hb), 3), round(max(hb), 3))

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi or not _FIT:
        fit(C.surface_tools([head]))
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'waist'); parts.append(cb)
    parts += frill(body_tree, hi) + knee_bands(body_tree, hi) + belt(body_tree, hi)
    parts += powder_horn(hi) + ball_bag(hi) + match_coil(hi) + knife(hi)
    parts += hat(hi) + arquebus(hi)
    return parts
C.build_kit = build_kit
