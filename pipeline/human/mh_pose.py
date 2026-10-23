"""Era-generic human base: MakeHuman (CC0) body -> Iron Crowns rest pose, in numpy (no Blender needed).
 1. macro-target the base mesh (mh_base.Human), scale to the IC stature (sole z=SOLE, crown z=CROWN)
 2. linear-blend-skin the MH default skeleton into OUR frozen rest (char_rig.BONES): limb chains re-aimed along our bone
    directions, joints pulled onto our joint positions, fingers curled round the musket grip axis (GRIP_C)
 3. MH bone weights summed onto our bone names (MH_TO_IC) for the game skin
IC coords: metres, z up, faces +y, +x = character's right."""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import mh_base as MB

SOLE, CROWN = 0.012, 1.772
# our joints (char_rig.BONES heads / tails, right side; mirrored for .L) - duplicated here so this module is Blender-free
J = {'shoulder': (0.18, -0.012, 1.425), 'elbow': (0.205, -0.012, 1.14), 'wrist': (0.222, 0.0, 0.895), 'hand_end': (0.228, 0.004, 0.735),
     'hip': (0.095, 0.0, 0.925), 'knee': (0.10, 0.012, 0.505), 'ankle': (0.10, -0.012, 0.088)}
GRIP_C = (0.203, 0.790); GRIP_R = 0.0175
NECK_TILT, NECK_SHIFT = 11.0, (0.0, -0.016, 0.0)

def mh_to_ic_bone(n):
    """MH default-rig bone -> IC deform bone."""
    side = '.R' if n.endswith('.R') else '.L' if n.endswith('.L') else ''
    b = n[:-2] if side else n
    if b in ('root', 'spine05', 'spine04', 'pelvis', 'special01'): return 'hips'
    if b == 'spine03': return 'spine'
    if b in ('spine02', 'spine01', 'breast', 'levator01'): return 'chest'
    if b.startswith('neck'): return 'neck'
    if b == 'clavicle': return 'clav' + side
    if b in ('shoulder01', 'upperarm01', 'upperarm02'): return 'upper_arm' + side
    if b.startswith('lowerarm'): return 'forearm' + side
    if b in ('wrist',) or b.startswith('metacarpal') or b.startswith('finger'): return 'hand' + side
    if b.startswith('upperleg'): return 'thigh' + side
    if b.startswith('lowerleg'): return 'shin' + side
    if b == 'foot' or b.startswith('toe'): return 'foot' + side
    return 'head'   # head, jaw, eyes, face muscles, tongue

def norm(v): return v / max(1e-9, np.linalg.norm(v))

def rot_between(a, b):
    a, b = norm(a), norm(b); v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.999999:
        ax = norm(np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0])); return axis_angle(ax, math.pi)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)

def axis_angle(ax, ang):
    ax = norm(np.asarray(ax, float)); x, y, z = ax; c, s = math.cos(ang), math.sin(ang); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s], [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])

def mir(p, s): return np.array([s * p[0], p[1], p[2]])

class PosedHuman:
    def __init__(self, curl=1.0, spread=0.0, grip_off=(0.0, 0.0, 0.0), human=None, fist=None, **macro):
        self.fist = dict(fist or {})   # {'.L': r}: that hand closes round a thinner virtual grip (relaxed fist, empty hand)
        h = human or MB.Human(**macro); self.h = h
        body = sorted(h.gverts['body'])
        V = h.V.copy()
        zmin, zmax = V[body, 2].min(), V[body, 2].max()
        k = (CROWN - SOLE) / (zmax - zmin)
        V = (V - [0, 0, zmin]) * k + [0, 0, SOLE]
        # centre x on 0, y so the ankle sits under our ankle joint
        self.scale = k; self.zmin = zmin
        bones = h.bones(V)
        self.rest_bones = bones
        names = list(bones)
        order, seen = [], set()
        def visit(n):
            if n in seen: return
            p = bones[n][2]
            if p: visit(p)
            seen.add(n); order.append(n)
        for n in names: visit(n)
        # weights matrix
        nv = len(V)
        self.bone_index = {n: i for i, n in enumerate(names)}
        W = np.zeros((nv, len(names)), np.float32)
        for n, lst in h.weights.items():
            if n not in self.bone_index: continue
            for vi, w in lst: W[vi, self.bone_index[n]] = w
        s = W.sum(1); W[s > 0] /= s[s > 0, None]
        W[s == 0, self.bone_index['head']] = 1.0   # (unweighted helper geometry)
        self.W = W
        # targets per chain bone (dir + head position), right side, mirrored for left
        tgt = {}
        for s_, sfx in ((1, '.R'), (-1, '.L')):
            jp = {k_: mir(np.array(v), s_) for k_, v in J.items()}
            ua = jp['elbow'] - jp['shoulder']; fa = jp['wrist'] - jp['elbow']; hd = jp['hand_end'] - jp['wrist']
            th = jp['knee'] - jp['hip']; sh = jp['ankle'] - jp['knee']
            sp = np.array([s_ * spread, 0, 0])
            tgt['upperarm01' + sfx] = (ua, jp['shoulder'] + sp); tgt['upperarm02' + sfx] = (ua, None)
            tgt['lowerarm01' + sfx] = (fa, jp['elbow'] + sp); tgt['lowerarm02' + sfx] = (fa, None)
            tgt['wrist' + sfx] = (hd, jp['wrist'] + sp + mir(np.array(grip_off, float), s_))
            tgt['upperleg01' + sfx] = (th, jp['hip']); tgt['upperleg02' + sfx] = (th, None)
            tgt['lowerleg01' + sfx] = (sh, jp['knee']); tgt['lowerleg02' + sfx] = (sh, None)
            tgt['foot' + sfx] = ('world', jp['ankle'])
        # neck: MH stands with the head carried ~5 cm forward of our head bone; bring the neck up straighter and back so
        # the cranium sits under the head bone (the shako / collar kit is authored round it)
        tgt['neck01'] = (('rotx', NECK_TILT), bones['neck01'][0] + np.array(NECK_SHIFT))
        tgt['head'] = (('rotx', -NECK_TILT), None)   # face stays upright
        self.tgt = tgt
        R = {}; P = {}   # posed rotation + posed head per bone:  x' = P[b] + R[b] (x - head_rest[b])
        for n in order:
            hd, tl, par, roll = bones[n]
            Rp = R[par] if par else np.eye(3)
            ph = (P[par] + Rp @ (hd - bones[par][0])) if par else hd.copy()
            Rb = Rp
            if n in tgt:
                d, pos = tgt[n]
                if isinstance(d, str): Rb = np.eye(3)   # feet: keep their rest orientation (flat on the ground)
                elif isinstance(d, tuple): Rb = axis_angle([1, 0, 0], math.radians(d[1])) @ Rp
                else: Rb = rot_between(Rp @ (tl - hd), d) @ Rp
                if pos is not None: ph = np.array(pos, float)
            R[n] = Rb; P[n] = ph
        # hand: roll about the hand axis so the palm faces the thigh (medial), then curl the fingers round the grip axis
        for s_, sfx in ((1, '.R'), (-1, '.L')):
            w = 'wrist' + sfx
            ax = norm(R[w] @ (bones[w][1] - bones[w][0]))
            # palm normal from the posed metacarpal heads (index -> little) and the hand axis
            m1 = P[w] + R[w] @ (bones['finger2-1' + sfx][0] - bones[w][0]); m4 = P[w] + R[w] @ (bones['finger5-1' + sfx][0] - bones[w][0])
            across = norm(m4 - m1)                       # index -> little finger
            pn = norm(np.cross(ax, across)) * s_         # palm normal candidate
            want = np.array([-s_, 0.0, 0.0])             # palm toward the body (medial)
            pn_p = norm(pn - ax * np.dot(pn, ax)); want_p = norm(want - ax * np.dot(want, ax))
            ang = math.atan2(np.dot(np.cross(pn_p, want_p), ax), np.dot(pn_p, want_p))
            self.palm_fix = getattr(self, 'palm_fix', {}); self.palm_fix[sfx] = math.degrees(ang)
            Rr = axis_angle(ax, ang)
            self._rot_subtree(order, bones, R, P, w, Rr, P[w])
        self.R, self.P, self.order, self.bones_ = R, P, order, bones
        if curl:
            self.curl(curl)
        self.V = self.skin(V)
        self.Vrest = V

    def _rot_subtree(self, order, bones, R, P, root, Rr, pivot):
        sub = {root}
        for n in order:
            if bones[n][2] in sub: sub.add(n)
        for n in sub:
            R[n] = Rr @ R[n]; P[n] = pivot + Rr @ (P[n] - pivot)

    def curl(self, amt=1.0, rf=0.0088):
        """wrap the fingers round the grip cylinder (axis = world y through GRIP_C, radius GRIP_R): each phalanx, proximal
        first, is turned (fingers: about +-y toward the palm; thumb: about the axis that moves its tip radially) by the
        angle that brings its tip to GRIP_R + finger radius from the grip axis without cutting into the grip."""
        R, P, bones, order = self.R, self.P, self.bones_, self.order
        for s_, sfx in ((1, '.R'), (-1, '.L')):
            r = self.fist.get(sfx, GRIP_R); D = r + rf
            # thinner grip: its axis moves toward the palm (outward) so the palm still rests on it
            c = np.array([s_ * (GRIP_C[0] + (GRIP_R - r)), 0.0, GRIP_C[1]])
            def dist(p): return math.hypot(p[0] - c[0], p[2] - c[2])
            def seg(n):
                hd, tl = bones[n][0], bones[n][1]
                return P[n], P[n] + R[n] @ (tl - hd)
            def solve(n, axis, angs, Dn):
                h0, t0 = seg(n)
                best = None
                for a in angs:
                    Rr = axis_angle(axis, math.radians(a))
                    t = h0 + Rr @ (t0 - h0)
                    pts = [h0 + (t - h0) * k for k in (0.25, 0.5, 0.75, 1.0)]
                    dm = min(dist(p) for p in pts)
                    cost = abs(dist(t) - Dn) + 4.0 * max(0.0, Dn - 0.001 - dm) + 0.00002 * abs(a)
                    if best is None or cost < best[0]: best = (cost, a)
                self._rot_subtree(order, bones, R, P, n, axis_angle(axis, math.radians(best[1] * amt)), P[n])
                return best[1]
            self.curl_angles = getattr(self, 'curl_angles', {})
            for f in (2, 3, 4, 5):
                h0, t0 = seg(f'finger{f}-1{sfx}')
                fax = norm(np.cross(norm(t0 - h0), np.array([-s_, 0.0, 0.0])))   # the finger's own flexion axis
                for g in (1, 2, 3):
                    n = f'finger{f}-{g}{sfx}'
                    self.curl_angles[n] = solve(n, fax, np.arange({1: 22, 2: 30, 3: 24}[g], {1: 76, 2: 101, 3: 76}[g], 2.0), D)
            for g in (1, 2, 3):   # thumb: over the top of the grip, down its inner side, tip toward the middle phalanges
                n = f'finger1-{g}{sfx}'
                self.curl_angles[n] = solve(n, np.array([0.0, s_, 0.0]), np.arange(-60, 91, 2.0), D + 0.001)

    def skin(self, V):
        out = np.zeros_like(V)
        bones = self.bones_
        for n, i in self.bone_index.items():
            w = self.W[:, i]; m = w > 0
            if not m.any(): continue
            hd = bones[n][0]
            out[m] += w[m, None] * ((V[m] - hd) @ self.R[n].T + self.P[n])
        return out

    def ic_weights(self):
        """{ic_bone: np.array(nv)} summed from the MH weights."""
        out = {}
        for n, i in self.bone_index.items():
            b = mh_to_ic_bone(n); out.setdefault(b, np.zeros(len(self.W), np.float32))
            out[b] += self.W[:, i]
        return out

    def joint(self, n):
        return self.P[n]
