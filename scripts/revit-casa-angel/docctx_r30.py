# -*- coding: utf-8 -*-
"""R30 DOC-file context: lets the documentation helpers (revit_openings_r4 / structure_r11 / fichas_r12 / ext_r23 …) run
inside Casa-Angel-DOC-<Rubro>.rvt, where the pilot is a Revit link (origin to origin, identity transform).
- el(doc, id): host views/annotation by id; pilot level ids → host level with the same name; anything else → link element.
- view family types and title block resolved by name in the host; colorize/paint of linked elements is skipped
  (Revit cannot override single linked elements); rooms are read from the link."""
import os
from Autodesk.Revit import DB
from System import Int64

def nm(e):
    try: return DB.Element.Name.GetValue(e)
    except Exception: return e.Name

def is_doc(doc):
    return os.path.basename(doc.PathName).startswith('Casa-Angel-DOC-')

def link_doc(doc):
    for li in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        ld = li.GetLinkDocument()
        if ld is not None: return ld
    raise Exception('El modelo principal no está vinculado o no está cargado')

def _vft(doc, fam):
    return next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == fam).Id.IntegerValue

def activate(doc, L, mods):
    """Patch the helper modules for this DOC document. Returns the link document."""
    if not is_doc(doc): return None
    ld = link_doc(doc)
    host_levels = dict((nm(l), l) for l in DB.FilteredElementCollector(doc).OfClass(DB.Level))
    lmap = {}
    for l in DB.FilteredElementCollector(ld).OfClass(DB.Level):
        if nm(l) in host_levels: lmap[l.Id.IntegerValue] = host_levels[nm(l)]
    tb_name = nm(ld.GetElement(DB.ElementId(Int64(4428)))) if ld.GetElement(DB.ElementId(Int64(4428))) is not None else None
    tb = next((t for t in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType() if nm(t) == tb_name), None) \
        or next(t for t in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType())
    L.PLAN_VFT = _vft(doc, DB.ViewFamily.FloorPlan); L.SECTION_VFT = _vft(doc, DB.ViewFamily.Section)
    L.VIEW3D_VFT = _vft(doc, DB.ViewFamily.ThreeDimensional); L.TITLEBLOCK = tb.Id.IntegerValue
    host_types = (DB.View, DB.Viewport, DB.TextNote, DB.Dimension, DB.CurveElement, DB.FilledRegion, DB.ElementType, DB.Level)

    def el(d, i):
        i = int(i)
        if i in lmap: return lmap[i]
        e = d.GetElement(DB.ElementId(Int64(i)))
        if e is not None and isinstance(e, host_types): return e
        le = ld.GetElement(DB.ElementId(Int64(i)))
        return le if le is not None else e

    def linked(e): return e is not None and e.Document is not None and e.Document.Equals(ld)
    for m in mods:
        if m is None: continue
        if hasattr(m, 'el'): m.el = el
        if hasattr(m, 'colorize'):
            orig = m.colorize
            m.colorize = (lambda o: (lambda d, v, e, rgb: None if linked(e) else o(d, v, e, rgb)))(orig)
        if hasattr(m, 'paint'):
            origp = m.paint
            m.paint = (lambda o: (lambda d, v, e, rgb, fill: None if linked(e) else o(d, v, e, rgb, fill)))(origp)
    L.LINK_DOC = ld
    return ld
