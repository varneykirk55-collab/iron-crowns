"""Visual pass (early-modern era, c.1500-1650 'pike and shot'): detailed kit for em_pike / em_musket infantry,
em_cuirassier cavalry and the early-modern culverin (art_culverin_em.glb, swapped in for art_cannon by battle_visuals.gd
because art_cannon is shared with the legacy look). Same rig, bone names, proportions and silhouettes as the generic
builders (template: c19_kit.py / med_kit.py). Readability rules (c19 review): team colour on large front AND back areas,
light accents (falling-band collars, stockings, plumes, flasks) that read at distance, no dark masses on the back,
contact AO only at the feet (shader). LOD1 (detail=False, > 75 m) keeps only what reads."""
from common import (hexc, MeshBuilder, MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_BRASS, MAT_SKIN, MAT_WOOD, MAT_PIPECLAY,
                    MAT_HIDE, MAT_FUR, MAT_IRON, MAT_HAIR, MAT_CANVAS)

TEAM = (1, 1, 1, 1.0)
SKIN = hexc('d9a988'); HAIR = hexc('4a3424')
STEEL = hexc('b8bfc6'); IRON = hexc('3a3d42'); BRASS = hexc('c09a45'); BRONZE = hexc('b08a48')
LINEN = hexc('ece4cf'); COLLAR = hexc('f3efe4'); STOCKING = hexc('e2dccd')
BUFF = hexc('c8a678'); LEATHER = hexc('7a5638'); LEATHER_D = hexc('3e2c1e'); SHOE = hexc('3a2a1e')
FELT = hexc('7a6a56'); ASH = hexc('9a7a52'); WALNUT = hexc('6b4426'); WOOD_D = hexc('5a3e26'); FLASK = hexc('d8c7a2')

def _legs(b, detail):
    """team slashed breeches to the knee, light stockings (reads like the c19 white trousers), garters, shoes."""
    for side, x in (('R', 0.09), ('L', -0.09)):
        b.box((0.145, 0.165, 0.38), (x, 0, 0.77), TEAM, 'thigh.' + side, taper=1.15, mat=MAT_WOOL)
        b.box((0.105, 0.125, 0.4), (x, 0, 0.3), STOCKING, 'shin.' + side, taper=1.12, mat=MAT_CANVAS)
        b.box((0.11, 0.24, 0.09), (x, 0.04, 0.05), SHOE, 'shin.' + side, mat=MAT_LEATHER)
        if detail:
            b.box((0.12, 0.14, 0.04), (x, 0, 0.5), TEAM, 'shin.' + side, mat=MAT_WOOL)  # garter ribbon
            b.box((0.06, 0.02, 0.04), (x, 0.13, 0.06), BRASS, 'shin.' + side, mat=MAT_BRASS)  # shoe buckle/rose

def _head(b, detail, s):
    b.box((0.09, 0.09, 0.06), (0, 0, 1.52), SKIN, 'head', mat=MAT_SKIN)
    b.sphere(0.115, (0, 0.01, 1.64), SKIN, 'head', segs=s, rings=5 if detail else 4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    if detail:
        b.box((0.2, 0.07, 0.1), (0, -0.075, 1.6), HAIR, 'head', mat=MAT_HAIR)
        b.box((0.05, 0.03, 0.06), (0, 0.11, 1.55), HAIR, 'head', mat=MAT_HAIR)  # beard

def _collar(b):
    """falling-band linen collar: light at the neck on both sides (front + back)."""
    b.box((0.34, 0.25, 0.04), (0, 0, 1.495), COLLAR, 'chest', taper=0.9, mat=MAT_PIPECLAY)

def _doublet(b, detail):
    b.box((0.34, 0.2, 0.24), (0, 0, 1.1), TEAM, 'spine', taper=1.12, mat=MAT_WOOL)
    b.box((0.4, 0.23, 0.26), (0, 0, 1.36), TEAM, 'chest', taper=1.05, mat=MAT_WOOL)
    b.box((0.37, 0.22, 0.12), (0, 0, 0.93), TEAM, 'hips', taper=1.1, mat=MAT_WOOL)  # skirts
    _collar(b)

# ------------------------------------------------------------------ infantry (rig = soldiers.BONES)
def pikeman(name, groups, detail):
    """pikeman c.1620: team doublet + breeches, steel breastplate with tassets (front only: the back stays team),
    light falling collar + stockings, crested morion with a light plume, 16 ft ash pike, short sword."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    _legs(b, detail)
    _doublet(b, detail)
    # corselet: breastplate (front, with a centre ridge), backplate kept narrow so the team doublet still reads behind
    b.box((0.38, 0.06, 0.34), (0, 0.105, 1.3), STEEL, 'chest', taper=1.08, mat=MAT_STEEL)
    b.box((0.18, 0.04, 0.24), (0, -0.115, 1.33), STEEL, 'chest', mat=MAT_STEEL)  # narrow backplate (centre)
    for x in (0.1, -0.1):
        b.box((0.16, 0.05, 0.22), (x, 0.11, 0.86), STEEL, 'hips', taper=1.1, mat=MAT_STEEL)  # tassets over the thighs
    b.box((0.38, 0.235, 0.04), (0, 0, 1.12), LEATHER_D, 'spine', mat=MAT_LEATHER)  # waist belt
    if detail:
        b.box((0.02, 0.014, 0.3), (0, 0.137, 1.3), hexc('dde2e6'), 'chest', mat=MAT_STEEL)  # breastplate ridge
        b.box((0.04, 0.05, 0.36), (-0.2, 0.0, 0.84), LEATHER_D, 'hips', rot=(12, 0, 0), mat=MAT_LEATHER)  # sword
        b.box((0.1, 0.03, 0.02), (-0.2, 0.03, 1.02), STEEL, 'hips', mat=MAT_STEEL)
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.11, 0.12, 0.3), (x, 0, 1.31), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), TEAM, 'forearm.' + side, taper=0.9, mat=MAT_WOOL)
        b.box((0.1, 0.11, 0.05), (x, 0, 0.955), COLLAR, 'forearm.' + side, mat=MAT_PIPECLAY)  # linen cuffs
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), SKIN, 'hand.' + side, mat=MAT_SKIN)
        if detail:
            b.box((0.13, 0.14, 0.1), (x, 0, 1.44), STEEL, 'upper_arm.' + side, mat=MAT_STEEL)  # pauldron lames
    _head(b, detail, s)
    # morion: domed crown with a tall comb, upswept brim (steel), light plume at the back
    b.sphere(0.13, (0, 0.0, 1.73), STEEL, 'head', segs=s, rings=4, scale=(0.95, 1.1, 0.8), mat=MAT_STEEL)
    b.box((0.03, 0.26, 0.11), (0, 0.0, 1.83), STEEL, 'head', mat=MAT_STEEL)  # comb
    b.box((0.34, 0.15, 0.02), (0, 0.0, 1.69), STEEL, 'head', taper=0.7, mat=MAT_STEEL)
    for y in (0.14, -0.14):
        b.box((0.13, 0.08, 0.02), (0, y, 1.72), STEEL, 'head', rot=(25 if y > 0 else -25, 0, 0), mat=MAT_STEEL)  # brim peaks
    b.cyl(0.03, 0.04, 0.16, (0.0, -0.09, 1.84), COLLAR, 'head', rot=(-30, 0, 0), segs=5, mat=MAT_FUR)
    # pike (long, hangs along the arm from hand.R; generic builder: L 3.8 at hx 0.24)
    hx, hz = 0.24, 0.89
    L = 3.8
    b.cyl(0.02, 0.018, L, (hx, 0, hz - L * 0.35), ASH, 'hand.R', segs=4 if not detail else 5, mat=MAT_WOOD)
    b.cyl(0.03, 0.0, 0.22, (hx, 0, hz - L * 0.85 - 0.11), STEEL, 'hand.R', rot=(180, 0, 0), segs=4, mat=MAT_STEEL)
    if detail:
        b.box((0.012, 0.012, 0.5), (hx + 0.022, 0, hz - L * 0.85 + 0.2), STEEL, 'hand.R', mat=MAT_STEEL)  # langets
    return b.to_object()

def musketeer(name, groups, detail):
    """musketeer c.1620: team coat + breeches, light falling collar + stockings, broad felt hat (mid tone, not black)
    with a team plume, buff bandolier with light powder flasks ('apostles'), matchlock musket, forked rest."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    _legs(b, detail)
    _doublet(b, detail)
    # bandolier over the left shoulder (front + back) with light flasks hanging at the front; powder bag at the hip
    b.box((0.06, 0.245, 0.52), (0.0, 0.0, 1.25), BUFF, 'chest', rot=(0, -32, 0), mat=MAT_LEATHER)
    n = 6 if detail else 4
    for i in range(n):
        t = (i + 0.5) / n
        x = -0.15 + 0.3 * t; z = 1.43 - 0.36 * t
        b.cyl(0.024, 0.024, 0.09, (x, 0.135, z - 0.06), FLASK, 'chest', segs=5, mat=MAT_PIPECLAY)
    b.box((0.36, 0.225, 0.04), (0, 0, 1.0), LEATHER_D, 'hips', mat=MAT_LEATHER)
    if detail:
        b.box((0.09, 0.06, 0.11), (0.16, 0.08, 0.9), LEATHER, 'hips', mat=MAT_LEATHER)  # bullet bag
        b.box((0.035, 0.05, 0.36), (-0.2, 0.0, 0.84), LEATHER_D, 'hips', rot=(12, 0, 0), mat=MAT_LEATHER)  # sword
        for z in (1.2, 1.3, 1.4):
            b.box((0.02, 0.012, 0.02), (0.03, 0.118, z), BRASS, 'chest', mat=MAT_BRASS)  # buttons
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.11, 0.12, 0.3), (x, 0, 1.31), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), TEAM, 'forearm.' + side, taper=0.9, mat=MAT_WOOL)
        b.box((0.1, 0.11, 0.05), (x, 0, 0.955), COLLAR, 'forearm.' + side, mat=MAT_PIPECLAY)
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), SKIN, 'hand.' + side, mat=MAT_SKIN)
    _head(b, detail, s)
    # broad-brimmed felt hat, crown + brim; brim turned up at one side; team plume
    b.cyl(0.25, 0.25, 0.025, (0, 0.0, 1.72), FELT, 'head', segs=s + 2, mat=MAT_WOOL)
    b.cyl(0.12, 0.13, 0.14, (0, 0.0, 1.8), FELT, 'head', segs=s, mat=MAT_WOOL)
    b.box((0.05, 0.22, 0.12), (-0.13, -0.02, 1.83), TEAM, 'head', rot=(0, 30, 0), taper=0.6, mat=MAT_FUR)  # plume
    if detail:
        b.cyl(0.134, 0.134, 0.03, (0, 0.0, 1.76), TEAM, 'head', segs=s, mat=MAT_WOOL)  # hat band
    # matchlock musket (long, hangs along the arm from hand.R) + light-wood forked rest in the left hand
    hx, hz = 0.24, 0.89
    b.box((0.055, 0.1, 0.2), (hx, 0.02, hz + 0.2), WALNUT, 'hand.R', mat=MAT_WOOD)      # butt
    b.box((0.045, 0.06, 0.82), (hx, 0.025, hz - 0.3), WALNUT, 'hand.R', mat=MAT_WOOD)   # stock
    b.cyl(0.016, 0.016, 1.3, (hx, 0.045, hz - 0.7), IRON, 'hand.R', segs=4 if not detail else 6, mat=MAT_IRON)  # barrel
    if detail:
        b.box((0.016, 0.05, 0.08), (hx + 0.028, 0.03, hz + 0.02), STEEL, 'hand.R', mat=MAT_STEEL)  # lock / serpentine
        b.box((0.008, 0.012, 0.6), (hx, -0.012, hz - 0.3), BUFF, 'hand.R', mat=MAT_LEATHER)          # sling
        b.cyl(0.012, 0.012, 1.3, (-hx, 0.0, hz - 0.5), ASH, 'hand.L', segs=4, mat=MAT_WOOD)        # musket rest
        b.box((0.1, 0.02, 0.02), (-hx, 0.0, hz + 0.14), IRON, 'hand.L', mat=MAT_IRON)
    return b.to_object()

# ------------------------------------------------------------------ cuirassier (rig = cavalry.BONES)
def cuirassier(name, groups, detail):
    """cuirassier c.1630: three-quarter armour (bright steel) over a team buff coat, wide team sash front + back,
    lobster-tail pot helmet with a light plume, team saddle cloth with a light hem; straight broadsword."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    HORSE = hexc('5a3e2a'); HORSE_D = hexc('2a1f18'); HOOF = hexc('26211d')
    b.box((0.46, 1.25, 0.5), (0, 0.02, 1.3), HORSE, 'body', taper=0.92, mat=MAT_HIDE)
    b.box((0.25, 0.32, 0.62), (0, 0.78, 1.62), HORSE, 'neck', rot=(-35, 0, 0), taper=0.75, mat=MAT_HIDE)
    b.box((0.2, 0.52, 0.22), (0, 1.12, 1.68), HORSE, 'head', rot=(-30, 0, 0), taper=0.8, mat=MAT_HIDE)
    b.box((0.07, 0.32, 0.34), (0, 0.72, 1.86), HORSE_D, 'neck', rot=(-35, 0, 0), mat=MAT_HAIR)
    b.box((0.12, 0.12, 0.56), (0, -0.73, 1.08), HORSE_D, 'tail', rot=(25, 0, 0), taper=0.55, mat=MAT_HAIR)
    for leg, x, y in (('fl', 0.17, 0.48), ('fr', -0.17, 0.48), ('bl', 0.17, -0.45), ('br', -0.17, -0.45)):
        b.box((0.13, 0.17, 0.5), (x, y, 0.88), HORSE, leg + '_up', taper=0.8, mat=MAT_HIDE)
        b.box((0.08, 0.09, 0.5), (x, y, 0.33), HORSE, leg + '_lo', mat=MAT_HIDE)
        b.box((0.1, 0.12, 0.08), (x, y + 0.01, 0.05), HOOF, leg + '_lo', mat=MAT_LEATHER)
    # team saddle cloth (large, both flanks) with a light hem; saddle; holsters
    b.box((0.52, 0.8, 0.36), (0, -0.1, 1.4), TEAM, 'body', mat=MAT_WOOL)
    b.box((0.526, 0.806, 0.05), (0, -0.1, 1.23), COLLAR, 'body', mat=MAT_PIPECLAY)
    b.box((0.42, 0.44, 0.07), (0, -0.05, 1.59), LEATHER, 'body', mat=MAT_LEATHER)
    if detail:
        for x in (0.2, -0.2):
            b.box((0.08, 0.1, 0.3), (x, 0.3, 1.5), LEATHER_D, 'body', rot=(-30, 0, 0), mat=MAT_LEATHER)  # pistol holsters
        b.box((0.47, 0.05, 0.07), (0, 0.66, 1.38), LEATHER_D, 'body', mat=MAT_LEATHER)
        b.box((0.212, 0.06, 0.2), (0, 1.0, 1.77), LEATHER_D, 'head', rot=(-30, 0, 0), mat=MAT_LEATHER)
        b.box((0.17, 0.05, 0.15), (0, 1.3, 1.6), LEATHER_D, 'head', rot=(-30, 0, 0), mat=MAT_LEATHER)
    # rider legs: steel tassets to the knee, buff-leather boots
    for x in (0.2, -0.2):
        b.box((0.13, 0.38, 0.13), (x, 0.08, 1.6), STEEL, 'body', mat=MAT_STEEL)
        b.box((0.12, 0.13, 0.4), (x, 0.24, 1.37), BUFF, 'body', mat=MAT_LEATHER)
        if detail:
            b.box((0.15, 0.1, 0.1), (x, 0.26, 1.58), BUFF, 'body', mat=MAT_LEATHER)  # boot tops
    # torso: team buff coat, cuirass, wide team sash diagonal front + back (reads team from behind too)
    b.box((0.34, 0.2, 0.4), (0, -0.05, 1.8), TEAM, 'r_spine', taper=1.1, mat=MAT_WOOL)
    b.box((0.36, 0.22, 0.3), (0, -0.05, 1.84), STEEL, 'r_spine', taper=1.08, mat=MAT_STEEL)
    b.box((0.4, 0.26, 0.09), (0, -0.05, 1.64), TEAM, 'r_spine', taper=1.05, mat=MAT_WOOL)   # coat skirts
    b.box((0.08, 0.25, 0.46), (0, -0.05, 1.82), TEAM, 'r_spine', rot=(0, 35, 0), mat=MAT_WOOL)  # sash
    b.box((0.2, 0.16, 0.03), (0, -0.05, 1.99), COLLAR, 'r_spine', mat=MAT_PIPECLAY)  # collar
    if detail:
        b.box((0.02, 0.012, 0.26), (0, 0.065, 1.84), hexc('dde2e6'), 'r_spine', mat=MAT_STEEL)
        b.box((0.025, 0.05, 0.75), (-0.25, -0.02, 1.32), LEATHER_D, 'body', rot=(55, 0, 0), mat=MAT_LEATHER)
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.13, 0.13, 0.14), (x, -0.05, 1.92), STEEL, 'r_arm.' + side, mat=MAT_STEEL)  # pauldron
        b.box((0.1, 0.11, 0.22), (x, -0.05, 1.76), TEAM, 'r_arm.' + side, mat=MAT_WOOL)
        b.box((0.095, 0.105, 0.26), (x, -0.05, 1.54), STEEL, 'r_fore.' + side, mat=MAT_STEEL)  # vambrace
        b.box((0.09, 0.1, 0.09), (x, -0.05, 1.38), BUFF, 'r_fore.' + side, mat=MAT_LEATHER)   # gauntlet
    b.box((0.09, 0.09, 0.05), (0, -0.05, 2.0), SKIN, 'r_head', mat=MAT_SKIN)
    b.sphere(0.115, (0, -0.04, 2.11), SKIN, 'r_head', segs=s, rings=4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    # lobster-tail pot: skull, peak, face bars, articulated neck guard, light plume
    b.sphere(0.13, (0, -0.04, 2.19), STEEL, 'r_head', segs=s, rings=4, scale=(1, 1.05, 0.85), mat=MAT_STEEL)
    b.box((0.2, 0.08, 0.02), (0, 0.1, 2.15), STEEL, 'r_head', rot=(-15, 0, 0), mat=MAT_STEEL)
    b.box((0.2, 0.08, 0.16), (0, -0.17, 2.05), STEEL, 'r_head', rot=(25, 0, 0), taper=1.2, mat=MAT_STEEL)  # lobster tail
    b.cyl(0.03, 0.04, 0.16, (0, -0.06, 2.32), COLLAR, 'r_head', rot=(-25, 0, 0), segs=5, mat=MAT_FUR)
    if detail:
        for x in (-0.04, 0.0, 0.04):
            b.box((0.012, 0.012, 0.14), (x, 0.13, 2.07), IRON, 'r_head', mat=MAT_IRON)  # face bars
    # straight broadsword
    hx, hz = 0.2, 1.38
    b.box((0.025, 0.05, 0.95), (hx + 0.04, -0.05, hz - 0.5), STEEL, 'r_fore.R', mat=MAT_STEEL)
    b.box((0.14, 0.06, 0.03), (hx + 0.04, -0.05, hz - 0.02), IRON, 'r_fore.R', mat=MAT_IRON)
    return b.to_object()

# ------------------------------------------------------------------ culverin (props.py conventions, groups body / recoil)
def culverin(groups, wheel):
    """long early-modern culverin on a two-wheeled block carriage; same footprint / groups as art_cannon."""
    b = MeshBuilder('art_culverin_em', groups)
    OAK = hexc('7a5634'); OAK_D = hexc('4a3220')
    for x in (0.16, -0.16):
        b.box((0.08, 2.6, 0.3), (x, -0.95, 0.5), OAK, 'body', rot=(-12, 0, 0), mat=MAT_WOOD)  # cheeks to the trail
    b.box((0.4, 0.4, 0.14), (0, -1.9, 0.27), OAK_D, 'body', rot=(-12, 0, 0), mat=MAT_WOOD)
    b.box((0.98, 0.14, 0.14), (0, 0.2, 0.65), OAK_D, 'body', mat=MAT_WOOD)
    b.cyl(0.04, 0.04, 1.08, (0, 0.2, 0.65), IRON, 'body', rot=(0, 90, 0), segs=6, mat=MAT_IRON)
    b.box((0.3, 0.3, 0.2), (0, -2.2, 0.2), TEAM, 'body', mat=MAT_WOOD)   # team trail end (as art_cannon)
    b.box((0.36, 0.9, 0.04), (0, -0.4, 0.82), TEAM, 'body', mat=MAT_WOOD)  # team-painted bed under the barrel
    b.box((0.38, 0.06, 0.06), (0, -0.4, 0.85), LINEN, 'body', mat=MAT_CANVAS)
    for wx in (0.42, -0.42):
        wheel(b, wx, 0.2, 0.65, 0.65, 0.09, OAK_D)
    # long bronze barrel with mouldings, dolphins (lifting handles), cascabel; recoil group
    b.cyl(0.15, 0.12, 0.7, (0, -0.15, 0.95), BRONZE, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    b.cyl(0.12, 0.095, 1.6, (0, 0.95, 0.95), BRONZE, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    for y in (-0.48, 0.2, 0.95):
        b.cyl(0.165, 0.165, 0.05, (0, y, 0.95), BRONZE, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    b.cyl(0.125, 0.125, 0.12, (0, 1.75, 0.95), BRONZE, 'recoil', rot=(-90, 0, 0), segs=10, mat=MAT_BRASS)
    b.sphere(0.06, (0, -0.56, 0.95), BRONZE, 'recoil', segs=6, rings=4, mat=MAT_BRASS)
    for x in (0.06, -0.06):
        b.box((0.03, 0.14, 0.06), (x, 0.15, 1.1), BRONZE, 'recoil', mat=MAT_BRASS)  # dolphins
    b.cyl(0.05, 0.05, 0.4, (0, 0.2, 0.95), BRONZE, 'recoil', rot=(0, 90, 0), segs=6, mat=MAT_BRASS)
    b.cyl(0.06, 0.06, 0.02, (0, 1.815, 0.95), hexc('15120f'), 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_IRON)
    # ladle / rammer and two light powder cartridges beside the trail, iron shot
    b.cyl(0.02, 0.02, 2.2, (0.6, -1.0, 0.04), ASH, 'body', rot=(-90, 0, 0), segs=4, mat=MAT_WOOD)
    for i, y in enumerate((-1.3, -1.55)):
        b.cyl(0.08, 0.08, 0.3, (-0.6, y, 0.08), LINEN, 'body', rot=(0, 90, 0), segs=6, mat=MAT_CANVAS)
    for x, y in ((0.75, -0.3), (0.85, -0.45), (0.7, -0.5)):
        b.sphere(0.07, (x, y, 0.07), IRON, 'body', segs=6, rings=4, mat=MAT_IRON)
    return b

# ------------------------------------------------------------------ polish pass: gun crew (rig = soldiers.BONES)
def gunner(name, groups, detail):
    """early-modern gunner / matross c.1600: team doublet + breeches (as the musketeer, so the side reads), buff
    leather apron and gauntlets, soft team-dyed Monmouth cap with a light band instead of the broad hat, powder horn
    and priming flask on a buff baldric, and a linstock (long ash staff, brass serpent head) instead of the matchlock."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    _legs(b, detail)
    _doublet(b, detail)
    b.box((0.3, 0.04, 0.36), (0, 0.112, 1.0), BUFF, 'hips', taper=1.1, mat=MAT_LEATHER)     # leather apron (front only)
    b.box((0.06, 0.245, 0.52), (0.0, 0.0, 1.25), BUFF, 'chest', rot=(0, 32, 0), mat=MAT_LEATHER)  # baldric (right shoulder)
    b.box((0.36, 0.225, 0.04), (0, 0, 1.05), LEATHER_D, 'hips', mat=MAT_LEATHER)            # belt
    if detail:
        b.cyl(0.035, 0.02, 0.2, (-0.15, 0.09, 0.95), FLASK, 'hips', rot=(0, 70, 0), segs=6, mat=MAT_PIPECLAY)  # powder horn
        b.box((0.08, 0.04, 0.1), (0.16, 0.09, 0.93), LEATHER, 'hips', mat=MAT_LEATHER)           # priming pouch
        b.box((0.035, 0.05, 0.3), (-0.2, -0.02, 0.84), LEATHER_D, 'hips', rot=(12, 0, 0), mat=MAT_LEATHER)  # hanger (short sword)
        for z in (1.2, 1.3, 1.4):
            b.box((0.02, 0.012, 0.02), (0.03, 0.118, z), BRASS, 'chest', mat=MAT_BRASS)
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.11, 0.12, 0.3), (x, 0, 1.31), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), TEAM, 'forearm.' + side, taper=0.9, mat=MAT_WOOL)
        b.box((0.11, 0.12, 0.09), (x, 0, 0.94), BUFF, 'forearm.' + side, mat=MAT_LEATHER)   # gauntlet cuffs
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), BUFF, 'hand.' + side, mat=MAT_LEATHER)       # gloved hands
    _head(b, detail, s)
    # Monmouth cap: soft rounded knitted cap, team dyed, light turned-up band (reads at distance)
    b.cyl(0.13, 0.13, 0.05, (0, 0.0, 1.735), LINEN, 'head', segs=s, mat=MAT_CANVAS)
    b.sphere(0.125, (0, -0.01, 1.78), TEAM, 'head', segs=s, rings=4, scale=(1, 1, 0.75), mat=MAT_WOOL)
    if detail:
        b.box((0.06, 0.06, 0.05), (0, -0.02, 1.88), TEAM, 'head', mat=MAT_WOOL)            # top knot
    # linstock: ash staff with a brass serpent head and a smouldering match (hangs along the arm from hand.R)
    hx, hz = 0.24, 0.89
    b.cyl(0.016, 0.016, 1.6, (hx, 0.03, hz - 0.35), ASH, 'hand.R', segs=4 if not detail else 6, mat=MAT_WOOD)
    b.box((0.09, 0.03, 0.08), (hx, 0.03, hz - 1.18), BRASS, 'hand.R', mat=MAT_BRASS)             # forked head
    if detail:
        b.box((0.012, 0.012, 0.06), (hx + 0.045, 0.03, hz - 1.24), hexc('d8c7a2'), 'hand.R', mat=MAT_CANVAS)  # match cord
        b.cyl(0.02, 0.012, 0.12, (hx, 0.03, hz + 0.47), IRON, 'hand.R', segs=4, mat=MAT_IRON)            # spike
    return b.to_object()
