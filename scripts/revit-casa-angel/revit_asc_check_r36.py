# -*- coding: utf-8 -*-
"""R36 Ascensor paso 0 (read-only, from any Casa-Angel-DOC file with the pilot linked): shaft outline (room 785703) with
segment types and bounding walls; vertical probes inside a Ø1,338 circle on the shaft axis: clear height above +6,00, slabs
at PA/PE, PB floor; doors near the shaft; curtain walls MC-1020586/1020050; Sala de Máquinas PA distance and size."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_asc', os.path.join(ROOT, 'revit_openings_r4.py'))
CTX = imp.load_source('ader_docctx_r30_asc', os.path.join(ROOT, 'docctx_r30.py'))
M = L.M; u = L.u
CATS = [DB.BuiltInCategory.OST_Roofs, DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_StructuralFraming, DB.BuiltInCategory.OST_Ceilings,
        DB.BuiltInCategory.OST_Walls, DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_StructuralFoundation]

def nm(e):
    try: return u(DB.Element.Name.GetValue(e))
    except Exception: return u''

def solids(e):
    o = DB.Options(); o.DetailLevel = DB.ViewDetailLevel.Fine; out = []
    def walk(g):
        for x in g:
            if isinstance(x, DB.Solid) and x.Volume > 1e-9: out.append(x)
            elif isinstance(x, DB.GeometryInstance): walk(x.GetInstanceGeometry())
    g = e.get_Geometry(o)
    if g is not None: walk(g)
    return out

def hits(ld, x, y, z0, z1):
    """all element intervals crossed by the vertical segment (x, y, z0..z1)."""
    ln = DB.Line.CreateBound(DB.XYZ(x, y, z0), DB.XYZ(x, y, z1)); out = []
    o = DB.Outline(DB.XYZ(x - .01, y - .01, z0), DB.XYZ(x + .01, y + .01, z1))
    for cat in CATS:
        for e in DB.FilteredElementCollector(ld).OfCategory(cat).WhereElementIsNotElementType().WherePasses(DB.BoundingBoxIntersectsFilter(o)):
            for s in solids(e):
                try: r = s.IntersectWithCurve(ln, DB.SolidCurveIntersectionOptions())
                except Exception: continue
                for i in range(r.SegmentCount):
                    c = r.GetCurveSegment(i); za, zb = sorted([c.GetEndPoint(0).Z, c.GetEndPoint(1).Z])
                    out.append({'id': e.Id.IntegerValue, 'cat': e.Category.Name, 'type': nm(ld.GetElement(e.GetTypeId())), 'z': [round(za * M, 3), round(zb * M, 3)]})
    return sorted(out, key=lambda h: h['z'][0])

def run(doc, uidoc, job):
    ld = CTX.link_doc(doc); phase = ld.Phases.get_Item(ld.Phases.Size - 1)
    rm = ld.GetElement(DB.ElementId(Int64(785703)))
    segs = []; walls = {}
    for loop in rm.GetBoundarySegments(DB.SpatialElementBoundaryOptions()):
        for sg in loop:
            c = sg.GetCurve(); w = ld.GetElement(sg.ElementId)
            seg = {'kind': c.GetType().Name, 'length_m': round(c.Length * M, 3), 'a': [round(c.GetEndPoint(0).X * M, 3), round(c.GetEndPoint(0).Y * M, 3)], 'b': [round(c.GetEndPoint(1).X * M, 3), round(c.GetEndPoint(1).Y * M, 3)]}
            if isinstance(c, DB.Arc): seg['radius_m'] = round(c.Radius * M, 3); seg['center'] = [round(c.Center.X * M, 3), round(c.Center.Y * M, 3)]
            if w is not None:
                seg['element'] = w.Id.IntegerValue; seg['elementCat'] = w.Category.Name if w.Category else None
                if isinstance(w, DB.Wall):
                    bb = w.get_BoundingBox(None)
                    walls[w.Id.IntegerValue] = {'type': nm(w.WallType), 'width_m': round(w.Width * M, 3), 'z': [round(bb.Min.Z * M, 3), round(bb.Max.Z * M, 3)] if bb else None,
                                                'curtain': w.WallType.Kind == DB.WallKind.Curtain}
            segs.append(seg)
    bb = rm.get_BoundingBox(None); cx = (bb.Min.X + bb.Max.X) / 2; cy = (bb.Min.Y + bb.Max.Y) / 2
    pts = [('centro', cx, cy)] + [('r0,669 %d°' % a, cx + .669 / M * math.cos(math.radians(a)), cy + .669 / M * math.sin(math.radians(a))) for a in range(0, 360, 45)]
    probes = []
    for lab, x, y in pts:
        inside = rm.IsPointInRoom(DB.XYZ(x, y, bb.Min.Z + 1.0 / M))
        hs = hits(ld, x, y, -1.0 / M, 12.0 / M)
        hz = [h for h in hs if h['cat'] not in ('Walls',)]
        above = [h for h in hz if h['z'][1] > 6.05]
        probes.append({'point': lab, 'xy': [round(x * M, 3), round(y * M, 3)], 'insideRoomPB': inside, 'hits': hs,
                       'firstAbove600': above[0] if above else None, 'clear_above_600_m': round(above[0]['z'][0] - 6.0, 3) if above else None,
                       'slabPA': [h for h in hz if 2.4 < h['z'][1] < 3.4], 'slabPE': [h for h in hz if 5.4 < h['z'][1] < 6.4], 'floorPB': [h for h in hz if -.8 < h['z'][1] < .4]})
    doors = []
    o = DB.Outline(bb.Min - DB.XYZ(.6 / M, .6 / M, 1 / M), DB.XYZ(bb.Max.X + .6 / M, bb.Max.Y + .6 / M, 9 / M))
    for e in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType().WherePasses(DB.BoundingBoxIntersectsFilter(o)):
        p = e.Location.Point if hasattr(e.Location, 'Point') else None
        doors.append({'id': e.Id.IntegerValue, 'type': nm(e.Symbol), 'level': nm(ld.GetElement(e.LevelId)), 'point': [round(p.X * M, 3), round(p.Y * M, 3), round(p.Z * M, 3)] if p else None})
    cw = []
    for i in (1020586, 1020050, 364138):
        w = ld.GetElement(DB.ElementId(Int64(i)))
        if w is None: continue
        c = w.Location.Curve if isinstance(w.Location, DB.LocationCurve) else None; b2 = w.get_BoundingBox(None)
        cw.append({'id': i, 'type': nm(w.WallType) if isinstance(w, DB.Wall) else nm(w), 'a': [round(c.GetEndPoint(0).X * M, 3), round(c.GetEndPoint(0).Y * M, 3)] if c else None,
                   'b': [round(c.GetEndPoint(1).X * M, 3), round(c.GetEndPoint(1).Y * M, 3)] if c else None, 'z': [round(b2.Min.Z * M, 3), round(b2.Max.Z * M, 3)] if b2 else None,
                   'width_m': round(w.Width * M, 3) if isinstance(w, DB.Wall) else None})
    sm = ld.GetElement(DB.ElementId(Int64(892788))); sb = sm.get_BoundingBox(None); sp = sm.Location.Point
    smr = {'area_m2': round(sm.Area * M * M, 2), 'bbox_m': [round((sb.Max.X - sb.Min.X) * M, 3), round((sb.Max.Y - sb.Min.Y) * M, 3)], 'point': [round(sp.X * M, 3), round(sp.Y * M, 3)],
           'straight_to_axis_m': round(math.hypot(sp.X - cx, sp.Y - cy) * M, 3), 'manhattan_to_axis_m': round((abs(sp.X - cx) + abs(sp.Y - cy)) * M, 3)}
    rec = {'readAt': L.now(), 'room': {'id': 785703, 'area_m2': round(rm.Area * M * M, 3), 'bbox_m': [round((bb.Max.X - bb.Min.X) * M, 3), round((bb.Max.Y - bb.Min.Y) * M, 3)],
           'axis': [round(cx * M, 3), round(cy * M, 3)], 'segments': segs, 'walls': walls}, 'probes': probes, 'doors': doors, 'curtain': cw, 'salaMaquinas': smr}
    L.R1.write(os.path.join(L.OUT, 'asc36-check.json'), rec)
    return {'status': 'success', 'clear': [(p['point'], p['clear_above_600_m']) for p in probes]}
