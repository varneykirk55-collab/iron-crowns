"""Visual pass (modern era, c.1980-2020): detailed kit for mod_rifle infantry (also mech_inf and gun crew), the modern
howitzer (art_howitzer_mod.glb, swapped in for art_howitzer for rocket_art / modern; art_howitzer stays legacy) and the
era-exclusive mbt_modern / ifv_modern (rebuilt in place, same footprint / turret / barrel positions). Template: c19_kit.py.
Readability rules (c19 review): procedural 3-tone camo (MAT_CAMO) keeps a team-dyed mid tone; the plate carrier and
helmet cover carry the strongest team dye (0.6), light IR / ID panels on the shoulders, helmet and back read at
distance; polymer (MAT_POLY) for rifle furniture / pads; contact AO only at the feet. LOD1 keeps only what reads."""
from common import (hexc, MeshBuilder, MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_SKIN, MAT_PIPECLAY, MAT_IRON, MAT_HAIR,
                    MAT_CANVAS, MAT_CAMO, MAT_POLY)

TEAM = (1, 1, 1, 1.0)
SKIN = hexc('d9a988'); HAIR = hexc('3a2a1e')
CAMO = (0.68, 0.66, 0.55, 0.34)        # camo base (shader adds the 3-tone pattern), team-dyed mid tone
CARRIER = (0.74, 0.7, 0.58, 0.6)   # plate carrier / helmet cover: strongest team dye on the large front + back areas
POUCH = (0.66, 0.62, 0.5, 0.25)
ID = hexc('ece8dc')                 # light ID / IR panels
BOOT = hexc('a08a64'); POLY = hexc('2a2b2c'); POLY_T = hexc('8a7e66'); STEEL = hexc('6a7076'); GLASS = hexc('1a2a30')

def rifleman(name, groups, detail):
    """modern infantryman: camo combat uniform, plate carrier with magazine pouches (team-dyed), knee pads, desert
    boots, ballistic helmet with cover, NVG mount and light ID band, team + light shoulder patches, carbine w/ optic."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    for side, x in (('R', 0.09), ('L', -0.09)):
        b.box((0.135, 0.155, 0.44), (x, 0, 0.74), CAMO, 'thigh.' + side, taper=1.1, mat=MAT_CAMO)
        b.box((0.115, 0.135, 0.36), (x, 0, 0.31), CAMO, 'shin.' + side, taper=1.15, mat=MAT_CAMO)
        b.box((0.125, 0.06, 0.12), (x, 0.065, 0.48), POLY_T, 'shin.' + side, mat=MAT_POLY)  # knee pad
        b.box((0.12, 0.25, 0.14), (x, 0.04, 0.07), BOOT, 'shin.' + side, mat=MAT_LEATHER)
    b.box((0.35, 0.21, 0.24), (0, 0, 1.1), CAMO, 'spine', taper=1.12, mat=MAT_CAMO)
    b.box((0.4, 0.23, 0.26), (0, 0, 1.36), CAMO, 'chest', taper=1.05, mat=MAT_CAMO)
    b.box((0.37, 0.22, 0.12), (0, 0, 0.93), CAMO, 'hips', taper=1.1, mat=MAT_CAMO)
    # plate carrier (front + back plates, cummerbund), magazine pouches at the front, light ID panel on the back plate
    b.box((0.38, 0.28, 0.32), (0, 0, 1.3), CARRIER, 'chest', taper=1.04, mat=MAT_CANVAS)
    b.box((0.34, 0.08, 0.12), (0, 0.15, 1.15), POUCH, 'chest', mat=MAT_CANVAS)        # triple mag pouch
    b.box((0.22, 0.012, 0.13), (0, -0.146, 1.36), ID, 'chest', mat=MAT_PIPECLAY)       # back ID / IR panel (light)
    b.box((0.39, 0.235, 0.05), (0, 0, 1.0), POUCH, 'hips', mat=MAT_CANVAS)            # battle belt
    if detail:
        b.box((0.2, 0.08, 0.2), (0, -0.18, 1.26), POUCH, 'chest', mat=MAT_CANVAS)     # hydration / assault pack (small)
        for x in (0.12, -0.12):
            b.box((0.07, 0.07, 0.1), (x, 0.13, 0.97), POUCH, 'hips', mat=MAT_CANVAS)  # belt pouches
        b.box((0.06, 0.04, 0.12), (-0.14, 0.15, 1.38), POLY, 'chest', mat=MAT_POLY)    # radio / tourniquet
        b.box((0.02, 0.02, 0.18), (-0.13, 0.15, 1.48), POLY, 'chest', mat=MAT_POLY)    # antenna stub
        b.box((0.2, 0.17, 0.06), (0, 0, 1.5), CAMO, 'chest', mat=MAT_CAMO)             # collar
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.105, 0.115, 0.3), (x, 0, 1.31), CAMO, 'upper_arm.' + side, mat=MAT_CAMO)
        b.box((0.112, 0.122, 0.09), (x, 0, 1.36), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)  # team flag patch (both arms)
        b.box((0.113, 0.123, 0.025), (x, 0, 1.42), ID, 'upper_arm.' + side, mat=MAT_PIPECLAY)  # light IR tab
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), CAMO, 'forearm.' + side, taper=0.9, mat=MAT_CAMO)
        b.box((0.085, 0.095, 0.09), (x, 0, 0.89), POLY_T, 'hand.' + side, mat=MAT_POLY)     # gloves
    b.box((0.09, 0.09, 0.06), (0, 0, 1.52), SKIN, 'head', mat=MAT_SKIN)
    b.sphere(0.115, (0, 0.01, 1.64), SKIN, 'head', segs=s, rings=5 if detail else 4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    # ballistic helmet with team-dyed cover, light ID band, NVG shroud, ear cut-outs (ear pro)
    b.sphere(0.138, (0, -0.005, 1.7), CARRIER, 'head', segs=s, rings=4, scale=(1, 1.06, 0.78), mat=MAT_CANVAS)
    b.cyl(0.142, 0.142, 0.03, (0, -0.005, 1.7), ID, 'head', segs=s, mat=MAT_PIPECLAY)
    if detail:
        b.box((0.06, 0.03, 0.05), (0, 0.13, 1.74), POLY, 'head', mat=MAT_POLY)        # NVG shroud
        for x in (0.12, -0.12):
            b.box((0.04, 0.08, 0.08), (x, 0.0, 1.62), POLY, 'head', mat=MAT_POLY)    # ear protection
        b.box((0.12, 0.02, 0.035), (0, 0.118, 1.655), GLASS, 'head', mat=MAT_POLY)    # glasses
    # carbine (polymer furniture, optic, short barrel) hanging along the arm from hand.R (generic: L 0.85)
    hx, hz = 0.24, 0.89
    b.box((0.045, 0.1, 0.16), (hx, 0.02, hz + 0.18), POLY, 'hand.R', mat=MAT_POLY)    # stock
    b.box((0.045, 0.07, 0.4), (hx, 0.03, hz - 0.1), POLY, 'hand.R', mat=MAT_POLY)     # receiver / handguard
    b.box((0.04, 0.08, 0.1), (hx, 0.0, hz - 0.02), POLY, 'hand.R', mat=MAT_POLY)      # magazine
    b.cyl(0.011, 0.011, 0.25, (hx, 0.04, hz - 0.42), STEEL, 'hand.R', segs=4, mat=MAT_IRON)
    if detail:
        b.box((0.035, 0.05, 0.1), (hx, 0.08, hz + 0.02), POLY, 'hand.R', mat=MAT_POLY)   # optic
        b.box((0.008, 0.012, 0.5), (hx, -0.015, hz - 0.1), POUCH, 'hand.R', mat=MAT_CANVAS)  # sling
    return b.to_object()

# ------------------------------------------------------------------ props (props.py conventions, groups body / recoil)
def howitzer(groups, wheel):
    """lightweight towed 155 mm howitzer (M777 class): split titanium trails, low saddle, long barrel with muzzle brake,
    team panel + light ID chevron on the cradle; footprint / groups as art_howitzer."""
    b = MeshBuilder('art_howitzer_mod', groups)
    PAINT = (0.5, 0.5, 0.4, 0.45); RUB = hexc('1e1e1e'); DARK = hexc('3a3d36')
    for s in (1, -1):
        b.box((0.14, 3.0, 0.16), (0.5 * s, -1.4, 0.3), PAINT, 'body', rot=(-6, 0, 16 * s), mat=MAT_STEEL)
        b.box((0.4, 0.2, 0.3), (0.95 * s, -2.75, 0.15), DARK, 'body', mat=MAT_STEEL)  # spades
        b.box((0.4, 0.5, 0.12), (0.85 * s, 0.7, 0.1), DARK, 'body', mat=MAT_STEEL)   # front stabilisers
    b.box((1.2, 1.0, 0.3), (0, 0.1, 0.55), PAINT, 'body', mat=MAT_STEEL)              # saddle
    b.box((0.8, 0.9, 0.35), (0, 0.0, 0.9), PAINT, 'body', mat=MAT_STEEL)              # cradle
    b.box((0.82, 0.5, 0.2), (0, 0.0, 0.95), TEAM, 'body', mat=MAT_WOOL)               # team panel (both sides)
    b.box((0.84, 0.08, 0.06), (0, 0.27, 1.08), ID, 'body', mat=MAT_PIPECLAY)          # light ID band
    for s in (1, -1):
        wheel(b, 0.72 * s, -0.1, 0.45, 0.45, 0.3, RUB)
    b.box((0.3, 0.3, 0.2), (0, -2.35, 0.2), TEAM, 'body', mat=MAT_WOOL)               # team trail end (as legacy)
    b.box((0.2, 0.3, 0.4), (0.5, -0.3, 1.0), DARK, 'body', mat=MAT_POLY)              # fire-control box
    # barrel + recuperators (recoil group)
    b.cyl(0.1, 0.085, 4.2, (0, 1.6, 1.35), PAINT, 'recoil', rot=(-80, 0, 0), segs=10, mat=MAT_STEEL)
    b.cyl(0.17, 0.17, 1.0, (0, -0.1, 1.05), STEEL, 'recoil', rot=(-80, 0, 0), segs=10, mat=MAT_STEEL)
    for s in (1, -1):
        b.cyl(0.06, 0.06, 1.4, (0.15 * s, 0.2, 1.22), DARK, 'recoil', rot=(-80, 0, 0), segs=6, mat=MAT_STEEL)
    b.box((0.3, 0.3, 0.36), (0, 3.62, 1.72), DARK, 'recoil', rot=(-80, 0, 0), mat=MAT_STEEL)  # muzzle brake
    # charges / shells beside the trail
    for i in range(3):
        b.cyl(0.08, 0.08, 0.55, (0.9 + i * 0.18, -1.2, 0.28), hexc('6a6a52'), 'body', segs=6, mat=MAT_STEEL)
    return b

def mbt(groups, tracks):
    """modern MBT: angular hull + composite turret (sand, team-dyed turret), side skirts, light ID chevron + team panels
    on turret sides / rear, bustle rack, commander sight, smoke dischargers; mbt_modern footprint / barrel unchanged."""
    b = MeshBuilder('mbt_modern', groups)
    sand = hexc('7d7a5c'); sandt = (0.5, 0.5, 0.38, 0.55); DARK = hexc('3e3d32'); TR = hexc('2f2c28')
    tracks(b, 3.6, 7.4, 1.0, TR)
    b.box((3.6, 7.0, 0.85), (0, 0, 1.4), sand, 'body', taper=0.97, mat=MAT_STEEL)
    b.box((3.6, 1.2, 0.5), (0, 3.4, 1.25), sand, 'body', rot=(20, 0, 0), mat=MAT_STEEL)
    for s in (1, -1):
        b.box((0.08, 6.4, 0.65), (s * 1.84, 0.1, 1.0), sand, 'body', mat=MAT_STEEL)    # side skirts
        b.box((0.09, 1.6, 0.12), (s * 1.85, 2.0, 1.2), TEAM, 'body', mat=MAT_WOOL)    # team skirt flash
    b.box((3.0, 3.4, 0.8), (0, -0.4, 2.2), sandt, 'body', taper=0.82, mat=MAT_STEEL)
    b.box((2.6, 1.2, 0.6), (0, 1.5, 2.15), sandt, 'body', rot=(-12, 0, 0), taper=0.7, mat=MAT_STEEL)
    for s in (1, -1):  # light inverted-V ID chevron on both turret sides
        b.box((0.04, 0.9, 0.1), (s * 1.27, -0.3, 2.3), ID, 'body', rot=(28, 0, 0), mat=MAT_PIPECLAY)
        b.box((0.04, 0.9, 0.1), (s * 1.27, -1.0, 2.3), ID, 'body', rot=(-28, 0, 0), mat=MAT_PIPECLAY)
        b.box((0.15, 0.25, 0.25), (s * 1.05, 0.9, 2.45), DARK, 'body', mat=MAT_POLY)  # smoke dischargers
    b.box((2.6, 0.9, 0.5), (0, -2.45, 2.15), DARK, 'body', mat=MAT_STEEL)             # bustle rack
    b.box((2.4, 0.7, 0.3), (0, -2.45, 2.4), POUCH, 'body', mat=MAT_CANVAS)            # stowage (tarps, light)
    b.box((0.6, 0.6, 0.3), (0.8, -0.8, 2.75), sand, 'body', mat=MAT_STEEL)
    b.box((0.35, 0.35, 0.3), (-0.7, -0.2, 2.75), DARK, 'body', mat=MAT_POLY)          # commander sight
    b.box((0.45, 0.04, 0.3), (0, -2.92, 2.15), ID, 'body', mat=MAT_PIPECLAY)          # rear ID panel
    b.cyl(0.09, 0.09, 5.0, (0, 3.9, 2.3), sand, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_STEEL)
    b.cyl(0.15, 0.15, 0.8, (0, 3.0, 2.3), sand, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_STEEL)
    b.cyl(0.13, 0.13, 1.4, (0, 4.8, 2.3), sand, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_STEEL)  # thermal sleeve
    return b

def ifv(groups, wheel):
    """modern 8x8 IFV: angular green hull, team-dyed turret, light ID chevrons on the sides, rear door, stowage,
    autocannon; ifv_modern footprint / barrel unchanged."""
    b = MeshBuilder('ifv_modern', groups)
    green = hexc('4f5a3e'); gt = (0.42, 0.47, 0.32, 0.55); RUB = hexc('1e1e1e'); DARK = hexc('2e3428')
    for s in (1, -1):
        for i in range(4):
            wheel(b, s * 1.3, -2.2 + i * 1.45, 0.55, 0.55, 0.45, RUB)
    b.box((2.8, 6.6, 1.3), (0, 0, 1.45), green, 'body', taper=0.9, mat=MAT_STEEL)
    b.box((2.8, 1.2, 1.0), (0, 3.3, 1.35), green, 'body', rot=(40, 0, 0), mat=MAT_STEEL)
    for s in (1, -1):
        b.box((0.04, 0.9, 0.12), (s * 1.42, 0.4, 1.65), ID, 'body', rot=(28, 0, 0), mat=MAT_PIPECLAY)
        b.box((0.04, 0.9, 0.12), (s * 1.42, -0.3, 1.65), ID, 'body', rot=(-28, 0, 0), mat=MAT_PIPECLAY)
        b.box((0.05, 1.8, 0.2), (s * 1.38, -1.8, 1.9), TEAM, 'body', mat=MAT_WOOL)    # team band on the hull sides
        b.box((0.3, 0.3, 0.05), (s * 0.9, 2.4, 2.12), DARK, 'body', mat=MAT_POLY)      # vision blocks
    b.box((1.4, 1.6, 0.55), (0, 0.3, 2.35), gt, 'body', taper=0.8, mat=MAT_STEEL)
    b.box((1.2, 0.04, 0.9), (0, -3.3, 1.45), DARK, 'body', mat=MAT_STEEL)             # rear ramp
    b.box((0.4, 0.04, 0.25), (0, -3.32, 1.75), ID, 'body', mat=MAT_PIPECLAY)
    b.box((1.8, 0.8, 0.25), (0, -2.2, 2.12), POUCH, 'body', mat=MAT_CANVAS)           # roof stowage
    b.cyl(0.06, 0.06, 2.3, (0, 2.1, 2.4), STEEL, 'recoil', rot=(-90, 0, 0), segs=6, mat=MAT_IRON)
    b.cyl(0.1, 0.1, 0.4, (0, 1.1, 2.4), DARK, 'recoil', rot=(-90, 0, 0), segs=6, mat=MAT_STEEL)
    return b
