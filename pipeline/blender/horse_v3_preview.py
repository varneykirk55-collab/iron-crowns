"""Cycles previews of horse_v3.blend (LOD0).  blender -b --python pipeline/blender/horse_v3_preview.py -- [outdir] [views]
views: side front34 rear34 head medieval napoleonic"""
import bpy, math, os, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUTDIR = argv[0] if argv else '/workspace/horse_previews'
VIEWS = argv[1].split(',') if len(argv) > 1 else ['side', 'front34', 'rear34', 'head', 'medieval', 'napoleonic']
SAMPLES = int(os.environ.get('HV3_SAMPLES', '96'))
RES = int(os.environ.get('HV3_RES', '1400'))
os.makedirs(OUTDIR, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'game', 'assets', 'models', 'horse_v3', 'horse_v3.blend'))
sc = bpy.context.scene

# (view, coat, layers, camera loc, target, lens)
CFG = {
    'side':       ('bay',      ['horse_body', 'horse_hair', 'horse_eyes'], (4.6, 0.20, 1.05), (0, 0.18, 1.0), 50),
    'front34':    ('chestnut', ['horse_body', 'horse_hair', 'horse_eyes'], (2.7, 3.6, 1.55), (0, 0.15, 1.0), 50),
    'rear34':     ('grey',     ['horse_body', 'horse_hair', 'horse_eyes'], (2.6, -3.6, 1.65), (0, -0.15, 0.95), 50),
    'head':       ('dark_bay', ['horse_body', 'horse_hair', 'horse_eyes'], (1.10, 2.15, 1.95), (0, 1.20, 1.66), 70),
    'medieval':   ('grey',     ['horse_body', 'horse_eyes', 'tack_1300', 'barding_1300'], (3.6, 2.9, 1.65), (0, 0.10, 1.0), 50),
    'napoleonic': ('bay',      ['horse_body', 'horse_hair', 'horse_eyes', 'tack_1800'], (3.7, 2.6, 1.6), (0, 0.10, 1.0), 50),
}

def mk_mat(name, col_attr, coat=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; Lk = nt.links
    bsdf = N.get('Principled BSDF')
    col = N.new('ShaderNodeAttribute'); col.attribute_name = col_attr
    mid = N.new('ShaderNodeAttribute'); mid.attribute_name = 'mat_id'
    base = col.outputs['Color']
    if coat == 'grey':   # dapples: voronoi-ish lightening on the barrel / quarters
        tc = N.new('ShaderNodeTexCoord')
        vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 14
        Lk.new(tc.outputs['Object'], vor.inputs['Vector'])
        ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[1].position = 0.12
        Lk.new(vor.outputs['Distance'], ramp.inputs['Fac'])
        mix = N.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs['Fac'].default_value = 0.35
        Lk.new(base, mix.inputs[1])
        inv = N.new('ShaderNodeInvert'); Lk.new(ramp.outputs['Color'], inv.inputs['Color'])
        g = N.new('ShaderNodeMixRGB'); g.inputs['Fac'].default_value = 1.0; g.blend_type = 'MIX'
        g.inputs[1].default_value = (1, 1, 1, 1); g.inputs[2].default_value = (0.72, 0.72, 0.72, 1)
        Lk.new(inv.outputs['Color'], g.inputs['Fac'])
        Lk.new(g.outputs['Color'], mix.inputs[2])
        base = mix.outputs['Color']
    Lk.new(base, bsdf.inputs['Base Color'])
    # per class roughness / metal: 3 steel, 4 brass -> metallic; 8 coat satin; 11 hair; 2 leather/hoof
    def eq(v):
        a = N.new('ShaderNodeMath'); a.operation = 'COMPARE'; a.inputs[1].default_value = v; a.inputs[2].default_value = 0.5
        Lk.new(mid.outputs['Fac'], a.inputs[0]); return a.outputs[0]
    met = N.new('ShaderNodeMath'); met.operation = 'ADD'
    Lk.new(eq(3), met.inputs[0]); Lk.new(eq(4), met.inputs[1])
    Lk.new(met.outputs[0], bsdf.inputs['Metallic'])
    r = N.new('ShaderNodeMapRange'); r.inputs['To Min'].default_value = 0.78; r.inputs['To Max'].default_value = 0.32
    Lk.new(met.outputs[0], r.inputs['Value'])
    rr = N.new('ShaderNodeMath'); rr.operation = 'SUBTRACT'; Lk.new(r.outputs['Result'], rr.inputs[0])
    sat = N.new('ShaderNodeMath'); sat.operation = 'MULTIPLY'; sat.inputs[1].default_value = 0.30
    c8 = eq(8); Lk.new(c8, sat.inputs[0]); Lk.new(sat.outputs[0], rr.inputs[1])
    Lk.new(rr.outputs[0], bsdf.inputs['Roughness'])
    if 'Sheen Weight' in bsdf.inputs:
        Lk.new(c8, bsdf.inputs['Sheen Weight'])
        bsdf.inputs['Sheen Roughness'].default_value = 0.4
    return m

def setup_world():
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    sky = w.node_tree.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'HOSEK_WILKIE'
    sky.sun_direction = Vector((0.5, 0.6, 0.6)).normalized(); sky.turbidity = 3
    w.node_tree.links.new(sky.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.35
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.6; sun.data.angle = math.radians(3)
    sun.rotation_euler = (math.radians(50), 0, math.radians(135)); sc.collection.objects.link(sun)
    fill = bpy.data.objects.new('fill', bpy.data.lights.new('fill', 'AREA'))
    fill.data.energy = 900; fill.data.size = 4; fill.location = (-4, 3, 3)
    fill.rotation_euler = Vector((4, -3, -2.2)).to_track_quat('Z', 'Y').to_euler(); sc.collection.objects.link(fill)
    rim = bpy.data.objects.new('rim', bpy.data.lights.new('rim', 'AREA'))
    rim.data.energy = 600; rim.data.size = 3; rim.location = (-1, -4.5, 3.2)
    rim.rotation_euler = Vector((1, 4.5, -2.2)).to_track_quat('Z', 'Y').to_euler(); sc.collection.objects.link(rim)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    g = bpy.context.active_object
    gm = bpy.data.materials.new('ground'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.32, 0.30, 0.27, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
    g.data.materials.append(gm)

setup_world()
sc.render.engine = 'CYCLES'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
try:
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
except Exception:
    pass
sc.render.resolution_x = RES; sc.render.resolution_y = int(RES * 0.75)
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam

LOD = int(os.environ.get('HV3_LOD', '0'))   # 1 / 2: quick looks at the lower LODs (file names get _lodN)
for i in (0, 1, 2):
    bpy.data.collections['LOD%d' % i].hide_render = (i != LOD)
lod0 = {o.name.rsplit('_lod', 1)[0]: o for o in bpy.data.collections['LOD%d' % LOD].objects}
tackmat = mk_mat('prev_tack', 'Col')
for v in VIEWS:
    coat, layers, loc, tgt, lens = CFG[v]
    bodymat = mk_mat('prev_body_' + v, 'coat_' + coat, coat)
    for name, o in lod0.items():
        on = name in layers
        o.hide_render = not on
        o.data.materials.clear()
        o.data.materials.append(bodymat if name in ('horse_body', 'horse_hair', 'horse_eyes') else tackmat)
    cam.location = Vector(loc); cam.data.lens = lens
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUTDIR, 'horse_v3_%s%s.png' % (v, '_lod%d' % LOD if LOD else ''))
    bpy.ops.render.render(write_still=True)
    print('rendered', sc.render.filepath, flush=True)
