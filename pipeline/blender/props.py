"""Static props: artillery & vehicles (era-specific), campaign-map pieces, ships, environment.
Vehicles: UVMap.u = 1 marks the recoiling barrel part (animated in the Godot shader)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import common, c19_kit, med_kit, em_kit, c20_kit, mod_kit
from common import hexc, MeshBuilder

TEAM = (1, 1, 1, 1.0)
WOOD = hexc('6e4a2b'); WOOD_D = hexc('4a3220'); IRON = hexc('3b3f44'); BRONZE = hexc('a07a3a'); STEEL = hexc('5c6268')
OLIVE = hexc('59603f'); OLIVE_TEAM = (0.45, 0.48, 0.32, 0.45); TRACK = hexc('2a2a2a'); RUBBER = hexc('1e1e1e')
STONE = hexc('8f8a80'); STONE_D = hexc('6d675e'); ROOF = hexc('9a4a32'); PLASTER = hexc('d8ccb0')
G = ['body', 'recoil']

def wheel(b, x, y, z, r, w, col, spokes=True):
    b.cyl(r, r, w, (x, y, z), col, 'body', rot=(0, 90, 0), segs=10)
    b.cyl(r * 0.25, r * 0.25, w * 1.6, (x, y, z), IRON, 'body', rot=(0, 90, 0), segs=6)

def finish(b, name):
    obj = b.to_object(with_vid=False)
    me = obj.data
    gi = obj.vertex_groups['recoil'].index if 'recoil' in obj.vertex_groups else -1
    uv = me.uv_layers['UVMap']
    rec = set()
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.5:
                rec.add(v.index)
    for loop in me.loops:
        uv.data[loop.index].uv = (1.0 if loop.vertex_index in rec else 0.0, uv.data[loop.index].uv[1])  # keep v = material class
    return obj

def bombard():
    # visual pass (medieval): art_bombard is only used by medieval bombards -> rebuilt in place (pipeline/blender/med_kit.py)
    return finish(med_kit.bombard(G), 'art_bombard')

def bombard_legacy():
    b = MeshBuilder('art_bombard', G)
    b.box((0.9, 2.2, 0.35), (0, -0.2, 0.25), WOOD, 'body')
    b.box((0.15, 0.4, 0.5), (0, -1.1, 0.35), WOOD_D, 'body')
    b.cyl(0.36, 0.42, 1.7, (0, 0.2, 0.75), IRON, 'recoil', rot=(-90, 0, 0), segs=10)
    for y in (-0.4, 0.2, 0.8):
        b.cyl(0.45, 0.45, 0.08, (0, y, 0.75), STEEL, 'recoil', rot=(-90, 0, 0), segs=10)
    b.box((1.0, 0.1, 0.5), (0, -1.0, 0.55), TEAM, 'body')
    return finish(b, 'art_bombard')

def field_gun_c19():
    # visual pass (c19): detailed field gun, same groups / footprint as art_cannon (pipeline/blender/c19_kit.py).
    # Separate asset because art_cannon is shared with early_modern 'culverins'; battle_visuals.gd swaps it in for c19.
    return finish(c19_kit.field_gun(G), 'art_field_gun_c19')

def culverin_em():
    # visual pass (early_modern): own asset, swapped in for art_cannon by battle_visuals.gd (art_cannon stays legacy)
    return finish(em_kit.culverin(G, wheel), 'art_culverin_em')

def cannon():
    b = MeshBuilder('art_cannon', G)
    b.box((0.18, 2.6, 0.18), (0, -1.1, 0.4), WOOD, 'body', rot=(-12, 0, 0))
    b.box((0.5, 0.8, 0.25), (0, 0.15, 0.75), WOOD, 'body')
    wheel(b, 0.42, 0.2, 0.65, 0.65, 0.09, WOOD_D)
    wheel(b, -0.42, 0.2, 0.65, 0.65, 0.09, WOOD_D)
    b.cyl(0.13, 0.17, 1.9, (0, 0.6, 0.95), BRONZE, 'recoil', rot=(-90, 0, 0), segs=10)
    b.cyl(0.19, 0.19, 0.12, (0, -0.32, 0.95), BRONZE, 'recoil', rot=(-90, 0, 0), segs=10)
    b.box((0.3, 0.3, 0.2), (0, -2.2, 0.2), TEAM, 'body')
    return finish(b, 'art_cannon')

def howitzer():
    b = MeshBuilder('art_howitzer', G)
    for s in (1, -1):
        b.box((0.16, 2.8, 0.18), (0.45 * s, -1.3, 0.35), OLIVE, 'body', rot=(-8, 0, 18 * s))
    b.box((0.9, 0.9, 0.4), (0, 0.1, 0.8), OLIVE, 'body')
    b.box((1.6, 0.08, 0.9), (0, 0.55, 1.05), OLIVE_TEAM, 'body')
    wheel(b, 0.7, 0.1, 0.55, 0.55, 0.25, RUBBER)
    wheel(b, -0.7, 0.1, 0.55, 0.55, 0.25, RUBBER)
    b.cyl(0.11, 0.09, 3.2, (0, 1.2, 1.3), OLIVE, 'recoil', rot=(-80, 0, 0), segs=8)
    b.cyl(0.18, 0.18, 0.9, (0, 0.0, 1.1), STEEL, 'recoil', rot=(-80, 0, 0), segs=8)
    b.cyl(0.14, 0.14, 0.3, (0, 2.78, 1.58), STEEL, 'recoil', rot=(-80, 0, 0), segs=8)
    return finish(b, 'art_howitzer')

def tracks(b, w, l, h, col=TRACK):
    for s in (1, -1):
        b.box((0.55, l, h), (s * (w / 2 - 0.28), 0, h / 2), col, 'body', taper=1.0)
        for i in range(6):
            wheel(b, s * (w / 2 - 0.28), -l / 2 + 0.5 + i * (l - 1.0) / 5, 0.38, 0.33, 0.6, hexc('3a3a3a'))

def howitzer_c20():
    # visual pass (c20): own asset, swapped in for art_howitzer by battle_visuals.gd (art_howitzer is shared with modern)
    return finish(c20_kit.howitzer(G, wheel), 'art_howitzer_c20')

def tank_c20():
    return finish(c20_kit.tank(G, tracks), 'tank_c20')  # visual pass (c20); legacy builder kept below as tank_c20_legacy

def tank_c20_legacy():
    b = MeshBuilder('tank_c20', G)
    tracks(b, 3.0, 6.0, 1.0)
    b.box((2.9, 5.6, 0.9), (0, 0, 1.35), OLIVE, 'body', taper=0.92)
    b.box((2.95, 1.0, 0.6), (0, 2.8, 1.1), OLIVE, 'body', rot=(35, 0, 0))
    b.cyl(1.05, 0.95, 0.85, (0, -0.3, 2.2), OLIVE_TEAM, 'body', segs=10)
    b.cyl(0.35, 0.35, 0.4, (0.4, -0.6, 2.75), OLIVE, 'body', segs=8)
    b.cyl(0.1, 0.1, 3.4, (0, 2.3, 2.25), OLIVE, 'recoil', rot=(-90, 0, 0), segs=8)
    b.cyl(0.18, 0.18, 0.5, (0, 0.85, 2.25), OLIVE, 'recoil', rot=(-90, 0, 0), segs=8)
    return finish(b, 'tank_c20')

def howitzer_mod():
    # visual pass (modern): own asset, swapped in for art_howitzer by battle_visuals.gd (art_howitzer stays legacy)
    return finish(mod_kit.howitzer(G, wheel), 'art_howitzer_mod')

def mbt():
    return finish(mod_kit.mbt(G, tracks), 'mbt_modern')  # visual pass (modern); legacy kept as mbt_legacy

def ifv():
    return finish(mod_kit.ifv(G, wheel), 'ifv_modern')  # visual pass (modern); legacy kept as ifv_legacy

def mbt_legacy():
    b = MeshBuilder('mbt_modern', G)
    sand = hexc('7d7a5c'); sandt = (0.5, 0.5, 0.38, 0.5)
    tracks(b, 3.6, 7.4, 1.0)
    b.box((3.6, 7.0, 0.85), (0, 0, 1.4), sand, 'body', taper=0.97)
    b.box((3.6, 1.2, 0.5), (0, 3.4, 1.25), sand, 'body', rot=(20, 0, 0))
    b.box((3.0, 3.4, 0.8), (0, -0.4, 2.2), sandt, 'body', taper=0.82)
    b.box((2.6, 1.2, 0.6), (0, 1.5, 2.15), sandt, 'body', rot=(-12, 0, 0), taper=0.7)
    b.box((0.6, 0.6, 0.3), (0.8, -0.8, 2.75), sand, 'body')
    b.cyl(0.09, 0.09, 5.0, (0, 3.9, 2.3), sand, 'recoil', rot=(-90, 0, 0), segs=8)
    b.cyl(0.15, 0.15, 0.8, (0, 3.0, 2.3), sand, 'recoil', rot=(-90, 0, 0), segs=8)
    return finish(b, 'mbt_modern')

def ifv_legacy():
    b = MeshBuilder('ifv_modern', G)
    green = hexc('4f5a3e'); gt = (0.42, 0.47, 0.32, 0.5)
    for s in (1, -1):
        for i in range(4):
            wheel(b, s * 1.3, -2.2 + i * 1.45, 0.55, 0.55, 0.45, RUBBER)
    b.box((2.8, 6.6, 1.3), (0, 0, 1.45), green, 'body', taper=0.9)
    b.box((2.8, 1.2, 1.0), (0, 3.3, 1.35), green, 'body', rot=(40, 0, 0))
    b.box((1.4, 1.6, 0.55), (0, 0.3, 2.35), gt, 'body', taper=0.8)
    b.cyl(0.06, 0.06, 2.3, (0, 2.1, 2.4), STEEL, 'recoil', rot=(-90, 0, 0), segs=6)
    return finish(b, 'ifv_modern')

def truck():
    b = MeshBuilder('truck_c20', G)
    for y in (-1.6, 1.6):
        for s in (1, -1):
            wheel(b, s * 1.0, y, 0.5, 0.5, 0.3, RUBBER)
    b.box((2.2, 1.6, 1.5), (0, 1.9, 1.5), OLIVE, 'body')
    b.box((2.3, 3.8, 0.25), (0, -0.9, 1.05), WOOD_D, 'body')
    b.box((2.3, 3.8, 1.4), (0, -0.9, 1.9), OLIVE_TEAM, 'body', taper=0.95)
    return finish(b, 'truck_c20')

# ---- campaign-map pieces ----
def army_standard():
    b = MeshBuilder('army_standard', G)
    b.cyl(0.55, 0.65, 0.18, (0, 0, 0.09), STONE_D, 'body', segs=12)
    b.cyl(0.035, 0.035, 2.6, (0, 0, 1.4), WOOD_D, 'body', segs=6)
    b.box((0.04, 0.9, 0.62), (0, 0.47, 2.25), TEAM, 'body')
    b.box((0.045, 0.9, 0.1), (0, 0.47, 1.92), hexc('e8d9a0'), 'body')
    b.sphere(0.08, (0, 0, 2.75), hexc('c8a24a'), 'body', segs=6, rings=4)
    # little soldier figure beside the pole
    b.box((0.26, 0.18, 0.62), (0.28, -0.1, 0.55), TEAM, 'body')
    b.sphere(0.12, (0.28, -0.1, 1.0), hexc('e2b48e'), 'body', segs=6, rings=4)
    return finish(b, 'army_standard')

def city(tier):
    b = MeshBuilder(f'city_{tier}', G)
    rnd = random.Random(tier)
    n = [5, 9, 14][tier]
    for i in range(n):
        a = rnd.random() * 6.283; r = 0.45 + rnd.random() * (0.8 + 0.25 * tier)
        x, y = math.cos(a) * r, math.sin(a) * r
        w = 0.25 + rnd.random() * 0.2; h = 0.25 + rnd.random() * 0.3
        b.box((w, w * 1.3, h), (x, y, h / 2), PLASTER, 'body', rot=(0, 0, rnd.random() * 90))
        b.box((w * 1.05, w * 1.35, 0.18), (x, y, h + 0.07), ROOF, 'body', rot=(0, 0, rnd.random() * 90), taper=0.2)
    b.cyl(0.32 + 0.06 * tier, 0.28 + 0.06 * tier, 0.9 + 0.4 * tier, (0, 0, 0.45 + 0.2 * tier), STONE, 'body', segs=8)
    b.cyl(0.36 + 0.06 * tier, 0.0, 0.45, (0, 0, 0.9 + 0.4 * tier + 0.22), TEAM, 'body', segs=8)
    if tier >= 1:
        for i in range(8):
            a = i / 8 * 6.283; R = 1.25 + 0.3 * tier
            b.box((1.0 + 0.2 * tier, 0.14, 0.32), (math.cos(a) * R, math.sin(a) * R, 0.16), STONE_D, 'body', rot=(0, 0, math.degrees(a) + 90))
    return finish(b, f'city_{tier}')

def capital_star():
    b = MeshBuilder('capital_star', G)
    b.cyl(0.4, 0.4, 0.06, (0, 0, 0.03), hexc('c8a24a'), 'body', segs=5)
    return finish(b, 'capital_star')

def battle_marker():
    b = MeshBuilder('battle_marker', G)
    for s in (1, -1):
        b.box((0.08, 0.08, 1.6), (0, 0, 0.9), hexc('d8d8d8'), 'body', rot=(0, 35 * s, 0))
        b.box((0.4, 0.1, 0.08), (0.42 * s, 0, 0.5), hexc('c8a24a'), 'body', rot=(0, 35 * s, 0))
    b.cyl(0.5, 0.5, 0.1, (0, 0, 0.05), hexc('9e1b1b'), 'body', segs=12)
    return finish(b, 'battle_marker')

def ship_sail():
    b = MeshBuilder('ship_sail', G)
    b.box((1.2, 4.0, 0.8), (0, 0, 0.4), WOOD, 'body', taper=0.7)
    b.box((1.0, 0.8, 0.7), (0, -1.6, 1.0), WOOD_D, 'body')
    for y, h in ((-0.6, 2.8), (0.8, 2.4)):
        b.cyl(0.06, 0.05, h, (0, y, 0.8 + h / 2), WOOD_D, 'body', segs=5)
        b.box((1.6, 0.06, h * 0.55), (0, y + 0.05, 1.0 + h * 0.5), hexc('ece4cc'), 'body', taper=0.85)
    b.box((0.04, 0.6, 0.35), (0, -0.6, 0.85 + 2.8), TEAM, 'body')
    return finish(b, 'ship_sail')

def ship_steel():
    b = MeshBuilder('ship_steel', G)
    gray = hexc('6f767d')
    b.box((1.3, 5.0, 0.7), (0, 0, 0.35), gray, 'body', taper=0.75)
    b.box((0.8, 1.4, 0.6), (0, -0.2, 1.0), hexc('8a9096'), 'body')
    b.cyl(0.18, 0.2, 0.9, (0, -0.6, 1.6), TEAM, 'body', segs=8)
    b.cyl(0.32, 0.32, 0.3, (0, 1.4, 0.85), gray, 'body', segs=8)
    b.cyl(0.05, 0.05, 1.0, (0, 1.9, 0.9), gray, 'body', rot=(-90, 0, 0), segs=5)
    return finish(b, 'ship_steel')

# ---- environment ----
def conifer():
    b = MeshBuilder('tree_conifer', G)
    b.cyl(0.12, 0.09, 1.0, (0, 0, 0.5), WOOD_D, 'body', segs=5)
    for i, (r, z) in enumerate(((1.1, 1.3), (0.85, 2.2), (0.55, 3.0))):
        b.cyl(r, 0.05, 1.4, (0, 0, z), hexc(['2f4d2a', '35552e', '3b5e33'][i]), 'body', segs=7)
    return finish(b, 'tree_conifer')

def broadleaf():
    b = MeshBuilder('tree_broadleaf', G)
    b.cyl(0.14, 0.1, 1.6, (0, 0, 0.8), WOOD_D, 'body', segs=5)
    b.sphere(1.0, (0, 0, 2.2), hexc('4c6b2f'), 'body', segs=7, rings=5, scale=(1, 1, 0.85))
    b.sphere(0.65, (0.5, 0.3, 2.7), hexc('577a35'), 'body', segs=6, rings=4)
    return finish(b, 'tree_broadleaf')

def palm():
    b = MeshBuilder('tree_palm', G)
    for i in range(5):
        b.cyl(0.13 - i * 0.01, 0.12 - i * 0.01, 0.7, (i * 0.06, 0, 0.35 + i * 0.68), hexc('8a6d45'), 'body', segs=5, rot=(0, 5, 0))
    for i in range(6):
        a = i * 60
        b.box((0.3, 1.6, 0.04), (0.3 + 0.7 * math.cos(math.radians(a)), 0.7 * math.sin(math.radians(a)), 3.4), hexc('4f7a2c'), 'body', rot=(-25, 0, a - 90))
    return finish(b, 'tree_palm')

def bush():
    b = MeshBuilder('bush', G)
    b.sphere(0.5, (0, 0, 0.3), hexc('51682e'), 'body', segs=6, rings=4, scale=(1.2, 1, 0.7))
    return finish(b, 'bush')

def rock():
    b = MeshBuilder('rock', G)
    b.sphere(0.7, (0, 0, 0.2), hexc('7c776e'), 'body', segs=6, rings=4, scale=(1.3, 1, 0.7))
    return finish(b, 'rock')

def house():
    b = MeshBuilder('house', G)
    b.box((2.2, 3.0, 1.8), (0, 0, 0.9), PLASTER, 'body')
    b.box((2.5, 3.3, 1.2), (0, 0, 2.3), ROOF, 'body', taper=0.08)
    b.box((0.4, 0.4, 1.0), (0.6, 0.8, 2.6), STONE_D, 'body')
    return finish(b, 'house')

def fence():
    b = MeshBuilder('fence', G)
    for y in (-1.5, 0, 1.5):
        b.box((0.1, 0.1, 0.9), (0, y, 0.45), WOOD, 'body')
    for z in (0.35, 0.7):
        b.box((0.06, 3.1, 0.08), (0, 0, z), WOOD, 'body')
    return finish(b, 'fence')

def main():
    builders = [bombard, cannon, field_gun_c19, culverin_em, howitzer, howitzer_c20, howitzer_mod, tank_c20, mbt, ifv, truck, army_standard, lambda: city(0), lambda: city(1),
                lambda: city(2), capital_star, battle_marker, ship_sail, ship_steel, conifer, broadleaf, palm, bush, rock, house, fence]
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []  # e.g. -- field_gun_c19 (skips props.blend)
    common.reset_scene()
    objs = []
    for i, fn in enumerate(builders):
        if only and getattr(fn, '__name__', '') not in [{'art_cannon': 'cannon', 'art_field_gun_c19': 'field_gun_c19', 'art_culverin_em': 'culverin_em', 'art_howitzer_c20': 'howitzer_c20', 'art_howitzer_mod': 'howitzer_mod', 'mbt_modern': 'mbt', 'ifv_modern': 'ifv'}.get(n, n) for n in only]:
            continue
        o = fn()
        common.export_glb([o], os.path.join(common.MODELS, o.name + '.glb'))
        objs.append(o)
    for i, o in enumerate(objs):
        o.location = ((i % 8) * 9.0, (i // 8) * 10.0, 0)
    if only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, 'props_' + '_'.join(only) + '.blend'))
        print('props done', len(objs)); return
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, 'props.blend'))
    print('props done', len(objs))

if __name__ == '__main__':
    main()
