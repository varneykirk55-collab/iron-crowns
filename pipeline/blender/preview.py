"""Render pose previews (workbench, vertex colours) for visual QA of generated assets."""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
import common, rigkit, soldiers, cavalry, importlib

def setup_render(path, res=(900, 300)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.color_type = 'VERTEX'
    sc.display.shading.light = 'STUDIO'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    return cam

vid = sys.argv[sys.argv.index('--') + 1]
common.reset_scene()
mod = cavalry if vid in cavalry.VARIANTS else soldiers
kit = mod.VARIANTS[vid]
CL = [(n, nf, l, (lambda fn: (lambda style: fn))(fn)) for n, nf, l, fn in cavalry.clips(kit)] if mod is cavalry else soldiers.CLIPS
objs = []
for i, (n, nf, loop, fn) in enumerate(CL):
    for j, t in enumerate((0.0, 0.3, 0.6)):
        rig = rigkit.build_armature(f's{i}{j}', mod.BONES)
        body = (mod.build_body if mod is soldiers else mod.build)(f'b{i}{j}', kit, True)
        rigkit.bind(body, rig)
        rig.location = (i * 1.6 , j * 0.0 + 0, 0)
        rig.location.x = (i * 3 + j) * 1.0
        rigkit.apply_pose(rig, fn(kit.get('style'))(t))

for o in bpy.data.objects:
    if o.type=='ARMATURE':
        x=o.location.x; o.location=(0, -x*(1.5 if mod is soldiers else 2.6), 0)
cam = setup_render('/tmp/preview_' + vid + '.png', (1800, 300) if mod is soldiers else (3600, 600))
cam.data.type='ORTHO'; cam.data.ortho_scale=28 if mod is soldiers else 48
cam.location=(20,-12.5 if mod is soldiers else -22,1.2); cam.rotation_euler=(math.radians(90),0,math.radians(90))
bpy.ops.render.render(write_still=True)
