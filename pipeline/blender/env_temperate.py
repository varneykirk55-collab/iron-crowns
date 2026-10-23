"""Temperate battlefield environment set (env/temperate; eastern & midwestern North America, Europe west of ~30 E
below 57 N, New Zealand): white oak with a broad spreading crown, sugar maple, tall straight hardwood (ash / tulip
poplar), eastern white pine, distance LOD for deciduous forest, hazel / dogwood understorey bush, bracken,
meadow grass with seed heads, wildflower patch, buff limestone boulders + layered ledge outcrop.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-temperate/ASSETS.md.
Run: blender -b --python pipeline/blender/env_temperate.py [-- name ...]   (writes game/assets/models/env_*.glb only)
Vertex colour alpha 1 = foliage (wind sway + rounded normals in env_foliage.gdshader), 0 = wood / stone."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import common
from common import hexc, MeshBuilder
from env_nordic import G, lerpc, jit, finish, colour_faces, new_faces, _stone, _blade

def _clump(b, c, r, sq, cols, hi, rnd, seed, k, rough=0.38, sub=1):
    bm = bmesh.ops.create_icosphere(b.bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((sq[0], sq[1], sq[2], 1)))
    for v in bm['verts']:
        v.co += (v.co - c).normalized() * noise.noise(v.co * 0.8 + Vector((seed, k, 3))) * r * rough
    col = cols[k % len(cols)]
    colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(lerpc(col, hi, max(0.0, f.calc_center_median().z - c.z) / r * 0.7), rnd, 0.07, 1.0))

def _leaf(b, base, d, length, width, droop, col, tip, segs=4, side_up=None):
    """Long drooping leaf / frond as a strip of quads (both sides drawn by the foliage material)."""
    d = Vector((d.x, d.y, 0)).normalized() if Vector((d.x, d.y, 0)).length > 1e-4 else Vector((1, 0, 0))
    side = Vector((-d.y, d.x, 0))
    prev = None
    for i in range(segs + 1):
        u = i / segs
        p = base + d * length * u + Vector((0, 0, length * (0.35 * u - droop * u * u)))
        w = width * math.sin(math.pi * min(0.98, 0.15 + u * 0.85)) + 0.02
        l = b.bm.verts.new(p - side * w); r = b.bm.verts.new(p + side * w); m = b.bm.verts.new(p + Vector((0, 0, w * 0.25)))
        if prev:
            for q in ((prev[0], l, m, prev[2]), (prev[2], m, r, prev[1])):
                f = b.bm.faces.new(q); f[b.mat_layer] = 0
                for lp in f.loops:
                    lp[b.col] = jit(lerpc(col, tip, u), random.Random(i), 0.05, 1.0)
        prev = (l, r, m)



def _limb(b, p0, p1, r0, r1, col, segs=5):
    dv = p1 - p0; mid = (p0 + p1) * 0.5
    b.cyl(r0, r1, dv.length, tuple(mid), col, 'body', rot=(0, math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)), math.degrees(math.atan2(dv.y, dv.x))), segs=segs)

def hardwood(name, seed, height, crown_w, cols, hi, bark, limbs=4, fork=0.42, n=12, sq=(1.15, 1.15, 0.85)):
    """Deciduous hardwood: trunk forking at `fork` x height into `limbs` spreading limbs, each carrying lumpy leaf
    masses; open-grown oaks are wide and low, forest maples / ash taller and narrower."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    zf = height * fork
    b.cyl(0.42, 0.3, zf + 0.4, (0, 0, zf / 2), hexc(bark), 'body', segs=7)
    tips = []
    for k in range(limbs):
        a = k / limbs * math.tau + rnd.uniform(-0.4, 0.4)
        out = Vector((math.cos(a), math.sin(a), 0))
        t = Vector((0, 0, zf)) + out * crown_w * rnd.uniform(0.25, 0.38) + Vector((0, 0, (height - zf) * rnd.uniform(0.35, 0.6)))
        _limb(b, Vector((0, 0, zf - 0.2)), t, 0.22, 0.1, hexc(bark))
        tips.append(t)
    for k in range(n):
        t = tips[k % limbs]
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.0, crown_w * 0.26)
        c = t + Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(-1.6, 1.4)))
        c.z = min(c.z, height - 1.2)
        _clump(b, c, rnd.uniform(2.3, 3.2) * crown_w / 10.0, sq, cols, hi, rnd, seed, k, rough=0.45)
    _clump(b, Vector((0, 0, height - 2.6)), crown_w * 0.3, (sq[0], sq[1], sq[2] * 1.1), cols, hi, rnd, seed, 99, rough=0.4)
    return finish(b, name, smooth=True)

def wpine(name='env_wpine', seed=311, height=22.0):
    """Eastern white pine: tall straight trunk, irregular whorls of long near-horizontal branches with soft
    blue-green needle tufts (the 'flag' silhouette above the hardwood canopy)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.45, 0.12, height, (0, 0, height / 2), hexc('4e4034'), 'body', segs=7)
    cols = [hexc('20382a', 1.0), hexc('284230', 1.0), hexc('2e4a34', 1.0)]
    hi = hexc('5a7a60', 1.0)
    whorls = 6
    for w in range(whorls):
        u = 0.4 + 0.58 * w / (whorls - 1)
        z = height * u
        L = (1.0 - u) * 7.0 + 1.6
        for k in range(3):
            a = rnd.uniform(0, math.tau)
            t = Vector((math.cos(a) * L, math.sin(a) * L, z + rnd.uniform(-0.2, 0.6)))
            _limb(b, Vector((0, 0, z)), t, 0.1, 0.05, hexc('4e4034'), segs=4)
            _clump(b, t * 0.8, 1.2 + L * 0.18, (1.6, 1.6, 0.5), cols, hi, rnd, seed, w * 3 + k, rough=0.4)
    _clump(b, Vector((0, 0, height - 0.6)), 1.4, (1.0, 1.0, 1.2), cols, hi, rnd, seed, 77, rough=0.35)
    return finish(b, name, smooth=True)

def hw_far(name='env_hw_far', c1='2a4220', c2='304a24', h1='587a38', h2='5f8240'):
    """Distance LOD for deciduous forest belts (~45 tris): trunk + two merged rounded domes."""
    rnd = random.Random(13)
    b = MeshBuilder(name, G)
    b.cyl(0.35, 0.25, 4.0, (0, 0, 2.0), hexc('4e4438'), 'body', segs=4)
    _clump(b, Vector((0, 0, 7.6)), 4.6, (1.1, 1.1, 1.0), [hexc(c1, 1.0)], hexc(h1, 1.0), rnd, 6, 0, rough=0.3, sub=1)
    _clump(b, Vector((1.8, 0.5, 11.0)), 2.6, (1.0, 1.0, 0.9), [hexc(c2, 1.0)], hexc(h2, 1.0), rnd, 6, 1, rough=0.3, sub=1)
    return finish(b, name, smooth=True)

def understorey(name='env_hazel', seed=321, c=('2e4a22', '385626', '2a4420'), hi=('7a9a48', '6a8a40')):
    """Hazel / dogwood understorey bush (~3 m): a few thin stems with loose leafy masses."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(4):
        a = rnd.uniform(0, math.tau); t = Vector((math.cos(a) * 0.9, math.sin(a) * 0.9, rnd.uniform(1.6, 2.4)))
        _limb(b, Vector((0, 0, 0)), t, 0.05, 0.03, hexc('5a4a3a'), segs=3)
        _clump(b, t, rnd.uniform(0.8, 1.1), (1.2, 1.2, 0.9), [hexc(c[0], 1.0), hexc(c[1], 1.0)], hexc(hi[0], 1.0), rnd, seed, k, rough=0.45)
    _clump(b, Vector((0, 0, 0.8)), 1.0, (1.3, 1.3, 0.7), [hexc(c[2], 1.0)], hexc(hi[1], 1.0), rnd, seed, 9, rough=0.45)
    return finish(b, name, smooth=True)

def bracken(name='env_bracken', seed=331, n=7):
    """Bracken fern patch (~0.9 m): stiff arching triangular fronds."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = k / n * math.tau + rnd.uniform(-0.3, 0.3); o = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0))
        b.cyl(0.015, 0.01, 0.5, (o.x, o.y, 0.25), hexc('4a5a2a'), 'body', segs=3)
        _leaf(b, o + Vector((0, 0, 0.5)), Vector((math.cos(a), math.sin(a), 0)), rnd.uniform(0.6, 0.9), 0.24, 0.55, hexc(['3a5a24', '44662a'][k % 2], 1.0), hexc('8a9a48', 1.0), segs=3)
    return finish(b, name, smooth=True)

def meadow(name='env_meadow', seed=341, n=12, h=0.75):
    """Tall meadow / prairie grass tuft with a few seed-head stalks (timothy / bluestem)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), -0.02))
        _blade(b, p, h * rnd.uniform(0.55, 1.1), 0.035, rnd.uniform(0.12, 0.35), a, hexc(['3e5e22', '4a6a28', '52702c'][k % 3], 1.0), hexc(['8a9a4c', '9aa658', '7e9244'][k % 3], 1.0))
    for k in range(3):
        a = rnd.uniform(0, math.tau); p = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0))
        _blade(b, p, h * rnd.uniform(1.2, 1.5), 0.015, 0.15, a, hexc('6a6a3a', 1.0), hexc('b0a070', 1.0))
    return finish(b, name)

def wildflowers(name='env_wildflowers', seed=351):
    """Low wildflower patch (goldenrod, aster, clover): green blades with small coloured heads."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    heads = ['d8b43a', 'c8a030', '9a7ac8', 'e8e4d8', 'd8b43a']
    for k in range(10):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 0.5)
        p = Vector((math.cos(a) * d, math.sin(a) * d, 0)); h = rnd.uniform(0.3, 0.6)
        _blade(b, p, h, 0.03, 0.1, a, hexc('3e5a24', 1.0), hexc('5a7a34', 1.0))
        b.sphere(0.06, (p.x + math.cos(a) * 0.1, p.y + math.sin(a) * 0.1, h), hexc(heads[k % len(heads)], 1.0), 'body', segs=4, rings=2)
    return finish(b, name)

LIME = [hexc('a39c8a'), hexc('948e7e'), hexc('aca594'), hexc('8a8476')]
LMOSS = [hexc('6a7a44'), hexc('7a8a50'), hexc('8a8a60')]

def lime_boulder(name, seed, size):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, flat=0.6, rough=0.26, pal=LIME, moss=LMOSS, moss_p=0.45, crev='6a6458')
    return finish(b, name)

def lime_outcrop(name='env_lime_outcrop', seed=361):
    """Layered sedimentary ledge ~9 x 5 x 2.5 m: stacked flat beds stepping back, lichen on the treads."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=LIME, moss=LMOSS, moss_p=0.5, crev='6a6458')
    for k in range(4):
        z = k * 0.6
        _stone(b, (k * 0.5, k * 0.3, z), (4.4 - k * 0.8, 2.6 - k * 0.4, 0.55), rnd, seed + k, subdiv=2, flat=0.4, rough=0.18, **kw)
    for k in range(3):
        a = rnd.uniform(0, math.tau)
        _stone(b, (math.cos(a) * 5.0, math.sin(a) * 3.2, 0), (rnd.uniform(0.4, 0.9),) * 2 + (rnd.uniform(0.3, 0.5),), rnd, seed + 9 + k, subdiv=1, **kw)
    return finish(b, name)

OAK = [hexc('26401c', 1.0), hexc('2e4a22', 1.0), hexc('365226', 1.0), hexc('223a1a', 1.0)]
MAPLE = [hexc('2c4a20', 1.0), hexc('345424', 1.0), hexc('3c5c28', 1.0)]
ASH = [hexc('2e4a24', 1.0), hexc('385628', 1.0), hexc('42602c', 1.0)]

BUILDERS = {
    'env_oak_a': lambda: hardwood('env_oak_a', 301, 15.0, 15.0, OAK, hexc('5e7e3a', 1.0), '4e463c', limbs=5, fork=0.3, n=20, sq=(1.15, 1.15, 0.9)),
    'env_maple_t': lambda: hardwood('env_maple_t', 302, 16.0, 10.0, MAPLE, hexc('6a8a40', 1.0), '5a5046', limbs=4, fork=0.36, n=18, sq=(1.05, 1.05, 1.05)),
    'env_ash_t': lambda: hardwood('env_ash_t', 303, 21.0, 9.0, ASH, hexc('70904a', 1.0), '6a6458', limbs=3, fork=0.45, n=15, sq=(1.0, 1.0, 1.05)),
    'env_wpine': wpine,
    'env_hw_far': hw_far,
    'env_hazel': understorey,
    'env_bracken': bracken,
    'env_meadow': meadow,
    'env_wildflowers': wildflowers,
    'env_lime_a': lambda: lime_boulder('env_lime_a', 371, (1.5, 1.1, 0.9)),
    'env_lime_b': lambda: lime_boulder('env_lime_b', 372, (0.9, 0.8, 0.6)),
    'env_lime_c': lambda: lime_boulder('env_lime_c', 373, (2.1, 1.5, 1.2)),
    'env_lime_outcrop': lime_outcrop,
}

# ---- seasonal variants (leaf colours baked per season so bark keeps its colour; temperate.gd swaps by battle month)
def _H(l): return [hexc(x, 1.0) for x in l]
SEASONAL = {
    'aut': {'oak': (_H(['6a4a24', '78522a', '5e4422', '80582a']), '9a7440'), 'maple': (_H(['7e2412', '8e3a14', '865014']), 'b07030'),
            'ash': (_H(['82681e', '927422', '766a20']), 'b09a3a'), 'n': 1.0},
    'win': {'oak': (_H(['6a5a48', '74624e']), '8a7a64'), 'maple': (_H(['625650', '6a5e56']), '807468'),
            'ash': (_H(['645a4e', '6c6054']), '82766a'), 'n': 0.22},
}
for _s, _p in SEASONAL.items():
    _f = _p['n']
    BUILDERS['env_oak_a_' + _s] = (lambda s=_s, p=_p, f=_f: hardwood('env_oak_a_' + s, 301, 15.0, 15.0, p['oak'][0], hexc(p['oak'][1], 1.0), '4e463c', limbs=5, fork=0.3, n=max(5, int(20 * f)), sq=(1.15, 1.15, 0.9)))
    BUILDERS['env_maple_t_' + _s] = (lambda s=_s, p=_p, f=_f: hardwood('env_maple_t_' + s, 302, 16.0, 10.0, p['maple'][0], hexc(p['maple'][1], 1.0), '5a5046', limbs=4, fork=0.36, n=max(4, int(18 * f)), sq=(1.05, 1.05, 1.05)))
    BUILDERS['env_ash_t_' + _s] = (lambda s=_s, p=_p, f=_f: hardwood('env_ash_t_' + s, 303, 21.0, 9.0, p['ash'][0], hexc(p['ash'][1], 1.0), '6a6458', limbs=3, fork=0.45, n=max(3, int(15 * f)), sq=(1.0, 1.0, 1.05)))
BUILDERS['env_hw_far_aut'] = lambda: hw_far('env_hw_far_aut', '6a4420', '7a6224', '9a6a3a', '9a7a3a')
BUILDERS['env_hw_far_win'] = lambda: hw_far('env_hw_far_win', '5a4e42', '5e5246', '72665a', '766a5e')
BUILDERS['env_hazel_aut'] = lambda: understorey('env_hazel_aut', 321, ('7a6624', '84561e', '6a5220'), ('a08a3a', '947432'))
BUILDERS['env_hazel_win'] = lambda: understorey('env_hazel_win', 321, ('5e5040', '665646', '58483a'), ('7a6c5a', '726452'))

def main():
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    common.reset_scene()
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        o = fn()
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print('ENVASSET', name, 'tris', tris)
        common.export_glb([o], os.path.join(common.MODELS, name + '.glb'))

if __name__ == "__main__":
    main()
