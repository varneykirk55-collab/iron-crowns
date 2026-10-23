"""Foot-slide check for baked character VATs (plain python3 + numpy; no Blender needed).
Planted sole vertices (height < H in two consecutive frames) must move backwards at the clip's authored ground speed
(walk 1.4 m/s, run 3.6 m/s, other clips 0); residual = slide. Usage: python3 char_footslide.py [ids...]"""
import json, os, sys
import numpy as np
VAT = os.path.join(os.path.dirname(__file__), '..', '..', 'game', 'assets', 'vat')
SPEED = {'walk': 1.4, 'run': 3.6, 'idle': 0.0, 'fire': 0.0, 'melee': 0.0}
H = 0.012

def check(kid, lod=0):
    j = json.load(open(os.path.join(VAT, f'{kid}_lod{lod}.json')))
    n, F, fps = j['vertices'], j['frames'], j['fps']
    P = np.fromfile(os.path.join(VAT, f'{kid}_lod{lod}.vat'), np.float32).reshape(F, n, 3)
    out = {}
    for cn, v in SPEED.items():
        c = j['clips'][cn]; s, k, loop = c['start'], c['count'], c['loop']
        res = []
        for f in range(k if loop else k - 1):
            a = P[s + f]; b = P[s + (f + 1) % k]
            m = (a[:, 1] < H) & (b[:, 1] < H)
            if not m.any():
                continue
            vel = (b[m] - a[m]) * fps                 # Godot coords: forward = -Z, so the planted ground moves +Z
            err = vel - np.array([0.0, 0.0, v])
            res.append(np.linalg.norm(err[:, [0, 2]], axis=1).mean())
        out[cn] = (float(np.mean(res)) if res else float('nan'), float(np.max(res)) if res else float('nan'), len(res))
    return out

if __name__ == '__main__':
    ids = sys.argv[1:] or ['c19sr_line', 'c19sr_grenadier', 'c19sr_artillery', 'c19sr_officer']
    print('kit clip mean_slide_m/s max_slide_m/s planted_frames')
    for kid in ids:
        for cn, (mu, mx, nf) in check(kid).items():
            print(f'{kid} {cn} {mu:.3f} {mx:.3f} {nf}')
