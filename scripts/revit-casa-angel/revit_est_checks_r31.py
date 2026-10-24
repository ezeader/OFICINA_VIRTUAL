# -*- coding: utf-8 -*-
"""R31 read-only structure checks (runs in any DOC file, reading the linked pilot): plan overlaps between slabs,
levels, materials and perimeters."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_estchk', os.path.join(ROOT, 'revit_openings_r4.py'))
CTX = imp.load_source('ader_docctx_r30_estchk', os.path.join(ROOT, 'docctx_r30.py'))
M = L.M; u = L.u; name = L.name; R1 = L.R1; OUT = L.OUT

def footprint(e):
    """Plan footprint solid (1 ft high at z=0) from the element's downward faces."""
    out = None
    for g in e.get_Geometry(DB.Options()):
        if not isinstance(g, DB.Solid) or g.Volume <= 0: continue
        for f in g.Faces:
            if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
                loops = [DB.CurveLoop.CreateViaTransform(cl, DB.Transform.CreateTranslation(DB.XYZ(0, 0, -f.Origin.Z))) for cl in f.GetEdgesAsCurveLoops()]
                try:
                    s = DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop](loops), DB.XYZ.BasisZ, 1.0)
                    out = s if out is None else DB.BooleanOperationsUtils.ExecuteBooleanOperation(out, s, DB.BooleanOperationsType.Union)
                except Exception: pass
    return out

def info(ld, i):
    e = ld.GetElement(DB.ElementId(Int64(i))); t = ld.GetElement(e.GetTypeId()); b = e.get_BoundingBox(None)
    p = e.get_Parameter(DB.BuiltInParameter.HOST_PERIMETER_COMPUTED); a = e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED)
    mats = sorted(set(u(name(ld.GetElement(m))) for m in e.GetMaterialIds(False)))
    return {'id': i, 'category': u(e.Category.Name), 'type': u(name(t)) if t else u'', 'level': u(name(ld.GetElement(e.LevelId))) if e.LevelId and ld.GetElement(e.LevelId) else None,
            'zBottom_m': round(b.Min.Z * M, 3), 'zTop_m': round(b.Max.Z * M, 3), 'area_m2': round(a.AsDouble() * M * M, 3) if a else None,
            'perimeter_m': round(p.AsDouble() * M, 3) if p else None, 'materials': mats}

def overlap(ld, a, b):
    fa, fb = footprint(ld.GetElement(DB.ElementId(Int64(a)))), footprint(ld.GetElement(DB.ElementId(Int64(b))))
    if fa is None or fb is None: return None
    i = DB.BooleanOperationsUtils.ExecuteBooleanOperation(fa, fb, DB.BooleanOperationsType.Intersect)
    d = DB.BooleanOperationsUtils.ExecuteBooleanOperation(fa, fb, DB.BooleanOperationsType.Difference)
    return {'intersection_m2': round(i.Volume * M * M, 3), 'aOutsideB_m2': round(d.Volume * M * M, 3)}

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L]) or doc
    ids = job['ids']; pairs = job['pairs']
    res = {'elements': dict((str(i), info(ld, i)) for i in ids), 'pairs': [dict({'a': a, 'b': b}, **(overlap(ld, a, b) or {})) for a, b in pairs], 'readAt': L.now()}
    R1.write(os.path.join(OUT, 'est31-checks.json'), res)
    return {'status': 'success', 'pairs': res['pairs'], 'elements': dict((k, (v['type'], v['category'], v['zBottom_m'], v['zTop_m'], v['area_m2'], v['perimeter_m'], v['materials'][:3])) for k, v in res['elements'].items())}
