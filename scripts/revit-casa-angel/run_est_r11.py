"""Build all structure sheets, one Revit job at a time; stop on the first failure."""
import json, subprocess, sys
from pathlib import Path

R = Path(__file__).parent; O = R / 'openings-r4'
MANIFEST = Path(sys.argv[1])

def job(**kw):
    p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps(dict(revision='r4', action='r11_est', **kw))], capture_output=True, text=True)
    print(kw.get('part'), kw.get('target', ''), (p.stdout or p.stderr)[:700], flush=True)
    if p.returncode: raise SystemExit('Revit job failed; stopping')

def c2(v): return ('%.2f' % v).replace('.', ',')

for part in ['plans', 'sec-311', 'sec-694', 'sec-353988', 'review', 'index']:
    rec = O / f'est-{part}.json'
    if rec.exists() and part == 'plans' and not json.loads(rec.read_text(encoding='utf-8')).get('v2'):
        job(part='reset', target='plans')
    if rec.exists() and part != 'plans': continue
    if rec.exists() and json.loads(rec.read_text(encoding='utf-8')).get('v2'): continue
    extra = {}
    if part == 'index':
        m = json.loads(MANIFEST.read_text(encoding='utf-8')); plan = json.loads((O / 'structure-plan.json').read_text(encoding='utf-8'))
        sheets = []
        for f in ['est-plans.json', 'est-sec-311.json', 'est-sec-694.json', 'est-sec-353988.json', 'est-review.json']:
            sheets += [s['number'] + '  ' + s['title'] for s in json.loads((O / f).read_text(encoding='utf-8'))['sheets']]
        mh = m['concreteWalls']
        lo = [e for e in plan['elements'] if e['kind'] == 'LO' and (e.get('concreteLayer_m') or 0) > 0 and 'Base' not in e.get('type', '')]
        conc_lines = [f"Muros MH {b['key']}: {b['count']} u. · {c2(b['volume_m3'])} m³" for b in mh['byLevel']]
        conc_lines.append(f"Muros MH total: {mh['count']} u. · {c2(mh['totals']['length_m'])} m · {c2(mh['totals']['volume_m3'])} m³")
        conc_lines += [f"{e['code']} · {c2(e['area_m2'])} m² × {c2(e['concreteLayer_m'])} = {c2(e['area_m2'] * e['concreteLayer_m'])} m³" for e in lo]
        conc_lines.append(f"Losas con capa de H°: {c2(sum(e['area_m2'] * e['concreteLayer_m'] for e in lo))} m³")
        pl = next(e for e in plan['elements'] if e['kind'] == 'PL'); conc_lines.append(f"Platea PL-01: {c2(pl['area_m2'])} m² × 0,15 = {c2(pl['area_m2'] * .15)} m³")
        criteria = ['Códigos: MH muros de hormigón, VE encadenados/vigas modeladas como muro,', 'LO losas y paquetes de piso, PL platea. Solo anotación:', 'no se escribieron en el parámetro Mark (cambio de modelo, pendiente de OK).',
                    'Muros MH = tipo "Muro Hormigón 20cm" (43, coincide con la planilla 1168184).', 'Losas: L01.01 (H° 15), L01.02 / L04.01 / L07.01 (H° 17,5), Insitu 22,5.',
                    'L01.00 en PA/PE: losa a confirmar. L0x.00 en PB: paquete sobre platea.', 'Fundaciones: solo platea PB modelada; resto no modelado / a definir.', 'Parámetro Structural de los muros: sin cambios.']
        extra = {'columns': [{'title': 'Criterios', 'lines': criteria}, {'title': 'Cómputo de hormigón', 'lines': conc_lines},
                             {'title': 'Láminas', 'lines': ['EST-00  Índice, criterios y cómputo'] + sheets},
                             {'title': 'No modelado / a definir', 'lines': [x[:70] for x in m['notModeled']]}], 'lines': []}
    job(part=part, **extra)
    d = json.loads(rec.read_text(encoding='utf-8')); d['v2'] = True; rec.write_text(json.dumps(d, indent=1), encoding='utf-8')
job(part='export')
p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps({'revision': 'r4', 'action': 'r4_verify'})], capture_output=True, text=True); print('verify', p.stdout[:300])
