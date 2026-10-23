import json, subprocess, sys
from pathlib import Path
R = Path(__file__).parent; O = R / 'openings-r4'
plan = json.loads((O / 'plan.json').read_text(encoding='utf-8'))
def job(**kw):
    p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps(dict(revision='r4', **kw))], capture_output=True, text=True)
    print(kw, (p.stdout or p.stderr)[:600], flush=True)
    if p.returncode: raise SystemExit('Revit job failed; stopping before dependent work')
for r in plan['rooms']:
    if not r['items']: continue
    rec = O / f"room-{r['key']}.json"
    if not rec.exists(): job(action='r4_room', key=r['key'])
    if not json.loads(rec.read_text(encoding='utf-8')).get('exported'): job(action='r4_export', key=r['key'])
job(action='r4_verify')
