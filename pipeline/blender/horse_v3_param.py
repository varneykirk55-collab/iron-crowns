"""Parametric (non-voxel) builders for horse v3 cloth and straps: ray-cast grid sheets with thickness, surface ribbons.
All return (V, F, fcls) with explicit per-face class codes (code = mat + 100 * variant) so colour bands are crisp."""
import math
import numpy as np

# ---------------------------------------------------------------------------------------------------------------------
class GridField:
    """trilinear sampler over a dense SDF grid F (nx, ny, nz) with origin lo and spacing step."""
    def __init__(self, F, lo, step):
        self.F = np.asarray(F, np.float32); self.lo = np.asarray(lo, float); self.step = float(step)
        self.n = np.array(self.F.shape)

    def __call__(self, P):
        P = np.asarray(P, float)
        q = (P - self.lo) / self.step
        i0 = np.floor(q).astype(int)
        out_lo = (i0 < 0).any(1) | (i0 >= self.n - 1).any(1)
        i0 = np.clip(i0, 0, self.n - 2)
        t = np.clip(q - i0, 0, 1)
        F = self.F
        x, y, z = i0[:, 0], i0[:, 1], i0[:, 2]
        tx, ty, tz = t[:, 0], t[:, 1], t[:, 2]
        c00 = F[x, y, z] * (1 - tx) + F[x + 1, y, z] * tx
        c10 = F[x, y + 1, z] * (1 - tx) + F[x + 1, y + 1, z] * tx
        c01 = F[x, y, z + 1] * (1 - tx) + F[x + 1, y, z + 1] * tx
        c11 = F[x, y + 1, z + 1] * (1 - tx) + F[x + 1, y + 1, z + 1] * tx
        v = (c00 * (1 - ty) + c10 * ty) * (1 - tz) + (c01 * (1 - ty) + c11 * ty) * tz
        return np.where(out_lo, 1.0, v)

def raycast(fn, O, Dirs, off, rmax=0.9, steps=180, iters=14):
    """first r where fn(O + r d) >= off, marching outward from O (assumed inside).  O, Dirs (N, 3)."""
    O = np.asarray(O, float); Dirs = np.asarray(Dirs, float)
    N = len(O)
    rs = np.linspace(0, rmax, steps)
    lo = np.zeros(N); hi = np.full(N, rmax); found = np.zeros(N, bool)
    prev = fn(O) - off
    for k in range(1, steps):
        v = fn(O + rs[k] * Dirs) - off
        hit = (~found) & (v >= 0) & (prev < 0)
        lo[hit] = rs[k - 1]; hi[hit] = rs[k]; found |= hit
        prev = np.where(found, prev, v)
        if found.all():
            break
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        v = fn(O + mid[:, None] * Dirs) - off
        inside = v < 0
        lo = np.where(inside, mid, lo); hi = np.where(inside, hi, mid)
    r = 0.5 * (lo + hi)
    return O + r[:, None] * Dirs, found

def arc_resample(curve, s_targets):
    """curve (M,3) -> points at arclength values s_targets (absolute)."""
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(curve, axis=0), axis=1))])
    return np.stack([np.interp(s_targets, L, curve[:, i]) for i in range(3)], -1), L[-1]

# ---------------------------------------------------------------------------------------------------------------------
def grid_mesh(G, fcls, thick, outward_ref=None, rim_cls=None):
    """G (nr, nc, 3) sheet -> closed slab of given thickness (inner layer offset along -normal).
    fcls (nr-1, nc-1) class codes.  outward_ref: point inside the body, used to orient normals outward."""
    nr, nc, _ = G.shape
    # vertex normals from grid tangents
    du = np.gradient(G, axis=1); dv = np.gradient(G, axis=0)
    Nn = np.cross(du, dv)
    Nn /= np.maximum(np.linalg.norm(Nn, axis=2, keepdims=True), 1e-12)
    if outward_ref is not None:
        ref = np.asarray(outward_ref, float)
        if ref.ndim == 1:
            ref = np.broadcast_to(ref, G.shape)
        s = np.sign(np.sum((G - ref) * Nn, axis=2).mean())
        Nn = Nn * (s if s != 0 else 1)
    idx = np.arange(nr * nc).reshape(nr, nc)
    Vo = G.reshape(-1, 3); Vi = (G - thick * Nn).reshape(-1, 3)
    V = np.concatenate([Vo, Vi], 0); off = nr * nc
    F = []; C = []
    for j in range(nr - 1):
        for i in range(nc - 1):
            a, b, c, d = idx[j, i], idx[j, i + 1], idx[j + 1, i + 1], idx[j + 1, i]
            F.append([a, b, c, d]); C.append(fcls[j, i])
            F.append([d + off, c + off, b + off, a + off]); C.append(fcls[j, i])
    # rims (boundary loop): rows 0 / nr-1, cols 0 / nc-1
    def rim(seq, cl):
        for k in range(len(seq) - 1):
            a, b = seq[k], seq[k + 1]
            F.append([b, a, a + off, b + off]); C.append(cl[k] if hasattr(cl, '__len__') else cl)
    rc = (lambda arr: arr) if rim_cls is None else (lambda arr: np.full(len(arr), rim_cls))
    rim(list(idx[0, :]), rc(fcls[0, :]))
    rim(list(idx[:, -1]), rc(fcls[:, -1]))
    rim(list(idx[-1, ::-1]), rc(fcls[-1, ::-1]))
    rim(list(idx[::-1, 0]), rc(fcls[::-1, 0]))
    F = np.array(F)
    # orientation: outer faces must face along Nn
    return V, F, np.array(C, int)

def ribbon(path, normals, half_w, half_t, cls_code, closed=False):
    """flat strap following path, lying on the surface with the given normals -> (V, F, fcls)."""
    p = np.asarray(path, float); n = np.asarray(normals, float)
    T = np.gradient(p, axis=0)
    if closed:
        T = np.roll(p, -1, 0) - np.roll(p, 1, 0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    n = n - np.sum(n * T, 1, keepdims=True) * T
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    B = np.cross(T, n)
    hw = np.broadcast_to(np.asarray(half_w, float), (len(p),))[:, None]
    ht = np.broadcast_to(np.asarray(half_t, float), (len(p),))[:, None]
    corners = [p + hw * B + ht * n, p - hw * B + ht * n, p - hw * B - ht * n, p + hw * B - ht * n]
    V = np.stack(corners, 1).reshape(-1, 3)
    F = []; M = len(p)
    rng = range(M) if closed else range(M - 1)
    for i in rng:
        i2 = (i + 1) % M
        for k in range(4):
            k2 = (k + 1) % 4
            F.append([i * 4 + k, i2 * 4 + k, i2 * 4 + k2, i * 4 + k2])
    if not closed:
        F.append([3, 2, 1, 0]); e = (M - 1) * 4; F.append([e, e + 1, e + 2, e + 3])
    cc = np.broadcast_to(np.asarray(cls_code), (len(F),)) if np.ndim(cls_code) == 0 else np.asarray(cls_code)
    return V, np.array(F), np.array(cc, int)

def ellipsoid_mesh(c, rad, R=None, segs=8, rings=5, cls_code=0):
    c = np.asarray(c, float); rad = np.asarray(rad, float)
    V = [c + np.array([0, 0, rad[2]])]
    for i in range(1, rings):
        th = math.pi * i / rings
        for k in range(segs):
            ph = 2 * math.pi * k / segs
            v = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)]) * rad
            V.append(c + (v @ np.asarray(R).T if R is not None else v))
    V.append(c - np.array([0, 0, rad[2]]))
    F = []
    for k in range(segs):
        F.append([0, 1 + k, 1 + (k + 1) % segs])
    for i in range(rings - 2):
        for k in range(segs):
            a = 1 + i * segs + k; b = 1 + i * segs + (k + 1) % segs
            F.append([a, a + segs, b + segs, b])
    last = len(V) - 1; base = 1 + (rings - 2) * segs
    for k in range(segs):
        F.append([last, base + (k + 1) % segs, base + k])
    return np.array(V), F, np.full(len(F), cls_code)

def join3(*ms):
    V = []; F = []; C = []; o = 0
    for m in ms:
        if m is None:
            continue
        v, f, c = m
        V.append(np.asarray(v, float)); F += [[int(i) + o for i in face] for face in f]; C += list(c); o += len(v)
    return np.concatenate(V, 0), F, np.array(C, int)

def lod_n(n0, lod, scale=(1.0, 0.5, 0.28), minimum=3):
    return max(minimum, int(round(n0 * scale[lod])))
