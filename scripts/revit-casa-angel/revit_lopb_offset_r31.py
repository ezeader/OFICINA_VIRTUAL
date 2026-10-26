# -*- coding: utf-8 -*-
"""R31 (user-approved: "sí, subilo"): LO-PB-01 (714161) offset -0,30 -> -0,09 so the 11 cm package sits on the platea top (-0,20).
Only that parameter; one small transaction; then save and record faces of LO-PB-01 and PL-01/PL-02."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_lopboff', os.path.join(ROOT, 'revit_openings_r4.py'))
K = imp.load_source('ader_lopbchk_r31_for_off', os.path.join(ROOT, 'revit_lopb_check_r31.py'))
M = L.M; R1 = L.R1; OUT = L.OUT

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    lo = doc.GetElement(DB.ElementId(Int64(714161))); p = lo.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
    before = round(p.AsDouble() * M, 3)
    tx = DB.Transaction(doc, 'ADER EST R31 - LO-PB-01 desfase -0,09 sobre platea (OK usuario)'); tx.Start()
    try: p.Set(-.09 / M); tx.Commit()
    except Exception:
        tx.RollBack(); raise
    doc.Save()
    rec = dict(K.run(doc, uidoc, job), offsetBefore_m=before)
    R1.write(os.path.join(OUT, 'est31-lopb-offset.json'), rec)
    return rec
