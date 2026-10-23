"""Prepass (system python + PIL): compose the CC0 eyebrow card (eyebrow002) into the CC0 MakeHuman skin albedo in the
base-mesh UV space, so the game atlas bakes brows straight from the skin. Writes pipeline/assets/mh/skin_soldier.png."""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import mh_base as M, mh_clo as C

A = M.ASSETS
def posmap(h, vuv, W, H, res=1024):
    """3D (IC, unposed) position of every texel of the skin UV, rasterised at res and upsampled; nan = no surface."""
    P = np.full((res, res, 3), np.nan, np.float32)
    V = h.V
    for f, t, g in zip(h.F, h.FT, h.G):
        if g != 'body': continue
        for a, b, c in [(0, 1, 2)] + ([(0, 2, 3)] if len(f) == 4 else []):
            uv = np.array([h.VT[t[k]] for k in (a, b, c)]) * [res, res]
            uv[:, 1] = res - uv[:, 1]
            x0, y0 = np.floor(uv.min(0)).astype(int); x1, y1 = np.ceil(uv.max(0)).astype(int)
            if x1 <= x0 or y1 <= y0: continue
            xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            T = np.array([[uv[0, 0] - uv[2, 0], uv[1, 0] - uv[2, 0]], [uv[0, 1] - uv[2, 1], uv[1, 1] - uv[2, 1]]])
            if abs(np.linalg.det(T)) < 1e-9: continue
            Ti = np.linalg.inv(T)
            l0 = Ti[0, 0] * (xs - uv[2, 0]) + Ti[0, 1] * (ys - uv[2, 1]); l1 = Ti[1, 0] * (xs - uv[2, 0]) + Ti[1, 1] * (ys - uv[2, 1])
            l2 = 1 - l0 - l1; ins = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
            if not ins.any(): continue
            p = l0[..., None] * V[f[a]] + l1[..., None] * V[f[b]] + l2[..., None] * V[f[c]]
            yy, xx = np.nonzero(ins)
            yy = np.clip(yy + y0, 0, res - 1); xx = np.clip(xx + x0, 0, res - 1)
            P[yy, xx] = p[ins]
    return P

def hair_mask(h, vuv, W, H, res=1024):
    P = posmap(h, vuv, W, H, res)
    he = h.V[sorted(h.gverts['helper-r-eye'])].mean(0); ze, ye = he[2], he[1]
    hv = h.V[[v for v in h.gverts['body'] if h.V[v][2] > ze - 0.1]]
    ymin, ymax = hv[:, 1].min(), hv[:, 1].max()
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    t = (y - ymin) / (ymax - ymin)
    # hairline height (relative to the eyes) along the head, back (t=0) to front (t=1)
    zh = ze + np.interp(t, [0.0, 0.30, 0.42, 0.50, 0.60, 0.72, 0.80, 1.0], [-0.080, -0.072, -0.030, 0.012, 0.030, 0.060, 0.074, 0.080])
    def ss(a, b, v): v = np.clip((v - a) / (b - a), 0, 1); return v * v * (3 - 2 * v)
    m = ss(-0.004, 0.006, z - zh)
    ear = (np.abs(x) > 0.071) & (t > 0.28) & (t < 0.56) & (z < ze + 0.035) & (z > ze - 0.06)
    m = np.where(ear, 0.0, m)
    sb = ss(0.505, 0.515, t) * ss(0.585, 0.570, t) * ss(ze - 0.045, ze - 0.035, z) * ss(0.055, 0.062, np.abs(x))   # sideburns
    m = np.maximum(m, sb * 0.95)
    m = np.nan_to_num(m * (z > ze - 0.12), nan=0.0)
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.5))
    return np.array(im).astype(np.float32) / 255.0

def main():
    h = M.Human()
    skin = Image.open(os.path.join(A, 'skin_middleage_caucasian_male.png')).convert('RGBA')
    W, H = skin.size
    # base vertex -> uv (first loop that uses it; the face / brow region has no UV seams)
    vuv = {}
    for f, t in zip(h.F, h.FT):
        for v, ti in zip(f, t):
            if ti >= 0 and v not in vuv: vuv[v] = h.VT[ti]
    refs, _ = C.read(os.path.join(A, 'eyebrow002.mhclo'))
    _, VT, F, FT, _ = M.read_obj(os.path.join(A, 'eyebrow002.obj'))
    # proxy vertex skin-uv = barycentric mix of its reference vertices' uvs
    puv = np.array([sum(w[j] * vuv[ix[j]] for j in range(3)) for ix, w, off in refs])
    brow = Image.open(os.path.join(A, 'eyebrow002.png')).convert('RGBA')
    bw, bh = brow.size
    acc = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for f, t in zip(F, FT):
        tris = [(0, 1, 2)] + ([(0, 2, 3)] if len(f) == 4 else [])
        for a, b, c in tris:
            src = np.array([[VT[t[k]][0] * bw, (1 - VT[t[k]][1]) * bh] for k in (a, b, c)])
            dst = np.array([[puv[f[k]][0] * W, (1 - puv[f[k]][1]) * H] for k in (a, b, c)])
            # affine dst->src for PIL
            Am = np.hstack([dst, np.ones((3, 1))]); coef = np.linalg.solve(Am, src)
            x0, y0 = np.floor(dst.min(0)).astype(int); x1, y1 = np.ceil(dst.max(0)).astype(int)
            if x1 <= x0 or y1 <= y0: continue
            ww, hh = x1 - x0, y1 - y0
            # map: src = [x+x0, y+y0, 1] @ coef
            data = (coef[0, 0], coef[1, 0], coef[0, 0] * x0 + coef[1, 0] * y0 + coef[2, 0],
                    coef[0, 1], coef[1, 1], coef[0, 1] * x0 + coef[1, 1] * y0 + coef[2, 1])
            patch = brow.transform((ww, hh), Image.AFFINE, data, resample=Image.BICUBIC)
            mask = Image.new('L', (ww, hh), 0)
            from PIL import ImageDraw
            ImageDraw.Draw(mask).polygon([tuple(p - (x0, y0)) for p in dst], fill=255)
            pa = np.array(patch); pa[..., 3] = (pa[..., 3].astype(np.uint16) * (np.array(mask) > 0)).astype(np.uint8)
            acc.alpha_composite(Image.fromarray(pa), (x0, y0))
    # brows: dark brown hair colour, slightly softened; composite over skin
    a0 = np.array(acc.split()[3]).astype(np.float32) / 255.0
    soft = np.array(acc.split()[3].filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(2.0))).astype(np.float32) / 255.0
    rng = np.random.default_rng(7); n = 0.75 + 0.25 * rng.random(a0.shape)
    al = np.clip(np.maximum(a0 * 0.8, soft * 0.35) * n, 0, 0.85)[..., None]
    hair = np.array([0.22, 0.155, 0.11])
    s = np.array(skin).astype(np.float32)[..., :3] / 255.0
    out = s * (1 - al) + hair * al
    # cropped hair + sideburns (the base is bald): mask from the 3D position of every skin texel
    hm = hair_mask(h, vuv, W, H)
    rng = np.random.default_rng(11)
    strands = np.array(Image.fromarray((rng.random((H, W)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32) / 255.0
    strands = np.clip((strands - 0.5) * 3.0 + 0.5, 0, 1)
    ah = (hm * (0.62 + 0.3 * strands))[..., None]
    hc = np.array([0.15, 0.105, 0.075]) * (0.8 + 0.4 * strands[..., None])
    out = out * (1 - ah) + hc * ah
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(A, 'skin_soldier.png'))
    print('brow pixels', int((al[..., 0] > 0.1).sum()))

if __name__ == '__main__':
    main()
