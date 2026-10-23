"""Visual pass (medieval era, c.1300): detailed kit for med_spear / med_archer infantry, med_knight cavalry and the
art_bombard prop. Same rig, bone names, proportions and silhouettes as the generic builders in soldiers.py /
cavalry.py / props.py (see c19_kit.py for the template). Readability rules (c19 review): team colour on the large
front AND back areas (cameras mostly see lines from behind), light linen / heraldic accents that read at distance,
no dark masses on the back, contact AO only at the feet (shader). LOD1 (detail=False, > 75 m) keeps only what reads."""
import math
from common import (hexc, MeshBuilder, MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_BRASS, MAT_SKIN, MAT_WOOD, MAT_PIPECLAY,
                    MAT_HIDE, MAT_FUR, MAT_IRON, MAT_HAIR, MAT_MAIL, MAT_CANVAS)

TEAM = (1, 1, 1, 1.0)
SKIN = hexc('d9a988'); HAIR = hexc('4a3424')
MAIL = hexc('9aa1a8'); STEEL = hexc('b4bbc2'); IRON = hexc('3a3d42'); BRASS = hexc('c09a45')
LINEN = hexc('ece4cf'); HERALD = hexc('f0ece0')           # light linen / heraldic charge (kept bright, no AO)
HOSE = hexc('7a6650'); HOSE_D = hexc('5e4e3e'); SHOE = hexc('3a2a1e'); LEATHER = hexc('6a4a30'); LEATHER_D = hexc('3e2c1e')
ASH = hexc('9a7a52'); YEW = hexc('b07a44'); WOOD_D = hexc('5a3e26'); FLETCH = hexc('f2efe6')

def _legs(b, hose, shoe, detail, mail=False):
    for side, x in (('R', 0.09), ('L', -0.09)):
        b.box((0.13, 0.15, 0.44), (x, 0, 0.74), MAIL if mail else hose, 'thigh.' + side, taper=1.1, mat=MAT_MAIL if mail else MAT_WOOL)
        b.box((0.11, 0.13, 0.36), (x, 0, 0.31), MAIL if mail else hose, 'shin.' + side, taper=1.15, mat=MAT_MAIL if mail else MAT_WOOL)
        b.box((0.11, 0.24, 0.09), (x, 0.04, 0.05), shoe, 'shin.' + side, mat=MAT_LEATHER)
        if detail:
            b.box((0.116, 0.136, 0.05), (x, 0, 0.44), LEATHER, 'shin.' + side, mat=MAT_LEATHER)  # garter / hose tie

def _head(b, detail, s):
    b.box((0.09, 0.09, 0.06), (0, 0, 1.52), SKIN, 'head', mat=MAT_SKIN)
    b.sphere(0.115, (0, 0.01, 1.64), SKIN, 'head', segs=s, rings=5 if detail else 4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)

def _cross(b, z0, bone, front=True, back=True, w=0.06, h=0.36, arm=0.3, y=0.118, zc=None):
    """light heraldic cross on a tabard (both faces): reads like the c19 white X at distance."""
    zc = z0 if zc is None else zc
    for sy in ((1,) if front and not back else (-1,) if back and not front else (1, -1)):
        b.box((w, 0.012, h), (0, y * sy, z0), HERALD, bone, mat=MAT_PIPECLAY)
        b.box((arm, 0.012, w), (0, y * sy, zc), HERALD, bone, mat=MAT_PIPECLAY)

# ------------------------------------------------------------------ infantry (rig = soldiers.BONES)
def spearman(name, groups, detail):
    """c.1300 foot sergeant: mail haubergeon under a team surcoat with a light cross, kettle hat over a mail coif,
    heater shield (team, light fess + rim), ash spear with a steel leaf head, short sword at the hip."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    _legs(b, HOSE, SHOE, detail)
    # mail skirt showing below the surcoat + mail sleeves
    b.box((0.37, 0.215, 0.14), (0, 0, 0.92), MAIL, 'hips', taper=1.05, mat=MAT_MAIL)
    # surcoat (team): torso + split skirt front / back to mid-thigh
    b.box((0.35, 0.21, 0.24), (0, 0, 1.1), TEAM, 'spine', taper=1.12, mat=MAT_WOOL)
    b.box((0.41, 0.235, 0.26), (0, 0, 1.36), TEAM, 'chest', taper=1.05, mat=MAT_WOOL)
    for y in (0.085, -0.085):
        b.box((0.34, 0.05, 0.3), (0, y, 0.84), TEAM, 'hips', taper=1.12, mat=MAT_WOOL)
    _cross(b, 1.27, 'chest', w=0.065, h=0.4, arm=0.32, y=0.124, zc=1.36)
    _cross(b, 0.86, 'hips', w=0.06, h=0.26, arm=0.0001, y=0.114)  # cross foot continues on the skirt
    b.box((0.36, 0.225, 0.045), (0, 0, 1.0), LEATHER_D, 'hips', mat=MAT_LEATHER)  # belt
    if detail:
        b.box((0.035, 0.05, 0.42), (-0.2, 0.0, 0.78), LEATHER_D, 'hips', rot=(12, 0, 0), mat=MAT_LEATHER)  # sword scabbard
        b.box((0.11, 0.03, 0.02), (-0.2, 0.03, 1.0), STEEL, 'hips', mat=MAT_STEEL)                       # cross guard
        b.box((0.045, 0.06, 0.06), (0.14, 0.12, 0.99), BRASS, 'hips', mat=MAT_BRASS)                     # buckle
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.11, 0.12, 0.3), (x, 0, 1.31), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)   # surcoat sleeve cap
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), MAIL, 'forearm.' + side, taper=0.9, mat=MAT_MAIL)
        b.box((0.085, 0.095, 0.09), (x, 0, 0.89), LEATHER, 'hand.' + side, mat=MAT_LEATHER)  # gloves
    _head(b, detail, s)
    # mail coif (around face, neck, shoulders) + kettle hat with a wide brim
    b.sphere(0.128, (0, -0.005, 1.65), MAIL, 'head', segs=s, rings=4, scale=(1.0, 1.0, 1.08), mat=MAT_MAIL)
    b.box((0.27, 0.22, 0.07), (0, -0.01, 1.53), MAIL, 'head', mat=MAT_MAIL)
    b.cyl(0.135, 0.12, 0.09, (0, 0.0, 1.745), STEEL, 'head', segs=s, mat=MAT_STEEL)
    b.cyl(0.215, 0.2, 0.022, (0, 0.0, 1.705), STEEL, 'head', segs=s, mat=MAT_STEEL)
    if detail:
        b.box((0.02, 0.2, 0.035), (0, 0.0, 1.795), STEEL, 'head', mat=MAT_STEEL)  # crown seam
        b.box((0.1, 0.012, 0.1), (0, 0.118, 1.6), SKIN, 'head', mat=MAT_SKIN)     # face opening
    # ash spear (hangs along the arm from hand.R)
    hx, hz = 0.24, 0.89
    L = 2.3
    b.cyl(0.019, 0.019, L, (hx, 0, hz - L * 0.35), ASH, 'hand.R', segs=4 if not detail else 5, mat=MAT_WOOD)
    b.box((0.06, 0.014, 0.24), (hx, 0, hz - L * 0.85 - 0.12), STEEL, 'hand.R', mat=MAT_STEEL)   # leaf blade
    b.cyl(0.024, 0.02, 0.08, (hx, 0, hz - L * 0.85 + 0.03), IRON, 'hand.R', segs=5, mat=MAT_IRON)  # socket
    # heater shield: team field, light fess (horizontal band), dark leather rim
    b.box((0.42, 0.04, 0.55), (-0.26, 0.09, 1.08), TEAM, 'forearm.L', taper=0.85, mat=MAT_WOOD)
    b.box((0.4, 0.046, 0.09), (-0.26, 0.09, 1.16), HERALD, 'forearm.L', mat=MAT_PIPECLAY)
    if detail:
        b.box((0.44, 0.036, 0.03), (-0.26, 0.09, 1.355), LEATHER_D, 'forearm.L', mat=MAT_LEATHER)   # top rim
        b.box((0.08, 0.05, 0.08), (-0.26, 0.12, 1.08), STEEL, 'forearm.L', mat=MAT_STEEL)          # boss
        b.box((0.02, 0.07, 0.4), (-0.26, -0.0, 1.28), LEATHER_D, 'chest', rot=(0, 25, 0), mat=MAT_LEATHER)  # guige strap
    return b.to_object()

def archer(name, groups, detail):
    """c.1300 archer: team padded jack with a light cross on the back, linen shirt sleeves, team hood with liripipe
    over a linen coif, tall yew longbow with a light string, arrow bag with white fletching above the right shoulder."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    _legs(b, HOSE_D, SHOE, detail)
    # padded jack (team) to the hips
    b.box((0.35, 0.21, 0.24), (0, 0, 1.1), TEAM, 'spine', taper=1.12, mat=MAT_WOOL)
    b.box((0.41, 0.235, 0.26), (0, 0, 1.36), TEAM, 'chest', taper=1.05, mat=MAT_WOOL)
    b.box((0.37, 0.22, 0.14), (0, 0, 0.92), TEAM, 'hips', taper=1.08, mat=MAT_WOOL)
    _cross(b, 1.27, 'chest', back=True, front=False, w=0.06, h=0.38, arm=0.3, y=0.124, zc=1.36)
    if detail:
        for z in (1.15, 1.25, 1.42):  # quilting lines (front)
            b.box((0.39, 0.012, 0.012), (0, 0.122, z), (0.6, 0.6, 0.6, 1.0), 'chest' if z > 1.22 else 'spine', mat=MAT_WOOL)
    b.box((0.36, 0.225, 0.045), (0, 0, 1.0), LEATHER, 'hips', mat=MAT_LEATHER)  # belt
    # arrow bag (linen) + fletching
    b.cyl(0.055, 0.065, 0.5, (0.12, -0.155, 1.33), LINEN, 'chest', rot=(-15, 20, 0), segs=s, mat=MAT_CANVAS)
    b.cyl(0.06, 0.05, 0.12, (0.17, -0.2, 1.63), FLETCH, 'chest', rot=(-15, 20, 0), segs=s, mat=MAT_PIPECLAY)
    if detail:
        b.box((0.03, 0.02, 0.5), (0.0, -0.13, 1.3), LEATHER, 'chest', rot=(0, -40, 0), mat=MAT_LEATHER)   # bag strap
        b.box((0.09, 0.03, 0.12), (0.13, 0.12, 0.92), LEATHER_D, 'hips', mat=MAT_LEATHER)                  # purse
        b.box((0.03, 0.04, 0.3), (-0.19, 0.02, 0.84), STEEL, 'hips', rot=(10, 0, 0), mat=MAT_STEEL)        # falchion
        b.cyl(0.07, 0.07, 0.02, (-0.2, 0.12, 0.98), STEEL, 'hips', rot=(90, 0, 0), segs=6, mat=MAT_STEEL)  # buckler
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.105, 0.115, 0.3), (x, 0, 1.31), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), LINEN, 'forearm.' + side, taper=0.9, mat=MAT_CANVAS)   # shirt sleeves (light)
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), SKIN, 'hand.' + side, mat=MAT_SKIN)
    b.box((0.095, 0.08, 0.12), (-0.24, 0.0, 1.0), LEATHER, 'forearm.L', mat=MAT_LEATHER)  # bracer
    _head(b, detail, s)
    # linen coif + team hood with shoulder cape (chaperon) and a short liripipe at the back
    b.sphere(0.128, (0, -0.005, 1.66), LINEN, 'head', segs=s, rings=4, scale=(1, 1.0, 1.05), mat=MAT_CANVAS)
    b.sphere(0.14, (0, -0.02, 1.69), TEAM, 'head', segs=s, rings=4, scale=(1, 1.05, 0.95), mat=MAT_WOOL)
    b.box((0.36, 0.26, 0.09), (0, -0.01, 1.52), TEAM, 'chest', taper=0.85, mat=MAT_WOOL)  # cape over the shoulders
    if detail:
        b.box((0.05, 0.12, 0.05), (0, -0.16, 1.73), TEAM, 'head', rot=(-30, 0, 0), mat=MAT_WOOL)
        b.box((0.11, 0.012, 0.11), (0, 0.13, 1.63), SKIN, 'head', mat=MAT_SKIN)
    # longbow in the left hand (taller than the man), light string
    hx, hz = 0.24, 0.89
    b.box((0.026, 0.04, 1.75), (-hx - 0.02, 0.0, hz + 0.02), YEW, 'hand.L', rot=(90, 0, 0), mat=MAT_WOOD)
    b.box((0.006, 1.66, 0.006), (-hx - 0.02, 0.0, hz + 0.1), FLETCH, 'hand.L', mat=MAT_PIPECLAY)
    if detail:
        b.box((0.034, 0.08, 0.05), (-hx - 0.02, 0.0, hz + 0.02), LEATHER_D, 'hand.L', mat=MAT_LEATHER)  # grip
    return b.to_object()

# ------------------------------------------------------------------ knight (rig = cavalry.BONES)
def knight(name, groups, detail):
    """c.1300 knight: mail with a team surcoat (light cross), flat-topped great helm with a team crest, heater shield
    (team, light chevron), lance with a team pennon; horse in a team caparison with a light hem band, steel chanfron."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    HORSE = hexc('6b4a30'); HORSE_D = hexc('2a1f18'); HOOF = hexc('26211d')
    b.box((0.46, 1.25, 0.5), (0, 0.02, 1.3), HORSE, 'body', taper=0.92, mat=MAT_HIDE)
    b.box((0.25, 0.32, 0.62), (0, 0.78, 1.62), HORSE, 'neck', rot=(-35, 0, 0), taper=0.75, mat=MAT_HIDE)
    b.box((0.2, 0.52, 0.22), (0, 1.12, 1.68), HORSE, 'head', rot=(-30, 0, 0), taper=0.8, mat=MAT_HIDE)
    b.box((0.07, 0.32, 0.34), (0, 0.72, 1.86), HORSE_D, 'neck', rot=(-35, 0, 0), mat=MAT_HAIR)
    b.box((0.12, 0.12, 0.56), (0, -0.73, 1.08), HORSE_D, 'tail', rot=(25, 0, 0), taper=0.55, mat=MAT_HAIR)
    for leg, x, y in (('fl', 0.17, 0.48), ('fr', -0.17, 0.48), ('bl', 0.17, -0.45), ('br', -0.17, -0.45)):
        b.box((0.13, 0.17, 0.5), (x, y, 0.88), HORSE, leg + '_up', taper=0.8, mat=MAT_HIDE)
        b.box((0.08, 0.09, 0.5), (x, y, 0.33), HORSE, leg + '_lo', mat=MAT_HIDE)
        b.box((0.1, 0.12, 0.08), (x, y + 0.01, 0.05), HOOF, leg + '_lo', mat=MAT_LEATHER)
    # caparison (team) draped to the knees, light hem band, crinet over the neck
    b.box((0.54, 1.32, 0.56), (0, 0.0, 1.16), TEAM, 'body', taper=0.96, mat=MAT_WOOL)
    b.box((0.548, 1.328, 0.07), (0, 0.0, 0.9), HERALD, 'body', mat=MAT_PIPECLAY)
    b.box((0.27, 0.34, 0.5), (0, 0.76, 1.6), TEAM, 'neck', rot=(-35, 0, 0), taper=0.8, mat=MAT_WOOL)
    b.box((0.22, 0.4, 0.17), (0, 1.1, 1.73), STEEL, 'head', rot=(-30, 0, 0), taper=0.85, mat=MAT_STEEL)  # chanfron
    if detail:
        _cross_y = 0.0
        for sx in (0.272, -0.272):  # light cross on each flank of the caparison
            b.box((0.012, 0.08, 0.4), (sx, -0.1, 1.2), HERALD, 'body', mat=MAT_PIPECLAY)
            b.box((0.012, 0.36, 0.08), (sx, -0.1, 1.27), HERALD, 'body', mat=MAT_PIPECLAY)
        b.box((0.47, 0.05, 0.07), (0, 0.66, 1.4), LEATHER_D, 'body', mat=MAT_LEATHER)   # peytral strap
        b.box((0.17, 0.05, 0.15), (0, 1.3, 1.6), LEATHER_D, 'head', rot=(-30, 0, 0), mat=MAT_LEATHER)  # noseband
    # war saddle with high cantle
    b.box((0.44, 0.42, 0.07), (0, -0.05, 1.58), LEATHER, 'body', mat=MAT_LEATHER)
    b.box((0.36, 0.06, 0.2), (0, -0.25, 1.68), WOOD_D, 'body', mat=MAT_WOOD)
    # rider legs: mail chausses, steel poleyns, prick spurs
    for x in (0.2, -0.2):
        b.box((0.12, 0.38, 0.13), (x, 0.08, 1.6), MAIL, 'body', mat=MAT_MAIL)
        b.box((0.11, 0.12, 0.4), (x, 0.24, 1.37), MAIL, 'body', mat=MAT_MAIL)
        b.box((0.13, 0.08, 0.1), (x, 0.28, 1.6), STEEL, 'body', mat=MAT_STEEL)
        b.box((0.12, 0.2, 0.07), (x, 0.28, 1.16), LEATHER_D, 'body', mat=MAT_LEATHER)
    # torso: mail under a team surcoat (light cross front + back), skirt over the saddle
    b.box((0.34, 0.2, 0.4), (0, -0.05, 1.8), MAIL, 'r_spine', taper=1.1, mat=MAT_MAIL)
    b.box((0.37, 0.23, 0.38), (0, -0.05, 1.79), TEAM, 'r_spine', taper=1.08, mat=MAT_WOOL)
    b.box((0.44, 0.3, 0.14), (0, -0.05, 1.62), TEAM, 'r_spine', taper=1.05, mat=MAT_WOOL)
    b.box((0.06, 0.012, 0.34), (0, 0.072, 1.8), HERALD, 'r_spine', mat=MAT_PIPECLAY)
    b.box((0.06, 0.012, 0.34), (0, -0.172, 1.8), HERALD, 'r_spine', mat=MAT_PIPECLAY)
    b.box((0.3, 0.012, 0.06), (0, -0.172, 1.86), HERALD, 'r_spine', mat=MAT_PIPECLAY)
    b.box((0.3, 0.012, 0.06), (0, 0.072, 1.86), HERALD, 'r_spine', mat=MAT_PIPECLAY)
    b.box((0.38, 0.24, 0.04), (0, -0.05, 1.69), LEATHER_D, 'r_spine', mat=MAT_LEATHER)  # sword belt
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.1, 0.11, 0.3), (x, -0.05, 1.8), MAIL, 'r_arm.' + side, mat=MAT_MAIL)
        b.box((0.09, 0.1, 0.26), (x, -0.05, 1.54), MAIL, 'r_fore.' + side, mat=MAT_MAIL)
        b.box((0.085, 0.095, 0.09), (x, -0.05, 1.38), MAIL, 'r_fore.' + side, mat=MAT_MAIL)
        if detail:
            b.sphere(0.07, (x, -0.05, 1.92), STEEL, 'r_arm.' + side, segs=6, rings=3, mat=MAT_STEEL)  # ailette-ish couter
    if detail:
        b.box((0.025, 0.05, 0.7), (-0.25, 0.0, 1.32), LEATHER_D, 'body', rot=(55, 0, 0), mat=MAT_LEATHER)  # scabbard
    b.box((0.09, 0.09, 0.05), (0, -0.05, 2.0), MAIL, 'r_head', mat=MAT_MAIL)
    b.sphere(0.115, (0, -0.04, 2.11), SKIN, 'r_head', segs=s, rings=4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    # flat-topped great helm, dark eye slit, team crest (fan) on top
    b.cyl(0.138, 0.132, 0.28, (0, -0.04, 2.13), STEEL, 'r_head', segs=s, mat=MAT_STEEL)
    b.box((0.18, 0.02, 0.025), (0, 0.095, 2.17), IRON, 'r_head', mat=MAT_IRON)
    b.box((0.03, 0.2, 0.12), (0, -0.04, 2.33), TEAM, 'r_head', mat=MAT_WOOL)
    if detail:
        b.box((0.02, 0.02, 0.22), (0, 0.098, 2.08), BRASS, 'r_head', mat=MAT_BRASS)   # brass cross reinforce
        b.box((0.12, 0.02, 0.02), (0, 0.098, 2.12), BRASS, 'r_head', mat=MAT_BRASS)
    # lance (ash) with team pennon below the head
    hx, hz = 0.2, 1.38
    b.cyl(0.026, 0.02, 3.2, (hx + 0.04, -0.05, hz - 1.0), ASH, 'r_fore.R', segs=5, mat=MAT_WOOD)
    b.cyl(0.05, 0.0, 0.25, (hx + 0.04, -0.05, hz - 2.7), STEEL, 'r_fore.R', rot=(180, 0, 0), segs=4, mat=MAT_STEEL)
    b.box((0.012, 0.3, 0.2), (hx + 0.04, -0.2, hz - 2.4), TEAM, 'r_fore.R', taper=0.2, rot=(0, 0, 0), mat=MAT_WOOL)
    b.cyl(0.04, 0.03, 0.12, (hx + 0.04, -0.05, hz - 0.15), IRON, 'r_fore.R', segs=5, mat=MAT_IRON)  # vamplate
    # heater shield: team, light chevron
    b.box((0.42, 0.04, 0.5), (-0.27, 0.05, 1.6), TEAM, 'r_fore.L', taper=0.8, mat=MAT_WOOD)
    b.box((0.06, 0.046, 0.34), (-0.18, 0.05, 1.6), HERALD, 'r_fore.L', rot=(0, 40, 0), mat=MAT_PIPECLAY)
    b.box((0.06, 0.046, 0.34), (-0.36, 0.05, 1.6), HERALD, 'r_fore.L', rot=(0, -40, 0), mat=MAT_PIPECLAY)
    return b.to_object()

# ------------------------------------------------------------------ bombard (props.py conventions, groups body / recoil)
def bombard(groups):
    b = MeshBuilder('art_bombard', groups)
    OAK = hexc('7a5634'); OAK_D = hexc('553a22')
    # timber bed (sledge) with side cheeks and a rear block, staked
    b.box((0.9, 2.2, 0.3), (0, -0.2, 0.22), OAK, 'body', mat=MAT_WOOD)
    for x in (0.4, -0.4):
        b.box((0.12, 2.0, 0.34), (x, -0.15, 0.52), OAK_D, 'body', mat=MAT_WOOD)
    b.box((0.15, 0.4, 0.5), (0, -1.1, 0.35), OAK_D, 'body', mat=MAT_WOOD)
    for x, y in ((0.52, 0.8), (-0.52, 0.8), (0.52, -1.0), (-0.52, -1.0)):
        b.box((0.08, 0.08, 0.5), (x, y, 0.2), OAK_D, 'body', mat=MAT_WOOD)
    # wrought-iron barrel: hooped staves (recoil group), dark bore, rope lashings (light)
    b.cyl(0.36, 0.42, 1.7, (0, 0.2, 0.75), IRON, 'recoil', rot=(-90, 0, 0), segs=12, mat=MAT_IRON)
    for y in (-0.5, -0.15, 0.2, 0.55, 0.95):
        b.cyl(0.45, 0.45, 0.08, (0, y, 0.75), hexc('5a5e64'), 'recoil', rot=(-90, 0, 0), segs=12, mat=MAT_STEEL)
    b.cyl(0.24, 0.24, 0.02, (0, 1.06, 0.75), hexc('121010'), 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_IRON)
    b.cyl(0.3, 0.3, 0.4, (0, -0.85, 0.72), IRON, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_IRON)  # powder chamber
    for y in (-0.3, 0.75):
        b.box((0.96, 0.06, 0.05), (0, y, 0.5), LINEN, 'body', mat=MAT_CANVAS)
    # mantlet (wooden pavise screen) painted in team colour with a light band (reads from behind)
    b.box((1.0, 0.1, 0.5), (0, -1.0, 0.55), TEAM, 'body', mat=MAT_WOOD)
    b.box((1.02, 0.11, 0.08), (0, -1.0, 0.62), HERALD, 'body', mat=MAT_PIPECLAY)
    # stone shot pile + rammer
    for i, (x, y) in enumerate(((0.75, -0.6), (0.85, -0.85), (0.7, -0.9))):
        b.sphere(0.13, (x, y, 0.13), hexc('a29c90'), 'body', segs=6, rings=4, mat=MAT_WOOD)
    b.cyl(0.02, 0.02, 2.0, (-0.75, -0.3, 0.04), OAK, 'body', rot=(-90, 0, 0), segs=4, mat=MAT_WOOD)
    return b
