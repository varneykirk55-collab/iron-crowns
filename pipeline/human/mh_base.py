"""MakeHuman hm08 base-mesh loader (CC0 assets, see docs/char/LICENSES.md). Pure numpy, no MakeHuman / MPFB code.
Loads base.obj, applies macro targets (gender / age / race / muscle / weight / height), resolves the default-rig joint
positions and the default skin weights, and converts everything to Iron Crowns character space:
metres, +Z up, character faces +Y, +X = the character's right side (MakeHuman: decimetres, +Y up, faces +Z, +X = left)."""
import os, gzip, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.environ.get('IC_MH_ASSETS', os.path.join(HERE, '..', 'assets', 'mh'))

def to_ic(p):
    p = np.asarray(p, np.float64)
    return np.stack([-p[..., 0], p[..., 2], p[..., 1]], -1) * 0.1

def mpfb_to_ic(p):   # MPFB Blender coords (metres, z up, faces -Y, +X = left) -> ours
    p = np.asarray(p, np.float64)
    return np.stack([-p[..., 0], -p[..., 1], p[..., 2]], -1)

def read_obj(path):
    V, VT, F, FT, G = [], [], [], [], []
    g = None
    for ln in open(path):
        if ln.startswith('v '): V.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith('vt '): VT.append([float(x) for x in ln.split()[1:3]])
        elif ln.startswith('g '): g = ln.split()[1]
        elif ln.startswith('f '):
            vs, ts = [], []
            for tok in ln.split()[1:]:
                a = tok.split('/'); vs.append(int(a[0]) - 1); ts.append(int(a[1]) - 1 if len(a) > 1 and a[1] else -1)
            F.append(vs); FT.append(ts); G.append(g)
    return np.array(V), np.array(VT) if VT else np.zeros((0, 2)), F, FT, G

def read_target(path):
    op = gzip.open if path.endswith('.gz') else open
    idx, d = [], []
    for ln in op(path, 'rt'):
        s = ln.split()
        if len(s) == 4 and not ln.startswith('#'):
            idx.append(int(s[0])); d.append([float(x) for x in s[1:]])
    return np.array(idx, np.int64), np.array(d).reshape(-1, 3)

def _mix(lo, hi, v, lo_name, mid_name, hi_name):
    """MakeHuman two-part macro weights -> {name: weight} (v in 0..1, 0.5 = average)."""
    if v < 0.5: return {lo_name: 1.0 - v / 0.5, mid_name: v / 0.5}
    return {mid_name: 1.0 - (v - 0.5) / 0.5, hi_name: (v - 0.5) / 0.5}

class Human:
    def __init__(self, muscle=0.62, weight=0.5, height=0.55, race='caucasian', age='young', gender='male'):
        A = ASSETS
        self.V0, self.VT, self.F, self.FT, self.G = read_obj(os.path.join(A, 'base.obj'))
        V = self.V0.copy()
        T = os.path.join(A, 'targets')
        ms = _mix(0, 1, muscle, 'minmuscle', 'averagemuscle', 'maxmuscle')
        ws = _mix(0, 1, weight, 'minweight', 'averageweight', 'maxweight')
        applied = []
        def add(name, w):
            if w < 1e-4: return
            p = os.path.join(T, name + '.target.gz')
            if not os.path.exists(p): return
            i, d = read_target(p); V[i] += w * d; applied.append((name, round(w, 3)))
        add(f'{race}-{gender}-{age}', 1.0)
        for m, a in ms.items():
            for w, b in ws.items():
                add(f'universal-{gender}-{age}-{m}-{w}', a * b)
                if height > 0.5: add(f'{gender}-{age}-{m}-{w}-maxheight', a * b * (height - 0.5) * 2)
                elif height < 0.5: add(f'{gender}-{age}-{m}-{w}-minheight', a * b * (0.5 - height) * 2)
        self.applied = applied
        self.Vmh = V
        self.V = to_ic(V)
        # groups -> vertex sets
        self.gverts = {}
        for f, g in zip(self.F, self.G):
            self.gverts.setdefault(g, set()).update(f)
        self.rig = json.load(open(os.path.join(A, 'rig.default.json')))
        self.weights = json.load(open(os.path.join(A, 'weights.default.json')))['weights']

    def joint(self, spec, V=None):
        V = self.V if V is None else V
        s = spec['strategy']
        if s == 'CUBE':
            vs = sorted(self.gverts['joint-' + spec['cube_name'][len('joint-'):]] if spec['cube_name'].startswith('joint-') else self.gverts[spec['cube_name']])
            return V[vs].mean(0)
        if s == 'VERTEX': return V[spec['vertex_index']]
        if s == 'MEAN': return V[spec['vertex_indices']].mean(0)
        raise ValueError(s)

    def bones(self, V=None):
        out = {}
        for n, b in self.rig.items():
            out[n] = (self.joint(b['head'], V), self.joint(b['tail'], V), b.get('parent'), b.get('roll', 0.0))
        return out

    def faces_in(self, groups):
        return [i for i, g in enumerate(self.G) if g in groups]
