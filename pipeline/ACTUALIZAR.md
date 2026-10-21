# SiteScore HN — cómo actualizar los datos

Estructura de trabajo: data/ (entradas), pipeline/ (scripts), site/ (lo que se publica). Correr todo desde la carpeta raíz.

1. Comercios (mensual): descargar el export HOT de HDX
   https://production-raw-data-api.s3.amazonaws.com/ISO3/HND/points_of_interest/hotosm_hnd_points_of_interest_osm_geojson.zip
   descomprimir en data/hot/ y correr `python3 pipeline/build_pois.py` → site/pois.js
   Después, en la página: Base de datos → «Calibrar objetivos con puntos existentes» en cada giro si cambió mucho la red,
   y copiar los L/m² resultantes a GIROS en app.js.
2. Población (anual): WorldPop R2025A, HND 100 m constrained 2020/2025/2030
   (https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/<año>/HND/v1/100m/constrained/hnd_pop_<año>_CN_100m_R2025A_v1.tif)
   → data/hnd_pop_<año>.tif
   Límites geoBoundaries gbOpen HND ADM1 y ADM2 (https://www.geoboundaries.org/api/current/gbOpen/HND/ALL/; los .geojson se bajan
   de media.githubusercontent.com porque están en Git LFS) → data/gb_adm1.geojson, data/gb_adm2.geojson
   Edad y sexo COD-PS 2024 (HDX cod-ps-hnd, hnd_admpop_adm2_2024.csv) → data/pop_adm2.csv
   Correr `python3 pipeline/build_data.py` → site/sitedata.js
   IPA: ingreso per cápita del hogar por departamento de la EPHPM base consolidada (INE). Al salir una nueva, actualizar IPC, NAT y HH
   en build_data.py. Pesos dentro del departamento (REL) y zonas de Tegucigalpa y San Pedro Sula (ZONES) son supuestos editables.
3. Página: `python3 pipeline/build_page.py` (app.src.txt con /*LEAFLET_CSS*/ = leaflet 1.9.4 min.css y /*APP_JS*/ = app.js)
   → site/index.html (artifact de claude.ai) y gh/index.html (página completa para GitHub Pages).
4. Artifact: publicar site/index.html al mismo enlace con files: sitedata.js, pois.js, sat/*, pipeline/*; capacidad downloads (PDF).
   GitHub: subir gh/index.html, sitedata.js, pois.js y sat/ al repositorio (Add file → Upload files) y hacer commit.
5. Vista satelital (opcional, anual): `python3 pipeline/build_sat.py` y luego `python3 pipeline/build_sat_pais.py` → site/sat/*.jpg + index.json
   (Sentinel-2 L2A de Earth Search, época seca nov–abr; 10 m en Distrito Central, valle de Sula y 18 ciudades; mosaico de 150 m del país).
   Detrás de un proxy, exportar CURL_CA_BUNDLE con el certificado del proxy para que GDAL lea las imágenes.
