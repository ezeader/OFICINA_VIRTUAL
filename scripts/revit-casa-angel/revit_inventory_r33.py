# -*- coding: utf-8 -*-
"""R33 read-only inventory of the pilot: every view (no templates) and sheet with name, number, type, dependents count, placed on sheet."""
import os, imp
from Autodesk.Revit import DB
ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_inv', os.path.join(ROOT, 'revit_openings_r4.py'))

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    placed = {}
    for vp in DB.FilteredElementCollector(doc).OfClass(DB.Viewport):
        placed[int(vp.ViewId.Value)] = int(vp.SheetId.Value)
    rows = []
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if v.IsTemplate: continue
        r = {'id': L.eid(v), 'name': v.Name, 'type': str(v.ViewType), 'sheet': placed.get(L.eid(v))}
        if isinstance(v, DB.ViewSheet): r['number'] = v.SheetNumber
        try: r['owned'] = len(DB.FilteredElementCollector(doc, v.Id).WhereElementIsNotElementType().ToElementIds()) if r['type'] in ('DraftingView', 'Legend') else None
        except Exception: r['owned'] = None
        rows.append(r)
    L.R1.write(os.path.join(L.OUT, 'r33-inventory.json'), {'views': rows, 'readAt': L.now()})
    return {'status': 'success', 'count': len(rows)}
