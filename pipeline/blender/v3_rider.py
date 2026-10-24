"""Eras v3 riders (kits 3 + 6, docs/char/ERAS_PROGRESS.md): the v3 human (MakeHuman head / hands / skin, v3 body
shell, kit garments) is built standing on the frozen infantry rest like every v3 kit, then moved into a SEATED rest
on the EXISTING cavalry rig (cavalry.BONES, Rob's horse + rider bones and clips, untouched):
  * seat(): per infantry bone a rigid (or slightly scaled) transform standing -> seated, linear-blend-skinned with the
    infantry weights (numpy). Torso: z squash 0.92 so the shoulder lands on r_arm (1.93) over the saddle; arms hang
    straight down the r_arm / r_fore chain (scale 0.97); thighs / shins re-aimed into the seat (knee forward / out on
    the shabraque, foot in the stirrup).
  * cavalry weights: hips / spine / chest / clav -> body below / r_spine above the waist (blend 1.57-1.68 seated z),
    neck + head -> r_head, upper_arm -> r_arm, forearm + hand (+ sabre) -> r_fore, legs -> body (the rig has no rider
    leg / hand bones). Horse parts (built HOFF away from the rider so their bake / AO never mixes) -> horse bones by
    position; tack rigid; reins blended head -> neck -> left hand, authored in the idle pose and moved back to rest.
  * bake(): cavalry.clips(VARIANTS[...]) baked into the same VAT / json layout as char_v2_build.bake_vat (rows
    0..frames, vatn normals, weapon_tip per frame, pal), exported as soldier_<kid>_lod{0,1}.glb."""
import math, os, json
import numpy as np
import bpy
from mathutils import Vector, Matrix
import common, rigkit, cavalry
import char_v2 as C
import char_rig as R

Z_HIP, K_TORSO, Y_SEAT = 1.488, 0.92, -0.05
SHOULDER_Y, SHOULDER_Z, SHOULDER_X = -0.056, 1.925, 0.188
ARM_SCALE = 0.97
KNEE = (0.295, 0.22, 1.213)
SHIN_DIR = (0.015, -0.07, -0.413)
WRIST_TILT = -35.0   # right hand: sabre fist cocked forward (blade ~ along Rob's r_fore swing, see kit)

def _T(v):
    m = np.eye(4); m[:3, 3] = v; return m

def _R(r3):
    m = np.eye(4); m[:3, :3] = r3; return m

def _S(sx, sy, sz):
    return np.diag([sx, sy, sz, 1.0])

def _rot_between(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(a @ b)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)

def _rx(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])

def _ap(m, p):
    return (m @ np.append(np.asarray(p, float), 1.0))[:3]

def seat_mats():
    """infantry bone -> 4x4 standing -> seated (rest) transform."""
    J = {b[0]: (np.array(b[1], float), np.array(b[2], float)) for b in R.BONES}
    M = {}
    MT = _T((0, Y_SEAT, Z_HIP)) @ _S(1, 1, K_TORSO) @ _T((0, 0, -0.95))
    for b in ('root', 'hips', 'spine', 'chest', 'clav.R', 'clav.L', 'prop'): M[b] = MT
    neck0 = J['neck'][0]
    MH = _T(_ap(MT, neck0) - neck0)
    M['neck'] = MH; M['head'] = MH
    for s, sd in ((1, '.R'), (-1, '.L')):
        sh, wr = J['upper_arm' + sd][0], J['forearm' + sd][1]
        P = np.array([s * SHOULDER_X, SHOULDER_Y, SHOULDER_Z])
        MA = _T(P) @ _R(_rot_between(wr - sh, (0, 0, -1))) @ _S(ARM_SCALE, ARM_SCALE, ARM_SCALE) @ _T(-sh)
        M['upper_arm' + sd] = MA; M['forearm' + sd] = MA
        if s > 0:
            W = _ap(MA, J['hand.R'][0])
            M['hand.R'] = _T(W) @ _R(_rx(WRIST_TILT)) @ _T(-W) @ MA
        else:
            M['hand.L'] = MA
        H, Kn, A = J['thigh' + sd][0], J['shin' + sd][0], J['shin' + sd][1]
        H2 = _ap(MT, H)
        K2 = np.array([s * KNEE[0], KNEE[1], KNEE[2]])
        d = K2 - H2; K2 = H2 + d / np.linalg.norm(d) * np.linalg.norm(Kn - H)
        M['thigh' + sd] = _T(H2) @ _R(_rot_between(Kn - H, K2 - H2)) @ _T(-H)
        sdir = np.array([s * SHIN_DIR[0], SHIN_DIR[1], SHIN_DIR[2]])
        MS = _T(K2) @ _R(_rot_between(A - Kn, sdir)) @ _T(-Kn)
        M['shin' + sd] = MS; M['foot' + sd] = MS
    return M

_M = None
def seat_point(bone, p):
    global _M
    if _M is None: _M = seat_mats()
    return Vector(_ap(_M[bone], tuple(p)))

# ------------------------------------------------------------------ cavalry pose maths (no armature needed)
CB = {b[0]: b for b in cavalry.BONES}
def pose_mats(pose):
    """armature-space deform matrices (4x4 numpy) of cavalry.BONES for a rigkit pose dict (same maths as
    rigkit.apply_pose: euler in armature axes about the bone head, composed down the chain, plus the root _loc)."""
    out = {}
    def get(n):
        if n in out: return out[n]
        _, h, t, par = CB[n]
        rot = pose.get(n, (0, 0, 0))
        Rm = np.array(__import__('mathutils').Euler([math.radians(a) for a in rot], 'XYZ').to_matrix())
        local = _T(h) @ _R(Rm) @ _T(-np.array(h, float))
        if par is None: m = _T(pose.get('_loc', (0, 0, 0))) @ local
        else: m = get(par) @ local
        out[n] = m; return m
    for n in CB: get(n)
    return out

def idle0():
    return pose_mats(cavalry.clips(cavalry.VARIANTS[C.RIDER['variant']])[0][3](0.0))

# ------------------------------------------------------------------ horse weights (horse coords, cavalry.BONES)
def ss(a, b, x): return C.ss(a, b, x)

LEGS = (('fl', 1, 0.48), ('fr', -1, 0.48), ('bl', 1, -0.45), ('br', -1, -0.45))
def horse_w(p):
    x, y, z = p
    w = {}
    for leg, sx, ly in LEGS:
        if x * sx < 0.03: continue
        front = leg[0] == 'f'
        g = ss(0.03, 0.08, x * sx) * ss(1.08 if front else 1.12, 0.90 if front else 0.95, z)
        dy = abs(y - ly) if front else abs(y - (ly - 0.06))
        g *= ss(0.25, 0.14, dy) if z > 0.8 else 1.0
        if g <= 0: continue
        lo = ss(0.68, 0.56, z)
        w[leg + '_up'] = g * (1 - lo); w[leg + '_lo'] = g * lo
    rest = max(0.0, 1.0 - sum(w.values()))
    if rest > 0:
        N0, N1 = np.array([0.6, 1.38]), np.array([0.92, 1.85])
        q = np.array([y, z]); ax = N1 - N0
        s = float((q - N0) @ ax / (ax @ ax))
        H0, H1 = np.array([0.92, 1.85]), np.array([1.38, 1.58])
        hx = H1 - H0; sh = float((q - H0) @ hx / (hx @ hx))
        ear = z > 1.86 and y > 0.8
        head = max(ss(-0.12, 0.05, sh) if y > 0.75 else 0.0, 1.0 if ear else 0.0)
        neck = (1 - head) * (ss(0.0, 0.30, s) if y > 0.40 else 0.0)
        w['head'] = w.get('head', 0) + rest * head; w['neck'] = rest * neck
        w['body'] = rest * (1 - head - neck)
    return w

def tail_w(p):
    x, y, z = p
    k = ss(-0.64, -0.74, y)
    return {'tail': k, 'body': 1 - k}

# ------------------------------------------------------------------ build + bake
def _infantry_weights(o):
    names = [g.name for g in o.vertex_groups]
    bi = {n: i for i, n in enumerate(R.BONES and [b[0] for b in R.BONES])}
    n = len(o.data.vertices); W = np.zeros((n, len(R.BONES)))
    for v in o.data.vertices:
        for g in v.groups:
            nm = names[g.group]
            if nm in bi: W[v.index, bi[nm]] += g.weight
    return W

def rider_map(w_inf, zs):
    """infantry bone weights (dict) + seated z -> cavalry weights."""
    out = {}
    def add(b, x):
        if x > 0: out[b] = out.get(b, 0) + x
    torso = sum(w_inf.get(b, 0) for b in ('root', 'hips', 'spine', 'chest', 'clav.R', 'clav.L', 'prop'))
    up = ss(1.57, 1.68, zs)
    add('r_spine', torso * up); add('body', torso * (1 - up))
    add('r_head', w_inf.get('neck', 0) + w_inf.get('head', 0))
    for sd in ('.R', '.L'):
        add('r_arm' + sd, w_inf.get('upper_arm' + sd, 0))
        add('r_fore' + sd, w_inf.get('forearm' + sd, 0) + w_inf.get('hand' + sd, 0))
        add('body', w_inf.get('thigh' + sd, 0) + w_inf.get('shin' + sd, 0) + w_inf.get('foot' + sd, 0))
    return out

def seated(o):
    """(n,3) seated rest positions and per-vertex cavalry weight dicts for a joined kit mesh o (pid attribute)."""
    M = seat_mats(); bones = [b[0] for b in R.BONES]
    n = len(o.data.vertices)
    co = np.zeros(n * 3); o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    pid = np.zeros(n, np.float32); o.data.attributes['pid'].data.foreach_get('value', pid); pid = np.round(pid).astype(int)
    keys = C.PID_KEYS
    gk = ['body' if i == 0 else keys[i - 1] for i in range(len(keys) + 1)]
    W = _infantry_weights(o)
    hoff = np.array(C.RIDER['hoff'], float)
    out = np.zeros_like(co); ws = []
    rigid = C.RIDER.get('rigid', {}); rein = C.RIDER.get('rein', ())
    idle = None
    for i in range(n):
        p = co[i]
        if p[1] < hoff[1] / 2:   # horse + tack (built at +HOFF)
            q = p - hoff; k = gk[pid[i]]
            if any(k.startswith(r) for r in rein):
                if idle is None: idle = idle0()
                w = C.RIDER['rein_w'](q, k)
                D = sum(w[b] * idle[b] for b in w)
                q = _ap(np.linalg.inv(D), q)
            elif k in rigid: w = {rigid[k]: 1.0}
            elif k.startswith(C.RIDER.get('tail', '\0')): w = tail_w(q)
            else: w = horse_w(q)
            out[i] = q; ws.append(w); continue
        wi = W[i]; s = wi.sum()
        if s <= 1e-6: wi = np.zeros(len(bones)); wi[bones.index('hips')] = 1.0; s = 1.0
        wi = wi / s
        P = np.zeros(3)
        for b in np.nonzero(wi > 1e-5)[0]:
            P += wi[b] * _ap(M[bones[b]], p)
        out[i] = P
        ws.append(rider_map({bones[b]: wi[b] for b in np.nonzero(wi > 1e-5)[0]}, P[2]))
    return out, ws

def make_seated(o, name):
    co, ws = seated(o)
    me = o.data.copy(); me.name = name
    me.vertices.foreach_set('co', co.ravel().astype(np.float32))
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    for g in list(ob.vertex_groups): ob.vertex_groups.remove(g)
    groups = {b[0]: ob.vertex_groups.new(name=b[0]) for b in cavalry.BONES}
    by = {}
    for i, w in enumerate(ws):
        s = sum(w.values()) or 1.0
        for b, x in w.items():
            if x / s > 1e-4: by.setdefault((b, round(x / s, 4)), []).append(i)
    for (b, x), idx in by.items(): groups[b].add(idx, x, 'REPLACE')
    me.update()
    return ob

def build_rig(name):
    bones = list(cavalry.BONES)
    tip = C.RIDER['tip']   # standing sabre point -> seated (rigid on hand.R)
    t = seat_point('hand.R', tip)
    bones.append(('weapon_tip', tuple(t), tuple(t + Vector((0, 0, 0.05))), 'r_fore.R'))
    return rigkit.build_armature(name, bones)

def bake_one(o, rig, lod, extra):
    import char_v2_build as CBd
    n = len(o.data.vertices)
    rigkit.bind(o, rig)
    kit = cavalry.VARIANTS[C.RIDER['variant']]
    meta = {'vertices': n, 'fps': 24, 'clips': {}, 'frames': 0, 'kit': C.KID, 'lod': lod,
            'normals': 'vatn rgba8 (n*0.5+0.5), same rows/cols as .vat', 'weapon_tip': {},
            'weapon_tip_note': "per clip, per frame position of the unweighted 'weapon_tip' bone (child of r_fore.R, sabre point) "
                               "in the same Godot model space as the .vat rows",
            'rig': 'cavalry.BONES (Rob: horse + rider bones and clips unchanged); v3 rider seated on it (v3_rider.py)'}
    meta.update(extra)
    if getattr(C, 'KIT_PAL', None): meta['pal'] = C.KIT_PAL
    pos, nrm = [], []; row = 0
    tipb = rig.pose.bones['weapon_tip']
    for cn, nf, loop, fn in cavalry.clips(kit):
        tips = []
        for f in range(nf):
            t = f / nf if loop else f / max(1, nf - 1)
            rigkit.apply_pose(rig, fn(t))
            bpy.context.view_layer.update()
            ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
            co = np.empty(n * 3, np.float32); me.vertices.foreach_get('co', co)
            nn = np.empty(n * 3, np.float32); me.vertices.foreach_get('normal', nn)
            ev.to_mesh_clear()
            co = co.reshape(n, 3); nn = nn.reshape(n, 3)
            pos.append(np.stack([co[:, 0], co[:, 2], -co[:, 1]], 1))
            g = np.stack([nn[:, 0], nn[:, 2], -nn[:, 1]], 1)
            g = np.clip(np.round((g * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
            nrm.append(np.concatenate([g, np.full((n, 1), 255, np.uint8)], 1))
            h = rig.matrix_world @ tipb.head
            tips.append([round(h.x, 4), round(h.z, 4), round(-h.y, 4)])
        meta['clips'][cn] = {'start': row, 'count': nf, 'loop': loop}
        meta['weapon_tip'][cn] = tips
        row += nf
    meta['frames'] = row
    P = np.stack(pos).astype(np.float32)
    meta['aabb'] = [P.reshape(-1, 3).min(0).tolist(), P.reshape(-1, 3).max(0).tolist()]
    meta['max_reach'] = 1.0
    base = os.path.join(common.VAT, f'{C.KID}_lod{lod}')
    open(base + '.vat', 'wb').write(P.tobytes())
    open(base + '.vatn', 'wb').write(np.stack(nrm).tobytes())
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    rigkit.apply_pose(rig, {}); bpy.context.view_layer.update()
    o.modifiers.clear(); o.parent = None
    me2 = o.data.copy(); me2.validate(verbose=True)
    st = bpy.data.objects.new(f'{C.KID}_lod{lod}', me2); bpy.context.scene.collection.objects.link(st)
    common.export_glb([st], os.path.join(common.MODELS, f'soldier_{C.KID}_lod{lod}.glb'))
    bpy.data.objects.remove(st)
    print('[rider] vat', lod, 'verts', n, 'frames', row, flush=True)
    return meta

def bake(full, farx, extra0, extra1, drop):
    rig = build_rig(C.KID)
    s0 = make_seated(full, C.KID + '_seated_lod0'); s1 = make_seated(farx, C.KID + '_seated_lod1')
    for o in [full, farx] + drop:
        bpy.data.objects.remove(o)
    bake_one(s0, rig, 0, extra0)
    bake_one(s1, rig, 1, extra1)
    rigkit.bind(s0, rig); bpy.data.objects.remove(s1)
    os.makedirs(common.BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, f'soldier_{C.KID}.blend'))
