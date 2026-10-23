"""List every exported openings view (R2, R3, R4) with the crop box the publisher used and the
elements to locate in it. Output: openings-r4/project-request.json (read by revit_survey_r9 'project')."""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).parent
PT_PER_FT = 2383.94 / 2.7592   # A1 landscape exported fit-to-page; calibration residuals < 1 pt


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--manifest', type=Path, required=True); a = ap.parse_args()
    m = load(a.manifest)
    room_items = {str(r['id']): [int(i['id']) if isinstance(i, dict) else int(i) for i in r.get('items', [])] for r in m['rooms']}
    views = []
    def add(rev, v, elements, margin_pt):
        views.append({'rev': rev, 'id': int(v['id']), 'box': v['box'], 'margin_ft': margin_pt / PT_PER_FT, 'elements': sorted(set(int(x) for x in elements))})
    for f in sorted((ROOT / 'openings-r2').glob('element-*.json')):
        r = load(f)
        for v in r['views']: add('R2', v, [r['item_id']], 10)
    for f in sorted((ROOT / 'openings-r2').glob('room-*.json')):
        r = load(f)
        for v in r['views']: add('R2', v, room_items.get(str(r['room_id']), []), 10)
    for case in m.get('reviewCases', []):
        f = ROOT / 'openings-r3' / f"context-{case['elementId']}.json"
        if not f.exists(): continue
        r = load(f)
        for v in r['views']: add('R3', v, [case['elementId']] + case.get('relatedElementIds', []), 10)
    for f in sorted((ROOT / 'openings-r4').glob('room-*.json')):
        r = load(f)
        items = [int(k) for k in r['elements']]
        for p in r['pages']:
            for v in p['views']:
                add('R4', v, items if v.get('kind') in ('plan', 'axo') else [v['elementId']], 3)
    (ROOT / 'openings-r4' / 'project-request.json').write_text(json.dumps({'views': views}), encoding='utf-8')
    print(json.dumps({'views': len(views), 'byRev': {k: sum(1 for v in views if v['rev'] == k) for k in ('R2', 'R3', 'R4')}}))


if __name__ == '__main__': main()
