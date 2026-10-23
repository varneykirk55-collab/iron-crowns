#!/usr/bin/env python3
"""Compose the proto v2 compare sheets from tests/proto_shots.tscn output (out/proto/engine):
  compare_sheet.png  : columns = v0.2.1 blocky c19_line | c19sr_line (v0.4 semi-real) | c19v2_line (proto), rows = views
  distance_sheet.png : the gameplay-distance block shots, each block captioned via labels.json (screen x of each model)
usage: python3 tools/proto_sheet.py [engine_dir] [out_dir]"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

src = sys.argv[1] if len(sys.argv) > 1 else 'out/proto/engine'
dst = sys.argv[2] if len(sys.argv) > 2 else 'out/proto'
COLS = [('c19_line', 'v0.2.1 blocky (c19_line)'), ('c19sr_line', 'v0.4 c19sr_line'), ('c19v2_line', 'PROTO v2 (c19v2_line)')]
ROWS = [('front', 'FRONT'), ('34', '3/4'), ('side', 'SIDE'), ('back', 'REAR'), ('bust', 'BUST'), ('bust_l', 'BUST (L)')]
NICK = {'c19_line': 'v0.2.1 blocky', 'c19sr_line': 'c19sr', 'c19v2_line': 'PROTO v2'}

def font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def cell(path, bust):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    if bust: im = im.crop((int(w * 0.30), int(h * 0.0), int(w * 0.70), int(h * 0.80)))
    else: im = im.crop((int(w * 0.33), 0, int(w * 0.67), h))
    return im.resize((360, int(360 * im.size[1] / im.size[0])), Image.LANCZOS)

def compare():
    F, f2 = font(26), font(20)
    cells = [[cell(os.path.join(src, f'{m}_{v}.png'), v.startswith('bust')) for m, _ in COLS] for v, _ in ROWS]
    lw, th = 130, 60
    W = lw + 360 * len(COLS); H = th + sum(r[0].size[1] for r in cells)
    S = Image.new('RGB', (W, H), (236, 232, 222)); d = ImageDraw.Draw(S)
    d.text((10, 16), 'FRA 1800', font=f2, fill=(30, 30, 30))
    for j, (_, t) in enumerate(COLS):
        d.text((lw + 360 * j + 12, 16), t, font=f2, fill=(160, 20, 20) if j == 2 else (30, 30, 30))
    y = th
    for i, (_, t) in enumerate(ROWS):
        rh = cells[i][0].size[1]
        d.text((10, y + rh // 2 - 13), t, font=F, fill=(30, 30, 30))
        for j in range(len(COLS)): S.paste(cells[i][j], (lw + 360 * j, y))
        d.line([(lw, y), (W, y)], fill=(120, 120, 120), width=2); y += rh
    for j in range(len(COLS) + 1): d.line([(lw + 360 * j, th), (lw + 360 * j, H)], fill=(120, 120, 120), width=2)
    S.save(os.path.join(dst, 'compare_sheet.png')); return S.size

def distance():
    lab = json.load(open(os.path.join(src, 'labels.json')))
    f2 = font(22); out = []
    for k in sorted([k for k in lab if k.startswith('game_')], key=lambda s: int(s[5:-1])):
        im = Image.open(os.path.join(src, k + '.png')).convert('RGB').resize((1200, 675), Image.LANCZOS); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 1200, 36], fill=(0, 0, 0)); d.text((10, 6), f'gameplay distance {k[5:]}  (3x6 blocks, FRA, q2)', font=f2, fill=(255, 255, 255))
        for m, x in lab[k].items():
            t = NICK[m]; tw = d.textlength(t, font=f2); cx = x * 1200
            d.rectangle([cx - tw / 2 - 6, 630, cx + tw / 2 + 6, 662], fill=(160, 20, 20) if m == 'c19v2_line' else (40, 40, 40))
            d.text((cx - tw / 2, 634), t, font=f2, fill=(255, 255, 255))
        out.append(im)
    S = Image.new('RGB', (2400, 675 * ((len(out) + 1) // 2)), (0, 0, 0))
    for i, im in enumerate(out): S.paste(im, ((i % 2) * 1200, (i // 2) * 675))
    S.save(os.path.join(dst, 'distance_sheet.png')); return S.size

if __name__ == '__main__':
    print('compare', compare()); print('distance', distance())
