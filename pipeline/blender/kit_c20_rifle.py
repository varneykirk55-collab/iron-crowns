"""Eras v3 kit 8: Great War infantryman, c.1914-1917 (unit c20_rifle; docs/char/ERAS_PROGRESS.md). Patches char_v2
(loaded by char_v2_build.py when V3_KIT=kit_c20_rifle). Only the base human (MakeHuman head / eyes / hands, ear fix),
body cage, rig and material library are shared; every garment / item is built fresh here:
  * wool service tunic in the team colour: five-button fly front, pleated chest patch pockets with button flaps,
    skirt to the upper thigh with bellows hip pockets, stand-and-fall collar; matching wool trousers
  * puttees spiral-wound from the ankle to below the knee (spiral wrap relief + tape at the top), ankle boots
  * webbing equipment: waist belt with a plate buckle, cartridge pouches either side of the buckle, Y-braces over the
    shoulders, small pack on the back with a rolled groundsheet, haversack + entrenching tool at the back hips,
    water bottle in a felt cover, bayonet scabbard on the left hip
  * steel helmet: V3_HELMET = brodie (default; British / US Mk I - M1917), stahlhelm (German M1916) or adrian
    (French M1915); a non-default helmet builds as kid v3_c20_rifle_<helmet>
  * bolt-action rifle with a long sword bayonet fixed (musket clips; weapon_tip = bayonet point)"""
import math, os, bpy
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import char_rig as R
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, gauss, limb, ring, grid_sweep, superellipsoid, set_slot

HELMET = os.environ.get('V3_HELMET', 'brodie')
C.KID = 'v3_c20_rifle' + ('' if HELMET == 'brodie' else '_' + HELMET)
C.CLIP_STYLE = 'musket'
C.TIP_LOCAL = (0.0, 1.31, -0.004)        # bayonet point (weapon_tip on the prop)
C.SLOT_MAT.update({'breeches': 'wool', 'gaiter': 'wool', 'shoe': 'shoe_leather', 'belt': 'canvas', 'cartbox': 'canvas',
                   'knapsack': 'canvas', 'roll': 'canvas', 'felt': 'iron', 'scabbard': 'leather', 'stock': 'wood',
                   'sponge': 'wool', 'button': 'brass', 'collar': 'wool'})
C.BODY_TRIS = 4300
HM.FIST['.L'] = 0.007
C.HEAD_BOX = (0.17, -0.17, 0.19, 1.95)  # helmet brim gets head-level texel density
C.KIT_PAL = {'gaiter': '#6a6248', 'shoe': '#3a2a1e', 'belt': '#8c8360', 'cartbox': '#837a57', 'knapsack': '#8a8160',
             'roll': '#5c5a44', 'felt': '#5a5d4a', 'scabbard': '#2d221a', 'steel': '#8b9095', 'metal': '#a68a45',
             'wood': '#6a4527', 'stock': '#6a4527', 'sponge': '#6b6253', 'button': '#a68a45'}
C.KIT_RULES = [(('wwhelm',), 'head'), (('wwbelt', 'wwbrace', 'wwputt', 'wwcoll', 'wwbtn', 'wwflap'), 'transfer'),
               (('wwskirt',), 'tail'), (('wwpouch', 'wwhav', 'wwbot', 'wwtool', 'wwbay'), 'hips'), (('wwpack',), 'chest'),
               (('wwstock', 'wwbarrel', 'wwguard', 'wwbolt', 'wwmag', 'wwband', 'wwbayo', 'wwsling', 'wwbutt'), 'prop')]

PUT_TOP = 0.505            # puttees: ankle to below the knee
BELT_Z = 0.985
COLLAR_Z = 1.548

def body_slot(p, part):
    x, y, z = p
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'coat'
    if part == 'arm': return 'coat'
    if part == 'leg':
        return 'gaiter' if z < PUT_TOP - 0.004 else 'coat'
    if z > COLLAR_Z: return 'skin'
    return 'coat'
C.body_slot = body_slot

def ss_np(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

_add_folds = C.add_folds
def add_folds(o, spread):
    """puttee spiral wrap (overlapping bands, sharp lower edges) + chest patch pockets / fly placket raised (bake)."""
    _add_folds(o, spread)
    me = o.data; me.update()
    n = len(me.vertices)
    P = np.zeros(n * 3); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    N = np.zeros(n * 3); me.vertices.foreach_get('normal', N); N = N.reshape(-1, 3)
    slot = np.zeros(len(me.polygons), np.int32); me.attributes['slot'].data.foreach_get('value', slot)
    lt = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lt)
    tot = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', tot)
    fs = np.repeat(slot, tot)
    put = np.zeros(n, bool); put[lt[fs == C.S['gaiter']]] = True
    coat = np.zeros(n, bool); coat[lt[fs == C.S['coat']]] = True
    x, y, z = P[:, 0], P[:, 1], P[:, 2]; ax = np.abs(x); s = np.sign(x + 1e-9)
    a = np.arctan2(y, s * (x - s * 0.092))
    u = z / 0.034 + s * a / (2 * np.pi)                     # one band per 3.4 cm of rise, wound outward
    f = u - np.floor(u)
    d = put * (0.0020 * f ** 0.6 - 0.0008) * ss_np(0.10, 0.13, z)
    arm = (ax > 0.172 + spread * 0.6) & (z > 0.86) & (z < 1.44)
    tor = ~arm & (z > 0.86) & (z < 1.55)
    pk = tor & (y > 0.03) & (ax > 0.055) & (ax < 0.150) & (z > 1.235) & (z < 1.395)
    pk_e = np.minimum.reduce([ax - 0.055, 0.150 - ax, z - 1.235, 1.395 - z])
    d += coat * pk * 0.0032 * ss_np(0.0, 0.004, pk_e)
    box = pk & (np.abs(ax - 0.1025) < 0.012)                  # box pleat down the pocket middle
    d += coat * box * 0.0012
    fly = tor & (y > 0.03) & (ax < 0.022) & (z > 0.98) & (z < 1.50)
    d += coat * fly * 0.0018 * ss_np(0.022, 0.016, ax)
    P = P + N * d[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
C.add_folds = add_folds

# ------------------------------------------------------------------ tunic skirt (closed front, back vent)
SK = [(1.005, .166, .118, .122), (0.95, .180, .126, .138), (0.89, .190, .134, .150), (0.83, .196, .140, .156),
      (0.785, .199, .144, .159)]
SK_Z0, SK_Z1 = SK[0][0], SK[-1][0]

def _sk(z):
    for a, b in zip(SK, SK[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0]); return [lerp(a[k], b[k], t) for k in range(1, 4)]
    return list((SK[0] if z > SK_Z0 else SK[-1])[1:])

def _skp(a, z, s, off=0.0):
    rx, rf, rb = _sk(z)
    f = lambda q: math.copysign(abs(q) ** (2.0 / 2.3), q)
    ca, sa = math.cos(a), math.sin(a)
    return V(s * (f(ca) * rx + off * ca), f(sa) * (rf if sa > 0 else rb) + off * sa, z)

def skirt(hi=False):
    out = []
    nz, na = (44, 110) if hi else (5, 8)
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            z = lerp(SK_Z0, SK_Z1, i / nz)
            dl0 = math.radians(1.0); dl1 = math.radians(3.0) * ss(0.92, SK_Z1, z)   # front closure / back vent
            outer, inner = [], []
            for j in range(na + 1):
                a = lerp(math.pi / 2 - dl0, -math.pi / 2 + dl1, j / na)
                p = _skp(a, z, s)
                if hi:
                    p += V(s * math.cos(a), math.sin(a), 0) * (0.0025 * math.exp(-((z - SK_Z1 - 0.008) / 0.008) ** 2))
                d = V(s * math.cos(a), math.sin(a), 0)
                outer.append(p); inner.append(p - d * 0.007)
            secs.append(outer + inner[::-1])
        out.append(grid_sweep('wwskirt' + ('R' if s > 0 else 'L'), secs, cap0=True, cap1=True, slot='coat'))
    return out

def hip_pockets(hi=False):
    """bellows hip pockets on the skirt: flap + button (the pocket bag is a raised panel)."""
    out = []
    for s in (1, -1):
        a = math.radians(48)
        for nm, z, r, th in (('wwskirt.pk', 0.865, (0.060, 0.008, 0.062), 0.008), ('wwflap', 0.925, (0.064, 0.007, 0.022), 0.010)):
            p = _skp(a, z, s, th * 0.5)
            nrm = V(s * math.cos(a), math.sin(a), 0).normalized()
            rot = nrm.to_track_quat('Y', 'Z').to_matrix()
            out.append(superellipsoid(nm + ('R' if s > 0 else 'L'), p, r, e=(3.5, 3.5), n=(12, 8) if hi else (6, 3), rot=rot, slot='coat'))
        b = _skp(a, 0.912, s, 0.015)
        out.append(superellipsoid('wwbtn.h', b, (0.006, 0.004, 0.006), e=(2, 2), n=(8, 4) if hi else (4, 2), slot='button'))
    return out

# ------------------------------------------------------------------ collar, buttons, chest pocket flaps
def collar(tree, hi=False):
    """turned-down (stand-and-fall) collar: lies over the stand from the top edge down onto the shoulders."""
    n = 96 if hi else 18
    rings_ = []
    for zz, off in ((COLLAR_Z + 0.002, 0.001), (COLLAR_Z - 0.010, 0.010), (COLLAR_Z - 0.035, 0.016), (COLLAR_Z - 0.052, 0.020)):
        rr = []
        for j in range(n):
            a = 2 * math.pi * j / n; d = V(math.cos(a), math.sin(a), 0)
            c = V(0, 0.020, zz)
            h = tree.ray_cast(c + d * 0.3, -d)
            r = ((V(h[0].x, h[0].y, 0) - V(0, 0.02, 0)).length if h[0] is not None else 0.065) + 0.004 + off
            fr = math.exp(-(math.atan2(math.cos(a), math.sin(a)) / 0.22) ** 2)   # open V at the throat
            rr.append(V(math.cos(a) * r, 0.020 + math.sin(a) * r, zz - 0.020 * fr * (1 - (zz - COLLAR_Z + 0.052) / 0.054)))
        rings_.append(rr)
    rings_.append([V(p.x * 0.96, 0.02 + (p.y - 0.02) * 0.96, p.z) for p in rings_[-1]])
    return [V3P.orient_out(grid_sweep('wwcoll', rings_, closed_u=True, cap0=False, cap1=False, slot='coat'))]

def buttons(tree, hi=False):
    out = []
    for i, z in enumerate((1.465, 1.36, 1.255, 1.15, 1.045)):
        h = V3P.surf(tree, (0.0, 0.5, z), (0, -1, 0), 0.006)
        if h: out.append(superellipsoid('wwbtn', h[0], (0.0075, 0.004, 0.0075), e=(2, 2), n=(10, 5) if hi else (5, 2), slot='button'))
    for s in (1, -1):
        h = V3P.surf(tree, (s * 0.1025, 0.5, 1.385), (0, -1, 0), 0.006)
        if not h: continue
        c, nrm = h
        rot = nrm.to_track_quat('Y', 'Z').to_matrix()
        out.append(superellipsoid('wwflap' + ('R' if s > 0 else 'L'), c, (0.052, 0.004, 0.020), e=(3.5, 3), n=(12, 6) if hi else (6, 2), rot=rot,
                                  slot='coat'))
        out.append(superellipsoid('wwbtn.p', c + nrm * 0.004 + V(0, 0, -0.008), (0.0055, 0.0035, 0.0055), e=(2, 2), n=(8, 4) if hi else (4, 2),
                                  slot='button'))
    return out

def puttee_tops(tree, hi=False):
    out = V3P.leg_hems(tree, lambda x, y: PUT_TOP + 0.010 * math.atan2(y, abs(x)) / math.pi, hi, z0=PUT_TOP - 0.01, slot='gaiter',
                       depth=0.022, off=0.0045)
    for o in out: o.name = 'wwputt' + o.name[3:]
    return out

# ------------------------------------------------------------------ webbing
def belt(tree, hi=False):
    out = [V3P.hem_band(tree, (0.0, 0.0, BELT_Z - 0.01), lambda x, y: BELT_Z, hi, depth=0.052, off=0.0105, name='wwbelt',
                        slot='belt', n=120 if hi else 20)]
    fr = V3P.surf(tree, (0.0, 0.5, BELT_Z - 0.026), (0, -1, 0), 0.013)
    c = fr[0] if fr else V(0, 0.135, BELT_Z - 0.026)
    out.append(superellipsoid('wwbelt.b', c + V(0, 0.002, 0), (0.034, 0.005, 0.027), e=(3, 3), n=(12, 6) if hi else (6, 3), slot='metal'))
    return out

def pouches(tree, hi=False):
    out = []
    for s in (1, -1):
        for k, xx in enumerate((0.055, 0.098, 0.140)):
            h = V3P.surf(tree, (s * xx, 0.5, BELT_Z - 0.030), (0, -1, 0), 0.028)
            if not h: continue
            c, nrm = h
            nrm = V(nrm.x, nrm.y, 0).normalized()
            rot = nrm.to_track_quat('Y', 'Z').to_matrix()
            out.append(superellipsoid('wwpouch' + ('R' if s > 0 else 'L'), c, (0.021, 0.020, 0.040), e=(3.2, 3.2),
                                      n=(12, 8) if hi else (6, 3), rot=rot, slot='cartbox'))
            if hi:
                out.append(superellipsoid('wwpouch.f', c + nrm * 0.019 + V(0, 0, 0.022), (0.021, 0.003, 0.018), e=(3.5, 3), n=(10, 4),
                                          rot=rot, slot='cartbox'))
    return out

def _brace_path(tree, s, hi):
    """Y-brace: front from the pouches up over the shoulder, down the back to the centre ring (surface samples)."""
    pn = []
    nf = 22 if hi else 6
    for i in range(nf + 1):
        z = lerp(BELT_Z + 0.04, 1.47, i / nf); x = s * lerp(0.098, 0.115, i / nf)
        h = V3P.surf(tree, (x, 0.5, z), (0, -1, 0), 0.006)
        if h: pn.append(h)
    for i in range(1, (8 if hi else 3)):
        y = lerp(0.06, -0.08, i / (8 if hi else 3))
        h = V3P.surf(tree, (s * 0.118, y, 1.9), (0, 0, -1), 0.006)
        if h: pn.append(h)
    nb = 16 if hi else 4
    for i in range(nb + 1):
        t = i / nb; z = lerp(1.47, 1.22, t); x = s * lerp(0.115, 0.012, t)
        h = V3P.surf(tree, (x, -0.5, z), (0, 1, 0), 0.006)
        if h: pn.append(h)
    return pn

def braces(tree, hi=False):
    out = []
    for s in (1, -1):
        pn = _brace_path(tree, s, hi)
        if len(pn) > 2: out.append(V3P.ribbon('wwbrace' + ('R' if s > 0 else 'L'), pn, 0.034, hi, th=0.003, slot='belt'))
    pn = []
    for i in range((10 if hi else 3) + 1):
        z = lerp(1.22, BELT_Z + 0.01, i / (10 if hi else 3))
        h = V3P.surf(tree, (0.0, -0.5, z), (0, 1, 0), 0.006)
        if h: pn.append(h)
    if len(pn) > 2: out.append(V3P.ribbon('wwbrace.c', pn, 0.034, hi, th=0.003, slot='belt'))
    h = V3P.surf(tree, (0.0, -0.5, 1.22), (0, 1, 0), 0.009)
    if h: out.append(superellipsoid('wwbrace.ring', h[0], (0.022, 0.004, 0.022), e=(2, 2), n=(10, 4) if hi else (5, 2), slot='metal'))
    return out

def pack(tree, hi=False):
    h = V3P.surf(tree, (0.0, -0.5, 1.30), (0, 1, 0), 0.0)
    by = h[0].y if h else -0.13
    c = V(0, by - 0.062, 1.30)
    out = [superellipsoid('wwpack', c, (0.150, 0.058, 0.130), e=(3.2, 3.0), n=(16, 10) if hi else (8, 4), slot='knapsack')]
    if hi:
        out.append(superellipsoid('wwpack.f', c + V(0, -0.050, 0.075), (0.150, 0.012, 0.070), e=(3.5, 3), n=(14, 6), slot='knapsack'))
    out.append(limb('wwpack.roll', [(0, c + V(-0.16, -0.008, 0.155)), (1, c + V(0.16, -0.008, 0.155))], [(0, 0.034, 0.034, 0.034)],
                    6 if hi else 2, 12 if hi else 6, fwd=V(0, 0, 1), slot='roll'))
    for sx in (-0.10, 0.10):
        out.append(limb('wwpack.st', [(0, c + V(sx, -0.040, 0.193)), (1, c + V(sx, -0.061, 0.0))], [(0, 0.012, 0.0022, 0.0022)], 2, 4,
                        fwd=V(0, -1, 0), slot='belt'))
    return out

def back_gear(hi=False):
    out = []
    # haversack at the left back hip
    out.append(superellipsoid('wwhav', V(-0.150, -0.130, 0.885), (0.050, 0.055, 0.085), e=(3, 3), n=(12, 8) if hi else (6, 3),
                              rot=Matrix.Rotation(math.radians(-35), 3, 'Z'), slot='knapsack'))
    # entrenching tool carrier at the back: blade case + helve
    out.append(superellipsoid('wwtool', V(0.060, -0.180, 0.905), (0.075, 0.020, 0.080), e=(3, 3), n=(12, 8) if hi else (6, 3),
                              slot='cartbox'))
    out.append(limb('wwtool.h', [(0, V(0.060, -0.170, 0.84)), (1, V(0.070, -0.165, 0.60))], [(0, 0.014, 0.014, 0.014)], 3 if hi else 1,
                    8 if hi else 4, slot='wood'))
    # water bottle in a felt cover at the right back hip
    out.append(superellipsoid('wwbot', V(0.165, -0.110, 0.860), (0.030, 0.060, 0.090), e=(2.4, 2.2), n=(14, 8) if hi else (6, 4),
                              rot=Matrix.Rotation(math.radians(30), 3, 'Z'), slot='sponge'))
    out.append(limb('wwbot.c', [(0, V(0.165, -0.110, 0.945)), (1, V(0.165, -0.110, 0.968))], [(0, 0.010, 0.010, 0.010)], 1, 6 if hi else 4,
                    slot='metal'))
    # bayonet scabbard on the left hip (frog on the belt)
    a, b = V(-0.168, -0.040, 0.955), V(-0.195, -0.100, 0.540)
    out.append(limb('wwbay', [(0, a), (1, b)], [(0, 0.008, 0.016, 0.016), (0.9, 0.007, 0.012, 0.012), (1, 0.005, 0.006, 0.006)],
                    6 if hi else 2, 8 if hi else 4, fwd=V(1, 0, 0), slot='scabbard', e=2.6))
    out.append(superellipsoid('wwbay.fr', a + V(0, 0, -0.03), (0.012, 0.024, 0.042), e=(3, 3), n=(8, 4) if hi else (4, 2), slot='belt'))
    return out

# ------------------------------------------------------------------ steel helmets (fitted round the hi MakeHuman head)
HAT_B = V(0.0, 0.004, 1.742)
HAT_R = Matrix.Rotation(math.radians(5), 3, 'X')
_FIT = {}

def _fit_band(htree, nu):
    rs = []
    for j in range(nu):
        a = 2 * math.pi * j / nu; d = HAT_R @ V(math.cos(a), math.sin(a), 0)
        best = None
        for dz in (0.0, -0.012, 0.012, 0.025):
            o = HAT_B + HAT_R @ V(0, 0, dz)
            h = htree.ray_cast(o + d * 0.3, -d)
            if h[0] is not None:
                r = (h[0] - o).dot(d); best = r if best is None else max(best, r)
        rs.append((best if best is not None else 0.08) + 0.008)
    return rs

def helmet(hi=False):
    nu = 96 if hi else 20
    rb = _FIT['band_hi' if hi else 'band_lo']
    L = lambda r, a, h: HAT_B + HAT_R @ V(math.cos(a) * r, math.sin(a) * r, h)
    A = lambda j: 2 * math.pi * j / nu
    out = []
    if HELMET == 'stahlhelm':
        crown_h, dome = 0.112, 0.6
    elif HELMET == 'adrian':
        crown_h, dome = 0.118, 0.5
    else:
        crown_h, dome = 0.098, 0.75
    ks = [0.0, 0.25, 0.5, 0.7, 0.85, 0.95, 1.0] if hi else [0.0, 0.5, 0.85, 1.0]
    rows = []
    for k in ks:
        g = math.sqrt(max(0.0, 1 - k ** 2)) if k > 0 else 1.0
        g = lerp(1.0, g, dome) if k < 1 else 0.0
        if k >= 1.0: break
        rows.append([L(rb[j] * (1.0 - (1 - g) * (1.0 if k > 0 else 0)), A(j), crown_h * k) for j in range(nu)])
    shell = []
    if HELMET == 'stahlhelm':
        # skirt: short visor at the front, flared neck guard dropping at the sides and back
        for t in (1.0, 0.65, 0.3) if hi else (1.0, 0.4):
            r_ = []
            for j in range(nu):
                a = A(j); front = max(0.0, math.sin(a)) ** 2; back = max(0.0, -math.sin(a))
                drop = lerp(0.030, 0.085, 1 - front) * t
                flare = (0.012 + 0.030 * (1 - front) * t ** 1.4) * t
                r_.append(L(rb[j] + flare, a, -drop))
            shell.append(r_)
        shell = shell[::-1]
        rows = shell + rows
        o = grid_sweep('wwhelm', rows, closed_u=True, cap0=False, cap1=True, slot='felt')
        out.append(V3P.orient_out(o))
        rim = rows[0]
        out.append(limb('wwhelm.rim', [(j / nu, rim[j % nu]) for j in range(nu + 1)], [(0, 0.0035, 0.0035, 0.0035)], nu, 6 if hi else 3,
                        fwd=V(0, 0, 1), slot='felt'))
        for s in (1, -1):   # ventilation lugs
            j = int(nu * (0.0 if s > 0 else 0.5)) % nu
            out.append(superellipsoid('wwhelm.lug', L(rb[j] + 0.004, A(j) + s * 0.25, 0.035), (0.010, 0.010, 0.010), e=(2, 2),
                                      n=(8, 4) if hi else (4, 2), slot='felt'))
        return out
    o = grid_sweep('wwhelm', rows, closed_u=True, cap0=False, cap1=True, slot='felt')
    out.append(V3P.orient_out(o))
    # brim
    if HELMET == 'adrian':
        W = lambda a: 0.012 + 0.035 * max(0.0, math.sin(a)) ** 2 + 0.050 * max(0.0, -math.sin(a)) ** 2   # front + longer rear peak
        Hd = lambda a, f: -0.018 * f * (0.4 + 0.6 * abs(math.sin(a)))
    else:   # Brodie: wide flat brim all round, slight droop
        W = lambda a: 0.050
        Hd = lambda a, f: -0.010 * f ** 1.5
    nb = 4 if hi else 1
    top = [[L(lerp(rb[j] - 0.002, rb[j] + W(A(j)), k / nb), A(j), Hd(A(j), k / nb)) for j in range(nu)] for k in range(nb + 1)]
    bot = [[p - HAT_R @ V(0, 0, 0.003) for p in r_] for r_ in top]
    out.append(V3P.orient_out(grid_sweep('wwhelm.brim', top + bot[::-1], closed_u=True, cap0=False, cap1=False, slot='felt')))
    e = top[-1]
    out.append(limb('wwhelm.rim', [(j / nu, e[j % nu]) for j in range(nu + 1)], [(0, 0.0028, 0.0028, 0.0028)], nu, 6 if hi else 3,
                    fwd=V(0, 0, 1), slot='felt'))
    if HELMET == 'adrian':   # crest comb front to back
        cp = []
        for m in range(13):
            a = math.radians(lerp(80, -80, m / 12))
            cp.append((m / 12, HAT_B + HAT_R @ V(0, math.sin(a) * rb[nu // 4] * 0.62, crown_h * 0.92 + 0.012 * math.cos(a) +
                                                 (0.0 if abs(a) < 1.2 else -0.01))))
        out.append(limb('wwhelm.crest', cp, [(0, 0.004, 0.006, 0.006), (0.5, 0.004, 0.018, 0.0), (1, 0.004, 0.006, 0.006)], 12 if hi else 4,
                        6 if hi else 4, fwd=V(0, 0, 1), slot='felt'))
    return out

def chin_strap(hi=False):
    """leather chin strap from the helmet sides under the chin (head-rigid)."""
    rb = _FIT['band_hi']; nu = len(rb)
    pts = []
    n = 14 if hi else 5
    for k in range(n + 1):
        t = k / n; a = math.pi * t
        x = math.cos(a) * lerp(rb[0], rb[nu // 2], t) * 0.93
        z = HAT_B.z - 0.012 - 0.150 * math.sin(a) ** 0.7
        y = 0.020 + 0.055 * math.sin(a) ** 2
        pts.append((t, V(x, y, z)))
    return [limb('wwhelm.strap', pts, [(0, 0.0025, 0.007, 0.007)], n, 4, fwd=V(0, 1, 0), slot='scabbard')]

# ------------------------------------------------------------------ bolt-action rifle (prop frame: barrel along +y)
def rifle(hi=False):
    T = lambda p: R.REST['prop'] @ V(p)
    rot3 = R.REST['prop'].to_3x3()
    up = rot3 @ V(0, 0, 1); side = rot3 @ V(1, 0, 0)
    stock = [(-0.34, 0.020, -0.130, 0.010), (-0.25, 0.020, -0.108, 0.012), (-0.12, 0.017, -0.064, 0.010), (-0.05, 0.014, -0.052, 0.006),
             (0.00, 0.016, -0.060, 0.010), (0.10, 0.018, -0.032, 0.012), (0.30, 0.016, -0.026, 0.010), (0.78, 0.014, -0.022, 0.008),
             (0.82, 0.012, -0.018, 0.004)]
    nu = 12 if hi else 6
    secs = []
    for y, hw, zb, zt in stock:
        zc, hz = (zb + zt) / 2, (zt - zb) / 2
        secs.append(ring(T((0, y, zc)), side, up, hw, hz, hz, nu, 3.0))
    out = [grid_sweep('wwstock', secs, slot='stock')]
    out.append(limb('wwbutt', [(0, T((0, -0.348, -0.060))), (1, T((0, -0.336, -0.060)))], [(0, 0.021, 0.072, 0.072)], 1, nu, fwd=up,
                    slot='steel', e=3.0))
    out.append(limb('wwbarrel', [(0, T((0, 0.0, 0.016))), (1, T((0, 0.90, 0.016)))], [(0, 0.012, 0.012, 0.012), (1, 0.008, 0.008, 0.008)],
                    3 if hi else 1, 10 if hi else 5, fwd=up, slot='steel'))
    out.append(limb('wwguard', [(0, T((0, 0.14, 0.022))), (1, T((0, 0.76, 0.020)))], [(0, 0.013, 0.008, 0.004)], 3 if hi else 1,
                    8 if hi else 4, fwd=up, slot='stock'))   # upper handguard
    out.append(superellipsoid('wwbolt', T((0.0, 0.03, 0.024)), (0.013, 0.075, 0.012), e=(3, 3), n=(10, 6) if hi else (5, 2), rot=rot3,
                              slot='steel'))
    out.append(limb('wwbolt.h', [(0, T((0.010, -0.010, 0.026))), (1, T((0.048, -0.022, 0.004)))], [(0, 0.0045, 0.0045, 0.0045)],
                    2 if hi else 1, 6 if hi else 3, fwd=up, slot='steel'))
    out.append(superellipsoid('wwbolt.k', T((0.050, -0.023, 0.002)), (0.008, 0.008, 0.008), e=(2, 2), n=(8, 4) if hi else (4, 2),
                              rot=rot3, slot='steel'))
    out.append(superellipsoid('wwmag', T((0, 0.075, -0.040)), (0.014, 0.035, 0.018), e=(3, 3), n=(8, 4) if hi else (4, 2), rot=rot3,
                              slot='steel'))
    out.append(limb('wwmag.tg', [(0, T((0, 0.000, -0.036))), (0.5, T((0, 0.020, -0.062))), (1, T((0, 0.045, -0.040)))],
                    [(0, 0.004, 0.003, 0.003)], 4 if hi else 2, 4, fwd=side, slot='steel'))   # trigger guard
    for y in (0.40, 0.76):
        out.append(limb('wwband', [(0, T((0, y - 0.008, -0.002))), (1, T((0, y + 0.008, -0.002)))], [(0, 0.020, 0.030, 0.030)], 1,
                        10 if hi else 5, fwd=up, slot='steel'))
    out.append(limb('wwbayo', [(0, T((0, 0.86, -0.006))), (1, T((0, 0.905, -0.006)))], [(0, 0.012, 0.012, 0.012)], 1, 8 if hi else 4,
                    fwd=up, slot='steel'))
    out.append(limb('wwbayo.b', [(0, T((0, 0.90, -0.006))), (0.8, T((0, 1.24, -0.004))), (1, T((0, 1.31, -0.004)))],
                    [(0, 0.004, 0.012, 0.012), (0.8, 0.003, 0.011, 0.011), (1, 0.001, 0.001, 0.001)], 6 if hi else 2, 6 if hi else 4,
                    fwd=up, slot='steel', e=2.5, cap1=False))
    sl = [T((0.0, 0.40, -0.030)), T((0.0, 0.20, -0.070)), T((0.0, -0.02, -0.095)), T((0.0, -0.26, -0.130))]
    secs = [[p + side * 0.003 + up * 0.010, p - side * 0.003 + up * 0.010, p - side * 0.003 - up * 0.010, p + side * 0.003 - up * 0.010]
            for p in sl]
    out.append(grid_sweep('wwsling', secs, slot='belt'))
    return out

def fit(htree):
    _FIT['band_hi'] = _fit_band(htree, 96)
    hb = _FIT['band_hi']
    _FIT['band_lo'] = [max(hb[(j * 96 // 20 + k) % 96] for k in range(-3, 4)) + 0.002 for j in range(20)]
    print('[c20_rifle] helmet', HELMET, 'band r', round(min(hb), 3), round(max(hb), 3), flush=True)

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi or not _FIT:
        fit(C.surface_tools([head]))
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'coat'); parts.append(cb)
    parts += skirt(hi) + hip_pockets(hi) + collar(body_tree, hi) + buttons(body_tree, hi) + puttee_tops(body_tree, hi)
    parts += belt(body_tree, hi) + pouches(body_tree, hi) + braces(body_tree, hi) + pack(body_tree, hi) + back_gear(hi)
    parts += helmet(hi) + chin_strap(hi) + rifle(hi)
    return parts
C.build_kit = build_kit
