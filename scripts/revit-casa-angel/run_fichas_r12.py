import json, subprocess, sys
from pathlib import Path
R = Path(__file__).parent; O = R / 'openings-r4'
plan = json.loads((O / 'structure-plan.json').read_text(encoding='utf-8'))
def job(**kw):
    p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps(dict(revision='r4', **kw))], capture_output=True, text=True)
    print(kw.get('part'), (p.stdout or p.stderr)[:400], flush=True)
    if p.returncode: raise SystemExit('Revit job failed; stopping')
if (O / 'est-f-test.json').exists(): job(action='r12_fichas', part='test', reset=True)
codes = [e['code'] for e in plan['elements']]
for i in range(0, len(codes), 8):
    part = 'g%02d' % (i // 8 + 1)
    if not (O / f'est-f-{part}.json').exists(): job(action='r12_fichas', part=part, codes=codes[i:i + 8])
job(action='r11_est', part='export'); job(action='r4_verify')
