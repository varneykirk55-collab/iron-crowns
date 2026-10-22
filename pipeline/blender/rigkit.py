"""Procedural rig + clip baking: builds armatures, keys procedural poses per frame, bakes Vertex Animation
Textures (VAT, float32 positions per vertex per frame, Godot Y-up coords) and exports rigged/animated GLB."""
import bpy, math, json, struct, os
from mathutils import Matrix, Vector, Euler, Quaternion
import common

def build_armature(name, bones):
    """bones: list of (name, head, tail, parent)"""
    arm = bpy.data.armatures.new(name + '_rig')
    obj = bpy.data.objects.new(name + '_rig', arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for bn, h, t, p in bones:
        b = arm.edit_bones.new(bn)
        b.head = Vector(h); b.tail = Vector(t); b.roll = 0.0
        if p:
            b.parent = eb[p]
        eb[bn] = b
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return obj

def bind(mesh_obj, rig):
    mesh_obj.parent = rig
    mod = mesh_obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig

def apply_pose(rig, pose, frame=None):
    """pose: {bone: (rx, ry, rz) degrees in armature axes, '_loc': (x,y,z) root offset}"""
    for pb in rig.pose.bones:
        B = pb.bone.matrix_local.to_3x3()
        rot = pose.get(pb.name, (0, 0, 0))
        R = Euler([math.radians(a) for a in rot], 'XYZ').to_matrix()
        local = (B.inverted() @ R @ B).to_quaternion()
        pb.rotation_quaternion = local
        if pb.parent is None:
            pb.location = Vector(pose.get('_loc', (0, 0, 0)))
        else:
            pb.location = Vector((0, 0, 0))
        if frame is not None:
            pb.keyframe_insert('rotation_quaternion', frame=frame)
            pb.keyframe_insert('location', frame=frame)

def bake(mesh_obj, rig, clips, out_base, fps=24):
    """clips: list of (name, nframes, loop, posefn(t in [0,1)))"""
    deps = bpy.context.evaluated_depsgraph_get()
    V = len(mesh_obj.data.vertices)
    data = bytearray()
    meta = {'vertices': V, 'fps': fps, 'clips': {}, 'frames': 0}
    row = 0
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    actions = []
    for name, nf, loop, fn in clips:
        rig.animation_data_create()
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        rig.animation_data.action = act
        frames = nf
        for f in range(frames):
            t = f / nf if loop else f / max(1, nf - 1)
            apply_pose(rig, fn(t), frame=f + 1)
        for f in range(frames):
            bpy.context.scene.frame_set(f + 1)
            deps = bpy.context.evaluated_depsgraph_get()
            ev = mesh_obj.evaluated_get(deps)
            me = ev.to_mesh()
            for v in me.vertices:
                x, y, z = v.co
                data += struct.pack('<3f', x, z, -y)
                lo.x = min(lo.x, x); lo.y = min(lo.y, z); lo.z = min(lo.z, -y)
                hi.x = max(hi.x, x); hi.y = max(hi.y, z); hi.z = max(hi.z, -y)
            ev.to_mesh_clear()
        meta['clips'][name] = {'start': row, 'count': frames, 'loop': loop}
        row += frames
        actions.append(act)
    meta['frames'] = row
    meta['aabb'] = [list(lo), list(hi)]
    open(out_base + '.vat', 'wb').write(bytes(data))
    json.dump(meta, open(out_base + '.json', 'w'), indent=1)
    print('baked', out_base, V, 'verts', row, 'frames')
    return actions

def export_static_copy(mesh_obj, path):
    """Export the rest-pose mesh (no skin) with vertex colours + VID uv for VAT playback."""
    me = mesh_obj.data.copy()
    o = bpy.data.objects.new(mesh_obj.name + '_static', me)
    bpy.context.scene.collection.objects.link(o)
    common.export_glb([o], path)
    bpy.data.objects.remove(o)

def export_rigged(mesh_obj, rig, path):
    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True); rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_skins=True,
                              export_animations=True, export_animation_mode='ACTIONS', export_vertex_color='ACTIVE',
                              export_all_vertex_colors=True)
    print('exported rigged', path)
