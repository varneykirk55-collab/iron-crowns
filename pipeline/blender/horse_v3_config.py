"""Horse v3: ONE config dict for every name / position the generator, the rig and the tack use.

PROVISIONAL (2026-10-23): Rob's HORSE_SKELETON_SPEC.md is not out yet. Bone + socket names / positions below are the
agreed provisional contract (saddle, rider_seat, stirrup.L/R, rein_bit, rein_hand.L/R, bridle; neck >= 3, tail >= 4,
fetlock per leg). When the spec lands, remap here (BONE_RENAME + positions) and re-run horse_v3.py; nothing else
hard-codes a bone name or a socket position.

Axes: Blender +Y forward (model front), +Z up, metres, ground z = 0, origin on the ground midway between the front and
hind hooves. Horse RIGHT = +X (so `.R` is +X, `.L` is -X; same as the legacy r_arm.R at +x). The VAT bake maps
(x, y, z) -> Godot (x, z, -y): front = Godot -Z (ANIM_INTERFACE.md).

Seat: target the v3 seated rider hip at z = 1.488 (v3_rider.Z_HIP, Rob: unchanged). The v3 seat transform squashes the
standing body by K_TORSO 0.92 about z 0.95 -> standing crotch (~0.84) lands at 1.488 - 0.92 * 0.11 = ~1.387, so the
saddle seat surface (top of the sheepskin / seat leather, centre line, deepest point) is SEAT_TOP_Z = 1.385.
That only leaves room for a ~1.46 m withers (see notes): WITHERS is the measured top of the withers of the mesh."""

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

# Sockets / tack bones. deform=True ones carry tack weights (Rob: tack weighted to real bones).
_SY, _ST = SEAT_Y, SEAT_TOP_Z
SOCKETS = [
    ('saddle', (0, _SY + 0.02, _ST - 0.01), (0, _SY + 0.22, _ST - 0.01), 'spine02', True),
    ('rider_seat', (0, _SY, Z_HIP), (0, _SY + 0.15, Z_HIP), 'saddle', False),   # v3 rider hip lands here
    ('stirrup.R', (0.17, _SY + 0.12, 1.33), (0.30, _SY + 0.20, 0.79), 'saddle', True),   # bar -> tread
    ('stirrup.L', (-0.17, _SY + 0.12, 1.33), (-0.30, _SY + 0.20, 0.79), 'saddle', True),
    ('bridle', (0, 1.00, 1.80), (0, 1.06, 1.86), 'head', False),
    ('rein_bit', (0, 1.255, 1.385), (0, 1.30, 1.385), 'head', False),          # bit centre (rings at +-0.065 x)
    ('rein_hand.R', (0.10, _SY + 0.33, 1.60), (0.10, _SY + 0.40, 1.60), 'saddle', False),
    ('rein_hand.L', (-0.10, _SY + 0.33, 1.60), (-0.10, _SY + 0.40, 1.60), 'saddle', False),
]
REIN_SEGS = 3   # rein.{L,R}.01..03: chain from the bit ring to rein_hand, parent head (Rob IKs to the hand)
BIT_RING_X = 0.068

# rename hook for Rob's spec: {'provisional_name': 'spec_name'}
BONE_RENAME = {}

# ---------------------------------------------------------------------------------------------------------------------
LOD = {   # target triangle counts per layer
    'body':  (7000, 1700, 480),
    'hair':  (1600, 380, 110),
    'eyes':  (160, 48, 0),
    'tack_1800': (5000, 1400, 420),
    'tack_1300': (4200, 1100, 340),
    'barding_1300': (3600, 900, 280),
}
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
