# -*- coding: utf-8 -*-
"""R29 Cubierta: model the roof package and CU-02 timber structure (user-approved), keep morphology.
Part 'probe' is read-only."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_cub29', os.path.join(ROOT, 'revit_openings_r4.py'))
OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; R1 = L.R1

def pts(c): return [[round(c.GetEndPoint(0).X * M, 3), round(c.GetEndPoint(0).Y * M, 3), round(c.GetEndPoint(0).Z * M, 3)], [round(c.GetEndPoint(1).X * M, 3), round(c.GetEndPoint(1).Y * M, 3), round(c.GetEndPoint(1).Z * M, 3)]]

def params(e, names):
    out = {}
    for p in e.Parameters:
        n = u(p.Definition.Name)
        if names is None or n in names:
            try: out[n] = round(p.AsDouble() * M, 4) if p.StorageType == DB.StorageType.Double else (u(p.AsString()) if p.StorageType == DB.StorageType.String else p.AsInteger())
            except Exception: pass
    return out

def probe(doc):
    plan = L.read('roof-plan')['elements']
    ids = dict((e['id'], e) for e in plan)
    roofs = []
    for r in [e for e in plan if e['kind'] == 'CU']:
        e = el(doc, r['id']); t = doc.GetElement(e.GetTypeId()); cs = t.GetCompoundStructure()
        faces = []
        for g in e.get_Geometry(DB.Options()):
            if not isinstance(g, DB.Solid) or g.Volume <= 0: continue
            for f in g.Faces:
                if isinstance(f, DB.PlanarFace) and abs(f.FaceNormal.Z) > .1:
                    bb = f.GetBoundingBox(); faces.append({'n': [round(f.FaceNormal.X, 3), round(f.FaceNormal.Y, 3), round(f.FaceNormal.Z, 3)], 'area': round(f.Area * M * M, 2),
                                                           'o': [round(f.Origin.X * M, 2), round(f.Origin.Y * M, 2), round(f.Origin.Z * M, 2)]})
        roofs.append({'code': r['code'], 'id': r['id'], 'class': e.GetType().Name, 'type': u(name(t)), 'typeId': eid(t), 'nRoofs': len([x for x in DB.FilteredElementCollector(doc).OfClass(DB.RoofBase) if x.GetTypeId() == t.Id]),
                      'layers': [[str(l.Function), u(name(doc.GetElement(l.MaterialId))) if l.MaterialId.IntegerValue > 0 else '', round(l.Width * M, 4)] for l in cs.GetLayers()] if cs else None,
                      'level': u(name(doc.GetElement(e.LevelId))), 'baseOffset': round(e.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM).AsDouble() * M, 3) if e.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM) else None,
                      'faces': faces})
    fr = []; types = {}
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_StructuralFraming).WhereElementIsNotElementType():
        if e.Id.IntegerValue not in ids: continue
        r = ids[e.Id.IntegerValue]; t = doc.GetElement(e.GetTypeId())
        types.setdefault(eid(t), {'family': u(t.FamilyName), 'type': u(name(t)), 'params': params(t, None), 'count': 0})['count'] += 1
        c = e.Location.Curve if isinstance(e.Location, DB.LocationCurve) else None
        fr.append({'code': r['code'], 'roof': r.get('roof'), 'typeId': eid(t), 'curve': pts(c) if c else None, 'zJust': e.get_Parameter(DB.BuiltInParameter.Z_JUSTIFICATION).AsInteger() if e.get_Parameter(DB.BuiltInParameter.Z_JUSTIFICATION) else None,
                   'yJust': e.get_Parameter(DB.BuiltInParameter.Y_JUSTIFICATION).AsInteger() if e.get_Parameter(DB.BuiltInParameter.Y_JUSTIFICATION) else None,
                   'rot': round(e.get_Parameter(DB.BuiltInParameter.STRUCTURAL_BEND_DIR_ANGLE).AsDouble() * 180 / math.pi, 1) if e.get_Parameter(DB.BuiltInParameter.STRUCTURAL_BEND_DIR_ANGLE) else None})
    return {'roofs': roofs, 'framing': fr, 'framingTypes': types}

# ---------------------------------------------------------------- model (user-approved physical change)

ROOF_TYPE = u'ADER Cubierta tejas + paquete R29'
LAYERS = [  # exterior (top) → interior (bottom); membranes have 0 thickness
    ('Finish1', u'ADER Teja cerámica', .020), ('Substrate', u'ADER Cámara ventilada 25 (contraclavaderas)', .025), ('Membrane', u'ADER Membrana hidrófuga respirable', 0.0),
    ('Insulation', u'ADER EPS 75 mm 20 kg/m³ (entre clavaderas)', .075), ('Membrane', u'ADER Barrera de vapor PE 200 µm', 0.0), ('Structure', u'ADER Machimbre pino 3/4" visto', .019)]
SECTIONS = {'VP': (u'Cabio LVL 50x150 (R29)', .05, .15), 'CR': (u'Listón LVL 25x50 (R29)', .025, .05)}
SPACING = .957   # same rafter spacing as CU-01 (m)

def material(doc, nm):
    for m in DB.FilteredElementCollector(doc).OfClass(DB.Material):
        if u(name(m)) == nm: return m.Id
    return DB.Material.Create(doc, nm)

def roof_type(doc, base):
    for t in DB.FilteredElementCollector(doc).OfClass(DB.RoofType):
        if u(name(t)) == ROOF_TYPE: return t
    t = base.Duplicate(ROOF_TYPE)
    ls = List[DB.CompoundStructureLayer]()
    for fn, mat, w in LAYERS:
        ls.Add(DB.CompoundStructureLayer(w / M, getattr(DB.MaterialFunctionAssignment, fn), material(doc, mat)))
    cs = DB.CompoundStructure.CreateSimpleCompoundStructure(ls)
    t.SetCompoundStructure(cs)
    return t

def framing_type(doc, base, nm, w, h):
    for t in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        if u(name(t)) == nm: return t
    t = base.Duplicate(nm)
    t.LookupParameter('Width').Set(w / M); t.LookupParameter('Height').Set(h / M)
    return t

def plane_z(f, x, y):
    n = f.FaceNormal; o = f.Origin
    return o.Z - (n.X * (x - o.X) + n.Y * (y - o.Y)) / n.Z

def seg_hits(poly, p, d):
    """t values where the plan line p + t·d crosses the polygon edges (2D)."""
    ts = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = b.X - a.X, b.Y - a.Y; den = d.X * ey - d.Y * ex
        if abs(den) < 1e-9: continue
        t = ((a.X - p.X) * ey - (a.Y - p.Y) * ex) / den; s = ((a.X - p.X) * d.Y - (a.Y - p.Y) * d.X) / den
        if -1e-6 <= s <= 1 + 1e-6: ts.append(t)
    return ts

def cu02_structure(doc, roof, rafter, hip, level):
    faces = []
    for g in roof.get_Geometry(DB.Options()):
        if isinstance(g, DB.Solid) and g.Volume > 0:
            faces += [f for f in g.Faces if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.1]
    made = []; edges = {}
    for f in faces:
        poly = [c.GetEndPoint(0) for c in f.GetEdgesAsCurveLoops()[0]]
        n = f.FaceNormal; down = DB.XYZ(-n.X, -n.Y, 0).Normalize(); e = DB.XYZ(-down.Y, down.X, 0)
        o = poly[0]; ss = [(q - o).DotProduct(e) for q in poly]; s0, s1 = min(ss), max(ss)
        k = int(math.floor((s1 - s0 - .1 / M) / (SPACING / M))) + 1; off = ((s1 - s0) - (k - 1) * SPACING / M) / 2
        for i in range(k):
            p = o + e * (s0 + off + i * SPACING / M)
            ts = seg_hits(poly, DB.XYZ(p.X, p.Y, 0), down)
            if len(ts) < 2: continue
            a = p + down * min(ts); b = p + down * max(ts)
            a = DB.XYZ(a.X, a.Y, plane_z(f, a.X, a.Y)); b = DB.XYZ(b.X, b.Y, plane_z(f, b.X, b.Y))
            if a.DistanceTo(b) < .3 / M: continue
            made.append(DB.Line.CreateBound(b, a))      # from the high end down to the eave
        for c in f.GetEdgesAsCurveLoops()[0]:
            a, b = c.GetEndPoint(0), c.GetEndPoint(1)
            key = tuple(sorted([(round(a.X, 2), round(a.Y, 2), round(a.Z, 2)), (round(b.X, 2), round(b.Y, 2), round(b.Z, 2))]))
            edges.setdefault(key, []).append((a, b))
    out = {'rafters': [], 'hips': []}
    for ln in made:
        fi = doc.Create.NewFamilyInstance(ln, rafter, level, DB.Structure.StructuralType.Beam); out['rafters'].append(fi)
    for key, segs in edges.items():
        if len(segs) < 2: continue          # eave edges belong to one face only
        a, b = segs[0]
        if a.DistanceTo(b) < .3 / M: continue
        fi = doc.Create.NewFamilyInstance(DB.Line.CreateBound(a, b), hip, level, DB.Structure.StructuralType.Beam); out['hips'].append(fi)
    for fi in out['rafters'] + out['hips']:
        for bip, v in [(DB.BuiltInParameter.Z_JUSTIFICATION, 0), (DB.BuiltInParameter.Y_JUSTIFICATION, 2)]:
            p = fi.get_Parameter(bip)
            if p and not p.IsReadOnly: p.Set(v)
    return out

def model(doc):
    plan = L.read('roof-plan')['elements']
    roofs = [el(doc, r['id']) for r in plan if r['kind'] == 'CU']
    vp = [el(doc, r['id']) for r in plan if r['kind'] == 'VP']; cr = [el(doc, r['id']) for r in plan if r['kind'] == 'CR']; vc0 = el(doc, [r['id'] for r in plan if r['kind'] == 'VC'][0])
    before = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().GetElementCount()
    tx = DB.Transaction(doc, 'ADER CUB R29 - paquete y estructura (aprobado por el usuario)'); tx.Start()
    try:
        rt = roof_type(doc, doc.GetElement(roofs[0].GetTypeId()))
        for r in roofs: r.RoofType = rt
        cab = framing_type(doc, doc.GetElement(vp[0].GetTypeId()), *SECTIONS['VP']); lis = framing_type(doc, doc.GetElement(cr[0].GetTypeId()), *SECTIONS['CR'])
        for s in (cab, lis):
            if not s.IsActive: s.Activate()
        for e in vp: e.Symbol = cab
        for e in cr: e.Symbol = lis
        cu02 = el(doc, [r['id'] for r in plan if r['code'] == 'CU-02'][0])
        made = cu02_structure(doc, cu02, cab, doc.GetElement(vc0.GetTypeId()), el(doc, 353988))
        tx.Commit()
    except Exception:
        tx.RollBack(); raise
    doc.Save()
    after = DB.FilteredElementCollector(doc).WhereElementIsNotElementType().GetElementCount()
    rec = {'readAt': L.now(), 'roofType': eid(rt), 'roofs': [eid(r) for r in roofs], 'cabio': eid(cab), 'liston': eid(lis), 'vpRetyped': len(vp), 'crRetyped': len(cr),
           'cu02Rafters': [[eid(x), pts(x.Location.Curve)] for x in made['rafters']], 'cu02Hips': [[eid(x), pts(x.Location.Curve)] for x in made['hips']], 'elementsBefore': before, 'elementsAfter': after,
           'layers': [[fn, mat, w] for fn, mat, w in LAYERS], 'sections': dict((k, [v[0], v[1], v[2]]) for k, v in SECTIONS.items()), 'spacing_m': SPACING}
    R1.write(os.path.join(OUT, 'cub29-model.json'), rec)
    return rec

def run(doc, uidoc, job):
    if job['part'] == 'model':
        L.assert_pilot(doc)
        rec = model(doc)
        return {'status': 'success', 'roofType': rec['roofType'], 'vp': rec['vpRetyped'], 'cr': rec['crRetyped'], 'rafters': len(rec['cu02Rafters']), 'hips': len(rec['cu02Hips']), 'elements': [rec['elementsBefore'], rec['elementsAfter']]}
    L.assert_pilot(doc)
    if job['part'] == 'probe':
        d = probe(doc); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'cub29-probe.json'), d)
        return {'status': 'success', 'roofs': [(r['code'], r['class'], r['type'], r['nRoofs'], r['layers'], len(r['faces'])) for r in d['roofs']], 'types': d['framingTypes']}
    raise Exception('Unknown part')
