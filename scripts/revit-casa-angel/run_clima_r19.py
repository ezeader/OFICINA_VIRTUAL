import json, subprocess, sys
from pathlib import Path
R = Path(__file__).parent; O = R / 'openings-r4'
plan = json.loads((O / 'hvac-plan.json').read_text(encoding='utf-8'))
def job(**kw):
    p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps(dict(revision='r4', action='r19_clima', **kw))], capture_output=True, text=True)
    print(kw.get('part'), (p.stdout or p.stderr)[:250], flush=True)
    if p.returncode: raise SystemExit('Revit job failed; stopping')
def c2(v): return ('%.2f' % v).replace('.', ',')
job(part='plans', reset=True); job(part='plans')
if (O / 'cli-ci-test.json').exists(): job(part='ci-test', reset=True)
ci = [e['code'] for e in plan['elements'] if e['kind'] == 'CI']
for i in range(0, len(ci), 9):
    part = 'ci%02d' % (i // 9 + 1)
    if not (O / f'cli-{part}.json').exists(): job(part=part, codes=ci[i:i + 9])
if not (O / 'cli-index.json').exists():
    els = plan['elements']; k = lambda x: [e for e in els if e['kind'] == x]
    sheets = []
    for f in sorted(O.glob('cli-*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        if isinstance(d, dict) and 'sheets' in d: sheets += [s['number'] for s in d['sheets']]
    comp = [f"{lv}: {c2(sum(e['length_m'] for e in k('CI') if e['levelCode'] == lv))} ml en {len([e for e in k('CI') if e['levelCode'] == lv])} locales" for lv in ['PB', 'PA', 'PE']]
    comp += [f"Distribución/montantes: {c2(sum(e['length_m'] for e in k('DI')))} ml", f"Total PEX Ø20: {c2(sum(e['length_m'] for e in k('CI') + k('DI')))} ml",
             f"Locales con densidad completa (≥ 4 m/m²): {len([e for e in k('CI') if e['density'] >= 4])} de {len(k('CI'))}", 'Colectores: CO-N (SM, PE) y CO-S (Sala de Máquinas, PA)', f"Termostatos: {len(k('TE'))}"]
    crit = ['CI: serpentín por local (tramos horizontales del nivel).', 'DI: distribución y montantes fuera de locales.', 'Densidad de referencia: paso 15 cm ≈ 6,7 m/m².', 'Códigos solo como anotación (no en Mark).']
    falt = ['Bomba de calor inverter (no modelada).', 'Circuito por salida de colector (sin sistemas propios).', 'Retorno clasificado como impulsión (Hydronic Supply).', 'Locales con densidad baja: trazado parcial.', 'Tanque de inercia, vaso de expansión, válvulas.']
    job(part='index', columns=[{'title': 'Criterios', 'lines': crit}, {'title': 'Cómputo', 'lines': comp}, {'title': 'Láminas', 'lines': ['CLI-00  Índice'] + sorted(sheets)}, {'title': 'No modelado / a definir', 'lines': falt}])
job(part='export')
p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps({'revision': 'r4', 'action': 'r4_verify'})], capture_output=True, text=True); print('verify', p.stdout[:200])
