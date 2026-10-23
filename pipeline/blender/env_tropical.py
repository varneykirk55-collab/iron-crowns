"""Tropical battlefield environment set (env/tropical; Philippines, Indonesia, Amazon, Congo, Caribbean, Hawaii):
rainforest canopy + emergent trees with buttress roots, coconut palm, banana, fern clumps, far-LOD rainforest crown,
lush tall grass, dark mossy basalt boulders + outcrop, low taro / leafy groundcover.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-tropical/ASSETS.md.
Run: blender -b --python pipeline/blender/env_tropical.py [-- name ...]   (writes game/assets/models/env_*.glb only)
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

def rain_tree(name, seed, height, crown_w, emergent=False):
    """Rainforest canopy tree: pale straight trunk with buttress fins, branches carrying layered dark-green crown
    masses; the emergent form is taller with a flat umbrella crown standing above the canopy."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('4e483e'); bark2 = hexc('3e382f')
    tr = 0.45 if emergent else 0.38
    b.cyl(tr, tr * 0.55, height * 0.78, (0, 0, height * 0.39), bark, 'body', segs=7)
    for k in range(5):                       # buttress roots: thin triangular fins
        a = k / 5 * math.tau + rnd.uniform(-0.3, 0.3)
        out = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-out.y, out.x, 0)) * 0.12
        h = height * rnd.uniform(0.1, 0.16); L = rnd.uniform(1.6, 2.6)
        p0 = out * tr * 0.6; p1 = out * (tr + L) + Vector((0, 0, -0.1)); p2 = out * tr * 0.7 + Vector((0, 0, h))
        vs = [b.bm.verts.new(v) for v in (p0 - side, p1, p2 - side * 0.5, p0 + side, p2 + side * 0.5)]
        for q in ((vs[0], vs[1], vs[2]), (vs[3], vs[4], vs[1]), (vs[2], vs[1], vs[4])):
            f = b.bm.faces.new(q); f[b.mat_layer] = 0
            for l in f.loops: l[b.col] = jit(bark2, rnd, 0.05)
    dark = [hexc('21401d', 1.0), hexc('2a4c22', 1.0), hexc('345a27', 1.0), hexc('1f3a1c', 1.0), hexc('3a5a24', 1.0)]
    hi = hexc('6e9a3e', 1.0)
    n = 8 if emergent else 12
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        if emergent:
            z = height * rnd.uniform(0.84, 0.97); d = rnd.uniform(0.5, 1.0) * crown_w * 0.5; r = rnd.uniform(2.4, 3.4); sq = (1.5, 1.5, 0.45)
        else:
            z = height * rnd.uniform(0.45, 0.95); d = rnd.uniform(0.3, 1.0) * crown_w * 0.45 * (1.15 - z / height * 0.4); r = rnd.uniform(1.9, 2.9); sq = (1.2, 1.2, 0.9)
        c = Vector((math.cos(a) * d, math.sin(a) * d, z))
        _clump(b, c, r, sq, dark, hi, rnd, seed, k, rough=0.48)
        if k < 5 and d > 1.0:
            b.cyl(0.14, 0.07, d + 0.5, (c.x * 0.5, c.y * 0.5, z - r * 0.4), bark2, 'body', rot=(0, 70, math.degrees(a)), segs=4)
    if not emergent:                         # hanging lianas / epiphyte mass on the trunk
        for k in range(3):
            a = rnd.uniform(0, math.tau); z = height * rnd.uniform(0.25, 0.55)
            _clump(b, Vector((math.cos(a) * tr, math.sin(a) * tr, z)), rnd.uniform(0.5, 0.8), (1, 1, 1.6), [hexc('2f5a2a', 1.0)], hi, rnd, seed, 20 + k, sub=1)
    return finish(b, name, smooth=True)

def palm(name, seed, height):
    """Coconut palm: slender curving ringed trunk, crown of long pinnate fronds drooping outwards, nut cluster."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    lean = Vector((rnd.uniform(0.5, 1.0), rnd.uniform(-0.3, 0.3), 0)) * height * 0.16
    segs = 7; prev = Vector((0, 0, 0))
    for i in range(segs):
        u = (i + 1) / segs
        p = lean * (u ** 2) + Vector((0, 0, height * u))
        mid = (prev + p) * 0.5; dv = p - prev
        rot_y = math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)); rot_z = math.degrees(math.atan2(dv.y, dv.x))
        b.cyl(0.24 - u * 0.08 + 0.02, 0.22 - u * 0.08, dv.length + 0.05, tuple(mid), hexc('4a4032') if i % 2 else hexc('564a3a'), 'body', rot=(0, rot_y, rot_z), segs=6)
        prev = p
    top = prev
    for k in range(4):
        a = k / 4 * math.tau
        b.sphere(0.16, (top.x + math.cos(a) * 0.25, top.y + math.sin(a) * 0.25, top.z - 0.35), hexc('6b5a2a'), 'body', segs=5, rings=3)
    nf = 11
    for k in range(nf):
        a = k / nf * math.tau + rnd.uniform(-0.15, 0.15)
        d = Vector((math.cos(a), math.sin(a), 0))
        _leaf(b, top + Vector((0, 0, 0.1)), d, rnd.uniform(4.6, 5.8), 0.62, rnd.uniform(0.75, 1.05), hexc(['2f5a24', '3a6a2a', '355f26'][k % 3], 1.0), hexc('7f9a44', 1.0), segs=5)
    return finish(b, name, smooth=True)

def banana(name='env_banana', seed=105):
    """Banana / wild plantain: clustered green pseudostems with huge paddle leaves (~4 m)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for s in range(3):
        o = Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0)); h = rnd.uniform(2.0, 3.2)
        b.cyl(0.16, 0.11, h, (o.x, o.y, h / 2), hexc('5b6b38'), 'body', segs=6)
        for k in range(6):
            a = k / 6 * math.tau + s
            _leaf(b, o + Vector((0, 0, h - 0.1)), Vector((math.cos(a), math.sin(a), 0)), rnd.uniform(1.8, 2.5), 0.42, rnd.uniform(0.25, 0.6), hexc(['3d7a2a', '4a8a30', '356d26'][k % 3], 1.0), hexc('8aa84a', 1.0), segs=4)
    return finish(b, name, smooth=True)

def fern(name='env_fern', seed=111, n=9, size=1.2):
    """Ground fern clump (~1 m): arching fronds from a central crown."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = k / n * math.tau + rnd.uniform(-0.2, 0.2)
        _leaf(b, Vector((0, 0, 0.05)), Vector((math.cos(a), math.sin(a), 0)), size * rnd.uniform(0.8, 1.1), size * 0.16, 0.9, hexc(['2c5a22', '35652a'][k % 2], 1.0), hexc('76a040', 1.0), segs=4)
        # turn the first segment upward so fronds arch
    for v in b.bm.verts:
        r = Vector((v.co.x, v.co.y, 0)).length
        v.co.z += size * 0.9 * math.sin(min(r / size, 1.0) * math.pi) * 0.55
    return finish(b, name, smooth=True)

def taro(name='env_taro', seed=121):
    """Low leafy groundcover (taro / ginger), knee-high: broad heart-shaped leaves on short stalks."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(6):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.05, 0.3)
        o = Vector((math.cos(a) * d, math.sin(a) * d, 0)); h = rnd.uniform(0.25, 0.5)
        b.cyl(0.02, 0.015, h, (o.x, o.y, h / 2), hexc('4f6a30'), 'body', segs=3)
        _leaf(b, o + Vector((0, 0, h)), Vector((math.cos(a), math.sin(a), 0)), rnd.uniform(0.35, 0.5), 0.2, 0.5, hexc(['2f6a26', '3a7a2c'][k % 2], 1.0), hexc('6a9a40', 1.0), segs=3)
    return finish(b, name, smooth=True)

def jungle_bush(name='env_jungle_bush', seed=125):
    """Understorey thicket (~2.5 m): overlapping leafy masses + a few broad leaves, fills the gaps between trunks."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('2a5022', 1.0), hexc('335c26', 1.0), hexc('3d6a2a', 1.0)]
    for k in range(5):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.2, 1.2)
        c = Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.7, 1.6)))
        _clump(b, c, rnd.uniform(0.8, 1.2), (1.2, 1.2, 0.9), cols, hexc('7aa448', 1.0), rnd, seed, k, rough=0.42)
    for k in range(5):
        a = k / 5 * math.tau
        _leaf(b, Vector((0, 0, 1.2)), Vector((math.cos(a), math.sin(a), 0)), 1.6, 0.3, 0.6, hexc('3a7028', 1.0), hexc('86a84c', 1.0), segs=3)
    return finish(b, name, smooth=True)

def tropic_far(name='env_tropic_far'):
    """Distance LOD for rainforest belts (~60 tris): a trunk and a flattened lumpy crown."""
    rnd = random.Random(7)
    b = MeshBuilder(name, G)
    b.cyl(0.4, 0.3, 9.0, (0, 0, 4.5), hexc('4e483e'), 'body', segs=4)
    _clump(b, Vector((0, 0, 11.5)), 4.6, (1.2, 1.2, 0.62), [hexc('22441f', 1.0)], hexc('4a7430', 1.0), rnd, 3, 0, rough=0.25, sub=1)
    return finish(b, name, smooth=True)

def grass_lush(name='env_grass_lush', seed=131, n=11, h=0.7):
    """Lush tall tropical grass (cogon / guinea grass), bright saturated green."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), -0.02))
        col = hexc(['356a22', '3f7626', '4a7f2a'][k % 3], 1.0); tip = hexc(['8fae4c', '9cb858', '7fa244'][k % 3], 1.0)
        _blade(b, p, h * rnd.uniform(0.6, 1.2), 0.04, rnd.uniform(0.15, 0.4), a, col, tip)
    return finish(b, name)

BASALT = [hexc('6a655e'), hexc('5c5852'), hexc('726c64'), hexc('55514c')]
MOSS = [hexc('3e5a2a'), hexc('4d6a30'), hexc('5a6a3a')]

def basalt_boulder(name, seed, size):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, flat=0.7, rough=0.34, pal=BASALT, moss=MOSS, moss_p=0.75, crev='3a3733')
    return finish(b, name)

def basalt_outcrop(name='env_basalt_outcrop', seed=141):
    """Weathered volcanic outcrop ~8 x 6 x 3 m, mossy, rounder and taller than the Nordic slabs."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=BASALT, moss=MOSS, moss_p=0.8, crev='3a3733')
    _stone(b, (0, 0, 0), (3.8, 2.8, 2.8), rnd, seed, subdiv=3, flat=0.8, rough=0.3, **kw)
    _stone(b, (3.0, 1.4, -0.2), (2.2, 1.8, 1.9), rnd, seed + 1, subdiv=2, flat=0.75, **kw)
    _stone(b, (-2.8, -1.2, -0.3), (1.9, 1.5, 1.4), rnd, seed + 2, subdiv=2, **kw)
    return finish(b, name)

BUILDERS = {
    'env_rain_tree_a': lambda: rain_tree('env_rain_tree_a', 101, 20.0, 11.0),
    'env_rain_tree_b': lambda: rain_tree('env_rain_tree_b', 102, 16.0, 9.0),
    'env_rain_emergent': lambda: rain_tree('env_rain_emergent', 103, 30.0, 14.0, True),
    'env_palm_a': lambda: palm('env_palm_a', 104, 13.0),
    'env_palm_b': lambda: palm('env_palm_b', 106, 10.0),
    'env_banana': banana,
    'env_fern': fern,
    'env_taro': taro,
    'env_jungle_bush': jungle_bush,
    'env_tropic_far': tropic_far,
    'env_grass_lush': grass_lush,
    'env_basalt_a': lambda: basalt_boulder('env_basalt_a', 151, (1.5, 1.2, 1.2)),
    'env_basalt_b': lambda: basalt_boulder('env_basalt_b', 152, (1.0, 0.9, 0.8)),
    'env_basalt_c': lambda: basalt_boulder('env_basalt_c', 153, (2.2, 1.8, 1.6)),
    'env_basalt_outcrop': basalt_outcrop,
}

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
