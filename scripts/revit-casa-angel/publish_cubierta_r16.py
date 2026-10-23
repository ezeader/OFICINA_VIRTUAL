"""Publish the Cubierta sheets to public/casa-angel/rubros/cubierta/manifest.json (web contract lib/rubros.ts).

--request : write openings-r4/cub-request.json for the read-only projection job
default   : copy PDFs, write svg.gz/PNGs, build the manifest
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'cubierta'; BASE = f'/casa-angel/rubros/{KEY}/'
PT_PER_FT = 2383.94 / 2.7592
KINDS = {'CU': 'Techos (faldones de tejas)', 'VC': 'Vigas de cubierta 6×20', 'VP': 'Piezas de madera 3×10', 'CR': 'Correas 1,5×5', 'FA': 'Fascias / zinguería de borde', 'CA': 'Canaletas', 'AL': 'Aleros metálicos'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('cub-*.json')):
        if f.name in ('cub-request.json', 'cub-elements.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'CUB-00', s['number'].startswith('CUB-F'), s['number']))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); ap.add_argument('--request', action='store_true'); a = ap.parse_args()
    sheets = records()
    if a.request:
        views = [{'rev': 'R16', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'cub-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    plan = read(OUT / 'roof-plan.json')['elements']; code = {str(e['id']): e['code'] for e in plan}
    proj = {str(p['id']): p for p in read(OUT / 'cub-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r16-{n}.pdf'; assert src.exists(), n
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
                              'tags': v['tags'], 'dimensions': [{'label': d['label'], 'values_m': d['values_m'], 'associative': d.get('associative')} for d in v['dims']],
                              'elements': [{'code': code.get(r['elementId']), 'elementId': r['elementId'], 'box': [round(x, 4) for x in r['box']]} for r in rows]})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'),
                    'elementId': s.get('elementId'), 'elementKind': s.get('elementKind'), 'note': 'Membrana, aislación y zinguería completa: no modelado / a definir.' if s.get('kind') == 'element' else None,
                    'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    k = lambda x: [e for e in plan if e['kind'] == x]
    codes = [{'code': e['code'], 'kind': e['kind'], 'label': e['label'], 'status': e['status'], 'elementId': str(e['id']), 'roof': e.get('roof'),
              'length_m': round(e['length_m'], 3) if e.get('length_m') else None, 'area_m2': round(e['area_m2'], 2) if e.get('area_m2') else None,
              'volume_m3': round(e['volume_m3'], 4) if e.get('volume_m3') else None, 'slopes_deg': e.get('slopes_deg'), 'aguas': e.get('aguas')} for e in plan]
    quantities = [{'label': e['code'] + ' · techo', 'group': 'Techos (tejas)', 'count': len(e['aguas']), 'value': round(e['area_m2'], 2), 'unit': 'm²', 'detail': 'aguas: ' + '; '.join(f"{c2(x['area_m2'])} m² a {c2(x['slope_deg'])}°" for x in e['aguas'])} for e in k('CU')]
    for x in ['VC', 'VP', 'CR']:
        for roof in ['CU-01', 'CU-02', 'CU-03']:
            rs = [e for e in k(x) if e.get('roof') == roof]
            if rs: quantities.append({'label': f'{KINDS[x]} · {roof}', 'group': 'Estructura de madera', 'count': len(rs), 'value': round(sum(e['length_m'] or 0 for e in rs), 2), 'unit': 'ml', 'detail': f"{c2(sum(e['volume_m3'] or 0 for e in rs))} m³"})
    quantities += [{'label': e['code'], 'group': 'Zinguería', 'count': 1, 'value': round(e['length_m'], 2), 'unit': 'ml', 'detail': KINDS[e['kind']]} for e in k('FA') + k('CA')]
    quantities += [{'label': e['code'], 'group': 'Aleros', 'count': 1, 'value': round(e['area_m2'], 2), 'unit': 'm²', 'detail': 'Alero metálico'} for e in k('AL')]
    wood = sum(e['volume_m3'] or 0 for x in ['VC', 'VP', 'CR'] for e in k(x))
    totals = [{'label': 'Vigas 6×20 (VC)', 'value': round(sum(e['length_m'] for e in k('VC')), 2), 'unit': 'ml', 'detail': f"{len(k('VC'))} piezas"},
              {'label': 'Piezas 3×10 (VP)', 'value': round(sum(e['length_m'] for e in k('VP')), 2), 'unit': 'ml', 'detail': f"{len(k('VP'))} piezas"},
              {'label': 'Correas 1,5×5 (CR)', 'value': round(sum(e['length_m'] for e in k('CR')), 2), 'unit': 'ml', 'detail': f"{len(k('CR'))} piezas"},
              {'label': 'Madera total', 'value': round(wood, 3), 'unit': 'm³', 'detail': 'Kerto LVL (familia del modelo)'},
              {'label': 'Zinguería (fascias + canaletas)', 'value': round(sum(e['length_m'] for e in k('FA') + k('CA')), 2), 'unit': 'ml', 'detail': 'sin bajadas ni cumbreras'},
              {'label': 'Tejas (3 techos)', 'value': round(sum(e['area_m2'] for e in k('CU')), 2), 'unit': 'm²', 'detail': 'superficie inclinada; pendientes 16,8° a 30°'}]
    m = {'title': 'Cubierta', 'summary': f"3 techos de tejas ({c2(totals[-1]['value'])} m²), estructura de madera de {len(k('VC')) + len(k('VP')) + len(k('CR'))} piezas ({c2(wood)} m³), fascias, canaletas y aleros. {len(out)} láminas: planta de techos, estructura, cortes, fichas de techos y de vigas 6×20.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': read(OUT / 'roof-raw.json')['readAt'], 'revision': 'R16', 'kinds': KINDS, 'sheets': out, 'codes': codes,
         'totals': totals, 'quantities': quantities, 'quantityNote': 'Superficies de tejas inclinadas medidas sobre cada agua; madera por longitud de cada pieza; VP y CR tienen código pero no ficha propia (se documentan en CUB-02 y en la ficha de su techo).',
         'notModeled': ['Membrana hidrófuga y aislación térmica (el tipo "Tejas 20mm" solo tiene madera 15 mm + 5 mm)', 'Bajadas pluviales, cumbreras, limatesas y babetas', 'Zinguería completa: solo 2 canaletas (14,2 ml) y 4 fascias', 'Fijaciones y uniones de la estructura de madera', 'CU-02 sin estructura de madera modelada', 'Piezas de madera sin nivel propio (nivel de referencia PE o Techos)'],
         'decisions': ['Códigos CU/VC/VP/CR/FA/CA/AL solo como anotación y en este manifest (no escritos en Mark).', 'Fichas individuales para techos (3) y vigas 6×20 (34); piezas 3×10 y correas en planta CUB-02 y planilla.'],
         'questions': ['¿Qué membrana y aislación lleva la cubierta (tipo y espesor)? Hoy no están modeladas.', '¿La estructura de madera de CU-02 existe o ese techo apoya sobre otra estructura?', '¿Escribimos los códigos de cubierta en el parámetro Mark del modelo (como en Estructura)?', '¿Sección real de las piezas "3×10" y "correas 1,5×5"? Parecen listones/clavaderas más que vigas.']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
