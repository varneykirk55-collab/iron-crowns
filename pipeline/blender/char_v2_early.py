import bpy, sys, math
sys.path.insert(0,'/workspace/ic_proto/pipeline/blender')
import char_v2 as C
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
parts=C.build_body_parts(); near=C.nearest_part(parts)
hi=C.fuse(parts, 0.005); C.drop_small_islands(hi); C.slot_body(hi, near)
lo=hi.copy(); lo.data=hi.data.copy(); bpy.context.scene.collection.objects.link(lo)
m=lo.modifiers.new('d','DECIMATE'); m.ratio=3000/C.tris(lo); m.use_symmetry=True; m.symmetry_axis='X'; m.use_collapse_triangulate=True
C.apply_mods(lo); C.unspread(hi, near); C.unspread(lo, near)
for k,v in parts.items():
    for o in v: bpy.data.objects.remove(o)
tree=C.surface_tools([hi])
H=C.join([hi]+C.build_kit(True, tree),'HI'); L=C.join([lo]+C.build_kit(False, tree),'LO')
print('TRIS hi',C.tris(H),'lo',C.tris(L))
for o in (H,L): C.preview_mats(o)
sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'
sc.display.shading.show_cavity=True; sc.display.shading.show_shadows=False
sc.view_settings.view_transform='Standard'
cam=bpy.data.objects.new('c',bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera=cam
cam.data.lens=85
def shoot(path, ang, tgt=Vector((0,0,1.05)), dist=4.9, res=(900,1300)):
    sc.render.resolution_x, sc.render.resolution_y = res
    a=math.radians(ang); d=Vector((math.sin(a), math.cos(a), 0.08)).normalized()
    cam.location=tgt+d*dist; cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=path; bpy.ops.render.render(write_still=True)
for nm,o in (('hi',H),('lod0',L)):
    for other in (H,L): other.hide_render = other is not o
    for v,ang in (('front',0),('side',90),('back',180),('34',35)):
        shoot(f'/workspace/ic_proto/out/proto/early/{nm}_{v}.png', ang)
    shoot(f'/workspace/ic_proto/out/proto/early/{nm}_bust.png', 25, Vector((0,0,1.60)), 2.4, (900,900))
bpy.ops.wm.save_as_mainfile(filepath='/tmp/c19v2_line_early.blend')
