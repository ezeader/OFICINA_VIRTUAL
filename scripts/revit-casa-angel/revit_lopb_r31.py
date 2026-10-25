# -*- coding: utf-8 -*-
"""R31 (user-approved geometry change): LO-PB-01 (714161) from 'Insitu Concrete 225mm' to a floor package without concrete
over the platea: new type 'ADER Paquete de piso sobre platea 11cm' = membrana hidrófuga + carpeta 11 cm (no H°).
The top stays at -0,09 (floors keep their top), so the bottom lands on the platea top (-0,20): no overlap, no double concrete."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_lopb', os.path.join(ROOT, 'revit_openings_r4.py'))
M = L.M; eid = L.eid; R1 = L.R1; OUT = L.OUT
TYPE = u'ADER Paquete de piso sobre platea 11cm'

def mat(doc, names):
    for n in names:
        m = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.Material) if x.Name == n), None)
        if m is not None: return m.Id
    return DB.ElementId.InvalidElementId

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    lo = doc.GetElement(DB.ElementId(Int64(714161))); old = doc.GetElement(lo.GetTypeId())
    b0 = lo.get_BoundingBox(None)
    tx = DB.Transaction(doc, 'ADER EST R31 - LO-PB-01 paquete de piso sin hormigon (OK usuario)'); tx.Start()
    try:
        t = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.FloorType) if DB.Element.Name.GetValue(x) == TYPE), None)
        if t is None:
            t = old.Duplicate(TYPE)
            layers = List[DB.CompoundStructureLayer]()
            layers.Add(DB.CompoundStructureLayer(0.0, DB.MaterialFunctionAssignment.Membrane, mat(doc, ['Damp-proofing', 'Film de Polietileno'])))
            layers.Add(DB.CompoundStructureLayer(.11 / M, DB.MaterialFunctionAssignment.Structure, mat(doc, ['Concrete, Sand/Cement Screed'])))
            cs = old.GetCompoundStructure(); cs.SetLayers(layers); cs.StructuralMaterialIndex = 1
            t.SetCompoundStructure(cs)
        lo.FloorType = t
        p = lo.get_Parameter(DB.BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL)
        if p is not None and not p.IsReadOnly: p.Set(0)
        tx.Commit()
    except Exception:
        tx.RollBack(); raise
    doc.Save()
    b1 = lo.get_BoundingBox(None)
    pl = [doc.GetElement(DB.ElementId(Int64(i))).get_BoundingBox(None) for i in (2287528, 2488978)]
    a = lo.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M; v = lo.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * M ** 3
    mats = sorted(set(doc.GetElement(i).Name for i in lo.GetMaterialIds(False)))
    rec = {'readAt': L.now(), 'id': 714161, 'oldType': DB.Element.Name.GetValue(old), 'newType': TYPE, 'area_m2': round(a, 3), 'volume_m3': round(v, 3), 'materials': mats,
           'before_z_m': [round(b0.Min.Z * M, 3), round(b0.Max.Z * M, 3)], 'after_z_m': [round(b1.Min.Z * M, 3), round(b1.Max.Z * M, 3)],
           'plateaTop_m': [round(b.Max.Z * M, 3) for b in pl]}
    R1.write(os.path.join(OUT, 'est31-lopb.json'), rec)
    return dict(rec, status='success')
