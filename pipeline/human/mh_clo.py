"""MakeHuman .mhclo proxy fitting (format reader, own implementation): each proxy vertex = barycentric mix of 3 base
vertices + an offset scaled by the base-mesh scale references; single-index lines = exact copy of one base vertex."""
import numpy as np

def read(path):
    refs, scale = [], {}
    in_verts = False
    for ln in open(path):
        s = ln.split()
        if not s or ln.startswith('#'): continue
        if s[0] in ('x_scale', 'y_scale', 'z_scale'):
            scale[s[0][0]] = (int(s[1]), int(s[2]), float(s[3])); continue
        if s[0] == 'verts': in_verts = True; continue
        if in_verts:
            if len(s) == 1 and s[0].lstrip('-').isdigit(): refs.append(((int(s[0]), 0, 0), (1.0, 0.0, 0.0), (0.0, 0.0, 0.0))); continue
            if len(s) == 9:
                refs.append((tuple(int(x) for x in s[:3]), tuple(float(x) for x in s[3:6]), tuple(float(x) for x in s[6:9]))); continue
            if s[0].isalpha(): in_verts = False
    return refs, scale

def fit(refs, scale, Vmh):
    """proxy vertex positions in MakeHuman obj space (decimetres, y up) from the (target-deformed) base vertices."""
    sc = np.ones(3)
    for k, ax in (('x', 0), ('y', 1), ('z', 2)):
        if k in scale:
            a, b, d = scale[k]; sc[ax] = abs(Vmh[a, ax] - Vmh[b, ax]) / d
    out = np.zeros((len(refs), 3))
    for i, (ix, w, off) in enumerate(refs):
        out[i] = sum(w[j] * Vmh[ix[j]] for j in range(3)) + np.array(off) * sc
    return out
