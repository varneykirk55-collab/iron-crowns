"""Eras v3 kit 3: French hussar trooper (5e-style light cavalry, c.1806-1812) mounted, sabre drawn
(docs/char/ERAS_PROGRESS.md). Patches char_v2 (loaded by char_v2_build.py when V3_KIT=kit_c19_hussar).

Rider: the v3 human (MakeHuman head / hands / skin, v3 body shell) built standing like every v3 kit, then seated on
the EXISTING cavalry rig by v3_rider.py (Kirk 17:11: Rob's horse + rider bones and clips untouched; no re-rig).
Every garment / item is built fresh here:
  * dolman (team colour) with red collar + pointed red cuffs, 15 rows of yellow lace frogging across the chest with
    3 rows of half-ball buttons, yellow back-seam braid ending in trefoils, Hungarian knots above the cuffs
  * barrel sash (red, yellow barrels) round the waist, knotted on the left hip
  * pelisse (team colour, black fur trim) slung on the left shoulder, empty sleeve, yellow cord across the chest
  * dark blue Hungarian breeches with yellow thigh knots + side stripes; Hessian boots with yellow trim + tassel, spurs
  * shako (black felt) with peak, yellow cords, cockade, tall plume; cadenettes, queue, moustache
  * light cavalry sabre (brass stirrup hilt) in the right fist; empty steel scabbard + sabretache on slings
Horse (bay, black points, built HOFF away so bake / AO never mix with the rider): fused body / neck / head / legs,
mane (right side) + tail; Hungarian saddle under a sheepskin with red wolf-tooth edge; shabraque with pointed rear
tails and yellow wolf-tooth lace edge; red valise, girth, breastplate, bridle + bit, reins (to the left fist), stirrups + leathers."""
import math, bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector
import char_v2 as C
import human_mh as HM, v3_parts as V3P
def RB(name, pn, w, hi=False, **kw):
    return [V3P.ribbon(name, pn, w, hi, **kw)] if len(pn) >= 2 else []
from char_v2 import V, ss, lerp, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_c19_hussar'
C.CLIP_STYLE = 'musket'   # unused (cavalry clips), kept for the shared code paths
HOFF = V(0, -6.0, 0)
C.RIDER = dict(variant='c19_hussar', hoff=tuple(HOFF), tail='hztail',
               rigid={'hzeye': 'head', 'hzbrid': 'head', 'hzbit': 'head', 'hzshab': 'body', 'hzsheep': 'body', 'hzval': 'body',
                      'hzgirth': 'body', 'hzedge': 'body', 'hzsedge': 'body', 'hzbreast': 'body', 'hzstir': 'body', 'hzleath': 'body'},
               rein=('hzrein',), tip=(0.2065, 0.0, 0.79))   # tip overwritten below (sabre point)
C.SLOT_MAT.update({'gold': 'wool', 'fur': 'fur', 'sponge': 'fur', 'felt': 'leather', 'boot': 'leather', 'cartbox': 'leather',
                   'scabbard': 'steel', 'sash': 'wool', 'turnback': 'wool', 'knapsack': 'hair'})   # horse coat: matte with a soft sheen + per-instance shade (bay / dark bay / brown)
C.BODY_TRIS = 2500
C.MH_LO = {'mhhead': 1650, 'mhhandR': 620, 'mhhandL': 580}
C.HEAD_BOX = (0.15, -0.15, 0.17, 2.02)
C.HAND_BOX_Y = 0.15
C.AO_AWAY_KEYS = ('hsab',)
C.UV_SCALES = [(lambda co: co.y < -3.0, (0.0, -6.0, 1.0), 0.62)]   # horse + tack: less texel density than the rider
C.KIT_PAL = {'knapsack': '#4a2b17', 'hair': '#17110c', 'gold': '#d9b648', 'breeches': '#283255', 'sponge': '#e6dfcf',
             'plume': '#1d1b1a'}
C.KIT_RULES = [(('hshako', 'hpeak', 'hplume', 'hcord', 'hcock', 'hhair'), 'head'), (('hlace', 'hknot', 'hsash', 'hstripe', 'hbtrim'), 'transfer'), (('hpel', 'hpcord'), 'transfer_torso'),
               (('hsab',), 'hand.R'),
               (('hbtasR', 'hspurR'), 'foot.R'), (('hbtasL', 'hspurL'), 'foot.L'),
               (('hz',), 'own')]

HM.FIST['.R'] = 0.014   # sabre grip
HM.FIST['.L'] = 0.014   # rein hand: relaxed fist (reins pass through it)

BOOT_FRONT, BOOT_BACK = 0.530, 0.470
COLLAR_TOP = 1.556

def _leg_c(z, s):
    return V(s * 0.10, 0.0, z)

def boot_top(x, y):
    """Hessian boot top: higher in front with a heart notch at the centre front."""
    s = 1 if x > 0 else -1
    a = math.atan2(y, abs(x) - 0.10)   # 0 = outside, pi/2 = front
    f = 0.5 + 0.5 * math.sin(a)        # 1 front, 0 back
    z = lerp(BOOT_BACK, BOOT_FRONT, f ** 1.5)
    d = math.degrees(abs(a - math.pi / 2))
    z -= 0.020 * math.exp(-(d / 9.0) ** 2)
    return z

def _cuff_top(x, y, z, s):
    t = (1.14 - z) / 0.245
    xc = s * (0.205 + 0.017 * t); yc = -0.012 + 0.012 * t
    phi = math.atan2(y - yc, s * (x - xc))   # 0 = outside of the forearm
    return 0.962 + 0.07 * max(0.0, 1.0 - abs(phi) / 1.25)

def body_slot(p, part):
    x, y, z = p; ax = abs(x)
    if part == 'shoe': return 'boot'
    if part == 'collar': return 'collar'
    if part == 'arm':
        s = 1 if x > 0 else -1
        return 'cuff' if z < _cuff_top(x, y, z, s) - 0.004 else 'coat'
    if part == 'leg':
        return 'boot' if z < boot_top(x, y) - 0.004 else 'breeches'
    if z > 1.586: return 'skin'
    if z > 1.53: return 'stock'
    if z < 0.955: return 'breeches'   # dolman ends at the waist, under the sash band (0.935 - 1.015)
    return 'coat'
C.body_slot = body_slot

# ------------------------------------------------------------------ dolman lace, knots, buttons
def lace(tree, hi):
    out = []
    S = lambda o, d, off=0.0028: V3P.surf(tree, o, d, off)
    for i in range(15):
        z = lerp(1.425, 1.035, i / 14)
        w = lerp(0.108, 0.062, (1.425 - z) / 0.39)
        nseg = 18 if hi else 6
        pn = []
        for k in range(nseg + 1):
            x = lerp(-w, w, k / nseg)
            r = S(V(x, 0.0, z), V(0, 1, 0))
            if r: pn.append(r)
        if len(pn) > 2: out += RB('hlace.f%d' % i, pn, 0.0095, hi, slot='gold')
        if hi:   # loops at the ends, buttons in 3 rows (centre + both sides)
            for x in (-w, w):
                r = S(V(x, 0.0, z), V(0, 1, 0), 0.0035)
                if r: out.append(superellipsoid('hlace.end', r[0], (0.009, 0.009, 0.006), e=(2, 2), n=(12, 6),
                                                rot=r[1].to_track_quat('Z', 'Y').to_matrix(), slot='gold'))
            for x in (0.0, -0.66 * w, 0.66 * w):
                r = S(V(x, 0.0, z), V(0, 1, 0), 0.0055)
                if r: out.append(superellipsoid('button', r[0], (0.0062, 0.0062, 0.0050), e=(2, 2), n=(14, 7),
                                                rot=r[1].to_track_quat('Z', 'Y').to_matrix(), slot='button'))
    # back seams: two braids from the shoulder blades curving in to the waist, trefoil at the bottom
    for s in (1, -1):
        nseg = 20 if hi else 8
        pn = []
        for k in range(nseg + 1):
            t = k / nseg; z = lerp(1.40, 1.03, t); x = s * lerp(0.105, 0.030, t ** 0.8)
            r = S(V(x, 0.0, z), V(0, -1, 0))
            if r: pn.append(r)
        out += RB('hlace.b', pn, 0.009, hi, slot='gold')
        if hi:
            for dx, dz in ((0.0, -0.018), (s * 0.016, -0.004), (-s * 0.012, -0.002)):
                r = S(V(s * 0.030 + dx, 0.0, 1.03 + dz), V(0, -1, 0), 0.0035)
                if r: out.append(superellipsoid('hlace.tre', r[0], (0.010, 0.010, 0.004), e=(2, 2), n=(12, 6),
                                                rot=r[1].to_track_quat('Z', 'Y').to_matrix(), slot='gold'))
    # pointed cuff edge braid (band) + Hungarian knot above the point
    for s in (1, -1):
        c0 = (s * 0.218, -0.004, 0.99)
        out.append(V3P.hem_band(tree, c0, lambda x, y, s=s: _cuff_top(x, y, 0.99, s) + 0.002, hi, depth=0.009, off=0.0026,
                                name='hlace.cuff', slot='gold', n=None if hi else 20))
        nseg = 24 if hi else 10
        pn = []
        for k in range(nseg + 1):   # knot: an arch up from the cuff point with two curled ends (Austrian knot)
            a = math.pi * k / nseg
            t = (1.14 - 1.07) / 0.245; xc = s * (0.205 + 0.017 * t); yc = -0.012 + 0.012 * t
            u = math.cos(a) * 0.022; z = 1.040 + math.sin(a) * 0.045
            d = V(s, 0.0, 0.0); f = V(0, 1, 0)
            o = V(xc, yc, z)
            r = S(o, (d + f * (u / 0.022) * 0.9).normalized())
            if r: pn.append(r)
        out += RB('hknot.c', pn, 0.0075, hi, slot='gold')
    return out

def breeches_trim(tree, hi):
    out = []
    S = lambda o, d, off=0.0028: V3P.surf(tree, o, d, off)
    for s in (1, -1):
        nseg = 26 if hi else 10
        pn = []
        for k in range(nseg + 1):   # Hungarian thigh knot: spearhead arch from the fly, curling ends
            t = k / nseg
            x = s * (0.035 + 0.075 * math.sin(math.pi * t * 0.9))
            z = 0.925 - 0.105 * math.sin(math.pi * min(1.0, t * 1.1)) ** 0.7 + 0.03 * t
            r = S(V(x, -0.03, z), V(0, 1, 0))
            if r: pn.append(r)
        out += RB('hknot.t', pn, 0.0085, hi, slot='gold')
        nseg = 18 if hi else 7
        pn = []
        for k in range(nseg + 1):   # outer side stripe, waist to boot top
            z = lerp(0.925, BOOT_BACK + 0.012, k / nseg)
            r = S(_leg_c(z, s), V(s, -0.15, 0))
            if r: pn.append(r)
        out += RB('hstripe', pn, 0.011, hi, slot='gold')
    return out

def boots(tree, hi):
    out = []
    for s, sd in ((1, 'R'), (-1, 'L')):
        out.append(V3P.hem_band(tree, (s * 0.10, 0.0, 0.50), boot_top, hi, depth=0.011, off=0.0030, name='hbtrim.' + sd,
                                slot='gold', n=None if hi else 24))
        r = V3P.surf(tree, V(s * 0.10, 0.0, boot_top(s * 0.10, 0.05) - 0.02), V(0, 1, 0), 0.006)
        if r:
            p = r[0]
            out.append(limb('hbtas' + sd, [(0, p + V(0, 0, 0.006)), (1, p + V(0, 0.004, -0.035))],
                            [(0, 0.004, 0.004, 0.004), (0.4, 0.006, 0.006, 0.006), (1, 0.009, 0.009, 0.009)],
                            6 if hi else 2, 8 if hi else 4, fwd=V(1, 0, 0), slot='gold'))
        # spur: neck + rowel at the heel, strap round the ankle
        heel = V(s * 0.10, -0.075, 0.045)
        out.append(limb('hspur' + sd, [(0, heel + V(0, 0.01, 0)), (1, heel + V(0, -0.035, 0.002))],
                        [(0, 0.004, 0.004, 0.004)], 3 if hi else 1, 6 if hi else 4, fwd=V(0, 0, 1), slot='steel'))
        out.append(superellipsoid('hspur' + sd + '.row', heel + V(0, -0.040, 0.002), (0.0025, 0.012, 0.012), e=(2, 2),
                                  n=(12, 6) if hi else (6, 3), slot='steel'))
    return out

# ------------------------------------------------------------------ sash
def sash(tree, hi):
    out = [V3P.hem_band(tree, (0.0, 0.0, 1.015), lambda x, y: 1.015, hi, depth=0.080, off=0.0085, name='hsash', slot='sash',
                        n=None if hi else 32)]
    if hi:   # barrels: three rows of knots round the band
        for z in (0.952, 0.975, 0.998):
            for j in range(36):
                a = 2 * math.pi * (j + 0.5 * (z > 0.97 and z < 0.98)) / 36
                d = V(math.cos(a), math.sin(a), 0)
                r = V3P.surf(tree, V(0, 0, z), d, 0.0105)
                if r: out.append(superellipsoid('hsash.bar', r[0], (0.0075, 0.0075, 0.0045), e=(2, 2), n=(10, 6),
                                                rot=r[1].to_track_quat('Z', 'X').to_matrix(), slot='gold'))
    r = V3P.surf(tree, V(0, 0, 0.975), V(-1, 0.25, 0), 0.010)
    if r:
        p, n = r
        out.append(superellipsoid('hsashk', p + n * 0.008, (0.020, 0.018, 0.020), e=(2, 2), n=(12, 8) if hi else (6, 4), slot='sash'))
        for k, dy in enumerate((0.012, -0.012)):
            a = p + n * 0.012 + V(0, dy, -0.012)
            out.append(limb('hsashk.c', [(0, a), (1, a + n * 0.010 + V(0, dy * 0.5, -0.060))],
                            [(0, 0.005, 0.005, 0.005), (0.7, 0.005, 0.005, 0.005), (1, 0.010, 0.010, 0.010)],
                            6 if hi else 2, 8 if hi else 4, fwd=V(0, 1, 0), slot='gold'))
    return out

# ------------------------------------------------------------------ pelisse (slung on the left shoulder)
PEL_A0, PEL_A1 = 196.0, 318.0
PEL_Z0, PEL_Z1 = 0.985, 1.44

def pelisse(tree, hi):
    na, nz = (60, 70) if hi else (12, 7)
    cols = []
    for j in range(na + 1):
        a = math.radians(lerp(PEL_A0, PEL_A1, j / na)); d = V(math.cos(a), math.sin(a), 0)
        col = []; rmax = 0.0; k0 = 0.0
        for i in range(nz + 1):
            z = lerp(PEL_Z1, PEL_Z0, i / nz)
            # top edge drapes over the left shoulder, lower toward the right shoulder blade
            ztop = lerp(1.44, 1.36, ss(210, 315, math.degrees(a)))
            zz = min(z, ztop) if i == 0 else lerp(ztop, PEL_Z0, i / nz)
            h = tree.ray_cast(V(0, -0.01, zz), d)
            r = (V(h[0].x, h[0].y, 0).length if h[0] is not None else 0.17)
            rmax = max(r, rmax - 0.35 * (ztop - PEL_Z0) / nz * (1.0 - k0)) if i else r   # hangs off the shoulder blades, eases in toward the waist (per metre, not per row)
            k = (ztop - zz) / max(1e-3, ztop - PEL_Z0); k0 = ss(0.55, 1.0, k)
            off = 0.014 + 0.022 * k * k
            rr = rmax + off
            col.append(V(d.x * rr, -0.01 + d.y * rr, zz))
        cols.append(col)
    rows = [[cols[j][i] for j in range(na + 1)] for i in range(nz + 1)]
    out = []
    if hi:   # thickness + soft vertical folds
        def fold(p, j):
            a = j / na
            return p + V(p.x, p.y + 0.01, 0).normalized() * 0.004 * math.sin(a * math.pi * 9)
        outer = [[fold(p, j) for j, p in enumerate(r)] for r in rows]
        o = grid_sweep('hpel', outer, closed_u=False, cap0=False, cap1=False, slot='coat')
    else:
        o = grid_sweep('hpel', rows, closed_u=False, cap0=False, cap1=False, slot='coat')
    out.append(o)
    # fur trim rolls: bottom hem, front (left) edge, top / collar
    def roll(name, pts, r):
        return limb(name, [(k / (len(pts) - 1), p) for k, p in enumerate(pts)], [(0, r, r, r)], (len(pts) - 1) * (3 if hi else 1),
                    10 if hi else 4, fwd=V(0, 0, 1), slot='fur')
    bot = [rows[-1][j] for j in range(0, na + 1, max(1, na // 12))]
    out.append(roll('hpel.fb', bot, 0.030))
    front = [cols[0][i] for i in range(0, nz + 1, max(1, nz // 8))]
    out.append(limb('hpel.ff', [(k / (len(front) - 1), p) for k, p in enumerate(front)], [(0, 0.026, 0.026, 0.026)],
                    (len(front) - 1) * (3 if hi else 1), 10 if hi else 4, fwd=V(1, 0, 0), slot='fur'))
    top = [rows[0][j] for j in range(0, na + 1, max(1, na // 10))]
    out.append(roll('hpel.ft', top, 0.026))
    # frogging: short yellow braids across the front panel (left side) + a column of buttons
    for i in range(6):
        z = lerp(1.34, 1.08, i / 5)
        ii = min(nz, max(1, round((rows[0][0].z - z) / max(1e-3, rows[0][0].z - PEL_Z0) * nz)))
        jn = max(2, na // 7)
        pn = [(cols[j][ii] + V(math.cos(math.radians(lerp(PEL_A0, PEL_A1, j / na))), math.sin(math.radians(lerp(PEL_A0, PEL_A1, j / na))), 0) * 0.004,
               V(math.cos(math.radians(lerp(PEL_A0, PEL_A1, j / na))), math.sin(math.radians(lerp(PEL_A0, PEL_A1, j / na))), 0))
              for j in range(1, jn + 1)]
        out += RB('hpcord.f', pn, 0.009, hi, th=0.004, slot='gold')
    # empty sleeve hanging down the back-left, fur cuff
    a0 = math.radians(214); d0 = V(math.cos(a0), math.sin(a0), 0)
    pa = cols[int(na * (214 - PEL_A0) / (PEL_A1 - PEL_A0))]
    top_p = pa[1] + d0 * 0.012; bot_p = pa[-2] + d0 * 0.016
    out.append(limb('hpel.sl', [(0, top_p), (0.5, (top_p + bot_p) / 2 + d0 * 0.012), (1, bot_p)],
                    [(0, 0.042, 0.012, 0.012), (0.8, 0.040, 0.011, 0.011), (1, 0.042, 0.012, 0.012)],
                    10 if hi else 4, 10 if hi else 6, fwd=d0, slot='coat'))
    out.append(limb('hpel.sc', [(0, bot_p + V(0, 0, 0.03)), (1, bot_p - V(0, 0, 0.012))], [(0, 0.046, 0.018, 0.018)],
                    2 if hi else 1, 10 if hi else 6, fwd=d0, slot='fur'))
    # pelisse cord: from the left shoulder front across the chest to under the right arm
    nseg = 24 if hi else 9
    pn = []
    for k in range(nseg + 1):
        t = k / nseg
        a = math.radians(lerp(200, 345, t)); z = lerp(1.42, 1.25, t) + 0.03 * math.sin(math.pi * t)
        r = V3P.surf(tree, V(0, 0, z) + V(math.cos(a), math.sin(a), 0) * 0.5, V(-math.cos(a), -math.sin(a), 0), 0.006)
        if r: pn.append(r)
    out += RB('hpcord', pn, 0.0065, hi, th=0.006, slot='gold')
    return out

# ------------------------------------------------------------------ shako, hair
SH_Z0, SH_Z1 = 1.700, 1.890
SH_BASE = V(0, 0.027, SH_Z0)
SH_TILT = Matrix.Rotation(math.radians(-4), 3, 'X')
def _shT(p): return SH_BASE + SH_TILT @ (p - SH_BASE)
def _shr(t): return lerp(0.086, 0.094, t), lerp(0.100, 0.107, t)

def shako(hi):
    ts = [i / 120 for i in range(121)] if hi else [0.0, 0.08, 0.5, 0.92, 1.0]
    nu = 180 if hi else 18
    secs = []
    for t in ts:
        rx, ry = _shr(t)
        bd = 0.0022 * (ss(0.0, 0.01, t) * ss(0.07, 0.06, t) + ss(0.92, 0.93, t))
        secs.append([_shT(p) for p in ring(V(0, SH_BASE.y, lerp(SH_Z0, SH_Z1, t)), V(1, 0, 0), V(0, 1, 0), rx + bd, ry + bd, ry + bd, nu, 2.0, 0.5)])
    out = [grid_sweep('hshako', secs, cap0=True, cap1=True, slot='felt')]
    npk = 12 if hi else 5; pk = []
    for j in range(npk + 1):
        a = math.pi * (0.12 + 0.76 * j / npk); c = V(math.cos(a), math.sin(a), 0)
        rx, ry = _shr(0.0)
        inner = V(rx * c.x, SH_BASE.y + ry * c.y, SH_Z0 + 0.004); outer = inner + V(c.x * 0.012, c.y * 0.055, -0.020)
        pk.append([_shT(inner), _shT(outer), _shT(outer + V(0, 0, 0.005)), _shT(inner + V(0, 0, 0.005))])
    out.append(grid_sweep('hpeak', pk, closed_u=True, cap0=True, cap1=True, slot='stock'))
    rx, ry = _shr(0.90)
    ck = _shT(V(0, SH_BASE.y + ry + 0.004, SH_Z0 + 0.90 * (SH_Z1 - SH_Z0)))
    out.append(superellipsoid('hcock', ck, (0.021, 0.006, 0.021), e=(2, 2), n=(16, 6) if hi else (12, 4), slot='collar'))
    # tall plume on the left front, out of a small brass socket
    p0 = _shT(V(-0.045, SH_BASE.y + 0.085, SH_Z1 - 0.01))
    out.append(limb('hplume', [(0, p0), (0.5, p0 + V(-0.004, -0.004, 0.12)), (1, p0 + V(-0.006, -0.012, 0.25))],
                    [(0, 0.008, 0.008, 0.008), (0.12, 0.020, 0.020, 0.020), (0.65, 0.018, 0.018, 0.018), (1, 0.003, 0.003, 0.003)],
                    20 if hi else 5, 14 if hi else 6, fwd=V(1, 0, 0), slot='plume'))
    # cords: two festoons across the front, raquettes + tassels down the right side
    for dz in (0.0, -0.025):
        nseg = 36 if hi else 7; path = []
        for k in range(nseg + 1):
            a = math.radians(-160 + 140 * k / nseg)
            t = 0.40 + dz / 0.19 - 0.13 * math.sin(math.pi * k / nseg)
            rx, ry = _shr(t)
            path.append((k / nseg, _shT(V(math.cos(a) * (rx + 0.0035), SH_BASE.y - math.sin(a) * (ry + 0.0035), SH_Z0 + t * (SH_Z1 - SH_Z0)))))
        out.append(limb('hcord', path, [(0, 0.0034, 0.0034, 0.0034)], 50 if hi else 7, 8 if hi else 4, fwd=V(0, 0, 1), slot='gold'))
    rs = path[-1][1]
    for k in range(2):
        a = rs + V(0.004, -0.014 * k, 0.0)
        out.append(limb('hcord.r', [(0, a), (0.6, a + V(0.008, -0.004, -0.08)), (1, a + V(0.010, -0.006, -0.13))],
                        [(0, 0.004, 0.004, 0.004), (0.55, 0.0045, 0.0045, 0.0045), (0.62, 0.012, 0.012, 0.012),
                         (0.8, 0.010, 0.010, 0.010), (0.85, 0.004, 0.004, 0.004), (1, 0.009, 0.009, 0.009)],
                        14 if hi else 4, 8 if hi else 4, fwd=V(0, 1, 0), slot='gold'))
    return out

def hair(htree, hi):
    out = []
    for s in (1, -1):   # cadenettes: thin braids in front of the ears down to the jaw
        pts = []
        for k in range(7):
            z = lerp(1.695, 1.565, k / 6)
            r = V3P.surf(htree, V(s * 0.25, 0.050 - 0.004 * k, z), V(-s, 0, 0), 0.006)
            if r: pts.append(r[0])
        if len(pts) > 2:
            out.append(limb('hhair.cad', [(k / (len(pts) - 1), p) for k, p in enumerate(pts)],
                            [(0, 0.0065, 0.0065, 0.0065), (0.9, 0.0055, 0.0055, 0.0055), (1, 0.0035, 0.0035, 0.0035)],
                            18 if hi else 4, 8 if hi else 4, fwd=V(0, 1, 0), slot='hair'))
    # queue: short clubbed pigtail at the nape
    r = V3P.surf(htree, V(0, -0.3, 1.66), V(0, 1, 0), 0.004)
    if r:
        p = r[0]
        out.append(limb('hhair.q', [(0, p + V(0, 0.004, 0.01)), (0.5, p + V(0, -0.012, -0.06)), (1, p + V(0, -0.018, -0.13))],
                        [(0, 0.010, 0.010, 0.010), (0.6, 0.011, 0.011, 0.011), (1, 0.007, 0.007, 0.007)],
                        14 if hi else 4, 10 if hi else 5, fwd=V(1, 0, 0), slot='hair'))
    # moustache (two tapered bars under the nose)
    for s in (1, -1):
        pts = []
        for k in range(6):
            x = s * lerp(0.002, 0.036, k / 5); z = 1.616 - 0.010 * (k / 5) ** 2
            r = V3P.surf(htree, V(x, 0.4, z), V(0, -1, 0), 0.0035)
            if r: pts.append(r[0])
        if len(pts) > 2:
            out.append(limb('hhair.m', [(k / (len(pts) - 1), p) for k, p in enumerate(pts)],
                            [(0, 0.0045, 0.0045, 0.0030), (0.4, 0.0050, 0.0055, 0.0030), (1, 0.0018, 0.0018, 0.0015)],
                            10 if hi else 3, 8 if hi else 4, fwd=V(0, 1, 0), slot='hair'))
    return out

# ------------------------------------------------------------------ sabre in the right fist
GRIP = V(0.2065, 0.0, 0.79)
BLADE_TILT = -20.0   # blade cocked down in the fist (+ v3_rider.WRIST_TILT) so it follows Rob's r_fore swing
_BT = Matrix.Rotation(math.radians(BLADE_TILT), 3, 'X')
def _sb(p): return GRIP + _BT @ (V(p) - GRIP)

def sabre(hi):
    out = []
    L0, L1 = 0.060, 0.86
    path = []
    n = 24 if hi else 8
    for k in range(n + 1):
        u = k / n; y = lerp(L0, L1, u)
        path.append((u, _sb(GRIP + V(0, y, 0.045 * u * u))))
    blade = limb('hsab.bl', path, [(0, 0.0035, 0.016, 0.004), (0.85, 0.0030, 0.013, 0.004), (1, 0.001, 0.002, 0.001)],
                 n, 8 if hi else 4, fwd=_BT @ V(0, 0, -1), slot='steel', e=2.0)
    out.append(blade)
    out.append(limb('hsab.gr', [(0, _sb(GRIP + V(0, -0.055, 0))), (1, _sb(GRIP + V(0, 0.052, 0)))],
                    [(0, 0.0125, 0.0125, 0.0125), (0.5, 0.0135, 0.0135, 0.0135), (1, 0.0120, 0.0120, 0.0120)],
                    6 if hi else 2, 10 if hi else 6, fwd=V(0, 0, 1), slot='cartbox'))
    out.append(superellipsoid('hsab.pm', _sb(GRIP + V(0, -0.062, 0.002)), (0.012, 0.012, 0.014), e=(2, 2), n=(10, 6) if hi else (6, 3), slot='metal'))
    out.append(superellipsoid('hsab.gd', _sb(GRIP + V(0, 0.058, -0.004)), (0.016, 0.008, 0.030), e=(2.5, 2.5), n=(12, 6) if hi else (6, 3), slot='metal'))
    # stirrup knuckle bow from the guard round under the fingers to the pommel
    bow = [(0, _sb(GRIP + V(0, 0.058, -0.030))), (0.5, _sb(GRIP + V(0, 0.0, -0.050))), (1, _sb(GRIP + V(0, -0.058, -0.012)))]
    out.append(limb('hsab.bw', bow, [(0, 0.0035, 0.0035, 0.0035)], 12 if hi else 4, 6 if hi else 3, fwd=V(1, 0, 0), slot='metal'))
    C.RIDER['tip'] = tuple(path[-1][1])
    return out

# ------------------------------------------------------------------ horse (horse coords; rider seat at y ~ -0.05)
BARREL = [(-0.70, 1.30, 1.05, 0.08), (-0.60, 1.36, 0.92, 0.20), (-0.45, 1.38, 0.86, 0.235), (-0.25, 1.35, 0.83, 0.245),
          (0.0, 1.33, 0.80, 0.255), (0.25, 1.38, 0.79, 0.245), (0.40, 1.46, 0.82, 0.225), (0.55, 1.40, 0.92, 0.20),
          (0.66, 1.30, 1.00, 0.15), (0.72, 1.20, 1.08, 0.08)]
HEAD0, HEAD1 = V(0, 0.90, 1.84), V(0, 1.36, 1.55)

def _head_axis(t): return HEAD0.lerp(HEAD1, t)

def horse_parts(hi):
    P = []
    y0, y1 = BARREL[0][0], BARREL[-1][0]
    tt = lambda y: (y - y0) / (y1 - y0)
    P.append(limb('b', [(tt(y), V(0, y, (a + b) / 2)) for y, a, b, w in BARREL], [(tt(y), w, (a - b) / 2, (a - b) / 2) for y, a, b, w in BARREL],
                  60 if hi else 24, 48 if hi else 24, fwd=V(0, 0, 1), e=2.2))
    for s in (1, -1):
        P.append(superellipsoid('hq', V(s * 0.135, -0.50, 1.13), (0.115, 0.23, 0.24), e=(2.2, 2.2), n=(32, 20) if hi else (16, 10)))
        P.append(superellipsoid('sh', V(s * 0.14, 0.43, 1.11), (0.10, 0.15, 0.25), e=(2.2, 2.2), n=(32, 20) if hi else (16, 10),
                                rot=Matrix.Rotation(math.radians(34), 3, 'X')))
    P.append(superellipsoid('br', V(0, 0.56, 1.03), (0.19, 0.12, 0.17), e=(2.2, 2.2), n=(32, 20) if hi else (16, 10)))
    P.append(limb('nk', [(0, V(0, 0.46, 1.26)), (0.5, V(0, 0.72, 1.525)), (1, V(0, 0.93, 1.75))],
                  [(0, 0.130, 0.21, 0.21), (0.5, 0.100, 0.170, 0.165), (1, 0.072, 0.118, 0.098)], 30 if hi else 14, 36 if hi else 18,
                  fwd=V(0, 1, -0.4), e=2.0))
    P.append(limb('hd', [(0, HEAD0), (1, HEAD1)],
                  [(0, 0.070, 0.10, 0.060), (0.12, 0.086, 0.16, 0.060), (0.30, 0.094, 0.13, 0.055), (0.55, 0.070, 0.075, 0.045),
                   (0.85, 0.060, 0.062, 0.045), (0.94, 0.063, 0.060, 0.050), (0.98, 0.052, 0.048, 0.040), (1.0, 0.020, 0.018, 0.014)],
                  40 if hi else 16, 36 if hi else 16, fwd=V(0, 0, -1), e=2.0))
    for s in (1, -1):
        P.append(limb('ear', [(0, V(s * 0.052, 0.885, 1.86)), (1, V(s * 0.068, 0.865, 2.01))],
                      [(0, 0.030, 0.022, 0.018), (0.6, 0.024, 0.016, 0.014), (1, 0.004, 0.004, 0.004)], 10 if hi else 4, 12 if hi else 6,
                      fwd=V(0, 1, 0)))
    for leg, s, front in (('fl', 1, True), ('fr', -1, True), ('bl', 1, False), ('br', -1, False)):
        x = s * 0.15
        if front:
            path = [(0, V(x, 0.46, 1.14)), (0.20, V(x, 0.49, 0.95)), (0.45, V(x, 0.50, 0.62)), (0.80, V(x, 0.50, 0.20)),
                    (0.92, V(x, 0.52, 0.09)), (1.0, V(x, 0.545, 0.0))]
            prof = [(0, 0.085, 0.11, 0.11), (0.20, 0.076, 0.096, 0.086), (0.40, 0.054, 0.058, 0.054), (0.47, 0.052, 0.056, 0.052),
                    (0.60, 0.036, 0.036, 0.046), (0.78, 0.040, 0.042, 0.050), (0.84, 0.046, 0.048, 0.055), (0.91, 0.036, 0.040, 0.040),
                    (0.95, 0.050, 0.055, 0.045), (1.0, 0.056, 0.064, 0.050)]
        else:
            path = [(0, V(x, -0.46, 1.18)), (0.22, V(x * 1.07, -0.38, 0.93)), (0.45, V(x, -0.585, 0.60)), (0.58, V(x, -0.57, 0.44)),
                    (0.80, V(x, -0.545, 0.19)), (0.92, V(x, -0.52, 0.085)), (1.0, V(x, -0.50, 0.0))]
            prof = [(0, 0.095, 0.13, 0.13), (0.22, 0.080, 0.115, 0.110), (0.43, 0.044, 0.056, 0.072), (0.47, 0.040, 0.045, 0.060),
                    (0.60, 0.034, 0.036, 0.046), (0.78, 0.040, 0.042, 0.050), (0.84, 0.046, 0.048, 0.055), (0.91, 0.036, 0.040, 0.040),
                    (0.95, 0.050, 0.055, 0.045), (1.0, 0.056, 0.064, 0.050)]
        P.append(limb('lg', path, prof, 60 if hi else 22, 24 if hi else 12, fwd=V(0, 1, 0), e=2.0))
    return P

def horse_slot(p):
    x, y, z = p.x, p.y - HOFF.y, p.z
    if z < 0.075 and abs(x) > 0.06: return 'shoe'
    if z < 0.47 and abs(x) > 0.06: return 'fur'
    ax = (HEAD1 - HEAD0); t = (V(0, y, z) - HEAD0).dot(ax) / ax.length_squared
    return 'knapsack'

_HORSE = {}
def horse_body(hi):
    """fused horse body (voxel remesh of the primitives), HOFF away from the rider. The hi fuse is cached as the ray tree
    for the tack / mane / reins."""
    parts = horse_parts(hi)
    o = C.fuse({'h': parts}, 0.0065 if hi else 0.016, 'hzbody')
    for q in parts: bpy.data.objects.remove(q)
    if not hi:
        m = o.modifiers.new('d', 'DECIMATE'); m.ratio = min(1.0, HORSE_LO / max(1, C.tris(o))); m.use_collapse_triangulate = True
        m.use_symmetry = True; m.symmetry_axis = 'X'
        C.apply_mods(o)
    if hi:
        _HORSE['tree'] = C.surface_tools([o])
    o.data.transform(Matrix.Translation(HOFF))
    set_slot(o, horse_slot)
    return o
HORSE_LO = 1700

def htree():
    if 'tree' not in _HORSE:
        parts = horse_parts(True); o = C.fuse({'h': parts}, 0.0065, '_ht')
        for q in parts: bpy.data.objects.remove(q)
        _HORSE['tree'] = C.surface_tools([o]); bpy.data.objects.remove(o)
    return _HORSE['tree']

def H(o):
    o.data.transform(Matrix.Translation(HOFF)); return o

def mane_tail(hi):
    t = htree(); out = []
    # mane: falls on the right (+x) side of the crest, poll to withers
    nr, nc = (60, 14) if hi else (12, 3)
    rows = []
    for i in range(nr + 1):
        u = i / nr
        y = lerp(0.88, 0.36, u); zc = lerp(1.88, 1.47, u ** 1.1) + 0.02 * math.sin(math.pi * u)
        top = V3P.surf(t, V(0, y, zc + 0.3), V(0, 0, -1), 0.004)
        if top is None: continue
        p0 = top[0]
        L = lerp(0.10, 0.16, math.sin(math.pi * min(1, u * 1.3)))
        row = []
        for j in range(nc + 1):
            v = j / nc
            q = p0 + V(0.010 + 0.060 * math.sin(v * 1.2), 0, 0)
            side = V3P.surf(t, V(0.35, y, p0.z - L * v), V(-1, 0, 0), 0.010)
            if side and v > 0.15: q = side[0] + V(0.008 * v, 0, 0)
            elif v > 0: q = V(max(q.x, 0.02), y, p0.z - L * v * 0.6)
            q = q + V(0, 0.015 * v, 0)
            row.append(q)
        rows.append(row)
    thick = 0.014 if hi else 0.012
    outer = rows; inner = [[q - V(thick, 0, 0) * (1 if True else 0) for q in r] for r in rows]
    if hi:
        outer = [[q + V(0.004 * math.sin(i * 1.7 + j * 0.3), 0, 0) for j, q in enumerate(r)] for i, r in enumerate(rows)]
    secs = [o_ + i_[::-1] for o_, i_ in zip(outer, inner)]
    out.append(H(grid_sweep('hzmane', secs, closed_u=True, cap0=True, cap1=True, slot='hair')))
    # forelock
    fl0 = V3P.surf(t, V(0, 0.93, 2.1), V(0, 0, -1), 0.004)
    if fl0:
        p = fl0[0]
        out.append(H(limb('hzmane.fl', [(0, p), (0.5, p + V(0.006, 0.05, -0.05)), (1, p + V(0.01, 0.075, -0.12))],
                          [(0, 0.030, 0.010, 0.010), (0.7, 0.026, 0.008, 0.008), (1, 0.008, 0.003, 0.003)], 10 if hi else 3,
                          10 if hi else 4, fwd=V(0, 1, 0.4), slot='hair')))
    # tail
    out.append(H(limb('hztail', [(0, V(0, -0.68, 1.33)), (0.15, V(0, -0.78, 1.27)), (0.45, V(0, -0.83, 1.05)), (0.8, V(0, -0.83, 0.78)),
                                 (1, V(0, -0.81, 0.62))],
                      [(0, 0.040, 0.040, 0.040), (0.25, 0.050, 0.050, 0.050), (0.6, 0.062, 0.050, 0.05), (0.92, 0.045, 0.036, 0.036),
                       (1, 0.010, 0.010, 0.010)], 30 if hi else 7, 16 if hi else 6, fwd=V(1, 0, 0), slot='hair')))
    for s in (1, -1):
        ax = HEAD1 - HEAD0
        c = V(s * 0.093, 1.05, 1.744)
        out.append(H(superellipsoid('hzeye', c, (0.010, 0.020, 0.015), e=(2, 2), n=(12, 6) if hi else (6, 4), slot='eye')))
    return out

# ------------------------------------------------------------------ tack (horse coords)
def _barrel(y):
    for a, b in zip(BARREL, BARREL[1:]):
        if a[0] <= y <= b[0]:
            k = (y - a[0]) / (b[0] - a[0]); return tuple(lerp(a[i], b[i], k) for i in range(1, 4))
    return BARREL[0][1:] if y < BARREL[0][0] else BARREL[-1][1:]

def side_curve(t, y, off, n=48):
    """surface curve of the horse at y from the spine (top) down the +x side: [(point, normal, arclen)], draped (never
    tucks back in under the widest point)."""
    top, bot, hw = _barrel(min(max(y, -0.62), 0.55)); zc = (top + bot) / 2
    pts = []; xm = 0.0; L = 0.0; prev = None
    for k in range(n + 1):
        a = math.radians(lerp(0, 175, k / n))
        d = V(math.sin(a), 0, math.cos(a))
        h = t.ray_cast(V(0, y, zc), d)
        if h[0] is None:
            if not pts: return []
            p = prev + V(0, 0, -0.02); nrm = V(1, 0, 0)
        else:
            p = h[0] + h[1] * off; nrm = h[1]
        if p.x < xm and p.z < zc + 0.05: p = V(xm, p.y, p.z); nrm = V(1, 0, 0)
        xm = max(xm, p.x)
        if prev is not None: L += (p - prev).length
        pts.append((p, nrm, L)); prev = p
    return pts

def _at(curve, s):
    for a, b in zip(curve, curve[1:]):
        if a[2] <= s <= b[2]:
            k = (s - a[2]) / max(1e-6, b[2] - a[2]); return a[0].lerp(b[0], k), a[1].lerp(b[1], k).normalized()
    return curve[-1][0], curve[-1][1]

def _s_at_z(curve, z):
    for a, b in zip(curve, curve[1:]):
        if a[0].z >= z >= b[0].z:
            k = (a[0].z - z) / max(1e-6, a[0].z - b[0].z); return lerp(a[2], b[2], k)
    return curve[-1][2]

SHAB_Y0, SHAB_Y1 = 0.34, -0.76
SHAB_YT = -0.50   # rear tail: top edge cut from here down to the point at SHAB_Y1
def shab_bottom(y):
    if y > 0.22: return 0.93 + 0.37 * (1 - math.sqrt(max(0.0, 1 - ((y - 0.22) / 0.12) ** 2)))
    if y > -0.40: return 0.93
    return 0.93 + 0.10 * (-0.40 - y) / (-0.40 - SHAB_Y1)
def shab_top(y, top):
    if y > SHAB_YT: return 9.0
    k = min(1.0, (SHAB_YT - y) / (SHAB_YT - SHAB_Y1))
    return lerp(top + 0.02, shab_bottom(y) + 0.002, k ** 0.8)

_CV = {}
def _cv(t, y, off):
    k = (round(y, 5), off)
    if k not in _CV:
        _CV[k] = side_curve(t, y, off)
        if not _CV[k]: _CV[k] = side_curve(t, y + 0.02, off)
    return _CV[k]

def shab_pt(t, y, v, s, off):
    """shabraque surface at length y, v = 0 top edge .. 1 bottom edge, side s: (point, normal)."""
    cv = _cv(t, max(y, -0.66), off)
    zb = shab_bottom(y); zt = shab_top(y, cv[0][0].z)
    s1 = _s_at_z(cv, zb); s0 = _s_at_z(cv, zt) if zt < 9 else 0.0
    s0 = min(s0, s1 - 0.01)
    p, n = _at(cv, lerp(s0, s1, v))
    return V(s * p.x, y, p.z), V(s * n.x, n.y, n.z).normalized()

def sheep_bottom(y): return lerp(1.17, 1.22, abs(y + 0.03) / 0.33) + 0.03 * ((y + 0.03) / 0.33) ** 2
SHEEP_Y0, SHEEP_Y1 = 0.30, -0.36
def sheep_pt(t, y, v, s, off):
    cv = _cv(t, y, off)
    p, n = _at(cv, _s_at_z(cv, sheep_bottom(y)) * v)
    return V(s * p.x, y, p.z), V(s * n.x, n.y, n.z).normalized()

def tooth_band(name, samples, w, tooth, step, slot):
    """lace edging as its own single-colour island: samples = dense [(point, normal, inward)] along an edge; strip of
    width w, inner edge vandyked (wolf-tooth) by tooth (0 = straight). Same geometry hi + lo (no id-map stair steps)."""
    L = [0.0]
    for a, b in zip(samples, samples[1:]): L.append(L[-1] + (b[0] - a[0]).length)
    m = max(2, 2 * int(L[-1] / (2 * step))) if tooth > 0 else max(2, int(L[-1] / step))
    verts = []; faces = []
    j = 0
    for k in range(m + 1):
        sk = L[-1] * k / m
        while j < len(L) - 2 and L[j + 1] < sk: j += 1
        f = (sk - L[j]) / max(1e-6, L[j + 1] - L[j])
        p = samples[j][0].lerp(samples[j + 1][0], f); n = samples[j][1].lerp(samples[j + 1][1], f).normalized()
        tg = (samples[j + 1][0] - samples[j][0]).normalized()
        iw = samples[j][2].lerp(samples[j + 1][2], f)
        iw = iw - n * iw.dot(n); iw = iw - tg * iw.dot(tg); iw.normalize()
        wk = w + (tooth if (k % 2 == 1 and tooth > 0) else 0.0)
        verts += [p, p + iw * wk]
    for k in range(m):
        a = 2 * k; fc = (a, a + 1, a + 3, a + 2)
        p0, p1, p2 = verts[fc[0]], verts[fc[1]], verts[fc[2]]
        nn = samples[min(len(samples) - 1, int(k / m * (len(samples) - 1)))][1]
        if (p1 - p0).cross(p2 - p0).dot(nn) < 0: fc = fc[::-1]
        faces.append(fc)
    return C.mk(name, verts, faces, slot)

def shabraque(hi):
    t = htree(); out = []
    nr, nc = (150, 70) if hi else (12, 6)
    for s in (1, -1):
        rows = [[shab_pt(t, lerp(SHAB_Y0, SHAB_Y1, i / nr), j / nc, s, 0.012)[0] for j in range(nc + 1)] for i in range(nr + 1)]
        out.append(H(grid_sweep('hzshab.' + ('R' if s > 0 else 'L'), rows, closed_u=False, cap0=False, cap1=False, slot='turnback')))
        # yellow lace edging with a wolf-tooth inner edge: front edge, bottom (round front corner), rear tail top cut
        E = []; d = 0.01; off = 0.0155
        for k in range(12):
            v = k / 11; p, n = shab_pt(t, SHAB_Y0, v, s, off); E.append((p, n, shab_pt(t, SHAB_Y0 - d, v, s, off)[0] - p))
        ny = 90
        for k in range(1, ny + 1):
            y = lerp(SHAB_Y0, SHAB_Y1 + 0.004, k / ny); p, n = shab_pt(t, y, 1.0, s, off)
            E.append((p, n, shab_pt(t, y, 0.9, s, off)[0] - p))
        for k in range(1, 25):
            y = lerp(SHAB_Y1 + 0.004, SHAB_YT, k / 24); p, n = shab_pt(t, y, 0.0, s, off)
            E.append((p, n, shab_pt(t, y, 0.1, s, off)[0] - p))
        out.append(H(tooth_band('hzedge.' + ('R' if s > 0 else 'L'), E, 0.022, 0.024, 0.036, 'gold')))
    # sheepskin over the saddle, red wolf-tooth edge
    nr, nc = (60, 30) if hi else (8, 5)
    for s in (1, -1):
        rows = []
        for i in range(nr + 1):
            y = lerp(SHEEP_Y0, SHEEP_Y1, i / nr)
            row = []
            for j in range(nc + 1):
                p, n = sheep_pt(t, y, j / nc, s, 0.030)
                lift = 0.010 * math.sin(math.pi * j / nc) if hi else 0.0
                if hi: lift += 0.0015 * math.sin(i * 1.9) * math.sin(j * 2.3)
                row.append(p + V(0, 0, lift))
            rows.append(row)
        out.append(H(grid_sweep('hzsheep.' + ('R' if s > 0 else 'L'), rows, closed_u=False, cap0=False, cap1=False, slot='sponge')))
        E = []
        for k in range(61):
            y = lerp(SHEEP_Y0, SHEEP_Y1, k / 60); p, n = sheep_pt(t, y, 1.0, s, 0.036)
            E.append((p, n, sheep_pt(t, y, 0.85, s, 0.036)[0] - p))
        out.append(H(tooth_band('hzsedge.' + ('R' if s > 0 else 'L'), E, 0.010, 0.020, 0.024, 'piping')))
    # valise behind the cantle
    out.append(H(limb('hzval', [(0, V(-0.21, -0.42, 1.435)), (1, V(0.21, -0.42, 1.435))],
                      [(0, 0.065, 0.065, 0.065), (0.04, 0.072, 0.072, 0.072), (0.96, 0.072, 0.072, 0.072), (1, 0.065, 0.065, 0.065)],
                      8 if hi else 3, 16 if hi else 8, fwd=V(0, 0, 1), slot='turnback')))
    return out

def strap_curve(t, pts_dirs, off):
    return [r for r in (V3P.surf(t, o, d, off) for o, d in pts_dirs) if r]

def tack(hi):
    t = htree(); out = []
    # girth round the belly behind the elbow
    pd = []
    for k in range(13):
        a = math.radians(lerp(-75, 75, k / 12))
        pd.append((V(0, 0.18, 1.05), V(math.sin(a), 0, -math.cos(a))))
    out += [H(x) for x in RB('hzgirth', strap_curve(t, pd, 0.012), 0.06, hi, slot='cartbox')]
    # breastplate round the chest
    pd = []
    for k in range(15):
        a = math.radians(lerp(-80, 80, k / 14))
        pd.append((V(0, 0.30, 1.13 - 0.05 * math.cos(a)), V(math.sin(a), math.cos(a), 0)))
    out += [H(x) for x in RB('hzbreast', strap_curve(t, pd, 0.008), 0.035, hi, slot='cartbox')]
    r = V3P.surf(t, V(0, 0.30, 1.08), V(0, 1, 0), 0.012)
    if r:
        out.append(H(superellipsoid('hzbreast.h', r[0], (0.030, 0.008, 0.030), e=(2, 2), n=(12, 6) if hi else (6, 3), slot='metal',
                                    rot=r[1].to_track_quat('Y', 'Z').to_matrix())))
    # bridle: cheekpieces, crown, browband, noseband, throatlatch; bit rings
    ax = HEAD1 - HEAD0; dax = ax.normalized()
    vdn = (V(0, 0, -1) - dax * V(0, 0, -1).dot(dax)).normalized()
    bit = _head_axis(0.80) + vdn * 0.035
    C.RIDER['bit'] = tuple(bit)
    for s in (1, -1):
        pd = []
        for k in range(9):
            q = bit.lerp(V(0, 0.885, 1.86), k / 8)
            pd.append((V(s * 0.4, q.y, q.z), V(-s, 0, 0)))
        out += [H(x) for x in RB('hzbrid.ch', strap_curve(t, pd, 0.004), 0.020, hi, slot='cartbox')]
        hb = V3P.surf(t, V(s * 0.4, bit.y, bit.z), V(-s, 0, 0), 0.006)
        bc = hb[0] if hb else V(s * 0.068, bit.y, bit.z)
        nl = 12 if hi else 6
        loop = [(k / nl, bc + V(0, 0.022 * math.cos(2 * math.pi * k / nl), 0.022 * math.sin(2 * math.pi * k / nl))) for k in range(nl)]
        out.append(H(limb('hzbit', loop + [(1.0, loop[0][1])], [(0, 0.0035, 0.0035, 0.0035)], nl, 6 if hi else 3, fwd=V(1, 0, 0),
                          slot='steel')))
    for nm, cen, n in (('hzbrid.nb', _head_axis(0.66), 20), ('hzbrid.cr', _head_axis(0.02), 20)):
        pd = []
        for k in range(n + 1):
            a = 2 * math.pi * k / n
            d = dax.cross(V(1, 0, 0)).normalized() * math.cos(a) + V(1, 0, 0) * math.sin(a)
            pd.append((cen, d))
        out += [H(x) for x in RB(nm, strap_curve(t, pd, 0.004), 0.022, hi, slot='cartbox')]
    pd = [(V(x, 1.20, 1.85), V(0, -0.2, -1)) for x in np.linspace(-0.09, 0.09, 9)]
    pd = [(V(x, 0.97, 1.80) + V(0, 0.3, 0.1), V(0, -1, -0.3)) for x in np.linspace(-0.08, 0.08, 9)]
    out += [H(x) for x in RB('hzbrid.bb', strap_curve(t, pd, 0.004), 0.018, hi, slot='cartbox')]
    # reins: bit -> along the neck -> left fist, authored in the IDLE pose (v3_rider moves them back to rest)
    import v3_rider as VR
    idle = VR.idle0()
    def idle_pt(bone, p): return Vector(VR._ap(idle[bone], tuple(p)))
    fist = idle_pt('r_fore.L', VR.seat_point('hand.L', (-0.214, 0.0, 0.79)))
    C.RIDER['fist_idle'] = tuple(fist)
    for s in (1, -1):
        b0 = idle_pt('head', V(s * 0.072, bit.y - 0.020, bit.z))
        n = 30 if hi else 9
        pts = []
        for k in range(n + 1):
            u = k / n
            mid = b0.lerp(fist + V(s * 0.012, 0, 0), u) + V(s * 0.05 * math.sin(math.pi * u), 0, -0.05 * math.sin(math.pi * u))
            loc, nrm, fi, dist = t.find_nearest(mid)
            if loc is not None and ((mid - loc).dot(nrm) < 0.0 or dist < 0.015) and u < 0.9:
                mid = loc + nrm * 0.015
            pts.append(mid)
        out.append(H(limb('hzrein', [(k / n, p) for k, p in enumerate(pts)], [(0, 0.008, 0.0028, 0.0028)], n, 4,
                          fwd=V(0, 0, 1), slot='cartbox')))
    C.RIDER['rein_w'] = lambda q, k: _rein_w(q, idle)
    # stirrups + leathers under the seated feet (ball of the foot)
    for s, sd in ((1, '.R'), (-1, '.L')):
        ball = VR.seat_point('foot' + sd, (s * 0.105, 0.085, 0.006))
        top = V(s * 0.215, 0.07, 1.30)
        eye = ball + V(0, 0, 0.125)
        out.append(H(limb('hzleath', [(0, top), (1, eye)], [(0, 0.014, 0.003, 0.003)], 6 if hi else 1, 4,
                          fwd=V(s, 0, 0), slot='cartbox')))
        loop = []
        nl = 12 if hi else 6
        for k in range(nl + 1):
            a = 2 * math.pi * k / nl
            loop.append((k / nl, ball + V(0.058 * math.sin(a) * 0.85, 0, 0.058 + 0.064 * math.cos(a)) - V(0, 0, 0.008)))
        out.append(H(limb('hzstir', loop[:-1] + [(1.0, loop[0][1])], [(0, 0.005, 0.006, 0.006)], nl, 6 if hi else 3,
                          fwd=V(0, 1, 0), slot='steel')))
        out.append(H(superellipsoid('hzstir.t', ball - V(0, 0, 0.012), (0.050, 0.032, 0.005), e=(3, 3), n=(10, 4) if hi else (6, 3),
                                    slot='steel')))
    # empty steel scabbard + sabretache on slings from the left hip (seated)
    hip = VR.seat_point('hips', (-0.150, -0.04, 0.975))
    sc0, sc1 = V(-0.262, -0.16, 1.30), V(-0.335, -0.76, 0.98)
    path = [(0, sc0), (0.5, sc0.lerp(sc1, 0.5) + V(-0.008, 0, 0)), (1, sc1)]
    out.append(H(limb('hzsc', path, [(0, 0.010, 0.018, 0.018), (0.9, 0.009, 0.014, 0.014), (1, 0.006, 0.008, 0.008)],
                      12 if hi else 5, 10 if hi else 5, fwd=V(-1, 0, 0), slot='steel', e=2.6)))
    for u in (0.12, 0.42):
        p, _ = C.path_frame(path, u)
        out.append(H(limb('hzsc.sl', [(0, hip + V(0, 0.0, -0.02)), (1, p)], [(0, 0.007, 0.002, 0.002)], 2 if hi else 1, 4,
                          fwd=V(-1, 0, 0), slot='cartbox')))
    st_c = V(-0.290, -0.30, 1.00)
    rot = Matrix.Rotation(math.radians(8), 3, 'X')
    def stache(q):
        return q
    out.append(H(superellipsoid('hzst', st_c, (0.012, 0.135, 0.165), e=(5, 5), n=(16, 8) if hi else (8, 4), rot=rot,
                                slot=(lambda c: 'gold' if (abs(c.y - st_c.y) > 0.112 or c.z - st_c.z < -0.140) else ('metal' if (c - st_c).length < 0.045 else 'turnback')) if hi else 'turnback')))
    for dy in (0.10, -0.10):
        out.append(H(limb('hzst.sl', [(0, hip + V(0, 0, -0.03)), (1, st_c + rot @ V(0, dy, 0.16))], [(0, 0.006, 0.002, 0.002)],
                          2 if hi else 1, 4, fwd=V(-1, 0, 0), slot='cartbox')))
    return out

def _rein_w(q, idle):
    """reins: bit end on the head, along the neck, fist end on r_fore.L (idle-space position q, horse coords)."""
    bit = Vector(C.RIDER['bit']); fist = Vector(C.RIDER['fist_idle'])
    import v3_rider as VR
    b0 = Vector(VR._ap(idle['head'], tuple(bit)))
    d = fist - b0; u = max(0.0, min(1.0, (Vector(tuple(q)) - b0).dot(d) / d.length_squared))
    h = ss(0.30, 0.12, u); f = ss(0.70, 0.92, u); n = max(0.0, 1 - h - f)
    return {k: v for k, v in (('head', h), ('neck', n), ('r_fore.L', f)) if v > 1e-4}

C.RIDER['rigid'].update({'hzsc': 'body', 'hzst': 'body'})

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    ht = C.surface_tools([head])
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'collar'); parts.append(cb)
    parts += lace(body_tree, hi) + breeches_trim(body_tree, hi) + boots(body_tree, hi) + sash(body_tree, hi)
    parts += pelisse(body_tree, hi) + shako(hi) + hair(ht, hi) + sabre(hi)
    parts.append(horse_body(hi))
    parts += mane_tail(hi) + shabraque(hi) + tack(hi)
    return parts
C.build_kit = build_kit
