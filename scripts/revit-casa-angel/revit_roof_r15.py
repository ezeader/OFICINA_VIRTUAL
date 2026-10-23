# -*- coding: utf-8 -*-
"""R15 read-only roof inventory: roofs (slope, area, footprint), timber framing, fascia, gutters."""
import os, imp, math, datetime
from Autodesk.Revit import DB
ROOT = os.path.dirname(__file__)
R1 = imp.load_source('ader_roof_r15_lib', os.path.join(ROOT, 'revit_openings_r1.py'))
clean = R1.clean; name = R1.name; eid = R1.eid; xyz = R1.xyz
M = .3048; M2 = M * M; M3 = M2 * M

def u(s):
    if s is None: return u''
    return s if isinstance(s, unicode) else clean(s)

def pv(e, bip, f=1.):
    try:
        p = e.get_Parameter(bip)
        if p is None or not p.HasValue: return None
        if p.StorageType == DB.StorageType.Double: return p.AsDouble() * f
        if p.StorageType == DB.StorageType.ElementId: return int(p.AsElementId().Value)
        return u(p.AsValueString() or p.AsString())
    except: return None

def inventory(doc):
    roofs = []
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Roofs).WhereElementIsNotElementType():
        t = doc.GetElement(e.GetTypeId()); b = e.get_BoundingBox(None)
        row = {'id': eid(e), 'type': u(name(t)), 'level': u(name(doc.GetElement(e.LevelId))), 'levelId': int(e.LevelId.Value),
               'area_m2': pv(e, DB.BuiltInParameter.HOST_AREA_COMPUTED, M2), 'volume_m3': pv(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED, M3),
               'baseOffset_m': pv(e, DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM, M), 'maxHeight_m': pv(e, DB.BuiltInParameter.ACTUAL_MAX_RIDGE_HEIGHT_PARAM, M),
               'slope': pv(e, DB.BuiltInParameter.ROOF_SLOPE), 'thickness_m': pv(e, DB.BuiltInParameter.ROOF_ATTR_THICKNESS_PARAM, M),
               'bbox': R1.bbox(e), 'kind': type(e).__name__, 'edges': []}
        if isinstance(e, DB.FootPrintRoof):
            try:
                profs = e.GetProfiles()
                for prof in profs:
                    for mc in prof:
                        c = mc.GeometryCurve; dfs = e.get_DefinesSlope(mc); sl = e.get_SlopeAngle(mc) if dfs else 0
                        row['edges'].append({'a': xyz(c.GetEndPoint(0)), 'b': xyz(c.GetEndPoint(1)), 'length_m': c.Length * M, 'definesSlope': dfs, 'slopeDeg': math.degrees(math.atan(sl)) if dfs else 0, 'overhang_m': e.get_Overhang(mc) * M})
            except Exception as ex: row['edgeError'] = str(ex)
        # actual top faces slope from geometry
        try:
            opt = DB.Options(); slopes = []
            for g in e.get_Geometry(opt):
                if isinstance(g, DB.Solid):
                    for f in g.Faces:
                        if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z > .2:
                            slopes.append({'deg': math.degrees(math.acos(min(1, f.FaceNormal.Z))), 'area_m2': f.Area * M2, 'normal': xyz(f.FaceNormal)})
            row['topFaces'] = sorted(slopes, key=lambda x: -x['area_m2'])[:12]
        except Exception as ex: row['geomError'] = str(ex)
        roofs.append(row)
    framing = []
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralFraming).WhereElementIsNotElementType():
        t = doc.GetElement(e.GetTypeId()); c = e.Location.Curve if isinstance(e.Location, DB.LocationCurve) else None
        framing.append({'id': eid(e), 'type': u(name(t)), 'family': u(t.FamilyName), 'length_m': pv(e, DB.BuiltInParameter.INSTANCE_LENGTH_PARAM, M) or (c.Length * M if c else None),
                        'cutLength_m': pv(e, DB.BuiltInParameter.STRUCTURAL_FRAME_CUT_LENGTH, M), 'refLevel': pv(e, DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM),
                        'volume_m3': pv(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED, M3), 'a': xyz(c.GetEndPoint(0)) if c else None, 'b': xyz(c.GetEndPoint(1)) if c else None,
                        'bbox': R1.bbox(e), 'material': u(name(doc.GetElement(e.StructuralMaterialId))) if e.StructuralMaterialId != DB.ElementId.InvalidElementId else u'',
                        'b_m': pv(t, DB.BuiltInParameter.STRUCTURAL_SECTION_COMMON_WIDTH, M), 'h_m': pv(t, DB.BuiltInParameter.STRUCTURAL_SECTION_COMMON_HEIGHT, M),
                        'typeParams': dict((u(p.Definition.Name), u(p.AsValueString() or p.AsString() or u'')) for p in t.Parameters if p.HasValue and p.Definition.Name in ('b', 'h', 'd', 'Width', 'Height', 'Depth', 'Ancho', 'Alto'))})
    others = []
    for cn in ['OST_Fascia', 'OST_Gutter', 'OST_RoofSoffit']:
        for e in DB.FilteredElementCollector(doc).OfCategory(getattr(DB.BuiltInCategory, cn)).WhereElementIsNotElementType():
            t = doc.GetElement(e.GetTypeId())
            others.append({'id': eid(e), 'category': cn, 'type': u(name(t)), 'length_m': pv(e, DB.BuiltInParameter.CURVE_ELEM_LENGTH, M) or pv(e, DB.BuiltInParameter.HOST_PERIMETER_COMPUTED, M),
                           'bbox': R1.bbox(e), 'profile': pv(t, DB.BuiltInParameter.FASCIA_PROFILE_PARAM)})
    alero = [{'id': eid(e), 'type': u(name(doc.GetElement(e.GetTypeId()))), 'area_m2': pv(e, DB.BuiltInParameter.HOST_AREA_COMPUTED, M2), 'bbox': R1.bbox(e), 'level': u(name(doc.GetElement(e.LevelId)))}
             for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsNotElementType() if 'Alero' in u(name(doc.GetElement(e.GetTypeId())))]
    data = {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'roofs': roofs, 'framing': framing, 'others': others, 'alero': alero}
    R1.write(os.path.join(ROOT, 'openings-r4', 'roof-raw.json'), data)
    return {'status': 'success', 'roofs': len(roofs), 'framing': len(framing), 'others': len(others), 'alero': len(alero)}

def run(doc, uidoc, job):
    assert os.path.basename(doc.PathName).lower() == 'casa-angel-piloto-documentacion.rvt'
    return inventory(doc)
