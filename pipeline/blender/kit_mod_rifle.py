"""Eras v3 kit 9: modern infantryman, c.1980-2000 (unit mod_rifle; docs/char/ERAS_PROGRESS.md). Patches char_v2
(loaded by char_v2_build.py when V3_KIT=kit_mod_rifle). Only the base human (MakeHuman head / eyes / hands, ear fix),
body cage, rig and material library are shared; every garment / item is built fresh here:
  * head with painted stubble (jaw, chin, upper lip)
  * gloves replacing the bare hands: the MakeHuman hand meshes re-slotted as leather gloves (same weights), slightly
    proud of the skin
  * camo combat jacket + trousers in the team colour with a printed 4-tone woodland pattern (luminance print baked into
    the detail map, CAMO_SLOTS), stand collar, thigh cargo pockets; trousers bloused into black combat boots
  * knee pads (hard cap on a strap)
  * plate carrier: front + back plates, shoulder straps, cummerbund; three magazine pouches + radio pouch with antenna
    stub on the front; small assault pack on the back; rigger's belt with a buckle
  * kevlar helmet (PASGT shape: brow lip, ear / neck skirt) with a camo cover (team colour), elastic band, NVG mount and
    chin strap
  * 5.56 mm assault rifle with optic and sling (musket clips for now; carbine clips requested from Rob; weapon_tip =
    muzzle)"""
import math, bpy
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import char_rig as R
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, gauss, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_mod_rifle'
C.CLIP_STYLE = 'musket'
C.TIP_LOCAL = (0.0, 0.635, 0.012)       # flash hider (weapon_tip on the prop)
C.SLOT_MAT.update({'coat': 'canvas', 'collar': 'canvas', 'boot': 'shoe_leather', 'shoe': 'shoe_leather', 'cuff': 'leather',
                   'cartbox': 'canvas', 'knapsack': 'canvas', 'belt': 'canvas', 'roll': 'canvas', 'stock': 'steel', 'steel': 'steel',
                   'metal': 'steel', 'sponge': 'canvas'})
C.CAMO_SLOTS = ('coat',)
C.BODY_TRIS = 4300
HM.FIST['.L'] = 0.007
C.HEAD_BOX = (0.17, -0.17, 0.19, 1.95)
C.KIT_PAL = {'boot': '#1f1d1b', 'shoe': '#1f1d1b', 'cuff': '#2e2b27', 'cartbox': '#6e6a4f', 'knapsack': '#66634a',
             'belt': '#5c5a45', 'roll': '#3b3a30', 'stock': '#262728', 'steel': '#3a3c3e', 'metal': '#4a4c4e', 'sponge': '#55543f'}
C.KIT_RULES = [(('mhelm',), 'head'), (('mknee', 'mcb', 'mstrap', 'mbelt', 'mboot', 'mcoll'), 'transfer'),
               (('mcarr', 'mmag', 'mradio', 'mpack'), 'chest'),
               (('mstock', 'mrec', 'mgrip', 'mrmag', 'mhg', 'mbarrel', 'moptic', 'msling', 'mfh'), 'prop')]

BOOT_TOP = 0.245
COLLAR_Z = 1.548
BELT_Z = 0.990

def body_slot(p, part):
    x, y, z = p
    if part == 'shoe': return 'boot'
    if part in ('collar', 'arm'): return 'coat'
    if part == 'leg':
        return 'boot' if z < BOOT_TOP - 0.004 else 'coat'
    if z > COLLAR_Z: return 'skin'
    return 'coat'
C.body_slot = body_slot

def ss_np(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

_add_folds = C.add_folds
def add_folds(o, spread):
    """thigh cargo pockets + sleeve pockets raised (bake), boot lacing ridges."""
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
    boot = np.zeros(n, bool); boot[lt[fs == C.S['boot']]] = True
    x, y, z = P[:, 0], P[:, 1], P[:, 2]; ax = np.abs(x)
    leg = z < 0.86
    lx = ax - 0.095                                   # outward from the leg centre line
    pk = leg & (lx > 0.035) & (z > 0.600) & (z < 0.760) & (y > -0.045) & (y < 0.055)
    pk_e = np.minimum.reduce([z - 0.600, 0.760 - z, y + 0.045, 0.055 - y])
    d = coat * pk * 0.0045 * ss_np(0.0, 0.006, pk_e)
    fl = leg & (lx > 0.035) & (z > 0.738) & (z < 0.772) & (y > -0.050) & (y < 0.060)
    d += coat * fl * 0.0025
    arm = (ax > 0.172 + spread * 0.6) & (z > 1.20) & (z < 1.44)
    sp = arm & (z > 1.29) & (z < 1.40)
    d += coat * sp * 0.0025 * ss_np(0.0, 0.008, np.minimum(z - 1.29, 1.40 - z))
    lace = boot & (y > 0.02) & (ax > 0.05) & (z > 0.07) & (z < BOOT_TOP)
    d += lace * 0.0012 * (np.sin(z / 0.012 * np.pi) > 0.3)
    P = P + N * d[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
C.add_folds = add_folds

# ------------------------------------------------------------------ head stubble + gloves (MakeHuman parts)
def stubble(head):
    me = head.data
    P = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    up = P[:, 2] > 1.58
    i = np.argmax(np.where(up, P[:, 1], -9)); nx, ny, nz = P[i]
    x, y, z = P[:, 0] - nx, P[:, 1], P[:, 2] - nz
    st = ss_np(-0.014, -0.026, z) * ss_np(-0.125, -0.100, z) * ss_np(ny - 0.125, ny - 0.085, y)
    lips = np.exp(-((z + 0.040) / 0.0075) ** 2) * np.exp(-(x / 0.021) ** 2)
    st = st * (1 - lips)
    st = np.maximum(st, np.exp(-((z + 0.030) / 0.005) ** 2) * np.exp(-(x / 0.022) ** 2) * 0.8 * (1 - lips))
    d = me.attributes['det2']; v = np.zeros(len(me.vertices)); d.data.foreach_get('value', v)
    v = v - 0.30 * st
    d.data.foreach_set('value', v)
    print('[mod_rifle] stubble on', int((st > 0.5).sum()), 'verts; nose', round(ny, 3), round(nz, 3), flush=True)

def glove(o, hi):
    me = o.data; me.update()
    n = len(me.vertices)
    P = np.zeros(n * 3); me.vertices.foreach_get('co', P)
    N = np.zeros(n * 3); me.vertices.foreach_get('normal', N)
    P = P + N * (0.0012 if hi else 0.0016)
    me.vertices.foreach_set('co', P); me.update()
    set_slot(o, 'cuff')
    a = me.attributes['albm']; a.data.foreach_set('value', [0.0] * len(me.polygons))

# ------------------------------------------------------------------ uniform details: collar, boot tops, knee pads
def collar(tree, hi=False):
    n = 96 if hi else 18
    rings_ = []
    for zz, off in ((COLLAR_Z + 0.008, 0.002), (COLLAR_Z - 0.004, 0.006), (COLLAR_Z - 0.028, 0.008)):
        rr = []
        for j in range(n):
            a = 2 * math.pi * j / n; d = V(math.cos(a), math.sin(a), 0)
            h = tree.ray_cast(V(0, 0.02, zz) + d * 0.3, -d)
            r = ((V(h[0].x, h[0].y, 0) - V(0, 0.02, 0)).length if h[0] is not None else 0.065) + 0.004 + off
            fr = math.exp(-(math.atan2(math.cos(a), math.sin(a)) / 0.18) ** 2)   # zip opening at the throat
            rr.append(V(math.cos(a) * r, 0.020 + math.sin(a) * r, zz - 0.022 * fr * (zz - COLLAR_Z + 0.03) / 0.04))
        rings_.append(rr)
    rings_.append([V(p.x * 0.95, 0.02 + (p.y - 0.02) * 0.95, p.z) for p in rings_[-1]])
    return [V3P.orient_out(grid_sweep('mcoll', rings_, closed_u=True, cap0=False, cap1=False, slot='coat'))]

def boot_tops(tree, hi=False):
    out = V3P.leg_hems(tree, lambda x, y: BOOT_TOP + 0.012 * max(0.0, -y) / 0.06, hi, z0=BOOT_TOP - 0.01, slot='boot',
                       depth=0.028, off=0.0050)
    for o in out: o.name = 'mboot' + o.name[3:]
    return out

def knee_pads(tree, hi=False):
    out = []
    for s in (1, -1):
        h = V3P.surf(tree, (s * 0.095, 0.5, 0.505), (0, -1, 0), 0.010)
        if not h: continue
        c, nrm = h
        nrm = V(nrm.x, nrm.y, 0).normalized()
        rot = nrm.to_track_quat('Y', 'Z').to_matrix()
        out.append(superellipsoid('mknee' + ('R' if s > 0 else 'L'), c, (0.050, 0.014, 0.062), e=(2.6, 2.6), n=(14, 10) if hi else (7, 4),
                                  rot=rot, slot='stock'))
        out += [V3P.hem_band(tree, (s * 0.095, 0.0, zz + 0.02), lambda x, y, zz=zz: zz, hi, depth=0.020, off=0.0040,
                             name='mknee.s' + ('R' if s > 0 else 'L') + str(k), slot='stock', n=48 if hi else 10)
                for k, zz in enumerate((0.565, 0.455))]
    return out

# ------------------------------------------------------------------ plate carrier + pouches + pack + belt
_PC = {}

def _plates(tree):
    if _PC: return _PC
    fy, by = -9.0, 9.0
    for x in np.linspace(-0.11, 0.11, 9):
        for z in np.linspace(1.16, 1.44, 8):
            h = tree.ray_cast(V(x, 0.5, z), V(0, -1, 0))
            if h[0] is not None: fy = max(fy, h[0].y)
            h = tree.ray_cast(V(x, -0.5, z), V(0, 1, 0))
            if h[0] is not None: by = min(by, h[0].y)
    _PC.update(fy=fy, by=by)
    print('[mod_rifle] plate carrier front y', round(fy, 3), 'back y', round(by, 3), flush=True)
    return _PC

def carrier(tree, hi=False):
    pc = _plates(tree)
    fy, by = pc['fy'], pc['by']
    out = []
    tilt = Matrix.Rotation(math.radians(-4), 3, 'X')
    out.append(superellipsoid('mcarr.f', V(0, fy + 0.020, 1.305), (0.128, 0.019, 0.155), e=(4.0, 4.0), n=(18, 12) if hi else (8, 5),
                              rot=tilt, slot='cartbox'))
    out.append(superellipsoid('mcarr.b', V(0, by - 0.020, 1.305), (0.130, 0.019, 0.160), e=(4.0, 4.0), n=(18, 12) if hi else (8, 5),
                              rot=Matrix.Rotation(math.radians(4), 3, 'X'), slot='cartbox'))
    # cummerbund round the waist under the plates
    out.append(V3P.hem_band(tree, (0.0, 0.0, 1.215), lambda x, y: 1.215, hi, depth=0.105, off=0.012, name='mcb', slot='cartbox',
                            n=120 if hi else 20))
    # shoulder straps: front plate top over the shoulder to the back plate top
    for s in (1, -1):
        pn = []
        nf = 6 if hi else 2
        for i in range(nf + 1):
            z = lerp(1.43, 1.50, i / nf)
            h = V3P.surf(tree, (s * 0.098, 0.5, z), (0, -1, 0), 0.010)
            if h: pn.append(h)
        for i in range(1, (8 if hi else 3)):
            yy = lerp(0.06, -0.08, i / (8 if hi else 3))
            h = V3P.surf(tree, (s * 0.105, yy, 1.9), (0, 0, -1), 0.010)
            if h: pn.append(h)
        for i in range(nf + 1):
            z = lerp(1.50, 1.43, i / nf)
            h = V3P.surf(tree, (s * 0.098, -0.5, z), (0, 1, 0), 0.010)
            if h: pn.append(h)
        if len(pn) > 2: out.append(V3P.ribbon('mstrap' + ('R' if s > 0 else 'L'), pn, 0.050, hi, th=0.007, slot='cartbox'))
    # magazine pouches (three, flap tops) + radio pouch with an antenna stub
    for k, x in enumerate((-0.068, 0.0, 0.068)):
        c = V(x, fy + 0.058, 1.215)
        out.append(superellipsoid('mmag', c, (0.031, 0.020, 0.058), e=(3.4, 3.4), n=(12, 8) if hi else (6, 3), rot=tilt, slot='knapsack'))
        out.append(superellipsoid('mmag.f', c + V(0, 0.004, 0.052), (0.032, 0.023, 0.012), e=(3.5, 3), n=(10, 4) if hi else (5, 2),
                                  rot=tilt, slot='knapsack'))
    c = V(-0.085, fy + 0.052, 1.395)
    out.append(superellipsoid('mradio', c, (0.028, 0.018, 0.045), e=(3.2, 3.2), n=(10, 6) if hi else (5, 3), slot='knapsack'))
    out.append(limb('mradio.a', [(0, c + V(-0.010, -0.004, 0.040)), (1, c + V(-0.022, -0.012, 0.150))],
                    [(0, 0.0045, 0.0045, 0.0045), (1, 0.003, 0.003, 0.003)], 2 if hi else 1, 6 if hi else 3, slot='stock'))
    return out

def assault_pack(tree, hi=False):
    by = _plates(tree)['by']
    c = V(0, by - 0.039 - 0.065, 1.285)
    out = [superellipsoid('mpack', c, (0.135, 0.065, 0.165), e=(3.0, 3.0), n=(16, 10) if hi else (8, 4), slot='knapsack')]
    out.append(superellipsoid('mpack.p', c + V(0, -0.060, -0.040), (0.105, 0.022, 0.080), e=(3.2, 3.0), n=(12, 6) if hi else (5, 2),
                              slot='knapsack'))
    for sx in (-0.11, 0.11):
        out.append(limb('mpack.st', [(0, c + V(sx, -0.050, 0.150)), (1, c + V(sx, -0.068, -0.120))], [(0, 0.011, 0.0022, 0.0022)],
                        2, 4, fwd=V(0, -1, 0), slot='belt'))
    return out

def belt(tree, hi=False):
    out = [V3P.hem_band(tree, (0.0, 0.0, BELT_Z - 0.01), lambda x, y: BELT_Z, hi, depth=0.042, off=0.0090, name='mbelt',
                        slot='belt', n=120 if hi else 20)]
    fr = V3P.surf(tree, (0.0, 0.5, BELT_Z - 0.021), (0, -1, 0), 0.011)
    c = fr[0] if fr else V(0, 0.135, BELT_Z - 0.021)
    out.append(superellipsoid('mbelt.b', c + V(0, 0.002, 0), (0.026, 0.005, 0.022), e=(3, 3), n=(10, 6) if hi else (5, 2), slot='metal'))
    return out

# ------------------------------------------------------------------ kevlar helmet (fitted round the hi MakeHuman head)
HAT_B = V(0.0, 0.004, 1.742)
HAT_R = Matrix.Rotation(math.radians(5), 3, 'X')
_FIT = {}

def _fit_ring(htree, nu, dzs):
    rs = []
    for j in range(nu):
        a = 2 * math.pi * j / nu; d = HAT_R @ V(math.cos(a), math.sin(a), 0)
        best = None
        for dz in dzs:
            o = HAT_B + HAT_R @ V(0, 0, dz)
            h = htree.ray_cast(o + d * 0.3, -d)
            if h[0] is not None:
                r = (h[0] - o).dot(d); best = r if best is None else max(best, r)
        rs.append(best if best is not None else 0.08)
    return rs

def fit(htree):
    _FIT['tree'] = htree
    hb = [r + 0.012 for r in _fit_ring(htree, 96, (0.0, -0.012, 0.012, 0.025))]
    _FIT['band_hi'] = hb
    _FIT['band_lo'] = [max(hb[(j * 96 // 20 + k) % 96] for k in range(-3, 4)) + 0.002 for j in range(20)]
    print('[mod_rifle] helmet band r', round(min(hb), 3), round(max(hb), 3), flush=True)

def helmet(hi=False):
    nu = 96 if hi else 20
    rb = _FIT['band_hi' if hi else 'band_lo']
    L = lambda r, a, h: HAT_B + HAT_R @ V(math.cos(a) * r, math.sin(a) * r, h)
    A = lambda j: 2 * math.pi * j / nu
    out = []
    crown_h, dome = 0.105, 0.72
    rows = []
    for k in ([0.0, 0.25, 0.5, 0.7, 0.85, 0.95] if hi else [0.0, 0.5, 0.85]):
        g = math.sqrt(max(0.0, 1 - k ** 2)) if k > 0 else 1.0
        g = lerp(1.0, g, dome)
        rows.append([L(rb[j] * g, A(j), crown_h * k) for j in range(nu)])
    # skirt: brow lip at the front, ear cover at the sides, neck guard at the back (cleared from the head below the band)
    drops = (1.0, 0.66, 0.33) if hi else (1.0, 0.45)
    skirt = []
    for t in drops:
        r_ = []
        for j in range(nu):
            a = A(j); front = max(0.0, math.sin(a)) ** 1.5
            drop = lerp(0.068, 0.020, front) * t
            r_.append((a, drop, rb[j] + 0.004 + 0.010 * t ** 1.5 * (1 - front)))
        skirt.append(r_)
    tree = _FIT['tree']
    rows_sk = []
    for r_ in skirt:
        row = []
        for j, (a, drop, rr) in enumerate(r_):
            d = HAT_R @ V(math.cos(a), math.sin(a), 0); o = HAT_B + HAT_R @ V(0, 0, -drop)
            h = tree.ray_cast(o + d * 0.3, -d)
            if h[0] is not None: rr = max(rr, (h[0] - o).dot(d) + 0.010)
            row.append(L(rr, a, -drop))
        rows_sk.append(row)
    rows = rows_sk + rows
    o = grid_sweep('mhelm', rows, closed_u=True, cap0=False, cap1=True, slot='coat')
    out.append(V3P.orient_out(o))
    rim = rows[0]
    out.append(limb('mhelm.rim', [(j / nu, rim[j % nu]) for j in range(nu + 1)], [(0, 0.0045, 0.0045, 0.0045)], nu, 6 if hi else 3,
                    fwd=V(0, 0, 1), slot='coat'))
    # elastic band round the cover
    k = 0.30
    g = lerp(1.0, math.sqrt(1 - k ** 2), dome)
    band = [L(rb[j] * g + 0.0035, A(j), crown_h * k) for j in range(nu)]
    out.append(limb('mhelm.band', [(j / nu, band[j % nu]) for j in range(nu + 1)], [(0, 0.004, 0.009, 0.009)], nu, 4,
                    fwd=V(0, 0, 1), slot='roll'))
    # NVG mount (shroud plate + bracket) above the brow
    jf = nu // 4
    c = L(rb[jf] * lerp(1.0, math.sqrt(1 - 0.30 ** 2), dome) + 0.012, math.pi / 2, crown_h * 0.25)
    out.append(superellipsoid('mhelm.nvg', c, (0.026, 0.010, 0.030), e=(3.2, 3.2), n=(10, 6) if hi else (5, 2), rot=HAT_R, slot='stock'))
    out.append(superellipsoid('mhelm.nvgb', c + HAT_R @ V(0, 0.010, -0.012), (0.018, 0.010, 0.012), e=(3, 3), n=(8, 4) if hi else (4, 2),
                              rot=HAT_R, slot='stock'))
    return out

def chin_strap(hi=False):
    rb = _FIT['band_hi']; nu = len(rb)
    pts = []
    n = 14 if hi else 5
    for k in range(n + 1):
        t = k / n; a = math.pi * t
        x = math.cos(a) * lerp(rb[0], rb[nu // 2], t) * 0.90
        z = HAT_B.z - 0.050 - 0.112 * math.sin(a) ** 0.7
        y = 0.022 + 0.052 * math.sin(a) ** 2
        pts.append((t, V(x, y, z)))
    return [limb('mhelm.strap', pts, [(0, 0.0025, 0.008, 0.008)], n, 4, fwd=V(0, 1, 0), slot='belt')]

# ------------------------------------------------------------------ assault rifle (prop frame: barrel along +y)
def rifle(hi=False):
    T = lambda p: R.REST['prop'] @ V(p)
    rot3 = R.REST['prop'].to_3x3()
    up = rot3 @ V(0, 0, 1); side = rot3 @ V(1, 0, 0); fwd = rot3 @ V(0, 1, 0)
    nu = 12 if hi else 6
    stock = [(-0.300, 0.020, -0.075, 0.030), (-0.290, 0.021, -0.072, 0.031), (-0.200, 0.018, -0.052, 0.028), (-0.100, 0.015, -0.026, 0.024),
             (-0.060, 0.015, -0.018, 0.024)]
    secs = [ring(T((0, y, (zb + zt) / 2)), side, up, hw, (zt - zb) / 2, (zt - zb) / 2, nu, 3.0) for y, hw, zb, zt in stock]
    out = [grid_sweep('mstock', secs, slot='stock')]
    out.append(superellipsoid('mrec', T((0, 0.040, 0.008)), (0.016, 0.105, 0.026), e=(3.5, 3.5), n=(12, 8) if hi else (6, 3), rot=rot3,
                              slot='steel'))
    out.append(limb('mgrip', [(0, T((0, -0.005, -0.012))), (1, T((0, -0.030, -0.090)))], [(0, 0.012, 0.016, 0.016)], 2 if hi else 1,
                    8 if hi else 4, fwd=fwd, slot='stock', e=2.6))
    out.append(limb('mgrip.tg', [(0, T((0, 0.000, -0.018))), (0.5, T((0, 0.030, -0.040))), (1, T((0, 0.058, -0.020)))],
                    [(0, 0.003, 0.003, 0.003)], 4 if hi else 2, 4, fwd=side, slot='steel'))
    out.append(limb('mrmag', [(0, T((0, 0.075, -0.012))), (0.5, T((0, 0.083, -0.085))), (1, T((0, 0.108, -0.160)))],
                    [(0, 0.012, 0.030, 0.030), (1, 0.012, 0.028, 0.028)], 6 if hi else 2, 8 if hi else 4, fwd=fwd, slot='steel', e=3.2))
    out.append(limb('mhg', [(0, T((0, 0.150, 0.006))), (1, T((0, 0.400, 0.006)))], [(0, 0.024, 0.024, 0.024), (1, 0.021, 0.021, 0.021)],
                    6 if hi else 2, 12 if hi else 6, fwd=up, slot='stock'))
    out.append(limb('mbarrel', [(0, T((0, 0.395, 0.010))), (1, T((0, 0.600, 0.012)))], [(0, 0.008, 0.008, 0.008)], 2 if hi else 1,
                    8 if hi else 4, fwd=up, slot='steel'))
    out.append(limb('mbarrel.fs', [(0, T((0, 0.430, 0.012))), (1, T((0, 0.430, 0.068)))], [(0, 0.006, 0.010, 0.010), (1, 0.004, 0.006, 0.006)],
                    2 if hi else 1, 6 if hi else 4, fwd=fwd, slot='steel'))   # front sight post
    out.append(limb('mfh', [(0, T((0, 0.590, 0.012))), (1, T((0, 0.635, 0.012)))], [(0, 0.011, 0.011, 0.011)], 2 if hi else 1,
                    8 if hi else 4, fwd=up, slot='steel'))
    out.append(limb('moptic', [(0, T((0, -0.010, 0.070))), (0.2, T((0, 0.010, 0.070))), (1, T((0, 0.120, 0.070)))],
                    [(0, 0.019, 0.019, 0.019), (0.2, 0.016, 0.016, 0.016), (1, 0.021, 0.021, 0.021)], 6 if hi else 2, 12 if hi else 6,
                    fwd=up, slot='stock'))
    out.append(superellipsoid('moptic.m', T((0, 0.055, 0.044)), (0.012, 0.040, 0.012), e=(3, 3), n=(8, 4) if hi else (4, 2), rot=rot3,
                              slot='stock'))
    sl = [T((0.0, 0.380, -0.025)), T((0.0, 0.200, -0.070)), T((0.0, -0.020, -0.100)), T((0.0, -0.270, -0.080))]
    secs = [[p + side * 0.003 + up * 0.010, p - side * 0.003 + up * 0.010, p - side * 0.003 - up * 0.010, p + side * 0.003 - up * 0.010]
            for p in sl]
    out.append(grid_sweep('msling', secs, slot='belt'))
    return out

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi:
        stubble(head)
    for o in parts:
        if o.name.startswith('mhhand'): glove(o, hi)
    if hi or not _FIT:
        fit(C.surface_tools([head]))
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'coat'); parts.append(cb)
    parts += collar(body_tree, hi) + boot_tops(body_tree, hi) + knee_pads(body_tree, hi)
    parts += belt(body_tree, hi) + carrier(body_tree, hi) + assault_pack(body_tree, hi)
    parts += helmet(hi) + chin_strap(hi) + rifle(hi)
    return parts
C.build_kit = build_kit
