"""R28 Cielorrasos propuesta: combine cp-probe.json (geometry, read-only) + ceil-plan.json (R21) into cp-plan.json."""
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).parent; OUT = ROOT / 'openings-r4'
sys.path.insert(0, str(ROOT))
from publish_openings_r4 import read

M = .3048
LC = {311: 'PB', 694: 'PA', 353988: 'PE'}
WET = ('Baño', 'Toilette', 'Cocina', 'Lavadero')
DOUBLE = ('Hall', 'Puente')          # stair hall / bridge: possible double height (flag, do not decide)
MIN_REST = .5                        # m²: slivers below this are boundary noise, not missing ceiling


def c2(x): return ('%.2f' % (0.0 if abs(x) < .005 else x)).replace('.', ',')
def clean(s): return s.encode('latin-1', 'backslashreplace').decode('unicode_escape') if isinstance(s, str) and '\\x' in s else s


def default_h(r):
    lc = r['levelCode']; n = r['name']
    if lc == 'PB': return 2.40 if n.startswith('Baño') and 'ppal' not in n else (2.50 if 'Servicio' in n else 2.60)
    if lc == 'PA': return 2.50 if any(k in n for k in ('Toilette', 'Cava', 'Cocina')) else 2.70
    return 2.50


def main():
    probe = read(OUT / 'cp-probe.json'); cp = read(OUT / 'ceil-plan.json')
    wood = {r['id']: r for r in read(OUT / 'cp-probe2.json')['rooms']}
    ce = {c['id']: c for c in cp['ceilings']}
    rooms = []; existing = []
    for r in probe['rooms']:
        r = dict(r); r['name'] = clean(r['name']); r['levelCode'] = LC[r['levelId']]
        r['wet'] = any(r['name'].startswith(k) for k in WET); r['docType'] = 'TC-01' if r['wet'] else 'TC-02'
        r['excluded'] = r['name'].startswith('Ascensor')
        cov = [(int(i), a) for i, a in r['covered'] if a > .05]
        r['covered'] = cov; r['existing_m2'] = sum(a for _, a in cov)
        rest = r['rest_m2'] if r['rest_m2'] >= MIN_REST and not r['excluded'] else 0.0
        ab = r.get('aboveRest') or r.get('above') or {}
        r['underRoof'] = bool(ab.get('isRoof')) and rest > 0
        r['slope_deg'] = round(ab.get('slope_deg', 0), 1) if r['underRoof'] else 0.0
        r['factor'] = 1 / math.cos(math.radians(r['slope_deg'])) if r['underRoof'] else 1.0
        r['doubleHeight'] = r['name'] in DOUBLE and rest > 0 and not r['underRoof']
        r['cpPlan_m2'] = rest; r['cp_m2'] = rest * r['factor']
        r['total_m2'] = 0.0 if r['excluded'] else r['existing_m2'] + r['cp_m2']
        hs = [ce[i]['height_m'] for i, _ in cov if i in ce]
        r['height_m'] = round(max(hs), 2) if hs else default_h(r)
        r['heightNote'] = ('bajo cubierta, sigue la pendiente (%s°)' % ('%.1f' % r['slope_deg']).replace('.', ',')) if r['underRoof'] else ('posible doble altura: a confirmar' if r['doubleHeight'] else ('h ' + c2(r['height_m'])))
        r['tapas'] = 1 if (r['name'].startswith(('Baño', 'Toilette', 'Sala de Maquinas'))) else 0
        r['buna_ml'] = 0.0 if r['excluded'] else r['perimeter_m']
        # R29 (user): under the wooden roof there is no gypsum ceiling — exposed tongue-and-groove, documented in Cubierta.
        # Sectors under a flat slab keep TC-02 (drawn as the 0,5 m probe cells).
        w = wood.get(r['id'])
        r['wood'] = bool(w and w['counts']['roof'] > 0 and not r['excluded'])
        if r['wood']:
            n_ = sum(w['counts'].values()); fr = w['counts']['roof'] / n_
            r['woodPlan_m2'] = r['area_m2'] * fr; r['slabCells'] = [[p[0], p[1]] for p in w['slabPts']]
            r['woodExisting'] = [i for i, _ in cov]
            slab = r['area_m2'] - r['woodPlan_m2']
            r['underRoof'] = False; r['slope_deg'] = 0.0; r['factor'] = 1.0; r['doubleHeight'] = False
            r['cpPlan_m2'] = slab; r['cp_m2'] = slab; r['existing_m2'] = 0.0; r['total_m2'] = slab
            r['buna_ml'] = r['perimeter_m'] * (1 - fr); r['tapas'] = 0
            r['heightNote'] = 'sector bajo losa (h %s)' % c2(w['slabClear'][0] - .5 if w['slabClear'] else r['height_m']) if slab > 0 else 'machimbre visto · ver Cubierta'
        else:
            r['woodPlan_m2'] = 0.0; r['slabCells'] = []; r['woodExisting'] = []
        rooms.append(r)
        for i, a in cov:
            c = ce.get(i)
            if c: existing.append({'id': i, 'code': c['code'], 'levelId': r['levelId'], 'modelType': c['typeCode'], 'docType': r['docType'], 'room': f"{r['number']} · {r['name']}", 'area_m2': c['area_m2'], 'height_m': c['height_m'],
                                   'changed': c['typeCode'] != r['docType'], 'wood': r['wood']})
    rooms.sort(key=lambda r: (['PB', 'PA', 'PE'].index(r['levelCode']), r['number']))
    n = {}
    for r in rooms:
        if r['cp_m2'] > 0:
            n[r['levelCode']] = n.get(r['levelCode'], 0) + 1; r['code'] = 'CP-%s-%02d' % (r['levelCode'], n[r['levelCode']]); r['cp'] = True
        else: r['code'] = None; r['cp'] = False
        ex = ', '.join(e['code'] + ('→' + e['docType'] if e['changed'] else '') for e in existing if e['id'] in [i for i, _ in r['covered']])
        if r['excluded']: r['tag'] = f"{r['number']} · {r['name']} · sin cielorraso (pasadizo)"
        elif r['wood']:
            r['tag'] = f"{r['number']} · {r['name']}\nmachimbre visto · ver Cubierta" + (f"\n{r['code']} · TC-02 {c2(r['cp_m2'])} m² bajo losa" if r['cp'] else '')
        elif r['cp']:
            vm = ' (v. magnitud)' if r['underRoof'] else ''
            r['tag'] = f"{r['code']} · {r['docType']} · propuesta\n{c2(r['cp_m2'])} m²{vm}\n{r['heightNote']}" + (f"\n+ existente {ex}" if ex else '')
        else: r['tag'] = f"{r['number']} · {r['docType']} ({ex.split('→')[0]})"
    (OUT / 'cp-plan.json').write_text(json.dumps({'readAt': probe['readAt'], 'rooms': rooms, 'existing': existing}, ensure_ascii=False, indent=1), encoding='utf-8')
    for r in rooms: print(r['levelCode'], r['number'], r['name'], r['docType'], round(r['existing_m2'], 2), round(r['cp_m2'], 2), r['code'], r['heightNote'], r['tapas'])
    print('changed', [(e['code'], e['modelType'], '->', e['docType']) for e in existing if e['changed']])


if __name__ == '__main__': main()
