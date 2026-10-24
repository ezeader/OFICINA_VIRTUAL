# -*- coding: utf-8 -*-
"""R31 (user-approved geometry change): extend the platea under the whole PB — new floor of the PL-01 type
('Platea PB 15CM', same level, same offset, same structural flag) on the plan footprint of LO-PB-01 (714161)."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_platea', os.path.join(ROOT, 'revit_openings_r4.py'))
M = L.M; eid = L.eid; R1 = L.R1; OUT = L.OUT

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    pl = doc.GetElement(DB.ElementId(Int64(2287528))); lo = doc.GetElement(DB.ElementId(Int64(714161)))
    lev = doc.GetElement(pl.LevelId); off = pl.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).AsDouble()
    # union of every downward face's footprint (the slab is stepped) → outline of the union at the level
    sol = None
    for g in lo.get_Geometry(DB.Options()):
        if isinstance(g, DB.Solid) and g.Volume > 0:
            for f in g.Faces:
                if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
                    ls = [DB.CurveLoop.CreateViaTransform(cl, DB.Transform.CreateTranslation(DB.XYZ(0, 0, lev.Elevation - f.Origin.Z))) for cl in f.GetEdgesAsCurveLoops()]
                    try:
                        s = DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop](ls), DB.XYZ.BasisZ, .5)
                        sol = s if sol is None else DB.BooleanOperationsUtils.ExecuteBooleanOperation(sol, s, DB.BooleanOperationsType.Union)
                    except Exception: pass
    assert sol is not None, 'Sin huella de LO-PB-01'
    # the slab's own sketch is a valid boundary by definition (the face union leaves very short segments)
    sk = doc.GetElement(lo.SketchId); loops = []
    for arr in sk.Profile:
        cl = DB.CurveLoop()
        for c in arr: cl.Append(c.CreateTransformed(DB.Transform.CreateTranslation(DB.XYZ(0, 0, lev.Elevation - c.GetEndPoint(0).Z))))
        loops.append(cl)
    tx = DB.Transaction(doc, 'ADER EST R31 - ampliacion de platea bajo LO-PB-01 (OK usuario)'); tx.Start()
    try:
        fl = DB.Floor.Create(doc, List[DB.CurveLoop](loops), pl.GetTypeId(), lev.Id)
        fl.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).Set(off)
        s = pl.get_Parameter(DB.BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL)
        if s is not None: fl.get_Parameter(DB.BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL).Set(s.AsInteger())
        tx.Commit()
    except Exception:
        tx.RollBack(); raise
    doc.Save()
    a = fl.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M; v = fl.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * M ** 3
    rec = {'readAt': L.now(), 'newFloor': eid(fl), 'area_m2': round(a, 3), 'volume_m3': round(v, 3), 'offset_m': round(off * M, 3), 'type': 'Platea PB 15CM'}
    R1.write(os.path.join(OUT, 'est31-platea.json'), rec)
    return dict(rec, status='success')
