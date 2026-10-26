"""R34 Parrilla de obra a medida: publish PAR-00 / P-01 / D-01 / D-02 / D-03 (Casa-Angel-DOC-Parrilla.rvt) into
public/casa-angel/rubros/parrilla/manifest.json. Hover parts come recorded in each view (drawn design, no model elements).
Budget keeps ids `parrilla` and `conducto-humos` (meaning updated) and adds the parts of the parrilla de obra."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

KEY = 'parrilla'; BASE = f'/casa-angel/rubros/{KEY}/'; NOTE = 'R34 · archivo Casa-Angel-DOC-Parrilla.rvt'
FILES = ('par34-index.json', 'par34-plans.json', 'par34-details.json')
SOURCE = 'California Residential Code 2025, cap. 10 (R1001 hogares de mampostería, R1003 chimeneas): https://gocodebook.com/es/library/us/ca/ca-residential-code/chapter-10-chimneys-and-fireplaces/section-r1003-masonry-chimneys'

# design (same constants as revit_par_r34.py)
JA, BOCA, LANA, FONDO, HOGAR, FRENTE = .12, 1.50, .025, .064, .60, .12
WIDTH = 2 * JA + BOCA + LANA; DEPTH = FONDO + HOGAR + FRENTE
Z_LOSA1, Z_BOCA, Z_CIELO, Z_LO1, Z_TOP = .84, 1.50, 2.50, 3.00, 9.40
import math
CH_X, CH_X2, Z_OFF0, OFF_DEG = 3.92, 4.388, 3.10, 30.0
Z_OFF1 = Z_OFF0 + (CH_X2 - CH_X) / math.tan(math.radians(OFF_DEG)); DIAG = (CH_X2 - CH_X) / math.sin(math.radians(OFF_DEG))
CAJON_NEW_X, CAJON = 3.645, (4.063, 1.882, 4.738, 3.232)


def c2(v): return ('%.2f' % v).replace('.', ',')


def compute():
    jambas = 2 * DEPTH * Z_CIELO; frente = BOCA * (Z_CIELO - Z_BOCA); canto = jambas + frente
    fondo = BOCA * (Z_CIELO - Z_LOSA1); solera = BOCA * HOGAR; plano = fondo + solera
    ladrillos = round((canto * 55 + plano * 33) * 1.10 / 10) * 10
    return {'jambas': jambas, 'frente': frente, 'canto': canto, 'fondo': fondo, 'solera': solera, 'plano': plano, 'ladrillos': ladrillos,
            'mortero_kg': round(ladrillos / 90 + .49) * 25, 'losa': BOCA * DEPTH * .10, 'dintel': 2 * (WIDTH - LANA), 'lana': DEPTH * Z_CIELO,
            'ch_simple': Z_LO1 - Z_CIELO, 'ch_doble': (Z_OFF0 - Z_LO1) + DIAG + (Z_TOP - Z_OFF1),
            'cajon': ((CAJON[3] - CAJON[1]) + 2 * (CAJON[0] - CAJON_NEW_X)) * 1.0}


def budget(q):
    L = [('parrilla-refractario-visto', 'Mampostería de ladrillo refractario visto 12 cm (jambas + frente de campana)', q['canto'], 'm²', f"jambas {c2(q['jambas'])} + frente {c2(q['frente'])} · junta tomada"),
         ('parrilla-refractario-plano', 'Revestimiento refractario de plano 6,4 cm (fondo + solera)', q['plano'], 'm²', f"fondo {c2(q['fondo'])} + solera {c2(q['solera'])} · mortero refractario"),
         ('parrilla-losa-base', 'Losa base H°A° 10 cm sobre jambas', q['losa'], 'm³', f"{c2(BOCA)} × {c2(DEPTH)} × 0,10"),
         ('parrilla-dintel', 'Dintel 2 L 2½" × ¼" (frente y trasdós)', q['dintel'], 'ml', 'acero, con pintura antióxido de alta temperatura'),
         ('parrilla-aislacion', 'Placa de lana cerámica 25 mm contra el tabique', q['lana'], 'm²', 'jamba este'),
         ('parrilla', 'Parrilla regulable acero inox 1,00 × 0,55 con elevación a manivela', 1, 'u', 'incluye bandeja recolectora de grasa'),
         ('parrilla-brasero', 'Brasero (canasto) de hierro 0,35 × 0,50', 1, 'u', ''),
         ('parrilla-garganta', 'Garganta de chapa 2 mm + registro de tiro (mariposa) en el collar Ø 35', 1, 'u', 'de +1,90 al collar, paredes ≤ 45°'),
         ('conducto-humos', 'Conducto Ø 35 acero inox simple pared (plenum PB)', q['ch_simple'], 'ml', f"+{c2(Z_CIELO)} a +{c2(Z_LO1)}"),
         ('conducto-humos-doble', 'Conducto Ø 35 doble pared aislado (PA a la vista, cruce de cubierta y remate)', q['ch_doble'], 'ml', f"+{c2(Z_LO1)} a +{c2(Z_TOP)} · incluye desvío {c2(DIAG)} ml"),
         ('conducto-codos', 'Codos 30° doble pared Ø 35', 2, 'u', 'desvío de 0,47 m dentro del cajón'),
         ('parrilla-puertas-lenero', 'Puertas del leñero 2 hojas chapa N°18 con marco L 1"', 1, 'u', f'{c2(BOCA)} × 0,69 · bisagras y tiradores'),
         ('parrilla-cajon-durlock', 'Ampliación del cajón Durlock del Comedor (placa RF)', q['cajon'], 'm²', 'tabique 0,42 m al oeste, de +3,00 a +4,00 (modelado)'),
         ('conducto-pase-losa', 'Pase en losa L01 0,50 × 0,50 (amplía el pase existente)', 1, 'u', 'a coordinar con Estructura'),
         ('conducto-babeta', 'Babeta / collar de cubierta + brochal entre cabios', 1, 'u', 'CU-03 · pase 0,50 × 0,50'),
         ('conducto-sombrerete', 'Sombrerete fijo acero inox Ø 0,70 con malla antichispa', 1, 'u', '')]
    lines = [{'id': i, 'label': l, 'value': round(v, 3 if u == 'm³' else 2), 'unit': u, 'detail': d, 'informative': False} for i, l, v, u, d in L]
    lines += [{'id': 'parrilla-ladrillos', 'label': 'Ladrillos refractarios 23 × 11,4 × 6,4 (referencia)', 'value': q['ladrillos'], 'unit': 'u', 'detail': '55 u/m² de canto · 33 u/m² de plano · +10 % · ya incluidos en las partidas de mampostería', 'informative': True},
              {'id': 'parrilla-mortero', 'label': 'Mortero refractario (referencia)', 'value': q['mortero_kg'], 'unit': 'kg', 'detail': '≈ 1 bolsa de 25 kg cada 90 ladrillos', 'informative': True},
              {'id': 'parrilla-k42db', 'label': 'Equipo K42DB modelado (reemplazado por la parrilla de obra)', 'value': 0, 'unit': 'u', 'detail': 'borrado del modelo (OK del usuario 26/10)', 'informative': True}]
    return lines


def index_columns():
    q = compute(); b = budget(q)
    comp = [f"{l['label'].split(' (')[0]}: {c2(l['value'])} {l['unit']}" for l in b if not l['informative']]
    return [{'title': 'Diseño (decisión del usuario 26/10)', 'lines': ['Parrilla de obra a medida en el Quincho', 'Boca 1,50 · hogar +0,90 · boca alta 0,60', 'Campana de ladrillo refractario visto hasta el cielorraso +2,50',
                                                                  'Conducto Ø 35 por cubierta, remate +9,40', 'En PA: a la vista desde +4,00 junto al ducto del hogar', 'Leñero con puertas de 2 hojas', 'Sombrerete fijo con malla antichispa', f"Medida exterior {c2(WIDTH)} × {c2(DEPTH)} m"]},
            {'title': 'Cómputo', 'lines': comp[:7]}, {'title': 'Cómputo (cont.)', 'lines': comp[7:] + [f"Ladrillos refractarios ≈ {q['ladrillos']} u", f"Mortero refractario ≈ {q['mortero_kg']} kg"]},
            {'title': 'Láminas R34', 'lines': ['PAR-00  Índice y cómputo', 'PAR-P-01  Ubicación PB · PA · techo', 'PAR-D-01  Planta, vista y corte 1:20', 'PAR-D-02  Conducto: corte esquemático', 'PAR-D-03  Cruce de cubierta y sombrerete', 'PAR-D-04  Tiraje: verificación + 3D',
                                               '', 'Modelo principal: K42DB reemplazado,', 'cajón ampliado (OK del usuario 26/10).']}]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--index-columns', action='store_true'); a = ap.parse_args()
    if a.index_columns: print(json.dumps(index_columns(), ensure_ascii=True)); return
    pub = a.public_dir / 'rubros' / KEY; old = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    sheets = sum((read(OUT / fn)['sheets'] for fn in FILES), [])
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r34-{n}.pdf'; assert src.exists(), n
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
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                              'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']],
                              'elements': [{'code': e['code'], 'label': e['label'], 'box': e['box']} for e in v['elements']]})
        assert n in page.get_text(), n
        pdf.close()
        new.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': 'general', 'element': None, 'elementId': None, 'elementKind': None,
                    'note': NOTE, 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    q = compute(); lines = budget(q)
    parts = {}
    for s in new:
        for v in s['views']:
            for e in v['elements']: parts.setdefault(e['code'], e['label'])
    pil = read(OUT / 'par34-pilot.json'); ids = {c['code']: str(c['id']) for c in pil['created']}
    codes = [{'code': k, 'kind': k[:2], 'label': lab, 'status': 'Modelado R34 en el modelo principal (DirectShape)' if k in ids else ('Existente (hogar de PA)' if k == 'CH-02' else 'Documentado R34'), 'elementId': ids.get(k)} for k, lab in sorted(parts.items())]
    codes += [{'code': 'K42DB', 'kind': 'PR', 'label': 'K42DB · equipo borrado del modelo (reemplazado)', 'status': 'Borrado 26/10 con OK del usuario (era 743956; conducto Ø 25 738025)', 'elementId': None}]
    m = dict(old)
    m.update({'revision': 'R34', 'status': 'modelado', 'readAt': read(OUT / 'par34-details.json')['readAt'], 'kinds': {'PR': 'Parrilla', 'CH': 'Conducto de humos'},
              'sheets': sorted(new, key=lambda s: (s['number'] != 'PAR-00', s['number'])), 'codes': codes,
              'summary': f"Parrilla de obra a medida en el Quincho (decisión del usuario): boca 1,50, hogar a +0,90, campana de ladrillo refractario visto hasta el cielorraso, parrilla regulable inox + brasero, leñero; conducto Ø 35 ({c2(q['ch_simple'] + q['ch_doble'])} ml) por el Comedor y la cubierta CU-03 con sombrerete fijo. en PA sube a la vista junto al ducto del hogar. Modelada en el modelo principal (reemplaza al K42DB; cajón Durlock ampliado) y documentada en 6 láminas en Casa-Angel-DOC-Parrilla.rvt.",
              'totals': [{'label': l['label'], 'value': l['value'], 'unit': l['unit'], 'detail': l['detail']} for l in lines if l['id'] in ('parrilla-refractario-visto', 'parrilla-refractario-plano', 'conducto-humos', 'conducto-humos-doble', 'parrilla-ladrillos')],
              'quantities': [{'label': l['label'], 'group': 'Conducto' if l['id'].startswith('conducto') else 'Parrilla', 'count': 1, 'value': l['value'], 'unit': l['unit'], 'detail': l['detail']} for l in lines if not l['informative']],
              'quantityNote': 'Cómputo del diseño R34 (modelado con DirectShape): superficies de mampostería por cara, conducto por cotas de nivel (cielorraso +2,50, PA +3,00, remate +9,40 ≥ cumbrera +8,63 + 0,60).',
              'notModeled': ['Garganta de chapa y registro de tiro (solo en láminas)', 'Babeta, brochal y pase de losa (solo en láminas)', 'Mesada vecina (existente, Equipamiento)'],
              'decisions': ['Usuario (26/10): parrilla de obra a medida (no el K42DB).', 'Usuario: boca 1,50 m y campana hasta el cielorraso.', 'Usuario: ladrillo refractario visto.', 'Usuario: conducto por cubierta con sombrerete fijo.',
                            'Tiraje (R1003.15, conducto redondo ≥ 1/12 de la boca): boca 1,50 × 0,60 = 0,90 m² → Ø 35 = 0,096 m² = 1/9,4 (el Ø 30 previo daba 1/13,8 sobre boca 0,65: insuficiente). Conducto simple pared en el plenum de PB, doble pared aislado desde la PA por el Comedor (madera vista) y la cubierta.',
                            'Conducto contra la jamba este (eje x 3,92 · y 2,30): pasa entre cabios c/0,96 (corta 1 listón, con brochal); remate +9,40 ≥ cumbrera +8,63 + 0,60 y ≥ techo +8,06 + 0,90 (R1003.9). Garganta desde +1,90 para que las paredes de la campana queden ≤ 45° (R1001.8.1).', 'Criterio de tiraje tomado de ' + SOURCE + ' · verificar con normativa local.', 'Usuario (26/10): ampliar el cajón, reemplazar el K42DB en el modelo y leñero con puertas; el conducto sube a la vista en PA junto al ducto del hogar (CH-02): desvío de 0,47 m con 2 codos a 30° dentro del cajón.', 'Usuario (vía sesión Documentación): parrilla estándar de mampostería hecha in situ; lo crítico es el tiraje. Modelada en 3D en el archivo DOC (DirectShape, Generic Models); no se descargó ninguna familia (las encontradas requieren cuenta).',
                            'Documentación en archivo propio Casa-Angel-DOC-Parrilla.rvt que vincula el modelo principal (criterio del usuario).'],
              'questions': ['El pase existente en la losa L01 (0,30 × 0,57, x 3,93–4,23) no coincide con el conducto (eje x 3,92 · y 2,30): ¿lo ajusto en el modelo a 0,50 × 0,50? (Estructura)',
                            'El conducto a la vista y el del hogar pasan delante de la ventana del Comedor (x 4,54–4,89, +4,13 a +5,27): ¿ok así?'],
              'budget': {'revision': 'R34', 'note': 'Partidas del diseño R34; informative = referencia (no se suma).', 'lines': lines}})
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': [s['number'] for s in m['sheets']], 'views': sum(len(s['views']) for s in new), 'lines': len(lines)}, ensure_ascii=False))


if __name__ == '__main__': main()
