"""Mosaico nacional de Honduras ~150 m con un percentil bajo por píxel (quita nubes) — correr después de build_sat.py"""
import json, os, numpy as np, rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds, Window
from rasterio.transform import from_origin
import build_sat as B
def pais(bbox=(-89.40, 12.95, -83.10, 16.55), res=150, K=14, maxcc=40, per_tile=18):
    B.DT = '2024-11-01T00:00:00Z/2026-05-01T00:00:00Z'  # dos épocas secas: Honduras tiene nubosidad dispersa casi todo el año
    w, s, e, n = bbox; x0, y0 = B.merc(w, s); x1, y1 = B.merc(e, n)
    W = int((x1 - x0) / res); H = int((y1 - y0) / res); dst_t = from_origin(x0, y1, res, res)
    stack = np.zeros((K, 3, H, W), np.uint8); cnt = np.zeros((H, W), np.uint8)
    feats, ids = [], set()
    for i in range(4):  # búsqueda por franjas para no topar el límite de 200 resultados por consulta
        for j in range(2):
            sb = [w + (e - w) * i / 4, s + (n - s) * j / 2, w + (e - w) * (i + 1) / 4, s + (n - s) * (j + 1) / 2]
            for f in B.search(sb, maxcc):
                if f['id'] not in ids: ids.add(f['id']); feats.append(f)
    by = {}
    for f in feats: by.setdefault(f['properties'].get('grid:code'), []).append(f)
    order = [f for g, l in by.items() for f in l[:per_tile]]; print('escenas candidatas', len(order))
    used = []
    for f in order:
        try:
            with rasterio.open(f['assets']['visual']['href']) as src:
                sb = transform_bounds('EPSG:4326', src.crs, *bbox)
                win = from_bounds(*sb, transform=src.transform).round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
                fac = 13; oh, ow = max(1, int(win.height / fac)), max(1, int(win.width / fac))
                arr = src.read(window=win, out_shape=(3, oh, ow), resampling=Resampling.average)
                st = src.window_transform(win) * rasterio.Affine.scale(win.width / ow, win.height / oh)
                tmp = np.zeros((3, H, W), np.uint8)
                reproject(arr, tmp, src_transform=st, src_crs=src.crs, dst_transform=dst_t, dst_crs='EPSG:3857', resampling=Resampling.bilinear, src_nodata=0, dst_nodata=0)
        except Exception as ex: print('err', f['id'], ex); continue
        valid = (tmp.min(axis=0) > 0) & (cnt < K)
        for k in range(K):
            m = valid & (cnt == k); stack[k][:, m] = tmp[:, m]
        cnt[valid] += 1; used.append(f['id'])
    print('escenas', len(used), 'cobertura', (cnt > 0).mean(), 'media capas', cnt[cnt > 0].mean())
    out = np.zeros((3, H, W), np.uint8)
    kk = np.clip(np.floor(0.3 * (cnt.astype(np.int16) - 1)), 0, K - 1).astype(np.int64)[None]
    inval = np.arange(K)[:, None, None] >= cnt[None]
    for b in range(3):
        a = stack[:, b].copy(); a[inval] = 255; a.sort(axis=0)
        out[b] = np.take_along_axis(a, kk, axis=0)[0]
    lut = (np.clip((np.arange(256) / 255.0) ** 0.85 * 1.08, 0, 1) * 255).astype(np.uint8)
    img = lut[out]; img[:, cnt == 0] = 236
    e_ = B.save(img, (s, w, n, e), 'hn_pais.jpg', 80)
    return used, e_
if __name__ == '__main__':
    used, e_ = pais(); e_['z'] = 0
    ix = json.load(open('site/sat/index.json')); ix['tiles'] = [e_] + [t for t in ix['tiles'] if t['f'] != e_['f']]
    ix['escenas'] = sorted(set(ix['escenas']) | set(used)); json.dump(ix, open('site/sat/index.json', 'w'))
