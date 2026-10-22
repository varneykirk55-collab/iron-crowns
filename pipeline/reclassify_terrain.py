"""Refine province terrain using the Natural Earth shaded-relief albedo colour + elevation + latitude."""
import json, numpy as np, os
from PIL import Image
M = os.path.join(os.path.dirname(__file__), '..', 'game', 'data', 'map')
d = json.load(open(os.path.join(M, 'provinces.json')))
W, H = d['width'], d['height']
ids = np.fromfile(os.path.join(M, 'province_ids.bin'), dtype=np.uint16).reshape(H, W)
alb = np.asarray(Image.open(os.path.join(M, 'albedo.jpg')).convert('RGB').resize((W, H))).astype(np.float32) / 255
hgt = np.fromfile(os.path.join(M, 'heights.bin'), dtype=np.float16).reshape(H // 2, W // 2).astype(np.float32)
hgt = np.repeat(np.repeat(hgt, 2, 0), 2, 1)
flat = ids.ravel()
cnt = np.bincount(flat, minlength=65536).astype(np.float64)
r = np.bincount(flat, alb[..., 0].ravel(), 65536) / np.maximum(cnt, 1)
g = np.bincount(flat, alb[..., 1].ravel(), 65536) / np.maximum(cnt, 1)
b = np.bincount(flat, alb[..., 2].ravel(), 65536) / np.maximum(cnt, 1)
hm = np.bincount(flat, hgt.ravel(), 65536) / np.maximum(cnt, 1)
hs = np.sqrt(np.maximum(np.bincount(flat, (hgt ** 2).ravel(), 65536) / np.maximum(cnt, 1) - hm ** 2, 0))
from collections import Counter
for p in d['provinces']:
    i = p['id']; R, G, B = r[i], g[i], b[i]; lat = abs(p['lat']); e = hm[i]; rough = hs[i]
    bright = (R + G + B) / 3
    gr = G - R
    if lat >= 66 or (lat > 58 and gr < 0.06) or bright > 0.93 and lat > 40: t = 'tundra'
    elif R >= G - 0.006 and lat < 42 and bright > 0.8: t = 'desert'
    elif rough > 0.55 or e > 1.6: t = 'mountains'
    elif gr > 0.09: t = 'jungle' if lat < 23 else 'forest'
    elif rough > 0.25 or e > 0.7: t = 'hills'
    elif gr > 0.055 and lat > 42: t = 'forest'
    else: t = 'plains'
    p['terrain'] = t
json.dump(d, open(os.path.join(M, 'provinces.json'), 'w'), separators=(',', ':'))
print(Counter(p['terrain'] for p in d['provinces']))
for code in ('USA', 'SWE', 'JPN', 'EGY', 'BRA', 'RUS'):
    print(code, [(p['name'], p['terrain']) for p in d['provinces'] if p['owner'] == code][:10])
