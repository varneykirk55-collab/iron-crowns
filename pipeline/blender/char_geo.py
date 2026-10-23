"""Character refinement: procedural mesh accumulation for the semi-realistic c19 soldiers.
Pure python (mathutils only) until to_object(). Every vertex carries skin weights; every face a colour slot,
material class, team amount and smooth flag. Coordinates: Blender, Z up, character faces +Y, +X = its right."""
import math
from mathutils import Vector, Matrix, Quaternion

def V(*a):
    return Vector(a[0] if len(a) == 1 else a)

def smoothstep(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return a + (b - a) * t

class Chain:
    """Skin weights along a bone chain [(bone, head, tail), ...] with a smooth blend zone at each joint."""
    def __init__(self, segs, blend=0.04, blends=None):
        self.segs = [(b, V(h), V(t)) for b, h, t in segs]
        self.cum = [0.0]
        for b, h, t in self.segs:
            self.cum.append(self.cum[-1] + (t - h).length)
        self.blends = blends or [blend] * (len(self.segs) - 1)

    def param(self, p):
        best = None
        for i, (b, h, t) in enumerate(self.segs):
            d = t - h; L2 = d.length_squared
            u = max(0.0, min(1.0, (p - h).dot(d) / L2)) if L2 > 0 else 0.0
            q = h + d * u
            dist = (p - q).length
            if best is None or dist < best[0] - 1e-9:
                best = (dist, self.cum[i] + u * (self.cum[i + 1] - self.cum[i]), i, u)
        # extend beyond ends
        return best[1]

    def __call__(self, p):
        s = self.param(V(p))
        n = len(self.segs); w = {}
        for i in range(n):
            lo = 1.0 if i == 0 else smoothstep(self.cum[i] - self.blends[i - 1], self.cum[i] + self.blends[i - 1], s)
            hi = 0.0 if i == n - 1 else smoothstep(self.cum[i + 1] - self.blends[i], self.cum[i + 1] + self.blends[i], s)
            if lo - hi > 1e-4:
                w[self.segs[i][0]] = w.get(self.segs[i][0], 0.0) + lo - hi
        return w

def fixed(bone):
    return lambda p: {bone: 1.0}

def mix_w(a, b, t):
    """blend two weight dicts"""
    out = {}
    for k, v in a.items():
        out[k] = out.get(k, 0) + v * (1 - t)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v * t
    return {k: v for k, v in out.items() if v > 1e-4}

class Part:
    def __init__(self, slot, mat, team=0.0, smooth=True):
        self.slot, self.mat, self.team, self.smooth = slot, mat, team, smooth

class CharMesh:
    def __init__(self, name):
        self.name = name
        self.co = []      # Vector
        self.w = []       # dict bone -> weight
        self.faces = []   # (idx tuple, slot, mat, team, smooth)

    def vert(self, p, wfn):
        self.co.append(V(p))
        w = wfn(self.co[-1]) if callable(wfn) else wfn
        tot = sum(w.values())
        self.w.append({k: v / tot for k, v in w.items()})
        return len(self.co) - 1

    def face(self, idx, part):
        slot = part.slot
        if callable(slot):
            c = sum((self.co[i] for i in idx), Vector()) / len(idx)
            slot = slot(c)
        if slot is None:
            return
        mat = part.mat
        if isinstance(slot, tuple):
            slot, mat = slot
        self.faces.append((tuple(idx), slot, mat, part.team, part.smooth))

    # ---------- primitives ----------
    def loft(self, rings, part, wfn, cap0=False, cap1=False, closed=True):
        """rings: list of lists of points (same count). Connect consecutive rings with quads."""
        ids = [[self.vert(p, wfn) for p in r] for r in rings]
        n = len(rings[0])
        m = n if closed else n - 1
        for a, b in zip(ids, ids[1:]):
            for j in range(m):
                k = (j + 1) % n
                self.face((a[j], a[k], b[k], b[j]), part)
        if cap0:
            self._cap(ids[0], part, wfn, rings[0], flip=True)
        if cap1:
            self._cap(ids[-1], part, wfn, rings[-1], flip=False)
        return ids

    def _cap(self, ring_ids, part, wfn, pts, flip):
        c = sum((V(p) for p in pts), Vector()) / len(pts)
        ci = self.vert(c, wfn)
        n = len(ring_ids)
        for j in range(n):
            k = (j + 1) % n
            self.face((ring_ids[k], ring_ids[j], ci) if flip else (ring_ids[j], ring_ids[k], ci), part)

    def box(self, size, mtx, part, wfn, taper=(1, 1)):
        """hard box: size (x,y,z), mtx = Matrix 4x4 placing the unit box; taper scales the +z face (x,y)."""
        sx, sy, sz = [s / 2 for s in size]
        P = []
        for z in (-sz, sz):
            tx, ty = (taper if z > 0 else (1, 1))
            for x, y in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                P.append(mtx @ V(x * tx, y * ty, z))
        quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        for q in quads:  # unshared verts -> flat normals
            ids = [self.vert(P[i], wfn) for i in q]
            self.face(ids, part)

    def tube(self, path, radii, segs, part, wfn, cap0=True, cap1=True, up=V(0, 0, 1), scale_x=None, phase=0.0):
        """sweep circles (rx = radii, optional ry multiplier scale_x) along a polyline path."""
        path = [V(p) for p in path]
        rings = []
        for i, p in enumerate(path):
            d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
            u = up - d * up.dot(d)
            if u.length < 1e-4:
                u = V(1, 0, 0) - d * d.x
            u.normalize(); v = d.cross(u)
            r = radii[i] if isinstance(radii, (list, tuple)) else radii
            rx = r * (scale_x[i] if isinstance(scale_x, (list, tuple)) else (scale_x or 1.0))
            ring = []
            for j in range(segs):
                a = 2 * math.pi * (j + phase) / segs
                ring.append(p + u * (math.cos(a) * r) + v * (math.sin(a) * rx))
            rings.append(ring)
        return self.loft(rings, part, wfn, cap0, cap1)

    def ribbon(self, pts, normals, width, part, wfn, thick=0.004):
        """flat strap along pts (surface normals given), slightly lifted; thin box cross-section."""
        rings = []
        for i, p in enumerate(pts):
            p = V(p); n = V(normals[i]).normalized()
            d = (V(pts[min(i + 1, len(pts) - 1)]) - V(pts[max(i - 1, 0)])).normalized()
            s = d.cross(n).normalized() * (width / 2)
            b = p + n * 0.002; t = p + n * (0.002 + abs(thick))
            if thick == 0:
                rings.append([b + n * 0.003 - s, b + n * 0.003 + s])   # thick=0: single flat strip (LOD1 lean)
            else:
                rings.append([b - s, b + s, t + s, t - s] if thick > 0 else [b - s, b + s, t])   # thick<0: cheap triangular strap
        if thick == 0:
            return self.loft(rings, part, wfn, closed=False)
        return self.loft(rings, part, wfn, True, True)

    def ellipsoid(self, c, r, segs, rings, part, wfn, mtx=None, shape=None):
        """uv ellipsoid; shape(theta, phi, p) -> p can deform each point."""
        c = V(c); out = []
        for i in range(1, rings):
            ph = math.pi * i / rings
            ring = []
            for j in range(segs):
                th = 2 * math.pi * j / segs
                p = V(math.sin(ph) * math.cos(th) * r[0], math.sin(ph) * math.sin(th) * r[1], math.cos(ph) * r[2])
                if shape:
                    p = shape(th, ph, p)
                p = (mtx.to_3x3() @ p) if mtx else p
                ring.append(c + p)
            out.append(ring)
        # rings go top -> bottom; loft them and cap both poles
        top = c + ((mtx.to_3x3() @ (shape(0, 0, V(0, 0, r[2])) if shape else V(0, 0, r[2]))) if mtx else (shape(0, 0, V(0, 0, r[2])) if shape else V(0, 0, r[2])))
        bot = c + ((mtx.to_3x3() @ V(0, 0, -r[2])) if mtx else V(0, 0, -r[2]))
        ids = [[self.vert(p, wfn) for p in rr] for rr in out]
        n = segs
        for a, b in zip(ids, ids[1:]):
            for j in range(n):
                k = (j + 1) % n
                self.face((a[j], b[j], b[k], a[k]), part)
        ti = self.vert(top, wfn); bi = self.vert(bot, wfn)
        for j in range(n):
            k = (j + 1) % n
            self.face((ti, ids[0][j], ids[0][k]), part)
            self.face((bi, ids[-1][k], ids[-1][j]), part)
        return ids

    def tris(self):
        return sum(len(f[0]) - 2 for f in self.faces)
