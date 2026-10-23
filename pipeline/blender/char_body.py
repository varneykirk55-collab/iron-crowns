"""Character refinement: shared semi-realistic body + swappable Napoleonic kit (c19).
One body mesh (torso/coat, arms, hands, legs, shoes, head) used by every foot model; kit parts (lapels, tails,
belts, cartridge box, knapsack, shako / bearskin / bicorne, musket+bayonet / rammer, sabre) are added per unit type.
Faces carry a palette SLOT (colour comes from a per-nation palette texture in Godot, UV.x = (slot+0.5)/32) and a
material class (common.MAT_*, UV.y = mat/16). Team mask (legacy tint path) = coat only, in UV2.y."""
import math
from mathutils import Vector, Matrix, Euler
from char_geo import V, CharMesh, Chain, Part, fixed, mix_w, smoothstep, lerp
import char_rig as R

MAT_DEFAULT, MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_BRASS, MAT_SKIN, MAT_WOOD, MAT_PIPECLAY, MAT_HIDE, MAT_FUR, MAT_IRON, MAT_HAIR = range(12)
MAT_CANVAS = 13

SLOT_NAMES = ['coat', 'lapel', 'collar', 'cuff', 'turnback', 'waist', 'breeches', 'gaiter', 'shoe', 'plume', 'felt',
              'metal', 'belt', 'cartbox', 'knapsack', 'roll', 'skin', 'hair', 'eye', 'mouth', 'wood', 'steel',
              'epaulette', 'fur', 'stock', 'button', 'gold', 'sash', 'boot', 'sponge', 'scabbard', 'piping']
S = {n: i for i, n in enumerate(SLOT_NAMES)}
# default palette: French line infantry, 1810 (nation palettes override coat/facings/etc. in battle_visuals.gd)
PALETTE = {
    'coat': '#24408a', 'lapel': '#e9e6dc', 'collar': '#b5261f', 'cuff': '#b5261f', 'turnback': '#b5261f',
    'waist': '#e9e6dc', 'breeches': '#e4e0d4', 'gaiter': '#1c1c1e', 'shoe': '#161515', 'plume': '#c8302a',
    'felt': '#19191b', 'metal': '#b8913a', 'belt': '#eeede6', 'cartbox': '#1b1817', 'knapsack': '#80603e',
    'roll': '#77716a', 'skin': '#d8a587', 'hair': '#3a291d', 'eye': '#1a1311', 'mouth': '#8c4c45',
    'wood': '#5e3d24', 'steel': '#a2a8ae', 'epaulette': '#b5261f', 'fur': '#141313', 'stock': '#111111',
    'button': '#c9a54a', 'gold': '#d2ab45', 'sash': '#b5261f', 'boot': '#121212', 'sponge': '#d8cfbf',
    'scabbard': '#1f1b18', 'piping': '#b5261f'}

LODS = {0: dict(torso=12, limb=8, leg=8, head=(14, 10), hand=7, feat=True, detail=True),
        1: dict(torso=6, limb=4, leg=5, head=(6, 5), hand=4, feat=False, detail=False, lean=True),
        2: dict(torso=8, limb=6, leg=6, head=(8, 6), hand=5, feat=False, detail=False)}
# 2 = mid set (stage 9, ~1.2-1.5k tris: line 1368, grenadier 1470, artillery 1352, officer 1198): full silhouette and
# tails without the LOD0 face / hand / lining detail; stored inside the LOD0 asset between the near and far sets.
# lean (stage 7, LOD1 500-800 tris): fewer torso / arm / leg rings, no thumb or hat lining, lighter tails, stock and hat
# trims; the silhouette parts (shako / bearskin / bicorne, knapsack + roll, musket + bayonet, crossbelts) all stay.
LEAN_TORSO_Z = [0.835, 0.99, 1.10, 1.24, 1.375, 1.43, 1.495]

def P(slot, mat, team=0.0, smooth=True):
    if isinstance(slot, str):
        slot = S[slot]
    return Part(slot, mat, team, smooth)

# ---------------------------------------------------------------- torso surface
# (z, rx, ry, yc) super-ellipse rings, exponent EXP (boxier than an ellipse: chest + shoulders)
TORSO = [(0.835, 0.12, 0.085, 0.0), (0.88, 0.158, 0.112, -0.006), (0.95, 0.166, 0.118, -0.012),
         (1.02, 0.153, 0.106, 0.0), (1.10, 0.150, 0.104, 0.006), (1.20, 0.161, 0.110, 0.012),
         (1.30, 0.176, 0.117, 0.014), (1.375, 0.184, 0.112, 0.008), (1.43, 0.168, 0.096, -0.004),
         (1.465, 0.105, 0.074, -0.006), (1.495, 0.064, 0.058, 0.0)]
EXP = 2.6

def torso_ring(z):
    for a, b in zip(TORSO, TORSO[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0]); t = t * t * (3 - 2 * t) * 0.5 + t * 0.5
            return tuple(lerp(a[i], b[i], t) for i in range(4))
    return TORSO[0] if z < TORSO[0][0] else TORSO[-1]

def sexp(c, s, e):
    """super-ellipse point for angle with cos c, sin s"""
    f = lambda x: math.copysign(abs(x) ** (2.0 / e), x)
    return f(c), f(s)

def torso_pt(ang, z, off=0.0):
    _, rx, ry, yc = torso_ring(z)
    cx, sy = sexp(math.cos(ang), math.sin(ang), EXP)
    p = V(rx * cx, yc + ry * sy, z)
    n = V(cx / max(rx, 1e-3), sy / max(ry, 1e-3), 0).normalized()
    return p + n * off, n

def torso_pt_x(x, z, front=True, off=0.0):
    """point on the torso surface with given x (front or back)"""
    _, rx, ry, yc = torso_ring(z)
    u = max(-0.985, min(0.985, x / rx))
    # invert the super-ellipse: cos^(2/e) = u
    c = math.copysign(abs(u) ** (EXP / 2.0), u)
    s = math.sqrt(max(0.0, 1 - c * c)) * (1 if front else -1)
    return torso_pt(math.atan2(s, c), z, off)

TORSO_CHAIN = Chain([('hips', (0, 0, 0.80), (0, 0, 1.06)), ('spine', (0, 0, 1.06), (0, 0, 1.26)),
                     ('chest', (0, 0, 1.26), (0, 0, 1.47)), ('neck', (0, 0, 1.47), (0, 0, 1.6))],
                    blends=[0.05, 0.06, 0.03])

def torso_w(p):
    w = TORSO_CHAIN(p)
    ax = abs(p.x)
    k = smoothstep(0.10, 0.175, ax) * smoothstep(1.32, 1.42, p.z) * 0.55
    if k > 0:
        w = mix_w(w, {'clav.R' if p.x > 0 else 'clav.L': 1.0}, k)
    # buttocks / crotch follow the thighs a little
    kl = smoothstep(0.93, 0.84, p.z) * 0.45 * smoothstep(0.02, 0.09, ax)
    if kl > 0:
        w = mix_w(w, {'thigh.R' if p.x > 0 else 'thigh.L': 1.0}, kl)
    return w

def side(p_or_x, r, l):
    x = p_or_x if isinstance(p_or_x, (int, float)) else p_or_x.x
    return r if x > 0 else l

def mirror_pts(pts):
    return [V(-p[0], p[1], p[2]) for p in pts]

# ---------------------------------------------------------------- body
def build_torso(m, L, coat_bottom=1.0, slots=None):
    segs = L['torso']
    zs = [r[0] for r in TORSO]
    extra = [0.985, 1.06, 1.16, 1.25, 1.34, 1.405, 1.45] if L['detail'] else [0.99, 1.24, 1.40]
    zs = sorted(set(zs + extra))
    if L.get('lean'):
        zs = LEAN_TORSO_Z
    rings = []
    for z in zs:
        ring = []
        for j in range(segs):
            a = 2 * math.pi * j / segs + math.pi / segs
            ring.append(torso_pt(a, z)[0])
        rings.append(ring)
    def slot(c):
        if c.z < coat_bottom and not (slots and slots.get('long_coat')):
            return (S['breeches'], MAT_WOOL)
        return (S['coat'], MAT_WOOL)
    part = P('coat', MAT_WOOL, 1.0)
    part.slot = slot
    # team amount only on coat faces: encode via a wrapper part per face
    m.loft(rings, TeamPart(slot), torso_w, cap0=True, cap1=True)

class TeamPart(Part):
    """part whose slot fn decides; team = 1 for coat faces"""
    def __init__(self, slotfn, smooth=True):
        super().__init__(slotfn, MAT_WOOL, 0.0, smooth)

def build_neck_head(m, L, kind):
    hw = fixed('head')
    # neck
    m.tube([(0, -0.004, 1.44), (0, 0.004, 1.53), (0, 0.012, 1.60)], [0.05, 0.047, 0.045], L['limb'],
           P('skin', MAT_SKIN), Chain([('neck', (0, 0, 1.44), (0, 0.012, 1.575)), ('head', (0, 0.012, 1.575), (0, 0.012, 1.8))], 0.03),
           cap0=False, cap1=False, scale_x=1.1)
    segs, rings = L['head']
    if L.get('lean'):
        rings = 4
    c = V(0, 0.016, 1.655)
    def shape(th, ph, p):
        x, y, z = p
        zc = math.cos(ph)
        if zc < -0.1:       # jaw: narrower, chin forward
            k = smoothstep(-0.1, -0.9, zc)
            x *= 1 - 0.22 * k
            if y > 0:
                y *= 1 + 0.08 * k
        if y > 0:           # flatter face
            y *= 0.93 if zc > -0.2 else 1.0
        else:               # rounder skull back
            y *= 1.05
            z += 0.004
        return V(x, y, z)
    def head_slot(cc):
        lp = cc - c
        if kind.get('bald_front') is False:
            pass
        if lp.z > 0.035 and lp.y < 0.075:
            return (S['hair'], MAT_HAIR)
        if lp.y < -0.035 and lp.z > -0.05:
            return (S['hair'], MAT_HAIR)
        if abs(lp.x) > 0.06 and lp.y < 0.035 and lp.z > -0.035 and lp.y > -0.04:
            return (S['hair'], MAT_HAIR)   # sideburns
        return (S['skin'], MAT_SKIN)
    hp = P('skin', MAT_SKIN); hp.slot = head_slot
    m.ellipsoid(c, (0.077, 0.096, 0.114), segs, rings, hp, hw, shape=shape)
    # nose, ears
    nose = [(0, 0.104, 1.675), (0, 0.118, 1.648), (0, 0.112, 1.636)]
    if not L.get('lean'):
        m.tube(nose, [0.011, 0.014, 0.010], 4 if L['feat'] else 3, P('skin', MAT_SKIN), hw, scale_x=0.8, phase=0.5)
    if L['feat']:
        for sx in (1, -1):
            m.ellipsoid(V(0.077 * sx, 0.004, 1.652), (0.012, 0.022, 0.03), 6, 3, P('skin', MAT_SKIN), hw)
            # eyes (dark almond) + brows
            m.ellipsoid(V(0.031 * sx, 0.094, 1.673), (0.013, 0.006, 0.0065), 6, 3, P('eye', MAT_DEFAULT), hw)
            m.box((0.03, 0.012, 0.008), Matrix.Translation(V(0.032 * sx, 0.097, 1.69)) @ Euler((0, math.radians(-8 * sx), 0)).to_matrix().to_4x4(),
                  P('hair', MAT_HAIR, smooth=False), hw)
        m.box((0.03, 0.008, 0.007), Matrix.Translation(V(0, 0.104, 1.608)), P('mouth', MAT_SKIN, smooth=False), hw)
        if kind.get('moustache'):
            for sx in (1, -1):
                m.tube([(0.004 * sx, 0.113, 1.626), (0.024 * sx, 0.108, 1.62), (0.036 * sx, 0.098, 1.606)],
                       [0.007, 0.007, 0.003], 4, P('hair', MAT_HAIR), hw, cap0=False)

def arm_path(sx):
    pts = [(0.135, -0.012, 1.432), (0.178, -0.012, 1.425), (0.192, -0.012, 1.30), (0.205, -0.012, 1.14),
           (0.214, -0.006, 1.02), (0.219, -0.002, 0.965), (0.221, 0.0, 0.915), (0.2215, 0.0, 0.90)]
    return [V(p[0] * sx, p[1], p[2]) for p in pts]

def arm_chain(sx):
    s = 'R' if sx > 0 else 'L'
    b = lambda n: (R.BI[n][1], R.BI[n][2])
    return Chain([('clav.' + s,) + b('clav.' + s), ('upper_arm.' + s,) + b('upper_arm.' + s),
                  ('forearm.' + s,) + b('forearm.' + s), ('hand.' + s,) + b('hand.' + s)], blends=[0.05, 0.05, 0.02])

def build_arms(m, L, kind):
    for sx in (1, -1):
        path = arm_path(sx)
        radii = [0.056, 0.063, 0.054, 0.045, 0.046, 0.053, 0.050, 0.030]
        if L.get('lean'):
            keep = [0, 2, 4, 6, 7]
            path = [path[i] for i in keep]; radii = [radii[i] for i in keep]
        def slot(c, sx=sx):
            if c.z < 0.97:
                return (S['cuff'], MAT_WOOL)
            return (S['coat'], MAT_WOOL)
        pr = P('coat', MAT_WOOL); pr.slot = slot
        ids = m.tube(path, radii, L['limb'], pr, arm_chain(sx), cap0=False, cap1=True, scale_x=1.08)
        build_hand(m, L, sx)
        if kind.get('epaulettes'):
            build_epaulette(m, L, sx, kind['epaulettes'])

def build_hand(m, L, sx):
    s = 'R' if sx > 0 else 'L'
    w = Chain([('forearm.' + s, R.BI['forearm.' + s][1], R.BI['forearm.' + s][2]),
               ('hand.' + s, R.BI['hand.' + s][1], R.BI['hand.' + s][2])], 0.015)
    # mitten: thin across X (palm faces the body), wide along Y; fingers loosely curled forward
    path = [(0.222, 0.0, 0.905), (0.223, 0.004, 0.872), (0.224, 0.012, 0.825), (0.222, 0.026, 0.79), (0.218, 0.036, 0.772)]
    path = [V(p[0] * sx, p[1], p[2]) for p in path]
    rad = [0.024, 0.023, 0.021, 0.017, 0.010]
    sxs = [1.6, 2.0, 2.1, 1.9, 1.5]
    if L.get('lean'):
        path = [path[0], path[3]]; rad = [rad[0], rad[3]]; sxs = [sxs[0], sxs[3]]
    m.tube(path, rad, L['hand'], P('skin', MAT_SKIN), w, cap0=False, cap1=True, scale_x=sxs, up=V(sx, 0, 0))
    if L.get('lean'):
        return
    thumb = [(0.214, 0.022, 0.878), (0.211, 0.04, 0.85), (0.214, 0.046, 0.826)]
    m.tube([V(p[0] * sx, p[1], p[2]) for p in thumb], [0.011, 0.01, 0.007], 5 if L['feat'] else 4, P('skin', MAT_SKIN), fixed('hand.' + s), cap0=False)

def build_epaulette(m, L, sx, slot):
    s = 'R' if sx > 0 else 'L'
    w = lambda p: mix_w({'clav.' + s: 1.0}, {'upper_arm.' + s: 1.0}, 0.45)
    # strap + fringed pad on the shoulder point
    pad = []
    for z, r in (((1.462, 0.050), (1.405, 0.066)) if L.get('lean') else ((1.468, 0.040), (1.462, 0.056), (1.44, 0.062), (1.405, 0.066))):
        pad.append([V(0.19 * sx + math.cos(a) * r * 0.9, -0.012 + math.sin(a) * r, z) for a in
                    [2 * math.pi * j / L['limb'] for j in range(L['limb'])]])
    m.loft(pad, P(slot, MAT_WOOL), w, cap0=True, cap1=False)

def leg_chain(sx):
    s = 'R' if sx > 0 else 'L'
    b = lambda n: (R.BI[n][1], R.BI[n][2])
    return Chain([('thigh.' + s,) + b('thigh.' + s), ('shin.' + s,) + b('shin.' + s), ('foot.' + s,) + b('foot.' + s)],
                 blends=[0.06, 0.02])

def build_legs(m, L, kind):
    gt = kind.get('gaiter_top', 0.575)
    for sx in (1, -1):
        pts = [(0.085, 0.0, 0.985), (0.095, 0.0, 0.925), (0.097, 0.008, 0.80), (0.099, 0.014, 0.66),
               (0.1, 0.016, gt + 0.02), (0.1, 0.016, gt - 0.005), (0.1, 0.014, 0.505), (0.1, 0.0, 0.43),
               (0.1, -0.010, 0.35), (0.1, -0.012, 0.22), (0.1, -0.012, 0.13), (0.1, -0.012, 0.075)]
        pts = [V(p[0] * sx, p[1], p[2]) for p in pts]
        rad = [0.083, 0.092, 0.082, 0.066, 0.056, 0.061, 0.055, 0.056, 0.059, 0.046, 0.039, 0.044]
        if not L['detail']:
            keep = [0, 3, 5, 7, 11] if L.get('lean') else [0, 1, 3, 4, 5, 7, 9, 11]
            pts = [pts[i] for i in keep]; rad = [rad[i] for i in keep]
        def slot(c, gt=gt):
            if c.z > gt:
                return (S['breeches'], MAT_WOOL)
            return (S[kind.get('lower_leg', 'gaiter')], MAT_LEATHER if kind.get('lower_leg') == 'boot' else MAT_CANVAS)
        pr = P('breeches', MAT_WOOL); pr.slot = slot
        m.tube(pts, rad, 4 if L.get('lean') else L['leg'], pr, leg_chain(sx), cap0=False, cap1=True, scale_x=[1.0] * 3 + [1.05] * (len(pts) - 3))
        build_shoe(m, L, sx, kind)

def build_shoe(m, L, sx, kind):
    s = 'R' if sx > 0 else 'L'
    w = lambda p: mix_w({'foot.' + s: 1.0}, {'shin.' + s: 1.0}, 0.35 * smoothstep(0.06, 0.1, p.z) * smoothstep(0.03, -0.04, p.y))
    secs = [(-0.072, 0.034, 0.030, 0.045), (-0.04, 0.042, 0.042, 0.052), (0.03, 0.045, 0.030, 0.04),
            (0.10, 0.047, 0.022, 0.03), (0.15, 0.040, 0.016, 0.022), (0.178, 0.022, 0.011, 0.015)]
    rings = []
    n = L['hand'] - 1 if L['detail'] else (4 if L.get('lean') else L['hand'] + 1)
    if not L['detail']:
        secs = [secs[1], secs[4]] if L.get('lean') else [secs[0], secs[2], secs[5]]
    for y, rx, rz, zc in secs:
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            ring.append(V(0.1 * sx + 0.008 * sx * (y > 0.05) + math.cos(a) * rx, y, max(0.002, zc + math.sin(a) * rz)))
        rings.append(ring)
    m.loft(rings, P(kind.get('shoe_slot', 'shoe'), MAT_LEATHER), w, cap0=True, cap1=True)

# ---------------------------------------------------------------- coat details
def build_lapels(m, L, kind):
    """plastron lapels (front chest), standing collar, turnbacks/tails"""
    nz = 6 if L['detail'] else 3
    nx = 4 if L['detail'] else 2
    if kind.get('lapels', True):
        rows = []
        for i in range(nz + 1):
            z = lerp(1.035, 1.425, i / nz)
            hw = lerp(0.055, 0.112, (i / nz) ** 0.8)
            rows.append([torso_pt_x(lerp(-hw, hw, j / nx), z, True, 0.0065)[0] for j in range(nx + 1)])
        m.loft(rows, P(kind.get('lapel_slot', 'lapel'), MAT_WOOL), torso_w, closed=False)
        if L['detail']:   # two button rows (small brass studs)
            for i in range(1, nz):
                z = lerp(1.035, 1.425, i / nz)
                hw = lerp(0.055, 0.112, (i / nz) ** 0.8) - 0.012
                for sx in (1, -1):
                    p, n = torso_pt_x(hw * sx, z, True, 0.011)
                    m.box((0.011, 0.006, 0.011), Matrix.Translation(p), P('button', MAT_BRASS, smooth=False), torso_w)
    # collar
    segs = L['limb']
    col = []
    for z, r in ((1.45, 0.078), (1.49, 0.07), (1.545, 0.066)):
        col.append([V(math.cos(a) * r, -0.004 + math.sin(a) * r * 0.95, z) for a in [2 * math.pi * j / segs for j in range(segs)]])
    m.loft(col, P('collar', MAT_WOOL), Chain([('chest', (0, 0, 1.3), (0, 0, 1.47)), ('neck', (0, 0, 1.47), (0, 0, 1.6))], 0.04), cap0=False, cap1=False)
    # tails
    tail_bottom = kind.get('tail_bottom', 0.74)
    nv = 5 if L['detail'] else (2 if L.get('lean') else 3)
    nu = 4 if L['detail'] else 2
    for sx in (1, -1):
        a0, a1 = (math.radians(-88), math.radians(-28)) if sx > 0 else (math.radians(-152), math.radians(-92))
        outer, inner = [], []
        for i in range(nv + 1):
            t = i / nv
            z = lerp(1.03, tail_bottom, t)
            zz = max(z, 0.95)
            flare = 1.0 + 0.10 * smoothstep(0.95, tail_bottom, z) + 0.035
            ro, ri = [], []
            for j in range(nu + 1):
                a = lerp(a0, a1, j / nu)
                p, n = torso_pt(a, zz)
                p = V(p.x * flare, p.y * flare - (0.004 if zz > 0.98 else 0.0), z)
                ro.append(p + n * 0.006); ri.append(p - n * 0.006)
            outer.append(ro); inner.append(ri)
        w = lambda p, sx=sx: mix_w(torso_w(p), {'thigh.R' if sx > 0 else 'thigh.L': 1.0}, 0.45 * smoothstep(0.95, 0.74, p.z))
        def oslot(c, sx=sx, a0=a0, a1=a1):
            # outer face: coat in the middle, coloured turnback toward the open edges
            ang = math.atan2(c.y, c.x)
            u = (ang - a0) / (a1 - a0)
            lat = u if sx > 0 else 1 - u
            return (S['turnback'], MAT_WOOL) if (lat > 0.55 and c.z < 0.99) else (S['coat'], MAT_WOOL)
        po = P('coat', MAT_WOOL); po.slot = oslot
        m.loft(outer, po, w, closed=False)
        if not L.get('lean'):   # lean: single-sided tails (cull_disabled shows the back face)
            m.loft([list(reversed(r)) for r in inner], P('turnback', MAT_WOOL), w, closed=False)
            # close the bottom edge
            m.loft([outer[-1], inner[-1]], P('turnback', MAT_WOOL), w, closed=False)

def build_crossbelts(m, L, kind):
    """white buff crossbelts: cartridge belt over left shoulder -> right hip, bayonet/sabre belt over right
    shoulder -> left hip, front and back."""
    W = kind.get('belt_w', 0.052)
    which = kind.get('belts', ('cart', 'bayo'))
    n = 5 if L['detail'] else 2
    for b in which:
        sx = -1 if b == 'cart' else 1          # shoulder side
        pts, nrm = [], []
        # front: hip (opposite side) -> shoulder
        for i in range(n + 1):
            t = i / n
            z = lerp(0.975, 1.43, t)
            x = lerp(-0.14 * sx, 0.115 * sx, t)
            p, nn = torso_pt_x(x, z, True, (0.013 if 1.03 < z < 1.43 else 0.008) + (0 if L['detail'] else 0.012))
            pts.append(p); nrm.append(nn)
        # over the shoulder
        for y, z in (((0.04, 1.465), (-0.01, 1.485), (-0.06, 1.465)) if L['detail'] else ((-0.01, 1.49),)):
            pts.append(V(0.122 * sx, y, z)); nrm.append(V(0, y * 3, 1).normalized())
        for i in range(n + 1):
            t = 1 - i / n
            z = lerp(0.975, 1.43, t)
            x = lerp(-0.14 * sx, 0.115 * sx, t)
            p, nn = torso_pt_x(x, z, False, 0.008 + (0 if L['detail'] else 0.01))
            pts.append(p); nrm.append(nn)
        m.ribbon(pts, nrm, W, P('belt', MAT_PIPECLAY), torso_w, thick=0 if L.get('lean') else -0.005)
    if 'cart' in which:   # cartridge box on the right back hip (+ brass badge)
        mt = Matrix.Translation(V(0.075, -0.135, 0.985)) @ Euler((math.radians(8), 0, math.radians(-22))).to_matrix().to_4x4()
        m.box((0.2, 0.065, 0.125), mt, P('cartbox', MAT_LEATHER, smooth=False), lambda p: mix_w(torso_w(p), {'hips': 1}, 0.6))
        if L['detail']:
            m.box((0.05, 0.01, 0.045), mt @ Matrix.Translation(V(0, -0.036, 0.01)), P('metal', MAT_BRASS, smooth=False), fixed('hips'))
    if 'bayo' in which:
        sab = kind.get('sabre')
        if sab:   # briquet: curved brass-hilted short sabre in black scabbard
            mt = Matrix.Translation(V(-0.17, -0.05, 0.86)) @ Euler((math.radians(-28), math.radians(4), 0)).to_matrix().to_4x4()
            m.box((0.024, 0.04, 0.56), mt @ Matrix.Translation(V(0, 0, -0.18)), P('scabbard', MAT_LEATHER, smooth=False),
                  lambda p: mix_w({'hips': 1}, {'thigh.L': 1}, 0.4 * smoothstep(0.9, 0.6, p.z)), taper=(0.8, 0.8))
            m.box((0.03, 0.06, 0.12), mt @ Matrix.Translation(V(0, 0.0, 0.15)), P('metal', MAT_BRASS, smooth=False), fixed('hips'))
        else:     # bayonet scabbard
            mt = Matrix.Translation(V(-0.165, -0.055, 0.86)) @ Euler((math.radians(-22), math.radians(4), 0)).to_matrix().to_4x4()
            m.box((0.022, 0.03, 0.27), mt @ Matrix.Translation(V(0, 0, -0.05)), P('scabbard', MAT_LEATHER, smooth=False),
                  lambda p: mix_w({'hips': 1}, {'thigh.L': 1}, 0.4 * smoothstep(0.9, 0.7, p.z)), taper=(0.7, 0.7))

def build_knapsack(m, L, kind):
    w = lambda p: mix_w({'chest': 1.0}, {'spine': 1.0}, smoothstep(1.3, 1.12, p.z))
    mt = Matrix.Translation(V(0, -0.162, 1.25)) @ Euler((math.radians(-4), 0, 0)).to_matrix().to_4x4()
    m.box((0.31, 0.12, 0.3), mt, P('knapsack', MAT_HIDE, smooth=False), w, taper=(0.97, 0.95))
    # rolled greatcoat on top
    segs = L['limb']
    m.tube([(-0.17, -0.152, 1.435), (0.0, -0.155, 1.445), (0.17, -0.152, 1.435)], [0.045, 0.048, 0.045], segs,
           P('roll', MAT_WOOL), fixed('chest'), up=V(0, 0, 1))
    if L['detail']:  # roll straps
        for x in (-0.11, 0.11):
            m.tube([(x, -0.147, 1.432), (x, -0.157, 1.45)], 0.052, 6, P('belt', MAT_LEATHER), fixed('chest'), cap0=False, cap1=False)

# ---------------------------------------------------------------- headgear (head-bone, head-space coords)
def head_mtx(dz=0.0, tilt=0.0):
    return Matrix.Translation(V(0, 0.012, 1.705 + dz)) @ Euler((math.radians(tilt), 0, 0)).to_matrix().to_4x4()

def oval_ring(cz, rx, ry, segs, mt, yc=0.0):
    return [mt @ V(math.cos(a) * rx, yc + math.sin(a) * ry, cz) for a in [2 * math.pi * (j + 0.5) / segs for j in range(segs)]]

def build_shako(m, L, kind):
    hw = fixed('head')
    mt = head_mtx(0.002, -3)
    segs = L['limb'] + (2 if L['detail'] else 1)
    prof = [(0.0, 0.097, 0.112), (0.03, 0.099, 0.114), (0.17, 0.113, 0.124), (0.195, 0.116, 0.126)]
    if L.get('lean'):
        prof = [prof[0], prof[2], prof[3]]
    rings = [oval_ring(z, rx, ry, segs, mt, 0.004) for z, rx, ry in prof]
    m.loft(rings, P('felt', MAT_LEATHER), hw, cap0=False, cap1=True)
    # inner lining hides the inside when seen from below
    if not L.get('lean'):
        m.loft([oval_ring(0.0, 0.094, 0.109, segs, mt, 0.004), oval_ring(0.05, 0.09, 0.105, segs, mt, 0.004)], P('felt', MAT_LEATHER), hw, cap1=True)
    # peak
    pk = []
    for i, r in enumerate((0.0, 0.065)):
        row = []
        for j in range(7 if L['detail'] else 4):
            a = math.radians(lerp(10, 170, j / (6 if L['detail'] else 3)))
            row.append(mt @ V(math.cos(a) * (0.1 + r * 0.6 * math.sin(a)), 0.004 + math.sin(a) * (0.114 + r), 0.004 - r * 0.35))
        pk.append(row)
    m.loft(pk, P('felt', MAT_LEATHER, smooth=False), hw, closed=False)
    if not L.get('lean'):
        m.loft([pk[1], [p + V(0, 0, -0.006) for p in pk[1]]], P('felt', MAT_LEATHER, smooth=False), hw, closed=False)
    # brass plate (lozenge / eagle plate) on the front
    c = mt @ V(0, 0.124, 0.095)
    lz = [c + V(0, 0.002, 0.052), c + V(0.042, 0.006, 0.0), c + V(0, 0.002, -0.05), c + V(-0.042, 0.006, 0.0)]
    i = [m.vert(p, hw) for p in lz]; ic = m.vert(c + V(0, 0.012, 0), hw)
    for a, b in zip(i, i[1:] + i[:1]):
        m.face((a, b, ic), P('metal', MAT_BRASS, smooth=False))
    # pompom / plume + cockade
    pl = kind.get('plume', 'pompom')
    if pl == 'pompom':
        m.ellipsoid(mt @ V(0, 0.124, 0.222), (0.022, 0.018, 0.03), 6 if L['detail'] else 4, 4 if L['detail'] else 3, P('plume', MAT_WOOL), hw)
    elif pl == 'plume':
        m.tube([mt @ V(0, 0.12, 0.19), mt @ V(0, 0.122, 0.26), mt @ V(0, 0.118, 0.40)], [0.02, 0.026, 0.008], 4 if L.get('lean') else 6,
               P('plume', MAT_FUR), hw)
    if kind.get('cords'):
        m.tube([mt @ V(-0.1, 0.09, 0.17), mt @ V(-0.02, 0.135, 0.08), mt @ V(0.06, 0.12, 0.12), mt @ V(0.11, 0.05, 0.17)],
               0.007, 3 if L.get('lean') else 4, P(kind['cords'], MAT_WOOL), hw, cap0=False, cap1=False)
    if L['detail']:   # chinscales down the cheeks
        for sx in (1, -1):
            pts = [mt @ V(0.099 * sx, 0.04, 0.01), V(0.083 * sx, 0.06, 1.64), V(0.062 * sx, 0.085, 1.585), V(0.03 * sx, 0.1, 1.56)]
            nrm = [V(sx, 0.2, 0), V(sx, 0.3, 0), V(sx, 0.6, -0.2), V(sx * 0.3, 0.6, -0.6)]
            m.ribbon(pts, nrm, 0.018, P('metal', MAT_BRASS), hw, thick=0.004)

def build_bearskin(m, L, kind):
    hw = fixed('head')
    mt = head_mtx(-0.004, 6)
    segs = L['limb'] + (1 if L.get('lean') else 2)
    prof = [(0.0, 0.1, 0.115), (0.06, 0.112, 0.128), (0.15, 0.124, 0.136), (0.25, 0.118, 0.128), (0.31, 0.095, 0.105),
            (0.34, 0.05, 0.06)]
    if not L['detail']:
        prof = [prof[0], prof[2], prof[4], prof[5]]
    rings = [oval_ring(z, rx, ry, segs, mt, 0.0) for z, rx, ry in prof]
    m.loft(rings, P('fur', MAT_FUR), hw, cap0=False, cap1=True)
    if not L.get('lean'):
        m.loft([oval_ring(0.0, 0.096, 0.11, segs, mt), oval_ring(0.05, 0.092, 0.106, segs, mt)], P('fur', MAT_FUR), hw, cap1=True)
    # front plate
    c = mt @ V(0, 0.118, 0.045)
    pts = [c + V(-0.07, -0.02, -0.03), c + V(0.07, -0.02, -0.03), c + V(0.06, 0.004, 0.035), c + V(-0.06, 0.004, 0.035)]
    i = [m.vert(p, hw) for p in pts]
    m.face(i, P('metal', MAT_BRASS, smooth=False))
    # red top patch (back, near the crown)
    pc = mt @ V(0, -0.075, 0.30)
    pts = [pc + V(-0.045, -0.035, -0.03), pc + V(0.045, -0.035, -0.03), pc + V(0.04, 0.005, 0.045), pc + V(-0.04, 0.005, 0.045)]
    i = [m.vert(p, hw) for p in pts]
    m.face(i, P('epaulette', MAT_WOOL, smooth=False))
    # plume on the left side
    m.tube([mt @ V(-0.118, 0.01, 0.12), mt @ V(-0.124, 0.012, 0.26), mt @ V(-0.12, 0.014, 0.44)], [0.016, 0.03, 0.01],
           6 if L['detail'] else 4, P('plume', MAT_FUR), hw)
    if L['detail']:  # white cords across the front
        m.tube([mt @ V(-0.12, 0.05, 0.2), mt @ V(-0.04, 0.13, 0.13), mt @ V(0.05, 0.135, 0.16), mt @ V(0.12, 0.06, 0.22)],
               0.007, 4, P('belt', MAT_WOOL), hw, cap0=False, cap1=False)
        for sx in (1, -1):
            pts = [mt @ V(0.101 * sx, 0.04, 0.01), V(0.083 * sx, 0.06, 1.64), V(0.062 * sx, 0.085, 1.585), V(0.03 * sx, 0.1, 1.56)]
            nrm = [V(sx, 0.2, 0), V(sx, 0.3, 0), V(sx, 0.6, -0.2), V(sx * 0.3, 0.6, -0.6)]
            m.ribbon(pts, nrm, 0.016, P('metal', MAT_BRASS), hw, thick=0.004)

def build_bicorne(m, L, kind):
    """officer's bicorne worn 'en bataille' (side to side)"""
    hw = fixed('head')
    mt = head_mtx(0.0, 0)
    segs = L['limb'] + 2
    m.loft([oval_ring(0.0, 0.098, 0.112, segs, mt), oval_ring(0.05, 0.094, 0.106, segs, mt)], P('felt', MAT_LEATHER), hw, cap1=True)
    n = 9 if L['detail'] else 5
    for sy in (1, -1):    # front and back brims folded up into a crescent
        bot, top = [], []
        for j in range(n):
            t = j / (n - 1)
            x = lerp(-0.25, 0.25, t)
            h = 0.03 + 0.14 * math.sin(math.pi * t) ** 0.8
            y = sy * (0.06 + 0.035 * math.sin(math.pi * t))
            bot.append(mt @ V(x, y, 0.005 + 0.04 * abs(x) / 0.25))
            top.append(mt @ V(x * 0.96, y * 0.9, 0.005 + h))
        m.loft([bot, top], P('felt', MAT_LEATHER, smooth=False), hw, closed=False)
        m.loft([[p + V(0, sy * 0.003, 0) for p in top], [p + V(0, sy * 0.003, 0) for p in bot]], P('gold', MAT_BRASS), hw, closed=False) if False else None
    # cockade + gold edging (front)
    m.ellipsoid(mt @ V(-0.11, 0.095, 0.08), (0.03, 0.006, 0.03), 6, 3, P('plume', MAT_WOOL), hw)

# ---------------------------------------------------------------- props (prop bone; local coords: +Y = axis)
def prop_to_rest(p):
    return R.REST['prop'] @ V(p)

def build_musket(m, L, kind):
    pw = fixed('prop')
    T = prop_to_rest
    d = L['detail']
    oct8 = [(1, 0.4), (0.4, 1), (-0.4, 1), (-1, 0.4), (-1, -0.4), (-0.4, -1), (0.4, -1), (1, -0.4)]
    sec = oct8 if d else [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    # (y, half width, z bottom, z top)
    stock = [(-0.35, 0.021, -0.14, 0.012), (-0.26, 0.021, -0.118, 0.014), (-0.12, 0.019, -0.07, 0.014),
             (-0.01, 0.015, -0.036, 0.01), (0.07, 0.018, -0.03, 0.012), (0.2, 0.016, -0.026, 0.006),
             (0.98, 0.014, -0.022, 0.006), (1.02, 0.012, -0.018, 0.004)]
    if L.get('lean'):
        stock = [stock[i] for i in (0, 2, 3, 7)]
    rings = []
    for y, hw_, zb, zt in stock:
        zc, hz = (zb + zt) / 2, (zt - zb) / 2
        rings.append([T((hw_ * cx, y, zc + hz * cz)) for cx, cz in sec])
    m.loft(rings, P('wood', MAT_WOOD), pw, cap0=True, cap1=True)
    # barrel
    m.tube([T((0, 0.02, 0.015)), T((0, 1.12, 0.015))], 0.0105, 6 if d else 4, P('steel', MAT_STEEL), pw, up=R.REST['prop'].to_3x3() @ V(0, 0, 1))
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    if d:
        for y in (0.42, 0.72, 0.97):
            m.tube([T((0, y - 0.007, -0.004)), T((0, y + 0.007, -0.004))], 0.026, 6, P('steel', MAT_IRON), pw, up=up, scale_x=0.75)
        m.box((0.006, 0.1, 0.03), Matrix.Translation(T((0.019, 0.05, -0.004))) @ R.REST['prop'].to_3x3().to_4x4(), P('steel', MAT_IRON, smooth=False), pw)
        m.box((0.008, 0.03, 0.04), Matrix.Translation(T((0.016, 0.0, 0.03))) @ R.REST['prop'].to_3x3().to_4x4(), P('steel', MAT_IRON, smooth=False), pw)
        m.box((0.006, 0.08, 0.02), Matrix.Translation(T((0, 0.0, -0.045))) @ R.REST['prop'].to_3x3().to_4x4(), P('steel', MAT_IRON, smooth=False), pw)
        # sling
        sl = [T((0, 0.42, -0.03)), T((0, 0.2, -0.075)), T((0, -0.02, -0.1)), T((0, -0.28, -0.135))]
        nrm = [R.REST['prop'].to_3x3() @ V(1, 0, 0)] * 4
        m.ribbon(sl, nrm, 0.022, P('belt', MAT_LEATHER), pw, thick=0.003)
    if kind.get('bayonet', True):
        if not L.get('lean'):
            m.tube([T((0, 1.06, 0.002)), T((0, 1.13, 0.002))], 0.0145, 5 if d else 3, P('steel', MAT_STEEL), pw, up=up)
        m.tube([T((0.018, 1.115, -0.006)), T((0.02, 1.32, -0.006)), T((0.02, 1.52, -0.006))], [0.0085, 0.0065, 0.0008], 3,
               P('steel', MAT_STEEL, smooth=False), pw, up=up)

def build_rammer(m, L, kind):
    pw = fixed('prop'); T = prop_to_rest
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    m.tube([T((0, -0.95, 0)), T((0, 1.55, 0))], 0.017, 6 if L['detail'] else 4, P('wood', MAT_WOOD), pw, up=up)
    m.tube([T((0, 1.55, 0)), T((0, 1.70, 0))], 0.058, 8 if L['detail'] else 5, P('wood', MAT_WOOD), pw, up=up)
    m.tube([T((0, -1.12, 0)), T((0, -0.95, 0))], 0.062, 8 if L['detail'] else 5, P('sponge', MAT_FUR), pw, up=up)

def build_sword(m, L, kind):
    pw = fixed('prop'); T = prop_to_rest
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    m.tube([T((0, -0.06, 0)), T((0, 0.06, 0))], 0.013, 5, P('gold', MAT_BRASS), pw, up=up)
    m.tube([T((0, 0.06, 0)), T((0, 0.5, 0.01)), T((0, 0.86, 0.03))], [0.014, 0.011, 0.002], 3, P('steel', MAT_STEEL, smooth=False), pw, up=up, scale_x=0.25)
    m.box((0.1, 0.01, 0.015), Matrix.Translation(T((0, 0.06, 0))) @ R.REST['prop'].to_3x3().to_4x4(), P('gold', MAT_BRASS, smooth=False), pw)

# ---------------------------------------------------------------- unit kits
KITS = {
    'c19sr_line': dict(head='shako', plume='pompom', prop='musket', belts=('cart', 'bayo'), knapsack=True),
    'c19sr_grenadier': dict(head='bearskin', prop='musket', belts=('cart', 'bayo'), knapsack=True, sabre=True,
                            epaulettes='epaulette', moustache=True),
    'c19sr_artillery': dict(head='shako', plume='plume', cords='epaulette', prop='rammer', belts=('bayo',), sabre=True,
                            knapsack=False, epaulettes='epaulette', lapel_slot='coat'),
    'c19sr_officer': dict(head='bicorne', prop='sword', belts=(), knapsack=False, epaulettes='gold', lower_leg='boot',
                          shoe_slot='boot', gaiter_top=0.6, tail_bottom=0.66, moustache=True),
}

def build(kit_id, lod):
    kind = KITS[kit_id]
    L = LODS[lod]
    m = CharMesh(f'{kit_id}_lod{lod}')
    build_torso(m, L)
    build_neck_head(m, L, kind)
    build_arms(m, L, kind)
    build_legs(m, L, kind)
    build_lapels(m, L, kind)
    if kind.get('belts'):
        build_crossbelts(m, L, kind)
    if kind.get('knapsack'):
        build_knapsack(m, L, kind)
    {'shako': build_shako, 'bearskin': build_bearskin, 'bicorne': build_bicorne}[kind['head']](m, L, kind)
    {'musket': build_musket, 'rammer': build_rammer, 'sword': build_sword}[kind['prop']](m, L, kind)
    if kit_id == 'c19sr_officer':
        # sash + gorget
        for z in (1.0, 1.035):
            pass
    return m
