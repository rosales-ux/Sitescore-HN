"""Vista satelital para SiteScore HN a partir de Sentinel-2 L2A (Copernicus, uso libre incluido comercial).
Fuente: Earth Search (Element 84) — colección sentinel-2-c1-l2a, recurso 'visual' (color verdadero, 10 m).
Salida: site/sat/*.jpg + site/sat/index.json  [{f, b: [[s, w], [n, e]], z: zoom mínimo}]
"""
import json, os, math, urllib.request, numpy as np, rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from PIL import Image

os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
os.environ.setdefault('AWS_NO_SIGN_REQUEST', 'YES')
os.environ.setdefault('GDAL_HTTP_MAX_RETRY', '4'); os.environ.setdefault('GDAL_HTTP_RETRY_DELAY', '2')
OUT = 'site/sat'; os.makedirs(OUT, exist_ok=True)
DT = '2025-11-01T00:00:00Z/2026-05-01T00:00:00Z'  # época seca

def search(bbox, maxcc=20):
    body = {"collections": ["sentinel-2-c1-l2a"], "bbox": bbox, "datetime": DT, "limit": 200, "query": {"eo:cloud_cover": {"lt": maxcc}},
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}]}
    req = urllib.request.Request("https://earth-search.aws.element84.com/v1/search", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    fs = json.load(urllib.request.urlopen(req, timeout=120))['features']
    return sorted(fs, key=lambda f: f['properties']['eo:cloud_cover'])

def merc(lon, lat):
    x = lon * 20037508.34 / 180; y = math.log(math.tan((90 + lat) * math.pi / 360)) * 6378137
    return x, y

def build(name, bbox, res, per_tile=3):
    w, s, e, n = bbox
    x0, y0 = merc(w, s); x1, y1 = merc(e, n)
    W = int((x1 - x0) / res); H = int((y1 - y0) / res)
    dst_t = from_origin(x0, y1, res, res)
    out = np.zeros((3, H, W), np.uint8); filled = np.zeros((H, W), bool)
    feats = search(bbox)
    # candidatos: por tile MGRS, los de menor nubosidad
    by = {}
    for f in feats: by.setdefault(f['properties'].get('grid:code'), []).append(f)
    order = []
    for k in range(per_tile):
        for g, lst in by.items():
            if k < len(lst): order.append(lst[k])
    order.sort(key=lambda f: f['properties']['eo:cloud_cover'])
    used = []
    for f in order:
        if filled.mean() > 0.999: break
        href = f['assets']['visual']['href']
        try:
            with rasterio.open(href) as src:
                sb = transform_bounds('EPSG:4326', src.crs, *bbox)
                win = from_bounds(*sb, transform=src.transform).round_offsets().round_lengths()
                win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
                fac = max(1, int(res / 10 * 0.9))
                oh, ow = max(1, int(win.height / fac)), max(1, int(win.width / fac))
                arr = src.read(window=win, out_shape=(3, oh, ow), resampling=Resampling.average)
                st = src.window_transform(win) * rasterio.Affine.scale(win.width / ow, win.height / oh)
                tmp = np.zeros((3, H, W), np.uint8)
                reproject(arr, tmp, src_transform=st, src_crs=src.crs, dst_transform=dst_t, dst_crs='EPSG:3857', resampling=Resampling.bilinear, src_nodata=0, dst_nodata=0)
        except Exception as ex:
            print('  error', f['id'], ex); continue
        ok = (tmp.max(axis=0) > 0) & ~filled
        if ok.sum() == 0: continue
        out[:, ok] = tmp[:, ok]; filled |= ok; used.append(f['id'])
        print(f"  {name}: {f['id']} cc={f['properties']['eo:cloud_cover']:.2f} cubre {filled.mean():.3f}")
    # realce suave (gamma) para pantalla
    lut = (np.clip((np.arange(256) / 255.0) ** 0.85 * 1.08, 0, 1) * 255).astype(np.uint8)
    img = lut[out]; img[:, ~filled] = 236
    return img, (s, w, n, e), used, filled.mean()

def save(img, b, fname, q=80):
    Image.fromarray(np.moveaxis(img, 0, -1)).save(os.path.join(OUT, fname), quality=q, optimize=True, progressive=True)
    return {'f': 'sat/' + fname, 'b': [[b[0], b[1]], [b[2], b[3]]]}

if __name__ == '__main__':
    idx = []; credits = set()
    # 1) País completo: build_sat_pais.py genera el mosaico sin nubes (hn_pais.jpg, 150 m) y lo agrega al índice
    # 2) Distrito Central (Tegucigalpa y Comayagüela) y valle de Sula (San Pedro Sula, Choloma, Villanueva, La Lima) a 10 m, en 2x2 piezas
    for tag, (W0, S0, E0, N0) in {'dc': (-87.32, 13.98, -87.08, 14.20), 'sula': (-88.10, 15.28, -87.82, 15.66)}.items():
        for i, (a, c) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
            w = W0 + (E0 - W0) * c / 2; e_ = W0 + (E0 - W0) * (c + 1) / 2
            s = S0 + (N0 - S0) * a / 2; n = S0 + (N0 - S0) * (a + 1) / 2
            img, b, used, cov = build(f'{tag}{i}', [w, s, e_, n], 10.3)
            e = save(img, b, f'{tag}_{i}.jpg', 78); e['z'] = 11; idx.append(e); credits.update(used)
    # 3) Cabeceras y ciudades intermedias, 10 m
    C = {'la_ceiba': (15.765, -86.800), 'choluteca': (13.303, -87.190), 'comayagua': (14.455, -87.640), 'el_progreso': (15.400, -87.805),
         'puerto_cortes': (15.835, -87.940), 'danli': (14.035, -86.575), 'juticalpa': (14.665, -86.220), 'siguatepeque': (14.598, -87.835),
         'santa_rosa_de_copan': (14.770, -88.780), 'tela': (15.775, -87.462), 'tocoa': (15.680, -86.000), 'olanchito': (15.482, -86.578),
         'roatan': (16.335, -86.520), 'catacamas': (14.845, -85.892), 'la_esperanza': (14.310, -88.170), 'la_paz': (14.318, -87.678),
         'san_lorenzo_nacaome': (13.465, -87.430), 'santa_barbara': (14.918, -88.236)}
    for k, (la, lo) in C.items():
        img, b, used, cov = build(k, [lo - .065, la - .06, lo + .065, la + .06], 10.3)
        e = save(img, b, f'{k}.jpg', 78); e['z'] = 11; idx.append(e); credits.update(used)
    json.dump({'tiles': idx, 'escenas': sorted(credits)}, open(os.path.join(OUT, 'index.json'), 'w'))
    print('archivos', len(idx), 'MB', round(sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)) / 1e6, 1))
