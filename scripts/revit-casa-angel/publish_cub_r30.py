"""R30 Cubierta (textos sin superposición, detalles D-01/D-02/D-03 desarrollados): publish the DOC-file sheets (Casa-Angel-DOC-Cubierta.rvt) into public/casa-angel/rubros/cubierta/manifest.json.
Keeps the R16 sheets (note: modelo previo al paquete), replaces CUB-00, adds CUB-P-01/02, CUB-C-01, CUB-D-01/02; budget R29."""
import argparse, collections, json, math, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'cubierta'; BASE = f'/casa-angel/rubros/{KEY}/'; PT_PER_FT = 2383.94 / 2.7592
FILES = ('cub29-sheets.json', 'cub29-details.json', 'cub29-index.json')
CLAV_W, SPACING = .05, .957
WOOD = ['Playroom', 'Comedor', 'Living', 'Puente', 'SM', 'Hall PE', 'Atelier', 'Hall', 'Sala de Maquinas']   # machimbre visto (Cielorrasos R30)


def c2(v): return ('%.2f' % v).replace('.', ',')
def clean(s): return s.encode('latin-1', 'backslashreplace').decode('unicode_escape') if isinstance(s, str) and '\\x' in s else s


def stats():
    d = read(OUT / 'cub29-plan.json'); fr = d['framing']
    ml = lambda k: sum(x['len_m'] for x in fr if x['kind'] == k)
    vol = lambda k: sum(x['len_m'] * x['w_m'] * x['h_m'] for x in fr if x['kind'] == k)
    ek = collections.defaultdict(float)
    for e in d['edges']:
        k = e['kind']
        if k == 'quiebre' and len(e.get('roofs', [])) > 1: k = 'limahoya'
        if e['len_m'] >= .2: ek[k] += e['len_m']
    area = sum(a['area_m2'] for a in d['aguas'])
    sh = read(OUT / 'cub29-sheets.json')['sheets']; baj = len(next(s for s in sh if s['number'] == 'CUB-P-01').get('bajadas', []))
    probe = {clean(r['name']): r for r in read(OUT / 'cp-probe.json')['rooms']}
    wood = []
    for n in WOOD:
        r = probe.get(n)
        if not r: continue
        ab = r.get('above') or {}; sl = ab.get('slope_deg', 0) if ab.get('isRoof') else 26.7
        frac = 1.0
        if n == 'Hall':
            w = {clean(x['name']).split(' ')[0]: x for x in read(OUT / 'cp-probe2.json')['rooms']}.get('Hall')
            if w: frac = w['counts']['roof'] / sum(w['counts'].values())
        plan = r['area_m2'] * frac; wood.append({'name': n, 'plan_m2': plan, 'slope': sl, 'true_m2': plan / math.cos(math.radians(sl))})
    return {'d': d, 'VC': ml('VC'), 'VP': ml('VP'), 'CR': ml('CR'), 'vol': vol('VC') + vol('VP') + vol('CR'), 'volVC': vol('VC'), 'nVC': len([x for x in fr if x['kind'] == 'VC']), 'nVP': len([x for x in fr if x['kind'] == 'VP']),
            'edges': ek, 'area': area, 'bajadas': baj, 'wood': wood}


def index_columns(st):
    e = st['edges']; a = st['area']
    comp = [f"Tejas / machimbre / membrana: {c2(a)} m² (v. magnitud)", f"EPS 75 neto: {c2(a * (1 - CLAV_W / SPACING))} m²", f"Cabios VP 5×15: {c2(st['VP'])} ml · clavaderas y contraclavaderas: {c2(st['VP'])} ml",
            f"Vigas VC 6×20: {c2(st['VC'])} ml · listones CR: {c2(st['CR'])} ml", f"Madera total: {c2(st['vol'])} m³", f"Cumbreras {c2(e['cumbrera'])} · limatesas {c2(e['limatesa'])} · limahoyas {c2(e['limahoya'] + e['limahoya horizontal'])} ml",
            f"Canaletas {c2(e['alero'])} ml · bajadas {st['bajadas']} u · babetas {c2(e['muro'])} ml", f"Machimbre visto sobre locales: {c2(sum(w['true_m2'] for w in st['wood']))} m²"]
    return [{'title': 'Paquete (confirmado, modelado)', 'lines': ['Teja cerámica apta baja pendiente', 'Cámara ventilada 25 (contraclavaderas)', 'Membrana hidrófuga respirable', 'EPS 75 mm entre clavaderas (sobre cabios)', 'Barrera de vapor PE 200 µm', 'Machimbre pino 3/4" visto', 'Cabios LVL 5×15 c/0,96 · VC 6×20 (calculista)']},
            {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas R30', 'lines': ['CUB-00  Índice', 'CUB-P-01  Planta de techos por faldón', 'CUB-P-02  Estructura', 'CUB-C-01  Cortes CU-01/02/03', 'CUB-D-01  Paquete a escala real (1:5)', 'CUB-D-02  Alero, cumbrera, limatesa', 'CUB-D-03  Apoyos y uniones (1:10)', 'CUB-D-04  Limahoya, babeta, bajada', 'R16: planta, cortes y fichas (modelo previo)']},
            {'title': 'Notas', 'lines': ['Archivo: Casa-Angel-DOC-Cubierta.rvt (vincula el modelo).', 'CU-03 a 16,8°: teja apta baja pendiente + membrana continua.', 'Encuentros horizontales bajos: limahoya / canaleta interna a verificar.', 'Secciones VC a verificar por calculista.']}]


def records():
    out = []
    for fn in FILES:
        if (OUT / fn).exists(): out += read(OUT / fn)['sheets']
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    st = stats()
    if a.index_columns: print(json.dumps(index_columns(st), ensure_ascii=True)); return
    sheets = records()
    if a.request:
        views = [{'rev': 'R29', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'cub29-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'rubros' / KEY; old = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    d = st['d']; byid = {str(x['id']): x for x in d['framing']}; ag = {}
    for x in d['aguas']: ag.setdefault(str(x['roof']), []).append(x)
    proj = {str(p['id']): p for p in read(OUT / 'cub29-elements.json')}
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r29-{n}.pdf'; assert src.exists(), n
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
                    if k in byid: x = byid[k]; els.append({'code': x['code'], 'elementId': k, 'label': f"{x['code']} · {x['type']} · {c2(x['len_m'])} ml", 'box': box})
                    elif k in ag: els.append({'code': ag[k][0]['roofCode'], 'elementId': k, 'label': f"{ag[k][0]['roofCode']} · {c2(sum(y['area_m2'] for y in ag[k]))} m² · paquete R29", 'box': box})
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        new.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'element': None, 'elementId': None, 'elementKind': None,
                    'note': 'R30 · archivo Casa-Angel-DOC-Cubierta.rvt', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    kept = [s for s in old['sheets'] if s['number'] != 'CUB-00' and s['number'] not in [x['number'] for x in new]]
    for s in kept: s['note'] = 'R16 · modelo previo al paquete R29 (secciones de cabios 3×10)'
    out = sorted(new + kept, key=lambda s: (s['number'] != 'CUB-00', s['number'].startswith('CUB-F'), not s['number'].startswith(('CUB-P', 'CUB-C', 'CUB-D')), s['number']))
    e = st['edges']; A = st['area']; lima = e['limahoya'] + e['limahoya horizontal']
    codes = [{'code': x['code'], 'kind': x['kind'], 'label': f"{x['code']} · {x['type']} · {c2(x['len_m'])} ml", 'status': ('Nuevo R29 (CU-02)' if x.get('new') else 'Modelado') + f" · {c2(x['w_m'] * 100).replace(',00', '')}×{c2(x['h_m'] * 100).replace(',00', '')}",
              'elementId': str(x['id']), 'roof': x['roof'], 'length_m': x['len_m'], 'volume_m3': round(x['len_m'] * x['w_m'] * x['h_m'], 4)} for x in d['framing']]
    codes += [{'code': x['code'], 'kind': 'CU', 'label': f"{x['code']} · {x['slope_deg']}° ({x['slope_pct']} %) · {c2(x['area_m2'])} m²", 'status': 'Agua con paquete R29', 'elementId': str(x['roof']), 'roof': x['roofCode'], 'area_m2': x['area_m2'], 'slope_deg': x['slope_deg']} for x in d['aguas']]
    quantities = [{'label': x['code'], 'group': f"Aguas · {x['roofCode']}", 'count': 1, 'value': x['area_m2'], 'unit': 'm²', 'detail': f"{x['slope_deg']}° · {x['slope_pct']} %"} for x in d['aguas']]
    quantities += [{'label': k, 'group': 'Bordes', 'count': 1, 'value': round(v, 2), 'unit': 'ml', 'detail': 'de la geometría del modelo'} for k, v in sorted(e.items())]
    quantities += [{'label': w['name'], 'group': 'Machimbre visto sobre locales (referencia)', 'count': 1, 'value': round(w['true_m2'], 2), 'unit': 'm²', 'detail': f"planta {c2(w['plan_m2'])} m² · {c2(w['slope'])}°"} for w in st['wood']]
    vc_m3 = st['volVC']
    budget = [('tejas', 'Teja cerámica (apta baja pendiente en CU-03)', A, 'm²', 'verdadera magnitud, 3 techos'),
              ('vigas-vc', 'Vigas VC LVL 6×20', st['VC'], 'ml', f"{st['nVC']} piezas · {c2(vc_m3)} m³ · incluye CU-02"),
              ('piezas-vp', 'Cabios VP LVL 5×15 c/0,96', st['VP'], 'ml', f"{st['nVP']} piezas · incluye CU-02"),
              ('correas-cr', 'Listones CR LVL 2,5×5', st['CR'], 'ml', 'paso según teja'),
              ('fascias', 'Fascias / zinguería de borde', next((l['value'] for l in old.get('budget', {}).get('lines', []) if l['id'] == 'fascias'), 0), 'ml', 'modeladas'),
              ('canaletas', 'Canaletas chapa galv. N°24', e['alero'], 'ml', 'modeladas + propuestas en todos los aleros'),
              ('alero-metalico', 'Alero metálico', next((l['value'] for l in old.get('budget', {}).get('lines', []) if l['id'] == 'alero-metalico'), 0), 'm²', 'AL-01, AL-02'),
              ('cubierta-machimbre', 'Machimbre pino 3/4" visto', A, 'm²', 'verdadera magnitud, incluye aleros'),
              ('cubierta-barrera-vapor', 'Barrera de vapor PE 200 µm', A, 'm²', 'solapes 10 cm'),
              ('cubierta-aislacion', 'EPS 75 mm 20 kg/m³ entre clavaderas', A * (1 - CLAV_W / SPACING), 'm²', 'neto, descontadas clavaderas'),
              ('cubierta-clavaderas', 'Clavaderas 5×7,5 sobre cabios', st['VP'], 'ml', '= ml de cabios'),
              ('cubierta-membrana', 'Membrana hidrófuga respirable', A, 'm²', 'continua bajo cumbreras y limahoyas'),
              ('cubierta-contraclavaderas', 'Contraclavaderas 2,5×5 (cámara ventilada)', st['VP'], 'ml', '= ml de cabios'),
              ('cubierta-cumbreras', 'Cumbreras ventiladas (pieza cerámica + perfil)', e['cumbrera'], 'ml', ''),
              ('cubierta-limatesas', 'Limatesas (pieza cerámica + perfil)', e['limatesa'], 'ml', ''),
              ('cubierta-limahoyas', 'Limahoyas chapa galv.', lima, 'ml', f"incluye {c2(e['limahoya horizontal'])} ml horizontales (canaleta interna a verificar)"),
              ('cubierta-babetas', 'Babetas / cupertinas contra muro', e['muro'], 'ml', ''),
              ('cubierta-bajadas', 'Bajadas Ø100', st['bajadas'], 'u', '1 por tramo y cada ≤10 ml de canaleta'),
              ('cubierta-herrajes', 'Herrajes: escuadras / colgadores galv. + tornillos', st['nVP'] * 2, 'u', '2 por cabio (apoyo inferior y superior, D-01c/d/e) · varillas Ø10 c/0,60 en soleras incluidas'),
              ('cubierta-peine', 'Peine anti-pájaros / rejilla de ventilación en aleros', e['alero'], 'ml', '= ml de canaleta (D-02a)'),
              ('cubierta-barniz-machimbre', 'Protector + barniz al agua del machimbre', A, 'm²', '2 manos, exterior en aleros'),
              ('cubierta-barniz-estructura', 'Protector + barniz de estructura vista', st['VC'] * .46 + st['VP'] * .35, 'm²', 'caras vistas VC (0,46 m²/ml) + VP (0,35 m²/ml)')]
    lines = [{'id': i, 'label': l, 'value': round(v, 2), 'unit': u, 'detail': dt, 'informative': False} for i, l, v, u, dt in budget]
    lines += [{'id': 'madera-total', 'label': 'Madera total (= VC + VP + CR)', 'value': round(st['vol'], 3), 'unit': 'm³', 'detail': 'referencia', 'informative': True},
              {'id': 'cubierta-machimbre-locales', 'label': 'Machimbre visto sobre locales (ver Cielorrasos)', 'value': round(sum(w['true_m2'] for w in st['wood']), 2), 'unit': 'm²',
               'detail': 'v. magnitud: ' + ', '.join(f"{w['name']} {c2(w['true_m2'])}" for w in st['wood']) + ' · ya incluido en cubierta-machimbre', 'informative': True}]
    totals = [{'label': l['label'], 'value': l['value'], 'unit': l['unit'], 'detail': l['detail']} for l in lines if l['id'] in ('vigas-vc', 'piezas-vp', 'correas-cr', 'canaletas', 'cubierta-cumbreras', 'cubierta-limatesas', 'cubierta-limahoyas', 'cubierta-bajadas', 'madera-total', 'tejas')]
    m = dict(old)
    m.update({'revision': 'R30', 'status': 'modelado', 'readAt': d['readAt'], 'sheets': out, 'codes': codes, 'quantities': quantities, 'totals': totals,
              'summary': f"Cubierta R29: 3 techos con paquete modelado (machimbre visto, barrera de vapor, EPS 75, membrana, cámara ventilada, teja) en {c2(A)} m²; cabios LVL 5×15 c/0,96 ({c2(st['VP'])} ml), vigas VC 6×20 ({c2(st['VC'])} ml), CU-02 con estructura. {len(out)} láminas (documentación en Casa-Angel-DOC-Cubierta.rvt).",
              'quantityNote': 'Cómputo desde el modelo vinculado: áreas de las caras inferiores (verdadera magnitud), largos de piezas, bordes clasificados por geometría (alero, cumbrera, limatesa, limahoya, encuentro con muro). Clavaderas sobre cabios c/0,96; EPS neto.',
              'notModeled': ['Clavaderas, contraclavaderas y zinguería nueva: computadas, no modeladas', 'Anclajes y escuadras metálicas (computadas como herrajes, ver D-03)', 'Cálculo estructural de vigas VC'],
              'decisions': ['Usuario: confirma el paquete (machimbre 3/4" visto + film + EPS 75 entre clavaderas + membrana respirable + cámara ventilada + teja) y CU-02 con la misma estructura que CU-01.',
                            'Usuario: CU-03 mantiene 16,8° con teja apta baja pendiente y membrana continua (recomendado).',
                            'Usuario: modelar sin cambiar la morfología; se redimensionaron cabios VP a LVL 5×15 (3×10 no verificaba: σ≈6 MPa, flecha≈L/530 a c/0,96 y luz 3,4 m) y listones CR a 2,5×5; VC 6×20 a verificar por calculista.',
                            'Clavaderas sobre cabios c/0,96 (no c/0,60) para no cargar el machimbre (acordado con el rubro).',
                            'Documentación en archivo propio Casa-Angel-DOC-Cubierta.rvt que vincula el modelo principal (criterio del usuario).'],
              'questions': [],
              'budget': {'revision': 'R30', 'note': 'Partidas sin solapes; existente + propuesto en el mismo id; informative = referencia.', 'lines': lines}})
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'new': len(new), 'budget': [(l['id'], l['value'], l['unit']) for l in lines]}, ensure_ascii=False))


if __name__ == '__main__': main()
