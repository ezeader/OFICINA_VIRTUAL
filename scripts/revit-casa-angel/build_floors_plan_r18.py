"""Codes, labels and quantities for Pisos y zócalos (documentation only).
TP-nn tipos de piso · PI-<nivel>-nn piezas (elementos piso) · ZO-nn zócalos modelados · por local: tipo, m², zócalo requerido.
Output: openings-r4/floors-plan.json"""
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from build_rubros_inventory_r14 import dec
LC = {'00. Planta Baja': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE', '005. Acceso ppal': 'PB'}
FLOOR_TYPES = ['L01.00 / 20cm', 'L01.01 / 30cm', 'L01.02 / 20cm', 'L02.00 / 20cm', 'L03.00 / 20cm', 'L04.01 / 20cm', 'L05.00 / 20cm', 'L06.00 / 20cm', 'L07.01 / 20cm',
               'Deck Terraza PA 05cm', 'Escalones 20cm', 'Escalones acceso 2m x 1m', 'Base Acceso']
FINISH = {'Piso Vinilico PB': 'vinílico', 'Carpet': 'alfombra', 'Piso de Madera PA': 'madera', 'Wood Planks': 'deck de madera', 'Hormigon': 'hormigón', 'Concrete - Black': 'hormigón negro', 'Grass': 'césped'}


def c2(v): return ('%.2f' % v).replace('.', ',')
def cm(v): return ('%.1f' % (v * 100)).replace('.', ',').replace(',0', '')


def main():
    d = dec(json.loads((OUT / 'floors-raw.json').read_text(encoding='utf-8-sig')))
    openings = json.loads((ROOT.parent.parent / 'work' / 'casa-angel-dimensioning' / 'openings-r4' / 'plan.json').read_text(encoding='utf-8')) if False else None
    floors = [f for f in d['floors'] if f['type'] in FLOOR_TYPES]
    types = []
    for i, t in enumerate(FLOOR_TYPES, 1):
        fs = [f for f in floors if f['type'] == t]
        if not fs: continue
        layers = fs[0]['layers']; top = layers[0] if layers else None
        finish = FINISH.get(top['material'], top['material']) if top else ''
        code = f'TP-{i:02d}'
        types.append({'code': code, 'type': t, 'finish': finish, 'layers': layers, 'thickness_m': round(sum(l['thickness_m'] for l in layers), 3),
                      'area_m2': round(sum(f['area_m2'] for f in fs), 2), 'count': len(fs), 'levels': sorted({f['level'] for f in fs}),
                      'label': f"{code} · {t.split(' /')[0]} · {finish} · {c2(sum(f['area_m2'] for f in fs))} m²",
                      'layerText': ' / '.join(f"{FINISH.get(l['material'], l['material'])} {cm(l['thickness_m'])}" for l in layers if l['thickness_m'] > 0) + ' cm'})
    tcode = {t['type']: t for t in types}
    pieces = []; n = collections.Counter()
    for f in sorted(floors, key=lambda f: (LC.get(f['level'], 'XX'), f['type'], f['id'])):
        lc = LC.get(f['level'], 'XX'); n[lc] += 1; t = tcode[f['type']]
        pieces.append({'id': f['id'], 'code': f'PI-{lc}-{n[lc]:02d}', 'kind': 'PI', 'type': f['type'], 'typeCode': t['code'], 'finish': t['finish'], 'level': f['level'], 'levelCode': lc,
                       'area_m2': f['area_m2'], 'label': f"PI-{lc}-{n[lc]:02d} · {t['code']} · {c2(f['area_m2'])} m²", 'bbox': f['bbox']})
    piece_of = {p['id']: p for p in pieces}
    rooms = []
    for r in sorted(d['rooms'], key=lambda r: (r['level'], r['number'])):
        fid = next((i for i in r['floorIds'] if i in piece_of), None)
        p = piece_of.get(fid); t = tcode[p['type']] if p else None
        rooms.append({'id': r['id'], 'number': r['number'], 'name': r['name'], 'level': r['level'], 'levelCode': LC.get(r['level'], 'XX'), 'area_m2': round(r['area_m2'], 2),
                      'perimeter_m': round(r['perimeter_m'], 2), 'piece': p['code'] if p else None, 'typeCode': t['code'] if t else None, 'finish': t['finish'] if t else None,
                      'label': f"{t['code'] if t else 'sin piso'} · {t['finish'] if t else ''} · {c2(r['area_m2'])} m²", 'finishParam': r['finishFloor'] or None})
    sweeps = [s for s in d['sweeps'] if 'Zocalo' in s['type']]
    zo = [{'id': s['id'], 'code': f'ZO-{i:02d}', 'kind': 'ZO', 'length_m': s['length_m'], 'label': f"ZO-{i:02d} · {c2(s['length_m'])} ml", 'bbox': s['bbox']} for i, s in enumerate(sweeps, 1)]
    out = {'types': types, 'pieces': pieces, 'rooms': rooms, 'skirtings': zo, 'cornices': [s for s in d['sweeps'] if 'Cornice' in s['type']], 'readAt': d['readAt']}
    (OUT / 'floors-plan.json').write_text(json.dumps(out, ensure_ascii=True, indent=1), encoding='utf-8')
    for t in types: print(t['label'], '|', t['layerText'], t['levels'])
    print(len(pieces), 'pieces', sum(z['length_m'] for z in zo), 'ml zocalo modelado vs perimetro locales', round(sum(r['perimeter_m'] for r in rooms), 1))


if __name__ == '__main__': main()
