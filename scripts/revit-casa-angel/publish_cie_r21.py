"""Publish Cielorrasos to public/casa-angel/rubros/cielorrasos/manifest.json (web contract lib/rubros.ts)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'cielorrasos'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'TC': 'Tipos de cielorraso', 'CE': 'Cielorrasos (piezas por nivel)'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('cie-*.json')):
        if f.name in ('cie-request.json', 'cie-elements.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'CIE-00', s['number'].startswith('CIE-F'), s['number']))


def index_columns(d):
    t = d['types']; r = d['rooms']
    comp = [f"{x['code']} {x['desc'][:34]}: {c2(x['area_m2'])} m²" for x in t] + [f"Total modelado: {c2(sum(x['area_m2'] for x in t))} m² en {len(d['ceilings'])} piezas"]
    for st in ['con cielorraso', 'parcial', 'sin cielorraso modelado']:
        rs = [x for x in r if x['status'] == st]; comp.append(f"Locales {st}: {len(rs)} ({c2(sum(x['area_m2'] for x in rs))} m²)")
    crit = ['TC: tipo de cielorraso del modelo; CE: cada pieza por nivel.', 'Cobertura por local: vertical desde el centro del local;', '"parcial" = hay cielorraso que cubre parte del local.', 'Altura = cara inferior sobre el nivel.', 'Códigos solo como anotación (no en Mark).']
    falt = ['15 locales sin cielorraso modelado (PE completo).', 'TC-03 "Plain": tipo genérico (perfilería + placa).', 'Buñas, tapas de inspección, cajones y gargantas.', 'Pintura de cielorrasos.']
    return [{'title': 'Criterios', 'lines': crit}, {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['CIE-00  Índice'] + sorted(s['number'] for s in records())}, {'title': 'No modelado / a definir', 'lines': falt}]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    d = read(OUT / 'ceil-plan.json')
    if a.index_columns: print(json.dumps(index_columns(d), ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R21', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'cie-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    cc = {str(c['id']): c for c in d['ceilings']}; rr = {str(r['id']): r for r in d['rooms']}
    proj = {str(p['id']): p for p in read(OUT / 'cie-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r21-{n}.pdf'; assert src.exists(), n
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
                els = []
                for r in proj.get(str(v['id']), {}).get('elements', []):
                    k = r['elementId']
                    if k in cc: els.append({'code': cc[k]['code'], 'elementId': k, 'label': cc[k]['label'], 'box': [round(x, 4) for x in r['box']]})
                    elif k in rr: els.append({'code': rr[k]['ceiling'] or (rr[k]['partial'][0] if rr[k]['partial'] else None), 'elementId': k, 'room': True, 'label': f"{rr[k]['number']} · {rr[k]['name']} · {rr[k]['status']}", 'box': [round(x, 4) for x in r['box']]})
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'),
                    'elementKind': s.get('elementKind'), 'note': None, 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    t = d['types']; ce = d['ceilings']; rooms = d['rooms']
    codes = [{'code': x['code'], 'kind': 'TC', 'label': x['label'], 'status': ('Tipo genérico · ' if x['generic'] else '') + 'Capas: ' + x['layerText'], 'area_m2': x['area_m2'], 'type': x['type'], 'layers': x['layers']} for x in t]
    codes += [{'code': x['code'], 'kind': 'CE', 'label': x['label'], 'status': x['type'], 'elementId': str(x['id']), 'typeCode': x['typeCode'], 'level': x['level'], 'area_m2': round(x['area_m2'], 2), 'height_m': round(x['height_m'], 2), 'perimeter_m': round(x['perimeter_m'] or 0, 2)} for x in ce]
    quantities = [{'label': f"{x['code']} · {x['desc']}", 'group': 'Tipos de cielorraso', 'count': x['count'], 'value': x['area_m2'], 'unit': 'm²', 'detail': x['layerText']} for x in t]
    quantities += [{'label': f"{x['number']} · {x['name']}", 'group': f"Locales · {x['level']}", 'count': 1, 'value': x['area_m2'], 'unit': 'm²', 'detail': x['status'] + (f" ({x['ceiling']})" if x['ceiling'] else (f" ({', '.join(x['partial'])})" if x['partial'] else ''))} for x in rooms]
    miss = [x for x in rooms if x['status'] == 'sin cielorraso modelado']; part = [x for x in rooms if x['status'] == 'parcial']
    totals = [{'label': x['desc'], 'value': x['area_m2'], 'unit': 'm²', 'detail': x['code']} for x in t]
    totals += [{'label': 'Locales sin cielorraso modelado', 'value': round(sum(x['area_m2'] for x in miss), 2), 'unit': 'm²', 'detail': f"{len(miss)} locales"},
               {'label': 'Locales con cielorraso parcial', 'value': round(sum(x['area_m2'] for x in part), 2), 'unit': 'm²', 'detail': f"{len(part)} locales"},
               {'label': 'Cielorrasos modelados', 'value': round(sum(x['area_m2'] for x in t), 2), 'unit': 'm²', 'detail': f"{len(ce)} piezas · {len(t)} tipos"}]
    m = {'title': 'Cielorrasos', 'summary': f"{len(ce)} cielorrasos ({c2(sum(x['area_m2'] for x in t))} m²) en {len(t)} tipos; {len([x for x in rooms if x['ceiling']])} locales con cielorraso, {len(part)} parciales y {len(miss)} sin cielorraso modelado. {len(out)} láminas.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': d['readAt'], 'revision': 'R21', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'm² según Revit (cara inferior). La cobertura por local se toma en el centro del local; "parcial" = hay cielorraso que cubre más del 10 % del local sin llegar al centro.',
         'notModeled': [f"{len(miss)} locales sin cielorraso modelado (incluye toda la planta Entrepiso)", 'TC-03 "Plain" es un tipo genérico (perfilería 45 + placa 12 mm)', 'Buñas, tapas de inspección, cajones y gargantas', 'Pintura de cielorrasos'],
         'decisions': ['Cielorrasos documentados en planta de cielorrasos (vista desde abajo) por nivel.', 'Códigos TC/CE solo como anotación (no escritos en Mark).'],
         'questions': ['¿Qué cielorraso llevan los locales sin cielorraso modelado (suspendido de placa, aplicado bajo losa, losa vista)?', '¿TC-03 ("Plain", planta alta) es Durlock ST como en PB? Hoy es un tipo genérico.', '¿Hay cajones, gargantas o buñas perimetrales a documentar?', '¿Escribimos los códigos TC/CE en el modelo (Mark)?']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
