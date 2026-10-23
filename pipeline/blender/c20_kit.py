"""Visual pass (c20 era, c.1914-1945): detailed kit for c20_rifle infantry (also used by trucks_inf and as gun crew),
the c20 howitzer (art_howitzer_c20.glb, swapped in for art_howitzer which is shared with modern rocket_art) and the
c20 tank (tank_c20 is era-exclusive -> rebuilt in place). Template: c19_kit.py. Readability rules (c19 review):
field uniforms stay drab but carry a stronger team dye (0.55 instead of 0.35, never darker than the c19 coats' value),
team armbands on BOTH arms + team helmet band, light canvas webbing / bedroll / puttee tops that read at distance,
no dark masses on the back, contact AO only at the feet. LOD1 (detail=False, > 75 m) keeps only what reads."""
from common import (hexc, MeshBuilder, MAT_WOOL, MAT_LEATHER, MAT_STEEL, MAT_BRASS, MAT_SKIN, MAT_WOOD, MAT_PIPECLAY,
                    MAT_IRON, MAT_HAIR, MAT_CANVAS, MAT_POLY)

TEAM = (1, 1, 1, 1.0)
SKIN = hexc('d9a988'); HAIR = hexc('4a3424')
TUNIC = (0.5, 0.49, 0.38, 0.55)      # drab serge, team-dyed (legacy DRAB 0.42/0.42/0.33 at 0.35)
TROUSER = (0.44, 0.43, 0.34, 0.45)
HELMET = (0.42, 0.44, 0.34, 0.3)
WEB = hexc('d2c7a2')                 # blancoed canvas webbing: light accent
PUTTEE = hexc('7e7558'); BOOT = hexc('3a2a1e'); LEATHER = hexc('6a4a30')
STEEL = hexc('8d949b'); IRON = hexc('34373b'); WALNUT = hexc('6b4426'); BRASS = hexc('b8964a')
BEDROLL = hexc('b9b4a2')

def rifleman(name, groups, detail):
    """c.1916 rifleman: team-dyed drab tunic + trousers, puttees, light canvas webbing (belt, braces, pouches, small
    pack + light bedroll), team armbands, steel 'brodie' helmet with a team band, bolt-action rifle with bayonet."""
    s = 8 if detail else 5
    b = MeshBuilder(name, groups)
    for side, x in (('R', 0.09), ('L', -0.09)):
        b.box((0.135, 0.155, 0.44), (x, 0, 0.74), TROUSER, 'thigh.' + side, taper=1.1, mat=MAT_WOOL)
        b.box((0.11, 0.13, 0.3), (x, 0, 0.27), PUTTEE, 'shin.' + side, taper=1.12, mat=MAT_WOOL)
        b.box((0.115, 0.135, 0.06), (x, 0, 0.44), WEB, 'shin.' + side, mat=MAT_CANVAS)  # puttee tape (light)
        b.box((0.11, 0.24, 0.09), (x, 0.04, 0.05), BOOT, 'shin.' + side, mat=MAT_LEATHER)
    b.box((0.35, 0.21, 0.24), (0, 0, 1.1), TUNIC, 'spine', taper=1.12, mat=MAT_WOOL)
    b.box((0.41, 0.235, 0.26), (0, 0, 1.36), TUNIC, 'chest', taper=1.05, mat=MAT_WOOL)
    b.box((0.37, 0.22, 0.12), (0, 0, 0.93), TUNIC, 'hips', taper=1.1, mat=MAT_WOOL)  # tunic skirt
    # webbing: belt, braces (front + back), ammo pouches at the front, small pack + bedroll on the back (light)
    b.box((0.37, 0.235, 0.05), (0, 0, 1.0), WEB, 'hips', mat=MAT_CANVAS)
    for x in (0.1, -0.1):
        b.box((0.045, 0.25, 0.42), (x, 0, 1.28), WEB, 'chest', mat=MAT_CANVAS)
        b.box((0.11, 0.06, 0.12), (x + 0.03 * (1 if x > 0 else -1), 0.13, 1.07), WEB, 'spine', mat=MAT_CANVAS)
    b.box((0.24, 0.09, 0.18), (0, -0.16, 1.3), WEB, 'chest', mat=MAT_CANVAS)       # small pack (kept small: team back reads)
    b.cyl(0.05, 0.05, 0.32, (0, -0.16, 1.43), BEDROLL, 'chest', rot=(0, 90, 0), segs=6, mat=MAT_CANVAS)
    if detail:
        b.box((0.06, 0.05, 0.3), (-0.17, -0.05, 0.86), LEATHER, 'hips', rot=(10, 0, 0), mat=MAT_LEATHER)  # bayonet frog
        b.box((0.08, 0.06, 0.12), (-0.15, -0.1, 0.98), (0.4, 0.42, 0.36, 0.0), 'hips', mat=MAT_STEEL)     # water bottle
        b.box((0.1, 0.06, 0.04), (-0.11, -0.13, 0.98), WEB, 'hips', mat=MAT_CANVAS)
        b.box((0.08, 0.1, 0.18), (0.18, -0.08, 0.94), WEB, 'hips', mat=MAT_CANVAS)       # haversack / entrenching tool
        for x in (0.07, -0.07):
            b.box((0.05, 0.015, 0.05), (x, 0.124, 1.36), (0.36, 0.36, 0.28, 0.4), 'chest', mat=MAT_WOOL)  # breast pockets
        b.box((0.2, 0.17, 0.06), (0, 0, 1.5), TUNIC, 'chest', mat=MAT_WOOL)                  # collar
    for side, x in (('R', 0.24), ('L', -0.24)):
        b.box((0.105, 0.115, 0.3), (x, 0, 1.31), TUNIC, 'upper_arm.' + side, mat=MAT_WOOL)
        b.box((0.115, 0.125, 0.08), (x, 0, 1.37), TEAM, 'upper_arm.' + side, mat=MAT_WOOL)   # team armband, both arms
        b.box((0.09, 0.1, 0.26), (x, 0, 1.06), TUNIC, 'forearm.' + side, taper=0.9, mat=MAT_WOOL)
        b.box((0.08, 0.09, 0.09), (x, 0, 0.89), SKIN, 'hand.' + side, mat=MAT_SKIN)
    b.box((0.09, 0.09, 0.06), (0, 0, 1.52), SKIN, 'head', mat=MAT_SKIN)
    b.sphere(0.115, (0, 0.01, 1.64), SKIN, 'head', segs=s, rings=5 if detail else 4, scale=(0.95, 1, 1.12), mat=MAT_SKIN)
    if detail:
        b.box((0.2, 0.06, 0.06), (0, -0.08, 1.62), HAIR, 'head', mat=MAT_HAIR)
        b.box((0.012, 0.03, 0.12), (0.1, 0.07, 1.6), WEB, 'head', mat=MAT_CANVAS)  # chin strap
    # brodie helmet: shallow bowl + wide brim, team band round the bowl
    b.sphere(0.13, (0, 0.0, 1.72), HELMET, 'head', segs=s, rings=4, scale=(1, 1.05, 0.62), mat=MAT_STEEL)
    b.cyl(0.215, 0.2, 0.022, (0, 0.0, 1.7), HELMET, 'head', segs=s + 2, mat=MAT_STEEL)
    b.cyl(0.133, 0.133, 0.035, (0, 0.0, 1.735), TEAM, 'head', segs=s, mat=MAT_WOOL)
    # bolt-action rifle with fixed bayonet, sling (hangs along the arm from hand.R; generic: L 1.15)
    hx, hz = 0.24, 0.89
    b.box((0.05, 0.1, 0.17), (hx, 0.02, hz + 0.19), WALNUT, 'hand.R', mat=MAT_WOOD)
    b.box((0.04, 0.055, 0.62), (hx, 0.025, hz - 0.22), WALNUT, 'hand.R', mat=MAT_WOOD)
    b.cyl(0.013, 0.013, 0.8, (hx, 0.045, hz - 0.4), IRON, 'hand.R', segs=4 if not detail else 6, mat=MAT_IRON)
    b.cyl(0.01, 0.0, 0.36, (hx + 0.02, 0.045, hz - 0.98), STEEL, 'hand.R', rot=(180, 0, 0), segs=3, mat=MAT_STEEL)
    if detail:
        b.box((0.03, 0.05, 0.08), (hx + 0.03, 0.03, hz + 0.04), IRON, 'hand.R', mat=MAT_IRON)  # bolt / magazine
        b.box((0.008, 0.012, 0.55), (hx, -0.012, hz - 0.2), WEB, 'hand.R', mat=MAT_CANVAS)       # sling
    return b.to_object()

# ------------------------------------------------------------------ props (props.py conventions, groups body / recoil)
GUN = (0.46, 0.49, 0.36, 0.5)   # olive gun paint, half team tinted
def howitzer(groups, wheel):
    """c.1916 field howitzer (105 mm class): box trail, spoked wooden wheels with steel tyres, gun shield with a team
    panel + light ID band, short thick barrel on a recuperator cradle, ammo + canvas cover. Footprint / groups as art_howitzer."""
    b = MeshBuilder('art_howitzer_c20', groups)
    WOOD = hexc('6e4a2b'); RUB = hexc('2a2622')
    b.box((0.36, 2.6, 0.24), (0, -1.35, 0.4), GUN, 'body', rot=(-9, 0, 0), mat=MAT_STEEL)    # box trail
    b.box((0.5, 0.3, 0.12), (0, -2.6, 0.18), GUN, 'body', mat=MAT_STEEL)                    # spade
    b.box((0.3, 0.3, 0.2), (0, -2.35, 0.25), TEAM, 'body', mat=MAT_WOOD)                    # team trail end
    b.box((1.3, 0.2, 0.2), (0, 0.1, 0.62), GUN, 'body', mat=MAT_STEEL)                      # axle
    b.box((0.7, 0.8, 0.35), (0, 0.1, 0.85), GUN, 'body', mat=MAT_STEEL)                     # cradle / saddle
    # shield: olive with a large team panel + light band (reads from behind too: panel on both faces)
    b.box((1.6, 0.06, 0.95), (0, 0.55, 1.05), GUN, 'body', mat=MAT_STEEL)
    b.box((1.0, 0.07, 0.45), (0, 0.55, 1.12), TEAM, 'body', mat=MAT_WOOL)
    b.box((1.62, 0.075, 0.08), (0, 0.55, 1.44), WEB, 'body', mat=MAT_CANVAS)
    for wx in (0.7, -0.7):
        wheel(b, wx, 0.1, 0.62, 0.62, 0.12, WOOD)
        b.cyl(0.64, 0.64, 0.1, (wx, 0.1, 0.62), IRON, 'body', rot=(0, 90, 0), segs=12, mat=MAT_IRON)  # steel tyre
    # barrel: short thick tube + recuperator above (recoil group), muzzle
    b.cyl(0.13, 0.12, 2.0, (0, 1.0, 1.2), GUN, 'recoil', rot=(-80, 0, 0), segs=10, mat=MAT_STEEL)
    b.cyl(0.18, 0.18, 1.0, (0, 0.0, 1.05), STEEL, 'recoil', rot=(-80, 0, 0), segs=10, mat=MAT_STEEL)
    b.cyl(0.08, 0.08, 1.2, (0, 0.3, 1.32), GUN, 'recoil', rot=(-80, 0, 0), segs=8, mat=MAT_STEEL)
    b.cyl(0.145, 0.145, 0.16, (0, 1.95, 1.36), IRON, 'recoil', rot=(-80, 0, 0), segs=10, mat=MAT_IRON)
    # ammunition: light shell cases in an open box, canvas cover rolled on the trail
    b.box((0.5, 0.35, 0.22), (0.9, -1.0, 0.11), hexc('6b5a3e'), 'body', mat=MAT_WOOD)
    for i in range(4):
        b.cyl(0.05, 0.05, 0.3, (0.75 + i * 0.1, -1.0, 0.3), BRASS, 'body', segs=6, mat=MAT_BRASS)
    b.cyl(0.1, 0.1, 0.6, (0, -1.6, 0.6), WEB, 'body', rot=(0, 90, 0), segs=6, mat=MAT_CANVAS)
    return b

def tank(groups, tracks):
    """c.1940 medium tank (tank_c20, era-exclusive -> rebuilt in place, same footprint / turret height / barrel):
    riveted olive hull, team turret band + large light national ID disc on turret sides + rear, mudguards, tools."""
    b = MeshBuilder('tank_c20', groups)
    OLIVE = hexc('59603f'); OT = (0.45, 0.48, 0.32, 0.45); TRACK = hexc('2f2c28')
    tracks(b, 3.0, 6.0, 1.0, TRACK)
    b.box((2.9, 5.6, 0.9), (0, 0, 1.35), OLIVE, 'body', taper=0.92, mat=MAT_STEEL)
    b.box((2.95, 1.0, 0.6), (0, 2.8, 1.1), OLIVE, 'body', rot=(35, 0, 0), mat=MAT_STEEL)
    for s in (1, -1):
        b.box((0.62, 6.1, 0.05), (s * 1.22, 0, 1.03), OLIVE, 'body', mat=MAT_STEEL)  # mudguards
        b.box((0.03, 1.2, 0.14), (s * 1.46, -1.4, 1.35), WEB, 'body', mat=MAT_CANVAS)  # light stowage
    b.box((2.4, 1.6, 0.06), (0, -1.9, 1.82), hexc('4a4d38'), 'body', mat=MAT_STEEL)    # engine deck grille
    b.cyl(1.05, 0.95, 0.85, (0, -0.3, 2.2), OT, 'body', segs=12, mat=MAT_STEEL)
    b.cyl(1.07, 1.07, 0.22, (0, -0.3, 2.3), TEAM, 'body', segs=12, mat=MAT_WOOL)        # team turret band
    for x, y in ((1.08, -0.3), (-1.08, -0.3)):
        b.box((0.04, 0.45, 0.45), (x, y, 2.2), WEB, 'body', mat=MAT_PIPECLAY)            # light ID disc (square-ish)
        b.box((0.05, 0.25, 0.25), (x, y, 2.2), TEAM, 'body', mat=MAT_WOOL)
    b.box((0.45, 0.04, 0.45), (0, -1.33, 2.2), WEB, 'body', mat=MAT_PIPECLAY)
    b.cyl(0.35, 0.35, 0.4, (0.4, -0.6, 2.75), OLIVE, 'body', segs=8, mat=MAT_STEEL)    # cupola
    b.cyl(0.36, 0.36, 0.05, (0.4, -0.6, 2.97), IRON, 'body', segs=8, mat=MAT_IRON)
    b.box((0.4, 0.7, 0.3), (0, -2.75, 1.45), OLIVE, 'body', mat=MAT_STEEL)             # rear stowage box
    for i in range(5):
        b.box((0.06, 0.06, 0.04), (-1.3 + i * 0.65, 2.55, 1.66), IRON, 'body', mat=MAT_IRON)  # rivet rows
    b.cyl(0.1, 0.1, 3.4, (0, 2.3, 2.25), OLIVE, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_STEEL)
    b.cyl(0.18, 0.18, 0.5, (0, 0.85, 2.25), OLIVE, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_STEEL)
    b.cyl(0.13, 0.13, 0.2, (0, 3.95, 2.25), IRON, 'recoil', rot=(-90, 0, 0), segs=8, mat=MAT_IRON)  # muzzle
    b.cyl(0.04, 0.04, 0.5, (0.45, 2.85, 1.55), IRON, 'body', rot=(-90, 0, 0), segs=5, mat=MAT_IRON)   # hull MG
    return b
