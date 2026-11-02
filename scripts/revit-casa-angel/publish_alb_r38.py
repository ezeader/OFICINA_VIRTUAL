"""R38 Albañilería: publish the master plans ALB-PB/PA/PE-01 and the wall detail sheets ALB-<lv>-02.. (Casa-Angel-DOC-Albanileria.rvt)
on top of the R28 manifest (decisions, questions, budget, TM fichas and ALB-00 kept). Codes: one M-<lv>-nn per wall (with the previous AB code)."""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate
from dom_rules_r35 import fix

KEY = 'albanileria'; BASE = f'/casa-angel/rubros/{KEY}/'
LVN = {'PB': '00. Planta Baja', 'PA': '01. Planta Alta', 'PE': '02. Planta Entrepiso'}
CATN = {'HV': 'H° visto', 'EI': 'Exterior – interior', 'II': 'Interior – interior', 'OT': 'Otros'}


def c2(x): return ('%.2f' % x).replace('.', ',')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); ap.add_argument('--base', type=Path, required=True); a = ap.parse_args()
    m = json.loads(a.base.read_text(encoding='utf-8'))          # R28 manifest (rubro session branch)
    sheets = fix(read(OUT / 'alb38-sheets.json')['sheets']); walls = fix(read(OUT / 'alb38-model.json')['walls'])
    pub = a.public_dir / 'rubros' / KEY; pub.mkdir(parents=True, exist_ok=True)
    byid = {str(w['id']): w for w in walls}
    prev_ab = {c.get('elementId'): c['code'] for c in m['codes'] if c.get('kind') == 'AB'}
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r38-{n}.pdf'; assert src.exists(), n
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
            els = [{'code': x['code'], 'elementId': x['elementId'], 'label': x['label'], 'box': x['box']} for x in v.get('albElements', [])]
            views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                          'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                          'tags': v['tags'], 'dimensions': [{'label': x['label'], 'values_m': x['values_m'], 'associative': x.get('associative')} for x in v.get('dims', [])], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        new.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'kind': 'general', 'element': None, 'elementId': None, 'elementKind': None,
                    'walls': s.get('walls'), 'note': 'R38 · archivo Casa-Angel-DOC-Albanileria.rvt', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz',
                    'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    nums = {x['number'] for x in new}
    kept = [s for s in m['sheets'] if s['number'] not in nums and s['number'] not in ('ALB-PB-01', 'ALB-PA-01', 'ALB-PE-01')]
    m['sheets'] = sorted(new, key=lambda s: s['number']) + kept
    tm = [c for c in m['codes'] if c.get('kind') == 'TM']
    mc = []
    for w in sorted([w for w in walls if w.get('code')], key=lambda w: w['code']):
        t = 'H° (Estructura)' if w['typeCode'] == 'HA' else w['typeCode']
        mc.append({'code': w['code'], 'kind': 'M', 'elementId': str(w['id']), 'level': LVN[w['level']], 'typeCode': t, 'type': w['type'], 'category': CATN[w['cat']],
                   'structure': bool(w['concrete']), 'previous': prev_ab.get(str(w['id'])), 'length_m': w['length_m'], 'height_m': w['height_m'], 'thickness_m': w['thickness_m'],
                   'area_m2': round(w['length_m'] * w['height_m'], 3), 'openings': len(w['openings']),
                   'label': '%s · %s · %s × %s × %s' % (w['code'], t, c2(w['length_m']), c2(w['height_m']), c2(w['thickness_m']))})
    m['codes'] = tm + mc
    m['kinds'] = dict(m.get('kinds', {}), M='Muro (código por nivel, izquierda→derecha y arriba→abajo)')
    m['revision'] = 'R38'
    m['summary'] = 'Albañilería R38: planos maestros por planta (PB, PA, PE) con los muros coloreados por categoría y un código por muro (M-PB-01…), cuadro de medidas, y láminas de detalle con la vista y el corte de cada muro. ' + m.get('summary', '')
    m.setdefault('decisions', [])
    t = 'R38: planos maestros y detalle por muro en Casa-Angel-DOC-Albanileria.rvt (modelo principal vinculado, sin cambios); códigos M-<nivel>-nn reemplazan a los AB (campo previous); los muros de H° van en gris y se computan en Estructura.'
    if t not in m['decisions']: m['decisions'].append(t)
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': sorted(nums), 'codes': len(mc), 'kept': [s['number'] for s in kept]}, ensure_ascii=False))


if __name__ == '__main__': main()
