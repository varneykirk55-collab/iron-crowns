"""Character refinement: clips for the semi-realistic c19 foot soldiers, authored as procedural poses on the
shared skeleton (char_rig). Feet are placed analytically (ground contact points move at exactly the sim speed ->
no foot sliding), arms are IK'd onto the musket / rammer grips, trunk is FK.
Clip lengths (24 fps) match the sim/battle_view contract: idle (loop), walk (24 = 1 s, 1.4 m), run (16, 2.4 m),
fire (48 = 2 s, play once; shot at ~0.3 s; present -> fire/recoil -> reload -> shoulder), melee (20 loop),
die (30 once), die_b (30 once, second death variant)."""
import math
from mathutils import Vector, Matrix, Euler, Quaternion
from char_geo import V, lerp, smoothstep
import char_rig as R

WALK_V, RUN_V = 1.4, 3.6
WALK_T, RUN_T = 1.0, 16 / 24.0

def ease(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def seg(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= b)

def lerpv(a, b, t):
    return V(a).lerp(V(b), t)

def rx(deg):
    return Matrix.Rotation(math.radians(deg), 3, 'X')

def prop_mtx(origin, ydir, ztop):
    y = V(ydir).normalized(); z = V(ztop); z = (z - y * z.dot(y)).normalized(); x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4(); m.translation = V(origin)
    return m

def blend_spec(a, b, t):
    """blend two pose specs (dicts) key by key"""
    if t <= 0: return a
    if t >= 1: return b
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if va is None: out[k] = vb; continue
        if vb is None: out[k] = va; continue
        if k == 'prop' and va[0] != vb[0] and 'mix' not in (va[0], vb[0]):
            out[k] = ('mix', va, vb, t)    # different parent frames: blended in world space by solve()
            continue
        out[k] = _blend(va, vb, t)
    return out

def _blend(va, vb, t):
    if isinstance(va, Matrix):
        return R.mlerp(va, vb, t)
    if isinstance(va, Vector):
        return va.lerp(vb, t)
    if isinstance(va, (int, float)):
        return lerp(va, vb, t)
    if isinstance(va, tuple) and va and isinstance(va[0], str):
        if va[0] != vb[0] or len(va) != len(vb):
            return va if t < 0.5 else vb
        return (va[0],) + tuple(_blend(x, y, t) for x, y in zip(va[1:], vb[1:]))
    if isinstance(va, (tuple, list)):
        if len(va) != len(vb): return va if t < 0.5 else vb
        return tuple(_blend(x, y, t) for x, y in zip(va, vb))
    if isinstance(va, str):
        return va if t < 0.5 else vb
    return va if t < 0.5 else vb

# ------------------------------------------------------------------ solver
HAND_REST = {}
def solve(spec):
    p = R.Pose()
    p.P['root'] = R.REST['root'].copy()
    p.fk('hips', spec.get('hipR', (0, 0, 0)), offset=spec.get('hip', (0, 0, 0)))
    p.fk('spine', spec.get('spine', (0, 0, 0)))
    p.fk('chest', spec.get('chest', (0, 0, 0)))
    p.fk('neck', spec.get('neck', (0, 0, 0)))
    p.fk('head', spec.get('head', (0, 0, 0)))
    p.fk('clav.R', spec.get('clavR', (0, 0, 0)))
    p.fk('clav.L', spec.get('clavL', (0, 0, 0)))
    frames = {'root': Matrix.Identity(4), 'hips': p.delta('hips'), 'chest': p.delta('chest')}
    pr = spec.get('prop', ('root', R.REST['prop']))
    if pr[0] == 'mix':
        _, (fa, Ma), (fb, Mb), tb = pr
        p.P['prop'] = R.mlerp(frames[fa] @ Ma, frames[fb] @ Mb, tb)
    else:
        p.P['prop'] = frames[pr[0]] @ pr[1]
    C3 = frames['chest'].to_3x3()
    for s, sx in (('R', 1), ('L', -1)):
        a = spec.get('arm' + s, ('fk', (0, 0, 0), (0, 0, 0), (0, 0, 0)))
        up, fo, ha = 'upper_arm.' + s, 'forearm.' + s, 'hand.' + s
        d0 = R.REST[ha].to_3x3() @ V(0, 1, 0)
        p0 = V(-sx, 0, 0)
        if a[0] == 'fk':
            p.fk(up, a[1]); p.fk(fo, a[2]); p.fk(ha, a[3])
        elif a[0] == 'grip':
            # ('grip', prop-local point, hand dir (chest-rest), palm normal (chest-rest), elbow pole (chest-rest))
            _, gl, d, pn, pole = a
            g = p.P['prop'] @ V(gl)
            d = (C3 @ V(d)).normalized(); pn = (C3 @ V(pn)).normalized()
            pn = (pn - d * pn.dot(d)).normalized()
            w = g - pn * 0.03 - d * 0.062
            p.limb(up, fo, ha, w, frames['chest'] @ V(pole), (1, 0, 0), end_frame=(d, pn), end_rest=(d0, p0))
        elif a[0] == 'ik':
            # ('ik', wrist (chest-rest), pole (chest-rest), hand dir, palm normal)
            _, w, pole, d, pn = a
            d = (C3 @ V(d)).normalized(); pn = (C3 @ V(pn)).normalized()
            p.limb(up, fo, ha, frames['chest'] @ V(w), frames['chest'] @ V(pole), (1, 0, 0), end_frame=(d, (pn - d * pn.dot(d)).normalized()), end_rest=(d0, p0))
    for s, sx in (('R', 1), ('L', -1)):
        ank, pitch, pole, yaw = spec['leg' + s]
        d0 = R.REST['foot.' + s].to_3x3() @ V(0, 1, 0)
        Q = Matrix.Rotation(math.radians(yaw), 3, 'Z') @ rx(pitch)
        p.limb('thigh.' + s, 'shin.' + s, 'foot.' + s, V(ank), V(pole), (-1, 0, 0),
               end_frame=(Q @ d0, Q @ V(1, 0, 0)), end_rest=(d0, V(1, 0, 0)))
    return p

# ------------------------------------------------------------------ feet
ANK = V(0, -0.012, 0.088)
HEEL_OFF = V(0, -0.062, -0.088)     # heel ground point - ankle
TOE_OFF = V(0, 0.132, -0.088)       # ball ground point - ankle
HT = TOE_OFF.y - HEEL_OFF.y

def foot_from_pivot(pivot, off, pitch):
    return V(pivot) - rx(pitch) @ off

def gait_foot(ph, x, v, T, beta, y_strike, lift, kick=0.0, strike_pitch=12.0, off_pitch=-38.0):
    """ph in [0,1): 0 = heel strike. Returns (ankle, pitch). Ground contact points move at -v (no slide)."""
    D = v * T * beta
    if ph < beta:
        u = ph / beta
        c = y_strike - D * u                     # heel ground y (moves backwards at -v)
        if u < 0.14:
            pt = strike_pitch * (1 - u / 0.14)
            return foot_from_pivot(V(x, c, 0), HEEL_OFF, pt), pt
        if u < 0.58:
            return foot_from_pivot(V(x, c, 0), HEEL_OFF, 0.0), 0.0
        pt = off_pitch * ((u - 0.58) / 0.42) ** 1.4
        return foot_from_pivot(V(x, c + HT, 0), TOE_OFF, pt), pt
    u = (ph - beta) / (1 - beta)
    a0 = foot_from_pivot(V(x, y_strike - D + HT, 0), TOE_OFF, off_pitch)
    a1 = foot_from_pivot(V(x, y_strike, 0), HEEL_OFF, strike_pitch)
    e = ease(u)
    a = a0.lerp(a1, e)
    a.z += lift * math.sin(math.pi * u) ** 0.9 + kick * math.sin(math.pi * min(1, u * 1.6)) ** 2
    a.y -= kick * 0.6 * math.sin(math.pi * min(1, u * 1.6)) ** 2
    pt = lerp(off_pitch, strike_pitch, ease(u * 1.2)) - 15 * math.sin(math.pi * u) * (kick > 0)
    return a, pt

def stand_legs(spread=0.105, fwdL=0.03, fwdR=-0.01, yaw=9):
    return {'legR': (V(spread, ANK.y + fwdR, ANK.z), 0.0, V(spread, 1.0, 0.5), yaw),
            'legL': (V(-spread, ANK.y + fwdL, ANK.z), 0.0, V(-spread, 1.0, 0.5), -yaw)}

# ------------------------------------------------------------------ musket holds (chest-rest coords)
def shoulder_arms(breath=0.0):
    """musket on the left shoulder, butt cupped in the left hand, barrel slanted back"""
    butt = V(-0.185, 0.165, 1.0)
    top = V(-0.16, -0.01, 1.47)
    d = (top - butt).normalized()
    M = prop_mtx(butt + d * 0.35, d, V(-1, 0.25, 0.1))       # barrel top faces outward-left
    grip = ('grip', V(0, -0.31, -0.07), V(0.25, 0.3, 0.6), V(0.0, -0.35, 0.95), V(-0.5, -0.4, 1.1))
    return {'prop': ('chest', M), 'armL': grip}

def order_arms():
    pass

def present(recoil=0.0, aim=1.0):
    """musket levelled at the right shoulder (root frame), cheek on the stock"""
    butt = V(0.11, 0.06 - 0.06 * recoil, 1.385 + 0.01 * recoil)
    d = V(-0.07, 1, 0.03 + 0.18 * recoil).normalized()
    M = prop_mtx(butt + d * 0.35, d, V(0, 0, 1))
    gR = ('grip', V(0, 0.0, -0.01), V(0.0, 0.35, -1), V(-1, 0, 0.2), V(0.6, -0.3, 1.0))
    gL = ('grip', V(0, 0.15, -0.02), V(0.9, 0.3, -0.1), V(0, 0, 1), V(-0.1, 0.1, 0.6))
    return {'prop': ('root', M), 'armR': gR, 'armL': gL}

def charge(thrust=0.0, height=0.0):
    """charge bayonet: musket levelled at the waist, butt by the right hip, bayonet forward (root frame)"""
    butt = V(0.13, -0.26 + 0.26 * thrust, 1.0 + height + 0.06 * thrust)
    d = V(-0.12, 1, 0.12 - 0.05 * thrust).normalized()
    M = prop_mtx(butt + d * 0.35, d, V(0, 0, 1))
    gR = ('grip', V(0, 0.0, -0.01), V(0.0, 0.4, -1), V(-1, 0, 0.1), V(0.7, -0.6, 0.9))
    gL = ('grip', V(0, 0.30, -0.02), V(0.85, 0.35, -0.2), V(0, 0, 1), V(-0.5, 0.2, 0.7))
    return {'prop': ('root', M), 'armR': gR, 'armL': gL}

def port_arms():
    """carried diagonally across the chest at the run (chest frame)"""
    wrist = V(0.13, 0.17, 1.06)
    d = V(-0.5, 0.12, 0.85).normalized()
    M = prop_mtx(wrist, d, V(0, 1, 0))
    gR = ('grip', V(0, 0.0, -0.01), V(-0.3, 0.3, -0.9), V(-0.6, 0.2, 0.4), V(0.7, -0.5, 0.9))
    gL = ('grip', V(0, 0.42, -0.02), V(0.6, 0.4, -0.3), V(0.5, 0.2, 0.8), V(-0.6, -0.3, 1.0))
    return {'prop': ('chest', M), 'armR': gR, 'armL': gL}

def reload_pos(stage):
    """musket upright in front of the left side, butt grounded (root frame); stage = ram height 0..1"""
    butt = V(-0.09, 0.34, 0.0)
    d = V(0.03, -0.02, 1).normalized()
    M = prop_mtx(butt - d * -0.35 + V(0, 0, 0), d, V(0, 1, 0))
    # musket origin = butt + 0.35 along the axis
    M.translation = butt + d * 0.35
    gL = ('grip', V(0, 0.60, -0.02), V(0.4, 0.5, 0.0), V(1, 0, 0), V(-0.6, -0.2, 1.0))
    ram = lerpv(V(-0.05, 0.36, 1.60), V(-0.055, 0.35, 1.48), stage)
    aR = ('ik', ram + V(0.02, -0.01, 0.07), V(0.5, -0.1, 1.0), V(-0.1, 0.1, -1), V(0, 0, -1))
    return {'prop': ('root', M), 'armL': gL, 'armR': aR}

def prime_pos(hand):
    """musket held low across the body (half-cock / priming), right hand at cartridge box(0) -> mouth(1) (root)"""
    wrist = V(0.12, 0.22, 1.02)
    d = V(-0.25, 1, 0.55).normalized()
    M = prop_mtx(wrist, d, V(0, 0, 1))
    gL = ('grip', V(0, 0.3, -0.02), V(0.8, 0.3, -0.2), V(0, 0, 1), V(-0.6, 0.0, 0.6))
    box = V(0.2, -0.08, 1.08); mouth = V(0.04, 0.1, 1.58); pan = V(0.08, 0.27, 1.1)
    if hand < 1:
        w = box.lerp(mouth, ease(hand))
    else:
        w = mouth.lerp(pan, ease(hand - 1))
    aR = ('ik', w + V(0.0, 0.0, 0.05), V(0.7, -0.4, 0.8), V(0.0, 0.3, -1), V(-1, 0, 0))
    return {'prop': ('root', M), 'armL': gL, 'armR': aR}

def free_arm_R(swing=0.0, out=0.0, bend=12.0):
    return {'armR': ('fk', (swing, 0, 4 + out), (-bend - max(0, swing) * 0.6, 0, 0), (0, 0, 0))}

def free_arm_L(swing=0.0, out=0.0, bend=12.0):
    return {'armL': ('fk', (swing, 0, -4 - out), (-bend - max(0, swing) * 0.6, 0, 0), (0, 0, 0))}

def merge(*ds):
    o = {}
    for d in ds:
        o.update(d)
    return o

# ------------------------------------------------------------------ clips (t in [0,1))
def idle(t, style='musket'):
    w = math.sin(2 * math.pi * t)
    b = math.sin(2 * math.pi * 3 * t)
    spec = merge(stand_legs(), {
        'hip': V(0.016 * w, 0.0, -0.012 - 0.004 * abs(w)), 'hipR': (0, 1.2 * w, 1.5 * w),
        'spine': (-1.0, -1.0 * w, 0), 'chest': (0.8 * b - 1.0, -0.6 * w, -1.2 * w), 'neck': (-2, 0, 0),
        'head': (-2 + 1.5 * math.sin(2 * math.pi * (t + 0.3)), 0, 7 * math.sin(2 * math.pi * (t + 0.15))),
        'clavR': (0, 0, 0.8 * b), 'clavL': (0, 0, -0.8 * b)})
    if style == 'rammer':
        spec.update(rammer_order()); spec.update(free_arm_L(2 * w, 2, 10))
    else:
        spec.update(shoulder_arms()); spec.update(free_arm_R(3 * w, 2, 10))
    return spec

def walk(t, style='musket'):
    yR = 0.29; beta = 0.6
    aR, pR = gait_foot(t % 1.0, 0.1, WALK_V, WALK_T, beta, yR, 0.10)
    aL, pL = gait_foot((t + 0.5) % 1.0, -0.1, WALK_V, WALK_T, beta, yR, 0.10)
    c2 = math.cos(4 * math.pi * (t - beta / 2))
    s1 = math.sin(2 * math.pi * (t + 0.12))
    spec = {
        'legR': (aR, pR, V(0.1, 1.0, 0.5), 6), 'legL': (aL, pL, V(-0.1, 1.0, 0.5), -6),
        'hip': V(0.012 * math.sin(2 * math.pi * (t - 0.05)), 0.0, -0.036 + 0.018 * c2), 'hipR': (0, 1.5 * s1, 6 * s1),
        'spine': (-3, 0, -3 * s1), 'chest': (-1, 0, -3 * s1), 'neck': (0, 0, 0), 'head': (-2, 0, 2 * s1)}
    if style == 'rammer':
        spec.update(rammer_carry()); spec.update(free_arm_L(-20 * s1, 3, 14))
    else:
        spec.update(shoulder_arms()); spec.update(free_arm_R(20 * s1, 3, 14))
    return spec

def run(t, style='musket'):
    yR = 0.25; beta = 0.33
    aR, pR = gait_foot(t % 1.0, 0.1, RUN_V, RUN_T, beta, yR, 0.16, kick=0.16, strike_pitch=6, off_pitch=-45)
    aL, pL = gait_foot((t + 0.5) % 1.0, -0.1, RUN_V, RUN_T, beta, yR, 0.16, kick=0.16, strike_pitch=6, off_pitch=-45)
    c2 = math.cos(4 * math.pi * (t - beta / 2))
    s1 = math.sin(2 * math.pi * (t + 0.1))
    spec = {
        'legR': (aR, pR, V(0.1, 1.0, 0.5), 4), 'legL': (aL, pL, V(-0.1, 1.0, 0.5), -4),
        'hip': V(0.01 * math.sin(2 * math.pi * t), 0.03, -0.045 - 0.025 * c2), 'hipR': (-6, 0, 8 * s1),
        'spine': (-6, 0, -5 * s1), 'chest': (-4, 0, -5 * s1), 'neck': (6, 0, 0), 'head': (4, 0, 3 * s1)}
    if style == 'rammer':
        spec.update(rammer_carry(run=True)); spec.update(free_arm_L(-35 * s1, 6, 70))
    else:
        spec.update(port_arms())
    return spec

def fire(t, style='musket'):
    """2.0 s: 0-0.25 present, 0.30 fire+recoil, 0.55 hold/lower, 0.6-1.05 prime (cartridge->mouth->pan),
    1.05-1.6 load + ram, 1.6-2.0 return to shoulder arms"""
    s = t * 2.0
    legs = stand_legs(0.13, 0.12, -0.08, 12)
    base = merge(legs, {'hip': V(0.0, 0.0, -0.02), 'hipR': (0, 0, -18)})
    aim = merge(base, {'spine': (-3, 0, -6), 'chest': (-3, 0, -6), 'neck': (-6, 6, 10), 'head': (-4, 10, 12),
                       'clavR': (0, 0, 6), 'clavL': (0, 0, 0)})
    if s < 0.25:                     # come up to present from shoulder arms
        e = ease(s / 0.25)
        a = merge(base, {'spine': (-1, 0, 0), 'chest': (-1, 0, 0)}, shoulder_arms(), free_arm_R(0, 2, 12))
        return blend_spec(a, merge(aim, present(0.0)), e)
    if s < 0.6:                      # shot at 0.30: recoil kick, settle
        r = 0.0 if s < 0.29 else math.exp(-(s - 0.29) * 14) * min(1, (s - 0.29) / 0.03)
        sp = merge(aim, present(r))
        sp['chest'] = (-3 + 6 * r, 0, -6 + 3 * r); sp['head'] = (-4 + 6 * r, 10, 12)
        sp['hip'] = V(0, -0.015 * r, -0.02)
        if s > 0.45:
            sp = blend_spec(sp, merge(base, {'spine': (-6, 0, -3), 'chest': (-4, 0, -2), 'neck': (-8, 0, 0), 'head': (-6, 0, 0)}, prime_pos(0.0)), ease((s - 0.45) / 0.15))
        return sp
    pose_p = lambda h: merge(base, {'spine': (-6, 0, -3), 'chest': (-4, 0, -2), 'neck': (-8, 0, 0), 'head': (-8 + 4 * min(h, 1), 0, 0)}, prime_pos(h))
    if s < 1.05:                     # prime: box -> mouth -> pan
        h = (s - 0.6) / 0.45 * 2.0
        return pose_p(h)
    pose_r = lambda st: merge(base, {'hipR': (0, 0, -8), 'spine': (-8, 0, 2), 'chest': (-6, 0, 4), 'neck': (-10, 0, 0), 'head': (-14, 0, 4)}, reload_pos(st))
    if s < 1.15:
        return blend_spec(pose_p(2.0), pose_r(0.0), ease((s - 1.05) / 0.1))
    if s < 1.6:                      # ram twice
        st = 0.5 - 0.5 * math.cos(2 * math.pi * 2 * (s - 1.15) / 0.45)
        return pose_r(st)
    e = ease((s - 1.6) / 0.4)
    end = merge(stand_legs(), {'hip': V(0, 0, -0.012), 'spine': (-1, 0, 0), 'chest': (-1, 0, 0), 'neck': (-2, 0, 0), 'head': (-2, 0, 0)},
                shoulder_arms(), free_arm_R(0, 2, 10))
    return blend_spec(pose_r(0.0), end, e)

def melee(t, style='musket'):
    if style == 'rammer':
        return rammer_work(t)
    k = math.sin(2 * math.pi * t)
    th = max(0.0, k) ** 0.7
    legs = {'legR': (V(0.14, -0.2, ANK.z), 0.0, V(0.2, 1, 0.5), 22), 'legL': (V(-0.1, 0.24, ANK.z), 0.0, V(-0.1, 1, 0.5), -4)}
    sp = merge(legs, {'hip': V(0.0, 0.02 + 0.07 * th, -0.07 - 0.02 * th), 'hipR': (-4 - 6 * th, 0, -14 + 6 * th),
                      'spine': (-6 - 6 * th, 0, -6 + 4 * th), 'chest': (-4 - 4 * th, 0, -6 + 4 * th), 'neck': (6 + 4 * th, 4, 8), 'head': (4 + 4 * th, 0, 6)},
               charge(thrust=th * 1.0 + 0.1 * min(0, k)))
    return sp

def keys(t, ks):
    """piecewise eased blend of key pose specs [(t0, spec), ...]"""
    if t <= ks[0][0]: return ks[0][1]
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t <= t1:
            return blend_spec(a, b, ease((t - t0) / (t1 - t0)))
    return ks[-1][1]

def _fk(u, f, h=(0, 0, 0)):
    return ('fk', u, f, h)

def die(t, style='musket'):
    """hit in the chest: recoil, knees buckle and sit back, fall onto the back"""
    k0 = idle(0.0, style)
    k0 = dict(k0); k0.pop('prop', None)
    if k0['armL'][0] != 'fk': k0['armL'] = _fk((-10, 0, -20), (-60, 0, 0))
    if k0['armR'][0] != 'fk': k0['armR'] = _fk((-10, 0, 20), (-60, 0, 0))
    k1 = merge(stand_legs(0.11, 0.04, -0.06, 10), {'hip': V(0, -0.05, -0.03), 'hipR': (8, 0, -8), 'spine': (6, 0, 0), 'chest': (10, 0, 8),
               'neck': (10, 0, 0), 'head': (16, 0, 6), 'clavR': (0, 0, 8), 'clavL': (0, 0, -8),
               'armR': _fk((30, 0, 35), (-30, 0, 0)), 'armL': _fk((25, 0, -40), (-45, 0, 0))})
    k2 = {'legR': (V(0.12, 0.0, ANK.z), 0.0, V(0.2, 1.0, 0.5), 14), 'legL': (V(-0.12, 0.06, ANK.z), 0.0, V(-0.2, 1.0, 0.5), -10),
          'hip': V(0, -0.2, -0.46), 'hipR': (28, 0, -10), 'spine': (8, 0, 0), 'chest': (6, 0, 6), 'neck': (-8, 0, 0), 'head': (-6, 0, 10),
          'clavR': (0, 0, 4), 'clavL': (0, 0, -4),
          'armR': _fk((25, 0, 40), (-20, 0, 0)), 'armL': _fk((15, 0, -40), (-25, 0, 0))}
    k3 = {'legR': (V(0.15, 0.30, 0.075), 70.0, V(0.3, 0.6, 1.0), 20), 'legL': (V(-0.13, 0.22, 0.08), 65.0, V(-0.3, 0.6, 1.0), -14),
          'hip': V(0, -0.5, -0.74), 'hipR': (84, 0, -12), 'spine': (4, 0, 0), 'chest': (2, 0, 4), 'neck': (-6, 0, 0), 'head': (-4, 0, 25),
          'clavR': (0, 0, 0), 'clavL': (0, 0, 0),
          'armR': _fk((20, 0, 60), (-15, 0, 0)), 'armL': _fk((10, 0, -55), (-30, 0, 0))}
    sp = dict(keys(t, [(0.0, k0), (0.18, k1), (0.5, k2), (1.0, k3)]))
    sp['prop'] = _drop(None, t, side=1)
    return sp

def die_b(t, style='musket'):
    """doubled over, drop to the knees, pitch forward onto the face"""
    k0 = idle(0.0, style)
    k0 = dict(k0); k0.pop('prop', None)
    if k0['armL'][0] != 'fk': k0['armL'] = _fk((-10, 0, -20), (-60, 0, 0))
    if k0['armR'][0] != 'fk': k0['armR'] = _fk((-10, 0, 20), (-60, 0, 0))
    k1 = merge(stand_legs(0.11, 0.06, -0.02, 10), {'hip': V(0, 0.03, -0.06), 'hipR': (-12, 0, 6), 'spine': (-16, 0, 0), 'chest': (-14, 0, -6),
               'neck': (-6, 0, 0), 'head': (-10, 0, 0),
               'armR': _fk((-35, 0, -8), (-75, 0, 0)), 'armL': _fk((-30, 0, 10), (-80, 0, 0))})
    k2 = {'legR': (V(0.12, -0.36, 0.11), -80.0, V(0.12, 1.0, -0.3), 8), 'legL': (V(-0.12, -0.34, 0.11), -80.0, V(-0.12, 1.0, -0.3), -8),
          'hip': V(0, 0.05, -0.45), 'hipR': (-14, 0, 4), 'spine': (-14, 0, 0), 'chest': (-12, 0, -4), 'neck': (-4, 0, 0), 'head': (-8, 0, 0),
          'armR': _fk((-25, 0, 0), (-50, 0, 0)), 'armL': _fk((-20, 0, 6), (-55, 0, 0))}
    k3 = {'legR': (V(0.13, -0.62, 0.07), -95.0, V(0.13, -0.3, -1.0), 8), 'legL': (V(-0.15, -0.58, 0.08), -95.0, V(-0.15, -0.3, -1.0), -12),
          'hip': V(0, 0.2, -0.79), 'hipR': (-84, 0, 6), 'spine': (-4, 0, 0), 'chest': (-2, 0, -4), 'neck': (16, 0, 0), 'head': (14, 0, -40),
          'armR': _fk((-30, 0, 30), (-30, 0, 0)), 'armL': _fk((-10, 0, -20), (-15, 0, 0))}
    sp = dict(keys(t, [(0.0, k0), (0.22, k1), (0.55, k2), (1.0, k3)]))
    sp['prop'] = _drop(None, t, side=-1)
    return sp

def _drop(prop, s, side=1):
    """musket released: falls and lands flat beside the body (root frame)"""
    p0 = idle_prop_world()
    p1 = prop_mtx(V(0.42 * side, 0.15 if side > 0 else 0.35, 0.025), V(0.15 * side, 1, 0), V(side, 0, 0.6))
    e = seg(s, 0.05, 0.55) ** 1.6
    return ('root', R.mlerp(p0, p1, e))

_IDLE_PROP = None
def idle_prop_world():
    global _IDLE_PROP
    if _IDLE_PROP is None:
        _IDLE_PROP = solve(idle(0.0)).P['prop'].copy()
    return _IDLE_PROP

# ------------------------------------------------------------------ artillery crew (rammer)
def rammer_order():
    """rammer stood upright on the right side, held in the right hand"""
    base = V(0.32, 0.12, 0.0)
    d = V(0.0, 0.0, 1)
    M = prop_mtx(base + d * 1.12, d, V(0, 1, 0))
    aR = ('grip', V(0, -0.02, 0), V(0, 0.2, -1), V(-1, 0, 0), V(0.6, -0.4, 1.0))
    return {'prop': ('root', M), 'armR': aR}

def rammer_carry(run=False):
    """carried at the trail, slanting forward, right hand"""
    w = V(0.27, 0.05 if not run else 0.12, 0.92)
    d = V(0.02, 1, 0.35 if run else 0.25).normalized()
    M = prop_mtx(w, d, V(0, 0, 1))
    aR = ('grip', V(0, 0.0, 0), V(0, 0.2, -1), V(-1, 0, 0), V(0.7, -0.5, 1.0))
    return {'prop': ('chest' if run else 'root', M), 'armR': aR}

def rammer_work(t):
    """ramming / sponging the bore: both hands on the staff, pushing forward and back (loop)"""
    k = 0.5 - 0.5 * math.cos(2 * math.pi * t)
    legs = {'legR': (V(0.16, -0.18, ANK.z), 0.0, V(0.2, 1, 0.5), 20), 'legL': (V(-0.1, 0.22, ANK.z), 0.0, V(-0.1, 1, 0.5), -6)}
    w = V(0.06, 0.02 + 0.3 * k, 1.1 - 0.03 * k)
    d = V(0.02, 1, -0.08).normalized()
    M = prop_mtx(w, d, V(0, 0, 1))
    aR = ('grip', V(0, -0.0, 0), V(0.5, 0.2, -0.8), V(-0.6, 0, 0.6), V(0.7, -0.6, 0.8))
    aL = ('grip', V(0, 0.3, 0), V(0.8, 0.3, -0.4), V(0, 0, 1), V(-0.6, -0.2, 0.6))
    return merge(legs, {'hip': V(0, 0.02 + 0.06 * k, -0.06 - 0.02 * k), 'hipR': (-4 - 6 * k, 0, -10),
                        'spine': (-8 - 4 * k, 0, -4), 'chest': (-6 - 6 * k, 0, -4), 'neck': (8, 0, 4), 'head': (6, 0, 4),
                        'prop': ('root', M), 'armR': aR, 'armL': aL})

# name, frames, loop, fn(t, style)
CLIPS = [('idle', 96, True, idle), ('walk', 24, True, walk), ('run', 16, True, run), ('fire', 48, False, fire),
         ('melee', 20, True, melee), ('die', 30, False, die), ('die_b', 30, False, die_b)]
