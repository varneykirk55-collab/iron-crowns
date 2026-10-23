"""Build the overworld terrain-rendering textures (graphics-map branch). Render-only: no gameplay data changes.

Inputs (data_src/, public domain / open data):
  tiles_z5/{x}_{y}.png   AWS Terrain Tiles (Terrarium encoding, zoom 5; SRTM/GMTED/ETOPO1 composite)
  NE1_50M_SR_W/          Natural Earth I land cover with shaded relief (colour source)
  SR_50M/                Natural Earth shaded relief only (used to remove the baked hillshade)
  game/data/map/province_ids.bin  (existing province raster, read only)
Outputs (game/assets/map_terrain/):
  terrain_albedo.jpg  4096x2048 de-shaded natural land colour, colour-graded, snow/rock tinted
  terrain_normal.jpg  4096x2048 R,G = signed-sqrt encoded slope (dh/dx, dh/dz), B = cavity (valleys dark, ridges light)
  terrain_data.png    4096x2048 R = coast signed distance, G = distance to nearest province border, B = forest density,
                      A = snow cover (all smooth -> bilinear filtered in the shader)
  terrain_nbr.png     4096x2048 R,G = id (lo, hi) of the province on the other side of the nearest province border
                      (texelFetch only; lets the shader classify country vs province borders with a single lookup)
  terrain_detail.png  512x512 tileable detail: R fine noise, G medium noise, B tree canopy, A field patchwork
"""
import os, math, json
import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.join(os.path.dirname(__file__), '..')
SRC = os.path.join(ROOT, 'data_src')
MAP = os.path.join(ROOT, 'game', 'data', 'map')
OUT = os.path.join(ROOT, 'game', 'assets', 'map_terrain')
os.makedirs(OUT, exist_ok=True)
W, H = 4096, 2048
HEIGHT_SCALE = 0.42      # world units per km (GameData.HEIGHT_SCALE)
TEX_U = 360.0 / W        # world units per texel
lat = 90 - (np.arange(H) + 0.5) / H * 180
ids = np.fromfile(os.path.join(MAP, 'province_ids.bin'), dtype=np.uint16).reshape(H, W)
land = ids != 0

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

# ---------------- elevation (zoom-5 Terrarium -> equirect 8192x4096 -> 2x2 mean) ----------------
print('elevation')
N = 32
merc = np.zeros((N * 256, N * 256), dtype=np.float32)
for x in range(N):
    for y in range(N):
        t = np.asarray(Image.open(os.path.join(SRC, 'tiles_z5', f'{x}_{y}.png')).convert('RGB'), dtype=np.float32)
        merc[y*256:(y+1)*256, x*256:(x+1)*256] = (t[..., 0] * 256 + t[..., 1] + t[..., 2] / 256) - 32768
W2, H2 = W * 2, H * 2
lat2 = 90 - (np.arange(H2) + 0.5) / H2 * 180
latc = np.clip(lat2, -85.0, 85.0)
my = (1 - np.log(np.tan(np.radians(latc)) + 1 / np.cos(np.radians(latc))) / math.pi) / 2 * (N * 256)
mx = (np.arange(W2) + 0.5) / W2 * (N * 256)
# bilinear sample in y (rows), exact-ish in x
y0 = np.clip(np.floor(my - 0.5).astype(int), 0, N * 256 - 2); fy = np.clip(my - 0.5 - y0, 0, 1)[:, None]
x0 = np.clip(np.floor(mx - 0.5).astype(int), 0, N * 256 - 2); fx = np.clip(mx - 0.5 - x0, 0, 1)[None, :]
e = (merc[y0][:, x0] * (1 - fx) + merc[y0][:, x0 + 1] * fx) * (1 - fy) + (merc[y0 + 1][:, x0] * (1 - fx) + merc[y0 + 1][:, x0 + 1] * fx) * fy
del merc
elev = e.reshape(H, 2, W, 2).mean(axis=(1, 3)) / 1000.0   # km
elev[lat < -85] = np.where(land[lat < -85], 2.5, -3)
land_e = np.where(land, np.maximum(elev, 0.0), 0.0)

# ---------------- normal / slope + cavity ----------------
print('normals')
hs = ndimage.gaussian_filter(land_e, 0.7) * HEIGHT_SCALE        # world units
coslat = np.cos(np.radians(np.clip(lat, -89, 89)))[:, None]
gx = (np.roll(hs, -1, 1) - np.roll(hs, 1, 1)) / (2 * TEX_U)
gz = (np.vstack([hs[1:], hs[-1:]]) - np.vstack([hs[:1], hs[:-1]])) / (2 * TEX_U)
GMAX = 4.0
def enc_signed_sqrt(g, gmax):
    return 0.5 + 0.5 * np.sign(g) * np.sqrt(np.clip(np.abs(g) / gmax, 0, 1))
cav = land_e - ndimage.gaussian_filter(land_e, 4.0)
cav = np.clip(0.5 + cav * 0.9, 0, 1)
nrm = np.stack([enc_signed_sqrt(gx, GMAX), enc_signed_sqrt(gz, GMAX), cav], -1)
nrm[~land] = [0.5, 0.5, 0.5]
Image.fromarray((nrm * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, 'terrain_normal.jpg'), quality=93)
slope = np.sqrt(gx * gx + gz * gz)

# ---------------- coast signed distance (texels) ----------------
print('coast sdf')
d_in = ndimage.distance_transform_edt(land)
d_out = ndimage.distance_transform_edt(~land)
sd = np.where(land, d_in - 0.5, -(d_out - 0.5))
CR = 24.0
coast = 0.5 + 0.5 * np.sign(sd) * np.sqrt(np.clip(np.abs(sd) / CR, 0, 1))

# ---------------- province border distance + id across the nearest border ----------------
print('province borders')
idl = ids.astype(np.int32)
B = np.zeros((H, W), bool)
other = np.zeros((H, W), np.int32)
for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
    nb = np.roll(idl, (dy, dx), (0, 1))
    if dy == 1: nb[0] = idl[0]
    if dy == -1: nb[-1] = idl[-1]
    m = land & (nb != 0) & (nb != idl)
    other = np.where(m & (other == 0), nb, other)
    B |= m
dist, ind = ndimage.distance_transform_edt(~B, return_indices=True)
nbr = other[ind[0], ind[1]]
nbr[~land] = 0
BR = 48.0
bdist = np.sqrt(np.clip((dist + 0.5) / BR, 0, 1))
bdist[~land] = 1.0
# keep the field smooth across the coast for the bilinear filter
# signed border distance for crisp close-zoom lines: the sign flips across each border (id < neighbour id), so a
# bilinear interpolation of neighbouring texels crosses zero exactly on the boundary between the two provinces.
SR = 8.0
sgn = np.where(idl < nbr, 1.0, -1.0)
sdist = sgn * np.sqrt(np.clip((dist + 0.5) / SR, 0, 1))
sb = np.where(land, 0.5 + 0.5 * sdist, 1.0)
nb_img = np.stack([(nbr & 255), (nbr >> 8), np.round(sb * 255)], -1).astype(np.uint8)
Image.fromarray(nb_img).save(os.path.join(OUT, 'terrain_nbr.png'), optimize=True)

# ---------------- colour: biome palette driven by Natural Earth I land cover ----------------
# NE1's pale cartographic palette is only used to classify land cover; the final colours come from our own
# palette. The baked hillshade is removed by dividing out high-frequency luminance before classification.
print('albedo')
ne = np.asarray(Image.open(os.path.join(SRC, 'NE1_50M_SR_W', 'NE1_50M_SR_W.tif')).convert('RGB').resize((W, H), Image.BOX)).astype(np.float32) / 255
src_ok = land & ~((ne[..., 2] > ne[..., 1] + 0.04) & (ne.mean(-1) < 0.85))
_, ii = ndimage.distance_transform_edt(~src_ok, return_indices=True)
ne = ne[ii[0], ii[1]]
lum0 = ne.mean(-1)
ratio = np.clip(lum0 / np.maximum(ndimage.gaussian_filter(lum0, 6.0), 1e-3), 0.6, 1.5)
base = np.clip(ne / ratio[..., None], 0, 1)
base = ndimage.gaussian_filter(base, (2.0, 2.0, 0))
r, g, b = base[..., 0], base[..., 1], base[..., 2]
lum = base.mean(-1)
alat = np.abs(lat)[:, None] * np.ones((1, W), np.float32)
gr = g - r                         # >0 vegetated, <0 arid
sat = base.max(-1) - base.min(-1)
yel = 0.5 * (r + g) - b               # yellowness: grassland/steppe high, tundra/ice low
w_ice = smoothstep(0.86, 0.92, lum) * smoothstep(0.0, 0.03, b - r) * np.maximum(smoothstep(38.0, 50.0, alat), smoothstep(3.0, 4.0, land_e))
w_forest = smoothstep(0.02, 0.10, gr) * (1 - w_ice)
w_desert = smoothstep(-0.005, -0.035, gr) * (1 - w_ice)
w_tundra = smoothstep(0.10, 0.04, yel) * smoothstep(45.0, 58.0, alat) * (1 - w_ice - w_forest - w_desert).clip(0, 1)
w_grass = np.clip(1 - w_desert - w_forest - w_ice - w_tundra, 0, 1)
tropic = smoothstep(28.0, 12.0, alat); boreal = smoothstep(48.0, 60.0, alat); polar = smoothstep(62.0, 72.0, alat)
def col(c): return np.array(c, np.float32)
c_forest = col([0.21, 0.31, 0.16]) * (1 - tropic[..., None]) + col([0.12, 0.29, 0.11]) * tropic[..., None]
c_forest = c_forest * (1 - boreal[..., None]) + col([0.17, 0.27, 0.16]) * boreal[..., None]
tg = smoothstep(-0.028, 0.012, gr)[..., None]
c_grass = col([0.62, 0.57, 0.36]) * (1 - tg) + col([0.40, 0.47, 0.25]) * tg
c_grass = c_grass * (1 - polar[..., None]) + col([0.50, 0.51, 0.42]) * polar[..., None]
dry = smoothstep(0.02, 0.10, -gr)[..., None]
c_desert = col([0.66, 0.58, 0.36]) * (1 - dry) + col([0.82, 0.67, 0.45]) * dry
c_ice = col([0.92, 0.94, 0.97])
c_tundra = col([0.50, 0.50, 0.40])
alb = (c_forest * w_forest[..., None] + c_grass * w_grass[..., None] + c_desert * w_desert[..., None] + c_ice * w_ice[..., None] + c_tundra * w_tundra[..., None])
# keep some of NE's large-scale tonal variation (wetlands, river valleys)
var = (lum / np.maximum(ndimage.gaussian_filter(lum, 30.0), 1e-3))[..., None]
alb = alb * np.clip(var, 0.85, 1.15)
forest = ndimage.gaussian_filter(smoothstep(0.03, 0.11, gr) * (1 - w_ice), 1.0)
forest = np.clip(forest * 1.2, 0, 1); forest[~land] = 0
glacier = w_ice
snowline = 6.0 - 5.1 * smoothstep(18.0, 66.0, alat)
prom = land_e - ndimage.gaussian_filter(land_e, 10.0)      # local prominence: peaks snow, high plateaus mostly don't
snow_e = land_e + 1.5 * np.maximum(prom, 0.0)
snow = np.maximum(glacier, smoothstep(snowline - 0.2, snowline + 0.9, snow_e) * smoothstep(0.02, 0.25, slope + 0.05))
snow = np.clip(ndimage.gaussian_filter(snow, 0.8), 0, 1); snow[~land] = 0
rock = np.clip(smoothstep(0.5, 1.6, slope) * 0.55 + smoothstep(2.0, 4.0, land_e) * 0.45, 0, 0.8) * (1 - snow)
rockc = col([0.45, 0.42, 0.38])
alb = alb * (1 - rock[..., None]) + rockc * rock[..., None]
alb = alb * (1 - snow[..., None]) + c_ice * snow[..., None]
alb = np.clip(alb, 0, 1)
Image.fromarray((alb * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, 'terrain_albedo.jpg'), quality=92)

data = np.stack([coast, bdist, forest, snow], -1)
Image.fromarray((np.clip(data, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'terrain_data.png'), optimize=True)

# ---------------- tileable detail texture ----------------
print('detail')
rng = np.random.default_rng(7)
S = 512
def tile_noise(scale, octaves=4, seed=0):
    r = np.random.default_rng(seed)
    acc = np.zeros((S, S), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        n = scale * 2 ** o
        g = r.random((n, n)).astype(np.float32)
        up = np.asarray(Image.fromarray(np.tile(g, (3, 3))).resize((S * 3, S * 3), Image.BICUBIC))[S:2*S, S:2*S]
        acc += up * amp; tot += amp; amp *= 0.5
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())
fine = tile_noise(32, 3, 1)
med = tile_noise(6, 4, 2)
# canopy: many soft blobs (tileable via wrap)
can = np.zeros((S, S), np.float32)
yy, xx = np.mgrid[0:S, 0:S]
pts = rng.random((900, 2)) * S
rad = rng.uniform(5, 10, 900)
for (px, py), rr in zip(pts, rad):
    dx = (xx - px + S / 2) % S - S / 2; dy = (yy - py + S / 2) % S - S / 2
    can = np.maximum(can, np.clip(1 - (dx * dx + dy * dy) / (rr * rr), 0, 1) ** 0.6 * rng.uniform(0.7, 1.0))
# field patchwork: tileable voronoi cells with per-cell tone
cells = rng.random((60, 2)) * S
best = np.full((S, S), 1e9); cid = np.zeros((S, S), int)
for i, (px, py) in enumerate(cells):
    dx = (xx - px + S / 2) % S - S / 2; dy = (yy - py + S / 2) % S - S / 2
    d = dx * dx + dy * dy
    m = d < best; best[m] = d[m]; cid[m] = i
tone = rng.random(60)
fields = tone[cid]
edge = ndimage.maximum_filter(cid, 3) != ndimage.minimum_filter(cid, 3)
fields = np.where(edge, 0.25, fields)
det = np.stack([fine, med, can, fields], -1)
Image.fromarray((det * 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'terrain_detail.png'))
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
