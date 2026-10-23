"""Nation uniform line-up: parses CHAR_PALETTE / NATION_UNIFORM from game/scripts/battle/battle_visuals.gd, resolves them
exactly like BattleVisuals._nation_palette (incl. the "facing" fan-out and the map-colour fallback for unlisted codes) and
renders every nation's line infantryman (3/4 view).
  blender -b --python pipeline/blender/char_nations.py -- [kit] [out.png]      (labels: python3 char_nations.py --label)"""
import sys, os, re, json, colorsys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GD = os.path.join(ROOT, 'game/scripts/battle/battle_visuals.gd')
NATIONS = os.path.join(ROOT, 'game/data/nations.json')
FAN = ['collar', 'cuff', 'turnback', 'epaulette', 'sash', 'piping']
NCOL = 12

def _dict_block(src, name):
    a = src.index(f'const {name} := {{')
    depth = 0
    for i in range(a, len(src)):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0: return src[src.index('{', a):i + 1]

def load_uniforms():
    src = open(GD).read()
    base = dict(re.findall(r'"(\w+)":\s*"([0-9a-f]{6})"', _dict_block(src, 'CHAR_PALETTE')))
    nu = {}
    for code, body in re.findall(r'"([A-Z]{3})":\s*\{([^}]*)\}', _dict_block(src, 'NATION_UNIFORM')):
        nu[code] = dict(re.findall(r'"(\w+)":\s*"([0-9a-f]{6})"', body))
    return base, nu

def h2c(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
def c2h(c): return ''.join('%02x' % max(0, min(255, round(x * 255))) for x in c)

def resolve(code, map_hex, base, nu):
    p = dict(base)
    if code in nu:
        u = nu[code]
    else:   # same derivation as _nation_palette's fallback
        r, g, b = h2c(map_hex.lstrip('#')); h, s, v = colorsys.rgb_to_hsv(r, g, b)
        coat = colorsys.hsv_to_rgb(h, min(s, 0.75), min(max(v * 0.62, 0.12), 0.6))
        if s < 0.15: coat = (0.88, 0.86, 0.8) if v > 0.7 else (0.25, 0.26, 0.28)
        lum = 0.2126 * coat[0] + 0.7152 * coat[1] + 0.0722 * coat[2]
        u = {'coat': c2h(coat), 'lapel': c2h(coat), 'facing': 'e9e6dc' if lum < 0.35 else '8a2222', 'plume': map_hex.lstrip('#')}
    for k, x in u.items():
        if k == 'facing':
            for f in FAN:
                if f not in u: p[f] = x
        else:
            p[k] = x
    return p

def nation_list():
    d = json.load(open(NATIONS))
    return [(m['code'], m['color']) for m in d['majors']] + [('minor:XXA', '#8a5ab0'), ('minor:XXB', '#e0e060'), ('minor:XXC', '#909090')]

if __name__ == '__main__' and '--label' in sys.argv:
    from PIL import Image, ImageDraw, ImageFont
    out = sys.argv[sys.argv.index('--label') + 1]
    im = Image.open(out).convert('RGB'); W, H = im.size
    nl = nation_list(); rows = (len(nl) + NCOL - 1) // NCOL
    S = Image.new('RGB', (W, H + 50), (30, 30, 32)); S.paste(im, (0, 50)); d = ImageDraw.Draw(S)
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    d.text((12, 12), 'Nation uniforms (NATION_UNIFORM, 47 majors + 3 derived minors) - c19sr_' + os.path.basename(out)[8:-4], fill=(235, 235, 235), font=f)
    cw = W / NCOL; rh = H / rows
    for i, (c, _) in enumerate(nl):
        x = (i % NCOL) * cw; y = 50 + (i // NCOL + 1) * rh - 34
        d.rectangle([x + 4, y, x + cw - 4, y + 28], fill=(20, 20, 22)); d.text((x + 10, y + 2), c.replace('minor:', '~'), fill=(240, 240, 240), font=f)
    S.save(out); print('labelled', out)
    sys.exit(0)

if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import bpy, math
    import char_build as CB, char_body as B, char_anim as A, common
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    kid = argv[0] if argv else 'c19sr_line'
    out = argv[1] if len(argv) > 1 else f'{CB.OUT}/nations/nations_{kid.replace("c19sr_", "")}.png'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    base, nu = load_uniforms()
    nl = nation_list()
    common.reset_scene()
    cm = B.build(kid, 0)
    idle = A.solve(dict((c[0], c) for c in A.CLIPS)['idle'][3](0.0, 'rammer' if 'artillery' in kid else 'musket'))
    orig = dict(B.PALETTE)
    pals = {}
    for i, (code, mc) in enumerate(nl):
        p = resolve(code.split(':')[-1], mc, base, nu); pals[code] = p
        for k in B.PALETTE: B.PALETTE[k] = '#' + p.get(k, orig[k].lstrip('#'))
        rig = CB.build_rig(f'n{i}')
        o = CB.to_object(cm, preview=True); CB.bind(o, rig); CB.set_preview_color(o); CB.apply(rig, idle)
        rig.location = ((i % NCOL) * 1.0, 0, -(i // NCOL) * 2.3)
        rig.rotation_euler = (0, 0, math.radians(180 + 30))
    B.PALETTE.clear(); B.PALETTE.update(orig)
    rows = (len(nl) + NCOL - 1) // NCOL
    W = NCOL * 1.0
    cam = CB.setup_cam(out, (int(W * 150), int(rows * 2.3 * 150)))
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = W
    cx = (W - 1.0) / 2; cz = 1.05 - (rows - 1) * 2.3 / 2
    CB.look_at(cam, (cx, -20, cz), (cx, 0, cz))
    bpy.ops.render.render(write_still=True)
    json.dump(pals, open(out.replace('.png', '.json'), 'w'), indent=0)
    print('wrote', out, len(nl))
