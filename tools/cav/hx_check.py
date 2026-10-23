"""Numeric self-check of HX VATs: ground penetration, per-frame pops, loop seams.  usage: hx_check.py <vat_base> [<mesh_json>]"""
import sys, json
import numpy as np
b = sys.argv[1]
js = json.load(open(b + '.json')); a = np.fromfile(b + '.vat', np.float32).reshape(js['frames'], js['vertices'], 3)
lay = None
if len(sys.argv) > 2:
    m = json.load(open(sys.argv[2])); lay = np.array([''] * js['vertices'], dtype=object)
    for f, l in zip(m['faces'], m['layers']):
        for i in f: lay[i] = l
bad = 0
for n, c in js['clips'].items():
    if n in ('idle', 'walk', 'run', 'melee', 'fire', 'die'):
        continue
    s = a[c['start']:c['start'] + c['count']]
    d = np.linalg.norm(np.diff(s, axis=0), axis=2)
    seam = np.linalg.norm(s[0] - s[-1], axis=1).max() if c['loop'] else 0.0
    jmp = d.max(); f = int(d.max(1).argmax())
    who = lay[d[f].argmax()] if lay is not None else ''
    flag = ' <<' if (jmp > 0.45 or s[..., 1].min() < -0.2) else ''
    bad += bool(flag)
    print('%-18s n=%3d minY %+.3f maxjump %.3f@%d(%s) seam %.3f%s' % (n, c['count'], s[..., 1].min(), jmp, f, who, seam, flag))
print('FLAGGED', bad)
