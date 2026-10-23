"""quick orthographic flat-shaded preview (PIL painter's algorithm) for the posed human - dev aid, no Blender."""
import numpy as np
from PIL import Image, ImageDraw

def render(V, F, view='front', size=900, box=None, out='/tmp/p.png', faces=None):
    V = np.asarray(V, float)
    yaw = {'front': 0, 'side': 90, 'back': 180, 'q': 35, 'lside': -90}[view]
    a = np.radians(yaw)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    W = V @ Rz.T       # camera looks along -y (from +y toward the character's face)
    X, D, Z = W[:, 0], W[:, 1], W[:, 2]
    if box is None: box = (X.min(), X.max(), Z.min(), Z.max())
    x0, x1, z0, z1 = box; sc = size / max(x1 - x0, z1 - z0)
    img = Image.new('RGB', (int((x1 - x0) * sc) + 1, int((z1 - z0) * sc) + 1), (40, 44, 52)); dr = ImageDraw.Draw(img)
    fl = faces if faces is not None else range(len(F))
    tris = []
    for i in fl:
        f = F[i]
        p = W[f]
        n = np.cross(p[1] - p[0], p[2] - p[0]); ln = np.linalg.norm(n)
        if ln == 0: continue
        n /= ln
        if n[1] <= 0: continue   # backface (camera at +y... looking -y): front faces have normal +y
        tris.append((p[:, 1].mean(), i, n))
    tris.sort()
    L = np.array([-0.4, 0.75, 0.5]); L /= np.linalg.norm(L)
    for d, i, n in tris:
        f = F[i]
        c = 0.25 + 0.75 * max(0, float(n @ L))
        col = tuple(int(255 * c * k) for k in (0.92, 0.80, 0.72))
        pts = [((X[v] - x0) * sc, (z1 - Z[v]) * sc) for v in f]
        dr.polygon(pts, fill=col)
    img.save(out)
    return img
