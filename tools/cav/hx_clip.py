"""Coat-through-cloth check for horse v3 bakes: for every hide vertex (layer horse_body, mat 8) under the covering cloth
(rest distance < 0.08 m to a cover vertex), signed distance to the nearest cover vertex along its baked normal, per frame.
d > EPS = the coat is outside the cloth there (a visible speck).  usage: hx_clip.py <vat_base> <mesh_json> <knight|hussar>"""
import sys, json
import numpy as np
EPS = 0.004
base, mj, kind = sys.argv[1:4]
js = json.load(open(base + '.json')); F, V = js['frames'], js['vertices']
P = np.fromfile(base + '.vat', np.float32).reshape(F, V, 3)
N = np.fromfile(base + '.vatn', np.uint8).reshape(F, V, 4)[..., :3].astype(np.float32) / 255.0 * 2.0 - 1.0
m = json.load(open(mj))
cov_l, cov_m = ('barding_1300', {1}) if kind == 'knight' else ('tack_1800', {1, 9})
body = set(); cov = set()
for f, l, mt in zip(m['faces'], m['layers'], m['mats']):
    if l == 'horse_body' and mt == 8: body.update(f)
    if l == cov_l and mt in cov_m: cov.update(f)
body = np.array(sorted(body)); cov = np.array(sorted(cov))
R = P[0]   # first frame (stand) as reference for the pairing
NR = N[0]
D = R[cov][None, :, :] - R[body][:, None, :]                # body -> cover
dist = np.linalg.norm(D, axis=-1)
along = (D * NR[body][:, None, :]).sum(-1)                   # along the body normal
lat = np.sqrt(np.maximum(dist ** 2 - along ** 2, 0))
face = (NR[body][:, None, :] * NR[cov][None, :, :]).sum(-1)   # cloth facing the same way (not a hem / far side)
score = np.where((dist < 0.08) & (face > 0.5) & (along > -0.06), lat + 0.2 * np.abs(along), 9.0)
nn = score.argmin(1); best = score[np.arange(len(body)), nn]
sel = best < 0.03
bi = body[sel]; ci = cov[nn[sel]]
tot = 0; worst = []
for name, c in js['clips'].items():
    if name in ('idle', 'walk', 'run', 'melee', 'fire', 'die'): continue
    s = slice(c['start'], c['start'] + c['count'])
    d = ((P[s, bi] - P[s, ci]) * N[s, ci]).sum(-1)       # + = body outside cloth
    out = d > EPS
    n_v = int(out.any(0).sum()); tot += n_v
    worst.append((name, n_v, float(d.max())))
    if n_v and '-v' in sys.argv:
        k = out.any(0); print('   ', name, 'at (godot x,y,z) e.g.', np.round(R[bi[k]][:4], 2).tolist())
print('covered hide verts', len(bi), 'out at rest', int((((R[bi] - R[ci]) * NR[ci]).sum(-1) > EPS).sum()))
for w in sorted(worst, key=lambda x: -x[1])[:8]:
    print('  %-16s verts_out %4d  max %.3f m' % w)
print('TOTAL_OUT', tot, 'clips_with_out', sum(1 for w in worst if w[1]))
