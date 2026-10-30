# -*- coding: utf-8 -*-
"""R36 Ascensor opción A · read-only pre-check (from a DOC file with the pilot linked): what is on the west side of the 10 cm
partition 368795 (rooms, doors/windows hosted, pipes/ducts/fixtures within 0,25 m, elements joined or attached), and the roof
framing / roofs over the shaft footprint enlarged to 1,40 × 2,60 (cabios and listones to cut, supports for the brochal)."""
import os, imp
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_asc2', os.path.join(ROOT, 'revit_openings_r4.py'))
CTX = imp.load_source('ader_docctx_r30_asc2', os.path.join(ROOT, 'docctx_r30.py'))
M = L.M; u = L.u

def nm(e):
    try: return u(DB.Element.Name.GetValue(e))
    except Exception: return u''

def box(e):
    b = e.get_BoundingBox(None)
    return [round(b.Min.X * M, 3), round(b.Min.Y * M, 3), round(b.Min.Z * M, 3), round(b.Max.X * M, 3), round(b.Max.Y * M, 3), round(b.Max.Z * M, 3)] if b else None

def within(ld, x0, y0, z0, x1, y1, z1, cats=None, skip=()):
    o = DB.Outline(DB.XYZ(x0 / M, y0 / M, z0 / M), DB.XYZ(x1 / M, y1 / M, z1 / M)); out = []
    for e in DB.FilteredElementCollector(ld).WhereElementIsNotElementType().WherePasses(DB.BoundingBoxIntersectsFilter(o)):
        if e.Category is None or e.Id.IntegerValue in skip: continue
        if cats and e.Category.Name not in cats: continue
        if e.Category.CategoryType != DB.CategoryType.Model: continue
        out.append({'id': e.Id.IntegerValue, 'cat': e.Category.Name, 'type': nm(ld.GetElement(e.GetTypeId())), 'box': box(e)})
    return out

def run(doc, uidoc, job):
    ld = CTX.link_doc(doc); phase = ld.Phases.get_Item(ld.Phases.Size - 1)
    w = ld.GetElement(DB.ElementId(Int64(368795)))
    c = w.Location.Curve; a, b = c.GetEndPoint(0), c.GetEndPoint(1)
    hosted = [{'id': i.IntegerValue, 'cat': ld.GetElement(i).Category.Name, 'type': nm(ld.GetElement(ld.GetElement(i).GetTypeId()))}
              for i in w.FindInserts(True, True, True, True)]
    joined = [{'id': i.IntegerValue, 'cat': ld.GetElement(i).Category.Name} for i in DB.JoinGeometryUtils.GetJoinedElements(ld, w)]
    west = ld.GetRoomAtPoint(DB.XYZ(a.X - .3 / M, (a.Y + b.Y) / 2, .5 / M), phase)
    x = a.X * M
    band = within(ld, x - .30, min(a.Y, b.Y) * M - .05, -.3, x + .05, max(a.Y, b.Y) * M + .05, 3.1, skip=(368795,))
    roof = within(ld, 4.243, 8.718, 6.2, 5.643, 11.318, 8.9, cats=('Structural Framing', 'Roofs', 'Walls', 'Ceilings', 'Floors', 'Generic Models'))
    rec = {'readAt': L.now(), 'wall': {'id': 368795, 'type': nm(w.WallType), 'a': [round(a.X * M, 3), round(a.Y * M, 3)], 'b': [round(b.X * M, 3), round(b.Y * M, 3)],
           'locationLine': w.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM).AsInteger(), 'pinned': w.Pinned, 'hosted': hosted, 'joined': joined,
           'topConstraint': nm(ld.GetElement(w.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).AsElementId())) if w.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE) else None},
           'westRoom': nm(west) if west is not None else None, 'westBand': band, 'overShaft': roof}
    L.R1.write(os.path.join(L.OUT, 'asc36-check2.json'), rec)
    return {'status': 'success', 'westRoom': rec['westRoom'], 'hosted': len(hosted), 'joined': len(joined), 'westBand': len(band), 'overShaft': len(roof)}
