"""Character refinement: shared skeleton for every semi-realistic c19 foot soldier + a pure-python pose solver
(FK for the trunk, analytic 2-bone IK for arms/legs, prop bone for musket/rammer, hands gripping the prop).
Poses are computed as armature-space bone matrices, then written to a real Blender armature (matrix_basis) so the
same animation drives the skinned mesh (VAT bake) and is keyed into actions (blend file / rigged export)."""
import math
from mathutils import Vector, Matrix, Quaternion, Euler
from char_geo import V, lerp, smoothstep

# name, head, tail, parent   (Blender coords; character faces +Y; +X = its right side; ~1.76 m tall)
BONES = [
    ('root', (0, 0, 0), (0, 0.15, 0), None),
    ('hips', (0, 0, 0.95), (0, 0, 1.06), 'root'),
    ('spine', (0, 0, 1.06), (0, 0, 1.26), 'hips'),
    ('chest', (0, 0, 1.26), (0, 0, 1.47), 'spine'),
    ('neck', (0, 0.0, 1.47), (0, 0.012, 1.575), 'chest'),
    ('head', (0, 0.012, 1.575), (0, 0.012, 1.77), 'neck'),
    ('clav.R', (0.025, 0.0, 1.43), (0.175, -0.012, 1.428), 'chest'),
    ('upper_arm.R', (0.18, -0.012, 1.425), (0.205, -0.012, 1.14), 'clav.R'),
    ('forearm.R', (0.205, -0.012, 1.14), (0.222, 0.0, 0.895), 'upper_arm.R'),
    ('hand.R', (0.222, 0.0, 0.895), (0.228, 0.004, 0.735), 'forearm.R'),
    ('clav.L', (-0.025, 0.0, 1.43), (-0.175, -0.012, 1.428), 'chest'),
    ('upper_arm.L', (-0.18, -0.012, 1.425), (-0.205, -0.012, 1.14), 'clav.L'),
    ('forearm.L', (-0.205, -0.012, 1.14), (-0.222, 0.0, 0.895), 'upper_arm.L'),
    ('hand.L', (-0.222, 0.0, 0.895), (-0.228, 0.004, 0.735), 'forearm.L'),
    ('thigh.R', (0.095, 0.0, 0.925), (0.1, 0.012, 0.505), 'hips'),
    ('shin.R', (0.1, 0.012, 0.505), (0.1, -0.012, 0.088), 'thigh.R'),
    ('foot.R', (0.1, -0.012, 0.088), (0.112, 0.15, 0.025), 'shin.R'),
    ('thigh.L', (-0.095, 0.0, 0.925), (-0.1, 0.012, 0.505), 'hips'),
    ('shin.L', (-0.1, 0.012, 0.505), (-0.1, -0.012, 0.088), 'thigh.L'),
    ('foot.L', (-0.1, -0.012, 0.088), (-0.112, 0.15, 0.025), 'shin.L'),
    ('prop', (0.29, 0.07, 0.43), (0.29, 0.07, 0.6), None),   # musket / rammer: local +Y = barrel / pole axis
]
BI = {b[0]: b for b in BONES}
PARENT = {b[0]: b[3] for b in BONES}

def _rest_matrix(name):
    """armature-space rest matrix with roll 0 (same convention Blender uses for roll = 0)."""
    _, h, t, _ = BI[name]
    h, t = V(h), V(t)
    y = (t - h).normalized()
    # Blender's roll-0 bone matrix: rotation taking +Y to the bone vector via vec_roll_to_mat3
    q = V(0, 1, 0).rotation_difference(y)
    # Blender special-cases bones pointing ~-Y; ours never do.
    m = q.to_matrix()
    # vec_roll_to_mat3 actually uses a specific minimal-rotation construction == rotation_difference result
    return Matrix.Translation(h) @ m.to_4x4()

REST = {b[0]: _rest_matrix(b[0]) for b in BONES}

def set_rest_from_blender(rig):
    """use Blender's own rest matrices (exact roll convention)."""
    for pb in rig.pose.bones:
        REST[pb.name] = pb.bone.matrix_local.copy()

def blen(name):
    _, h, t, _ = BI[name]
    return (V(t) - V(h)).length

def rot_arm(e):
    """euler degrees (armature axes) -> 3x3"""
    return Euler([math.radians(a) for a in e], 'XYZ').to_matrix()

# prop grips (prop-local coords, +Y along the prop, +Z = top of the barrel, +X = lock side)
MUSKET = {'butt': -0.35, 'wrist': 0.0, 'fore': 0.24, 'band': 0.55, 'muzzle': 1.12, 'tip': 1.52}

def frame_from(d, s):
    """orthonormal 3x3 with columns (s_orth, d, s_orth x d)"""
    d = V(d).normalized(); s = V(s)
    s = (s - d * s.dot(d))
    if s.length < 1e-6:
        s = V(1, 0, 0) - d * d.x
    s.normalize()
    m = Matrix((s, d, s.cross(d))).transposed()
    return m

def two_bone(S, W, a, b, pole):
    """elbow/knee position for shoulder S, wrist W, lengths a,b, pole point."""
    D = W - S; dist = D.length
    dist_c = max(min(dist, (a + b) * 0.9995), abs(a - b) + 1e-4)
    dn = D.normalized()
    W2 = S + dn * dist_c
    x = (a * a - b * b + dist_c * dist_c) / (2 * dist_c)
    h = math.sqrt(max(a * a - x * x, 0.0))
    pv = (pole - S); pv = pv - dn * pv.dot(dn)
    if pv.length < 1e-6:
        pv = V(0, 0, 1) - dn * dn.z
    pv.normalize()
    return S + dn * x + pv * h, W2, dist / (a + b)

class Pose:
    """armature-space posed matrices for every bone."""
    def __init__(self):
        self.P = {}
        self.reach = 1.0

    def fk(self, name, euler=(0, 0, 0), offset=None):
        R = REST[name]; par = PARENT[name]
        L = R.to_3x3().inverted() @ rot_arm(euler) @ R.to_3x3()
        if par is None or par == 'root':
            Pp = Matrix.Identity(4)
            M = Pp @ R @ L.to_4x4()
        else:
            Pp = self.P[par]
            M = Pp @ REST[par].inverted() @ R @ L.to_4x4()
        if offset is not None:
            M = Matrix.Translation(V(offset)) @ M
        self.P[name] = M
        return M

    def delta(self, name):
        """posed * rest^-1: maps rest armature coords into the posed frame of bone `name`."""
        return self.P[name] @ REST[name].inverted()

    def set_dir(self, name, head, d, hinge, rest_hinge):
        R3 = REST[name].to_3x3()
        d0 = (R3 @ V(0, 1, 0))
        Q = frame_from(d, hinge) @ frame_from(d0, rest_hinge).transposed()
        self.P[name] = Matrix.Translation(head) @ (Q @ R3).to_4x4()

    def limb(self, upper, lower, end, target, pole, rest_hinge, end_frame=None, end_rest=None, end_euler=None):
        """2-bone IK: target = position of `end` head (wrist / ankle)."""
        par = PARENT[upper]
        S = (self.P[par] @ REST[par].inverted() @ REST[upper]).translation if par != 'root' else REST[upper].translation
        a, b = blen(upper), blen(lower)
        E, W, r = two_bone(S, V(target), a, b, V(pole))
        self.reach = max(self.reach, r) if r > 1 else self.reach
        u1 = (E - S).normalized(); u2 = (W - E).normalized()
        n = u1.cross(u2)
        if n.length < 1e-3:
            n = (V(pole) - S).cross(u1) * -1.0
            n = (V(pole) - S).normalized().cross(u1)
            n = -n if n.dot(V(rest_hinge)) < 0 else n
        n.normalize()
        self.set_dir(upper, S, u1, n, V(rest_hinge))
        self.set_dir(lower, E, u2, n, V(rest_hinge))
        R3 = REST[end].to_3x3()
        if end_frame is not None:     # (dir, secondary) target frame + rest (dir, secondary)
            Q = frame_from(*end_frame) @ frame_from(*end_rest).transposed()
            self.P[end] = Matrix.Translation(W) @ (Q @ R3).to_4x4()
        else:                         # follow the lower bone + extra armature-axes euler
            L = REST[lower].to_3x3().inverted() @ R3
            M3 = self.P[lower].to_3x3() @ L
            if end_euler:
                M3 = rot_arm(end_euler) @ M3
            self.P[end] = Matrix.Translation(W) @ M3.to_4x4()
        return E, W

    def basis(self, name):
        """matrix_basis for a Blender pose bone so that its posed matrix == self.P[name]."""
        R = REST[name]; par = PARENT[name]
        if par is None:
            return R.inverted() @ self.P[name]
        Pp = self.P[par] if par in self.P else REST[par]
        return (REST[par].inverted() @ R).inverted() @ Pp.inverted() @ self.P[name]

def mlerp(A, B, t):
    """blend two 4x4 rigid matrices"""
    la, ra, _ = A.decompose(); lb, rb, _ = B.decompose()
    return Matrix.Translation(la.lerp(lb, t)) @ ra.slerp(rb, t).to_matrix().to_4x4()
