"""R31 Estructura: publish EST-FU-01 and EST-F-LO-PB-01 (Casa-Angel-DOC-Estructura.rvt) into public/casa-angel/structure/manifest.json
(replaces those two sheets; adds PL-02 = ampliación de platea 2488978; LO-PB-01 as floor package; decisions / openQuestions)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate

BASE = '/casa-angel/structure/'; PT_PER_FT = 2383.94 / 2.7592
CODES = {'2287528': 'PL-01', '2488978': 'PL-02', '714161': 'LO-PB-01'}


def c2(v): return ('%.2f' % v).replace('.', ',')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path); ap.add_argument('--request', action='store_true'); a = ap.parse_args()
    sheets = read(OUT / 'est31-sheets.json')['sheets']
    if a.request:
        views = [{'rev': 'R31', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'est31-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'structure'; m = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    proj = {str(p['id']): p for p in read(OUT / 'est31-elements.json')}
    pla = read(OUT / 'est31-platea.json'); chk = read(OUT / 'est31-checks.json')['elements']
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r31-{n}.pdf'; assert src.exists(), n
        shutil.copy2(src, pub / f'{n}.pdf')
        pdf = fitz.open(src); page = pdf[0]; pw, ph = page.rect.width, page.rect.height
        svg(page, pub / f'{n}.svg.gz'); page.get_pixmap(matrix=fitz.Matrix(.6, .6)).save(pub / f'{n}-preview.png'); page.get_pixmap(matrix=fitz.Matrix(.35, .35)).save(pub / f'{n}.png')
        scale, ox, oy, used, res = calibrate(page, [(x['text'], x['anchor']) for x in s['notes']] + [(v['label'], v['anchor']) for v in s['views']])
        views = []
        for v in s['views']:
            lo, hi = v['box']
            rect = fitz.Rect(ox + lo[0] * scale - 3, oy - hi[1] * scale - 3, ox + hi[0] * scale + 3, oy - lo[1] * scale + 3) & page.rect
            crop = fitz.open(); p = crop.new_page(width=rect.width, height=rect.height); p.show_pdf_page(p.rect, pdf, 0, clip=rect)
            file = f"{n}-view-{v['id']}.svg.gz"; svg(p, pub / file); crop.close()
            els = [{'code': CODES[r['elementId']], 'elementId': r['elementId'], 'box': [round(x, 4) for x in r['box']]} for r in proj.get(str(v['id']), {}).get('elements', []) if r['elementId'] in CODES]
            views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'), 'caseId': None,
                          'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                          'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v['dims']], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        rec = {'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': s.get('kind', 'general'), 'note': 'R31 · archivo Casa-Angel-DOC-Estructura.rvt',
               'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'outsideCrop': [], 'views': views}
        if s.get('element'): rec.update(element=s['element'], elementId=s['elementId'], elementKind=s['elementKind'], rebar=('Paquete de piso: sin armadura propia (la platea PL-02 lleva la malla).' if s['element'] == 'LO-PB-01' else 'Malla superior e inferior por cuantía de referencia hasta el cálculo.'))
        new.append(rec)
    nums = [x['number'] for x in new]
    m['sheets'] = [x if x['number'] not in nums else next(y for y in new if y['number'] == x['number']) for x in m['sheets']]
    for x in new:
        if x['number'] not in [y['number'] for y in m['sheets']]: m['sheets'].append(x)
    codes = m['codes']
    lo = next(c for c in codes if c['code'] == 'LO-PB-01')
    off = read(OUT / 'est31-lopb-offset.json'); lz = [f[0] for f in off['horizFaces']]
    lo.update(status='Paquete de piso sobre platea (no losa de H°) · R31 · cambiado en el modelo', label=f"LO-PB-01 · {c2(lo['area_m2'])} m² · paquete de piso 11 cm sobre PL-02",
              type=off['type'], thickness_m=0.11, concreteLayer_m=0, structural=False, top_m=max(lz), bottom_m=min(lz),
              note=f"R31 (OK usuario): tipo «{off['type']}» (membrana hidrófuga + carpeta 11 cm, no estructural), desfase −0,30 → −0,09: {c2(min(lz))} / {c2(max(lz))}, apoya sobre la platea (−0,20) sin superposición. Fuera del cómputo de H°.")
    for e in m.get('slabsAndFoundations', []):
        if str(e.get('id')) == '714161':
            vol = round(lo['area_m2'] * .11, 3); old_v = e.get('volume_m3') or 0
            e.update(type=off['type'], thickness_m=0.11, volume_m3=vol, structural=False, concreteLayer_m=0, offset_m=off['offset_m'])
            for g in m.get('slabSummary', []):
                if g['key'] == '00. Planta Baja | Losa / estructura' and abs(g['area_m2'] - lo['area_m2']) < .01: g['key'] = '00. Planta Baja | Paquete de piso (sin capa de hormigón) · LO-PB-01'; g['volume_m3'] = vol
    if not any(c['code'] == 'PL-02' for c in codes):
        i = next(k for k, c in enumerate(codes) if c['code'] == 'PL-01')
        codes.insert(i + 1, {'id': '2488978', 'code': 'PL-02', 'kind': 'PL', 'level': '00. Planta Baja', 'label': f"PL-02 · {c2(pla['area_m2'])} m² · ampliación de platea R31", 'status': 'Modelado R31 (OK usuario) · tipo Platea PB 15CM bajo LO-PB-01',
                                 'type': 'Platea PB 15CM', 'area_m2': pla['area_m2'], 'volume_m3': round(pla['area_m2'] * .15, 3), 'concreteLayer_m': 0.15, 'thickness_m': 0.15, 'typeVolume_m3': pla['volume_m3']})
    tot_a = chk['2287528']['area_m2'] + pla['area_m2']
    m.setdefault('decisions', [])
    for t in [f"R31: platea ampliada (PL-02, {c2(pla['area_m2'])} m²) bajo toda la huella de LO-PB-01 con OK del usuario; platea total {c2(tot_a)} m².",
              'R31: LO-PB-01 documentado como paquete de piso sobre platea (EST-F-LO-PB-01, corte tipo en EST-FU-01).',
              'R31 (OK usuario): LO-PB-01 cambiado en el modelo a «ADER Paquete de piso sobre platea 11cm» y subido a −0,20 / −0,09; el hormigón de PB se computa solo en la platea (PL-01 + PL-02).',
              'R31: ficha EST-F-PL-02 (ampliación de platea, H° e 15).']:
        if t not in m['decisions']: m['decisions'].append(t)
    m['openQuestions'] = [q for q in m.get('openQuestions', []) if 'tipo de LO-PB-01' not in q]   # answered: changed in the model (R31)
    m['documentationRevision'] = 'R31'
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': nums, 'plateaTotal_m2': round(tot_a, 3), 'codes': len(codes)}, ensure_ascii=False))


if __name__ == '__main__': main()
