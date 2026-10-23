"""Combat animation v1 (Rob, proto/anim-combat-v1): extra c19sr musket clips, appended to char_anim.CLIPS so they
bake AFTER BJORN's reserved rows 0-263 (idle walk run fire melee die die_b). Never reorders / edits char_anim.py.

Clips (24 fps, rows appended in this order):
  mk_march   24 loop   marching step, stronger weight transfer than walk (same analytic feet -> no foot slide at 1.4 m/s)
  mk_aim     16 once   shoulder arms -> make ready -> present (last frame = levelled, held while waiting for the volley)
  mk_fire    12 once   present, shot on frame 1 (MK_SHOT_S), recoil, lower to priming position
  mk_reload  62 once   prime (cartridge -> mouth -> pan), musket upright, ram twice, return to shoulder arms
The json gets per-clip 'prop_tip' (Godot model space, one [x,y,z] per frame) = prop bone origin + local +Y * MUSKET muzzle,
the fallback for BJORN's 'weapon_tip' bone data (renderer reads weapon_tip first, then prop_tip).

Registration: importing this module appends the clips (idempotent). Bake with
  CHAR_OUT=<scratch> blender -b --python pipeline/blender/char_anim_combat.py -- bake [ids]
which registers the clips, runs char_build.bake() unchanged, then writes prop_tip into each json.
(Equivalent to `char_build.py -- bake` once char_build imports char_anim_combat; see ANIM_INTERFACE.md.)"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector
from char_geo import V
import char_anim as A
import char_rig as R

MK_SHOT_S = 1.0 / 24.0          # muzzle flash time inside mk_fire (s)
RESERVED_ROWS = 264             # BJORN's rows 0-263

def _stance():
    """firing stance (same as char_anim.fire's base)"""
    return A.merge(A.stand_legs(0.13, 0.12, -0.08, 12), {'hip': V(0.0, 0.0, -0.02), 'hipR': (0, 0, -18)})

def _aim_body():
    return A.merge(_stance(), {'spine': (-3, 0, -6), 'chest': (-3, 0, -6), 'neck': (-6, 6, 10), 'head': (-4, 10, 12),
                               'clavR': (0, 0, 6), 'clavL': (0, 0, 0)})

def _prime(h):
    return A.merge(_stance(), {'spine': (-6, 0, -3), 'chest': (-4, 0, -2), 'neck': (-8, 0, 0), 'head': (-8 + 4 * min(h, 1), 0, 0)}, A.prime_pos(h))

def _ram(st):
    return A.merge(_stance(), {'hipR': (0, 0, -8), 'spine': (-8, 0, 2), 'chest': (-6, 0, 4), 'neck': (-10, 0, 0), 'head': (-14, 0, 4)}, A.reload_pos(st))

def _shoulder():
    return A.merge(A.stand_legs(), {'hip': V(0, 0, -0.012), 'spine': (-1, 0, 0), 'chest': (-1, 0, 0), 'neck': (-2, 0, 0), 'head': (-2, 0, 0)},
                   A.shoulder_arms(), A.free_arm_R(0, 2, 10))

def mk_march(t, style='musket'):
    """drill march: walk's no-slide feet, more hip sway / roll, chest counter-rotation, steady head, small arm swing"""
    if style == 'rammer':
        return A.walk(t, style)
    sp = dict(A.walk(t, style))
    s1 = math.sin(2 * math.pi * (t + 0.12))
    sw = math.sin(2 * math.pi * (t - 0.05))                      # weight over the stance foot
    c2 = math.cos(4 * math.pi * (t - 0.3))
    sp['hip'] = V(0.026 * sw, 0.0, -0.04 + 0.024 * c2)          # lateral weight transfer + double bob
    sp['hipR'] = (-1.5, 3.0 * sw, 8 * s1)                        # pelvis drops over the swing leg, rotates with the stride
    sp['spine'] = (-4, -1.5 * sw, -5 * s1)
    sp['chest'] = (-1, -1.0 * sw, -4 * s1)                       # shoulders counter-rotate
    sp['neck'] = (0, 1.0 * sw, 3 * s1)
    sp['head'] = (-2, 1.5 * sw, 5 * s1)                          # eyes stay on the line of march
    sp.update(A.free_arm_R(14 * s1, 3, 14))
    return sp

def mk_aim(t, style='musket'):
    if style == 'rammer':
        return A.idle(0.0, style)
    k0 = _shoulder()
    k1 = A.merge(_stance(), {'spine': (-2, 0, -4), 'chest': (-2, 0, -4), 'neck': (-4, 0, 4), 'head': (-4, 0, 4)}, A.prime_pos(2.0))
    k2 = A.merge(_aim_body(), A.present(0.0))
    return A.keys(t, [(0.0, k0), (0.45, k1), (1.0, k2)])

def mk_fire(t, style='musket'):
    if style == 'rammer':
        return A.idle(0.0, style)
    s = t * (12 - 1) / 24.0                                      # seconds into the clip
    r = 0.0 if s < MK_SHOT_S else math.exp(-(s - MK_SHOT_S) * 12) * min(1.0, (s - MK_SHOT_S) / 0.03)
    sp = A.merge(_aim_body(), A.present(r))
    sp['chest'] = (-3 + 7 * r, 0, -6 + 3 * r); sp['head'] = (-4 + 7 * r, 10, 12)
    sp['hip'] = V(0, -0.02 * r, -0.02)
    if s > 0.25:
        sp = A.blend_spec(sp, _prime(0.0), A.ease((s - 0.25) / 0.21))
    return sp

def mk_reload(t, style='musket'):
    if style == 'rammer':
        return A.idle(0.0, style)
    s = t * (62 - 1) / 24.0                                      # 0 .. 2.54 s
    if s < 0.85:                                                 # bite cartridge, prime the pan
        return _prime(s / 0.85 * 2.0)
    if s < 1.05:
        return A.blend_spec(_prime(2.0), _ram(0.0), A.ease((s - 0.85) / 0.2))
    if s < 1.95:                                                 # pour + ram twice
        st = 0.5 - 0.5 * math.cos(2 * math.pi * 2 * (s - 1.05) / 0.9)
        return _ram(st)
    return A.blend_spec(_ram(0.0), _shoulder(), A.ease((s - 1.95) / 0.55))

COMBAT_CLIPS = [('mk_march', 24, True, mk_march), ('mk_aim', 16, False, mk_aim), ('mk_fire', 12, False, mk_fire),
                ('mk_reload', 62, False, mk_reload)]

def register():
    names = [c[0] for c in A.CLIPS]
    for c in COMBAT_CLIPS:
        if c[0] not in names:
            A.CLIPS.append(c)
    assert sum(c[1] for c in A.CLIPS[:7]) == RESERVED_ROWS, 'reserved rows 0-263 changed'

register()

def prop_tips(kid):
    """per clip, per frame: muzzle position in Godot model coords (prop origin + local +Y * MUSKET['muzzle'])"""
    style = 'rammer' if 'artillery' in kid else 'musket'
    along = R.MUSKET['muzzle'] if style == 'musket' else 1.1
    out = {}
    for cn, nf, loop, fn in A.CLIPS:
        pts = []
        for f in range(nf):
            t = f / nf if loop else f / max(1, nf - 1)
            p = A.solve(fn(t, style))
            w = p.P['prop'] @ Vector((0, along, 0))
            pts.append([round(w.x, 4), round(w.z, 4), round(-w.y, 4)])
        out[cn] = pts
    return out

def write_tips(kid):
    import common
    tips = prop_tips(kid)
    for lod in (0, 1):
        path = os.path.join(common.VAT, f'{kid}_lod{lod}.json')
        j = json.load(open(path))
        for cn, pts in tips.items():
            if cn in j['clips']:
                j['clips'][cn]['prop_tip'] = pts
        j['events'] = {'mk_fire': {'shot': MK_SHOT_S}}
        json.dump(j, open(path, 'w'), indent=1)
        print('prop_tip ->', path)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if argv and argv[0] == 'bake':
        import char_build
        os.makedirs(char_build.OUT + '/turn', exist_ok=True)
        ids = argv[1:] or ['c19sr_line']
        for kid in ids:
            for lod in (0, 1):
                char_build.bake(kid, lod, keep_blend=False)
            write_tips(kid)
    elif argv and argv[0] == 'poses':
        import char_build
        os.makedirs(char_build.OUT + '/turn', exist_ok=True)
        char_build.poses(argv[1] if len(argv) > 1 else 'c19sr_line', [c[0] for c in COMBAT_CLIPS], tag='combat')
