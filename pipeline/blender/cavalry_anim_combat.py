"""anim-combat-v1 horse gaits (MOTION ONLY): appends hv_* clips to the cavalry VATs after the 144 legacy rows.

Does not touch cavalry.py, the horse/rider meshes, textures, materials, GLBs or the legacy rows: the mesh is rebuilt
with cavalry.build() purely to evaluate vertex positions, the legacy idle rows are re-evaluated and checked against the
stored ones (same vertex order), and the old bytes are copied verbatim. Idempotent via json 'base_frames'.

Gaits are procedural with per-leg footfall phases and 2-bone IK so hooves are planted during stance:
  walk   four-beat lateral sequence  LH -> LF -> RH -> RF  (duty 0.62), head nods twice per stride
  trot   two-beat diagonals (LH+RF, RH+LF), suspension, head steady, body bobs twice per stride
  canter three-beat right lead: LH, then RH+LF diagonal, then leading RF, suspension; body rocks, neck counter-swings
  gallop four-beat transverse: LH, RH, LF, RF, suspension; neck extends/flexes once per stride
Transition clips blend leg phases/stride/body motion over one cycle (phase 0 of gait A -> phase 0 of gait B).
Usage: blender -b --python pipeline/blender/cavalry_anim_combat.py -- bake [variant ...] | sheet <variant> <png>
"""
import sys, os, math, json, struct
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import common, rigkit, cavalry

BASE_FRAMES = 144
PI2 = 2 * math.pi
# legs: name -> hip (y, z), x side; upper/lower lengths from cavalry.BONES (read-only)
LEGS = {}
for bn, h, t, p in cavalry.BONES:
    if bn.endswith('_up'):
        LEGS[bn[:2]] = {'hip': (h[1], h[2]), 'a': h[2] - t[2]}
    if bn.endswith('_lo'):
        LEGS[bn[:2]]['b'] = h[2] - t[2]; LEGS[bn[:2]]['g'] = t[2]
PIVOT = (-0.55, 1.3)  # body bone head (y, z)

def ss(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def H(c, terms):
    """sum of harmonics: terms = [(n, amp, phase)] -> sum amp*cos(2pi n (c - phase))"""
    return sum(a * math.cos(PI2 * n * (c - p)) for n, a, p in terms)

# fl = +X side (rider's right? cavalry.py names) - only the phase pattern matters: the 'l' pair and 'r' pair alternate.
# Footfall (stance start) phase per leg, duty factor, half stride A (m), swing lift (front, hind), body channels.
GAITS = {
    'stand': dict(T=24, ph={'br': 0.0, 'fr': 0.25, 'bl': 0.5, 'fl': 0.75}, beta=0.62, A=0.0, lift=(0.0, 0.0), ch={}),
    'walk': dict(T=24, ph={'br': 0.0, 'fr': 0.25, 'bl': 0.5, 'fl': 0.75}, beta=0.62, A=0.26, lift=(0.13, 0.10), ch={
        'z': (-0.012, [(2, 0.012, 0.0)]), 'pitch': (0.0, [(2, 0.8, 0.0)]), 'roll': (0.0, [(1, 2.0, 0.35)]),
        'neck': (0.0, [(2, 4.0, 0.33 - 0.25)]), 'neck_z': (0.0, [(1, 2.5, 0.0)]), 'head': (0.0, [(2, -1.5, 0.08)]),
        'tail': (10.0, [(2, 2.0, 0.1)]), 'tail_z': (0.0, [(1, 6.0, 0.2)]), 'r_spine': (0.0, [(2, 1.2, 0.1)])}),
    'trot': dict(T=16, ph={'br': 0.875, 'fr': 0.375, 'bl': 0.375, 'fl': 0.875}, beta=0.42, A=0.30, lift=(0.20, 0.16), ch={
        'z': (-0.03, [(2, 0.035, 0.335)]), 'pitch': (0.0, [(2, 0.6, 0.3)]), 'roll': (0.0, [(2, 0.8, 0.2)]),
        'neck': (2.0, [(2, -1.0, 0.335)]), 'neck_z': (0.0, [(1, 1.0, 0.1)]), 'head': (0.0, [(2, 1.0, 0.335)]),
        'tail': (18.0, [(2, 3.0, 0.335)]), 'tail_z': (0.0, [(1, 4.0, 0.1)]), 'r_spine': (-2.0, [(2, 1.5, 0.385)])}),
    'canter': dict(T=14, ph={'br': 0.125, 'fr': 0.375, 'bl': 0.375, 'fl': 0.625}, beta=0.33, A=0.34, lift=(0.24, 0.20), ch={
        'z': (-0.045, [(1, 0.05, 0.05)]), 'y': (0.0, [(1, 0.02, 0.5)]), 'pitch': (0.0, [(1, 4.0, 0.25)]),
        'roll': (1.5, [(1, 1.0, 0.6)]), 'neck': (3.0, [(1, -5.0, 0.25)]), 'neck_z': (2.0, []), 'head': (0.0, [(1, 2.0, 0.3)]),
        'tail': (25.0, [(1, 5.0, 0.3)]), 'tail_z': (0.0, [(1, 3.0, 0.1)]), 'r_spine': (-5.0, [(1, -3.0, 0.27)])}),
    'gallop': dict(T=12, ph={'br': 0.125, 'fr': 0.475, 'bl': 0.225, 'fl': 0.575}, beta=0.25, A=0.38, lift=(0.30, 0.24), ch={
        'z': (-0.065, [(1, 0.06, 0.975)]), 'y': (0.0, [(1, 0.03, 0.6)]), 'pitch': (0.0, [(1, 5.0, 0.3)]),
        'roll': (0.0, [(1, 1.0, 0.4)]), 'neck': (-4.0, [(1, -7.0, 0.7)]), 'neck_z': (0.0, []), 'head': (6.0, [(1, 3.0, 0.7)]),
        'tail': (35.0, [(1, 6.0, 0.4)]), 'tail_z': (0.0, [(1, 2.0, 0.1)]), 'r_spine': (-12.0, [(1, -3.5, 0.32)])}),
}
ORDER = ['stand', 'walk', 'trot', 'canter', 'gallop']

def v_nom(g):
    G = GAITS[g]
    return 0.0 if G['A'] == 0 else 2 * G['A'] / (G['beta'] * G['T'] / 24.0)

def chan(G, name, c):
    off, terms = G['ch'].get(name, (0.0, []))
    return off + H(c, terms)

def ik(hip, foot, a, b, knee_fwd):
    dy, dz = foot[0] - hip[0], foot[1] - hip[1]
    D = math.hypot(dy, dz); D = max(1e-4, min(D, (a + b) * 0.9995))
    al = math.atan2(dy, -dz)
    be = math.acos(max(-1, min(1, (a * a + D * D - b * b) / (2 * a * D))))
    t1 = al + be if knee_fwd else al - be
    ky, kz = hip[0] + a * math.sin(t1), hip[1] - a * math.cos(t1)
    t2 = math.atan2(foot[0] - ky, -(foot[1] - kz))
    return t1, t2

def body_frame(z, y, pitch_deg):
    ph = math.radians(pitch_deg)
    def tf(p):
        qy, qz = p[0] - PIVOT[0], p[1] - PIVOT[1]
        return (PIVOT[0] + y + qy * math.cos(ph) - qz * math.sin(ph), PIVOT[1] + z + qy * math.sin(ph) + qz * math.cos(ph))
    return tf

def hoof_target(Gs, k, leg, c, extra=(0.0, 0.0)):
    """blend of two gait parameter sets (k = weight of second) -> hoof (y, z) in armature space"""
    G0, G1 = Gs
    ph = G0['ph'][leg] * (1 - k) + G1['ph'][leg] * k
    beta = G0['beta'] * (1 - k) + G1['beta'] * k
    A = G0['A'] * (1 - k) + G1['A'] * k
    fi = 0 if leg[0] == 'f' else 1
    lift = G0['lift'][fi] * (1 - k) + G1['lift'][fi] * k
    u = (c - ph) % 1.0
    hy, hz = LEGS[leg]['hip']; g = LEGS[leg]['g']
    if u < beta:
        s = u / beta; y = A - 2 * A * s; z = g
    else:
        s = (u - beta) / (1 - beta)
        if leg[0] == 'f':  # fore: fold early, reach forward late
            y = -A + 2 * A * ss(s ** 0.8); z = g + lift * math.sin(math.pi * min(1, s ** 0.75)) ** 1.2
        else:
            y = -A + 2 * A * ss(s); z = g + lift * math.sin(math.pi * s)
    return (hy + y + extra[0], z + extra[1])

def gait_pose(kit, g0, g1, k, c, lean_lance=None):
    G0, G1 = GAITS[g0], GAITS[g1]
    ch = lambda n: chan(G0, n, c) * (1 - k) + chan(G1, n, c) * k
    z, y, pitch, roll = ch('z'), ch('y'), ch('pitch'), ch('roll')
    tf = body_frame(z, y, pitch)
    p = {'_loc': (0, y, z), 'body': (pitch, roll, 0)}
    for leg, L in LEGS.items():
        hip = tf(L['hip'])
        foot = hoof_target((G0, G1), k, leg, c)
        t1, t2 = ik(hip, foot, L['a'], L['b'], knee_fwd=(leg[0] == 'f'))
        p[leg + '_up'] = (math.degrees(t1) - pitch, 0, 0)
        p[leg + '_lo'] = (math.degrees(t2 - t1), 0, 0)
    p['neck'] = (ch('neck') - 0.5 * pitch, 0, ch('neck_z'))
    p['head'] = (ch('head'), 0, 0)
    p['tail'] = (ch('tail'), 0, ch('tail_z'))
    p.update(cavalry.rider_hold(kit))
    p['r_spine'] = (ch('r_spine') - 0.8 * pitch, -0.6 * roll, 0)
    p['r_head'] = (-0.4 * (ch('r_spine') - 0.8 * pitch) - 0.2 * pitch, 0, 0)
    if kit['weapon'] == 'lance':  # lance comes down to the level as the horse goes into the gallop (legacy 'run')
        w = {'stand': 0, 'walk': 0, 'trot': 0, 'canter': 0.35, 'gallop': 1.0}
        lv = w[g0] * (1 - k) + w[g1] * k
        p['r_arm.R'] = (25 + 35 * lv, 0, 0); p['r_fore.R'] = (60 - 18 * lv, 0, 0)
    return p

def loop_clip(kit, g):
    return lambda t: gait_pose(kit, g, g, 0.0, t)

def trans_clip(kit, g0, g1):
    return lambda t: gait_pose(kit, g0, g1, ss(t), t)

def stand_clip(kit):
    def f(t):
        p = gait_pose(kit, 'stand', 'stand', 0.0, 0.0)
        w = ss((t - 0.1) / 0.25) * (1 - ss((t - 0.65) / 0.25))  # weight onto the other hind, rest one hind hoof
        tf = body_frame(-0.006 * w + 0.004 * math.sin(PI2 * 3 * t), 0.0, 0.0)
        for leg in LEGS:
            ex = (0.06 * w, 0.03 * w) if leg == 'bl' else (0.0, 0.0)
            L = LEGS[leg]
            t1, t2 = ik(tf(L['hip']), hoof_target((GAITS['stand'], GAITS['stand']), 0, leg, 0.0, ex), L['a'], L['b'], leg[0] == 'f')
            p[leg + '_up'] = (math.degrees(t1), 0, 0); p[leg + '_lo'] = (math.degrees(t2 - t1), 0, 0)
        p['_loc'] = (0, 0, -0.006 * w + 0.004 * math.sin(PI2 * 3 * t))
        p['body'] = (0, -2.0 * w, 0)
        p['neck'] = (6 * math.sin(PI2 * t), 0, 5 * math.sin(PI2 * t) * (1 - w * 0.5))
        p['head'] = (-3 * math.sin(PI2 * 2 * t), 0, 0)
        p['tail'] = (8 + 3 * math.sin(PI2 * 2 * t), 0, 10 * math.sin(PI2 * 2 * t))
        return p
    return f

def melee_clip(kit):
    """standing fight: horse shifts and steps in place, tosses head; rider strikes (same arm motion as legacy attack)"""
    def f(t):
        kk = 0.5 - 0.5 * math.cos(PI2 * t)
        p = gait_pose(kit, 'stand', 'walk', 0.25, t)
        p['neck'] = (-6 * kk + 3, 0, 6 * math.sin(PI2 * t))
        p['head'] = (8 * math.sin(PI2 * 2 * t), 0, 0)
        p['body'] = (p['body'][0] + 1.5 * math.sin(PI2 * t), p['body'][1], 2 * math.sin(PI2 * t))
        if kit['weapon'] == 'lance':
            p.update({'r_arm.R': (75, 0, 0), 'r_fore.R': (27 + 18 * kk, 0, 0), 'r_spine': (-20 * kk, 0, 0), 'r_arm.L': (35, 0, 0), 'r_fore.L': (50, 0, 0)})
        else:
            p.update({'r_arm.R': (170 - 120 * kk, 0, 20 * kk), 'r_fore.R': (30, 0, 0), 'r_spine': (-5 - 15 * kk, 0, 10 * kk), 'r_arm.L': (35, 0, 0), 'r_fore.L': (55, 0, 0)})
        p['r_head'] = (5 * kk, 0, 0)
        return p
    return f

def combat_clips(kit):
    out = [('hv_stand', 48, True, stand_clip(kit)), ('hv_melee', 24, True, melee_clip(kit))]
    for g in ORDER[1:]:
        out.append((f'hv_{g}', GAITS[g]['T'], True, loop_clip(kit, g)))
    for a, b in zip(ORDER[:-1], ORDER[1:]):
        na = 'idle' if a == 'stand' else a
        out.append((f'hv_{na}_{b}', GAITS[b]['T'] if a == 'stand' else (GAITS[a]['T'] + GAITS[b]['T']) // 2, False, trans_clip(kit, a, b)))
        out.append((f'hv_{b}_{na}', GAITS[b]['T'] if a == 'stand' else (GAITS[a]['T'] + GAITS[b]['T']) // 2, False, trans_clip(kit, b, a)))
    return out

# ---------- baking ----------
def setup(vid, lod):
    common.reset_scene()
    kit = cavalry.VARIANTS[vid]
    rig = rigkit.build_armature('horse', cavalry.BONES)
    body = cavalry.build(f'{vid}_lod{lod}', kit, lod == 0)
    rigkit.bind(body, rig)
    return rig, body, kit

def eval_frame(rig, body, pose):
    rigkit.apply_pose(rig, pose)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    vals = [(v.co.x, v.co.z, -v.co.y) for v in me.vertices]
    ev.to_mesh_clear()
    return vals

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
    legacy = {c[0]: c for c in cavalry.clips(kit)}
    err = 0.0
    for name, f in (('idle', 0), ('idle', 7), ('walk', 5), ('run', 3)):
        st = meta['clips'][name]['start']; nf = legacy[name][1]
        vals = eval_frame(rig, body, legacy[name][3](f / nf))
        ref = struct.unpack_from(f'<{nv * 3}f', old, (st + f) * nv * 12)
        err = max(err, max(abs(a - b) for i, v in enumerate(vals) for a, b in zip(v, ref[i * 3:i * 3 + 3])))
    assert err < 1e-4, f'legacy re-evaluation differs from stored rows by {err}'
    print(f'{vid} lod{lod}: legacy check max err {err:.2e}')
    data = bytearray(old)
    clips = {k: v for k, v in meta['clips'].items() if v['start'] < nb}
    lo = list(meta['aabb'][0]); hi = list(meta['aabb'][1])
    row = nb
    for name, nf, loop, fn in combat_clips(kit):
        for f in range(nf):
            t = f / nf if loop else f / max(1, nf - 1)
            for x, y, z in eval_frame(rig, body, fn(t)):
                data += struct.pack('<3f', x, y, z)
                lo = [min(lo[0], x), min(lo[1], y), min(lo[2], z)]; hi = [max(hi[0], x), max(hi[1], y), max(hi[2], z)]
        clips[name] = {'start': row, 'count': nf, 'loop': loop}
        g = name[3:]
        if g in GAITS and v_nom(g) > 0:
            clips[name]['v_nom'] = round(v_nom(g), 3)
        row += nf
    assert bytes(data[:len(old)]) == old
    meta['clips'] = clips; meta['frames'] = row; meta['base_frames'] = nb; meta['aabb'] = [lo, hi]
    open(base + '.vat', 'wb').write(bytes(data))
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    print('appended', base, nv, 'verts rows', nb, '->', row)

def sheet(vid, out_png):
    """side-view contact sheet: 8 frames of each gait loop (workbench)"""
    rig, body, kit = setup(vid, 0)
    cl = {c[0]: c for c in combat_clips(kit)}
    rows = ['hv_walk', 'hv_trot', 'hv_canter', 'hv_gallop', 'hv_stand']
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
    sc.render.resolution_x = 300; sc.render.resolution_y = 260
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 3.4
    cam.location = (5.0, 0.2, 1.2); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    me = bpy.data.meshes.new('ground'); me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    gr = bpy.data.objects.new('ground', me); sc.collection.objects.link(gr)
    tmp = []
    for r in rows:
        for i in range(8):
            rigkit.apply_pose(rig, cl[r][3](i / 8)); bpy.context.view_layer.update()
            p = f'/tmp/hsheet_{len(tmp):02d}.png'; sc.render.filepath = p
            bpy.ops.render.render(write_still=True); tmp.append(p)
    import subprocess
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + sum([['-i', p] for p in tmp], []) +
                   ['-filter_complex', f'xstack=inputs={len(tmp)}:layout=' + '|'.join(f'{(k % 8) * 300}_{(k // 8) * 260}' for k in range(len(tmp))), out_png])
    print('sheet', out_png, rows)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    mode = argv[0] if argv else 'bake'
    if mode == 'bake':
        for vid in (argv[1:] or list(cavalry.VARIANTS)):
            for lod in (0, 1):
                bake(vid, lod)
    elif mode == 'sheet':
        sheet(argv[1] if len(argv) > 1 else 'em_cuirassier', argv[2] if len(argv) > 2 else '/workspace/ic_anim/out/horse_sheet.png')
    elif mode == 'speeds':
        print({g: round(v_nom(g), 2) for g in ORDER})
