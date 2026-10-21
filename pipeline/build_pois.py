"""Comercios y generadores de tráfico de Honduras desde el export HOT/OSM de HDX (actualización mensual).
Fuente: https://data.humdata.org/dataset/hotosm_hnd_points_of_interest
Descarga: https://production-raw-data-api.s3.amazonaws.com/ISO3/HND/points_of_interest/hotosm_hnd_points_of_interest_osm_geojson.zip
Salida: site/pois.js  {giros: {COD: [[lat, lon, marca, nombre], ...]}, gens: [[lat, lon, tipo, nombre], ...], fecha}
Uso (desde la carpeta raíz): python3 pipeline/build_pois.py [data/hot/points_of_interest.geojson]
"""
import json, re, sys, os
from shapely.geometry import shape

SRC = sys.argv[1] if len(sys.argv) > 1 else 'data/hot/points_of_interest.geojson'
d = json.load(open(SRC))

GIRO_TAGS = {
    'SUP': {'shop': ['supermarket', 'wholesale', 'hypermarket'], 'amenity': ['marketplace']},
    'FAR': {'amenity': ['pharmacy'], 'shop': ['chemist']},
    'RAP': {'amenity': ['fast_food']},
    'RES': {'amenity': ['restaurant', 'cafe']},
    'GAS': {'amenity': ['fuel']},
    'FER': {'shop': ['hardware', 'doityourself', 'paint', 'trade']},
    'CON': {'shop': ['convenience']},
    'BAN': {'amenity': ['bank']},
    'ROP': {'shop': ['clothes', 'shoes', 'second_hand']},
    'PAN': {'shop': ['bakery', 'pastry']},
}
GEN_TAGS = {('shop', 'mall'): 'M', ('amenity', 'marketplace'): 'K', ('amenity', 'school'): 'E',
            ('amenity', 'university'): 'E', ('amenity', 'college'): 'E', ('amenity', 'hospital'): 'O',
            ('amenity', 'clinic'): 'O', ('amenity', 'bus_station'): 'U'}
# marcas de Honduras: (regex sobre el nombre en minúsculas, clave). La primera que coincide gana.
BRANDS = {
    'SUP': [(r'walmart', 'WM'), (r'pa[ií]z', 'PZ'), (r'maxi ?-? ?desp[ae]n?sa|maxi ?bodega', 'MX'), (r'(despensa|dispensa|despenda) famil?i?ar', 'DF'),
            (r'm[aá]s ?x ?menos', 'MXM'), (r'pricesmart', 'PS'), (r'la colonia', 'LC'), (r'antorcha', 'ANT'), (r'colonial', 'COL'),
            (r'junior', 'JUN'), (r"eldon'?s", 'ELD'), (r'banasupro', 'BAN'), (r'la despensa', 'LDE'), (r'econ[oó]mica', 'ECO')],
    'FAR': [(r'kielsa', 'KIE'), (r'sim[aá]n', 'SIM'), (r'del ahorro|el ahorro|farmacias? ahorro', 'AHO'), (r'farm?a ?city|farmcity', 'FCY'),
            (r'punto ?farma', 'PFA'), (r'regis', 'REG'), (r'pharmaster', 'PHM'), (r'vaver', 'VAV'), (r'econ[oó]micas', 'ECO'),
            (r'farmalife', 'FLI'), (r'san (rafael|antonio|jorge|juan|pablo|miguel|jos[eé])', '_S')],
    'RAP': [(r'mc ?donald', 'MCD'), (r'campero', 'CAM'), (r'pollolandia', 'PLL'), (r'burger king', 'BK'), (r"wendy", 'WEN'), (r'subway', 'SUB'),
            (r"papa john", 'PJ'), (r'little caesar', 'LCA'), (r'\bkfc\b', 'KFC'), (r'popeyes', 'POP'), (r"church'?s", 'CHU'), (r'dunkin', 'DUN'),
            (r'domino', 'DOM'), (r'pizza hut', 'PH'), (r'bigos', 'BIG'), (r'baleadas express', 'BEX'), (r'super ?pollo', 'SPO'),
            (r'pollo campesino', 'PCA'), (r'cinnabon', 'CIN'), (r'quiznos', 'QZ'), (r'taco ?pollo', 'TPO'), (r'coco baleadas', 'COC'),
            (r'pollos? el (?:rey|corral)|el corral', 'ECR'), (r'pollo tropical', 'PTR'), (r'power chicken', 'PCH')],
    'RES': [(r'starbucks', 'STB'), (r'esp?res?s?o americano', 'ESA'), (r'caf[eé] welchez|welchez', 'WEL'), (r'pizza hut', 'PH'),
            (r"denny'?s", 'DEN'), (r"applebee", 'APP'), (r"chili'?s", 'CHI'), (r"friday", 'TGI'), (r'la albahaca', 'ALB'),
            (r"tony roma", 'TRO'), (r"ruby tuesday", 'RTU'), (r'mango tango', 'MTA'), (r'cafetini', 'CFT'), (r"toto'?s pizza", 'TOT'),
            (r'pupusas? miraflores', 'PMI'), (r'pollolandia', 'PLL'), (r'campero', 'CAM'), (r'tio dolmo|t[ií]o dolmo', 'TDO'),
            (r"costa'?s burg", 'COS'), (r'e ?coffee', 'ECO'), (r'bigos', 'BIG'), (r'(la )?casa del caf[eé]', 'LCC')],
    'GAS': [(r'\buno\b', 'UNO'), (r'puma', 'PUM'), (r'texaco', 'TEX'), (r'shell', 'SHE'), (r'petrosun', 'PSU'), (r'dippsa', 'DIP'),
            (r'american', 'AME'), (r'mobil|esso', 'MOB'), (r'gasolinera', '')],
    'FER': [(r'\bepa\b', 'EPA'), (r'pinturas americanas?', 'PAM'), (r'sherwin', 'SHW'), (r'alutech', 'ALU'), (r'pintacasa', 'PIN'),
            (r'ferromax', 'FMX'), (r'la mundial', 'MUN'), (r'comex', 'CMX'), (r'protecto', 'PRT'), (r'femosa|\bace\b', 'ACE'),
            (r'larach', 'LAR'), (r'ferrecentro', 'FRC'), (r'promaco', 'PRM'), (r'novacentro|novaconstru', 'NOV'), (r'\bintexsy|intex', 'ITX'),
            (r'super tornillos', 'STO'), (r'serrano industrial', 'SER')],
    'CON': [(r'circle ?k', 'CK'), (r'texaco|star ?mart|food ?mart', 'TEX'), (r'\buno\b|la uno', 'UNO'), (r'pronto', 'PRO'), (r'puma', 'PUM'),
            (r'super ?7', 'S7'), (r'flash ?mart', 'FLA'), (r'pulper[ií]a|abarroter[ií]a|mercadito|mini ?super', '_T')],
    'BAN': [(r'cajero|\batm\b|autobanco|auto banco', 'ATM'), (r'occidente', 'OCC'), (r'atl[aá]ntida', 'ATL'), (r'banpa[ií]s|del pa[ií]s', 'BPA'),
            (r'ficohsa', 'FIC'), (r'\bbac\b|credomatic|bamer', 'BAC'), (r'davivienda', 'DAV'), (r'azteca', 'AZT'), (r'banrural|ban rural', 'BRU'),
            (r'lafise', 'LAF'), (r'banco popular', 'POP'), (r'banhcaf', 'BHC'), (r'banadesa', 'BDS'), (r'prom[eé]rica', 'PRO'),
            (r'ficensa', 'FCE'), (r'cofisa', 'COF'), (r'banco central', 'BCH'), (r'citi', 'CIT'), (r'continental', 'CON'),
            (r'cooperativa|coop\b|coac|coompol', 'COO'), (r'banco de los trabajadores|bantrab', 'BTR'), (r'uno bank|banco uno', 'BUN')],
    'ROP': [(r'diunsa', 'DIU'), (r'carri[oó]n', 'CAR'), (r'lady lee', 'LLE'), (r'kmart', 'KMA'), (r'payless', 'PAY'), (r'megapaca', 'MPC'),
            (r"ma[nn]?gy'?s|manny'?s", 'MAN'), (r'esther marka', 'EST'), (r'el palacio', 'PAL'), (r'aca joe', 'ACA'), (r'nautica', 'NAU'),
            (r'van heusen', 'VAN'), (r'\bzara\b', 'ZAR'), (r'\bbata\b', 'BAT'), (r'adoc', 'ADO'), (r'sermay', 'SMA'), (r'unlimited', 'UNL'),
            (r'ropa americana|paca|american (store|rags)', '_P')],
    'PAN': [(r"salman", 'SAL'), (r'princesita', 'PRI'), (r'super queques', 'SQQ'), (r'skandia', 'SKA'), (r'hawit', 'HAW'), (r'italiana', 'ITA'),
            (r'moderna', 'MOD'), (r"basilio", 'BAS'), (r'shadd?ai|shadday', 'SHA'), (r'panifer', 'PNF'), (r'pan y m[aá]s', 'PYM')],
}
# nombres que OSM etiqueta como supermercado o tienda por departamentos pero que no son del giro
NOT_SUP = r'curacao|tropigas|casa bueso|escalante|gallo m[aá]s gallo|kafie|casino|embotelladora|repuestos|ferreter|mall\b|jetstereo|tortiller|bingo'
REV = {}
for g, t in GIRO_TAGS.items():
    for k, vals in t.items():
        for v in vals: REV.setdefault((k, v), []).append(g)

out = {g: [] for g in GIRO_TAGS}; gens = []; seen = set()
for f in d['features']:
    p = f['properties']; geom = f['geometry']
    if geom is None: continue
    if geom['type'] == 'Point': lo, la = geom['coordinates'][:2]
    else:
        c = shape(geom).representative_point(); lo, la = c.x, c.y
    if not (12.9 < la < 17.5 and -89.5 < lo < -82.5): continue
    name = (p.get('name') or '').strip()
    nl = name.lower()
    tags = [(k, p.get(k)) for k in ('amenity', 'shop') if p.get(k)]
    if any(v in ('supermarket', 'department_store', 'wholesale') for k, v in tags) and re.search(NOT_SUP, nl): tags = [t for t in tags if t[0] != 'shop']
    if ('shop', 'department_store') in tags:
        # Walmart y Paiz cuentan como supermercado; Diunsa, Carrión, Lady Lee y Kmart como ropa; las demás se omiten
        tags = [('shop', 'supermarket')] if re.search(r'walmart|pa[ií]z', nl) else [('shop', 'clothes')] if re.search(r'diunsa|carri[oó]n|lady lee|kmart', nl) else [t for t in tags if t != ('shop', 'department_store')]
    # pulperías etiquetadas como supermercado: van a conveniencia (tienda de barrio)
    if ('shop', 'supermarket') in tags and re.search(r'pulper[ií]a|abarroter[ií]a|mercadito|mini ?super', nl) and not re.search(r'colonia|despensa|antorcha', nl):
        tags = [('shop', 'convenience')]
    for k, v in tags:
        gt = GEN_TAGS.get((k, v))
        if gt:
            key = ('G', gt, round(la, 4), round(lo, 4))
            if key not in seen:
                seen.add(key); gens.append([round(la, 5), round(lo, 5), gt, name[:40]])
        for g in REV.get((k, v), []):
            b = ''
            for rx, code in BRANDS.get(g, []):
                if re.search(rx, nl): b = code; break
            if b == '_S': b = ''
            if not b and v in ('wholesale',): b = '_W'
            if not b and v in ('marketplace',): b = '_K'
            if not b and v in ('doityourself',): b = '_D'
            if not b and v in ('second_hand',): b = '_P'
            if g == 'BAN' and b == 'BCH': continue  # banco central: no atiende público minorista
            key = (g, b or nl, round(la, 3), round(lo, 3))
            if key in seen: continue
            seen.add(key)
            out[g].append([round(la, 5), round(lo, 5), b, name[:40]])

fecha = None
rd = os.path.join(os.path.dirname(SRC), 'README.txt')
if os.path.exists(rd):
    m = re.search(r'Snapshot:\s*(\S+)', open(rd).read())
    if m: fecha = m.group(1)
open('site/pois.js', 'w', encoding='utf-8').write('window.SP=' + json.dumps({'giros': out, 'gens': gens, 'fecha': fecha}, ensure_ascii=False, separators=(',', ':')) + ';')
print({g: len(v) for g, v in out.items()}, 'gens', len(gens), 'fecha', fecha)
from collections import Counter
for g in out:
    c = Counter(x[2] for x in out[g]); print(g, c.most_common(16))
