"""Construye la base de datos geoespacial para SiteScore HN (Honduras).
Salida: site/sitedata.js  (correr desde la carpeta raíz: python3 pipeline/build_data.py)  (window.SD = {...})
- Grilla de población WorldPop R2025A 2020/2025/2030 (100 m, restringida) agregada a 500 m
- 298 municipios de geoBoundaries ADM2 (ICF 2019, CC BY 4.0), unidos por nombre y departamento a las
  proyecciones 2024 de edad y sexo (HDX COD-PS, UNFPA e INE)
- Zonas de ingreso alto en el Distrito Central (Tegucigalpa) y San Pedro Sula (polígonos aproximados, supuesto editable)
- Índice de poder adquisitivo (IPA): ingreso per cápita mensual del hogar por departamento, EPHPM 2023 base consolidada (INE),
  con pesos relativos dentro de cada departamento (cabeceras y ciudades más altas que el área rural) recalibrados
  para que el promedio ponderado del departamento iguale su ingreso EPHPM
- Hogares: personas por hogar por departamento, EPHPM 2023 (promedio nacional 3.8)
Entradas en data/: hnd_pop_2020/2025/2030.tif, gb_adm2.geojson, gb_adm1.geojson, pop_adm2.csv
"""
import json, base64, re, csv, unicodedata
import numpy as np, rasterio
from shapely.geometry import shape, Point, Polygon, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import contains_xy

F = 5  # 100 m x 5 = 500 m
d = rasterio.open('data/hnd_pop_2025.tif')
a = d.read(1).astype('float64'); a[a < 0] = 0
H = (a.shape[0] // F) * F; W = (a.shape[1] // F) * F
b = a[:H, :W].reshape(H // F, F, W // F, F).sum(axis=(1, 3)); del a
res = d.res[0] * F
x0, y1 = d.bounds.left, d.bounds.top
rows, cols = np.nonzero(b >= 5)
pops = b[rows, cols]
lon = x0 + (cols + 0.5) * res
lat = y1 - (rows + 0.5) * res
print('celdas', len(pops), 'pob', round(pops.sum()), 'max fila/col', rows.max(), cols.max())
def agg(path):
    r = rasterio.open(path); assert r.shape == d.shape and abs(r.bounds.left - d.bounds.left) < 1e-9
    x = r.read(1).astype('float64'); x[x < 0] = 0
    return x[:H, :W].reshape(H // F, F, W // F, F).sum(axis=(1, 3))[rows, cols]
p20 = agg('data/hnd_pop_2020.tif'); p30 = agg('data/hnd_pop_2030.tif')
print('2020', round(p20.sum()), '2030', round(p30.sum()))

# ---------------- Nombres ----------------
norm = lambda t: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower())
DEPN = {'atlantida': 'Atlántida', 'choluteca': 'Choluteca', 'colon': 'Colón', 'comayagua': 'Comayagua', 'copan': 'Copán', 'cortes': 'Cortés',
        'elparaiso': 'El Paraíso', 'franciscomorazan': 'Francisco Morazán', 'graciasadios': 'Gracias a Dios', 'intibuca': 'Intibucá',
        'islasdelabahia': 'Islas de la Bahía', 'bayislands': 'Islas de la Bahía', 'lapaz': 'La Paz', 'lempira': 'Lempira', 'ocotepeque': 'Ocotepeque',
        'olancho': 'Olancho', 'santabarbara': 'Santa Bárbara', 'valle': 'Valle', 'yoro': 'Yoro'}
# tildes por palabra (las fuentes vienen sin tildes)
ACC = {'Jose': 'José', 'Maria': 'María', 'Concepcion': 'Concepción', 'Jeronimo': 'Jerónimo', 'Ramon': 'Ramón', 'Martin': 'Martín', 'Lucia': 'Lucía',
       'Belen': 'Belén', 'Union': 'Unión', 'Paraiso': 'Paraíso', 'Copan': 'Copán', 'Colon': 'Colón', 'Cortes': 'Cortés', 'Danli': 'Danlí',
       'Sebastian': 'Sebastián', 'Agustin': 'Agustín', 'Andres': 'Andrés', 'Nicolas': 'Nicolás', 'Tomas': 'Tomás', 'Matias': 'Matías', 'Ines': 'Inés',
       'Jesus': 'Jesús', 'Limon': 'Limón', 'Aguan': 'Aguán', 'Yuscaran': 'Yuscarán', 'Guinope': 'Güinope', 'Moroceli': 'Morocelí', 'Oropoli': 'Oropolí',
       'Alubaren': 'Alubarén', 'Curaren': 'Curarén', 'Marale': 'Maralé', 'Angeles': 'Ángeles', 'Esquias': 'Esquías', 'Lamani': 'Lamaní',
       'Lejamani': 'Lejamaní', 'Meambar': 'Meámbar', 'Taulabe': 'Taulabé', 'Corquin': 'Corquín', 'Bahia': 'Bahía', 'Atlantida': 'Atlántida',
       'Intibuca': 'Intibucá', 'Barbara': 'Bárbara', 'Morazan': 'Morazán', 'Encarnacion': 'Encarnación', 'Asuncion': 'Asunción', 'Lopez': 'López',
       'Goascoran': 'Goascorán', 'Tomala': 'Tomalá', 'Sensenti': 'Sensentí', 'Culmi': 'Culmí', 'Salama': 'Salamá', 'Yocon': 'Yocón',
       'Nispero': 'Níspero', 'Proteccion': 'Protección', 'Quimistan': 'Quimistán', 'Jocon': 'Jocón', 'Roatan': 'Roatán', 'Saba': 'Sabá',
       'Cane': 'Cané', 'Marcovia': 'Marcovia', 'Namasigue': 'Namasigüe', 'Ojojona': 'Ojojona', 'Opatoro': 'Opatoro', 'Victoria': 'Victoria',
       'Juticalpa': 'Juticalpa', 'Bonito': 'Bonito', 'Lepaera': 'Lepaera', 'Teupasenti': 'Teupasenti', 'Ilama': 'Ilama', 'Petoa': 'Petoa',
       'Comayaguela': 'Comayagüela', 'Ocotepeque': 'Ocotepeque', 'Guarizama': 'Guarizama', 'Mangulile': 'Mangulile', 'Cabanas': 'Cabañas',
       'Penas': 'Peñas', 'Brus': 'Brus', 'Wampusirpi': 'Wampusirpi', 'Ahuas': 'Ahuas', 'Gualcince': 'Gualcince', 'Piraera': 'Piraera',
       'Concordia': 'Concordia', 'Valladolid': 'Valladolid', 'Duyure': 'Duyure', 'Choluteca': 'Choluteca', 'Lauterique': 'Lauterique',
       'Masaguara': 'Masaguara', 'Yamaranguila': 'Yamaranguila', 'Magdalena': 'Magdalena', 'Guajiquiro': 'Guajiquiro', 'Celilac': 'Celilac',
       'Ceguaca': 'Ceguaca', 'Esteban': 'Esteban', 'Jutiapa': 'Jutiapa'}
def pretty(t):
    t = re.sub(r'\s+', ' ', t.strip())
    return ' '.join(ACC.get(w, w) for w in t.split(' ')).replace('De ', 'de ').replace('Del ', 'del ')

# ---------------- Municipios: geoBoundaries ADM2 + COD-PS ADM2 ----------------
a2 = json.load(open('data/gb_adm2.geojson'))['features']; a1 = json.load(open('data/gb_adm1.geojson'))['features']
g1 = [(DEPN[norm(f['properties']['shapeName'])], shape(f['geometry']).buffer(0)) for f in a1]
cod = [r for r in csv.DictReader(open('data/pop_adm2.csv', encoding='utf-8-sig')) if int(r['T_TL'] or 0) > 0]
for r in cod: r['dep'] = DEPN[norm(r['ADM1_ES'])]; r['key'] = r['ADM2_PCODE']
idx = {(norm(r['ADM2_ES']), norm(r['dep'])): r for r in cod}
poly, lakes = [], []
for i, f in enumerate(a2):
    g = shape(f['geometry']).buffer(0); n = f['properties']['shapeName']
    if norm(n) == 'lagodeyojoa': lakes.append(g); continue
    dep = max(g1, key=lambda x: x[1].intersection(g).area)[0]
    r = idx.get((norm(n), norm(dep)))
    if r is None: raise SystemExit(f'sin pareja: {n} {dep}')
    poly.append([g, r])
used = {r['key'] for g, r in poly}
print('COD-PS sin polígono:', [(r['ADM2_ES'], r['dep'], r['T_TL']) for r in cod if r['key'] not in used])
for g in lakes:  # el lago se une al municipio vecino con mayor frontera común
    nb = max(poly, key=lambda x: x[0].buffer(0.002).intersection(g).area); nb[0] = unary_union([nb[0], g]).buffer(0)
D = sorted([(r, g) for g, r in poly], key=lambda x: (x[0]['dep'], x[0]['ADM2_ES']))
print('municipios', len(D), 'de', len(cod))

# ---------------- Zonas de ingreso alto (supuesto editable; polígonos aproximados) ----------------
ZONES = [  # (municipio, nombre, peso relativo, polígono lon/lat). Referencia: centros comerciales, hoteles y colonias en OpenStreetMap
    ('Distrito Central', 'Tegucigalpa · Palmira, Lomas del Guijarro, Lomas del Mayab, Los Próceres', 5.4,
     [(-87.198, 14.080), (-87.162, 14.080), (-87.162, 14.096), (-87.180, 14.106), (-87.198, 14.106)]),
    ('Distrito Central', 'Tegucigalpa · Tepeyac, Loma Linda, Miraflores, Las Colinas, Toncontín', 3.2,
     [(-87.215, 14.062), (-87.168, 14.062), (-87.168, 14.080), (-87.198, 14.080), (-87.198, 14.095), (-87.215, 14.095)]),
    ('Distrito Central', 'Tegucigalpa · El Hatillo', 2.8, [(-87.205, 14.112), (-87.150, 14.112), (-87.150, 14.170), (-87.205, 14.170)]),
    ('San Pedro Sula', 'San Pedro Sula · Trejo, Los Álamos, Jardines del Valle, Altiplano', 3.0,
     [(-88.058, 15.478), (-88.031, 15.478), (-88.031, 15.548), (-88.058, 15.548)]),
    ('San Pedro Sula', 'San Pedro Sula · Río de Piedras, Guamilito, Juan Lindo, Universidad', 2.0,
     [(-88.031, 15.495), (-88.013, 15.495), (-88.013, 15.540), (-88.031, 15.540)]),
]
REST = {'Distrito Central': 'Tegucigalpa · Centro, Comayagüela y resto', 'San Pedro Sula': 'San Pedro Sula · Centro y resto'}

# ---------------- IPA ----------------
# EPHPM 2023, base consolidada (INE), tabla «Ingreso per cápita por nivel educativo, según departamento»: L por persona al mes
IPC = {'Atlántida': 4242, 'Colón': 4207, 'Comayagua': 4021, 'Copán': 3797, 'Cortés': 5303, 'Choluteca': 3921, 'El Paraíso': 3447,
       'Francisco Morazán': 4977, 'Gracias a Dios': 3070, 'Intibucá': 3338, 'Islas de la Bahía': 7601, 'La Paz': 3563, 'Lempira': 2537,
       'Ocotepeque': 4216, 'Olancho': 3503, 'Santa Bárbara': 3319, 'Valle': 4461, 'Yoro': 4210}
NAT = 4329
# EPHPM 2023, tabla 10: personas por hogar por departamento (nacional 3.8)
HH = {'Atlántida': 3.5, 'Colón': 3.8, 'Comayagua': 3.9, 'Copán': 3.7, 'Cortés': 3.5, 'Choluteca': 3.9, 'El Paraíso': 4.0, 'Francisco Morazán': 3.7,
      'Gracias a Dios': 5.6, 'Intibucá': 4.1, 'Islas de la Bahía': 3.6, 'La Paz': 4.1, 'Lempira': 4.3, 'Ocotepeque': 3.6, 'Olancho': 3.9,
      'Santa Bárbara': 3.6, 'Valle': 3.8, 'Yoro': 3.8}
# Pesos relativos dentro del departamento (resto del departamento = 1.0). Se reescalan para que el promedio ponderado por
# población WorldPop 2025 iguale el ingreso EPHPM del departamento. Supuesto editable.
REL = {'Distrito Central': 2.2, 'Santa Lucía': 2.6, 'Valle de Ángeles': 2.0, 'San Antonio de Oriente': 1.6, 'Talanga': 1.4, 'Tatumbla': 1.3,
       'San Pedro Sula': 1.3, 'Puerto Cortés': 1.3, 'La Lima': 1.2, 'Villanueva': 1.15, 'Choloma': 1.15, 'San Manuel': 1.1, 'Pimienta': 1.1, 'Potrerillos': 1.1,
       'La Ceiba': 1.7, 'Tela': 1.35, 'El Progreso': 1.7, 'Olanchito': 1.35, 'Yoro': 1.15, 'Comayagua': 1.6, 'Siguatepeque': 1.6, 'Villa de San Antonio': 1.15,
       'La Paz': 1.7, 'Marcala': 1.4, 'Choluteca': 1.8, 'San Marcos de Colón': 1.2, 'Nacaome': 1.4, 'San Lorenzo': 1.5, 'Amapala': 1.1,
       'Danlí': 1.6, 'El Paraíso': 1.3, 'Yuscarán': 1.15, 'Juticalpa': 1.7, 'Catacamas': 1.45, 'Santa Rosa de Copán': 1.9, 'Copán Ruinas': 1.35,
       'Nueva Arcadia': 1.35, 'Ocotepeque': 1.5, 'Gracias': 1.9, 'La Esperanza': 1.9, 'Intibucá': 1.4, 'Santa Bárbara': 1.6, 'Trinidad': 1.1,
       'Tocoa': 1.5, 'Trujillo': 1.45, 'Roatán': 1.15, 'José Santos Guardiola': 0.8, 'Utila': 1.05, 'Puerto Lempira': 1.6}

munis = []; geoms = []; rel = []
for r, g in D:
    nm, dep = pretty(r['ADM2_ES']), r['dep']
    zs = [z for z in ZONES if z[0] == nm]
    rest = g
    for zn in zs:
        zg = Polygon(zn[3]).intersection(g)
        if zg.is_empty: continue
        rest = rest.difference(zg)
        geoms.append(zg); rel.append(zn[2]); munis.append({'d': dep, 'm': zn[1], 'z': 1, 'h': HH[dep], 'key': r['key']})
    geoms.append(rest); rel.append(REL.get(nm, 1.0))
    munis.append({'d': dep, 'm': REST.get(nm, nm) if zs else nm, 'h': HH[dep], 'key': r['key'], **({'z': 1} if zs else {'po': int(r['T_TL'])})})
for k, m in enumerate(munis):
    rp = geoms[k].representative_point(); m['id'] = k; m['la'] = round(rp.y, 4); m['lo'] = round(rp.x, 4)

mid = np.full(len(pops), -1, dtype=np.int32)
for gi, gm in enumerate(geoms):
    mm = contains_xy(gm, lon, lat); mid[mm & (mid < 0)] = gi
tree = STRtree(geoms)
for k in np.nonzero(mid < 0)[0]: mid[k] = tree.nearest(Point(lon[k], lat[k]))
mp = np.bincount(mid, weights=pops, minlength=len(munis))
for m in munis: m['p'] = int(round(mp[m['id']]))

# Recalibración por departamento
rel = np.array(rel)
for dep in IPC:
    ks = [k for k, m in enumerate(munis) if m['d'] == dep]
    w = sum(mp[k] * rel[k] for k in ks) / max(sum(mp[k] for k in ks), 1)
    f = (IPC[dep] / NAT) / w
    for k in ks: munis[k]['i'] = round(float(rel[k] * f), 2)
# Normalización: promedio nacional ponderado por población = 1.00
w = sum(m['p'] * m['i'] for m in munis) / sum(m['p'] for m in munis)
print('IPA medio antes de normalizar', round(w, 3))
for m in munis: m['i'] = round(m['i'] / w, 2)
for dep in IPC:
    ks = [m for m in munis if m['d'] == dep]
    print(f"  {dep:18s} EPHPM {IPC[dep]/NAT:.2f}  modelo {sum(m['p']*m['i'] for m in ks)/sum(m['p'] for m in ks):.2f}")

# Edad y sexo (COD-PS 2024): 15 bandas; 70+ = 70-74 + 75-79 + 80+
BANDS = ['00_04', '05_09', '10_14', '15_19', '20_24', '25_29', '30_34', '35_39', '40_44', '45_49', '50_54', '55_59', '60_64', '65_69']
prof = {}
for r in cod:
    v = [float(r['F_' + x]) for x in BANDS] + [float(r['F_70_74']) + float(r['F_75_79']) + float(r['F_80Plus'])] + \
        [float(r['M_' + x]) for x in BANDS] + [float(r['M_70_74']) + float(r['M_75_79']) + float(r['M_80Plus'])]
    prof[r['key']] = v
AGES = []; akey = {}
for m in munis:
    v = prof[m['key']]; t = sum(v); sh = tuple(round(x / t, 4) for x in v)
    if sh not in akey: akey[sh] = len(AGES); AGES.append(list(sh))
    m['a'] = akey[sh]
for m in munis: del m['key']

out_f = []
def rnd(c):
    if isinstance(c[0], (float, int)): return [round(c[0], 4), round(c[1], 4)]
    return [rnd(x) for x in c]
for i, gm in enumerate(geoms):
    s = gm.simplify(0.0015, preserve_topology=True)
    if s.geom_type == 'GeometryCollection':
        s = unary_union([x for x in s.geoms if x.geom_type in ('Polygon', 'MultiPolygon')])
    gj = mapping(s)
    out_f.append({'type': 'Feature', 'properties': {'id': i}, 'geometry': {'type': gj['type'], 'coordinates': rnd(gj['coordinates'])}})

b64 = lambda arr: base64.b64encode(arr.tobytes()).decode()
SD = {
  'meta': {'res': res, 'src': 'WorldPop R2025A 2020/2025/2030 (100 m, constrained) agregado a 500 m; geoBoundaries ADM2 (ICF 2019); EPHPM 2023; COD-PS 2024 edad y sexo',
           'n': int(len(pops)), 'pop': int(round(pops.sum())), 'iso': 'HND'},
  'grid': {'x0': x0, 'y1': y1}, 'r': b64(rows.astype('<u2')), 'c': b64(cols.astype('<u2')),
  'pop': b64(np.minimum(np.round(pops), 65535).astype('<u2')), 'mid': b64(mid.astype('<u2')), 'munis': munis,
  'p20': b64(np.minimum(np.round(p20), 65535).astype('<u2')), 'p30': b64(np.minimum(np.round(p30), 65535).astype('<u2')),
  'ages': AGES, 'bands': ['0–4', '5–9', '10–14', '15–19', '20–24', '25–29', '30–34', '35–39', '40–44', '45–49', '50–54', '55–59', '60–64', '65–69', '70+'],
  'geo': {'type': 'FeatureCollection', 'features': out_f},
}
s = 'window.SD=' + json.dumps(SD, ensure_ascii=False, separators=(',', ':')) + ';'
open('site/sitedata.js', 'w', encoding='utf-8').write(s)
print('size KB', len(s.encode()) // 1024, 'registros', len(munis))
print([(m['m'], m['p'], m['i']) for m in sorted(munis, key=lambda m: -m['p'])[:16]])
print([(m['m'], m['p'], m['i']) for m in munis if m.get('z')])
