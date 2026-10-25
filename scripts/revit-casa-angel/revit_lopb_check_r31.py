# -*- coding: utf-8 -*-
"""R31 read-only check of LO-PB-01 (714161) after the type change: type, layers, shape edits, dependents, faces z."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_lopbchk', os.path.join(ROOT, 'revit_openings_r4.py'))
M = L.M; R1 = L.R1; OUT = L.OUT

def faces(doc, i):
    e = doc.GetElement(DB.ElementId(Int64(i))); zs = []
    for g in e.get_Geometry(DB.Options()):
        if isinstance(g, DB.Solid):
            for f in g.Faces:
                if isinstance(f, DB.PlanarFace) and abs(f.FaceNormal.Z) > .99: zs.append((round(f.Origin.Z * M, 3), round(f.Area * M * M, 2), 'top' if f.FaceNormal.Z > 0 else 'bottom'))
    bb = e.get_BoundingBox(None)
    return {'type': DB.Element.Name.GetValue(doc.GetElement(e.GetTypeId())), 'faces': sorted(set(zs)), 'bbox_z': [round(bb.Min.Z * M, 3), round(bb.Max.Z * M, 3)],
            'bbox_xy': [round(bb.Min.X * M, 2), round(bb.Min.Y * M, 2), round(bb.Max.X * M, 2), round(bb.Max.Y * M, 2)]}

def run(doc, uidoc, job):
    lo = doc.GetElement(DB.ElementId(Int64(714161))); t = doc.GetElement(lo.GetTypeId())
    cs = t.GetCompoundStructure()
    layers = [(str(x.Function), round(x.Width * M, 3), doc.GetElement(x.MaterialId).Name if x.MaterialId.IntegerValue > 0 else None) for x in cs.GetLayers()]
    se = lo.GetSlabShapeEditor(); shp = None
    if se is not None:
        try: shp = {'enabled': se.IsEnabled, 'vertices': [round(v.Position.Z * M, 3) for v in se.SlabShapeVertices]}
        except Exception as ex: shp = str(ex)
    deps = {}
    for i in lo.GetDependentElements(None):
        e = doc.GetElement(i); c = e.Category.Name if e is not None and e.Category else type(e).__name__
        deps[c] = deps.get(c, 0) + 1
    zs = []
    opt = DB.Options(); opt.ComputeReferences = False
    for g in lo.get_Geometry(opt):
        if isinstance(g, DB.Solid):
            for f in g.Faces:
                if isinstance(f, DB.PlanarFace) and abs(f.FaceNormal.Z) > .99: zs.append((round(f.Origin.Z * M, 3), round(f.Area * M * M, 2), 'top' if f.FaceNormal.Z > 0 else 'bottom'))
    p = lambda b: lo.get_Parameter(b)
    rec = {'type': DB.Element.Name.GetValue(t), 'layers': layers, 'shape': shp, 'dependents': deps, 'horizFaces': sorted(set(zs)),
           'structural': p(DB.BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL).AsInteger(), 'offset_m': round(p(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).AsDouble() * M, 3),
           'level': doc.GetElement(lo.LevelId).Name, 'modified': doc.IsModified, 'lopb': faces(doc, 714161), 'PL-01': faces(doc, 2287528), 'PL-02': faces(doc, 2488978)}
    R1.write(os.path.join(OUT, 'est31-lopb-check.json'), rec)
    return dict(rec, status='success')
