"""Build the strategic world map data from Natural Earth (public domain) + AWS Terrarium elevation tiles.
Outputs into game/data/map:
  province_ids.bin  uint16 W*H, equirectangular, 0 = water, 65535 = wasteland (Antarctica)
  seazone_ids.bin   uint16 SW*SH coarse sea zones (0 = land/unnavigable)
  heights.bin       float16 HW*HH elevation in km (negative = ocean depth)
  albedo.png        land colour map (from Natural Earth I shaded relief)
  provinces.json, countries.json, seazones.json
"""
import json, math, os, sys, collections
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.cluster.vq import kmeans2

Image.MAX_IMAGE_PIXELS = None
SRC = os.path.join(os.path.dirname(__file__), '..', 'data_src')
OUT = os.path.join(os.path.dirname(__file__), '..', 'game', 'data', 'map')
W, H = 4096, 2048           # province raster
HW, HH = 2048, 1024         # height raster
SW, SH = 1024, 512          # sea zone raster
rng = np.random.default_rng(1234)

SOV = {'US1':'USA','GB1':'GBR','FR1':'FRA','DN1':'DNK','NL1':'NLD','CH1':'CHN','FI1':'FIN','IS1':'ISR',
       'KA1':'KAZ','CU1':'CUB','AU1':'AUS','NZ1':'NZL','CYN':'CYP','SOL':'SOM','KOS':'SRB','SAH':'MAR','KAS':'IND','PSX':'ISR'}
ADMIN1_COUNTRIES = {'United States of America':'USA','Canada':'CAN','Australia':'AUS','Brazil':'BRA','India':'IND','China':'CHN'}
# province-count overrides for detail on playable / major nations
PROV_OVERRIDE = {'SWE':8,'JPN':9,'NOR':5,'FIN':5,'DNK':2,'RUS':26,'MEX':9,'GBR':5,'FRA':7,'DEU':6,'ESP':6,'ITA':5,
                 'KOR':3,'PRK':3,'POL':4,'UKR':5,'TUR':6,'IRN':6,'MNG':5,'KAZ':7,'ARG':8,'EGY':4,'ZAF':5,'IDN':12,
                 'PHL':4,'TWN':1,'CUB':2,'GRL':4,'NZL':2,'SAU':5,'DZA':5,'LBY':4,'COD':6,'SDN':4,'PER':4,'COL':4}

def lonlat_to_px(lon, lat, w, h):
    return ((lon + 180.0) / 360.0 * w, (90.0 - lat) / 180.0 * h)

def rings_of(geom):
    if geom['type'] == 'Polygon':
        return [geom['coordinates']]
    return geom['coordinates']

def draw_feature(img_draw, geom, value, w, h, holes_value=None):
    for poly in rings_of(geom):
        ext = [lonlat_to_px(x, y, w, h) for x, y, *_ in poly[0]]
        if len(ext) >= 3:
            img_draw.polygon(ext, fill=value)
        if holes_value is not None:
            for hole in poly[1:]:
                pts = [lonlat_to_px(x, y, w, h) for x, y, *_ in hole]
                if len(pts) >= 3:
                    img_draw.polygon(pts, fill=holes_value)

def poly_area(geom):
    a = 0
    for poly in rings_of(geom):
        r = poly[0]
        s = 0
        for i in range(len(r) - 1):
            s += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]
        a += abs(s) / 2
    return a

print('loading geojson')
countries = json.load(open(os.path.join(SRC, 'ne_50m_admin_0_countries.geojson')))['features']
admin1 = json.load(open(os.path.join(SRC, 'ne_50m_admin_1_states_provinces.geojson')))['features']
places = json.load(open(os.path.join(SRC, 'ne_50m_populated_places_simple.geojson')))['features']

# ---------------- country raster ----------------
feat_info = []
for f in countries:
    p = f['properties']
    code = p['ADM0_A3']
    owner = SOV.get(p['SOV_A3'], code)
    if code == 'ATA':
        owner = 'ATA'
    feat_info.append(dict(code=code, owner=owner, name=p['NAME'], continent=p['CONTINENT'], pop=p['POP_EST'] or 0,
                          gdp=p['GDP_MD'] or 0, geom=f['geometry'], area=poly_area(f['geometry']), admin=p['ADMIN']))
feat_info.sort(key=lambda d: -d['area'])
img = Image.new('I', (W, H), 0)
dr = ImageDraw.Draw(img)
for i, fi in enumerate(feat_info):
    draw_feature(dr, fi['geom'], i + 1, W, H, holes_value=0)
craster = np.array(img, dtype=np.int32)  # feature index + 1
print('countries rasterized', np.count_nonzero(craster))

# ---------------- admin-1 raster ----------------
a1img = Image.new('I', (W, H), 0)
a1dr = ImageDraw.Draw(a1img)
a1list = []
for f in admin1:
    p = f['properties']
    if p['admin'] in ADMIN1_COUNTRIES:
        a1list.append(dict(name=p['name'], country=ADMIN1_COUNTRIES[p['admin']], geom=f['geometry'], area=poly_area(f['geometry'])))
a1list.sort(key=lambda d: -d['area'])
for i, a in enumerate(a1list):
    draw_feature(a1dr, a['geom'], i + 1, W, H)
a1raster = np.array(a1img, dtype=np.int32)

# ---------------- elevation ----------------
print('elevation')
merc = np.zeros((4096, 4096), dtype=np.float32)
for x in range(16):
    for y in range(16):
        t = np.asarray(Image.open(os.path.join(SRC, 'tiles', f'{x}_{y}.png')).convert('RGB'), dtype=np.float32)
        merc[y*256:(y+1)*256, x*256:(x+1)*256] = (t[..., 0] * 256 + t[..., 1] + t[..., 2] / 256) - 32768
lat = 90 - (np.arange(HH) + 0.5) / HH * 180
latc = np.clip(lat, -85.0, 85.0)
my = (1 - np.log(np.tan(np.radians(latc)) + 1 / np.cos(np.radians(latc))) / math.pi) / 2 * 4096
my = np.clip(my.astype(int), 0, 4095)
mx = np.clip(((np.arange(HW) + 0.5) / HW * 4096).astype(int), 0, 4095)
elev = merc[my[:, None], mx[None, :]] / 1000.0  # km
# land mask at height res from country raster
land_hr = np.array(Image.fromarray((craster > 0).astype(np.uint8) * 255).resize((HW, HH), Image.BILINEAR)) > 127
elev = np.where(land_hr, np.maximum(elev, 0.02), np.minimum(elev, -0.05))
elev = ndimage.gaussian_filter(elev, 0.6)
elev = np.where(land_hr, np.maximum(elev, 0.01), np.minimum(elev, -0.03))
elev[lat < -85] = np.where(land_hr[lat < -85], 2.5, -3)
elev.astype(np.float16).tofile(os.path.join(OUT, 'heights.bin'))
elev_full = np.array(Image.fromarray(elev.astype(np.float32)).resize((W, H), Image.BILINEAR))

# ---------------- albedo ----------------
print('albedo')
ne = Image.open(os.path.join(SRC, 'NE1_50M_SR_W', 'NE1_50M_SR_W.tif')).convert('RGB').resize((W, H), Image.LANCZOS)
alb = np.asarray(ne).copy()
alb.astype(np.uint8)
Image.fromarray(alb).save(os.path.join(OUT, 'albedo.jpg'), quality=92)
albf = alb.astype(np.float32) / 255

# ---------------- provinces ----------------
print('provinces')
prov_raster = np.zeros((H, W), dtype=np.int32)
provinces = []
yy, xx = np.mgrid[0:H, 0:W]
lat_full = 90 - (np.arange(H) + 0.5) / H * 180
coslat = np.cos(np.radians(lat_full))

owners = collections.OrderedDict()
for i, fi in enumerate(feat_info):
    owners.setdefault(fi['owner'], []).append(i + 1)

def add_province(mask, owner, region, name_hint):
    pid = len(provinces) + 1
    prov_raster[mask] = pid
    provinces.append(dict(id=pid, owner=owner, region=region, name_hint=name_hint, mx=None))
    return pid

for owner, fidx in owners.items():
    for fid in fidx:
        fi = feat_info[fid - 1]
        mask = craster == fid
        n_px = int(mask.sum())
        if n_px < 6:
            continue
        if owner == 'ATA':
            prov_raster[mask] = 65535
            continue
        if fi['code'] in ADMIN1_COUNTRIES.values():
            ids = a1raster * mask
            own_ids = np.array([0] + [1 if a['country'] == fi['code'] else 0 for a in a1list], dtype=np.int32)
            ids = ids * own_ids[ids]
            # fill uncovered pixels of the country with nearest admin1
            cover = ids > 0
            if cover.any():
                _, inds = ndimage.distance_transform_edt(~cover, return_indices=True)
                filled = ids[inds[0], inds[1]]
                filled[~mask] = 0
                # merge tiny admin1 regions
                counts = collections.Counter(filled[mask].tolist())
                # iterate merges
                changed = True
                while changed:
                    changed = False
                    counts = collections.Counter(filled[mask].tolist())
                    for aid, cnt in sorted(counts.items(), key=lambda t: t[1]):
                        if cnt < 70 and len(counts) > 1:
                            m = filled == aid
                            dil = ndimage.binary_dilation(m, iterations=2) & mask & ~m
                            nb = collections.Counter(filled[dil].tolist())
                            nb.pop(0, None)
                            if nb:
                                tgt = nb.most_common(1)[0][0]
                                filled[m] = tgt
                                changed = True
                                break
                for aid in sorted(set(filled[mask].tolist())):
                    add_province(filled == aid, owner, fi['name'], a1list[aid - 1]['name'])
                continue
        # Voronoi split
        n = PROV_OVERRIDE.get(fi['code'], int(np.clip(round(n_px / 2200), 1, 10)))
        if n_px < 400 and fi['code'] not in PROV_OVERRIDE:
            n = 1
        ys, xs = np.nonzero(mask)
        if n <= 1:
            add_province(mask, owner, fi['name'], None)
            continue
        pts = np.stack([xs * float(np.cos(np.radians(90 - (ys.mean() + 0.5) / H * 180))), ys], axis=1).astype(np.float64)
        sample = pts[rng.choice(len(pts), size=min(len(pts), 20000), replace=False)]
        cent, _ = kmeans2(sample, n, seed=7, minit='++')
        d = ((pts[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for k in range(n):
            sel = lab == k
            if sel.sum() == 0:
                continue
            m = np.zeros_like(mask)
            m[ys[sel], xs[sel]] = True
            add_province(m, owner, fi['name'], None)

N = len(provinces)
print('province count', N)

# drop provinces that ended too small (<5px): merge into neighbour with same owner if any, else keep
# ---------------- province stats ----------------
flat = prov_raster.ravel()
valid = (flat > 0) & (flat < 65535)
counts = np.bincount(flat[valid], minlength=N + 1)
sx = np.bincount(flat[valid], weights=xx.ravel()[valid], minlength=N + 1)
sy = np.bincount(flat[valid], weights=yy.ravel()[valid], minlength=N + 1)
sel_e = elev_full.ravel()[valid]
se = np.bincount(flat[valid], weights=sel_e, minlength=N + 1)
se2 = np.bincount(flat[valid], weights=sel_e ** 2, minlength=N + 1)
alb_r = np.bincount(flat[valid], weights=albf[..., 0].ravel()[valid], minlength=N + 1)
alb_g = np.bincount(flat[valid], weights=albf[..., 1].ravel()[valid], minlength=N + 1)
alb_b = np.bincount(flat[valid], weights=albf[..., 2].ravel()[valid], minlength=N + 1)

# adjacency (with horizontal wrap)
def pairs(a, b):
    m = (a != b) & (a > 0) & (b > 0) & (a < 65535) & (b < 65535)
    return np.stack([a[m], b[m]], 1)
pr = prov_raster
P = np.concatenate([pairs(pr[:, :-1], pr[:, 1:]), pairs(pr[:-1, :], pr[1:, :]), pairs(pr[:, -1], pr[:, 0]),
                    pairs(pr[:-1, :-1], pr[1:, 1:]), pairs(pr[:-1, 1:], pr[1:, :-1])])
P = np.sort(P, 1)
edge_counts = collections.Counter(map(tuple, P.tolist()))
adj = collections.defaultdict(dict)
for (a, b), c in edge_counts.items():
    adj[a][b] = c
    adj[b][a] = c

# coastal
water = pr == 0
coast_mask = ndimage.binary_dilation(water, iterations=1) & (pr > 0) & (pr < 65535)
coast_ids = set(np.unique(pr[coast_mask]).tolist())

# ---------------- sea zones ----------------
print('sea zones')
water_c = np.array(Image.fromarray(water.astype(np.uint8) * 255).resize((SW, SH), Image.NEAREST)) > 127
lat_c = 90 - (np.arange(SH) + 0.5) / SH * 180
water_c[(lat_c < -66) | (lat_c > 82), :] = False  # polar ice not navigable
labels = np.zeros((SH, SW), dtype=np.int32)
seeds = []
step = 26  # ~9 degrees
for y in range(step // 2, SH, step):
    latv = lat_c[y]
    xstep = int(step / max(0.35, math.cos(math.radians(latv))))
    for x in range(xstep // 2, SW, xstep):
        if water_c[y, x]:
            seeds.append((y, x))
# also seed every water component that got no seed and is big enough
comp, ncomp = ndimage.label(water_c)
seeded = set(comp[y, x] for y, x in seeds)
for c in range(1, ncomp + 1):
    if c not in seeded:
        ys, xs = np.nonzero(comp == c)
        if len(ys) > 40:
            seeds.append((ys[len(ys)//2], xs[len(xs)//2]))
for i, (y, x) in enumerate(seeds):
    labels[y, x] = i + 1
# geodesic growth with wrap
for it in range(2000):
    un = (labels == 0) & water_c
    if not un.any():
        break
    grew = False
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        sh = np.roll(labels, (dy, dx), axis=(0, 1))
        if dy == 1: sh[0, :] = 0
        if dy == -1: sh[-1, :] = 0
        m = un & (sh > 0) & (labels == 0)
        if m.any():
            labels[m] = sh[m]
            grew = True
    if not grew:
        break
# remove tiny zones (merge into neighbours)
zc = np.bincount(labels.ravel(), minlength=len(seeds) + 1)
# renumber
used = [z for z in range(1, len(seeds) + 1) if zc[z] > 0]
remap = np.zeros(len(seeds) + 1, dtype=np.int32)
for i, z in enumerate(used):
    remap[z] = i + 1
labels = remap[labels]
NZ = len(used)
print('sea zones', NZ)
zP = np.concatenate([pairs(labels[:, :-1], labels[:, 1:]), pairs(labels[:-1, :], labels[1:, :]), pairs(labels[:, -1], labels[:, 0])])
zP = np.sort(zP, 1)
zadj = collections.defaultdict(set)
for a, b in set(map(tuple, zP.tolist())):
    zadj[a].add(b); zadj[b].add(a)
labels.astype(np.uint16).tofile(os.path.join(OUT, 'seazone_ids.bin'))
# zone stats
zys, zxs = np.nonzero(labels)
zl = labels[zys, zxs]
zcnt = np.bincount(zl, minlength=NZ + 1)
zsx = np.bincount(zl, weights=zxs, minlength=NZ + 1)
zsy = np.bincount(zl, weights=zys, minlength=NZ + 1)
# coastal sea zones: touch land
land_c = ~water_c
land_near = ndimage.binary_dilation(land_c, iterations=2)
coastal_zone = set(np.unique(labels[land_near & (labels > 0)]).tolist())
# province <-> zone links: land province pixels at full res next to water; map to coarse
prov_zone = collections.defaultdict(set)
cy, cx = np.nonzero(coast_mask)
for dy in (-4, 0, 4):
    for dx in (-4, 0, 4):
        ty = np.clip((cy + dy) * SH // H, 0, SH - 1)
        tx = ((cx + dx) * SW // W) % SW
        z = labels[ty, tx]
        ok = z > 0
        for p, zz in set(zip(pr[cy[ok], cx[ok]].tolist(), z[ok].tolist())):
            prov_zone[p].add(zz)

# ---------------- names from populated places ----------------
place_list = []
for f in places:
    q = f['properties']
    place_list.append((q['longitude'], q['latitude'], q['name'], q['pop_max'] or 0, q['adm0cap'], q.get('adm0_a3')))
prov_places = collections.defaultdict(list)
for lon, la, name, pop, cap, a3 in place_list:
    px, py = lonlat_to_px(lon, la, W, H)
    ix, iy = int(px) % W, min(int(py), H - 1)
    pid = pr[iy, ix]
    if pid == 0 or pid == 65535:
        # nearest land within 3 px
        win = pr[max(0, iy-3):iy+4, max(0, ix-3):ix+4]
        cand = win[(win > 0) & (win < 65535)]
        if len(cand) == 0:
            continue
        pid = collections.Counter(cand.tolist()).most_common(1)[0][0]
    prov_places[pid].append((pop, name, cap, lon, la))

def compass(dx, dy):
    ang = math.degrees(math.atan2(-dy, dx)) % 360
    names = ['Eastern', 'Northeastern', 'Northern', 'Northwestern', 'Western', 'Southwestern', 'Southern', 'Southeastern']
    return names[int(((ang + 22.5) % 360) // 45)]

RES_TABLE = {'mountains': ['iron', 'gold', 'iron', 'coal', 'horses'], 'hills': ['iron', 'coal', 'timber', 'grain', 'horses'],
             'plains': ['grain', 'grain', 'horses', 'timber', 'oil'], 'desert': ['oil', 'oil', 'gold', 'horses', 'iron'],
             'forest': ['timber', 'timber', 'iron', 'grain', 'coal'], 'tundra': ['timber', 'oil', 'fish', 'iron', 'gold'],
             'jungle': ['timber', 'grain', 'gold', 'oil', 'timber']}

# country-level stats
country_feat = {fi['owner']: fi for fi in reversed(feat_info) if fi['owner'] == fi['code']}
for fi in feat_info:
    country_feat.setdefault(fi['owner'], fi)
owner_pop = collections.defaultdict(float)
for fi in feat_info:
    owner_pop[fi['owner']] += fi['pop']

out_prov = []
used_names = set()
owner_prov = collections.defaultdict(list)
for pv in provinces:
    pid = pv['id']
    c = counts[pid]
    if c == 0:
        pv['dead'] = True
        continue
    owner_prov[pv['owner']].append(pid)
owner_area = {o: sum(counts[p] for p in ps) for o, ps in owner_prov.items()}

for pv in provinces:
    if pv.get('dead'):
        continue
    pid = pv['id']
    c = counts[pid]
    mx_, my_ = sx[pid] / c, sy[pid] / c
    # label point: province pixel closest to mean
    ys, xs = np.nonzero(pr[max(0, int(my_) - 60):int(my_) + 61, max(0, int(mx_) - 60):int(mx_) + 61] == pid)
    if len(ys):
        oy, ox = max(0, int(my_) - 60), max(0, int(mx_) - 60)
        k = ((ys + oy - my_) ** 2 + (xs + ox - mx_) ** 2).argmin()
        lx, ly = xs[k] + ox, ys[k] + oy
    else:
        ys, xs = np.nonzero(pr == pid)
        lx, ly = xs[0], ys[0]
    lon = (lx + 0.5) / W * 360 - 180
    la = 90 - (ly + 0.5) / H * 180
    em = se[pid] / c
    estd = math.sqrt(max(0, se2[pid] / c - em * em))
    r, g, b = alb_r[pid] / c, alb_g[pid] / c, alb_b[pid] / c
    if em > 1.6 or estd > 0.55:
        relief = 'mountains'
    elif em > 0.6 or estd > 0.22:
        relief = 'hills'
    else:
        relief = 'flat'
    bright = (r + g + b) / 3
    if abs(la) > 62 or (bright > 0.75 and abs(la) > 50):
        biome = 'tundra'
    elif r > g * 1.08 and bright > 0.45:
        biome = 'desert'
    elif abs(la) < 18 and g > r * 1.02:
        biome = 'jungle'
    elif g > r * 1.0 and bright < 0.42:
        biome = 'forest'
    else:
        biome = 'plains'
    terrain = relief if relief != 'flat' else biome
    if terrain == 'plains' and biome != 'plains':
        terrain = biome
    pl = sorted(prov_places.get(pid, []), reverse=True)
    name = pv['name_hint']
    if not name:
        if pl:
            name = pl[0][1]
        else:
            same = [q['id'] for q in provinces if not q.get('dead') and q['region'] == pv['region'] and q['owner'] == pv['owner']]
            if len(same) > 1:
                cxp = np.mean([sx[p] / counts[p] for p in same])
                cyp = np.mean([sy[p] / counts[p] for p in same])
                name = compass(mx_ - cxp, my_ - cyp) + ' ' + pv['region']
            else:
                name = pv['region']
    base = name
    k = 2
    while name in used_names:
        name = f'{base} {"II III IV V VI VII VIII".split()[min(k-2, 6)]}'
        k += 1
    used_names.add(name)
    is_cap = any(p[2] == 1 for p in pl)
    city_pop = sum(p[0] for p in pl)
    area_share = c / owner_area[pv['owner']]
    h = (pid * 2654435761) % 2**32
    res = RES_TABLE[terrain if terrain in RES_TABLE else 'plains'][h % 5]
    if pid in coast_ids and h % 3 == 0 and res in ('grain', 'timber'):
        res = 'fish'
    city = None
    if pl:
        city = [round(pl[0][3], 3), round(pl[0][4], 3), pl[0][1]]
    out_prov.append(dict(id=pid, name=name, owner=pv['owner'], region=pv['region'], lon=round(lon, 3), lat=round(la, 3),
                         area=int(c), terrain=terrain, elev=round(em, 3), resource=res, coastal=pid in coast_ids,
                         capital_city=is_cap, city=city, city_pop=int(city_pop), area_share=round(area_share, 5),
                         neighbors={str(k2): int(v) for k2, v in adj[pid].items()},
                         seazones=sorted(prov_zone.get(pid, [])) if pid in coast_ids else []))

# population: share of national population by area and cities
by_owner = collections.defaultdict(list)
for p in out_prov:
    by_owner[p['owner']].append(p)
for o, ps in by_owner.items():
    tot_city = sum(p['city_pop'] for p in ps) or 1
    pop = owner_pop[o] or 100000
    for p in ps:
        p['population'] = int(pop * (0.45 * p['area_share'] + 0.55 * p['city_pop'] / tot_city))
    if not any(p['capital_city'] for p in ps):
        max(ps, key=lambda p: p['population'])['capital_city'] = True
    else:
        caps = [p for p in ps if p['capital_city']]
        for p in caps[1:]:
            p['capital_city'] = False

out_countries = []
for o, ps in by_owner.items():
    fi = country_feat[o]
    out_countries.append(dict(code=o, name=fi['name'] if fi['owner'] == fi['code'] else fi['admin'], continent=fi['continent'],
                              population=int(owner_pop[o]), gdp_md=int(sum(f['gdp'] for f in feat_info if f['owner'] == o)),
                              provinces=[p['id'] for p in ps], capital=[p['id'] for p in ps if p['capital_city']][0]))

# reindex: keep raster ids (dead ids just unused)
prov_raster.astype(np.uint16).tofile(os.path.join(OUT, 'province_ids.bin'))
seaz = []
for z in range(1, NZ + 1):
    if zcnt[z] == 0:
        continue
    seaz.append(dict(id=z, lon=round((zsx[z] / zcnt[z] + 0.5) / SW * 360 - 180, 2), lat=round(90 - (zsy[z] / zcnt[z] + 0.5) / SH * 180, 2),
                     coastal=z in coastal_zone, neighbors=sorted(zadj[z]), size=int(zcnt[z])))
json.dump(dict(width=W, height=H, provinces=out_prov), open(os.path.join(OUT, 'provinces.json'), 'w'), separators=(',', ':'))
json.dump(out_countries, open(os.path.join(OUT, 'countries.json'), 'w'), indent=0)
json.dump(dict(width=SW, height=SH, zones=seaz), open(os.path.join(OUT, 'seazones.json'), 'w'), separators=(',', ':'))
meta = dict(province_raster=[W, H], height_raster=[HW, HH], sea_raster=[SW, SH], provinces=len(out_prov), countries=len(out_countries), seazones=len(seaz))
json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
print(meta)
for code in ('USA', 'SWE', 'JPN'):
    ps = by_owner[code]
    print(code, len(ps), [p['name'] for p in ps][:60])
