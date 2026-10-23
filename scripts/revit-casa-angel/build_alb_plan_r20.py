"""Codes for Albañilería (muros y tabiques no estructurales), documentation only.
TM-nn tipo de muro · AB-<nivel>-nn muro. Output: openings-r4/alb-plan.json"""
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from build_rubros_inventory_r14 import dec
LC = {'00. Planta Baja': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE', '005. Acceso ppal': 'PB'}
LID = {'PB': 311, 'PA': 694, 'PE': 353988}
TYPES = [('Muro Interior 10cm', 'mampostería interior 10 cm'), ('Muro Interior 20cm', 'mampostería interior 20 cm'), ('Interior - Blockwork 101', 'bloque de hormigón 5 cm'),
         ('Bajo Escalera', 'tabique bajo escalera (hormigón 10 cm)'), ('Muro Fachada eje', 'muro de fachada (eje)'), ('Muro Fachada ppal', 'muro de fachada principal (hormigón visto 8 cm)'),
         ('W111.ar 70.400 ST 12.5', 'Durlock W111: 1 placa ST por cara, montante 70'), ('W112.ar 70.400 ST.RH 12.5', 'Durlock W112: 2 placas por cara (ST / RH), montante 70'),
         ('Durlock Chimenea', 'revestimiento de chimenea (piedra 5 cm)'), ('Cierre Cielorraso', 'cierre de cielorraso (2 cm)')]
FIN = {'White Paint': 'pintura (genérico)', 'Concrete, Cast In Situ': 'hormigón', 'Hormigon fachada': 'hormigón de fachada', 'Placa de Yeso ST 12,5mm Knauf': 'placa Knauf ST 12,5',
       'Placa de Yeso RH 12,5mm Knauf': 'placa Knauf RH 12,5', 'Montantes y Soleras Knauf': 'montantes y soleras 70', 'Concrete Masonry Units': 'bloque de hormigón', 'Piedra Chimenea': 'piedra', '<White>': 'genérico blanco', '': 'sin material'}


def c2(v): return ('%.2f' % v).replace('.', ',')
def cm(v): return ('%.1f' % (v * 100)).replace('.', ',').replace(',0', '')


def main():
    s = dec(json.loads((OUT / 'inventory-structure.json').read_text(encoding='utf-8-sig')))
    types = []
    for i, (t, desc) in enumerate(TYPES, 1):
        ws = [w for w in s['walls'] if w['type'] == t]
        if not ws: continue
        layers = s['wallTypes'].get(t, {}).get('layers', [])
        types.append({'code': f'TM-{i:02d}', 'type': t, 'desc': desc, 'layers': layers, 'thickness_m': round(sum(l['thickness_m'] for l in layers), 3),
                      'count': len(ws), 'length_m': round(sum(w['length_m'] or 0 for w in ws), 2), 'area_m2': round(sum(w['area_m2'] or 0 for w in ws), 2), 'volume_m3': round(sum(w['volume_m3'] or 0 for w in ws), 3),
                      'levels': sorted({w['level'] for w in ws}), 'generic': all(l['material'] in ('White Paint', '<White>', '') for l in layers),
                      'layerText': ' / '.join(f"{FIN.get(l['material'], l['material'])} {cm(l['thickness_m'])}" for l in layers if l['thickness_m'] > 0) + ' cm',
                      'label': f"TM-{i:02d} · {desc} · {c2(sum(w['area_m2'] or 0 for w in ws))} m²"})
    tcode = {t['type']: t for t in types}
    walls = []; n = collections.Counter()
    for w in sorted([w for w in s['walls'] if w['type'] in tcode], key=lambda w: (LC.get(w['level'], 'XX'), w['type'], w['id'])):
        lc = LC.get(w['level'], 'XX'); n[lc] += 1; t = tcode[w['type']]; code = f'AB-{lc}-{n[lc]:02d}'
        walls.append({'id': w['id'], 'code': code, 'kind': 'AB', 'typeCode': t['code'], 'type': w['type'], 'level': w['level'], 'levelCode': lc, 'sheetLevel': LID.get(lc, 311),
                      'length_m': w['length_m'], 'height_m': w['height_m'], 'thickness_m': w['width_m'], 'area_m2': w['area_m2'], 'volume_m3': w['volume_m3'],
                      'label': f"{code} · {t['code']} · {c2(w['length_m'] or 0)} × {c2(w['height_m'] or 0)} · e {cm(w['width_m'] or 0)}",
                      'status': t['desc'] + (' · composición genérica en el modelo' if t['generic'] else '')})
    (OUT / 'alb-plan.json').write_text(json.dumps({'types': types, 'walls': walls}, ensure_ascii=True, indent=1), encoding='utf-8')
    for t in types: print(t['label'], '|', t['layerText'], t['levels'], 'generic' if t['generic'] else '')
    print(collections.Counter(w['levelCode'] for w in walls))


if __name__ == '__main__': main()
