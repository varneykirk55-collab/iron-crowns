"""Rob / cavalry overhaul: the new horse armature (HX rig) + a pure-python pose solver.

Spec: HORSE_SKELETON_SPEC.md (v1.1).  Blender coords: +Y = horse forward, +Z up, +X = horse's right, metres.
Bones are (name, head, tail, parent).  Poses are armature-space matrices P[name]; the skinning delta of a bone is
P @ REST^-1 (same convention as char_rig, so the char_rig rider can be composed onto the rider_seat socket).
No Blender data is needed to pose; build_armature() makes a real armature for the rigged export."""
import math
from mathutils import Vector, Matrix, Euler

def V(*a):
    if len(a) == 1:
        return Vector(a[0])
    return Vector(a)

def _legs(s, sx):
    x = lambda v: v * sx
    return [
        ('scapula.' + s, (x(0.13), 0.44, 1.34), (x(0.17), 0.70, 1.06), 'chest'),
        ('humerus.' + s, (x(0.17), 0.70, 1.06), (x(0.16), 0.52, 0.84), 'scapula.' + s),
        ('radius.' + s, (x(0.16), 0.52, 0.84), (x(0.155), 0.54, 0.50), 'humerus.' + s),
        ('cannon_f.' + s, (x(0.155), 0.54, 0.50), (x(0.15), 0.54, 0.23), 'radius.' + s),
        ('fetlock_f.' + s, (x(0.15), 0.54, 0.23), (x(0.15), 0.60, 0.09), 'cannon_f.' + s),
        ('hoof_f.' + s, (x(0.15), 0.60, 0.09), (x(0.15), 0.68, 0.0), 'fetlock_f.' + s),
        ('femur.' + s, (x(0.17), -0.50, 1.18), (x(0.19), -0.30, 0.88), 'pelvis'),
        ('tibia.' + s, (x(0.19), -0.30, 0.88), (x(0.16), -0.64, 0.54), 'femur.' + s),
        ('cannon_h.' + s, (x(0.16), -0.64, 0.54), (x(0.15), -0.62, 0.23), 'tibia.' + s),
        ('fetlock_h.' + s, (x(0.15), -0.62, 0.23), (x(0.15), -0.57, 0.09), 'cannon_h.' + s),
        ('hoof_h.' + s, (x(0.15), -0.57, 0.09), (x(0.15), -0.49, 0.0), 'fetlock_h.' + s),
    ]

HX_BONES = [
    ('root', (0, 0, 0), (0, 0.25, 0), None),
    ('body', (0, 0, 1.22), (0, 0.30, 1.22), 'root'),
    ('pelvis', (0, -0.32, 1.34), (0, -0.80, 1.30), 'body'),
    ('spine_01', (0, -0.32, 1.34), (0, 0.02, 1.30), 'body'),
    ('spine_02', (0, 0.02, 1.30), (0, 0.36, 1.34), 'spine_01'),
    ('chest', (0, 0.36, 1.34), (0, 0.66, 1.28), 'spine_02'),
    ('neck_01', (0, 0.66, 1.28), (0, 0.84, 1.52), 'chest'),
    ('neck_02', (0, 0.84, 1.52), (0, 0.97, 1.72), 'neck_01'),
    ('neck_03', (0, 0.97, 1.72), (0, 1.05, 1.86), 'neck_02'),
    ('head', (0, 1.05, 1.86), (0, 1.40, 1.44), 'neck_03'),
    ('jaw', (0, 1.10, 1.72), (0, 1.36, 1.41), 'head'),
    ('ear.L', (-0.06, 1.04, 1.89), (-0.07, 1.02, 2.04), 'head'),
    ('ear.R', (0.06, 1.04, 1.89), (0.07, 1.02, 2.04), 'head'),
    ('tail_01', (0, -0.80, 1.30), (0, -0.89, 1.21), 'pelvis'),
    ('tail_02', (0, -0.89, 1.21), (0, -0.94, 1.08), 'tail_01'),
    ('tail_03', (0, -0.94, 1.08), (0, -0.97, 0.94), 'tail_02'),
    ('tail_04', (0, -0.97, 0.94), (0, -0.99, 0.80), 'tail_03'),
    ('tail_05', (0, -0.99, 0.80), (0, -1.00, 0.63), 'tail_04'),
] + _legs('R', 1) + _legs('L', -1) + [
    # sockets (deform only for tack)
    ('saddle', (0, 0.12, 1.42), (0, 0.32, 1.42), 'spine_02'),
    ('rider_seat', (0, 0.10, 1.488), (0, 0.10, 1.60), 'saddle'),
    ('stirrup.L', (-0.20, 0.16, 1.38), (-0.27, 0.16, 0.86), 'saddle'),
    ('stirrup.R', (0.20, 0.16, 1.38), (0.27, 0.16, 0.86), 'saddle'),
    ('rein_bit', (0, 1.30, 1.44), (0, 1.30, 1.52), 'head'),
    ('bridle', (0, 1.06, 1.82), (0, 1.12, 1.87), 'head'),
    ('rein_hand.L', (-0.09, 0.40, 1.66), (-0.09, 0.50, 1.66), 'saddle'),
    ('rein_hand.R', (0.09, 0.40, 1.66), (0.09, 0.50, 1.66), 'saddle'),
    ('lance', (0.12, 0.30, 1.60), (0.12, 3.30, 1.70), 'saddle'),
]
# rein chains: 4 bones per side from the bit ring (0,±0.07) to rein_hand, rest = straight line with a small sag
def _rein_rest(sx):
    a = V(0.07 * sx, 1.30, 1.44); b = V(0.09 * sx, 0.40, 1.66)
    pts = []
    for i in range(5):
        t = i / 4
        p = a.lerp(b, t); p.z -= 0.10 * 4 * t * (1 - t)
        pts.append(p)
    return pts
for _s, _sx in (('L', -1), ('R', 1)):
    _p = _rein_rest(_sx)
    for _i in range(4):
        HX_BONES.append(('rein_%02d.%s' % (_i + 1, _s), tuple(_p[_i]), tuple(_p[_i + 1]), 'saddle'))

BI = {b[0]: b for b in HX_BONES}
PARENT = {b[0]: b[3] for b in HX_BONES}
NAMES = [b[0] for b in HX_BONES]

def _rest_matrix(name):
    _, h, t, _ = BI[name]
    h, t = V(h), V(t)
    y = (t - h).normalized()
    q = V(0, 1, 0).rotation_difference(y)
    return Matrix.Translation(h) @ q.to_matrix().to_4x4()

REST = {n: _rest_matrix(n) for n in NAMES}
HEAD = {n: V(BI[n][1]) for n in NAMES}
TAIL = {n: V(BI[n][2]) for n in NAMES}
def blen(n):
    return (TAIL[n] - HEAD[n]).length

def rot(e):
    """euler degrees about armature X (pitch, +=nose up for forward bones), Y (roll), Z (yaw) -> 3x3"""
    return Euler([math.radians(a) for a in e], 'XYZ').to_matrix()

def about(p, R3):
    """4x4 rotating by R3 about point p"""
    p = V(p)
    return Matrix.Translation(p) @ R3.to_4x4() @ Matrix.Translation(-p)

def frame_from(d, s):
    d = V(d).normalized(); s = V(s)
    s = (s - d * s.dot(d))
    if s.length < 1e-6:
        s = V(1, 0, 0) - d * d.x
    s.normalize()
    return Matrix((s, d, s.cross(d))).transposed()

def two_bone(S, W, a, b, pole):
    D = W - S; dist = D.length
    dist_c = max(min(dist, (a + b) * 0.9995), abs(a - b) + 1e-4)
    dn = D.normalized()
    W2 = S + dn * dist_c
    x = (a * a - b * b + dist_c * dist_c) / (2 * dist_c)
    h = math.sqrt(max(a * a - x * x, 0.0))
    pv = pole - S; pv = pv - dn * pv.dot(dn)
    if pv.length < 1e-6:
        pv = V(0, 0, 1) - dn * dn.z
    pv.normalize()
    return S + dn * x + pv * h, W2

class HPose:
    """D[name] = skinning delta (posed @ rest^-1) for every bone, in armature space."""
    def __init__(self):
        self.D = {}

    def fk(self, name, euler=(0, 0, 0), pre=None):
        """child follows its parent's delta, then rotates by euler (armature axes) about its posed head."""
        par = PARENT[name]
        Dp = self.D[par] if par is not None else Matrix.Identity(4)
        h = Dp @ HEAD[name]
        Rp = Dp.to_3x3()
        # euler is expressed in the parent's current frame (so 'pitch' stays a pitch when the body rolls)
        M = about(h, Rp @ rot(euler) @ Rp.inverted()) @ Dp
        if pre is not None:
            M = pre @ M
        self.D[name] = M
        return M

    def set_seg(self, name, head, d, hinge, rest_hinge):
        """place bone with posed head at `head`, direction d, using hinge vectors for roll."""
        d0 = TAIL[name] - HEAD[name]
        Q = frame_from(d, hinge) @ frame_from(d0, rest_hinge).transposed()
        self.D[name] = Matrix.Translation(V(head)) @ Q.to_4x4() @ Matrix.Translation(-HEAD[name])

    def head(self, name):
        return self.D[name] @ HEAD[name]

    def tail(self, name):
        return self.D[name] @ TAIL[name]

    def posed(self, name):
        return self.D[name] @ REST[name]

    def basis(self, name):
        """matrix_basis for a Blender pose bone (rest from REST) so its armature-space pose == D @ REST."""
        R = REST[name]; par = PARENT[name]
        P = self.D[name] @ R
        if par is None:
            return R.inverted() @ P
        Pp = self.D[par] @ REST[par]
        return (REST[par].inverted() @ R).inverted() @ Pp.inverted() @ P

def build_armature(name='hx_rig'):
    import bpy
    arm = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for n, h, t, p in HX_BONES:
        eb = arm.edit_bones.new(n)
        eb.head = h; eb.tail = t; eb.roll = 0.0
        if p:
            eb.parent = arm.edit_bones[p]
        eb.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:   # use Blender's exact rest matrices (roll convention)
        REST[pb.name] = pb.bone.matrix_local.copy()
    return rig
