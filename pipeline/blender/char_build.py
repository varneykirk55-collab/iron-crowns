"""Character refinement driver (headless):  blender -b --python pipeline/blender/char_build.py -- <cmd> [ids]
cmds: preview (rest-pose turntable stills), bake (VAT pos+normal, glb, blend), poses (clip contact sheet)."""
import sys, os, math, json, struct
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import common
import char_rig as R
import char_body as B

OUT = os.environ.get('CHAR_OUT', '/workspace/iron-crowns-visual/out/char')
PXM = int(os.environ.get('CHAR_PXM', '120'))

def hex2lin(h):
    c = common.hexc(h)
    return tuple(((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c[:3])

def build_rig(name):
    arm = bpy.data.armatures.new(name + '_rig')
    obj = bpy.data.objects.new(name + '_rig', arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for bn, h, t, p in R.BONES:
        b = arm.edit_bones.new(bn)
        b.head = Vector(h); b.tail = Vector(t); b.roll = 0.0
        b.use_connect = False
        if p:
            b.parent = eb[p]
        eb[bn] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    R.set_rest_from_blender(obj)
    return obj

def to_object(cm, preview=True):
    me = bpy.data.meshes.new(cm.name)
    me.from_pydata([tuple(c) for c in cm.co], [], [f[0] for f in cm.faces])
    me.update()
    obj = bpy.data.objects.new(cm.name, me)
    bpy.context.scene.collection.objects.link(obj)
    # consistent outward normals per island
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for poly in me.polygons:
        poly.use_smooth = cm.faces[poly.index][4]
    names = [b[0] for b in R.BONES]
    for n in names:
        obj.vertex_groups.new(name=n)
    for i, w in enumerate(cm.w):
        for b, x in w.items():
            obj.vertex_groups[b].add((i,), x, 'REPLACE')
    me.uv_layers.new(name='UVMap'); me.uv_layers.new(name='VID')
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    if preview:
        me.color_attributes.new('PCol', 'BYTE_COLOR', 'CORNER')
    n = len(me.vertices)
    nl = len(me.loops)
    lvi = [0] * nl; me.loops.foreach_get('vertex_index', lvi)
    pal = [common.hexc(B.PALETTE[s]) for s in B.SLOT_NAMES]
    u0 = [0.0] * (2 * nl); u1 = [0.0] * (2 * nl); c0 = [1.0] * (4 * nl); c1 = [1.0] * (4 * nl)
    for poly in me.polygons:
        _, slot, mat, team, smooth = cm.faces[poly.index]
        team = 1.0 if slot == B.S['coat'] else 0.0
        c = pal[slot]
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            u0[2 * li] = (slot + 0.5) / 32.0; u0[2 * li + 1] = mat / 16.0
            u1[2 * li] = (lvi[li] + 0.5) / n; u1[2 * li + 1] = team
            c1[4 * li:4 * li + 3] = c[:3]
    me.uv_layers['UVMap'].data.foreach_set('uv', u0)
    me.uv_layers['VID'].data.foreach_set('uv', u1)
    me.color_attributes['Col'].data.foreach_set('color', c0)
    if preview:
        me.color_attributes['PCol'].data.foreach_set('color', c1)
    me.color_attributes.active_color_index = 0
    mat = bpy.data.materials.new(cm.name + '_m')
    mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes.get('Principled BSDF')
    at = nt.nodes.new('ShaderNodeVertexColor'); at.layer_name = 'PCol'
    nt.links.new(at.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.8
    me.materials.append(mat)
    return obj

def bind(obj, rig):
    obj.parent = rig
    mod = obj.modifiers.new('Armature', 'ARMATURE'); mod.object = rig

def apply(rig, pose):
    for pb in rig.pose.bones:
        if pb.name in pose.P:
            Bm = pose.basis(pb.name)
            loc, rot, _ = Bm.decompose()
            pb.rotation_quaternion = rot; pb.location = loc
        else:
            pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)

def setup_cam(path, res, ortho=None):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.color_type = 'VERTEX'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.show_cavity = True
    sc.display.shading.cavity_type = 'WORLD'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    sc.render.film_transparent = False
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    return cam

def look_at(cam, pos, target):
    cam.location = Vector(pos)
    d = Vector(target) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def set_preview_color(obj):
    # Workbench VERTEX colour uses the active colour attribute
    me = obj.data
    me.color_attributes.active_color = me.color_attributes['PCol']

def preview(ids, lod=0, posefn=None, tag='rest'):
    common.reset_scene()
    k = 0
    for kid in ids:
        for ang in (0, 35, 90, 180):
            rig = build_rig(f'{kid}_{ang}')
            cm = B.build(kid, lod)
            o = to_object(cm); bind(o, rig); set_preview_color(o)
            if posefn:
                apply(rig, posefn())
            rig.location = (k * 0.85, 0, 0)
            rig.rotation_euler = (0, 0, math.radians(180 + ang))  # face the camera (camera looks along +Y)
            k += 1
        print(kid, 'lod', lod, 'tris', cm.tris(), 'verts', len(cm.co))
    cam = setup_cam(f'{OUT}/turn/{tag}_lod{lod}.png', (360 * k, 820), ortho=None)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.85 * k
    look_at(cam, ((k - 1) * 0.85 / 2, -8, 1.0), ((k - 1) * 0.85 / 2, 0, 0.95))
    bpy.ops.render.render(write_still=True)

def poses(kid, clips=None, ncol=8, angs=(90, 30), tag=None, lod=0):
    import char_anim as A
    common.reset_scene()
    style = 'rammer' if 'artillery' in kid else 'musket'
    sel = [c for c in A.CLIPS if not clips or c[0] in clips]
    cm = B.build(kid, lod)
    rows = 0
    worst = 1.0
    for ri, (cn, nf, loop, fn) in enumerate(sel):
        for vi, ang in enumerate(angs):
            for ci in range(ncol):
                t = ci / ncol if loop else ci / (ncol - 1) * 0.999
                p = A.solve(fn(t, style))
                if p.reach > 1.01 and vi == 0:
                    print(f'  reach {cn} t={t:.2f} {p.reach:.3f}')
                worst = max(worst, p.reach)
                rig = build_rig(f'{cn}_{vi}_{ci}')
                o = to_object(cm); bind(o, rig); set_preview_color(o)
                apply(rig, p)
                rig.location = ((ci + vi * (ncol + 0.5)) * 1.0, 0, -rows * 2.05)
                rig.rotation_euler = (0, 0, math.radians(180 + ang))
        rows += 1
        print('clip', cn, 'ok')
    W = (ncol * 2 + 0.5) * 1.0
    cam = setup_cam(f'{OUT}/turn/poses_{tag or kid}.png', (int(W * PXM), int(rows * 2.05 * PXM)))
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = W
    cx = (W - 1.0) / 2; cz = 1.0 - (rows - 1) * 2.05 / 2
    look_at(cam, (cx, -20, cz), (cx, 0, cz))
    bpy.ops.render.render(write_still=True)
    print('max reach ratio', worst)

def _append_sets(cm, kid):
    """stage 9: append the mid set (char_body LODS[2]) and then the LOD1 set to a LOD0 CharMesh.
    Returns (mid_verts = end of the mid set, mid tris)."""
    mid_tris = 0
    for lod in (2, 1):
        o = B.build(kid, lod)
        off = len(cm.co)
        cm.co += o.co; cm.w += o.w
        cm.faces += [(tuple(i + off for i in f[0]),) + tuple(f[1:]) for f in o.faces]
        if lod == 2:
            mid_tris = o.tris(); mid_end = len(cm.co)
    return mid_end, mid_tris

def _single(kid, pose, ang, path, res, lod=0, focus=(0.0, 0.95), height=2.0, dist=9.0):
    """one perspective still: rig rotated by ang (0 = facing camera), camera framing `height` m (vertical) around focus z"""
    common.reset_scene()
    cm = B.build(kid, lod)
    # preview renders only the requested set (lod 0 / 2 = mid / 1); the bake stores all three in the LOD0 asset
    rig = build_rig(kid)
    o = to_object(cm); bind(o, rig); set_preview_color(o)
    if pose is not None:
        apply(rig, pose)
    rig.rotation_euler = (0, 0, math.radians(180 + ang))
    sc = bpy.context.scene
    cam = setup_cam(path, res)
    sc.display.shading.show_shadows = True
    sc.display.shading.shadow_intensity = 0.35
    sc.display.render_aa = '16'
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.sensor_height = 24.0
    cam.data.lens = 24.0 * dist / height
    look_at(cam, (focus[0], -dist, focus[1] + 0.05), (focus[0], 0, focus[1]))
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))   # ground for the contact shadow
    gm = bpy.context.active_object.data
    gm.color_attributes.new('PCol', 'FLOAT_COLOR', 'CORNER')
    gm.color_attributes['PCol'].data.foreach_set('color', [0.42, 0.45, 0.36, 1.0] * len(gm.loops))
    gm.color_attributes.active_color = gm.color_attributes['PCol']
    bpy.ops.render.render(write_still=True)
    print('wrote', path, 'tris', cm.tris())

def turn(kid='c19sr_line'):
    """close-up turntable (front / 3-4 / side / back, idle stance) + busts + idle/fire/reload pose stills"""
    import char_anim as A
    clips = {c[0]: c for c in A.CLIPS}
    style = 'rammer' if 'artillery' in kid else 'musket'
    idle = A.solve(clips['idle'][3](0.0, style))
    d = f'{OUT}/turn'
    short = kid.replace('c19sr_', '')
    for name, ang in (('front', 0), ('34', 35), ('side', 90), ('back', 180)):
        _single(kid, idle, ang, f'{d}/{short}_turn_{name}.png', (900, 1500), focus=(0.0, 1.0), height=2.15)
    _single(kid, idle, 25, f'{d}/{short}_bust_34.png', (1200, 1200), focus=(0.0, 1.52), height=1.0)
    _single(kid, idle, 0, f'{d}/{short}_bust_front.png', (1200, 1200), focus=(0.0, 1.52), height=1.0)
    f = clips['fire'][3]
    sheet = [('idle', clips['idle'][3](0.0, style)), ('aim', f(0.14, style)), ('fire_recoil', f(0.152, style)),
             ('prime', f(0.42, style)), ('reload_ram', f(0.64, style)), ('reload_return', f(0.88, style))]
    for name, spec in sheet:
        p = A.solve(spec)
        _single(kid, p, 35, f'{d}/{short}_pose_{name}.png', (800, 1240), focus=(0.0, 1.05), height=2.4)
        print('pose', name, 'reach', round(p.reach, 3))

def key_pose(rig, pose, frame):
    apply(rig, pose)
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        pb.keyframe_insert('location', frame=frame)

def bake(kid, lod, keep_blend=False):
    """VAT positions (float32 RGB, Godot coords) + VAT normals (RGBA8 .vatn), static glb (rest pose, VID uv2),
    optional rigged glb + .blend with one keyed action per clip."""
    import numpy as np
    import char_anim as A
    common.reset_scene()
    style = 'rammer' if 'artillery' in kid else 'musket'
    cm = B.build(kid, lod)
    near_verts = None
    if lod == 0:
        # stage 7/9: the LOD0 asset carries [LOD0 | mid | LOD1] vertex sets (see _append_sets); char_vat.gdshader
        # draws one set per instance by camera distance (battle_visuals char_lod / char_mid), the others collapse to a point.
        near_tris = cm.tris(); near_verts = len(cm.co)
        mid_verts, mid_tris = _append_sets(cm, kid)
    rig = build_rig(kid)
    o = to_object(cm, preview=keep_blend); bind(o, rig)
    if keep_blend:
        set_preview_color(o)
        o.data.color_attributes.active_color = o.data.color_attributes['Col']
    n = len(o.data.vertices)
    pos, nrm = [], []
    meta = {'vertices': n, 'fps': 24, 'clips': {}, 'frames': 0, 'tris': cm.tris(), 'kit': kid, 'lod': lod,
            'normals': 'vatn rgba8 (n*0.5+0.5), same rows/cols as .vat'}
    if near_verts is not None:
        meta.update({'tris': near_tris, 'near_verts': near_verts, 'mid_verts': mid_verts, 'tris_mid': mid_tris,
                     'tris_far': cm.tris() - near_tris - mid_tris, 'tris_stored': cm.tris(),
                     'split': 'verts [0,near_verts) = LOD0 set (drawn to char_lod), [near_verts,mid_verts) = mid set '
                              '(drawn char_lod..char_mid), [mid_verts,vertices) = LOD1 set (drawn past char_mid)'})
    row = 0
    worst = 1.0
    for cn, nf, loop, fn in A.CLIPS:
        if keep_blend:
            rig.animation_data_create()
            act = bpy.data.actions.new(f'{kid}_{cn}'); act.use_fake_user = True
            rig.animation_data.action = act
        for f in range(nf):
            t = f / nf if loop else f / max(1, nf - 1)
            p = A.solve(fn(t, style))
            worst = max(worst, p.reach)
            if keep_blend:
                key_pose(rig, p, f + 1)
            else:
                apply(rig, p)
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            ev = o.evaluated_get(deps)
            me = ev.to_mesh()
            co = np.empty(n * 3, np.float32); me.vertices.foreach_get('co', co)
            nn = np.empty(n * 3, np.float32); me.vertices.foreach_get('normal', nn)
            ev.to_mesh_clear()
            co = co.reshape(n, 3); nn = nn.reshape(n, 3)
            pos.append(np.stack([co[:, 0], co[:, 2], -co[:, 1]], 1))
            g = np.stack([nn[:, 0], nn[:, 2], -nn[:, 1]], 1)
            g = np.clip(np.round((g * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
            nrm.append(np.concatenate([g, np.full((n, 1), 255, np.uint8)], 1))
        meta['clips'][cn] = {'start': row, 'count': nf, 'loop': loop}
        row += nf
    meta['frames'] = row
    P = np.stack(pos).astype(np.float32)
    meta['aabb'] = [P.reshape(-1, 3).min(0).tolist(), P.reshape(-1, 3).max(0).tolist()]
    meta['max_reach'] = round(worst, 3)
    vdir = common.VAT; mdir = common.MODELS
    base = os.path.join(vdir, f'{kid}_lod{lod}')
    open(base + '.vat', 'wb').write(P.tobytes())
    open(base + '.vatn', 'wb').write(np.stack(nrm).tobytes())
    json.dump(meta, open(base + '.json', 'w'), indent=1)
    # static rest-pose copy (no armature, no preview colour)
    me2 = o.data.copy()
    if 'PCol' in me2.color_attributes:
        me2.color_attributes.remove(me2.color_attributes['PCol'])
    me2.color_attributes.active_color = me2.color_attributes['Col']
    st = bpy.data.objects.new(f'{kid}_lod{lod}', me2)
    bpy.context.scene.collection.objects.link(st)
    common.export_glb([st], os.path.join(mdir, f'soldier_{kid}_lod{lod}.glb'))
    bpy.data.objects.remove(st)
    if keep_blend:
        rig.animation_data.action = None
        for pb in rig.pose.bones:
            pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        os.makedirs(common.BLEND, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, f'soldier_{kid}.blend'))
    print('baked', kid, 'lod', lod, 'verts', n, 'near_verts', near_verts, 'mid', meta.get('mid_verts'), meta.get('tris_mid'), 'tris', meta['tris'], 'stored', cm.tris(), 'frames', row, 'max reach', round(worst, 3))

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['preview']
    cmd = argv[0]
    os.makedirs(OUT + '/turn', exist_ok=True)
    if cmd == 'preview':
        ids = argv[1:] or ['c19sr_line']
        for lod in (0, 1):
            preview(ids, lod, tag='_'.join(i.replace('c19sr_', '') for i in ids))
    elif cmd == 'poses':
        kid = argv[1] if len(argv) > 1 else 'c19sr_line'
        clips = argv[2].split(',') if len(argv) > 2 else None
        poses(kid, clips, tag=(argv[3] if len(argv) > 3 else None))
    elif cmd == 'turn':
        turn(argv[1] if len(argv) > 1 else 'c19sr_line')
    elif cmd == 'bake':
        ids = argv[1:] or ['c19sr_line', 'c19sr_grenadier', 'c19sr_artillery', 'c19sr_officer']
        for kid in ids:
            for lod in (0, 1):
                bake(kid, lod, keep_blend=(lod == 0))
