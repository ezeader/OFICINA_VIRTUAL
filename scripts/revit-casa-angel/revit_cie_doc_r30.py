# -*- coding: utf-8 -*-
"""R30 Cielorrasos documentation inside Casa-Angel-DOC-Cielorrasos.rvt (pilot linked; ceilings modeled in R30).
inventory (read-only from the link) · plans (ceiling plans per level with type regions + labels) · details · index · export."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
X = imp.load_source('ader_ext_r23_for_ciedoc', os.path.join(ROOT, 'revit_ext_r23.py'))
S = X.S; L = S.L; F = X.F
CTX = imp.load_source('ader_docctx_r30_cie', os.path.join(ROOT, 'docctx_r30.py'))
OUT = L.OUT; M = L.M; eid = L.eid; u = L.u; name = L.name; R1 = L.R1; c2 = X.c2
RUBRO = u'CIELORRASOS'; PRE = 'ADER CIE R30 - '
LEVELS = [(u'00. Planta Baja', 'PB'), (u'01. Planta Alta', 'PA'), (u'02. Planta Entrepiso', 'PE')]
RH, ST = u'Placa de Yeso RH 12,5mm Knauf', u'Placa de Yeso ST 12,5mm Knauf'
FILL = {'TC-01': (25, 98, 143), 'TC-02': (196, 98, 16), 'TC-03': (150, 150, 150)}
WOOD = (u'Playroom', u'Comedor', u'Living', u'Puente', u'SM', u'Hall PE', u'Atelier', u'Hall', u'Sala de Maquinas')
TAPAS = (u'Baño', u'Toilette')
FOOT = u'Cielorrasos R30 (archivo de documentación con el modelo principal vinculado). Suspendidos de placa de yeso 12,5 sobre perfilería galvanizada: TC-01 Knauf RH en zonas húmedas, TC-02 Knauf ST en el resto; buña Z 15; tapas 60×60 en baños y toilettes. Bajo la cubierta de madera: machimbre visto (ver Cubierta). Cotas en metros.'

def mxy(p): return [p.X, p.Y]

def bottom_loops(e):
    out = []
    for g in e.get_Geometry(DB.Options()):
        if isinstance(g, DB.Solid) and g.Volume > 0:
            for f in g.Faces:
                if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
                    out.append([[mxy(c.GetEndPoint(0)) for c in cl] for cl in f.GetEdgesAsCurveLoops()])
    return out

def inventory(ld):
    old = {}
    try:
        for c in L.read('ceil-plan')['ceilings']: old[c['id']] = c['code']
    except Exception: pass
    try:
        for r in L.read('cp-plan')['rooms']:
            if r.get('code'): old.setdefault('room:%d' % r['id'], r['code'])
    except Exception: pass
    rooms = []
    for rm in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if rm.Area > 0 and isinstance(rm.Location, DB.LocationPoint):
            rooms.append(rm)
    ceils = []
    for e in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Ceilings).WhereElementIsNotElementType():
        t = ld.GetElement(e.GetTypeId()); tn = u(name(t)); lev = ld.GetElement(e.LevelId); b = e.get_BoundingBox(None)
        # a point that lies on the ceiling (largest triangle of its underside), 0,30 m below it: the room it covers
        best = (0, (b.Min + b.Max) * .5)
        for g in e.get_Geometry(DB.Options()):
            if isinstance(g, DB.Solid) and g.Volume > 0:
                for f in g.Faces:
                    if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
                        msh = f.Triangulate()
                        for k in range(msh.NumTriangles):
                            tr = msh.get_Triangle(k); p0, p1, p2 = tr.get_Vertex(0), tr.get_Vertex(1), tr.get_Vertex(2)
                            ar = (p1 - p0).CrossProduct(p2 - p0).GetLength() / 2
                            if ar > best[0]: best = (ar, (p0 + p1 + p2) / 3.0)
        c = best[1]
        rm = ld.GetRoomAtPoint(DB.XYZ(c.X, c.Y, b.Min.Z - .3 / M))
        tc = 'TC-01' if tn == RH else ('TC-02' if tn == ST else 'TC-03')
        a = e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M; p = e.get_Parameter(DB.BuiltInParameter.HOST_PERIMETER_COMPUTED)
        ceils.append({'id': eid(e), 'type': tn, 'tc': tc, 'level': u(name(lev)), 'area_m2': round(a, 3), 'perimeter_m': round(p.AsDouble() * M, 3) if p else None,
                      'height_m': round((b.Min.Z - lev.Elevation) * M, 2), 'roomId': eid(rm) if rm else None, 'loops': bottom_loops(e), 'center': [c.X, c.Y],
                      'code': old.get(eid(e)) or (old.get('room:%d' % eid(rm)) if rm else None)})
    rr = []
    for rm in rooms:
        nm = u(rm.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()); cs = [c for c in ceils if c['roomId'] == eid(rm)]
        cov = sum(c['area_m2'] for c in cs); area = rm.Area * M * M
        buna = (rm.Perimeter * M) if cov >= .95 * area else sum(c['perimeter_m'] or 0 for c in cs)
        rr.append({'id': eid(rm), 'number': u(rm.Number), 'name': nm, 'level': u(name(rm.Document.GetElement(rm.LevelId))), 'area_m2': round(area, 3), 'perimeter_m': round(rm.Perimeter * M, 3),
                   'ceilings': [c['id'] for c in cs], 'covered_m2': round(cov, 3), 'buna_ml': round(buna, 3) if cs else 0.0, 'tapa': 1 if (cs and nm.startswith(TAPAS)) else 0,
                   'wood': nm in WOOD, 'p': [rm.Location.Point.X, rm.Location.Point.Y], 'excluded': nm.startswith(u'Ascensor')})
    # codes for ceilings without one (should not happen): CE-xx-nn
    n = 0
    for c in sorted(ceils, key=lambda c: c['id']):
        if not c['code']: n += 1; c['code'] = 'CE-N-%02d' % n
    return {'ceilings': ceils, 'rooms': rr}

def region(doc, v, loops, z, rgb, ftype, solid):
    cls = List[DB.CurveLoop]()
    for lp in loops:
        cl = DB.CurveLoop(); pts = [DB.XYZ(a[0], a[1], z) for a in lp]
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if a.DistanceTo(b) > 1e-3: cl.Append(DB.Line.CreateBound(a, b))
        cls.Add(cl)
    fr = DB.FilledRegion.Create(doc, ftype.Id, v.Id, cls)
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb)
    ov.SetSurfaceForegroundPatternColor(c); ov.SetProjectionLineColor(c); ov.SetProjectionLineWeight(3)
    if solid is not None: ov.SetSurfaceForegroundPatternId(solid)
    try: ov.SetSurfaceTransparency(55)
    except Exception: pass
    v.SetElementOverrides(fr.Id, ov)

def filled_type(doc):
    return list(DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType))[0]

def solid_fill(doc):
    for fp in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
        try:
            if fp.GetFillPattern().IsSolidFill: return fp.Id
        except Exception: pass
    return None

def ceiling_plan(doc, lvname, d, code):
    lev = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if name(l) == lvname)
    rooms = [r for r in d['rooms'] if r['level'] == lvname]; cs = [c for c in d['ceilings'] if c['level'] == lvname]
    pts = [p for r in rooms for p in [r['p']]] + [q for c in cs for lp in c['loops'][:1] for l in lp for q in l]
    rl = [CTX_LD.GetElement(DB.ElementId(Int64(r['id']))) for r in rooms]
    bx = DB.BoundingBoxXYZ(); pad = 1.0 / M
    xs, ys = [], []
    for e in rl:
        b = e.get_BoundingBox(None); xs += [b.Min.X, b.Max.X]; ys += [b.Min.Y, b.Max.Y]
    bx.Min = DB.XYZ(min(xs) - pad, min(ys) - pad, lev.Elevation - 3 / M); bx.Max = DB.XYZ(max(xs) + pad, max(ys) + pad, lev.Elevation + 9 / M)
    vft = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == DB.ViewFamily.CeilingPlan)
    v = DB.ViewPlan.Create(doc, vft.Id, lev.Id); L.setup_view(doc, v); v.Name = PRE + code + ' - CIELORRASOS'
    v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False; v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)
    vr = v.GetViewRange()
    for plane, off in [(DB.PlanViewPlane.BottomClipPlane, 0.), (DB.PlanViewPlane.CutPlane, 1.8), (DB.PlanViewPlane.TopClipPlane, 2.9), (DB.PlanViewPlane.ViewDepthPlane, 2.9)]:
        vr.SetLevelId(plane, lev.Id); vr.SetOffset(plane, off / M)
    try: v.SetViewRange(vr)
    except Exception: pass
    z = v.Origin.Z; ft = filled_type(doc); sf = solid_fill(doc)
    for c in cs:
        for lp in c['loops']:
            try: region(doc, v, lp, z, FILL[c['tc']], ft, sf)
            except Exception: pass
        L.tn(doc, v.Id, DB.XYZ(c['center'][0] - .6 / M, c['center'][1], lev.Elevation), u'%s · %s\n%s m² · h %s' % (c['code'], c['tc'], c2(c['area_m2']), c2(c['height_m'])), 'tag')
    for r in rooms:
        if r['excluded']: t = u'%s %s · sin cielorraso (pasadizo)' % (r['number'], r['name'])
        elif r['wood'] and r['covered_m2'] < .9 * r['area_m2']: t = u'%s %s · machimbre visto (ver Cubierta)' % (r['number'], r['name'])
        elif not r['ceilings']: t = u'%s %s · sin cielorraso' % (r['number'], r['name'])
        else: t = u'%s %s' % (r['number'], r['name']) + (u' · tapa 60×60' if r['tapa'] else u'')
        L.tn(doc, v.Id, DB.XYZ(r['p'][0] - .6 / M, r['p'][1] - .6 / M, lev.Elevation), t, 'room')
    rh = sum(c['area_m2'] for c in cs if c['tc'] == 'TC-01'); st = sum(c['area_m2'] for c in cs if c['tc'] == 'TC-02')
    sub = u'RH %s m² · ST %s m² · %d cielorrasos · buña %s ml' % (c2(rh), c2(st), len(cs), c2(sum(r['buna_ml'] for r in rooms)))
    lines = [u'Azul: TC-01 placa Knauf RH 12,5 (zonas húmedas).', u'Naranja: TC-02 placa Knauf ST 12,5.', u'Buña Z 15 en todo el perímetro; tapas 60×60 en baños y toilettes.', u'Machimbre visto: ver Cubierta.']
    it = X.item(v, v.CropBox, u'Planta de cielorrasos · ' + lvname, 'plan', lvname, [c['code'] for c in cs], [], [c['id'] for c in cs] + [r['id'] for r in rooms], lines)
    s = S.lay_sheet(doc, 'CIE-' + code + '-01', u'Planta de cielorrasos · ' + lvname, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Cielorrasos · ' + code)
    return dict(s, kind='general', level=lvname, sector=lvname)

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CIE-00'; sheet.Name = u'Cielorrasos · índice'
    head = u'CASA ÁNGEL · CIELORRASOS · ÍNDICE Y CÓMPUTO (R30)'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CIE-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Cielorrasos', 'sector': u'General'}]

def details(doc):
    R28 = imp.load_source('ader_cie_r28_for_doc', os.path.join(ROOT, 'revit_cie_r28.py'))
    R28.L = L; R28.S = S; R28.FOOT = FOOT
    s = R28.details_sheet(doc)
    return s

def plain(doc, label, body):
    tx = DB.Transaction(doc, label); tx.Start()
    try: r = body(); tx.Commit(); return r
    except Exception: tx.RollBack(); raise

CTX_LD = None

def run(doc, uidoc, job):
    global CTX_LD
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, F, X, None]); CTX_LD = ld
    assert ld is not None, 'Abrir Casa-Angel-DOC-Cielorrasos.rvt'
    part = job['part']; path = os.path.join(OUT, 'cie30-' + part + '.json')
    if part == 'inventory':
        d = inventory(ld); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'cie30-plan.json'), d)
        return {'status': 'success', 'ceilings': [(c['code'], c['tc'], c['area_m2'], c['height_m']) for c in d['ceilings']], 'rooms': len(d['rooms'])}
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in ('cie30-plans.json', 'cie30-details.json', 'cie30-index.json'):
            if not os.path.exists(os.path.join(OUT, fn)): continue
            rec = R1.read(os.path.join(OUT, fn))
            for sh in rec['sheets']:
                opts.FileName = 'r30-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([doc.GetElement(DB.ElementId(Int64(sh['sheetId']))).Id]), opts)); done.append(sh['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if job.get('resetPart'):
        rec = R1.read(path)
        def body():
            n = 0
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [v['id'] for v in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id); n += 1
            return n
        n = plain(doc, 'ADER CIE R30 - reset ' + part, body); os.remove(path); doc.Save(); return {'status': 'success', 'deleted': n}
    if os.path.exists(path): return {'status': 'success', 'existing': True}
    L.register_font(); d = L.read('cie30-plan')
    def body():
        if part == 'info': _info(doc, ld); return []
        if part == 'plans': return [ceiling_plan(doc, ln, d, code) for ln, code in LEVELS]
        if part == 'details': return details(doc)
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets = plain(doc, 'ADER CIE R30 - ' + part, body)
    for sh in sheets:
        for v in sh['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [v['scale'] for v in sh['views']]) for sh in sheets]}

def _info(doc, ld):
    src = ld.ProjectInformation; dst = doc.ProjectInformation
    for bip in (DB.BuiltInParameter.PROJECT_NAME, DB.BuiltInParameter.CLIENT_NAME, DB.BuiltInParameter.PROJECT_NUMBER, DB.BuiltInParameter.PROJECT_ISSUE_DATE,
                DB.BuiltInParameter.PROJECT_STATUS, DB.BuiltInParameter.PROJECT_AUTHOR, DB.BuiltInParameter.PROJECT_ADDRESS):
        a, b = src.get_Parameter(bip), dst.get_Parameter(bip)
        if a is not None and b is not None and not b.IsReadOnly and a.AsString(): b.Set(a.AsString())
    return True
