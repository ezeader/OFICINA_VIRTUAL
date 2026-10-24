"""Publish Pileta to public/casa-angel/rubros/pileta/manifest.json (web contract lib/rubros.ts)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'pileta'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'VA': 'Muros del vaso', 'FO': 'Fondo', 'BO': 'Borde / solárium', 'AG': 'Agua'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('pil-*.json')):
        if f.name in ('pil-request.json', 'pil-elements.json', 'pil-plan.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'PIL-00', s['number'].startswith('PIL-F'), s['number']))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    els = read(OUT / 'pil-plan.json')['elements']; k = lambda x: [e for e in els if e['kind'] == x]
    va, fo, bo, ag = k('VA'), k('FO'), k('BO'), k('AG')
    if a.index_columns:
        comp = [e['label'] for e in els] + [f"Revestimiento venecitas: {c2(sum(e['area_m2'] for e in va) + sum(e['area_m2'] for e in fo))} m² (muros + fondo)", f"Hormigón/mampostería del vaso: {c2(sum(e['volume_m3'] for e in va))} m³"]
        cols = [{'title': 'Criterios', 'lines': ['VA: muros del vaso; FO: fondo; BO: borde/solárium;', 'AG: volumen de agua (modelo genérico).', 'Códigos solo como anotación (no en Mark).']},
                {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['PIL-00  Índice'] + sorted(s['number'] for s in records())},
                {'title': 'No modelado / a definir', 'lines': ['Equipo de filtrado y bomba, skimmers, retornos.', 'Cañerías e iluminación subacuática.', 'Estructura real del vaso (hoy muro de "venecitas" 20 cm).', 'Escalera / acceso al agua y vereda perimetral.']}]
        print(json.dumps(cols, ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R22', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'pil-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    code = {str(e['id']): e for e in els}; proj = {str(p['id']): p for p in read(OUT / 'pil-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r22-{n}.pdf'; assert src.exists(), n
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
    codes = [{'code': e['code'], 'kind': e['kind'], 'label': e['label'], 'status': e['status'], 'elementId': str(e['id']), 'length_m': e.get('length_m'), 'area_m2': e.get('area_m2'), 'volume_m3': e.get('volume_m3')} for e in els]
    quantities = [{'label': e['code'], 'group': KINDS[e['kind']], 'count': 1, 'value': round(e.get('area_m2') or e.get('volume_m3') or 0, 2), 'unit': 'm²' if e.get('area_m2') else 'm³', 'detail': e['label']} for e in els]
    ven = sum(e['area_m2'] for e in va) + sum(e['area_m2'] for e in fo)
    totals = [{'label': 'Muros del vaso', 'value': round(sum(e['area_m2'] for e in va), 2), 'unit': 'm²', 'detail': f"{len(va)} muros · {c2(sum(e['volume_m3'] for e in va))} m³"},
              {'label': 'Fondo', 'value': round(sum(e['area_m2'] for e in fo), 2), 'unit': 'm²', 'detail': 'venecitas 5 cm + base 10 cm'},
              {'label': 'Borde / solárium', 'value': round(sum(e['area_m2'] for e in bo), 2), 'unit': 'm²', 'detail': '"Piso Pileta" 15 cm'},
              {'label': 'Agua', 'value': round(sum(e['volume_m3'] for e in ag), 2), 'unit': 'm³', 'detail': 'volumen modelado'},
              {'label': 'Revestimiento venecitas (muros + fondo)', 'value': round(ven, 2), 'unit': 'm²', 'detail': 'cara interior estimada con área de Revit'}]
    m = {'title': 'Pileta', 'summary': f"Vaso de {c2(max(e['length_m'] for e in va))} × {c2(min(e['length_m'] for e in va))} m, 2,00 m de alto de muro; {c2(sum(e['volume_m3'] for e in ag))} m³ de agua; {c2(ven)} m² de venecitas. {len(out)} láminas.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': read(OUT / 'pil-plan.json')['readAt'], 'revision': 'R22', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'Áreas según Revit (una cara por muro). Volumen de agua del modelo genérico "Agua pileta".',
         'notModeled': ['Equipo de filtrado, bomba, skimmers y retornos', 'Cañerías e iluminación subacuática', 'Estructura real del vaso (muros modelados como "venecitas" 20 cm)', 'Escalera / acceso al agua'],
         'decisions': ['Pileta documentada como un vaso: planta, cortes y ficha.', 'Códigos VA/FO/BO/AG solo como anotación (no escritos en Mark).'],
         'questions': ['¿De qué es la estructura del vaso (hormigón armado, bloque)? Hoy es un muro de "venecitas" de 20 cm.', '¿Qué equipo de filtrado y climatización de pileta lleva (si lleva)?', '¿Profundidad constante de 2,00 m o con pendiente / escalón?', '¿Escribimos los códigos de pileta en el modelo (Mark)?']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
