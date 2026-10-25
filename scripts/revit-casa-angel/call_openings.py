import json,urllib.request,sys
from pathlib import Path
R=Path(__file__).parent
job=json.loads(sys.argv[1]);(R/'openings-job.json').write_text(json.dumps(job),encoding='utf8')
(R/'openings-r1.flag').write_text('active',encoding='utf8')
port=None
for p in (48884,48885,48886):
 try:
  r=urllib.request.Request(f'http://127.0.0.1:{p}/revit-mcp-v1/diagnostics/revit_state',b'{}',{'Content-Type':'application/json'})
  with urllib.request.urlopen(r,timeout=20) as f:d=json.load(f)
  target=(R/'../../outputs/casa-angel/documentacion'/('Casa-Angel-DOC-%s.rvt'%job['doc'])) if job.get('doc') else (R/'../../outputs/casa-angel/Casa-Angel-piloto-documentacion.rvt')
  dp=d.get('document_state',{}).get('path','').lower()
  if dp==str(target.resolve()).lower() or (job.get('action')=='switch' and dp.startswith(str((R/'../../outputs/casa-angel').resolve()).lower())):port=p;break
 except Exception:pass
if not port:raise RuntimeError('Working copy not available')
r=urllib.request.Request(f'http://127.0.0.1:{port}/revit-mcp-v1/ader/sanitary-documentation',b'{"action":"inspect"}',{'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(r,timeout=240) as f:d=json.load(f)
 print(json.dumps(d,ensure_ascii=True),flush=True)
 if d.get('status')!='success':sys.exit(1)
finally:(R/'openings-r1.flag').unlink(missing_ok=True)
