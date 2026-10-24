# -*- coding: utf-8 -*-
"""R30 read-only audit: views / sheets / annotation elements in the pilot, grouped by the ADER prefix that created them."""
import os, imp, re
from Autodesk.Revit import DB

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_audit', os.path.join(ROOT, 'revit_openings_r4.py'))
u = L.u; name = L.name

def group_of(n):
    m = re.match(r'ADER ([A-Z]+(?: [A-Z]+)?) (R\d+)', n)
    if m: return m.group(1) + ' ' + m.group(2)
    if n.startswith('ADER'): return n.split(' - ')[0][:24]
    return 'original'

SHEET_RUBRO = [('ABR-', 'Aberturas'), ('EST-', 'Estructura'), ('CUB-', 'Cubierta'), ('PIS-', 'Pisos'), ('CLI-', 'Climatización'), ('ALB-', 'Albañilería'),
               ('CIE-', 'Cielorrasos'), ('PIL-', 'Pileta'), ('EXT-', 'Exteriores'), ('EQ-', 'Equipamiento'), ('RV-', 'Revestimientos'), ('SAN', 'Sanitarias'), ('IS-', 'Sanitarias')]

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    views = {}; sheets = {}
    for v in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if v.IsTemplate: continue
        if isinstance(v, DB.ViewSheet):
            g = next((r for p, r in SHEET_RUBRO if v.SheetNumber.startswith(p)), 'otras')
            sheets[g] = sheets.get(g, 0) + 1
        else:
            g = group_of(u(name(v))); views[g] = views.get(g, 0) + 1
    ann = {}
    for cat in ['OST_TextNotes', 'OST_Dimensions', 'OST_Lines', 'OST_DetailComponents', 'OST_Viewports']:
        ann[cat[4:]] = DB.FilteredElementCollector(doc).OfCategory(getattr(DB.BuiltInCategory, cat)).WhereElementIsNotElementType().GetElementCount()
    total = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().GetElementCount()
    return {'status': 'success', 'views': sorted(views.items(), key=lambda x: -x[1]), 'sheets': sorted(sheets.items(), key=lambda x: -x[1]),
            'viewsTotal': sum(views.values()), 'sheetsTotal': sum(sheets.values()), 'annotation': ann, 'elements': total}
