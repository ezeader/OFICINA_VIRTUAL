# -*- coding: utf-8 -*-
"""R35 Domótica etapa 2 · read-only extraction from the linked pilot (run in Casa-Angel-DOC-Domotica.rvt):
rooms (boundary, centre), doors and windows (point, width, wall direction, facing, rooms on each side), electrical and
mechanical equipment, stairs and roofs. Output openings-r4/dom35-model.json for the placement rules (publish side)."""
import os, imp
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_dom', os.path.join(ROOT, 'revit_openings_r4.py'))
CTX = imp.load_source('ader_docctx_r30_dom', os.path.join(ROOT, 'docctx_r30.py'))
M = L.M; u = L.u

def nm(e):
    try: return u(DB.Element.Name.GetValue(e))
    except Exception: return u(getattr(e, 'Name', u''))

def lvname(d, e):
    try:
        lid = e.LevelId
        if lid is None or lid.IntegerValue < 0:
            p = e.get_Parameter(DB.BuiltInParameter.FAMILY_LEVEL_PARAM) or e.get_Parameter(DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM)
            lid = p.AsElementId() if p is not None else None
        return nm(d.GetElement(lid)) if lid is not None and lid.IntegerValue > 0 else None
    except Exception: return None

def xy(p): return [round(p.X * M, 3), round(p.Y * M, 3), round(p.Z * M, 3)]

def width(e):
    for src in (e, e.Symbol):
        for b in (DB.BuiltInParameter.DOOR_WIDTH, DB.BuiltInParameter.WINDOW_WIDTH, DB.BuiltInParameter.FAMILY_WIDTH_PARAM):
            p = src.get_Parameter(b)
            if p is not None and p.HasValue and p.AsDouble() > 0: return round(p.AsDouble() * M, 3)
        p = src.LookupParameter('Width') or src.LookupParameter('Ancho')
        if p is not None and p.HasValue and p.AsDouble() > 0: return round(p.AsDouble() * M, 3)
    return None

def run(doc, uidoc, job):
    ld = CTX.link_doc(doc); phase = ld.Phases.get_Item(ld.Phases.Size - 1)
    rooms = []
    opt = DB.SpatialElementBoundaryOptions()
    for r in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if r.Area <= 0 or r.Location is None: continue
        loops = r.GetBoundarySegments(opt); poly = []
        if loops and loops.Count:
            best = max(loops, key=lambda lp: sum(s.GetCurve().Length for s in lp))
            poly = [xy(s.GetCurve().GetEndPoint(0))[:2] for s in best]
        bb = r.get_BoundingBox(None)
        rooms.append({'id': r.Id.IntegerValue, 'name': u(r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() or u''), 'number': u(r.Number or u''),
                      'level': lvname(ld, r), 'area_m2': round(r.Area * M * M, 2), 'point': xy(r.Location.Point), 'poly': poly,
                      'bbox': xy(bb.Min)[:2] + xy(bb.Max)[:2] if bb else None})
    ops = []
    for cat, kind in ((DB.BuiltInCategory.OST_Doors, 'door'), (DB.BuiltInCategory.OST_Windows, 'window')):
        for e in DB.FilteredElementCollector(ld).OfCategory(cat).WhereElementIsNotElementType():
            if not isinstance(e, DB.FamilyInstance) or e.Location is None or not hasattr(e.Location, 'Point'): continue
            h = e.Host; wd = None
            if isinstance(h, DB.Wall) and isinstance(h.Location, DB.LocationCurve):
                c = h.Location.Curve
                if isinstance(c, DB.Line): wd = [round(c.Direction.X, 4), round(c.Direction.Y, 4)]
            def rn(r): return {'id': r.Id.IntegerValue, 'name': u(r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() or u'')} if r is not None else None
            try: fr = rn(e.get_FromRoom(phase)); to = rn(e.get_ToRoom(phase))
            except Exception: fr = to = None
            bb = e.get_BoundingBox(None)
            ops.append({'id': e.Id.IntegerValue, 'kind': kind, 'family': u(e.Symbol.FamilyName), 'type': nm(e.Symbol), 'level': lvname(ld, e),
                        'point': xy(e.Location.Point), 'width_m': width(e), 'wallDir': wd, 'facing': [round(e.FacingOrientation.X, 4), round(e.FacingOrientation.Y, 4)],
                        'hand': [round(e.HandOrientation.X, 4), round(e.HandOrientation.Y, 4)], 'from': fr, 'to': to,
                        'mark': u(e.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK).AsString() or u''), 'bboxZ': [round(bb.Min.Z * M, 3), round(bb.Max.Z * M, 3)] if bb else None})
    eq = []
    for cat, kind in ((DB.BuiltInCategory.OST_ElectricalEquipment, 'electrical'), (DB.BuiltInCategory.OST_MechanicalEquipment, 'mechanical'),
                      (DB.BuiltInCategory.OST_ElectricalFixtures, 'elecfixture'), (DB.BuiltInCategory.OST_PlumbingFixtures, 'plumbing')):
        for e in DB.FilteredElementCollector(ld).OfCategory(cat).WhereElementIsNotElementType():
            if not isinstance(e, DB.FamilyInstance): continue
            bb = e.get_BoundingBox(None)
            if bb is None: continue
            p = (bb.Min + bb.Max) * .5
            rm = None
            try: rm = e.get_Room(phase)
            except Exception: pass
            eq.append({'id': e.Id.IntegerValue, 'kind': kind, 'family': u(e.Symbol.FamilyName), 'type': nm(e.Symbol), 'level': lvname(ld, e), 'point': xy(p),
                       'room': u(rm.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()) if rm is not None else None})
    st = []
    for e in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Stairs).WhereElementIsNotElementType():
        bb = e.get_BoundingBox(None)
        if bb is None: continue
        st.append({'id': e.Id.IntegerValue, 'bbox': xy(bb.Min) + xy(bb.Max), 'name': nm(e)})
    rf = []
    for e in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Roofs).WhereElementIsNotElementType():
        bb = e.get_BoundingBox(None)
        if bb is not None: rf.append({'id': e.Id.IntegerValue, 'bbox': xy(bb.Min) + xy(bb.Max)})
    cw = []
    for w in DB.FilteredElementCollector(ld).OfClass(DB.Wall):
        try:
            if w.WallType.Kind != DB.WallKind.Curtain or not isinstance(w.Location, DB.LocationCurve): continue
        except Exception: continue
        c = w.Location.Curve; a, b = c.GetEndPoint(0), c.GetEndPoint(1); mid = (a + b) * .5
        d = (b - a).Normalize(); n = DB.XYZ(-d.Y, d.X, 0); bb = w.get_BoundingBox(None); z = (bb.Min.Z + min(bb.Max.Z, bb.Min.Z + 1.2 / M) ) * .5 if bb else mid.Z + 1.0 / M
        def room_at(q):
            r = ld.GetRoomAtPoint(DB.XYZ(q.X, q.Y, z), phase)
            return {'id': r.Id.IntegerValue, 'name': u(r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() or u'')} if r is not None else None
        doors = 0
        try:
            for pid in w.CurtainGrid.GetPanelIds():
                pe = ld.GetElement(pid)
                if pe is not None and pe.Category is not None and pe.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Doors): doors += 1
        except Exception: pass
        cw.append({'id': w.Id.IntegerValue, 'type': nm(w.WallType), 'level': lvname(ld, w), 'a': xy(a), 'b': xy(b), 'length_m': round(c.Length * M, 3),
                   'height_m': round((bb.Max.Z - bb.Min.Z) * M, 3) if bb else None, 'left': room_at(mid + n * (.4 / M)), 'right': room_at(mid - n * (.4 / M)), 'doorPanels': doors})
    lv = sorted([(round(l.Elevation * M, 3), nm(l)) for l in DB.FilteredElementCollector(ld).OfClass(DB.Level)])
    rec = {'readAt': L.now(), 'levels': lv, 'rooms': rooms, 'openings': ops, 'equipment': eq, 'stairs': st, 'roofs': rf, 'curtain': cw}
    L.R1.write(os.path.join(L.OUT, 'dom35-model.json'), rec)
    return {'status': 'success', 'rooms': len(rooms), 'openings': len(ops), 'equipment': len(eq), 'stairs': len(st), 'roofs': len(rf), 'curtain': len(cw)}
