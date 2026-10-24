# -*- coding: utf-8 -*-
"""R25: read-only data for rubros still to define (revestimientos, parrilla, eléctrica, gas, domótica, solar)."""
import os, imp
from Autodesk.Revit import DB

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_pend', os.path.join(ROOT, 'revit_openings_r4.py'))
OUT = L.OUT; M = L.M; eid = L.eid; u = L.u; name = L.name; R1 = L.R1

def pval(e, bip):
    p = e.get_Parameter(bip)
    return p.AsDouble() if p and p.HasValue else 0.0

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    rooms = []
    for r in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if r.Area <= 0: continue
        rooms.append({'id': eid(r), 'number': u(r.Number), 'name': u(name(r)), 'level': u(name(doc.GetElement(r.LevelId))), 'area_m2': r.Area * M * M,
                      'perimeter_m': r.Perimeter * M, 'height_m': r.UnboundedHeight * M})
    items = []
    for cat in ['OST_SpecialityEquipment', 'OST_DuctCurves', 'OST_ElectricalEquipment', 'OST_ElectricalFixtures', 'OST_LightingFixtures', 'OST_LightingDevices', 'OST_DataDevices', 'OST_FireAlarmDevices', 'OST_SecurityDevices', 'OST_CommunicationDevices', 'OST_GenericModel', 'OST_MechanicalEquipment']:
        for e in DB.FilteredElementCollector(doc).OfCategory(getattr(DB.BuiltInCategory, cat)).WhereElementIsNotElementType():
            t = doc.GetElement(e.GetTypeId()); fam = u(t.FamilyName) if t is not None and hasattr(t, 'FamilyName') else u''
            if cat in ('OST_SpecialityEquipment', 'OST_GenericModel', 'OST_MechanicalEquipment') and not any(k in (fam + u(name(t) if t else u'')).lower() for k in [u'parrilla', u'pump', u'panel', u'solar']): continue
            b = e.get_BoundingBox(None)
            lv = doc.GetElement(e.LevelId) if e.LevelId else None
            items.append({'id': eid(e), 'cat': cat[4:], 'family': fam, 'type': u(name(t)) if t else u'', 'level': u(name(lv)) if lv else None,
                          'length_m': pval(e, DB.BuiltInParameter.CURVE_ELEM_LENGTH) * M, 'diameter_m': pval(e, DB.BuiltInParameter.RBS_CURVE_DIAMETER_PARAM) * M,
                          'bbox': [[b.Min.X * M, b.Min.Y * M, b.Min.Z * M], [b.Max.X * M, b.Max.Y * M, b.Max.Z * M]] if b else None})
    gas = [u(name(t)) for t in DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipingSystemType) if u'gas' in u(name(t)).lower()]
    R1.write(os.path.join(OUT, 'pend-data.json'), {'readAt': L.now(), 'rooms': rooms, 'items': items, 'gasSystemTypes': gas})
    return {'status': 'success', 'rooms': len(rooms), 'items': [(i['cat'], i['family'], i['type']) for i in items], 'gas': gas}
