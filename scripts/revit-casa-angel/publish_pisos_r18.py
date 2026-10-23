"""Publish Pisos y zócalos to public/casa-angel/rubros/pisos/manifest.json (web contract lib/rubros.ts).
--index-columns : print the EST-like index columns JSON for the Revit index job
--request       : projection request for the read-only job
default         : assets + manifest"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'pisos'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'TP': 'Tipos de piso (paquetes)', 'PI': 'Piezas de piso por nivel', 'ZO': 'Zócalos modelados'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('pis-*.json')):
        if f.name in ('pis-request.json', 'pis-elements.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'PIS-00', s['number'].startswith('PIS-F'), s['number']))


def index_columns(d):
    types = d['types']; rooms = d['rooms']
    comp = [f"{t['code']} {t['type'].split(' /')[0]} ({t['finish']}): {c2(t['area_m2'])} m²" for t in types]
    comp.append(f"Total pisos: {c2(sum(t['area_m2'] for t in types))} m²")
    zmod = sum(z['length_m'] for z in d['skirtings']); zreq = sum(r['perimeter_m'] for r in rooms)
    comp += [f"Zócalos modelados (ZO): {c2(zmod)} ml en {len(d['skirtings'])} tramos", f"Perímetro de locales (zócalo a computar): {c2(zreq)} ml (sin descontar vanos)"]
    crit = ['TP: tipo de piso = tipo de piso del modelo (paquete completo).', 'Terminación = capa superior del paquete.', 'PI: cada elemento piso, por nivel. ZO: zócalos modelados.',
            'Local → tipo: vertical por el centro del local.', 'Códigos solo como anotación (no escritos en Mark).']
    falt = ['Terminación de piso y zócalo no cargadas en los locales.', 'Zócalos: solo 5 tramos (25,6 ml) en PB.', 'Baños con vinílico (TP-01/04/05) y Baño PA', 'con alfombra (TP-02): verificar.',
            'Hall sobre "Base Acceso" (hormigón + 1 m de césped): verificar.', 'Umbrales, solias y juntas de dilatación.']
    return [{'title': 'Criterios', 'lines': crit}, {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['PIS-00  Índice'] + sorted(s['number'] for s in records())}, {'title': 'No modelado / a verificar', 'lines': falt}]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    d = read(OUT / 'floors-plan.json')
    if a.index_columns: print(json.dumps(index_columns(d), ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R18', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'pis-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    code = {str(p['id']): p['code'] for p in d['pieces']}; code.update({str(z['id']): z['code'] for z in d['skirtings']})
    room = {str(r['id']): r for r in d['rooms']}
    proj = {str(p['id']): p for p in read(OUT / 'pis-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r18-{n}.pdf'; assert src.exists(), n
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
                els = []
                for r in rows:
                    rid = r['elementId']
                    if rid in room: els.append({'code': room[rid]['typeCode'], 'elementId': rid, 'box': [round(x, 4) for x in r['box']], 'label': f"{room[rid]['number']} · {room[rid]['name']} · {room[rid]['label']}", 'room': True})
                    else: els.append({'code': code.get(rid), 'elementId': rid, 'box': [round(x, 4) for x in r['box']]})
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'),
                    'elementKind': s.get('elementKind'), 'note': 'Corte de paquete a 1:5 con capas y espesores del tipo del modelo.' if s.get('kind') == 'element' else None,
                    'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    types = d['types']; rooms = d['rooms']
    codes = [{'code': t['code'], 'kind': 'TP', 'label': t['label'], 'status': 'Paquete: ' + t['layerText'], 'area_m2': t['area_m2'], 'thickness_m': t['thickness_m'], 'finish': t['finish'], 'type': t['type'], 'layers': t['layers']} for t in types]
    codes += [{'code': p['code'], 'kind': 'PI', 'label': p['label'], 'status': f"{p['type']} · {p['finish']}", 'elementId': str(p['id']), 'area_m2': round(p['area_m2'], 2), 'level': p['level'], 'typeCode': p['typeCode']} for p in d['pieces']]
    codes += [{'code': z['code'], 'kind': 'ZO', 'label': z['label'], 'status': 'Zócalo modelado (Wall Sweep "Zocalo")', 'elementId': str(z['id']), 'length_m': round(z['length_m'], 3)} for z in d['skirtings']]
    quantities = [{'label': f"{t['code']} · {t['type'].split(' /')[0]}", 'group': 'Tipos de piso', 'count': t['count'], 'value': t['area_m2'], 'unit': 'm²', 'detail': f"{t['finish']} · {', '.join(t['levels'])}"} for t in types]
    quantities += [{'label': f"{r['number']} · {r['name']}", 'group': f"Locales · {r['level']}", 'count': 1, 'value': r['area_m2'], 'unit': 'm²', 'detail': f"{r['typeCode']} {r['finish']} · perímetro {c2(r['perimeter_m'])} ml"} for r in rooms]
    quantities += [{'label': z['code'], 'group': 'Zócalos modelados', 'count': 1, 'value': round(z['length_m'], 2), 'unit': 'ml', 'detail': 'PB'} for z in d['skirtings']]
    fin = {}
    for t in types: fin[t['finish']] = fin.get(t['finish'], 0) + t['area_m2']
    zmod = sum(z['length_m'] for z in d['skirtings']); zreq = sum(r['perimeter_m'] for r in rooms)
    totals = [{'label': f'Piso {k}', 'value': round(v, 2), 'unit': 'm²', 'detail': 'por terminación'} for k, v in sorted(fin.items(), key=lambda x: -x[1])]
    totals += [{'label': 'Zócalos modelados', 'value': round(zmod, 2), 'unit': 'ml', 'detail': f"{len(d['skirtings'])} tramos"},
               {'label': 'Zócalo a computar (perímetro de locales)', 'value': round(zreq, 2), 'unit': 'ml', 'detail': 'sin descontar vanos de puertas'},
               {'label': 'Pisos (todos los tipos)', 'value': round(sum(t['area_m2'] for t in types), 2), 'unit': 'm²', 'detail': f"{len(types)} tipos · {len(d['pieces'])} piezas"}]
    m = {'title': 'Pisos y zócalos', 'summary': f"{len(types)} tipos de piso ({c2(sum(t['area_m2'] for t in types))} m²) en {len(d['pieces'])} piezas; los 30 locales tienen tipo de piso asignado. Zócalos: {c2(zmod)} ml modelados de {c2(zreq)} ml de perímetro. {len(out)} láminas: plantas por nivel, fichas por tipo con corte de paquete.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': d['readAt'], 'revision': 'R18', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'm² de cada pieza según Revit (cara superior). Tipo de piso por local tomado en el centro del local. Zócalo a computar = perímetro de local (no descuenta puertas).',
         'notModeled': ['Terminación de piso y de zócalo no cargadas en los locales (parámetros vacíos)', 'Zócalos solo en 5 tramos de PB (25,6 ml)', 'Umbrales, solias y juntas', 'Pisos de baños específicos (cerámico/porcelanato): hoy los baños usan vinílico o alfombra'],
         'decisions': ['Códigos TP/PI/ZO solo como anotación (no escritos en Mark).', 'Cada tipo de piso del modelo es un TP con ficha y corte de paquete a 1:5.'],
         'questions': ['¿Los baños de PB van con piso vinílico (TP-01, TP-04, TP-05)? ¿Y el Baño PA con alfombra (TP-02)? Parece un tipo de piso provisorio.',
                       '¿El Hall está bien sobre "Base Acceso" (hormigón 20 cm + 1 m de césped)? ¿Cuál es su piso terminado?',
                       '¿Qué zócalo lleva cada local (material y altura)? Solo hay 5 tramos modelados.',
                       '¿Escribimos los códigos TP/PI en el modelo (Mark)?']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
