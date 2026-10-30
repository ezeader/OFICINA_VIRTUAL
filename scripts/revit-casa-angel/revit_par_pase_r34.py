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
    raise Exception('Unknown part')
