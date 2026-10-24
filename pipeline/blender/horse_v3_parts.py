"""Horse v3 parts (numpy only, no bpy): body, hair, eyes and the 1300 / 1800 tack + barding as part dicts.

part = {
  'name', 'layer',                      # layer = output mesh object (horse_body, horse_hair, ..., tack_1800, ...)
  'geo': (verts, faces)  or  'gen': fn(lod) -> (verts, faces)   # SDF parts give geo (decimated per LOD in bpy),
                                                                   # parametric tubes give gen (built per LOD)
  'smooth': laplacian iterations before decimation, 'sym': X-symmetric decimate, 'solidify': thickness (0 = none),
  'cls': fn(P_face_centroids) -> mat class per face,
  'col': fn(P, mat) -> (rgb[N,3], team[N]) per corner (P = corner vertex positions, mat = face class of the corner),
  'w':   weight spec: 'bone:<name>' | fn(P, ctx) -> {bone: w[N]}   (ctx.transfer(P), ctx.chain(P, bones, sigma))
}
All names / positions come from horse_v3_config (one dict to remap when Rob's HORSE_SKELETON_SPEC.md lands)."""
import math
import numpy as np
import horse_v3_config as C
import horse_v3_sdf as S

MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_BRASS, MAT_WOOD, MAT_HIDE, MAT_FUR, MAT_HAIR = 1, 2, 3, 4, 6, 8, 9, 11

def _sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def sym_box(lo, hi, step):
    """grid box with x symmetric about 0 so the surface-nets mesh is mirror-exact (for symmetric decimation)."""
    hx = max(abs(lo[0]), abs(hi[0]))
    n = int(math.ceil(2 * hx / step))
    hx = n * step / 2
    return (-hx, lo[1], lo[2]), (hx, hi[1], hi[2])

def grid_points(lo, n, step):
    xs = [lo[i] + np.arange(n[i]) * step for i in range(3)]
    return np.meshgrid(*xs, indexing='ij')

def nets(F, lo, step, keep=None):
    """surface nets + optional face filter keep(face_centroids) -> bool; drops unreferenced verts."""
    V, Q = S.surface_nets(F, lo, step)
    if keep is not None and len(Q):
        m = keep(V[Q].mean(1))
        Q = Q[m]
    if len(Q):   # drop tiny disconnected islands (stray specks from thin SDF features)
        lab = np.arange(len(V))
        for _ in range(400):
            m = lab[Q].min(1)
            new = lab.copy()
            for c in range(Q.shape[1]):
                np.minimum.at(new, Q[:, c], m)
            new = new[new]
            if np.array_equal(new, lab):
                break
            lab = new
        fl = lab[Q[:, 0]]
        u, cnt = np.unique(fl, return_counts=True)
        big = set(u[cnt >= max(40, int(0.002 * len(Q)))].tolist())
        Q = Q[np.array([f in big for f in fl])]
    used = np.unique(Q)
    remap = -np.ones(len(V), int); remap[used] = np.arange(len(used))
    return V[used], remap[Q]

def poly_sdf2(P2, poly):
    """signed distance to a closed 2D polygon (inside < 0). P2 (N,2), poly list of (y, z)."""
    v = np.asarray(poly, float); n = len(v)
    d = np.full(len(P2), 1e9); s = np.ones(len(P2))
    for i in range(n):
        a, b = v[i], v[i - 1]
        e = b - a; w = P2 - a
        t = np.clip((w @ e) / (e @ e), 0, 1)
        q = w - t[:, None] * e
        d = np.minimum(d, np.einsum('ij,ij->i', q, q))
        c1 = P2[:, 1] >= a[1]; c2 = P2[:, 1] < b[1]; c3 = e[0] * w[:, 1] > e[1] * w[:, 0]
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)

def polyline_dist(P, pts):
    pts = np.asarray(pts, float); d = np.full(len(P), 1e9); tpar = np.zeros(len(P))
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; e = b - a
        t = np.clip(((P - a) @ e) / (e @ e), 0, 1)
        di = np.linalg.norm(P - (a + t[:, None] * e), axis=1)
        m = di < d
        d = np.where(m, di, d); tpar = np.where(m, (L[i] + t * (L[i + 1] - L[i])) / L[-1], tpar)
    return d, tpar

def resample(pts, n):
    pts = np.asarray(pts, float)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    s = np.linspace(0, L[-1], n)
    return np.stack([np.interp(s, L, pts[:, i]) for i in range(3)], 1)

def smooth_path(pts, it=2):
    p = np.array(pts, float)
    for _ in range(it):
        p[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
    return p

def push_out(fn, P, off, iters=12):
    """move points that are closer than `off` to the surface of fn out onto the off level set."""
    P = np.array(P, float)
    for _ in range(iters):
        d = fn(P)
        m = d < off
        if not m.any():
            break
        P[m] = P[m] - (d[m] - off)[:, None] * S.grad(fn, P[m])
    return P

def on_surface(fn, pts, off, n=40):
    """anchor polyline -> resampled, projected onto fn == off, smoothed."""
    p = resample(pts, n)
    p = S.project(fn, p, off, 10)
    p = smooth_path(p, 2)
    return S.project(fn, p, off, 6)

def tube_mesh(path, r, sides, closed=False, cap=True):
    """parametric tube along a polyline -> (V, faces as lists)."""
    p = np.asarray(path, float); n = len(p)
    T = np.gradient(p, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N0 = np.cross(T[0], up); N0 /= np.linalg.norm(N0)
    Ns = [N0]
    for i in range(1, n):     # parallel transport
        v = Ns[-1] - (Ns[-1] @ T[i]) * T[i]; Ns.append(v / np.linalg.norm(v))
    Ns = np.array(Ns); Bs = np.cross(T, Ns)
    rr = np.broadcast_to(np.asarray(r, float), (n,))
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    V = (p[:, None, :] + rr[:, None, None] * (np.cos(ang)[None, :, None] * Ns[:, None, :]
                                           + np.sin(ang)[None, :, None] * Bs[:, None, :])).reshape(-1, 3)
    F = []
    m = n if closed else n - 1
    for i in range(m):
        i2 = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            F.append([i * sides + k, i * sides + k2, i2 * sides + k2, i2 * sides + k])
    V = list(V)
    if cap and not closed:
        for end, flip in ((0, True), (n - 1, False)):
            c = len(V); V.append(p[end])
            for k in range(sides):
                a, b = end * sides + k, end * sides + (k + 1) % sides
                F.append([b, a, c] if flip else [a, b, c])
    return np.array(V), F

def box_mesh(c, half, R=None):
    c = np.asarray(c, float); h = np.asarray(half, float)
    s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * h
    if R is not None:
        s = s @ np.asarray(R).T
    V = s + c
    F = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return V, F

def join(*meshes):
    V = []; F = []; o = 0
    for v, f in meshes:
        V.append(np.asarray(v, float)); F += [[i + o for i in face] for face in f]; o += len(v)
    return np.concatenate(V, 0), F

def mirror_x(P):
    return P * np.array([-1.0, 1, 1])

# ---------------------------------------------------------------------------------------------------------------------
# shared fields
HORSE = S.horse_field()
hd = HORSE.eval
_body_cache = {}

def horse_grid(lo, hi, step):
    key = (tuple(np.round(lo, 5)), tuple(np.round(hi, 5)), step)
    if key not in _body_cache:
        _body_cache[key] = HORSE.grid(lo, hi, step)
    return _body_cache[key]

def drape_eval(fn, P, reach=0.55, n=28):
    """column min of fn above each point (cloth hanging from the widest point)."""
    d = fn(P)
    for k in range(1, n + 1):
        d = np.minimum(d, fn(P + np.array([0, 0, reach * k / n])))
    return d

def cummin_down(F):
    """F[..., z] -> min over z' >= z (z axis = 2, ascending)."""
    return np.minimum.accumulate(F[:, :, ::-1], axis=2)[:, :, ::-1]

# head frame (poll -> muzzle)
_P0 = np.array(C.LM['poll'], float); _P1 = np.array(C.LM['muzzle'], float)
HEAD_AX = (_P1 - _P0) / np.linalg.norm(_P1 - _P0)
HEAD_LEN = float(np.linalg.norm(_P1 - _P0))
HEAD_DORSAL = np.array([0, -HEAD_AX[2], HEAD_AX[1]]) * (1 if -HEAD_AX[2] > 0 else -1)   # up / forward face normal

def head_tv(P):
    q = P - _P0
    return (q @ HEAD_AX) / HEAD_LEN, q @ HEAD_DORSAL

# ---------------------------------------------------------------------------------------------------------------------
# coats
def points_mask(P):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    front = (y > 0.15) & (z < 0.70)
    hind = (y < -0.2) & (z < 0.75)
    m = np.where(front, 1 - _sstep(0.40, 0.58, z), 0.0)
    m = np.where(hind, 1 - _sstep(0.44, 0.64, z), m)
    t, v = head_tv(P)
    m = np.maximum(m, np.where(z > 1.86, _sstep(1.86, 1.93, z), 0.0))      # ear tips / rims
    m = np.maximum(m, 0.35 * _sstep(0.84, 0.97, t) * (z > 1.2))              # muzzle
    return np.clip(m, 0, 1)

def coat_rgb(P, coat_name):
    cfg = C.COATS[coat_name]
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    base = np.asarray(cfg['coat'], float)[None, :] * (0.93 + 0.10 * _sstep(0.8, 1.5, z))[:, None]
    # slightly lighter flank / belly underside, darker topline
    base = base * (1.0 + 0.10 * (1 - _sstep(0.80, 0.95, z)) * (z > 0.75))[:, None]
    pm = points_mask(P)
    if cfg.get('points') is not None:
        base = base * (1 - pm[:, None]) + np.asarray(cfg['points'])[None, :] * pm[:, None]
    t, v = head_tv(P)
    skin = _sstep(0.90, 0.99, t) * (z > 1.2)                                  # dark muzzle skin
    base = base * (1 - 0.6 * skin[:, None]) + 0.6 * skin[:, None] * np.array([0.09, 0.075, 0.07])
    white = np.zeros(len(P))
    if cfg.get('blaze'):
        width = 0.020 + 0.018 * t
        white = np.maximum(white, ((np.abs(x) < width) & (v > 0.025) & (t > 0.10) & (t < 0.93)).astype(float))
    for s in cfg.get('socks', ()):
        sx = -1 if s.endswith('.L') else 1
        legy = (y > 0.15) if s.startswith('f_') else (y < -0.2)
        white = np.maximum(white, ((x * sx > 0.02) & legy & (z > 0.06) & (z < 0.22)).astype(float))
    base = base * (1 - white[:, None]) + white[:, None] * np.array([0.86, 0.84, 0.80])
    return np.clip(base, 0, 1)

def hoof_face(Pc):
    return Pc[:, 2] < 0.064

def hoof_blend(P, rgb):
    """Per-corner smooth blend coat -> hoof horn by height (no per-face colour streaks at the coronet)."""
    t = _sstep(0.050, 0.068, P[:, 2])[:, None]
    return rgb * t + np.asarray(C.HOOF_RGB, float)[None, :] * (1 - t)

# ---------------------------------------------------------------------------------------------------------------------
def body_part():
    st = C.VOXEL['body']
    lo, hi = sym_box((-0.36, -1.0, -0.02), (0.36, 1.48, 2.06), st)
    F, lo, st = horse_grid(lo, hi, st)
    V, Q = nets(F, lo, st)

    def cls(Pc):
        return np.where(hoof_face(Pc), MAT_LEATHER, MAT_HIDE)

    def col(P, mat):
        rgb = hoof_blend(P, coat_rgb(P, 'bay'))
        return rgb, np.zeros(len(P))

    def w(P, ctx):
        _, tags = HORSE.eval(P, want_tags=True)
        names = list(tags); D = np.stack([tags[n] for n in names], 1)
        dmin = D.min(1, keepdims=True)
        W = np.exp(-(D - dmin) / 0.022)
        out = {}
        for i, n in enumerate(names):
            if n in S.CHAINS:
                sub = ctx.chain(P, S.CHAINS[n], 0.06)
                for b, wb in sub.items():
                    out[b] = out.get(b, 0) + W[:, i] * wb
            else:
                out[n] = out.get(n, 0) + W[:, i]
        return out

    return {'name': 'body', 'layer': 'horse_body', 'geo': (V, Q), 'smooth': 3, 'post_smooth': 0.25, 'sym': True, 'solidify': 0, 'voxel': C.VOXEL['body'] * 0.9, 'lod_voxel': (1.0, 1.5, 2.2),
            'cls': cls, 'col': col, 'w': w, 'wsmooth': 4, 'coat': True}

def eye_part():
    def gen(lod):
        segs, rings = ((8, 5), (0, 0), (0, 0))[lod]
        if segs == 0:
            return None
        Vs = []; Fs = []
        for (c, r) in S.EYES:
            V = [np.array(c) + r * np.array([0, 0, 1.0])]
            for i in range(1, rings):
                th = math.pi * i / rings
                for k in range(segs):
                    ph = 2 * math.pi * k / segs
                    V.append(np.array(c) + r * np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)]))
            V.append(np.array(c) - r * np.array([0, 0, 1.0]))
            F = []
            for k in range(segs):
                F.append([0, 1 + k, 1 + (k + 1) % segs][::-1])
            for i in range(rings - 2):
                for k in range(segs):
                    a = 1 + i * segs + k; b = 1 + i * segs + (k + 1) % segs
                    F.append([a, a + segs, b + segs, b][::-1])
            last = len(V) - 1; base = 1 + (rings - 2) * segs
            for k in range(segs):
                F.append([last, base + (k + 1) % segs, base + k][::-1])
            Vs.append((np.array(V), F))
        V, F = join(*Vs)
        return V, F, np.full(len(F), MAT_LEATHER)
    return {'name': 'eyes', 'layer': 'horse_eyes', 'gen': gen, 'cls': lambda Pc: np.full(len(Pc), MAT_LEATHER),
            'col': lambda P, m: (np.tile(C.EYE_RGB, (len(P), 1)), np.zeros(len(P))), 'w': 'bone:head', 'flat': False}

# ---------------------------------------------------------------------------------------------------------------------
# hair: mane (+X side of the crest), forelock, tail.  locks = blended flattened round cones -> clumped strands
def _crest_points(n):
    crest = np.array([(0, 0.985, 1.815), (0, 0.90, 1.76), (0, 0.78, 1.67), (0, 0.64, 1.57), (0, 0.50, 1.49), (0, 0.40, 1.45)])
    p = resample(crest, n)
    return push_out(hd, p, 0.0, 6)

def hair_field(which='mane'):
    """which = 'mane' (mane + forelock) or 'tail'.  Two parts in the horse_hair layer (part_id) so a variant can drop
    the mane (1300 crinet) without losing the tail."""
    Hh = S.Field()
    rng = np.random.default_rng(7)
    if which == 'mane':
        base = _crest_points(30)
        for i, b in enumerate(base):
            t = i / (len(base) - 1)
            L = 0.12 + 0.13 * math.sin(math.pi * min(1, t * 1.15)) ** 0.7
            # two staggered rows: a full body of hair on the crest that falls to the +X side
            for row, (dx, dz, rs) in enumerate(((0.006, 0.020, 1.0), (0.030, 0.006, 0.85))):
                if row == 1 and i % 2:
                    continue
                p0 = b + np.array([dx, 0, dz])
                p1 = b + np.array([0.050 + dx, -0.03, -0.30 * L + 0.01])
                p2 = b + np.array([0.068 + dx + 0.02 * rng.random(), -0.05, -L * (0.9 + 0.2 * rng.random())])
                pts = push_out(hd, np.array([p0, p1, p2]), 0.016, 10)
                r0 = (0.030 if 0.05 < t < 0.95 else 0.020) * rs
                Hh.u(S.chain(list(map(tuple, pts)), [r0, 0.022 * rs, 0.008]), 0.016, 'mane')
        for k, (dx, ln) in enumerate(((-0.024, 0.16), (0.0, 0.20), (0.024, 0.15))):
            p0 = np.array([dx, 0.985, 1.84]); p1 = np.array([dx * 1.3, 1.04, 1.79]); p2 = np.array([dx * 1.6, 1.07, 1.84 - ln])
            pts = push_out(hd, np.array([p0, p1, p2]), 0.012, 10)
            Hh.u(S.chain(list(map(tuple, pts)), [0.020, 0.016, 0.006]), 0.012, 'forelock')
    else:
        # tail: one tapered volume (full at the middle, narrower from behind) + a few loose locks for a ragged tip
        spine = [(0, -0.725, 1.325), (0, -0.82, 1.18), (0, -0.885, 0.95), (0, -0.925, 0.70), (0, -0.945, 0.50)]
        Hh.u(S.chain(spine, [0.046, 0.058, 0.072, 0.066, 0.030], (0.78, 1.0, 1.0)), 0.03, 'tail')
        for k in range(6):
            a = 2 * math.pi * k / 6 + 0.4
            dx, dy = 0.035 * math.cos(a), 0.03 * math.sin(a)
            p0 = (dx, -0.92 + dy, 0.72); p1 = (dx * 1.2, -0.935 + dy, 0.55)
            p2 = (dx * 0.9 + 0.01 * rng.standard_normal(), -0.945 + dy, 0.40 + 0.06 * rng.random())
            Hh.u(S.chain([p0, p1, p2], [0.030, 0.024, 0.008]), 0.03, 'tail')
    def grooves(P, d):
        if which == 'tail':   # lock grooves running down the tail (8 around), a little twist with height
            ang = np.arctan2(P[:, 0] / 0.78, P[:, 1] + 0.90 + 0.04 * (1.3 - P[:, 2]))
            return d + 0.0065 * np.sin(8 * ang + 3.0 * P[:, 2]) * np.clip((1.25 - P[:, 2]) / 0.15, 0, 1)
        g = 0.0016 * np.sin(P[:, 0] * 260 + P[:, 1] * 40) + 0.0012 * np.sin(P[:, 1] * 300 + P[:, 2] * 90)
        return d + g
    Hh.post(grooves)
    return Hh

def hair_part(which='mane'):
    Hh = hair_field(which)
    st = C.VOXEL['hair']
    lo, hi = ((-0.20, 0.30, 1.0), (0.22, 1.12, 1.92)) if which == 'mane' else ((-0.14, -1.06, 0.32), (0.14, -0.66, 1.40))
    F, lo, st = Hh.grid(lo, hi, st)
    V, Q = nets(F, lo, st)

    def col(P, mat):
        return np.tile(C.COATS['bay']['hair'], (len(P), 1)), np.zeros(len(P))

    def w(P, ctx):
        tail = (P[:, 1] < -0.6)
        out = {}
        wt = ctx.chain(P, C.TAIL_CHAIN, 0.07)
        wb = ctx.transfer(P)
        for b, v in wb.items():
            out[b] = out.get(b, 0) + np.where(tail, 0, v)
        for b, v in wt.items():
            out[b] = out.get(b, 0) + np.where(tail, v, 0)
        return out
    return {'name': which, 'layer': 'horse_hair', 'geo': (V, Q), 'budget': {'mane': (760, 128, 44), 'tail': (1140, 128, 44)}[which], 'smooth': 1, 'voxel': C.VOXEL['hair'] * 0.8, 'lod_voxel': (1.0, 1.5, 2.2), 'sym': False, 'solidify': 0,
            'cls': lambda Pc: np.full(len(Pc), MAT_HAIR), 'col': col, 'w': w, 'wsmooth': 2, 'hair': True}

# ---------------------------------------------------------------------------------------------------------------------
# tack helpers
SY, ST = C.SEAT_Y, C.SEAT_TOP_Z
BRIDLE_OFF = 0.006

def weights_saddle_blend(P, ctx, r0=0.22, r1=0.55):
    """saddle near the seat, body transfer further away (cloth / straps that cover moving anatomy)."""
    s = _sstep(r0, r1, np.abs(P[:, 1] - (SY + 0.08)) + 0.4 * np.maximum(0, 1.2 - P[:, 2]))
    out = {'saddle': 1 - s}
    for b, v in ctx.transfer(P).items():
        out[b] = out.get(b, 0) + s * v
    return out

def w_transfer(P, ctx):
    return ctx.transfer(P)

def sdf_part(name, layer, field_fn, lo, hi, step, cls, col, w, smooth=1, sym=True, solidify=0.0):
    lo, hi = sym_box(lo, hi, step) if sym else (lo, hi)
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    n = np.ceil((hi - lo) / step).astype(int) + 1
    X, Y, Z = grid_points(lo, n, step)
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    del X, Y, Z
    F = field_fn(P, lambda: HORSE.grid(lo, lo + (n - 1.5) * step, step)[0].ravel().astype(float)).reshape(tuple(n))
    V, Q = nets(F.astype(np.float32), lo, step)
    return {'name': name, 'layer': layer, 'geo': (V, Q), 'smooth': smooth, 'sym': sym, 'solidify': solidify, 'voxel': step,
            'cls': cls, 'col': col, 'w': w, 'wsmooth': 2}

def strap_field(paths, off, th, half_w, extra=None):
    """leather straps lying on the horse: shell(horse, off) ∩ tube(path, half_w)."""
    def f(P, hgrid):
        h = hgrid()
        shell = np.abs(h - off) - th / 2
        band = shell < 0.012
        d = np.full(len(P), 1.0)
        for pth in paths:
            dist, _ = polyline_dist(P[band], pth)
            d[band] = np.minimum(d[band], dist - half_w)
        out = np.maximum(shell, d)
        if extra is not None:
            out = extra(P, h, out)
        return out
    return f

def torus_sdf(P, c, axis, R, r):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis)
    q = P - np.asarray(c, float)
    a = q @ axis
    rad = np.linalg.norm(q - a[:, None] * axis, axis=1)
    return np.sqrt((rad - R) ** 2 + a * a) - r

def leather_col(rgb):
    def col(P, mat):
        out = np.tile(rgb, (len(P), 1))
        out[mat == MAT_BRASS] = (0.78, 0.60, 0.25)
        out[mat == MAT_STEEL] = (0.62, 0.63, 0.66)
        return out, np.zeros(len(P))
    return col

# ---------------------------------------------------------------------------------------------------------------------
# bridle (both eras): cheekpieces + crown, browband, throatlatch, (noseband), bit, rings, reins on the rein chains
def bridle_paths(noseband=True):
    def side(pts):
        pts = np.asarray(pts, float)
        return np.concatenate([pts, mirror_x(pts[::-1])[1:]], 0)
    cheek = side([(C.BIT_RING_X - 0.010, 1.252, 1.40), (0.075, 1.17, 1.52), (0.093, 1.06, 1.655), (0.085, 0.985, 1.765),
                  (0.04, 0.965, 1.83), (0.0, 0.962, 1.845)])
    brow = side([(0.088, 0.99, 1.77), (0.06, 1.035, 1.79), (0.0, 1.05, 1.80)])
    throat = side([(0.088, 0.985, 1.765), (0.10, 0.955, 1.66), (0.075, 0.935, 1.56), (0.0, 0.93, 1.525)])
    paths = [on_surface(hd, p, BRIDLE_OFF, 50) for p in (cheek, brow, throat)]
    if noseband:
        c = _P0 + HEAD_AX * HEAD_LEN * 0.66
        Nn = np.array([1.0, 0, 0]); B = np.cross(HEAD_AX, Nn)
        ring = np.array([c + 0.16 * (math.cos(a) * Nn + math.sin(a) * B) for a in np.linspace(0, 2 * math.pi, 49)])
        paths.append(S.project(hd, ring, BRIDLE_OFF, 12))
    return paths


_rein_cache = {}
def rein_path(side, low=0.0, hand_dx=0.0):
    key = (side, low, hand_dx)
    if key not in _rein_cache:
        _rein_cache[key] = _rein_path(side, low, hand_dx)
    return _rein_cache[key].copy()

def _rein_path(side, low, hand_dx):
    """spec rest rein (bit ring -> rein_hand line, sag 0.10 * 4t(1-t)) built in spec coords, inverse-warped to the
    modelling frame, then kept off the neck (push_out; ends stay on the bit ring / rein_hand)."""
    sx = 1 if side == 'R' else -1
    a = np.array([sx * C.SPEC_BIT_RING_X, 1.30, 1.44 - low]); b = np.array([sx * (0.09 - hand_dx), 0.40, 1.66])
    t = np.linspace(0, 1, 40)[:, None]
    ps = a * (1 - t) + b * t
    ps[:, 2] -= 0.10 * 4 * t[:, 0] * (1 - t[:, 0])
    p = C.to_model(ps)
    q = push_out(hd, p, 0.020, 14)
    q[0] = p[0]; q[-1] = p[-1]
    return q

def rein_bones(side):
    return [(n, np.array(h), np.array(t)) for n, h, t, par, d in C.MODEL_EXTRA_BONES if n.startswith('rein_') and n.endswith(side)]

# ---------------------------------------------------------------------------------------------------------------------
# saddle cores (SDF) – the hussar tree hides under the sheepskin; the 1300 war saddle is the visible saddle
def core_1800(P, h):
    """hussar (Bock) tree: thin pad + pommel arch + cantle, unioned with the horse for the cloth drape."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    region = np.maximum(np.maximum(-0.16 - y, y - 0.40), 1.22 - z)
    pad = np.maximum(h - 0.006, region)
    q = P.copy(); q[:, 1] = q[:, 1] + 1.6 * x * x
    pom = S.box_round((0, 0.355, 1.50), (0.075, 0.022, 0.06), 0.02, S.rot_x(-18))['f'](q)
    q2 = P.copy(); q2[:, 1] = q2[:, 1] - 1.4 * x * x
    can = S.box_round((0, -0.115, 1.43), (0.12, 0.02, 0.05), 0.018, S.rot_x(18))['f'](q2)
    return S.smin(S.smin(pad, pom, 0.03), can, 0.03)

def core_1800_eval(P):
    return core_1800(P, hd(P))

def saddle_1300_field(P, h):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    t = 0.016 + 0.016 * _sstep(1.24, 1.33, z)
    region = np.maximum(np.maximum(-0.15 - y, y - 0.40), 1.12 - z)
    pad = np.maximum(np.maximum(h - t, 0.011 - h), region)
    # pommel: tall plate over the withers, curving back round the thighs
    q = P.copy(); q[:, 1] = q[:, 1] + 1.8 * x * x
    pom = S.box_round((0, 0.345, 1.535), (0.125, 0.018, 0.10), 0.016, S.rot_x(-14))['f'](q)
    pom = np.maximum(pom, -(h - 0.012))
    # cantle: wraps round the rider's hips (radius 0.21 about the seat), high at the back, lower at the sides
    r = np.sqrt(x * x + (y - SY) ** 2)
    ztop = 1.47 + 0.10 * np.clip(-(y - SY) / 0.21, 0, 1)
    can = np.maximum(np.maximum(np.abs(r - 0.215) - 0.013, z - ztop), np.maximum(1.33 - z, y - (SY - 0.07)))
    can = np.maximum(can, -(h - 0.012))
    return S.smin(S.smin(pad, pom, 0.025), can, 0.025)

def _base_horse_core(core):
    def fg(lo, n, step):
        Fh = HORSE.grid(lo, lo + (n - 1.5) * step, step)[0].astype(float)
        if core is None:
            return Fh
        X, Y, Z = grid_points(lo, n, step)
        P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        sel = (P[:, 2] > 1.15) & (P[:, 1] > -0.40) & (P[:, 1] < 0.55)
        out = Fh.ravel().copy()
        out[sel] = np.minimum(out[sel], core(P[sel], out[sel]))
        return out.reshape(Fh.shape)
    return fg



# =====================================================================================================================
# parametric tack (horse_v3_param): clean edges, crisp colour bands, per-LOD resolution
import horse_v3_param as PM

def wolf_teeth(y, period=0.055, amp=0.028):
    ph = (y / period) % 1.0
    return amp * (1 - 2 * np.abs(ph - 0.5))

TEAM = (0.62, 0.10, 0.09)
GOLD = (0.80, 0.62, 0.24)
CREAM = (0.84, 0.76, 0.50)
STEEL = (0.62, 0.63, 0.66)
V_TRIM = 100            # class variant: trim / lace (code = mat + 100 * variant)

def hn(P):
    """outward horse surface normal."""
    return S.grad(hd, np.asarray(P, float))

def part_gen(name, layer, gen, w, col):
    cache = {}
    def cached(lod):
        k = (lod, PM.RES)
        if k not in cache:
            cache[k] = gen(lod)
        return cache[k]
    return {'name': name, 'layer': layer, 'gen': cached, 'w': w, 'col': col, 'cls': None}

def code_col(table):
    """table: code -> (rgb, team)."""
    def col(P, code):
        out = np.zeros((len(P), 3)); team = np.zeros(len(P))
        for c, (rgb, t) in table.items():
            m = code == c
            out[m] = rgb; team[m] = t
        return out, team
    return col

# ---------------------------------------------------------------------------------------------------------------------
_drape_cache = {}
def drape_field(kind):
    """trilinear sampler of the cloth drape field (column min of horse [+ 1800 saddle core], head/neck cut)."""
    if kind in _drape_cache:
        return _drape_cache[kind]
    st = 0.0065
    lo = np.array([-0.48, -1.02, 0.25]); hi = np.array([0.48, 0.92, 1.80])
    n = np.ceil((hi - lo) / st).astype(int) + 1
    core = core_1800 if kind == '1800' else None
    Fb = _base_horse_core(core)(lo, n, st)
    ys = lo[1] + np.arange(n[1]) * st
    Fb = np.maximum(Fb, (ys - 0.78)[None, :, None])             # drop head / upper neck footprint
    D = cummin_down(Fb)
    _drape_cache[kind] = PM.GridField(D, lo, st)
    return _drape_cache[kind]

def slice_sheet(fn, off, y_back, y_front, hem, nc, nr, ny_tab=90, zc=1.08, band=None, phimax=172):
    """sheet over the back from y-slices: polar rays (x-z plane) from (0, y, zc); rows run side -> top -> side,
    truncated where z drops to hem(y).  y_back / y_front: fn(|t|) -> y edge (t = 0 top, 1 hem).
    band: trim width (m) -> rows/cols forced at the band boundary.  returns G (nr, nc, 3), (s, t) grids."""
    yt = np.linspace(min(y_back(0), y_back(1)), max(y_front(0), y_front(1)), ny_tab)
    nt = 161
    tt = np.linspace(-1, 1, nt)
    phis = np.radians(np.linspace(-phimax, phimax, 345))
    TAB = np.zeros((ny_tab, nt, 3)); Ls = np.zeros(ny_tab)
    O = np.zeros((ny_tab * len(phis), 3)); Dd = np.zeros_like(O)
    for i, y in enumerate(yt):
        sl = slice(i * len(phis), (i + 1) * len(phis))
        O[sl] = (0, y, zc); Dd[sl, 0] = np.sin(phis); Dd[sl, 2] = np.cos(phis)
    Pts, found = PM.raycast(fn, O, Dd, off, rmax=1.1, steps=220)
    Pts = Pts.reshape(ny_tab, len(phis), 3); found = found.reshape(ny_tab, len(phis))
    mid = len(phis) // 2
    for i, y in enumerate(yt):
        h = hem(np.array([y]))[0]
        cur = Pts[i]
        halves = []
        for sgn in (1, -1):
            idx = np.arange(mid, len(phis)) if sgn > 0 else np.arange(mid, -1, -1)
            seq = cur[idx]; ok = found[i, idx]
            stop = len(seq)
            for k in range(1, len(seq)):
                if (not ok[k]) or seq[k, 2] <= h:
                    stop = k; break
            seq = seq[:stop + 1].copy()
            if len(seq) >= 2 and seq[-1, 2] < h:             # cut exactly at the hem
                a, b = seq[-2], seq[-1]
                f = (a[2] - h) / max(a[2] - b[2], 1e-9)
                seq[-1] = a + f * (b - a)
            halves.append(seq)
        Lp = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(halves[0], axis=0), axis=1))])
        Lm = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(halves[1], axis=0), axis=1))])
        for j, t in enumerate(tt):
            if t >= 0:
                TAB[i, j] = [np.interp(t * Lp[-1], Lp, halves[0][:, c]) for c in range(3)]
            else:
                TAB[i, j] = [np.interp(-t * Lm[-1], Lm, halves[1][:, c]) for c in range(3)]
        Ls[i] = Lp[-1]
    Lmean = float(Ls.mean())
    t_rows = np.linspace(-1, 1, nr)
    s_cols = np.linspace(0, 1, nc)
    if band:
        tb = 1 - band / Lmean
        t_rows = np.unique(np.concatenate([t_rows, [-tb, tb]]))
        span = np.mean([y_front(0) - y_back(0), y_front(1) - y_back(1)])
        sb = band / span
        s_cols = np.unique(np.concatenate([s_cols, [sb, 1 - sb]]))
    Tg, Sg = np.meshgrid(t_rows, s_cols, indexing='ij')
    Y = y_back(np.abs(Tg)) * (1 - Sg) + y_front(np.abs(Tg)) * Sg
    fy = np.interp(Y, yt, np.arange(ny_tab)); fi = np.clip(np.floor(fy).astype(int), 0, ny_tab - 2); wy = fy - fi
    ft = (Tg + 1) / 2 * (nt - 1); fj = np.clip(np.floor(ft).astype(int), 0, nt - 2); wt = ft - fj
    def tab(a, b):
        return TAB[a, b]
    G = ((tab(fi, fj) * (1 - wt)[..., None] + tab(fi, fj + 1) * wt[..., None]) * (1 - wy)[..., None]
         + (tab(fi + 1, fj) * (1 - wt)[..., None] + tab(fi + 1, fj + 1) * wt[..., None]) * wy[..., None])
    # exact y (table interpolation keeps it close already)
    G[..., 1] = Y
    return G, Sg, Tg, Lmean

def face_st(Sg, Tg):
    s = 0.25 * (Sg[:-1, :-1] + Sg[1:, :-1] + Sg[:-1, 1:] + Sg[1:, 1:])
    t = 0.25 * (Tg[:-1, :-1] + Tg[1:, :-1] + Tg[:-1, 1:] + Tg[1:, 1:])
    return s, t

def cloth_part(name, layer, kind, off, thick, y_back, y_front, hem, res, band, main_code, trim_code, w, col,
               hem_only=False, edges=('hem', 'front', 'back'), zc=1.08):
    def gen(lod):
        nc = PM.lod_n(res[0], lod, minimum=4); nr = PM.lod_n(res[1], lod, minimum=5)
        G, Sg, Tg, Lm = slice_sheet(drape_field(kind), off, y_back, y_front, hem, nc, nr, band=band, zc=zc)
        s, t = face_st(Sg, Tg)
        tb = 1 - band / Lm if band else 2
        span = np.mean([y_front(0) - y_back(0), y_front(1) - y_back(1)])
        sb = band / span if band else -1
        trim = np.zeros(s.shape, bool)
        if 'hem' in edges:
            trim |= np.abs(t) > tb
        if 'front' in edges:
            trim |= s > 1 - sb
        if 'back' in edges:
            trim |= s < sb
        fc = np.where(trim, trim_code, main_code)
        ref = np.stack([np.zeros(G.shape[:2]), G[..., 1], np.full(G.shape[:2], zc)], -1)
        return PM.grid_mesh(G, fc, thick, outward_ref=ref)
    return part_gen(name, layer, gen, w, col)

# ---------------------------------------------------------------------------------------------------------------------
def strap(name, layer, pts, off, half_w, half_t, code, res, w, col, closed=False, project=True):
    """leather strap following anchor points across the horse surface (centre at off + half_t)."""
    base = on_surface(hd, pts, off + half_t, 80) if project else np.asarray(pts, float)
    def gen(lod):
        n = PM.lod_n(res, lod, minimum=4)
        p = resample(base, n) if not closed else resample(np.concatenate([base, base[:1]], 0), n + 1)[:-1]
        if project:
            p = S.project(hd, p, off + half_t, 4)
        return PM.ribbon(p, hn(p), half_w, half_t, code, closed=closed, flat=True)
    return part_gen(name, layer, gen, w, col)

def section_path(center, normal, a0, a1, off, n=60, down=(0, 0, -1.0)):
    """horse surface curve in the plane (center, normal): rays from center, angles a0..a1 (deg) from `down`."""
    nrm = np.asarray(normal, float); nrm /= np.linalg.norm(nrm)
    dn = np.asarray(down, float); dn = dn - (dn @ nrm) * nrm; dn /= np.linalg.norm(dn)
    side = np.cross(nrm, dn)
    angs = np.radians(np.linspace(a0, a1, n))
    Dd = np.cos(angs)[:, None] * dn + np.sin(angs)[:, None] * side
    O = np.tile(np.asarray(center, float), (n, 1))
    P, ok = PM.raycast(hd, O, Dd, off, rmax=0.6, steps=160)
    return P[ok]

def neck_sheet(off, thick, phimax, res, band, main_code, trim_code):
    """crinet: sections perpendicular to the neck spine, rays fanned over the crest."""
    spine = resample(np.array([(0, 0.53, 1.20), (0, 0.66, 1.38), (0, 0.78, 1.56), (0, 0.88, 1.69), (0, 0.935, 1.75)]), 60)
    def gen(lod):
        nj = PM.lod_n(res[0], lod, minimum=4); ni = PM.lod_n(res[1], lod, minimum=5)
        sp = resample(spine, nj)
        Tn = np.gradient(sp, axis=0); Tn /= np.linalg.norm(Tn, axis=1, keepdims=True)
        U = np.stack([np.zeros(nj), -Tn[:, 2], Tn[:, 1]], 1)
        U *= np.sign(U[:, 2:3] + 1e-9)
        phis = np.radians(np.linspace(-phimax, phimax, ni))
        tb = band
        phis = np.unique(np.concatenate([phis, np.radians([-phimax + tb, phimax - tb])]))
        ni = len(phis)
        X = np.array([1.0, 0, 0])
        O = np.repeat(sp, ni, 0)
        Dd = (np.cos(phis)[None, :, None] * U[:, None, :] + np.sin(phis)[None, :, None] * X[None, None, :]).reshape(-1, 3)
        P, ok = PM.raycast(hd, O, Dd, off, rmax=0.5, steps=120)
        G = P.reshape(nj, ni, 3)
        ph = 0.5 * (phis[:-1] + phis[1:])
        trim = np.abs(np.degrees(ph)) > phimax - tb
        fc = np.where(np.broadcast_to(trim[None, :], (nj - 1, ni - 1)), trim_code, main_code)
        return PM.grid_mesh(G, fc, thick, outward_ref=np.repeat(sp[:, None, :], ni, 1))
    return gen

# ---------------------------------------------------------------------------------------------------------------------
def bridle_parts(layer, rgb, noseband, brass):
    paths = bridle_paths(noseband)
    names = ['bridle_cheek', 'bridle_brow', 'bridle_throat', 'bridle_nose']
    col = code_col({MAT_LEATHER: (rgb, 0), MAT_BRASS: (GOLD, 0), MAT_STEEL: (STEEL, 0)})
    out = []
    for nm, p in zip(names, paths):
        closed = nm == 'bridle_nose'
        def gen(lod, p=p, closed=closed):
            n = PM.lod_n(60 if not closed else 40, lod, minimum=6)
            q = resample(p, n) if not closed else resample(p, n + 1)[:-1]
            q = S.project(hd, q, BRIDLE_OFF + 0.0035, 4)
            return PM.ribbon(q, hn(q), 0.010, 0.0035, MAT_LEATHER, closed=closed, flat=True)
        out.append(part_gen(nm, layer, gen, 'bone:head', col))
    if brass:
        def ros(lod):
            if lod == 2:
                return None
            ms = []
            for sx in (1, -1):
                c = S.project(hd, np.array([[sx * 0.088, 0.99, 1.77]]), BRIDLE_OFF + 0.009, 8)[0]
                ms.append(PM.ellipsoid_mesh(c, (0.016, 0.016, 0.016), segs=(6, 5)[lod], rings=(4, 3)[lod], cls_code=MAT_BRASS))
            return PM.join3(*ms)
        out.append(part_gen('rosettes', layer, ros, 'bone:head', col))
    return out

def bit_part(layer, curb=False):
    bx = C.BIT_RING_X
    bit = np.array([h for n, h, t, p, d in C.SOCKETS if n == 'rein_bit'][0], float)
    def gen(lod):
        sides = (4, 3, 3)[lod]; rn_ = (8, 6, 5)[lod]
        ms = [tube_mesh(np.array([[-bx, bit[1], bit[2]], [bx, bit[1], bit[2]]]), 0.0065, sides)]
        for sx in (1, -1):
            ring = np.array([[sx * bx, bit[1] + 0.022 * math.cos(a), bit[2] + 0.022 * math.sin(a)]
                             for a in np.linspace(0, 2 * math.pi, rn_, endpoint=False)])
            ms.append(tube_mesh(ring, 0.004, max(3, sides - 1), closed=True))
            if curb:
                sh = np.array([[sx * (bx + 0.006), bit[1] + 0.01, bit[2] + 0.06], [sx * (bx + 0.006), bit[1] + 0.005, bit[2] - 0.07]])
                ms.append(tube_mesh(sh, 0.005, max(3, sides - 1)))
        V, F = join(*ms)
        return V, F, np.full(len(F), MAT_STEEL)
    return part_gen('bit', layer, gen, 'bone:head', code_col({MAT_STEEL: (STEEL, 0)}))

def reins_part(layer, rgb, double=False):
    def gen(lod):
        n = PM.lod_n(22, lod, (1.0, 0.55, 0.32), 5); sides = (4, 3, 3)[lod]
        ms = []
        for side in ('R', 'L'):
            ms.append(tube_mesh(resample(rein_path(side), n), 0.0065, sides))
            if double and lod < 1:
                ms.append(tube_mesh(resample(rein_path(side, low=0.05, hand_dx=0.018), n), 0.0055, sides))
        V, F = join(*ms)
        return V, F, np.full(len(F), MAT_LEATHER)
    def w(P, ctx):
        out = {}
        for side in ('R', 'L'):
            sel = (P[:, 0] > 0) if side == 'R' else (P[:, 0] <= 0)
            names = [b[0] for b in rein_bones(side)]
            a = np.array(C.REIN_REST[side][0]); e = np.array(C.REIN_REST[side][-1])
            wa = 1 - _sstep(0.02, 0.06, np.linalg.norm(P - a, axis=1))     # spec: rein ends on rein_bit / rein_hand
            we = 1 - _sstep(0.02, 0.06, np.linalg.norm(P - e, axis=1))
            mid = np.clip(1 - wa - we, 0, 1)
            for b, v in ctx.chain(P, names, 0.05).items():
                out[b] = out.get(b, 0) + np.where(sel, v * mid, 0)
            out['rein_bit'] = out.get('rein_bit', 0) + np.where(sel, wa, 0)
            out['rein_hand.' + side] = np.where(sel, we, 0)
        return out
    return part_gen('reins', layer, gen, w, code_col({MAT_LEATHER: (rgb, 0)}))

def stirrup_part(layer, cloth_fn, iron_style, leather_rgb):
    soc = {n: (np.array(h), np.array(t)) for n, h, t, p, d in C.SOCKETS}
    eye_h = 0.14 if iron_style == '1800' else 0.16
    cache = {}
    def leather_path(side):
        h, tread = soc['stirrup.' + side]
        sx = np.sign(h[0])
        eye = tread + np.array([0, 0, eye_h])
        if side not in cache:
            t = np.linspace(0, 1, 24)[:, None]
            p = h * (1 - t) + eye * t
            for _ in range(60):
                m = cloth_fn(p) < 0.010
                if not m.any():
                    break
                p[m, 0] += sx * 0.004
            p = smooth_path(p, 3)
            p[-1] = eye
            cache[side] = p
        return cache[side].copy(), eye, tread, sx
    def gen(lod):
        ms = []
        sides = (5, 5, 5)[lod]; na = (9, 6, 4)[lod]
        for side in ('R', 'L'):
            p, eye, tread, sx = leather_path(side)
            p = resample(p, PM.lod_n(12, lod, (1.0, 0.5, 0.25), 3))
            nrm = np.tile([sx, 0, 0], (len(p), 1)).astype(float)
            ms.append(PM.ribbon(p, nrm, 0.014, 0.003, MAT_LEATHER, flat=True))
            w_ = 0.062 if iron_style == '1800' else 0.07
            ex = 1.0 if iron_style == '1800' else 0.75
            arch = np.array([tread + np.array([w_ * math.cos(a), 0, (eye_h - 0.005) * math.sin(a) ** ex])
                             for a in np.linspace(0, math.pi, na)])
            V, F = tube_mesh(arch, 0.0065 if iron_style == '1800' else 0.008, max(3, sides - 2))
            ms.append((V, F, np.full(len(F), MAT_STEEL)))
            if lod < 2:
                V, F = box_mesh(tread + np.array([0, 0, -0.004]), (w_ + 0.006, 0.024 if iron_style == '1800' else 0.03, 0.005))
                ms.append((V, F, np.full(len(F), MAT_STEEL)))
        return PM.join3(*ms)
    def w(P, ctx):
        out = {'saddle': np.zeros(len(P))}
        for side in ('R', 'L'):
            h, tread = soc['stirrup.' + side]
            sel = np.sign(P[:, 0]) == np.sign(h[0])
            t = np.clip((h[2] - P[:, 2]) / (h[2] - tread[2]), 0, 1)
            ws = _sstep(0.0, 0.3, t)
            out['saddle'] += np.where(sel, 1 - ws, 0)
            out['stirrup.' + side] = np.where(sel, ws, 0)
        return out
    return part_gen('stirrups', layer, gen, w, code_col({MAT_LEATHER: (leather_rgb, 0), MAT_STEEL: (STEEL, 0)}))

def girth_part(layer, rgb, off, half_w):
    n = np.array([0, math.cos(math.radians(12)), -math.sin(math.radians(12))])
    p = section_path((0, 0.27, 1.02), n, -100, 100, off + 0.004, 80)
    p = p[p[:, 2] < 1.24]
    def gen(lod):
        q = resample(p, PM.lod_n(40, lod, minimum=8))
        return PM.ribbon(q, hn(q), half_w, 0.004, MAT_LEATHER, flat=True)
    return part_gen('girth', layer, gen, 'bone:saddle', code_col({MAT_LEATHER: (rgb, 0)}))

def dock_loop(layer, rgb, off):
    c = np.array([0, -0.755, 1.295]); ax = np.array([0, -0.85, -0.53]); ax /= np.linalg.norm(ax)
    e1 = np.array([1.0, 0, 0]); e2 = np.cross(ax, e1)
    def gen(lod):
        k = PM.lod_n(16, lod, minimum=6)
        a = np.linspace(0, 2 * math.pi, k, endpoint=False)
        Dd = np.cos(a)[:, None] * e1 + np.sin(a)[:, None] * e2
        P, ok = PM.raycast(hd, np.tile(c, (k, 1)), Dd, off, rmax=0.2, steps=60)
        return PM.ribbon(P, Dd, 0.012, 0.004, MAT_LEATHER, closed=True, flat=True)
    return part_gen('crupper_dock', layer, gen, lambda P, ctx: ctx.chain(P, ['tail_01', 'tail_02'], 0.05),
                    code_col({MAT_LEATHER: (rgb, 0)}))

def crupper_w(P, ctx):
    return weights_saddle_blend(P, ctx, 0.25, 0.5)

# ---------------------------------------------------------------------------------------------------------------------
def tack_1800():
    L = 'tack_1800'
    parts = []
    black = (0.07, 0.06, 0.055)
    wool = code_col({MAT_WOOL: (TEAM, 1), MAT_BRASS + V_TRIM: (GOLD, 0), MAT_BRASS: (GOLD, 0)})
    sb_w = lambda P, ctx: weights_saddle_blend(P, ctx, 0.25, 0.60)
    # shabraque with Vandyke (pointed) rear corner and gold lace border
    parts.append(cloth_part('shabraque', L, '1800', 0.009, 0.005,
                            y_back=lambda t: -0.50 - 0.30 * t ** 1.5, y_front=lambda t: 0.44 + 0.03 * t,
                            hem=lambda y: 0.985 - 0.06 * _sstep(-0.1, -0.75, y), res=(34, 26), band=0.032,
                            main_code=MAT_WOOL, trim_code=MAT_BRASS + V_TRIM, w=sb_w, col=wool))
    # sheepskin over the seat, team-colour wolf-teeth (Vandyke) border
    sk = code_col({MAT_FUR: ((0.90, 0.88, 0.83), 0), MAT_WOOL: (TEAM, 1)})
    parts.append(cloth_part('sheepskin', L, '1800', 0.024, 0.012,
                            y_back=lambda t: -0.20 - 0.02 * t, y_front=lambda t: 0.42 + 0.0 * t,
                            hem=lambda y: 1.170 - wolf_teeth(y), res=(42, 16), band=0.035,
                            main_code=MAT_FUR, trim_code=MAT_WOOL, w=sb_w, col=sk))
    # portmanteau (valise) behind the cantle
    yv = -0.29
    zs = np.linspace(1.2, 1.6, 400)
    ztop = float(zs[hd(np.stack([np.zeros(400), np.full(400, yv), zs], 1)) < 0].max())
    zc = ztop + 0.010 + 0.068
    def valise(P, hgrid):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        r2 = np.sqrt((y - yv) ** 2 + ((z - zc) * 1.05) ** 2)
        q = np.stack([np.abs(x) - 0.20, r2 - 0.068], 1)
        return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0) - 0.012
    val = sdf_part('valise', L, valise, (-0.24, yv - 0.10, zc - 0.10), (0.24, yv + 0.10, zc + 0.10), 0.0045,
                   lambda Pc: np.where(np.abs(Pc[:, 0]) > 0.180, MAT_BRASS, MAT_WOOL), wool, 'bone:saddle', smooth=1)
    val['budget'] = (170, 60, 0); val['skip'] = (2,); val['sharp'] = 60
    parts.append(val)
    parts.append(girth_part(L, (0.30, 0.20, 0.12), 0.012, 0.035))
    lcol = code_col({MAT_LEATHER: (black, 0), MAT_BRASS: (GOLD, 0)})
    parts.append(strap('breastplate', L, [(0.20, 0.38, 1.22), (0.21, 0.55, 1.17), (0.15, 0.70, 1.11), (0.06, 0.785, 1.09),
                                          (0, 0.795, 1.09), (-0.06, 0.785, 1.09), (-0.15, 0.70, 1.11), (-0.21, 0.55, 1.17),
                                          (-0.20, 0.38, 1.22)], 0.010, 0.016, 0.0045, MAT_LEATHER, 50, w_transfer, lcol))
    parts.append(strap('martingale', L, [(0, 0.795, 1.09), (0, 0.76, 0.96), (0, 0.66, 0.85), (0, 0.45, 0.80), (0, 0.30, 0.79)],
                       0.010, 0.016, 0.0045, MAT_LEATHER, 26, w_transfer, lcol))
    heart_c = S.project(hd, np.array([[0, 0.80, 1.09]]), 0.022, 10)[0]
    def heart(lod):
        segs, rings = ((10, 6), (6, 4), (4, 3))[lod]
        return PM.ellipsoid_mesh(heart_c, (0.036, 0.016, 0.040), segs=segs, rings=rings, cls_code=MAT_BRASS)
    parts.append(part_gen('heart', L, heart, w_transfer, lcol))
    parts.append(strap('crupper', L, [(0, -0.16, 1.40), (0, -0.40, 1.45), (0, -0.62, 1.42), (0, -0.70, 1.37)],
                       0.014, 0.016, 0.0045, MAT_LEATHER, 26, crupper_w, lcol))
    parts.append(dock_loop(L, black, 0.012))
    parts += bridle_parts(L, black, noseband=True, brass=True)
    parts.append(bit_part(L, curb=True))
    parts.append(reins_part(L, black, double=True))
    df = drape_field('1800')
    parts.append(stirrup_part(L, lambda P: df(P) - 0.026, '1800', black))
    return parts

def tack_1300():
    L = 'tack_1300'
    parts = []
    brown = (0.33, 0.19, 0.10)
    def sad(P, hgrid):
        return saddle_1300_field(P, hgrid())
    def sad_cls(Pc):
        x, y, z = Pc[:, 0], Pc[:, 1], Pc[:, 2]
        r = np.sqrt(x * x + (y - SY) ** 2)
        pom = (y > 0.30) & (z > 1.42)
        can = (np.abs(r - 0.215) < 0.03) & (y < SY - 0.04) & (z > 1.36)
        return np.where(pom | can, MAT_WOOD, MAT_LEATHER)
    sad_col = code_col({MAT_LEATHER: (brown, 0), MAT_WOOD: (TEAM, 1)})
    sp = sdf_part('saddle', L, sad, (-0.34, -0.22, 1.08), (0.34, 0.46, 1.70), C.VOXEL['saddle'] * 0.8,
                  sad_cls, sad_col, 'bone:saddle', smooth=1)
    sp['budget'] = (880, 280, 100)
    parts.append(sp)
    parts.append(girth_part(L, brown, 0.009, 0.04))
    lcol = code_col({MAT_LEATHER: (brown, 0)})
    parts.append(strap('peytral', L, [(0.21, 0.36, 1.26), (0.22, 0.55, 1.18), (0.15, 0.70, 1.12), (0.06, 0.785, 1.10),
                                      (0, 0.795, 1.10), (-0.06, 0.785, 1.10), (-0.15, 0.70, 1.12), (-0.22, 0.55, 1.18),
                                      (-0.21, 0.36, 1.26)], 0.010, 0.022, 0.0045, MAT_LEATHER, 50, w_transfer, lcol))
    parts.append(strap('crupper', L, [(0, -0.16, 1.40), (0, -0.40, 1.45), (0, -0.62, 1.42), (0, -0.70, 1.37)],
                       0.012, 0.018, 0.0045, MAT_LEATHER, 26, crupper_w, lcol))
    parts.append(dock_loop(L, brown, 0.012))
    parts += bridle_parts(L, brown, noseband=False, brass=False)
    parts.append(bit_part(L, curb=False))
    parts.append(reins_part(L, brown, double=False))
    parts.append(stirrup_part(L, lambda P: drape_field('1300')(P) - 0.034, '1300', brown))
    return parts

CAP_HEM = 0.60   # spec: caparison skirt cut at the forearm so the gait reads (was 0.36, above the fetlocks)

def barding_1300():
    L = 'barding_1300'
    parts = []
    cap_col = code_col({MAT_WOOL: (TEAM, 1), MAT_WOOL + V_TRIM: (CREAM, 0)})
    def torso_w(P, ctx):
        Q = P.copy(); Q[:, 0] = 0; Q[:, 2] = np.maximum(Q[:, 2], 1.05)
        return ctx.chain(Q, ['pelvis', 'spine01', 'spine02', 'chest'], 0.08)
    # rear / body caparison: from behind the shoulder over the back and quarters, hem just above the fetlocks
    parts.append(cloth_part('caparison', L, '1300', 0.032, 0.005,   # pass 2: 0.032 clears the rounder croup
                            y_back=lambda t: -0.745 - 0.11 * t,   # back edge stops at the tail root (dock exits)
                            y_front=lambda t: 0.50 + 0.02 * t,
                            hem=lambda y: CAP_HEM + 0 * y, res=(36, 28), band=0.06,
                            main_code=MAT_WOOL, trim_code=MAT_WOOL + V_TRIM, w=torso_w, col=cap_col,
                            edges=('hem',), zc=1.02))
    # front (chest) curtain: horizontal rays round a vertical axis
    df = drape_field('1300')
    def front(lod):
        na = PM.lod_n(24, lod, minimum=6); nz = PM.lod_n(18, lod, minimum=5)
        th = np.radians(np.linspace(-98, 98, na))
        zt = lambda a: 1.36 - 0.10 * (np.abs(a) / np.radians(98)) ** 1.5
        band = 0.06
        G = np.zeros((nz + 1, na, 3)); fc = np.zeros((nz, na - 1), int)
        rows = []
        for j in range(nz + 1):
            rows.append(j / nz)
        rows = np.unique(np.concatenate([rows, [band / 0.9]]))
        G = np.zeros((len(rows), na, 3))
        for i, a in enumerate(th):
            top = zt(a)
            zs = top - (top - CAP_HEM) * rows
            O = np.stack([np.zeros(len(zs)), np.full(len(zs), 0.30), zs], 1)
            Dd = np.tile([math.sin(a), math.cos(a), 0.0], (len(zs), 1))
            P, ok = PM.raycast(df, O, Dd, 0.026, rmax=0.8, steps=160)
            G[:, i] = P
        rr = 0.5 * (rows[:-1] + rows[1:])
        hemrow = (1 - rr) * 1.0 < band / 0.9 + 1e-6
        fc = np.where(np.broadcast_to(hemrow[:, None], (len(rows) - 1, na - 1)), MAT_WOOL + V_TRIM, MAT_WOOL)
        ref = np.stack([np.zeros(G.shape[:2]), np.full(G.shape[:2], 0.30), G[..., 2]], -1)
        return PM.grid_mesh(G, fc, 0.005, outward_ref=ref)
    parts.append(part_gen('caparison_front', L, front, torso_w, cap_col))
    # crinet over the crest
    cr = neck_sheet(0.028, 0.005, 118, (16, 18), 14, MAT_WOOL, MAT_WOOL + V_TRIM)
    parts.append(part_gen('crinet', L, cr, w_transfer, cap_col))
    # chanfron: steel plate over the face with eye holes
    eyes = [np.array(c) for c, r in S.EYES]
    def chanfron(P, hgrid):
        h = hgrid()
        t, v = head_tv(P)
        x = P[:, 0]
        width = 0.075 + 0.02 * (1 - t)
        reg = np.maximum.reduce([0.10 - t, t - 0.86, np.abs(x) - width, -0.005 - v])
        d = np.maximum(np.abs(h - 0.012) - 0.0035, reg)
        for e in eyes:
            d = np.maximum(d, -(np.linalg.norm(P - e, axis=1) - 0.034))
        return d
    ch = sdf_part('chanfron', L, chanfron, (-0.14, 0.94, 1.30), (0.14, 1.42, 1.86), 0.003,
                  lambda Pc: np.full(len(Pc), MAT_STEEL), code_col({MAT_STEEL: (STEEL, 0)}), 'bone:head', smooth=1)
    ch['budget'] = (300, 110, 50)   # no edge split: on a 7 mm plate it doubles the verts (rim reads fine smooth)
    parts.append(ch)
    return parts

def all_parts():
    import time
    out = {}
    for k, fn in (('body', lambda: [body_part()]), ('hair', lambda: [hair_part('mane'), hair_part('tail')]), ('eyes', lambda: [eye_part()]),
                  ('tack_1800', tack_1800), ('tack_1300', tack_1300), ('barding_1300', barding_1300)):
        t = time.time(); out[k] = fn(); print('  parts %-12s %.1fs' % (k, time.time() - t), flush=True)
    for k in out:   # far set (LOD2, <= 0.6k verts horse + tack): drop the small bits
        for p in out[k]:
            if p['name'] in LOD2_SKIP:
                p['skip'] = tuple(sorted(set(p.get('skip', ())) | {2}))
    return out

LOD2_SKIP = {'heart', 'crupper_dock', 'martingale', 'bridle_throat', 'bridle_brow', 'bit', 'rosettes'}
