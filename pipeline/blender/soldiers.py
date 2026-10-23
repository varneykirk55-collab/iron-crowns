"""Generates era infantry soldiers: rigged low-poly humanoid + era kit, 6 reusable clips, VAT bake, GLB export.
Character faces +Y in Blender (=> -Z forward in Godot). Run: blender -b --python soldiers.py"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import common, rigkit, c19_kit, med_kit, em_kit, c20_kit, mod_kit
from common import hexc, MeshBuilder

BONES = [
    ('root', (0, 0, 0), (0, 0.2, 0), None),
    ('hips', (0, 0, 0.95), (0, 0, 1.05), 'root'),
    ('spine', (0, 0, 1.05), (0, 0, 1.28), 'hips'),
    ('chest', (0, 0, 1.28), (0, 0, 1.5), 'spine'),
    ('head', (0, 0, 1.52), (0, 0, 1.78), 'chest'),
    ('upper_arm.R', (0.2, 0, 1.45), (0.2, 0, 1.18), 'chest'),
    ('forearm.R', (0.2, 0, 1.18), (0.2, 0, 0.93), 'upper_arm.R'),
    ('hand.R', (0.2, 0, 0.93), (0.2, 0, 0.85), 'forearm.R'),
    ('upper_arm.L', (-0.2, 0, 1.45), (-0.2, 0, 1.18), 'chest'),
    ('forearm.L', (-0.2, 0, 1.18), (-0.2, 0, 0.93), 'upper_arm.L'),
    ('hand.L', (-0.2, 0, 0.93), (-0.2, 0, 0.85), 'forearm.L'),
    ('thigh.R', (0.09, 0, 0.95), (0.09, 0, 0.52), 'hips'),
    ('shin.R', (0.09, 0, 0.52), (0.09, 0, 0.09), 'thigh.R'),
    ('thigh.L', (-0.09, 0, 0.95), (-0.09, 0, 0.52), 'hips'),
    ('shin.L', (-0.09, 0, 0.52), (-0.09, 0, 0.09), 'thigh.L'),
]
GROUPS = [b[0] for b in BONES]

SKIN = hexc('e2b48e'); LEATHER = hexc('4a3220'); METAL = hexc('a0a8b0'); DARKMETAL = hexc('4b5056')
WOOD = hexc('7a5230'); TEAM = (1, 1, 1, 1.0); TEAM_DARK = (0.6, 0.6, 0.6, 1.0); WHITE = hexc('e8e4da')
BOOT = hexc('2a2420'); DRAB = (0.42, 0.42, 0.33, 0.35); DRAB_DARK = (0.3, 0.3, 0.24, 0.25); CAMO = (0.36, 0.38, 0.30, 0.3)

VARIANTS = {
    # id: dict(kit) ; style decides clip arm poses
    'med_spear':  dict(coat=TEAM, legs=hexc('5b4a3a'), hat='kettle', weapon='spear', shield=True, style='spear', builder='med_spear'),
    'med_archer': dict(coat=TEAM, legs=hexc('5b4a3a'), hat='hood', weapon='bow', quiver=True, style='bow', builder='med_archer'),
    'em_pike':    dict(coat=TEAM, legs=hexc('3c342c'), hat='morion', weapon='pike', style='spear', builder='em_pike'),
    'em_musket':  dict(coat=TEAM, legs=hexc('3c342c'), hat='widehat', weapon='musket', style='gun', builder='em_musket'),
    'c19_line':   dict(coat=TEAM, legs=WHITE, hat='shako', weapon='musket_bayonet', belts=True, style='gun', builder='c19_line'),
    'c19_grenadier': dict(coat=TEAM, legs=WHITE, hat='bearskin', weapon='musket_bayonet', belts=True, style='gun', builder='c19_grenadier'),  # polish pass
    'c19_artillery': dict(coat=TEAM, legs=WHITE, hat='shako', weapon='rammer', style='gun', builder='c19_artillery'),         # polish pass: gun crew
    'em_gunner':  dict(coat=TEAM, legs=hexc('3c342c'), hat='cap', weapon='linstock', style='gun', builder='em_gunner'),            # polish pass: gun crew
    'c20_rifle':  dict(coat=DRAB, legs=DRAB_DARK, hat='brodie', weapon='rifle', pack=True, style='gun', armband=True, builder='c20_rifle'),
    'mod_rifle':  dict(coat=CAMO, legs=CAMO, hat='modern', weapon='carbine', vest=True, style='gun', armband=True, builder='mod_rifle'),
}

def build_body(name, kit, detail):
    if kit.get('builder') == 'c19_line':  # visual pass: detailed Napoleonic kit (pipeline/blender/c19_kit.py)
        return c19_kit.line_infantry(name, GROUPS, detail)
    if kit.get('builder') == 'c19_grenadier':  # polish pass: bearskin grenadier (c19_kit.grenadier)
        return c19_kit.grenadier(name, GROUPS, detail)
    if kit.get('builder') == 'c19_artillery':  # polish pass: c19 foot-artillery gun crew
        return c19_kit.artillery_crew(name, GROUPS, detail)
    if kit.get('builder') == 'em_gunner':      # polish pass: early-modern gun crew
        return em_kit.gunner(name, GROUPS, detail)
    if kit.get('builder') == 'med_spear':  # visual pass: medieval kits (pipeline/blender/med_kit.py)
        return med_kit.spearman(name, GROUPS, detail)
    if kit.get('builder') == 'mod_rifle':  # visual pass: modern kit (pipeline/blender/mod_kit.py)
        return mod_kit.rifleman(name, GROUPS, detail)
    if kit.get('builder') == 'c20_rifle':  # visual pass: c20 kit (pipeline/blender/c20_kit.py)
        return c20_kit.rifleman(name, GROUPS, detail)
    if kit.get('builder') == 'em_pike':  # visual pass: early-modern kits (pipeline/blender/em_kit.py)
        return em_kit.pikeman(name, GROUPS, detail)
    if kit.get('builder') == 'em_musket':
        return em_kit.musketeer(name, GROUPS, detail)
    if kit.get('builder') == 'med_archer':
        return med_kit.archer(name, GROUPS, detail)
    s = 8 if detail else 5
    b = MeshBuilder(name, GROUPS)
    coat, legs = kit['coat'], kit['legs']
    # legs
    for side, x in (('R', 0.09), ('L', -0.09)):
        b.box((0.13, 0.15, 0.44), (x, 0, 0.74), legs, 'thigh.' + side, taper=1.1)
        b.box((0.11, 0.13, 0.36), (x, 0, 0.31), legs, 'shin.' + side, taper=1.15)
        b.box((0.11, 0.24, 0.09), (x, 0.04, 0.05), BOOT, 'shin.' + side)
    # torso
    b.box((0.34, 0.2, 0.24), (0, 0, 1.1), coat, 'spine', taper=1.12)
    b.box((0.4, 0.23, 0.26), (0, 0, 1.36), coat, 'chest', taper=1.05)
    b.box((0.36, 0.21, 0.08), (0, 0, 0.98), LEATHER, 'hips')  # belt
    if kit.get('belts') and detail:
        b.box((0.06, 0.24, 0.5), (0.0, 0.0, 1.25), WHITE, 'chest', rot=(0, 30, 0))
        b.box((0.06, 0.24, 0.5), (0.0, 0.0, 1.25), WHITE, 'chest', rot=(0, -30, 0))
    if kit.get('vest'):
        b.box((0.42, 0.27, 0.34), (0, 0, 1.3), hexc('3d4234', 0.15), 'chest')
    if kit.get('pack'):
        b.box((0.3, 0.14, 0.3), (0, -0.17, 1.32), hexc('5e5a3e', 0.1), 'chest')
    if kit.get('quiver'):
        b.cyl(0.05, 0.06, 0.5, (0.12, -0.15, 1.35), LEATHER, 'chest', rot=(-15, 20, 0), segs=s)
    # arms
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.1, 0.11, 0.3), (x, 0, 1.31), coat, 'upper_arm.' + side)
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), coat, 'forearm.' + side, taper=0.9)
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), SKIN, 'hand.' + side)
    if kit.get('armband'):
        b.box((0.11, 0.12, 0.06), (-0.24, 0, 1.36), TEAM, 'upper_arm.L')
    # head
    b.box((0.09, 0.09, 0.06), (0, 0, 1.52), SKIN, 'head')
    b.sphere(0.115, (0, 0.01, 1.64), SKIN, 'head', segs=s, rings=5 if detail else 4, scale=(0.95, 1, 1.12))
    hat = kit['hat']
    if hat == 'kettle':
        b.cyl(0.13, 0.12, 0.08, (0, 0.01, 1.72), METAL, 'head', segs=s)
        b.cyl(0.21, 0.19, 0.02, (0, 0.01, 1.69), METAL, 'head', segs=s)
    elif hat == 'hood':
        b.sphere(0.135, (0, -0.01, 1.67), hexc('6b5a40'), 'head', segs=s, rings=4, scale=(1, 1.05, 1.05))
    elif hat == 'morion':
        b.sphere(0.13, (0, 0.0, 1.72), METAL, 'head', segs=s, rings=4, scale=(1, 1.3, 0.8))
        b.box((0.02, 0.24, 0.07), (0, 0, 1.82), METAL, 'head')
    elif hat == 'widehat':
        b.cyl(0.11, 0.1, 0.12, (0, 0.01, 1.77), hexc('2c2622'), 'head', segs=s)
        b.cyl(0.24, 0.24, 0.02, (0, 0.01, 1.72), hexc('2c2622'), 'head', segs=s)
    elif hat == 'shako':
        b.cyl(0.115, 0.13, 0.2, (0, 0.01, 1.8), hexc('1c1c22'), 'head', segs=s)
        b.box((0.16, 0.05, 0.02), (0, 0.12, 1.71), hexc('1c1c22'), 'head')
        if detail:
            b.sphere(0.03, (0, 0.11, 1.9), TEAM, 'head', segs=5, rings=3)
    elif hat == 'brodie':
        b.sphere(0.13, (0, 0.01, 1.71), hexc('53573f', 0.2), 'head', segs=s, rings=4, scale=(1, 1, 0.55))
        b.cyl(0.2, 0.2, 0.015, (0, 0.01, 1.7), hexc('53573f', 0.2), 'head', segs=s)
    elif hat == 'modern':
        b.sphere(0.135, (0, 0.0, 1.69), hexc('4b5040', 0.25), 'head', segs=s, rings=4, scale=(1, 1.05, 0.8))
    # weapons, modelled hanging down along the arm from the hand (see rig notes)
    w = kit['weapon']
    hx, hz = 0.2, 0.89
    if w in ('spear', 'pike'):
        L = 2.3 if w == 'spear' else 3.8
        b.cyl(0.018, 0.018, L, (hx + 0.04, 0, hz - L * 0.35), WOOD, 'hand.R', segs=4)
        b.cyl(0.035, 0.0, 0.2, (hx + 0.04, 0, hz - L * 0.85 - 0.1), METAL, 'hand.R', rot=(180, 0, 0), segs=4)
    elif w == 'bow':
        b.box((0.025, 1.2, 0.04), (-hx - 0.04, 0.0, hz), WOOD, 'hand.L')
        b.box((0.005, 1.15, 0.005), (-hx - 0.04, 0.0, hz + 0.08), WHITE, 'hand.L')
    else:
        L = {'musket': 1.45, 'musket_bayonet': 1.45, 'rifle': 1.15, 'carbine': 0.85}[w]
        stock = WOOD if w in ('musket', 'musket_bayonet', 'rifle') else hexc('2b2b2b')
        b.box((0.05, 0.08, 0.4), (hx + 0.04, 0.02, hz + 0.08), stock, 'hand.R')
        b.cyl(0.016, 0.016, L - 0.3, (hx + 0.04, 0.02, hz - (L - 0.3) / 2 + 0.05), DARKMETAL, 'hand.R', segs=4)
        if w == 'musket_bayonet':
            b.cyl(0.01, 0.0, 0.4, (hx + 0.06, 0.02, hz - (L - 0.3) - 0.15), METAL, 'hand.R', rot=(180, 0, 0), segs=3)
        if w == 'carbine':
            b.box((0.04, 0.06, 0.12), (hx + 0.04, 0.06, hz - 0.15), hexc('2b2b2b'), 'hand.R')
    if kit.get('shield'):
        b.box((0.42, 0.04, 0.55), (-0.26, 0.09, 1.08), TEAM, 'forearm.L', taper=0.85)
        b.box((0.08, 0.05, 0.08), (-0.26, 0.12, 1.08), METAL, 'forearm.L')
    return b.to_object()

# ---------------- poses ----------------
def S(t, ph=0.0):
    return math.sin(2 * math.pi * (t + ph))

def carry(style):
    if style == 'bow':
        return {'upper_arm.L': (25, 0, 0), 'forearm.L': (20, 0, 0), 'upper_arm.R': (5, 0, 0), 'forearm.R': (15, 0, 0)}
    if style == 'spear':
        return {'upper_arm.R': (15, 0, -5), 'forearm.R': (150, 0, 0), 'upper_arm.L': (30, 0, 0), 'forearm.L': (50, 0, 0)}
    return {'upper_arm.R': (10, 0, -5), 'forearm.R': (160, 0, 0), 'upper_arm.L': (5, 0, 0), 'forearm.L': (10, 0, 0)}

def mix(a, b, k):
    out = {}
    for key in set(a) | set(b):
        va = a.get(key, (0, 0, 0)); vb = b.get(key, (0, 0, 0))
        out[key] = tuple(va[i] * (1 - k) + vb[i] * k for i in range(3))
    return out

def legs(t, amp, knee, bob, lean):
    p = {'thigh.R': (amp * S(t), 0, 0), 'thigh.L': (-amp * S(t), 0, 0),
         'shin.R': (-knee * max(0, S(t, 0.25)) - 5, 0, 0), 'shin.L': (-knee * max(0, S(t, 0.75)) - 5, 0, 0),
         'spine': (-lean, 0, 0), '_loc': (0, 0, -bob * abs(S(t, 0.25)))}
    return p

def clip_idle(style):
    def f(t):
        p = dict(carry(style)); p['chest'] = (2 * S(t), 0, 0); p['head'] = (0, 0, 6 * S(t, 0.1)); return p
    return f

def clip_walk(style):
    def f(t):
        p = legs(t, 24, 35, 0.03, 3); p.update(carry(style))
        if style != 'bow':
            p['upper_arm.L'] = (-18 * S(t), 0, 0)
        p['chest'] = (0, 0, 4 * S(t)); return p
    return f

def clip_run(style):
    def f(t):
        p = legs(t, 42, 70, 0.07, 14)
        if style in ('gun', 'spear'):  # weapon levelled for the charge
            p.update({'upper_arm.R': (55, 0, 0), 'forearm.R': (35, 0, 0), 'upper_arm.L': (60, 0, 15), 'forearm.L': (30, 0, 0)})
        else:
            p.update(carry(style)); p['upper_arm.R'] = (-35 * S(t), 0, 0)
        return p
    return f

def clip_fire(style):
    def f(t):
        base = carry(style)
        if style == 'bow':
            aim = {'upper_arm.L': (88, 0, -8), 'forearm.L': (0, 0, 0), 'upper_arm.R': (85, 0, 25), 'forearm.R': (-10, 0, 120 * min(1, t * 3)), 'head': (0, 0, -10)}
        elif style == 'spear':  # throw / jab overhead
            aim = {'upper_arm.R': (150 - 80 * max(0, min(1, (t - 0.3) * 4)), 0, 0), 'forearm.R': (10, 0, 0), 'chest': (-10 * max(0, min(1, (t - 0.3) * 4)), 0, 0), 'upper_arm.L': (40, 0, 0)}
        else:
            aim = {'upper_arm.R': (82, 0, 18), 'forearm.R': (8, 0, -20), 'upper_arm.L': (78, 0, -25), 'forearm.L': (25, 0, 0), 'head': (-6, 0, 8), 'chest': (0, 0, 12)}
        # 0-.2 raise, .2-.3 aim, .3 FIRE (recoil), .45-.9 reload, back to ready
        if t < 0.2:
            p = mix(base, aim, t / 0.2)
        elif t < 0.45:
            p = dict(aim)
            if 0.28 < t < 0.38 and style == 'gun':
                k = 1 - abs(t - 0.31) / 0.07
                p['chest'] = (8 * k, 0, 12); p['upper_arm.R'] = (82 + 10 * k, 0, 18)
        elif t < 0.9:
            k = (t - 0.45) / 0.45
            reload = {'upper_arm.R': (30, 0, 0), 'forearm.R': (90 + 30 * S(k * 3), 0, 0), 'upper_arm.L': (40, 0, 10), 'forearm.L': (60, 0, 0), 'chest': (-8, 0, 0), 'head': (-12, 0, 0)}
            if style == 'bow':
                reload = {'upper_arm.R': (20 + 10 * S(k), 0, 40), 'forearm.R': (90, 0, 0), 'upper_arm.L': (40, 0, 0)}
            p = mix(aim, reload, min(1, k * 4)) if k < 0.25 else reload
        else:
            p = mix(aim if style == 'bow' else base, base, (t - 0.9) / 0.1)
        p.update({'thigh.R': (-8, 0, 0), 'thigh.L': (14, 0, 0), 'shin.L': (-14, 0, 0)})
        return p
    return f

def clip_melee(style):
    def f(t):
        k = 0.5 - 0.5 * math.cos(2 * math.pi * t)
        p = {'upper_arm.R': (40 + 50 * k, 0, -10), 'forearm.R': (60 - 55 * k, 0, 0), 'upper_arm.L': (50 + 30 * k, 0, 10),
             'forearm.L': (40, 0, 0), 'chest': (-5 - 15 * k, 0, 15 - 25 * k), 'spine': (-5, 0, 0),
             'thigh.R': (-15, 0, 0), 'thigh.L': (25 + 8 * k, 0, 0), 'shin.L': (-20, 0, 0), 'shin.R': (-10, 0, 0),
             '_loc': (0, 0.1 * k, -0.04)}
        if style == 'bow':  # archers fight with a short blade: overhead chop
            p['upper_arm.R'] = (150 - 110 * k, 0, 0); p['forearm.R'] = (30, 0, 0)
        return p
    return f

def clip_die(style):
    def f(t):
        base = carry(style)
        if t < 0.25:
            k = t / 0.25
            p = mix(base, {'chest': (15, 0, 10), 'head': (25, 0, 0), 'upper_arm.R': (60, 0, 30), 'upper_arm.L': (50, 0, -40),
                           'thigh.R': (30, 0, 0), 'thigh.L': (35, 0, 0), 'shin.R': (-60, 0, 0), 'shin.L': (-55, 0, 0)}, k)
            p['_loc'] = (0, -0.05 * k, -0.15 * k)
        else:
            k = min(1, (t - 0.25) / 0.55)
            k = k * k * (3 - 2 * k)
            p = {'root': (88 * k, 0, 8 * k), 'chest': (15 - 10 * k, 0, 10), 'head': (25 - 30 * k, 0, 0),
                 'upper_arm.R': (60 + 80 * k, 0, 30 + 30 * k), 'upper_arm.L': (50 + 70 * k, 0, -40 - 30 * k),
                 'thigh.R': (30 - 20 * k, 0, 0), 'thigh.L': (35 - 10 * k, 0, 0), 'shin.R': (-60 + 50 * k, 0, 0), 'shin.L': (-55 + 30 * k, 0, 0),
                 '_loc': (0, -0.05 - 0.2 * k, -0.15 + 0.27 * k)}
        return p
    return f

CLIPS = [('idle', 24, True, clip_idle), ('walk', 24, True, clip_walk), ('run', 16, True, clip_run),
         ('fire', 48, True, clip_fire), ('melee', 20, True, clip_melee), ('die', 30, False, clip_die)]

def main():
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for vid, kit in VARIANTS.items():
        if only and vid not in only:
            continue
        for lod in (0, 1):
            common.reset_scene()
            rig = rigkit.build_armature('soldier', BONES)
            body = build_body(f'{vid}_lod{lod}', kit, detail=(lod == 0))
            rigkit.bind(body, rig)
            clips = [(n, nf, loop, fn(kit['style'])) for n, nf, loop, fn in CLIPS]
            base = os.path.join(common.VAT, f'{vid}_lod{lod}')
            rigkit.bake(body, rig, clips, base)
            rigkit.export_static_copy(body, os.path.join(common.MODELS, f'soldier_{vid}_lod{lod}.glb'))
            if lod == 0:
                rigkit.export_rigged(body, rig, os.path.join(common.MODELS, f'soldier_{vid}_rigged.glb'))
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, f'soldier_{vid}.blend'))

if __name__ == '__main__':
    main()
