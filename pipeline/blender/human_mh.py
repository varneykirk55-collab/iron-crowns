"""Blender side of the era-generic human base (docs/char/CHAR_SYSTEM.md): MakeHuman CC0 body posed into our rest
(pipeline/human/mh_pose.py) -> Blender meshes for the parts a uniform kit leaves visible (head, hands, ...), with
  * vertex groups = our frozen char_rig bone names (MH weights summed per bone, mh_pose.mh_to_ic_bone)
  * UV layer 'mh' = MakeHuman base UVs (skin albedo / eye texture), face attribute 'albm' (1 skin, 2 eye) for the albedo bake
  * the low-poly eye proxy fitted from its .mhclo (rigid to 'head').
No MPFB / MakeHuman code is used; only CC0 data files under pipeline/assets/mh (see docs/char/LICENSES.md)."""
import os, sys, math
import numpy as np
import bpy, bmesh
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'human'))
import mh_pose as MP, mh_base as MB, mh_clo as MC

GRIP_OFF = (0.008, 0.0, 0.0)   # hand shifted 8 mm outward so the fist closes round the grip axis without cutting into it
_cache = {}

def posed(spread=0.0):
    k = ('p', spread)
    if k not in _cache:
        h = _cache.get('h') or MB.Human(); _cache['h'] = h
        _cache[k] = MP.PosedHuman(spread=spread, grip_off=GRIP_OFF, human=h)
    return _cache[k]

def _mesh(name, V, faces, uvs=None, uvname='mh'):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(f) for f in faces])
    if uvs is not None:
        ul = me.uv_layers.new(name=uvname)
        flat = [c for fu in uvs for uv in fu for c in uv]
        ul.data.foreach_set('uv', flat)
    me.validate(); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    for p in me.polygons: p.use_smooth = True
    return o

def part(name, face_ids, ph, albm=1.0, slot='skin', rigid=None):
    """sub-mesh of the posed MH base (faces by index) with MH uvs, our-bone weights, attributes slot / albm / det2."""
    h = ph.h
    used = sorted({v for i in face_ids for v in h.F[i]})
    remap = {v: k for k, v in enumerate(used)}
    faces = [[remap[v] for v in h.F[i]] for i in face_ids]
    uvs = [[tuple(h.VT[t]) for t in h.FT[i]] for i in face_ids]
    o = _mesh(name, ph.V[used], faces, uvs)
    W = ph.ic_weights()
    for b, w in W.items():
        g = o.vertex_groups.get(b) or o.vertex_groups.new(name=b)
        if rigid: continue
        for k, vi in enumerate(used):
            if w[vi] > 0.002: g.add([k], float(w[vi]), 'REPLACE')
    if rigid:
        o.vertex_groups[rigid].add(list(range(len(used))), 1.0, 'REPLACE')
    _attrs(o, slot, albm)
    return o

def _attrs(o, slot, albm):
    import char_body as B
    me = o.data
    a = me.attributes.get('slot') or me.attributes.new('slot', 'INT', 'FACE')
    a.data.foreach_set('value', [B.S[slot]] * len(me.polygons))
    m = me.attributes.new('albm', 'FLOAT', 'FACE'); m.data.foreach_set('value', [albm] * len(me.polygons))
    d = me.attributes.get('det2') or me.attributes.new('det2', 'FLOAT', 'POINT')
    d.data.foreach_set('value', [8.0 / 15.0] * len(me.vertices))

def dominant(ph, face_ids):
    """face -> dominant IC bone (by summed vertex weights)."""
    W = ph.ic_weights(); names = list(W); M = np.stack([W[n] for n in names], 1)
    out = {}
    for i in face_ids:
        out[i] = names[int(M[ph.h.F[i]].sum(0).argmax())]
    return out

def body_faces(ph):
    return [i for i, g in enumerate(ph.h.G) if g == 'body']

def head_faces(ph, zcut=1.53):
    fb = body_faces(ph); dom = dominant(ph, fb)
    return [i for i in fb if dom[i] in ('head', 'neck') and ph.V[ph.h.F[i]][:, 2].mean() > zcut]

def hand_faces(ph, side, zcut=0.93):
    fb = body_faces(ph); dom = dominant(ph, fb); sx = 1 if side == '.R' else -1
    return [i for i in fb if (dom[i] == 'hand' + side or (dom[i] == 'forearm' + side and ph.V[ph.h.F[i]][:, 2].mean() < zcut))
            and sx * ph.V[ph.h.F[i]][:, 0].mean() > 0.1]

def eyes(ph, name='eyes'):
    """low-poly MH eye proxy (cornea + iris/sclera texture), fitted to the rest head, then moved
    with the posed head bone (the neck is tilted / shifted back in mh_pose)."""
    A = MB.ASSETS
    refs, scale = MC.read(os.path.join(A, 'eye_lowpoly.mhclo'))
    Pm = MC.fit(refs, scale, ph.h.Vmh)
    P = (MB.to_ic(Pm) - [0, 0, ph.zmin]) * ph.scale + [0, 0, MP.SOLE]
    hb = ph.bones_['head'][0]; P = (P - hb) @ ph.R['head'].T + ph.P['head']   # follow the posed head (neck tilt + shift)
    _, VT, F, FT, _ = MB.read_obj(os.path.join(A, 'eye_lowpoly.obj'))
    o = _mesh(name, P, F, [[tuple(VT[t]) for t in ft] for ft in FT])
    o.vertex_groups.new(name='head').add(list(range(len(P))), 1.0, 'REPLACE')
    _attrs(o, 'eye', 2.0)
    return o

def ear_weight(P):
    """soft mask (0..1) of the auricles on the posed MH head (centre y ~0.01, out to |x| 0.088, z 1.60..1.72)."""
    def ss(a, b, t): t = np.clip((t - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
    ax = np.abs(P[:, 0]); y = P[:, 1]; z = P[:, 2]
    return ss(0.058, 0.068, ax) * np.exp(-((y - 0.010) / 0.032) ** 2) * ss(1.585, 1.605, z) * (1 - ss(1.725, 1.745, z))

def smooth_ears(o, iters=6, lam=0.5, mu=-0.53, mask=None):
    """Taubin (lambda / mu) smoothing of the ear vertices only (weighted by ear_weight): rounds the auricle folds that a
    2.4k-tri LOD0 head can't carry (decimation faceting + bake rays crossing between folds) without shrinking the ear."""
    me = o.data; n = len(me.vertices)
    P = np.zeros(n * 3); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    E = np.zeros(len(me.edges) * 2, np.int64); me.edges.foreach_get('vertices', E); E = E.reshape(-1, 2)
    w = ear_weight(P)[:, None] if mask is None else (ear_weight(P) * mask)[:, None]
    if w.max() < 1e-3: return
    deg = np.zeros(n); np.add.at(deg, E[:, 0], 1); np.add.at(deg, E[:, 1], 1); deg = np.maximum(deg, 1)[:, None]
    for k in range(iters * 2):
        acc = np.zeros_like(P); np.add.at(acc, E[:, 0], P[E[:, 1]]); np.add.at(acc, E[:, 1], P[E[:, 0]])
        P = P + (lam if k % 2 == 0 else mu) * w * (acc / deg - P)
    me.vertices.foreach_set('co', P.ravel()); me.update()

def subdivide(o, levels):
    m = o.modifiers.new('sd', 'SUBSURF'); m.levels = levels; m.render_levels = levels; m.uv_smooth = 'PRESERVE_BOUNDARIES'
    bpy.context.view_layer.objects.active = o
    with bpy.context.temp_override(object=o, active_object=o):
        bpy.ops.object.modifier_apply(modifier=m.name)
