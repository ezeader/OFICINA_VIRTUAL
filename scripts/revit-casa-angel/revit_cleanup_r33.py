# -*- coding: utf-8 -*-
"""R33 (user-approved per rubro): delete old ADER views/sheets of migrated rubros from the pilot, listed in r33-plan-<R>.json.
Only View elements (sheets included); chunks of 50, one transaction each; stops when the time budget is spent; then saves."""
import os, imp, time, json
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List
ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_clean', os.path.join(ROOT, 'revit_openings_r4.py'))

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    t0 = time.time(); budget = job.get('seconds', 600); log = {}
    for r in job['rubros']:
        ids = json.load(open(os.path.join(L.OUT, 'r33-plan-' + r + '.json')))['delete']
        views = []
        for i in ids:
            e = doc.GetElement(DB.ElementId(Int64(int(i))))
            if e is None: continue
            assert isinstance(e, DB.View) and not e.IsTemplate, 'No es vista: %s' % i
            views.append(e.Id)
        done = 0
        for k in range(0, len(views), 50):
            if time.time() - t0 > budget: log[r] = {'deleted': done, 'pending': len(views) - done, 'stopped': 'tiempo'}; break
            chunk = [x for x in views[k:k + 50] if doc.GetElement(x) is not None]   # a sheet may have taken its views already
            tx = DB.Transaction(doc, 'ADER R33 - limpieza %s %d' % (r, k // 50 + 1)); tx.Start()
            try: doc.Delete(List[DB.ElementId](chunk)); tx.Commit()
            except Exception:
                tx.RollBack(); raise
            done += len(chunk)
        else: log[r] = {'deleted': done, 'pending': 0}
    doc.Save()
    log['seconds'] = round(time.time() - t0, 1)
    L.R1.write(os.path.join(L.OUT, 'r33-cleanup.json'), log)
    return dict(log, status='success')
