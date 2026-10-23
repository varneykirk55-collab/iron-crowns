"""Shared shell-building helpers for the eras v3 kits (geometry code only; every kit passes its own garment cut).

hem_band: a real, slightly proud garment edge (gaiter top, boot top, hose cuff ...) swept round a limb of the body
surface. A slot boundary painted on the body shell shows as a stair-stepped edge (hi faces + id-map texels); the band's
edge is geometry, so it stays a smooth line at any zoom. Kits move their body-shell slot boundary under the band."""
import math
from mathutils import Vector as V
import char_v2 as C

def _center(tree, c0):
    """limb centre at the height of c0: midpoint of the surface hits along +-x and +-y from c0 (inside the limb)."""
    c = V(c0)
    for ax in (V((1, 0, 0)), V((0, 1, 0))):
        a = tree.ray_cast(c, ax); b = tree.ray_cast(c, -ax)
        if a[0] is not None and b[0] is not None:
            m = (a[0] + b[0]) / 2
            c = c + ax * (m - c).dot(ax)
    return c

def hem_band(tree, c0, top_fn, hi=False, depth=0.032, off=0.0032, name='hem', slot='gaiter'):
    """band whose upper edge follows z = top_fn(x, y) round the limb whose inside contains c0 (x, y, z~top).
    Profile (hi): tucked inner lip, rounded top edge, flat outer face down to top - depth. lo: 3-point profile."""
    n = 96 if hi else 14
    prof = ([(0.0, -0.0015), (0.0, off * 0.55), (-0.0015, off * 0.92), (-0.004, off), (-depth, off), (-depth - 0.004, -0.0015)]
            if hi else [(0.0, -0.001), (-0.002, off), (-depth, off * 0.8)])
    cz = {}
    def center(z):
        k = round(z, 3)
        if k not in cz: cz[k] = _center(tree, V((c0[0], c0[1], z)))
        return cz[k]
    secs = []
    for j in range(n):
        a = 2 * math.pi * j / n
        d = V((math.cos(a), math.sin(a), 0.0))
        z = c0[2]; hit = None
        for _ in range(3):   # find the edge height at this azimuth (top_fn depends on the surface point)
            c = center(z); h = tree.ray_cast(c, d)
            if h[0] is None: break
            hit = h; z = top_fn(h[0].x, h[0].y)
        if hit is None: continue
        sec = []
        for dz, o in prof:
            c = center(z + dz); h = tree.ray_cast(c, d)
            if h[0] is None: h = hit
            nn = V((h[1].x, h[1].y, 0.0)).normalized() if h[1].z < 0.9 else d
            sec.append(V((h[0].x, h[0].y, z + dz)) + nn * o)
        secs.append(sec)
    secs.append(secs[0])
    # sections are profiles, swept round the limb: transpose to rings for grid_sweep (open profile, closed sweep)
    rings = [[s[i] for s in secs[:-1]] for i in range(len(prof))]
    o = C.grid_sweep(name, rings, closed_u=True, cap0=False, cap1=False, slot=slot)
    return o

def leg_hems(tree, top_fn, hi=False, z0=0.5, slot='gaiter', **kw):
    """one hem band per leg (names hem.R / hem.L, rule 'transfer'); top_fn(x, y) -> edge height."""
    return [hem_band(tree, (s * 0.10, 0.0, z0), top_fn, hi, name='hem.' + ('R' if s > 0 else 'L'), slot=slot, **kw)
            for s in (1, -1)]
