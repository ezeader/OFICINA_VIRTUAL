# -*- coding: utf-8 -*-
"""R30: per-rubro documentation file Casa-Angel-DOC-<Rubro>.rvt (outputs\\casa-angel\\documentacion\\).
create (from the pilot session): metric ES template + ADER standards copied from the pilot (title block, text, dimension
and viewport types) + levels matching the pilot. The pilot is LINKED later (part 'link', run with the DOC file open
and the pilot closed: Revit cannot link a model that is open in the same session)."""
import os, imp
from Autodesk.Revit import DB
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_docfile', os.path.join(ROOT, 'revit_openings_r4.py'))
u = L.u; name = L.name
TEMPLATE = r'C:\ProgramData\Autodesk\RVT 2025\Templates\Default_M_ESP.rte'
PILOT = os.path.normpath(os.path.join(ROOT, '..', '..', 'outputs', 'casa-angel', 'Casa-Angel-piloto-documentacion.rvt'))
TYPE_NAMES = [n for n, _, _ in L.TEXT_TYPES.values()] + ['ADER ABR - texto', 'ADER ABR R4 - Cotas', 'ADER ABR R2 - Cotas', 'ADER ABR R4 - Radio', 'ADER ABR - viewport']

def doc_path(doc, rubro):
    return os.path.join(os.path.dirname(doc.PathName), 'documentacion', 'Casa-Angel-DOC-%s.rvt' % rubro)

def create(doc, rubro):
    app = doc.Application; path = doc_path(doc, rubro)
    if not os.path.isdir(os.path.dirname(path)): os.makedirs(os.path.dirname(path))
    if os.path.exists(path): return {'status': 'success', 'existing': path, 'size': os.path.getsize(path)}
    nd = app.NewProjectDocument(TEMPLATE); info = {}
    try:
        ids = List[DB.ElementId]()
        ids.Add(DB.ElementId(L.TITLEBLOCK))
        for t in DB.FilteredElementCollector(doc).WhereElementIsElementType():
            if u(name(t)) in TYPE_NAMES: ids.Add(t.Id)
        tx = DB.Transaction(nd, 'ADER DOC - estándares y niveles'); tx.Start()
        opt = DB.CopyPasteOptions(); opt.SetDuplicateTypeNamesHandler(UseDest())
        copied = DB.ElementTransformUtils.CopyElements(doc, ids, nd, DB.Transform.Identity, opt)
        info['copied'] = copied.Count
        # levels = pilot levels (same names and elevations); template levels renamed/reused, extra ones removed
        pl = sorted([(l.Elevation, u(name(l))) for l in DB.FilteredElementCollector(doc).OfClass(DB.Level)])
        tl = sorted(list(DB.FilteredElementCollector(nd).OfClass(DB.Level)), key=lambda l: l.Elevation)
        made = []
        for i, (z, n) in enumerate(pl):
            lv = tl[i] if i < len(tl) else DB.Level.Create(nd, z)
            lv.Elevation = z; lv.Name = n + (u'' if True else u''); made.append(n)
        for extra in tl[len(pl):]: nd.Delete(extra.Id)
        info['levels'] = made
        try: nd.ProjectInformation.Name = u'Casa Ángel · Documentación ' + rubro
        except Exception: pass
        tx.Commit()
        so = DB.SaveAsOptions(); so.OverwriteExistingFile = False; nd.SaveAs(path, so)
    finally:
        nd.Close(False)
    info.update(status='success', path=path, size=os.path.getsize(path))
    return info

class UseDest(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args): return DB.DuplicateTypeAction.UseDestinationTypes

def link(doc):
    """Run with the DOC file active and the pilot closed: link the pilot origin-to-origin."""
    for t in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkType):
        return {'status': 'success', 'existing': u(name(t)), 'loaded': DB.RevitLinkType.IsLoaded(doc, t.Id)}
    tx = DB.Transaction(doc, 'ADER DOC - vincular modelo principal'); tx.Start()
    res = DB.RevitLinkType.Create(doc, DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(PILOT), DB.RevitLinkOptions(False))
    inst = DB.RevitLinkInstance.Create(doc, res.ElementId, DB.ImportPlacement.Origin)
    tx.Commit(); doc.Save()
    return {'status': 'success', 'linkType': res.ElementId.IntegerValue, 'load': str(res.LoadResult), 'instance': inst.Id.IntegerValue}

def run(doc, uidoc, job):
    if job['part'] == 'create':
        L.assert_pilot(doc); return create(doc, job['rubro'])
    if job['part'] == 'link':
        assert os.path.basename(doc.PathName).startswith('Casa-Angel-DOC-'), 'Abrir el archivo DOC'
        return link(doc)
    raise Exception('Unknown part')
