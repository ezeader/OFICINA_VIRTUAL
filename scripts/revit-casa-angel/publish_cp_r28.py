"""R28: publish Cielorrasos PROPUESTA into public/casa-angel/rubros/cielorrasos/manifest.json (web contract lib/rubros.ts).
Keeps the R21 sheets (existing ceilings), replaces CIE-00 and adds CIE-P-PB/PA/PE + CIE-D-01."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'cielorrasos'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
KINDS = {'TC': 'Tipos de cielorraso', 'CE': 'Cielorrasos existentes (modelo)', 'CP': 'Cielorrasos propuestos (por local)'}
SKIP = ('cp-request.json', 'cp-elements.json', 'cp-plan.json', 'cp-probe.json')
TYPES = {'TC-01': 'Suspendido placa Knauf RH 12,5 (zonas húmedas)', 'TC-02': 'Suspendido placa Knauf ST 12,5'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def records():
    out = []
    for f in sorted(OUT.glob('cp-*.json')):
        if f.name in SKIP: continue
        d = read(f)
        if isinstance(d, dict) and 'sheets' in d: out += d['sheets']
    return out


def stats(d):
    rooms = [r for r in d['rooms'] if not r['excluded']]
    by = lambda t: [r for r in rooms if r['docType'] == t]
    return {'rooms': rooms, 'RH': sum(r['total_m2'] for r in by('TC-01')), 'ST': sum(r['total_m2'] for r in by('TC-02')), 'existing': sum(r['existing_m2'] for r in rooms),
            'cp': sum(r['cp_m2'] for r in rooms), 'buna': sum(r['buna_ml'] for r in rooms), 'tapas': sum(r['tapas'] for r in rooms),
            'vm': [r for r in rooms if r['underRoof']], 'dbl': [r for r in rooms if r['doubleHeight']], 'excluded': [r for r in d['rooms'] if r['excluded']]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    d = read(OUT / 'cp-plan.json'); st = stats(d)
    if a.index_columns:
        comp = [f"TC-01 RH: {c2(st['RH'])} m² · TC-02 ST: {c2(st['ST'])} m²", f"Existente modelado: {c2(st['existing'])} m² · propuesto: {c2(st['cp'])} m²",
                f"Buña perimetral Z 15: {c2(st['buna'])} ml · tapas 60×60: {st['tapas']} u", f"Pintura de cielorrasos: {c2(st['RH'] + st['ST'])} m²", ''] + \
               [f"{r['code']} {r['name']}: {c2(r['cp_m2'])} m²" + (' (v. magnitud)' if r['underRoof'] else '') for r in st['rooms'] if r['cp']]
        cols = [{'title': 'Propuesta a confirmar', 'lines': ['TC-01 placa RH: baños, toilettes, cocina, lavadero.', 'TC-02 placa ST: resto de los locales.', 'TC-03 "Plain" se reparte entre TC-01 y TC-02.', 'Parciales: se completa el resto del local.', 'Altura: la del cielorraso del local o vecino.', 'Bajo cubierta: verdadera magnitud.', 'Ascensor: sin cielorraso (pasadizo).', 'El modelo no se modificó.']},
                {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['CIE-00  Índice', 'CIE-P-PB / PA / PE  Propuesta', 'CIE-D-01  Detalles', 'CIE-PB/PA/PE-01  Existente (R21)', 'CIE-F-TC-01..03  Tipos del modelo (R21)']},
                {'title': 'A confirmar', 'lines': [f"Bajo cubierta inclinada: {', '.join(r['name'] for r in st['vm'])}.", f"Posible doble altura: {', '.join(r['name'] for r in st['dbl'])}.", 'Modelar los cielorrasos propuestos en Revit (OK).']}]
        print(json.dumps(cols, ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R28', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'cp-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    old = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    roomby = {str(r['id']): r for r in d['rooms']}; exby = {str(e['id']): e for e in d['existing']}
    proj = {str(p['id']): p for p in read(OUT / 'cp-elements.json')}
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r28-{n}.pdf'; assert src.exists(), n
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
                        rr = roomby[k]
                        lab = (f"{rr['number']} · {rr['name']} · sin cielorraso (pasadizo)" if rr['excluded'] else
                               f"{rr['code'] or rr['number']} · {rr['name']} · {rr['docType']} · total {c2(rr['total_m2'])} m²" + (f" (propuesto {c2(rr['cp_m2'])})" if rr['cp'] else ' (existente)') + ' · propuesta')
                        els.append({'code': rr['code'], 'elementId': k, 'room': True, 'label': lab, 'box': box})
                    elif k in exby:
                        e = exby[k]; els.append({'code': e['code'], 'elementId': k, 'label': f"{e['code']} · existente · {e['docType']}" + (f" (modelo {e['modelType']})" if e['changed'] else '') + f" · {c2(e['area_m2'])} m²", 'box': box})
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        new.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': s.get('element'), 'elementId': s.get('elementId'),
                    'elementKind': s.get('elementKind'), 'note': 'Propuesta a confirmar', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    kept = [s for s in old['sheets'] if s['number'] != 'CIE-00' and not s['number'].startswith(('CIE-P-', 'CIE-D-'))]
    for s in kept: s['note'] = s.get('note') or 'Existente en el modelo (R21)'
    out = sorted(new + kept, key=lambda s: (s['number'] != 'CIE-00', s['number'].startswith('CIE-F'), not s['number'].startswith(('CIE-P', 'CIE-D')), s['number']))
    loc = lambda r: f"{r['number']} · {r['name']} · {r['levelCode']}"
    codes = [{'code': 'TC-01', 'kind': 'TC', 'label': 'TC-01 · ' + TYPES['TC-01'], 'status': 'Propuesta · perfilería galvanizada 35, velas c/1,00, buña Z 15', 'area_m2': round(st['RH'], 2)},
             {'code': 'TC-02', 'kind': 'TC', 'label': 'TC-02 · ' + TYPES['TC-02'], 'status': 'Propuesta · perfilería galvanizada 35, velas c/1,00, buña Z 15', 'area_m2': round(st['ST'], 2)},
             {'code': 'TC-03', 'kind': 'TC', 'label': 'TC-03 · "Plain" (genérico del modelo)', 'status': 'Disuelto en TC-01 / TC-02 (solo documentación)', 'area_m2': 0}]
    codes += [{'code': e['code'], 'kind': 'CE', 'label': f"{e['code']} · {e['room']} · {c2(e['area_m2'])} m²", 'status': f"Existente · {e['docType']}" + (f" (modelo {e['modelType']}, reasignado en la documentación)" if e['changed'] else ''),
               'elementId': str(e['id']), 'typeCode': e['docType'], 'modelTypeCode': e['modelType'], 'area_m2': round(e['area_m2'], 2), 'height_m': round(e['height_m'], 2)} for e in d['existing']]
    codes += [{'code': r['code'], 'kind': 'CP', 'label': f"{r['code']} · {loc(r)} · {r['docType']} · {c2(r['cp_m2'])} m²", 'status': 'Propuesta a confirmar · ' + r['heightNote'], 'elementId': str(r['id']), 'room': loc(r), 'typeCode': r['docType'],
               'area_m2': round(r['cp_m2'], 2), 'planArea_m2': round(r['cpPlan_m2'], 2), 'height_m': None if r['underRoof'] else r['height_m'], 'slope_deg': r['slope_deg'] or None, 'trueMagnitude': r['underRoof'],
               'doubleHeight': r['doubleHeight'], 'perimeter_m': round(r['perimeter_m'], 2)} for r in st['rooms'] if r['cp']]
    quantities = [{'label': loc(r), 'group': f"Locales · {r['docType']}", 'count': 1, 'value': round(r['total_m2'], 2), 'unit': 'm²',
                   'detail': (f"existente {c2(r['existing_m2'])} + " if r['existing_m2'] else '') + (f"propuesto {c2(r['cp_m2'])} ({r['code']})" if r['cp'] else 'sin propuesta') + f" · buña {c2(r['buna_ml'])} ml" + (f" · {r['tapas']} tapa" if r['tapas'] else '') + f" · {r['heightNote']}"} for r in st['rooms']]
    quantities += [{'label': loc(r), 'group': 'Sin cielorraso (decisión)', 'count': 1, 'value': round(r['area_m2'], 2), 'unit': 'm²', 'detail': 'pasadizo del ascensor'} for r in st['excluded']]
    totals = [{'label': 'Placa RH (TC-01)', 'value': round(st['RH'], 2), 'unit': 'm²', 'detail': 'existente + propuesto'}, {'label': 'Placa ST (TC-02)', 'value': round(st['ST'], 2), 'unit': 'm²', 'detail': 'existente + propuesto'},
              {'label': 'Buña perimetral Z 15', 'value': round(st['buna'], 2), 'unit': 'ml', 'detail': 'perímetro de los locales'}, {'label': 'Tapas de inspección 60×60', 'value': st['tapas'], 'unit': 'u', 'detail': 'baños, toilettes y sala de máquinas'},
              {'label': 'Existente modelado', 'value': round(st['existing'], 2), 'unit': 'm²', 'detail': f"{len(d['existing'])} cielorrasos"}, {'label': 'Propuesto (nuevo)', 'value': round(st['cp'], 2), 'unit': 'm²', 'detail': f"{len([r for r in st['rooms'] if r['cp']])} locales"},
              {'label': 'Cielorrasos (total propuesta)', 'value': round(st['RH'] + st['ST'], 2), 'unit': 'm²', 'detail': 'RH + ST'}]
    budget = [{'id': 'cielorraso-placa-rh', 'label': 'Placa RH 12,5 colocada con masillado (TC-01)', 'value': round(st['RH'], 2), 'unit': 'm²', 'detail': 'existente + propuesto; sin estructura ni pintura', 'informative': False},
              {'id': 'cielorraso-placa-st', 'label': 'Placa ST 12,5 colocada con masillado (TC-02)', 'value': round(st['ST'], 2), 'unit': 'm²', 'detail': 'existente + propuesto; sin estructura ni pintura', 'informative': False},
              {'id': 'cielorraso-perfileria', 'label': 'Estructura suspendida de perfiles galvanizados', 'value': round(st['RH'] + st['ST'], 2), 'unit': 'm²', 'detail': 'soleras + montantes 35 c/0,40, velas c/1,00', 'informative': False},
              {'id': 'cielorraso-bunas', 'label': 'Buña perimetral Z 15 mm', 'value': round(st['buna'], 2), 'unit': 'ml', 'detail': 'perímetro de los locales', 'informative': False},
              {'id': 'cielorraso-tapas-inspeccion', 'label': 'Tapas de inspección 60×60', 'value': st['tapas'], 'unit': 'u', 'detail': 'baños, toilettes y sala de máquinas', 'informative': False},
              {'id': 'cielorraso-pintura', 'label': 'Pintura de cielorrasos (látex; antihongos en RH)', 'value': round(st['RH'] + st['ST'], 2), 'unit': 'm²', 'detail': 'RH + ST', 'informative': False},
              {'id': 'cielorraso-total', 'label': 'Cielorrasos (total propuesta)', 'value': round(st['RH'] + st['ST'], 2), 'unit': 'm²', 'detail': 'referencia', 'informative': True},
              {'id': 'cielorraso-existente', 'label': 'Existente modelado', 'value': round(st['existing'], 2), 'unit': 'm²', 'detail': 'referencia', 'informative': True},
              {'id': 'cielorraso-propuesto', 'label': 'Propuesto (nuevo)', 'value': round(st['cp'], 2), 'unit': 'm²', 'detail': 'referencia', 'informative': True}]
    vm = ', '.join(f"{r['name']} ({('%.1f' % r['slope_deg']).replace('.', ',')}°)" for r in st['vm']); dbl = ', '.join(r['name'] for r in st['dbl'])
    m = dict(old)
    m.update({'title': 'Cielorrasos', 'revision': 'R28', 'status': 'propuesta', 'readAt': d['readAt'], 'kinds': KINDS, 'sheets': out, 'codes': codes, 'totals': totals, 'quantities': quantities,
              'summary': f"PROPUESTA A CONFIRMAR: {c2(st['RH'] + st['ST'])} m² de cielorrasos suspendidos ({c2(st['RH'])} m² RH en zonas húmedas, {c2(st['ST'])} m² ST), de los que {c2(st['existing'])} m² ya están modelados y {c2(st['cp'])} m² se proponen; buña {c2(st['buna'])} ml, {st['tapas']} tapas de inspección. {len(out)} láminas.",
              'quantityNote': f"Propuesta a confirmar. Área propuesta = local − cielorrasos existentes (geometría del modelo, límite Finish). Bajo cubierta inclinada se computa en verdadera magnitud: {vm}. Posible doble altura (escalera / puente), computado en planta: {dbl}. Ascensor excluido.",
              'notModeled': ['Cielorrasos propuestos (CP): solo dibujados en 2D, no modelados', 'Buñas, tapas de inspección y perfilería', 'Pintura de cielorrasos'],
              'decisions': ['Hipótesis: zonas húmedas TC-01 RH, resto TC-02 ST; TC-03 se reparte; parciales se completan; altura del local o del vecino.', 'Documentado con regiones y detalles 2D sobre plantas de cielorraso: no se tocaron geometría ni tipos.',
                            'Códigos TC/CE/CP solo como anotación (no Mark).', 'Ascensor sin cielorraso (pasadizo).', f"Bajo cubierta en verdadera magnitud: {vm}."],
              'questions': ['¿Confirmás la propuesta (húmedos placa RH, resto ST, buña perimetral Z 15, tapas 60×60)?',
                            f"{vm.split(' (')[0] if vm else ''}… quedan bajo la cubierta inclinada: ¿cielorraso siguiendo la pendiente (como se computó) o plano a 2,70 m?",
                            f"¿{dbl} son doble altura (escalera)? Hoy se computan en planta como cielorraso común.",
                            '¿Modelamos los cielorrasos propuestos en Revit? (cambia el modelo: requiere tu OK)'],
              'budget': {'revision': 'R28', 'note': 'Partidas sin solapes: la placa no incluye estructura ni pintura; informative = referencia.', 'lines': budget}})
    m['questions'][1] = f"Comedor, Living, Playroom y la Planta Entrepiso quedan bajo la cubierta inclinada ({vm}): ¿cielorraso siguiendo la pendiente (como se computó) o plano?"
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'new': len(new), 'codes': len(codes), 'RH': round(st['RH'], 2), 'ST': round(st['ST'], 2), 'existing': round(st['existing'], 2), 'cp': round(st['cp'], 2), 'buna': round(st['buna'], 2), 'tapas': st['tapas']}))


if __name__ == '__main__': main()
