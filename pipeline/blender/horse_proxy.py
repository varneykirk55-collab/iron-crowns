"""Rob / cavalry overhaul: self-built PROXY meshes for the new HX horse rig (stand-in until Bill's horse mesh).

Layers (spec section 6): body (coat), tack (saddle, cloth, bridle, reins, stirrups), barding (knight caparison +
chanfron), rider (char_rig skeleton, built standing in char_rig rest coords then placed by A0), weapons.
Geometry is plain python (no bpy): Geo holds verts, per-vertex bone weights {bone: w} (horse bone names as-is,
rider bones prefixed 'r:'), faces with a flat colour (rgba, a = team amount) and a material class id."""
import math
from mathutils import Vector, Matrix
import horse_rig as H
from horse_rig import V

def hexc(h, a=0.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

# material class ids (common.py / vat.gdshader)
M_DEF, M_WOOL, M_LEATHER, M_STEEL, M_BRASS, M_SKIN, M_WOOD, M_CLAY, M_HIDE, M_FUR, M_IRON, M_HAIR, M_MAIL, M_CANVAS = range(14)

COAT = hexc('6b4a30'); MANE = hexc('2a1d14'); HOOF = hexc('26211d'); MUZZLE = hexc('3a2a20')
LEATHER = hexc('4a3220'); BLACKL = hexc('1e1a18'); METAL = hexc('a3abb3'); IRON = hexc('3a3d42'); BRASS = hexc('c09a45')
WOOD = hexc('7a5230'); SKIN = hexc('e2b48e'); BOOT = hexc('231d19'); TEAM = (1.0, 1.0, 1.0, 1.0)
LACE = hexc('d9c36a'); FUR = hexc('e4ded2'); CLOTH_D = hexc('2e2a26')
A0 = Matrix.Translation((0, 0.10, 0.538))          # rider armature -> horse rest (hips at rider_seat)

class Geo:
    def __init__(self):
        self.v = []; self.w = []; self.f = []; self.fc = []; self.fm = []; self.layer = []; self.fl = []
        self.cur = 'body'

    def vert(self, p, w):
        self.v.append(V(p)); self.w.append(dict(w)); self.layer.append(self.cur)
        return len(self.v) - 1

    def face(self, idx, col, mat, outward=None):
        if outward is not None:
            a, b, c = self.v[idx[0]], self.v[idx[1]], self.v[idx[2]]
            n = (b - a).cross(c - a)
            ctr = sum((self.v[i] for i in idx), Vector()) / len(idx)
            if n.dot(ctr - V(outward)) < 0:
                idx = list(reversed(idx))
        self.f.append(tuple(idx)); self.fc.append(col); self.fm.append(mat); self.fl.append(self.cur)

    def ring(self, c, xa, ya, rx, ry, n, w, rot0=0.0, shape=None):
        c = V(c); xa = V(xa).normalized(); ya = V(ya).normalized()
        out = []
        for i in range(n):
            a = rot0 + 2 * math.pi * i / n
            ca, sa = math.cos(a), math.sin(a)
            if shape:
                ca, sa = shape(ca, sa)
            out.append(self.vert(c + xa * (rx * ca) + ya * (ry * sa), w))
        return out

    def bridge(self, r1, r2, c1, c2, col, mat):
        n = len(r1); mid = (V(c1) + V(c2)) * 0.5
        for i in range(n):
            j = (i + 1) % n
            # outward test against the local axis point
            q = [r1[i], r1[j], r2[j], r2[i]]
            a = self.v[q[0]]; b = self.v[q[1]]; c = self.v[q[2]]
            ctr = (self.v[q[0]] + self.v[q[1]] + self.v[q[2]] + self.v[q[3]]) * 0.25
            ax = (V(c2) - V(c1)); ax = ax.normalized() if ax.length > 1e-9 else V(0, 0, 1)
            rel = ctr - V(c1); rel = rel - ax * rel.dot(ax)
            n_ = (b - a).cross(c - a)
            if n_.length < 1e-12:
                n_ = (c - a).cross(self.v[q[3]] - a)
            if n_.dot(rel) < 0:
                q = list(reversed(q))
            self.f.append(tuple(q)); self.fc.append(col); self.fm.append(mat); self.fl.append(self.cur)

    def cap(self, r, c, away, col, mat, w=None, tip=None):
        """fan cap: if tip given, cone to that point; else flat n-gon fan via a centre vertex"""
        cc = self.vert(tip if tip is not None else c, w if w is not None else self.w[r[0]])
        n = len(r)
        for i in range(n):
            j = (i + 1) % n
            self.face([r[i], r[j], cc], col, mat, outward=V(c) - (V(away) - V(c)).normalized() * 0.5 if tip is None else V(c) - (V(tip) - V(c)) * 2)

    def tube(self, pts, radii, ws, n, col, mat, caps=(True, True), up=(0, 0, 1), ry_scale=None, cols=None, mats=None):
        pts = [V(p) for p in pts]
        rings = []
        up = V(up)
        for k, p in enumerate(pts):
            if k == 0:
                t = pts[1] - pts[0]
            elif k == len(pts) - 1:
                t = pts[-1] - pts[-2]
            else:
                t = (pts[k + 1] - pts[k]).normalized() + (pts[k] - pts[k - 1]).normalized()
            t.normalize()
            xa = up.cross(t)
            if xa.length < 1e-4:
                xa = V(1, 0, 0).cross(t)
            xa.normalize(); ya = t.cross(xa)
            rx = radii[k] if not isinstance(radii[k], tuple) else radii[k][0]
            rr = radii[k] if not isinstance(radii[k], tuple) else radii[k][1]
            rings.append(self.ring(p, xa, ya, rx, rr, n, ws[k]))
        for k in range(len(pts) - 1):
            self.bridge(rings[k], rings[k + 1], pts[k], pts[k + 1], cols[k] if cols else col, mats[k] if mats else mat)
        if caps[0]:
            self.cap(rings[0], pts[0], pts[1], cols[0] if cols else col, mats[0] if mats else mat)
        if caps[1]:
            self.cap(rings[-1], pts[-1], pts[-2], cols[-1] if cols else col, mats[-1] if mats else mat)
        return rings

    def box(self, M, size, w, col, mat):
        M = Matrix(M); sx, sy, sz = size
        idx = []
        for z in (-1, 1):
            for y in (-1, 1):
                for x in (-1, 1):
                    idx.append(self.vert(M @ V(x * sx / 2, y * sy / 2, z * sz / 2), w))
        ctr = M @ V(0, 0, 0)
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            self.face([idx[i] for i in q], col, mat, outward=ctr)
        return idx

    def ellipsoid(self, c, r, w, col, mat, n=8, rings=5, M=None):
        c = V(c); M = Matrix.Identity(3) if M is None else M
        top = self.vert(c + M @ V(0, 0, r[2]), w); bot = self.vert(c + M @ V(0, 0, -r[2]), w)
        rr = []
        for k in range(1, rings):
            ph = math.pi * k / rings
            z = math.cos(ph); s = math.sin(ph)
            rr.append([self.vert(c + M @ V(r[0] * s * math.cos(2 * math.pi * i / n), r[1] * s * math.sin(2 * math.pi * i / n), r[2] * z), w) for i in range(n)])
        for i in range(n):
            j = (i + 1) % n
            self.face([top, rr[0][i], rr[0][j]], col, mat, outward=c)
            self.face([bot, rr[-1][j], rr[-1][i]], col, mat, outward=c)
        for k in range(len(rr) - 1):
            for i in range(n):
                j = (i + 1) % n
                self.face([rr[k][i], rr[k][j], rr[k + 1][j], rr[k + 1][i]], col, mat, outward=c)

    def transform_from(self, start, M, wmap=None):
        for i in range(start, len(self.v)):
            self.v[i] = M @ self.v[i]
            if wmap:
                self.w[i] = {wmap(k): x for k, x in self.w[i].items()}

    def counts(self):
        tris = sum(len(f) - 2 for f in self.f)
        return len(self.v), tris

# ------------------------------------------------------------------ weight helpers
def blend_w(t, keys):
    """keys: [(t0, bone), (t1, bone), ...] sorted; linear blend between neighbours"""
    if t <= keys[0][0]:
        return {keys[0][1]: 1.0}
    for (ta, a), (tb, b) in zip(keys, keys[1:]):
        if t <= tb:
            u = (t - ta) / (tb - ta)
            if a == b:
                return {a: 1.0}
            return {a: 1 - u, b: u} if 0 < u < 1 else ({a: 1.0} if u <= 0 else {b: 1.0})
    return {keys[-1][1]: 1.0}

BODY_KEYS = [(-0.62, 'pelvis'), (-0.30, 'spine_01'), (-0.05, 'spine_01'), (0.22, 'spine_02'), (0.40, 'chest')]
def body_w(y):
    return blend_w(y, BODY_KEYS)

# horse barrel stations: (y, zc, half-width, half-height)
BODY_ST = [(-0.99, 1.25, 0.05, 0.07), (-0.95, 1.23, 0.14, 0.20), (-0.86, 1.21, 0.21, 0.28), (-0.68, 1.18, 0.25, 0.32),
           (-0.42, 1.15, 0.265, 0.315), (-0.15, 1.12, 0.28, 0.305), (0.10, 1.11, 0.285, 0.31), (0.33, 1.13, 0.27, 0.36),
           (0.50, 1.12, 0.24, 0.37), (0.64, 1.07, 0.195, 0.31), (0.75, 1.03, 0.13, 0.22), (0.80, 1.02, 0.05, 0.10)]

def _sq(p):  # flatter-top, slightly squarer barrel section
    def f(c, s):
        return (math.copysign(abs(c) ** p, c), math.copysign(abs(s) ** p, s))
    return f

def build_horse_body(g, lod):
    g.cur = 'body'
    n = 14 if lod == 0 else 8
    st = BODY_ST if lod == 0 else BODY_ST[::2] + [BODY_ST[-1]]
    st = sorted(set(st))
    rings = []
    for y, zc, w, h in st:
        rings.append((g.ring((0, y, zc), (1, 0, 0), (0, 0, 1), w, h, n, body_w(y), rot0=-math.pi / 2, shape=_sq(0.85)), V(0, y, zc)))
    for (r1, c1), (r2, c2) in zip(rings, rings[1:]):
        g.bridge(r1, r2, c1, c2, COAT, M_HIDE)
    g.cap(rings[0][0], rings[0][1], rings[1][1], COAT, M_HIDE)
    g.cap(rings[-1][0], rings[-1][1], rings[-2][1], COAT, M_HIDE)
    # neck: centre line with sections perpendicular to it; crest on top (+ mane strip)
    nk = [((0, 0.56, 1.30), 0.17, 0.27, {'chest': 1.0}),
          ((0, 0.72, 1.44), 0.14, 0.21, {'chest': 0.3, 'neck_01': 0.7}),
          ((0, 0.84, 1.58), 0.115, 0.17, {'neck_01': 0.5, 'neck_02': 0.5}),
          ((0, 0.93, 1.71), 0.095, 0.14, {'neck_02': 0.5, 'neck_03': 0.5}),
          ((0, 1.00, 1.82), 0.08, 0.115, {'neck_03': 0.5, 'head': 0.5})]
    if lod > 0:
        nk = [nk[0], nk[2], nk[4]]
    nn = 10 if lod == 0 else 6
    nrings = []
    for k, (c, w, h, wt) in enumerate(nk):
        c = V(c)
        a = V(nk[min(k + 1, len(nk) - 1)][0]) - V(nk[max(k - 1, 0)][0]); a.normalize()
        ya = a.cross(V(1, 0, 0)) * -1.0       # up-ish, perpendicular to the neck
        nrings.append((g.ring(c, (1, 0, 0), ya, w, h, nn, wt, rot0=-math.pi / 2), c))
    for (r1, c1), (r2, c2) in zip(nrings, nrings[1:]):
        g.bridge(r1, r2, c1, c2, COAT, M_HIDE)
    # head: poll -> muzzle along the head bone
    hd = [((0, 1.03, 1.87), 0.065, 0.07), ((0, 1.10, 1.79), 0.095, 0.115), ((0, 1.22, 1.63), 0.08, 0.085),
          ((0, 1.33, 1.50), 0.065, 0.07), ((0, 1.395, 1.425), 0.05, 0.05)]
    if lod > 0:
        hd = [hd[0], hd[1], hd[3], hd[4]]
    hn = 10 if lod == 0 else 6
    hrings = []
    hdir = (V(1.40, 1.44, 0) * 0)  # unused
    axis = (V((0, 1.40, 1.44)) - V((0, 1.05, 1.86))).normalized()
    ya = axis.cross(V(1, 0, 0)) * -1.0
    for k, (c, w, h) in enumerate(hd):
        col = COAT if k < len(hd) - 2 else MUZZLE
        hrings.append((g.ring(c, (1, 0, 0), ya, w, h, hn, {'head': 1.0}, rot0=-math.pi / 2), V(c), col))
    for (r1, c1, _), (r2, c2, col) in zip(hrings, hrings[1:]):
        g.bridge(r1, r2, c1, c2, COAT if col is COAT else MUZZLE, M_HIDE if col is COAT else M_DEF)
    g.cap(hrings[0][0], hrings[0][1], hrings[1][1], COAT, M_HIDE)
    g.cap(hrings[-1][0], hrings[-1][1], hrings[-2][1], MUZZLE, M_DEF)
    # ears
    for s, sx in (('L', -1), ('R', 1)):
        b = 'ear.' + s
        h0 = H.HEAD[b]; t0 = H.TAIL[b]
        g.tube([h0, t0], [0.025, 0.004], [{b: 1.0}, {b: 1.0}], 4 if lod else 5, COAT, M_HIDE, caps=(True, False), up=(0, 1, 0))
    # mane: thin crest blade along the neck top
    mp = [((0, 0.50, 1.52), {'chest': 1.0}), ((0, 0.70, 1.62), {'neck_01': 1.0}), ((0, 0.83, 1.74), {'neck_01': 0.5, 'neck_02': 0.5}),
          ((0, 0.93, 1.85), {'neck_02': 0.5, 'neck_03': 0.5}), ((0, 1.00, 1.93), {'neck_03': 0.5, 'head': 0.5})]
    if lod > 0:
        mp = [mp[0], mp[2], mp[4]]
    prev = None
    for p, w in mp:
        p = V(p)
        a = g.vert(p + V(-0.025, 0, 0.0), w); b = g.vert(p + V(0.025, 0, 0.0), w)
        c = g.vert(p + V(0, -0.03, -0.11), w)
        if prev:
            pa, pb, pc = prev
            ctr = p + V(0, 0, -0.2)
            g.face([pa, a, c, pc], MANE, M_HAIR, outward=ctr + V(0.5, 0, 0))
            g.face([pb, pc, c, b], MANE, M_HAIR, outward=ctr + V(-0.5, 0, 0))
            g.face([pa, pb, b, a], MANE, M_HAIR, outward=ctr)
        prev = (a, b, c)
    # tail: hair tube along the 5-bone chain
    tpts = [H.HEAD['tail_01']] + [H.TAIL['tail_%02d' % i] for i in range(1, 6)]
    tr = [0.05, 0.055, 0.075, 0.085, 0.08, 0.035]
    tw = [{'pelvis': 0.4, 'tail_01': 0.6}, {'tail_01': 0.5, 'tail_02': 0.5}, {'tail_02': 0.5, 'tail_03': 0.5},
          {'tail_03': 0.5, 'tail_04': 0.5}, {'tail_04': 0.5, 'tail_05': 0.5}, {'tail_05': 1.0}]
    g.tube(tpts, tr, tw, 6 if lod == 0 else 4, MANE, M_HAIR, caps=(False, True), up=(1, 0, 0))
    build_legs(g, lod)

def _mix(a, b, t=0.5):
    return {a: 1 - t, b: t}

def build_legs(g, lod):
    n = 8 if lod == 0 else 5
    for s, sx in (('R', 1), ('L', -1)):
        x = lambda v: v * sx
        sc, hu, ra, cf, ff, hf = ['%s.%s' % (b, s) for b in ('scapula', 'humerus', 'radius', 'cannon_f', 'fetlock_f', 'hoof_f')]
        fore = [((x(0.12), 0.46, 1.24), (0.09, 0.12), {sc: 0.6, 'chest': 0.4}),
                ((x(0.165), 0.66, 1.06), (0.085, 0.11), _mix(sc, hu)),
                ((x(0.165), 0.55, 0.88), (0.075, 0.085), _mix(hu, ra, 0.6)),
                ((x(0.158), 0.535, 0.70), 0.055, {ra: 1.0}),
                ((x(0.155), 0.54, 0.54), 0.042, {ra: 1.0}),
                ((x(0.155), 0.54, 0.50), 0.042, _mix(ra, cf)),
                ((x(0.152), 0.54, 0.45), 0.032, {cf: 1.0}),
                ((x(0.15), 0.54, 0.27), 0.032, {cf: 1.0}),
                ((x(0.15), 0.54, 0.23), 0.040, _mix(cf, ff)),
                ((x(0.15), 0.57, 0.16), 0.032, {ff: 1.0}),
                ((x(0.15), 0.60, 0.10), 0.036, _mix(ff, hf, 0.7))]
        hb, ti, ch, fh, hh = ['%s.%s' % (b, s) for b in ('femur', 'tibia', 'cannon_h', 'fetlock_h', 'hoof_h')]
        hind = [((x(0.13), -0.58, 1.26), (0.10, 0.14), {'pelvis': 0.7, hb: 0.3}),
                ((x(0.17), -0.50, 1.08), (0.115, 0.17), {'pelvis': 0.3, hb: 0.7}),
                ((x(0.185), -0.40, 0.92), (0.10, 0.13), _mix(hb, ti, 0.4)),
                ((x(0.18), -0.47, 0.74), (0.065, 0.09), {ti: 1.0}),
                ((x(0.165), -0.60, 0.58), (0.04, 0.06), {ti: 1.0}),
                ((x(0.16), -0.64, 0.54), (0.038, 0.055), _mix(ti, ch)),
                ((x(0.158), -0.635, 0.49), 0.032, {ch: 1.0}),
                ((x(0.15), -0.62, 0.27), 0.032, {ch: 1.0}),
                ((x(0.15), -0.62, 0.23), 0.040, _mix(ch, fh)),
                ((x(0.15), -0.595, 0.16), 0.032, {fh: 1.0}),
                ((x(0.15), -0.57, 0.10), 0.036, _mix(fh, hh, 0.7))]
        for chain, hoofb, toe_y in ((fore, hf, 0.635), (hind, hh, -0.525)):
            if lod > 0:
                chain = [chain[i] for i in (0, 1, 2, 3, 5, 7, 8, 10)]
            pts = [c[0] for c in chain]; rad = [c[1] for c in chain]; ws = [c[2] for c in chain]
            rings = g.tube(pts, rad, ws, n, COAT, M_HIDE, caps=(True, False), up=(1, 0, 0))
            # hoof: frustum from the coronet ring down to the sole
            top = rings[-1]
            c0 = V(pts[-1])
            sole_c = V((x(0.15), toe_y, 0.0))
            bot = g.ring(sole_c, (1, 0, 0), (0, 1, 0), 0.06, 0.068, n, {hoofb: 1.0})
            # re-weight the coronet ring slightly towards the hoof bone
            g.bridge(top, bot, c0, sole_c, HOOF, M_DEF)
            g.cap(bot, sole_c, c0, HOOF, M_DEF)

# ------------------------------------------------------------------ tack
def build_tack(g, lod, variant):
    g.cur = 'tack'
    n = 8 if lod == 0 else 5
    kn = variant == 'med_knight'; hu = variant == 'c19_hussar'
    # saddle cloth / shabraque (team colour), draped over the back, weighted like the barrel under it
    cloth = TEAM if not kn else CLOTH_D
    cl_y = (-0.30, 0.42) if hu else (-0.16, 0.36)
    drop = 0.36 if hu else 0.24
    ys = [cl_y[0] + (cl_y[1] - cl_y[0]) * i / (3 if lod == 0 else 2) for i in range(4 if lod == 0 else 3)]
    rows = []
    nk = 7 if lod == 0 else 5
    for y in ys:
        zc, w, hh = _station(y)
        row = []
        for k in range(nk):
            u = k / (nk - 1)                    # 0 = right flap bottom, 1 = left flap bottom
            if k == 0 or k == nk - 1:
                sd = 1 if k == 0 else -1
                p = V(sd * (w + 0.03), y, zc + hh * 0.35 - drop)
            else:
                ang = math.pi * (k - 1) / (nk - 3)
                cq, sq = _sq(0.85)(math.cos(ang), math.sin(ang))
                p = V(cq * (w + 0.025), y, zc + sq * (hh + 0.022))
                if k in (1, nk - 2):
                    p = V(math.copysign(w + 0.03, math.cos(ang)), y, zc + hh * 0.35)
            row.append(g.vert(p, body_w(y)))
        rows.append((row, V(0, y, zc)))
    for (r1, c1), (r2, c2) in zip(rows, rows[1:]):
        for i in range(len(r1) - 1):
            g.face([r1[i], r1[i + 1], r2[i + 1], r2[i]], cloth, M_WOOL, outward=(c1 + c2) * 0.5)
    if hu:   # sheepskin over the seat
        g.box(Matrix.Translation((0, 0.10, 1.465)), (0.34, 0.46, 0.03), {'saddle': 1.0}, FUR, M_FUR)
    # saddle seat, pommel, cantle
    sw = {'saddle': 1.0}
    g.box(Matrix.Translation((0, 0.10, 1.445)), (0.28, 0.44, 0.05), sw, LEATHER, M_LEATHER)
    pom_h = 0.16 if kn else 0.08; can_h = 0.20 if kn else 0.09
    g.box(Matrix.Translation((0, 0.33, 1.47 + pom_h / 2)) @ Matrix.Rotation(math.radians(-15), 4, 'X'), (0.20 if kn else 0.14, 0.05, pom_h), sw, WOOD if kn else LEATHER, M_WOOD if kn else M_LEATHER)
    g.box(Matrix.Translation((0, -0.13, 1.47 + can_h / 2)) @ Matrix.Rotation(math.radians(12), 4, 'X'), (0.30 if kn else 0.22, 0.05, can_h), sw, WOOD if kn else LEATHER, M_WOOD if kn else M_LEATHER)
    # saddle flaps
    for sx in (-1, 1):
        g.box(Matrix.Translation((sx * 0.25, 0.14, 1.30)) @ Matrix.Rotation(math.radians(sx * -14), 4, 'Y'), (0.02, 0.30, 0.26), {'saddle': 0.6, 'spine_02': 0.4}, LEATHER, M_LEATHER)
    # girth
    zc, w, hh = _station(0.28)
    gr = g.ring((0, 0.28, zc), (1, 0, 0), (0, 0, 1), w + 0.012, hh + 0.012, 12 if lod == 0 else 8, body_w(0.28), rot0=-math.pi / 2, shape=_sq(0.85))
    gr2 = g.ring((0, 0.34, zc), (1, 0, 0), (0, 0, 1), w + 0.012, hh + 0.012, 12 if lod == 0 else 8, body_w(0.34), rot0=-math.pi / 2, shape=_sq(0.85))
    g.bridge(gr, gr2, V(0, 0.28, zc), V(0, 0.34, zc), LEATHER, M_LEATHER)
    # breastplate strap (hussar / cuirassier)
    if not kn:
        g.tube([(0.20, 0.42, 1.25), (0.13, 0.70, 1.08), (-0.13, 0.70, 1.08), (-0.20, 0.42, 1.25)], [0.012] * 4,
               [{'spine_02': 1.0}, {'chest': 1.0}, {'chest': 1.0}, {'spine_02': 1.0}], 4, LEATHER, M_LEATHER, caps=(False, False), up=(0, 0, 1))
    # stirrups: leather + iron tread, rigid on the stirrup socket (era length is applied by the pose)
    for s, sx in (('L', -1), ('R', 1)):
        b = 'stirrup.' + s
        h0 = H.HEAD[b]; t0 = H.TAIL[b]
        d = (t0 - h0)
        g.box(Matrix.Translation(h0 + d * 0.45) @ _look(d), (0.035, 0.008, d.length * 0.9), {b: 1.0}, LEATHER, M_LEATHER)
        tr = t0
        g.box(Matrix.Translation(tr + V(0, 0, 0.0)) @ _look(d), (0.11, 0.07, 0.015), {b: 1.0}, METAL if not kn else IRON, M_STEEL if not kn else M_IRON)
        for sy in (-1, 1):
            g.box(Matrix.Translation(tr + V(0, sy * 0.035, 0.05)) @ _look(d), (0.10, 0.01, 0.10), {b: 1.0}, METAL if not kn else IRON, M_STEEL if not kn else M_IRON)
    # bridle: headstall + noseband + browband (head bone), bit (rein_bit)
    axis = (V((0, 1.40, 1.44)) - V((0, 1.05, 1.86))).normalized(); ya = axis.cross(V(1, 0, 0)) * -1.0
    for c, w_, h_ in (((0, 1.06, 1.84), 0.075, 0.085), ((0, 1.315, 1.515), 0.07, 0.075)):
        r1 = g.ring(V(c) - axis * 0.012, (1, 0, 0), ya, w_ + 0.01, h_ + 0.01, 8 if lod == 0 else 6, {'head': 1.0}, rot0=-math.pi / 2)
        r2 = g.ring(V(c) + axis * 0.012, (1, 0, 0), ya, w_ + 0.01, h_ + 0.01, 8 if lod == 0 else 6, {'head': 1.0}, rot0=-math.pi / 2)
        g.bridge(r1, r2, V(c) - axis * 0.012, V(c) + axis * 0.012, BLACKL if hu else LEATHER, M_LEATHER)
    for sx in (-1, 1):
        g.tube([(sx * 0.072, 1.07, 1.83), (sx * 0.072, 1.30, 1.46)], [0.01, 0.01], [{'head': 1.0}, {'rein_bit': 1.0}], 4, BLACKL if hu else LEATHER, M_LEATHER, caps=(False, False), up=(1, 0, 0))
        g.box(Matrix.Translation((sx * 0.075, 1.30, 1.44)), (0.012, 0.045, 0.045), {'rein_bit': 1.0}, METAL, M_STEEL)
    # reins: 4-bone chain per side, rigid segments
    for s in ('L', 'R'):
        pts = [H.HEAD['rein_01.' + s]] + [H.TAIL['rein_%02d.%s' % (i, s)] for i in range(1, 5)]
        ws = [{'rein_bit': 1.0}] + [{'rein_%02d.%s' % (i, s): 0.5, 'rein_%02d.%s' % (i + 1, s): 0.5} for i in range(1, 4)] + [{'rein_hand.' + s: 1.0}]
        g.tube(pts, [0.008] * 5, ws, 4 if lod == 0 else 3, BLACKL if hu else LEATHER, M_LEATHER, caps=(False, False), up=(0, 0, 1))
    if hu:   # sabretache-free hussar: valise/roll behind the cantle
        g.tube([(-0.17, -0.22, 1.52), (0.17, -0.22, 1.52)], [0.055, 0.055], [{'saddle': 1.0}, {'saddle': 1.0}], 6 if lod == 0 else 4, TEAM, M_WOOL, up=(0, 0, 1))

def _station(y):
    st = BODY_ST
    for (ya, za, wa, ha), (yb, zb, wb, hb) in zip(st, st[1:]):
        if ya <= y <= yb:
            u = (y - ya) / (yb - ya)
            return za + (zb - za) * u, wa + (wb - wa) * u, ha + (hb - ha) * u
    return st[-1][1:]

def _look(d):
    """4x4 rotation taking local +Z to direction d"""
    q = V(0, 0, 1).rotation_difference(V(d).normalized())
    return q.to_matrix().to_4x4()

# ------------------------------------------------------------------ barding (knight)
def build_barding(g, lod):
    g.cur = 'barding'
    n = 10 if lod == 0 else 6
    ys = [-0.97, -0.80, -0.55, -0.25, 0.05, 0.36, 0.60, 0.74] if lod == 0 else [-0.97, -0.55, 0.05, 0.60, 0.74]
    rows = []
    for y in ys:
        zc, w, hh = _station(y)
        row = []
        for k in range(n + 1):
            u = k / n
            ang = math.pi * u
            cx, sz = _sq(0.85)(math.cos(ang), math.sin(ang))
            if 0.15 < u < 0.85:
                p = V(cx * (w + 0.035), y, zc + sz * (hh + 0.03))
            else:
                sd = 1 if u <= 0.15 else -1
                fl = 1.0 - min(1.0, abs(u - (0 if sd > 0 else 1)) / 0.15)
                p = V(sd * (w + 0.05), y, zc + (hh + 0.03) * 0.45 - 0.58 * fl)
            row.append(g.vert(p, body_w(y)))
        rows.append((row, V(0, y, zc)))
    for (r1, c1), (r2, c2) in zip(rows, rows[1:]):
        for i in range(len(r1) - 1):
            col = TEAM
            g.face([r1[i], r1[i + 1], r2[i + 1], r2[i]], col, M_WOOL, outward=(c1 + c2) * 0.5)
    # crinet cloth over the neck, chanfron (steel face plate)
    nk = [((0, 0.62, 1.36), 0.19, 0.29, {'chest': 1.0}), ((0, 0.84, 1.58), 0.13, 0.19, {'neck_01': 0.5, 'neck_02': 0.5}),
          ((0, 1.00, 1.82), 0.095, 0.13, {'neck_03': 0.5, 'head': 0.5})]
    rr = []
    for k, (c, w, h, wt) in enumerate(nk):
        a = V(nk[min(k + 1, 2)][0]) - V(nk[max(k - 1, 0)][0]); a.normalize()
        ya = a.cross(V(1, 0, 0)) * -1.0
        row = []
        for i in range(n + 1):
            ang = math.pi * i / n
            row.append(g.vert(V(c) + V(1, 0, 0) * (w * math.cos(ang)) + ya * (h * math.sin(ang) - 0.02), wt))
        rr.append((row, V(c)))
    for (r1, c1), (r2, c2) in zip(rr, rr[1:]):
        for i in range(len(r1) - 1):
            g.face([r1[i], r1[i + 1], r2[i + 1], r2[i]], TEAM, M_WOOL, outward=(c1 + c2) * 0.5)
    axis = (V((0, 1.40, 1.44)) - V((0, 1.05, 1.86))).normalized(); ya = axis.cross(V(1, 0, 0)) * -1.0
    M = Matrix((V(1, 0, 0), axis, ya)).transposed()
    c = V((0, 1.20, 1.66)) + ya * 0.085
    g.box(Matrix.Translation(c) @ M.to_4x4(), (0.12, 0.36, 0.02), {'head': 1.0}, METAL, M_STEEL)

# ------------------------------------------------------------------ rider (char_rig skeleton, rider coords)
def build_rider(g, lod, variant):
    g.cur = 'rider'
    start = len(g.v)
    import char_rig as CR
    n = 8 if lod == 0 else 5
    kn = variant == 'med_knight'; hu = variant == 'c19_hussar'; cu = variant == 'em_cuirassier'
    coat = METAL if kn else TEAM
    coat_m = M_MAIL if kn else M_WOOL
    # torso loft (z, half-width, half-depth)
    tz = [(0.86, 0.15, 0.11, {'hips': 1.0}), (0.96, 0.165, 0.12, {'hips': 1.0}), (1.07, 0.15, 0.11, {'hips': 0.4, 'spine': 0.6}),
          (1.20, 0.155, 0.11, {'spine': 0.7, 'chest': 0.3}), (1.31, 0.18, 0.12, {'chest': 1.0}), (1.42, 0.19, 0.115, {'chest': 1.0}),
          (1.47, 0.09, 0.07, {'chest': 0.6, 'neck': 0.4})]
    if lod > 0:
        tz = [tz[0], tz[2], tz[4], tz[5], tz[6]]
    rings = []
    for z, w, d, wt in tz:
        rings.append((g.ring((0, 0.005, z), (1, 0, 0), (0, 1, 0), w, d, n, wt), V(0, 0.005, z)))
    for k, ((r1, c1), (r2, c2)) in enumerate(zip(rings, rings[1:])):
        g.bridge(r1, r2, c1, c2, coat, coat_m)
    g.cap(rings[0][0], rings[0][1], rings[1][1], coat, coat_m)
    if kn:   # surcoat (team) over the mail torso
        sz = [(0.90, 0.175, 0.13, {'hips': 1.0}), (1.07, 0.165, 0.125, {'hips': 0.4, 'spine': 0.6}), (1.30, 0.19, 0.13, {'chest': 1.0}), (1.40, 0.195, 0.125, {'chest': 1.0})]
        rr = [(g.ring((0, 0.005, z), (1, 0, 0), (0, 1, 0), w, d, n, wt), V(0, 0.005, z)) for z, w, d, wt in sz]
        for (r1, c1), (r2, c2) in zip(rr, rr[1:]):
            g.bridge(r1, r2, c1, c2, TEAM, M_WOOL)
    if cu:   # cuirass
        cz = [(1.06, 0.165, 0.125, {'spine': 1.0}), (1.24, 0.175, 0.135, {'spine': 0.4, 'chest': 0.6}), (1.42, 0.195, 0.13, {'chest': 1.0})]
        rr = [(g.ring((0, 0.008, z), (1, 0, 0), (0, 1, 0), w, d, n, wt), V(0, 0.008, z)) for z, w, d, wt in cz]
        for (r1, c1), (r2, c2) in zip(rr, rr[1:]):
            g.bridge(r1, r2, c1, c2, METAL, M_STEEL)
    if hu:   # lace bars across the dolman chest
        for z in (1.25, 1.31, 1.37):
            g.box(Matrix.Translation((0, 0.125, z)), (0.22, 0.012, 0.018), {'chest': 1.0}, LACE, M_BRASS)
    # neck + head
    g.tube([(0, 0.0, 1.45), (0, 0.01, 1.58)], [0.05, 0.048], [{'neck': 1.0}, {'neck': 0.5, 'head': 0.5}], 6 if lod == 0 else 4, SKIN if not kn else METAL, M_SKIN if not kn else M_MAIL, caps=(False, False))
    g.ellipsoid((0, 0.025, 1.665), (0.085, 0.10, 0.11), {'head': 1.0}, SKIN, M_SKIN, n=8 if lod == 0 else 6, rings=5 if lod == 0 else 4)
    if kn:     # great helm
        g.tube([(0, 0.02, 1.57), (0, 0.02, 1.79)], [0.11, 0.105], [{'head': 1.0}, {'head': 1.0}], 8 if lod == 0 else 6, METAL, M_STEEL, caps=(True, True))
        g.box(Matrix.Translation((0, 0.13, 1.70)), (0.16, 0.012, 0.015), {'head': 1.0}, IRON, M_IRON)   # eye slit
    elif hu:   # shako + plume
        g.tube([(0, 0.02, 1.71), (0, 0.025, 1.92)], [0.095, 0.11], [{'head': 1.0}, {'head': 1.0}], 8 if lod == 0 else 6, BLACKL, M_WOOL, caps=(True, True))
        g.tube([(0, 0.04, 1.92), (0, 0.05, 2.06)], [0.03, 0.012], [{'head': 1.0}, {'head': 1.0}], 5, FUR, M_FUR, caps=(False, True))
        g.box(Matrix.Translation((0, 0.12, 1.73)), (0.15, 0.05, 0.012), {'head': 1.0}, BLACKL, M_LEATHER)  # peak
    else:      # cuirassier helmet + crest + neck guard
        g.ellipsoid((0, 0.02, 1.73), (0.11, 0.12, 0.10), {'head': 1.0}, METAL, M_STEEL, n=8 if lod == 0 else 6, rings=4)
        g.box(Matrix.Translation((0, 0.0, 1.84)), (0.03, 0.20, 0.06), {'head': 1.0}, BRASS, M_BRASS)
        g.box(Matrix.Translation((0, -0.10, 1.66)) @ Matrix.Rotation(math.radians(-25), 4, 'X'), (0.18, 0.02, 0.10), {'head': 1.0}, METAL, M_STEEL)
    # arms
    for s, sx in (('R', 1), ('L', -1)):
        ua, fa, hd = 'upper_arm.' + s, 'forearm.' + s, 'hand.' + s
        sh = V(CR.BI[ua][1]); el = V(CR.BI[fa][1]); wr = V(CR.BI[hd][1]); ht = V(CR.BI[hd][2])
        g.tube([sh + V(0, 0, 0.02), el, wr], [0.058, 0.046, 0.036],
               [{'chest': 0.3, ua: 0.7}, {ua: 0.5, fa: 0.5}, {fa: 0.7, hd: 0.3}], n if lod == 0 else 4, coat, coat_m, caps=(True, False), up=(0, 1, 0))
        # gauntlet / glove / cuff
        cuff = METAL if kn else (BLACKL if cu else LACE)
        g.tube([wr + (el - wr) * 0.12, wr], [0.042, 0.042], [{fa: 1.0}, {fa: 0.5, hd: 0.5}], 6 if lod == 0 else 4, cuff, M_STEEL if kn else M_LEATHER, caps=(False, False), up=(0, 1, 0))
        g.box(Matrix.Translation(wr + (ht - wr) * 0.45), (0.05, 0.08, 0.10), {hd: 1.0}, hexc('3a2a1e') if not kn else METAL, M_LEATHER if not kn else M_STEEL)
    # legs
    for s, sx in (('R', 1), ('L', -1)):
        th, sh_, ft = 'thigh.' + s, 'shin.' + s, 'foot.' + s
        hp = V(CR.BI[th][1]); kn_ = V(CR.BI[sh_][1]); an = V(CR.BI[ft][1])
        breech = (hexc('d8d2c0') if cu else TEAM) if not kn else METAL
        g.tube([hp + V(0, 0, 0.03), kn_, an + V(0, 0, 0.06)], [0.088, 0.058, 0.045], [{'hips': 0.3, th: 0.7}, {th: 0.5, sh_: 0.5}, {sh_: 1.0}],
               n if lod == 0 else 4, breech, M_WOOL if not kn else M_MAIL, caps=(True, False), up=(0, 1, 0))
        # boot shaft (hussar: short hessian boot, cuirassier: tall jackboot, knight: steel greave)
        btop = 0.62 if cu else (0.42 if hu else 0.47)
        g.tube([(sx * 0.1, 0.012 - 0.024 * (1 - (btop - 0.088) / 0.417), btop), an + V(0, 0, 0.02)], [0.056, 0.05], [{th: 0.2, sh_: 0.8} if btop > 0.5 else {sh_: 1.0}, {sh_: 1.0}],
               6 if lod == 0 else 4, BOOT if not kn else METAL, M_LEATHER if not kn else M_STEEL, caps=(False, False), up=(0, 1, 0))
        g.box(Matrix.Translation(an + V(0.008 * sx, 0.05, -0.04)) @ Matrix.Rotation(math.radians(-8), 4, 'X'), (0.085, 0.24, 0.075), {ft: 1.0}, BOOT if not kn else METAL, M_LEATHER if not kn else M_STEEL)
    if kn:   # heater shield on the left forearm
        el = V(CR.BI['forearm.L'][1]); wr = V(CR.BI['hand.L'][1])
        c = (el + wr) * 0.5 + V(-0.07, 0, 0)
        g.box(Matrix.Translation(c), (0.025, 0.36, 0.46), {'forearm.L': 1.0}, TEAM, M_WOOD)
    # weapon on the prop bone (rest: prop head (0.29,0.07,0.43), +Y of the bone = world +Z)
    ph = V(CR.BI['prop'][1])
    pw = {'prop': 1.0}
    if kn:   # arming sword
        g.box(Matrix.Translation(ph + V(0, 0, 0.03)), (0.03, 0.03, 0.14), pw, LEATHER, M_LEATHER)
        g.box(Matrix.Translation(ph + V(0, 0, 0.105)), (0.025, 0.20, 0.02), pw, IRON, M_IRON)
        g.box(Matrix.Translation(ph + V(0, 0, 0.50)), (0.008, 0.045, 0.78), pw, METAL, M_STEEL)
    else:    # curved light-cavalry sabre / straight heavy pallasch
        g.box(Matrix.Translation(ph + V(0, 0, 0.03)), (0.028, 0.03, 0.13), pw, BLACKL, M_LEATHER)
        g.box(Matrix.Translation(ph + V(0, 0.02, 0.10)), (0.04, 0.07, 0.02), pw, BRASS, M_BRASS)
        if hu:
            g.box(Matrix.Translation(ph + V(0, -0.02, 0.33)) @ Matrix.Rotation(math.radians(-4), 4, 'X'), (0.008, 0.035, 0.44), pw, METAL, M_STEEL)
            g.box(Matrix.Translation(ph + V(0, -0.055, 0.73)) @ Matrix.Rotation(math.radians(-10), 4, 'X'), (0.008, 0.03, 0.38), pw, METAL, M_STEEL)
        else:
            g.box(Matrix.Translation(ph + V(0, 0, 0.53)), (0.008, 0.038, 0.84), pw, METAL, M_STEEL)
    # place into horse coordinates, prefix the rider bones
    g.transform_from(start, A0, wmap=lambda b: 'r:' + b)

def build_lance(g, lod):
    g.cur = 'weapon'
    h0 = H.HEAD['lance']; t0 = H.TAIL['lance']
    a = (t0 - h0).normalized()
    w = {'lance': 1.0}
    n = 6 if lod == 0 else 4
    g.tube([h0 - a * 0.85, h0 + a * 0.10, h0 + a * 0.25, h0 + a * 2.85, h0 + a * 3.0], [0.022, 0.03, 0.028, 0.02, 0.003],
           [w] * 5, n, WOOD, M_WOOD, caps=(True, False), up=(0, 0, 1))
    g.tube([h0 + a * 0.10, h0 + a * 0.26], [0.09, 0.03], [w, w], n, METAL, M_STEEL, caps=(True, False), up=(0, 0, 1))   # vamplate
    # pennon
    p0 = h0 + a * 2.55; p1 = h0 + a * 2.80
    i0 = g.vert(p0, w); i1 = g.vert(p1, w); i2 = g.vert(p0 + V(0, -0.30, -0.10) + V(0, 0, 0), w); i3 = g.vert(p0 + V(0.0, -0.05, -0.20), w)
    g.f.append((i0, i1, i2)); g.fc.append(TEAM); g.fm.append(M_WOOL); g.fl.append('weapon')
    g.f.append((i0, i2, i1)); g.fc.append(TEAM); g.fm.append(M_WOOL); g.fl.append('weapon')

def build(variant, lod):
    g = Geo()
    build_horse_body(g, lod)
    build_tack(g, lod, variant)
    if variant == 'med_knight':
        build_barding(g, lod)
        build_lance(g, lod)
    build_rider(g, lod, variant)
    return g
