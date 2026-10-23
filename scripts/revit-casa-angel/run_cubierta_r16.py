import json, subprocess, sys
from pathlib import Path
R = Path(__file__).parent; O = R / 'openings-r4'
plan = json.loads((O / 'roof-plan.json').read_text(encoding='utf-8'))
def job(**kw):
    p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps(dict(revision='r4', **kw))], capture_output=True, text=True)
    print(kw.get('part'), (p.stdout or p.stderr)[:300], flush=True)
    if p.returncode: raise SystemExit('Revit job failed; stopping')
def c2(v): return ('%.2f' % v).replace('.', ',')
vc = [e['code'] for e in plan['elements'] if e['kind'] == 'VC']
for i in range(0, len(vc), 9):
    part = 'vc%02d' % (i // 9 + 1)
    if not (O / f'cub-{part}.json').exists(): job(action='r16_cubierta', part=part, codes=vc[i:i + 9])
if not (O / 'cub-index.json').exists():
    els = plan['elements']; k = lambda x: [e for e in els if e['kind'] == x]
    sheets = []
    for f in sorted(O.glob('cub-*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        if isinstance(d, dict) and 'sheets' in d: sheets += [s['number'] for s in d['sheets']]
    cu = k('CU')
    comp = [f"{e['code']}: {c2(e['area_m2'])} m² · pend. {' / '.join(c2(s) + '°' for s in e['slopes_deg'])}" for e in cu]
    comp.append(f"Total tejas: {c2(sum(e['area_m2'] for e in cu))} m²")
    for x, t in [('VC', 'Vigas 6×20'), ('VP', 'Piezas 3×10'), ('CR', 'Correas 1,5×5')]:
        comp.append(f"{t} ({x}): {len(k(x))} u. · {c2(sum(e['length_m'] or 0 for e in k(x)))} ml · {c2(sum(e['volume_m3'] or 0 for e in k(x)))} m³")
    comp.append(f"Fascias (FA): {c2(sum(e['length_m'] for e in k('FA')))} ml · Canaletas (CA): {c2(sum(e['length_m'] for e in k('CA')))} ml")
    comp.append(f"Aleros metálicos (AL): {c2(sum(e['area_m2'] for e in k('AL')))} m²")
    crit = ['Códigos: CU techos (faldones), VC vigas 6×20, VP piezas 3×10,', 'CR correas 1,5×5, FA fascias, CA canaletas, AL aleros metálicos.', 'Solo anotación (no se escribieron en el modelo).',
            'Madera: familia Kerto LVL; piezas sin nivel propio', '(nivel de referencia PE o Techos).', 'Pendientes medidas sobre la geometría de cada agua.']
    falt = ['Membrana hidrófuga y aislación térmica (el tipo de techo', 'solo tiene madera 15 mm + 5 mm).', 'Bajadas pluviales, cumbreras, limatesas, babetas.', 'Zinguería completa (solo 2 canaletas, 14 ml).', 'Fijaciones y uniones de la estructura de madera.', 'CU-02 sin estructura de madera modelada.']
    job(action='r16_cubierta', part='index', columns=[{'title': 'Criterios', 'lines': crit}, {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['CUB-00  Índice'] + sorted(sheets)}, {'title': 'No modelado / a definir', 'lines': falt}])
job(action='r16_cubierta', part='export'); job(action='r4_verify')
