"""Codes for Cielorrasos: TC-nn tipo · CE-<nivel>-nn pieza; rooms with/without modeled ceiling. Output: openings-r4/ceil-plan.json"""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from build_rubros_inventory_r14 import dec
LC = {'00. Planta Baja': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE'}
DESC = {'Placa de Yeso RH 12,5mm Knauf': 'placa Knauf RH 12,5 (resistente a humedad)', 'Placa de Yeso ST 12,5mm Knauf': 'placa Knauf ST 12,5', 'Plain': 'genérico: perfilería 45 + placa 12 mm'}
def c2(v): return ('%.2f' % v).replace('.', ',')
def cm(v): return ('%.1f' % (v * 100)).replace('.', ',').replace(',0', '')
d = dec(json.loads((OUT / 'ceil-raw.json').read_text(encoding='utf-8-sig')))
types = []
for i, t in enumerate(['Placa de Yeso RH 12,5mm Knauf', 'Placa de Yeso ST 12,5mm Knauf', 'Plain'], 1):
    cs = [c for c in d['ceilings'] if c['type'] == t]
    if not cs: continue
    types.append({'code': f'TC-{i:02d}', 'type': t, 'desc': DESC[t], 'layers': cs[0]['layers'], 'count': len(cs), 'area_m2': round(sum(c['area_m2'] for c in cs), 2),
                  'layerText': ' / '.join(f"{l['material']} {cm(l['thickness_m'])}" for l in cs[0]['layers']) + ' cm', 'generic': t == 'Plain',
                  'label': f"TC-{i:02d} · {DESC[t]} · {c2(sum(c['area_m2'] for c in cs))} m²"})
tc = {t['type']: t for t in types}
ceil = []; n = collections.Counter()
for c in sorted(d['ceilings'], key=lambda c: (LC[c['level']], c['type'], c['id'])):
    lc = LC[c['level']]; n[lc] += 1; code = f'CE-{lc}-{n[lc]:02d}'
    ceil.append({**c, 'code': code, 'kind': 'CE', 'levelCode': lc, 'typeCode': tc[c['type']]['code'], 'label': f"{code} · {tc[c['type']]['code']} · {c2(c['area_m2'])} m² · h {c2(c['height_m'])}"})
cc = {c['id']: c for c in ceil}
rb = {r['id']: r['bbox'] for r in json.loads((ROOT / 'openings-r2' / 'registry.json').read_text(encoding='utf-8'))['rooms'] if r.get('bbox')}
def overlap(a, b):
    ox = min(a['max'][0], b['max'][0]) - max(a['min'][0], b['min'][0]); oy = min(a['max'][1], b['max'][1]) - max(a['min'][1], b['min'][1])
    return max(0, ox) * max(0, oy) * .0929
rooms = []
for r in d['rooms']:
    part = [c['code'] for c in ceil if c['level'] == r['level'] and r['id'] in rb and overlap(c['bbox'], rb[r['id']]) > .1 * r['area_m2']] if not r['ceiling'] else []
    rooms.append({'id': r['id'], 'number': r['number'], 'name': r['name'], 'level': r['level'], 'levelCode': LC[r['level']], 'area_m2': round(r['area_m2'], 2),
                  'ceiling': cc[r['ceiling']]['code'] if r['ceiling'] else None, 'partial': part, 'status': 'con cielorraso' if r['ceiling'] else ('parcial' if part else 'sin cielorraso modelado')})
(OUT / 'ceil-plan.json').write_text(json.dumps({'types': types, 'ceilings': ceil, 'rooms': rooms, 'readAt': d['readAt']}, ensure_ascii=True, indent=1), encoding='utf-8')
for t in types: print(t['label'])
print(len(ceil), 'piezas;', collections.Counter(r['status'] for r in rooms))
