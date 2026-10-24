#!/usr/bin/env python3
"""before / after close-up sheet: rows bust R, bust L, right hand, left hand; columns before | after (out/proto/beforeafter)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1] if len(sys.argv) > 1 else 'out/proto/beforeafter'
tag_b = sys.argv[2] if len(sys.argv) > 2 else '_before'; tag_a = sys.argv[3] if len(sys.argv) > 3 else '_after'
rows = ['close_bust', 'close_bust_l', 'close_hand_r', 'close_hand_l']
W, H = 640, 360; pad = 40
S = Image.new('RGB', (2 * W + 30, len(rows) * (H + 10) + pad), (28, 28, 30)); D = ImageDraw.Draw(S)
try: f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
except Exception: f = ImageFont.load_default()
for c, (t, lab) in enumerate(((tag_b, 'BEFORE (25d38b3)'), (tag_a, 'AFTER'))):
    D.text((10 + c * (W + 10), 8), lab, fill=(235, 235, 235), font=f)
    for r, n in enumerate(rows):
        p = os.path.join(d, n + t + '.png')
        if os.path.exists(p): S.paste(Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS), (10 + c * (W + 10), pad + r * (H + 10)))
S.save(os.path.join(d, 'beforeafter_sheet.png')); print(S.size)
