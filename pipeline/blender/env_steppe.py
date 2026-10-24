"""Steppe battlefield environment set (env/steppe; the Kazakh / Pontic-Caspian and Central Asian steppe, the
Mongolian plateau and southern Siberian forest-steppe, the Tibetan / Pamir / Hindu Kush high steppe, the Great Plains
prairie, the Argentine / Uruguayan pampa and the dry Andean-foot monte): feather-grass tuft, wormwood and pea-shrub
scrub, Siberian larch, cottonwood / steppe poplar, the pampa ombu, weathered granite tors + a tor outcrop, a
grass-grown kurgan / khirigsuur burial mound, a far-LOD grove.
100 % procedural / original (bmesh primitives + mathutils.noise, helpers from env_nordic.py) -> no licence obligations;
see evidence/env-steppe/ASSETS.md.
Run: blender -b --python pipeline/blender/env_steppe.py [-- name ...]   (writes game/assets/models/env_*.glb only)
Vertex colour alpha 1 = foliage (wind sway + rounded normals in env_foliage.gdshader), 0 = wood / stone / earth."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, noise
import common
from common import hexc, MeshBuilder
from env_nordic import G, lerpc, jit, finish, colour_faces, new_faces, _stone, _blade

def _clump(b, c, r, sq, cols, hi, rnd, seed, k, rough=0.38, sub=1, alpha=1.0):
    bm = bmesh.ops.create_icosphere(b.bm, subdivisions=sub, radius=r, matrix=Matrix.Translation(c) @ Matrix.Diagonal((sq[0], sq[1], sq[2], 1)))
    for v in bm['verts']:
        v.co += (v.co - c).normalized() * noise.noise(v.co * 0.8 + Vector((seed, k, 3))) * r * rough
    col = cols[k % len(cols)]
    colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(lerpc(col, hi, max(0.0, f.calc_center_median().z - c.z) / r * 0.7), rnd, 0.07, alpha))

def _limb(b, p0, p1, r0, r1, col, segs=5):
    d = p1 - p0
    rot_y = math.degrees(math.atan2(Vector((d.x, d.y, 0)).length, d.z)); rot_z = math.degrees(math.atan2(d.y, d.x))
    b.cyl(r0, r1, d.length, tuple((p0 + p1) * 0.5), col, 'body', rot=(0, rot_y, rot_z), segs=segs)

def feather_grass(name='env_feather_grass', seed=501, n=12, h=0.6):
    """Feather grass (Stipa) bunch: a dense tussock of fine wiry blades with long silvery awns arching out; the biome
    tints it green in spring, tawny in summer, dormant grey-brown in winter."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    for k in range(n):
        a = rnd.uniform(0, math.tau)
        p = Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), -0.02))
        col = hexc(['7a7c4c', '72744a', '84845a'][k % 3], 1.0)
        tip = hexc(['d8d4be', 'cac6aa', 'e2dec8'][k % 3], 1.0) if k % 2 == 0 else hexc('a8a476', 1.0)
        _blade(b, p, h * rnd.uniform(0.6, 1.35), 0.025, rnd.uniform(0.25, 0.55), a, col, tip)
    return finish(b, name)

def wormwood(name='env_wormwood', seed=511):
    """Wormwood / sagebrush (Artemisia) clump ~0.5 m: low, loose, silvery grey-green domes."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    cols = [hexc('7a806a', 1.0), hexc('848a74', 1.0), hexc('707662', 1.0)]; hi = hexc('aeb29c', 1.0)
    for k in range(4):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.05, 0.45)
        _clump(b, Vector((math.cos(a) * d, math.sin(a) * d, 0.14)), rnd.uniform(0.24, 0.34), (1.3, 1.3, 0.8), cols, hi, rnd, seed, k, rough=0.45)
    return finish(b, name, smooth=True)

def pea_shrub(name='env_pea_shrub', seed=521):
    """Steppe pea-shrub / spiraea / jarilla scrub (Caragana; monte creosote in Argentina) ~1.1 m: an upright, twiggy,
    darker olive bush of several stems."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    stem = hexc('5a4c3c')
    cols = [hexc('4e5a2e', 1.0), hexc('566234', 1.0), hexc('48542a', 1.0)]; hi = hexc('7e8a4c', 1.0)
    for k in range(5):
        a = rnd.uniform(0, math.tau)
        tip = Vector((math.cos(a) * rnd.uniform(0.2, 0.5), math.sin(a) * rnd.uniform(0.2, 0.5), rnd.uniform(0.7, 1.0)))
        _limb(b, Vector((0, 0, -0.05)), tip, 0.03, 0.015, stem, segs=3)
        _clump(b, tip, rnd.uniform(0.3, 0.42), (1.0, 1.0, 1.1), cols, hi, rnd, seed, k, rough=0.5)
    return finish(b, name, smooth=True)

def larch(name='env_larch', seed=531, height=16.0):
    """Siberian larch (Larix sibirica; Mongolian / Altai north slopes): a straight trunk under an open, narrow cone of
    soft, light-green whorls (sky shows through, unlike the dense Nordic spruce)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    b.cyl(0.3, 0.08, height, (0, 0, height * 0.5), hexc('6a4c38'), 'body', segs=6)
    cols = [hexc('5a6e2e', 1.0), hexc('627634', 1.0), hexc('52662a', 1.0)]; hi = hexc('8a9a4c', 1.0)
    n = 7
    for k in range(n):
        t = k / (n - 1)
        z = height * (0.28 + t * 0.66)
        r = 2.4 * (1.0 - t * 0.8) + 0.3
        for j in range(3 if t < 0.7 else 1):
            a = rnd.uniform(0, math.tau)
            off = Vector((math.cos(a), math.sin(a), 0)) * r * 0.35 if j else Vector((0, 0, 0))
            _clump(b, Vector((0, 0, z)) + off, r * 0.55, (1.4, 1.4, 0.55), cols, hi, rnd, seed, k * 3 + j, rough=0.45)
    return finish(b, name, smooth=True)

def cottonwood(name='env_cottonwood', seed=541, height=17.0, width=12.0):
    """Plains cottonwood / steppe poplar (Populus deltoides / laurifolia; the riverside tree of the prairie and the
    Central Asian tugai): thick furrowed grey trunk forking low into heavy limbs, a broad, irregular, light-green crown."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('6e675c'); bark2 = hexc('5e584e')
    fork = Vector((0.2, 0, height * 0.32))
    _limb(b, Vector((0, 0, -0.2)), fork, 0.55, 0.42, bark, segs=7)
    cols = [hexc('54682e', 1.0), hexc('5e7234', 1.0), hexc('4c602a', 1.0)]; hi = hexc('8a9c50', 1.0)
    for k in range(4):
        a = k / 4 * math.tau + rnd.uniform(-0.4, 0.4)
        p1 = fork + Vector((math.cos(a), math.sin(a), 0)) * width * rnd.uniform(0.18, 0.3) + Vector((0, 0, height * rnd.uniform(0.25, 0.38)))
        _limb(b, fork, p1, 0.28, 0.12, bark2, segs=5)
        for j in range(2):
            c = p1 + Vector((rnd.uniform(-2, 2), rnd.uniform(-2, 2), rnd.uniform(0.5, 2.5)))
            _clump(b, c, rnd.uniform(1.9, 2.5), (1.2, 1.2, 0.95), cols, hi, rnd, seed, k * 2 + j, rough=0.42)
    return finish(b, name, smooth=True)

def ombu(name='env_ombu', seed=551, height=11.0, width=14.0):
    """Ombu (Phytolacca dioica): the lone shade tree of the treeless pampa; a massive, buttressed, swollen pale trunk
    and a wide, dense, dark umbrella crown."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bark = hexc('8a8070'); bark2 = hexc('786e60')
    b.cyl(1.6, 0.9, 1.4, (0, 0, 0.5), bark, 'body', segs=9)
    b.cyl(0.9, 0.6, height * 0.3, (0, 0, 1.2 + height * 0.15), bark, 'body', segs=8)
    top = Vector((0, 0, height * 0.42))
    cols = [hexc('3e5222', 1.0), hexc('465a28', 1.0), hexc('384c1e', 1.0)]; hi = hexc('6c7e40', 1.0)
    for k in range(7):
        a = rnd.uniform(0, math.tau); d = rnd.uniform(0.2, 1.0) * width * 0.36
        c = Vector((math.cos(a) * d, math.sin(a) * d, height * rnd.uniform(0.62, 0.84)))
        if k < 5: _limb(b, top, c, 0.32, 0.12, bark2, segs=5)
        _clump(b, c, rnd.uniform(2.4, 3.0), (1.3, 1.3, 0.6), cols, hi, rnd, seed, k, rough=0.32)
    return finish(b, name, smooth=True)

TOR = [hexc('8e8678'), hexc('847c70'), hexc('9a9282'), hexc('7a7268')]
TOR_LICHEN = [hexc('a09a5a'), hexc('8a8a5e'), hexc('b0a070')]   # orange / yellow-grey crustose lichen

def tor(name, seed, size):
    """Weathered steppe granite tor block: rounded, lichen-crusted, half buried in the turf."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    _stone(b, (0, 0, 0), size, rnd, seed, flat=0.6, rough=0.3, pal=TOR, moss=TOR_LICHEN, moss_p=0.4, crev='5a544c')
    if seed % 2 == 1:
        _stone(b, (size[0] * 0.9, -size[1] * 0.4, 0), (size[0] * 0.4, size[1] * 0.4, size[2] * 0.5), rnd, seed + 7, subdiv=1, flat=0.55, rough=0.3, pal=TOR, moss=TOR_LICHEN, moss_p=0.4, crev='5a544c')
    return finish(b, name)

def tor_outcrop(name='env_tor_outcrop', seed=571):
    """Steppe tor outcrop (Kazakh melkosopochnik / Mongolian granite hill crest, ~10 x 7 x 4 m): a low dome of
    weathered blocks with a stacked pair on top and loose stones."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    kw = dict(pal=TOR, moss=TOR_LICHEN, moss_p=0.4, crev='5a544c')
    _stone(b, (0, 0, -0.4), (5.0, 3.4, 1.8), rnd, seed, subdiv=3, flat=0.5, rough=0.24, **kw)
    _stone(b, (-0.6, 0.3, 1.5), (2.2, 1.8, 1.4), rnd, seed + 1, subdiv=2, flat=0.55, rough=0.28, **kw)
    _stone(b, (-0.3, 0.2, 3.0), (1.3, 1.1, 0.9), rnd, seed + 2, subdiv=2, flat=0.6, rough=0.3, **kw)
    _stone(b, (2.6, -1.0, 0.6), (1.6, 1.3, 1.1), rnd, seed + 3, subdiv=2, flat=0.55, rough=0.28, **kw)
    for k in range(5):
        a = rnd.uniform(0, math.tau)
        _stone(b, (math.cos(a) * 5.6, math.sin(a) * 3.9, 0), (rnd.uniform(0.4, 0.8), rnd.uniform(0.4, 0.7), rnd.uniform(0.3, 0.5)), rnd, seed + 5 + k, subdiv=1, flat=0.55, rough=0.3, **kw)
    return finish(b, name)

def kurgan(name='env_kurgan', seed=581, r=7.0, h=2.4):
    """Kurgan / khirigsuur: an old grass-grown burial mound (~14 m across, 2.4 m high) with a ring of grey kerb stones;
    the landmark of every steppe from the Pontic to Mongolia. Earth faces are alpha 0 (no sway)."""
    rnd = random.Random(seed)
    b = MeshBuilder(name, G)
    bm = bmesh.ops.create_uvsphere(b.bm, u_segments=16, v_segments=6, radius=1.0, matrix=Matrix.Identity(4))
    for v in bm['verts']:
        p = v.co.copy()
        z = max(p.z, 0.0)
        p.z = (z ** 1.4) * h - 0.25
        p.x *= r * (1.0 + noise.noise(p * 2.0) * 0.06); p.y *= r * (1.0 + noise.noise(p * 2.0 + Vector((3, 1, 0))) * 0.06)
        v.co = p
    turf = [hexc('6e6e40'), hexc('76764a'), hexc('666a3e')]
    colour_faces(b, new_faces(b, bm['verts']), lambda f: jit(lerpc(turf[rnd.randrange(3)], hexc('8a7a5a'), 0.25 if f.calc_center_median().z > h * 0.85 else 0.0), rnd, 0.05))
    for k in range(14):
        a = k / 14 * math.tau + rnd.uniform(-0.1, 0.1)
        _stone(b, (math.cos(a) * r * 1.05, math.sin(a) * r * 1.05, 0), (rnd.uniform(0.35, 0.6), rnd.uniform(0.3, 0.5), rnd.uniform(0.25, 0.45)), rnd, seed + k, subdiv=1, flat=0.55, rough=0.3, pal=TOR, moss=TOR_LICHEN, moss_p=0.3, crev='5a544c')
    return finish(b, name)

def steppe_far(name='env_steppe_far'):
    """Distance LOD for birch / poplar / larch groves (~40 tris)."""
    rnd = random.Random(9)
    b = MeshBuilder(name, G)
    b.cyl(0.3, 0.2, 5.0, (0, 0, 2.5), hexc('6e675c'), 'body', segs=4)
    _clump(b, Vector((0, 0, 7.2)), 3.0, (1.1, 1.1, 1.0), [hexc('54662e', 1.0)], hexc('7e8e4a', 1.0), rnd, 3, 0, rough=0.2, sub=1)
    return finish(b, name, smooth=True)

BUILDERS = {
    'env_feather_grass': feather_grass,
    'env_wormwood': wormwood,
    'env_pea_shrub': pea_shrub,
    'env_larch': larch,
    'env_cottonwood': cottonwood,
    'env_ombu': ombu,
    'env_tor_a': lambda: tor('env_tor_a', 561, (1.4, 1.1, 0.9)),
    'env_tor_b': lambda: tor('env_tor_b', 562, (2.2, 1.7, 1.3)),
    'env_tor_outcrop': tor_outcrop,
    'env_kurgan': kurgan,
    'env_steppe_far': steppe_far,
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
