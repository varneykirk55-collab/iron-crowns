"""Shared helpers for the Blender asset pipeline (run headless: blender -b --python <script>).
All geometry is built procedurally from primitives -> original low-poly stylised assets.
Vertex colour RGBA: rgb = base colour, alpha = team-colour blend amount (tinted in Godot shader)."""
import bpy, bmesh, math, os, json, struct
from mathutils import Matrix, Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'game', 'assets'))
MODELS = os.path.join(ROOT, 'models')
VAT = os.path.join(ROOT, 'vat')
BLEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'blend'))
os.makedirs(MODELS, exist_ok=True); os.makedirs(VAT, exist_ok=True); os.makedirs(BLEND, exist_ok=True)

def hexc(h, a=0.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

class MeshBuilder:
    """Accumulates primitive parts into one bmesh with per-part colour and bone weight."""
    def __init__(self, name, groups=()):
        self.name = name
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col')
        self.deform = self.bm.verts.layers.deform.verify()
        self.groups = list(groups)

    def _finish(self, verts, color, bone):
        faces = set()
        for v in verts:
            for f in v.link_faces:
                faces.add(f)
        for f in faces:
            for l in f.loops:
                l[self.col] = color
        if bone is not None:
            gi = self.groups.index(bone)
            for v in verts:
                v[self.deform][gi] = 1.0
        return verts

    def box(self, size, loc, color, bone=None, rot=(0, 0, 0), taper=1.0):
        m = Matrix.Translation(Vector(loc)) @ Euler([math.radians(r) for r in rot]).to_matrix().to_4x4() @ Matrix.Diagonal((size[0], size[1], size[2], 1))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        verts = r['verts']
        if taper != 1.0:  # shrink top face (local +Z)
            c = Vector(loc)
            for v in verts:
                local = m.inverted() @ v.co
                if local.z > 0:
                    local.x *= taper; local.y *= taper
                    v.co = m @ local
        return self._finish(verts, color, bone)

    def cyl(self, r1, r2, depth, loc, color, bone=None, rot=(0, 0, 0), segs=8):
        m = Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot]).to_matrix().to_4x4()
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth, matrix=m)
        return self._finish(res['verts'], color, bone)

    def sphere(self, r, loc, color, bone=None, segs=8, rings=5, scale=(1, 1, 1)):
        m = Matrix.Translation(Vector(loc)) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=r, matrix=m)
        return self._finish(res['verts'], color, bone)

    def to_object(self, with_vid=True):
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        obj = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(obj)
        for g in self.groups:
            obj.vertex_groups.new(name=g)
        uv0 = me.uv_layers.new(name='UVMap')
        # second UV: x = vertex id for VAT lookup (0 for static props), y = team-colour amount
        # (glTF drops vertex-colour alpha, so the team mask travels in UV2.y)
        uv1 = me.uv_layers.new(name='VID')
        n = len(me.vertices)
        col = me.color_attributes['Col']
        for loop in me.loops:
            a = col.data[loop.index].color[3]
            uv1.data[loop.index].uv = (((loop.vertex_index + 0.5) / n) if with_vid else 0.0, a)
        for poly in me.polygons:
            poly.use_smooth = False
        me.color_attributes.active_color_index = 0
        mat = vcol_material()
        me.materials.append(mat)
        return obj

_mat = None
def vcol_material():
    global _mat
    if 'VertexColour' in bpy.data.materials:
        return bpy.data.materials['VertexColour']
    m = bpy.data.materials.new('VertexColour')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    attr = nt.nodes.new('ShaderNodeVertexColor')
    attr.layer_name = 'Col'
    nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    _mat = m
    return m

def export_glb(objs, path, skins=False, anims=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=not skins,
                              export_skins=skins, export_animations=anims, export_vertex_color='ACTIVE',
                              export_all_vertex_colors=True, export_texcoords=True, export_normals=True,
                              export_morph=False, export_animation_mode='ACTIONS')
    print('exported', path)
