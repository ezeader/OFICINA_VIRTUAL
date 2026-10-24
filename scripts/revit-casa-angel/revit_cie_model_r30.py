# -*- coding: utf-8 -*-
"""R30 Cielorrasos: model the proposed ceilings (user-approved): CP regions as real ceilings with the Knauf types
(TC-01 RH / TC-02 ST) at the defined heights; existing "Plain" (TC-03) ceilings and the Lavadero get their documentary
Knauf type. Ceilings under the wooden roof are not deleted (needs explicit OK); Mark is not written."""
import os, imp
from Autodesk.Revit import DB
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_cie30', os.path.join(ROOT, 'revit_openings_r4.py'))
OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; R1 = L.R1
TYPES = {'TC-01': u'Placa de Yeso RH 12,5mm Knauf', 'TC-02': u'Placa de Yeso ST 12,5mm Knauf'}
KEEP_WOOD = (u'Baño PA',)     # user: Baño PA keeps its RH ceiling under the wooden roof

def ctype(doc, nm):
    return next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.CeilingType) if u(name(t)) == nm)

def loops_from(region, z):
    out = List[DB.CurveLoop]()
    for lp in region:
        cl = DB.CurveLoop(); pts = [DB.XYZ(p[0], p[1], z) for p in lp]
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if a.DistanceTo(b) > 1e-3: cl.Append(DB.Line.CreateBound(a, b))
        out.Add(cl)
    return out

def cells_region(cells, z):
    """Union of the 0,5 m probe cells (slab sector) → outline loops."""
    h = .25 / M; solid = None
    for x, y in cells:
        cl = DB.CurveLoop()
        q = [DB.XYZ(x - h, y - h, z), DB.XYZ(x + h, y - h, z), DB.XYZ(x + h, y + h, z), DB.XYZ(x - h, y + h, z)]
        for i in range(4): cl.Append(DB.Line.CreateBound(q[i], q[(i + 1) % 4]))
        s = DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop]([cl]), DB.XYZ.BasisZ, 1.0)
        solid = s if solid is None else DB.BooleanOperationsUtils.ExecuteBooleanOperation(solid, s, DB.BooleanOperationsType.Union)
    regions = []
    for f in solid.Faces:
        if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
            regions.append([[[c.GetEndPoint(0).X, c.GetEndPoint(0).Y] for c in cl] for cl in f.GetEdgesAsCurveLoops()])
    return regions

def model(doc):
    d = L.read('cp-plan')
    for r in d['rooms']: r['name'] = R1.clean(r['name'])
    made = []; retyped = []
    tx = DB.Transaction(doc, 'ADER CIE R30 - cielorrasos propuestos (aprobado por el usuario)'); tx.Start()
    try:
        for r in d['rooms']:
            if r['excluded'] or not r['cp']: continue
            lev = el(doc, r['levelId']); z = lev.Elevation; t = ctype(doc, TYPES[r['docType']])
            regions = cells_region(r['slabCells'], z) if r.get('wood') else r['restLoops']
            h = (2.80 if r.get('wood') else r['height_m'])
            for reg in regions:
                c = DB.Ceiling.Create(doc, loops_from(reg, z), t.Id, lev.Id)
                c.get_Parameter(DB.BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM).Set(h / M)
                made.append({'id': eid(c), 'room': r['id'], 'code': r['code'], 'type': r['docType'], 'height_m': h})
        for e in d['existing']:
            room = next((x for x in d['rooms'] if e['id'] in x.get('woodExisting', []) or any(i == e['id'] for i, _ in x['covered'])), None)
            if e.get('wood') and not (room and room['name'] in KEEP_WOOD): continue
            c = el(doc, e['id']); t = ctype(doc, TYPES[e['docType']])
            if c.GetTypeId() != t.Id: c.ChangeTypeId(t.Id); retyped.append({'id': e['id'], 'code': e['code'], 'from': e['modelType'], 'to': e['docType']})
        tx.Commit()
    except Exception:
        tx.RollBack(); raise
    doc.Save()
    rec = {'readAt': L.now(), 'created': made, 'retyped': retyped}
    R1.write(os.path.join(OUT, 'cie30-model.json'), rec)
    return rec

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Modelar solo en el modelo principal'
    if job['part'] == 'model':
        rec = model(doc)
        return {'status': 'success', 'created': [(c['code'], c['type'], c['height_m']) for c in rec['created']], 'retyped': [(x['code'], x['from'], x['to']) for x in rec['retyped']]}
    raise Exception('Unknown part')
