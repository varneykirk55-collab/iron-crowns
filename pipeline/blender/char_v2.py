"""PROTO V2 (docs/char/PROTO_V2.md): sculpted-geometry c19 line fusilier.
High-poly sculpt (fused body via voxel remesh, parametric head / hands / kit at high resolution) -> game mesh (quadriflow
retopo for the fused body, the same parametric functions at game resolution for the rest) -> Cycles bake of slot map,
tangent normal map and AO into one atlas -> skinned to char_rig.BONES -> VAT bake (char_v2_bake.py).
Blender coords: Z up, character faces +Y, +X = its right."""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(__file__))
import char_body as B   # SLOT_NAMES / S / PALETTE / MAT_* (same palette contract as c19sr)
import char_rig as R

S = B.S
M = dict(wool=B.MAT_WOOL, leather=B.MAT_LEATHER, steel=B.MAT_STEEL, brass=B.MAT_BRASS, skin=B.MAT_SKIN, wood=B.MAT_WOOD,
         pipeclay=B.MAT_PIPECLAY, fur=B.MAT_FUR, iron=B.MAT_IRON, hair=B.MAT_HAIR, canvas=B.MAT_CANVAS, default=B.MAT_DEFAULT)
SLOT_MAT = {'coat': 'wool', 'lapel': 'wool', 'collar': 'wool', 'cuff': 'wool', 'turnback': 'wool', 'waist': 'wool',
            'breeches': 'canvas', 'gaiter': 'wool', 'shoe': 'leather', 'plume': 'fur', 'felt': 'leather', 'metal': 'brass',
            'belt': 'pipeclay', 'cartbox': 'leather', 'knapsack': 'hide', 'roll': 'wool', 'skin': 'skin', 'hair': 'hair',
            'eye': 'skin', 'mouth': 'skin', 'wood': 'wood', 'steel': 'steel', 'button': 'brass', 'stock': 'leather',
            'piping': 'wool', 'epaulette': 'wool'}
M['hide'] = B.MAT_HIDE

def V(*a):
    return Vector(a[0] if len(a) == 1 else a)

def ss(a, b, x):
    if a == b: return 1.0 if x >= b else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

def lerp(a, b, t): return a + (b - a) * t

def gauss(d, r): return math.exp(-(d * d) / (r * r))

# ------------------------------------------------------------------ mesh helpers
def mk(name, verts, faces, slot=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for p in me.polygons: p.use_smooth = smooth
    if slot is not None:
        set_slot(o, slot)
    return o

def set_slot(o, slot):
    """slot: name or fn(face_center) -> name. Stored as face int attribute 'slot'."""
    me = o.data
    a = me.attributes.get('slot') or me.attributes.new('slot', 'INT', 'FACE')
    vals = []
    for p in me.polygons:
        s = slot(p.center) if callable(slot) else slot
        vals.append(S[s])
    a.data.foreach_set('value', vals)

def grid_sweep(name, sections, closed_u=True, cap0=True, cap1=True, slot=None):
    """sections: list of rings (lists of Vector, equal length) -> quad mesh with optional fan caps."""
    n = len(sections[0]); verts = [p for r in sections for p in r]; faces = []
    m = n if closed_u else n - 1
    for i in range(len(sections) - 1):
        for j in range(m):
            k = (j + 1) % n
            faces.append((i * n + j, i * n + k, (i + 1) * n + k, (i + 1) * n + j))
    for cap, ri, flip in ((cap0, 0, True), (cap1, len(sections) - 1, False)):
        if not cap: continue
        c = sum(sections[ri], Vector()) / n; verts.append(c); ci = len(verts) - 1
        for j in range(n):
            k = (j + 1) % n
            a, b = ri * n + j, ri * n + k
            faces.append((b, a, ci) if flip else (a, b, ci))
    o = mk(name, verts, faces, slot)
    fix_normals(o)
    return o

def fix_normals(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(o.data); bm.free()

def ring(c, u, v, rx, rf, rb, n, e=2.0, phase=0.0, fn=None):
    """asymmetric (super-)ellipse ring around c in plane (u = side axis, v = front axis): rf front / rb back half-depth."""
    out = []
    for j in range(n):
        a = 2 * math.pi * (j + phase) / n
        ca, sa = math.cos(a), math.sin(a)
        f = lambda x: math.copysign(abs(x) ** (2.0 / e), x)
        x, y = f(ca) * rx, f(sa) * (rf if sa > 0 else rb)
        p = c + u * x + v * y
        if fn: p = fn(p, a)
        out.append(p)
    return out

def interp_prof(prof, t):
    w = max(len(r) for r in prof); prof = [tuple(r) + (0.0,) * (w - len(r)) for r in prof]
    """prof: list of (t, values...) sorted by t; smooth (catmull-ish) interpolation of the values."""
    if t <= prof[0][0]: return prof[0][1:]
    if t >= prof[-1][0]: return prof[-1][1:]
    for i in range(len(prof) - 1):
        a, b = prof[i], prof[i + 1]
        if a[0] <= t <= b[0]:
            s = (t - a[0]) / (b[0] - a[0])
            p0 = prof[max(i - 1, 0)]; p3 = prof[min(i + 2, len(prof) - 1)]
            out = []
            for k in range(1, len(a)):
                y0, y1, y2, y3 = p0[k], a[k], b[k], p3[k]
                m1 = (y2 - y0) / 2; m2 = (y3 - y1) / 2   # catmull-rom (uniform-ish)
                h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s; h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
                out.append(h00 * y1 + h10 * m1 + h01 * y2 + h11 * m2)
            return out

def path_frame(path, t):
    """point + tangent along a polyline path [(t, Vector)], t in [0,1]"""
    for i in range(len(path) - 1):
        (ta, a), (tb, b) = path[i], path[i + 1]
        if ta <= t <= tb or i == len(path) - 2:
            s = (t - ta) / (tb - ta) if tb > ta else 0
            p0 = path[max(i - 1, 0)][1]; p3 = path[min(i + 2, len(path) - 1)][1]
            # catmull-rom position
            s2, s3 = s * s, s * s * s
            p = 0.5 * ((2 * a) + (-p0 + b) * s + (2 * p0 - 5 * a + 4 * b - p3) * s2 + (-p0 + 3 * a - 3 * b + p3) * s3)
            d = (b - a).normalized()
            return p, d
    return path[-1][1], (path[-1][1] - path[-2][1]).normalized()

def limb(name, path, prof, nt, nu, fwd=V(0, 1, 0), e=2.0, cap0=True, cap1=True, slot=None, tw=None):
    """sweep along path; prof(t) -> rx, rf, rb, (offset_front)"""
    secs = []
    for i in range(nt + 1):
        t = i / nt
        if tw: t = tw(t)
        p, d = path_frame(path, t)
        v = (fwd - d * fwd.dot(d)).normalized(); u = v.cross(d).normalized()
        vals = interp_prof(prof, t)
        rx, rf, rb = vals[:3]; off = vals[3] if len(vals) > 3 else 0.0
        secs.append(ring(p + v * off, u, v, rx, rf, rb, nu, e))
    return grid_sweep(name, secs, cap0=cap0, cap1=cap1, slot=slot)

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join(); o = bpy.context.active_object; o.name = name; o.data.name = name
    return o

def apply_mods(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)

# ------------------------------------------------------------------ body (fused: torso + neck + collar, arms, legs, shoes)
SPREAD = 0.06   # arms are built this much further out (+-x) so the voxel remesh doesn't fuse them to the ribs; moved back after

TORSO_PROF = [  # (z, rx, rf, rb, front offset)
    (0.80, 0.10, 0.07, 0.07, 0.0), (0.86, 0.158, 0.095, 0.112, -0.006), (0.94, 0.166, 0.100, 0.124, -0.012),
    (1.02, 0.152, 0.096, 0.104, -0.002), (1.10, 0.140, 0.100, 0.094, 0.004), (1.20, 0.144, 0.110, 0.098, 0.010),
    (1.28, 0.150, 0.122, 0.102, 0.012), (1.35, 0.158, 0.124, 0.110, 0.008), (1.41, 0.162, 0.106, 0.104, 0.000),
    (1.445, 0.152, 0.088, 0.092, -0.006), (1.475, 0.125, 0.074, 0.080, -0.006), (1.50, 0.086, 0.062, 0.064, -0.002), (1.52, 0.058, 0.055, 0.053, 0.004),
    (1.62, 0.054, 0.052, 0.050, 0.012)]
TORSO_TOP = 1.555   # stage 5: the neck stub ends inside the collar; the MakeHuman head + neck sits on top

def torso_shape(p, a):
    x, y, z = p
    d = 0.0
    if y > 0:   # chest (pectorals) and belly
        for sx in (1, -1):
            d += 0.012 * gauss(x - sx * 0.072, 0.05) * gauss(z - 1.31, 0.06)
        d += 0.004 * gauss(z - 1.12, 0.05) * gauss(x, 0.08)
    else:       # shoulder blades, spine groove, buttocks
        for sx in (1, -1):
            d += 0.010 * gauss(x - sx * 0.075, 0.05) * gauss(z - 1.36, 0.06)
            d += 0.014 * gauss(x - sx * 0.07, 0.06) * gauss(z - 0.93, 0.06)
        d -= 0.006 * gauss(x, 0.02) * ss(1.0, 1.1, z) * ss(1.45, 1.38, z)
    # trapezius: shoulders slope up into the neck
    if 1.40 < z < 1.50:
        d += 0.0
    n = V(x, y * 1.6, 0)
    if n.length < 1e-6: return p
    return p + n.normalized() * d

def build_torso(res):
    nz, nu = res
    secs = []
    for i in range(nz + 1):
        z = lerp(0.80, TORSO_TOP if USE_MH else 1.62, i / nz)
        rx, rf, rb, off = interp_prof(TORSO_PROF, z)
        rx = max(rx, 0.04)
        secs.append(ring(V(0, off, z), V(1, 0, 0), V(0, 1, 0), rx, rf, rb, nu, 2.35, 0.5 + nu / 4, torso_shape))
    return grid_sweep('torso', secs, cap0=True, cap1=True)

def collar_band(res):
    """stand collar: closed, top edge dips at the front under the chin."""
    nz, nu = res
    secs = []
    for t in (0.0, 0.5, 1.0):
        # stage 5b: ~6 cm stand collar round the MakeHuman neck (was a 9.4 cm tube): centred on the neck (y +0.02),
        # top 1.556 at the back dipping to ~1.536 under the chin
        r = ring(V(0, 0.020, 0), V(1, 0, 0), V(0, 1, 0), 0.074 - 0.006 * t, 0.072 - 0.006 * t, 0.070 - 0.006 * t, nu, 2.2, 0.5)
        sec = []
        for p in r:
            fr = ss(0.04, 0.085, p.y)
            ztop = 1.556 - 0.020 * fr
            sec.append(V(p.x, p.y, lerp(1.478, ztop, t)))
        secs.append(sec)
    return grid_sweep('collar', secs, cap0=True, cap1=True)

ARM_PROF = [(0.0, 0.050, 0.050, 0.050), (0.10, 0.060, 0.058, 0.058), (0.22, 0.054, 0.052, 0.050), (0.36, 0.047, 0.051, 0.045, 0.004),
            (0.50, 0.041, 0.040, 0.046, -0.003), (0.60, 0.045, 0.046, 0.044), (0.74, 0.042, 0.041, 0.041), (0.855, 0.036, 0.034, 0.034),
            (0.87, 0.042, 0.040, 0.040), (0.98, 0.040, 0.036, 0.036), (1.0, 0.030, 0.026, 0.026)]

def arm_path(s, spread=True):
    sp = SPREAD if spread else 0.0
    pts = [(0.0, (0.120, -0.012, 1.432)), (0.12, (0.180, -0.012, 1.400)), (0.50, (0.205, -0.012, 1.14)), (1.0, (0.222, 0.0, 0.905))]
    return [(t, V(s * (x + (sp if t > 0.05 else sp * 0.5)), y, z)) for t, (x, y, z) in pts]

def build_arm(s, res, spread=True):
    nt, nu = res
    return limb('arm' + ('R' if s > 0 else 'L'), arm_path(s, spread), ARM_PROF, nt, nu, cap0=True, cap1=True)

LEG_PROF = [(0.0, 0.086, 0.086, 0.086), (0.10, 0.088, 0.088, 0.092), (0.30, 0.074, 0.078, 0.070, 0.005), (0.45, 0.056, 0.058, 0.055),
            (0.50, 0.052, 0.057, 0.050), (0.535, 0.053, 0.053, 0.053), (0.55, 0.061, 0.058, 0.062), (0.68, 0.063, 0.054, 0.074, -0.006),
            (0.85, 0.046, 0.044, 0.050), (0.95, 0.042, 0.045, 0.046), (1.0, 0.047, 0.052, 0.050)]

def leg_path(s):
    return [(0.0, V(s * 0.088, 0.0, 0.975)), (0.5, V(s * 0.1, 0.012, 0.505)), (1.0, V(s * 0.1, -0.012, 0.085))]

def build_leg(s, res):
    nt, nu = res
    return limb('leg' + ('R' if s > 0 else 'L'), leg_path(s), LEG_PROF, nt, nu, cap0=True, cap1=True)

SHOE_PROF = [(0.0, 0.034, 0.030, 0.030), (0.15, 0.040, 0.050, 0.040), (0.45, 0.042, 0.040, 0.036), (0.8, 0.040, 0.026, 0.026),
             (1.0, 0.022, 0.016, 0.016)]

def build_shoe(s, res):
    nt, nu = res
    path = [(0.0, V(s * 0.100, -0.050, 0.040)), (0.4, V(s * 0.102, 0.030, 0.036)), (1.0, V(s * 0.112, 0.170, 0.026))]
    o = limb('shoe' + ('R' if s > 0 else 'L'), path, SHOE_PROF, nt, nu, fwd=V(0, 0, 1), e=2.6)
    for v in o.data.vertices:   # flat sole
        v.co.z = max(v.co.z, 0.004)
    return o

def body_slot(p, part):
    x, y, z = p; ax = abs(x)
    if part == 'shoe': return 'shoe'
    if part == 'collar': return 'collar'
    if part == 'arm':
        return 'cuff' if z < 0.968 else 'coat'
    if part == 'leg':
        if z < 0.545 + 0.02 * ss(-0.01, 0.05, y): return 'gaiter'   # knee-high black gaiters (concept)
        return 'breeches'
    # torso
    if z > 1.586: return 'skin'
    if z > 1.49: return 'stock'
    front = y > 0.02
    if front:
        lap_w = lerp(0.050, 0.098, ss(1.04, 1.40, z))   # lapels: narrow at the waist, wide at the chest (habit 1812 cut)
        if z > 1.03 and ax < lap_w:
            if ax > lap_w - 0.007: return 'piping'
            return 'lapel'
        if z <= 1.03 and z > 0.90 and ax < 0.13: return 'waist'
        if z <= 0.90: return 'breeches'
        return 'coat'
    if z < 0.90 and ax < 0.2: return 'breeches'
    return 'coat'

def build_body_parts(res_t=(40, 32), res_l=(40, 24), spread=True):
    parts = {'torso': [build_torso((60, res_t[1]))], 'collar': [collar_band((6, res_t[1]))],
             'arm': [build_arm(1, res_l, spread), build_arm(-1, res_l, spread)],
             'leg': [build_leg(1, res_l), build_leg(-1, res_l)], 'shoe': [build_shoe(1, (16, 16)), build_shoe(-1, (16, 16))]}
    return parts

def fuse(parts, voxel=0.005, name='body_hi'):
    objs = [o.copy() for v in parts.values() for o in v]
    for o in objs:
        o.data = o.data.copy(); bpy.context.scene.collection.objects.link(o)
    o = join(objs, name)
    m = o.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = voxel; m.adaptivity = 0.0; m.use_smooth_shade = True
    apply_mods(o)
    sm = o.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); sm.iterations = 3; sm.smooth_type = 'SIMPLE'; sm.use_only_smooth = True
    apply_mods(o)
    return o

def nearest_part(parts):
    trees = {}
    for k, objs in parts.items():
        for o in objs:
            bm = bmesh.new(); bm.from_mesh(o.data); trees.setdefault(k, []).append(BVHTree.FromBMesh(bm)); bm.free()
    def f(p):
        best = (1e9, None)
        for k, ts in trees.items():
            for t in ts:
                r = t.find_nearest(p)
                if r[0] is not None and r[3] < best[0]: best = (r[3], k)
        return best[1]
    def dist(p, k):
        return min((t.find_nearest(p)[3] for t in trees[k]), default=1e9)
    f.dist = dist
    return f

def unspread(o, near):
    """move arm-owned vertices back by SPREAD (smooth blend in the shoulder junction)."""
    for v in o.data.vertices:
        p = v.co
        if abs(p.x) < 0.10 or p.z < 0.85: continue
        da = near.dist(p, 'arm'); dt = min(near.dist(p, 'torso'), near.dist(p, 'collar'))
        w = ss(-0.012, 0.012, dt - da)
        v.co.x -= math.copysign(SPREAD * w, p.x)

# ------------------------------------------------------------------ head (parametric; evaluated hi for bake, lo for game)
HEAD_C = V(0, 0.010, 1.666)
HEAD_DZ = 1.672 - HEAD_C.z   # feature heights below are authored for a head centre at z 1.672
HEAD_R = (0.074, 0.094, 0.112)

def head_point(u, v):
    """u: angle around z (0 = +x, pi/2 = front +y), v: 0 top .. pi bottom"""
    sv, cv, cu, su = math.sin(v), math.cos(v), math.cos(u), math.sin(u)
    xn, yn, zn = sv * cu, sv * su, cv
    a, b, h = HEAD_R
    x, y, z = a * xn, b * yn, h * zn
    # cranium wider at the back/top, jaw narrows to the chin, back of the skull tucks into the neck
    if zn < 0:
        x *= lerp(1.0, 0.76 if yn > 0 else 0.86, ss(-0.05, -0.95, zn))
        if yn < 0: y *= lerp(1.0, 0.45, ss(0.0, -0.85, zn))
        else: y *= lerp(1.0, 0.92, ss(-0.4, -1.0, zn))
    else:
        x *= 1.0 + 0.04 * ss(0.2, 0.7, zn) * ss(0.4, -0.5, yn)
        if yn < 0: y *= 1.06
    if yn > 0:   # flatten the face plane a little
        y = min(y, b * 0.86 + (y - b * 0.86) * 0.35) if y > b * 0.86 else y
    p = HEAD_C + V(x, y, z)
    # facial features as forward displacements, front-weighted
    wf = ss(0.25, 0.75, yn)
    if wf > 0:
        X, Z = p.x, p.z + HEAD_DZ; ax = abs(X)
        d = 0.0
        d += 0.026 * gauss(X, 0.0095 + 0.007 * ss(1.67, 1.645, Z)) * ss(1.708, 1.655, Z) * ss(1.632, 1.652, Z)  # nose
        d += 0.0035 * gauss(X, 0.008) * gauss(Z - 1.690, 0.012)                         # nose bridge (between the eyes)
        d -= 0.0030 * gauss(ax - 0.012, 0.004) * gauss(Z - 1.643, 0.006)                # nostril wings / alar groove
        d += 0.0090 * gauss(Z - 1.708, 0.008) * gauss(X, 0.050) * (1.0 - 0.4 * gauss(X, 0.008))   # brow ridge
        d -= 0.0100 * gauss(ax - 0.031, 0.013) * gauss(Z - 1.690, 0.010)                # eye sockets
        d += 0.0020 * gauss(ax - 0.031, 0.009) * gauss(Z - 1.689, 0.004)                # eyeballs / lids
        d += 0.0070 * gauss(ax - 0.047, 0.016) * gauss(Z - 1.664, 0.014)                # cheekbones
        d -= 0.0045 * gauss(ax - 0.050, 0.014) * gauss(Z - 1.630, 0.014)                # cheek hollow (cheek / jaw planes)
        d -= 0.0030 * gauss(ax - 0.022, 0.006) * gauss(Z - 1.636, 0.016)                # naso-labial fold
        d += 0.0040 * gauss(Z - 1.625, 0.004) * gauss(X, 0.017)                         # upper lip
        d -= 0.0045 * gauss(Z - 1.6175, 0.0025) * gauss(X, 0.019)                       # mouth line
        d += 0.0040 * gauss(Z - 1.610, 0.0045) * gauss(X, 0.015)                        # lower lip
        d -= 0.0030 * gauss(Z - 1.600, 0.004) * gauss(X, 0.016)                         # mento-labial groove
        d += 0.0095 * gauss(Z - 1.585, 0.013) * gauss(X, 0.024)                         # chin
        d += 0.0040 * gauss(ax - 0.050, 0.010) * gauss(Z - 1.588, 0.012)                # jaw angle (defined jaw line)
        p.y += d * wf
    return p

NEUTRAL = 8.0 / 15.0

def head_det(p):
    """painted skin detail for the bake: < NEUTRAL stubble / shadow, > NEUTRAL ruddy (lips, cheeks, nose, ears); eye slot: iris 0 .. sclera 1"""
    X, Y, Z = p; Z += HEAD_DZ; ax = abs(X)
    front = Y > HEAD_C.y + 0.04
    if front and 0.018 < ax < 0.045 and abs(Z - 1.689) < 0.0062:
        r = math.hypot((ax - 0.0315) / 0.0068, (Z - 1.689) / 0.0062)
        return 0.0 if r < 0.75 else 1.0   # iris (dark) / sclera
    d = NEUTRAL
    stub = ss(1.640, 1.625, Z) * ss(0.012, 0.035, Y - HEAD_C.y + 0.03) * (1.0 - gauss(Z - 1.617, 0.006) * gauss(X, 0.02))
    stub = max(stub, gauss(Z - 1.628, 0.004) * gauss(X, 0.022) * 0.8)   # moustache shadow above the lip
    d -= 0.42 * stub
    d += 0.40 * gauss(Z - 1.6175, 0.007) * gauss(X, 0.018)            # lips
    d += 0.25 * gauss(ax - 0.045, 0.016) * gauss(Z - 1.650, 0.014)    # cheeks
    d += 0.22 * gauss(X, 0.010) * gauss(Z - 1.645, 0.010)             # nose tip
    d += 0.25 * ss(0.062, 0.072, ax)                                    # ears
    d -= 0.12 * gauss(ax - 0.031, 0.016) * gauss(Z - 1.680, 0.008)    # under-eye shadow
    return max(0.0, min(1.0, d))

def head_slot(p):
    X, Y, Z = p; Z += HEAD_DZ; ax = abs(X); rel = p - HEAD_C
    front = Y > HEAD_C.y + 0.055
    if front and 0.018 < ax < 0.045 and abs(Z - 1.689) < 0.0058 - 0.003 * abs(ax - 0.031) / 0.014 and Y > 0.07:
        return 'eye'   # iris / sclera painted in the detail map (head_det)
    if front and 0.012 < ax < 0.050 and 1.699 + 0.002 * ss(0.03, 0.05, ax) < Z < 1.7075 + 0.002 * ss(0.03, 0.05, ax): return 'hair'  # eyebrows
    if front and abs(Z - 1.6175) < 0.0035 and ax < 0.017: return 'mouth'
    if Z > 1.735 and Y < HEAD_C.y + 0.06: return 'hair'
    if Y < HEAD_C.y - 0.02 and Z > 1.625 and ax < 0.071: return 'hair'
    if 0.058 < ax < 0.0725 and HEAD_C.y - 0.008 < Y < HEAD_C.y + 0.035 and 1.630 < Z < 1.72: return 'hair'   # sideburns (concept: long, to the jaw)
    return 'skin'

def build_head(nu, nv, name='head'):
    verts = [head_point(2 * math.pi * j / nu - math.pi / 2, math.pi * i / nv) for i in range(1, nv) for j in range(nu)]
    secs = [verts[k * nu:(k + 1) * nu] for k in range(nv - 1)]
    o = grid_sweep(name, secs, cap0=True, cap1=True)
    # ears
    ears = []
    for s in (1, -1):
        e = limb('ear', [(0, V(s * 0.072, 0.004, 1.690 - HEAD_DZ)), (1, V(s * 0.072, -0.002, 1.640 - HEAD_DZ))],
                 [(0, 0.004, 0.008, 0.008), (0.3, 0.010, 0.016, 0.012), (0.8, 0.009, 0.011, 0.011), (1, 0.004, 0.006, 0.006)],
                 max(4, nv // 4), max(6, nu // 3), fwd=V(s * 0.3, 1, 0))
        for vv in e.data.vertices:  # cup the ear backwards
            vv.co.x += s * 0.01 * max(0.0, -(vv.co.y - 0.004)) / 0.02
        ears.append(e)
    o = join([o] + ears, name)
    set_slot(o, head_slot)
    set_det(o, head_det)
    return o

def set_det(o, fn):
    """point float attribute 'det2' (painted detail for the bake, see head_det)"""
    me = o.data
    a = me.attributes.get('det2') or me.attributes.new('det2', 'FLOAT', 'POINT')
    a.data.foreach_set('value', [fn(v.co) for v in me.vertices])

# ------------------------------------------------------------------ hands (thumb + grouped fingers; hi = separate fingers)
GRIP_C = (0.203, 0.790)   # hand rest space (x, z) of the grip axis (musket stock runs ~ along y through the fist; see PROTO_V2.md)
GRIP_R = 0.0175

def build_hand(s, hi=False):
    """Back of hand + four knuckled fingers curled round the grip + opposed thumb. hi: separate fingers with knuckle /
    joint bulges and nails for the bake; game: the same fingers at low resolution (they read in silhouette)."""
    sx = lambda p: V(s * p[0], p[1], p[2])
    parts = []
    nt, nu = (14, 16) if hi else (3, 8)
    palm = limb('palm', [(0, sx((0.222, 0.002, 0.902))), (0.45, sx((0.224, 0.004, 0.852))), (1, sx((0.226, 0.005, 0.808)))],
                [(0, 0.0140, 0.020, 0.020), (0.35, 0.0160, 0.033, 0.031), (1, 0.0145, 0.035, 0.033)], nt, nu, fwd=V(0, 1, 0), e=2.2)
    parts.append(palm)
    cx, cz = GRIP_C
    def fpath(y, L):   # knuckle (back of the hand) -> around the grip -> tip pressed against the palm side
        r = GRIP_R + 0.0095
        pts = [(0.0, sx((0.229, y, 0.806)))]
        for k, a in enumerate((-10, -55, -105, -150, -185)):
            aa = math.radians(a) * (0.80 + 0.2 * L)
            pts.append(((k + 1) / 5.0, sx((cx + r * math.cos(aa), y, cz + r * math.sin(aa) + 0.004))))
        return pts
    fingers = ((0.025, 0.92, 0.0086), (0.008, 1.0, 0.0093), (-0.009, 0.97, 0.0090), (-0.025, 0.82, 0.0079))
    for y, L, r in fingers:
        prof = [(0, r * 1.22, r * 1.12, r * 1.12), (0.12, r * 1.0, r, r),            # knuckle (MCP) bulge
                (0.36, r * 1.08, r * 1.04, r * 1.04), (0.46, r * 0.95, r * 0.95, r * 0.95),   # PIP joint
                (0.70, r * 0.98, r * 0.96, r * 0.96), (0.80, r * 0.88, r * 0.86, r * 0.86),   # DIP joint
                (1, r * 0.72, r * 0.68, r * 0.68)]
        parts.append(limb('fing', fpath(y, L), prof, 22 if hi else 4, 10 if hi else 5, fwd=V(0, 1, 0)))
    # thumb: from the base of the palm, across the front of the grip, tip over the index finger
    thumb = limb('thumb', [(0, sx((0.210, 0.028, 0.880))), (0.35, sx((0.196, 0.040, 0.850))), (0.7, sx((0.184, 0.036, 0.818))),
                           (1, sx((0.186, 0.026, 0.796)))],
                 [(0, 0.0135, 0.0135, 0.0135), (0.35, 0.0105, 0.0105, 0.0105), (0.55, 0.0098, 0.0098, 0.0098), (0.62, 0.0104, 0.0104, 0.0104),
                  (1, 0.0072, 0.0072, 0.0072)], 14 if hi else 3, 10 if hi else 6, fwd=V(s, 0, 0))
    parts.append(thumb)
    o = join(parts, 'hand' + ('R' if s > 0 else 'L'))
    set_slot(o, 'skin')
    if hi:   # knuckle tendons on the back of the hand
        for v in o.data.vertices:
            p = v.co
            if s * p.x > 0.230 and 0.81 < p.z < 0.89:
                for y, L, r in fingers:
                    p.x += s * 0.0012 * gauss(p.y - y, 0.0035) * ss(0.89, 0.85, p.z)
    set_det(o, lambda p: NEUTRAL + 0.12 * ss(0.0, 0.01, -(s * p.x - 0.215)) * ss(0.83, 0.79, p.z))   # ruddier knuckles / fingertips
    return o

# ------------------------------------------------------------------ uniform kit
def superellipsoid(name, c, r, e=(4.0, 4.0), n=(16, 10), rot=None, slot=None, fn=None):
    """box-ish rounded solid: r = half extents (x, y, z); e = (around, vertical) exponents."""
    nu, nv = n; rot = rot or Matrix.Identity(3)
    f = lambda x, k: math.copysign(abs(x) ** (2.0 / k), x)
    secs = []
    for i in range(1, nv):
        v = math.pi * i / nv; cv, sv = f(math.cos(v), e[1]), f(math.sin(v), e[1])
        row = []
        for j in range(nu):
            u = 2 * math.pi * j / nu; cu, su = f(math.cos(u), e[0]), f(math.sin(u), e[0])
            q = V(r[0] * sv * cu, r[1] * sv * su, r[2] * cv)
            if fn: q = fn(q)
            row.append(c + rot @ q)
        secs.append(row)
    return grid_sweep(name, secs, cap0=True, cap1=True, slot=slot)

def coat_tails(hi=False):
    out = []
    nz, nw = (24, 10) if hi else (5, 3)
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            t = i / nz; z = lerp(1.03, 0.60, t)
            yb = lerp(-0.118, -0.150, ss(1.03, 0.93, z)); yb = lerp(yb, -0.104, ss(0.90, 0.60, z))
            xc = s * lerp(0.082, 0.062, t); hw = lerp(0.080, 0.048, t)
            th = 0.011
            outer, inner = [], []
            for j in range(nw + 1):
                w = -1 + 2 * j / nw; x = xc + s * w * hw
                y = yb - 0.02 * (1 - w * w) * 0.5 + 0.012 * ss(0.10, 0.18, abs(x))
                outer.append(V(x, y, z)); inner.append(V(x, y + th, z))
            secs.append(outer + inner[::-1])
        o = grid_sweep('tail', secs, cap0=True, cap1=True)
        def tslot(p, s=s):
            if p.z > 0.95: return 'coat'
            # visible red turnback with a blue edge along the outer seam
            return 'coat' if abs(p.x) > 0.125 - 0.04 * (1.0 - (p.z - 0.6) / 0.35) else 'turnback'
        set_slot(o, tslot)
        out.append(o)
    return out

def surface_tools(objs):
    bm = bmesh.new()
    for o in objs:
        tmp = bmesh.new(); tmp.from_mesh(o.data); tmp.transform(o.matrix_world)
        me = bpy.data.meshes.new('_t'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    return BVHTree.FromBMesh(bm)

def crossbelt(tree, s, hi=False, width=0.052, off=0.006):
    """belt over shoulder -s down to hip +s: intersection of the torso with a tilted plane z = z0 + k*x."""
    k = (0.97 - 1.455) / (s * 0.115 - (-s * 0.125)); z0 = 1.455 - k * (-s * 0.125)
    n = 64 if hi else 40
    pts, nrm = [], []
    for j in range(n):
        a = 2 * math.pi * j / n
        d = V(math.cos(a), math.sin(a), 0)
        x = 0.0
        for _ in range(6):
            z = z0 + k * x
            hit = tree.ray_cast(V(0, 0.0, z) + d * 0.5, -d)
            if hit[0] is None: break
            x = hit[0].x
        if hit[0] is None: continue
        pts.append(hit[0] + hit[1] * off); nrm.append(hit[1])
    secs = []
    m = len(pts)
    for j in range(m):
        tng = (pts[(j + 1) % m] - pts[j - 1]).normalized()
        side = nrm[j].cross(tng).normalized()
        p = pts[j]; th = 0.0045
        secs.append([p + side * width / 2, p - side * width / 2, p - side * width / 2 - nrm[j] * th, p + side * width / 2 - nrm[j] * th])
    secs.append(secs[0])
    o = grid_sweep('belt', secs, cap0=False, cap1=False, slot='belt')
    if hi: st_uv(o, [0.0, 1.0, 1.0, 0.0])
    return o

def st_uv(o, across):
    """uv 'st' for straps: u = metres along the strap, v = 0..1 across (stitch rows in the bake material)."""
    me = o.data; uvl = me.uv_layers.new(name='st'); k = len(across)
    nv = len(me.vertices); m = nv // k
    lens = [0.0]
    for j in range(1, m):
        lens.append(lens[-1] + (me.vertices[j * k].co - me.vertices[(j - 1) * k].co).length)
    for p in me.polygons:
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            uvl.data[li].uv = (lens[min(vi // k, m - 1)], across[vi % k])

def knapsack(hi=False):
    n = (24, 14) if hi else (10, 6)
    pack = superellipsoid('pack', V(0, -0.150, 1.26), (0.152, 0.055, 0.145), e=(5.0, 5.0), n=n, slot='knapsack')
    roll = limb('roll', [(0, V(-0.17, -0.140, 1.448)), (1, V(0.17, -0.140, 1.448))],
                [(0, 0.030, 0.030, 0.030), (0.06, 0.043, 0.043, 0.043), (0.94, 0.043, 0.043, 0.043), (1, 0.030, 0.030, 0.030)],
                12 if hi else 4, 16 if hi else 8, fwd=V(0, 0, 1), slot='roll')
    parts = [pack, roll]
    # roll straps + pack flap edge
    for x in (-0.09, 0.09):
        parts.append(limb('strap', [(0, V(x, -0.140, 1.40)), (1, V(x, -0.140, 1.49))], [(0, 0.046, 0.046, 0.046)], 2, 10 if hi else 6,
                          fwd=V(0, 1, 0), slot='belt') if hi else None)
    if hi:
        parts.append(superellipsoid('pack.flap', V(0, -0.207, 1.315), (0.150, 0.007, 0.092), e=(6, 6), n=(24, 8), slot='knapsack'))
        for x in (-0.07, 0.07):
            parts.append(limb('pack.strap', [(0, V(x, -0.216, 1.40)), (1, V(x, -0.214, 1.20))], [(0, 0.011, 0.0025, 0.0025)], 8, 6,
                              fwd=V(0, 1, 0), slot='cartbox'))
            parts.append(superellipsoid('pack.buckle', V(x, -0.219, 1.215), (0.012, 0.003, 0.010), e=(6, 6), n=(10, 4), slot='metal'))
    return [p for p in parts if p]

def cartbox(hi=False):
    rot = Matrix.Rotation(math.radians(-18), 3, 'Z')
    box = superellipsoid('cart', V(0.105, -0.185, 0.965), (0.10, 0.034, 0.068), e=(5.0, 5.0), n=(16, 10) if hi else (8, 4),
                         rot=rot, slot='cartbox')
    return [box]

def scabbard(hi=False):
    a = V(-0.150, -0.075, 1.0); b = V(-0.168, -0.135, 0.70)
    sc = limb('scab', [(0, a), (1, b)], [(0, 0.012, 0.016, 0.016), (1, 0.008, 0.011, 0.011)], 6 if hi else 2, 8 if hi else 4,
              fwd=V(0, 1, 0), slot='scabbard')
    hilt = limb('hilt', [(0, a), (1, a + V(0.0, 0.03, 0.10))], [(0, 0.014, 0.014, 0.014), (1, 0.011, 0.011, 0.011)], 4 if hi else 1,
                8 if hi else 4, fwd=V(1, 0, 0), slot='metal')
    return [sc, hilt]

SHAKO_Z0, SHAKO_Z1 = 1.716, 1.866   # Kirk ref: body ~ face height (was 1.732..1.930), brim just above the brow
SHK_RX0, SHK_RY0 = 0.083, 0.100
SHAKO_DY = 0.024

def shako(hi=False):
    nu = 32 if hi else 20
    tilt = Matrix.Rotation(math.radians(-4), 3, 'X')
    base = V(0, 0.004, SHAKO_Z0)
    def T(p): return base + tilt @ (p - base)
    secs = []
    ts = [i / 160 for i in range(161)] if hi else [0.0, 0.06, 0.5, 0.94, 1.0]
    if hi: nu = 240   # fine enough that the plate outline in the id bake is smooth, not stepped
    for t in ts:
        z = lerp(SHAKO_Z0, SHAKO_Z1, t)
        rx = lerp(SHK_RX0, 0.092, t); ry = lerp(SHK_RY0, 0.106, t)
        bd = 0.0022 * (ss(0.0, 0.01, t) * ss(0.075, 0.065, t) + ss(0.925, 0.935, t))   # leather bands
        rx += bd; ry += bd
        secs.append([T(p) for p in ring(V(0, 0.004, z), V(1, 0, 0), V(0, 1, 0), rx, ry, ry, nu, 2.0, 0.5)])
    body = grid_sweep('shako', secs, cap0=True, cap1=True)
    def sslot(p):
        q = tilt.inverted() @ (p - base) + base
        if q.y > 0.06 and abs(q.x) / 0.036 + abs(q.z - 1.789) / 0.046 < 1.0:
            return 'metal'          # brass lozenge plate
        return 'felt'
    set_slot(body, sslot)
    # peak (visor)
    pk = []
    npk = 10 if hi else 5
    for j in range(npk + 1):
        a = math.pi * (0.12 + 0.76 * j / npk)
        c = V(math.cos(a), math.sin(a), 0)
        inner = V(SHK_RX0 * c.x, 0.004 + SHK_RY0 * c.y, SHAKO_Z0 + 0.004)
        outer = inner + V(c.x * 0.016, c.y * 0.055, -0.020)
        pk.append([T(inner), T(outer), T(outer + V(0, 0, 0.005)), T(inner + V(0, 0, 0.005))])
    peak = grid_sweep('peak', pk, closed_u=True, cap0=True, cap1=True, slot='felt')
    # plume on a short stem at the front-top, cockade below
    top = T(V(0, 0.086, SHAKO_Z1 - 0.004))
    plume = superellipsoid('plume', top + V(0, -0.004, 0.030), (0.030, 0.030, 0.038), e=(2, 2), n=(28, 18) if hi else (10, 6),
                           slot='plume')   # red pompom (concept)
    cock = superellipsoid('cockade', T(V(0, 0.108, SHAKO_Z1 - 0.020)), (0.021, 0.006, 0.021), e=(2, 2), n=(14, 6) if hi else (8, 3),
                          slot='collar')
    out = [body, peak, plume, cock]
    if hi:   # raised brass lozenge plate with a rim (bake only)
        pc = V(0, 0.004, 1.789); q = []
        for k in range(48):
            a = 2 * math.pi * k / 48; c, s_ = math.cos(a), math.sin(a)
            r = 1.0 / (abs(c) / 0.034 + abs(s_) / 0.044)
            q.append((c * r, s_ * r))
        rings = []
        for sc_, dz in ((1.0, 0.0), (1.0, 0.0022), (0.86, 0.0030), (0.0, 0.0034)):
            row = []
            for x, z in q:
                zz = pc.z + z * sc_
                tt = (zz - SHAKO_Z0) / (SHAKO_Z1 - SHAKO_Z0)
                ry = lerp(SHK_RY0, 0.106, tt) + 0.002
                row.append(T(V(x * sc_, pc.y + ry * math.sqrt(max(0.0, 1 - (x / lerp(SHK_RX0, 0.092, tt)) ** 2)) - 0.001 + dz, zz)))
            rings.append(row)
        out.append(grid_sweep('shako.plate', rings, cap0=False, cap1=False, slot='metal'))
    for o in out:   # stage 5: the MakeHuman cranium sits ~2.4 cm further forward than the stage-4 head
        o.data.transform(Matrix.Translation((0.0, SHAKO_DY, 0.0)))
    return out

def musket(hi=False):
    T = lambda p: R.REST['prop'] @ V(p)
    up = R.REST['prop'].to_3x3() @ V(0, 0, 1)
    side = R.REST['prop'].to_3x3() @ V(1, 0, 0)
    stock = [(-0.35, 0.021, -0.14, 0.012), (-0.26, 0.021, -0.118, 0.014), (-0.12, 0.019, -0.07, 0.014),
             (-0.01, 0.015, -0.036, 0.01), (0.07, 0.018, -0.03, 0.012), (0.2, 0.016, -0.026, 0.006),
             (0.98, 0.014, -0.022, 0.006), (1.02, 0.012, -0.018, 0.004)]
    nu = 12 if hi else 6
    secs = []
    for y, hw, zb, zt in stock:
        zc, hz = (zb + zt) / 2, (zt - zb) / 2
        secs.append(ring(T((0, y, zc)), side, up, hw, hz, hz, nu, 3.0))
    parts = [grid_sweep('stock', secs, slot='wood')]
    parts.append(limb('barrel', [(0, T((0, 0.02, 0.015))), (1, T((0, 1.12, 0.015)))], [(0, 0.0105, 0.0105, 0.0105), (1, 0.0095, 0.0095, 0.0095)],
                      2, 10 if hi else 5, fwd=up, slot='steel'))
    for y in ((0.42, 0.72, 0.97) if True else ()):
        parts.append(limb('band', [(0, T((0, y - 0.008, -0.004))), (1, T((0, y + 0.008, -0.004)))], [(0, 0.021, 0.030, 0.030)], 1,
                          10 if hi else 5, fwd=up, slot='steel'))
    parts.append(superellipsoid('lock', T((0.018, 0.05, 0.0)), (0.006, 0.05, 0.016), e=(4, 4), n=(8, 4), rot=R.REST['prop'].to_3x3(), slot='steel'))
    parts.append(limb('socket', [(0, T((0, 1.06, 0.002))), (1, T((0, 1.13, 0.002)))], [(0, 0.0145, 0.0145, 0.0145)], 1, 8 if hi else 5,
                      fwd=up, slot='steel'))
    parts.append(limb('bayonet', [(0, T((0.018, 1.115, -0.006))), (0.5, T((0.02, 1.32, -0.006))), (1, T((0.02, 1.52, -0.006)))],
                      [(0, 0.0085, 0.0085, 0.0085), (0.5, 0.0065, 0.0065, 0.0065), (1, 0.0008, 0.0008, 0.0008)], 4 if hi else 2, 6 if hi else 3,
                      fwd=up, slot='steel', cap1=False))
    sl = [T((0.0, 0.42, -0.03)), T((0.0, 0.2, -0.075)), T((0.0, -0.02, -0.1)), T((0.0, -0.28, -0.135))]
    secs = []
    for p in sl:
        secs.append([p + side * 0.003 + up * 0.011, p - side * 0.003 + up * 0.011, p - side * 0.003 - up * 0.011, p + side * 0.003 - up * 0.011])
    parts.append(grid_sweep('sling', secs, slot='belt'))
    return parts

# ------------------------------------------------------------------ assembly
def slot_body(o, near):
    def f(p):
        return body_slot(p, near(p))
    set_slot(o, f)

USE_MH = True
MH_LO = {'mhhead': 2400, 'mhhandR': 1000, 'mhhandL': 1000}   # LOD0 budgets (tris)

def mh_parts(hi):
    import human_mh as HM
    ph = HM.posed()
    out = [HM.part('mhhead', HM.head_faces(ph), ph), HM.eyes(ph, 'mheye'),
           HM.part('mhhandR', HM.hand_faces(ph, '.R'), ph), HM.part('mhhandL', HM.hand_faces(ph, '.L'), ph)]
    for o in out:
        if hi:
            HM.subdivide(o, 1 if o.name.startswith('mhhand') else 2)
        elif o.name.split('.')[0] in MH_LO:   # (the hi kit is built first, so the lo copies are named mhhead.001 ...)
            m = o.modifiers.new('d', 'DECIMATE'); m.ratio = min(1.0, MH_LO[o.name.split('.')[0]] / max(1, tris(o))); m.use_collapse_triangulate = True
            apply_mods(o)
    return out

def build_kit(hi, body_tree):
    parts = []
    if USE_MH:   # stage 5: MakeHuman CC0 head / eyes / hands (pipeline/human, human_mh.py), real skin albedo
        parts += mh_parts(hi)
    else:
        parts.append(build_head(192, 144) if hi else build_head(34, 22))
        parts += [build_hand(1, hi), build_hand(-1, hi)]
    if not hi:
        cb = collar_band((2, 28)); set_slot(cb, 'collar'); parts.append(cb)   # clean swept collar shell; the low body cage is fused without it (no voxel-ragged edge)
    parts += coat_tails(hi)
    parts += [crossbelt(body_tree, 1, hi), crossbelt(body_tree, -1, hi, off=0.0105)]
    parts += knapsack(hi) + cartbox(hi) + scabbard(hi) + shako(hi) + musket(hi)
    if hi: parts += buttons(body_tree)
    return parts

def preview_mats(o):
    """Workbench preview: one material per slot (palette colour)."""
    me = o.data
    a = me.attributes.get('slot')
    used = sorted(set(a.data[i].value for i in range(len(me.polygons)))) if a else [0]
    me.materials.clear()
    idx = {}
    for s in used:
        nm = 'pv_' + B.SLOT_NAMES[s]
        mat = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        h = B.PALETTE[B.SLOT_NAMES[s]].lstrip('#')
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        mat.diffuse_color = [x ** 2.2 for x in c] + [1]
        me.materials.append(mat); idx[s] = len(me.materials) - 1
    if a:
        for i, p in enumerate(me.polygons): p.material_index = idx[a.data[i].value]

def drop_small_islands(o, keep_frac=0.02):
    bm = bmesh.new(); bm.from_mesh(o.data)
    seen = set(); isl = []
    for f in bm.faces:
        if f.index in seen: continue
        st = [f]; comp = []; seen.add(f.index)
        while st:
            g = st.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); st.append(h)
        isl.append(comp)
    big = max(len(c) for c in isl)
    kill = [f for c in isl if len(c) < big * keep_frac for f in c]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(o.data); bm.free()
    return len(isl)


# ------------------------------------------------------------------ bake-only detail: buttons, folds, seams
def buttons(tree):
    """brass buttons on the lapels, waistcoat and cuffs, projected onto the high-poly body (bake source only)."""
    out = []
    def on_body(x, z, r=0.0075, slot='metal', d=+1):
        hit = tree.ray_cast(V(x, 0.5 * d, z), V(0, -d, 0))
        if hit[0] is None: return
        p, n = hit[0], hit[1]
        out.append(superellipsoid('button', p + n * 0.0015, (r, r, 0.0028), e=(2, 2.6), n=(14, 6),
                                  rot=n.to_track_quat('Z', 'Y').to_matrix(), slot=slot))
    for i in range(7):   # lapel buttons (habit-veste: 7 a side)
        z = lerp(1.38, 1.07, i / 6); lw = lerp(0.050, 0.098, ss(1.04, 1.40, z))
        for sx in (1, -1): on_body(sx * (lw - 0.017), z)
    for z in (0.94, 0.985, 1.025): on_body(0.0, z, 0.006)   # waistcoat
    return out

def add_folds(o, spread):
    """sculpted cloth folds on the fused high-poly (spread pose), stage 5b: compression folds with rounded bulges and
    sharp creases (|sin|^0.7 profile), phase-warped + amplitude-broken by low-frequency noise so they don't read as
    ripples. Inner elbows, armpit drag, back tension (shoulder blades -> waist), waist gathers, sleeve gathers above
    the cuffs, knee bunching above the gaiters; seams sunk, lapels / cuffs / collar proud. Numpy (was per-vertex python)."""
    import numpy as np
    me = o.data; me.update()
    n = len(me.vertices)
    P = np.zeros(n * 3); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    N = np.zeros(n * 3); me.vertices.foreach_get('normal', N); N = N.reshape(-1, 3)
    slot = np.zeros(len(me.polygons), np.int32); me.attributes['slot'].data.foreach_get('value', slot)
    lt = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lt)
    tot = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', tot)
    fs = np.repeat(slot, tot)
    def has(slots):
        m = np.zeros(n, bool); m[lt[np.isin(fs, list(slots))]] = True; return m
    # vertices on a slot boundary (seams): min != max slot over the vertex's faces
    mn = np.full(n, 99); mx = np.full(n, -1); np.minimum.at(mn, lt, fs); np.maximum.at(mx, lt, fs)
    seam = mn != mx
    x, y, z = P[:, 0], P[:, 1], P[:, 2]; ax = np.abs(x); sx = np.where(x > 0, 1.0, -1.0)
    def g(d, r): return np.exp(-(d * d) / (r * r))
    def s(a, b, t): t = np.clip((t - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
    def lfn(k):   # cheap smooth 3D noise (sum of sines), -1..1
        return (np.sin(k * 23.1 * x + 1.3 + 17.0 * z) * np.sin(k * 19.7 * z + 0.7 + 11.0 * y) + 0.5 * np.sin(k * 41.0 * y + 31.0 * x + 2.1)) / 1.5
    def fold(u):   # rounded bulges, sharp creases at the zero crossings
        return np.abs(np.sin(np.pi * u)) ** 0.7 - 0.55
    w = lfn(1.0); amp = 0.65 + 0.35 * lfn(2.3)
    d = np.zeros(n)
    sl = has({S['coat'], S['cuff'], S['lapel'], S['turnback'], S['collar'], S['waist'], S['breeches'], S['piping']}) | ~has({S['skin']})
    # inner elbow: arcs across the crook (front = +y)
    ex = 0.205 + spread; u = z - 1.14
    d += 0.0068 * s(-0.005, 0.03, y + 0.012) * g(ax - ex, 0.05) * g(u, 0.05) * fold(u / 0.022 + 2.2 * (y + 0.012) / 0.03 + 0.4 * w)
    # sleeve gathers above the cuffs
    d += 0.0032 * s(0.15 + spread, 0.19 + spread, ax) * g(z - 0.985, 0.035) * fold((z - 0.985) / 0.017 + 0.6 * w)
    # armpits: radial drag folds from the pit onto the sleeve and the coat side
    A = np.stack([sx * (0.150 + spread * 0.5), np.full(n, -0.005), np.full(n, 1.33)], 1)
    r = np.linalg.norm(P - A, axis=1); ang = np.arctan2(z - 1.33, y + 0.005)
    d += 0.0058 * g(r, 0.065) * s(0.012, 0.03, r) * fold(5.0 * ang / np.pi + 0.3 * w)
    # back tension: diagonal drag lines from the shoulder blades down towards the waist centre
    bk = s(-0.02, -0.05, y) * s(0.02, 0.05, ax) * (1 - s(0.15, 0.19, ax)) * g(z - 1.26, 0.11)
    perp = (ax * 0.62 + (z - 1.26) * 0.78)   # across the (0.13, 1.38) -> (0, 1.08) direction
    d += 0.0042 * bk * fold(perp / 0.034 + 0.5 * w)
    # waist: horizontal compression folds at the sides / back above the belt line
    d += 0.0045 * (ax > 0.05) * s(0.04, 0.0, y) * g(z - 1.06, 0.045) * fold((z - 1.06) / 0.019 + 8.0 * x + 0.5 * w)
    # knees: breeches bunching above the gaiter top + behind the knee
    leg = (z < 0.78) & (ax < 0.17)
    d += leg * 0.0052 * g(z - 0.60, 0.045) * fold((z - 0.60) / 0.021 + 12.0 * y + 0.5 * w)
    d += leg * 0.0045 * g(z - 0.50, 0.032) * s(0.0, -0.03, y - 0.012) * fold((z - 0.50) / 0.016 + 0.4 * w)
    # seat / back of the thigh drag under the tails
    d += 0.0030 * s(-0.02, -0.06, y) * g(z - 0.86, 0.06) * (ax < 0.17) * fold((x * 0.5 + (z - 0.86)) / 0.03 + 0.4 * w)
    d *= 1.5 * amp * sl   # ~2x the stage-4 peak-to-peak depth
    # seams: grooves where cloth panels meet; lapels / cuffs / collar stand proud
    d -= 0.0012 * seam
    d += 0.0016 * has({S['lapel'], S['piping']})
    d += 0.0010 * has({S['cuff'], S['collar']})
    P = P + N * d[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
