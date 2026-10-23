"""Eras v3 kit 1: French line grenadier, c.1806-1812 (docs/char/ERAS_PROGRESS.md). Patches char_v2 (loaded by
char_v2_build.py when V3_KIT=kit_c19_grenadier). Only the base human (MakeHuman head / eyes / hands, ear fix), the body
cage, rig and material library are shared; every garment / item here is built fresh for this kit:
  * pre-1812 habit: square-cut white lapels piped red ending at the waist, skirts cut away below them over a white
    waistcoat, long tails to the back of the knee with red turnbacks + white grenade badges, vertical pocket flaps
  * red cuffs with white three-button cuff flaps; red fringed epaulettes with crescents
  * bonnet a poil (bearskin): fur cap with brass front plate, white cords + flounders, red plume (left), red top patch
    with a white cross
  * sabre-briquet in a black scabbard with brass fittings + red sword knot, bayonet frog; cartridge box with a brass
    grenade; calfskin knapsack with a ticking-covered greatcoat roll
  * knee gaiters with the heart-shaped front cut; moustache (grenadier custom)"""
import math, bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import char_v2 as C
from char_v2 import V, ss, lerp, gauss, limb, ring, grid_sweep, superellipsoid, set_slot

C.KID = 'v3_c19_grenadier'
C.SLOT_MAT.update({'fur': 'fur', 'gold': 'brass', 'scabbard': 'leather', 'sash': 'wool'})
C.KIT_RULES = [(('bsk', 'mous'), 'head'), (('epaul', 'fringe'), 'transfer'),
               (('sabre', 'sbhilt', 'sbknot', 'bayscab', 'frog'), 'hips'), (('gpack', 'groll', 'gstrap'), 'chest'),
               (('gcart',), 'hips')]

# ------------------------------------------------------------------ habit (body shell slots)
LAP_W = 0.090            # square-cut lapels, constant width
LAP_Z0, LAP_Z1 = 1.09, 1.41

def body_slot(p, part):
    x, y, z = p; ax = abs(x)
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'collar'
    if part == 'arm':
        if z < 0.968:
            return 'cuff'
        if z < 1.035 and y < -0.012:   # white cuff flap on the back of the sleeve
            return 'lapel'
        return 'coat'
    if part == 'leg':
        # knee gaiters: top higher at the back, heart-shaped dip at the front of the knee
        top = 0.585 - 0.03 * ss(0.0, 0.05, y) * math.exp(-((x - math.copysign(0.10, x)) / 0.03) ** 2)
        if z < top: return 'gaiter'
        return 'breeches'
    if z > 1.586: return 'skin'
    if z > 1.49: return 'stock'
    if y > 0.02:
        if LAP_Z0 < z < LAP_Z1 + 0.02 and ax < LAP_W:
            if ax > LAP_W - 0.007 or z < LAP_Z0 + 0.007: return 'piping'
            return 'lapel'
        cut = lerp(LAP_W, 0.175, ss(LAP_Z0, 0.90, z))   # skirts cut away below the lapels: waistcoat shows in a widening V
        if 0.90 < z <= LAP_Z0 + 0.001 and ax < cut: return 'waist'
        if z <= 0.90: return 'breeches'
        return 'coat'
    if z < 0.90 and ax < 0.2: return 'breeches'
    return 'coat'
C.body_slot = body_slot

def coat_tails(hi=False):
    """long habit tails (to the back of the knee), red turnbacks with a white grenade, vertical pocket flaps."""
    out = []
    nz, nw = (32, 12) if hi else (6, 3)
    Z0, Z1 = 1.04, 0.50
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            t = i / nz; z = lerp(Z0, Z1, t)
            yb = lerp(-0.118, -0.152, ss(1.04, 0.93, z)); yb = lerp(yb, -0.100, ss(0.90, 0.52, z))
            xc = s * lerp(0.088, 0.058, t); hw = lerp(0.088, 0.044, t)
            th = 0.012
            outer, inner = [], []
            for j in range(nw + 1):
                w = -1 + 2 * j / nw; x = xc + s * w * hw
                y = yb - 0.022 * (1 - w * w) * 0.5 + 0.014 * ss(0.10, 0.19, abs(x))
                outer.append(V(x, y, z)); inner.append(V(x, y + th, z))
            secs.append(outer + inner[::-1])
        o = grid_sweep('tail', secs, cap0=True, cap1=True)
        def tslot(p, s=s):
            ax = abs(p.x)
            if p.z > 0.97: return 'coat'
            k = (p.z - Z1) / (0.97 - Z1)
            edge = 0.130 - 0.055 * (1.0 - k)   # turnback: inner part of the tail, widening downwards
            if ax < edge:
                gc = V(s * lerp(0.052, 0.040, 0.0), 0, 0.585)   # grenade badge low on the turnback
                d = math.hypot(ax - 0.050, p.z - 0.585)
                if d < 0.016 or (abs(ax - 0.050) < 0.006 * (1 - (p.z - 0.60) / 0.035) and 0.60 < p.z < 0.635): return 'lapel'
                return 'turnback'
            if 0.70 < p.z < 0.93 and abs(ax - 0.150) < 0.010: return 'piping'   # vertical pocket flap ('en long')
            return 'coat'
        set_slot(o, tslot)
        out.append(o)
    return out
C.coat_tails = coat_tails

def buttons(tree):
    out = []
    def on_body(x, z, r=0.0075, slot='metal', d=+1, y0=0.0):
        hit = tree.ray_cast(V(x, 0.5 * d + y0, z), V(0, -d, 0))
        if hit[0] is None: return
        p, n = hit[0], hit[1]
        out.append(superellipsoid('button', p + n * 0.0015, (r, r, 0.0028), e=(2, 2.6), n=(14, 6),
                                  rot=n.to_track_quat('Z', 'Y').to_matrix(), slot=slot))
    for i in range(7):   # lapels: 7 a side, square cut
        z = lerp(1.385, 1.115, i / 6)
        for sx in (1, -1): on_body(sx * (LAP_W - 0.016), z)
    for i in range(5): on_body(0.0, lerp(1.07, 0.93, i / 4), 0.0055)   # waistcoat, visible in the cut-away
    return out
C.buttons = buttons

# ------------------------------------------------------------------ epaulettes
def _top(tree, x, y):
    hit = tree.ray_cast(V(x, y, 1.75), V(0, 0, -1))
    return hit[0], hit[1]

def epaulettes(tree, hi=False):
    out = []
    for s in (1, -1):
        # strap: collar -> shoulder point, laid on the coat
        n = 16 if hi else 5
        secs = []
        for i in range(n + 1):
            t = i / n; x = s * lerp(0.068, 0.168, t)
            p, nr = _top(tree, x, -0.006)
            if p is None: continue
            w = lerp(0.034, 0.044, t); th = 0.004
            sd = V(0, 1, 0)
            secs.append([p + nr * 0.0015 + sd * w / 2, p + nr * 0.0015 - sd * w / 2, p + nr * (0.0015 + th) - sd * w / 2, p + nr * (0.0015 + th) + sd * w / 2])
        out.append(grid_sweep('epaul.strap', secs, closed_u=True, slot='epaulette'))
        # crescent pad at the shoulder point, tilted with the shoulder slope
        c, nr = _top(tree, s * 0.188, -0.008)
        rot = nr.to_track_quat('Z', 'Y').to_matrix()
        cres = superellipsoid('epaul.cres', c + nr * 0.008, (0.040, 0.050, 0.010), e=(2.3, 2.2), n=(28, 10) if hi else (10, 4),
                              rot=rot, slot='epaulette')
        out.append(cres)
        # fringe: hangs from the outer half of the crescent over the deltoid
        m = 40 if hi else 10
        ring_top, ring_bot = [], []
        for k in range(m + 1):
            a = math.radians(-115 + 230 * k / m)      # around the outward (+x*s) direction
            d = V(s * math.cos(a), math.sin(a) * 1.18, 0)
            top = c + nr * 0.004 + V(d.x * 0.040, d.y * 0.044, 0)
            bot = top + V(d.x * 0.014, d.y * 0.010, -0.050 + 0.010 * (1 - math.cos(a)))
            ring_top.append(top); ring_bot.append(bot)
        if hi:   # individual twisted bullion cords
            for k in range(m + 1):
                out.append(limb('fringe', [(0, ring_top[k]), (1, ring_bot[k])], [(0, 0.0034, 0.0034, 0.0034), (1, 0.0028, 0.0028, 0.0028)],
                                4, 6, fwd=V(s, 0, 0), slot='epaulette'))
        else:    # thin two-sided skirt
            secs = []
            for k in range(m + 1):
                o = (ring_bot[k] - c); o.z = 0; o = o.normalized() * 0.004
                secs.append([ring_top[k] + o, ring_bot[k] + o, ring_bot[k] - o, ring_top[k] - o])
            out.append(grid_sweep('fringe', secs, closed_u=True, cap0=True, cap1=True, slot='epaulette'))
    return out

# ------------------------------------------------------------------ bearskin
BSK_BASE = V(0, 0.030, 1.708)
BSK_H = 0.300
BSK_PROF = [(0.0, 0.086, 0.106, 0.098), (0.12, 0.096, 0.114, 0.106), (0.45, 0.110, 0.124, 0.118), (0.75, 0.114, 0.124, 0.120),
            (0.88, 0.104, 0.112, 0.110), (0.95, 0.080, 0.086, 0.086), (1.0, 0.0, 0.0, 0.0)]
BSK_TILT = Matrix.Rotation(math.radians(-5), 3, 'X')

def _bsk_T(p):
    return BSK_BASE + BSK_TILT @ (p - BSK_BASE)

def _plate(x, t):   # brass front plate region (front, lower half, arched top)
    return abs(x) < 0.062 * (1 - 0.35 * t) and t < 0.30 - 0.06 * (x / 0.06) ** 2

def bearskin(hi=False):
    nu = 200 if hi else 22
    ts = [i / 120 for i in range(121)] if hi else [0.0, 0.08, 0.3, 0.55, 0.78, 0.9, 0.97]
    secs = []
    for t in ts:
        rx, rf, rb = C.interp_prof(BSK_PROF, t)
        if t > 0.95: k = math.sqrt(max(0.0, 1 - ((t - 0.95) / 0.05) ** 2)); rx, rf, rb = 0.080 * k, 0.086 * k, 0.086 * k
        z = BSK_BASE.z + BSK_H * t
        def fur(p, a, t=t):
            if not hi or t < 0.01: return p
            q = p - V(0, BSK_BASE.y, p.z)
            if _plate(q.x, t) and q.y > 0: return p + q.normalized() * 0.003   # smooth raised plate
            # downward-flowing fur clumps: |sin|^0.6 ridges, phase-warped
            u = a * 30 + 2.6 * math.sin(t * 9.0 + a * 3) + 1.5 * math.sin(a * 7 + t * 23)
            v = a * 71 + 4 * math.sin(t * 31 + a * 5)
            d = 0.0045 * (abs(math.sin(u)) ** 0.6 - 0.5) + 0.0016 * (abs(math.sin(v)) ** 0.8 - 0.5)
            d *= ss(0.0, 0.04, t)
            return p + q.normalized() * d
        secs.append([_bsk_T(p) for p in ring(V(0, BSK_BASE.y, z), V(1, 0, 0), V(0, 1, 0), rx, rf, rb, nu, 2.0, 0.5, fur)])
    body = grid_sweep('bsk', secs, cap0=True, cap1=True)
    inv = BSK_TILT.inverted()
    def bslot(p):
        q = inv @ (p - BSK_BASE); t = q.z / BSK_H
        if q.y > 0.04 and _plate(q.x, t): return 'metal'
        if t > 0.86 and q.y < -0.02 and abs(q.x) < 0.07:   # red top patch at the back, white cross
            if abs(q.x) < 0.007 or abs(t - 0.93) < 0.012: return 'lapel'
            return 'collar'
        return 'fur'
    set_slot(body, bslot)
    out = [body]
    # cords: festoon across the front above the plate, flounders + tassels on the right
    nseg = 40 if hi else 8
    path = []
    for k in range(nseg + 1):
        a = math.radians(-160 + 140 * k / nseg)   # left side round the front to the right side
        t = 0.40 - 0.10 * math.sin(math.radians(-160 + 140 * k / nseg) * -1 + 0.0) * 0.0 - 0.08 * math.sin(math.pi * k / nseg)
        rx, rf, rb = C.interp_prof(BSK_PROF, t)
        r = 1.0 if hi else 1.0
        q = V(math.cos(a) * (rx + 0.004), BSK_BASE.y + math.sin(a) * -1 * (rf + 0.004), BSK_BASE.z + BSK_H * t)
        path.append((k / nseg, _bsk_T(q)))
    path = [(t, V(-p.x, p.y, p.z)) if False else (t, p) for t, p in path]
    out.append(limb('bskcord', path, [(0, 0.0042, 0.0042, 0.0042)], 60 if hi else 8, 8 if hi else 4, fwd=V(0, 0, 1), slot='belt'))
    rs = path[-1][1]
    for k, dz in enumerate((0.0, 0.012)):
        a = rs + V(0.006, -0.01 * k, -dz)
        out.append(limb('bskcord.fl', [(0, a), (1, a + V(0.012, -0.004, -0.075))], [(0, 0.005, 0.005, 0.005), (0.8, 0.006, 0.006, 0.006), (1, 0.010, 0.010, 0.010)],
                        10 if hi else 3, 8 if hi else 4, fwd=V(0, 1, 0), slot='belt'))
    # plume: red, on the left side, rising from a cockade
    pa = _bsk_T(V(-0.112, BSK_BASE.y + 0.020, BSK_BASE.z + 0.12))
    out.append(limb('bskplume', [(0, pa), (0.5, pa + V(-0.012, -0.006, 0.12)), (1, pa + V(-0.010, -0.012, 0.25))],
                    [(0, 0.011, 0.011, 0.011), (0.25, 0.022, 0.022, 0.022), (0.7, 0.020, 0.020, 0.020), (1, 0.003, 0.003, 0.003)],
                    24 if hi else 6, 16 if hi else 6, fwd=V(1, 0, 0), slot='plume'))
    out.append(superellipsoid('bskcock', pa + V(-0.006, 0.004, -0.006), (0.006, 0.020, 0.020), e=(2, 2), n=(14, 6) if hi else (8, 3),
                              slot='lapel'))
    if hi:   # grenade relief on the plate
        c = _bsk_T(V(0, BSK_BASE.y + 0.126, BSK_BASE.z + 0.050))
        out.append(superellipsoid('bskgren', c, (0.013, 0.004, 0.013), e=(2, 2), n=(16, 8), slot='metal'))
        for dx in (-0.007, 0.0, 0.007):
            out.append(limb('bskgren.f', [(0, c + V(dx, 0, 0.010)), (1, c + V(dx * 1.8, 0.0, 0.034 - abs(dx)))],
                            [(0, 0.004, 0.0025, 0.0025), (1, 0.0008, 0.0008, 0.0008)], 6, 6, fwd=V(0, 1, 0), slot='metal'))
    return out

# ------------------------------------------------------------------ moustache
def moustache(hi=False):
    import human_mh as HM
    ph = HM.posed(); h = HM.part('_mtmp', HM.head_faces(ph), ph)
    bm = bmesh.new(); bm.from_mesh(h.data); tree = BVHTree.FromBMesh(bm); bm.free(); bpy.data.objects.remove(h)
    n = 24 if hi else 8
    secs = []
    for i in range(n + 1):
        x = lerp(-0.036, 0.036, i / n); ax = abs(x)
        z = 1.609 - 0.012 * ss(0.012, 0.036, ax) + 0.002 * gauss(x, 0.006)
        hit = tree.ray_cast(V(x, 0.3, z), V(0, -1, 0))
        if hit[0] is None: continue
        p, nr = hit[0], hit[1]
        k = 1.0 - ss(0.016, 0.036, ax)
        hgt = lerp(0.0025, 0.0085, k); th = lerp(0.0012, 0.0042, k)
        up = V(0, 0, 1); up = (up - nr * up.dot(nr)).normalized()
        b = p + nr * 0.0006
        secs.append([b + up * hgt * 0.5, b + up * hgt * 0.5 + nr * th * 0.6, b - up * hgt * 0.5 + nr * th, b - up * hgt * 0.5])
    return [grid_sweep('mous', secs, closed_u=True, slot='hair')]

# ------------------------------------------------------------------ sabre-briquet + bayonet frog, cartridge box, knapsack
def sabre(hi=False):
    a = V(-0.162, -0.035, 0.985)
    path = [(0, a), (0.5, V(-0.178, -0.105, 0.715)), (1, V(-0.186, -0.185, 0.445))]
    sc = limb('sabre', path, [(0, 0.012, 0.019, 0.019), (0.9, 0.010, 0.015, 0.015), (1, 0.008, 0.010, 0.010)], 12 if hi else 4,
              10 if hi else 5, fwd=V(1, 0, 0), slot='scabbard', e=2.6)
    out = [sc]
    def band(t0, t1, nm):
        p0, _ = C.path_frame(path, t0); p1, _ = C.path_frame(path, t1)
        return limb(nm, [(0, p0), (1, p1)], [(0, 0.0135, 0.021, 0.021)], 1, 10 if hi else 5, fwd=V(1, 0, 0), slot='metal', e=2.6)
    out += [band(0.0, 0.07, 'sabre.throat'), band(0.90, 1.0, 'sabre.chape')]
    if hi: out.append(band(0.45, 0.48, 'sabre.ring'))
    # brass hilt: grip forward-up from the throat, knuckle bow, pommel
    g0 = a + V(0.0, 0.010, 0.020); g1 = g0 + V(0.0, 0.040, 0.105)
    out.append(limb('sbhilt', [(0, g0), (1, g1)], [(0, 0.013, 0.011, 0.011), (0.5, 0.014, 0.012, 0.012), (1, 0.012, 0.010, 0.010)],
                    6 if hi else 2, 10 if hi else 5, fwd=V(1, 0, 0), slot='metal'))
    bow = [(0, g0 + V(0, 0.018, -0.002)), (0.5, g0 + V(0, 0.050, 0.055)), (1, g1 + V(0, 0.010, 0.004))]
    out.append(limb('sbhilt.bow', bow, [(0, 0.0045, 0.0045, 0.0045)], 12 if hi else 4, 6 if hi else 4, fwd=V(1, 0, 0), slot='metal'))
    # red sword knot looped on the hilt, tassel hanging outside the scabbard
    k0 = g1 + V(-0.012, 0.0, -0.01)
    out.append(limb('sbknot', [(0, k0), (0.6, k0 + V(-0.010, 0.006, -0.10)), (1, k0 + V(-0.012, 0.004, -0.13))],
                    [(0, 0.004, 0.004, 0.004), (0.7, 0.005, 0.005, 0.005), (0.78, 0.012, 0.012, 0.012), (1, 0.016, 0.016, 0.016)],
                    10 if hi else 4, 8 if hi else 4, fwd=V(1, 0, 0), slot='plume'))
    # bayonet in its scabbard in the same frog, in front of the sabre
    b0 = V(-0.150, 0.000, 0.975)
    out.append(limb('bayscab', [(0, b0), (1, b0 + V(-0.012, -0.040, -0.37))], [(0, 0.010, 0.012, 0.012), (1, 0.005, 0.006, 0.006)],
                    6 if hi else 2, 8 if hi else 4, fwd=V(1, 0, 0), slot='scabbard'))
    out.append(superellipsoid('frog', V(-0.160, -0.018, 0.965), (0.010, 0.040, 0.030), e=(4, 4), n=(12, 6) if hi else (6, 3), slot='belt'))
    return out

def cartbox(hi=False):
    rot = Matrix.Rotation(math.radians(-16), 3, 'Z')
    c = V(0.100, -0.186, 0.968)
    out = [superellipsoid('gcart', c, (0.106, 0.036, 0.070), e=(5.5, 5.5), n=(18, 10) if hi else (8, 4), rot=rot, slot='cartbox')]
    if hi:   # flap edge + brass grenade badge on the flap
        out.append(superellipsoid('gcart.flap', c + rot @ V(0, -0.037, 0.012), (0.104, 0.004, 0.058), e=(6, 6), n=(20, 8), rot=rot, slot='cartbox'))
        g = c + rot @ V(0, -0.043, 0.004)
        out.append(superellipsoid('gcart.gren', g, (0.012, 0.004, 0.012), e=(2, 2), n=(16, 8), rot=rot, slot='metal'))
        for dx in (-0.006, 0.0, 0.006):
            out.append(limb('gcart.f', [(0, g + rot @ V(dx, 0, 0.009)), (1, g + rot @ V(dx * 1.8, 0, 0.030 - abs(dx)))],
                            [(0, 0.0035, 0.002, 0.002), (1, 0.0008, 0.0008, 0.0008)], 6, 6, fwd=rot @ V(0, -1, 0), slot='metal'))
    return out

def knapsack(hi=False):
    n = (26, 16) if hi else (10, 6)
    pack = superellipsoid('gpack', V(0, -0.152, 1.255), (0.158, 0.058, 0.150), e=(6.0, 5.0), n=n, slot='knapsack')
    roll = limb('groll', [(0, V(-0.185, -0.146, 1.452)), (1, V(0.185, -0.146, 1.452))],
                [(0, 0.028, 0.028, 0.028), (0.05, 0.046, 0.046, 0.046), (0.95, 0.046, 0.046, 0.046), (1, 0.028, 0.028, 0.028)],
                14 if hi else 4, 18 if hi else 8, fwd=V(0, 0, 1), slot='roll')
    out = [pack, roll]
    for x in ((-0.12, 0.0, 0.12) if hi else (-0.12, 0.12)):   # three roll straps
        out.append(limb('gstrap', [(0, V(x, -0.146, 1.452 - 0.001)), (1, V(x + 0.0001, -0.146, 1.452 + 0.001))],
                        [(0, 0.049, 0.049, 0.049)], 1, 12 if hi else 6, fwd=V(0, 1, 0), slot='belt'))
    if hi:
        out.append(superellipsoid('gpack.flap', V(0, -0.212, 1.31), (0.156, 0.007, 0.096), e=(7, 7), n=(26, 8), slot='knapsack'))
        for x in (-0.085, 0.085):
            out.append(limb('gpack.strap', [(0, V(x, -0.221, 1.40)), (1, V(x, -0.219, 1.19))], [(0, 0.012, 0.0025, 0.0025)], 8, 6,
                            fwd=V(0, 1, 0), slot='cartbox'))
            out.append(superellipsoid('gpack.buckle', V(x, -0.224, 1.205), (0.013, 0.003, 0.011), e=(6, 6), n=(10, 4), slot='metal'))
    return out

# ------------------------------------------------------------------ assembly
def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, 'collar'); parts.append(cb)
    parts += coat_tails(hi)
    parts += [C.crossbelt(body_tree, 1, hi), C.crossbelt(body_tree, -1, hi, off=0.0105)]
    parts += epaulettes(body_tree, hi)
    parts += knapsack(hi) + cartbox(hi) + sabre(hi) + bearskin(hi) + moustache(hi) + C.musket(hi)
    if hi: parts += buttons(body_tree)
    return parts
C.build_kit = build_kit
