# -*- coding: utf-8 -*-
"""R31 Estructura in Casa-Angel-DOC-Estructura.rvt (pilot linked): PB entirely on the platea.
EST-FU-01: platea PL-01 + ampliación PL-02 (2488978, R31) with contour, perimeter, levels and the typical section;
EST-F-LO-PB-01: LO-PB-01 documented as a floor package over the platea (not a concrete slab)."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64

ROOT = os.path.dirname(__file__)
C = imp.load_source('ader_cubdoc_r30_for_est', os.path.join(ROOT, 'revit_cub_doc_r30.py'))
B = C.B; L = C.L; S = C.S; X = C.X; R1 = C.R1; CTX = C.CTX
M = L.M; OUT = L.OUT; eid = L.eid; u = C.u; name = C.name; c2 = C.c2
PRE = 'ADER EST R31 - '
RUBRO = u'ESTRUCTURA'
FOOT = u'Estructura R31 (archivo de documentación con el modelo principal vinculado). Toda la PB apoya sobre platea H°A° 15 cm (PL-01 + ampliación PL-02 R31) sobre film y tosca compactada; LO-PB-01 se documenta como paquete de piso. Armadura por cuantía de referencia hasta el cálculo. Cotas en metros.'
IDS = {'PL-01': 2287528, 'PL-02': 2488978, 'LO-PB-01': 714161}
COL = {'PL-01': (25, 98, 200), 'PL-02': (220, 120, 0), 'LO-PB-01': (40, 140, 60)}

def outline(ld, i):
    e = ld.GetElement(DB.ElementId(Int64(i))); sk = ld.GetElement(e.SketchId)
    return e, [[c for c in arr] for arr in sk.Profile]

def plan(doc, lvname, vname, pts, pad=2.0):
    lev = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if name(l) == lvname)
    v = DB.ViewPlan.Create(doc, DB.ElementId(Int64(L.PLAN_VFT)), lev.Id); L.setup_view(doc, v); v.Name = vname
    bx = DB.BoundingBoxXYZ(); p = pad / M
    bx.Min = DB.XYZ(min(q.X for q in pts) - p, min(q.Y for q in pts) - p, lev.Elevation - 5 / M); bx.Max = DB.XYZ(max(q.X for q in pts) + p, max(q.Y for q in pts) + p, lev.Elevation + 5 / M)
    v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False
    v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)
    vr = v.GetViewRange()
    for plane, off in [(DB.PlanViewPlane.TopClipPlane, 2.0), (DB.PlanViewPlane.CutPlane, 1.2), (DB.PlanViewPlane.BottomClipPlane, -1.0), (DB.PlanViewPlane.ViewDepthPlane, -1.0)]:
        vr.SetLevelId(plane, lev.Id); vr.SetOffset(plane, off / M)
    v.SetViewRange(vr)
    for cat in (DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Rooms):
        try: v.SetCategoryHidden(DB.ElementId(cat), True)
        except Exception: pass
    return v, lev

def draw_outline(doc, v, loops, z, rgb, w):
    for arr in loops:
        for c in arr:
            a, b = c.GetEndPoint(0), c.GetEndPoint(1)
            B.line(doc, v, DB.XYZ(a.X, a.Y, z), DB.XYZ(b.X, b.Y, z), rgb, w)

def pts_of(loops): return [c.GetEndPoint(0) for arr in loops for c in arr]

def ext_dims(doc, v, pts, z, label):
    f = L.AxisFrame(v, DB.XYZ(0, 0, z), DB.XYZ.BasisX, DB.XYZ.BasisY)
    xs = [min(p.X for p in pts), max(p.X for p in pts)]; ys = [min(p.Y for p in pts), max(p.Y for p in pts)]
    return [L.tick_dim(doc, f, label + u' extensión X', xs, True, ys[0] - 1.0 / M), L.tick_dim(doc, f, label + u' extensión Y', ys, False, xs[1] + 1.0 / M)]

def area_vol(e):
    a = e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M; v_ = e.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * M ** 3
    p = e.get_Parameter(DB.BuiltInParameter.HOST_PERIMETER_COMPUTED); return a, v_, (p.AsDouble() * M if p else 0)

def section_detail(doc, sfx, blocks=()):
    """Typical section 1:10: tosca + film + platea H°A° 15 + floor package (LO-PB-01) up to ±0,00."""
    v = C.drafting(doc, PRE + 'CORTE TIPO PLATEA ' + sfx, 10); W = 1.2; dims = []
    C.rect(doc, v, 0, -.55, W, -.45, 'eps', 2)                 # tosca compactada (hatch)
    C.dl(doc, v, (0, -.45), (W, -.45), 5)                        # film
    C.rect(doc, v, 0, -.45, W, -.30, 'hormigon', 5)               # platea 15 (fondo -0,45 . sup -0,30 ver nota)
    C.dl(doc, v, (.03, -.42), (W - .03, -.42), 2, u'Trazo'); C.dl(doc, v, (.03, -.33), (W - .03, -.33), 2, u'Trazo')
    C.rect(doc, v, 0, -.30, W, -.20, 'mamposteria', 2)            # relleno / contrapiso hasta NSP platea
    C.rect(doc, v, 0, -.20, W, -.09, 'solido', 1)                 # carpeta / aislación hidrófuga + contrapiso (LO-PB-01)
    C.rect(doc, v, 0, -.09, W, 0, None, 3)                        # piso terminado (rubro Pisos)
    pts = [((1.0, -.05), u'Piso terminado ±0,00 (ver rubro Pisos)'), ((1.0, -.15), u'LO-PB-01: aislación hidrófuga + carpeta (paquete de piso, no losa)'),
           ((1.0, -.25), u'Relleno / contrapiso de nivelación (según modelo)'), ((1.0, -.38), u'Platea H°A° 15 cm · malla sup. e inf. por cuantía de referencia'),
           ((1.0, -.45), u'Film de polietileno 200 µm'), ((1.0, -.50), u'Tosca compactada (sub-base)')]
    C.labels_column(doc, v, pts, W + .15, .02, .085)
    if blocks: C.legend(doc, v, 0, -.75 / M, 0, list(blocks), [])
    f = L.AxisFrame(v, DB.XYZ.Zero, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims.append(L.tick_dim(doc, f, u'Niveles', [-.45 / M, -.30 / M, -.20 / M, -.09 / M, 0], False, -.08 / M, tick=.02 / M))
    dims.append(L.tick_dim(doc, f, u'Platea + paquete', [-.45 / M, 0], False, -.20 / M, tick=.02 / M))
    L.tn(doc, v.Id, C.V((0, -.65)), u'Niveles del modelo: platea −0,45 / −0,20 (tipo «Platea PB 15CM»: tosca + film + H°) · LO-PB-01 −0,20 / −0,09 (R31) · NPT ±0,00', 'text')
    return C.item(doc, v, u'Corte tipo · platea y paquete de piso', [u'PL-01', u'PL-02', u'LO-PB-01'], dims)

def lay(doc, number, title, sub, items, sheet_name, scales=None, plan_region=False):
    old = list(L.SCALES)
    if scales: L.SCALES[:] = list(scales)
    try: s = S.lay_sheet(doc, number, title, sub, items, FOOT, plan_region=plan_region, rubro=RUBRO, sheet_name=sheet_name)
    finally: L.SCALES[:] = old
    return s

def sheet_fu(doc, ld):
    data = {}; allpts = []
    for k, i in IDS.items():
        e, lo = outline(ld, i); data[k] = (e, lo); allpts += pts_of(lo)
    pl = pts_of(data['PL-01'][1]) + pts_of(data['PL-02'][1])
    v, lev = plan(doc, u'00. Planta Baja', PRE + 'PLATEA', pl); z = lev.Elevation
    crop = C.crop_of(v); placed = []
    draw_outline(doc, v, data['PL-01'][1], z, COL['PL-01'], 9); draw_outline(doc, v, data['PL-02'][1], z, COL['PL-02'], 9)
    rows = []
    for k in ('PL-01', 'PL-02'):
        e = data[k][0]; a, vol, per = area_vol(e); ps = pts_of(data[k][1])
        cx = sum(p.X for p in ps) / len(ps); cy = sum(p.Y for p in ps) / len(ps)
        C.place(doc, v, DB.XYZ(cx, cy, z), u'%s\n%s m² · %s m³' % (k, c2(a), c2(vol)), placed, crop, 'tag', z)
        rows.append((k, a, vol, per))
    dims = ext_dims(doc, v, pl, z, u'Platea')
    A = sum(r[1] for r in rows); Vt = sum(r[2] for r in rows)
    lines = [u'Azul: PL-01 platea existente', u'Naranja: PL-02 ampliación R31 (bajo LO-PB-01)', u'Tipo «Platea PB 15CM»: tosca + film + H°A° 15', u'Nivel superior −0,20 · fondo −0,45']
    tab = [u'%s · %s m² · %s m³ · perímetro %s m' % (k, c2(a), c2(vol), c2(per)) for k, a, vol, per in rows] + [u'Total platea · %s m² · %s m³' % (c2(A), c2(Vt)),
           u'(perímetro exterior de la unión: ver EST-00)']
    it = X.item(v, v.CropBox, u'Platea PB · contorno', 'plan', u'00. Planta Baja', ['PL-01', 'PL-02'], dims, [IDS['PL-01'], IDS['PL-02']])
    s = lay(doc, 'EST-FU-01', u'Platea de fundación PB', u'Toda la PB sobre platea: PL-01 + ampliación PL-02 (R31) · H°A° 15 cm · niveles y corte tipo', [it, section_detail(doc, 'FU-01', [(u'Referencias', lines), (u'Platea', tab)])], u'Estructura · FU-01', plan_region=True)
    return dict(s, kind='general', level=u'00. Planta Baja', sector=u'Fundación', totals={'area_m2': round(A, 3), 'volume_m3': round(Vt, 3)})

def sheet_lo(doc, ld):
    e, lo = outline(ld, IDS['LO-PB-01']); _, pl2 = outline(ld, IDS['PL-02']); ps = pts_of(lo)
    v, lev = plan(doc, u'00. Planta Baja', PRE + 'LO-PB-01 PAQUETE', ps, 1.5); z = lev.Elevation
    crop = C.crop_of(v); placed = []
    draw_outline(doc, v, pl2, z, COL['PL-02'], 5); draw_outline(doc, v, lo, z, COL['LO-PB-01'], 9)
    a, vol, per = area_vol(e)
    cx = sum(p.X for p in ps) / len(ps); cy = sum(p.Y for p in ps) / len(ps)
    C.place(doc, v, DB.XYZ(cx, cy, z), u'LO-PB-01 · paquete de piso\n%s m² · sobre platea PL-02' % c2(a), placed, crop, 'tag', z)
    dims = ext_dims(doc, v, ps, z, u'LO-PB-01')
    lines = [u'Verde: LO-PB-01 (paquete de piso)', u'Naranja: platea PL-02 debajo (misma huella)', u'Área %s m² · perímetro %s m' % (c2(a), c2(per)),
             u'Tipo R31: «ADER Paquete de piso sobre platea 11cm»', u'membrana hidrófuga + carpeta 11 cm, no estructural', u'−0,20 / −0,09: apoya sobre la platea, sin superposición', u'Antes: «Insitu Concrete 225mm» dentro de la platea', u'(cambio aprobado por el usuario, R31)']
    it = X.item(v, v.CropBox, u'LO-PB-01 · planta', 'plan', u'00. Planta Baja', ['LO-PB-01'], dims, [IDS['LO-PB-01']])
    s = lay(doc, 'EST-F-LO-PB-01', u'Ficha LO-PB-01 · paquete de piso sobre platea', u'LO-PB-01 no es losa de hormigón: aislación hidrófuga + carpeta sobre la platea PL-02 · ver EST-FU-01', [it, section_detail(doc, 'LO-PB-01', [(u'LO-PB-01', lines)])], u'Estructura · LO-PB-01', plan_region=True)
    return dict(s, kind='element', element=u'LO-PB-01', elementId=str(IDS['LO-PB-01']), elementKind='LO', level=u'00. Planta Baja', sector=u'Sector: 00. Planta Baja')

def sheet_pl2(doc, ld):
    e, lo = outline(ld, IDS['PL-02']); ps = pts_of(lo)
    v, lev = plan(doc, u'00. Planta Baja', PRE + 'PL-02 PLATEA', ps, 1.5); z = lev.Elevation
    crop = C.crop_of(v); placed = []
    draw_outline(doc, v, lo, z, COL['PL-02'], 9)
    a, vol, per = area_vol(e); hc = a * .15
    cx = sum(p.X for p in ps) / len(ps); cy = sum(p.Y for p in ps) / len(ps)
    C.place(doc, v, DB.XYZ(cx, cy, z), u'PL-02 · platea H°A° e 15\n%s m² · H° %s m³' % (c2(a), c2(hc)), placed, crop, 'tag', z)
    dims = ext_dims(doc, v, ps, z, u'PL-02')
    lines = [u'Naranja: PL-02 ampliación de platea (R31)', u'Tipo «Platea PB 15CM»: tosca + film + H°A° 15', u'Nivel superior −0,20 · fondo −0,45',
             u'Área %s m² · perímetro %s m' % (c2(a), c2(per)), u'Hormigón: %s m² × 0,15 = %s m³' % (c2(a), c2(hc)), u'Volumen del tipo (0,25 total): %s m³' % c2(vol),
             u'Encima: LO-PB-01 paquete de piso 11 cm (sin H°)', u'Armadura: malla sup. e inf. por cuantía de referencia']
    it = X.item(v, v.CropBox, u'PL-02 · planta', 'plan', u'00. Planta Baja', ['PL-02'], dims, [IDS['PL-02']])
    s = lay(doc, 'EST-F-PL-02', u'Ficha PL-02 · ampliación de platea', u'PL-02: platea H°A° 15 cm bajo LO-PB-01 · %s m² · H° %s m³ · ver EST-FU-01' % (c2(a), c2(hc)), [it, section_detail(doc, 'PL-02', [(u'PL-02', lines)])], u'Estructura · PL-02', plan_region=True)
    return dict(s, kind='element', element=u'PL-02', elementId=str(IDS['PL-02']), elementKind='PL', level=u'00. Planta Baja', sector=u'Sector: 00. Planta Baja')

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None, 'Abrir Casa-Angel-DOC-Estructura.rvt'
    part = job['part']; path = os.path.join(OUT, 'est31-' + part + '.json')
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        rec = R1.read(os.path.join(OUT, 'est31-sheets.json')); done = []
        for sh in rec['sheets']:
            opts.FileName = 'r31-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([DB.ElementId(Int64(sh['sheetId']))]), opts)); done.append(sh['number'])
        R1.write(os.path.join(OUT, 'est31-sheets.json'), rec); return {'status': 'success', 'exported': done}
    if os.path.exists(path) and not job.get('redo'): return {'status': 'success', 'existing': True}
    if os.path.exists(path):
        rec = R1.read(path)
        def wipe():
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id)
        B.plain(doc, 'ADER EST R31 - borrar ' + part, wipe); os.remove(path)
    L.register_font()
    def body():
        if part == 'info': B.project_info(doc, ld); return []
        if part == 'sheets': return [sheet_fu(doc, ld), sheet_lo(doc, ld), sheet_pl2(doc, ld)]
    sheets = B.plain(doc, 'ADER EST R31 - ' + part, body)
    for sh in sheets:
        for x in sh['views']: x.pop('view', None)
    R1.write(path, {'part': part, 'revision': 'R31', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [x['scale'] for x in sh['views']], sh.get('totals')) for sh in sheets]}

from System.Collections.Generic import List
