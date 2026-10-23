"""Publish R4 room-grouped openings sheets (PDF + svg.gz + png) and extend the manifest.

Additive only: existing manifest fields are kept; R4 data lands in
manifest['documentationR4'], rooms[].r4, items[].documentation.r4 and items[].dimensions.
"""
import argparse, gzip, hashlib, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT / 'pdf-runtime'))
import pymupdf as fitz

BASE = '/casa-angel/openings/'


def decode(value):
    if isinstance(value, str): return re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), value)
    if isinstance(value, list): return [decode(x) for x in value]
    if isinstance(value, dict): return {k: decode(v) for k, v in value.items()}
    return value


def read(path): return decode(json.loads(Path(path).read_text(encoding='utf-8-sig')))
def save(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
def svg(page, path):
    # 0.01 pt precision is far below print resolution and roughly halves the payload.
    data = re.sub(r"(\d+\.\d{2})\d+", lambda m: m.group(1), page.get_svg_image(text_as_path=True))
    path.write_bytes(gzip.compress(data.encode(), mtime=0))
norm = lambda s: ' '.join(s.split())


def calibrate(page, anchors):
    """Least-squares map sheet feet -> PDF points from native text anchors."""
    lines = [(norm(''.join(s['text'] for s in l['spans'])), fitz.Rect(l['bbox']))
             for b in page.get_text('dict')['blocks'] for l in b.get('lines', [])]
    pairs = []
    for text, (ax, ay) in anchors:
        hit = next((r for t, r in lines if t == norm(text)), None)
        if hit is None: hit = next((r for t, r in lines if norm(text)[:40] and t.startswith(norm(text)[:40])), None)
        if hit: pairs.append((ax, ay, hit.x0, hit.y0))
    assert len(pairs) >= 2, 'Not enough native anchors to calibrate'
    n = len(pairs); mx = sum(p[0] for p in pairs) / n; px = sum(p[2] for p in pairs) / n
    sx = sum((p[0] - mx) * (p[2] - px) for p in pairs) / max(1e-9, sum((p[0] - mx) ** 2 for p in pairs))
    scale = sx if 700 < sx < 900 else 2383.94 / 2.7559
    ox = px - mx * scale
    oy = sum(p[3] + p[1] * scale for p in pairs) / n
    res = max(max(abs(ox + p[0] * scale - p[2]), abs(oy - p[1] * scale - p[3])) for p in pairs)
    assert res < 6, f'Calibration residual too large: {res}'
    return scale, ox, oy, len(pairs), res


def crop_view(pdf, pageno, rect, path):
    doc = fitz.open(); p = doc.new_page(width=rect.width, height=rect.height)
    p.show_pdf_page(p.rect, pdf, pageno, clip=rect); svg(p, path); doc.close()


def publish_room(rec, public):
    key = rec['key']; src = OUT / f'r4-room-{key}.pdf'
    assert rec['exported'] and src.exists(), f'Missing export for {key}'
    dest = public / f'r4-room-{key}.pdf'; shutil.copy2(src, dest)
    assert hashlib.sha256(src.read_bytes()).digest() == hashlib.sha256(dest.read_bytes()).digest()
    pdf = fitz.open(src); assert len(pdf) == len(rec['pages']), f'{key}: page count mismatch'
    fonts = sorted({f[3].split('+')[-1] for i in range(len(pdf)) for f in pdf[i].get_fonts()})
    sheets = []
    for i, page_rec in enumerate(rec['pages']):
        page = pdf[i]
        stem = f'r4-room-{key}-p{i + 1}'
        svg(page, public / f'{stem}.svg.gz')
        page.get_pixmap(matrix=fitz.Matrix(.35, .35)).save(public / f'{stem}.png')
        page.get_pixmap(matrix=fitz.Matrix(.6, .6)).save(public / f'{stem}-preview.png')
        anchors = [(n['text'], n['anchor']) for n in page_rec['notes']] + [(v['label'], v['anchor']) for v in page_rec['views']]
        scale, ox, oy, used, res = calibrate(page, anchors)
        views = []
        for v in page_rec['views']:
            lo, hi = v['box']
            rect = fitz.Rect(ox + lo[0] * scale - 3, oy - hi[1] * scale - 3, ox + hi[0] * scale + 3, oy - lo[1] * scale + 3) & page.rect
            assert not rect.is_empty
            file = f'r4-view-{v["id"]}.svg.gz'; crop_view(pdf, i, rect, public / file)
            # Per-drawing data for the sheet viewer: the cotas and tags drawn in this view.
            def dimrow(d): return {'label': d['label'], 'values_m': [round(x, 4) for x in d.get('values_m', [])], 'associative': d.get('associative'), **({'radius_m': round(d['radius_m'], 4)} if d.get('radius_m') else {})}
            if v.get('kind') in ('plan', 'axo'):
                tags = rec['codes']
                vdims = [dict(dimrow(d), code=e['code']) for e in rec['elements'].values() for d in e['dimensions'] if v.get('kind') == 'plan' and 'planta' in d['label'] and not d.get('error')]
            else:
                e = rec['elements'][str(v['elementId'])]; tags = [e['code']]
                vdims = [dict(dimrow(d), code=e['code']) for d in e['dimensions'] if 'planta' not in d['label'] and not d.get('error')]
            views.append({k: v[k] for k in ('id', 'name', 'label', 'scale', 'kind') if k in v} | {'elementId': str(v['elementId']) if v.get('elementId') else None, 'code': v.get('code'), 'image': BASE + file, 'tags': tags, 'dimensions': vdims,
                          'roomLabel': rec.get('roomLabel'), 'region': [round(rect.x0 / page.rect.width, 4), round(rect.y0 / page.rect.height, 4), round(rect.x1 / page.rect.width, 4), round(rect.y1 / page.rect.height, 4)]})
        assert page_rec['sheet_number'] in page.get_text(), f'Sheet number missing on {stem}'
        sheets.append({'sheetId': str(page_rec['sheet_id']), 'sheetNumber': page_rec['sheet_number'], 'page': i + 1, 'pages': len(rec['pages']),
                       'pdf': BASE + f'r4-room-{key}.pdf', 'image': BASE + f'{stem}.svg.gz', 'thumbnail': BASE + f'{stem}.png', 'preview': BASE + f'{stem}-preview.png', 'views': views,
                       'calibration': {'anchors': used, 'residual_pt': round(res, 2)}})
    pdf.close()
    return sheets, fonts


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    public = a.public_dir; manifest = read(public / 'manifest.json')
    before_ids = [(i['id'], i['uid']) for i in manifest['items']]
    plan = read(OUT / 'plan.json'); verification = read(OUT / 'verification.json')
    assert verification['physicalUnchanged'], 'Physical verification failed; not publishing'
    rooms = {str(r['id']): r for r in manifest['rooms']}; items = {i['id']: i for i in manifest['items']}
    all_sheets = []; fonts = set(); dims_total = 0; non_assoc = 0
    for item in manifest['items']:
        item['documentation'].pop('r4', None)
    for r in plan['rooms']:
        if not r['items']: continue
        rec = read(OUT / f'room-{r["key"]}.json')
        rec['roomLabel'] = 'Sin local asignado' if r['number'] == 'SL' else f"{r['number']} · {r['name']}"
        sheets, f = publish_room(rec, public); fonts |= set(f)
        entry = {'key': r['key'], 'roomId': str(r['id']) if r['id'] else None, 'name': rec['name'], 'level': rec['level'], 'codes': rec['codes'], 'sheets': sheets}
        all_sheets.append(entry)
        if r['id']: rooms[str(r['id'])]['r4'] = {'sheets': sheets}
        for eid_, e in rec['elements'].items():
            it = items[str(eid_)]
            doc = it['documentation'].setdefault('r4', {'sheets': [], 'views': [], 'dimensions': [], 'data': []})
            view_img = next((v['image'] for s in sheets for v in s['views'] if v['id'] == e['viewId']), None)
            doc['sheets'].append(e['sheet']); doc['views'].append({'viewId': str(e['viewId']), 'roomKey': r['key'], 'roomName': rec['name'], 'image': view_img})
            dims = [{'label': d['label'], 'values_m': [round(x, 4) for x in d.get('values_m', [])], 'associative': d.get('associative'),
                     'view': 'plan' if 'planta' in d['label'] else 'elevation', 'roomKey': r['key']} for d in e['dimensions'] if not d.get('error')]
            doc['dimensions'] += dims; doc['data'] = e['data']; dims_total += len(dims); non_assoc += len([d for d in dims if d['associative'] is False])
    for item in manifest['items']:
        r4 = item['documentation'].get('r4')
        # One fabrication dimension set per element (from its first room elevation; plan widths kept once).
        if r4:
            first = r4['views'][0]['roomKey']
            item['dimensions'] = [d for d in r4['dimensions'] if d['roomKey'] == first]
    counts = manifest['counts']
    pages = sum(len(s['sheets']) for s in all_sheets)
    manifest['documentationR4'] = {
        'revision': 'R4', 'readAt': verification['at'], 'font': 'Bahnschrift SB Condensed ADER', 'pdfFonts': sorted(fonts),
        'grouping': 'Por local: planta con codigos y anchos + alzado interior acotado de cada abertura. Elementos compartidos aparecen en ambos locales y se computan una vez.',
        'sheets': all_sheets,
        'totals': {'roomGroups': len(all_sheets), 'sheets': pages, 'elevations': sum(len(r['items']) for r in plan['rooms']),
                   'uniqueElements': len(items), 'windows': counts['windows'], 'doors': counts['doors'], 'curtainWalls': counts['curtainWalls'],
                   'dimensions': dims_total, 'nonAssociativeDimensions': non_assoc,
                   'roomsWithoutOpenings': [r['name'] for r in plan['rooms'] if not r['items']]},
        'verification': verification,
        'units': 'm, precision 0.001',
    }
    assert before_ids == [(i['id'], i['uid']) for i in manifest['items']]
    save(public / 'manifest.json', manifest)
    print(json.dumps(manifest['documentationR4']['totals'], ensure_ascii=False))


if __name__ == '__main__': main()
