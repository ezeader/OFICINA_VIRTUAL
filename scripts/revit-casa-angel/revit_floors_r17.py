# -*- coding: utf-8 -*-
"""R17 read-only floors inventory: floor elements + layers, floor type under each room, wall-sweep skirtings."""
import os, imp, datetime
from Autodesk.Revit import DB
ROOT = os.path.dirname(__file__)
R1 = imp.load_source('ader_floors_r17_lib', os.path.join(ROOT, 'revit_openings_r1.py'))
clean = R1.clean; name = R1.name; eid = R1.eid; xyz = R1.xyz
M = .3048; M2 = M * M

def u(s):
    if s is None: return u''
    return s if isinstance(s, unicode) else clean(s)

def solids(e):
    out = []
    for g in e.get_Geometry(DB.Options()) or []:
        if isinstance(g, DB.Solid) and g.Volume > 0: out.append(g)
        elif isinstance(g, DB.GeometryInstance):
            for h in g.GetInstanceGeometry():
                if isinstance(h, DB.Solid) and h.Volume > 0: out.append(h)
    return out

def run(doc, uidoc, job):
    assert os.path.basename(doc.PathName).lower() == 'casa-angel-piloto-documentacion.rvt'
    floors = []; geo = {}
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsNotElementType():
        t = doc.GetElement(e.GetTypeId()); cs = t.GetCompoundStructure() if t else None
        layers = [{'function': str(l.Function), 'material': u(name(doc.GetElement(l.MaterialId))) if l.MaterialId != DB.ElementId.InvalidElementId else u'', 'thickness_m': l.Width * M} for l in (cs.GetLayers() if cs else [])]
        p = e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED)
        floors.append({'id': eid(e), 'type': u(name(t)), 'level': u(name(doc.GetElement(e.LevelId))), 'levelId': int(e.LevelId.Value),
                       'area_m2': p.AsDouble() * M2 if p else None, 'offset_m': (e.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).AsDouble() * M) if e.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM) else None,
                       'layers': layers, 'bbox': R1.bbox(e)})
        geo[eid(e)] = solids(e)
    rooms = []
    for r in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if r.Area <= 0 or not isinstance(r.Location, DB.LocationPoint): continue
        p = r.Location.Point; lev = doc.GetElement(r.LevelId)
        line = DB.Line.CreateBound(DB.XYZ(p.X, p.Y, lev.Elevation - 2.5 / M), DB.XYZ(p.X, p.Y, lev.Elevation + .6 / M))
        hits = []
        for fid, ss in geo.items():
            for s in ss:
                try:
                    res = s.IntersectWithCurve(line, DB.SolidCurveIntersectionOptions())
                    if res.SegmentCount > 0:
                        top = max(res.GetCurveSegment(i).GetEndPoint(1).Z for i in range(res.SegmentCount))
                        hits.append((top, fid)); break
                except: pass
        hits.sort(reverse=True)
        rooms.append({'id': eid(r), 'name': u(r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()), 'number': u(r.Number), 'level': u(name(lev)), 'levelId': int(r.LevelId.Value),
                      'area_m2': r.Area * M2, 'perimeter_m': r.Perimeter * M, 'floorIds': [h[1] for h in hits], 'topFloor': hits[0][1] if hits else None,
                      'finishFloor': u(r.get_Parameter(DB.BuiltInParameter.ROOM_FINISH_FLOOR).AsString() or u''), 'finishBase': u(r.get_Parameter(DB.BuiltInParameter.ROOM_FINISH_BASE).AsString() or u'')})
    sweeps = []
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Cornices).WhereElementIsNotElementType():
        t = doc.GetElement(e.GetTypeId()); L = e.get_Parameter(DB.BuiltInParameter.CURVE_ELEM_LENGTH)
        host = None
        try: host = eid(e.GetHostIds()[0]) if e.GetHostIds().Count else None
        except: pass
        sweeps.append({'id': eid(e), 'type': u(name(t)), 'length_m': L.AsDouble() * M if L else None, 'host': host, 'bbox': R1.bbox(e)})
    R1.write(os.path.join(ROOT, 'openings-r4', 'floors-raw.json'), {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'floors': floors, 'rooms': rooms, 'sweeps': sweeps})
    return {'status': 'success', 'floors': len(floors), 'rooms': len(rooms), 'roomsWithFloor': len([r for r in rooms if r['topFloor']]), 'sweeps': len(sweeps)}
