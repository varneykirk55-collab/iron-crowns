"""Contact sheets for the HX cavalry VATs (system python: numpy + PIL).  Painter's-algorithm flat render.
usage: python3 tools/cav/hx_sheet.py <vat_base> <mesh_json> <out.png> clip[:n] [clip[:n] ...] [--view side|q3|front|top] [--cell 260]"""
import sys, json, math
import numpy as np
from PIL import Image, ImageDraw

def load(base):
    js = json.load(open(base + '.json'))
    a = np.fromfile(base + '.vat', np.float32).reshape(js['frames'], js['vertices'], 3)
    b = np.stack([a[..., 0], -a[..., 2], a[..., 1]], -1)      # back to blender coords (x right, y fwd, z up)
    return js, b

def view_mat(view):
    if view == 'side':     # camera on the horse's left (-X) looking +X: screen x = +y (forward to the right)... flipped so forward = left->right
        yaw, pitch = 90.0, 8.0
    elif view == 'q3':
        yaw, pitch = 135.0, 18.0
    elif view == 'front':
        yaw, pitch = 180.0, 6.0
    elif view == 'top':
        yaw, pitch = 90.0, 80.0
    elif view == 'rside':
        yaw, pitch = -90.0, 8.0
    else:
        yaw, pitch = float(view), 12.0
    y = math.radians(yaw); p = math.radians(pitch)
    # camera looks along direction d (from camera to subject)
    d = np.array([math.cos(p) * math.sin(y) * 1.0, -math.cos(p) * math.cos(y), -math.sin(p)])
    d = np.array([-math.cos(p) * math.cos(y - math.pi / 2), -math.cos(p) * math.sin(y - math.pi / 2), -math.sin(p)])
    up = np.array([0, 0, 1.0])
    r = np.cross(d, up); r /= np.linalg.norm(r)
    u = np.cross(r, d)
    return r, u, d

def render(P, faces, cols, view, size, ctr, scale, ground=True, label=None):
    W, Hh = size
    img = Image.new('RGB', size, (205, 210, 200))
    dr = ImageDraw.Draw(img)
    r, u, d = view_mat(view)
    def proj(X):
        Xc = X - ctr
        return np.stack([W / 2 + (Xc @ r) * scale, Hh * 0.62 - (Xc @ u) * scale, Xc @ d], -1)
    if ground:
        g = []
        for gx in np.linspace(-3, 3, 13):
            a = proj(np.array([[gx, -3.0 + ctr[1], 0], [gx, 3.0 + ctr[1], 0]]))
            dr.line([tuple(a[0, :2]), tuple(a[1, :2])], fill=(180, 186, 176))
        for gy in np.linspace(-3, 3, 13):
            a = proj(np.array([[-3.0 + ctr[0], gy + ctr[1], 0], [3.0 + ctr[0], gy + ctr[1], 0]]))
            dr.line([tuple(a[0, :2]), tuple(a[1, :2])], fill=(180, 186, 176))
    S = proj(P)
    L = np.array([0.4, -0.5, 0.75]); L /= np.linalg.norm(L)
    tris = []
    for fi, f in enumerate(faces):
        pts = P[f]
        n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        nl = np.linalg.norm(n)
        if nl < 1e-12:
            continue
        n /= nl
        if n @ d > 0:      # back face
            continue
        depth = S[f, 2].mean()
        tris.append((depth, fi, n))
    tris.sort(key=lambda t: -t[0])
    for depth, fi, n in tris:
        f = faces[fi]
        c = cols[fi]
        team = c[3]
        base = np.array(c[:3]) * (1 - team) + np.array([0.75, 0.15, 0.12]) * team
        sh = 0.45 + 0.55 * max(0.0, float(n @ L))
        rgb = tuple(int(min(255, x * sh * 255)) for x in base)
        dr.polygon([tuple(S[i, :2]) for i in f], fill=rgb)
    if label:
        dr.text((4, 4), label, fill=(0, 0, 0))
    return img

def main(a):
    base, mesh, out = a[0], a[1], a[2]
    rest = a[3:]
    view = 'side'; cell = 260; follow = True
    specs = []
    i = 0
    while i < len(rest):
        if rest[i] == '--view':
            view = rest[i + 1]; i += 2; continue
        if rest[i] == '--cell':
            cell = int(rest[i + 1]); i += 2; continue
        specs.append(rest[i]); i += 1
    js, B = load(base)
    m = json.load(open(mesh))
    faces = [np.array(f) for f in m['faces']]; cols = m['cols']
    rows = []
    for sp in specs:
        nm, _, n = sp.partition(':')
        c = js['clips'][nm]
        n = int(n) if n else min(c['count'], 8)
        fr = [c['start'] + int(round(k * (c['count'] - (0 if c['loop'] else 1)) / (n if c['loop'] else max(n - 1, 1)))) for k in range(n)]
        fr = [min(x, c['start'] + c['count'] - 1) for x in fr]
        rows.append((nm, fr))
    ncol = max(len(fr) for _, fr in rows)
    sheet = Image.new('RGB', (ncol * cell, len(rows) * cell), (255, 255, 255))
    for ri, (nm, fr) in enumerate(rows):
        for ci, f in enumerate(fr):
            ctr = np.array([0.0, 0.0, 1.1])
            im = render(B[f], faces, cols, view, (cell, cell), ctr, cell / 4.2, label='%s %d' % (nm, f - js['clips'][nm]['start']))
            sheet.paste(im, (ci * cell, ri * cell))
    sheet.save(out)
    print('wrote', out, sheet.size)

if __name__ == '__main__':
    main(sys.argv[1:])
