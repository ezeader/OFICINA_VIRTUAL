# -*- coding: utf-8 -*-
"""R34e: pase en losa L01 para el conducto de la parrilla (OK del usuario 30/10: agrandar a 0,50 x 0,50).
probe: read the Pase_Rectangular instance; apply: center it on the conducto axis and set 0,50 x 0,50."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
ROOT = os.path.dirname(__file__)
P = imp.load_source('ader_par_r34_for_pase', os.path.join(ROOT, 'revit_par_r34.py'))
M = P.M; u = P.u; name = P.name; R1 = P.R1; OUT = P.OUT
PASE = 2349814
SLAB = 2157154          # L01.00 / 20cm (PA floor over the Quincho)

def info(e):
    ps = {}
    for p in e.Parameters:
        try: ps[u(p.Definition.Name)] = (p.AsValueString() or p.AsString(), p.IsReadOnly, str(p.StorageType))
        except Exception: pass
    t = e.Document.GetElement(e.GetTypeId()); tp = {}
    for p in t.Parameters:
        try: tp[u(p.Definition.Name)] = (p.AsValueString() or p.AsString(), str(p.StorageType))
        except Exception: pass
    loc = e.Location
    return {'family': u(e.Symbol.FamilyName), 'type': u(name(t)), 'point': P.mx(loc.Point) if hasattr(loc, 'Point') else None, 'bbox': P.bbm(e),
            'host': (u(name(e.Host)) + ' #' + str(e.Host.Id.IntegerValue)) if e.Host else None, 'params': ps, 'typeParams': tp,
            'rotation': getattr(loc, 'Rotation', None), 'hand': [e.HandOrientation.X, e.HandOrientation.Y], 'facing': [e.FacingOrientation.X, e.FacingOrientation.Y]}

def run(doc, uidoc, job):
    assert os.path.basename(doc.PathName).lower() == 'casa-angel-piloto-documentacion.rvt', 'Abrir el modelo principal'
    e = doc.GetElement(DB.ElementId(Int64(PASE)))
    if job['part'] == 'probe': return {'status': 'success', 'pase': info(e)}
    if job['part'] == 'apply':
        # the Pase_Rectangular 2349814 is a 0,19 x 0,14 opening in the H° wall (not the slab): it stays. The slab L01 gets a new 0,50 x 0,50 shaft opening.
        fl = doc.GetElement(DB.ElementId(Int64(SLAB)))
        assert u(name(doc.GetElement(fl.GetTypeId()))) == u'L01.00 / 20cm', 'La losa no es L01.00 / 20cm'
        for o in DB.FilteredElementCollector(doc).OfClass(DB.Opening):
            if o.Host is not None and o.Host.Id.IntegerValue == SLAB and P.mx(o.get_BoundingBox(None).Min)[0] < P.CH_X < P.mx(o.get_BoundingBox(None).Max)[0]:
                return {'status': 'success', 'existing': o.Id.IntegerValue}
        h = .25; cx, cy, z = P.CH_X, P.CH_Y, 3.0
        pts = [DB.XYZ((cx + a_) / M, (cy + b_) / M, z / M) for a_, b_ in ((-h, -h), (h, -h), (h, h), (-h, h))]
        ca = DB.CurveArray()
        for i in range(4): ca.Append(DB.Line.CreateBound(pts[i], pts[(i + 1) % 4]))
        out = {}
        def body():
            o = doc.Create.NewOpening(fl, ca, True); out['opening'] = o.Id.IntegerValue
            pc = o.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
            if pc is not None: pc.Set(u'CH-PA · pase 0,50 x 0,50 conducto parrilla (R34e, OK usuario 30/10)')
            return out
        P.B.plain(doc, u'ADER Parrilla R34e - pase losa L01 0,50 x 0,50 (OK usuario)', body)
        o = doc.GetElement(DB.ElementId(Int64(out['opening'])))
        out['bbox'] = P.bbm(o); R1.write(os.path.join(OUT, 'par34-pase.json'), dict(out, readAt=P.L.now())); doc.Save()
        return dict(out, status='success')
    raise Exception('Unknown part')
