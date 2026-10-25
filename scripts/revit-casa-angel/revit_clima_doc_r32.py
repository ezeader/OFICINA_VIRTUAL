# -*- coding: utf-8 -*-
"""R32 Climatización etapa 1 in Casa-Angel-DOC-Climatizacion.rvt (pilot linked): CLI-P-PB / PA / PE.
Linked architecture in halftone; serpentine traced with detail lines over each pipe axis (one colour per circuit CI),
distribution DI dark grey dashed, risers with a circle; collector feeding each circuit from cli32-conn.json (connectivity,
else nearest collector = "asignado por cercanía"); label per room; collectors and thermostats with code; table per level."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
C = imp.load_source('ader_cubdoc_r30_for_cli', os.path.join(ROOT, 'revit_cub_doc_r30.py'))
B = C.B; L = C.L; S = C.S; X = C.X; R1 = C.R1; CTX = C.CTX
M = L.M; OUT = L.OUT; eid = L.eid; u = C.u; name = C.name; c2 = C.c2
PRE = 'ADER CLI R32 - '
RUBRO = u'CLIMATIZACIÓN'
FOOT = u'Climatización R32 (archivo de documentación con el modelo principal vinculado). Piso radiante: serpentines PEX Ø20 (mando + retorno) trazados sobre el eje de cada tubo del modelo; colector de cada circuito por conectividad de tubos y accesorios. Densidad completa ≥ 4 m/m². Bomba de calor: no modelada.'
LEVELS = [('PB', u'00. Planta Baja', 100), ('PA', u'01. Planta Alta', 100), ('PE', u'02. Planta Entrepiso', 50)]
PAL = [(214, 39, 40), (31, 119, 180), (44, 160, 44), (255, 127, 14), (148, 103, 189), (23, 190, 207), (227, 119, 194), (140, 86, 75),
       (188, 189, 34), (0, 90, 70), (120, 30, 120), (200, 80, 0), (60, 60, 200), (0, 140, 100)]

def data():
    plan = L.read('hvac-plan')['elements']; conn = L.read('cli32-conn')
    return plan, dict((c['code'], c) for c in conn['circuits']), conn['pipeCurves_ft']

def loc(ld, i):
    e = ld.GetElement(DB.ElementId(Int64(int(i))))
    if e is None: return None
    l = e.Location
    if hasattr(l, 'Point') and l.Point is not None: return l.Point
    b = e.get_BoundingBox(None); return (b.Min + b.Max) * .5 if b else None

def collector_for(ld, x, cc, co_pts):
    c = cc.get(x['code'], {}); r = c.get('reached') or {}
    if c.get('collector') and sorted(r.values())[-1] > (sorted(r.values())[-2] if len(r) > 1 else 0): return c['collector'], u'conectividad'
    p = loc(ld, x['roomId']) if x.get('roomId') else None
    if p is None: return (c.get('collector') or u'?'), u'sin ubicación'
    k = min(co_pts, key=lambda k: co_pts[k].DistanceTo(p)); return k, u'asignado por cercanía'

def plan_view(doc, lvname, vname, pts, scale):
    lev = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if name(l) == lvname)
    v = DB.ViewPlan.Create(doc, DB.ElementId(Int64(L.PLAN_VFT)), lev.Id); L.setup_view(doc, v); v.Name = vname; v.Scale = scale
    pad = 1.5 / M; bx = DB.BoundingBoxXYZ()
    bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, lev.Elevation - 5 / M); bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, lev.Elevation + 5 / M)
    v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False
    v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)
    vr = v.GetViewRange()
    for plane, off in [(DB.PlanViewPlane.TopClipPlane, 2.0), (DB.PlanViewPlane.CutPlane, 1.2), (DB.PlanViewPlane.BottomClipPlane, -.6), (DB.PlanViewPlane.ViewDepthPlane, -.6)]:
        vr.SetLevelId(plane, lev.Id); vr.SetOffset(plane, off / M)
    v.SetViewRange(vr)
    for cat in (DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Rooms):
        try: v.SetCategoryHidden(DB.ElementId(cat), True)
        except Exception: pass
    for li in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        ov = DB.OverrideGraphicSettings(); ov.SetHalftone(True); v.SetElementOverrides(li.Id, ov)
    return v, lev

_STY = {}
def style(doc, key, rgb, w, pat=None):
    """Line style (subcategory of Lines) per circuit: one style instead of one override per detail line."""
    if key in _STY: return _STY[key]
    lines = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines); nm_ = u'ADER CLI ' + key
    sc = lines.SubCategories.get_Item(nm_) if lines.SubCategories.Contains(nm_) else doc.Settings.Categories.NewSubcategory(lines, nm_)
    sc.LineColor = DB.Color(*rgb); sc.SetLineWeight(w, DB.GraphicsStyleType.Projection)
    if pat is not None: sc.SetLinePatternId(pat, DB.GraphicsStyleType.Projection)
    _STY[key] = sc.GetGraphicsStyle(DB.GraphicsStyleType.Projection); return _STY[key]

def seg(doc, v, c, z, sty):
    a = DB.XYZ(c[0], c[1], z); b = DB.XYZ(c[3], c[4], z)
    if a.DistanceTo(b) < .02 / M: return False
    dc = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(a, b)); dc.LineStyle = sty; return True

def text_view(doc, vname, blocks):
    v = C.drafting(doc, vname, 10)
    C.legend(doc, v, 0, 0, 0, blocks, [])
    return v

def level_sheet(doc, ld, code, lvname, scale, plan, cc, curves, co_pts):
    cis = sorted([x for x in plan if x['kind'] == 'CI' and x.get('levelCode') == code], key=lambda x: x['code'])
    dis = [x for x in plan if x['kind'] == 'DI' and x.get('levelCode') == code]
    pts = [DB.XYZ(c[0], c[1], 0) for x in cis + dis for p in x['pipeIds'] for c in [curves.get(str(p))] if c]
    pts += [p for x in plan if x['kind'] == 'CO' and x.get('level') == lvname for p in [loc(ld, x['id'])] if p is not None]
    v, lev = plan_view(doc, lvname, PRE + 'PLANTA ' + code, pts, scale); z = lev.Elevation
    dash = next((p.Id for p in DB.FilteredElementCollector(doc).OfClass(DB.LinePatternElement) if u(name(p)) == u'Trazo'), None)
    crop = C.crop_of(v); placed = []; rows = []; elements = []
    for x in dis:
        for p in x['pipeIds']:
            c = curves.get(str(p))
            if not c: continue
            if not seg(doc, v, c, z, style(doc, 'DI', (70, 70, 70), 3, dash)) and abs(c[5] - c[2]) > .3 / M:     # vertical riser
                q = DB.XYZ(c[0], c[1], z); B.circle(doc, v, q, .10 / M, (70, 70, 70))
    for k, x in enumerate(cis):
        col = PAL[k % len(PAL)]
        for p in x['pipeIds']:
            c = curves.get(str(p))
            if c: seg(doc, v, c, z, style(doc, x['code'], col, 5))
        co, how = collector_for(ld, x, cc, co_pts)
        st = u'completo' if x['density'] >= 4 else u'incompleto'
        rp = loc(ld, x['roomId']) if x.get('roomId') else None
        if rp is None or not (crop[0] < rp.X < crop[2] and crop[1] < rp.Y < crop[3]):
            cs = [curves[str(p)] for p in x['pipeIds'] if str(p) in curves]; rp = DB.XYZ(sum(c[0] for c in cs) / len(cs), sum(c[1] for c in cs) / len(cs), z)
        C.place(doc, v, DB.XYZ(rp.X, rp.Y, z), u'%s · %s\n%s ml · %s m² · %s m/m²\n%s%s · %s' % (R1.clean(x['room'] or u''), x['code'], c2(x['length_m']), c2(x['area_m2']), c2(x['density']), co,
                u' (cercanía)' if how != u'conectividad' else u'', st), placed, crop, 'tag', z)
        rows.append((x, co, how, st)); elements.append(x['roomId'])
    for x in plan:
        if x['kind'] not in ('CO', 'TE'): continue
        p = loc(ld, x['id'])
        if p is None: continue
        lvok = x.get('level') == lvname or (x['kind'] == 'TE' and x.get('room') and any(r[0]['room'] == x['room'] for r in rows))
        if not lvok: continue
        q = DB.XYZ(p.X, p.Y, z)
        if x['kind'] == 'CO':
            B.circle(doc, v, q, .18 / M, (0, 0, 0))
            n = len([r for r in rows if r[1] == x['code']])
            C.place(doc, v, q, u'%s · colector\n%d circuitos de este nivel' % (x['code'], n), placed, crop, 'tag', z)
        else:
            s = .08 / M
            for a, b in [((-s, -s), (s, -s)), ((s, -s), (s, s)), ((s, s), (-s, s)), ((-s, s), (-s, -s))]:
                B.line(doc, v, DB.XYZ(q.X + a[0], q.Y + a[1], z), DB.XYZ(q.X + b[0], q.Y + b[1], z), (0, 0, 0), 4)
            C.place(doc, v, q, x['code'], placed, crop, 'text', z)
    tab = [u'%s  %s  %s  %s ml  %s m²  %s m/m²  %s' % (x['code'], R1.clean(x['room'] or u''), co + (u'*' if how != u'conectividad' else u''), c2(x['length_m']), c2(x['area_m2']), c2(x['density']), st) for x, co, how, st in rows]
    tot_l = sum(r[0]['length_m'] for r in rows); tot_a = sum(r[0]['area_m2'] for r in rows); tot_d = sum(x['length_m'] for x in dis)
    tab += [u'', u'Total %s: %d circuitos · %s ml en locales · %s m² · distribución %s ml' % (code, len(rows), c2(tot_l), c2(tot_a), c2(tot_d)), u'* asignado por cercanía (sin camino de tubos al colector)']
    refs = [u'Color por circuito CI (trazo sobre el eje del tubo)', u'Gris discontinuo: distribución DI · círculo gris: montante (sube / baja entre niveles)', u'Círculo negro: colector CO · cuadrado: termostato TE',
            u'Arquitectura del modelo vinculado en medio tono']
    tv = text_view(doc, PRE + 'CUADRO ' + code, [(u'Circuitos del nivel ' + code, tab), (u'Referencias', refs)])
    it = X.item(v, v.CropBox, u'Piso radiante · ' + lvname, 'plan', lvname, [r[0]['code'] for r in rows], [], elements)
    tt = C.item(doc, tv, u'Cuadro de circuitos · ' + code, [], [])
    old = list(L.SCALES); L.SCALES[:] = [10, 50, 75]
    try: s = S.lay_sheet(doc, 'CLI-P-' + code, u'Piso radiante · trazado de serpentines · ' + lvname, u'Un color por circuito · colector de cada circuito · etiqueta por local (ml, m², m/m², colector, estado)',
                         [it, tt], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Climatización · ' + code)
    finally: L.SCALES[:] = old
    return dict(s, kind='general', level=lvname, sector=u'Piso radiante', circuits=[{'code': x['code'], 'collector': co, 'method': how, 'status': st, 'roomId': x['roomId']} for x, co, how, st in rows],
                totals={'length_m': round(tot_l, 2), 'area_m2': round(tot_a, 2), 'distribution_m': round(tot_d, 2)})

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CLI-00'; sheet.Name = u'Climatización · índice'
    head = u'CASA ÁNGEL · CLIMATIZACIÓN · ÍNDICE (R32)'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CLI-00', 'title': u'Índice', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'General', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None, 'Abrir Casa-Angel-DOC-Climatizacion.rvt'
    part = job['part']; path = os.path.join(OUT, 'cli32-' + part + '.json')
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in ('cli32-plans.json', 'cli32-index.json'):
            if not os.path.exists(os.path.join(OUT, fn)): continue
            rec = R1.read(os.path.join(OUT, fn))
            for sh in rec['sheets']:
                opts.FileName = 'r32-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([DB.ElementId(Int64(sh['sheetId']))]), opts)); done.append(sh['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path) and not job.get('redo'): return {'status': 'success', 'existing': True}
    if os.path.exists(path):
        rec = R1.read(path)
        def wipe():
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']] + sh.get('extraViews', []):
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id)
        B.plain(doc, 'ADER CLI R32 - borrar ' + part, wipe); os.remove(path)
    L.register_font()
    def body():
        if part == 'info': B.project_info(doc, ld); return []
        if part == 'index': return index_part(doc, job)
        if part == 'plans':
            plan, cc, curves = data()
            co_pts = dict((x['code'], loc(ld, x['id'])) for x in plan if x['kind'] == 'CO')
            return [level_sheet(doc, ld, code, lvn, sc, plan, cc, curves, co_pts) for code, lvn, sc in LEVELS]
        raise Exception('Unknown part')
    sheets = B.plain(doc, 'ADER CLI R32 - ' + part, body)
    for sh in sheets:
        for x in sh['views']: x.pop('view', None)
    R1.write(path, {'part': part, 'revision': 'R32', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [x['scale'] for x in sh['views']], sh.get('totals')) for sh in sheets],
            'byCollector': [(c['code'], c['collector'], c['method']) for sh in sheets for c in sh.get('circuits', [])]}
