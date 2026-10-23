"""Publish structure sheets (EST-*) and extend public/casa-angel/structure/manifest.json (additive).

Step 1 (--request): write openings-r4/est-request.json for the read-only projection job.
Step 2 (default): copy PDFs, write sheet/view svg.gz + PNGs, add manifest['sheets'] and manifest['codes'].
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime')); sys.path.insert(0, str(ROOT))
import pymupdf as fitz
from publish_openings_r4 import read, svg, norm


def calibrate(page, anchors):
    """Robust sheet-feet -> PDF-points map: fixed A1 scale, offsets from the median of exact text matches."""
    lines = [(norm(''.join(s['text'] for s in l['spans'])), fitz.Rect(l['bbox'])) for b in page.get_text('dict')['blocks'] for l in b.get('lines', [])]
    pairs = [(ax, ay, r.x0, r.y0) for text, (ax, ay) in anchors for t, r in lines if t == norm(text) or (len(norm(text)) > 30 and t.startswith(norm(text)[:30]))]
    assert pairs, 'no anchors'
    # Fit-to-page can shrink a sheet whose annotations overflow the border: estimate the scale from anchor pairs.
    est = []
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            p, q = pairs[i], pairs[j]
            if abs(p[1] - q[1]) > .1: est.append(-(p[3] - q[3]) / (p[1] - q[1]))
            if abs(p[0] - q[0]) > .1: est.append((p[2] - q[2]) / (p[0] - q[0]))
    est = sorted(e for e in est if 500 < e < 1000)
    scale = est[len(est) // 2] if est else page.rect.width / 2.7592
    xs = sorted(p[2] - p[0] * scale for p in pairs); ys = sorted(p[3] + p[1] * scale for p in pairs)
    ox, oy = xs[len(xs) // 2], ys[len(ys) // 2]
    inl = [p for p in pairs if abs(ox + p[0] * scale - p[2]) < 3 and abs(oy - p[1] * scale - p[3]) < 3]
    assert len(inl) >= 1, 'calibration: no consistent anchor'
    return scale, ox, oy, len(inl), max(max(abs(ox + p[0] * scale - p[2]), abs(oy - p[1] * scale - p[3])) for p in inl)

BASE = '/casa-angel/structure/'
PARTS = ['est-index.json', 'est-plans.json', 'est-sec-311.json', 'est-sec-694.json', 'est-sec-353988.json', 'est-review.json']
PT_PER_FT = 2383.94 / 2.7592


def records():
    out = []
    for f in PARTS + sorted(x.name for x in OUT.glob('est-f-g*.json')):
        p = OUT / f
        if p.exists(): out += read(p)['sheets']
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); ap.add_argument('--request', action='store_true'); a = ap.parse_args()
    sheets = records()
    if a.request:
        views = [{'rev': 'R11', 'id': v['id'], 'box': v['box'], 'margin_ft': 3 / PT_PER_FT, 'elements': v['elements']} for s in sheets for v in s['views']]
        (OUT / 'est-request.json').write_text(json.dumps({'views': views}), encoding='utf-8'); print(len(views)); return
    pub = a.public_dir / 'structure'; pub.mkdir(parents=True, exist_ok=True)
    mpath = pub / 'manifest.json'; m = json.loads(mpath.read_text(encoding='utf-8'))
    plan = read(OUT / 'structure-plan.json'); code = {str(e['id']): e['code'] for e in plan['elements']}
    opening = {str(i['id']): i['code'] for i in read(OUT / 'plan.json')['items']}
    proj = {str(p['id']): p for p in read(OUT / 'est-elements.json')}
    out = []
    for s in sorted(sheets, key=lambda s: s['number']):
        n = s['number']; src = OUT / f'r11-{n}.pdf'; assert src.exists(), n
        shutil.copy2(src, pub / f'{n}.pdf')
        pdf = fitz.open(src); page = pdf[0]; pw, ph = page.rect.width, page.rect.height
        svg(page, pub / f'{n}.svg.gz')
        page.get_pixmap(matrix=fitz.Matrix(.6, .6)).save(pub / f'{n}-preview.png')
        page.get_pixmap(matrix=fitz.Matrix(.35, .35)).save(pub / f'{n}.png')
        views = []
        if s['views']:
            scale, ox, oy, used, res = calibrate(page, [(x['text'], x['anchor']) for x in s['notes']] + [(v['label'], v['anchor']) for v in s['views']])
            for v in s['views']:
                lo, hi = v['box']
                rect = fitz.Rect(ox + lo[0] * scale - 3, oy - hi[1] * scale - 3, ox + hi[0] * scale + 3, oy - lo[1] * scale + 3) & page.rect
                crop = fitz.open(); p = crop.new_page(width=rect.width, height=rect.height); p.show_pdf_page(p.rect, pdf, 0, clip=rect)
                file = f"{n}-view-{v['id']}.svg.gz"; svg(p, pub / file); crop.close()
                rows = proj.get(str(v['id']), {}).get('elements', [])
                views.append({'id': str(v['id']), 'name': v['name'], 'label': v['label'], 'scale': v['scale'], 'kind': v['kind'], 'sector': v.get('sector'),
                              'roomLabel': v.get('sector'), 'caseId': v.get('caseId'), 'image': BASE + file,
                              'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)],
                              'tags': v['tags'], 'dimensions': v['dims'],
                              'elements': [{'code': code.get(r['elementId']) or opening.get(r['elementId']), 'elementId': r['elementId'], 'box': [round(x, 4) for x in r['box']]} for r in rows]})
        assert n in page.get_text(), f'sheet number missing in {n}'
        pdf.close()
        extra = {'kind': 'element', 'element': s['element'], 'elementId': s.get('elementId'), 'elementKind': s.get('elementKind'),
                 'rebar': 'Armadura: a definir por el calculista.'} if s.get('kind') == 'element' else {'kind': 'general'}
        out.append({**extra, 'number': n, 'title': s['title'], 'level': s.get('level'), 'sector': s.get('sector'), 'sheetId': str(s['sheetId']),
                    'pdf': BASE + f'{n}.pdf', 'image': BASE + f'{n}.svg.gz', 'preview': BASE + f'{n}-preview.png', 'thumbnail': BASE + f'{n}.png',
                    'outsideCrop': s.get('outside') or [], 'views': views})
    m['sheets'] = out
    m['codes'] = [{k: e.get(k) for k in ('id', 'code', 'kind', 'level', 'label', 'status', 'type', 'length_m', 'height_m', 'thickness_m', 'area_m2', 'volume_m3', 'concreteLayer_m') if k in e} for e in plan['elements']]
    for e in m['codes']: e['id'] = str(e['id'])
    m['documentationRevision'] = 'R11'
    m['codesWrittenToModel'] = False
    m['decisions'] = ['Losas L01.00 de PA/PE: losa a confirmar (no se asume hormigón).', 'Fundaciones: solo platea PB; resto no modelado / a definir.',
                      'Parámetro Structural de los muros: sin cambios; se filtra por tipo "Muro Hormigón 20cm".',
                      'Códigos MH/VE/LO/PL: usados en láminas y manifest; no escritos en Mark (requiere OK explícito del usuario: es cambio de parámetros del modelo).']
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sheets': len(out), 'views': sum(len(s['views']) for s in out), 'codes': len(m['codes'])}))


if __name__ == '__main__': main()
