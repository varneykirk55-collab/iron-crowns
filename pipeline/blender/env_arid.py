"""Arid battlefield environment set (env/arid; SW North America, Sahara / Arabia / Iran, Central-Asian deserts, Thar,
Australian interior): saguaro + prickly pear + creosote + mesquite (Americas only), umbrella thorn acacia, date palm,
tamarisk, saxaul, spinifex hummock, sparse dry bunchgrass, gravel, wind-rounded sandstone boulders, layered mesa
outcrop, low desert-scrub distance LOD.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-arid/ASSETS.md.
Run: blender -b --python pipeline/blender/env_arid.py [-- name ...]   (writes game/assets/models/env_*.glb only)
Vertex colour alpha 1 = foliage (wind sway + rounded normals in env_foliage.gdshader), 0 = wood / stone / cactus."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import common
from common import hexc, MeshBuilder
from env_nordic import G, lerpc, jit, finish, colour_faces, new_faces, _stone, _blade

SAND = [hexc('a08a6e'), hexc('987e62'), hexc('aa9476'), hexc('8e765c')]     # red-ochre sandstone (tinted per region)
DESERT_VARNISH = [hexc('4e4034'), hexc('5c4a3a')]

def limb(b, p0, p1, r0, r1, col, segs=6, alpha=0.0):
    dv = p1 - p0
    mid = (p0 + p1) * 0.5
    ry = math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)); rz = math.degrees(math.atan2(dv.y, dv.x))
    b.cyl(r0, r1, dv.length + 0.05, tuple(mid), hexc(col, alpha) if isinstance(col, str) else col, 'body', rot=(0, ry, rz), segs=segs)

def _clump(b, c, r, sq, cols, hi, rnd, seed, k, rough=0.38, sub=1):
    bm = bmesh.ops.create_icosphere(b.bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((sq[0], sq[1], sq[2], 1)))
    for v in bm['verts']:
        v.co += (v.co - c).normalized() * noise.noise(v.co * 0.8 + Vector((seed, k, 3))) * r * rough
    col = cols[k % len(cols)]
    colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(lerpc(col, hi, max(0.0, f.calc_center_median().z - c.z) / r * 0.7), rnd, 0.07, 1.0))

def _ribbed(b, p0, p1, r, col, rib, segs=10):
    """Cactus column: cylinder whose alternate vertices are pulled in -> pleated ribs, rounded top."""
    dv = p1 - p0
    ry = math.degrees(math.atan2(Vector((dv.x, dv.y, 0)).length, dv.z)); rz = math.degrees(math.atan2(dv.y, dv.x))
    rot = Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Rotation(math.radians(ry), 4, 'Y')
    bm = bmesh.ops.create_cone(b.bm, cap_ends=True, segments=segs, radius1=r, radius2=r * 0.92, depth=dv.length,
                               matrix=Matrix.Translation((p0 + p1) * 0.5) @ rot)
    vs = bm['verts']
    ax = dv.normalized()
    for i, v in enumerate(vs):
        rel = v.co - (p0 + p1) * 0.5
        along = rel.dot(ax)
        radial = rel - ax * along
        if radial.length > 1e-4:
            ang = math.atan2(radial.y, radial.x) if abs(ax.z) > 0.5 else math.atan2(radial.z, radial.y)
            k = 0.86 + 0.14 * abs(math.cos(ang * segs / 2))
            v.co = (p0 + p1) * 0.5 + ax * along + radial * k
        if along > dv.length * 0.49:          # domed tip
            v.co = (p0 + p1) * 0.5 + ax * (along + r * 0.35) + radial * 0.55
    def fc(f):
        c = f.calc_center_median()
        return jit(lerpc(col, rib, 0.5 + 0.5 * math.sin(c.x * 9.0 + c.y * 7.0)), random.Random(int(c.z * 10)), 0.05)
    colour_faces(b, new_faces(b, vs), fc)

def saguaro(name, seed, height):
    """Saguaro (Sonoran only): pleated grey-green column with 1-4 up-turned arms."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    col = hexc('4f6a3e'); rib = hexc('6c8150')
    r = 0.34
    _ribbed(b, Vector((0, 0, -0.2)), Vector((0, 0, height)), r, col, rib, segs=12)
    for k in range(rnd.randint(2, 4)):
        a = rnd.uniform(0, math.tau) if k == 0 else a + rnd.uniform(1.6, 3.2)
        z = height * rnd.uniform(0.38, 0.62)
        d = Vector((math.cos(a), math.sin(a), 0))
        elbow = Vector((0, 0, z)) + d * rnd.uniform(0.75, 1.05) + Vector((0, 0, 0.25))
        limb(b, Vector((0, 0, z)) + d * 0.1, elbow, r * 0.62, r * 0.6, col, segs=8)
        top = elbow + Vector((0, 0, rnd.uniform(1.4, height * 0.4)))
        _ribbed(b, elbow - Vector((0, 0, 0.25)), top, r * 0.66, col, rib, segs=8)
    return finish(b, name, smooth=True)

def prickly(name='env_prickly', seed=303):
    """Prickly pear (Opuntia) clump: flat oval pads stacked on pads, a few yellow-red fruit."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    pads = [(Vector((0, 0, 0.25)), 0.0, 0)]
    out = []
    while pads and len(out) < 14:
        c, a, d = pads.pop(0)
        out.append((c, a))
        if d < 2:
            for k in range(rnd.randint(1, 3)):
                a2 = a + rnd.uniform(-1.0, 1.0)
                pads.append((c + Vector((math.cos(a2) * 0.25, math.sin(a2) * 0.25, 0.4)), a2, d + 1))
    for c, a in out:
        b.sphere(0.24, tuple(c), jit(hexc('5f7a3c'), rnd, 0.06), 'body', segs=7, rings=4, scale=(1.0, 0.18, 1.3))
        bm_obj = None
    for k in range(5):
        c, a = out[rnd.randrange(len(out))]
        b.sphere(0.05, tuple(c + Vector((0, 0, 0.3))), hexc(['b8482c', 'c8a03c'][k % 2]), 'body', segs=4, rings=3)
    # rotate pads to their direction: done via random yaw of whole clump at placement; pads stay readable from all sides
    return finish(b, name, smooth=True)

def twig_shrub(name, seed, r, h, n, cols, hi, bark, alpha_core=True, flat=1.0):
    """Generic open desert shrub: a few thin grey stems fanning out from the root crown, small sparse foliage puffs
    (creosote, saltbush, saxaul, tamarisk)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = k * 2.39996 + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        tip = d * r * rnd.uniform(0.5, 1.0) + Vector((0, 0, h * rnd.uniform(0.6, 1.0)))
        limb(b, Vector((0, 0, -0.05)), tip, 0.05, 0.02, bark, segs=4)
        _clump(b, tip, r * rnd.uniform(0.32, 0.45), (1.0, 1.0, 0.8 * flat), cols, hi, rnd, seed, k, rough=0.5, sub=1)
    return finish(b, name, smooth=True)

def mesquite(name='env_mesquite', seed=311, height=6.0):
    """Mesquite / palo verde: low multi-stemmed tree, dark twisted trunks, wide airy pale-green crown of small puffs."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('5a6a38', 1.0), hexc('66763e', 1.0), hexc('4e5e32', 1.0)]; hi = hexc('a0a868', 1.0)
    k = 0
    for s in range(3):
        a = s * 2.1 + rnd.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        p1 = d * 1.2 + Vector((0, 0, height * 0.4))
        limb(b, Vector((0, 0, -0.1)), p1, 0.2, 0.13, '3e2e22')
        for t in range(3):
            a2 = a + rnd.uniform(-0.9, 0.9)
            p2 = p1 + Vector((math.cos(a2), math.sin(a2), 0)) * rnd.uniform(1.4, 2.6) + Vector((0, 0, height * rnd.uniform(0.25, 0.45)))
            limb(b, p1, p2, 0.12, 0.05, '46362a', segs=5)
            _clump(b, p2, rnd.uniform(1.0, 1.4), (1.3, 1.3, 0.55), cols, hi, rnd, seed, k, rough=0.5); k += 1
    return finish(b, name, smooth=True)

def acacia(name, seed, height, width):
    """Umbrella thorn acacia (A. tortilis / raddiana; also stands in for mulga + khejri): forked dark trunk, flat
    spreading crown built from wide thin pads."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('4a5a2c', 1.0), hexc('56662f', 1.0), hexc('40522a', 1.0)]; hi = hexc('8a9450', 1.0)
    fork = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), height * 0.35))
    limb(b, Vector((0, 0, -0.1)), fork, 0.26, 0.2, '3a2c22', segs=6)
    k = 0
    for s in range(4):
        a = s * 1.57 + rnd.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        p2 = fork + d * width * rnd.uniform(0.25, 0.4) + Vector((0, 0, height * rnd.uniform(0.45, 0.58)))
        limb(b, fork, p2, 0.16, 0.07, '3e3024', segs=5)
        for t in range(2):
            a2 = a + rnd.uniform(-0.6, 0.6)
            c = p2 + Vector((math.cos(a2), math.sin(a2), 0)) * rnd.uniform(0.3, 1.3) + Vector((0, 0, rnd.uniform(-0.1, 0.3)))
            _clump(b, c, width * rnd.uniform(0.2, 0.26), (1.0, 1.0, 0.22), cols, hi, rnd, seed, k, rough=0.35); k += 1
    return finish(b, name, smooth=True)

def date_palm(name, seed, height):
    """Date palm (oases / coasts of N Africa, Arabia, Mesopotamia, Indus): stout scaly trunk with a slight curve,
    dense crown of stiff arching fronds, hanging orange date bunches."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized() * height * 0.08
    prev = Vector((0, 0, -0.2)); segs = 5
    for i in range(segs):
        u = (i + 1) / segs
        p = lean * u * u + Vector((0, 0, height * u))
        limb(b, prev, p, 0.36 - u * 0.06, 0.32 - u * 0.06, '7a6248' if i % 2 else '6a5440', segs=7)
        prev = p
    top = prev
    for k in range(16):
        a = k * 2.39996
        up = 0.75 if k < 6 else 0.25
        L = rnd.uniform(3.2, 4.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        pv = None
        for i in range(5):
            u = i / 4
            p = top + d * L * u + Vector((0, 0, L * (up * u - 0.75 * u * u)))
            w = 0.42 * math.sin(math.pi * min(0.97, 0.12 + u * 0.88)) + 0.03
            l = b.bm.verts.new(p - side * w); r = b.bm.verts.new(p + side * w); m = b.bm.verts.new(p + Vector((0, 0, w * 0.35)))
            if pv:
                for q in ((pv[0], l, m, pv[2]), (pv[2], m, r, pv[1])):
                    f = b.bm.faces.new(q); f[b.mat_layer] = 0
                    for lp in f.loops:
                        lp[b.col] = jit(lerpc(hexc('3e5430', 1.0), hexc('8a9a5a', 1.0), u), rnd, 0.05, 1.0)
            pv = (l, r, m)
    for k in range(3):
        a = rnd.uniform(0, math.tau)
        b.sphere(0.28, tuple(top + Vector((math.cos(a) * 0.45, math.sin(a) * 0.45, -0.6))), hexc('b0602a'), 'body', segs=5, rings=3, scale=(1, 1, 1.5))
    return finish(b, name, smooth=True)

def spinifex(name='env_spinifex', seed=341):
    """Spinifex hummock (Australian interior): low dome-ring of stiff spiky grey-green blades."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(34):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.0, 0.7)
        p = Vector((math.cos(a) * d, math.sin(a) * d, -0.02))
        _blade(b, p, rnd.uniform(0.35, 0.6), 0.04, rnd.uniform(0.2, 0.45), a, hexc(['8a8a52', '7e8250', '969060'][k % 3], 1.0), hexc('d2c890', 1.0))
    return finish(b, name)

def dry_tuft(name='env_dry_tuft', seed=351):
    """Sparse desert bunchgrass (galleta / tobosa / aristida / drinn): a few pale straw blades."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(7):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), -0.02))
        _blade(b, p, 0.42 * rnd.uniform(0.6, 1.15), 0.03, rnd.uniform(0.15, 0.4), a,
               hexc(['8a7c4c', '7c7046', '948654'][k % 3], 1.0), hexc('d4c48c', 1.0))
    return finish(b, name)

def gravel(name='env_gravel', seed=361):
    """Desert pavement: a scatter of small wind-polished dark-varnished stones."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(7):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0, 0.8)
        s = rnd.uniform(0.07, 0.18)
        _stone(b, (math.cos(a) * d, math.sin(a) * d, 0), (s, s * 0.9, s * 0.55), rnd, seed + k, subdiv=1, pal=SAND[:2] + DESERT_VARNISH, moss=[], moss_p=0.0, crev='4a3424')
    return finish(b, name)

def sandstone(name, seed, size):
    """Wind-rounded sandstone boulder: soft rounded mass, faint horizontal bedding bands, dark desert varnish below."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, subdiv=2, flat=0.7, rough=0.22, pal=SAND, moss=[], moss_p=0.0, crev='5a4a3a')
    _bands(b, size[2])
    return finish(b, name, smooth=True)

def _bands(b, h):
    lay = [hexc('b8a080'), hexc('987a5c'), hexc('a88c6c'), hexc('8a6c50')]
    for f in b.bm.faces:
        z = f.calc_center_median().z
        k = int((z + 10.0) / max(h * 0.22, 0.25)) % len(lay)
        for l in f.loops:
            c = l[b.col]
            m = lay[k]
            l[b.col] = (c[0] * 0.6 + m[0] * 0.4, c[1] * 0.6 + m[1] * 0.4, c[2] * 0.6 + m[2] * 0.4, c[3])

def mesa_outcrop(name='env_mesa_outcrop', seed=371):
    """Layered sandstone butte ~11 x 8 x 6 m: stacked flat cap-rock slabs over a talus apron of fallen blocks."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=SAND, moss=[], moss_p=0.0, crev='54463a')
    z = -0.4
    w = 4.4
    for k in range(4):
        hgt = rnd.uniform(1.0, 1.6)
        _stone(b, (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.3, 0.3), z + hgt * 0.5), (w, w * 0.72, hgt * 0.7), rnd, seed + k, subdiv=2, flat=0.6, rough=0.18, **kw)
        z += hgt * 0.95; w *= rnd.uniform(0.78, 0.9)
    for k in range(7):
        a = rnd.uniform(0, math.tau)
        s = rnd.uniform(0.4, 1.0)
        _stone(b, (math.cos(a) * 5.6, math.sin(a) * 4.2, 0), (s, s * 0.8, s * 0.6), rnd, seed + 9 + k, subdiv=1, **kw)
    _bands(b, 6.0)
    return finish(b, name)

def poplar(name='env_poplar', seed=391, height=14.0):
    """Euphrates / Lombardy-type poplar (Central-Asian + Iranian oases, N China loess plain, Mesopotamia): pale grey
    trunk, tall narrow column of grey-green leaf clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    limb(b, Vector((0, 0, -0.2)), Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), height * 0.9)), 0.3, 0.1, '8a8478', segs=6)
    cols = [hexc('4e6234', 1.0), hexc('5a6c3a', 1.0), hexc('46582e', 1.0)]; hi = hexc('a2ac76', 1.0)
    for k in range(11):
        u = 0.25 + 0.7 * k / 10
        w = 1.0 + 1.2 * math.sin(math.pi * min(1.0, u * 1.1))
        a = k * 2.39996
        c = Vector((math.cos(a) * w * 0.35, math.sin(a) * w * 0.35, height * u))
        _clump(b, c, w * 0.8, (1.0, 1.0, 1.5), cols, hi, rnd, seed, k, rough=0.4)
    return finish(b, name, smooth=True)

def arid_far(name='env_arid_far'):
    """Distance LOD: low flat-topped scrub tree (acacia / mesquite silhouette) - short trunk + flattened dome."""
    b = MeshBuilder(name, G)
    b.cyl(0.25, 0.15, 3.0, (0, 0, 1.5), hexc('3e3024'), 'body', segs=4)
    b.sphere(3.0, (0, 0, 3.4), hexc('56623a', 1.0), 'body', segs=6, rings=3, scale=(1.0, 1.0, 0.4))
    return finish(b, name)

CREOSOTE = [hexc('4e5c2e', 1.0), hexc('5a6834', 1.0), hexc('465428', 1.0)]
SALT = [hexc('7a826a', 1.0), hexc('868c72', 1.0), hexc('707a62', 1.0)]
TAMARISK = [hexc('6a7a5a', 1.0), hexc('7a8462', 1.0), hexc('8a7a72', 1.0)]
SAXAUL = [hexc('6a7448', 1.0), hexc('5e6a40', 1.0)]

BUILDERS = {
    'env_saguaro_a': lambda: saguaro('env_saguaro_a', 301, 9.0),
    'env_saguaro_b': lambda: saguaro('env_saguaro_b', 302, 6.5),
    'env_prickly': prickly,
    'env_creosote': lambda: twig_shrub('env_creosote', 321, 0.9, 1.5, 7, CREOSOTE, hexc('9aa45a', 1.0), '4a3e30'),
    'env_saltbush': lambda: twig_shrub('env_saltbush', 322, 0.8, 0.8, 6, SALT, hexc('b4b89a', 1.0), '6a604e', flat=0.7),
    'env_tamarisk': lambda: twig_shrub('env_tamarisk', 323, 1.4, 2.6, 9, TAMARISK, hexc('c0a0a0', 1.0), '5a4438'),
    'env_saxaul': lambda: twig_shrub('env_saxaul', 324, 1.2, 1.9, 6, SAXAUL, hexc('a4ac6c', 1.0), '7a7266', flat=0.6),
    'env_mesquite': mesquite,
    'env_acacia_a': lambda: acacia('env_acacia_a', 331, 6.5, 9.0),
    'env_acacia_b': lambda: acacia('env_acacia_b', 332, 4.8, 7.0),
    'env_date_palm': lambda: date_palm('env_date_palm', 341, 11.0),
    'env_spinifex': spinifex,
    'env_dry_tuft': dry_tuft,
    'env_gravel': gravel,
    'env_sandstone_a': lambda: sandstone('env_sandstone_a', 381, (1.5, 1.2, 1.0)),
    'env_sandstone_b': lambda: sandstone('env_sandstone_b', 382, (0.9, 0.8, 0.6)),
    'env_sandstone_c': lambda: sandstone('env_sandstone_c', 383, (2.3, 1.8, 1.6)),
    'env_mesa_outcrop': mesa_outcrop,
    'env_arid_far': arid_far,
    'env_poplar': poplar,
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
