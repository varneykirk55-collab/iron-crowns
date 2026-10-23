"""Visual pass (c19 / Napoleonic era): detailed kit for c19_line infantry, c19_hussar cavalry and the c19 field gun (art_field_gun_c19.glb).
Same rig, bone names, proportions and silhouettes as the generic builders in soldiers.py / cavalry.py / props.py;
adds kit detail + per-part material class (common.MAT_*, exported in UVMap.v) for metal / leather / fabric shading.
LOD1 (detail=False, > 75 m) keeps only the parts that read at battle distance."""
import math
from common import hexc, MeshBuilder, MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_BRASS, MAT_SKIN, MAT_WOOD, MAT_PIPECLAY, MAT_HIDE, MAT_FUR, MAT_IRON, MAT_HAIR

TEAM = (1, 1, 1, 1.0)           # full team tint (coat / dolman)
TEAM_FACING = (0.5, 0.5, 0.5, 1.0)  # darker team shade for collar / cuffs / pelisse
# readability pass: KNAPSACK was 6a4a30, FELT 1b1b20, WOOL_WHITE dcd6c6 (read as black blobs from behind at battle distance)
SKIN = hexc('d9a988'); HAIR = hexc('3a2a1e')
WOOL_WHITE = hexc('e8e4d8'); PIPECLAY = hexc('efede6'); BLACK_LEATHER = hexc('1e1a18'); FELT = hexc('2a2a31')
BRASS = hexc('c09a45'); GOLD_LACE = hexc('d6b45c'); STEEL = hexc('aab1b8'); IRON = hexc('3a3d42')
WALNUT = hexc('6b4426'); KNAPSACK = hexc('8e6e4c'); BLANKET = hexc('8a8d90'); SHEEPSKIN = hexc('e4ded2')

# ------------------------------------------------------------------ infantry (rig = soldiers.BONES)
def line_infantry(name, groups, detail):
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    # legs: white trousers, black gaiters + shoes
    for side, x in (('R', 0.09), ('L', -0.09)):
        b.box((0.13, 0.15, 0.44), (x, 0, 0.74), WOOL_WHITE, 'thigh.' + side, taper=1.1, mat=MAT_WOOL)
        b.box((0.11, 0.13, 0.17), (x, 0, 0.405), WOOL_WHITE, 'shin.' + side, taper=1.1, mat=MAT_WOOL)
        b.box((0.118, 0.138, 0.17), (x, 0, 0.165), BLACK_LEATHER, 'shin.' + side, taper=1.08, mat=MAT_LEATHER)  # short gaiters (were 0.24 tall)
        b.box((0.11, 0.24, 0.09), (x, 0.04, 0.05), BLACK_LEATHER, 'shin.' + side, mat=MAT_LEATHER)
    # torso: short-tailed coatee (team colour)
    b.box((0.34, 0.2, 0.24), (0, 0, 1.1), TEAM, 'spine', taper=1.12, mat=MAT_WOOL)
    b.box((0.4, 0.23, 0.26), (0, 0, 1.36), TEAM, 'chest', taper=1.05, mat=MAT_WOOL)
    b.box((0.2, 0.17, 0.07), (0, 0, 1.5), TEAM_FACING, 'chest', mat=MAT_WOOL)  # standing collar
    # coat tails at the back, over the seat
    b.box((0.3, 0.045, 0.26), (0, -0.105, 0.88), TEAM, 'hips', taper=1.15, mat=MAT_WOOL)
    # pipeclayed crossbelts (read at distance -> both LODs)
    b.box((0.065, 0.245, 0.52), (0.0, 0.0, 1.25), PIPECLAY, 'chest', rot=(0, 30, 0), mat=MAT_PIPECLAY)
    b.box((0.065, 0.245, 0.52), (0.0, 0.0, 1.25), PIPECLAY, 'chest', rot=(0, -30, 0), mat=MAT_PIPECLAY)
    # knapsack: smaller + lower than before so the back still reads team colour; white pipeclay straps over it
    # (cameras mostly see the line from behind -> the white X / straps must read from the back too)
    b.box((0.26, 0.1, 0.22), (0, -0.165, 1.24), KNAPSACK, 'chest', mat=MAT_LEATHER)
    for x in (0.085, -0.085):
        b.box((0.045, 0.02, 0.4), (x, -0.222, 1.3), PIPECLAY, 'chest', mat=MAT_PIPECLAY)   # knapsack shoulder straps
    b.box((0.26, 0.02, 0.035), (0, -0.222, 1.42), PIPECLAY, 'chest', mat=MAT_PIPECLAY)      # breast/cross strap
    if detail:
        b.box((0.06, 0.02, 0.06), (0, 0.126, 1.27), BRASS, 'chest', mat=MAT_BRASS)          # belt plate
        b.box((0.08, 0.046, 0.22), (0, -0.112, 0.89), PIPECLAY, 'hips', mat=MAT_PIPECLAY)     # turnbacks
        b.cyl(0.055, 0.055, 0.34, (0, -0.17, 1.5), BLANKET, 'chest', rot=(0, 90, 0), segs=6, mat=MAT_WOOL)  # rolled greatcoat
        b.box((0.16, 0.075, 0.11), (0.12, -0.14, 1.0), BLACK_LEATHER, 'hips', mat=MAT_LEATHER)   # cartridge box
        b.box((0.035, 0.05, 0.3), (-0.18, -0.07, 0.84), BLACK_LEATHER, 'hips', rot=(18, 0, 0), mat=MAT_LEATHER)  # bayonet scabbard
        for x in (0.2, -0.2):
            b.box((0.1, 0.13, 0.03), (x, 0, 1.49), PIPECLAY, 'chest', mat=MAT_PIPECLAY)       # shoulder straps
    # arms
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.1, 0.11, 0.3), (x, 0, 1.31), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), TEAM, 'forearm.' + side, taper=0.9, mat=MAT_WOOL)
        if detail:
            b.box((0.096, 0.106, 0.06), (x, 0, 0.965), TEAM_FACING, 'forearm.' + side, mat=MAT_WOOL)  # cuffs
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), SKIN, 'hand.' + side, mat=MAT_SKIN)
    # head
    b.box((0.09, 0.09, 0.06), (0, 0, 1.52), SKIN, 'head', mat=MAT_SKIN)
    b.sphere(0.115, (0, 0.01, 1.64), SKIN, 'head', segs=s, rings=5 if detail else 4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    if detail:
        b.box((0.2, 0.07, 0.1), (0, -0.075, 1.63), HAIR, 'head', mat=MAT_HAIR)
    # stovepipe / Belgic shako: felt body, leather visor + top band, brass plate, cords, team pompom
    b.cyl(0.118, 0.13, 0.2, (0, 0.01, 1.8), FELT, 'head', segs=s, mat=MAT_WOOL)
    b.box((0.17, 0.06, 0.02), (0, 0.125, 1.71), BLACK_LEATHER, 'head', rot=(-12, 0, 0), mat=MAT_LEATHER)
    if detail:
        b.cyl(0.133, 0.133, 0.03, (0, 0.01, 1.885), BLACK_LEATHER, 'head', segs=s, mat=MAT_LEATHER)
        b.box((0.08, 0.016, 0.09), (0, 0.133, 1.79), BRASS, 'head', rot=(-3, 0, 0), mat=MAT_BRASS)
        b.box((0.2, 0.02, 0.018), (0, 0.125, 1.735), PIPECLAY, 'head', rot=(0, 0, 4), mat=MAT_PIPECLAY)
        b.cyl(0.024, 0.03, 0.07, (0, 0.11, 1.93), TEAM, 'head', segs=6, mat=MAT_WOOL)
    # .75 musket ("Brown Bess" pattern): walnut stock, steel barrel/lock, socket bayonet, white sling
    hx, hz = 0.24, 0.89
    gx = hx  # weapon modelled hanging along the arm from the hand (see rig notes in soldiers.py)
    b.box((0.05, 0.1, 0.17), (gx, 0.02, hz + 0.2), WALNUT, 'hand.R', mat=MAT_WOOD)        # butt
    b.box((0.042, 0.06, 0.3), (gx, 0.02, hz - 0.0), WALNUT, 'hand.R', mat=MAT_WOOD)       # wrist / lock area
    b.box((0.036, 0.046, 0.72), (gx, 0.025, hz - 0.5), WALNUT, 'hand.R', mat=MAT_WOOD)    # fore-stock
    b.cyl(0.014, 0.014, 1.12, (gx, 0.045, hz - 0.59), STEEL, 'hand.R', segs=4 if not detail else 6, mat=MAT_STEEL)  # barrel
    b.cyl(0.011, 0.0, 0.42, (gx + 0.02, 0.045, hz - 1.15 - 0.21), STEEL, 'hand.R', rot=(180, 0, 0), segs=3, mat=MAT_STEEL)  # bayonet
    if detail:
        b.box((0.016, 0.05, 0.07), (gx + 0.026, 0.03, hz + 0.02), STEEL, 'hand.R', mat=MAT_STEEL)  # lock
        b.box((0.054, 0.104, 0.02), (gx, 0.02, hz + 0.29), BRASS, 'hand.R', mat=MAT_BRASS)       # butt plate
        b.box((0.008, 0.012, 0.66), (gx, -0.012, hz - 0.42), PIPECLAY, 'hand.R', mat=MAT_PIPECLAY)  # sling
    return b.to_object()

# ------------------------------------------------------------------ hussar (rig = cavalry.BONES)
def hussar(name, groups, detail):
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    HORSE = hexc('6b4a30'); HORSE_D = hexc('2a1f18'); HOOF = hexc('26211d')
    # horse (unchanged proportions); hide colour is varied per instance in the shader (MAT_HIDE)
    b.box((0.46, 1.25, 0.5), (0, 0.02, 1.3), HORSE, 'body', taper=0.92, mat=MAT_HIDE)
    b.box((0.25, 0.32, 0.62), (0, 0.78, 1.62), HORSE, 'neck', rot=(-35, 0, 0), taper=0.75, mat=MAT_HIDE)
    b.box((0.2, 0.52, 0.22), (0, 1.12, 1.68), HORSE, 'head', rot=(-30, 0, 0), taper=0.8, mat=MAT_HIDE)
    b.box((0.07, 0.32, 0.34), (0, 0.72, 1.86), HORSE_D, 'neck', rot=(-35, 0, 0), mat=MAT_HAIR)  # mane
    b.box((0.12, 0.12, 0.56), (0, -0.73, 1.08), HORSE_D, 'tail', rot=(25, 0, 0), taper=0.55, mat=MAT_HAIR)
    for leg, x, y in (('fl', 0.17, 0.48), ('fr', -0.17, 0.48), ('bl', 0.17, -0.45), ('br', -0.17, -0.45)):
        b.box((0.13, 0.17, 0.5), (x, y, 0.88), HORSE, leg + '_up', taper=0.8, mat=MAT_HIDE)
        b.box((0.08, 0.09, 0.5), (x, y, 0.33), HORSE, leg + '_lo', mat=MAT_HIDE)
        b.box((0.1, 0.12, 0.08), (x, y + 0.01, 0.05), HOOF, leg + '_lo', mat=MAT_LEATHER)
    # shabraque (team saddle cloth) with lace edge, sheepskin over the saddle
    b.box((0.5, 0.7, 0.3), (0, -0.12, 1.43), TEAM_FACING, 'body', mat=MAT_WOOL)
    b.box((0.4, 0.46, 0.06), (0, -0.05, 1.58), SHEEPSKIN, 'body', mat=MAT_FUR)
    if detail:
        b.box((0.506, 0.706, 0.04), (0, -0.12, 1.29), GOLD_LACE, 'body', mat=MAT_BRASS)          # lace edge
        b.box((0.5, 0.28, 0.24), (0, -0.55, 1.42), TEAM_FACING, 'body', taper=0.4, rot=(12, 0, 0), mat=MAT_WOOL)  # pointed rear
        b.box((0.47, 0.05, 0.07), (0, 0.66, 1.38), BLACK_LEATHER, 'body', mat=MAT_LEATHER)        # breast strap
        b.box((0.212, 0.06, 0.2), (0, 1.0, 1.77), BLACK_LEATHER, 'head', rot=(-30, 0, 0), mat=MAT_LEATHER)  # bridle crown
        b.box((0.17, 0.05, 0.15), (0, 1.3, 1.6), BLACK_LEATHER, 'head', rot=(-30, 0, 0), mat=MAT_LEATHER)   # noseband
    # rider legs (rigid to horse body): breeches + hessian boots
    for x in (0.2, -0.2):
        b.box((0.12, 0.38, 0.13), (x, 0.08, 1.6), TEAM_FACING, 'body', mat=MAT_WOOL)
        b.box((0.11, 0.12, 0.4), (x, 0.24, 1.37), BLACK_LEATHER, 'body', mat=MAT_LEATHER)
    if detail:
        b.box((0.02, 0.17, 0.23), (-0.27, -0.12, 1.4), TEAM_FACING, 'body', mat=MAT_WOOL)          # sabretache
        b.box((0.025, 0.05, 0.72), (-0.25, -0.02, 1.32), STEEL, 'body', rot=(55, 0, 0), mat=MAT_STEEL)  # scabbard
    # rider torso: dolman (team), gold frogging, barrel sash
    b.box((0.34, 0.2, 0.4), (0, -0.05, 1.8), TEAM, 'r_spine', taper=1.1, mat=MAT_WOOL)
    b.box((0.38, 0.23, 0.12), (0, -0.05, 1.65), hexc('d9c36a'), 'r_spine', mat=MAT_WOOL)  # sash
    # pelisse slung over the left shoulder, fur trimmed
    b.box((0.17, 0.26, 0.36), (-0.2, -0.08, 1.81), TEAM_FACING, 'r_spine', mat=MAT_WOOL)
    if detail:
        b.box((0.18, 0.27, 0.05), (-0.2, -0.08, 1.63), hexc('2a2522'), 'r_spine', mat=MAT_FUR)
        for z in (1.78, 1.85, 1.92):
            b.box((0.22, 0.02, 0.016), (0.02, 0.06 - (z - 1.78) * 0.12, z), GOLD_LACE, 'r_spine', mat=MAT_BRASS)
        b.box((0.39, 0.235, 0.025), (0, -0.05, 1.67), TEAM, 'r_spine', mat=MAT_WOOL)  # sash stripe (team)
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.1, 0.11, 0.3), (x, -0.05, 1.8), TEAM, 'r_arm.' + side, mat=MAT_WOOL)
        b.box((0.09, 0.1, 0.26), (x, -0.05, 1.54), TEAM, 'r_fore.' + side, mat=MAT_WOOL)
        b.box((0.08, 0.09, 0.09), (x, -0.05, 1.38), SKIN, 'r_fore.' + side, mat=MAT_SKIN)
    b.box((0.09, 0.09, 0.05), (0, -0.05, 2.0), SKIN, 'r_head', mat=MAT_SKIN)
    b.sphere(0.115, (0, -0.04, 2.11), SKIN, 'r_head', segs=s, rings=4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    # shako with tall plume
    b.cyl(0.115, 0.13, 0.22, (0, -0.04, 2.27), FELT, 'r_head', segs=s, mat=MAT_WOOL)
    b.cyl(0.035, 0.02, 0.2, (0, 0.04, 2.47), hexc('efeee8'), 'r_head', segs=5, mat=MAT_FUR)
    if detail:
        b.box((0.16, 0.06, 0.02), (0, 0.08, 2.17), BLACK_LEATHER, 'r_head', rot=(-12, 0, 0), mat=MAT_LEATHER)
        b.box((0.2, 0.02, 0.018), (0, 0.075, 2.22), GOLD_LACE, 'r_head', rot=(0, 0, -5), mat=MAT_BRASS)   # cords
        b.box((0.06, 0.016, 0.06), (0, 0.085, 2.29), BRASS, 'r_head', mat=MAT_BRASS)                       # cockade/plate
    # light cavalry sabre
    hx, hz = 0.2, 1.38
    b.box((0.02, 0.05, 0.85), (hx + 0.04, -0.05, hz - 0.45), STEEL, 'r_fore.R', mat=MAT_STEEL)
    b.box((0.12, 0.06, 0.03), (hx + 0.04, -0.05, hz - 0.02), BRASS, 'r_fore.R', mat=MAT_BRASS)
    return b.to_object()

# ------------------------------------------------------------------ field gun (props.py conventions, groups body / recoil)
def field_gun(groups):
    b = MeshBuilder('art_field_gun_c19', groups)  # own asset: art_cannon stays legacy for early_modern culverins
    PAINT = (0.6, 0.62, 0.58, 0.5)  # carriage paint, half team tinted (French olive / British grey-blue feel per side)
    WOOD_D = hexc('4a3220')
    # split-trail carriage: two cheeks joined at the trail, axle-tree, trail transom
    for x in (0.17, -0.17):
        b.box((0.07, 2.5, 0.26), (x * 0.8, -0.88, 0.5), PAINT, 'body', rot=(10, 0, -3 if x > 0 else 3), mat=MAT_WOOD)  # slopes down to the trail
    b.box((0.3, 0.5, 0.14), (0, -1.6, 0.37), PAINT, 'body', rot=(10, 0, 0), mat=MAT_WOOD)
    b.box((0.98, 0.14, 0.14), (0, 0.2, 0.65), PAINT, 'body', mat=MAT_WOOD)
    b.cyl(0.04, 0.04, 1.08, (0, 0.2, 0.65), IRON, 'body', rot=(0, 90, 0), segs=6, mat=MAT_IRON)
    b.box((0.3, 0.3, 0.2), (0, -2.2, 0.2), TEAM, 'body', mat=MAT_WOOD)  # team-painted trail end (kept)
    b.box((0.12, 0.12, 0.04), (0, -2.33, 0.31), IRON, 'body', mat=MAT_IRON)  # lunette
    b.box((0.05, 0.05, 1.0), (0.12, -2.05, 0.65), WALNUT, 'body', rot=(-28, 0, 0), mat=MAT_WOOD)  # handspike
    b.box((0.1, 0.12, 0.1), (0, -0.35, 0.78), IRON, 'body', mat=MAT_IRON)  # elevating screw
    # rammer / sponge lying beside the trail
    b.cyl(0.02, 0.02, 2.0, (0.55, -1.0, 0.04), WALNUT, 'body', rot=(-90, 0, 0), segs=4, mat=MAT_WOOD)
    b.cyl(0.06, 0.06, 0.2, (0.55, 0.05, 0.06), hexc('2a2622'), 'body', rot=(-90, 0, 0), segs=6, mat=MAT_FUR)
    # spoked wheels with iron tyres
    for wx in (0.48, -0.48):
        wheel(b, wx, 0.2, 0.65, 0.65, 0.08, WOOD_D)
    # bronze barrel: breech, reinforce rings, chase, muzzle swell, cascabel, trunnions (recoil group)
    BZ = BRASS
    b.cyl(0.17, 0.155, 0.55, (0, -0.05, 0.95), BZ, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    b.cyl(0.14, 0.115, 1.25, (0, 0.85, 0.95), BZ, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    b.cyl(0.14, 0.14, 0.12, (0, 1.5, 0.95), BZ, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    for y in (-0.32, 0.22):
        b.cyl(0.185, 0.185, 0.06, (0, y, 0.95), BZ, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    b.cyl(0.11, 0.08, 0.1, (0, -0.38, 0.95), BZ, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_BRASS)
    b.sphere(0.06, (0, -0.47, 0.95), BZ, 'recoil', segs=6, rings=4, mat=MAT_BRASS)
    b.cyl(0.05, 0.05, 0.46, (0, 0.2, 0.95), BZ, 'recoil', rot=(0, 90, 0), segs=6, mat=MAT_BRASS)
    b.cyl(0.07, 0.07, 0.02, (0, 1.565, 0.95), hexc('15120f'), 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_IRON)  # bore
    return b

def wheel(b, x, y, z, r, w, col):
    n = 10
    seg = 2 * r * math.sin(math.pi / n) * 1.04
    for i in range(n):
        a = 360.0 * i / n
        ar = math.radians(a)
        cy, cz = y + math.cos(ar) * (r - 0.05), z + math.sin(ar) * (r - 0.05)
        b.box((w, seg, 0.1), (x, cy, cz), col, 'body', rot=(a + 90, 0, 0), mat=MAT_WOOD)
        ty, tz = y + math.cos(ar) * (r - 0.004), z + math.sin(ar) * (r - 0.004)
        b.box((w * 0.9, seg, 0.018), (x, ty, tz), IRON, 'body', rot=(a + 90, 0, 0), mat=MAT_IRON)
    for i in range(6):
        a = 180.0 * i / 6 + 15
        b.box((w * 0.5, 0.04, 2 * (r - 0.08)), (x, y, z), col, 'body', rot=(a, 0, 0), mat=MAT_WOOD)
    b.cyl(0.11, 0.11, w * 1.8, (x, y, z), col, 'body', rot=(0, 90, 0), segs=8, mat=MAT_WOOD)
    b.cyl(0.05, 0.05, w * 2.4, (x, y, z), IRON, 'body', rot=(0, 90, 0), segs=6, mat=MAT_IRON)
