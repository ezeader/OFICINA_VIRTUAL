"""R32 Climatización etapa 1: publish CLI-P-PB/PA/PE + new CLI-00 (Casa-Angel-DOC-Climatizacion.rvt) into
public/casa-angel/rubros/climatizacion/manifest.json. R19 sheets stay with note "R19 · previo"; CI codes get `collector`; same budget ids."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'climatizacion'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592


def c2(v): return ('%.2f' % v).replace('.', ',')


def circuits():
    return [c for fn in ('cli32-plans.json',) if (OUT / fn).exists() for s in read(OUT / fn)['sheets'] for c in s.get('circuits', [])]


def index_columns():
    rec = read(OUT / 'cli32-plans.json')['sheets']; cs = circuits()
    lv = [f"{s['number']}: {len(s['circuits'])} circuitos · {c2(s['totals']['length_m'])} ml · {c2(s['totals']['area_m2'])} m² · distr. {c2(s['totals']['distribution_m'])} ml" for s in rec]
    by = {}
    for c in cs: by.setdefault(c['collector'], []).append(c['code'] + ('*' if c['method'] != 'conectividad' else ''))
    co = [f"{k}: {len(v)} circuitos" for k, v in sorted(by.items())] + [f"  {k}: " + ', '.join(v) for k, v in sorted(by.items())] + ['* asignado por cercanía']
    inc = [c['code'] for c in cs if c['status'] != 'completo']
    return [{'title': 'Láminas R32 (etapas 1 y 2)', 'lines': ['CLI-00  Índice', 'CLI-P-PB  Planta Baja · serpentines', 'CLI-P-PA  Planta Alta · serpentines', 'CLI-P-PE  Entrepiso · serpentines', 'CLI-CO-N  Colector Norte · planta, alzado, salidas', 'CLI-CO-S  Colector Sur · planta, alzado, salidas',
                                                     'R19: plantas y fichas previas (las fichas por local se reemplazan en la etapa 3)']},
            {'title': 'Por nivel', 'lines': lv}, {'title': 'Por colector', 'lines': co},
            {'title': 'Notas', 'lines': ['Densidad completa ≥ 4 m/m².', 'Incompletos: ' + (', '.join(inc) or 'ninguno'), 'TE-05 sin local; TE-04 y TE-09 sin nivel en el modelo.', 'Bomba de calor: no modelada.']}]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    if a.index_columns: print(json.dumps(index_columns(), ensure_ascii=True)); return
    sheets = read(OUT / 'cli32-plans.json')['sheets'] + sum((read(OUT / fn)['sheets'] for fn in ('cli32-collectors.json', 'cli32-index.json') if (OUT / fn).exists()), [])
    if a.request:
        views = [{'rev': 'R32', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views'] if v['elements']]
        (OUT / 'cli32-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; m = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    proj = {str(p['id']): p for p in read(OUT / 'cli32-elements.json')}
    cs = circuits(); room2ci = {str(c['roomId']): c['code'] for c in cs}
    plan = {x['code']: x for x in read(OUT / 'hvac-plan.json')['elements']}
    room2ci.update({str(x['id']): x['code'] for x in plan.values() if x['kind'] in ('CO', 'GA')})
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r32-{n}.pdf'; assert src.exists(), n
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
                    k = room2ci.get(r['elementId'])
                    if k: x = plan[k]; els.append(dict({'code': k, 'elementId': r['elementId'], 'label': x['label'], 'box': [round(q, 4) for q in r['box']]}, **({'room': True} if x['kind'] == 'CI' else {})))
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        new.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'), 'elementKind': s.get('elementKind'), 'outlets': s.get('outlets'),
                    'note': 'R32 · archivo Casa-Angel-DOC-Climatizacion.rvt', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz',
                    'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    nums = [x['number'] for x in new]
    kept = [s for s in m['sheets'] if s['number'] not in nums]
    for s in kept:
        s['note'] = 'R19 · previo (se reemplaza en la etapa 3)'
        if s['number'] in ('CLI-PB-01', 'CLI-PA-01', 'CLI-PE-01') and not str(s.get('sector', '')).startswith('R19 previo'): s['sector'] = 'R19 previo · ' + (s.get('level') or '')
    m['sheets'] = sorted(new, key=lambda s: (s['number'] != 'CLI-00', s['number'])) + kept
    by = {c['code']: c for c in cs}
    for c in m['codes']:
        if c['code'] in by: c.update(collector=by[c['code']]['collector'], collectorMethod=by[c['code']]['method'])
    m['revision'] = 'R32'
    m['summary'] = f"Climatización R32 (etapas 1 y 2): detalle de los colectores CLI-CO-N / CLI-CO-S (planta 1:20, alzado con gabinete, esquema de salidas S01..) y plantas CLI-P-PB/PA/PE con el trazado de cada serpentín por circuito y el colector que lo alimenta ({sum(1 for c in cs if c['collector'] == 'CO-N')} circuitos a CO-N, {sum(1 for c in cs if c['collector'] == 'CO-S')} a CO-S; {sum(1 for c in cs if c['method'] != 'conectividad')} asignados por cercanía). Láminas R19 como previas."
    m.setdefault('decisions', [])
    t = 'R32 etapa 1: documentación en Casa-Angel-DOC-Climatizacion.rvt; colector de cada circuito por conectividad de tubos desde CO-N / CO-S (cercanía si no hay camino). Etapas 2 (colectores) y 3 (fichas por local) después del OK del usuario.'
    if t not in m['decisions']: m['decisions'].append(t)
    t2 = 'R32 etapa 2: una lámina por colector (CLI-CO-N, CLI-CO-S); salidas S01.. ordenadas por el conector del colector; el gabinete Hidroflex no tiene geometría en corte, el alzado dibuja su contorno (0,80 × 0,50) y las barras de ida y retorno.'
    if t2 not in m['decisions']: m['decisions'].append(t2)
    if 'budget' in m: m['budget']['revision'] = 'R32'
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': nums, 'collectors': {k: [c['code'] for c in cs if c['collector'] == k] for k in ('CO-N', 'CO-S')}}, ensure_ascii=False))


if __name__ == '__main__': main()
