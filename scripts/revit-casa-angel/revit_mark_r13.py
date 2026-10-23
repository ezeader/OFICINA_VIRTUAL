# -*- coding: utf-8 -*-
"""R13: write structure codes into the Mark parameter of the 72 structural elements (user-approved).
Only ALL_MODEL_MARK is touched; previous values are recorded; physical snapshot must stay identical."""
import os, imp
from Autodesk.Revit import DB
ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_mark', os.path.join(ROOT, 'revit_openings_r4.py'))

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    if job.get('part') == 'notes': return fix_notes(doc, job)
    plan = L.read('structure-plan'); rows = []
    def body():
        for r in plan['elements']:
            e = L.el(doc, r['id']); p = e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
            old = p.AsString()
            if old != r['code']:
                assert not p.IsReadOnly, 'Mark read-only on ' + str(r['id'])
                p.Set(r['code'])
            rows.append({'id': r['id'], 'code': r['code'], 'previous': old, 'written': p.AsString() == r['code']})
        return rows
    out, checked = L.guarded(doc, 'ADER EST R13 - codigos en Mark (aprobado por el usuario)', body)
    L.write('mark-r13', {'readAt': L.now(), 'physicalChecked': checked, 'rows': out})
    doc.Save()
    dup = {}
    for x in out:
        if x['previous']: dup[x['previous']] = dup.get(x['previous'], 0) + 1
    return {'status': 'success', 'written': sum(1 for x in out if x['written']), 'total': len(out),
            'hadPrevious': [(x['code'], x['previous']) for x in out if x['previous'] and x['previous'] != x['code']], 'physicalChecked': checked}

def fix_notes(doc, job):
    reps = [(u'solo como anotaci\u00f3n (no se escribieron en el modelo)', u'escritos tambi\u00e9n en el par\u00e1metro Mark del modelo'),
            (u'C\u00f3digos como anotaci\u00f3n.', u'C\u00f3digos escritos en Mark.'),
            (u'no se escribieron en el par\u00e1metro Mark (cambio de modelo, pendiente de OK).', u'escritos en el par\u00e1metro Mark (aprobado por el usuario).'),
            (u'LO losas y paquetes de piso, PL platea. Solo anotaci\u00f3n:', u'LO losas y paquetes de piso, PL platea. Tambi\u00e9n en Mark:')]
    changed = []
    def body():
        for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet):
            if not s.SheetNumber.startswith('EST-'): continue
            for n in DB.FilteredElementCollector(doc, s.Id).OfClass(DB.TextNote):
                t = n.Text; t2 = t
                for a, b in reps: t2 = t2.replace(a, b)
                if t2 != t: n.Text = t2; changed.append(s.SheetNumber)
        return changed
    out, checked = L.guarded(doc, 'ADER EST R13 - notas Mark', body)
    doc.Save()
    return {'status': 'success', 'notesChanged': len(out), 'sheets': len(set(out))}
