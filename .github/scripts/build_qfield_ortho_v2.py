#!/usr/bin/env python3
import concurrent.futures
import hashlib
import math
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()

CAPABILITIES_URL = 'https://geos1.snitcr.go.cr/Ortofoto1k/wmts?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0'
LAYER_ID = 'ortofoto2017_1000'
TARGET_RESOLUTION = 0.5
BBOX = (515554.05925504, 1063487.24559595, 518089.40387793, 1066042.08707424)
AREA_WKT = '''POLYGON ((515792.44657394296 1065511.3458931092, 515843.11224806897 1065577.58309672, 515897.9682520248 1065640.3392892485, 515956.779679948 1065699.3457565864, 516019.2946929817 1065754.3498416012, 516085.24559767195 1065805.116025744, 516154.3499921899 1065851.4269372832, 516226.3119754234 1065893.0842818297, 516300.8234138499 1065929.9096911908, 516377.5652606733 1065961.7454869142, 516456.2089216504 1065988.4553552563, 516536.4176617406 1066009.9249306933, 516617.8480465383 1066026.062285473, 516700.1514123915 1066036.7983231272, 516782.97535883257 1066042.0870742411, 516865.9652570277 1066041.9058932385, 516948.7657677172 1066036.2555553224, 517031.0223622286 1066025.1602531662, 517112.38283998746 1066008.6674933708, 517192.4988361204 1065986.8478931175, 517271.02731262526 1065959.794877905, 517347.6320267821 1065927.6242816476, 517421.9849705159 1065890.4738508489, 517493.76777454413 1065848.502654971, 517562.67307132 1065801.8904055248, 517628.4058109254 1065750.8366867828, 517690.68452429364 1065695.560101413, 517749.2425283648 1065636.2973346845, 517803.82906798535 1065573.3021412443, 517854.2103897057 1065506.8442588057, 517900.1707428353 1065437.2082533843, 517941.51330349286 1065364.692301035, 517978.0610177059 1065289.6069112867, 518009.65735987463 1065212.2735977503, 518036.1670034614 1065133.0235015796, 518057.4764008955 1065052.1959736778, 518073.49427033076 1064970.1371217193, 518084.15198705276 1064887.1983282014, 518089.40387793246 1064803.7347458773, 518089.2274175901 1064720.1037770004, 518083.62332548725 1064636.6635429016, 518072.6155634551 1064553.7713504457, 518056.25123369176 1064471.7821619355, 518034.6003776705 1064391.0470750234, 518007.75567676773 1064311.911819122, 517975.8320559206 1064234.7152747887, 517938.96619197534 1064159.7880223815, 517897.315928851 1064087.4509262517, 517851.05960198335 1064018.0137605034, 517800.39527497033 1063951.7738822275, 517745.5398916511 1063889.0149578922, 517686.728347262 1063830.005748344, 517624.21248265146 1063774.9989576382, 517558.26000585116 1063724.230150617, 517489.1533455811 1063677.9167438925, 517417.188441728 1063636.2570745456, 517342.6734777846 1063599.429550546, 517265.92756086675 1063567.5918865295, 517187.27935486234 1063540.8804282057, 517107.06567257753 1063519.4095683051, 517025.63003297744 1063503.2712565553, 516943.3211896281 1063492.5346058006, 516860.4916367187 1063487.245595945, 516777.4960990085 1063487.4268769918, 516694.6900122537 1063493.077672026, 516612.4280005335 1063504.1737805533, 516531.06235711346 1063520.6676821755, 516450.9415352502 1063542.4887401743, 516372.4086555197 1063569.5435041082, 516295.8000359766 1063601.7161101424, 516221.4437515249 1063638.8687773854, 516149.6582286023 1063680.842398108, 516080.75088127796 1063727.45721931, 516015.0167945579 1063778.5136127167, 515952.7374605543 1063833.7929298945, 515894.1795729502 1063893.058438833, 515839.59388490353 1063956.0563379645, 515789.2141352943 1064022.5168432808, 515743.2560479153 1064092.1553438886, 515701.9164078758 1064164.6736210394, 515665.3722191825 1064239.7611254256, 515633.77994710545 1064317.0963072563, 515607.2748485488 1064396.347993408, 515585.9703933094 1064477.1768057735, 515569.95777867676 1064559.2366147023, 515559.3055394483 1064642.1760213207, 515554.0592550399 1064725.639862387, 515554.24135489616 1064809.27073122, 515559.8510230631 1064892.7105082003, 515570.86420230573 1064975.6018942853, 515587.23369773035 1065057.589940968, 515608.889379482 1065138.3235701355, 515635.7384836105 1065217.457077314, 515667.66600984253 1065294.6516118716, 515704.53521450836 1065369.5766278335, 515746.1881965283 1065441.9112991178, 515792.44657394296 1065511.3458931092))'''

NS = {
    'wmts': 'http://www.opengis.net/wmts/1.0',
    'ows': 'http://www.opengis.net/ows/1.1',
    'xlink': 'http://www.w3.org/1999/xlink',
}


def text(node, path):
    found = node.find(path, NS)
    return None if found is None else found.text


def fetch_bytes(url, attempts=5):
    last = None
    for n in range(attempts):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 QField orthophoto builder'})
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read(), response.headers.get_content_type()
        except Exception as exc:
            last = exc
            time.sleep(min(2 ** n, 12))
    raise RuntimeError(f'Failed to fetch {url}: {last}')


def add_query(endpoint, params):
    parts = urllib.parse.urlsplit(endpoint)
    existing = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = urllib.parse.urlencode(existing + list(params.items()))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


raw, _ = fetch_bytes(CAPABILITIES_URL)
Path('wmts_capabilities.xml').write_bytes(raw)
root = ET.fromstring(raw)

layer = None
for candidate in root.findall('.//wmts:Contents/wmts:Layer', NS):
    if text(candidate, 'ows:Identifier') == LAYER_ID:
        layer = candidate
        break
if layer is None:
    raise RuntimeError(f'Layer {LAYER_ID} not found')

formats = [e.text for e in layer.findall('wmts:Format', NS) if e.text]
fmt = 'image/jpeg' if 'image/jpeg' in formats else ('image/png' if 'image/png' in formats else formats[0])
styles = layer.findall('wmts:Style', NS)
style = None
for candidate in styles:
    if candidate.attrib.get('isDefault', '').lower() == 'true':
        style = text(candidate, 'ows:Identifier')
        break
if style is None and styles:
    style = text(styles[0], 'ows:Identifier')
style = style or 'default'

linked = [e.text for e in layer.findall('wmts:TileMatrixSetLink/wmts:TileMatrixSet', NS) if e.text]
chosen_tms = None
for tms in root.findall('.//wmts:Contents/wmts:TileMatrixSet', NS):
    ident = text(tms, 'ows:Identifier')
    crs = text(tms, 'ows:SupportedCRS') or ''
    if ident in linked and '5367' in crs:
        chosen_tms = tms
        break
if chosen_tms is None:
    raise RuntimeError('No EPSG:5367 TileMatrixSet linked to the layer')
tms_id = text(chosen_tms, 'ows:Identifier')

matrices = []
for matrix in chosen_tms.findall('wmts:TileMatrix', NS):
    matrix_id = text(matrix, 'ows:Identifier')
    scale = float(text(matrix, 'wmts:ScaleDenominator'))
    resolution = scale * 0.00028
    top_left = [float(v) for v in text(matrix, 'wmts:TopLeftCorner').split()]
    tile_width = int(text(matrix, 'wmts:TileWidth'))
    tile_height = int(text(matrix, 'wmts:TileHeight'))
    matrix_width = int(text(matrix, 'wmts:MatrixWidth'))
    matrix_height = int(text(matrix, 'wmts:MatrixHeight'))
    matrices.append({
        'id': matrix_id, 'resolution': resolution, 'top_left_x': top_left[0], 'top_left_y': top_left[1],
        'tile_width': tile_width, 'tile_height': tile_height,
        'matrix_width': matrix_width, 'matrix_height': matrix_height,
    })
# Prefer the nearest native resolution that is not finer than requested, to avoid artificial oversampling.
coarser = [m for m in matrices if m['resolution'] >= TARGET_RESOLUTION]
selected = min(coarser, key=lambda m: m['resolution'] - TARGET_RESOLUTION) if coarser else min(matrices, key=lambda m: abs(m['resolution'] - TARGET_RESOLUTION))

operation = root.find(".//ows:Operation[@name='GetTile']/ows:DCP/ows:HTTP/ows:Get", NS)
if operation is None:
    raise RuntimeError('GetTile KVP endpoint not found')
endpoint = operation.attrib.get('{http://www.w3.org/1999/xlink}href')
if not endpoint:
    raise RuntimeError('GetTile endpoint has no href')

res = selected['resolution']
tw, th = selected['tile_width'], selected['tile_height']
origin_x, origin_y = selected['top_left_x'], selected['top_left_y']
minx, miny, maxx, maxy = BBOX
col_min = max(0, math.floor((minx - origin_x) / (tw * res)))
col_max = min(selected['matrix_width'] - 1, math.floor((maxx - origin_x) / (tw * res)))
row_min = max(0, math.floor((origin_y - maxy) / (th * res)))
row_max = min(selected['matrix_height'] - 1, math.floor((origin_y - miny) / (th * res)))
if col_max < col_min or row_max < row_min:
    raise RuntimeError('Computed WMTS tile range is empty')

cols = col_max - col_min + 1
rows = row_max - row_min + 1
width = cols * tw
height = rows * th
mosaic_minx = origin_x + col_min * tw * res
mosaic_maxy = origin_y - row_min * th * res
print(f'TileMatrixSet={tms_id!r}; matrix={selected["id"]!r}; resolution={res:.9f} m')
print(f'Tiles columns {col_min}-{col_max}, rows {row_min}-{row_max}: {cols * rows} tiles')

srs = osr.SpatialReference(); srs.ImportFromEPSG(5367)
driver = gdal.GetDriverByName('GTiff')
mosaic = driver.Create('ortho_mosaic_native.tif', width, height, 3, gdal.GDT_Byte,
                       options=['TILED=YES', 'COMPRESS=DEFLATE', 'BIGTIFF=IF_SAFER', 'NUM_THREADS=ALL_CPUS'])
mosaic.SetGeoTransform((mosaic_minx, res, 0, mosaic_maxy, 0, -res))
mosaic.SetProjection(srs.ExportToWkt())
for b in range(1, 4):
    mosaic.GetRasterBand(b).SetNoDataValue(0)


def download_tile(rc):
    row, col = rc
    params = {
        'SERVICE': 'WMTS', 'REQUEST': 'GetTile', 'VERSION': '1.0.0',
        'LAYER': LAYER_ID, 'STYLE': style, 'FORMAT': fmt,
        'TILEMATRIXSET': tms_id, 'TILEMATRIX': selected['id'],
        'TILEROW': str(row), 'TILECOL': str(col),
    }
    url = add_query(endpoint, params)
    data, content_type = fetch_bytes(url)
    return row, col, data, content_type

pairs = [(r, c) for r in range(row_min, row_max + 1) for c in range(col_min, col_max + 1)]
completed = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    for row, col, data, content_type in executor.map(download_tile, pairs):
        vsi = f'/vsimem/tile_{row}_{col}'
        gdal.FileFromMemBuffer(vsi, data)
        tile = gdal.Open(vsi)
        if tile is None or tile.RasterCount < 3:
            sample = data[:200].decode('utf-8', errors='replace')
            raise RuntimeError(f'Invalid tile {row},{col}; type={content_type}; sample={sample}')
        xoff = (col - col_min) * tw
        yoff = (row - row_min) * th
        for band_index in range(1, 4):
            array = tile.GetRasterBand(band_index).ReadAsArray()
            mosaic.GetRasterBand(band_index).WriteArray(array, xoff, yoff)
        tile = None
        gdal.Unlink(vsi)
        completed += 1
        if completed % 100 == 0 or completed == len(pairs):
            print(f'Downloaded {completed}/{len(pairs)} tiles')
mosaic.FlushCache(); mosaic = None

cutline_driver = ogr.GetDriverByName('GPKG')
cutline_ds = cutline_driver.CreateDataSource('area_cutline.gpkg')
cutline_layer = cutline_ds.CreateLayer('area', srs, ogr.wkbPolygon)
feature = ogr.Feature(cutline_layer.GetLayerDefn())
feature.SetGeometry(ogr.CreateGeometryFromWkt(AREA_WKT))
cutline_layer.CreateFeature(feature)
feature = None; cutline_ds = None

warp_options = gdal.WarpOptions(
    format='GTiff', cutlineDSName='area_cutline.gpkg', cropToCutline=True,
    dstSRS='EPSG:5367', xRes=res, yRes=res, resampleAlg='bilinear', dstNodata=0,
    multithread=True, creationOptions=['TILED=YES', 'COMPRESS=DEFLATE', 'BIGTIFF=IF_SAFER', 'NUM_THREADS=ALL_CPUS'])
gdal.Warp('ortho_clip_tmp.tif', 'ortho_mosaic_native.tif', options=warp_options)

translate_options = gdal.TranslateOptions(
    format='COG', noData=0,
    creationOptions=['COMPRESS=JPEG', 'QUALITY=90', 'BIGTIFF=IF_SAFER', 'NUM_THREADS=ALL_CPUS', 'OVERVIEWS=AUTO'])
gdal.Translate('ortofoto_snit_2015_2018_area_qfield.tif', 'ortho_clip_tmp.tif', options=translate_options)

final = gdal.Open('ortofoto_snit_2015_2018_area_qfield.tif')
gt = final.GetGeoTransform()
out_bounds = (gt[0], gt[3] + final.RasterYSize * gt[5], gt[0] + final.RasterXSize * gt[1], gt[3])
lines = [
    'Fuente: IGN/SNIT, Mosaico Ortofotos 1:1.000 2015-2018',
    f'Capa WMTS: {LAYER_ID}',
    f'TileMatrixSet: {tms_id}',
    f'TileMatrix: {selected["id"]}',
    f'CRS: EPSG:5367 (CR05 / CRTM05)',
    f'Resolución nativa utilizada: {res:.9f} m/píxel',
    f'Dimensiones: {final.RasterXSize} x {final.RasterYSize} píxeles',
    f'Extensión: {out_bounds}',
    f'Teselas descargadas: {len(pairs)}',
]
for idx in range(1, 4):
    stats = final.GetRasterBand(idx).GetStatistics(False, True)
    lines.append(f'Banda {idx} min/max/media/desv: {stats}')
final = None
Path('raster_info.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
sha = hashlib.sha256(Path('ortofoto_snit_2015_2018_area_qfield.tif').read_bytes()).hexdigest()
Path('SHA256SUMS.txt').write_text(f'{sha}  ortofoto_snit_2015_2018_area_qfield.tif\n', encoding='utf-8')
print(Path('raster_info.txt').read_text())
print('Output bytes:', Path('ortofoto_snit_2015_2018_area_qfield.tif').stat().st_size)
