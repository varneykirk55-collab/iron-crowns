"""Horse v3: ONE config module for every name / position the generator, the rig and the tack use.

Spec: HORSE_SKELETON_SPEC.md v1.2 (origin/rob/cavalry-animation-overhaul a263833, Rob; read-only here).  The exported
armature is SPEC_BONES (= horse_rig.HX_BONES); sockets are the spec sockets.  The generator still models in its own
anatomical frame (LM / BONES below, weights authored there); WARP (thin-plate spline over landmark pairs) maps every
final vertex onto the spec frame, and spec sockets are inverse-warped into the modelling frame for tack placement.
If the spec changes: edit SPEC_BONES / _WARP_C / _WARP_S / BONE_RENAME here and re-run horse_v3.py.

Axes (spec 1): Blender +Y forward, +Z up, metres, ground z = 0; horse RIGHT = +X (.R = +X).  Bake maps
(x, y, z) -> Godot (x, z, -y).

Seat (spec 3): saddle socket (0, 0.12, 1.42) = lowest seat point on top of the pad; rider_seat 1.488 = v3 seated hip.
SEAT_Y / SEAT_TOP_Z below are overridden from the (inverse-warped) spec sockets further down; the lines here are the
old provisional modelling-frame values kept for the LM block."""

WITHERS = 1.46          # metres, top of withers (14.1 hh); 1.50-1.55 does not fit a 1.488 hip with a real saddle
Z_HIP = 1.488           # v3 seated hip joint (rider_seat socket z)
SEAT_TOP_Z = 1.385      # saddle seat top surface (centre line) under the rider crotch
SEAT_Y = 0.10           # y of the rider hip joint / deepest point of the seat on this horse

# ---------------------------------------------------------------------------------------------------------------------
# Landmarks (anatomy, Blender coords). Bones and SDF primitives are built from these.
LM = {
    'withers': (0.0, 0.36, 1.46), 'back_low': (0.0, 0.08, 1.35), 'loin': (0.0, -0.22, 1.37),
    'croup': (0.0, -0.44, 1.415), 'tail_root': (0.0, -0.72, 1.34),
    'poll': (0.0, 1.00, 1.76), 'muzzle': (0.0, 1.36, 1.34),
    # legs: side x is the +X (right) value; mirrored for left
    'f_shoulder': (0.13, 0.66, 1.08), 'f_elbow': (0.14, 0.42, 0.86), 'f_knee': (0.12, 0.47, 0.46),
    'f_fetlock': (0.12, 0.465, 0.15), 'f_coronet': (0.12, 0.50, 0.065), 'f_toe': (0.12, 0.555, 0.0),
    'h_hip': (0.15, -0.53, 1.12), 'h_stifle': (0.165, -0.36, 0.88), 'h_hock': (0.13, -0.63, 0.50),
    'h_fetlock': (0.125, -0.615, 0.15), 'h_coronet': (0.125, -0.58, 0.065), 'h_toe': (0.125, -0.525, 0.0),
}

# ---------------------------------------------------------------------------------------------------------------------
# Armature. (name, head, tail, parent, deform). Leg bones listed for the RIGHT side with x > 0; `.L` mirrored.
_R_LEG = [
    ('f_scapula', (0.12, 0.40, 1.36), 'f_shoulder', 'chest'),
    ('f_humerus', 'f_shoulder', 'f_elbow', 'f_scapula'),
    ('f_forearm', 'f_elbow', 'f_knee', 'f_humerus'),
    ('f_cannon', 'f_knee', 'f_fetlock', 'f_forearm'),
    ('f_fetlock', 'f_fetlock', 'f_coronet', 'f_cannon'),     # pastern, rotates at the fetlock joint
    ('f_hoof', 'f_coronet', 'f_toe', 'f_fetlock'),
    ('h_femur', 'h_hip', 'h_stifle', 'pelvis'),
    ('h_tibia', 'h_stifle', 'h_hock', 'h_femur'),
    ('h_cannon', 'h_hock', 'h_fetlock', 'h_tibia'),
    ('h_fetlock', 'h_fetlock', 'h_coronet', 'h_cannon'),
    ('h_hoof', 'h_coronet', 'h_toe', 'h_fetlock'),
]

BONES = [
    ('root', (0, 0, 0), (0, 0.25, 0), None, False),
    ('pelvis', (0, -0.42, 1.25), (0, -0.14, 1.25), 'root', True),
    ('spine01', (0, -0.14, 1.25), (0, 0.12, 1.24), 'pelvis', True),
    ('spine02', (0, 0.12, 1.24), (0, 0.36, 1.25), 'spine01', True),
    ('chest', (0, 0.36, 1.25), (0, 0.56, 1.22), 'spine02', True),
    ('neck01', (0, 0.56, 1.22), (0, 0.72, 1.40), 'chest', True),
    ('neck02', (0, 0.72, 1.40), (0, 0.86, 1.57), 'neck01', True),
    ('neck03', (0, 0.86, 1.57), (0, 0.98, 1.71), 'neck02', True),
    ('head', (0, 0.98, 1.71), (0, 1.33, 1.37), 'neck03', True),
    ('jaw', (0, 1.03, 1.62), (0, 1.30, 1.33), 'head', True),
    ('ear.R', (0.05, 0.995, 1.83), (0.07, 1.01, 1.97), 'head', True),
    ('ear.L', (-0.05, 0.995, 1.83), (-0.07, 1.01, 1.97), 'head', True),
    ('tail01', (0, -0.74, 1.34), (0, -0.82, 1.24), 'pelvis', True),
    ('tail02', (0, -0.82, 1.24), (0, -0.88, 1.06), 'tail01', True),
    ('tail03', (0, -0.88, 1.06), (0, -0.91, 0.86), 'tail02', True),
    ('tail04', (0, -0.91, 0.86), (0, -0.93, 0.62), 'tail03', True),
]
for side, sx in (('.R', 1.0), ('.L', -1.0)):
    for n, h, t, p in _R_LEG:
        hh = LM[h] if isinstance(h, str) else h
        tt = LM[t] if isinstance(t, str) else t
        pp = p + side if p.startswith(('f_', 'h_')) else p
        BONES.append((n + side, (sx * hh[0], hh[1], hh[2]), (sx * tt[0], tt[1], tt[2]), pp, True))

# =====================================================================================================================
# Rob's HX rig, HORSE_SKELETON_SPEC.md v1.2 (origin/rob/cavalry-animation-overhaul a263833, rig 511bc5c).  Copied
# here read-only; if the spec changes, edit SPEC_BONES / WARP and re-run.  The generator models in its own frame
# (LM / BONES above); WARP maps that frame onto the spec frame (applied to every final vertex), sockets are authored
# in spec coords and inverse-warped into the modelling frame for tack placement.
def _spec_legs(s, sx):
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

SPEC_BONES = [   # (name, head, tail, parent) – spec v1.2 section 2 (= horse_rig.HX_BONES)
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
] + _spec_legs('R', 1) + _spec_legs('L', -1) + [
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
REIN_SEGS = 4
SPEC_BIT_RING_X = 0.07
def _rein_rest(sx):   # spec: straight bit ring -> rein_hand line, sag 0.10 * 4t(1-t)
    a = (0.07 * sx, 1.30, 1.44); b = (0.09 * sx, 0.40, 1.66); out = []
    for i in range(REIN_SEGS + 1):
        t = i / REIN_SEGS
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t - 0.10 * 4 * t * (1 - t)))
    return out
for _s, _sx in (('L', -1), ('R', 1)):
    _p = _rein_rest(_sx)
    for _i in range(REIN_SEGS):
        SPEC_BONES.append(('rein_%02d.%s' % (_i + 1, _s), _p[_i], _p[_i + 1], 'saddle'))
SOCKET_NAMES = ('saddle', 'rider_seat', 'stirrup.L', 'stirrup.R', 'rein_bit', 'bridle', 'rein_hand.L', 'rein_hand.R',
                'lance')

# modelling-frame point -> spec-frame point.  Trunk: skin points on the top line; legs: joint centres (x kept: the
# spec joints sit at x 0.15-0.19, the mesh joints at 0.12-0.165 inside a 0.42-0.44 m chest; swing is about X, so the
# x offset does not change the deformation); head/neck: bone joints.  Mirrored for -x automatically.
_WARP_C = [   # centre line (x = 0)
    ((0, 0.33, 1.47), (0, 0.38, 1.55)),        # withers skin  -> ~1.55
    ((0, 0.05, 1.349), (0, 0.08, 1.385)),      # back (lowest) skin
    ((0, -0.45, 1.432), (0, -0.45, 1.50)),     # croup skin    -> ~1.50
    ((0, -0.74, 1.34), (0, -0.80, 1.30)),      # tail root     -> tail_01 head
    ((0, -0.93, 0.62), (0, -1.00, 0.63)),      # tail bone tip -> tail_05 tail
    ((0, -0.05, 0.865), (0, -0.05, 0.87)),     # belly (fix pass 1: lighter barrel, ~0.68 m girth depth)
    ((0, 0.56, 1.22), (0, 0.66, 1.28)),        # neck_01 head
    ((0, 0.72, 1.40), (0, 0.84, 1.52)),        # neck_02 head
    ((0, 0.86, 1.57), (0, 0.97, 1.72)),        # neck_03 head
    ((0, 1.00, 1.76), (0, 1.05, 1.86)),        # poll (head head)
    ((0, 1.36, 1.34), (0, 1.40, 1.44)),        # muzzle (head tail)
    ((0, 1.03, 1.62), (0, 1.10, 1.72)),        # jaw head
    ((0, 1.255, 1.385), (0, 1.30, 1.44)),      # mouth corner / bit centre -> rein_bit
]
_WARP_S = [   # +x side, mirrored
    ((0.07, 1.01, 1.97), (0.07, 1.02, 2.04)),  # ear tip
    ((0.13, 0.66, 1.08), (0.13, 0.70, 1.06)),  # point of shoulder (humerus head)
    ((0.14, 0.42, 0.86), (0.14, 0.52, 0.84)),  # elbow (radius head)
    ((0.12, 0.47, 0.46), (0.12, 0.54, 0.50)),  # knee (cannon_f head)
    ((0.12, 0.465, 0.15), (0.12, 0.54, 0.23)),  # front fetlock
    ((0.12, 0.50, 0.065), (0.12, 0.60, 0.09)),  # front coronet
    ((0.12, 0.555, 0.0), (0.12, 0.68, 0.0)),    # front toe
    ((0.12, 0.48, 0.0), (0.12, 0.59, 0.0)),     # front heel (keeps the sole flat)
    ((0.165, 0.515, 0.0), (0.165, 0.635, 0.0)), # front sole, outside
    ((0.075, 0.515, 0.0), (0.075, 0.635, 0.0)), # front sole, inside
    ((0.15, -0.53, 1.12), (0.15, -0.50, 1.18)),  # hip (femur head)
    ((0.165, -0.36, 0.88), (0.165, -0.30, 0.88)),  # stifle (tibia head)
    ((0.13, -0.63, 0.50), (0.13, -0.64, 0.54)),  # hock (cannon_h head)
    ((0.125, -0.615, 0.15), (0.125, -0.62, 0.23)),  # hind fetlock
    ((0.125, -0.58, 0.065), (0.125, -0.57, 0.09)),  # hind coronet
    ((0.125, -0.525, 0.0), (0.125, -0.49, 0.0)),    # hind toe
    ((0.125, -0.60, 0.0), (0.125, -0.57, 0.0)),     # hind heel
    ((0.17, -0.56, 0.0), (0.17, -0.53, 0.0)),       # hind sole, outside
    ((0.08, -0.56, 0.0), (0.08, -0.53, 0.0)),       # hind sole, inside
]
WARP_PAIRS = _WARP_C + [p for a, b in _WARP_S for p in ((a, b), ((-a[0],) + a[1:], (-b[0],) + b[1:]))]
import horse_v3_warp as _W
WARP = _W.TPS([a for a, b in WARP_PAIRS], [b for a, b in WARP_PAIRS])

def to_model(p):
    """spec-frame point(s) -> modelling frame (inverse warp)."""
    return _W.np.asarray(WARP.inverse(p))

# Sockets / tack bones in the MODELLING frame (inverse-warped spec sockets).  deform=True ones carry tack weights.
_SPEC = {n: (h, t, p) for n, h, t, p in SPEC_BONES}
_DEFORM_SOCKETS = {'saddle', 'stirrup.L', 'stirrup.R', 'rein_bit', 'rein_hand.L', 'rein_hand.R'}
SOCKETS = []
for _n in SOCKET_NAMES:
    _h, _t, _p = _SPEC[_n]
    if _n == 'lance':
        _hh = to_model([_h])[0]; _tt = _hh + _W.np.subtract(_t, _h)
    else:
        _hh, _tt = to_model([_h, _t])
    SOCKETS.append((_n, tuple(map(float, _hh)), tuple(map(float, _tt)), _p, _n in _DEFORM_SOCKETS))
_SOC = {s[0]: s for s in SOCKETS}
SEAT_Y = _SOC['rider_seat'][1][1]
SEAT_TOP_Z = _SOC['saddle'][1][2]          # saddle socket = lowest seat point on top of the pad
BIT_RING_X = SPEC_BIT_RING_X
# rein chain rest pose in the modelling frame (tack reins are built along it and weighted to it)
REIN_REST = {s: [tuple(map(float, q)) for q in to_model(_rein_rest(sx))] for s, sx in (('R', 1), ('L', -1))}
TAIL_CHAIN = ['tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05']
# spec chains as modelling-frame segments for weighting (tail, reins)
MODEL_EXTRA_BONES = []
for _n, _h, _t, _p in SPEC_BONES:
    if _n.startswith(('tail_', 'rein_0')):
        _hh, _tt = to_model([_h, _t])
        MODEL_EXTRA_BONES.append((_n, tuple(map(float, _hh)), tuple(map(float, _tt)), _p, True))

# modelling-bone name -> spec name (vertex groups are written with spec names)
BONE_RENAME = {'spine01': 'spine_01', 'spine02': 'spine_02', 'neck01': 'neck_01', 'neck02': 'neck_02',
               'neck03': 'neck_03', 'tail01': 'tail_01', 'tail02': 'tail_02', 'tail03': 'tail_03', 'tail04': 'tail_04'}
for _s in ('.R', '.L'):
    for _a, _b in (('f_scapula', 'scapula'), ('f_humerus', 'humerus'), ('f_forearm', 'radius'), ('f_cannon', 'cannon_f'),
                   ('f_fetlock', 'fetlock_f'), ('f_hoof', 'hoof_f'), ('h_femur', 'femur'), ('h_tibia', 'tibia'),
                   ('h_cannon', 'cannon_h'), ('h_fetlock', 'fetlock_h'), ('h_hoof', 'hoof_h')):
        BONE_RENAME[_a + _s] = _b + _s

# ---------------------------------------------------------------------------------------------------------------------
LOD = {   # triangle targets for the SDF (voxel) layers; parametric layers are sized by VBUDGET
    'body':  (6400, 1150, 420),
    'hair':  (1500, 260, 90),
    'eyes':  (96, 0, 0),
    'tack_1800': (0, 0, 0),
    'tack_1300': (0, 0, 0),
    'barding_1300': (0, 0, 0),
}
# spec v1.2 section 6: Blender vertex counts after sharp splits.  LOD0 horse <= 4.4k, tack + barding <= 1.7k per
# variant; LOD1 horse + tack <= 1.5k; LOD2 horse + tack <= 0.6k.  (Rider + weapon budgets are separate.)
VBUDGET = {
    'horse_body':   (3500, 640, 240),
    'horse_hair':   (820, 150, 55),
    'horse_eyes':   (70, 0, 0),
    'tack_1800':    (1480, 690, 290),   # glb export adds ~10 % (UV / colour splits): 1.7k exported cap
    'tack_1300':    (880, 400, 160),
    'barding_1300': (620, 290, 140),
}
RES_STEPS = (1.0, 0.9, 0.8, 0.7, 0.62, 0.55, 0.48, 0.42, 0.36, 0.3, 0.25, 0.2)
VOXEL = {'body': 0.0065, 'hair': 0.005, 'cloth': 0.0055, 'saddle': 0.005}

# material classes (common.MAT_*): coat = HIDE 8, mane/tail = HAIR 11, hoof/eye = LEATHER 2 (dark, glossy)
COATS = {   # coat rgb, points rgb (lower legs / mane / tail / muzzle), hair rgb, markings
    'bay':       {'coat': (0.36, 0.20, 0.11), 'points': (0.06, 0.05, 0.045), 'hair': (0.05, 0.04, 0.035), 'socks': ()},
    'chestnut':  {'coat': (0.50, 0.27, 0.13), 'points': None, 'hair': (0.55, 0.33, 0.16), 'socks': ('h_.L',), 'blaze': True},
    'dark_bay':  {'coat': (0.17, 0.10, 0.06), 'points': (0.05, 0.04, 0.035), 'hair': (0.04, 0.035, 0.03), 'socks': ()},
    'black':     {'coat': (0.06, 0.055, 0.05), 'points': None, 'hair': (0.035, 0.032, 0.03), 'socks': ()},
    'grey':      {'coat': (0.62, 0.61, 0.58), 'points': (0.30, 0.29, 0.28), 'hair': (0.70, 0.69, 0.66), 'socks': (), 'dapple': True},
}
HOOF_RGB = (0.12, 0.10, 0.085)
EYE_RGB = (0.03, 0.02, 0.015)

TEAM_RGB = (0.62, 0.10, 0.09)   # preview stand-in for the team colour on team-masked cloth
