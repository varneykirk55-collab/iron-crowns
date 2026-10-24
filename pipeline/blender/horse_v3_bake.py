"""Rob / cavalry integration: load Bill's frozen horse v3 mesh (game/assets/models/horse_v3/horse_v3.blend, design ab70c61,
READ-ONLY) into a horse_proxy.Geo so horse_anim.bake_variant bakes it on the HX rig unchanged.

* Bill's armature == horse_rig.HX_BONES (checked at load: heads/tails < 1e-4 m, same parents), vertex groups carry spec
  bone names -> his weights are used as authored (<= 4 per vertex).
* Layers per variant (names mapped on OUR side, no rename in Bill's files):
    med_knight (1300): horse_body + horse_hair (tail only: the mane, part_id 0, is hidden under the crinet) + horse_eyes
                       + tack_1300 + barding_1300   -> cavalry_hx_med_knight_lod{0,1}
    c19_hussar (1800): horse_body + horse_hair (mane + tail) + horse_eyes + tack_1800 -> cavalry_hx_c19_hussar_lod{0,1}
  Bill's LOD1 has no eyes (by design).  LOD2 is not used yet (runtime has 2 LODs; see the report).
* Coat specks: body (hide) vertices that sit under the covering cloth (1300 caparison / front curtain / crinet,
  1800 shabraque / sheepskin) are pulled inwards by PUSH along their rest normal, so LBS differences between the body
  and the cloth cannot push hide through the cloth at the shoulder / croup.  Only covered vertices move; weights are kept.
* UVMap.u (Bill's coat 'points' mask) is carried to UV.x for hx_vat.gdshader's per-instance coats.
* Per-corner colours (Col = bay + points), team mask (VID.y), material class (mat_id) and smooth shading are kept.
  The rider (char_rig proxy) and the knight's lance are still horse_proxy geometry (v3 riders come later)."""
import os
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import horse_rig as H
import horse_proxy as HP

BLEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'game', 'assets', 'models', 'horse_v3', 'horse_v3.blend'))
LAYERS = {
    'med_knight': ['horse_body', 'horse_hair', 'horse_eyes', 'tack_1300', 'barding_1300'],
    'c19_hussar': ['horse_body', 'horse_hair', 'horse_eyes', 'tack_1800'],
}
HIDE_PARTS = {'med_knight': {'horse_hair': {0}}}                  # mane under the crinet
COVER = {'med_knight': {'barding_1300': {0, 1, 2}}, 'c19_hussar': {'tack_1800': {0, 1}}}
# metres along the rest normal; per covering part ('*' = default).  The knight's front curtain (barding part 1) hangs over
# the swinging shoulder, so the coat under it goes deeper.
PUSH = {'med_knight': {'*': 0.022, ('barding_1300', 1): 0.045}, 'c19_hussar': {'*': 0.014}}
RAY = 0.09
TEAM_BASE = (1.0, 1.0, 1.0, 1.0)
if os.environ.get('HX_V3_PUSH'):   # diagnostics only (clipping before/after): override the push distance
    PUSH = {k: {'*': float(os.environ['HX_V3_PUSH'])} for k in PUSH}
_cache = {}

def supported(variant):
    return variant in LAYERS

def _read(name):
    """-> dict of python data for Bill's object `name` (read once, objects removed again)."""
    if name in _cache:
        return _cache[name]
    with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n == name or n == 'horse_v3_rig']
    objs = {o.name: o for o in dst.objects if o is not None}
    rig = objs.get('horse_v3_rig')
    if rig is not None and 'rig_ok' not in _cache:
        for b in rig.data.bones:
            assert b.name in H.HEAD, ('unknown bone', b.name)
            d = max((b.head_local - H.HEAD[b.name]).length, (b.tail_local - H.TAIL[b.name]).length)
            assert d < 1e-4, ('rest mismatch', b.name, d)
        _cache['rig_ok'] = True
    o = objs.get(name)
    if o is None:
        _cache[name] = None
        return None
    me = o.data
    gn = {g.index: g.name for g in o.vertex_groups}
    M = o.matrix_world.copy()
    v = [M @ x.co for x in me.vertices]
    n = [(M.to_3x3() @ x.normal).normalized() for x in me.vertices]
    w = [{gn[g.group]: g.weight for g in x.groups if g.weight > 0} for x in me.vertices]
    np_ = len(me.polygons)
    pid = [0] * np_; me.attributes['part_id'].data.foreach_get('value', pid)
    mid = [0] * np_; me.attributes['mat_id'].data.foreach_get('value', mid)
    col = me.color_attributes['Col'].data; vid = me.uv_layers['VID'].data; uvm = me.uv_layers['UVMap'].data
    faces = []
    for p in me.polygons:
        li = list(p.loop_indices)
        faces.append(dict(v=list(p.vertices), cc=[tuple(col[l].color) for l in li], team=[vid[l].uv[1] for l in li], pts=[uvm[l].uv[0] for l in li],
                          mat=mid[p.index], part=pid[p.index], smooth=p.use_smooth))
    d = dict(v=v, n=n, w=w, faces=faces)
    for ob in dst.objects:
        if ob is not None:
            dat = ob.data
            bpy.data.objects.remove(ob)
            if dat is not None and dat.users == 0:
                (bpy.data.meshes if isinstance(dat, bpy.types.Mesh) else bpy.data.armatures).remove(dat)
    _cache[name] = d
    return d

def _norm_w(w):
    items = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    s = sum(x for _, x in items) or 1.0
    return {b: x / s for b, x in items}

def add_layer(g, layer, lod, hide=(), push=None, cover=None):
    d = _read('%s_lod%d' % (layer, lod))
    if d is None:
        return 0
    g.cur = layer
    faces = [f for f in d['faces'] if f['part'] not in hide]
    used = sorted(set(i for f in faces for i in f['v']))
    pos = {i: Vector(d['v'][i]) for i in used}
    moved = 0
    if push and cover is not None:
        hide_v = set(i for f in faces if f['mat'] == HP.M_HIDE for i in f['v'])
        for i in hide_v:
            nn = d['n'][i]
            hit = cover[0].ray_cast(pos[i] - nn * 0.002, nn, RAY)
            if hit[0] is not None:
                pm = push.get(cover[1][hit[2]], push['*']) if isinstance(push, dict) else push
                pos[i] = pos[i] - nn * pm; moved += 1
    remap = {}
    for i in used:
        remap[i] = g.vert(pos[i], _norm_w(d['w'][i]))
    for f in faces:
        idx = tuple(remap[i] for i in f['v'])
        # team-masked corners: Bill paints a preview red (horse_v3_config.TEAM_RGB); the runtime dyes base * team colour,
        # so those corners get the white team base the other VATs use.
        cc = [TEAM_BASE if t > 0.5 else c for c, t in zip(f['cc'], f['team'])]
        avg = tuple(sum(c[k] for c in cc) / len(cc) for k in range(3)) + (sum(f['team']) / len(cc),)
        g.f.append(idx); g.fc.append(avg); g.fm.append(f['mat']); g.fl.append(layer)
        g.fcc.append([tuple(c[:3]) + (t,) for c, t in zip(cc, f['team'])]); g.fs.append(f['smooth']); g.fu.append(list(f['pts']))
    return moved

def _cover_tree(variant, lod):
    tris = []; verts = []; key = []
    for layer, parts in COVER.get(variant, {}).items():
        d = _read('%s_lod%d' % (layer, lod))
        if d is None:
            continue
        for f in d['faces']:
            if f['part'] in parts:
                base = len(verts)
                verts += [Vector(d['v'][i]) for i in f['v']]
                tris.append(tuple(range(base, base + len(f['v'])))); key.append((layer, f['part']))
    return (BVHTree.FromPolygons(verts, tris), key) if tris else None

def build(variant, lod):
    g = HP.Geo()
    g.fcc = []; g.fs = []; g.fu = []
    tree = _cover_tree(variant, lod)
    g.v3_info = {'mesh': 'horse_v3 ab70c61', 'pushed': 0}
    for layer in LAYERS[variant]:
        hide = HIDE_PARTS.get(variant, {}).get(layer, set())
        mv = add_layer(g, layer, lod, hide=hide, push=PUSH[variant] if layer == 'horse_body' and tree else None, cover=tree)
        g.v3_info['pushed'] += mv
    n0 = len(g.f)
    if variant == 'med_knight':
        HP.build_lance(g, lod)
    HP.build_rider(g, lod, variant)
    for _ in range(len(g.f) - len(g.fcc)):   # proxy faces: flat colour, flat shading
        g.fcc.append(None); g.fs.append(False); g.fu.append(None)
    assert len(g.fcc) == len(g.f) == len(g.fs)
    print('V3MESH', variant, 'lod', lod, 'verts', len(g.v), 'faces', len(g.f), 'bill_faces', n0, 'pushed', g.v3_info['pushed'])
    return g
