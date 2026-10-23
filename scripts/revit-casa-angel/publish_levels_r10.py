"""Publish one general openings plan per level and add manifest['documentationR4']['levels'] (additive)."""
import argparse, gzip, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime'))
import pymupdf as fitz
sys.path.insert(0, str(ROOT))
from publish_openings_r4 import calibrate, read, svg, BASE


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    public = a.public_dir; mpath = public / 'manifest.json'
    m = json.loads(mpath.read_text(encoding='utf-8'))
    lv = read(OUT / 'levels.json'); proj = {str(p['id']): p for p in read(OUT / 'levels-elements.json')}
    plan = read(OUT / 'plan.json')
    code = {i['id']: i['code'] for i in m['items']}
    label = {str(r['id']): ('Sin local asignado' if r['number'] == 'SL' else f"{r['number']} · {r['name']}") for r in plan['rooms'] if r['id']}
    levels = []
    for x in lv['levels']:
        assert x['exported']
        src = OUT / f"r10-level-{x['code']}.pdf"; stem = f"r10-level-{x['code']}"
        shutil.copy2(src, public / f'{stem}.pdf')
        pdf = fitz.open(src); page = pdf[0]; pw, ph = page.rect.width, page.rect.height
        scale, ox, oy, used, res = calibrate(page, [(n['text'], n['anchor']) for n in x['notes']] + [(x['label'], x['anchor'])])
        lo, hi = x['box']
        rect = fitz.Rect(ox + lo[0] * scale - 3, oy - hi[1] * scale - 3, ox + hi[0] * scale + 3, oy - lo[1] * scale + 3) & page.rect
        crop = fitz.open(); p = crop.new_page(width=rect.width, height=rect.height); p.show_pdf_page(p.rect, pdf, 0, clip=rect)
        svg(p, public / f'{stem}.svg.gz')
        z = 2400 / rect.width; p.get_pixmap(matrix=fitz.Matrix(z, z)).save(public / f'{stem}-preview.png')
        page.get_pixmap(matrix=fitz.Matrix(.6, .6)).save(public / f'{stem}-sheet-preview.png')
        svg(page, public / f'{stem}-sheet.svg.gz')
        crop.close(); pdf.close()
        rows = proj[str(x['viewId'])]['elements']
        items = set(str(i) for i in x['items'])
        levels.append({'level': x['level'], 'code': x['code'], 'sheetId': str(x['sheetId']), 'sheetNumber': x['sheetNumber'], 'scale': x['scale'],
                       'image': BASE + f'{stem}.svg.gz', 'preview': BASE + f'{stem}-preview.png', 'aspect': round(rect.width / rect.height, 4),
                       'sheet': {'pdf': BASE + f'{stem}.pdf', 'image': BASE + f'{stem}-sheet.svg.gz', 'preview': BASE + f'{stem}-sheet-preview.png',
                                 'region': [round(rect.x0 / pw, 4), round(rect.y0 / ph, 4), round(rect.x1 / pw, 4), round(rect.y1 / ph, 4)]},
                       'elements': [{'code': code.get(r['elementId']), 'elementId': r['elementId'], 'box': [round(v, 4) for v in r['box']]} for r in rows if r['elementId'] in items],
                       'rooms': [{'roomId': int(r['elementId']), 'label': label.get(r['elementId']), 'box': [round(v, 4) for v in r['box']]} for r in rows if r['elementId'] not in items],
                       'calibration': {'anchors': used, 'residual_pt': round(res, 2)}})
    m['documentationR4']['levels'] = levels
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([(l['code'], l['scale'], len(l['elements']), len(l['rooms']), l['aspect']) for l in levels]))


if __name__ == '__main__': main()
