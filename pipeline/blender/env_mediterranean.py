"""Mediterranean battlefield environment set (env/mediterranean; the Med basin, California, central Chile, southern
Australia): umbrella stone pine, Italian cypress, gnarled olive, holm oak (also coast live oak / peumo), deciduous
downy oak (Balkan / Anatolian interior), Aleppo / black pine, eucalypt, maquis / chaparral shrub, low garrigue
cushions (lavender / thyme / rosemary), summer-dry grass tuft, pale limestone boulders + a layered karst outcrop, a
far-LOD evergreen crown.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-mediterranean/ASSETS.md.
Run: blender -b --python pipeline/blender/env_mediterranean.py [-- name ...]   (writes game/assets/models/env_*.glb only)
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

PINE = [hexc('3c4c24', 1.0), hexc('44542a', 1.0), hexc('364620', 1.0)]
PINE_HI = hexc('5a6a34', 1.0)

def stone_pine(name='env_stone_pine', seed=301, height=13.0):
    """Umbrella / stone pine (Pinus pinea): a bare, slightly leaning red-brown trunk forking high into a few limbs
    under a broad, dense, flat-bottomed dome of dark needle clouds."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('6a4a36'); bark2 = hexc('5a3e2e')
    lean = Vector((0.6, 0.2, 0))
    fork = Vector((0, 0, height * 0.6)) + lean
    _limb(b, Vector((0, 0, -0.2)), fork, 0.34, 0.26, bark, segs=6)
    for k in range(5):
        a = k / 5 * math.tau + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        tip = fork + d * rnd.uniform(2.4, 3.6) + Vector((0, 0, height * rnd.uniform(0.16, 0.24)))
        _limb(b, fork, tip, 0.18, 0.09, bark2, segs=4)
        _clump(b, tip + Vector((0, 0, 0.5)), rnd.uniform(2.0, 2.6), (1.5, 1.5, 0.5), PINE, PINE_HI, rnd, seed, k, rough=0.3)
    _clump(b, fork + Vector((0, 0, height * 0.3)), 3.0, (1.6, 1.6, 0.42), PINE, PINE_HI, rnd, seed, 9, rough=0.25)
    return finish(b, name, smooth=True)

def cypress(name='env_cypress', seed=311, height=14.0):
    """Italian cypress (Cupressus sempervirens 'Stricta'): a tall, narrow, dense dark-green flame column."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.2, 0.14, height * 0.2, (0, 0, height * 0.1), hexc('4a3a2c'), 'body', segs=5)
    cols = [hexc('26341a', 1.0), hexc('2c3c1e', 1.0), hexc('223018', 1.0)]; hi = hexc('46582c', 1.0)
    n = 6
    for k in range(n):
        t = k / (n - 1)
        r = 1.05 * (1.0 - t * 0.72)
        z = height * (0.12 + t * 0.78)
        _clump(b, Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), z)), r, (1.0, 1.0, 2.0), cols, hi, rnd, seed, k, rough=0.22)
    return finish(b, name, smooth=True)

OLIVE = [hexc('5f6a48', 1.0), hexc('6a7452', 1.0), hexc('56603f', 1.0)]
OLIVE_HI = hexc('9aa080', 1.0)

def olive(name, seed, height, width):
    """Olive tree: a short, thick, twisted and split grey trunk dividing into 2-3 leaning limbs; a broad, loose,
    silvery grey-green crown of separate clumps (orchard-pruned, so the crown is open in the middle)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('6a6458'); bark2 = hexc('5a554a')
    b.cyl(0.42, 0.34, 0.9, (0, 0, 0.35), bark, 'body', segs=7)
    nl = 3
    for k in range(nl):
        a = k / nl * math.tau + rnd.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        p1 = Vector((0, 0, 0.7)) + d * rnd.uniform(0.5, 0.9) + Vector((0, 0, height * 0.28))
        _limb(b, Vector((0, 0, 0.6)), p1, 0.24, 0.16, bark2, segs=5)
        for j in range(2):
            a2 = a + rnd.uniform(-0.8, 0.8)
            c = p1 + Vector((math.cos(a2), math.sin(a2), 0)) * width * rnd.uniform(0.15, 0.3) + Vector((0, 0, height * rnd.uniform(0.25, 0.42)))
            _limb(b, p1, c, 0.12, 0.05, bark2, segs=4)
            _clump(b, c, rnd.uniform(1.2, 1.6), (1.3, 1.3, 0.8), OLIVE, OLIVE_HI, rnd, seed, k * 2 + j, rough=0.45)
    return finish(b, name, smooth=True)

def holm_oak(name='env_holm_oak', seed=331, height=10.0, width=10.0):
    """Holm oak / cork oak (Quercus ilex / suber; also coast live oak in California and peumo / quillay in Chile):
    a short stout trunk under a dense, dark, rounded evergreen crown, low and wide."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('4a4038'); bark2 = hexc('40372f')
    b.cyl(0.38, 0.28, height * 0.4, (0, 0, height * 0.2), bark, 'body', segs=6)
    cols = [hexc('3e4c24', 1.0), hexc('46542a', 1.0), hexc('384620', 1.0), hexc('4c5a2e', 1.0)]; hi = hexc('76804a', 1.0)
    for k in range(9):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.1, 1.0) * width * 0.34
        c = Vector((math.cos(a) * d, math.sin(a) * d, height * rnd.uniform(0.5, 0.82)))
        if k < 4:
            _limb(b, Vector((0, 0, height * 0.36)), c, 0.18, 0.08, bark2, segs=4)
        _clump(b, c, rnd.uniform(2.0, 2.6), (1.25, 1.25, 0.8), cols, hi, rnd, seed, k, rough=0.36)
    return finish(b, name, smooth=True)

def oak_dec(name='env_oak_dec', seed=341, height=13.0, width=10.0):
    """Deciduous downy / Turkey oak (Quercus pubescens / cerris; Balkan and Anatolian hills): taller and more open
    than the holm oak, a fresher mid green, lobed crown of loose clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('5a5046'); bark2 = hexc('4c443a')
    b.cyl(0.36, 0.24, height * 0.55, (0, 0, height * 0.275), bark, 'body', segs=6)
    cols = [hexc('4a5a26', 1.0), hexc('54642c', 1.0), hexc('445224', 1.0)]; hi = hexc('7a8644', 1.0)
    for k in range(10):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.15, 1.0) * width * 0.36
        c = Vector((math.cos(a) * d, math.sin(a) * d, height * rnd.uniform(0.55, 0.92)))
        if k < 5:
            _limb(b, Vector((0, 0, height * 0.45)), c, 0.16, 0.06, bark2, segs=4)
        _clump(b, c, rnd.uniform(1.6, 2.2), (1.2, 1.2, 0.9), cols, hi, rnd, seed, k, rough=0.42)
    return finish(b, name, smooth=True)

def aleppo_pine(name='env_aleppo_pine', seed=351, height=12.0):
    """Aleppo / Calabrian pine (Pinus halepensis; also black pine and Californian grey pine with a tint): a crooked,
    leaning grey trunk with irregular, open tiers of lighter needle clumps; you see sky through the crown."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('6a6056'); bark2 = hexc('5a5249')
    p0 = Vector((0, 0, -0.2)); p1 = Vector((0.5, 0.1, height * 0.45)); p2 = Vector((0.2, 0.8, height * 0.85))
    _limb(b, p0, p1, 0.3, 0.22, bark, segs=6); _limb(b, p1, p2, 0.22, 0.12, bark, segs=5)
    cols = [hexc('46552a', 1.0), hexc('4e5e30', 1.0), hexc('3e4c26', 1.0)]; hi = hexc('74823e', 1.0)
    for k in range(7):
        t = rnd.uniform(0.35, 1.0)
        base = p0.lerp(p1, min(1.0, t * 2)) if t < 0.5 else p1.lerp(p2, (t - 0.5) * 2)
        a = rnd.uniform(0, math.tau)
        c = base + Vector((math.cos(a), math.sin(a), 0)) * rnd.uniform(1.4, 2.8) + Vector((0, 0, rnd.uniform(0.3, 1.0)))
        _limb(b, base, c, 0.1, 0.05, bark2, segs=3)
        _clump(b, c, rnd.uniform(1.2, 1.7), (1.4, 1.4, 0.6), cols, hi, rnd, seed, k, rough=0.42)
    return finish(b, name, smooth=True)

def eucalypt(name='env_eucalypt', seed=361, height=18.0):
    """Eucalypt (river red gum / mallee-type, southern Australia; also planted in California, Chile and Iberia): tall
    pale, smooth, peeling cream-grey trunk forking into crooked limbs; a sparse, open, drooping blue-grey-green
    crown of vertically elongated clumps."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('9a9282'); bark2 = hexc('847c6e')
    fork = Vector((0.3, 0.0, height * 0.42))
    _limb(b, Vector((0, 0, -0.2)), fork, 0.42, 0.3, bark, segs=6)
    b.cyl(0.5, 0.42, 0.8, (0, 0, 0.2), hexc('7a6e5e'), 'body', segs=6)
    cols = [hexc('56624a', 1.0), hexc('5e6a50', 1.0), hexc('4e5a44', 1.0)]; hi = hexc('8a9478', 1.0)
    for k in range(4):
        a = k / 4 * math.tau + rnd.uniform(-0.4, 0.4)
        d = Vector((math.cos(a), math.sin(a), 0))
        p1 = fork + d * rnd.uniform(1.8, 3.0) + Vector((0, 0, height * rnd.uniform(0.2, 0.3)))
        _limb(b, fork, p1, 0.2, 0.1, bark2, segs=4)
        for j in range(2):
            c = p1 + Vector((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), rnd.uniform(0.5, 2.5)))
            _limb(b, p1, c, 0.08, 0.04, bark2, segs=3)
            _clump(b, c, rnd.uniform(1.3, 1.8), (1.0, 1.0, 1.3), cols, hi, rnd, seed, k * 2 + j, rough=0.5)
    return finish(b, name, smooth=True)

def maquis(name='env_maquis', seed=371):
    """Maquis / chaparral / matorral shrub (lentisk, myrtle, kermes oak, chamise): a dense, dark, glossy rounded
    clump ~1.6 m tall, several overlapping lobes."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('44502a', 1.0), hexc('4c582e', 1.0), hexc('3e4a26', 1.0)]; hi = hexc('76804a', 1.0)
    for k in range(4):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.1, 0.7)
        c = Vector((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.5, 0.9)))
        _clump(b, c, rnd.uniform(0.6, 0.85), (1.2, 1.2, 0.9), cols, hi, rnd, seed, k, rough=0.4)
    return finish(b, name, smooth=True)

def garrigue(name='env_garrigue', seed=381):
    """Garrigue cushions (lavender, thyme, rosemary, rock-rose): a low knot of grey-green domes ~0.5 m with a few
    lavender-purple flower tips."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('6a7058', 1.0), hexc('747a60', 1.0), hexc('5e6650', 1.0)]; hi = hexc('9a9a80', 1.0)
    for k in range(4):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.1, 0.6)
        c = Vector((math.cos(a) * d, math.sin(a) * d, 0.12))
        _clump(b, c, rnd.uniform(0.3, 0.42), (1.3, 1.3, 0.75), cols, hi, rnd, seed, k, rough=0.35)
    for k in range(6):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.0, 0.6)
        p = Vector((math.cos(a) * d, math.sin(a) * d, 0.2))
        _blade(b, p, rnd.uniform(0.3, 0.45), 0.03, 0.05, a, hexc('6a7058', 1.0), hexc('8a6aa0', 1.0))
    return finish(b, name, smooth=True)

def med_grass(name='env_med_grass', seed=391, n=10, h=0.5):
    """Mediterranean annual grass tuft (wild oats / bromes): fine blades that are green in the wet winter-spring and
    sun-bleached straw by summer (the biome tints it per season); a few seed-head tips."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.13, 0.13), rnd.uniform(-0.13, 0.13), -0.02))
        col = hexc(['7a7a44', '6e7040', '84804a'][k % 3], 1.0); tip = hexc(['c8bc80', 'bab070', 'd4c88e'][k % 3], 1.0)
        _blade(b, p, h * rnd.uniform(0.6, 1.3), 0.03, rnd.uniform(0.15, 0.4), a, col, tip)
    return finish(b, name)

LIME = [hexc('b4ac9c'), hexc('a8a090'), hexc('bcb4a4'), hexc('9e978a')]
LIME_LICHEN = [hexc('9a9478'), hexc('8a846c'), hexc('a8a088')]

def limestone(name, seed, size):
    """Pale karst limestone block: angular, flat-topped, fissured."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, flat=0.55, rough=0.32, pal=LIME, moss=LIME_LICHEN, moss_p=0.25, crev='6e6658')
    if seed % 2 == 0:
        _stone(b, (size[0] * 1.0, size[1] * 0.5, 0), (size[0] * 0.45, size[1] * 0.4, size[2] * 0.45), rnd, seed + 7, subdiv=1, flat=0.5, rough=0.3, pal=LIME, moss=[], moss_p=0.0, crev='6e6658')
    return finish(b, name)

def karst(name='env_karst', seed=401):
    """Karst limestone outcrop (~11 x 7 x 4 m): stepped, bedded ledges of pale grey-cream rock with fissures, loose
    blocks at the foot (Dalmatian / Provençal / Greek hill-side)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=LIME, moss=LIME_LICHEN, moss_p=0.25, crev='6e6658')
    _stone(b, (0, 0, -0.3), (5.4, 3.6, 1.6), rnd, seed, subdiv=3, flat=0.45, rough=0.22, **kw)
    _stone(b, (0.8, 0.4, 1.3), (3.6, 2.4, 1.4), rnd, seed + 1, subdiv=2, flat=0.4, rough=0.24, **kw)
    _stone(b, (1.4, 0.6, 2.6), (2.0, 1.4, 1.0), rnd, seed + 2, subdiv=2, flat=0.4, rough=0.24, **kw)
    for k in range(4):
        a = rnd.uniform(0, math.tau)
        _stone(b, (math.cos(a) * 5.8, math.sin(a) * 4.0, 0), (rnd.uniform(0.5, 0.9), rnd.uniform(0.4, 0.7), rnd.uniform(0.3, 0.6)), rnd, seed + 5 + k, subdiv=1, flat=0.5, rough=0.3, **kw)
    return finish(b, name)

def med_far(name='env_med_far'):
    """Distance LOD for evergreen woods / olive groves (~40 tris): a short trunk under a rounded dark crown."""
    rnd = random.Random(7)
    b = MeshBuilder(name, G)
    b.cyl(0.3, 0.22, 4.0, (0, 0, 2.0), hexc('4a4038'), 'body', segs=4)
    _clump(b, Vector((0, 0, 5.6)), 3.2, (1.25, 1.25, 0.8), [hexc('4c5a2e', 1.0)], hexc('76824a', 1.0), rnd, 3, 0, rough=0.2, sub=1)
    return finish(b, name, smooth=True)

BUILDERS = {
    'env_stone_pine': stone_pine,
    'env_cypress': cypress,
    'env_olive_a': lambda: olive('env_olive_a', 321, 6.0, 8.0),
    'env_olive_b': lambda: olive('env_olive_b', 322, 4.8, 6.5),
    'env_holm_oak': holm_oak,
    'env_oak_dec': oak_dec,
    'env_aleppo_pine': aleppo_pine,
    'env_eucalypt': eucalypt,
    'env_maquis': maquis,
    'env_garrigue': garrigue,
    'env_med_grass': med_grass,
    'env_limestone_a': lambda: limestone('env_limestone_a', 411, (1.5, 1.2, 1.0)),
    'env_limestone_b': lambda: limestone('env_limestone_b', 412, (2.3, 1.8, 1.4)),
    'env_karst': karst,
    'env_med_far': med_far,
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
