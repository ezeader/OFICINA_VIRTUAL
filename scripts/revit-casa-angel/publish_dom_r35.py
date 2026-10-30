"""R35 Domótica etapa 2: publish the 12 DOM sheets (Casa-Angel-DOC-Domotica.rvt) into public/casa-angel/rubros/domotica/manifest.json
with codes {code, kind, system, level, room, mount, base|opc} and quantities per system (base / opc). Budget untouched (etapa 4)."""
import argparse, json, shutil, sys, collections
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg
from publish_structure_r11 import calibrate
from dom_rules_r35 import fix

KEY = 'domotica'; BASE = f'/casa-angel/rubros/{KEY}/'
SYSN = {'IL': 'Iluminación y sensores', 'CR': 'Cortinas', 'CL': 'Climatización', 'CA': 'Cámaras', 'RD': 'Red, rack, tableros y energía', 'AU': 'Audio', 'AC': 'Acceso', 'RG': 'Riego', 'SG': 'Seguridad técnica'}
LVN = {'PB': '00. Planta Baja', 'PA': '01. Planta Alta', 'PE': '02. Planta Entrepiso'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    pl = json.loads((OUT / 'dom35-plan.json').read_text(encoding='utf-8')); sheets = fix(read(OUT / 'dom35-sheets.json')['sheets'])
    pub = a.public_dir / 'rubros' / KEY; m = json.loads((pub / 'manifest.json').read_text(encoding='utf-8'))
    new = []
    for s in sheets:
        n = s['number']; src = OUT / f'r35-{n}.pdf'; assert src.exists(), n
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
            els = [dict({'code': x['code'], 'label': x['label'], 'box': x['box']}, **({'room': True, 'elementId': x['elementId']} if x.get('room') else {})) for x in v.get('domElements', [])]
            views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'), 'roomLabel': v.get('sector'),
                          'image': BASE + file, 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                          'tags': v['tags'], 'dimensions': [], 'elements': els})
        assert n in page.get_text(), n
        pdf.close()
        sysk = s.get('system')
        new.append({'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': SYSN.get(sysk, 'General'), 'kind': 'general', 'element': None, 'elementId': None, 'elementKind': None,
                    'system': sysk, 'note': 'R35 · archivo Casa-Angel-DOC-Domotica.rvt', 'sheetId': str(s['sheetId']), 'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz',
                    'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png', 'views': views})
    els = pl['elements']
    codes = [{'code': e['code'], 'kind': e['kind'], 'system': e['system'], 'type': e['type'], 'level': LVN[e['level']], 'room': e['room'], 'mount': e['mount'],
              'scope': 'opc' if e['opt'] else 'base', 'label': '%s · %s · %s' % (e['code'], e['type'], e['room']), 'note': e.get('note') or None,
              **({'zone': e['zone']} if e.get('zone') else {}), **({'width_m': e['width']} if e.get('width') else {})} for e in els]
    q = []
    for x in pl['quantities']:
        if x['kind'] == 'LZ': continue
        for sc in ('base', 'opc'):
            if x[sc]: q.append({'label': '%s · %s' % (x['type'], sc), 'group': SYSN[x['system']], 'count': x[sc], 'value': x[sc], 'unit': 'u', 'detail': '%s (%s)' % (x['kind'], sc),
                                'system': x['system'], 'kind': x['kind'], 'scope': sc})
    zones = collections.Counter(e['zone'] for e in els if e['kind'] == 'LZ')
    tot = collections.Counter(); opc = collections.Counter()
    for e in els:
        if e['kind'] == 'LZ': continue
        (opc if e['opt'] else tot)[e['system']] += 1
    m.update(revision='R35', readAt=read(OUT / 'dom35-sheets.json')['readAt'], model='Casa-Angel-DOC-Domotica.rvt (modelo principal vinculado)',
             summary='Domótica etapa 2: ubicación en planta de %d elementos base y %d opcionales en 12 láminas (índice, iluminación por nivel y una por sistema). Locales: %d nivel A, %d B, %d C.'
             % (sum(tot.values()), sum(opc.values()), zones['A'], zones['B'], zones['C']),
             kinds={e['kind']: e['type'] for e in els}, sheets=new, codes=codes, quantities=q,
             totals=[{'label': SYSN[k], 'value': tot[k], 'unit': 'u', 'detail': 'base %d · opc %d' % (tot[k], opc[k])} for k in SYSN if tot[k] or opc[k]] +
                    [{'label': 'Locales por nivel de iluminación', 'value': sum(zones.values()), 'unit': 'locales', 'detail': 'A %d · B %d · C %d' % (zones['A'], zones['B'], zones['C'])}],
             revisar=list(dict.fromkeys(pl['revisar'])))
    m.setdefault('decisions', [])
    t = 'R35 etapa 2: símbolos 2D por reglas sobre locales y aberturas del modelo, en Casa-Angel-DOC-Domotica.rvt (el modelo principal no se toca); presupuesto en la etapa 4.'
    if t not in m['decisions']: m['decisions'].append(t)
    (pub / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': [x['number'] for x in new], 'codes': len(codes), 'base': sum(tot.values()), 'opc': sum(opc.values())}, ensure_ascii=False))


if __name__ == '__main__': main()
