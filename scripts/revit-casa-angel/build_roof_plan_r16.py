"""Codes and labels for the Cubierta sheets (documentation only).
CU techos (faldones) · VC vigas de cubierta 6×20 · VP piezas 3×10 · CR correas 1,5×5 · FA fascias · CA canaletas · AL aleros metálicos.
Output: openings-r4/roof-plan.json"""
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from build_rubros_inventory_r14 import dec
M = .3048


def c2(v): return ('%.2f' % v).replace('.', ',')
def c1(v): return ('%.1f' % v).replace('.', ',')


def centre(b): return [(b['min'][i] + b['max'][i]) / 2 for i in range(3)]


def main():
    d = dec(json.loads((OUT / 'roof-raw.json').read_text(encoding='utf-8-sig')))
    els = []
    roofs = sorted(d['roofs'], key=lambda r: (r['levelId'] != 353988, -r['area_m2']))
    for i, r in enumerate(roofs, 1):
        faces = [f for f in r.get('topFaces', []) if f['deg'] > 1]
        slopes = sorted({round(f['deg'], 1) for f in faces})
        code = f'CU-{i:02d}'
        els.append({'id': r['id'], 'code': code, 'kind': 'CU', 'level': r['level'], 'levelId': r['levelId'], 'area_m2': r['area_m2'], 'volume_m3': r['volume_m3'],
                    'slopes_deg': slopes, 'aguas': [{'slope_deg': round(f['deg'], 1), 'area_m2': round(f['area_m2'], 2)} for f in faces],
                    'ridge_m': r['maxHeight_m'], 'label': f"{code} · {c1(r['area_m2'])} m² · {' / '.join(c1(s) + '°' for s in slopes)}",
                    'status': 'Tejas 20 mm (tipo: madera 15 mm + 5 mm); membrana y aislación no modeladas', 'bbox': r['bbox']})
    roof_boxes = [(e['code'], e['bbox']) for e in els]
    def roof_of(b):
        c = centre(b)
        for code, rb in roof_boxes:
            if rb['min'][0] - 2 <= c[0] <= rb['max'][0] + 2 and rb['min'][1] - 2 <= c[1] <= rb['max'][1] + 2 and rb['min'][2] - 4 <= c[2] <= rb['max'][2] + 2: return code
        return None
    kinds = [('Viga Cubierta', 'VC', 2, '6×20'), ('Viga Principal', 'VP', 3, '3×10'), ('Correas', 'CR', 3, '1,5×5')]
    for key, pre, w, sec in kinds:
        rows = sorted([f for f in d['framing'] if key in f['type']], key=lambda f: (f['refLevel'] or 0, round(centre(f['bbox'])[1], 1), round(centre(f['bbox'])[0], 1)))
        for i, f in enumerate(rows, 1):
            code = f'{pre}-{i:0{w}d}'
            els.append({'id': f['id'], 'code': code, 'kind': pre, 'level': '02. Planta Entrepiso' if f['refLevel'] == 353988 else '03. Planta de Techos', 'levelId': f['refLevel'],
                        'length_m': f['length_m'], 'volume_m3': f['volume_m3'], 'section': sec, 'roof': roof_of(f['bbox']),
                        'label': f"{code} · {c2(f['length_m'] or 0)} · {sec}", 'status': f"{f['type']} (Kerto LVL); sin nivel propio, nivel de referencia {'PE' if f['refLevel'] == 353988 else 'Techos'}", 'bbox': f['bbox']})
    for pre, cat, txt in [('FA', 'OST_Fascia', 'Fascia / zinguería de borde'), ('CA', 'OST_Gutter', 'Canaleta')]:
        rows = [o for o in d['others'] if o['category'] == cat]
        for i, o in enumerate(rows, 1):
            code = f'{pre}-{i:02d}'
            els.append({'id': o['id'], 'code': code, 'kind': pre, 'length_m': o['length_m'], 'label': f"{code} · {c2(o['length_m'] or 0)} ml", 'status': txt, 'roof': roof_of(o['bbox']), 'bbox': o['bbox']})
    for i, a in enumerate(sorted(d['alero'], key=lambda a: -a['area_m2']), 1):
        code = f'AL-{i:02d}'
        els.append({'id': a['id'], 'code': code, 'kind': 'AL', 'level': a['level'], 'area_m2': a['area_m2'], 'label': f"{code} · {c1(a['area_m2'])} m² · metálico", 'status': 'Alero metálico (piso "Alero Metalico" 15 cm)', 'bbox': a['bbox']})
    (OUT / 'roof-plan.json').write_text(json.dumps({'elements': els}, ensure_ascii=True, indent=1), encoding='utf-8')
    print(collections.Counter(e['kind'] for e in els), collections.Counter((e['kind'], e.get('roof')) for e in els if e['kind'] in ('VC', 'VP', 'CR', 'FA', 'CA')))
    for e in els:
        if e['kind'] in ('CU', 'AL', 'FA', 'CA'): print(e['label'], e.get('aguas', ''))


if __name__ == '__main__': main()
