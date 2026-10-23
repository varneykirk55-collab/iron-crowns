"""c19v2 line fusilier prototype build (headless):
   blender -b --python pipeline/blender/char_v2_build.py -- [all|mesh|bake]
Builds the sculpted high-poly + game meshes (char_v2.py), skins the game meshes to the unchanged char_rig.BONES
(+ unweighted leaf helper 'weapon_tip' under prop), UV-packs one shared atlas, bakes normal + AO + slot-id maps from the
high-poly in Cycles, derives mid / far sets by weighted decimation, and bakes the VAT exactly like char_build.bake
(same clip rows, same json keys) plus 'weapon_tip' per clip.
Outputs: game/assets/vat/c19v2_line_lod{0,1}.{vat,vatn,json}, game/assets/vat/c19v2_line_maps.vat (raw RGBA8:
normal map rows then id map rows, see json 'maps'), game/assets/models/soldier_c19v2_line_lod{0,1}.glb,
out/proto/bake/*.png (map previews), blend/soldier_c19v2_line.blend."""
import sys, os, math, json, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import common
import char_rig as R
import char_body as B
import char_v2 as C
import char_build as CB

KID = 'c19v2_line'
TEX = int(os.environ.get('V2_TEX', '2048'))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTP = os.path.join(ROOT, 'out', 'proto', 'bake')
LO_VOXEL = float(os.environ.get('V2_LO_VOXEL', '0.013'))
BODY_TRIS = int(os.environ.get('V2_BODY_TRIS', '6500'))   # LOD0 budget raised to ~8-12k (Kirk, 12:33 EDT)
MID_TRIS = int(os.environ.get('V2_MID_TRIS', '2000'))
FAR_TRIS = int(os.environ.get('V2_FAR_TRIS', '700'))
TIP_LOCAL = (0.02, 1.52, -0.006)    # bayonet tip in prop-local coordinates (char_body.build_musket / char_v2.musket)
DEFORM = [b[0] for b in R.BONES if b[0] not in ('root', 'prop')]

def log(*a):
    print('[v2]', *a, flush=True)

# ------------------------------------------------------------------ rigs
def build_rig(name, spread=0.0):
    rig = CB.build_rig(name)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    if spread:
        for s, sfx in ((1, '.R'), (-1, '.L')):
            eb['clav' + sfx].tail.x += s * spread
            for b in ('upper_arm', 'forearm', 'hand'):
                eb[b + sfx].head.x += s * spread; eb[b + sfx].tail.x += s * spread
    else:
        tip = eb.new('weapon_tip')                    # leaf helper: unweighted, child of prop, at the bayonet tip
        p = R.REST['prop'] @ Vector(TIP_LOCAL)
        ax = (R.REST['prop'].to_3x3() @ Vector((0, 1, 0))).normalized()
        tip.head = p; tip.tail = p + ax * 0.05; tip.roll = 0.0
        tip.parent = eb['prop']; tip.use_connect = False; tip.use_deform = False
    if spread:   # heat-weight rig only: keep root / prop out of the body's automatic weights (the game rig deforms with prop)
        for n in ('root', 'prop'):
            eb[n].use_deform = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig

def add_groups(o):
    for n in [b[0] for b in R.BONES]:
        if n not in o.vertex_groups:
            o.vertex_groups.new(name=n)

def rigid(o, bone):
    add_groups(o)
    o.vertex_groups[bone].add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')

def auto_weights(o, rig):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    o.parent = None
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    add_groups(o)

def transfer_weights(src, dst):
    add_groups(dst)
    bm = bmesh.new(); bm.from_mesh(src.data); tree = BVHTree_from(bm)
    dl = src.data.vertices
    gi = {g.index: g.name for g in src.vertex_groups}
    for v in dst.data.vertices:
        loc, nrm, fi, d = tree.find_nearest(v.co)
        if fi is None: continue
        f = src.data.polygons[fi]
        acc = {}
        ws = []
        for vi in f.vertices:
            w = 1.0 / max((dl[vi].co - v.co).length, 1e-4)
            ws.append((vi, w))
        tot = sum(w for _, w in ws)
        for vi, w in ws:
            for g in dl[vi].groups:
                acc[gi[g.group]] = acc.get(gi[g.group], 0.0) + g.weight * w / tot
        s = sum(acc.values()) or 1.0
        for n, w in acc.items():
            if w / s > 0.01:
                dst.vertex_groups[n].add([v.index], w / s, 'REPLACE')
    bm.free()

def BVHTree_from(bm):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromBMesh(bm)

def tail_weights(o):
    add_groups(o)
    for v in o.data.vertices:
        z = v.co.z; side = '.R' if v.co.x > 0 else '.L'
        wt = 0.45 * C.ss(0.98, 0.62, z)
        o.vertex_groups['hips'].add([v.index], 1.0 - wt, 'REPLACE')
        if wt > 0.001:
            o.vertex_groups['thigh' + side].add([v.index], wt, 'REPLACE')

RULES = [  # object-name prefix -> weight rule
    (('head', 'shako', 'peak', 'plume', 'cockade'), 'head'), (('handR',), 'hand.R'), (('handL',), 'hand.L'),
    (('pack', 'roll', 'strap'), 'chest'), (('stock', 'barrel', 'band', 'lock', 'socket', 'bayonet', 'sling'), 'prop'),
    (('cart', 'scab', 'hilt'), 'hips'), (('tail',), 'tail'), (('belt', 'collar'), 'transfer')]

def rule_for(name):
    for pre, r in RULES:
        if name.split('.')[0] in pre or any(name.startswith(p) for p in pre):
            return r
    raise KeyError(name)

# ------------------------------------------------------------------ geometry
def joint_keep(o, spread):
    """vertex group 'keep' (decimate protection) around shoulders, elbows, wrists, hips, knees, ankles, neck."""
    g = o.vertex_groups.new(name='keep')
    J = []
    for s in (1, -1):
        J += [(Vector((s * (0.18 + spread), -0.012, 1.42)), 0.07), (Vector((s * (0.205 + spread), -0.012, 1.14)), 0.06),
              (Vector((s * (0.222 + spread), 0.0, 0.92)), 0.04), (Vector((s * 0.095, 0.0, 0.93)), 0.09),
              (Vector((s * 0.1, 0.012, 0.505)), 0.07), (Vector((s * 0.1, -0.012, 0.09)), 0.05)]
    J += [(Vector((0, 0, 1.50)), 0.06)]
    for v in o.data.vertices:
        w = max(math.exp(-((v.co - c).length / r) ** 2) for c, r in J)
        g.add([v.index], w, 'REPLACE')

def decimate(o, target, group=None, sym=True):
    m = o.modifiers.new('d', 'DECIMATE'); m.ratio = min(1.0, target / max(1, C.tris(o)))
    m.use_collapse_triangulate = True
    if sym: m.use_symmetry = True; m.symmetry_axis = 'X'
    if group: m.vertex_group = group; m.vertex_group_factor = 4.0; m.invert_vertex_group = True
    C.apply_mods(o)

def relax(o, target, iters=6):
    """Even out decimation slivers / folds: Laplacian relax, snap back onto the sculpt, then beautify the triangulation."""
    m = o.modifiers.new('s', 'LAPLACIANSMOOTH'); m.iterations = iters; m.lambda_factor = 0.4; m.use_volume_preserve = True
    w = o.modifiers.new('w', 'SHRINKWRAP'); w.target = target; w.wrap_method = 'NEAREST_SURFACEPOINT'
    C.apply_mods(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.beautify_fill()
    bpy.ops.object.mode_set(mode='OBJECT')

BODY_KEYS = ('collar', 'button')
AO_AWAY = set()   # part groups moved out of the way for the AO bake (hands hang by the thighs in the rest pose)   # lo collar shell / hi-only buttons bake against the body group (pid 0)

def build_meshes():
    t0 = time.time()
    parts = C.build_body_parts(); near = C.nearest_part(parts)
    hi = C.fuse(parts, 0.005); C.drop_small_islands(hi); C.slot_body(hi, near)
    C.add_folds(hi, C.SPREAD)   # cloth folds + seams (bake source)
    # low cage from a coarser remesh of the same parts: thin ledges (lapels, cuffs, collar) melt into the volume and come
    # back through the normal map, instead of decimating the 5 mm sculpt into slivers / folds
    lo = C.fuse({k: v for k, v in parts.items() if k != 'collar'}, LO_VOXEL, 'body'); C.drop_small_islands(lo); C.slot_body(lo, near)
    sm = lo.modifiers.new('sm', 'CORRECTIVE_SMOOTH'); sm.iterations = 4; sm.smooth_type = 'SIMPLE'; sm.use_only_smooth = True
    C.apply_mods(lo)
    joint_keep(lo, C.SPREAD)
    decimate(lo, BODY_TRIS, 'keep')
    lo.vertex_groups.remove(lo.vertex_groups['keep'])
    # skin the body while the arms are still spread (clean heat weights, no arm/rib bleeding), then move the arms back
    srig = build_rig('spread', C.SPREAD)
    auto_weights(lo, srig)
    bpy.data.objects.remove(srig)
    C.unspread(hi, near); C.unspread(lo, near)
    for v in parts.values():
        for o in v: bpy.data.objects.remove(o)
    tree = C.surface_tools([hi])
    kit_hi = C.build_kit(True, tree); kit_lo = C.build_kit(False, tree)
    for o in kit_lo:
        r = rule_for(o.name)
        if r == 'tail': tail_weights(o)
        elif r == 'transfer': transfer_weights(lo, o)
        else: rigid(o, r)
    import re
    def gkey(o): return re.match(r'[A-Za-z]*', o.name.split('.')[0]).group(0)
    keys = sorted(set(gkey(o) for o in kit_hi + kit_lo))
    log('part groups', keys)
    for o in [hi, lo] + kit_hi + kit_lo:   # group id: the normal / id bakes are 'exploded' per group (no cross-part ray hits)
        i = 0 if o in (hi, lo) or gkey(o) in BODY_KEYS else 1 + keys.index(gkey(o))
        if gkey(o) in ('handL', 'handR'): AO_AWAY.add(i)   # lo collar shell bakes from the fused hi body
        at = o.data.attributes.new('pid', 'FLOAT', 'POINT'); at.data.foreach_set('value', [float(i)] * len(o.data.vertices))
    for o in [hi] + kit_hi:   # painted detail default (neutral) where nothing was painted
        if 'det2' not in o.data.attributes: C.set_det(o, lambda p: C.NEUTRAL)
    H = C.join([hi] + kit_hi, 'HI')
    sl = np.zeros(len(H.data.polygons), np.int32); H.data.attributes['slot'].data.foreach_get('value', sl)
    mk = H.data.attributes.new('matk', 'FLOAT', 'FACE')
    mk.data.foreach_set('value', [float(C.M[C.SLOT_MAT.get(B.SLOT_NAMES[x], 'wool')]) for x in sl])
    L = C.join([lo] + kit_lo, KID + '_lod0')
    for o in (H, L): o.data.validate()
    for p in L.data.polygons: p.use_smooth = True
    for p in H.data.polygons: p.use_smooth = True
    log('meshes', 'hi tris', C.tris(H), 'lod0 tris', C.tris(L), round(time.time() - t0, 1), 's')
    return H, L

# ------------------------------------------------------------------ atlas + bake
FEATURE_SCALE = 2.4
FACE_SCALE = 3.4     # head gets more again (painted eyes / stubble / lips)   # head / hands get this much more texel density (face paint, fingers)

def unwrap(L):
    me = L.data
    while len(me.uv_layers): me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name='atlas')
    # temporarily enlarge the head + shako + hands so the area-proportional packer gives them more texels
    hv = [v.index for v in me.vertices if (v.co.z > 1.545 and abs(v.co.x) < 0.13 and -0.13 < v.co.y < 0.16 and v.co.z < 2.0)
          or (v.co.z < 0.91 and 0.18 < abs(v.co.x) < 0.25 and v.co.z > 0.70)]
    orig = {i: me.vertices[i].co.copy() for i in hv}
    for i in hv:
        hd = me.vertices[i].co.z > 1.5
        c = Vector((0, 0.01, 1.666)) if hd else Vector((math.copysign(0.215, me.vertices[i].co.x), 0.01, 0.83))
        k = FACE_SCALE if hd and me.vertices[i].co.z < 1.725 else FEATURE_SCALE
        me.vertices[i].co = c + (me.vertices[i].co - c) * k
    bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); bpy.context.view_layer.objects.active = L
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    for i, c in orig.items(): me.vertices[i].co = c

def bake_maps(H, L):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.cage_extrusion = 0.025; sc.render.bake.max_ray_distance = 0.06
    sc.render.bake.margin = 6
    if sc.world is None: sc.world = bpy.data.worlds.new('w')
    sc.world.light_settings.distance = 0.12
    imgs = {}
    for nm, cs in (('nrm', 'Non-Color'), ('ao', 'Non-Color'), ('id', 'Non-Color'), ('det', 'Non-Color')):
        im = bpy.data.images.new(f'{KID}_{nm}', TEX, TEX, alpha=False, float_buffer=False)
        im.colorspace_settings.name = cs; imgs[nm] = im
    # low: one material with an image node per bake target (active node = target)
    lm = bpy.data.materials.new('bake_lo'); lm.use_nodes = True
    L.data.materials.clear(); L.data.materials.append(lm)
    tn = lm.node_tree.nodes.new('ShaderNodeTexImage')
    # high: emission of the slot attribute (for the id bake) + plain diffuse
    hm = bpy.data.materials.new('bake_hi'); hm.use_nodes = True
    nt = hm.node_tree; nt.nodes.clear()
    at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'slot'; at.attribute_type = 'GEOMETRY'
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 8.0 / 255.0
    em = nt.nodes.new('ShaderNodeEmission'); df = nt.nodes.new('ShaderNodeBsdfDiffuse')
    add = nt.nodes.new('ShaderNodeAddShader'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(at.outputs['Fac'], mul.inputs[0]); nt.links.new(mul.outputs[0], em.inputs['Color'])
    nt.links.new(em.outputs[0], add.inputs[0]); nt.links.new(df.outputs[0], add.inputs[1]); nt.links.new(add.outputs[0], out.inputs[0])
    det_rgb = detail_nodes(nt, df)
    H.data.materials.clear(); H.data.materials.append(hm)
    for a in ('visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'):
        setattr(L, a, False)   # the low cage must not occlude the high-poly AO rays
    bpy.ops.object.select_all(action='DESELECT'); H.select_set(True); L.select_set(True); bpy.context.view_layer.objects.active = L
    def explode(sign):
        for o in (H, L):
            pid = np.zeros(len(o.data.vertices), np.float32); o.data.attributes['pid'].data.foreach_get('value', pid)
            co = np.zeros(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', co)
            co = co.reshape(-1, 3); co[:, 0] += sign * pid * 4.0
            o.data.vertices.foreach_set('co', co.ravel()); o.data.update()
    def away(sign):
        for o in (H, L):
            pid = np.zeros(len(o.data.vertices), np.float32); o.data.attributes['pid'].data.foreach_get('value', pid)
            co = np.zeros(len(o.data.vertices) * 3, np.float32); o.data.vertices.foreach_get('co', co)
            co = co.reshape(-1, 3); co[np.isin(np.round(pid).astype(int), list(AO_AWAY)), 2] += sign * 10.0
            o.data.vertices.foreach_set('co', co.ravel()); o.data.update()
    away(1.0)
    for nm, typ, smp in (('ao', 'AO', 64), ('nrm', 'NORMAL', 1), ('id', 'EMIT', 1), ('det', 'EMIT', 4)):
        if nm == 'nrm': away(-1.0); explode(1.0)   # AO in place (belts / pack occlude the coat); normal + id + detail per part pair
        nt.links.new((det_rgb if nm == 'det' else mul.outputs[0]), em.inputs['Color'])
        tn.image = imgs[nm]; lm.node_tree.nodes.active = tn
        sc.cycles.samples = smp
        sc.cycles.filter_width = 0.01 if nm == 'id' else 1.5   # no AA blending between slot ids
        sc.render.bake.margin_type = 'EXTEND'
        sc.cycles.filter_width = 0.01 if nm == 'id' else 1.5
        t0 = time.time()
        kw = dict(type=typ)
        if typ == 'NORMAL': kw.update(normal_space='TANGENT')
        bpy.ops.object.bake(**kw)
        log('baked', nm, round(time.time() - t0, 1), 's')
    explode(-1.0)
    px = {k: np.array(v.pixels[:], np.float32).reshape(TEX, TEX, 4) for k, v in imgs.items()}
    return px

def detail_nodes(nt, df):
    """High-poly bake material detail: bump (-> baked into the normal map) and the painted detail emission
    (r = luminance variation, g = per-material detail: skin stubble/ruddy + eyes from 'det2', wear on brass / leather)."""
    N = nt.nodes.new; L = nt.links.new
    def attr(name, typ='GEOMETRY'):
        a = N('ShaderNodeAttribute'); a.attribute_name = name; a.attribute_type = typ; return a.outputs['Fac']
    def math(op, a, b=None, c=None, v=None):
        m = N('ShaderNodeMath'); m.operation = op
        for k, x in enumerate((a, b, c)):
            if x is None: continue
            if isinstance(x, (int, float)): m.inputs[k].default_value = x
            else: L(x, m.inputs[k])
        return m.outputs[0]
    def add(*xs):
        acc = xs[0]
        for x in xs[1:]: acc = math('ADD', acc, x)
        return acc
    mk = attr('matk'); det2 = attr('det2')
    def mask(*ks): return add(*[math('COMPARE', mk, float(k), 0.1) for k in ks])
    tc = N('ShaderNodeTexCoord')
    def noise(scale, detail=3.0):
        n = N('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        L(tc.outputs['Object'], n.inputs['Vector']); return math('SUBTRACT', n.outputs['Fac'], 0.5)
    nF = noise(900.0, 4.0); nM = noise(220.0, 3.0); nL = noise(40.0, 2.0)
    wv = N('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'DIAGONAL'
    wv.inputs['Scale'].default_value = 250.0; wv.inputs['Distortion'].default_value = 1.5
    L(tc.outputs['Object'], wv.inputs['Vector']); tw = math('SUBTRACT', wv.outputs['Fac'], 0.5)
    vo = N('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 650.0; L(tc.outputs['Object'], vo.inputs['Vector'])
    gr = math('SUBTRACT', vo.outputs['Distance'], 0.5)
    uv = N('ShaderNodeUVMap'); uv.uv_map = 'st'; sp = N('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sp.inputs[0])
    band = add(math('COMPARE', sp.outputs['Y'], 0.12, 0.035), math('COMPARE', sp.outputs['Y'], 0.88, 0.035))
    dash = math('LESS_THAN', math('FRACT', math('MULTIPLY', sp.outputs['X'], 180.0)), 0.6)
    stitch = math('MULTIPLY', band, dash)
    wool = mask(B.MAT_WOOL); canvas = mask(B.MAT_CANVAS); lea = mask(B.MAT_LEATHER, B.MAT_HIDE); clay = mask(B.MAT_PIPECLAY)
    skin = mask(B.MAT_SKIN); fur = mask(B.MAT_FUR); wood = mask(B.MAT_WOOD); metal = mask(B.MAT_BRASS, B.MAT_STEEL, B.MAT_IRON)
    # bump height
    h = add(math('MULTIPLY', wool, add(math('MULTIPLY', tw, 0.7), math('MULTIPLY', nF, 0.6))),
            math('MULTIPLY', canvas, math('MULTIPLY', nF, 0.5)), math('MULTIPLY', lea, math('MULTIPLY', gr, 0.5)),
            math('MULTIPLY', clay, math('MULTIPLY', nF, 0.25)), math('MULTIPLY', fur, nF), math('MULTIPLY', skin, math('MULTIPLY', nF, 0.12)),
            math('MULTIPLY', stitch, -1.0))
    bp = N('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.55; bp.inputs['Distance'].default_value = 0.0007
    L(h, bp.inputs['Height']); L(bp.outputs['Normal'], df.inputs['Normal'])
    # luminance detail
    lum = add(0.5, math('MULTIPLY', wool, add(math('MULTIPLY', nF, 0.30), math('MULTIPLY', tw, 0.10), math('MULTIPLY', nM, 0.16), math('MULTIPLY', nL, 0.10))),
              math('MULTIPLY', canvas, add(math('MULTIPLY', nF, 0.18), math('MULTIPLY', nL, 0.08))),
              math('MULTIPLY', lea, add(math('MULTIPLY', nM, 0.35), math('MULTIPLY', nL, 0.15))),
              math('MULTIPLY', clay, add(math('MULTIPLY', nM, 0.12), math('MULTIPLY', nL, 0.06))),
              math('MULTIPLY', skin, add(math('MULTIPLY', nM, 0.10), math('MULTIPLY', nL, 0.08))),
              math('MULTIPLY', fur, math('MULTIPLY', nF, 0.45)), math('MULTIPLY', wood, add(math('MULTIPLY', nM, 0.30), math('MULTIPLY', nL, 0.2))),
              math('MULTIPLY', metal, math('MULTIPLY', nM, 0.12)), math('MULTIPLY', stitch, -0.22))
    # per-material detail: skin / eyes painted, brass + leather edge wear (convexity + noise), rest neutral
    geo = N('ShaderNodeNewGeometry')
    wear = math('ADD', math('MULTIPLY', math('SUBTRACT', geo.outputs['Pointiness'], 0.5), 6.0), math('MULTIPLY', nM, 0.9))
    wear = math('MAXIMUM', math('MINIMUM', wear, 1.0), 0.0)
    wm = add(lea, metal)
    d2 = add(math('MULTIPLY', skin, det2), math('MULTIPLY', wm, wear),
             math('MULTIPLY', math('SUBTRACT', 1.0, add(skin, wm)), C.NEUTRAL))
    cmb = N('ShaderNodeCombineXYZ'); L(lum, cmb.inputs[0]); L(d2, cmb.inputs[1])
    return cmb.outputs[0]

def finish_maps(px):
    """-> nrm RGBA8 (xyz tangent normal, a = AO) and id RGBA8 (r = slot * 8, g = material * 16, b = team mask), top row first."""
    n = px['nrm'][..., :3]; ao = px['ao'][..., 0]
    ids = np.clip(np.round(px['id'][..., 0] * 255.0 / 8.0), 0, 31).astype(np.int32)
    mats = np.array([C.M[C.SLOT_MAT.get(s, 'wool')] for s in B.SLOT_NAMES], np.int32)
    ao = np.clip(0.35 + 0.65 * ao, 0, 1)
    nrm8 = np.concatenate([np.round(n * 255), np.round(ao[..., None] * 255)], -1).astype(np.uint8)
    det = px['det']; lum = np.clip(np.round(det[..., 0] * 255), 0, 255).astype(np.int32)
    d2 = np.clip(np.round(det[..., 1] * 15), 0, 15).astype(np.int32)
    # g = material * 16 + painted detail (4 bit), b = luminance detail (128 = neutral); coat / team = slot 0
    id8 = np.stack([ids * 8, mats[ids] * 16 + d2, lum, np.full_like(ids, 255)], -1).astype(np.uint8)
    nrm8 = nrm8[::-1].copy(); id8 = id8[::-1].copy()   # Blender pixels are bottom row first
    return nrm8, id8, ids[::-1].copy()

def face_slots(o, ids_top):
    """per-face slot = majority of the id map at the face's loop UVs + centre (used by mid / far sets and as fallback)."""
    me = o.data; uv = me.uv_layers['atlas'].data
    res = []
    for p in me.polygons:
        pts = [uv[li].uv for li in p.loop_indices]
        c = sum(pts, Vector((0, 0))) / len(pts)
        votes = {}
        for q in pts + [c, c, c]:
            q = (q * 0.75 + c * 0.25)
            x = min(TEX - 1, max(0, int(q.x * TEX))); y = min(TEX - 1, max(0, int((1 - q.y) * TEX)))
            s = int(ids_top[y, x]); votes[s] = votes.get(s, 0) + 1
        res.append(max(votes.items(), key=lambda kv: kv[1])[0])
    a = me.attributes.get('slot') or me.attributes.new('slot', 'INT', 'FACE')
    a.data.foreach_set('value', res)

# ------------------------------------------------------------------ export attributes
def game_layers(o):
    """UVMap (slot/mat per face, as c19sr), VID (vertex index / team), atlas (3rd layer -> Godot CUSTOM0), Col white."""
    me = o.data
    atl = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers['atlas'].data.foreach_get('uv', atl)
    while len(me.uv_layers): me.uv_layers.remove(me.uv_layers[0])
    for nm in ('UVMap', 'VID', 'atlas'): me.uv_layers.new(name=nm)
    me.uv_layers['atlas'].data.foreach_set('uv', atl)
    n = len(me.vertices); nl = len(me.loops)
    lvi = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', lvi)
    slots = np.zeros(len(me.polygons), np.int32); me.attributes['slot'].data.foreach_get('value', slots)
    u0 = np.zeros(nl * 2, np.float32); u1 = np.zeros(nl * 2, np.float32)
    for p in me.polygons:
        s = int(slots[p.index]); mat = C.M[C.SLOT_MAT.get(B.SLOT_NAMES[s], 'wool')]
        team = 1.0 if s == B.S['coat'] else 0.0
        for li in p.loop_indices:
            u0[2 * li] = (s + 0.5) / 32.0; u0[2 * li + 1] = mat / 16.0
            u1[2 * li] = (lvi[li] + 0.5) / n; u1[2 * li + 1] = team
    me.uv_layers['UVMap'].data.foreach_set('uv', u0); me.uv_layers['VID'].data.foreach_set('uv', u1)
    if 'Col' not in me.color_attributes:
        me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    me.color_attributes['Col'].data.foreach_set('color', np.ones(nl * 4, np.float32))

def concat(objs, name):
    """vertex sets in order (near | mid | far); vertex groups / uv / slot preserved."""
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    out = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(out)
    for g in objs[0].vertex_groups: out.vertex_groups.new(name=g.name)
    return out

# ------------------------------------------------------------------ VAT
def bake_vat(o, rig, lod, extra):
    import char_anim as A
    n = len(o.data.vertices)
    CB.bind(o, rig)
    pos, nrm = [], []
    meta = {'vertices': n, 'fps': 24, 'clips': {}, 'frames': 0, 'kit': KID, 'lod': lod,
            'normals': 'vatn rgba8 (n*0.5+0.5), same rows/cols as .vat', 'weapon_tip': {},
            'weapon_tip_note': "per clip, per frame position of the unweighted 'weapon_tip' bone (child of prop, bayonet tip) "
                               "in the same Godot model space as the .vat rows"}
    meta.update(extra)
    row = 0; worst = 1.0
    tipb = rig.pose.bones['weapon_tip']
    for cn, nf, loop, fn in A.CLIPS:
        tips = []
        for f in range(nf):
            t = f / nf if loop else f / max(1, nf - 1)
            p = A.solve(fn(t, 'musket')); worst = max(worst, p.reach)
            CB.apply(rig, p)
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
    meta['max_reach'] = round(worst, 3)
    base = os.path.join(common.VAT, f'{KID}_lod{lod}')
    open(base + '.vat', 'wb').write(P.tobytes())
    open(base + '.vatn', 'wb').write(np.stack(nrm).tobytes())
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    o.modifiers.clear(); o.parent = None
    me2 = o.data.copy()
    if me2.validate(verbose=True): log('validate fixed mesh', lod)
    st = bpy.data.objects.new(f'{KID}_lod{lod}', me2); bpy.context.scene.collection.objects.link(st)
    common.export_glb([st], os.path.join(common.MODELS, f'soldier_{KID}_lod{lod}.glb'))
    bpy.data.objects.remove(st)
    log('vat', lod, 'verts', n, 'frames', row, 'max reach', round(worst, 3))
    return meta

def save_png(arr, path):
    im = bpy.data.images.new(os.path.basename(path), arr.shape[1], arr.shape[0], alpha=True)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set((arr[::-1].astype(np.float32) / 255.0).ravel())
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()

def main():
    common.reset_scene()
    os.makedirs(OUTP, exist_ok=True)
    H, L = build_meshes()
    unwrap(L)
    px = bake_maps(H, L)
    nrm8, id8, ids_top = finish_maps(px)
    save_png(nrm8, os.path.join(OUTP, f'{KID}_nrm_ao.png')); save_png(id8, os.path.join(OUTP, f'{KID}_id.png'))
    vis = np.zeros_like(id8)
    pal = np.array([common.hexc(B.PALETTE[s])[:3] for s in B.SLOT_NAMES]) * 255
    vis[..., :3] = pal[ids_top].astype(np.uint8); vis[..., 3] = 255
    save_png(vis, os.path.join(OUTP, f'{KID}_id_palette.png'))
    # game copies: PNG bytes under a non-image extension (Godot must not import / VRAM-compress them; loaded with
    # Image.load_png_from_buffer, so the id map stays exact)
    import shutil
    shutil.copy(os.path.join(OUTP, f'{KID}_nrm_ao.png'), os.path.join(common.VAT, f'{KID}_nrm.vtex'))
    shutil.copy(os.path.join(OUTP, f'{KID}_id.png'), os.path.join(common.VAT, f'{KID}_id.vtex'))
    old = os.path.join(common.VAT, f'{KID}_maps.vat')
    if os.path.exists(old): os.remove(old)
    face_slots(L, ids_top)
    # mid + far sets: decimated copies (weights / uv kept), small trinkets dropped first
    def lod_copy(target, drop_small, name):
        o = L.copy(); o.data = L.data.copy(); o.name = name; bpy.context.scene.collection.objects.link(o)
        if drop_small:
            bm = bmesh.new(); bm.from_mesh(o.data)
            import collections
            seen = set(); kill = []
            for f in bm.faces:
                if f.index in seen: continue
                st = [f]; comp = []; seen.add(f.index)
                while st:
                    g = st.pop(); comp.append(g)
                    for e in g.edges:
                        for h in e.link_faces:
                            if h.index not in seen: seen.add(h.index); st.append(h)
                area = sum(x.calc_area() for x in comp)
                if area < drop_small: kill += comp
            bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(o.data); bm.free()
        decimate(o, target, sym=True)
        o.data.validate()
        face_slots(o, ids_top)
        return o
    mid = lod_copy(MID_TRIS, 0.0025, 'mid')
    far = lod_copy(FAR_TRIS, 0.006, 'far')
    tn, tm, tf = C.tris(L), C.tris(mid), C.tris(far)
    log('tris near', tn, 'mid', tm, 'far', tf)
    full = concat([L, mid, far], KID + '_lod0')
    farx = concat([far], KID + '_lod1')
    nv, mv = len(L.data.vertices), len(L.data.vertices) + len(mid.data.vertices)
    for o in (full, farx): game_layers(o)
    rig = build_rig(KID)
    maps = {'nrm': f'{KID}_nrm.vtex', 'id': f'{KID}_id.vtex', 'size': TEX, 'format': 'PNG RGBA8',
            'layout': 'nrm: xyz tangent-space normal (Blender / OpenGL convention), a = AO; id: r = slot*8, g = material*16, '
                      'b = team mask; both sampled with UV3 (Godot CUSTOM0, the atlas layer)'}
    extra0 = {'tris': tn, 'near_verts': nv, 'mid_verts': mv, 'tris_mid': tm, 'tris_far': tf, 'tris_stored': tn + tm + tf, 'maps': maps,
              'split': 'verts [0,near_verts) = LOD0 set, [near_verts,mid_verts) = mid set, [mid_verts,vertices) = far set'}
    m0 = bake_vat(full, rig, 0, extra0)
    m1 = bake_vat(farx, rig, 1, {'tris': tf, 'maps': maps})
    # keep a rigged blend for Rob (rest pose, all sets skinned to the same bones)
    for o in (H,):
        bpy.data.objects.remove(o)
    for o in (L, mid, far):
        CB.bind(o, rig)
    os.makedirs(common.BLEND, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, f'soldier_{KID}.blend'))
    json.dump({'near': tn, 'mid': tm, 'far': tf, 'near_verts': nv, 'mid_verts': mv - nv, 'far_verts': len(far.data.vertices)},
              open(os.path.join(OUTP, 'tris.json'), 'w'), indent=1)
    log('done')

if __name__ == '__main__':
    main()
