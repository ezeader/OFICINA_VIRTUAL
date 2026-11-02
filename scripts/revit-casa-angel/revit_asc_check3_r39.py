# -*- coding: utf-8 -*-
"""R39 Ascensor A1 · read-only data for the model change (run in a DOC file with the pilot linked): framing over the shaft
(curve ends, z, section, type), roof 1086089 over it, floor 1011940 / ceiling 2488781 sketch lines touching x 4,243,
reticulado 2250136 and wine racks 870143 / 1452870 (family, location, length-type parameters)."""
import os, imp
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_asc3', os.path.join(ROOT, 'revit_openings_r4.py'))
CTX = imp.load_source('ader_docctx_r30_asc3', os.path.join(ROOT, 'docctx_r30.py'))
M = L.M; u = L.u

def nm(e):
    try: return u(DB.Element.Name.GetValue(e))
    except Exception: return u''

def p3(p): return [round(p.X * M, 3), round(p.Y * M, 3), round(p.Z * M, 3)]

def params(e):
    out = {}
    for p in e.Parameters:
        try:
            if p.StorageType == DB.StorageType.Double and p.Definition.UnitType if False else p.StorageType == DB.StorageType.Double:
                out[u(p.Definition.Name)] = round(p.AsDouble() * M, 4)
        except Exception: pass
    return out

def run(doc, uidoc, job):
    ld = CTX.link_doc(doc)
    o = DB.Outline(DB.XYZ(4.143 / M, 8.618 / M, 6.2 / M), DB.XYZ(5.743 / M, 11.418 / M, 9.0 / M))
    fr = []
    for e in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_StructuralFraming).WhereElementIsNotElementType().WherePasses(DB.BoundingBoxIntersectsFilter(o)):
        c = e.Location.Curve if isinstance(e.Location, DB.LocationCurve) else None
        fr.append({'id': e.Id.IntegerValue, 'type': nm(e.Symbol), 'family': u(e.Symbol.FamilyName), 'a': p3(c.GetEndPoint(0)) if c else None, 'b': p3(c.GetEndPoint(1)) if c else None,
                   'level': nm(ld.GetElement(e.LevelId)) if e.LevelId.IntegerValue > 0 else None, 'host': e.Host.Id.IntegerValue if e.Host else None})
    def sk(i):
        e = ld.GetElement(DB.ElementId(Int64(i)))
        s = ld.GetElement(e.SketchId) if e is not None and hasattr(e, 'SketchId') else None
        if s is None: return None
        ls = []
        for arr in s.Profile:
            for c in arr: ls.append([p3(c.GetEndPoint(0)), p3(c.GetEndPoint(1))])
        return {'id': i, 'type': nm(ld.GetElement(e.GetTypeId())), 'lines': [x for x in ls if abs(x[0][0] - 4.243) < .02 or abs(x[1][0] - 4.243) < .02], 'n': len(ls)}
    fam = []
    for i in (2250136, 870143, 1452870, 994672, 1156694):
        e = ld.GetElement(DB.ElementId(Int64(i)))
        if e is None: continue
        loc = e.Location; bb = e.get_BoundingBox(None)
        fam.append({'id': i, 'family': u(e.Symbol.FamilyName) if hasattr(e, 'Symbol') else None, 'type': nm(ld.GetElement(e.GetTypeId())),
                    'point': p3(loc.Point) if hasattr(loc, 'Point') else None, 'curve': [p3(loc.Curve.GetEndPoint(0)), p3(loc.Curve.GetEndPoint(1))] if hasattr(loc, 'Curve') else None,
                    'bbox': p3(bb.Min) + p3(bb.Max) if bb else None, 'facing': [round(e.FacingOrientation.X, 3), round(e.FacingOrientation.Y, 3)] if hasattr(e, 'FacingOrientation') else None,
                    'host': e.Host.Id.IntegerValue if getattr(e, 'Host', None) else None, 'inst': params(e), 'typeParams': params(ld.GetElement(e.GetTypeId()))})
    rf = ld.GetElement(DB.ElementId(Int64(1086089)))
    rec = {'readAt': L.now(), 'framing': fr, 'floor': sk(1011940), 'ceiling': sk(2488781), 'families': fam,
           'roof': {'id': 1086089, 'type': nm(rf.RoofType), 'bbox': p3(rf.get_BoundingBox(None).Min) + p3(rf.get_BoundingBox(None).Max)},
           'walls': [{'id': i, 'curve': [p3(ld.GetElement(DB.ElementId(Int64(i))).Location.Curve.GetEndPoint(k)) for k in (0, 1)]} for i in (368795, 1156693)]}
    L.R1.write(os.path.join(L.OUT, 'asc39-check3.json'), rec)
    return {'status': 'success', 'framing': len(fr), 'families': len(fam)}
