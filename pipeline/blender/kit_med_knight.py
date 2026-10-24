"""Eras v3 kit 6: mounted man-at-arms / knight, c.1300 (unit med_knight; docs/char/ERAS_PROGRESS.md). Patches char_v2
(loaded by char_v2_build.py when V3_KIT=kit_med_knight).

RIDER ONLY (Kirk 21:01): the v3 human seated on the EXISTING cavalry rig by v3_rider.py, exactly like the hussar
(cavalry.BONES / clips untouched, variant 'med_knight' = lance clips). The horse body, mane / tail and the generic
tack (girth, breast strap, bridle, bit, reins, stirrups) are the shared kit-3 horse code imported unchanged from
kit_c19_hussar (horses belong to Bill; no barding / caparison here). Hussar items (scabbard, sabretache,
shabraque, sheepskin, valise) are NOT used.
Fresh c.1300 garments / gear (no clothing reused):
  * mail hauberk (sleeves to the wrist) + mail chausses over the legs and feet, mail coif at the neck (mail-grey slot,
    ring-row relief in the bake); padded aketon implied under it (quilted hem edge below the hauberk)
  * sleeveless heraldic surcoat in the team colour, slit front and back for riding, with a cream chevron on the chest
  * steel poleyns on the knees, gilt prick spurs
  * flat-topped great helm with eye slits (ocularia), breaths, a brass cross reinforcement
  * heater shield on the left forearm (team field, cream chevron, leather rim), sword belt, sword in its scabbard
    hung on the left hip, couched lance with a swallow-tailed team pennon (prop, weapon_tip at the lance point)
  * medieval war saddle (high pommel and wrap-round cantle) on a small team-colour saddle cloth (tack, not barding)."""
import math, bpy
import numpy as np
from mathutils import Matrix, Vector
import kit_c19_hussar as HZ        # shared horse / tack code (horse coords); its module-level C patches are overridden below
import char_v2 as C
import char_rig as R
import human_mh as HM, v3_parts as V3P
import v3_rider as VR
from char_v2 import V, ss, lerp, limb, ring, grid_sweep, superellipsoid, set_slot

VR.WRIST_TILT = 0.0   # lance fist hangs straight in the seated rest (lance along the forearm, Rob's lance pose levels it)

C.KID = 'v3_med_knight'
C.CLIP_STYLE = 'musket'   # unused (cavalry clips)
HOFF = HZ.HOFF
C.RIDER = dict(variant='med_knight', hoff=tuple(HOFF), tail='hztail',
               rigid={'hzeye': 'head', 'hzbrid': 'head', 'hzbit': 'head', 'hzgirth': 'body', 'hzbreast': 'body',
                      'hzstir': 'body', 'hzleath': 'body', 'kzsad': 'body', 'kzcloth': 'body', 'kzsc': 'body'},
               rein=('hzrein',), tip=(0.25, 0.0, -1.8))   # tip overwritten by lance()
C.SLOT_MAT.update({'scabbard': 'steel', 'belt': 'worn_leather', 'cartbox': 'worn_leather', 'knapsack': 'hair',
                   'lapel': 'wool', 'turnback': 'wool', 'gold': 'wool', 'stock': 'leather'})
C.BODY_TRIS = 2500
C.MH_LO = {'mhhead': 600, 'mhhandR': 620, 'mhhandL': 580}   # head is inside the great helm
C.HEAD_BOX = (0.0, -0.13, 0.16, 2.0)   # no face texel boost (the face is hidden)
C.HAND_BOX_Y = 0.15
C.AO_AWAY_KEYS = ('klance', 'kshield')
C.UV_SCALES = [(lambda co: co.y < -3.0, (0.0, -6.0, 1.0), 0.62)]
C.KIT_PAL = {'knapsack': '#4a2b17', 'hair': '#17110c', 'scabbard': '#767a7f', 'lapel': '#e2cf8a', 'belt': '#4a2d1a',
             'cartbox': '#3e2616', 'metal': '#c9a548', 'stock': '#0d0c0b', 'turnback': '#d8ccb0'}
C.KIT_RULES = [(('khelm',), 'head'), (('ksur', 'kbelt', 'kaket'), 'transfer'),
               (('klance',), 'hand.R'), (('kshield',), 'forearm.L'),
               (('kpolR',), 'shin.R'), (('kpolL',), 'shin.L'), (('kspurR',), 'foot.R'), (('kspurL',), 'foot.L'),
               (('hz', 'kz'), 'own')]

HM.FIST['.R'] = 0.020   # lance grip
HM.FIST['.L'] = 0.014   # rein hand

J = {b[0]: (V(b[1]), V(b[2])) for b in R.BONES}
MAIL, PLATE = 'scabbard', 'steel'

# ------------------------------------------------------------------ body shell slots
SUR_TOP = 1.47

def _chev(ax, z, zt=1.33, k=1.05, w=0.026):
    return abs(z - (zt - k * ax)) < w and ax < 0.15

def body_slot(p, part):
    x, y, z = p; ax = abs(x)
    if part == 'shoe': return MAIL
    if part == 'collar': return MAIL
    if part in ('arm', 'leg'): return MAIL
    if z > SUR_TOP - 0.02 * ss(0.05, 0.12, ax): return MAIL           # coif / mail at the neck + shoulders
    if ax > 0.150 and z > 1.30: return MAIL                         # sleeveless surcoat: armholes show the hauberk
    if z < 0.99: return MAIL                                        # hauberk skirt between the legs (under the surcoat)
    if _chev(ax, z): return 'lapel'
    return 'coat'
C.body_slot = body_slot

_add_folds = C.add_folds
def add_folds(o, spread):
    """mail: soft ring-row relief (period 2 cm, well above the hi vertex spacing so it can't alias) on the mail slot."""
    _add_folds(o, spread)
    me = o.data; me.update()
    n = len(me.vertices)
    P = np.zeros(n * 3); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    N = np.zeros(n * 3); me.vertices.foreach_get('normal', N); N = N.reshape(-1, 3)
    slot = np.zeros(len(me.polygons), np.int32); me.attributes['slot'].data.foreach_get('value', slot)
    lt = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lt)
    tot = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('loop_total', tot)
    fs = np.repeat(slot, tot)
    m = np.zeros(n, bool); m[lt[fs == C.S[MAIL]]] = True
    d = 0.0007 * np.sin(2 * np.pi * P[:, 2] / 0.020)
    P = P + N * (d * m)[:, None]
    me.vertices.foreach_set('co', P.ravel()); o.data.update()
C.add_folds = add_folds

# ------------------------------------------------------------------ surcoat skirt (split front / back, riding slits)
SK = [(1.010, .182, .128, .134), (0.95, .196, .136, .156), (0.88, .206, .146, .170), (0.76, .216, .158, .178),
      (0.62, .226, .168, .184)]
SK_Z0, SK_Z1 = SK[0][0], SK[-1][0]
def _sk(z):
    for a, b in zip(SK, SK[1:]):
        if b[0] <= z <= a[0]:
            t = (a[0] - z) / (a[0] - b[0]); return [lerp(a[k], b[k], t) for k in range(1, 4)]
    return list((SK[0] if z > SK_Z0 else SK[-1])[1:])

def surcoat_skirt(hi=False):
    out = []
    nz, na = (48, 96) if hi else (5, 9)
    for s in (1, -1):
        secs = []
        for i in range(nz + 1):
            t = i / nz; z = lerp(SK_Z0, SK_Z1, t)
            rx, rf, rb = _sk(z)
            dl = math.radians(lerp(4.0, 22.0, ss(0.93, SK_Z1, z)))   # slits open towards the hem
            outer, inner = [], []
            for j in range(na + 1):
                a = lerp(math.pi / 2 - dl, -math.pi / 2 + dl, j / na)
                ca, sa = math.cos(a), math.sin(a)
                ry = rf if sa > 0 else rb
                fold = (0.006 * math.sin(a * 7.0 + 0.6) * ss(0.95, 0.70, z)) if hi else 0.0
                p = V(s * (rx + fold) * ca, (ry + fold) * sa, z)
                outer.append(p); inner.append(V(s * (rx - 0.006) * ca, (ry - 0.006) * sa, z))
            secs.append(outer + inner[::-1])
        o = grid_sweep('ksur' + ('R' if s > 0 else 'L'), secs, closed_u=True, cap0=False, cap1=True, slot='coat')
        out.append(V3P.orient_out(o))
    # quilted aketon hem peeping below the surcoat (linen, 2 cm)
    return out

def sword_belt(tree, hi):
    n = 64 if hi else 14; pts = []
    for j in range(n + 1):
        a = 2 * math.pi * j / n
        z = 0.985 - 0.035 * (0.5 - 0.5 * math.sin(a)) * (1 if math.cos(a) < 0 else 0.4)   # slung low on the left hip
        rx, rf, rb = _sk(z)
        ry = rf if math.sin(a) > 0 else rb
        p = V((rx + 0.004) * math.cos(a), (ry + 0.004) * math.sin(a), z)
        pts.append((0 if j == 0 else j / n, p))
    o = limb('kbelt', pts, [(0, 0.0030, 0.016, 0.016)], n, 6 if hi else 4, fwd=V(0, 0, 1), slot='belt', cap0=False, cap1=False)
    b = superellipsoid('kbelt.b', V(0, _sk(0.985)[1] + 0.010, 0.985), (0.022, 0.006, 0.022), e=(3, 3),
                       n=(10, 4) if hi else (6, 3), slot='metal')
    return [o, b]

# ------------------------------------------------------------------ knees / spurs
def poleyns(tree, hi):
    out = []
    for s, sd in ((1, 'R'), (-1, 'L')):
        k = J['shin.' + ('R' if s > 0 else 'L')][0]
        h = V3P.surf(tree, V(k.x, 0.4, k.z + 0.01), V(0, -1, 0), 0.010)
        c = h[0] if h else V(k.x, 0.08, k.z)
        out.append(superellipsoid('kpol' + sd, c + V(0, -0.006, 0), (0.050, 0.026, 0.058), e=(2.3, 2.3),
                                  n=(20, 12) if hi else (8, 5), slot=PLATE))
        out.append(superellipsoid('kpol' + sd + '.w', c + V(s * 0.040, -0.016, 0), (0.010, 0.030, 0.040), e=(2.5, 2.5),
                                  n=(10, 6) if hi else (4, 3), slot=PLATE))   # side wing
    return out

def spurs(tree, hi):
    out = []
    for s, sd in ((1, 'R'), (-1, 'L')):
        f = J['foot.' + ('R' if s > 0 else 'L')][0]
        c = V(f.x, f.y - 0.005, 0.070)
        n = 16 if hi else 6; path = []
        for k in range(n + 1):
            a = math.radians(lerp(-80, 260, k / n) - 90)
            path.append((k / n, c + V(0.050 * math.cos(a), 0.058 * math.sin(a), 0.0)))
        path = [p for p in path if p[1].y < c.y + 0.02]
        path = [(i / (len(path) - 1), p) for i, (_, p) in enumerate(path)]
        out.append(limb('kspur' + sd, path, [(0, 0.0035, 0.0045, 0.0045)], len(path) - 1, 6 if hi else 3, fwd=V(0, 0, 1),
                        slot='metal'))
        back = min(path, key=lambda q: q[1].y)[1]
        out.append(limb('kspur' + sd + '.n', [(0, back), (1, back + V(0, -0.050, 0.004))],
                        [(0, 0.0040, 0.0040, 0.0040), (1, 0.0012, 0.0012, 0.0012)], 3 if hi else 1, 6 if hi else 3,
                        fwd=V(0, 0, 1), slot='metal'))
    return out

# ------------------------------------------------------------------ great helm (fitted round the hi MakeHuman head)
HELM = {}
HZ0, HZ1, HTOP = 1.548, 1.815, 1.842
H_CY = 0.014
def _fit_helm(head):
    if HELM: return
    rx0, rf0, rb0 = 0.104, 0.118, 0.116
    k = 0.0
    for v in head.data.vertices:
        p = head.matrix_world @ v.co
        if p.z < HZ0 + 0.01: continue
        ry = rf0 if p.y > H_CY else rb0
        k = max(k, math.sqrt((p.x / rx0) ** 2 + ((p.y - H_CY) / ry) ** 2))
    g = max(1.0, k / 0.90)
    HELM.update(rx=rx0 * g, rf=rf0 * g, rb=rb0 * g)
    print('[knight] helm fit scale', round(g, 3), HELM, flush=True)

def helm_slot(c):
    a = math.atan2(c.x, c.y - H_CY)   # 0 = front
    ad = math.degrees(abs(a))
    if c.z > HZ1 - 0.004: return PLATE
    if 1.650 < c.z < 1.668 and 9 < ad < 72: return 'stock'                               # eye slits
    if c.x < 0 and 1.585 < c.z < 1.625 and 25 < ad < 70:                              # breaths (right of the face = -x)
        u = (ad - 25) / 9.0; v = (c.z - 1.585) / 0.013
        if abs(u - round(u)) < 0.22 and abs(v - round(v)) < 0.28: return 'stock'
    if abs(c.x) < 0.011 and c.y > H_CY and c.z < 1.79: return 'metal'                     # brass cross: upright
    if 1.668 < c.z < 1.684 and ad < 80: return 'metal'                                     # brass cross: brow band
    return PLATE

def great_helm(hi):
    rx, rf, rb = HELM['rx'], HELM['rf'], HELM['rb']
    nu = 128 if hi else 22
    ts = [i / 40 for i in range(41)] if hi else [0.0, 0.42, 0.62, 1.0]
    secs = [ring(V(0, H_CY, HZ0 + 0.004), V(1, 0, 0), V(0, 1, 0), rx - 0.006, rf - 0.006, rb - 0.006, nu, 2.15, 0.5)]
    for t in ts:
        z = lerp(HZ0, HZ1, t)
        g = 1.0 - 0.06 * t ** 1.5                     # slight taper to the crown
        def fn(p, a, z=z):
            if not hi: return p
            ad = math.degrees(abs(math.atan2(p.x, p.y - H_CY)))
            q = p
            if 1.650 < z < 1.668 and 9 < ad < 72:          # eye slits: sunk 5 mm
                d = (q - V(0, H_CY, z)); d.z = 0; q = q - d.normalized() * 0.005
            if ad < 16:                                     # pointed front ridge (stiffness, period form)
                d = (q - V(0, H_CY, z)); d.z = 0; q = q + d.normalized() * 0.006 * (1 - ad / 16)
            return q
        secs.append(ring(V(0, H_CY, z), V(1, 0, 0), V(0, 1, 0), rx * g, rf * g, rb * g, nu, 2.15, 0.5, fn=fn))
    for t in ((0.5, 1.0) if not hi else (0.25, 0.5, 0.75, 0.92, 1.0)):    # low dome
        g = 0.94 * math.sqrt(max(0.0, 1 - t * t)) if t < 1.0 else 0.0
        if t >= 1.0: break
        secs.append(ring(V(0, H_CY, HZ1 + (HTOP - HZ1) * t), V(1, 0, 0), V(0, 1, 0), rx * g, rf * g, rb * g, nu, 2.15, 0.5))
    o = grid_sweep('khelm', secs, closed_u=True, cap0=False, cap1=True, slot=helm_slot if hi else PLATE)
    return [V3P.orient_out(o)]

# ------------------------------------------------------------------ heater shield on the left forearm
SH_C = V(-0.262, -0.006, 1.020)          # on the outside of the hanging left forearm
SH_TOP, SH_PT, SH_W = 0.20, -0.40, 0.225  # along y (top towards +y: point down once the rein forearm is raised)
def _sh_hw(f):
    return SH_W if f < 0.30 else SH_W * max(0.0, math.cos(math.pi / 2 * (f - 0.30) / 0.70)) ** 0.75

def shield(hi):
    nf, nw = (40, 40) if hi else (6, 6)
    secs = []
    for i in range(nf + 1):
        f = i / nf
        y = SH_C.y + lerp(SH_TOP, SH_PT, f)
        hw = max(_sh_hw(f), 0.004)
        front, back = [], []
        for j in range(nw + 1):
            w = lerp(-hw, hw, j / nw)
            bulge = 0.040 * (1 - (w / SH_W) ** 2)          # convex across the width
            x = SH_C.x - bulge
            front.append(V(x - 0.006, y, SH_C.z + w)); back.append(V(x + 0.006, y, SH_C.z + w))
        secs.append(front + back[::-1])
    def sl(c):
        f = (SH_C.y + SH_TOP - c.y) / (SH_TOP - SH_PT)
        w = c.z - SH_C.z; hw = _sh_hw(min(max(f, 0), 1))
        if c.x > SH_C.x - 0.025 * (1 - (w / SH_W) ** 2) + 0.003: return 'wood'            # inside face
        if abs(w) > hw - 0.013 or f < 0.025: return 'belt'                               # leather rim
        if abs(f - (0.62 - 1.05 * abs(w))) < 0.065: return 'lapel'                      # chevron
        return 'coat'
    o = grid_sweep('kshield', secs, closed_u=True, cap0=True, cap1=True, slot=sl if hi else 'coat')
    o = V3P.orient_out(o)
    if not hi: set_slot(o, sl)
    # enarmes + guige stub on the inside (leather)
    out = [o]
    for dz, dy in ((0.07, 0.02), (-0.07, -0.06)):
        out.append(superellipsoid('kshield.s', V(SH_C.x + 0.022, SH_C.y + dy, SH_C.z + dz), (0.010, 0.030, 0.012), e=(3, 3),
                                  n=(8, 4) if hi else (4, 2), slot='belt'))
    return out

# ------------------------------------------------------------------ couched lance + pennon (prop on hand.R)
GRIP = V(0.2065, 0.0, 0.79)
def lance(hi):
    d = (J['forearm.R'][1] - J['upper_arm.R'][0]).normalized()   # seated rest: straight down the arm chain
    side = V(1, 0, 0) - d * d.x; side.normalize()
    a = GRIP + side * 0.042
    butt, tip = a - d * 0.62, a + d * 2.95
    L = (tip - butt).length
    tt = lambda s: s / L
    n = 40 if hi else 8
    prof = [(0, 0.020, 0.020, 0.020), (tt(0.55), 0.024, 0.024, 0.024), (tt(0.70), 0.020, 0.020, 0.020),
            (tt(L - 0.30), 0.015, 0.015, 0.015), (tt(L - 0.24), 0.012, 0.012, 0.012), (1.0, 0.012, 0.012, 0.012)]
    out = [limb('klance', [(0, butt), (1, tip - d * 0.24)], prof, n, 10 if hi else 6, fwd=V(0, 1, 0), slot='wood')]
    h0 = tip - d * 0.25
    out.append(limb('klance.h', [(0, h0), (0.25, h0 + d * 0.06), (1, tip)],
                    [(0, 0.014, 0.014, 0.014), (0.2, 0.011, 0.011, 0.011), (0.3, 0.020, 0.006, 0.006), (1, 0.001, 0.001, 0.001)],
                    12 if hi else 3, 8 if hi else 4, fwd=V(0, 1, 0), slot=PLATE, e=2.0))
    # swallow-tailed pennon behind the head (rest frame: -y hangs down once the lance is levelled)
    p0, p1 = tip - d * 0.30, tip - d * 0.62
    rows = []
    nr, nc = (16, 20) if hi else (3, 4)
    for i in range(nr + 1):
        u = i / nr
        q = p0.lerp(p1, u)
        Lf = 0.42 - 0.12 * abs(u - 0.5) * 2 * (1 if u > 0 else 0)   # swallow tail notch
        row = []
        for j in range(nc + 1):
            v = j / nc
            wave = (0.012 * math.sin(v * 5.0 + u)) if hi else 0.0
            row.append(q + V(0, -1, 0) * (0.012 + Lf * v) + side * wave + d * (0.08 * v * v))
        rows.append(row)
    secs = [[p + side * 0.0015 for p in r] + [p - side * 0.0015 for p in r][::-1] for r in rows]
    out.append(V3P.orient_out(grid_sweep('klance.p', secs, closed_u=True, cap0=True, cap1=True, slot='coat')))
    C.RIDER['tip'] = tuple(tip)
    return out

# ------------------------------------------------------------------ saddle, saddle cloth, sword (horse coords)
def saddle(hi):
    t = HZ.htree(); out = []
    # saddle cloth: team colour, double layer, under the saddle
    ys = np.linspace(0.20, -0.40, 26 if hi else 7)
    rows = []
    for y in ys:
        cv = HZ.side_curve(t, float(y), 0.010)
        if not cv: continue
        Lmax = 0.40 - 0.10 * (abs(float(y) + 0.10) / 0.30) ** 2
        k = 14 if hi else 4
        half = [HZ._at(cv, Lmax * j / k)[0] for j in range(k + 1)]
        row = [V(-p.x, p.y, p.z) for p in half[::-1]] + half[1:]
        rows.append(row)
    secs = [[p + V(0, 0, 0.004) if True else p for p in r] for r in rows]
    inner = [[V(p.x * 0.985, p.y, p.z - 0.006) for p in r] for r in rows]
    secs2 = [o + i[::-1] for o, i in zip(secs, inner)]
    out.append(HZ.H(V3P.orient_out(grid_sweep('kzcloth', secs2, closed_u=True, cap0=True, cap1=True,
                                              slot=(lambda c: 'lapel' if (abs(abs(c.x) - 0.0) > 0 and False) else 'coat')))))
    # seat panels (leather), pommel arch, wrap-round cantle (wood, leather-covered)
    seat = []
    for y in np.linspace(0.16, -0.24, 16 if hi else 5):
        cv = HZ.side_curve(t, float(y), 0.030)
        if not cv: continue
        k = 8 if hi else 3
        half = [HZ._at(cv, 0.20 * j / k)[0] for j in range(k + 1)]
        seat.append([V(-p.x, p.y, p.z) for p in half[::-1]] + half[1:])
    seat_in = [[V(p.x, p.y, p.z - 0.020) for p in r] for r in seat]
    out.append(HZ.H(V3P.orient_out(grid_sweep('kzsad', [o + i[::-1] for o, i in zip(seat, seat_in)], closed_u=True,
                                              cap0=True, cap1=True, slot='belt'))))
    n = 16 if hi else 6
    pom = [(k / n, V(0.13 * math.cos(math.pi * k / n), 0.17 + 0.012 * math.sin(math.pi * k / n),
                     1.365 + 0.17 * math.sin(math.pi * k / n))) for k in range(n + 1)]
    out.append(HZ.H(limb('kzsad.p', pom, [(0, 0.028, 0.016, 0.016), (0.5, 0.040, 0.016, 0.016), (1, 0.028, 0.016, 0.016)],
                         n, 8 if hi else 4, fwd=V(0, 1, 0), slot='wood')))
    can = []
    for k in range(n + 1):
        a = math.radians(lerp(-78, 78, k / n))
        can.append((k / n, V(0.17 * math.sin(a), -0.06 - 0.17 * math.cos(a), 1.465 - 0.03 * abs(math.sin(a)))))
    out.append(HZ.H(limb('kzsad.c', can, [(0, 0.012, 0.05, 0.05), (0.5, 0.014, 0.085, 0.085), (1, 0.012, 0.05, 0.05)],
                         n, 8 if hi else 4, fwd=V(0, 0, 1), slot='wood', e=2.4)))
    return out

def sword(hi):
    out = []
    sc0, sc1 = V(-0.262, -0.12, 1.33), V(-0.330, -0.86, 0.96)
    dv = (sc1 - sc0).normalized()
    path = [(0, sc0), (1, sc1)]
    out.append(HZ.H(limb('kzsc', path, [(0, 0.011, 0.024, 0.024), (0.9, 0.009, 0.018, 0.018), (1, 0.006, 0.010, 0.010)],
                         12 if hi else 4, 10 if hi else 5, fwd=V(-1, 0, 0), slot='belt', e=2.6)))
    out.append(HZ.H(limb('kzsc.ch', [(0, sc1 - dv * 0.05), (1, sc1 + dv * 0.01)], [(0, 0.012, 0.020, 0.020), (1, 0.007, 0.011, 0.011)],
                         2, 8 if hi else 4, fwd=V(-1, 0, 0), slot='metal')))   # chape
    g0 = sc0 - dv * 0.01
    side = dv.cross(V(-1, 0, 0)).normalized()
    out.append(HZ.H(limb('kzsc.gd', [(0, g0 - side * 0.10), (1, g0 + side * 0.10)], [(0, 0.008, 0.008, 0.008)],
                         4 if hi else 1, 6 if hi else 4, fwd=V(-1, 0, 0), slot=PLATE)))   # straight cross guard
    out.append(HZ.H(limb('kzsc.gr', [(0, g0), (1, g0 - dv * 0.11)], [(0, 0.014, 0.014, 0.014)], 4 if hi else 1,
                         8 if hi else 5, fwd=V(-1, 0, 0), slot='cartbox')))
    out.append(HZ.H(superellipsoid('kzsc.pm', g0 - dv * 0.125, (0.010, 0.026, 0.026), e=(2, 2), n=(12, 8) if hi else (6, 4),
                                   rot=dv.to_track_quat('X', 'Z').to_matrix(), slot=PLATE)))   # wheel pommel
    hip = VR.seat_point('hips', (-0.170, -0.02, 0.965))
    for u in (0.05, 0.30):
        p = sc0.lerp(sc1, u)
        out.append(HZ.H(limb('kzsc.sl', [(0, hip + V(0, 0, -0.01)), (1, p)], [(0, 0.008, 0.002, 0.002)], 2 if hi else 1, 4,
                             fwd=V(-1, 0, 0), slot='belt')))
    return out

def generic_tack(hi):
    """kit-3 tack minus the hussar-only items (scabbard + sabretache)."""
    parts = HZ.tack(hi); keep = []
    for o in parts:
        if o.name.startswith('hzsc') or o.name.startswith('hzst'):
            bpy.data.objects.remove(o)
        else:
            keep.append(o)
    return keep

def build_kit(hi, body_tree):
    parts = C.mh_parts(hi)
    head = [o for o in parts if o.name.startswith('mhhead')][0]
    if hi: _fit_helm(head)
    if not hi:
        cb = C.collar_band((2, 28)); set_slot(cb, MAIL); parts.append(cb)
    parts += surcoat_skirt(hi) + sword_belt(body_tree, hi) + poleyns(body_tree, hi) + spurs(body_tree, hi)
    parts += great_helm(hi) + shield(hi) + lance(hi)
    parts.append(HZ.horse_body(hi))
    parts += HZ.mane_tail(hi) + generic_tack(hi) + saddle(hi) + sword(hi)
    return parts
C.build_kit = build_kit
