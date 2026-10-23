"""Codes and labels for the structure sheets (documentation only; nothing is written to Mark).

MH-<nivel>-nn  muros 'Muro Hormigón 20cm' (orden del manifest)
VE-<nivel>-nn  encadenados / vigas modelados como muros
LO-<nivel>-nn  losas y paquetes de piso (estado según capa de hormigón del tipo)
PL-01          platea PB
Output: openings-r4/structure-plan.json (read by revit_structure_r11.py)
"""
import argparse, collections, json, re
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
LC = {'00. Planta Baja': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE', '03. Planta de Techos': 'PT', '005. Acceso ppal': 'AC'}
SHEET_LEVEL = {'PB': 311, 'AC': 311, 'PA': 694, 'PE': 353988}


def dec(v):
    if isinstance(v, str): return re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m[1], 16)), v)
    if isinstance(v, list): return [dec(x) for x in v]
    if isinstance(v, dict): return {k: dec(x) for k, x in v.items()}
    return v


def c2(v): return ('%.2f' % v).replace('.', ',')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--manifest', type=Path, required=True); a = ap.parse_args()
    m = json.loads(a.manifest.read_text(encoding='utf-8'))
    inv = dec(json.loads((OUT / 'inventory-structure.json').read_text(encoding='utf-8-sig')))
    lev_id = {l['name']: l['id'] for l in inv['levels']}
    els = []
    for w in m['concreteWalls']['elements']:
        lc = w['code'].split('-')[1]
        els.append({'id': int(w['id']), 'code': w['code'], 'kind': 'MH', 'levelCode': lc, 'level': w['level'], 'sheetLevel': SHEET_LEVEL[lc],
                    'label': f"{w['code']} · {c2(w['length_m'])} × {c2(w['height_m'] or 0)} · e {round((w['thickness_m'] or 0) * 100):.0f}",
                    'length_m': w['length_m'], 'height_m': w['height_m'], 'thickness_m': w['thickness_m'], 'area_m2': w['area_m2'], 'volume_m3': w['volume_m3'], 'status': 'Hormigón armado (tipo Muro Hormigón 20cm)'})
    ve = [w for w in inv['walls'] if w['type'] in ('Viga de encadenado invertida', 'VIGA encuentro 2 techos, revestimiento fachada')]
    n = collections.Counter()
    for w in sorted(ve, key=lambda w: (w['level'], w['id'])):
        lc = LC[w['level']]; n[lc] += 1; code = f'VE-{lc}-{n[lc]:02d}'
        sec = f"{round(w['width_m'] * 100):.0f}×{round((w['height_m'] or 0) * 100):.0f}"
        els.append({'id': w['id'], 'code': code, 'kind': 'VE', 'levelCode': lc, 'level': w['level'], 'sheetLevel': SHEET_LEVEL[lc],
                    'label': f"{code} · {c2(w['length_m'])} · {sec}", 'length_m': w['length_m'], 'height_m': w['height_m'], 'thickness_m': w['width_m'],
                    'area_m2': w['area_m2'], 'volume_m3': w['volume_m3'], 'status': w['type'] + ' (modelado como muro)'})
    n = collections.Counter()
    for f in sorted(m['slabsAndFoundations'], key=lambda f: (f['level'], f['type'], f['id'])):
        lc = LC[f['level']]
        if 'Platea' in f['type']:
            code = 'PL-01'; status = 'Platea de fundación (capa de hormigón 15 cm)'
            label = f"PL-01 · {c2(f['area_m2'])} m² · H° e 15 · {c2(f['area_m2'] * .15)} m³"
        else:
            n[lc] += 1; code = f'LO-{lc}-{n[lc]:02d}'
            conc = f['concreteLayer_m'] or 0
            if 'Base Acceso' in f['type']: status = 'Base de acceso (e 1,20 m a verificar)'; tail = 'base acceso · e 120 (verificar)'
            elif conc > 0: status = f'Losa con capa de hormigón {round(conc * 100, 1):g} cm'; tail = f"H° e {round(conc * 100, 1):g}".replace('.', ',')
            elif lc == 'PB': status = 'Paquete de piso sobre platea (sin hormigón propio)'; tail = 'paquete s/ platea'
            else: status = 'Losa a confirmar (tipo sin capa de hormigón)'; tail = 'losa a confirmar'
            label = f"{code} · {c2(f['area_m2'])} m² · {tail}"
        els.append({'id': int(f['id']), 'code': code, 'kind': 'PL' if code == 'PL-01' else 'LO', 'levelCode': lc, 'level': f['level'], 'sheetLevel': SHEET_LEVEL[lc],
                    'label': label, 'type': f['type'], 'area_m2': f['area_m2'], 'thickness_m': f['thickness_m'], 'concreteLayer_m': f['concreteLayer_m'], 'status': status})
    code_of = {str(e['id']): e['code'] for e in els}
    cases = []
    for i, c in enumerate(m['reviewCases'], 1):
        cases.append({'id': c['id'], 'n': i, 'title': c['title'], 'elementIds': [int(x) for x in c['elementIds']],
                      'codes': [code_of.get(str(x), c['codes'][k] if k < len(c['codes']) else str(x)) for k, x in enumerate(c['elementIds'])],
                      'observation': c['observation'], 'proposedCorrection': c['proposedCorrection']})
    (OUT / 'structure-plan.json').write_text(json.dumps({'elements': els, 'cases': cases}, ensure_ascii=True, indent=1), encoding='utf-8')
    print(json.dumps(collections.Counter(e['kind'] + '-' + e['levelCode'] for e in els)), len(cases))


if __name__ == '__main__': main()
