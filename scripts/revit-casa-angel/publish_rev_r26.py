"""Publish Revestimientos (propuesta a confirmar) to public/casa-angel/rubros/revestimientos/manifest.json (web contract lib/rubros.ts)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'revestimientos'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592; M = .3048
KINDS = {'RV': 'Revestimiento de baños y toilettes (0,00–2,40)', 'RF': 'Franja sobre mesada (0,90–1,50)', 'PI': 'Pintura de muros (0,00–2,60)'}
SKIP = ('rev-request.json', 'rev-elements.json', 'rev-plan.json')


def c2(v): return ('%.2f' % v).replace('.', ',')


def clean(s): return s.encode('latin-1', 'backslashreplace').decode('unicode_escape') if isinstance(s, str) and '\\x' in s else s


def records():
    out = []
    for f in sorted(OUT.glob('rev-*.json')):
        if f.name in SKIP: continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'RV-00', s['number'].startswith('RV-F'), s['number']))


def load():
    d = read(OUT / 'rev-plan.json')
    for r in d['rooms']: r['name'] = clean(r['name']); r['level'] = clean(r['level'])
    return d


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    d = load(); rooms = d['rooms']
    rv = [r for r in rooms if r['kind'] == 'RV']; bands = [(r, b) for r in rooms for b in r['bands']]
    T = {'rev': sum(r['rev_m2'] for r in rv), 'band': sum(b['m2'] for _, b in bands), 'paint': sum(r['paint_m2'] for r in rooms)}
    gross_rev = sum(f['revGross_m2'] for r in rv for f in r['faces'])
    if a.index_columns:
        comp = [f"{r['code']} {r['name']}: {c2(r['rev_m2'])} m²" for r in rv] + [f"Revestimiento total: {c2(T['rev'])} m² (bruto {c2(gross_rev)})"]
        comp += [f"{b['code']} {r['name']}: {c2(b['len_m'])} × 0,60 = {c2(b['m2'])} m²" for r, b in bands] + [f"Pintura de muros: {c2(T['paint'])} m² en {len(rooms)} locales"]
        cols = [{'title': 'Hipótesis (propuesta a confirmar)', 'lines': ['Baños y toilettes: revestidos 0,00 a 2,40 m.', 'Cocina y lavadero: franja 0,90 a 1,50 m', 'sobre mesada y lavaderos.', 'Resto de muros: pintura hasta 2,60 m.', 'Fachada: hormigón visto, sin revestimiento.', 'Vanos, muros cortina y arcos descontados.', 'El modelo no se modificó.']},
                {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['RV-00  Índice', 'RV-01..03  Plantas PB / PA / PE'] + sorted(s['number'] for s in records() if s['number'].startswith('RV-F'))},
                {'title': 'A definir', 'lines': ['Material y formato (porcelanato / cerámico).', 'Altura final en baños (2,40 o a cielorraso).', 'Franja de cocina con ventanas sobre mesada.', 'Quincho: franja sobre mesada (no incluida).', 'Pintura: tipo y terminación.']}]
        print(json.dumps(cols, ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R26', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'rev-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    roomby = {str(r['id']): r for r in rooms}; proj = {str(p['id']): p for p in read(OUT / 'rev-elements.json')}
    try: opcode = {str(i['id']): i['code'] for i in json.loads((a.public_dir / 'openings' / 'manifest.json').read_text(encoding='utf-8'))['items']}
    except Exception: opcode = {}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r26-{n}.pdf'; assert src.exists(), n
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
                    k = r['elementId']; box = [round(x, 4) for x in r['box']]
                    if k in roomby:
                        rr = roomby[k]; lab = f"{rr['code']} · {rr['number']} · {rr['name']} · " + (f"revestimiento {c2(rr['rev_m2'])} m²" if rr['kind'] == 'RV' else f"pintura {c2(rr['paint_m2'])} m²" + (f" · franja {c2(rr['band_m2'])} m²" if rr['bands'] else ''))
                        els.append({'code': rr['code'], 'elementId': k, 'room': True, 'label': lab, 'box': box})
                    else:
                        els.append({'code': opcode.get(k), 'elementId': k, 'label': f"Vano {opcode.get(k) or k} (descontado)", 'box': box})
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'),
                    'elementKind': s.get('elementKind'), 'note': 'Propuesta a confirmar', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    loc = lambda r: f"{r['number']} · {r['name']} · {r['levelCode']}"
    codes = []
    for r in rooms:
        faces = [{'face': f'C{k + 1}', 'length_m': round(f['len'] * M, 3), 'net_m2': round(f['rev_m2'] if r['kind'] == 'RV' else f['paint_m2'], 3), 'openings_m2': round(f['opening_m2'], 3)} for k, f in enumerate(r['faces']) if f['len'] * M >= .05]
        if r['kind'] == 'RV':
            codes.append({'code': r['code'], 'kind': 'RV', 'label': f"{r['code']} · {loc(r)} · {c2(r['rev_m2'])} m²", 'status': 'Propuesta a confirmar · revestimiento 0,00–2,40 · material a definir', 'elementId': str(r['id']), 'room': loc(r), 'level': r['level'],
                          'area_m2': round(r['rev_m2'], 3), 'gross_m2': round(sum(f['revGross_m2'] for f in r['faces']), 3), 'paintAbove_m2': round(r['paint_m2'], 3), 'faces': faces})
        else:
            codes.append({'code': r['code'], 'kind': 'PI', 'label': f"{r['code']} · {loc(r)} · {c2(r['paint_m2'])} m²", 'status': 'Propuesta a confirmar · pintura 0,00–2,60', 'elementId': str(r['id']), 'room': loc(r), 'level': r['level'], 'area_m2': round(r['paint_m2'], 3), 'faces': faces})
    for r, b in bands:
        codes.append({'code': b['code'], 'kind': 'RF', 'label': f"{b['code']} · {r['name']} · {c2(b['len_m'])} × 0,60 = {c2(b['m2'])} m²", 'status': 'Propuesta a confirmar · franja 0,90–1,50 sobre ' + ', '.join(b['items']), 'elementId': str(r['id']), 'room': loc(r), 'level': r['level'],
                      'length_m': round(b['len_m'], 3), 'area_m2': round(b['m2'], 3), 'face': f"C{b['face'] + 1}"})
    quantities = [{'label': loc(r), 'group': 'Revestimiento · baños y toilettes', 'count': 1, 'value': round(r['rev_m2'], 2), 'unit': 'm²', 'detail': f"{r['code']} · bruto {c2(sum(f['revGross_m2'] for f in r['faces']))} − vanos"} for r in rv]
    quantities += [{'label': f"{b['code']} · {r['name']}", 'group': 'Revestimiento · franjas sobre mesada', 'count': 1, 'value': round(b['m2'], 2), 'unit': 'm²', 'detail': f"{c2(b['len_m'])} ml × 0,60 − vanos · {', '.join(b['items'])}"} for r, b in bands]
    quantities += [{'label': loc(r), 'group': f"Pintura · {r['level']}", 'count': 1, 'value': round(r['paint_m2'], 2), 'unit': 'm²', 'detail': r['code'] + (' · 2,40–2,60 sobre revestimiento' if r['kind'] == 'RV' else ' · 0,00–2,60 − vanos' + (' − franja' if r['bands'] else ''))} for r in rooms]
    totals = [{'label': 'Revestimiento baños y toilettes', 'value': round(T['rev'], 2), 'unit': 'm²', 'detail': f"{len(rv)} locales · bruto {c2(gross_rev)} m² − vanos"},
              {'label': 'Franjas cocina y lavadero', 'value': round(T['band'], 2), 'unit': 'm²', 'detail': f"{len(bands)} franjas · {c2(sum(b['len_m'] for _, b in bands))} ml"},
              {'label': 'Pintura de muros', 'value': round(T['paint'], 2), 'unit': 'm²', 'detail': f"{len(rooms)} locales · hasta 2,60"},
              {'label': 'Revestimiento total (propuesta)', 'value': round(T['rev'] + T['band'], 2), 'unit': 'm²', 'detail': 'sin desperdicio; material a definir'}]
    m = {'title': 'Revestimientos', 'summary': f"PROPUESTA A CONFIRMAR: {c2(T['rev'])} m² de revestimiento en {len(rv)} baños y toilettes (h 2,40), {c2(T['band'])} m² de franjas en cocina y lavadero, {c2(T['paint'])} m² de pintura de muros; vanos descontados. {len(out)} láminas.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': d['readAt'], 'revision': 'R26', 'status': 'propuesta', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'Propuesta a confirmar. Superficies por cara terminada del local (límite Finish de Revit) por altura de la hipótesis, descontando puertas, ventanas, pases, muros cortina, arcos y separaciones de local. Sin desperdicio ni cortes.',
         'notModeled': ['Capas de terminación en los muros (el cómputo sale de los locales, no de capas)', 'Material, formato y despiece', 'Guardas, cantoneras, buñas y zócalos sanitarios', 'Revestimiento de fachada (hipótesis: hormigón visto)', 'Franja sobre la mesada del Quincho'],
         'decisions': ['Propuesta con hipótesis recomendadas: baños 0,00–2,40; cocina y lavadero franja 0,90–1,50; resto pintado hasta 2,60; fachada hormigón visto.', 'Documentado con detalles 2D sobre el modelo existente: no se tocaron geometría ni capas de muros.',
                       'Códigos RV/RF/PI solo como anotación.'],
         'questions': ['¿Material y formato del revestimiento de baños (porcelanato 60×120, cerámico 30×60, microcemento)?', '¿Baños revestidos hasta 2,40 m (propuesta) o hasta el cielorraso?',
                       '¿La franja de cocina va solo bajo las ventanas (0,90–1,13 m, como da hoy) o se cambia la altura de las ventanas / mesada?', '¿El Quincho lleva franja sobre la mesada y la parrilla?',
                       '¿Pintura: látex interior en todos los locales y esmalte / epoxi en lavadero y sala de máquinas?', '¿Modelamos las capas de terminación en los muros para que el cómputo salga del modelo? (cambia el modelo: requiere tu OK)']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes), 'rev': round(T['rev'], 2), 'band': round(T['band'], 2), 'paint': round(T['paint'], 2)}))


if __name__ == '__main__': main()
