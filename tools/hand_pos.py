#!/usr/bin/env python3
"""Hand centres (Godot coords, model origin) of a v2 VAT unit at a clip's first frame, for proto_shots --close=1 --hr/--hl.
usage: hand_pos.py <model> [clip]   e.g. hand_pos.py c19v2_line idle"""
import json, struct, sys, numpy as np
m = sys.argv[1]; clip = sys.argv[2] if len(sys.argv) > 2 else 'idle'
j = json.load(open(f'game/assets/vat/{m}_lod0.json'))
b = open(f'game/assets/models/soldier_{m}_lod0.glb', 'rb').read()
n0 = struct.unpack_from('<I', b, 12)[0]; g = json.loads(b[20:20 + n0]); bin0 = 20 + n0 + 8
def acc(i):
    a = g['accessors'][i]; v = g['bufferViews'][a['bufferView']]
    k = {'VEC2': 2, 'VEC3': 3}[a['type']]
    return np.frombuffer(b, np.float32, a['count'] * k, bin0 + v.get('byteOffset', 0) + a.get('byteOffset', 0)).reshape(-1, k)
slot, vid = [], []
for pr in g['meshes'][0]['primitives']:
    slot.append(acc(pr['attributes']['TEXCOORD_0'])[:, 0]); vid.append(acc(pr['attributes']['TEXCOORD_1'])[:, 0])
slot = np.floor(np.concatenate(slot) * 32).astype(int); vid = np.clip((np.concatenate(vid) * j['vertices']).astype(int), 0, j['vertices'] - 1)
nv, fr = j['vertices'], j['frames']
vat = np.fromfile(f'game/assets/vat/{m}_lod0.vat', np.float32).reshape(fr, nv, 3)
f0 = int(j['clips'][clip]['start']); P = vat[f0, vid]
near = vid < j.get('near_verts', nv)
sk = near & (slot == 16) & (P[:, 1] < 1.35)   # skin below the neck = hands
for nm, sel in (('hr', sk & (P[:, 0] > 0)), ('hl', sk & (P[:, 0] < 0))):
    c = P[sel].mean(0); print(f'--{nm}={c[0]:.3f},{c[1]:.3f},{c[2]:.3f}', end=' ')
print()
