"""Visual pass: overworld army markers (map_marker_<era>.glb), one per era, built from the era's battle-kit soldiers
(lod1 detail) so the campaign map shows recognisable troops instead of the generic army_standard figure.
Static props: team mask in UV2.y, material class in UVMap.v (same contract as props.py). Same pivot / footprint as
army_standard (pedestal r~0.6 at the origin, ~2.8 tall) so world_map.gd selection (top = 1.6 * scale) is unchanged.
Soldiers face Blender -Y (= Godot +Z, towards the default map camera); the flag spans X-Z so it reads at yaw 0.
Run: blender -b --python pipeline/blender/markers.py [-- medieval c20 ...]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix
import common, med_kit, em_kit, c19_kit, c20_kit, mod_kit
from common import hexc, MeshBuilder, MAT_WOOD, MAT_WOOL, MAT_BRASS, MAT_PIPECLAY, MAT_STEEL
from soldiers import GROUPS

TEAM = (1, 1, 1, 1.0)
ERAS = {  # era id -> (front soldier, second soldier)
    'medieval': (med_kit.spearman, med_kit.archer),
    'early_modern': (em_kit.pikeman, em_kit.musketeer),
    'c19': (c19_kit.line_infantry, c19_kit.line_infantry),
    'c20': (c20_kit.rifleman, c20_kit.rifleman),
    'modern': (mod_kit.rifleman, mod_kit.rifleman),
}
K = 0.82  # soldier scale on the marker (battle soldiers are ~1.8 tall)

def base_and_flag(era):
    b = MeshBuilder('marker_base_' + era, ['body', 'recoil'])
    b.cyl(0.6, 0.68, 0.16, (0, 0, 0.08), hexc('6d675e'), 'body', segs=12, mat=MAT_STEEL)
    b.cyl(0.6, 0.6, 0.05, (0, 0, 0.175), TEAM, 'body', segs=12, mat=MAT_WOOL)       # team top disc: reads top-down
    b.cyl(0.035, 0.035, 2.6, (0.05, 0.28, 1.4), hexc('4a3220'), 'body', segs=6, mat=MAT_WOOD)
    b.box((0.95, 0.04, 0.64), (0.53, 0.28, 2.33), TEAM, 'body', mat=MAT_WOOL)       # flag (faces the camera)
    b.box((0.95, 0.045, 0.09), (0.53, 0.28, 1.97), hexc('ece2c0'), 'body', mat=MAT_PIPECLAY)  # light hem
    b.sphere(0.08, (0.05, 0.28, 2.75), hexc('c8a24a'), 'body', segs=6, rings=4, mat=MAT_BRASS)
    return b.to_object(with_vid=False)

def soldier(fn, name, x, y, yaw):
    o = fn(name, GROUPS, False)
    o.data.transform(Matrix.Translation((x, y, 0.2)) @ Matrix.Rotation(math.radians(180 + yaw), 4, 'Z') @ Matrix.Scale(K, 4))
    return o

def build(era):
    a, b2 = ERAS[era]
    objs = [base_and_flag(era), soldier(a, 'm_a', -0.24, -0.08, 8), soldier(b2, 'm_b', 0.27, 0.06, -12)]
    for o in objs:
        o.vertex_groups.clear()
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = 'map_marker_' + era
    print('marker', era, len(o.data.vertices), 'verts')
    common.export_glb([o], os.path.join(common.MODELS, f'map_marker_{era}.glb'))
    return o

if __name__ == '__main__':
    only = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else list(ERAS)
    common.reset_scene()
    for e in only:
        build(e)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, 'map_markers.blend'))
