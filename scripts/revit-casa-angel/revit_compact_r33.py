# -*- coding: utf-8 -*-
"""R33: save the pilot compacted (SaveOptions.Compact) after the cleanup; no element changes."""
import os, imp
from Autodesk.Revit import DB
ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_compact', os.path.join(ROOT, 'revit_openings_r4.py'))

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    assert os.path.basename(doc.PathName).lower() == L.PILOT, 'Solo en el modelo principal'
    o = DB.SaveOptions(); o.Compact = True; doc.Save(o)
    return {'status': 'success', 'bytes': os.path.getsize(doc.PathName)}
