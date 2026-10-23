"""Savanna battlefield environment set (env/savanna; East / southern African bushveld, miombo woodland, Guinea
savanna and Sahel, the Deccan, cerrado / campos): flat-topped umbrella thorn, baobab, miombo / dry-deciduous
woodland tree, candelabra euphorbia, thorn scrub, tall golden bunchgrass, laterite termite mounds, rounded granite
kopje boulders + kopje outcrop, a far-LOD bushveld crown.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-savanna/ASSETS.md.
Run: blender -b --python pipeline/blender/env_savanna.py [-- name ...]   (writes game/assets/models/env_*.glb only)
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

def _limb(b, p0, p1, r0, r1, col, segs=5):
    d = p1 - p0
    rot_y = math.degrees(math.atan2(Vector((d.x, d.y, 0)).length, d.z)); rot_z = math.degrees(math.atan2(d.y, d.x))
    b.cyl(r0, r1, d.length, tuple((p0 + p1) * 0.5), col, 'body', rot=(0, rot_y, rot_z), segs=segs)

def umbrella_thorn(name, seed, height, width):
    """Umbrella thorn (Vachellia tortilis type): short forked trunk, a few long up-and-out limbs carrying a very flat,
    wide, thin crown of separate pads, so the sky shows through between them."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('4a3f34'); bark2 = hexc('3d342b')
    fork = height * 0.32
    b.cyl(0.26, 0.2, fork, (0, 0, fork / 2), bark, 'body', segs=6)
    cols = [hexc('4a5a26', 1.0), hexc('55642c', 1.0), hexc('3f5022', 1.0), hexc('5d6a30', 1.0)]
    hi = hexc('8a9446', 1.0)
    nl = 5
    for k in range(nl):
        a = k / nl * math.tau + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        tip = d * width * rnd.uniform(0.28, 0.42) + Vector((0, 0, height * rnd.uniform(0.82, 0.92)))
        _limb(b, Vector((0, 0, fork - 0.2)), tip, 0.13, 0.06, bark2, segs=4)
        for j in range(2):
            c = tip + Vector((rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), rnd.uniform(0.1, 0.5)))
            _clump(b, c, rnd.uniform(1.6, 2.2), (1.6, 1.6, 0.34), cols, hi, rnd, seed, k * 2 + j, rough=0.32)
    _clump(b, Vector((0, 0, height * 0.95)), 2.0, (1.7, 1.7, 0.32), cols, hi, rnd, seed, 30, rough=0.3)
    return finish(b, name, smooth=True)

def baobab(name='env_baobab', seed=211, height=14.0):
    """Baobab: a huge swollen bottle trunk (~7 m girth), short stubby root-like branches, sparse small leaf clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('8a7a6a'); bark2 = hexc('7a6c5e')
    th = height * 0.66
    b.cyl(2.3, 1.5, th, (0, 0, th / 2), bark, 'body', segs=9)
    b.cyl(2.6, 2.3, 1.2, (0, 0, 0.5), bark2, 'body', segs=9)
    cols = [hexc('4f6a2a', 1.0), hexc('5a7430', 1.0), hexc('466024', 1.0)]
    for k in range(7):
        a = k / 7 * math.tau + rnd.uniform(-0.25, 0.25)
        d = Vector((math.cos(a), math.sin(a), 0))
        p0 = Vector((0, 0, th - 0.4)) + d * 0.9
        p1 = p0 + d * rnd.uniform(2.6, 4.2) + Vector((0, 0, rnd.uniform(1.8, 3.2)))
        _limb(b, p0, p1, 0.5, 0.18, bark2, segs=5)
        p2 = p1 + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.8, 1.5)))
        _limb(b, p1, p2, 0.18, 0.08, bark2, segs=4)
        _clump(b, p2 + Vector((0, 0, 0.3)), rnd.uniform(1.1, 1.5), (1.3, 1.3, 0.75), cols, hexc('8aa04a', 1.0), rnd, seed, k, rough=0.4)
    return finish(b, name, smooth=True)

def miombo(name, seed, height, width, cols, hi):
    """Miombo / dry-deciduous woodland tree (Brachystegia; also stands in for teak / sal in the Deccan): straight grey
    trunk, an open, slightly flattened rounded crown of loose clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('5a5248'); bark2 = hexc('4a433a')
    b.cyl(0.3, 0.2, height * 0.62, (0, 0, height * 0.31), bark, 'body', segs=6)
    for k in range(9):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.2, 1.0) * width * 0.42
        z = height * rnd.uniform(0.66, 0.92)
        c = Vector((math.cos(a) * d, math.sin(a) * d, z))
        if k < 4:
            _limb(b, Vector((0, 0, height * 0.55)), c, 0.14, 0.06, bark2, segs=4)
        _clump(b, c, rnd.uniform(1.8, 2.5), (1.3, 1.3, 0.72), cols, hi, rnd, seed, k, rough=0.42)
    return finish(b, name, smooth=True)

def euphorbia(name='env_euphorbia', seed=231, height=7.0):
    """Candelabra euphorbia: a short trunk with a dense bowl of upcurving, ribbed succulent green branches."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    trunk = hexc('5a5040'); g = hexc('4e6a34', 1.0); g2 = hexc('5f7a3a', 1.0)
    b.cyl(0.32, 0.26, height * 0.35, (0, 0, height * 0.175), trunk, 'body', segs=6)
    base = Vector((0, 0, height * 0.33))
    for k in range(11):
        a = k / 11 * math.tau + rnd.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        out = rnd.uniform(0.9, 1.9)
        p1 = base + d * out + Vector((0, 0, rnd.uniform(0.2, 0.5)))
        p2 = p1 + d * 0.15 + Vector((0, 0, height * rnd.uniform(0.4, 0.6)))
        _limb(b, base, p1, 0.16, 0.14, g, segs=4)
        _limb(b, p1, p2, 0.15, 0.1, g2 if k % 2 else g, segs=5)
    return finish(b, name, smooth=True)

def thornbush(name='env_thornbush', seed=241):
    """Low thorn scrub / sickle-bush clump (~1.8 m): twiggy stems under a few flat, grey-green leaf masses."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('4a3e32')
    cols = [hexc('5a6430', 1.0), hexc('4c5a2a', 1.0), hexc('66703a', 1.0)]
    for k in range(5):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.2, 0.9)
        c = Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.9, 1.5)))
        _limb(b, Vector((0, 0, 0)), c, 0.05, 0.03, bark, segs=3)
        _clump(b, c, rnd.uniform(0.6, 0.85), (1.4, 1.4, 0.6), cols, hexc('94984e', 1.0), rnd, seed, k, rough=0.45)
    return finish(b, name, smooth=True)

def sav_grass(name='env_sav_grass', seed=251, n=12, h=0.85):
    """Tall savanna bunchgrass (red oat grass / thatching grass): fine golden blades, knee- to thigh-high."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.14, 0.14), rnd.uniform(-0.14, 0.14), -0.02))
        col = hexc(['8a7a40', '7a6c38', '948446'][k % 3], 1.0); tip = hexc(['d8c27a', 'cfb46a', 'e0cc8a'][k % 3], 1.0)
        _blade(b, p, h * rnd.uniform(0.6, 1.25), 0.035, rnd.uniform(0.2, 0.5), a, col, tip)
    return finish(b, name)

def termite_mound(name, seed, height):
    """Laterite termite mound: a lumpy red-earth cone with a couple of chimney spires."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    earth = [hexc('9a5a36'), hexc('8a5030'), hexc('a2643c')]
    _stone(b, (0, 0, 0), (1.3, 1.2, height * 0.45), rnd, seed, subdiv=2, flat=1.0, rough=0.22, pal=earth, moss=[], moss_p=0.0, crev='6a3a22')
    for k in range(2):
        o = Vector((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0))
        hh = height * rnd.uniform(0.7, 1.0)
        b.cyl(0.45, 0.12, hh, (o.x, o.y, hh / 2), earth[k], 'body', segs=6)
    return finish(b, name)

GRANITE = [hexc('8a8278'), hexc('7e776e'), hexc('948c80'), hexc('767068')]
LICHEN = [hexc('8a8a6a'), hexc('7a6e58'), hexc('9a8f6a')]

def kopje_boulder(name, seed, size):
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, flat=0.9, rough=0.18, pal=GRANITE, moss=LICHEN, moss_p=0.35, crev='5a544c')
    return finish(b, name)

def kopje(name='env_kopje', seed=261):
    """Kopje / inselberg pile: big rounded exfoliating granite boulders stacked on a low dome (~10 x 8 x 6 m)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=GRANITE, moss=LICHEN, moss_p=0.35, crev='5a544c')
    _stone(b, (0, 0, -0.6), (5.0, 4.0, 1.8), rnd, seed, subdiv=3, flat=0.7, rough=0.14, **kw)
    for k, (p, s) in enumerate([((0.6, 0.2, 1.6), (2.4, 2.0, 2.1)), ((-2.2, -0.8, 1.1), (1.8, 1.6, 1.6)),
                                ((2.6, -1.4, 0.9), (1.6, 1.4, 1.4)), ((0.2, 0.4, 3.8), (1.4, 1.2, 1.3)), ((-0.6, 2.2, 0.8), (1.3, 1.2, 1.1))]):
        _stone(b, p, s, rnd, seed + k + 1, subdiv=2, flat=0.9, rough=0.16, **kw)
    return finish(b, name)

def sav_far(name='env_sav_far'):
    """Distance LOD for bushveld / woodland belts (~40 tris): a thin trunk under a flat-topped crown."""
    rnd = random.Random(9)
    b = MeshBuilder(name, G)
    b.cyl(0.3, 0.22, 5.0, (0, 0, 2.5), hexc('4a3f34'), 'body', segs=4)
    _clump(b, Vector((0, 0, 6.0)), 3.6, (1.4, 1.4, 0.4), [hexc('4a5a28', 1.0)], hexc('7a8a40', 1.0), rnd, 3, 0, rough=0.2, sub=1)
    return finish(b, name, smooth=True)

MIOMBO = ([hexc('4a6226', 1.0), hexc('56702c', 1.0), hexc('6a6a2c', 1.0), hexc('425a22', 1.0)], hexc('94a04a', 1.0))

BUILDERS = {
    'env_umbrella_a': lambda: umbrella_thorn('env_umbrella_a', 201, 9.0, 12.0),
    'env_umbrella_b': lambda: umbrella_thorn('env_umbrella_b', 202, 6.5, 9.0),
    'env_baobab': baobab,
    'env_miombo_a': lambda: miombo('env_miombo_a', 221, 13.0, 11.0, *MIOMBO),
    'env_miombo_b': lambda: miombo('env_miombo_b', 222, 10.0, 9.0, *MIOMBO),
    'env_euphorbia': euphorbia,
    'env_thornbush': thornbush,
    'env_sav_grass': sav_grass,
    'env_termite_a': lambda: termite_mound('env_termite_a', 271, 2.6),
    'env_termite_b': lambda: termite_mound('env_termite_b', 272, 1.8),
    'env_kopje_a': lambda: kopje_boulder('env_kopje_a', 281, (1.6, 1.4, 1.3)),
    'env_kopje_b': lambda: kopje_boulder('env_kopje_b', 282, (2.4, 2.0, 1.9)),
    'env_kopje': kopje,
    'env_sav_far': sav_far,
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
