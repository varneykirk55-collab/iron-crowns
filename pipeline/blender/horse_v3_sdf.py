"""Horse v3 signed-distance modelling (numpy only, no bpy): anatomy primitives -> smooth-blended SDF -> surface nets
mesh. Every primitive carries a weight tag (a bone name or a chain name) used for the smooth skin weights."""
import math
import numpy as np
from horse_v3_config import LM, BONES

F32 = np.float32

def _v(p):
    return np.asarray(p, dtype=np.float64)

def rot_x(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def rot_y(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def rot_z(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

# ---------------------------------------------------------------------------------------------------------------------
# primitives: each is a dict with 'f' (P[N,3] -> d[N]) and 'box' (lo, hi) bounds
def sphere(c, r):
    c = _v(c)
    return {'f': lambda P: np.linalg.norm(P - c, axis=1) - r, 'box': (c - r, c + r)}

def ellipsoid(c, rad, R=None):
    c = _v(c); rad = _v(rad); Ri = None if R is None else np.asarray(R).T
    def f(P):
        q = P - c
        if Ri is not None:
            q = q @ Ri.T
        k0 = np.linalg.norm(q / rad, axis=1)
        k1 = np.linalg.norm(q / (rad * rad), axis=1)
        return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -rad.min())
    m = rad.max()
    return {'f': f, 'box': (c - m, c + m)}

def roundcone(a, b, ra, rb, scale=None):
    a = _v(a); b = _v(b)
    s = None if scale is None else _v(scale)
    ba = b - a; l2 = float(ba @ ba); rr = ra - rb; a2 = l2 - rr * rr; il2 = 1.0 / l2
    def f(P):
        p = P if s is None else a + (P - a) / s
        pa = p - a
        y = pa @ ba
        z = y - l2
        w = pa * l2 - np.outer(y, ba)
        x2 = np.einsum('ij,ij->i', w, w)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        d1 = np.sqrt(x2 + z2) * il2 - rb
        d2 = np.sqrt(x2 + y2) * il2 - ra
        d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - ra
        d = np.where(np.sign(z) * a2 * z2 > k, d1, np.where(np.sign(y) * a2 * y2 < k, d2, d3))
        return d if s is None else d * s.min()
    m = max(ra, rb) * (1.0 if s is None else max(1.0, s.max()))
    lo = np.minimum(a, b) - m; hi = np.maximum(a, b) + m
    return {'f': f, 'box': (lo, hi)}

def chain(pts, rads, scale=None):
    return [roundcone(pts[i], pts[i + 1], rads[i], rads[i + 1], scale) for i in range(len(pts) - 1)]

def box_round(c, half, r, R=None):
    c = _v(c); half = _v(half); Ri = None if R is None else np.asarray(R).T
    def f(P):
        q = P - c
        if Ri is not None:
            q = q @ Ri.T
        q = np.abs(q) - (half - r)
        return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(axis=1), 0) - r
    m = np.linalg.norm(half)
    return {'f': f, 'box': (c - m, c + m)}

def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def ssub(d, s, k):
    """subtract shape s from d (smooth)."""
    if k <= 0:
        return np.maximum(d, -s)
    h = np.clip(0.5 - 0.5 * (d + s) / k, 0, 1)
    return d * (1 - h) + (-s) * h + k * h * (1 - h)

def sint(a, b, k):
    return -smin(-a, -b, k)

# ---------------------------------------------------------------------------------------------------------------------
class Field:
    """ordered list of ops: ('u', prim, k, tag) smooth union, ('s', prim, k, None) smooth subtract,
    ('i', prim, k, None) smooth intersect, ('fn', callable(P, d) -> d) post op."""
    def __init__(self):
        self.ops = []

    def u(self, prims, k, tag):
        for p in (prims if isinstance(prims, list) else [prims]):
            self.ops.append(('u', p, k, tag))
        return self

    def s(self, prims, k):
        for p in (prims if isinstance(prims, list) else [prims]):
            self.ops.append(('s', p, k, None))
        return self

    def i(self, prims, k):
        for p in (prims if isinstance(prims, list) else [prims]):
            self.ops.append(('i', p, k, None))
        return self

    def post(self, fn):
        self.ops.append(('fn', fn, 0, None))
        return self

    def eval(self, P, want_tags=False):
        P = np.asarray(P, dtype=np.float64)
        d = np.full(len(P), 10.0)
        tags = {}
        for op, p, k, tag in self.ops:
            if op == 'fn':
                d = p(P, d); continue
            v = p['f'](P)
            if op == 'u':
                d = smin(d, v, k)
                if want_tags:
                    tags[tag] = v if tag not in tags else np.minimum(tags[tag], v)
            elif op == 's':
                d = ssub(d, v, k)
            elif op == 'i':
                d = sint(d, v, k)
        return (d, tags) if want_tags else d

    def grid(self, lo, hi, step):
        lo = _v(lo); hi = _v(hi)
        n = np.ceil((hi - lo) / step).astype(int) + 1
        xs = [lo[i] + np.arange(n[i]) * step for i in range(3)]
        F = np.full(tuple(n), 10.0, dtype=F32)
        full = None
        for op, p, k, tag in self.ops:
            if op == 'fn':
                if full is None:
                    X, Y, Z = np.meshgrid(*xs, indexing='ij')
                    full = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
                    del X, Y, Z
                F = p(full, F.ravel().astype(np.float64)).astype(F32).reshape(F.shape)
                continue
            blo, bhi = p['box']
            m = k + 2 * step + 0.01
            sl = []
            for i in range(3):
                a = int(max(0, math.floor((blo[i] - m - lo[i]) / step)))
                b = int(min(n[i], math.ceil((bhi[i] + m - lo[i]) / step) + 1))
                sl.append(slice(a, b))
            if any(s.start >= s.stop for s in sl):
                continue
            X, Y, Z = np.meshgrid(xs[0][sl[0]], xs[1][sl[1]], xs[2][sl[2]], indexing='ij')
            P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
            v = p['f'](P).reshape(X.shape)
            sub = F[sl[0], sl[1], sl[2]].astype(np.float64)
            if op == 'u':
                sub = smin(sub, v, k)
            elif op == 's':
                sub = ssub(sub, v, k)
            elif op == 'i':
                sub = sint(sub, v, k)
            F[sl[0], sl[1], sl[2]] = sub.astype(F32)
        return F, lo, step

def grad(field_fn, P, h=1e-3):
    P = np.asarray(P, float)
    g = np.zeros_like(P)
    for i in range(3):
        e = np.zeros(3); e[i] = h
        g[:, i] = (field_fn(P + e) - field_fn(P - e)) / (2 * h)
    n = np.linalg.norm(g, axis=1, keepdims=True)
    return g / np.maximum(n, 1e-9)

def project(field_fn, P, level=0.0, iters=8):
    """move points onto the iso-surface field == level along the gradient."""
    P = np.array(P, float)
    for _ in range(iters):
        d = field_fn(P) - level
        P = P - d[:, None] * grad(field_fn, P)
    return P

# ---------------------------------------------------------------------------------------------------------------------
def surface_nets(F, lo, step):
    """naive surface nets: one vertex per sign-changing cell (mean of edge crossings), one quad per sign-changing
    grid edge. Returns verts (N,3) world, quads (M,4) outward-wound (inside = F < 0)."""
    nx, ny, nz = F.shape
    C = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    views = [F[a:nx - 1 + a, b:ny - 1 + b, c:nz - 1 + c] for a, b, c in C]
    neg = [v < 0 for v in views]
    anyneg = np.logical_or.reduce(neg); allneg = np.logical_and.reduce(neg)
    act = anyneg & ~allneg
    I, J, K = np.nonzero(act)
    fc = np.stack([F[I + a, J + b, K + c] for a, b, c in C], 0).astype(np.float64)   # (8, M)
    E = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    Cv = np.array(C, float)
    acc = np.zeros((len(I), 3)); cnt = np.zeros(len(I))
    for e0, e1 in E:
        f0, f1 = fc[e0], fc[e1]
        cr = (f0 < 0) != (f1 < 0)
        t = np.where(cr, f0 / np.where(cr, f0 - f1, 1.0), 0.0)
        pos = Cv[e0][None, :] + t[:, None] * (Cv[e1] - Cv[e0])[None, :]
        acc += pos * cr[:, None]; cnt += cr
    loc = acc / np.maximum(cnt, 1)[:, None]
    verts = (np.stack([I, J, K], 1) + loc) * step + lo
    idx = -np.ones((nx - 1, ny - 1, nz - 1), dtype=np.int64)
    idx[I, J, K] = np.arange(len(I))
    quads = []
    ins = F < 0
    # x edges
    s0 = ins[:-1, 1:-1, 1:-1]; s1 = ins[1:, 1:-1, 1:-1]
    i, j, k = np.nonzero(s0 != s1); j = j + 1; k = k + 1
    q = np.stack([idx[i, j - 1, k - 1], idx[i, j, k - 1], idx[i, j, k], idx[i, j - 1, k]], 1)
    flip = ~ins[i, j, k]
    q[flip] = q[flip][:, ::-1]; quads.append(q)
    # y edges
    s0 = ins[1:-1, :-1, 1:-1]; s1 = ins[1:-1, 1:, 1:-1]
    i, j, k = np.nonzero(s0 != s1); i = i + 1; k = k + 1
    q = np.stack([idx[i - 1, j, k - 1], idx[i - 1, j, k], idx[i, j, k], idx[i, j, k - 1]], 1)
    flip = ~ins[i, j, k]
    q[flip] = q[flip][:, ::-1]; quads.append(q)
    # z edges
    s0 = ins[1:-1, 1:-1, :-1]; s1 = ins[1:-1, 1:-1, 1:]
    i, j, k = np.nonzero(s0 != s1); i = i + 1; j = j + 1
    q = np.stack([idx[i - 1, j - 1, k], idx[i, j - 1, k], idx[i, j, k], idx[i - 1, j, k]], 1)
    flip = ~ins[i, j, k]
    q[flip] = q[flip][:, ::-1]; quads.append(q)
    quads = np.concatenate(quads, 0)
    quads = quads[(quads >= 0).all(1)]
    return verts, quads

# ---------------------------------------------------------------------------------------------------------------------
def _m(p, sx):
    return (sx * p[0], p[1], p[2])

def horse_field():
    """the anatomical horse body (coat + hooves), tags = weight groups."""
    H = Field()
    # --- torso (tag 'torso' -> spine chain weights) --------------------------------------------------------------
    H.u(ellipsoid((0, 0.20, 1.10), (0.215, 0.38, 0.235), rot_x(-4)), 0.0, 'torso')           # rib cage
    H.u(ellipsoid((0, -0.08, 1.10), (0.24, 0.40, 0.225)), 0.10, 'torso')                   # barrel / belly
    H.u(ellipsoid((0, 0.06, 0.99), (0.17, 0.30, 0.11)), 0.10, 'torso')                      # belly floor
    for sx in (1, -1):
        H.u(ellipsoid((sx * 0.10, -0.48, 1.215), (0.17, 0.30, 0.20), rot_x(10)), 0.09, 'pelvis')    # glutes / quarters
        H.u(roundcone((sx * 0.11, -0.60, 1.16), (sx * 0.13, -0.58, 0.88), 0.15, 0.06, (0.85, 1, 1)), 0.07, 'pelvis')  # hamstrings
    H.u(chain([(0, -0.15, 1.25), (0, -0.44, 1.32), (0, -0.70, 1.26)], [0.075, 0.08, 0.055]), 0.07, 'pelvis')   # croup line
    H.u(chain([(0, 0.48, 1.37), (0, 0.32, 1.36), (0, 0.08, 1.228), (0, -0.20, 1.26)],
              [0.06, 0.075, 0.07, 0.08]), 0.08, 'torso')                                      # withers -> back -> loin
    # --- shoulders / chest -------------------------------------------------------------------------------------------
    for sx in (1, -1):
        H.u(ellipsoid((sx * 0.13, 0.53, 1.18), (0.07, 0.15, 0.26), rot_x(40)), 0.10, 'chest')        # shoulder blade
        H.u(ellipsoid((sx * 0.15, 0.56, 0.98), (0.09, 0.13, 0.13), rot_x(-30)), 0.06, 'f_humerus' + ('.R' if sx > 0 else '.L'))  # triceps / upper arm
    H.u(ellipsoid((0, 0.62, 1.03), (0.18, 0.14, 0.17)), 0.07, 'chest')                      # breast
    H.u(ellipsoid((0, 0.47, 0.92), (0.14, 0.15, 0.085)), 0.07, 'chest')                      # brisket / girth floor
    # --- neck (lateral squash) ---------------------------------------------------------------------------------------
    nk = (0.62, 1.0, 1.0)
    H.u(chain([(0, 0.52, 1.17), (0, 0.72, 1.42), (0, 0.83, 1.63), (0, 0.93, 1.75)], [0.30, 0.20, 0.12, 0.08], nk),
        0.08, 'neck')
    H.u(chain([(0, 0.42, 1.385), (0, 0.66, 1.56), (0, 0.86, 1.69), (0, 0.99, 1.78)], [0.06, 0.07, 0.06, 0.045],
              (0.75, 1.0, 1.0)), 0.07, 'neck')                                                # crest
    # --- head ------------------------------------------------------------------------------------------------------
    H.u(ellipsoid((0, 1.02, 1.735), (0.095, 0.10, 0.085), rot_x(-35)), 0.05, 'head')        # poll / cranium
    H.u(ellipsoid((0, 1.06, 1.57), (0.10, 0.125, 0.125), rot_x(-30)), 0.035, 'jaw')         # cheeks / jowl
    H.u(roundcone((0, 1.08, 1.72), (0, 1.29, 1.45), 0.082, 0.056, (0.95, 1, 1)), 0.05, 'head')    # face / nasal
    H.u(ellipsoid((0, 1.325, 1.39), (0.066, 0.075, 0.072), rot_x(-40)), 0.04, 'head')       # muzzle
    H.u(roundcone((0, 1.07, 1.575), (0, 1.29, 1.335), 0.05, 0.034, (0.95, 1, 1)), 0.05, 'jaw')     # lower jaw / chin
    for sx in (1, -1):
        H.u(ellipsoid((sx * 0.074, 1.13, 1.695), (0.022, 0.03, 0.016)), 0.025, 'head')      # brow over the eye
        H.u(ellipsoid((sx * 0.072, 1.17, 1.60), (0.02, 0.07, 0.02), rot_x(-45)), 0.04, 'head')    # facial crest
        H.u(ellipsoid((sx * 0.047, 1.377, 1.418), (0.014, 0.022, 0.024), rot_x(-40)), 0.012, 'head')   # nostril flare (alar)
    # ears: flattened round cones, inner hollow
    for sx, sd in ((1, '.R'), (-1, '.L')):
        a = (sx * 0.05, 0.995, 1.81); b = (sx * 0.072, 1.01, 1.955)
        H.u(roundcone(a, b, 0.036, 0.011, (1.0, 0.6, 1.0)), 0.02, 'ear' + sd)
    # --- legs ------------------------------------------------------------------------------------------------------
    for sx, sd in ((1, '.R'), (-1, '.L')):
        g = lambda n: n + sd
        L = {k: _m(v, sx) for k, v in LM.items() if k.startswith(('f_', 'h_'))}
        # front
        H.u(roundcone(L['f_shoulder'], L['f_elbow'], 0.10, 0.08), 0.06, g('f_humerus'))
        H.u(roundcone(_m((0.145, 0.43, 0.86), sx), _m((0.122, 0.465, 0.50), sx), 0.075, 0.045), 0.04, g('f_forearm'))
        H.u(ellipsoid(_m((0.14, 0.445, 0.74), sx), (0.062, 0.07, 0.13), rot_x(-4)), 0.04, g('f_forearm'))   # forearm muscle
        H.u(ellipsoid(_m((0.12, 0.47, 0.455), sx), (0.047, 0.05, 0.055)), 0.03, g('f_forearm'))         # knee (carpus)
        H.u(sphere(_m((0.12, 0.43, 0.465), sx), 0.026), 0.02, g('f_forearm'))                           # accessory carpal
        H.u(roundcone(_m((0.12, 0.472, 0.43), sx), _m((0.12, 0.47, 0.17), sx), 0.029, 0.027, (0.85, 1, 1)), 0.018, g('f_cannon'))
        H.u(roundcone(_m((0.12, 0.445, 0.42), sx), _m((0.12, 0.44, 0.18), sx), 0.017, 0.020), 0.012, g('f_cannon'))  # flexor tendons
        H.u(ellipsoid(_m((0.12, 0.458, 0.145), sx), (0.04, 0.05, 0.044)), 0.025, g('f_fetlock'))       # fetlock joint
        H.u(roundcone(_m((0.12, 0.47, 0.13), sx), _m((0.12, 0.502, 0.07), sx), 0.027, 0.031), 0.015, g('f_fetlock'))  # pastern
        H.u(roundcone(_m((0.12, 0.505, 0.07), sx), _m((0.12, 0.525, 0.012), sx), 0.036, 0.049, (1.0, 1.08, 1.0)), 0.010, g('f_hoof'))
        # hind
        H.u(roundcone(_m((0.14, -0.50, 1.10), sx), L['h_stifle'], 0.14, 0.08), 0.07, g('h_femur'))
        H.u(roundcone(_m((0.15, -0.47, 0.86), sx), _m((0.13, -0.625, 0.53), sx), 0.08, 0.042), 0.04, g('h_tibia'))
        H.u(ellipsoid(_m((0.14, -0.56, 0.74), sx), (0.06, 0.08, 0.13), rot_x(-30)), 0.045, g('h_tibia'))   # gaskin
        H.u(roundcone(_m((0.135, -0.66, 0.78), sx), _m((0.13, -0.69, 0.58), sx), 0.035, 0.03), 0.04, g('h_tibia'))   # achilles
        H.u(ellipsoid(_m((0.13, -0.635, 0.51), sx), (0.045, 0.065, 0.06)), 0.035, g('h_tibia'))         # hock joint
        H.u(sphere(_m((0.13, -0.695, 0.575), sx), 0.030), 0.02, g('h_tibia'))                             # point of hock
        H.u(roundcone(_m((0.13, -0.625, 0.47), sx), _m((0.125, -0.615, 0.17), sx), 0.031, 0.028, (0.85, 1, 1)), 0.018, g('h_cannon'))
        H.u(roundcone(_m((0.13, -0.655, 0.45), sx), _m((0.125, -0.64, 0.18), sx), 0.018, 0.020), 0.012, g('h_cannon'))
        H.u(ellipsoid(_m((0.125, -0.625, 0.145), sx), (0.04, 0.05, 0.044)), 0.025, g('h_fetlock'))
        H.u(roundcone(_m((0.125, -0.615, 0.13), sx), _m((0.125, -0.582, 0.07), sx), 0.026, 0.030), 0.015, g('h_fetlock'))
        H.u(roundcone(_m((0.125, -0.58, 0.07), sx), _m((0.125, -0.562, 0.012), sx), 0.034, 0.047, (1.0, 1.08, 1.0)), 0.010, g('h_hoof'))
    # tail dock
    H.u(chain([(0, -0.71, 1.285), (0, -0.78, 1.25), (0, -0.84, 1.16)], [0.048, 0.042, 0.034]), 0.06, 'tail')   # dock, flush with the croup (no lump)
    # --- carving -----------------------------------------------------------------------------------------------------
    for sx in (1, -1):
        H.s(ellipsoid((sx * 0.037, 1.388, 1.402), (0.011, 0.015, 0.021), rot_x(-40)), 0.008)   # nostrils (comma-shaped)
        H.s(ellipsoid((sx * 0.066, 1.036, 1.895), (0.016, 0.03, 0.055), rot_x(8)), 0.008)       # ear hollow (front face)
        H.s(sphere((sx * 0.094, 1.125, 1.675), 0.018), 0.014)                                  # eye socket
    H.s(ellipsoid((0, 1.34, 1.32), (0.066, 0.04, 0.011), rot_x(-40)), 0.012)                 # mouth line (soft: no notches)
    for sx in (1, -1):   # eyelids (after the socket carve) half-cover the eyeball -> no stuck-on disc
        H.u(ellipsoid((sx * 0.099, 1.125, 1.692), (0.013, 0.027, 0.009), rot_x(-8)), 0.006, 'head')    # upper lid
        H.u(ellipsoid((sx * 0.097, 1.122, 1.660), (0.011, 0.023, 0.006), rot_x(-8)), 0.006, 'head')    # lower lid
    H.post(lambda P, d: np.maximum(d, -(P[:, 2] - 0.002)))                                      # flat hoof soles
    return H

EYES = [((sx * 0.092, 1.125, 1.675), 0.021) for sx in (1, -1)]

# tag -> bone for chain-weighted groups
CHAINS = {
    'torso': ['pelvis', 'spine01', 'spine02', 'chest'],
    'neck': ['chest', 'neck01', 'neck02', 'neck03', 'head'],
    'tail': ['pelvis', 'tail_01', 'tail_02', 'tail_03'],
}
