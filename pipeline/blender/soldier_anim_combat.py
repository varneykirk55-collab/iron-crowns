"""Combat animation v1 (Rob, proto/anim-combat-v1): extra clips for the LEGACY 15-bone soldier rig (soldiers.BONES),
used by the 1300 spear levy (med_spear). Appends rows AFTER the existing 162 rows (idle walk run fire melee die) of
game/assets/vat/med_spear_lod{0,1}.vat without touching them; glb / blend / soldiers.py are not modified.

  blender -b --python pipeline/blender/soldier_anim_combat.py -- bake  [variants]   # default: med_spear
  blender -b --python pipeline/blender/soldier_anim_combat.py -- sheet [variant]    # pose contact sheet png (review)

Safety: the vertex count must match the json, a re-evaluated 'idle' must reproduce rows 0..23 (same vertex order),
the old rows are copied byte-for-byte from the existing file (idempotent: json 'base_frames' marks the cut).
Per-frame 'weapon_tip' (spear blade point, Godot model coords) is written for every new clip."""
import sys, os, math, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
import common, rigkit, soldiers

S = soldiers.S
BASE_FRAMES = 162
SPEAR_TIP = {'med_spear': ('hand.R', Vector((0.24, 0.0, 0.89 - 2.3 * 0.85 - 0.24)))}   # med_kit.spearman blade point (rest)

def ss(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def mix(a, b, k):
    out = soldiers.mix(a, b, k)
    la = a.get('_loc', (0, 0, 0)); lb = b.get('_loc', (0, 0, 0))
    out['_loc'] = tuple(la[i] * (1 - k) + lb[i] * k for i in range(3))
    return out

def keys(t, ks, ease=ss):
    """ks: [(time, pose), ...] sorted; eased piecewise blend"""
    if t <= ks[0][0]:
        return dict(ks[0][1])
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t <= t1:
            return mix(a, b, ease((t - t0) / max(1e-6, t1 - t0)))
    return dict(ks[-1][1])

def M(*ds):
    out = {}
    for d in ds:
        out.update(d)
    return out

# ---------- building blocks (degrees, armature axes; +X swings a limb forward, spine -X leans forward) ----------
SHIELD_UP = {'upper_arm.L': (62, 0, -18), 'forearm.L': (-58, 0, 4), 'hand.L': (0, 0, 0)}     # heater shield in front of the chest
SHIELD_CARRY = {'upper_arm.L': (30, 0, -8), 'forearm.L': (-26, 0, 0)}
STANCE = {'thigh.L': (24, 0, 4), 'shin.L': (-20, 0, 0), 'thigh.R': (-14, 0, -4), 'shin.R': (-12, 0, 0),
          'hips': (0, 0, -10), 'spine': (-6, 0, 0), '_loc': (0.0, 0.0, -0.055)}             # left foot forward, knees soft

def guard(t=0.0):
    b = S(t)
    p = M(STANCE, SHIELD_UP, {'chest': (-2, 0, -6), 'head': (4, 0, 14),
                              'upper_arm.R': (16 + 2 * b, 0, 14), 'forearm.R': (70 - 2 * b, 0, 0)})   # spear levelled, point slightly low
    p['_loc'] = (0.012 * b, 0.015 * S(t, 0.25), -0.055 + 0.008 * S(t * 2))                          # weight shift
    return p

CHAMBER = M(STANCE, SHIELD_UP, {'chest': (4, 0, -28), 'spine': (-2, 0, 0), 'head': (2, 0, 26),
                                'upper_arm.R': (-32, 0, 26), 'forearm.R': (116, 0, 0), '_loc': (0, -0.09, -0.06)})
STRIKE = M(SHIELD_UP, {'thigh.L': (42, 0, 4), 'shin.L': (-34, 0, 0), 'thigh.R': (-28, 0, -4), 'shin.R': (-4, 0, 0),
                       'hips': (0, 0, -2), 'spine': (-14, 0, 0), 'chest': (-8, 0, 22), 'head': (12, 0, -14),
                       'upper_arm.R': (86, 0, -14), 'forearm.R': (6, 0, 0),
                       'upper_arm.L': (56, 0, -30), '_loc': (0, 0.3, -0.1)})

def clip_pk_advance(t):
    """steady advance: spear upright on the shoulder, shield carried, hip sway + counter-rotation"""
    p = soldiers.legs(t, 24, 36, 0.035, 3)
    p.update({'upper_arm.R': (14 + 4 * S(t), 0, -5), 'forearm.R': (148, 0, 0)})
    p.update({'upper_arm.L': (26 - 6 * S(t), 0, -8), 'forearm.L': (-22, 0, 0)})
    p['hips'] = (0, 3 * S(t, 0.25), 7 * S(t))
    p['spine'] = (-4, 0, -4 * S(t))
    p['chest'] = (0, -2 * S(t, 0.25), -4 * S(t))
    p['head'] = (0, 2 * S(t, 0.25), 2 * S(t))
    p['_loc'] = (0.028 * S(t, 0.25), 0.0, p['_loc'][2])
    return p

def clip_pk_charge(t):
    """charge at the run: spear levelled underarm, shield up"""
    p = soldiers.legs(t, 40, 68, 0.06, 12)
    p.update(SHIELD_UP)
    p.update({'upper_arm.R': (30 + 3 * S(t), 0, 10), 'forearm.R': (58, 0, 0), 'chest': (0, 0, -10 + 3 * S(t)),
              'hips': (0, 0, 8 * S(t)), 'head': (6, 0, 10)})
    return p

def clip_pk_guard(t):
    return guard(t)

def clip_pk_thrust(t):
    return keys(t, [(0.0, guard(0)), (0.32, CHAMBER), (0.56, STRIKE), (1.0, mix(STRIKE, CHAMBER, 0.12))])

def clip_pk_recover(t):
    return keys(t, [(0.0, mix(STRIKE, CHAMBER, 0.12)), (0.45, mix(CHAMBER, guard(0), 0.5)), (1.0, guard(0))])

HIT = M(STANCE, {'thigh.L': (14, 0, 4), 'shin.L': (-12, 0, 0), 'thigh.R': (-22, 0, -4), 'shin.R': (-16, 0, 0),
                 'spine': (8, 0, 0), 'chest': (12, 0, -22), 'head': (18, 0, 16),
                 'upper_arm.R': (-4, 0, 26), 'forearm.R': (100, 0, 0), 'upper_arm.L': (74, 0, -30), 'forearm.L': (-50, 0, 0),
                 '_loc': (0, -0.14, -0.07)})

def clip_pk_hit(t):
    return keys(t, [(0.0, guard(0)), (0.18, HIT), (0.4, HIT), (1.0, guard(0))])

def clip_pk_collapse(t):
    rec = HIT
    kneel = M({'thigh.L': (62, 0, 6), 'shin.L': (-104, 0, 0), 'thigh.R': (40, 0, -6), 'shin.R': (-118, 0, 0),
               'spine': (-22, 0, 0), 'chest': (-6, 0, -10), 'head': (-24, 0, 10),
               'upper_arm.R': (40, 0, 16), 'forearm.R': (44, 0, 0), 'upper_arm.L': (36, 0, -10), 'forearm.L': (-10, 0, 0),
               '_loc': (0, -0.05, -0.4)})
    down = M({'root': (0, 84, 0), 'thigh.L': (44, 0, 0), 'shin.L': (-60, 0, 0), 'thigh.R': (30, 0, 0), 'shin.R': (-74, 0, 0),
              'spine': (-14, 0, 0), 'chest': (-4, 0, 0), 'head': (-10, 0, -20),
              'upper_arm.R': (70, 0, 40), 'forearm.R': (30, 0, 0), 'upper_arm.L': (64, 0, -20), 'forearm.L': (-16, 0, 0),
              '_loc': (-0.1, -0.05, 0.13)})
    return keys(t, [(0.0, guard(0)), (0.1, rec), (0.42, kneel), (0.8, down), (1.0, down)])

def clip_pk_withdraw(t):
    """back away from the enemy: guard upper body, reversed stepping, glance over the shoulder"""
    p = soldiers.legs(1.0 - t, 20, 30, 0.025, -2)
    p.update(SHIELD_UP)
    p.update({'upper_arm.R': (18, 0, 14), 'forearm.R': (74, 0, 0), 'chest': (2, 0, -8 + 3 * S(t)),
              'hips': (0, 0, -5 * S(t)), 'head': (0, 0, 30 * ss(abs(S(t, 0.1))) - 6)})
    return p

def clip_pk_flee(t):
    """run away, spear carried high, shield arm pumping"""
    p = soldiers.legs(t, 44, 76, 0.07, 18)
    p.update({'upper_arm.R': (26 + 8 * S(t), 0, -6), 'forearm.R': (128, 0, 0),
              'upper_arm.L': (-30 * S(t), 0, -6), 'forearm.L': (40, 0, 0),
              'hips': (0, 0, 9 * S(t)), 'chest': (0, 0, -7 * S(t)), 'head': (10, 0, 0)})
    return p

COMBAT_CLIPS = [('pk_advance', 24, True, clip_pk_advance), ('pk_charge', 16, True, clip_pk_charge),
                ('pk_guard', 48, True, clip_pk_guard), ('pk_thrust', 14, False, clip_pk_thrust),
                ('pk_recover', 12, False, clip_pk_recover), ('pk_hit', 14, False, clip_pk_hit),
                ('pk_collapse', 38, False, clip_pk_collapse), ('pk_withdraw', 24, True, clip_pk_withdraw),
                ('pk_flee', 16, True, clip_pk_flee)]
EVENTS = {'pk_thrust': {'contact': 0.56 * 13 / 24.0}}

# ---------- baking ----------
def setup(vid, lod):
    common.reset_scene()
    kit = soldiers.VARIANTS[vid]
    rig = rigkit.build_armature('soldier', soldiers.BONES)
    body = soldiers.build_body(f'{vid}_lod{lod}', kit, detail=(lod == 0))
    rigkit.bind(body, rig)
    return rig, body, kit

def eval_frame(rig, body, pose):
    rigkit.apply_pose(rig, pose)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(deps)
    me = ev.to_mesh()
    vals = []
    for v in me.vertices:
        x, y, z = v.co
        vals.append((x, z, -y))
    ev.to_mesh_clear()
    return vals

def tip_of(rig, vid):
    bone, rest = SPEAR_TIP[vid]
    pb = rig.pose.bones[bone]
    w = rig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ rest
    return [round(w.x, 4), round(w.z, 4), round(-w.y, 4)]

def bake(vid, lod):
    base = os.path.join(common.VAT, f'{vid}_lod{lod}')
    meta = json.load(open(base + '.json'))
    nb = meta.get('base_frames', meta['frames'])
    assert nb == BASE_FRAMES, f'{base}: expected {BASE_FRAMES} base rows, got {nb}'
    raw = open(base + '.vat', 'rb').read()
    nv = meta['vertices']
    old = raw[:nb * nv * 12]
    rig, body, kit = setup(vid, lod)
    assert len(body.data.vertices) == nv, f'vertex count {len(body.data.vertices)} != {nv}'
    # rows 0..23 (idle) must be reproduced -> same vertex order / same rig
    idle = soldiers.clip_idle(kit['style'])
    err = 0.0
    for f in (0, 7, 13):
        vals = eval_frame(rig, body, idle(f / 24))
        ref = struct.unpack_from(f'<{nv * 3}f', old, f * nv * 12)
        err = max(err, max(abs(a - b) for v, i in zip(vals, range(nv)) for a, b in zip(v, ref[i * 3:i * 3 + 3])))
    assert err < 1e-4, f'idle re-evaluation differs from stored rows by {err}'
    print(f'{vid} lod{lod}: idle check max err {err:.2e}')
    data = bytearray(old)
    clips = {k: v for k, v in meta['clips'].items() if v['start'] < nb}
    lo = list(meta['aabb'][0]); hi = list(meta['aabb'][1])
    row = nb
    for name, nf, loop, fn in COMBAT_CLIPS:
        tips = []
        for f in range(nf):
            t = f / nf if loop else f / max(1, nf - 1)
            vals = eval_frame(rig, body, fn(t))
            for x, y, z in vals:
                data += struct.pack('<3f', x, y, z)
                lo = [min(lo[0], x), min(lo[1], y), min(lo[2], z)]; hi = [max(hi[0], x), max(hi[1], y), max(hi[2], z)]
            if vid in SPEAR_TIP:
                tips.append(tip_of(rig, vid))
        clips[name] = {'start': row, 'count': nf, 'loop': loop}
        if tips:
            clips[name]['weapon_tip'] = tips
        row += nf
    assert bytes(data[:len(old)]) == old
    meta['clips'] = clips
    meta['frames'] = row
    meta['base_frames'] = nb
    meta['aabb'] = [lo, hi]
    meta['events'] = EVENTS
    open(base + '.vat', 'wb').write(bytes(data))
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    print('appended', base, nv, 'verts rows', nb, '->', row)

def sheet(vid, out_png, cols=None):
    """contact sheet: chosen frames of each new clip, side view, workbench"""
    rig, body, kit = setup(vid, 0)
    frames = cols or [(n, t) for n, nf, loop, fn in COMBAT_CLIPS for t in ((0.0, 0.5) if loop else (0.0, 0.3, 0.56, 1.0))]
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
    sc.render.resolution_x = 360; sc.render.resolution_y = 420
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 4.2
    tmp = []
    fn = {c[0]: c[3] for c in COMBAT_CLIPS}
    for i, (n, t) in enumerate(frames):
        rigkit.apply_pose(rig, fn[n](t)); bpy.context.view_layer.update()
        for j, (loc, rot) in enumerate((((4.0, 0.6, 1.0), (math.radians(90), 0, math.radians(90))),
                                        ((2.6, 3.4, 1.4), (math.radians(80), 0, math.radians(142))))):
            cam.location = loc; cam.rotation_euler = rot
            p = f'/tmp/sheet_{i:02d}_{j}.png'; sc.render.filepath = p
            bpy.ops.render.render(write_still=True); tmp.append(p)
    import subprocess
    n = len(frames)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + sum([['-i', p] for p in tmp], []) +
                   ['-filter_complex', f'xstack=inputs={len(tmp)}:layout=' + '|'.join(f'{(k % 8) * 360}_{(k // 8) * 420}' for k in range(len(tmp))), out_png])
    print('sheet', out_png, [f'{a}@{b}' for a, b in frames])

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    mode = argv[0] if argv else 'bake'
    if mode == 'bake':
        for vid in (argv[1:] or ['med_spear']):
            for lod in (0, 1):
                bake(vid, lod)
    elif mode == 'sheet':
        sheet(argv[1] if len(argv) > 1 else 'med_spear', argv[2] if len(argv) > 2 else '/workspace/ic_anim/out/pk_sheet.png')
