"""East Asian battlefield environment set (env/east_asia; Japan, Taiwan, Korea, eastern China):
sugi (Cryptomeria) cedar, Japanese red pine with layered cloud-pad crowns, evergreen broadleaf (camphor / oak),
maple, bamboo grove, distance LOD for mixed hill forest, susuki silver grass, sasa dwarf bamboo, azalea bushes,
mossy grey andesite boulders + outcrop.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-east-asia/ASSETS.md.
Run: blender -b --python pipeline/blender/env_eastasia.py [-- name ...]   (writes game/assets/models/env_*.glb only)
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


def sugi(name, seed, height):
    """Sugi / Cryptomeria: tall straight red-brown trunk, bare lower third, narrow dense spire of dark
    blue-green foliage (a tapering core cone wrapped in overlapping lumpy masses) with a pointed top."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.42, 0.12, height * 0.95, (0, 0, height * 0.475), hexc('4e3424'), 'body', segs=7)
    z0 = height * 0.3
    b.cyl(2.6, 0.15, height - z0, (0, 0, (height + z0) / 2), hexc('1c3220', 1.0), 'body', segs=7)
    cols = [hexc('1e3622', 1.0), hexc('233e26', 1.0), hexc('29442a', 1.0)]
    hi = hexc('4c6a40', 1.0)
    n = 18
    for k in range(n):
        u = 0.3 + 0.62 * k / (n - 1)
        z = height * u
        w = (1.0 - u) * 3.2 + 0.5
        a = k * 2.39996
        d = w * 0.55
        c = Vector((math.cos(a) * d, math.sin(a) * d, z))
        _clump(b, c, w * 0.62, (1.0, 1.0, 1.25), cols, hi, rnd, seed, k, rough=0.4)
    return finish(b, name, smooth=True)

def jpine(name, seed, height):
    """Japanese red / black pine (akamatsu / kuromatsu): leaning, kinked red-brown trunk, horizontal branches carrying
    flat layered 'cloud' needle pads."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * height * 0.18
    prev = Vector((0, 0, 0)); segs = 5
    pts = []
    for i in range(segs):
        u = (i + 1) / segs
        p = lean * math.sin(u * 2.2) + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), height * 0.82 * u))
        mid = (prev + p) * 0.5; dv = p - prev
        ry = math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)); rz = math.degrees(math.atan2(dv.y, dv.x))
        b.cyl(0.34 - u * 0.18, 0.3 - u * 0.18, dv.length + 0.1, tuple(mid), hexc('55382a') if i % 2 else hexc('604030'), 'body', rot=(0, ry, rz), segs=6)
        pts.append(p); prev = p
    cols = [hexc('243e24', 1.0), hexc('2c4628', 1.0), hexc('34502c', 1.0)]
    hi = hexc('6a8a4c', 1.0)
    for k in range(9):
        base = pts[min(len(pts) - 1, 1 + k % 4)] if k < 8 else pts[-1]
        a = rnd.uniform(0, math.tau); d = rnd.uniform(1.0, 3.4) if k < 8 else 0.0
        c = base + Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.2, 1.0)))
        if d > 0.5:
            dv = c - base; mid = (base + c) * 0.5
            b.cyl(0.1, 0.06, dv.length, tuple(mid), hexc('5e3a28'), 'body', rot=(0, math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)), math.degrees(math.atan2(dv.y, dv.x))), segs=4)
        _clump(b, c, rnd.uniform(1.4, 2.1), (1.5, 1.5, 0.42), cols, hi, rnd, seed, k, rough=0.35)
    return finish(b, name, smooth=True)

def broadleaf(name, seed, height, crown_w, cols, hi, bark='6a6458'):
    """Evergreen broadleaf (camphor / evergreen oak) or maple: grey trunk forking into a big rounded dome of
    lumpy foliage masses, full to the ground at the edge."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.36, 0.24, height * 0.45, (0, 0, height * 0.225), hexc(bark), 'body', segs=6)
    for k in range(3):
        a = k / 3 * math.tau + rnd.uniform(-0.4, 0.4)
        b.cyl(0.18, 0.1, height * 0.35, (math.cos(a) * 0.7, math.sin(a) * 0.7, height * 0.52), hexc(bark), 'body', rot=(0, 28, math.degrees(a)), segs=5)
    for k in range(11):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.2, 1.0) * crown_w * 0.38
        z = height * rnd.uniform(0.5, 0.88) - d * 0.2
        c = Vector((math.cos(a) * d, math.sin(a) * d, z))
        _clump(b, c, rnd.uniform(1.8, 2.6) * crown_w / 9.0, (1.15, 1.15, 0.9), cols, hi, rnd, seed, k, rough=0.45)
    return finish(b, name, smooth=True)

def bamboo(name='env_bamboo', seed=211, n=7, height=11.0):
    """Bamboo grove clump (madake): bundle of slender jointed green culms arching outward, feathery leaf sprays
    hanging along the upper half."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for s in range(n):
        o = Vector((rnd.uniform(-1.3, 1.3), rnd.uniform(-1.3, 1.3), 0))
        h = height * rnd.uniform(0.75, 1.1)
        out = Vector((o.x, o.y, 0)).normalized() if o.length > 0.1 else Vector((1, 0, 0))
        prev = o; segs = 3
        for i in range(segs):
            u = (i + 1) / segs
            p = o + out * (u ** 2) * h * 0.16 + Vector((0, 0, h * u))
            mid = (prev + p) * 0.5; dv = p - prev
            ry = math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)); rz = math.degrees(math.atan2(dv.y, dv.x))
            b.cyl(0.08, 0.07, dv.length, tuple(mid), hexc('5a7034') if i % 2 else hexc('667a3a'), 'body', rot=(0, ry, rz), segs=3)
            if i >= 1:
                for k in range(2):
                    a = rnd.uniform(0, math.tau)
                    _leaf(b, p, Vector((math.cos(a), math.sin(a), 0)), rnd.uniform(1.4, 2.0), 0.32, 0.9, hexc(['3a6224', '446e28'][k], 1.0), hexc('7a9a46', 1.0), segs=2)
            prev = p
        _clump(b, prev + out * 0.4, 0.9, (1.0, 1.0, 1.4), [hexc('3a6224', 1.0), hexc('46702a', 1.0)], hexc('92b058', 1.0), rnd, seed, s, rough=0.5)
    return finish(b, name, smooth=True)

def ea_far(name='env_ea_far'):
    """Distance LOD for mixed hill forest (~70 tris): trunk + one broad lumpy dome, rounder than the conifer LOD."""
    rnd = random.Random(9)
    b = MeshBuilder(name, G)
    b.cyl(0.35, 0.25, 6.0, (0, 0, 3.0), hexc('5a4a3a'), 'body', segs=4)
    _clump(b, Vector((0, 0, 9.0)), 4.2, (1.1, 1.1, 0.9), [hexc('223a22', 1.0)], hexc('4a6a3a', 1.0), rnd, 5, 0, rough=0.3, sub=1)
    return finish(b, name, smooth=True)

def susuki(name='env_susuki', seed=221, n=14):
    """Susuki / Japanese silver grass (Miscanthus): tall arching blades with pale silky flower plumes (~1.6 m)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), -0.02))
        _blade(b, p, rnd.uniform(0.9, 1.4), 0.035, rnd.uniform(0.3, 0.6), a, hexc('4a6a2a', 1.0), hexc('8a9a52', 1.0))
    for k in range(6):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), 0))
        _blade(b, p, rnd.uniform(1.4, 1.8), 0.02, rnd.uniform(0.2, 0.4), a, hexc('7a7a4a', 1.0), hexc('e4dcc4', 1.0))
        top = p + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 1.5))
        _leaf(b, top - Vector((0, 0, 0.1)), Vector((math.cos(a), math.sin(a), 0)), 0.45, 0.09, 1.2, hexc('cfc6aa', 1.0), hexc('efe8d6', 1.0), segs=2)
    return finish(b, name)

def sasa(name='env_sasa', seed=231):
    """Sasa dwarf bamboo thicket (~1.2 m): dense low leafy mass with broad pointed leaves; carpets forest floors."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('2c4a22', 1.0), hexc('345426', 1.0), hexc('3c5c2a', 1.0)]
    for k in range(4):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.2, 1.0)
        _clump(b, Vector((math.cos(a) * d, math.sin(a) * d, 0.55)), rnd.uniform(0.6, 0.85), (1.4, 1.4, 0.75), cols, hexc('7a9a4a', 1.0), rnd, seed, k, rough=0.4)
    for k in range(9):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.3, 1.3)
        _leaf(b, Vector((math.cos(a) * d, math.sin(a) * d, 0.7)), Vector((math.cos(a), math.sin(a), 0)), 0.55, 0.11, 0.6, hexc('3a6226', 1.0), hexc('a2b062', 1.0), segs=2)
    return finish(b, name, smooth=True)

def azalea(name='env_azalea', seed=241):
    """Tsutsuji azalea bush (~1.4 m): dense rounded small-leaved mound, a few pink-flowering patches."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('26401e', 1.0), hexc('2e4a24', 1.0)]
    for k in range(5):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.1, 0.8)
        c = Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.6, 0.9)))
        bm = bmesh.ops.create_icosphere(b.bm, subdivisions=1, radius=0.75, matrix=Matrix.Translation(c) @ Matrix.Diagonal((1.2, 1.2, 0.85, 1)))
        for v in bm['verts']:
            v.co += (v.co - c).normalized() * noise.noise(v.co * 1.5 + Vector((seed, k, 2))) * 0.25
        col = cols[k % 2]
        colour_faces(b, new_faces(b, bm['verts']), lambda f: hexc('b0587a', 1.0) if (f.calc_center_median().z > c.z and rnd.random() < 0.22) else jit(col, rnd, 0.08, 1.0))
    return finish(b, name, smooth=True)

ANDESITE = [hexc('77746e'), hexc('6a6862'), hexc('827d74'), hexc('615f5a')]
MOSS = [hexc('4a6a30'), hexc('587a36'), hexc('6a7a44')]

def andesite_boulder(name, seed, size):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, flat=0.75, rough=0.36, pal=ANDESITE, moss=MOSS, moss_p=0.7, crev='45433f')
    return finish(b, name)

def andesite_outcrop(name='env_andesite_outcrop', seed=251):
    """Weathered volcanic crag ~9 x 6 x 4 m: steep jointed blocks with mossy ledges (hill country of Honshu / Kyushu)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=ANDESITE, moss=MOSS, moss_p=0.75, crev='45433f')
    _stone(b, (0, 0, 0), (3.2, 2.6, 3.8), rnd, seed, subdiv=3, flat=0.85, rough=0.3, **kw)
    _stone(b, (2.8, 1.2, -0.3), (2.2, 1.9, 2.4), rnd, seed + 1, subdiv=2, flat=0.8, **kw)
    _stone(b, (-2.6, -1.4, -0.3), (1.8, 1.6, 1.6), rnd, seed + 2, subdiv=2, **kw)
    for k in range(3):
        a = rnd.uniform(0, math.tau)
        _stone(b, (math.cos(a) * 4.6, math.sin(a) * 3.6, 0), (rnd.uniform(0.4, 0.8),) * 2 + (rnd.uniform(0.3, 0.6),), rnd, seed + 5 + k, subdiv=1, **kw)
    return finish(b, name)

BROAD = [hexc('243e1e', 1.0), hexc('2c4824', 1.0), hexc('34522a', 1.0), hexc('203a1c', 1.0)]
MAPLE = [hexc('3a5a24', 1.0), hexc('46682a', 1.0), hexc('52702e', 1.0)]

BUILDERS = {
    'env_sugi_a': lambda: sugi('env_sugi_a', 201, 24.0),
    'env_sugi_b': lambda: sugi('env_sugi_b', 202, 18.0),
    'env_jpine_a': lambda: jpine('env_jpine_a', 203, 14.0),
    'env_jpine_b': lambda: jpine('env_jpine_b', 204, 11.0),
    'env_broadleaf_a': lambda: broadleaf('env_broadleaf_a', 205, 15.0, 11.0, BROAD, hexc('5a7a3c', 1.0)),
    'env_maple_a': lambda: broadleaf('env_maple_a', 206, 10.0, 8.0, MAPLE, hexc('8aa44c', 1.0), bark='5a5048'),
    'env_bamboo': bamboo,
    'env_ea_far': ea_far,
    'env_susuki': susuki,
    'env_sasa': sasa,
    'env_azalea': azalea,
    'env_andesite_a': lambda: andesite_boulder('env_andesite_a', 261, (1.4, 1.1, 1.2)),
    'env_andesite_b': lambda: andesite_boulder('env_andesite_b', 262, (0.9, 0.8, 0.8)),
    'env_andesite_c': lambda: andesite_boulder('env_andesite_c', 263, (2.0, 1.6, 1.7)),
    'env_andesite_outcrop': andesite_outcrop,
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
