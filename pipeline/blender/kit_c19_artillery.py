"""Eras v3 kit 2: French foot artillery gunner (artillerie a pied), c.1806-1812, serving the piece with the rammer /
sponge (docs/char/ERAS_PROGRESS.md). Patches char_v2 (loaded by char_v2_build.py when V3_KIT=kit_c19_artillery).
Only the base human, body cage, rig and material library are shared; every garment / item is built fresh here:
  * all-blue habit: blue lapels piped red (square cut, to the waist), blue collar piped red, red cuffs with blue cuff
    flaps piped red, red turnbacks with blue grenades, vertical pocket flaps piped red; blue waistcoat + blue breeches
  * black gaiters to just below the knee (straight top)
  * red fringed epaulettes (foot artillery), brass buttons
  * 1806 shako: bell-topped black felt, leather top / bottom bands, brass lozenge plate with crossed cannons,
    tricolour cockade, tall red plume, red cords with flounders + tassels on the right side
  * single white crossbelt with the artillery sabre-briquet, narrow cartridge belt with a small black pouch
    (brass crossed cannons)
  * rammer / sponge staff (same prop axis and extents as the existing crewman, so the 'rammer' clips fit)"""
import math, bpy
from mathutils import Matrix
import char_v2 as C
import human_mh as HM, v3_parts as V3P
from char_v2 import V, ss, lerp, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_c19_artillery'
C.CLIP_STYLE = 'rammer'
C.TIP_LOCAL = (0.0, 1.70, 0.0)          # rammer head end (weapon_tip on the prop)
C.SLOT_MAT.update({'gold': 'brass', 'scabbard': 'leather', 'sponge': 'fur', 'felt': 'leather', 'shoe': 'shoe_leather'})
C.BODY_TRIS = 5000
C.HEAD_BOX = (0.15, -0.15, 0.17, 2.02)  # shako + plume get head-level texel density
C.KIT_PAL = {'breeches': '#26315c', 'waist': '#26315c'}   # blue waistcoat + breeches (foot artillery)
C.KIT_RULES = [(('ashako', 'apeak', 'aplume', 'acock', 'acord'), 'head'), (('aepaul', 'afringe'), 'transfer'),
               (('asabre', 'ahilt', 'aknot', 'afrog'), 'hips'), (('apouch',), 'hips'),
               (('ramstaff', 'ramhead', 'sponge'), 'prop')]

LAP_W = 0.088
LAP_Z0, LAP_Z1 = 1.09, 1.475

GAITER_TOP = 0.470
HM.FIST['.L'] = 0.007   # empty left hand: relaxed fist

def body_slot(p, part):
    x, y, z = p; ax = abs(x)
    if part == 'shoe': return 'shoe'
    if part == 'collar':
        ztop = 1.556 - 0.020 * ss(0.04, 0.085, y)
        return 'piping' if z > ztop - 0.007 else 'coat'   # blue collar, red piping along the top
    if part == 'arm':
        if z < 0.968: return 'cuff'
        if z < 1.036 and y < -0.008:          # blue cuff flap piped red on the back of the sleeve
            if z > 1.029 or y > -0.015: return 'piping'
            return 'coat'
        return 'coat'
    if part == 'leg':
        if z < GAITER_TOP - 0.014: return 'gaiter'   # straight-topped gaiters just under the knee (edge = hem band)
        return 'breeches'
    if z > 1.586: return 'skin'
    if z > 1.49: return 'stock'
    if y > 0.02:
        lw = LAP_W + 0.010 * ss(1.36, LAP_Z1, z)
        if LAP_Z0 < z < LAP_Z1 + 0.02 and ax < lw:
            if ax > lw - 0.007 or z < LAP_Z0 + 0.007: return 'piping'
            return 'coat'                      # blue lapel
        cut = lerp(LAP_W, 0.170, ss(LAP_Z0, 0.90, z))
        if 0.90 < z <= LAP_Z0 + 0.001 and ax < cut: return 'waist'
        if z <= 0.90: return 'breeches'
        return 'coat'
    if z < 0.90 and ax < 0.2: return 'breeches'
    return 'coat'
C.body_slot = body_slot

def coat_tails(hi=False):
    """habit tails to mid-thigh, red turnbacks with blue grenades, vertical pocket flaps piped red."""
    out = []
    nz, nw = (28, 12) if hi else (5, 3)
    Z0, Z1 = 1.04, 0.60
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            t = i / nz; z = lerp(Z0, Z1, t)
            yb = lerp(-0.118, -0.150, ss(1.04, 0.94, z)); yb = lerp(yb, -0.112, ss(0.90, 0.62, z))
            xc = s * lerp(0.090, 0.064, t); hw = lerp(0.090, 0.052, t)
            outer, inner = [], []
            for j in range(nw + 1):
                w = -1 + 2 * j / nw; x = xc + s * w * hw
                y = yb - 0.010 * (1 - w * w) + 0.014 * ss(0.10, 0.19, abs(x))
                outer.append(V(x, y, z)); inner.append(V(x, y + 0.012, z))
            secs.append(outer + inner[::-1])
        o = grid_sweep('tail', secs, cap0=True, cap1=True)
        def tslot(p):
            ax = abs(p.x)
            if p.z > 0.97: return 'coat'
            k = (p.z - Z1) / (0.97 - Z1)
            if ax < 0.128 - 0.045 * (1.0 - k):
                d = math.hypot(ax - 0.052, p.z - 0.672)       # blue grenade badge on the turnback
                if d < 0.014 or (abs(ax - 0.052) < 0.005 * (1 - (p.z - 0.685) / 0.03) and 0.685 < p.z < 0.715): return 'coat'
                return 'turnback'
            if 0.74 < p.z < 0.94 and abs(ax - 0.150) < 0.011:
                return 'piping' if abs(ax - 0.150) > 0.006 or p.z < 0.746 else 'coat'
            return 'coat'
        set_slot(o, tslot)
        out.append(o)
    return out
C.coat_tails = coat_tails

def buttons(tree):
    out = []
    def on_body(x, z, r=0.0072):
        hit = tree.ray_cast(V(x, 0.5, z), V(0, -1, 0))
        if hit[0] is None: return
        p, n = hit[0], hit[1]
        out.append(superellipsoid('button', p + n * 0.0015, (r, r, 0.0028), e=(2, 2.6), n=(14, 6),
                                  rot=n.to_track_quat('Z', 'Y').to_matrix(), slot='metal'))
    for i in range(7):
        z = lerp(1.385, 1.115, i / 6)
        for sx in (1, -1): on_body(sx * (LAP_W - 0.016), z)
    for i in range(4): on_body(0.0, lerp(1.06, 0.94, i / 3), 0.0052)
    return out
C.buttons = buttons

# ------------------------------------------------------------------ epaulettes (foot artillery: red, short fringe)
def epaulettes(tree, hi=False):
    out = []
    def top(x, y):
        h = tree.ray_cast(V(x, y, 1.75), V(0, 0, -1)); return h[0], h[1]
    for s in (1, -1):
        n = 14 if hi else 4
        secs = []
        for i in range(n + 1):
            t = i / n; p, nr = top(s * lerp(0.070, 0.170, t), -0.006)
            if p is None: continue
            w = lerp(0.030, 0.040, t)
            secs.append([p + nr * 0.0015 + V(0, w / 2, 0), p + nr * 0.0015 - V(0, w / 2, 0),
                         p + nr * 0.0055 - V(0, w / 2, 0), p + nr * 0.0055 + V(0, w / 2, 0)])
        out.append(grid_sweep('aepaul.strap', secs, closed_u=True, slot='epaulette'))
        c, nr = top(s * 0.186, -0.008)
        rot = nr.to_track_quat('Z', 'Y').to_matrix()
        out.append(superellipsoid('aepaul.cres', c + nr * 0.007, (0.036, 0.046, 0.009), e=(2.2, 2.2), n=(26, 10) if hi else (10, 4),
                                  rot=rot, slot='epaulette'))
        m = 34 if hi else 9
        rt, rb = [], []
        for k in range(m + 1):
            a = math.radians(-105 + 210 * k / m)
            d = V(s * math.cos(a), math.sin(a) * 1.2, 0)
            t0 = c + nr * 0.004 + V(d.x * 0.036, d.y * 0.040, 0)
            rt.append(t0); rb.append(t0 + V(d.x * 0.010, d.y * 0.008, -0.038 + 0.008 * (1 - math.cos(a))))
        if hi:
            for k in range(m + 1):
                out.append(limb('afringe', [(0, rt[k]), (1, rb[k])], [(0, 0.0032, 0.0032, 0.0032), (1, 0.0026, 0.0026, 0.0026)],
                                4, 6, fwd=V(s, 0, 0), slot='epaulette'))
        else:
            secs = []
            for k in range(m + 1):
                o = (rb[k] - c); o.z = 0; o = o.normalized() * 0.004
                secs.append([rt[k] + o, rb[k] + o, rb[k] - o, rt[k] - o])
            out.append(grid_sweep('afringe', secs, closed_u=True, cap0=True, cap1=True, slot='epaulette'))
    return out

# ------------------------------------------------------------------ 1806 shako
SH_Z0, SH_Z1 = 1.712, 1.900
SH_BASE = V(0, 0.028, SH_Z0)
SH_TILT = Matrix.Rotation(math.radians(-5), 3, 'X')
def _shT(p): return SH_BASE + SH_TILT @ (p - SH_BASE)
def _shr(t): return lerp(0.084, 0.097, t), lerp(0.101, 0.110, t)   # bell top (wider crown)

def shako(hi=False):
    ts = [i / 150 for i in range(151)] if hi else [0.0, 0.07, 0.5, 0.93, 1.0]
    nu = 220 if hi else 20
    secs = []
    for t in ts:
        rx, ry = _shr(t)
        bd = 0.0022 * (ss(0.0, 0.01, t) * ss(0.085, 0.075, t) + ss(0.905, 0.915, t))   # leather bands (bottom + top)
        rx += bd; ry += bd
        secs.append([_shT(p) for p in ring(V(0, SH_BASE.y, lerp(SH_Z0, SH_Z1, t)), V(1, 0, 0), V(0, 1, 0), rx, ry, ry, nu, 2.0, 0.5)])
    body = grid_sweep('ashako', secs, cap0=True, cap1=True)
    inv = SH_TILT.inverted()
    def sslot(p):
        q = inv @ (p - SH_BASE); t = q.z / (SH_Z1 - SH_Z0)
        if q.y > 0.05 and abs(q.x) / 0.040 + abs(q.z - 0.080) / 0.056 < 1.0: return 'metal'   # brass lozenge plate
        return 'felt'
    set_slot(body, sslot)
    out = [body]
    pk = []
    for j in range((12 if hi else 5) + 1):   # peak
        a = math.pi * (0.10 + 0.80 * j / (12 if hi else 5))
        c = V(math.cos(a), math.sin(a), 0)
        rx, ry = _shr(0.0)
        inner = V(rx * c.x, SH_BASE.y + ry * c.y, SH_Z0 + 0.004)
        outer = inner + V(c.x * 0.014, c.y * 0.052, -0.022)
        pk.append([_shT(inner), _shT(outer), _shT(outer + V(0, 0, 0.005)), _shT(inner + V(0, 0, 0.005))])
    out.append(grid_sweep('apeak', pk, closed_u=True, cap0=True, cap1=True, slot='felt'))
    # tricolour cockade at the top front, tall red plume above it
    rx, ry = _shr(0.93)
    ck = _shT(V(0, SH_BASE.y + ry + 0.004, SH_Z0 + 0.93 * (SH_Z1 - SH_Z0)))
    out.append(superellipsoid('acock', ck, (0.020, 0.006, 0.020), e=(2, 2), n=(14, 6) if hi else (8, 3), slot='collar'))
    p0 = ck + V(0, -0.010, 0.010)
    out.append(limb('aplume', [(0, p0), (0.5, p0 + V(0, -0.006, 0.10)), (1, p0 + V(0, -0.012, 0.21))],
                    [(0, 0.008, 0.008, 0.008), (0.15, 0.020, 0.020, 0.020), (0.6, 0.017, 0.017, 0.017), (1, 0.003, 0.003, 0.003)],
                    20 if hi else 5, 14 if hi else 6, fwd=V(1, 0, 0), slot='plume'))
    # red cords: two festoons across the front at mid height, flounders + tassels on the right
    for k0, dz in ((0, 0.0), (1, -0.022)):
        nseg = 36 if hi else 7
        path = []
        for k in range(nseg + 1):
            a = math.radians(-165 + 150 * k / nseg)
            t = 0.42 + dz / 0.19 - 0.12 * math.sin(math.pi * k / nseg)
            rx, ry = _shr(t)
            path.append((k / nseg, _shT(V(math.cos(a) * (rx + 0.0035), SH_BASE.y - math.sin(a) * (ry + 0.0035), SH_Z0 + t * (SH_Z1 - SH_Z0)))))
        out.append(limb('acord', path, [(0, 0.0034, 0.0034, 0.0034)], 50 if hi else 7, 8 if hi else 4, fwd=V(0, 0, 1), slot='plume'))
    rs = path[-1][1]
    for k in range(2):
        a = rs + V(0.004, -0.012 * k, 0.004)
        out.append(limb('acord.fl', [(0, a), (1, a + V(0.010, -0.004, -0.10))],
                        [(0, 0.004, 0.004, 0.004), (0.75, 0.005, 0.005, 0.005), (1, 0.010, 0.010, 0.010)],
                        10 if hi else 3, 8 if hi else 4, fwd=V(0, 1, 0), slot='plume'))
    if hi:   # crossed cannons + crowned eagle blob on the plate (relief, same group as the shako)
        def on_plate(x, zq, d=0.004):
            t = zq / (SH_Z1 - SH_Z0); rx, ry = _shr(t)
            y = SH_BASE.y + ry * math.sqrt(max(0.0, 1 - (x / rx) ** 2))
            return _shT(V(x, y + d, SH_Z0 + zq))
        for sgn in (1, -1):
            out.append(limb('ashako.can', [(0, on_plate(-sgn * 0.026, 0.050)), (1, on_plate(sgn * 0.026, 0.092))],
                            [(0, 0.0035, 0.0035, 0.0035), (0.85, 0.0030, 0.0030, 0.0030), (1, 0.0042, 0.0042, 0.0042)],
                            10, 8, fwd=V(0, 1, 0), slot='metal'))
        out.append(superellipsoid('ashako.eagle', on_plate(0, 0.104, 0.003), (0.011, 0.004, 0.012), e=(2, 2), n=(14, 6), slot='metal'))
    return out

# ------------------------------------------------------------------ sabre-briquet, pouch
def sabre(hi=False):
    a = V(-0.160, -0.030, 0.985)
    path = [(0, a), (0.5, V(-0.176, -0.095, 0.735)), (1, V(-0.184, -0.170, 0.480))]
    out = [limb('asabre', path, [(0, 0.011, 0.018, 0.018), (0.9, 0.009, 0.014, 0.014), (1, 0.007, 0.010, 0.010)], 12 if hi else 4,
                10 if hi else 5, fwd=V(1, 0, 0), slot='scabbard', e=2.6)]
    for t0, t1, nm in ((0.0, 0.07, 'asabre.throat'), (0.90, 1.0, 'asabre.chape')):
        p0, _ = C.path_frame(path, t0); p1, _ = C.path_frame(path, t1)
        out.append(limb(nm, [(0, p0), (1, p1)], [(0, 0.0125, 0.020, 0.020)], 1, 10 if hi else 5, fwd=V(1, 0, 0), slot='metal', e=2.6))
    g0 = a + V(0.0, 0.010, 0.020); g1 = g0 + V(0.0, 0.036, 0.100)
    out.append(limb('ahilt', [(0, g0), (1, g1)], [(0, 0.012, 0.010, 0.010), (0.5, 0.013, 0.011, 0.011), (1, 0.011, 0.010, 0.010)],
                    6 if hi else 2, 10 if hi else 5, fwd=V(1, 0, 0), slot='metal'))
    out.append(limb('ahilt.bow', [(0, g0 + V(0, 0.017, -0.002)), (0.5, g0 + V(0, 0.046, 0.052)), (1, g1 + V(0, 0.010, 0.004))],
                    [(0, 0.0042, 0.0042, 0.0042)], 12 if hi else 4, 6 if hi else 4, fwd=V(1, 0, 0), slot='metal'))
    k0 = g1 + V(-0.012, 0.0, -0.01)
    out.append(limb('aknot', [(0, k0), (0.6, k0 + V(-0.010, 0.006, -0.09)), (1, k0 + V(-0.012, 0.004, -0.115))],
                    [(0, 0.004, 0.004, 0.004), (0.75, 0.005, 0.005, 0.005), (0.8, 0.011, 0.011, 0.011), (1, 0.014, 0.014, 0.014)],
                    10 if hi else 4, 8 if hi else 4, fwd=V(1, 0, 0), slot='plume'))
    out.append(superellipsoid('afrog', V(-0.158, -0.016, 0.966), (0.010, 0.036, 0.028), e=(4, 4), n=(12, 6) if hi else (8, 4), slot='belt'))
    return out

def pouch(hi=False):
    rot = Matrix.Rotation(math.radians(-14), 3, 'Z')
    c = V(0.112, -0.176, 0.985)
    out = [superellipsoid('apouch', c, (0.075, 0.030, 0.052), e=(5.5, 5.5), n=(16, 10) if hi else (8, 4), rot=rot, slot='cartbox')]
    if hi:
        out.append(superellipsoid('apouch.flap', c + rot @ V(0, -0.031, 0.010), (0.073, 0.004, 0.042), e=(6, 6), n=(18, 8), rot=rot, slot='cartbox'))
        g = c + rot @ V(0, -0.037, 0.004)
        for sgn in (1, -1):
            out.append(limb('apouch.can', [(0, g + rot @ V(-sgn * 0.020, 0, -0.014)), (1, g + rot @ V(sgn * 0.020, 0, 0.014))],
                            [(0, 0.0030, 0.0030, 0.0030), (0.85, 0.0026, 0.0026, 0.0026), (1, 0.0036, 0.0036, 0.0036)], 8, 6,
                            fwd=rot @ V(0, -1, 0), slot='metal'))
    return out

# ------------------------------------------------------------------ rammer / sponge staff
def rammer(hi=False):
    import char_rig as R
    T = lambda p: R.REST['prop'] @ V(p)
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    out = [limb('ramstaff', [(0, T((0, -0.95, 0))), (1, T((0, 1.55, 0)))], [(0, 0.017, 0.017, 0.017), (1, 0.016, 0.016, 0.016)],
                8 if hi else 3, 10 if hi else 6, fwd=up, slot='wood')]
    out.append(limb('ramhead', [(0, T((0, 1.55, 0))), (0.15, T((0, 1.57, 0))), (1, T((0, 1.70, 0)))],
                    [(0, 0.024, 0.024, 0.024), (0.15, 0.056, 0.056, 0.056), (1, 0.056, 0.056, 0.056)], 6 if hi else 2, 16 if hi else 8,
                    fwd=up, slot='wood'))
    out.append(limb('sponge', [(0, T((0, -0.95, 0))), (0.1, T((0, -0.97, 0))), (0.9, T((0, -1.10, 0))), (1, T((0, -1.12, 0)))],
                    [(0, 0.022, 0.022, 0.022), (0.1, 0.060, 0.060, 0.060), (0.9, 0.062, 0.062, 0.062), (1, 0.040, 0.040, 0.040)],
                    8 if hi else 3, 16 if hi else 8, fwd=up, slot='sponge'))
    if hi:
        for y in (1.535, -0.935):   # iron ferrules
            out.append(limb('ramstaff.fer', [(0, T((0, y - 0.012, 0))), (1, T((0, y + 0.012, 0)))], [(0, 0.0195, 0.0195, 0.0195)], 1, 10,
                            fwd=up, slot='steel'))
    return out

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'coat'); parts.append(cb)
    parts += coat_tails(hi)
    parts += V3P.leg_hems(body_tree, lambda x, y: GAITER_TOP, hi, z0=0.46)   # real gaiter top edge (smooth hem)
    cb = C.crossbelt(body_tree, -1, hi, width=0.056, off=0.0105); cb.name = 'beltx'   # own bake group at the crossing
    parts += [cb, C.crossbelt(body_tree, 1, hi, width=0.040)]
    parts += epaulettes(body_tree, hi) + sabre(hi) + pouch(hi) + shako(hi) + rammer(hi)
    if hi: parts += buttons(body_tree)
    return parts
C.build_kit = build_kit
