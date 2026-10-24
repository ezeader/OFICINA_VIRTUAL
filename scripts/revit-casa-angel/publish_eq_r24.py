"""Publish Equipamiento fijo to public/casa-angel/rubros/equipamiento/manifest.json (web contract lib/rubros.ts)."""
import argparse, collections, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'equipamiento'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'PL': 'Placares', 'MU': 'Muebles fijos (TV, pared, vinoteca, mesas de luz)', 'VA': 'Vanitorios', 'ME': 'Mesadas y bajomesadas', 'LV': 'Lavaderos', 'MA': 'Mamparas', 'EQ': 'Equipos de cocina'}
SKIP = ('eq-request.json', 'eq-elements.json', 'eq-plan.json', 'eq-probe.json', 'eq-run.json')


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('eq-*.json')):
        if f.name in SKIP: continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'EQ-00', s['number'].startswith('EQ-F'), s['number']))


def front_m2(e): return e['width_m'] * e['height_m']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    plan = read(OUT / 'eq-plan.json'); els = plan['elements']; loose = plan['loose']
    g = {k: [e for e in els if e['kind'] == k] for k in KINDS}
    if a.index_columns:
        comp = [f"{k} {KINDS[k].split(' (')[0]}: {len(v)} u" + (f" · frente {c2(sum(front_m2(e) for e in v))} m²" if k == 'PL' else (f" · {c2(sum(e['width_m'] for e in v))} ml" if k in ('VA', 'ME', 'LV') else '')) for k, v in g.items() if v]
        comp.append(f"Mobiliario suelto (referencia): {len(loose)} piezas")
        cols = [{'title': 'Criterios', 'lines': ['Fijo = familia in situ (carpintería) + mamparas', 'y equipos de cocina. Medidas: caja envolvente.', 'Artefactos sanitarios: rubro Sanitarias.', 'Mobiliario suelto y ascensor: fuera del rubro.', 'Códigos solo como anotación (no en Mark).']},
                {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['EQ-00  Índice', 'EQ-01  Planta Baja', 'EQ-02  Planta Alta', f"EQ-F-…  {len([s for s in records() if s['number'].startswith('EQ-F')])} fichas (PL, MU, VA, ME, LV)"]},
                {'title': 'No modelado / a definir', 'lines': ['Muebles de cocina altos y despiece de bajomesadas.', 'Interiores de placares (estantes, barrales, cajones).', 'Herrajes, materiales y terminaciones.', 'Bomba de pileta (Grundfos): ver Pileta.']}]
        print(json.dumps(cols, ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R24', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'eq-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    code = {str(e['id']): e for e in els}; proj = {str(p['id']): p for p in read(OUT / 'eq-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r24-{n}.pdf'; assert src.exists(), n
        shutil.copy2(src, pub / f'{n}.pdf')
        pdf = fitz.open(src); page = pdf[0]; pw, ph = page.rect.width, page.rect.height
        svg(page, pub / f'{n}.svg.gz'); page.get_pixmap(matrix=fitz.Matrix(.6, .6)).save(pub / f'{n}-preview.png'); page.get_pixmap(matrix=fitz.Matrix(.35, .35)).save(pub / f'{n}.png')
        views = []
        if s['views']:
            scale, ox, oy, used, res = calibrate(page, [(x['text'], x['anchor']) for x in s['notes']] + [(v['label'], v['anchor']) for v in s['views']])
            for v in s['views']:
                lo, hi = v['box']
                rect = fitz.Rect(ox + lo[0] * scale - 3, oy - hi[1] * scale - 3, ox + hi[0] * scale + 3, oy - lo[1] * scale + 3) & page.rect
                crop = fitz.open(); p = crop.new_page(width=rect.width, height=rect.height); p.show_pdf_page(p.rect, pdf, 0, clip=rect)
                file = f"{n}-view-{v['id']}.svg.gz"; svg(p, pub / file); crop.close()
                rows = proj.get(str(v['id']), {}).get('elements', [])
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']],
                              'elements': [{'code': (code.get(r['elementId']) or {}).get('code'), 'elementId': r['elementId'], 'label': (code.get(r['elementId']) or {}).get('label'), 'box': [round(x, 4) for x in r['box']]} for r in rows]})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'),
                    'elementKind': s.get('elementKind'), 'note': None, 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    r3 = lambda v: round(v, 3)
    codes = [{'code': e['code'], 'kind': e['kind'], 'label': e['label'], 'status': e['status'], 'elementId': str(e['id']), 'type': e['family'], 'room': e['room'], 'level': e['level'],
              'width_m': r3(e['width_m']), 'depth_m': r3(e['depth_m']), 'height_m': r3(e['height_m']), 'bottom_m': r3(e['bottom_m']), 'length_m': r3(e['width_m']),
              'area_m2': r3(front_m2(e)), 'inPlace': e['inPlace'], 'materials': e['materials']} for e in els]
    quantities = [{'label': f"{e['code']} · {e['what']}", 'group': f"{KINDS[e['kind']]} · {e['level']}", 'count': 1, 'value': round(e['width_m'], 2), 'unit': 'ml', 'detail': f"{c2(e['width_m'])} × {c2(e['depth_m'])} × {c2(e['height_m'])} · {e['room'] or 'sin local'}"} for e in els]
    lc = collections.Counter(x['family'] for x in loose)
    quantities += [{'label': fam, 'group': 'Mobiliario suelto (referencia)', 'count': c, 'value': c, 'unit': 'u', 'detail': 'no se computa como fijo'} for fam, c in sorted(lc.items())]
    totals = [{'label': 'Placares', 'value': round(sum(front_m2(e) for e in g['PL']), 2), 'unit': 'm²', 'detail': f"{len(g['PL'])} placares · frente ancho × alto · {c2(sum(e['width_m'] for e in g['PL']))} ml"},
              {'label': 'Muebles fijos', 'value': len(g['MU']), 'unit': 'u', 'detail': ', '.join(f"{c} {w}" for w, c in collections.Counter(e['what'] for e in g['MU']).items())},
              {'label': 'Vanitorios', 'value': round(sum(e['width_m'] for e in g['VA']), 2), 'unit': 'ml', 'detail': f"{len(g['VA'])} vanitorios"},
              {'label': 'Mesadas y bajomesadas', 'value': round(sum(e['width_m'] for e in g['ME']), 2), 'unit': 'ml', 'detail': f"{len(g['ME'])} piezas"},
              {'label': 'Lavaderos', 'value': len(g['LV']), 'unit': 'u', 'detail': f"{c2(sum(e['width_m'] for e in g['LV']))} ml"},
              {'label': 'Mamparas', 'value': len(g['MA']), 'unit': 'u', 'detail': 'productos de catálogo'},
              {'label': 'Equipos de cocina', 'value': len(g['EQ']), 'unit': 'u', 'detail': ', '.join(e['what'] for e in g['EQ'])},
              {'label': 'Equipamiento fijo', 'value': len(els), 'unit': 'u', 'detail': f"{len([s for s in out if s['kind'] == 'element'])} fichas"}]
    m = {'title': 'Equipamiento fijo', 'summary': f"{len(els)} elementos fijos: {len(g['PL'])} placares, {len(g['MU'])} muebles fijos, {len(g['VA'])} vanitorios, {len(g['ME'])} mesadas, {len(g['LV'])} lavaderos, {len(g['MA'])} mamparas y {len(g['EQ'])} equipos de cocina. {len(out)} láminas.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': plan['readAt'], 'revision': 'R24', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'Medidas de caja envolvente del modelo (ancho × profundidad × alto). Placares: m² de frente (ancho × alto). Mobiliario suelto listado solo como referencia.',
         'notModeled': ['Muebles de cocina altos y despiece de bajomesadas (solo 3 cajoneras modeladas)', 'Interiores de placares (estantes, barrales, cajones)', 'Herrajes, materiales y terminaciones (las familias in situ no tienen material)', 'Bomba de pileta Grundfos: se documenta con Pileta'],
         'decisions': ['Fijo = familias in situ de carpintería + mamparas + equipos de cocina; el resto es mobiliario suelto (referencia).', 'Artefactos sanitarios quedan en Sanitarias; puertas del ascensor fuera del rubro.',
                       'Ficha por pieza de carpintería (planta, alzado frontal, axonométrica); mamparas y equipos solo en plantas.', 'Códigos PL/MU/VA/ME/LV/MA/EQ solo como anotación (no escritos en Mark).'],
         'questions': ['¿Las mesas de luz y muebles TV in situ son de obra / carpintería fija? Hoy se cuentan como fijos.', '¿Qué muebles de cocina faltan (alacenas, columnas) y en qué material?', '¿Material y terminación de placares y vanitorios (melamina, laqueado, madera)?', '¿Escribimos los códigos de equipamiento en el modelo (Mark)?']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
