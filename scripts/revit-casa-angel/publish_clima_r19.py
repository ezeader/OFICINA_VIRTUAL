"""Publish Climatización to public/casa-angel/rubros/climatizacion/manifest.json (web contract lib/rubros.ts).
The earlier inventory manifest (public/casa-angel/climatizacion/manifest.json) is left untouched."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'climatizacion'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'CI': 'Circuitos de piso radiante por local', 'DI': 'Distribución y montantes', 'CO': 'Colectores', 'GA': 'Gabinetes de colector', 'TE': 'Cronotermostatos', 'BO': 'Bomba (genérica)'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('cli-*.json')):
        if f.name in ('cli-request.json', 'cli-elements.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'CLI-00', s['number'].startswith('CLI-F'), s['number']))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); a = ap.parse_args()
    sheets = records(); plan = read(OUT / 'hvac-plan.json'); els = plan['elements']
    if a.request:
        views = [{'rev': 'R19', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'cli-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    code = {str(e['roomId']): e for e in els if e['kind'] == 'CI'}; code.update({str(e['id']): e for e in els if e.get('id')})
    proj = {str(p['id']): p for p in read(OUT / 'cli-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r19-{n}.pdf'; assert src.exists(), n
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
                    'elementKind': s.get('elementKind'), 'note': 'Serpentín según el modelo; circuito por salida de colector a definir.' if s.get('elementKind') == 'CI' else None,
                    'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    k = lambda x: [e for e in els if e['kind'] == x]
    codes = [{'code': e['code'], 'kind': e['kind'], 'label': e['label'], 'status': e['status'], 'elementId': str(e.get('id') or e.get('roomId') or ''), 'length_m': e.get('length_m'), 'area_m2': e.get('area_m2'),
              'room': e.get('room'), 'level': e.get('level'), 'density_m_per_m2': e.get('density'), 'supply_m': e.get('supply_m'), 'return_m': e.get('return_m')} for e in els]
    quantities = [{'label': f"{e['code']} · {e['room']}", 'group': f"Circuitos · {e['levelCode']}", 'count': len(e['pipeIds']), 'value': e['length_m'], 'unit': 'ml',
                   'detail': f"{c2(e['area_m2'])} m² · {c2(e['density'])} m/m² · {e['status']}"} for e in k('CI')]
    quantities += [{'label': e['code'], 'group': 'Distribución', 'count': len(e['pipeIds']), 'value': e['length_m'], 'unit': 'ml', 'detail': e['status']} for e in k('DI')]
    quantities += [{'label': e['code'], 'group': KINDS[e['kind']], 'count': 1, 'value': 1, 'unit': 'u.', 'detail': e['label']} for e in k('CO') + k('GA') + k('TE') + k('BO')]
    tot = sum(e['length_m'] for e in k('CI') + k('DI'))
    totals = [{'label': f'Serpentín {lv}', 'value': round(sum(e['length_m'] for e in k('CI') if e['levelCode'] == lv), 2), 'unit': 'ml', 'detail': f"{len([e for e in k('CI') if e['levelCode'] == lv])} locales"} for lv in ['PB', 'PA', 'PE']]
    totals += [{'label': 'Distribución y montantes', 'value': round(sum(e['length_m'] for e in k('DI')), 2), 'unit': 'ml', 'detail': 'fuera de locales'},
               {'label': 'Colectores / termostatos', 'value': len(k('CO')), 'unit': 'u.', 'detail': f"{len(k('TE'))} cronotermostatos"},
               {'label': 'Tubo PEX Ø20 total', 'value': round(tot, 2), 'unit': 'ml', 'detail': 'mando + retorno'}]
    m = {'title': 'Climatización (piso radiante)', 'summary': f"Piso radiante con {c2(tot)} ml de PEX Ø20 en {len(k('CI'))} locales, colectores Norte y Sur, {len(k('TE'))} cronotermostatos. {len(out)} láminas: plantas de serpentines por nivel, fichas por circuito/local y por colector. Bomba de calor no modelada.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': plan['readAt'], 'revision': 'R19', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'Longitud de serpentín por local = tramos horizontales del nivel dentro del local; densidad de referencia 6,7 m/m² (paso 15 cm). Locales con densidad < 4 m/m² tienen trazado parcial.',
         'notModeled': ['Bomba de calor inverter aire-agua (solo hay una bomba centrífuga genérica)', 'Circuitos por salida de colector: los serpentines están en 4 sistemas de Revit, no uno por circuito', 'Retorno cargado como "Hydronic Supply"', 'Tanque de inercia, vaso de expansión, válvula mezcladora, cabezales electrotérmicos', 'Trazado completo en baños, cuartos de invitados y otros locales de densidad baja'],
         'decisions': ['Un código CI por local (serpentín), DI para distribución; códigos solo como anotación.', 'El inventario anterior (climatizacion/manifest.json) se mantiene; este manifest es el de la mesa de rubros.'],
         'questions': ['¿Marca, modelo y potencia de la bomba de calor? ¿Dónde va la unidad exterior?', '¿Los locales con densidad baja (cuartos de invitados, baños, Living, Cava…) llevan serpentín completo? Hoy el trazado es parcial.', '¿Qué salida del colector alimenta cada local? Así armamos un circuito por salida.', '¿Corregimos el sistema de los retornos a "Hydronic Return" en el modelo? (cambio de parámetros MEP, requiere OK)']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
