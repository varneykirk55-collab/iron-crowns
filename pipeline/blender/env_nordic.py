"""Nordic battlefield environment set (env/scandinavia-medieval): Norway spruce, Scots pine, silver birch, far-LOD
conifer, granite boulders + low outcrops, grass tufts, heather, juniper, reeds, fallen log, pebble clusters.
100 % procedural / original (built from bmesh primitives + mathutils.noise displacement in this script, no external
meshes or textures) -> no licence obligations; see evidence/env-scandinavia/ASSETS.md.
Run: blender -b --python pipeline/blender/env_nordic.py [-- name ...]   (writes game/assets/models/env_*.glb only)
The helpers (MeshBuilder wrappers, _stone, _blade, colour utils) are imported by the other biome scripts (env_<biome>.py).
Units are metres (Z up in Blender, Y up in Godot). Vertex colour alpha (-> UV2.y, glTF drops alpha) is the foliage
mask read by game/shaders/env_foliage.gdshader: 1 = needles / leaves / blades (wind sway + rounded crown normals),
0 = wood / stone (rigid)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import common
from common import hexc, MeshBuilder

G = ['body', 'recoil']

def lerpc(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(4))

def jit(c, rnd, amt=0.06, a=None):
    k = 1.0 + rnd.uniform(-amt, amt)
    return (min(c[0] * k, 1), min(c[1] * k * (1 + rnd.uniform(-amt, amt) * 0.4), 1), min(c[2] * k, 1), c[3] if a is None else a)

def finish(b, name, smooth=False):
    obj = b.to_object(with_vid=False)
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj

def colour_faces(b, faces, fn):
    for f in faces:
        c = fn(f)
        for l in f.loops:
            l[b.col] = c

def new_faces(b, verts):
    fs = set()
    for v in verts:
        fs.update(v.link_faces)
    return fs

# ------------------------------------------------------------------ conifers
def spruce(name='env_spruce_a', seed=1, height=15.0, radius=3.4, tiers=9, segs=9):
    """Norway spruce: tiers of drooping, jagged branch skirts around a trunk, narrowing to a spire."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('3d2c20')
    b.cyl(0.32, 0.12, height * 0.55, (0, 0, height * 0.275), bark, 'body', segs=6)
    dark = hexc('1c3420', 1.0); mid = hexc('2b4a2c', 1.0); tip = hexc('46643a', 1.0)
    z0 = height * 0.14
    for t in range(tiers):
        u = t / (tiers - 1)
        r = radius * (1.0 - u) ** 0.95 * rnd.uniform(0.88, 1.08) + 0.35
        z = z0 + (height * 0.9 - z0) * u ** 0.92
        drop = r * rnd.uniform(0.42, 0.55)          # branch tips droop below the attachment ring
        hgt = (height - z0) / tiers * 1.9
        top = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), z + hgt * 0.55))
        ring = []
        rot = rnd.uniform(0, math.tau)
        for s in range(segs * 2):
            a = rot + s / (segs * 2) * math.tau
            rr = r * (1.0 if s % 2 == 0 else rnd.uniform(0.58, 0.72))   # jagged outline
            zz = z - drop * (1.0 if s % 2 == 0 else 0.7) + rnd.uniform(-0.15, 0.15)
            ring.append(b.bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, zz)))
        inner = [b.bm.verts.new((math.cos(rot + s / segs * math.tau) * r * 0.25, math.sin(rot + s / segs * math.tau) * r * 0.25, z - drop * 0.15)) for s in range(segs)]
        vt = b.bm.verts.new(top)
        fs = []
        n = len(ring)
        for s in range(n):
            fs.append(b.bm.faces.new((ring[s], ring[(s + 1) % n], vt)))
        for s in range(segs):   # underside so the skirt has volume from low cameras
            fs.append(b.bm.faces.new((inner[s], ring[(2 * s + 1) % n], ring[2 * s])))
            fs.append(b.bm.faces.new((inner[s], inner[(s + 1) % segs], ring[(2 * s + 1) % n])))
        for f in fs:
            f[b.mat_layer] = 0
            for l in f.loops:
                h = (l.vert.co.z - z0) / height
                out = Vector((l.vert.co.x, l.vert.co.y, 0)).length / max(r, 0.01)
                c = lerpc(dark, mid, min(out, 1.0))
                c = lerpc(c, tip, max(0.0, out - 0.75) * 1.6 * (0.5 + 0.5 * h))
                l[b.col] = jit(c, rnd, 0.05, 1.0)
    return finish(b, name, smooth=True)

def pine(name='env_pine_a', seed=3, height=16.0):
    """Scots pine: long bare trunk, orange upper bark, a high, flat, irregular crown of needle clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.34, 0.24, height * 0.45, (0, 0, height * 0.225), hexc('4a3526'), 'body', segs=7)
    lean = Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0))
    b.cyl(0.24, 0.1, height * 0.4, (lean.x * 0.5, lean.y * 0.5, height * 0.65), hexc('7a5a40'), 'body', segs=6)
    for k in range(6):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.6, 2.6); z = height * rnd.uniform(0.66, 0.95)
        r = rnd.uniform(1.4, 2.3) * (1.15 - (z / height - 0.66))
        c = Vector((math.cos(a) * d + lean.x, math.sin(a) * d + lean.y, z))
        bm = bmesh.ops.create_icosphere(b.bm, subdivisions=1, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((1.3, 1.3, 0.55, 1)))
        for v in bm['verts']:
            v.co += (v.co - c).normalized() * noise.noise(v.co * 0.9 + Vector((seed, k, 0))) * r * 0.35
        col = hexc(['21391f', '28432a', '2e4a2c'][k % 3], 1.0)
        colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(lerpc(col, hexc('4a6a3c', 1.0), max(0.0, f.calc_center_median().z - c.z) / r * 0.8), rnd, 0.06, 1.0))
        if k < 4:   # branch to the clump
            b.cyl(0.08, 0.05, d + 0.3, ((c.x + lean.x) * 0.5, (c.y + lean.y) * 0.5, z - 0.6), hexc('5e4632'), 'body', rot=(0, 90, math.degrees(a)), segs=4)
    return finish(b, name, smooth=True)

def birch(name='env_birch_a', seed=5, height=11.0):
    """Silver birch: slender white trunk with dark lenticel bands, loose light-green crown clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bands = 7
    lean = rnd.uniform(-6, 6)
    for i in range(bands):
        h0 = height * 0.7 * i / bands
        col = hexc('d8d4c8') if i % 2 == 0 else hexc('5a5550') if i in (1, 5) else hexc('bdb8ac')
        r0 = 0.2 * (1 - i / bands * 0.6); r1 = 0.2 * (1 - (i + 1) / bands * 0.6)
        b.cyl(r0, r1, height * 0.7 / bands, (0, math.sin(math.radians(lean)) * h0, h0 + height * 0.7 / bands / 2), col, 'body', segs=6, rot=(lean, 0, 0))
    lc = [hexc('5f7f3a', 1.0), hexc('6e8c44', 1.0), hexc('566f34', 1.0), hexc('7a9a4c', 1.0)]
    top_y = math.sin(math.radians(lean)) * height * 0.7
    for k in range(7):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.3, 1.8); z = height * rnd.uniform(0.5, 0.95)
        r = rnd.uniform(1.0, 1.7) * (1.2 - abs(z / height - 0.72))
        c = Vector((math.cos(a) * d, math.sin(a) * d + top_y * (z / height), z))
        bm = bmesh.ops.create_icosphere(b.bm, subdivisions=1, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((1, 1, 1.25, 1)))
        for v in bm['verts']:
            v.co += (v.co - c).normalized() * noise.noise(v.co * 1.3 + Vector((seed, k, 1))) * r * 0.4
        col = lc[k % 4]
        colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(lerpc(col, hexc('94ad5c', 1.0), max(0.0, f.calc_center_median().z - c.z) / r * 0.5), rnd, 0.07, 1.0))
    return finish(b, name, smooth=True)

def conifer_far(name='env_conifer_far'):
    """Distance LOD for the far forest belts (~40 tris): two stacked jagged cones."""
    b = MeshBuilder(name, G)
    b.cyl(0.3, 0.2, 3.0, (0, 0, 1.5), hexc('3d2c20'), 'body', segs=4)
    b.cyl(3.0, 0.4, 8.0, (0, 0, 6.0), hexc('203a22', 1.0), 'body', segs=7)
    b.cyl(1.9, 0.05, 6.5, (0, 0, 11.5), hexc('2a472b', 1.0), 'body', segs=6)
    return finish(b, name, smooth=True)

# ------------------------------------------------------------------ stone
GRANITE = [hexc('8a867e'), hexc('7b776f'), hexc('938c80'), hexc('6f6b66')]
LICHEN = [hexc('9a9670'), hexc('6f7a4a'), hexc('a8a690')]

def _stone(b, c, size, rnd, seed, subdiv=2, flat=0.55, rough=0.28, pal=None, moss=None, moss_p=0.55, crev='5d5953'):
    """pal / moss / crev: rock + lichen palette (defaults: Nordic granite); other biomes pass their own."""
    pal = pal or GRANITE; moss = LICHEN if moss is None else moss
    bm = bmesh.ops.create_icosphere(b.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4))
    base = pal[rnd.randrange(len(pal))]
    off = Vector((seed * 3.1, seed * 1.7, seed * 0.3))
    for v in bm['verts']:
        p = v.co.copy()
        d = 1.0 + noise.noise(p * 1.4 + off) * rough + noise.noise(p * 3.5 + off) * rough * 0.35
        p *= d
        p = Vector((p.x * size[0], p.y * size[1], p.z * size[2]))
        if p.z < 0: p.z *= 0.35                       # flat, embedded base
        p.z -= size[2] * 0.18                         # sunk into the ground a little
        if p.z > size[2] * flat:                      # glacial planing: flattened top
            p.z = size[2] * flat + (p.z - size[2] * flat) * 0.35
        v.co = p + Vector(c)
    def fc(f):
        n = f.normal
        cc = jit(base, rnd, 0.07)
        cc = lerpc(cc, hexc(crev), max(0.0, -n.z) * 0.7)              # darker undersides / crevices
        if moss and n.z > 0.55 and rnd.random() < moss_p:               # lichen + moss on the upper faces
            cc = lerpc(cc, moss[rnd.randrange(len(moss))], rnd.uniform(0.35, 0.8))
        return cc
    fs = new_faces(b, bm['verts'])
    for f in fs: f.normal_update()
    colour_faces(b, fs, fc)

def boulder(name, seed, size):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed)
    if seed % 2 == 0:   # a split-off companion stone
        _stone(b, (size[0] * 1.05, size[1] * 0.4, 0), (size[0] * 0.4, size[1] * 0.35, size[2] * 0.4), rnd, seed + 11, subdiv=1)
    return finish(b, name)

def outcrop(name='env_outcrop_a', seed=21):
    """Low glacier-polished granite outcrop (hällmark) ~9 x 6 x 2.2 m: overlapping planed slabs + loose stones."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), (4.6, 3.0, 2.0), rnd, seed, subdiv=3, flat=0.5, rough=0.22)
    _stone(b, (3.4, 1.6, -0.2), (2.6, 1.9, 1.5), rnd, seed + 1, subdiv=2, flat=0.45)
    _stone(b, (-3.2, -1.0, -0.3), (2.2, 1.6, 1.1), rnd, seed + 2, subdiv=2)
    for k in range(4):
        a = rnd.uniform(0, math.tau)
        _stone(b, (math.cos(a) * 5.4, math.sin(a) * 3.8, 0), (rnd.uniform(0.4, 0.8),) * 2 + (rnd.uniform(0.3, 0.5),), rnd, seed + 5 + k, subdiv=1)
    return finish(b, name)

def pebbles(name='env_pebbles'):
    rnd = random.Random(31)
    b = MeshBuilder(name, G)
    for k in range(5):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 0.9)
        s = rnd.uniform(0.12, 0.3)
        _stone(b, (math.cos(a) * d, math.sin(a) * d, 0), (s * 1.3, s, s * 0.7), rnd, 40 + k, subdiv=1)
    return finish(b, name)

# ------------------------------------------------------------------ ground cover
def _blade(b, p, h, w, lean, a, col, tipc):
    up = Vector((math.cos(a) * lean, math.sin(a) * lean, h))
    side = Vector((-math.sin(a), math.cos(a), 0)) * w
    v0 = b.bm.verts.new(p - side); v1 = b.bm.verts.new(p + side); v2 = b.bm.verts.new(p + up)
    f = b.bm.faces.new((v0, v1, v2))
    f[b.mat_layer] = 0
    for l in f.loops:
        l[b.col] = tipc if l.vert is v2 else col

def grass_tuft(name='env_grass_tuft', seed=41, n=9, h=0.55, dry=False):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), -0.02))
        if dry:
            col = hexc(['7d7445', '8a7f4c', '6f6a3e'][k % 3], 1.0); tip = hexc('b5a66c', 1.0)
        else:
            col = hexc(['3e5328', '4a5f2c', '55682f'][k % 3], 1.0); tip = hexc(['8a8f4e', '9a9858', '7b8446'][k % 3], 1.0)
        _blade(b, p, h * rnd.uniform(0.6, 1.15), 0.035, rnd.uniform(0.1, 0.3), a, col, tip)
    return finish(b, name)

def heather(name='env_heather', seed=51):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(6):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 0.35)
        c = (math.cos(a) * d, math.sin(a) * d, 0.12)
        col = hexc(['5b4a52', '6a5560', '4b5232', '735a68'][k % 4], 1.0)
        b.sphere(rnd.uniform(0.18, 0.28), c, col, 'body', segs=5, rings=3, scale=(1, 1, 0.65))
    return finish(b, name, smooth=True)

def juniper(name='env_juniper', seed=61):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(4):
        c = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0.5 + k * 0.35))
        bm = bmesh.ops.create_icosphere(b.bm, subdivisions=1, radius=0.7 - k * 0.12, matrix=Matrix.Translation(c) @ Matrix.Diagonal((1, 1, 1.4, 1)))
        for v in bm['verts']:
            v.co += (v.co - c).normalized() * noise.noise(v.co * 2.0 + Vector((k, 0, 7))) * 0.18
        colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(hexc('2c4430', 1.0), rnd, 0.1, 1.0))
    return finish(b, name, smooth=True)

def reeds(name='env_reeds', seed=71):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(14):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), -0.05))
        _blade(b, p, rnd.uniform(1.0, 1.7), 0.03, rnd.uniform(0.05, 0.2), a, hexc('55603a', 1.0), hexc(['a39a62', '8f9455'][k % 2], 1.0))
    return finish(b, name)

def fallen_log(name='env_log', seed=81):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.3, 0.22, 7.0, (0, 0, 0.22), hexc('5b4634'), 'body', rot=(0, 90, 0), segs=7)
    b.cyl(0.08, 0.04, 1.4, (1.5, 0.5, 0.5), hexc('4a3a2c'), 'body', rot=(50, 0, 20), segs=4)
    return finish(b, name)

BUILDERS = {
    'env_spruce_a': lambda: spruce('env_spruce_a', 1, 15.0, 3.4, 9),
    'env_spruce_b': lambda: spruce('env_spruce_b', 2, 18.0, 3.0, 11),
    'env_spruce_c': lambda: spruce('env_spruce_c', 4, 11.0, 3.0, 8),
    'env_pine_a': lambda: pine('env_pine_a', 3, 16.0),
    'env_birch_a': lambda: birch('env_birch_a', 5, 11.0),
    'env_birch_b': lambda: birch('env_birch_b', 6, 9.0),
    'env_conifer_far': conifer_far,
    'env_boulder_a': lambda: boulder('env_boulder_a', 11, (1.6, 1.2, 1.1)),
    'env_boulder_b': lambda: boulder('env_boulder_b', 12, (1.1, 0.9, 0.8)),
    'env_boulder_c': lambda: boulder('env_boulder_c', 13, (2.4, 1.8, 1.4)),
    'env_outcrop_a': outcrop,
    'env_pebbles': pebbles,
    'env_grass_tuft': grass_tuft,
    'env_grass_dry': lambda: grass_tuft('env_grass_dry', 42, 8, 0.45, True),
    'env_heather': heather,
    'env_juniper': juniper,
    'env_reeds': reeds,
    'env_log': fallen_log,
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
