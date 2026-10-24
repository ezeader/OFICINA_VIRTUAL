"""Publish Exteriores to public/casa-angel/rubros/exteriores/manifest.json (web contract lib/rubros.ts)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'exteriores'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'TE': 'Terreno (toposólidos)', 'CA': 'Calle', 'AC': 'Base de acceso', 'EA': 'Escalones de acceso', 'EE': 'Escalera exterior', 'BA': 'Barandas exteriores', 'PO': 'Portón (hojas)'}


def c2(v): return ('%.2f' % v).replace('.', ',')
def c1(v): return f'{v:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def records():
    out = []
    for f in sorted(OUT.glob('ext-*.json')):
        if f.name in ('ext-request.json', 'ext-elements.json', 'ext-plan.json', 'ext-probe.json'): continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return sorted(out, key=lambda s: (s['number'] != 'EXT-00', s['number'].startswith('EXT-F'), s['number']))


def groups(els):
    k = lambda x: [e for e in els if e['kind'] == x]
    return {x: k(x) for x in KINDS}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    plan = read(OUT / 'ext-plan.json'); els = plan['elements']; g = groups(els)
    ints = plan['interiorRailings']
    if a.index_columns:
        comp = [f"Terreno TE-01..{len(g['TE']):02d}: {c1(sum(e['area_m2'] for e in g['TE']))} m²", f"Calle CA-01: {c1(g['CA'][0]['area_m2'])} m²",
                f"Base de acceso AC-01: {c2(g['AC'][0]['area_m2'])} m²", f"Escalones EA-01..{len(g['EA']):02d}: {len(g['EA'])} u · {c2(sum(e['area_m2'] for e in g['EA']))} m²",
                f"Escalera EE-01: {g['EE'][0]['risers']} alzadas de {c2(g['EE'][0]['riser_m'])}",
                f"Barandas BA-01..{len(g['BA']):02d}: {c2(sum(e['length_m'] for e in g['BA']))} ml (h 0,90)", f"Portón PO-01..{len(g['PO']):02d}: {c2(sum(e['area_m2'] for e in g['PO']))} m²"]
        cols = [{'title': 'Criterios', 'lines': ['TE terreno · CA calle · AC acceso · EA escalones;', 'EE escalera exterior · BA barandas · PO portón.', 'Barandas interiores (escalera/hall): no se computan acá.', 'Deck, borde de pileta y aleros: en Pisos, Pileta y Cubierta.', 'Códigos solo como anotación (no en Mark).']},
                {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['EXT-00  Índice'] + sorted(s['number'] for s in records())},
                {'title': 'No modelado / a definir', 'lines': [f"Vegetación: {len(plan['plantingTypes'])} especies cargadas, {plan['plantingPlaced']} colocadas.", 'Solados exteriores, veredas y senderos.', 'Cercos y medianeras; riego; iluminación exterior.', 'Terminación de escalones y herrajes del portón.']}]
        print(json.dumps(cols, ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R23', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'ext-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    code = {str(e['id']): e for e in els}; proj = {str(p['id']): p for p in read(OUT / 'ext-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r23-{n}.pdf'; assert src.exists(), n
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
    keep = ('length_m', 'area_m2', 'volume_m3', 'height_m', 'top_m', 'risers', 'riser_m', 'tread_m', 'sector')
    codes = [dict({'code': e['code'], 'kind': e['kind'], 'label': e['label'], 'status': e['status'], 'elementId': str(e['id']), 'type': e['type']}, **{k: (round(e[k], 3) if isinstance(e[k], float) else e[k]) for k in keep if e.get(k) is not None}) for e in els]
    def qv(e):
        if e['kind'] == 'BA': return round(e['length_m'], 2), 'ml'
        if e['kind'] == 'EE': return e['risers'], 'alzadas'
        return round(e['area_m2'], 2), 'm²'
    quantities = [{'label': e['code'], 'group': KINDS[e['kind']], 'count': 1, 'value': qv(e)[0], 'unit': qv(e)[1], 'detail': e['label']} for e in els]
    ba = sum(e['length_m'] for e in g['BA']); po = sum(e['area_m2'] for e in g['PO']); te = sum(e['area_m2'] for e in g['TE'])
    ee = g['EE'][0]
    totals = [{'label': 'Calle', 'value': round(g['CA'][0]['area_m2'], 2), 'unit': 'm²', 'detail': 'piso "Calle"'},
              {'label': 'Base de acceso', 'value': round(g['AC'][0]['area_m2'], 2), 'unit': 'm²', 'detail': f"+{c2(g['AC'][0]['top_m'])}"},
              {'label': 'Escalones de acceso', 'value': len(g['EA']), 'unit': 'u', 'detail': f"{c2(sum(e['area_m2'] for e in g['EA']))} m² · alzada 0,20"},
              {'label': 'Escalera exterior', 'value': ee['risers'], 'unit': 'alzadas', 'detail': f"alzada {c2(ee['riser_m'])} · huella {c2(ee['tread_m'])} · sube {c2(ee['height_m'])} m"},
              {'label': 'Barandas exteriores', 'value': round(ba, 2), 'unit': 'ml', 'detail': f"{len(g['BA'])} barandas · h 0,90"},
              {'label': 'Portón', 'value': round(po, 2), 'unit': 'm²', 'detail': f"{len(g['PO'])} hojas · e 5 cm"},
              {'label': 'Terreno', 'value': round(te, 2), 'unit': 'm²', 'detail': f"{len(g['TE'])} toposólidos"}]
    m = {'title': 'Exteriores', 'summary': f"Terreno {c1(te)} m², calle {c1(g['CA'][0]['area_m2'])} m², acceso con {len(g['EA'])} escalones, escalera exterior de {ee['risers']} alzadas, {c2(ba)} ml de barandas y portón de {c2(po)} m². {len(out)} láminas.",
         'model': 'Casa-Angel-piloto-documentacion.rvt', 'readAt': plan['readAt'], 'revision': 'R23', 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
         'quantityNote': 'Áreas según Revit (cara superior para terreno, calle y acceso; una cara para el portón). Barandas: largo del recorrido. Deck, borde de pileta y aleros se computan en Pisos, Pileta y Cubierta.',
         'notModeled': [f"Vegetación: {len(plan['plantingTypes'])} especies cargadas en el modelo, {plan['plantingPlaced']} colocadas", 'Solados exteriores, veredas y senderos', 'Cercos, medianeras y portón de calle', 'Riego e iluminación exterior',
                        'Terminación de escalones y herrajes / accionamiento del portón'],
         'decisions': ['Exteriores documentados con implantación general, planta PB, barandas y fichas (acceso, escalera, portón).',
                       f"Barandas interiores ({len(ints)}, {c2(sum(x['length_m'] for x in ints))} ml, escalera y hall) quedan fuera de este rubro.",
                       'Códigos TE/CA/AC/EA/EE/BA/PO solo como anotación (no escritos en Mark).'],
         'questions': ['¿Qué vegetación va y dónde (árboles, césped, canteros)? Hoy no hay ninguna colocada.', '¿Qué solado llevan veredas, acceso y patio de pileta?', '¿Hay cerco perimetral o portón de calle a documentar?', '¿Escribimos los códigos de exteriores en el modelo (Mark)?']}
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(codes)}))


if __name__ == '__main__': main()
