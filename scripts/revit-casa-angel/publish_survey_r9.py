"""Add hover boxes and survey data to the openings manifest (additive only).

- every exported view (R2 items/rooms, R3 review contexts, R4 sheets) gets
  `elements: [{code, elementId, box:[x0,y0,x1,y1]}]` in 0-1 fractions of its SVG (top-left origin);
- the same data goes to view-elements.json {viewId: [...]};
- items[] get `survey` (opening type, glazing, frame, thermal, notes) and, for curtain walls, `panels`.
"""
import argparse, json, re
from pathlib import Path

OUT = Path(__file__).parent / 'openings-r4'


def dec(v):
    if isinstance(v, str): return re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), v)
    if isinstance(v, list): return [dec(x) for x in v]
    if isinstance(v, dict): return {k: dec(x) for k, x in v.items()}
    return v


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--public-dir', type=Path, required=True); a = ap.parse_args()
    mpath = a.public_dir / 'manifest.json'; m = json.loads(mpath.read_text(encoding='utf-8'))
    before = json.dumps({k: v for k, v in m.items()}, sort_keys=True)
    code = {i['id']: i['code'] for i in m['items']}
    proj = dec(json.loads((OUT / 'view-elements.json').read_text(encoding='utf-8-sig')))
    errors = [p for p in proj if p.get('error')]
    by_view = {}
    for p in proj:
        if p.get('error'): continue
        by_view[str(p['id'])] = [{'code': code.get(e['elementId']), 'elementId': e['elementId'], 'box': [round(x, 4) for x in e['box']], **({'clipped': True} if e['clipped'] else {})} for e in p['elements']]
    touched = 0
    def tag(views):
        nonlocal touched
        for v in views or []:
            k = str(v.get('id'))
            if k in by_view: v['elements'] = by_view[k]; touched += 1
    for it in m['items']:
        tag(it.get('documentation', {}).get('views'))
    for r in m['rooms']:
        tag(r.get('views'))
    for c in m.get('reviewCases', []):
        tag((c.get('context') or {}).get('views'))
    for g in m.get('documentationR4', {}).get('sheets', []):
        for s in g['sheets']: tag(s['views'])
    for r in m['rooms']:
        for s in (r.get('r4') or {}).get('sheets', []): tag(s['views'])
    surv = dec(json.loads((OUT / 'survey-summary.json').read_text(encoding='utf-8')))
    for it in m['items']:
        s = surv.get(it['id'])
        if not s: continue
        it['survey'] = {k: v for k, v in s.items() if k not in ('panels', 'code')}
        if s.get('panels') is not None: it['panels'] = s['panels']
    (a.public_dir / 'view-elements.json').write_text(json.dumps(by_view, ensure_ascii=False), encoding='utf-8')
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'viewsWithElements': len(by_view), 'viewEntriesTagged': touched, 'projectionErrors': len(errors),
                      'itemsWithSurvey': sum(1 for i in m['items'] if 'survey' in i), 'curtainWithPanels': sum(1 for i in m['items'] if 'panels' in i)}))


if __name__ == '__main__': main()
