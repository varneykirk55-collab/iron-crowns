"""Rob / cavalry overhaul: HX horse locomotion + rider sync + mounted combat, baked to VAT (multi-layer LBS).

Clip rows are documented in docs/cav/HX_CLIPS.md (generated).  Phase 0 of every gait cycle = right-hind footfall.
Hooves are IK-planted: in stance a toe moves at -v in the root frame (= fixed on the ground while the root moves at
+v), so playback speed = ground speed / v_nom gives no foot sliding."""
import math, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector, Matrix, Euler, Quaternion
import horse_rig as H
from horse_rig import V, rot, about, frame_from
import char_rig as CR

FPS = 24
LEGS = ('fR', 'fL', 'hR', 'hL')
SX = {'R': 1, 'L': -1}
L_HOOF = (H.TAIL['hoof_f.R'] - H.HEAD['hoof_f.R']).length
L_PAST_F = H.blen('fetlock_f.R'); L_CAN_F = H.blen('cannon_f.R')
L_PAST_H = H.blen('fetlock_h.R'); L_CAN_H = H.blen('cannon_h.R')
TOE0 = {'f': H.TAIL['hoof_f.R'].y, 'h': H.TAIL['hoof_h.R'].y}
HOOF_REST = math.degrees(math.atan2(0.08, 0.09))          # coronet->toe angle from vertical (41.6)
PAST_REST_F = math.degrees(math.atan2(0.06, 0.14)); PAST_REST_H = math.degrees(math.atan2(0.05, 0.14))
CAN_REST_F = 0.0; CAN_REST_H = math.degrees(math.atan2(0.02, 0.31))

def sm(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)

def lerp(a, b, t):
    return a + (b - a) * t

def dirv(theta):
    """unit vector theta degrees from straight down towards +Y (root frame sagittal plane)"""
    t = math.radians(theta)
    return V(0, math.sin(t), -math.cos(t))

# ------------------------------------------------------------------ gaits
# off = footfall phase of each leg (unwrapped so parameters blend continuously); duty = stance fraction
GAITS = {
    'stand':  dict(F=26, v=0.0, duty=1.0, off={'hR': 0.0, 'fR': 0.25, 'hL': 0.5, 'fL': 0.75}, lf=0.0, lh=0.0, fold=0, hfold=0, pf=0, load=2, reach=0.0),
    'walk':   dict(F=26, v=1.10, duty=0.62, off={'hR': 0.0, 'fR': 0.25, 'hL': 0.5, 'fL': 0.75}, lf=0.10, lh=0.08, fold=40, hfold=20, pf=35, load=8, reach=0.03),
    'trot':   dict(F=17, v=2.20, duty=0.42, off={'hR': 0.0, 'fR': 0.5, 'hL': 0.5, 'fL': 1.0}, lf=0.17, lh=0.13, fold=75, hfold=35, pf=55, load=14, reach=0.06),
    'canter': dict(F=14, v=4.00, duty=0.36, off={'hR': 0.0, 'fR': 0.27, 'hL': 0.27, 'fL': 0.5}, lf=0.24, lh=0.17, fold=90, hfold=45, pf=65, load=20, reach=0.10),
    'gallop': dict(F=12, v=6.00, duty=0.27, off={'hR': 0.0, 'fR': 0.38, 'hL': 0.12, 'fL': 0.5}, lf=0.28, lh=0.22, fold=100, hfold=55, pf=75, load=26, reach=0.16),
}
GAITS['charge'] = dict(GAITS['gallop'])
GAIT_ORDER = ['stand', 'walk', 'trot', 'canter', 'gallop', 'charge']
NUMK = ('F', 'v', 'duty', 'lf', 'lh', 'fold', 'hfold', 'pf', 'load', 'reach')

def gblend(a, b, t):
    A, B = GAITS[a], GAITS[b]
    g = {k: lerp(A[k], B[k], t) for k in NUMK}
    g['off'] = {l: lerp(A['off'][l], B['off'][l], t) for l in LEGS}
    return g

# body / rider channels per gait as a function of phase p in [0,1)
def channels(name, p, variant):
    c = 2 * math.pi
    ch = dict(z=0.0, y=0.0, x=0.0, pitch=0.0, roll=0.0, yaw=0.0, pelvis=0.0, spine=0.0, neck=0.0, neck_yaw=0.0, head=0.0,
              tail=0.0, tail_yaw=0.0, ear=0.0, jaw=0.0, breath=0.0,
              r_dz=0.0, r_dy=0.0, r_lean=0.0, r_pitch=0.0, r_roll=0.0, r_yaw=0.0, r_head=0.0, hand_dy=0.0, hand_dz=0.0, sag=0.10)
    kn = variant == 'med_knight'; hu = variant == 'c19_hussar'
    if name == 'stand':
        ch['breath'] = math.sin(c * p)
        ch['z'] = 0.004 * math.sin(c * p)
        ch['x'] = 0.012 * math.sin(c * p + 0.6)
        ch['roll'] = -0.8 * math.sin(c * p + 0.6)
        ch['neck'] = -4 + 3.0 * math.sin(c * p + 1.2)
        ch['neck_yaw'] = 5.0 * math.sin(c * p)
        ch['head'] = 2.0 * math.sin(c * p * 2 + 0.3)
        ch['tail_yaw'] = 14.0 * math.sin(c * p * 2)
        ch['tail'] = -4.0
        ch['ear'] = 18.0 * max(0.0, math.sin(c * (p - 0.55) * 3)) if 0.55 < p < 0.72 else 0.0
        ch['r_lean'] = 2.0; ch['r_yaw'] = 3.0 * math.sin(c * p + 2.0)
        ch['sag'] = 0.12
    elif name == 'walk':
        ch['z'] = 0.012 * math.cos(2 * c * (p - 0.12))
        ch['pitch'] = 0.8 * math.sin(2 * c * p)
        ch['roll'] = 1.6 * math.sin(c * (p - 0.05))
        ch['yaw'] = 1.2 * math.sin(c * (p - 0.2))
        ch['x'] = 0.008 * math.sin(c * (p - 0.05))
        ch['neck'] = -6 + 5.0 * math.cos(2 * c * (p - 0.30))
        ch['head'] = -2.0 * math.cos(2 * c * (p - 0.30))
        ch['neck_yaw'] = 2.0 * math.sin(c * p)
        ch['tail_yaw'] = 7.0 * math.sin(c * (p - 0.15)); ch['tail'] = -2.0
        ch['pelvis'] = 1.0 * math.sin(2 * c * p)
        ch['r_pitch'] = 3.0 * math.sin(2 * c * (p - 0.1)); ch['r_roll'] = -1.2 * math.sin(c * (p - 0.05)); ch['r_lean'] = 2.0
        ch['r_yaw'] = 3.0 * math.sin(c * (p - 0.05))
        ch['hand_dy'] = 0.035 * math.cos(2 * c * (p - 0.30)); ch['sag'] = 0.10
    elif name == 'trot':
        ch['z'] = -0.035 * math.cos(2 * c * (p - 0.21))
        ch['pitch'] = 0.8 * math.sin(2 * c * (p - 0.21))
        ch['roll'] = 1.2 * math.sin(c * (p - 0.1))
        ch['neck'] = -2.0 + 1.5 * math.cos(2 * c * (p - 0.30))
        ch['head'] = 2.0
        ch['tail'] = 2.0 + 7.0 * math.cos(2 * c * (p - 0.33)); ch['tail_yaw'] = 4 * math.sin(c * p)
        ch['pelvis'] = 1.5 * math.sin(2 * c * (p - 0.21))
        ch['spine'] = 0.8 * math.cos(2 * c * (p - 0.21))
        if hu:   # rising (posting) trot: up on one diagonal, sit on the other
            u = 0.5 - 0.5 * math.cos(c * (p - 0.06))
            ch['r_dz'] = 0.085 * u; ch['r_dy'] = 0.05 * u; ch['r_lean'] = 10.0 + 6.0 * u
            ch['r_pitch'] = 0.0
        else:    # sitting trot: hips absorb, torso damps the bounce
            ch['r_dz'] = 0.018 * math.cos(2 * c * (p - 0.24)); ch['r_lean'] = 4.0 if kn else 6.0
            ch['r_pitch'] = -2.5 * math.cos(2 * c * (p - 0.24))
        ch['hand_dz'] = -0.6 * ch['r_dz']; ch['sag'] = 0.08
    elif name == 'canter':
        ch['pitch'] = 5.0 * math.cos(c * (p - 0.12))
        ch['z'] = 0.045 * math.cos(c * (p - 0.88))
        ch['roll'] = 1.0 * math.sin(c * p)
        ch['yaw'] = -2.0
        ch['pelvis'] = 4.0 * math.cos(c * (p - 0.90))
        ch['spine'] = 2.0 * math.cos(c * (p - 0.90))
        ch['neck'] = -4.0 + 7.0 * math.cos(c * (p - 0.95))
        ch['head'] = -3.0 * math.cos(c * (p - 0.95))
        ch['tail'] = 8.0 + 8.0 * math.cos(c * (p - 0.2))
        ch['r_pitch'] = -0.55 * 5.0 * math.cos(c * (p - 0.12)) + 3.0 * math.sin(c * (p - 0.1))
        ch['r_lean'] = 6.0 if not hu else 10.0
        ch['r_dz'] = 0.012 * math.cos(c * (p - 0.1)); ch['r_dy'] = 0.015 * math.sin(c * p)
        ch['hand_dy'] = 0.06 * math.cos(c * (p - 0.95)); ch['sag'] = 0.07
    elif name in ('gallop', 'charge'):
        ch['pitch'] = 4.5 * math.cos(c * (p - 0.10))
        ch['z'] = 0.055 * math.cos(c * (p - 0.90))
        ch['roll'] = 0.8 * math.sin(c * p)
        ch['yaw'] = -1.5
        ch['pelvis'] = 9.0 * math.cos(c * (p - 0.90))          # tuck (gathered) in suspension, extend at push-off
        ch['spine'] = 4.0 * math.cos(c * (p - 0.90))
        ch['neck'] = -10.0 + 10.0 * math.cos(c * (p - 0.95))
        ch['head'] = 4.0 - 5.0 * math.cos(c * (p - 0.95))
        ch['tail'] = 22.0 + 8.0 * math.cos(c * (p - 0.25)); ch['tail_yaw'] = 3 * math.sin(c * p)
        ch['ear'] = -10.0
        if hu:   # light cavalry: half seat, out of the saddle, forward
            ch['r_dz'] = 0.06 + 0.012 * math.cos(c * (p - 0.15)); ch['r_dy'] = 0.07; ch['r_lean'] = 26.0
        elif kn:
            ch['r_dz'] = 0.012 * math.cos(c * (p - 0.15)); ch['r_dy'] = 0.02; ch['r_lean'] = 10.0
        else:
            ch['r_dz'] = 0.035 + 0.012 * math.cos(c * (p - 0.15)); ch['r_dy'] = 0.05; ch['r_lean'] = 18.0
        ch['r_pitch'] = -0.6 * 4.5 * math.cos(c * (p - 0.10))
        ch['hand_dy'] = 0.09 * math.cos(c * (p - 0.95)); ch['sag'] = 0.04
        if name == 'charge':
            ch['neck'] -= 6.0; ch['head'] -= 4.0; ch['ear'] = -35.0; ch['pitch'] -= 1.5
            ch['r_lean'] += 8.0; ch['tail'] += 6.0
            if kn:
                ch['r_lean'] = 16.0; ch['r_dz'] = 0.01
    return ch

def ch_blend(a, b, t):
    return {k: lerp(a[k], b[k], t) for k in a}

# ------------------------------------------------------------------ leg simulator
class LegSim:
    """per-leg stance/swing state machine integrated over a clip (root frame, Y forward)."""
    def __init__(self, leg):
        self.leg = leg; self.kind = leg[0]; self.side = leg[1]
        self.stance = True
        self.toe = TOE0[self.kind]
        self.lift = self.toe
        self.y0 = TOE0[self.kind]

    def neutral(self, g):
        return TOE0[self.kind] + (g['reach'] * (0.6 if self.kind == 'f' else 1.0))

    def step(self, g, ph_leg, dt, T):
        D = g['v'] * T * g['duty']
        st = ph_leg < g['duty'] - 1e-9 or g['duty'] >= 0.999
        if self.stance and not st:          # lift-off
            self.lift = self.toe
        if (not self.stance) and st:        # footfall
            self.toe = self.neutral(g) + D / 2
        self.stance = st
        if st:
            self.toe -= g['v'] * dt
        return st

    def _chain_K(self, toe_y, toe_z, th_h, th_p, th_c):
        f = self.kind == 'f'
        toe = V(0, toe_y, toe_z)
        C = toe - dirv(th_h) * L_HOOF
        F = C - dirv(th_p) * (L_PAST_F if f else L_PAST_H)
        return toe, F - dirv(th_c) * (L_CAN_F if f else L_CAN_H)

    def _toe_from_K(self, K, th_h, th_p, th_c):
        f = self.kind == 'f'
        t = K + dirv(th_c) * (L_CAN_F if f else L_CAN_H) + dirv(th_p) * (L_PAST_F if f else L_PAST_H) + dirv(th_h) * L_HOOF
        return t.y, t.z

    def sample(self, g, ph_leg):
        """returns (toe y, toe z, theta_hoof, theta_pastern, theta_cannon) in the root frame"""
        f = self.kind == 'f'
        duty = g['duty']
        past_rest = PAST_REST_F if f else PAST_REST_H
        can_rest = CAN_REST_F if f else CAN_REST_H
        if self.stance:
            s = ph_leg / duty if duty < 0.999 else 0.5
            load = math.sin(math.pi * min(s, 1.0))
            bo = sm((s - 0.80) / 0.20) if duty < 0.999 else 0.0     # breakover: heel up, pivot on the toe
            th_h = lerp(HOOF_REST, -8.0, bo)
            th_p = lerp(past_rest + g['load'] * load, -6.0, bo)
            if f:
                th_c = lerp(lerp(5.0, -9.0, s), -16.0, bo) if duty < 0.999 else 0.0
            else:
                th_c = lerp(lerp(can_rest + 9.0, can_rest - 16.0, s), can_rest - 24.0, bo) if duty < 0.999 else can_rest
            return self.toe, 0.0, th_h, th_p, th_c
        u = min(max((ph_leg - duty) / max(1 - duty, 1e-6), 0.0), 1.0)
        if ph_leg < duty * 0.5:      # state says swing but the phase wrapped to early stance (blend jitter)
            u = 1.0
        D = g['v'] * (g['F'] / FPS) * duty
        land = self.neutral(g) + D / 2
        fold = g['fold'] if f else g['hfold']
        # swing angles start at the lift-off (breakover) angles and end at the footfall angles
        th_p = lerp(-6.0, past_rest, sm(u)) - g['pf'] * math.sin(math.pi * min(1.0, u ** 0.8))
        th_h = th_p + lerp(-2.0, HOOF_REST - past_rest, sm(u)) - 12.0 * math.sin(math.pi * u)
        if f:
            th_c = lerp(-16.0, 5.0, sm(u)) - fold * math.sin(math.pi * min(1.0, u ** 0.75))
        else:
            th_c = lerp(can_rest - 24.0, can_rest + 9.0, sm(u)) - fold * 0.8 * math.sin(math.pi * min(1.0, u / 0.8))
        # the knee/hock travels from its lift-off to its footfall position (arc); the toe hangs from it
        _, K0 = self._chain_K(self.lift, 0.0, -8.0, -6.0, -16.0 if f else can_rest - 24.0)
        _, K1 = self._chain_K(land, 0.0, HOOF_REST, past_rest, 5.0 if f else can_rest + 9.0)
        e = sm(u) * 0.85 + u * 0.15
        lift = g['lf'] if f else g['lh']
        K = K0.lerp(K1, e) + V(0, 0, lift * 0.55 * math.sin(math.pi * u ** 0.9))
        y, z = self._toe_from_K(K, th_h, th_p, th_c)
        if z < 0.0:
            K.z -= z; z = 0.0
        if u < 1e-6 or u > 1 - 1e-6:
            y = self.lift if u < 0.5 else land; z = 0.0
        return y, z, th_h, th_p, th_c

def frac(x):
    return x - math.floor(x)

def simulate(N, loop, gfun, chfun, pre_cycles=3):
    """gfun(u) -> gait params at normalised clip time u in [0,1]; chfun(u, phase) -> channels.
    returns per-frame list of (legs{leg: sample}, channels, phase)."""
    # clip duration: one gait cycle for transitions (phase runs 0 -> 1), N frames for loops
    sub = 8
    legs = {l: LegSim(l) for l in LEGS}
    g0 = gfun(0.0)
    T0 = g0['F'] / FPS
    # pre-roll in the steady starting gait so state at u=0 equals the loop state at phase 0
    steps = int(pre_cycles * g0['F'] * sub)
    dt = T0 / (g0['F'] * sub)
    ph = -pre_cycles
    for i in range(steps):
        ph += dt / T0
        for l, ls in legs.items():
            ls.step(g0, frac(ph - g0['off'][l]), dt, T0)
    ph = 0.0
    for l, ls in legs.items():   # snap phase exactly
        pass
    out = []
    Tclip = N / FPS
    total = N * sub
    # phase rate: loops: 1 cycle over N frames; transitions: phase advances by integral of 1/T, normalised to 1
    if not loop:
        acc = []
        s = 0.0
        for i in range(total):
            u = (i + 0.5) / total
            s += 1.0 / (gfun(u)['F'] / FPS)
            acc.append(s)
        norm = acc[-1]
    for f in range(N):
        u = f / N if loop else f / N
        g = gfun(u)
        samp = {l: legs[l].sample(g, frac(ph - g['off'][l])) for l in LEGS}
        out.append((samp, chfun(u, frac(ph) if loop else min(ph, 1.0)), ph, g))
        for k in range(sub):
            i = f * sub + k
            uu = (i + 0.5) / total
            gg = gfun(uu)
            T = gg['F'] / FPS
            dph = (1.0 / total) if loop else (1.0 / (gg['F'] / FPS)) / norm
            dtt = (T / total) if loop else (dph * T)     # loops: N frames = exactly one cycle of period T
            ph += dph
            for l, ls in legs.items():
                ls.step(gg, frac(ph - gg['off'][l]), dtt if loop else dtt, T)
    return out

# ------------------------------------------------------------------ horse pose
def leg_chain_targets(toe_y, toe_z, th_h, th_p, th_c, x, f):
    toe = V(x, toe_y, toe_z)
    C = toe - dirv(th_h) * L_HOOF
    F = C - dirv(th_p) * (L_PAST_F if f else L_PAST_H)
    K = F - dirv(th_c) * (L_CAN_F if f else L_CAN_H)
    return toe, C, F, K

def pose_horse(spec, root=Matrix.Identity(4)):
    """spec: channels + legs {leg: (toe_y, toe_z, th_h, th_p, th_c)} + optional overrides; returns HPose"""
    p = H.HPose()
    p.D['root'] = root
    ch = spec['ch']
    Rb = rot((ch['pitch'], ch['roll'], ch['yaw']))
    body = Matrix.Translation(V(ch['x'], ch['y'], ch['z'])) @ about(H.HEAD['body'], Rb)
    p.D['body'] = root @ body
    p.fk('pelvis', (ch['pelvis'], 0, 0))
    p.fk('spine_01', (ch['spine'] * 0.5 + 0.4 * ch['breath'], 0, 0))
    p.fk('spine_02', (ch['spine'] * -0.6, 0, 0))
    p.fk('chest', (-0.5 * ch['breath'], 0, 0))
    nk = ch['neck']
    p.fk('neck_01', (nk * 0.45, 0, ch['neck_yaw'] * 0.4))
    p.fk('neck_02', (nk * 0.35, 0, ch['neck_yaw'] * 0.35))
    p.fk('neck_03', (nk * 0.20, 0, ch['neck_yaw'] * 0.25))
    p.fk('head', (ch['head'] - nk * 0.55, 0, 0))
    p.fk('jaw', (-ch['jaw'], 0, 0))
    p.fk('ear.L', (ch['ear'], 0, 0)); p.fk('ear.R', (ch['ear'] * (0.6 if ch['ear'] > 0 else 1.0), 0, 0))
    for i in range(1, 6):
        p.fk('tail_%02d' % i, (ch['tail'] * (0.5 if i == 1 else 0.25), 0, ch['tail_yaw'] * (0.15 + 0.08 * i)))
    reach_err = 0.0
    legs = spec['legs']
    for leg in LEGS:
        f = leg[0] == 'f'; s = leg[1]; sx = SX[s]
        toe_y, toe_z, th_h, th_p, th_c = legs[leg]
        ov = spec.get('leg_world', {}).get(leg)
        toe, C, F, K = leg_chain_targets(toe_y, toe_z, th_h, th_p, th_c, 0.15 * sx, f)
        toe = root @ toe; C = root @ C; F = root @ F; K = root @ K
        if ov is not None:      # (weight, toe, C, F, K) in world: blend towards a body-relative pose
            w, t2, c2, f2, k2 = ov
            toe = toe.lerp(t2, w); C = C.lerp(c2, w); F = F.lerp(f2, w); K = K.lerp(k2, w)
        Xb = p.D['body'].to_3x3() @ V(1, 0, 0)
        if f:
            sc, up, lo = 'scapula.' + s, 'humerus.' + s, 'radius.' + s
            a, b = H.blen(up), H.blen(lo)
            Pd = p.D['chest']
            best = None
            for ang in range(-36, 37, 2):
                M = Pd @ about(H.HEAD[sc], rot((ang, 0, 0)))
                S = M @ H.TAIL[sc]
                d = (K - S).length
                cost = abs(d - 0.90 * (a + b)) + 0.0008 * abs(ang)
                if best is None or cost < best[0]:
                    best = (cost, ang)
            ang = best[1]
            p.fk(sc, (ang, 0, 0))
            S = p.tail(sc)
            pole = S + p.D['chest'].to_3x3() @ V(0, -0.6, -0.25)
        else:
            up, lo = 'femur.' + s, 'tibia.' + s
            a, b = H.blen(up), H.blen(lo)
            S = p.D['pelvis'] @ H.HEAD[up]
            pole = S + p.D['pelvis'].to_3x3() @ V(0, 0.7, -0.3)
        E, K2 = H.two_bone(S, K, a, b, pole)
        reach_err = max(reach_err, (K2 - K).length)
        p.set_seg(up, S, E - S, Xb, V(1, 0, 0))
        p.set_seg(lo, E, K2 - E, Xb, V(1, 0, 0))
        names = ('cannon_f.', 'fetlock_f.', 'hoof_f.') if f else ('cannon_h.', 'fetlock_h.', 'hoof_h.')
        pts = [K2]
        for nm, tgt in zip(names, (F, C, toe)):
            d = (tgt - pts[-1]).normalized()
            p.set_seg(nm + s, pts[-1], d, Xb, V(1, 0, 0))
            pts.append(pts[-1] + d * H.blen(nm + s))
        reach_err = max(reach_err, (pts[-1] - toe).length)
    # sockets
    p.fk('saddle')
    p.fk('rider_seat')
    for s in ('L', 'R'):
        sw = spec.get('stir', {}).get(s, (0, 0, 0))
        p.fk('stirrup.' + s, sw)
    p.fk('rein_bit'); p.fk('bridle')
    p.reach_err = reach_err
    return p

def set_socket(p, name, pos, R3):
    """place a socket bone: posed head at pos, rotated by R3 (armature space) from rest"""
    p.D[name] = Matrix.Translation(V(pos)) @ R3.to_4x4() @ Matrix.Translation(-H.HEAD[name])

def pose_reins(p, sag):
    for s, sx in (('L', -1), ('R', 1)):
        a = p.D['rein_bit'] @ V(0.075 * sx, 1.30, 1.44)
        b = p.head('rein_hand.' + s)
        pts = []
        L = (b - a).length
        for i in range(5):
            t = i / 4
            q = a.lerp(b, t); q.z -= sag * 4 * t * (1 - t) * min(1.0, 0.9 / max(L, 0.3))
            pts.append(q)
        for i in range(4):
            n = 'rein_%02d.%s' % (i + 1, s)
            d = pts[i + 1] - pts[i]
            d0 = H.TAIL[n] - H.HEAD[n]
            Q = d0.rotation_difference(d).to_matrix()
            sc = d.length / max(d0.length, 1e-6)
            # rein segments are allowed to stretch along their length (presentation; tack bones, spec 5)
            S = Matrix.Identity(4)
            dn = d0.normalized()
            for r in range(3):
                for c in range(3):
                    S[r][c] = (1 if r == c else 0) + (sc - 1) * dn[r] * dn[c]
            p.D[n] = Matrix.Translation(pts[i]) @ Q.to_4x4() @ S @ Matrix.Translation(-H.HEAD[n])

# ------------------------------------------------------------------ rider
A0 = Matrix.Translation((0, 0.10, 0.538))
A0i = A0.inverted()
STIR_LEN = {'med_knight': 1.10, 'c19_hussar': 0.90, 'em_cuirassier': 1.0}

def rx(a):
    return Matrix.Rotation(math.radians(a), 3, 'X')

def grip_frame(a, dhint, sx):
    a = V(a).normalized(); d = V(dhint); d = (d - a * d.dot(a))
    if d.length < 1e-4:
        d = V(0, 0, 1) - a * a.z
    d.normalize()
    pn = a.cross(d) * sx
    return d, pn.normalized()

def nrm(v):
    v = V(v)
    return v.normalized() if v.length > 1e-9 else V(0, 0, 1)

def eval_wp(Dh, Dc, mix):
    """mix: [(weight, (frame, grip, axis, knuckle))] -> grip point, axis, knuckle hint in rider rest coords"""
    g = V(0, 0, 0); a = V(0, 0, 0); k = V(0, 0, 0); ws = 0.0
    for w, (fr, gp, ax, kn) in mix:
        if w <= 1e-6:
            continue
        Fm = Dh if fr == 'hips' else Dc
        g += (Fm @ V(gp)) * w; a += (Fm.to_3x3() @ nrm(ax)) * w; k += (Fm.to_3x3() @ nrm(kn)) * w; ws += w
    return g / ws, nrm(a), nrm(k)

def solve_rider(hp, rs, variant):
    """hp: posed horse; rs: rider spec.  Returns (deltas {'r:bone': 4x4 horse-armature space}, extra scales, lance)."""
    Mseat = rs.get('seat') or (hp.D['rider_seat'] @ A0)
    Mi = Mseat.inverted()
    p = CR.Pose()
    p.fk('hips', rs['hipR'], offset=rs['hip'])
    p.fk('spine', rs['spine']); p.fk('chest', rs['chest']); p.fk('neck', rs['neck']); p.fk('head', rs['head'])
    p.fk('clav.R', rs.get('clavR', (0, 0, 0))); p.fk('clav.L', rs.get('clavL', (0, 0, 0)))
    Dh = p.delta('hips'); Dc = p.delta('chest')
    # ---- legs: ankles on the stirrup treads (or FK when thrown)
    L = STIR_LEN[variant]
    for s, sx in (('R', 1), ('L', -1)):
        lm = rs.get('leg' + s, 'stirrup')
        if lm == 'stirrup':
            b = 'stirrup.' + s
            hd = hp.head(b); tl = hp.tail(b)
            tread = hd + (tl - hd) * L
            R3 = Mi.to_3x3() @ hp.D[b].to_3x3()
            ank = Mi @ tread + R3 @ V(0, -0.10, 0.075)
            d0 = CR.REST['foot.' + s].to_3x3() @ V(0, 1, 0)
            Q = R3 @ Matrix.Rotation(math.radians(sx * -10), 3, 'Z') @ rx(rs.get('heel', 16))
            hipp = Dh @ V(CR.BI['thigh.' + s][1])
            pole = hipp + V(sx * 0.30, 0.7, -0.1)
            p.limb('thigh.' + s, 'shin.' + s, 'foot.' + s, ank, pole, (-1, 0, 0), end_frame=(Q @ d0, Q @ V(1, 0, 0)), end_rest=(d0, V(1, 0, 0)))
        else:
            th, sh, ft = lm
            p.fk('thigh.' + s, th); p.fk('shin.' + s, sh); p.fk('foot.' + s, ft)
    # ---- rein hand target (both reins in the left hand); sockets follow the hand
    rh = rs.get('rein_hand', (-0.10, 0.36, 1.08))
    Ht = (Dh @ V(rh) + Dc @ V(rh)) * 0.5 + V(0, rs.get('hand_dy', 0.0), rs.get('hand_dz', 0.0))
    Hw = Mseat @ Ht
    Rs = hp.D['saddle'].to_3x3()
    if rs.get('rein_w', 0.0) > 0:       # rider thrown: the reins drop onto the neck in front of the saddle
        Hw = Hw.lerp(hp.D['saddle'] @ V(-0.03, 0.42, 1.52), rs['rein_w'])
    set_socket(hp, 'rein_hand.L', Hw, Rs)
    set_socket(hp, 'rein_hand.R', Hw + Rs @ V(0.035, 0, 0), Rs)
    # ---- weapons
    pr = rs.get('prop'); ln = rs.get('lance')
    G = {}
    if pr:
        G['prop'] = list(eval_wp(Dh, Dc, pr[0])) + [pr[1]]
    if ln:
        G['lance'] = list(eval_wp(Dh, Dc, ln[0])) + [ln[1]]
    # ---- arms
    for s, sx in (('R', 1), ('L', -1)):
        up, fo, ha = 'upper_arm.' + s, 'forearm.' + s, 'hand.' + s
        d0 = CR.REST[ha].to_3x3() @ V(0, 1, 0); p0 = V(-sx, 0, 0)
        am = rs.get('arm' + s, 'rein' if s == 'L' else 'prop')
        if am == 'rein' or (am in G):
            if am == 'rein':
                gp = Ht
                ax = Mi.to_3x3() @ (Rs @ V(sx * 0.25, 0.30, 1.0))
                kn = Mi.to_3x3() @ (Rs @ V(sx * 0.3, 1.0, -0.2))
            else:
                gp, ax, kn = G[am][0], G[am][1], G[am][2]
            d, pn = grip_frame(ax, kn, sx)
            w = gp - pn * 0.03 - d * 0.062
            pl = rs.get('pole' + s)
            pole = Dc @ (V(pl) if pl else V(sx * 0.45, -0.35, 1.0))
            E, W = p.limb(up, fo, ha, w, pole, (1, 0, 0), end_frame=(d, pn), end_rest=(d0, p0))
            if am in G:
                G[am][0] = gp + (W - w)        # hand could not reach: the weapon stays in the fist
        elif isinstance(am, tuple):
            p.fk(up, am[0]); p.fk(fo, am[1]); p.fk(ha, am[2])
        else:
            p.fk(up, (0, 0, 0)); p.fk(fo, (-25, 0, 0)); p.fk(ha, (0, 0, 0))
    out = {}
    for b in CR.REST:
        if b in ('prop', 'root'):
            continue
        out['r:' + b] = Mseat @ p.delta(b) @ A0i
    out['r:root'] = Mseat @ A0i
    ph = V(CR.BI['prop'][1])
    if 'prop' in G:
        g, a, kn, scl = G['prop']
        Q = frame_from(a, kn) @ frame_from(V(0, 0, 1), V(0, 1, 0)).transposed()
        Dp = Matrix.Translation(g) @ Q.to_4x4() @ Matrix.Translation(-ph)
        out['r:prop'] = Mseat @ Dp @ scale_about(ph, scl) @ A0i
    else:
        out['r:prop'] = Mseat @ Dh @ scale_about(ph, 0.0) @ A0i
    lance = None
    if 'lance' in G:
        g, a, kn, scl = G['lance']
        lance = (Mseat @ g, nrm(Mseat.to_3x3() @ a), scl)
    return out, lance, p

def scale_about(c, s):
    c = V(c)
    return Matrix.Translation(c) @ Matrix.Diagonal((s, s, s, 1.0)) @ Matrix.Translation(-c)

def place_lance(hp, lance):
    if lance is None:
        hp.D['lance'] = hp.D['saddle'] @ scale_about(H.HEAD['lance'], 0.0)
        return
    g, a, scl = lance
    a0 = (H.TAIL['lance'] - H.HEAD['lance']).normalized()
    Q = frame_from(a, V(0, 0, 1)) @ frame_from(a0, V(0, 0, 1)).transposed()
    hp.D['lance'] = Matrix.Translation(g) @ Q.to_4x4() @ Matrix.Translation(-H.HEAD['lance']) @ scale_about(H.HEAD['lance'], scl)

# ------------------------------------------------------------------ weapon poses (rider rest coords; frame, grip, axis, knuckles)
WP = {
    'sabre_carry': ('hips', (0.25, 0.22, 1.00), (0.0, -0.40, 1.0), (0, 1, 0.3)),     # blade at the shoulder
    'sabre_point': ('chest', (0.30, 0.62, 1.33), (-0.05, 1.0, -0.12), (0, 0, -1)),    # charge: arm extended, point forward
    'sword_carry': ('hips', (0.27, 0.24, 1.02), (0.05, 0.25, 1.0), (0, 1, 0)),        # held upright at the thigh
    'guard':       ('chest', (0.32, 0.38, 1.16), (0.10, 0.55, 1.0), (0, 1, -0.4)),
    'cut_prep':    ('chest', (0.30, -0.06, 1.58), (0.15, -0.75, 0.65), (0, 0.3, 1)),  # raised high behind
    'cut_mid':     ('chest', (0.34, 0.32, 1.50), (0.12, 0.57, 0.82), (0, 0.98, -0.19)),  # over the top
    'cut_hit':     ('chest', (0.36, 0.60, 1.14), (0.10, 1.0, -0.55), (0, 0, -1)),
    'cut_follow':  ('chest', (0.06, 0.46, 0.92), (-0.80, 0.35, -0.55), (-0.3, 0, -1)),
    'thrust_prep': ('chest', (0.30, -0.02, 1.26), (0.0, 1.0, -0.05), (0, 0, -1)),
    'thrust_hit':  ('chest', (0.30, 0.78, 1.25), (-0.05, 1.0, -0.10), (0, 0, -1)),
    'back_prep':   ('chest', (-0.10, 0.28, 1.46), (-0.60, 0.30, 0.80), (-1, 0.2, 0)),
    'back_mid':    ('chest', (0.20, 0.50, 1.36), (0.10, 0.90, 0.50), (0.93, -0.25, 0.27)),   # across the front
    'back_hit':    ('chest', (0.46, 0.46, 1.12), (0.80, 0.60, -0.30), (1, 0, -0.3)),
    'back_follow': ('chest', (0.42, 0.04, 1.00), (0.60, -0.40, -0.40), (1, -0.3, 0)),
    'sheath':      ('hips', (0.20, 0.02, 0.86), (0.0, 0.10, 1.0), (0, 1, 0)),          # knight sword at the hip (hidden)
    'lance_up':    ('hips', (0.26, 0.18, 0.95), (0.0, 0.15, 1.0), (0, 1, 0)),
    'lance_couch': ('chest', (0.22, 0.30, 1.20), (-0.17, 1.0, -0.06), (0, 0, -1)),
    'lance_drop':  ('hips', (0.36, 0.30, 0.80), (0.30, 0.6, -0.7), (0, 0, -1)),
}

def carry_wp(variant, charge):
    """(prop mix, prop scale, lance mix|None, lance scale, right-arm mode) for travel + charge blend c in [0,1]"""
    if variant == 'med_knight':
        return [(1.0, WP['sheath'])], 0.0, [(1 - charge, WP['lance_up']), (charge, WP['lance_couch'])], 1.0, 'lance'
    if variant == 'c19_hussar':
        return [(1 - charge, WP['sabre_carry']), (charge, WP['sabre_point'])], 1.0, None, 0.0, 'prop'
    return [(1 - charge, WP['sword_carry']), (charge, WP['sabre_point'])], 1.0, None, 0.0, 'prop'

def rider_spec(variant, ch, lean_x=0.0, yaw_x=0.0, charge=0.0, prop=None, lance=None, armR=None):
    lean = ch['r_lean'] + lean_x
    rp = ch['r_pitch']
    rs = {
        'hip': (0, ch['r_dy'], ch['r_dz']),
        'hipR': (-lean * 0.20 + rp * 0.5, ch['r_roll'], ch['r_yaw'] * 0.6 + yaw_x * 0.2),
        'spine': (-lean * 0.40 + rp * 0.3, -ch['r_roll'] * 0.5, yaw_x * 0.35),
        'chest': (-lean * 0.40 + rp * 0.2, -ch['r_roll'] * 0.4, yaw_x * 0.45),
        'neck': (lean * 0.35 - ch['pitch'] * 0.3, 0, -yaw_x * 0.3),
        'head': (lean * 0.50 - ch['pitch'] * 0.3 - rp * 0.5 + ch['r_head'], 0, -yaw_x * 0.35 - ch['r_yaw'] * 0.5),
        'hand_dy': ch['hand_dy'], 'hand_dz': ch['hand_dz'],
    }
    pm, ps, lm, ls, am = carry_wp(variant, charge)
    rs['prop'] = prop if prop is not None else (pm, ps)
    lz = lance if lance is not None else ((lm, ls) if lm else None)
    if lz:
        rs['lance'] = lz
    rs['armR'] = armR or am
    if variant == 'med_knight':
        rs['clavL'] = (0, 0, 0)
    return rs

# ------------------------------------------------------------------ full frame evaluation
def frame_deltas(variant, hp, rs, sag):
    out, lance, rp = solve_rider(hp, rs, variant)
    place_lance(hp, lance)
    pose_reins(hp, sag)
    D = dict(hp.D)
    D.update(out)
    return D, hp, rp

def legs_tuple(samp):
    return {l: samp[l] for l in LEGS}

def stand_legs():
    out = {}
    for l in LEGS:
        f = l[0] == 'f'
        out[l] = (TOE0[l[0]], 0.0, HOOF_REST, PAST_REST_F if f else PAST_REST_H, CAN_REST_F if f else CAN_REST_H)
    return out

def leg_lerp(A, B, t):
    return {l: tuple(lerp(a, b, t) for a, b in zip(A[l], B[l])) for l in LEGS}

def stir_euler(ch):
    return (-ch['pitch'] * 0.7 + ch.get('stir', 0.0), 0, 0)

# steady gait tables (phase -> legs), used to land transitions exactly on the target loop
_TABLE = {}
def gait_table(name, n=96):
    if name not in _TABLE:
        g = GAITS[name]
        sim = simulate(n, True, lambda u: g, lambda u, ph: None)
        _TABLE[name] = [s[0] for s in sim]
    return _TABLE[name]

def table_legs(name, ph):
    t = gait_table(name); n = len(t)
    x = frac(ph) * n; i = int(x) % n; j = (i + 1) % n; u = x - int(x)
    A, B = t[i], t[j]
    out = {}
    for l in LEGS:
        a, b = A[l], B[l]
        if abs(a[0] - b[0]) > 0.3:      # stance/swing wrap between samples: no interpolation
            out[l] = a
        else:
            out[l] = tuple(lerp(x0, x1, u) for x0, x1 in zip(a, b))
    return out

def gait_frames(variant, A, B=None, N=None):
    """returns per-frame (legs, channels, extras) for a loop (B None) or a one-cycle transition A->B."""
    if B is None:
        g = GAITS[A]
        N = N or g['F']
        sim = simulate(N, True, lambda u: g, lambda u, ph: channels(A, ph, variant))
        return [(s[0], s[1], dict(charge=1.0 if A == 'charge' else 0.0, lean_x=0.0, yaw_x=0.0)) for s in sim]
    gA, gB = GAITS[A], GAITS[B]
    iA, iB = GAIT_ORDER.index(A), GAIT_ORDER.index(B)
    accel = 1 if iB > iA else -1
    if N is None:   # one cycle: T = 1 / integral(1/T)
        inv = sum(1.0 / lerp(gA['F'], gB['F'], sm((k + 0.5) / 64)) for k in range(64)) / 64
        N = max(8, int(round(1.0 / inv)))
        if 'stand' in (A, B):
            N = max(N, 24)
    gf = lambda u: gblend(A, B, sm(u))
    cf = lambda u, ph: ch_blend(channels(A, ph, variant), channels(B, ph, variant), sm(u))
    sim = simulate(N, False, gf, cf)
    out = []
    for f, (samp, ch, ph, g) in enumerate(sim):
        u = f / N
        land = sm((u - 0.65) / 0.35)
        legs = leg_lerp(samp, table_legs(B, ph), land) if land > 0 else samp
        bump = math.sin(math.pi * u)
        ch = dict(ch)
        if accel > 0:
            lean_x = 9.0 * bump; ch['neck'] -= 5.0 * bump; ch['pitch'] -= 1.0 * bump
        else:
            lean_x = -10.0 * bump; ch['head'] += 7.0 * bump; ch['pitch'] += 3.5 * bump; ch['neck'] += 4.0 * bump
            ch['pelvis'] -= 3.0 * bump
        cA = 1.0 if A == 'charge' else 0.0; cB = 1.0 if B == 'charge' else 0.0
        out.append((legs, ch, dict(charge=lerp(cA, cB, sm(u)), lean_x=lean_x, yaw_x=0.0)))
    return out

def eval_frame(variant, legs, ch, ex, root=None, stir=None):
    spec = {'ch': ch, 'legs': legs, 'stir': {s: stir_euler(ch) for s in 'LR'}}
    hp = pose_horse(spec, root or Matrix.Identity(4))
    rs = rider_spec(variant, ch, lean_x=ex.get('lean_x', 0.0), yaw_x=ex.get('yaw_x', 0.0), charge=ex.get('charge', 0.0),
                    prop=ex.get('prop'), lance=ex.get('lance'), armR=ex.get('armR'))
    for k in ('hip_dz', 'hip_dy'):
        if k in ex:
            h = list(rs['hip']); h[2 if k == 'hip_dz' else 1] += ex[k]; rs['hip'] = tuple(h)
    if 'chest_yaw' in ex:
        c = list(rs['chest']); c[2] += ex['chest_yaw']; rs['chest'] = tuple(c)
        s_ = list(rs['spine']); s_[2] += ex['chest_yaw'] * 0.5; rs['spine'] = tuple(s_)
    if 'seat' in ex:
        rs['seat'] = ex['seat']
    for k in ('legR', 'legL', 'armL'):
        if k in ex:
            rs[k] = ex[k]
    if 'torso_x' in ex:
        c = list(rs['chest']); c[0] += ex['torso_x']; rs['chest'] = tuple(c)
        n_ = list(rs['head']); n_[0] -= ex['torso_x'] * 0.6; rs['head'] = tuple(n_)
    return frame_deltas(variant, hp, rs, ch['sag'])

# ------------------------------------------------------------------ combat + death clips
def toe_from_K(K, th_h, th_p, th_c, f):
    Fp = K + dirv(th_c) * (L_CAN_F if f else L_CAN_H)
    C = Fp + dirv(th_p) * (L_PAST_F if f else L_PAST_H)
    toe = C + dirv(th_h) * L_HOOF
    return (toe.y, toe.z, th_h, th_p, th_c)

FOLD = {'f': (V(0, 0.66, 0.62), -40.0, -70.0, -95.0), 'h': (V(0, -0.66, 0.64), 70.0, 55.0, 35.0)}
def fold_legs():
    out = {}
    for l in LEGS:
        K, a, b, c = FOLD[l[0]]
        out[l] = toe_from_K(K, a, b, c, l[0] == 'f')
    return out

def keyed(keys, t):
    """keys [(t, value-dict)] -> smoothstep-interpolated dict (values: floats or WP names -> mix list)"""
    if t <= keys[0][0]:
        A = B = keys[0][1]; u = 0.0
    elif t >= keys[-1][0]:
        A = B = keys[-1][1]; u = 0.0
    else:
        for (ta, A), (tb, B) in zip(keys, keys[1:]):
            if t <= tb:
                u = sm((t - ta) / (tb - ta)); break
    out = {}
    for k in A:
        a, b = A[k], B.get(k, A[k])
        if isinstance(a, str):
            out[k] = [(1 - u, WP[a]), (u, WP[b])]
        else:
            out[k] = lerp(a, b, u)
    return out

def stand_ch(variant, p, ears=0.0):
    ch = channels('stand', p, variant)
    ch['ear'] = min(ch['ear'], 0.0) + ears
    return ch

def melee_frames(variant, kind):
    kn = variant == 'med_knight'
    guard_lance = ([(1.0, WP['lance_drop'])], 0.0) if kn else None
    rows = []
    if kind == 'ready':          # 48 loop: horse stands its ground, paws once; rider at guard, scanning
        N = 48
        for f in range(N):
            p = f / N
            ch = stand_ch(variant, p, ears=-25.0)
            legs = stand_legs()
            u = (p - 0.30) / 0.18
            if 0 <= u <= 1:      # paw with the right fore
                s = math.sin(math.pi * u)
                y, z, a, b, c = legs['fR']
                legs['fR'] = (y + 0.10 * s, 0.10 * s, a - 30 * s, b - 40 * s, c - 35 * s)
            ex = dict(prop=([(1.0, WP['guard'])], 1.0), lance=guard_lance, yaw_x=10 * math.sin(2 * math.pi * p), lean_x=3.0)
            rows.append((legs, ch, ex))
        return rows, True
    if kind in ('draw', 'ready_idle'):
        N = (24 if kind == 'draw' else 16) + (12 if kn else 0)
        for f in range(N):
            t = f / (N - 1)
            if kind == 'ready_idle':
                t = 1 - t
            p = (f / N) * 0.5
            ch = stand_ch(variant, p, ears=-25.0 * sm(t))
            pm, ps, lm, ls, am = carry_wp(variant, 0.0)
            if kn:   # lance lowered and let go (fades), sword drawn from the hip
                wl = sm(t / 0.45)
                lance = ([(1 - wl, WP['lance_up']), (wl, WP['lance_drop'])], 1.0 - sm((t - 0.25) / 0.25))
                ws = sm((t - 0.50) / 0.50)
                prop = ([(1 - ws, WP['sheath']), (ws, WP['guard'])], sm((t - 0.30) / 0.15))
                armR = 'lance' if t < 0.50 else 'prop'
            else:
                ws = sm(t)
                prop = ([(1 - ws, pm[0][1]), (ws, WP['guard'])], 1.0); lance = None; armR = 'prop'
            ex = dict(prop=prop, lance=lance, armR=armR, lean_x=3.0 * t, chest_yaw=-12 * math.sin(math.pi * t))
            rows.append((stand_legs(), ch, ex))
        return rows, False
    if kind in ('strike_a', 'strike_b'):
        N = 36
        thrust = variant == 'c19_hussar' and kind == 'strike_b'
        if kind == 'strike_a':     # overhead cut: prep high behind -> strike forward-low -> follow-through -> recover
            K = [(0.00, dict(w='guard', yaw=0.0, dz=0.0, tx=0.0)), (0.28, dict(w='cut_prep', yaw=-25.0, dz=0.02, tx=6.0)),
                 (0.41, dict(w='cut_mid', yaw=-5.0, dz=0.05, tx=-6.0)),
                 (0.55, dict(w='cut_hit', yaw=15.0, dz=0.06, tx=-18.0)), (0.71, dict(w='cut_follow', yaw=22.0, dz=0.03, tx=-14.0)),
                 (1.00, dict(w='guard', yaw=0.0, dz=0.0, tx=0.0))]
        elif thrust:               # hussar point
            K = [(0.00, dict(w='guard', yaw=0.0, dz=0.0, tx=0.0)), (0.32, dict(w='thrust_prep', yaw=-18.0, dz=0.01, tx=4.0)),
                 (0.50, dict(w='thrust_hit', yaw=8.0, dz=0.07, tx=-22.0)), (0.66, dict(w='thrust_hit', yaw=6.0, dz=0.05, tx=-16.0)),
                 (1.00, dict(w='guard', yaw=0.0, dz=0.0, tx=0.0))]
        else:                      # backhand
            K = [(0.00, dict(w='guard', yaw=0.0, dz=0.0, tx=0.0)), (0.28, dict(w='back_prep', yaw=25.0, dz=0.02, tx=2.0)),
                 (0.41, dict(w='back_mid', yaw=5.0, dz=0.04, tx=-4.0)),
                 (0.55, dict(w='back_hit', yaw=-20.0, dz=0.05, tx=-12.0)), (0.72, dict(w='back_follow', yaw=-28.0, dz=0.03, tx=-8.0)),
                 (1.00, dict(w='guard', yaw=0.0, dz=0.0, tx=0.0))]
        for f in range(N):
            t = f / (N - 1)
            k = keyed(K, t)
            ch = stand_ch(variant, 0.25 + 0.25 * t, ears=-30.0)
            hit = math.exp(-((t - 0.55) / 0.12) ** 2)
            ch['y'] += 0.04 * hit; ch['pitch'] -= 2.0 * hit; ch['neck'] -= 4.0 * hit
            ex = dict(prop=(k['w'], 1.0), lance=guard_lance, chest_yaw=k['yaw'], hip_dz=k['dz'], torso_x=k['tx'], lean_x=3.0)
            rows.append((stand_legs(), ch, ex))
        return rows, False
    if kind == 'hit':              # 18: horse flinches sideways and throws its head, rider rocks back
        N = 18
        for f in range(N):
            t = f / (N - 1)
            e = math.sin(math.pi * min(1.0, t / 0.35)) if t < 0.35 else math.exp(-(t - 0.35) * 5.0) * math.cos((t - 0.35) * 12) * 0.9
            e2 = math.sin(math.pi * min(t / 0.6, 1.0))
            ch = stand_ch(variant, 0.1, ears=-40.0 * e2)
            ch['x'] -= 0.06 * e; ch['roll'] -= 6.0 * e; ch['head'] += 16.0 * e; ch['neck'] += 10.0 * e; ch['pitch'] += 2.5 * e
            ch['tail'] += 15 * e2; ch['jaw'] = 14 * e2
            legs = stand_legs()
            y, z, a, b, c = legs['hL']
            legs['hL'] = (y + 0.08 * e2, 0.06 * e2, a - 20 * e2, b - 25 * e2, c - 15 * e2)
            ex = dict(prop=([(1.0, WP['guard'])], 1.0), lance=guard_lance, lean_x=3.0 - 16.0 * e, chest_yaw=10 * e, hip_dz=0.02 * e)
            rows.append((legs, ch, ex))
        return rows, False

DIE = {
    # pitch keys (t, deg, pivot y), roll keys (t, deg), drop (t, m), fore/hind fold (t, w), rider: detach t0,t1, ground hip, yaw
    'a': dict(pitch=[(0, 0), (0.30, -16), (0.55, -10), (1, 0)], piv=-0.55, roll=[(0, 0), (0.30, 4), (0.80, 80), (1, 82)],
              drop=[(0, 0), (0.30, 0.14), (0.80, 0.10), (1, 0.08)], ff=[(0, 0), (0.28, 0.85), (1, 0.6)], hf=[(0, 0), (0.45, 0.2), (0.9, 0.7), (1, 0.7)],
              side=1, det=(0.22, 0.70), hip=(-0.95, 1.30, 0.14), yaw=20.0, lunge=12.0),
    'b': dict(pitch=[(0, 0), (0.32, 26), (0.62, 12), (1, 0)], piv=-0.50, roll=[(0, 0), (0.35, -6), (0.85, -80), (1, -82)],
              drop=[(0, 0), (0.35, 0.0), (0.85, 0.12), (1, 0.11)], ff=[(0, 0), (0.25, 0.9), (0.5, 0.5), (1, 0.6)], hf=[(0, 0), (0.5, 0.1), (0.9, 0.7), (1, 0.7)],
              side=-1, det=(0.25, 0.78), hip=(0.85, -1.45, 0.14), yaw=60.0, lunge=-16.0),
    'c': dict(pitch=[(0, 0), (0.40, 14), (0.70, 8), (1, 0)], piv=0.66, roll=[(0, 0), (0.40, 2), (0.85, 76), (1, 78)],
              drop=[(0, 0), (0.40, 0.04), (0.85, 0.14), (1, 0.13)], ff=[(0, 0), (0.45, 0.15), (0.9, 0.6), (1, 0.6)], hf=[(0, 0), (0.38, 0.9), (1, 0.7)],
              side=1, det=(0.30, 0.80), hip=(-1.00, -0.25, 0.14), yaw=-70.0, lunge=-8.0),
}

def kv(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (ta, a), (tb, b) in zip(keys, keys[1:]):
        if t <= tb:
            return lerp(a, b, sm((t - ta) / (tb - ta)))
    return keys[-1][1]

def die_frames(variant, kind):
    d = DIE[kind]
    N = 48
    rows = []
    SL, FL = stand_legs(), fold_legs()
    for f in range(N):
        t = f / (N - 1)
        pitch = kv(d['pitch'], t); roll = kv(d['roll'], t); drop = kv(d['drop'], t)
        root = (Matrix.Translation((0, 0, -drop)) @ about(V(d['side'] * 0.32, 0, 0), rot((0, roll, 0)))
                @ about(V(0, d['piv'], 0), rot((pitch, 0, 0))))
        legs = {}
        for l in LEGS:
            w = kv(d['ff'] if l[0] == 'f' else d['hf'], t)
            legs[l] = tuple(lerp(a, b, w) for a, b in zip(SL[l], FL[l]))
        ch = channels('stand', 0.2, variant)
        lim = sm((t - 0.5) / 0.5)
        ch['neck'] = lerp(-4, 14 if kind == 'b' else -18, sm(t / 0.5)) * (1 - lim) + (-8) * lim
        ch['head'] = lerp(0, 20, sm(t / 0.4)) * (1 - lim) + 10 * lim
        ch['ear'] = -40.0; ch['jaw'] = 20 * math.sin(math.pi * min(1, t / 0.6)); ch['tail'] = lerp(10, -10, t)
        ch['tail_yaw'] = 10 * math.sin(6 * t)
        spec = {'ch': ch, 'legs': legs, 'stir': {s: (0, 0, 0) for s in 'LR'}}
        hp = pose_horse(spec, root)
        # rider: jolted, then thrown clear onto his back
        t0, t1 = d['det']
        w = sm((t - t0) / (t1 - t0))
        Mlive = hp.D['rider_seat'] @ A0
        R = Matrix.Rotation(math.radians(d['yaw']), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X')
        G = Matrix.Translation(V(d['hip'])) @ R @ Matrix.Translation((0, 0, -0.95))
        seat = mlerp_s(Mlive, G, w)
        seat = Matrix.Translation((0, 0, 0.55 * math.sin(math.pi * w))) @ seat
        jolt = math.sin(math.pi * min(1.0, t / max(t0 + 0.12, 0.01)))
        ex = dict(lean_x=d['lunge'] * jolt * (1 - w), seat=seat, charge=0.0)
        pm, ps, lm, ls, am = carry_wp(variant, 0.0)
        fade = 1.0 - sm((t - t0) / 0.15)
        ex['prop'] = (pm, ps * fade)
        if lm:
            ex['lance'] = (lm, ls * fade)
        ex['rein_w'] = w
        ex['fk_k'] = sm(w / 0.35)
        if w > 0.0:
            fl = math.sin(math.pi * w)
            for s, sx in (('R', 1), ('L', -1)):
                ex['leg' + s] = ((lerp(70, 12, w), 0, sx * lerp(-8, -14, w)), (lerp(-80, -15, w) - 25 * fl, 0, 0), (lerp(0, -20, w), 0, 0))
                ex['arm' + s] = ((lerp(10, 25, w) + 110 * fl, 0, sx * (15 + 20 * fl)), (-30 * fl - 10, 0, 0), (0, 0, 0))
        rows.append(('direct', hp, ch, ex))
    return rows, False

def mlerp_s(A, B, t):
    la, ra, _ = A.decompose(); lb, rb, _ = B.decompose()
    return Matrix.Translation(la.lerp(lb, t)) @ ra.slerp(rb, t).to_matrix().to_4x4()

# ------------------------------------------------------------------ clip table
TRANS = [('stand', 'walk', 'hz_idle_walk'), ('walk', 'stand', 'hz_walk_idle'), ('walk', 'trot', 'hz_walk_trot'), ('trot', 'walk', 'hz_trot_walk'),
         ('trot', 'canter', 'hz_trot_canter'), ('canter', 'trot', 'hz_canter_trot'), ('canter', 'gallop', 'hz_canter_gallop'),
         ('gallop', 'canter', 'hz_gallop_canter'), ('gallop', 'charge', 'hz_gallop_charge'), ('charge', 'gallop', 'hz_charge_gallop')]

def clip_rows(variant):
    """[(clip, loop, v_nom, rows)]; rows are (legs, ch, ex) or ('direct', hp, ch, ex)"""
    C = []
    C.append(('hz_stand', True, 0.0, gait_frames(variant, 'stand', N=96)))
    for gname in ('walk', 'trot', 'canter', 'gallop', 'charge'):
        C.append(('hz_' + gname, True, GAITS[gname]['v'], gait_frames(variant, gname)))
    for A, B, nm in TRANS:
        C.append((nm, False, (GAITS[A]['v'] + GAITS[B]['v']) / 2, gait_frames(variant, A, B)))
    for kind, nm in (('ready', 'hz_melee_ready'), ('draw', 'hz_draw'), ('ready_idle', 'hz_ready_idle'), ('strike_a', 'hz_strike_a'),
                     ('strike_b', 'hz_strike_b'), ('hit', 'hz_hit')):
        rows, loop = melee_frames(variant, kind)
        C.append((nm, loop, 0.0, rows))
    for k in 'abc':
        rows, loop = die_frames(variant, k)
        C.append(('cv_die_' + k, loop, 0.0, rows))
    return C

ALIASES = {'idle': 'hz_stand', 'walk': 'hz_walk', 'run': 'hz_gallop', 'melee': 'hz_melee_ready', 'fire': 'hz_melee_ready', 'die': 'cv_die_a'}

def row_deltas(variant, row):
    if row[0] == 'direct':
        _, hp, ch, ex = row
        rs = rider_spec(variant, ch, lean_x=ex.get('lean_x', 0.0), charge=ex.get('charge', 0.0), prop=ex.get('prop'), lance=ex.get('lance'))
        rs['seat'] = ex['seat']; rs['rein_w'] = ex.get('rein_w', 0.0)
        for k in ('legR', 'legL', 'armL', 'armR'):
            if k in ex:
                rs[k] = ex[k]
        k = ex.get('fk_k', 1.0)
        if k < 1.0 and any(x in ex for x in ('legR', 'legL', 'armL', 'armR')):
            rsi = dict(rs)
            for x in ('legR', 'legL', 'armL', 'armR'):
                rsi.pop(x, None)
            DI, _, _ = frame_deltas(variant, hp, rsi, 0.12)
            DI = {b: m.copy() for b, m in DI.items()}
            D, hp2, rp = frame_deltas(variant, hp, rs, 0.12)
            for b in D:
                if b.startswith('r:') and b in DI:
                    if b == 'r:prop':
                        D[b] = DI[b] * (1 - k) + D[b] * k
                    else:
                        D[b] = mlerp_s(DI[b], D[b], k)
            return D, hp2
        D, hp2, rp = frame_deltas(variant, hp, rs, 0.12)
        return D, hp2
    legs, ch, ex = row
    D, hp, rp = eval_frame(variant, legs, ch, ex)
    return D, hp

# ------------------------------------------------------------------ bake (multi-layer LBS, numpy) + export
def weights_arrays(g, bones):
    import numpy as np
    bi = {b: i for i, b in enumerate(bones)}
    n = len(g.v)
    idx = np.zeros((n, 4), np.int32); wt = np.zeros((n, 4), np.float32)
    for i, w in enumerate(g.w):
        items = sorted(w.items(), key=lambda kv_: -kv_[1])[:4]
        s = sum(x for _, x in items)
        for k, (b, x) in enumerate(items):
            idx[i, k] = bi[b]; wt[i, k] = x / s
    return idx, wt

def bake_variant(variant, lod, outdir, prevdir=None, only=None):
    import numpy as np
    import horse_proxy as HP
    g = HP.build(variant, lod)
    bones = list(H.NAMES) + ['r:' + b for b in CR.REST]
    used = set(b for w in g.w for b in w)
    missing = used - set(bones)
    assert not missing, missing
    idx, wt = weights_arrays(g, bones)
    vh = np.array([[p.x, p.y, p.z, 1.0] for p in g.v], np.float64)
    clips = clip_rows(variant)
    if only:
        clips = [c for c in clips if c[0] in only]
    frames = []; meta = {}
    row = 0
    stats = {}
    ident = np.eye(4)
    for name, loop, vnom, rows in clips:
        start = row
        worst = 0.0
        for r in rows:
            D, hp = row_deltas(variant, r)
            worst = max(worst, getattr(hp, 'reach_err', 0.0))
            M = np.stack([np.array(D[b]) if b in D else ident for b in bones])
            P = np.zeros((len(vh), 3))
            for k in range(4):
                Mk = M[idx[:, k]]
                P += wt[:, k:k + 1] * np.einsum('vij,vj->vi', Mk, vh)[:, :3]
            frames.append(P.astype(np.float32))
            row += 1
        meta[name] = {'start': start, 'count': len(rows), 'loop': bool(loop)}
        if vnom:
            meta[name]['v_nom'] = round(vnom, 3)
        stats[name] = round(worst, 4)
    for a, b in ALIASES.items():
        if b in meta:
            meta[a] = dict(meta[b])
    arr = np.stack(frames)                       # (F, V, 3) blender coords
    godot = np.stack([arr[..., 0], arr[..., 2], -arr[..., 1]], -1).astype(np.float32)
    lo = godot.reshape(-1, 3).min(0); hi = godot.reshape(-1, 3).max(0)
    base = os.path.join(outdir, 'hx_%s_lod%d' % (variant, lod))
    open(base + '.vat', 'wb').write(godot.tobytes())
    js = {'vertices': len(g.v), 'fps': FPS, 'frames': int(arr.shape[0]), 'aabb': [lo.tolist(), hi.tolist()], 'clips': meta,
          'rig': 'hx (HORSE_SKELETON_SPEC v1.1)', 'layers': sorted(set(g.layer))}
    json.dump(js, open(base + '.json', 'w'), indent=1)
    if prevdir:
        os.makedirs(prevdir, exist_ok=True)
        json.dump({'faces': [list(f) for f in g.f], 'cols': [list(c) for c in g.fc], 'mats': g.fm, 'layers': g.fl},
                  open(os.path.join(prevdir, 'hx_%s_lod%d_mesh.json' % (variant, lod)), 'w'))
    v, t = g.counts()
    print('BAKED', base, 'verts', v, 'tris', t, 'frames', arr.shape[0], 'reach_err', max(stats.values()))
    return g, js, stats

def to_blender(g, name, with_groups=False):
    import bpy
    me = bpy.data.meshes.new(name)
    seen = set(); keep = []
    for i, f in enumerate(g.f):           # drop duplicate / degenerate faces (glTF + Blender validity)
        key = tuple(sorted(f))
        if len(set(f)) < 3 or key in seen:
            continue
        seen.add(key); keep.append(i)
    me.from_pydata([tuple(p) for p in g.v], [], [tuple(g.f[i]) for i in keep])
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    n = len(me.vertices); nl = len(me.loops)
    lvi = [0] * nl; me.loops.foreach_get('vertex_index', lvi)
    me.uv_layers.new(name='UVMap'); me.uv_layers.new(name='VID')
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    u0 = [0.0] * (2 * nl); u1 = [0.0] * (2 * nl); c0 = [1.0] * (4 * nl)
    for poly in me.polygons:
        col = g.fc[keep[poly.index]]; mat = g.fm[keep[poly.index]]
        for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
            u0[2 * li] = 0.0; u0[2 * li + 1] = mat / 16.0
            u1[2 * li] = (lvi[li] + 0.5) / n; u1[2 * li + 1] = col[3]
            c0[4 * li:4 * li + 4] = [col[0], col[1], col[2], col[3]]
        poly.use_smooth = False
    me.uv_layers['UVMap'].data.foreach_set('uv', u0)
    me.uv_layers['VID'].data.foreach_set('uv', u1)
    me.color_attributes['Col'].data.foreach_set('color', c0)
    me.color_attributes.active_color_index = 0
    import common
    me.materials.append(common.vcol_material())
    if with_groups:
        names = sorted(set(b for w in g.w for b in w))
        for b in names:
            obj.vertex_groups.new(name=b)
        for i, w in enumerate(g.w):
            for b, x in w.items():
                obj.vertex_groups[b].add((i,), x, 'REPLACE')
    return obj

def main(argv):
    import bpy, common
    variants = [a for a in argv if a in ('med_knight', 'c19_hussar', 'em_cuirassier')] or ['med_knight', 'c19_hussar', 'em_cuirassier']
    no_export = '--no-export' in argv
    prev = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'out', 'hx_prev'))
    report = {}
    for vr in variants:
        for lod in (0, 1):
            common.reset_scene()
            g, js, stats = bake_variant(vr, lod, common.VAT if not no_export else prev, prevdir=prev)
            report['%s_lod%d' % (vr, lod)] = {'verts': g.counts()[0], 'tris': g.counts()[1], 'frames': js['frames'], 'reach': stats,
                                              'layers': {l: sum(1 for x in g.fl if x == l) for l in sorted(set(g.fl))}}
            if not no_export:
                o = to_blender(g, 'hx_%s_lod%d' % (vr, lod))
                common.export_glb([o], os.path.join(common.MODELS, 'cavalry_hx_%s_lod%d.glb' % (vr, lod)))
                if lod == 0:   # rigged handoff for Bill: hx armature + skinned proxy (rest pose)
                    _rest = {k: m.copy() for k, m in H.REST.items()}
                    rig = H.build_armature('hx_rig')
                    H.REST.clear(); H.REST.update(_rest)   # the bake keeps its own rest frames
                    o2 = to_blender(g, 'hx_%s_skinned' % vr, with_groups=True)
                    # rider bones are not in the horse armature: rider verts ride on rider_seat in the handoff file
                    for vg in list(o2.vertex_groups):
                        if vg.name.startswith('r:'):
                            o2.vertex_groups.remove(vg)
                    seat = o2.vertex_groups.get('rider_seat') or o2.vertex_groups.new(name='rider_seat')
                    seat.add([i for i, w in enumerate(g.w) if any(b.startswith('r:') for b in w)], 1.0, 'REPLACE')
                    mod = o2.modifiers.new('arm', 'ARMATURE'); mod.object = rig; o2.parent = rig
                    common.export_glb([rig, o2], os.path.join(common.MODELS, 'cavalry_hx_%s_rigged.glb' % vr), skins=True)
                    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(common.BLEND, 'cavalry_hx_%s.blend' % vr))
    json.dump(report, open(os.path.join(prev, 'bake_report.json'), 'w'), indent=1)
    print('REPORT', json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'reach'} for k, v in report.items()}))

if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main(argv)
