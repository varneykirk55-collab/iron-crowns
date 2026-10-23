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
    'stand': dict(T=24, ph={'br': 0.0, 'fr': 0.25, 'bl': 0.5, 'fl': 0.75}, beta=0.62, A=0.0, E=(0.0, 0.0), lift=(0.0, 0.0), ch={}),
    'walk': dict(T=24, ph={'br': 0.0, 'fr': 0.25, 'bl': 0.5, 'fl': 0.75}, beta=0.62, A=0.26, E=(0.16, 0.12), lift=(0.24, 0.17), ch={
        'z': (-0.03, [(2, 0.02, 0.0)]), 'pitch': (0.0, [(2, 1.2, 0.0)]), 'roll': (0.0, [(1, 2.5, 0.35)]),
        'neck': (0.0, [(2, 9.0, 0.33 - 0.25)]), 'neck_z': (0.0, [(1, 3.5, 0.0)]), 'head': (0.0, [(2, -4.0, 0.08)]),
        'tail': (10.0, [(2, 2.0, 0.1)]), 'tail_z': (0.0, [(1, 6.0, 0.2)]), 'r_spine': (0.0, [(2, 1.2, 0.1)])}),
    'trot': dict(T=16, ph={'br': 0.875, 'fr': 0.375, 'bl': 0.375, 'fl': 0.875}, beta=0.42, A=0.30, E=(0.26, 0.22), lift=(0.36, 0.28), ch={
        'z': (-0.05, [(2, 0.05, 0.335)]), 'pitch': (0.0, [(2, 1.0, 0.3)]), 'roll': (0.0, [(2, 0.8, 0.2)]),
        'neck': (2.0, [(2, -3.0, 0.335)]), 'neck_z': (0.0, [(1, 1.5, 0.1)]), 'head': (0.0, [(2, 2.0, 0.335)]),
        'tail': (18.0, [(2, 3.0, 0.335)]), 'tail_z': (0.0, [(1, 4.0, 0.1)]), 'r_spine': (-2.0, [(2, 1.5, 0.385)])}),
    'canter': dict(T=14, ph={'br': 0.125, 'fr': 0.375, 'bl': 0.375, 'fl': 0.625}, beta=0.33, A=0.34, E=(0.36, 0.32), lift=(0.42, 0.32), ch={
        'z': (-0.07, [(1, 0.07, 0.05)]), 'y': (0.0, [(1, 0.03, 0.5)]), 'pitch': (0.0, [(1, 7.0, 0.25)]),
        'roll': (1.5, [(1, 1.0, 0.6)]), 'neck': (3.0, [(1, -10.0, 0.25)]), 'neck_z': (2.0, []), 'head': (0.0, [(1, 4.0, 0.3)]),
        'tail': (25.0, [(1, 5.0, 0.3)]), 'tail_z': (0.0, [(1, 3.0, 0.1)]), 'r_spine': (-5.0, [(1, -3.0, 0.27)])}),
    'gallop': dict(T=12, ph={'br': 0.125, 'fr': 0.475, 'bl': 0.225, 'fl': 0.575}, beta=0.25, A=0.38, E=(0.48, 0.44), lift=(0.48, 0.36), ch={
        'z': (-0.09, [(1, 0.08, 0.975)]), 'y': (0.0, [(1, 0.04, 0.6)]), 'pitch': (0.0, [(1, 8.0, 0.3)]),
        'roll': (0.0, [(1, 1.0, 0.4)]), 'neck': (-6.0, [(1, -13.0, 0.7)]), 'neck_z': (0.0, []), 'head': (6.0, [(1, 6.0, 0.7)]),
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
    E = G0['E'][fi] * (1 - k) + G1['E'][fi] * k   # swing overreach (v2): fore reach forward before landing, hind kick back at toe-off
    u = (c - ph) % 1.0
    hy, hz = LEGS[leg]['hip']; g = LEGS[leg]['g']
    if u < beta:
        s = u / beta; y = A - 2 * A * s; z = g
    else:
        s = (u - beta) / (1 - beta)
        if leg[0] == 'f':  # fore: fold early (knee up), reach well forward late, then come back onto the landing spot
            y = -A + 2 * A * ss(s ** 0.8) + E * math.sin(math.pi * ss((s - 0.35) / 0.65)) * ss((s - 0.35) / 0.3)
            z = g + lift * math.sin(math.pi * min(1, s ** 0.75)) ** 1.2
        else:  # hind: kick back off the ground, fold the hock, swing through
            y = -A + 2 * A * ss(s) - E * math.sin(math.pi * min(1.0, s / 0.45))
            z = g + lift * math.sin(math.pi * s) ** 0.8
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

# ---------- death (v2): the sim's cavalry 'vanish' is shown as the regiment dying ----------
# Horse: stumbles nose-down, front knees buckle (kneels), hind quarters drop, then it rolls onto its side; legs
# stretch out, neck lies along the ground. Rider (r_spine chain + the rider-leg boxes, which the kits weight to the
# horse 'body' bone) leaves the saddle on his own trajectory: a = thrown forward over the shoulder, b = slides off the
# side away from the roll, c = goes over the rump onto his back. Play-once clips; the last frame is the body on the field.
DIE = {  # side the horse rolls to (+1 = its +x), rider release t, flight time, landing hip (armature xyz), landing euler (deg)
    'a': dict(s=1, rel=0.14, fl=0.30, P=(-0.35, 2.05, 0.2), E=(-92, 0, 25), arc=0.55, lean=(-30, 0, 0)),
    'b': dict(s=-1, rel=0.30, fl=0.36, P=(0.95, 0.15, 0.2), E=(-8, 95, 0), arc=0.25, lean=(0, 25, 0)),
    'c': dict(s=1, rel=0.10, fl=0.40, P=(-0.3, -1.8, 0.2), E=(95, 0, -15), arc=0.35, lean=(30, 0, 0)),
}

def horse_die_pose(kit, var, t):
    D = DIE[var]; sg = D['s']
    k1 = ss(t / 0.28); k1b = ss((t - 0.06) / 0.28); k2 = ss((t - 0.2) / 0.3); k3 = ss((t - 0.42) / 0.38)
    th = sg * (6 * k2 * (1 - k3) + 84 * k3)
    hc = 1.3 - 0.2 * k1 - 0.5 * k2
    hc = hc * (1 - k3) + 0.40 * k3
    p = cavalry.rider_hold(kit)
    p['root'] = (0, th, 0)
    p['_loc'] = (-1.3 * math.sin(math.radians(th)) + sg * 0.3 * k3, 0.25 * k1 * (1 - k3), hc - 1.3 * math.cos(math.radians(th)))
    p['body'] = (-16 * k1 + 13 * k2, 0, 0)
    tw = 0.12 * math.sin(PI2 * 2.5 * t) * ss((t - 0.7) / 0.1) * (1 - ss((t - 0.9) / 0.1))   # last kicks
    for leg, kk in (('fl', k1), ('fr', k1b)):
        p[leg + '_up'] = (50 * kk - 28 * k3 + 8 * tw * 57, 0, 0)
        p[leg + '_lo'] = (-120 * kk + 88 * k3, 0, 0)
    for leg, o in (('bl', 0.0), ('br', 6.0)):
        p[leg + '_up'] = (-45 * k2 + 30 * k3 + o * k3 - 5 * tw * 57, 0, 0)
        p[leg + '_lo'] = (100 * k2 - 72 * k3, 0, 0)
    p['neck'] = (-30 * k1 + 8 * k3, 0, -sg * 22 * k3)
    p['head'] = (15 * k1 - 5 * k3, 0, 0)
    p['tail'] = (5 - 10 * k2, 0, 0)
    lv = ss(t / max(D['rel'], 0.05))
    p['r_spine'] = tuple(a * lv for a in D['lean'])
    p['r_head'] = (-0.3 * D['lean'][0] * lv, 0, 0)
    return p

def die_clip(kit, var):
    D = DIE[var]
    def f(t):
        p = horse_die_pose(kit, var, t)
        if t > D['rel']:
            u = min(1.0, (t - D['rel']) / D['fl'])
            fl = math.sin(math.pi * u)
            p['r_arm.R'] = (60 + 90 * fl + 40 * u, 0, 30 * u); p['r_fore.R'] = (20 + 30 * fl, 0, 0)
            p['r_arm.L'] = (50 + 80 * fl + 50 * u, 0, -30 * u); p['r_fore.L'] = (25 + 25 * fl, 0, 0)
            p['r_head'] = (-20 * fl + 10 * u, 0, 10 * u)
            P = (D['P'][0] * D['s'] if var != 'b' else D['P'][0] * -D['s'], D['P'][1], D['P'][2])
            E = (D['E'][0], D['E'][1] * (-D['s'] if var == 'b' else 1), D['E'][2] * D['s'])
            p['_rider'] = (horse_die_pose(kit, var, D['rel']), u, P, E, D['arc'])
        else:
            p['_rider'] = None   # still in the saddle (leaning): rider legs follow the rider's spine
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
    for var in DIE:
        out.append((f'cv_die_{var}', 48, False, die_clip(kit, var)))
    return out

# ---------- baking ----------
def setup(vid, lod):
    common.reset_scene()
    kit = cavalry.VARIANTS[vid]
    rig = rigkit.build_armature('horse', cavalry.BONES)
    body = cavalry.build(f'{vid}_lod{lod}', kit, lod == 0)
    rigkit.bind(body, rig)
    return rig, body, kit

def rider_leg_verts(body):
    """vertices of the rider's leg boxes (kits weight them to the horse 'body' bone): connected components bound to
    'body' whose centre sits at the stirrup/thigh spot (|x| ~0.2, y 0.06..0.295, z 1.1..1.66). Motion only."""
    me = body.data
    par = list(range(len(me.vertices)))
    def fd(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for e in me.edges:
        a, b = fd(e.vertices[0]), fd(e.vertices[1])
        if a != b: par[a] = b
    comp = {}
    for v in me.vertices:
        comp.setdefault(fd(v.index), []).append(v.index)
    gi = body.vertex_groups['body'].index
    out = []
    for vs in comp.values():
        if any(not me.vertices[i].groups or me.vertices[i].groups[0].group != gi for i in vs):
            continue
        cx = sum(me.vertices[i].co.x for i in vs) / len(vs); cy = sum(me.vertices[i].co.y for i in vs) / len(vs)
        cz = sum(me.vertices[i].co.z for i in vs) / len(vs)
        if abs(abs(cx) - 0.2) < 0.02 and 0.06 <= cy <= 0.295 and 1.1 <= cz <= 1.66:
            out += vs
    return out

_RL = {}
def eval_frame(rig, body, pose):
    from mathutils import Matrix, Euler, Vector
    rigkit.apply_pose(rig, pose)
    bpy.context.view_layer.update()
    pb = rig.pose.bones['r_spine']
    Mr = None
    if '_rider' in pose and pose['_rider'] is None:
        Mr = pb.matrix @ pb.bone.matrix_local.inverted()
    elif '_rider' in pose:
        pre, u, P, E, arc = pose['_rider']
        rigkit.apply_pose(rig, pre); bpy.context.view_layer.update()
        M0 = pb.matrix.copy()
        rigkit.apply_pose(rig, pose); bpy.context.view_layer.update()
        B3 = pb.bone.matrix_local.to_3x3()
        q1 = (Euler([math.radians(a) for a in E], 'XYZ').to_matrix() @ B3).to_quaternion()
        uh = 1 - (1 - u) ** 1.6
        loc = Vector((M0.translation.x + (P[0] - M0.translation.x) * uh, M0.translation.y + (P[1] - M0.translation.y) * uh,
                      M0.translation.z + (P[2] - M0.translation.z) * u * u + arc * math.sin(math.pi * u)))
        q = M0.to_quaternion().slerp(q1, ss(u))
        pb.matrix = Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        bpy.context.view_layer.update()
        Mr = pb.matrix @ pb.bone.matrix_local.inverted()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    vals = [(v.co.x, v.co.z, -v.co.y) for v in me.vertices]
    ev.to_mesh_clear()
    if Mr is not None:   # rider legs leave the saddle with him
        if body.name not in _RL:
            _RL[body.name] = rider_leg_verts(body)
        for i in _RL[body.name]:
            c = Mr @ body.data.vertices[i].co
            vals[i] = (c.x, c.z, -c.y)
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

def sheet(vid, out_png, rows=None, ncol=8, side=1):
    """side-view contact sheet (workbench) of the BAKED vertex positions: ncol frames of each clip row"""
    rig, body, kit = setup(vid, 0)
    cl = {c[0]: c for c in combat_clips(kit)}
    rows = rows or ['hv_walk', 'hv_trot', 'hv_canter', 'hv_gallop', 'hv_stand']
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
    W, Hh = (300, 260)
    sc.render.resolution_x = W; sc.render.resolution_y = Hh
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 3.4 if rows[0].startswith('hv') else 5.2
    cam.location = (5.0 * side, 0.2, 1.2 if rows[0].startswith('hv') else 1.0)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90 * side))
    me = bpy.data.meshes.new('ground'); me.from_pydata([(-4, -4, 0), (4, -4, 0), (4, 4, 0), (-4, 4, 0)], [], [(0, 1, 2, 3)])
    gr = bpy.data.objects.new('ground', me); sc.collection.objects.link(gr)
    shown = bpy.data.objects.new('shown', body.data.copy()); sc.collection.objects.link(shown)
    body.hide_render = True
    tmp = []
    for r in rows:
        nf, loop = cl[r][1], cl[r][2]
        for i in range(ncol):
            t = i / ncol if loop else i / max(1, ncol - 1)
            vals = eval_frame(rig, body, cl[r][3](t))
            for v, (x, y, z) in zip(shown.data.vertices, vals):
                v.co = (x, -z, y)
            shown.data.update()
            p = f'/tmp/hsheet_{len(tmp):02d}.png'; sc.render.filepath = p
            bpy.ops.render.render(write_still=True); tmp.append(p)
    import subprocess
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + sum([['-i', p] for p in tmp], []) +
                   ['-filter_complex', f'xstack=inputs={len(tmp)}:layout=' + '|'.join(f'{(k % ncol) * W}_{(k // ncol) * Hh}' for k in range(len(tmp))), out_png])
    print('sheet', out_png, rows)

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    mode = argv[0] if argv else 'bake'
    if mode == 'bake':
        for vid in (argv[1:] or list(cavalry.VARIANTS)):
            for lod in (0, 1):
                bake(vid, lod)
    elif mode == 'sheet':
        sheet(argv[1] if len(argv) > 1 else 'em_cuirassier', argv[2] if len(argv) > 2 else '/workspace/ic_anim/out/horse_sheet.png',
              argv[3].split(',') if len(argv) > 3 else None, int(argv[4]) if len(argv) > 4 else 8, int(argv[5]) if len(argv) > 5 else 1)
    elif mode == 'speeds':
        print({g: round(v_nom(g), 2) for g in ORDER})
