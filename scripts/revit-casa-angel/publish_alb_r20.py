"""Publish Albañilería to public/casa-angel/rubros/albanileria/manifest.json (web contract lib/rubros.ts)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'albanileria'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'TM': 'Tipos de muro / tabique', 'AB': 'Muros y tabiques no estructurales'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('alb-*.json')):
        if f.name in ('alb-request.json', 'alb-elements.json', 'alb-plan.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'ALB-00', s['number'].startswith('ALB-F'), s['number']))


def index_columns(d):
    t = d['types']
    comp = [f"{x['code']} {x['type'][:24]}: {c2(x['area_m2'])} m² · {c2(x['length_m'])} ml" for x in t]
    comp.append(f"Total: {c2(sum(x['area_m2'] for x in t))} m² · {len(d['walls'])} muros")
    dur = [x for x in t if x['type'].startswith('W11')]
    comp.append(f"Durlock: {c2(sum(x['area_m2'] for x in dur))} m² de tabique")
    crit = ['TM: tipo de muro del modelo; AB: cada muro, por nivel.', 'Muros de hormigón (MH) y encadenados: ver Estructura.', 'Muros cortina, portón y "Puerta Arco": ver Aberturas.', 'Códigos solo como anotación (no en Mark).']
    falt = ['Mampostería con una sola capa genérica (pintura):', 'definir ladrillo/bloque, revoques y terminaciones.', 'Dinteles, refuerzos y encuentros con estructura.', 'Aislaciones en muros de fachada.']
    return [{'title': 'Criterios', 'lines': crit}, {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['ALB-00  Índice'] + sorted(s['number'] for s in records())}, {'title': 'No modelado / a definir', 'lines': falt}]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    d = read(OUT / 'alb-plan.json')
    if a.index_columns: print(json.dumps(index_columns(d), ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R20', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'alb-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    wcode = {str(w['id']): w for w in d['walls']}
    proj = {str(p['id']): p for p in read(OUT / 'alb-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r20-{n}.pdf'; assert src.exists(), n
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
                              'elements': [{'code': (wcode.get(r['elementId']) or {}).get('code'), 'elementId': r['elementId'], 'label': (wcode.get(r['elementId']) or {}).get('label'), 'box': [round(x, 4) for x in r['box']]} for r in rows]})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'),
                    'elementKind': s.get('elementKind'), 'note': 'Corte de muro con capas del tipo del modelo.' if s.get('kind') == 'element' else None,
                    'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    t = d['types']; w = d['walls']
    codes = [{'code': x['code'], 'kind': 'TM', 'label': x['label'], 'status': ('Composición genérica · ' if x['generic'] else '') + 'Capas: ' + x['layerText'], 'area_m2': x['area_m2'], 'length_m': x['length_m'], 'volume_m3': x['volume_m3'], 'thickness_m': x['thickness_m'], 'type': x['type'], 'layers': x['layers']} for x in t]
    codes += [{'code': x['code'], 'kind': 'AB', 'label': x['label'], 'status': x['status'], 'elementId': str(x['id']), 'typeCode': x['typeCode'], 'level': x['level'],
               'length_m': round(x['length_m'] or 0, 3), 'height_m': round(x['height_m'] or 0, 3), 'area_m2': round(x['area_m2'] or 0, 2), 'volume_m3': round(x['volume_m3'] or 0, 3)} for x in w]
    quantities = [{'label': f"{x['code']} · {x['type']}", 'group': 'Tipos de muro', 'count': x['count'], 'value': x['area_m2'], 'unit': 'm²', 'detail': f"{c2(x['length_m'])} ml · {c2(x['volume_m3'])} m³ · {x['desc']}"} for x in t]
    for lv in ['PB', 'PA', 'PE']:
        ws = [x for x in w if x['levelCode'] == lv]
        if ws: quantities.append({'label': f'Muros {lv}', 'group': 'Por nivel', 'count': len(ws), 'value': round(sum(x['area_m2'] or 0 for x in ws), 2), 'unit': 'm²', 'detail': f"{c2(sum(x['length_m'] or 0 for x in ws))} ml"})
    dur = [x for x in t if x['type'].startswith('W11')]; mam = [x for x in t if x['code'] in ('TM-01', 'TM-02', 'TM-03', 'TM-04')]; fac = [x for x in t if x['code'] in ('TM-05', 'TM-06')]
    totals = [{'label': 'Mampostería y tabiques interiores', 'value': round(sum(x['area_m2'] for x in mam), 2), 'unit': 'm²', 'detail': 'TM-01 a TM-04'},
              {'label': 'Durlock (W111 + W112)', 'value': round(sum(x['area_m2'] for x in dur), 2), 'unit': 'm²', 'detail': 'placas Knauf ST/RH + montantes 70'},
              {'label': 'Muros de fachada', 'value': round(sum(x['area_m2'] for x in fac), 2), 'unit': 'm²', 'detail': 'TM-05, TM-06'},
              {'label': 'Muros y tabiques (todos)', 'value': round(sum(x['area_m2'] for x in t), 2), 'unit': 'm²', 'detail': f"{len(w)} muros · {len(t)} tipos"}]
    m = {'title': 'Albañilería', 'summary': f"{len(w)} muros y tabiques no estructurales en {len(t)} tipos ({c2(sum(x['area_m2'] for x in t))} m²). {len(out)} láminas: plantas por nivel y fichas por tipo con corte de capas.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': read(OUT / 'inventory-structure.json')['readAt'], 'revision': 'R20', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'Superficie de muro según Revit (una cara); para revoques/pintura multiplicar por caras a terminar. Durlock: placas = superficie × placas por cara × 2.',
         'notModeled': ['Composición real de la mampostería (los tipos tienen una sola capa "pintura")', 'Revoques, dinteles, refuerzos y encuentros con la estructura', 'Aislaciones de muros de fachada'],
         'decisions': ['Muros de hormigón y encadenados se documentan en Estructura; muros cortina, portón y "Puerta Arco" en Aberturas.', 'Códigos TM/AB solo como anotación (no escritos en Mark).'],
         'questions': ['¿De qué son los muros interiores de 10 y 20 cm (ladrillo hueco, común, bloque)? Hoy son una capa genérica de "pintura".', '¿Qué revoques y terminaciones llevan (grueso + fino, yeso, enduido)?', '¿Los muros de fachada llevan aislación térmica?', '¿Escribimos los códigos TM/AB en el modelo (Mark)?']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
