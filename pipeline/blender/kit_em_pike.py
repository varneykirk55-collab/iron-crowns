"""Eras v3 kit 7a: Landsknecht pikeman, c.1500-1520 (pike and shot era start) (docs/char/ERAS_PROGRESS.md).
Patches char_v2 (loaded by char_v2_build.py when V3_KIT=kit_em_pike). Only the base human (MakeHuman head / eyes /
hands, ear fix), body cage, rig and material library are shared; every garment / item is built fresh here:
  * doublet in the team colour: big puffed upper sleeves slashed lengthwise over a pale linen lining, tight forearm,
    rows of short slashes across the back; low neck over a white linen shirt with a small stand collar
  * puffed, slashed upper hose (Pluderhose to the knee, team panels over the lining); mi-parti lower hose (right leg
    off-white, left leg red) with cloth garters tied below the knee
  * blunt, broad-toed 'cow-mouth' (Kuhmaul) shoes
  * globose steel breastplate (front only) with rolled edges and leather shoulder straps
  * wide slashed black felt beret (Barett), tilted, with two curling ostrich plumes (one white, one team)
  * Katzbalger short sword (S-guard, fan pommel) at the left hip on a narrow sword belt
  * ash pike (~4.5 m) with a narrow socketed head and long iron langets (held with the musket clips)"""
import math, bpy
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, gauss, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_em_pike'
C.CLIP_STYLE = 'musket'                 # shouldered at idle / walk, levelled for the charge (melee)
PIKE_Y0, PIKE_Y1 = -0.45, 4.05
C.TIP_LOCAL = (0.0, PIKE_Y1, 0.0)       # pike point (weapon_tip on the prop)
C.SLOT_MAT.update({'sash': 'wool', 'waist': 'canvas', 'stock': 'wool', 'felt': 'wool', 'plume': 'canvas', 'cartbox': 'worn_leather',
                   'scabbard': 'worn_leather', 'shoe': 'worn_leather', 'breeches': 'wool', 'gaiter': 'wool'})
C.BODY_TRIS = 4700
HM.FIST['.L'] = 0.007                   # empty left hand: relaxed fist
C.HEAD_BOX = (0.21, -0.21, 0.22, 1.95)  # wide beret + plumes get head-level texel density
C.KIT_PAL = {'sash': '#d8c99a', 'waist': '#ebe6d8', 'stock': '#2f2a26', 'felt': '#262220', 'plume': '#f0ebe0',
             'breeches': '#ddd5c2', 'gaiter': '#8a2a22', 'shoe': '#3b2c22', 'cartbox': '#4f3722', 'scabbard': '#2e2219',
             'steel': '#a9afb5', 'metal': '#b8913a', 'wood': '#a3825a'}
C.KIT_RULES = [(('lpberet', 'lpplume'), 'head'), (('lpbreast', 'lpstrap'), 'transfer_torso'), (('lpbelt', 'lpgart'), 'transfer'),
               (('lpsword',), 'hips'), (('lpshaft', 'lphead', 'lplang'), 'prop')]

# body cage: puffed upper sleeves, pinched at the elbow; puffed upper hose to the knee, then tight hose
C.ARM_PROF = [(0.0, 0.050, 0.050, 0.050), (0.09, 0.060, 0.064, 0.064), (0.22, 0.060, 0.069, 0.067), (0.35, 0.055, 0.062, 0.058, 0.004),
              (0.45, 0.045, 0.047, 0.048), (0.50, 0.041, 0.040, 0.046, -0.003), (0.60, 0.045, 0.046, 0.044), (0.74, 0.042, 0.041, 0.041),
              (0.855, 0.036, 0.034, 0.034), (0.87, 0.042, 0.040, 0.040), (0.98, 0.040, 0.036, 0.036), (1.0, 0.030, 0.026, 0.026)]
C.LEG_PROF = [(0.0, 0.090, 0.092, 0.094), (0.12, 0.094, 0.100, 0.104), (0.30, 0.088, 0.092, 0.084, 0.005), (0.43, 0.070, 0.072, 0.068),
              (0.50, 0.055, 0.057, 0.054), (0.60, 0.056, 0.054, 0.062, -0.003), (0.68, 0.058, 0.052, 0.067, -0.006),
              (0.85, 0.044, 0.042, 0.047), (0.95, 0.038, 0.040, 0.040), (1.0, 0.042, 0.046, 0.044)]
C.SHOE_PROF = [(0.0, 0.034, 0.030, 0.030), (0.15, 0.041, 0.048, 0.040), (0.45, 0.046, 0.036, 0.034), (0.8, 0.052, 0.024, 0.024),
               (0.93, 0.050, 0.020, 0.020), (1.0, 0.040, 0.014, 0.014)]   # Kuhmaul: broad, blunt, low toe

GART_Z = 0.475          # garter top (below the knee); slashed upper hose end just under it
HOSE_Z = 0.468
SL_ARM = (0.07, 0.44)   # sleeve puff (arm path param)
N_ARM, W_ARM = 9, 0.30
N_LEG, W_LEG = 11, 0.28

def _arm_t(p, s):
    """(t, angle) of p round the spread arm axis (front = +y)."""
    pts = C.arm_path(s, True)
    best = None
    for (t0, a), (t1, b) in zip(pts, pts[1:]):
        ab = b - a; u = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared)); q = a + ab * u
        dd = (p - q).length
        if best is None or dd < best[0]: best = (dd, lerp(t0, t1, u), q, ab.normalized())
    dd, t, q, d = best
    v = (V(0, 1, 0) - d * d.y).normalized(); u = v.cross(d).normalized()
    r = p - q
    return t, math.atan2(r.dot(v), s * r.dot(u)), dd

def _frac(a, n): return (a / (2 * math.pi) * n) % 1.0

def zone(p, part):
    """('slot', puff phase or None): garment layout shared by body_slot (ids) and add_folds (relief)."""
    x, y, z = p; ax = abs(x); s = 1.0 if x >= 0 else -1.0
    if part == 'arm':
        t, a, _ = _arm_t(V(p), s)
        if SL_ARM[0] < t < SL_ARM[1]:
            f = _frac(a, N_ARM)
            return ('sash', None) if f < W_ARM else ('coat', (f - W_ARM) / (1 - W_ARM))
        return ('coat', None)
    if part in ('leg', 'torso') and HOSE_Z < z < 0.985 and not (part == 'torso' and z > 0.96 and y > 0.02):
        a = math.atan2(y, s * (x - s * 0.092))
        f = _frac(a + 0.15, N_LEG)
        return ('sash', None) if f < W_LEG else ('coat', (f - W_LEG) / (1 - W_LEG))
    if part == 'leg':
        return ('breeches' if x > 0 else 'gaiter', None)
    if z > 1.586: return ('skin', None)
    if y > 0.0 and z > 1.462 + 0.03 * ss(0.05, 0.11, ax): return ('waist', None)       # shirt in the low square neck
    if y < -0.02 and 1.12 < z < 1.42 and ax < 0.125:                                   # back: rows of short slashes
        rz = (z - 1.12) / 0.10; fr = rz % 1.0
        if 0.12 < fr < 0.88 and ((x / 0.042 + 0.5 * (int(rz) % 2)) % 1.0) < 0.22: return ('sash', None)
    return ('coat', None)

def body_slot(p, part):
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'waist'
    return zone(p, part)[0]
C.body_slot = body_slot

# ------------------------------------------------------------------ slash relief (bake source): wraps the cloth folds
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
        x, y, z = P[i]
        if lin[i] and not coat[i]: d[i] = -0.0035; continue
        if not coat[i]: continue
        ax = abs(x)
        part = 'arm' if (ax > 0.172 + spread * 0.6 and 0.86 < z < 1.44) else ('leg' if z < 0.985 else 'torso')
        sl, ph = zone((x, y, z), part)
        if ph is not None:
            amp = 0.0075 if part == 'arm' else 0.0085
            d[i] = amp * math.sin(math.pi * ph) ** 0.55
    P = P + N * d[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
C.add_folds = add_folds

# ------------------------------------------------------------------ breastplate (fitted to the doublet, front only)
_FIT = {}
BP_NA, BP_NZ = 64, 40
BP_A = math.radians(92.0)

def _bp_ztop(a):
    aa = abs(a)
    return 1.428 + 0.016 * ss(0.0, math.radians(26), aa) - 0.150 * ss(math.radians(34), math.radians(84), aa)

def _bp_zbot(a):
    return 0.985 - 0.012 * math.cos(a) ** 4 + 0.03 * ss(math.radians(60), math.radians(92), abs(a))

def _fit_bp(tree):
    R = np.zeros((BP_NZ + 1, BP_NA + 1))
    Z = np.zeros_like(R)
    for j in range(BP_NA + 1):
        a = lerp(-BP_A, BP_A, j / BP_NA); d = V(math.sin(a), math.cos(a), 0)
        for i in range(BP_NZ + 1):
            z = lerp(_bp_zbot(a), _bp_ztop(a), i / BP_NZ); Z[i, j] = z
            c = V(0, 0.0, z); h = tree.ray_cast(c, d)
            R[i, j] = (V(h[0].x, h[0].y, 0)).length if h[0] is not None else np.nan
    for j in range(BP_NA + 1):
        m = np.isnan(R[:, j])
        if m.any(): R[m, j] = np.nanmax(R[:, j]) if not m.all() else 0.15
    raw = R.copy()
    S_ = R.copy()
    for _ in range(14):   # rigid plate: smooth hard (no pectorals / slash puffs), never inside the doublet
        T_ = S_.copy()
        T_[1:-1] = (S_[:-2] + S_[1:-1] * 2 + S_[2:]) / 4
        T_[:, 1:-1] = (T_[:, :-2] + T_[:, 1:-1] * 2 + T_[:, 2:]) / 4
        S_ = np.maximum(T_, raw + 0.010)
    for i in range(BP_NZ + 1):   # globose: the belly bulges forward under the chest
        for j in range(BP_NA + 1):
            a = lerp(-BP_A, BP_A, j / BP_NA)
            S_[i, j] += 0.012 * gauss(Z[i, j] - 1.20, 0.13) * math.cos(a) ** 2 + 0.004
    return S_, Z

def _bp_pt(R, Z, i, j, off=0.0):
    a = lerp(-BP_A, BP_A, j / BP_NA)
    return V(math.sin(a) * (R[i, j] + off), math.cos(a) * (R[i, j] + off), Z[i, j])

def breastplate(tree, hi=False):
    R, Z = _FIT['bp']
    js = list(range(0, BP_NA + 1, 1 if hi else 4)); is_ = list(range(0, BP_NZ + 1, 1 if hi else 5))
    secs = []
    for j in js:
        outer = [_bp_pt(R, Z, i, j, 0.0 if hi else 0.0015) for i in is_]
        inner = [_bp_pt(R, Z, i, j, -0.0035) for i in is_]
        if hi:   # flared bottom lip
            outer[0] = outer[0] + V(math.sin(lerp(-BP_A, BP_A, j / BP_NA)), math.cos(lerp(-BP_A, BP_A, j / BP_NA)), 0) * 0.004
        secs.append(outer + inner[::-1])
    out = [V3P.orient_out(grid_sweep('lpbreast', secs, closed_u=True, cap0=True, cap1=True, slot='steel'))]
    # rolled top edge (neck + arm openings) and a stop rib above it
    top = [_bp_pt(R, Z, BP_NZ, j, 0.001) for j in range(0, BP_NA + 1, 1 if hi else 4)]
    out.append(limb('lpbreast.roll', [(k / (len(top) - 1), p) for k, p in enumerate(top)], [(0, 0.0048, 0.0048, 0.0048)],
                    len(top) - 1, 8 if hi else 3, fwd=V(0, 0, 1), slot='steel'))
    if hi:
        rib = [_bp_pt(R, Z, BP_NZ - 3, j, 0.0) for j in range(4, BP_NA - 3)]
        out.append(limb('lpbreast.rib', [(k / (len(rib) - 1), p) for k, p in enumerate(rib)], [(0, 0.0022, 0.0022, 0.0022)],
                        len(rib) - 1, 6, fwd=V(0, 0, 1), slot='steel'))
        for j in (8, 20, 32, 44, 56):   # rivets along the bottom
            a = lerp(-BP_A, BP_A, j / BP_NA); n_ = V(math.sin(a), math.cos(a), 0)
            out.append(superellipsoid('lpbreast.riv', _bp_pt(R, Z, 2, j, 0.0005), (0.0035, 0.0035, 0.002), e=(2, 2), n=(8, 4),
                                      rot=n_.to_track_quat('Z', 'Y').to_matrix(), slot='metal'))
    # leather shoulder straps: plate top -> over the shoulder -> down the back
    for s in (1, -1):
        j = int(BP_NA / 2 + s * BP_NA * 0.205)
        p0 = _bp_pt(R, Z, BP_NZ - 2, j, 0.002)
        pn = []
        for k in range(13 if hi else 6):
            u = k / (12 if hi else 5)
            ang = lerp(0.0, math.pi * 0.92, u)   # sweep over the shoulder, front -> back
            c = V(s * 0.105, 0.0, 1.30)
            o = c + V(0, math.cos(ang), math.sin(ang)) * 0.5
            h = V3P.surf(tree, o, c - o, 0.0035)
            if h: pn.append(h)
        pn = [(p0, (p0 - V(0, 0, p0.z)).normalized())] + [q for q in pn if q[0].y < p0.y - 0.01]
        out.append(V3P.ribbon('lpstrap', pn, 0.024, hi, th=0.003, slot='cartbox'))
    return out

# ------------------------------------------------------------------ sword belt + Katzbalger at the left hip
BELT_Z = 0.958

def belt(tree, hi=False):
    out = [V3P.hem_band(tree, (0.0, 0.0, BELT_Z - 0.01), lambda x, y: BELT_Z - 0.012 * ss(0.0, 0.10, y) * 0.0 - 0.010 * ss(-0.02, -0.12, y), hi,
                        depth=0.020, off=0.0095, name='lpbelt', slot='cartbox', n=110 if hi else 20)]
    fr = V3P.surf(tree, (0.0, 0.5, BELT_Z - 0.01), (0, -1, 0), 0.011)
    c = fr[0] if fr else V(0.0, 0.13, BELT_Z - 0.01)
    out.append(superellipsoid('lpbelt.buck', c + V(0, 0.003, 0), (0.020, 0.005, 0.016), e=(2.4, 2.4), n=(10, 6) if hi else (6, 3), slot='metal'))
    return out

def sword(hi=False):
    th = V(-0.168, 0.085, 0.925)                      # scabbard throat
    tip = V(-0.205, -0.215, 0.665)
    d = (tip - th).normalized()                       # blade direction (down-back)
    side = d.cross(V(1, 0, 0)).normalized()           # guard plane: across the blade, roughly vertical / fore-aft
    out = [limb('lpsword', [(0, th), (1, tip)], [(0, 0.024, 0.008, 0.008), (0.8, 0.021, 0.007, 0.007), (1, 0.012, 0.005, 0.005)],
                8 if hi else 2, 10 if hi else 4, fwd=V(1, 0, 0), slot='scabbard', e=3.0)]
    out.append(limb('lpsword.chape', [(0, tip - d * 0.05), (1, tip + d * 0.004)], [(0, 0.0215, 0.0075, 0.0075), (1, 0.013, 0.0055, 0.0055)],
                    2 if hi else 1, 10 if hi else 4, fwd=V(1, 0, 0), slot='steel', e=3.0))
    out.append(limb('lpsword.locket', [(0, th - d * 0.004), (1, th + d * 0.03)], [(0, 0.026, 0.0095, 0.0095)], 1, 10 if hi else 4,
                    fwd=V(1, 0, 0), slot='steel', e=3.0, cap0=False, cap1=False))
    g = th - d * 0.010
    # S-shaped guard (figure-of-eight 'Katzbalger' hilt): two horizontal loops curling opposite ways
    for sg in (1, -1):
        pts = []
        for k in range(13 if hi else 5):
            u = k / (12 if hi else 4)
            ang = sg * u * math.pi * 1.6
            pts.append((u, g + side * sg * (0.035 * u) + (-d) * (0.020 * math.sin(ang * 0.9) * sg)))
        out.append(limb('lpsword.guard', pts, [(0, 0.0045, 0.0045, 0.0045), (1, 0.0038, 0.0038, 0.0038)], len(pts) - 1, 6 if hi else 3,
                        fwd=V(1, 0, 0), slot='steel'))
    gp0 = g - d * 0.004; gp1 = g - d * 0.105
    out.append(limb('lpsword.grip', [(0, gp0), (0.5, (gp0 + gp1) / 2), (1, gp1)], [(0, 0.011, 0.011, 0.011), (0.5, 0.013, 0.013, 0.013), (1, 0.010, 0.010, 0.010)],
                    6 if hi else 2, 8 if hi else 4, fwd=V(1, 0, 0), slot='cartbox'))
    # flat fan pommel
    out.append(superellipsoid('lpsword.pom', gp1 - d * 0.014, (0.034, 0.010, 0.016), e=(2.2, 3.0), n=(12, 6) if hi else (6, 3),
                              rot=Matrix((side, V(1, 0, 0), -d)).transposed(), slot='steel'))
    return out

def garters(tree, hi=False):
    out = V3P.leg_hems(tree, lambda x, y: GART_Z + 0.010 * ss(0.03, -0.05, y), hi, z0=GART_Z - 0.012, slot='stock', depth=0.024, off=0.0045)
    for o in out: o.name = 'lpgart' + o.name[3:]
    for s in (1, -1):   # bow knot on the outside of the leg, tails hanging
        c = V3P.surf(tree, (s * 0.30, 0.0, GART_Z - 0.012), (-s, 0, 0), 0.008)
        p = c[0] if c else V(s * 0.155, 0.0, GART_Z - 0.012)
        for k in (1, -1):
            out.append(superellipsoid('lpgart.bow', p + V(0, k * 0.016, 0.004), (0.006, 0.016, 0.011), e=(2, 2), n=(8, 5) if hi else (5, 3), slot='stock'))
            out.append(limb('lpgart.tail', [(0, p + V(0, k * 0.004, -0.004)), (1, p + V(s * 0.004, k * 0.014, -0.085))],
                            [(0, 0.0035, 0.009, 0.009), (1, 0.003, 0.011, 0.011)], 3 if hi else 1, 4, fwd=V(s, 0, 0), slot='stock', e=4.0))
    return out

# ------------------------------------------------------------------ slashed beret + ostrich plumes
HC = V(0, 0.004, 1.664)
BER_B = V(0.004, 0.000, 1.738)                       # beret base centre (head band)
BER_R = Matrix.Rotation(math.radians(-11), 3, 'Y') @ Matrix.Rotation(math.radians(-5), 3, 'X')   # tilted: right side up
BER_RB = 0.162                                        # brim radius

def _fit_band(htree, nu):
    rs = []
    for j in range(nu):
        a = 2 * math.pi * j / nu; d = BER_R @ V(math.cos(a), math.sin(a), 0)
        best = None
        for dz in (0.0, -0.010, 0.010):
            o = BER_B + BER_R @ V(0, 0, dz)
            h = htree.ray_cast(o + d * 0.3, -d)
            if h[0] is not None:
                r = (h[0] - o).dot(d); best = r if best is None else max(best, r)
        rs.append((best if best is not None else 0.08) + 0.006)
    return rs

def beret(hi=False):
    nu = 96 if hi else 20
    rb = _FIT['band_hi' if hi else 'band_lo']
    L = lambda r, a, h: BER_B + BER_R @ V(math.cos(a) * r, math.sin(a) * r, h)
    rings_ = []
    prof = [(0.0, 0.0, 0.0), (0.0, 0.003, 0.012), (0.5, 0.0, 0.020), (0.92, 0.0, 0.026), (1.0, 0.0, 0.034), (0.965, 0.0, 0.047),
            (0.62, 0.0, 0.054), (0.22, 0.0, 0.052)]
    for k, (f, dr, h) in enumerate(prof):
        ring_ = []
        for j in range(nu):
            a = 2 * math.pi * j / nu
            R0 = rb[j]; Rb = BER_RB * (1.0 - 0.04 * math.cos(2 * a))
            r = lerp(R0, Rb, f) + dr if k >= 2 else R0 + dr
            if k == 7: r = 0.035
            if hi and 3 <= k <= 5:   # slashed / scalloped edge of the brim
                r += 0.007 * (abs(math.sin(7 * a)) ** 0.5 - 0.6)
            ring_.append(L(r, a, h))
        rings_.append(ring_)
    def sl(c):   # slashes in the brim show the lining
        q = BER_R.transposed() @ (c - BER_B); a = math.atan2(q.y, q.x); r = math.hypot(q.x, q.y)
        if r > 0.10 and q.z > 0.028 and ((a / (2 * math.pi) * 14 + 0.5) % 1.0) < 0.16: return 'sash'
        return 'felt'
    out = [V3P.orient_out(grid_sweep('lpberet', rings_, closed_u=True, cap0=True, cap1=True, slot=sl))]
    # two curling ostrich plumes laid over the brim from the front-left, drooping behind
    for k, (slot, a0, sc) in enumerate((('plume', 2.15, 1.0), ('coat', 2.45, 0.86))):
        pth = []
        for m in range(9):
            u = m / 8
            a = a0 + u * 1.9 * sc
            r = lerp(0.05, BER_RB + 0.03, u ** 0.8)
            h = 0.058 + 0.05 * math.sin(math.pi * u * 0.8) - 0.09 * ss(0.7, 1.0, u) + 0.006 * k
            pth.append((u, L(r, a, h)))
        ns = 40 if hi else 10
        prof_ = []
        for m in range(ns + 1):
            u = m / ns
            w = (0.010 + 0.028 * math.sin(math.pi * min(1.0, u * 1.15)) ** 0.7) * sc
            if hi: w *= 1.0 + 0.22 * abs(math.sin(u * 55.0))   # fluffy barbs
            prof_.append((u, w, 0.0055, 0.0055))
        out.append(limb('lpplume', pth, prof_, ns, 8 if hi else 6, fwd=BER_R @ V(0, 0, 1), slot=slot, e=2.6))
    return out

# ------------------------------------------------------------------ pike
def pike(hi=False):
    import char_rig as R
    T = lambda p: R.REST['prop'] @ V(p)
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    y0, y1 = PIKE_Y0, PIKE_Y1
    out = [limb('lpshaft', [(0, T((0, y0, 0))), (0.5, T((0, 1.5, 0))), (1, T((0, y1 - 0.20, 0)))],
                [(0, 0.0160, 0.0160, 0.0160), (0.2, 0.0172, 0.0172, 0.0172), (1, 0.0140, 0.0140, 0.0140)],
                12 if hi else 3, 10 if hi else 6, fwd=up, slot='wood')]
    out.append(limb('lphead.sock', [(0, T((0, y1 - 0.22, 0))), (0.8, T((0, y1 - 0.13, 0))), (1, T((0, y1 - 0.115, 0)))],
                    [(0, 0.0160, 0.0160, 0.0160), (0.8, 0.0120, 0.0120, 0.0120), (1, 0.009, 0.009, 0.009)], 4 if hi else 1, 10 if hi else 6,
                    fwd=up, slot='steel'))
    out.append(limb('lphead', [(0, T((0, y1 - 0.12, 0))), (0.3, T((0, y1 - 0.085, 0))), (1, T((0, y1, 0)))],
                    [(0, 0.008, 0.006, 0.006), (0.3, 0.0145, 0.0065, 0.0065), (0.7, 0.009, 0.0045, 0.0045), (1, 0.0006, 0.0006, 0.0006)],
                    12 if hi else 3, 10 if hi else 4, fwd=up, slot='steel', cap1=False))
    for sg in (1, -1):   # long langets nailed down the shaft
        side = R.REST['prop'].to_3x3() @ V(sg, 0, 0)
        out.append(limb('lplang', [(0, T((0, y1 - 0.62, 0)) + side * 0.0145), (1, T((0, y1 - 0.20, 0)) + side * 0.0148)],
                        [(0, 0.0012, 0.0045, 0.0045), (1, 0.0016, 0.0055, 0.0055)], 4 if hi else 1, 4, fwd=up, slot='steel', e=4.0))
    out.append(limb('lpshaft.butt', [(0, T((0, y0 - 0.005, 0))), (1, T((0, y0 + 0.05, 0)))], [(0, 0.0170, 0.0170, 0.0170)], 1,
                    10 if hi else 5, fwd=up, slot='steel'))
    return out

def fit(htree, body_tree):
    _FIT['band_hi'] = _fit_band(htree, 96)
    hb = _FIT['band_hi']
    _FIT['band_lo'] = [max(hb[(j * 96 // 20 + k) % 96] for k in range(-3, 4)) + 0.002 for j in range(20)]
    _FIT['bp'] = _fit_bp(body_tree)
    print('[em_pike] band r', round(min(hb), 3), round(max(hb), 3), 'bp r', round(float(_FIT['bp'][0].min()), 3), round(float(_FIT['bp'][0].max()), 3))

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi or not _FIT:
        fit(C.surface_tools([head]), body_tree)
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'waist'); parts.append(cb)
    parts += breastplate(body_tree, hi) + belt(body_tree, hi) + sword(hi) + garters(body_tree, hi)
    parts += beret(hi) + pike(hi)
    return parts
C.build_kit = build_kit
