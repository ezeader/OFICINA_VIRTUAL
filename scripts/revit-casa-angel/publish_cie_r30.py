"""R30 Cielorrasos: publish the DOC-file sheets (Casa-Angel-DOC-Cielorrasos.rvt) and the computation from the model
into public/casa-angel/rubros/cielorrasos/manifest.json. Same budget ids as R28/R29."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'cielorrasos'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
FILES = ('cie30-index.json', 'cie30-plans.json', 'cie30-details.json')
TYPES = {'TC-01': 'Suspendido placa Knauf RH 12,5 (zonas húmedas)', 'TC-02': 'Suspendido placa Knauf ST 12,5'}


def c2(v): return ('%.2f' % v).replace('.', ',')
def clean(s): return s.encode('latin-1', 'backslashreplace').decode('unicode_escape') if isinstance(s, str) and '\\x' in s else s


def load():
    d = read(OUT / 'cie30-plan.json')
    for r in d['rooms']: r['name'] = clean(r['name']); r['level'] = clean(r['level'])
    for c in d['ceilings']: c['level'] = clean(c['level']); c['type'] = clean(c['type'])
    room = {r['id']: r for r in d['rooms']}
    for c in d['ceilings']: c['room'] = room.get(c['roomId'])
    wood = [dict(r, wood_m2=round(r['area_m2'] - r['covered_m2'], 3)) for r in d['rooms'] if r['wood'] and r['area_m2'] - r['covered_m2'] > .5]
    return d, wood


def stats(d, wood):
    cs = d['ceilings']; by = lambda t: [c for c in cs if c['tc'] == t]
    return {'RH': sum(c['area_m2'] for c in by('TC-01')), 'ST': sum(c['area_m2'] for c in by('TC-02')), 'CE': sum(c['area_m2'] for c in cs if c['code'].startswith('CE')),
            'CP': sum(c['area_m2'] for c in cs if c['code'].startswith('CP')), 'buna': sum(r['buna_ml'] for r in d['rooms']), 'tapas': sum(r['tapa'] for r in d['rooms']),
            'wood': sum(w['wood_m2'] for w in wood), 'n': len(cs)}


def index_columns(d, wood):
    st = stats(d, wood)
    comp = [f"TC-01 placa RH: {c2(st['RH'])} m²", f"TC-02 placa ST: {c2(st['ST'])} m²", f"Perfilería y pintura: {c2(st['RH'] + st['ST'])} m²", f"Buña Z 15: {c2(st['buna'])} ml · tapas 60×60: {st['tapas']} u", ''] + \
           [f"{r['number']} {r['name']}: {c2(r['covered_m2'])} m²" for r in d['rooms'] if r['ceilings']]
    return [{'title': 'Criterio (confirmado y modelado)', 'lines': ['TC-01 Knauf RH: baños, toilettes, cocina, lavadero.', 'TC-02 Knauf ST: resto de los locales.', 'Sala de TV con ST (2,70); Baño PA con RH.', 'Bajo la cubierta de madera: machimbre visto', '(ver Cubierta). Sala de Máquinas sin cielorraso.', 'Ascensor: sin cielorraso (pasadizo).']},
            {'title': 'Cómputo (desde el modelo)', 'lines': comp}, {'title': 'Láminas', 'lines': ['CIE-00  Índice', 'CIE-PB-01  Planta Baja', 'CIE-PA-01  Planta Alta', 'CIE-PE-01  Planta Entrepiso', 'CIE-D-01  Detalles']},
            {'title': 'Machimbre visto (ver Cubierta)', 'lines': [f"{w['number']} {w['name']}: {c2(w['wood_m2'])} m²" for w in wood] + [f"Total en planta: {c2(st['wood'])} m²"]}]


def records():
    out = []
    for fn in FILES:
        if (OUT / fn).exists(): out += read(OUT / fn)['sheets']
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    d, wood = load(); st = stats(d, wood)
    if a.index_columns: print(json.dumps(index_columns(d, wood), ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R30', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'cie30-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; old = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    cby = {str(c['id']): c for c in d['ceilings']}; rby = {str(r['id']): r for r in d['rooms']}
    proj = {str(p['id']): p for p in read(OUT / 'cie30-elements.json')}
    out = []
    for s in sheets:
        n = s['number']; src = OUT / f'r30-{n}.pdf'; assert src.exists(), n
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
                    if k in cby: c = cby[k]; els.append({'code': c['code'], 'elementId': k, 'label': f"{c['code']} · {c['tc']} · {c2(c['area_m2'])} m² · h {c2(c['height_m'])}", 'box': box})
                    elif k in rby:
                        rr = rby[k]; lab = f"{rr['number']} · {rr['name']} · " + ('machimbre visto (ver Cubierta)' if rr['wood'] and rr['covered_m2'] < .9 * rr['area_m2'] else (f"cielorraso {c2(rr['covered_m2'])} m²" if rr['ceilings'] else 'sin cielorraso'))
                        els.append({'code': None, 'elementId': k, 'room': True, 'label': lab, 'box': box})
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        out.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': None, 'elementId': None, 'elementKind': None,
                    'note': 'R30 · archivo Casa-Angel-DOC-Cielorrasos.rvt', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    out.sort(key=lambda s: (s['number'] != 'CIE-00', s['number'].startswith('CIE-D'), s['number']))
    loc = lambda r: f"{r['number']} · {r['name']} · {'PB' if r['level'].startswith('00') else ('PA' if r['level'].startswith('01') else 'PE')}" if r else 'sin local'
    codes = [{'code': t, 'kind': 'TC', 'label': f"{t} · {TYPES[t]}", 'status': 'Modelado · perfilería galvanizada 35, velas c/1,00, buña Z 15', 'area_m2': round(st['RH' if t == 'TC-01' else 'ST'], 2)} for t in ('TC-01', 'TC-02')]
    codes += [{'code': c['code'], 'kind': c['code'][:2], 'label': f"{c['code']} · {loc(c['room'])} · {c['tc']} · {c2(c['area_m2'])} m²", 'status': ('Modelado R30 (propuesta confirmada)' if c['code'].startswith('CP') else 'Existente') + f" · {c['type']} · h {c2(c['height_m'])}",
               'elementId': str(c['id']), 'typeCode': c['tc'], 'room': loc(c['room']), 'area_m2': c['area_m2'], 'perimeter_m': c['perimeter_m'], 'height_m': c['height_m']} for c in d['ceilings']]
    quantities = [{'label': loc(r), 'group': f"Locales · {r['level']}", 'count': len(r['ceilings']), 'value': round(r['covered_m2'], 2), 'unit': 'm²',
                   'detail': ', '.join(cby[str(i)]['code'] + ' ' + cby[str(i)]['tc'] for i in r['ceilings']) + f" · buña {c2(r['buna_ml'])} ml" + (' · 1 tapa' if r['tapa'] else '')} for r in d['rooms'] if r['ceilings']]
    quantities += [{'label': loc(w), 'group': 'Machimbre visto · ver Cubierta (no se suma)', 'count': 1, 'value': w['wood_m2'], 'unit': 'm²', 'detail': 'superficie en planta sin cielorraso'} for w in wood]
    quantities += [{'label': loc(r), 'group': 'Sin cielorraso (decisión)', 'count': 1, 'value': r['area_m2'], 'unit': 'm²', 'detail': 'pasadizo del ascensor'} for r in d['rooms'] if r['excluded']]
    T = st['RH'] + st['ST']
    totals = [{'label': 'Placa RH (TC-01)', 'value': round(st['RH'], 2), 'unit': 'm²', 'detail': 'modelado'}, {'label': 'Placa ST (TC-02)', 'value': round(st['ST'], 2), 'unit': 'm²', 'detail': 'modelado'},
              {'label': 'Buña perimetral Z 15', 'value': round(st['buna'], 2), 'unit': 'ml', 'detail': 'perímetro de los locales con cielorraso'}, {'label': 'Tapas de inspección 60×60', 'value': st['tapas'], 'unit': 'u', 'detail': 'baños y toilettes'},
              {'label': 'Machimbre visto (ver Cubierta)', 'value': round(st['wood'], 2), 'unit': 'm²', 'detail': 'no se suma'}, {'label': 'Cielorrasos (total)', 'value': round(T, 2), 'unit': 'm²', 'detail': f"{st['n']} cielorrasos modelados"}]
    budget = [{'id': 'cielorraso-placa-rh', 'label': 'Placa RH 12,5 colocada con masillado (TC-01)', 'value': round(st['RH'], 2), 'unit': 'm²', 'detail': 'modelado; sin estructura ni pintura', 'informative': False},
              {'id': 'cielorraso-placa-st', 'label': 'Placa ST 12,5 colocada con masillado (TC-02)', 'value': round(st['ST'], 2), 'unit': 'm²', 'detail': 'modelado; sin estructura ni pintura', 'informative': False},
              {'id': 'cielorraso-perfileria', 'label': 'Estructura suspendida de perfiles galvanizados', 'value': round(T, 2), 'unit': 'm²', 'detail': 'soleras + montantes 35 c/0,40, velas c/1,00', 'informative': False},
              {'id': 'cielorraso-bunas', 'label': 'Buña perimetral Z 15 mm', 'value': round(st['buna'], 2), 'unit': 'ml', 'detail': 'perímetro de los locales con cielorraso', 'informative': False},
              {'id': 'cielorraso-tapas-inspeccion', 'label': 'Tapas de inspección 60×60', 'value': st['tapas'], 'unit': 'u', 'detail': 'baños y toilettes', 'informative': False},
              {'id': 'cielorraso-pintura', 'label': 'Pintura de cielorrasos (látex; antihongos en RH)', 'value': round(T, 2), 'unit': 'm²', 'detail': 'RH + ST', 'informative': False},
              {'id': 'cielorraso-total', 'label': 'Cielorrasos (total)', 'value': round(T, 2), 'unit': 'm²', 'detail': 'referencia', 'informative': True},
              {'id': 'cielorraso-existente', 'label': 'Existentes antes de R30 (CE)', 'value': round(st['CE'], 2), 'unit': 'm²', 'detail': 'referencia', 'informative': True},
              {'id': 'cielorraso-propuesto', 'label': 'Modelados en R30 (CP)', 'value': round(st['CP'], 2), 'unit': 'm²', 'detail': 'referencia', 'informative': True},
              {'id': 'cielorraso-madera-vista', 'label': 'Locales con cubierta de madera vista (ver Cubierta)', 'value': round(st['wood'], 2), 'unit': 'm²',
               'detail': 'en planta: ' + ', '.join(f"{w['name']} {c2(w['wood_m2'])}" for w in wood) + ' · el machimbre lo computa Cubierta (cubierta-machimbre)', 'informative': True}]
    m = dict(old)
    m.update({'title': 'Cielorrasos', 'revision': 'R30', 'status': 'modelado', 'readAt': d['readAt'], 'kinds': {'TC': 'Tipos de cielorraso', 'CE': 'Cielorrasos existentes (antes de R30)', 'CP': 'Cielorrasos modelados en R30'},
              'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
              'summary': f"{st['n']} cielorrasos modelados: {c2(st['RH'])} m² placa RH en zonas húmedas y {c2(st['ST'])} m² placa ST; buña {c2(st['buna'])} ml, {st['tapas']} tapas. Bajo la cubierta de madera ({c2(st['wood'])} m²) queda el machimbre visto (ver Cubierta). {len(out)} láminas en Casa-Angel-DOC-Cielorrasos.rvt.",
              'quantityNote': 'Cómputo desde el modelo vinculado: área de cada cielorraso, local por punto bajo el cielorraso; buña = perímetro del local si está cubierto (≥95 %), si no el perímetro de los cielorrasos.',
              'notModeled': ['Buñas, tapas de inspección y perfilería (computadas, no modeladas)', 'Pintura de cielorrasos', 'Machimbre visto: rubro Cubierta'],
              'decisions': [x for x in old.get('decisions', []) if 'Ascensor' in x or 'Usuario' in x] + ['Usuario: "Sí al baño PA con placa RH, y dibujalos en Revit": cielorrasos propuestos modelados en el modelo principal (R30) con tipos Knauf RH/ST.',
                            'Usuario: la Sala de TV lleva cielorraso (ST, 2,70); la Sala de Máquinas no (cielorraso borrado del modelo, con backup).', 'Documentación en archivo propio Casa-Angel-DOC-Cielorrasos.rvt que vincula el modelo principal.'],
              'questions': [],
              'budget': {'revision': 'R30', 'note': 'Partidas sin solapes: la placa no incluye estructura ni pintura; el machimbre visto lo computa Cubierta; informative = referencia.', 'lines': budget}})
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'RH': round(st['RH'], 2), 'ST': round(st['ST'], 2), 'buna': round(st['buna'], 2), 'tapas': st['tapas'], 'wood': round(st['wood'], 2), 'CE': round(st['CE'], 2), 'CP': round(st['CP'], 2)}))


if __name__ == '__main__': main()
