# -*- coding: utf-8 -*-
"""Switch the active Revit document (user-approved): open + activate a file inside outputs\\casa-angel (the pilot or
documentacion\\Casa-Angel-DOC-*.rvt), then close the previous one saving it (Close(True)) and reload unloaded links."""
import os
from Autodesk.Revit import DB

ROOT = os.path.dirname(__file__)
BASE = os.path.normcase(os.path.abspath(os.path.join(ROOT, '..', '..', 'outputs', 'casa-angel')))
PILOT = os.path.join(BASE, 'casa-angel-piloto-documentacion.rvt')
DOCDIR = os.path.join(BASE, 'documentacion')

def allowed(p):
    p = os.path.normcase(os.path.abspath(p))
    if p == PILOT: return True
    return os.path.dirname(p) == DOCDIR and os.path.basename(p).startswith('casa-angel-doc-') and p.endswith('.rvt')

def docs(app):
    out = []
    for d in list(app.Documents):
        try:
            if d.IsValidObject and not d.IsLinked: out.append(d)
        except Exception: pass   # stale handle of a document closed earlier
    return out

def run(doc, uidoc, job):
    target = job['target']
    if not os.path.isabs(target): target = os.path.join(BASE, target)
    target = os.path.abspath(target)
    assert allowed(target), 'Ruta fuera de outputs\\casa-angel: ' + target
    assert os.path.exists(target), 'No existe: ' + target
    uiapp = uidoc.Application; app = uiapp.Application
    if os.path.normcase(doc.PathName) == os.path.normcase(target): return {'status': 'success', 'active': target, 'note': 'ya activo'}
    unloaded = []   # a file loaded as a link in an open document cannot be opened as host: unload that link first
    for d in docs(app):
        for lt in DB.FilteredElementCollector(d).OfClass(DB.RevitLinkType):
            ext = lt.GetExternalFileReference()
            p = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(ext.GetAbsolutePath()) if ext else ''
            if os.path.normcase(os.path.abspath(p)) == os.path.normcase(target) and DB.RevitLinkType.IsLoaded(d, lt.Id):
                lt.Unload(None); unloaded.append(DB.Element.Name.GetValue(lt))
    ui = uiapp.OpenAndActivateDocument(target)
    assert ui is not None, 'Revit no abrió ' + target + ' (¿diálogo abierto?)'
    new = ui.Document
    closed = []
    # close every other casa-angel document (saving), so links to them can load; other projects are left alone
    for d in docs(app):
        if d.Equals(new) or not allowed(d.PathName): continue
        n = os.path.basename(d.PathName); d.Close(True); closed.append(n)
    reloaded = []
    for lt in DB.FilteredElementCollector(new).OfClass(DB.RevitLinkType):
        try:
            if not DB.RevitLinkType.IsLoaded(new, lt.Id):
                lt.Load(); reloaded.append(DB.Element.Name.GetValue(lt))
        except Exception as ex: reloaded.append('ERROR ' + str(ex))
    return {'status': 'success', 'active': new.PathName, 'closed': closed, 'linksReloaded': reloaded}
