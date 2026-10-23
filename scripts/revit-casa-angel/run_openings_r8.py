import json, subprocess, sys
from pathlib import Path
R = Path(__file__).parent; O = R / 'openings-r4'
plan = json.loads((O / 'plan.json').read_text(encoding='utf-8'))
def job(**kw):
    p = subprocess.run([sys.executable, str(R / 'call_openings.py'), json.dumps(dict(revision='r4', **kw))], capture_output=True, text=True)
    print(kw, (p.stdout or p.stderr)[:500], flush=True)
    if p.returncode: raise SystemExit('Revit job failed; stopping')
for r in plan['rooms']:
    if not r['items']: continue
    rec = O / f"room-{r['key']}.json"
    if rec.exists() and not json.loads(rec.read_text(encoding='utf-8')).get('r8'):
        job(action='r4_reset', key=r['key'])
    if not rec.exists(): job(action='r4_room', key=r['key'])
    d = json.loads(rec.read_text(encoding='utf-8'))
    if not d.get('r8'):
        job(action='r4_export', key=r['key'])
        d = json.loads(rec.read_text(encoding='utf-8')); d['r8'] = True; rec.write_text(json.dumps(d, indent=1), encoding='utf-8')
job(action='r4_check'); job(action='r4_verify')
