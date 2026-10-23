"""Horse + rider cavalry generator with its own quadruped rig, 5 clips, VAT bake + GLB export."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import common, rigkit, c19_kit
from common import hexc, MeshBuilder

BONES = [
    ('root', (0, 0, 0), (0, 0.2, 0), None),
    ('body', (0, -0.55, 1.3), (0, 0.6, 1.3), 'root'),
    ('neck', (0, 0.6, 1.38), (0, 0.92, 1.85), 'body'),
    ('head', (0, 0.92, 1.85), (0, 1.38, 1.58), 'neck'),
    ('tail', (0, -0.62, 1.38), (0, -0.85, 0.85), 'body'),
    ('fl_up', (0.17, 0.48, 1.12), (0.17, 0.48, 0.62), 'body'), ('fl_lo', (0.17, 0.48, 0.62), (0.17, 0.48, 0.05), 'fl_up'),
    ('fr_up', (-0.17, 0.48, 1.12), (-0.17, 0.48, 0.62), 'body'), ('fr_lo', (-0.17, 0.48, 0.62), (-0.17, 0.48, 0.05), 'fr_up'),
    ('bl_up', (0.17, -0.45, 1.15), (0.17, -0.45, 0.62), 'body'), ('bl_lo', (0.17, -0.45, 0.62), (0.17, -0.45, 0.05), 'bl_up'),
    ('br_up', (-0.17, -0.45, 1.15), (-0.17, -0.45, 0.62), 'body'), ('br_lo', (-0.17, -0.45, 0.62), (-0.17, -0.45, 0.05), 'br_up'),
    ('r_spine', (0, -0.05, 1.62), (0, -0.05, 1.98), 'body'),
    ('r_head', (0, -0.05, 2.0), (0, -0.05, 2.24), 'r_spine'),
    ('r_arm.R', (0.2, -0.05, 1.93), (0.2, -0.05, 1.66), 'r_spine'), ('r_fore.R', (0.2, -0.05, 1.66), (0.2, -0.05, 1.41), 'r_arm.R'),
    ('r_arm.L', (-0.2, -0.05, 1.93), (-0.2, -0.05, 1.66), 'r_spine'), ('r_fore.L', (-0.2, -0.05, 1.66), (-0.2, -0.05, 1.41), 'r_arm.L'),
]
GROUPS = [b[0] for b in BONES]
SKIN = hexc('e2b48e'); METAL = hexc('a3abb3'); LEATHER = hexc('4a3220'); WOOD = hexc('7a5230'); TEAM = (1, 1, 1, 1.0)
HORSE = hexc('6b4a30'); HORSE_D = hexc('3a281b'); BOOT = hexc('231d19')

VARIANTS = {
    'med_knight': dict(rider=METAL, surcoat=TEAM, hat='greathelm', weapon='lance', barding=True),
    'em_cuirassier': dict(rider=TEAM, surcoat=METAL, hat='lobster', weapon='sabre'),
    'c19_hussar': dict(rider=TEAM, surcoat=hexc('d9c36a'), hat='shako', weapon='sabre', builder='c19_hussar'),
}

def build(name, kit, detail):
    if kit.get('builder') == 'c19_hussar':  # visual pass: detailed Napoleonic kit (pipeline/blender/c19_kit.py)
        return c19_kit.hussar(name, GROUPS, detail)
    s = 8 if detail else 5
    b = MeshBuilder(name, GROUPS)
    # horse
    b.box((0.46, 1.25, 0.5), (0, 0.02, 1.3), HORSE, 'body', taper=0.92)
    b.box((0.25, 0.32, 0.62), (0, 0.78, 1.62), HORSE, 'neck', rot=(-35, 0, 0), taper=0.75)
    b.box((0.2, 0.52, 0.22), (0, 1.12, 1.68), HORSE, 'head', rot=(-30, 0, 0), taper=0.8)
    b.box((0.06, 0.3, 0.32), (0, 0.72, 1.85), HORSE_D, 'neck', rot=(-35, 0, 0))  # mane
    b.box((0.1, 0.1, 0.5), (0, -0.72, 1.1), HORSE_D, 'tail', rot=(25, 0, 0), taper=0.5)
    for leg, x, y in (('fl', 0.17, 0.48), ('fr', -0.17, 0.48), ('bl', 0.17, -0.45), ('br', -0.17, -0.45)):
        b.box((0.13, 0.17, 0.5), (x, y, 0.88), HORSE, leg + '_up', taper=0.8)
        b.box((0.08, 0.09, 0.5), (x, y, 0.33), HORSE, leg + '_lo')
        b.box((0.1, 0.12, 0.08), (x, y + 0.01, 0.05), HORSE_D, leg + '_lo')
    if kit.get('barding'):
        b.box((0.52, 1.0, 0.36), (0, 0.0, 1.18), TEAM, 'body')
    b.box((0.5, 0.42, 0.06), (0, -0.05, 1.57), LEATHER, 'body')  # saddle
    # rider legs (rigid to horse body)
    for x in (0.2, -0.2):
        b.box((0.12, 0.38, 0.13), (x, 0.08, 1.6), kit['rider'], 'body')
        b.box((0.11, 0.12, 0.4), (x, 0.24, 1.37), BOOT, 'body')
    # rider torso
    b.box((0.34, 0.2, 0.4), (0, -0.05, 1.8), kit['rider'], 'r_spine', taper=1.1)
    b.box((0.38, 0.23, 0.2), (0, -0.05, 1.67), kit['surcoat'], 'r_spine')
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.1, 0.11, 0.3), (x, -0.05, 1.8), kit['rider'], 'r_arm.' + side)
        b.box((0.09, 0.1, 0.26), (x, -0.05, 1.54), kit['rider'], 'r_fore.' + side)
        b.box((0.08, 0.09, 0.09), (x, -0.05, 1.38), SKIN, 'r_fore.' + side)
    b.box((0.09, 0.09, 0.05), (0, -0.05, 2.0), SKIN, 'r_head')
    b.sphere(0.115, (0, -0.04, 2.11), SKIN, 'r_head', segs=s, rings=4, scale=(0.95, 1, 1.12))
    if kit['hat'] == 'greathelm':
        b.cyl(0.13, 0.13, 0.27, (0, -0.04, 2.13), METAL, 'r_head', segs=s)
    elif kit['hat'] == 'lobster':
        b.sphere(0.13, (0, -0.04, 2.17), METAL, 'r_head', segs=s, rings=4, scale=(1, 1.05, 0.85))
        b.box((0.16, 0.1, 0.12), (0, -0.16, 2.08), METAL, 'r_head')
    else:
        b.cyl(0.115, 0.13, 0.22, (0, -0.04, 2.27), hexc('1c1c22'), 'r_head', segs=s)
    hx, hz = 0.2, 1.38
    if kit['weapon'] == 'lance':
        b.cyl(0.025, 0.02, 3.2, (hx + 0.04, -0.05, hz - 1.0), WOOD, 'r_fore.R', segs=4)
        b.cyl(0.05, 0.0, 0.25, (hx + 0.04, -0.05, hz - 2.7), METAL, 'r_fore.R', rot=(180, 0, 0), segs=4)
        b.box((0.42, 0.04, 0.5), (-0.27, 0.05, 1.6), TEAM, 'r_fore.L', taper=0.8)
    else:
        b.box((0.02, 0.05, 0.85), (hx + 0.04, -0.05, hz - 0.45), METAL, 'r_fore.R')
        b.box((0.12, 0.06, 0.03), (hx + 0.04, -0.05, hz - 0.02), hexc('b8962e'), 'r_fore.R')
    return b.to_object()

def S(t, ph=0.0):
    return math.sin(2 * math.pi * (t + ph))

def rider_hold(kit):
    if kit['weapon'] == 'lance':
        return {'r_arm.R': (25, 0, 0), 'r_fore.R': (60, 0, 0), 'r_arm.L': (35, 0, 0), 'r_fore.L': (50, 0, 0)}
    return {'r_arm.R': (15, 0, 0), 'r_fore.R': (140, 0, 0), 'r_arm.L': (35, 0, 0), 'r_fore.L': (55, 0, 0)}

def gait(t, amp, knee, phases, bob, pitch):
    p = {}
    for leg, ph in phases.items():
        p[leg + '_up'] = (amp * S(t, ph), 0, 0)
        p[leg + '_lo'] = ((knee if leg[0] == 'f' else -knee) * max(0, S(t, ph + 0.25)) * (-1 if leg[0] == 'f' else 1), 0, 0)
    p['body'] = (pitch * S(t, 0.1), 0, 0)
    p['neck'] = (-pitch * 1.5 * S(t, 0.2), 0, 0)
    p['_loc'] = (0, 0, bob * S(t * 2, 0.1) if bob else 0)
    p['tail'] = (10 + 5 * S(t), 0, 0)
    return p

def clips(kit):
    walk_ph = {'fl': 0.0, 'br': 0.25, 'fr': 0.5, 'bl': 0.75}
    gal_ph = {'fl': 0.0, 'fr': 0.1, 'bl': 0.5, 'br': 0.6}
    def idle(t):
        p = rider_hold(kit); p['neck'] = (6 * S(t), 0, 4 * S(t, 0.3)); p['tail'] = (8 + 6 * S(t), 0, 5 * S(t)); return p
    def walk(t):
        p = gait(t, 18, 40, walk_ph, 0.02, 1.5); p.update(rider_hold(kit)); p['r_spine'] = (2 * S(t * 2), 0, 0); return p
    def gallop(t):
        p = gait(t, 38, 70, gal_ph, 0.08, 6); p.update(rider_hold(kit)); p['r_spine'] = (-12 + 5 * S(t), 0, 0)
        if kit['weapon'] == 'lance':
            p['r_arm.R'] = (60, 0, 0); p['r_fore.R'] = (42, 0, 0)
        return p
    def attack(t):
        p = gait(t, 38, 70, gal_ph, 0.08, 6)
        k = 0.5 - 0.5 * math.cos(2 * math.pi * t)
        if kit['weapon'] == 'lance':
            p.update({'r_arm.R': (75, 0, 0), 'r_fore.R': (27 + 18 * k, 0, 0), 'r_spine': (-20 * k, 0, 0), 'r_arm.L': (35, 0, 0), 'r_fore.L': (50, 0, 0)})
        else:
            p.update({'r_arm.R': (170 - 120 * k, 0, 20 * k), 'r_fore.R': (30, 0, 0), 'r_spine': (-5 - 15 * k, 0, 10 * k), 'r_arm.L': (35, 0, 0), 'r_fore.L': (55, 0, 0)})
        return p
    def die(t):
        k = min(1, t / 0.7); k = k * k * (3 - 2 * k)
        p = rider_hold(kit)
        p.update({'root': (0, -85 * k, 0), 'fl_up': (40 * k, 0, 0), 'fl_lo': (-70 * k, 0, 0), 'bl_up': (-30 * k, 0, 0),
                  'fr_up': (25 * k, 0, 0), 'br_up': (-20 * k, 0, 0), 'neck': (25 * k, 0, 15 * k), 'r_spine': (20 * k, -25 * k, 0),
                  'r_arm.R': (25 + 20 * k, 0, 0), '_loc': (0, 0, -0.35 * k)})
        return p
    return [('idle', 24, True, idle), ('walk', 24, True, walk), ('run', 12, True, gallop), ('melee', 24, True, attack),
            ('fire', 24, True, attack), ('die', 36, False, die)]

def main():
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []  # e.g. -- c19_hussar
    for vid, kit in VARIANTS.items():
        if only and vid not in only:
            continue
        for lod in (0, 1):
            common.reset_scene()
            rig = rigkit.build_armature('horse', BONES)
            body = build(f'{vid}_lod{lod}', kit, lod == 0)
            rigkit.bind(body, rig)
            rigkit.bake(body, rig, clips(kit), os.path.join(common.VAT, f'{vid}_lod{lod}'))
            rigkit.export_static_copy(body, os.path.join(common.MODELS, f'cavalry_{vid}_lod{lod}.glb'))
            if lod == 0:
                rigkit.export_rigged(body, rig, os.path.join(common.MODELS, f'cavalry_{vid}_rigged.glb'))
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, f'cavalry_{vid}.blend'))

if __name__ == '__main__':
    main()
