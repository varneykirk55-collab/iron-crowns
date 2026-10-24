"""Horse v3 generator: anatomical horse body + hair + eyes, 1300 / 1800 tack and 1300 barding as separate mesh
layers, one separate horse armature (bones + sockets from horse_v3_config), smooth skin weights, LOD0/1/2 glbs.

run:  blender -b --python pipeline/blender/horse_v3.py            (from the repo root)
out:  game/assets/models/horse_v3/horse_v3_lod{0,1,2}.glb, horse_v3.blend, horse_v3_stats.json
Encoding = legacy MeshBuilder: UVMap.v = mat/16 (UVMap.u = coat 'points' mask on the body, 0 elsewhere),
VID = (vertex id, team mask), Col = sRGB vertex colour (alpha = team).  Coat variants are extra blend-only colour
attributes (coat_<name>); only 'Col' (= bay) is exported."""
import bpy, bmesh, json, math, os, sys, time
import numpy as np
from mathutils import Vector, kdtree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import horse_v3_config as C
import horse_v3_sdf as S
import horse_v3_parts as HP

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'game', 'assets', 'models', 'horse_v3')
LAYER_TARGET = {'horse_body': C.LOD['body'], 'horse_hair': C.LOD['hair'], 'horse_eyes': C.LOD['eyes'],
                'tack_1800': C.LOD['tack_1800'], 'tack_1300': C.LOD['tack_1300'],
                'barding_1300': C.LOD['barding_1300']}
t0 = time.time()

def log(*a):
    print('[horse_v3 %6.1fs]' % (time.time() - t0), *a, flush=True)

def rn(name):
    return C.BONE_RENAME.get(name, name)

# ---------------------------------------------------------------------------------------------------------------------
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def all_bones():
    """modelling-frame segments used for weighting (anatomical bones, sockets, spec tail / rein chains)."""
    return list(C.BONES) + list(C.SOCKETS) + list(C.MODEL_EXTRA_BONES)

NON_DEFORM = {'root', 'rider_seat', 'lance', 'bridle'}

def build_armature():
    """the exported armature is Rob's HX rig (spec v1.2 coords and names, C.SPEC_BONES)."""
    arm = bpy.data.armatures.new('horse_v3_rig')
    rig = bpy.data.objects.new('horse_v3_rig', arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for n, h, t, p in C.SPEC_BONES:
        d = n not in NON_DEFORM
        b = arm.edit_bones.new(n)
        b.head = Vector(h); b.tail = Vector(t)
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0.05, 0))
        b.use_deform = bool(d)
        eb[n] = (b, p)
    for n, (b, p) in eb.items():
        if p and p in eb:
            b.parent = eb[p][0]
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig

# ---------------------------------------------------------------------------------------------------------------------
class Ctx:
    """weight helpers.  bones: name -> (head, tail)"""
    def __init__(self, bones):
        self.seg = {n: (np.array(h, float), np.array(t, float)) for n, h, t, p, d in bones}
        self.body = None      # (kd, verts, W[name] arrays) after the body LOD0 is weighted

    def seg_dist(self, P, name):
        a, b = self.seg[name]; e = b - a
        t = np.clip(((P - a) @ e) / max(e @ e, 1e-12), 0, 1)
        return np.linalg.norm(P - (a + t[:, None] * e), axis=1)

    def chain(self, P, names, sigma):
        D = np.stack([self.seg_dist(P, n) for n in names], 1)
        W = np.exp(-((D - D.min(1, keepdims=True)) / sigma) ** 2)
        W /= W.sum(1, keepdims=True)
        return {n: W[:, i] for i, n in enumerate(names)}

    def transfer(self, P, k=6):
        kd, BV, BW = self.body
        out = {n: np.zeros(len(P)) for n in BW}
        for i, p in enumerate(P):
            hits = kd.find_n(Vector(p), k)
            ws = np.array([1.0 / (h[2] + 0.004) ** 2 for h in hits]); ws /= ws.sum()
            for (co, idx, dist), w in zip(hits, ws):
                for n, arr in BW.items():
                    v = arr[idx]
                    if v:
                        out[n][i] += w * v
        return out

def normalize_top4(W, nv):
    names = [n for n in W if np.any(W[n] > 1e-6)]
    M = np.stack([np.asarray(W[n], float) for n in names], 1) if names else np.zeros((nv, 0))
    if M.shape[1] > 4:
        idx = np.argsort(-M, axis=1)[:, 4:]
        np.put_along_axis(M, idx, 0, axis=1)
    M[M < 0.01] = 0
    s = M.sum(1, keepdims=True); s[s == 0] = 1
    M = M / s
    return {n: M[:, i] for i, n in enumerate(names)}

def smooth_weights(W, edges, nv, iters):
    if iters <= 0 or len(edges) == 0:
        return W
    deg = np.bincount(edges.ravel(), minlength=nv).astype(float); deg[deg == 0] = 1
    for n in list(W):
        w = np.asarray(W[n], float)
        for _ in range(iters):
            acc = np.zeros(nv)
            np.add.at(acc, edges[:, 0], w[edges[:, 1]]); np.add.at(acc, edges[:, 1], w[edges[:, 0]])
            w = 0.5 * w + 0.5 * acc / deg
        W[n] = w
    return W

# ---------------------------------------------------------------------------------------------------------------------
def mesh_from(V, F, name, fcls=None):
    F = [list(map(int, f)) for f in F]
    if fcls is not None:
        keep = [i for i, f in enumerate(F) if len(set(f)) == len(f) and len(f) >= 3]
        F = [F[i] for i in keep]; fcls = np.asarray(fcls, int)[keep]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in np.asarray(V, float)], [], F)
    if fcls is None:
        me.validate()
    else:
        a = me.attributes.new('fc', 'INT', 'FACE'); a.data.foreach_set('value', fcls.astype(np.int32))
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

def tri_count_raw(F):
    return sum(len(f) - 2 for f in F)

def _eval_mesh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    return me

def _read(me):
    nV = len(me.vertices); nL = len(me.loops)
    Vo = np.zeros(nV * 3); me.vertices.foreach_get('co', Vo); Vo = Vo.reshape(-1, 3)
    lv = np.zeros(nL, int); me.loops.foreach_get('vertex_index', lv)
    fc = None
    if 'fc' in me.attributes:
        fc = np.zeros(len(me.polygons), np.int32); me.attributes['fc'].data.foreach_get('value', fc)
    return Vo, lv.reshape(-1, 3), fc

def process(part, lod, target):
    """-> numpy (V, T, fc) after smooth / remesh / decimate / triangulate.  target = tri budget for geo parts."""
    if 'gen' in part:
        g = part['gen'](lod)
        if g is None:
            return None
        V, F, fcl = g
        ob = mesh_from(V, F, 'tmp_' + part['name'], fcl)
    else:
        V, F = part['geo']
        ob = mesh_from(V, F, 'tmp_' + part['name'])
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()
    if 'geo' in part:
        if part.get('smooth', 0):
            m = ob.modifiers.new('sm', 'SMOOTH'); m.factor = 0.5; m.iterations = part['smooth']
        if part.get('voxel'):
            # surface-nets output has non-manifold edges that stall collapse decimation: voxel remesh first
            m = ob.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = part['voxel'] * (part.get('lod_voxel') or (1, 1, 1))[lod]; m.adaptivity = 0.0
            m.use_smooth_shade = True
        me = _eval_mesh(ob)
        ntri = sum(len(p.vertices) - 2 for p in me.polygons)
        bpy.data.objects.remove(ob)
        ob = bpy.data.objects.new('tmp2_' + part['name'], me)
        bpy.context.scene.collection.objects.link(ob)
        ratio = target / max(ntri, 1)
        if ratio < 0.999:
            # chain collapse stages of ratio >= ~0.15 (one very small ratio stalls on these meshes), then tighten the
            # last stage until the result fits (+8 %); fall back to non-symmetric collapse if symmetry gets stuck
            stages = max(1, int(math.ceil(math.log(ratio) / math.log(0.15))))
            r1 = ratio ** (1.0 / stages)
            mods = []
            for k in range(stages):
                m = ob.modifiers.new('dec%d' % k, 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = r1
                if part.get('sym'):
                    m.use_symmetry = True; m.symmetry_axis = 'X'
                mods.append(m)
            m = mods[-1]
            def count():
                me2 = _eval_mesh(ob)
                n = sum(len(p.vertices) - 2 for p in me2.polygons)
                bpy.data.meshes.remove(me2)
                return n
            for attempt in range(2):
                for _ in range(6):
                    nt2 = count()
                    if nt2 <= target * 1.08:
                        break
                    m.ratio = max(m.ratio * target / nt2 * 0.97, 0.01)
                if nt2 <= target * 1.08 or not part.get('sym'):
                    break
                for mm in mods:
                    mm.use_symmetry = False
                m.ratio = r1
    if part.get('sharp'):
        # spec v1.2: normals are recomputed per frame in the bake -> hard edges must be real splits
        m = ob.modifiers.new('es', 'EDGE_SPLIT'); m.split_angle = math.radians(part['sharp'])
        m.use_edge_angle = True; m.use_edge_sharp = True
    m = ob.modifiers.new('tri', 'TRIANGULATE')
    me = _eval_mesh(ob)
    Vo, T, fc = _read(me)
    bpy.data.meshes.remove(me)
    bpy.data.objects.remove(ob)
    return Vo, T, fc

def part_data(part, lod, target, ctx):
    r = process(part, lod, target)
    if r is None:
        return None
    V, T, fc = r
    ok = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 2] != T[:, 0])
    T = T[ok]; fc = fc[ok] if fc is not None else None
    _, first = np.unique(np.sort(T, 1), axis=0, return_index=True)
    first = np.sort(first)
    T = T[first]; fc = fc[first] if fc is not None else None
    Pc = V[T].mean(1)
    code = np.asarray(fc if fc is not None else part['cls'](Pc), int)
    fm = code % 100
    Pcorner = V[T.ravel()]
    rgb, team = part['col'](Pcorner, np.repeat(code, 3))
    cm = np.repeat(fm, 3)
    coats = {}
    if part.get('coat'):
        for cn in C.COATS:
            c = HP.hoof_blend(Pcorner, HP.coat_rgb(Pcorner, cn))
            coats[cn] = c
        u = HP.points_mask(Pcorner)
        u[cm != HP.MAT_HIDE] = 0
    elif part.get('hair'):
        for cn in C.COATS:
            coats[cn] = np.tile(C.COATS[cn]['hair'], (len(Pcorner), 1))
        u = np.zeros(len(Pcorner))
    else:
        u = np.zeros(len(Pcorner))
    w = part['w']
    if isinstance(w, str):
        W = {w.split(':', 1)[1]: np.ones(len(V))}
    else:
        W = w(V, ctx)
    edges = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], 0)
    W = smooth_weights(W, edges, len(V), part.get('wsmooth', 0))
    W = normalize_top4(W, len(V))
    return dict(V=V, T=T, fm=fm, rgb=np.asarray(rgb, float), team=np.asarray(team, float), u=u, coats=coats, W=W,
                name=part['name'])

def build_layer_object(name, datas, rig, coll):
    V = []; T = []; fm = []; rgb = []; team = []; u = []; W = {}; coats = {}; pid = []
    o = 0
    for i, d in enumerate(datas):
        V.append(d['V']); T.append(d['T'] + o); fm.append(d['fm']); rgb.append(d['rgb']); team.append(d['team'])
        u.append(d['u']); pid.append(np.full(len(d['T']), i))
        for n, w in d['W'].items():
            W.setdefault(n, []).append((o, w))
        for cn, c in d['coats'].items():
            coats.setdefault(cn, []).append((sum(len(x['T']) for x in datas[:i]) * 3, c))
        o += len(d['V'])
    V = C.WARP(np.concatenate(V)); T = np.concatenate(T); fm = np.concatenate(fm); rgb = np.concatenate(rgb)
    team = np.concatenate(team); u = np.concatenate(u); pid = np.concatenate(pid)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V)); me.vertices.foreach_set('co', V.ravel())
    me.loops.add(len(T) * 3); me.loops.foreach_set('vertex_index', T.ravel())
    me.polygons.add(len(T)); me.polygons.foreach_set('loop_start', np.arange(len(T)) * 3)
    me.update(calc_edges=True)
    nL = len(T) * 3
    col = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    c4 = np.concatenate([np.clip(rgb, 0, 1), team[:, None]], 1).astype(np.float32)
    col.data.foreach_set('color_srgb', c4.ravel())
    for cn, chunks in coats.items():
        full = np.concatenate([np.clip(rgb, 0, 1), team[:, None]], 1).astype(np.float32)
        for start, c in chunks:
            full[start:start + len(c), :3] = c
        a = me.color_attributes.new('coat_' + cn, 'BYTE_COLOR', 'CORNER')
        a.data.foreach_set('color_srgb', full.ravel())
    me.color_attributes.active_color = me.color_attributes['Col']
    me.color_attributes.render_color_index = me.color_attributes.find('Col')
    uv0 = me.uv_layers.new(name='UVMap')
    uvv = np.stack([u, np.repeat(fm, 3) / 16.0], 1).astype(np.float32)
    uv0.data.foreach_set('uv', uvv.ravel())
    uv1 = me.uv_layers.new(name='VID')
    lv = T.ravel()
    uv1.data.foreach_set('uv', np.stack([(lv + 0.5) / len(V), team], 1).astype(np.float32).ravel())
    me.polygons.foreach_set('use_smooth', np.ones(len(T), bool))
    a = me.attributes.new('mat_id', 'INT', 'FACE'); a.data.foreach_set('value', fm.astype(np.int32))
    a = me.attributes.new('part_id', 'INT', 'FACE'); a.data.foreach_set('value', pid.astype(np.int32))
    me.materials.append(vcol_material())
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for n, chunks in W.items():
        g = ob.vertex_groups.new(name=rn(n))
        full = np.zeros(len(V))
        for start, w in chunks:
            full[start:start + len(w)] = w
        idx = np.nonzero(full > 0)[0]
        for i in idx:
            g.add([int(i)], float(full[i]), 'REPLACE')
    ob.parent = rig
    md = ob.modifiers.new('rig', 'ARMATURE'); md.object = rig
    ob['parts'] = json.dumps([d['name'] for d in datas])
    return ob, len(T), len(V)

def vcol_material():
    if 'VertexColour' in bpy.data.materials:
        return bpy.data.materials['VertexColour']
    m = bpy.data.materials.new('VertexColour'); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get('Principled BSDF')
    at = nt.nodes.new('ShaderNodeVertexColor'); at.layer_name = 'Col'
    nt.links.new(at.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    return m

# ---------------------------------------------------------------------------------------------------------------------
def main():
    reset()
    os.makedirs(OUT, exist_ok=True)
    log('building part fields')
    groups = HP.all_parts()
    layers = {'horse_body': groups['body'], 'horse_hair': groups['hair'], 'horse_eyes': groups['eyes'],
              'tack_1800': groups['tack_1800'], 'tack_1300': groups['tack_1300'], 'barding_1300': groups['barding_1300']}
    bones = all_bones()
    rig = build_armature()
    ctx = Ctx(bones)
    stats = {'lods': {}, 'parts': {}}
    lod_objs = {}
    for lod in (0, 1, 2):
        coll = bpy.data.collections.new('LOD%d' % lod)
        bpy.context.scene.collection.children.link(coll)
        lod_objs[lod] = []
        stats['lods'][lod] = {}
        for lname, parts in layers.items():
            target = LAYER_TARGET[lname][lod]
            vb = C.VBUDGET[lname][lod]
            if vb <= 0:
                continue
            parts = [p for p in parts if lod not in p.get('skip', ())]
            geo = [p for p in parts if 'geo' in p]
            fixed = sum(p['budget'][lod] for p in geo if 'budget' in p)
            free = [p for p in geo if 'budget' not in p]
            raw = sum(len(p['geo'][1]) for p in free)
            free_t = target if free else 0
            # vertex budget (spec v1.2 counts Blender verts after splits): pick the largest parametric resolution
            # multiplier that fits; SDF parts are estimated at ~0.52 verts / tri
            for res in C.RES_STEPS:
                HP.PM.RES = res
                gv = 0
                for p in parts:
                    if 'gen' in p:
                        g = p['gen'](lod)
                        if g is not None:
                            gv += len(g[0]) * p.get('vmul', 1.0)
                est = gv + 0.52 * (fixed + free_t)
                if est <= vb:
                    break
            log('LOD%d %-13s RES %.2f est %d / budget %d verts' % (lod, lname, HP.PM.RES, est, vb))
            stats.setdefault('res', {}).setdefault(lname, {})[lod] = HP.PM.RES
            datas = []
            for p in parts:
                if 'gen' in p:
                    r = 0
                elif 'budget' in p:
                    r = p['budget'][lod]
                else:
                    r = free_t * len(p['geo'][1]) / max(raw, 1)
                if lname == 'horse_body' and lod == 0 and ctx.body is None:
                    pass
                d = part_data(p, lod, r, ctx)
                if d is None:
                    continue
                datas.append(d)
                stats['parts'].setdefault(lname, {}).setdefault(p['name'], {})[lod] = [int(len(d['T'])), int(len(d['V']))]
                if lname == 'horse_body':
                    kd = kdtree.KDTree(len(d['V']))
                    for i, v in enumerate(d['V']):
                        kd.insert(Vector(v), i)
                    kd.balance()
                    ctx.body = (kd, d['V'], d['W'])
            if not datas:
                continue
            HP.PM.RES = 1.0
            ob, nt, nv = build_layer_object('%s_lod%d' % (lname, lod), datas, rig, coll)
            lod_objs[lod].append(ob)
            stats['lods'][lod][lname] = {'tris': nt, 'verts': nv}
            log('LOD%d %-13s %6d tris %5d verts  parts %s' % (lod, lname, nt, nv, [(d['name'], len(d['T']), len(d['V'])) for d in datas]))
    # export
    for lod in (0, 1, 2):
        bpy.ops.object.select_all(action='DESELECT')
        for o in lod_objs[lod]:
            o.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        path = os.path.join(OUT, 'horse_v3_lod%d.glb' % lod)
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_skins=True,
                                  export_animations=False, export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                                  export_texcoords=True, export_normals=True, export_morph=False,
                                  export_attributes=False)
        log('exported', path, os.path.getsize(path))
    for lod in (1, 2):
        bpy.data.collections['LOD%d' % lod].hide_render = True
        bpy.data.collections['LOD%d' % lod].hide_viewport = True
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'horse_v3.blend'), compress=True)
    stats['sockets'] = {n: {'head': list(h), 'tail': list(t), 'parent': p} for n, h, t, p in C.SPEC_BONES
                        if n in C.SOCKET_NAMES}
    stats['bones'] = [b[0] for b in C.SPEC_BONES]
    groups = {}
    for lod in (0, 1, 2):
        for o in lod_objs[lod]:
            groups[o.name] = sorted(g.name for g in o.vertex_groups)
    stats['vertex_groups'] = groups
    spec_names = set(stats['bones'])
    stats['unknown_groups'] = sorted({g for v in groups.values() for g in v if g not in spec_names})
    # per-variant totals (verts), spec v1.2 budgets: LOD0 horse <= 4.4k, tack+barding <= 1.7k; LOD1 horse+tack
    # <= 1.5k; LOD2 horse+tack <= 0.6k
    L = stats['lods']
    def tot(lod, names):
        return sum(L[lod][n]['verts'] for n in names if n in L[lod])
    horse = ['horse_body', 'horse_hair', 'horse_eyes']
    stats['totals'] = {v: {lod: {'horse': tot(lod, horse), 'kit': tot(lod, kit), 'horse+kit': tot(lod, horse + kit)}
                           for lod in (0, 1, 2)}
                       for v, kit in (('hx_c19_hussar', ['tack_1800']), ('hx_med_knight', ['tack_1300', 'barding_1300']))}
    with open(os.path.join(OUT, 'horse_v3_stats.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    log('done', json.dumps(stats['lods']))

main()
