"""Codes for Climatización (piso radiante), documentation only.
CI-<nivel>-nn circuito/serpentín por local · CO-N / CO-S colectores · GA gabinetes · TE-nn termostatos · BO bomba (genérica).
Output: openings-r4/hvac-plan.json"""
import collections, json, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from build_rubros_inventory_r14 import dec
LC = {'00. Planta Baja': 'PB', '01. Planta Alta': 'PA', '02. Planta Entrepiso': 'PE', '005. Acceso ppal': 'PB'}
LID = {'PB': 311, 'PA': 694, 'PE': 353988}


def c2(v): return ('%.2f' % v).replace('.', ',')


def main():
    d = dec(json.loads((OUT / 'inventory-hvac-detail.json').read_text(encoding='utf-8-sig')))
    rooms = {r['id']: r for r in d['rooms']}
    pex = [p for p in d['pipes'] if 'PEX' in p['type'] or 'Hidroflex' in p['type']]
    circ = collections.OrderedDict(); loose = collections.defaultdict(list)
    for p in pex:
        r = rooms.get(p['room'])
        horiz = abs(p['a'][2] - p['b'][2]) < .01
        if r and r['level'] == p['level'] and horiz:
            circ.setdefault(r['id'], []).append(p)
        else:
            loose[LC.get(p['level'], 'PB')].append(p)
    els = []; n = collections.Counter()
    for rid, ps in sorted(circ.items(), key=lambda x: (LC[rooms[x[0]]['level']], rooms[x[0]]['name'])):
        r = rooms[rid]; lc = LC[r['level']]; n[lc] += 1; code = f'CI-{lc}-{n[lc]:02d}'
        sup = sum(p['length_m'] for p in ps if 'Mando' in p['type']); ret = sum(p['length_m'] for p in ps if 'Retorno' in p['type'])
        dens = (sup + ret) / r['area_m2'] if r['area_m2'] else 0
        els.append({'code': code, 'kind': 'CI', 'roomId': rid, 'room': r['name'], 'level': r['level'], 'levelCode': lc, 'levelId': LID[lc], 'area_m2': round(r['area_m2'], 2),
                    'supply_m': round(sup, 2), 'return_m': round(ret, 2), 'length_m': round(sup + ret, 2), 'density': round(dens, 2), 'pipeIds': [p['id'] for p in ps],
                    'systems': sorted({p['systemName'] for p in ps if p['systemName']}),
                    'label': f"{code} · {r['name']} · {c2(sup + ret)} ml · {c2(dens)} m/m²", 'status': 'completo' if dens >= 4 else 'incompleto o solo distribución (densidad < 4 m/m²)'})
    for lc, ps in loose.items():
        els.append({'code': f'DI-{lc}', 'kind': 'DI', 'level': lc, 'levelCode': lc, 'levelId': LID.get(lc, 311), 'length_m': round(sum(p['length_m'] for p in ps), 2), 'pipeIds': [p['id'] for p in ps],
                    'label': f"DI-{lc} · distribución y montantes · {c2(sum(p['length_m'] for p in ps))} ml", 'status': 'tramos fuera de locales o verticales'})
    acc = d['accessories']
    for a in acc:
        fam = a['family']; r = rooms.get(a['room'])
        if 'Colector' in fam:
            code = 'CO-N' if (r and r['name'] == 'SM') or 'Entrepiso' in (a['level'] or '') else 'CO-S'; kind = 'CO'
            label = f"{code} · Colector {'Norte' if code == 'CO-N' else 'Sur'} · {r['name'] if r else ''}"
        elif 'Gabinete' in fam:
            code = 'GA-N' if (r and r['name'] == 'SM') else 'GA-S'; kind = 'GA'; label = f"{code} · gabinete de colector"
        elif 'termostato' in fam.lower():
            n['TE'] += 1; code = f"TE-{n['TE']:02d}"; kind = 'TE'; label = f"{code} · cronotermostato · {r['name'] if r else 'sin local'}"
        elif a['category'] == 'Mechanical Equipment':
            code = 'BO-01'; kind = 'BO'; label = 'BO-01 · bomba centrífuga genérica (no es la bomba de calor)'
        else: continue
        els.append({'code': code, 'kind': kind, 'id': a['id'], 'room': r['name'] if r else None, 'level': a['level'], 'label': label, 'status': fam + ' · ' + a['type']})
    (OUT / 'hvac-plan.json').write_text(json.dumps({'elements': els, 'readAt': d['readAt']}, ensure_ascii=True, indent=1), encoding='utf-8')
    for e in els: print(e['label'], '|', e['status'][:40])


if __name__ == '__main__': main()
