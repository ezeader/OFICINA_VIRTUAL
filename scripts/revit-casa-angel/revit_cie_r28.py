# -*- coding: utf-8 -*-
"""R28: Cielorrasos PROPUESTA a confirmar (documentation only — no geometry, types or Mark changed).
TC-01 suspendido placa RH 12,5 (zonas húmedas) · TC-02 suspendido placa ST 12,5 (resto) · TC-03 se disuelve en la documentación.
CP-<nivel>-nn cielorraso propuesto por local (área faltante = local − cielorrasos existentes). Buña Z 15 mm perimetral; tapas 60×60.
Parts: probe (read-only), plans, details, index, export, reset/resetPart."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
C = imp.load_source('ader_ceil_r21_for_r28', os.path.join(ROOT, 'revit_ceil_r21.py'))
S = C.S; L = S.L; P = C.P; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; R1 = L.R1
RUBRO = u'CIELORRASOS'
PRE = 'ADER CIE R28 - '
LEVELS = C.LEVELS
WET = (u'Baño', u'Toilette', u'Cocina', u'Lavadero')
FOOT = u'PROPUESTA A CONFIRMAR · Cielorrasos suspendidos de placa de yeso 12,5 mm sobre perfilería galvanizada: TC-01 placa RH en zonas húmedas (baños, toilettes, cocina, lavadero), TC-02 placa ST en el resto. Buña perimetral Z 15 mm; tapa de inspección 60×60 en baños, toilettes y sala de máquinas. Rayado: cielorraso propuesto (CP); sin rayado: existente en el modelo. El modelo no se modificó.'

def c2(x): return (u'%.2f' % (0.0 if abs(x) < .005 else x)).replace(u'.', u',')

def loops_of_room(room, z):
    opt = DB.SpatialElementBoundaryOptions(); opt.SpatialElementBoundaryLocation = DB.SpatialElementBoundaryLocation.Finish
    out = []
    for loop in room.GetBoundarySegments(opt):
        cl = DB.CurveLoop()
        for seg in loop:
            c = seg.GetCurve(); t = DB.Transform.CreateTranslation(DB.XYZ(0, 0, z - c.GetEndPoint(0).Z)); cl.Append(c.CreateTransformed(t))
        out.append(cl)
    return out

def footprint(e, z):
    sols = []
    for s in C.solids(e):
        for f in s.Faces:
            if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
                loops = [DB.CurveLoop.CreateViaTransform(cl, DB.Transform.CreateTranslation(DB.XYZ(0, 0, z - f.Origin.Z))) for cl in f.GetEdgesAsCurveLoops()]
                try: sols.append(DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop](loops), DB.XYZ.BasisZ, 1.0))
                except Exception: pass
    return sols

def bottom_loops(solid):
    out = []
    for f in solid.Faces:
        if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.9:
            # one region per bottom face: list of loops, each a list of [x, y] vertices (feet)
            out.append([[[c.GetEndPoint(0).X, c.GetEndPoint(0).Y] for c in cl] for cl in f.GetEdgesAsCurveLoops()])
    return out

def up_hit(doc, view3d, p):
    flt = DB.LogicalOrFilter(DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Floors), DB.ElementCategoryFilter(DB.BuiltInCategory.OST_Roofs))
    ri = DB.ReferenceIntersector(flt, DB.FindReferenceTarget.Face, view3d)
    rc = ri.FindNearest(p, DB.XYZ.BasisZ)
    if rc is None: return None
    ref = rc.GetReference(); e = doc.GetElement(ref); slope = 0.0
    try:
        face = e.GetGeometryObjectFromReference(ref)
        n = face.ComputeNormal(face.Project(ref.GlobalPoint).UVPoint); slope = math.degrees(math.acos(min(1.0, abs(n.Z))))
    except Exception: pass
    t = doc.GetElement(e.GetTypeId())
    return {'id': eid(e), 'cat': u(e.Category.Name), 'type': u(name(t)) if t else u'', 'z': ref.GlobalPoint.Z, 'slope_deg': slope, 'isRoof': isinstance(e, DB.RoofBase)}

def probe(doc):
    v3 = next(v for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D) if not v.IsTemplate and not v.IsPerspective)
    ceils = {}
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Ceilings).WhereElementIsNotElementType():
        ceils.setdefault(e.LevelId.IntegerValue, []).append(e)
    rows = []
    for room in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if room.Area <= 0 or not isinstance(room.Location, DB.LocationPoint): continue
        lid = room.LevelId.IntegerValue; z = doc.GetElement(room.LevelId).Elevation
        rs = DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop](loops_of_room(room, z)), DB.XYZ.BasisZ, 1.0)
        rest = rs; covered = []
        for ce in ceils.get(lid, []):
            for fp in footprint(ce, z):
                try:
                    inter = DB.BooleanOperationsUtils.ExecuteBooleanOperation(rest, fp, DB.BooleanOperationsType.Intersect)
                    if inter.Volume > 1e-4: covered.append([eid(ce), inter.Volume * M * M])
                    rest = DB.BooleanOperationsUtils.ExecuteBooleanOperation(rest, fp, DB.BooleanOperationsType.Difference)
                except Exception: pass
        p = room.Location.Point
        hit = up_hit(doc, v3, DB.XYZ(p.X, p.Y, z + .3 / M))
        # probe also the centroid of the uncovered part (partial rooms)
        hit_rest = None
        if rest.Volume > 1e-4 and covered:
            c = rest.ComputeCentroid(); hit_rest = up_hit(doc, v3, DB.XYZ(c.X, c.Y, z + .3 / M))
        rows.append({'id': eid(room), 'number': u(room.Number), 'name': u(room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()), 'levelId': lid, 'z': z,
                     'area_m2': room.Area * M * M, 'perimeter_m': room.Perimeter * M, 'rest_m2': rest.Volume * M * M, 'covered': covered,
                     'restLoops': bottom_loops(rest) if rest.Volume > 1e-4 else [], 'center': [p.X, p.Y, p.Z],
                     'restCenter': [rest.ComputeCentroid().X, rest.ComputeCentroid().Y] if rest.Volume > 1e-4 else None,
                     'above': hit, 'aboveRest': hit_rest, 'clear_m': ((hit['z'] - z) * M) if hit else None})
    return rows

# ---------------------------------------------------------------- drawing

def filled_type(doc):
    ts = list(DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType))
    for t in ts:
        try:
            fp = doc.GetElement(t.ForegroundPatternId)
            if fp is not None and not fp.GetFillPattern().IsSolidFill: return t
        except Exception: pass
    return ts[0]

def region(doc, v, loops, z, rgb, ftype):
    cls = List[DB.CurveLoop]()
    for lp in loops:
        cl = DB.CurveLoop()
        pts = [DB.XYZ(a[0], a[1], z) for a in lp]
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if a.DistanceTo(b) > 1e-3: cl.Append(DB.Line.CreateBound(a, b))
        cls.Add(cl)
    fr = DB.FilledRegion.Create(doc, ftype.Id, v.Id, cls)
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb)
    ov.SetSurfaceForegroundPatternColor(c); ov.SetProjectionLineColor(c); ov.SetProjectionLineWeight(3)
    v.SetElementOverrides(fr.Id, ov); return fr

COL = {'TC-01': (25, 98, 143), 'TC-02': (196, 98, 16)}
FILL = {'TC-01': (214, 230, 245), 'TC-02': (250, 228, 205)}

def level_plan(doc, lid, lc, ln, d, ftype, solid):
    level = el(doc, lid); z = level.Elevation
    rooms = [r for r in d['rooms'] if r['levelId'] == lid]; rels = [el(doc, r['id']) for r in rooms]
    ces = [c for c in d['existing'] if c['levelId'] == lid]
    v = C.ceiling_plan(doc, level, [x for x in rels if x is not None] + [el(doc, c['id']) for c in ces], PRE + lc + ' - PROPUESTA')
    zz = v.Origin.Z
    for c in ces:   # existing ceilings painted by their documentary type
        C.paint(doc, v, el(doc, c['id']), FILL[c['docType']], solid)
    for r, re_ in zip(rooms, rels):
        if r['excluded']:
            L.tn(doc, v.Id, DB.XYZ(r['center'][0], r['center'][1], z), r['number'] + u' · ' + r['name'] + u' · sin cielorraso (pasadizo)', 'room'); continue
        if r['cp']:
            for lp in r['restLoops']:
                try: region(doc, v, lp, zz, COL[r['docType']], ftype)
                except Exception: pass
        p = r['restCenter'] if r['cp'] and r['covered'] else r['center']
        # keep the whole note inside the crop: annotation crop hides notes that cross it (≈ .13 m per character at 1:60)
        cb = v.CropBox; ch = .13 if (cb.Max.X - cb.Min.X) * M > 15 else .045    # small crops end up at 1:20
        w = max(len(x) for x in r['tag'].split(u'\n')) * ch / M
        x0 = max(min(p[0] - .6 / M, cb.Max.X - w - .3 / M), cb.Min.X + .3 / M)
        L.tn(doc, v.Id, DB.XYZ(x0, p[1], z), r['tag'], 'tag')
    rh = sum(r['total_m2'] for r in rooms if r['docType'] == 'TC-01' and not r['excluded']); st = sum(r['total_m2'] for r in rooms if r['docType'] == 'TC-02' and not r['excluded'])
    cp = sum(r['cp_m2'] for r in rooms)
    sub = u'PROPUESTA A CONFIRMAR · RH %s m² · ST %s m² · propuesto %s m² (rayado) · buña %s ml' % (c2(rh), c2(st), c2(cp), c2(sum(r['perimeter_m'] for r in rooms if not r['excluded'])))
    lines = [u'Azul: TC-01 placa RH 12,5 (zonas húmedas).', u'Naranja: TC-02 placa ST 12,5.', u'Relleno liso: existente en el modelo. Rayado: propuesto (CP).', u'Buña Z 15 mm en todo el perímetro.']
    it = C.item(v, v.CropBox, u'Cielorrasos propuestos · ' + ln, 'plan', ln, [r['code'] for r in rooms if r.get('code')], [], [r['id'] for r in rooms] + [c['id'] for c in ces], lines)
    return dict(S.lay_sheet(doc, 'CIE-P-' + lc, u'Propuesta de cielorrasos · ' + ln, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Cielorrasos · propuesta ' + lc), kind='general', level=ln, sector=ln)

def drafting(doc, vname, scale=5):
    vft = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == DB.ViewFamily.Drafting)
    v = DB.ViewDrafting.Create(doc, vft.Id); v.Name = vname; v.Scale = scale
    return v

def dl(doc, v, a, b, w=None):
    c = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(DB.XYZ(a[0] / M, a[1] / M, 0), DB.XYZ(b[0] / M, b[1] / M, 0)))
    if w:
        ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineWeight(w); v.SetElementOverrides(c.Id, ov)
    return c

def rect(doc, v, x0, y0, x1, y1, w=None):
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]: dl(doc, v, a, b, w)

def detail_ceiling(doc, kind):
    """Section through a suspended ceiling: slab, hangers, 35 mm profiles, 12,5 mm board, Z shadow gap at the wall. Units: m in drawing space."""
    v = drafting(doc, PRE + 'DETALLE ' + kind, 5)
    rect(doc, v, 0, .50, 1.20, .62, 7)                       # losa
    rect(doc, v, 1.20, -.30, 1.35, .62, 7)                   # muro
    for x in (.25, .65, 1.05): dl(doc, v, (x, .50), (x, .095), 3)        # velas rígidas
    rect(doc, v, 0, .060, 1.185, .095, 3)                    # solera / montante 35
    rect(doc, v, 0, .0475, 1.185, .060, 5)                   # placa 12,5 (exagerada x1)
    dl(doc, v, (1.185, .0475), (1.185, .095), 3); dl(doc, v, (1.185, .095), (1.20, .095), 3)   # buña Z 15
    f = L.AxisFrame(v, DB.XYZ.Zero, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims = [L.tick_dim(doc, f, u'Plenum', [.095 / M, .50 / M], False, -.12 / M, tick=.02 / M), L.tick_dim(doc, f, u'Buña', [1.185 / M, 1.20 / M], True, -.06 / M, tick=.02 / M),
            L.tick_dim(doc, f, u'Velas c/1,00 (esquema)', [.25 / M, .65 / M, 1.05 / M], True, .72 / M, tick=.02 / M)]
    board = u'placa RH 12,5 (verde, resistente a humedad)' if kind == 'TC-01' else u'placa ST 12,5'
    L.tn(doc, v.Id, DB.XYZ(0, -.10 / M, 0), u'%s · %s\nperfiles galvanizados 35 (soleras + montantes c/0,40)\nvelas rígidas a losa c/1,00 · juntas tomadas\nbuña perimetral Z 15 mm contra muro' % (kind, board), 'text')
    L.tn(doc, v.Id, DB.XYZ(.05 / M, .56 / M, 0), u'Losa', 'tag'); L.tn(doc, v.Id, DB.XYZ(.30 / M, .30 / M, 0), u'Vela', 'tag')
    return {'view': v, 'box': None, 'title': u'Detalle ' + kind + u' · corte', 'kind': 'detail', 'sector': u'Detalles', 'tags': [kind], 'dims': S.dims_out(dims), 'elements': [], 'data': None}

def detail_buna(doc):
    v = drafting(doc, PRE + 'DETALLE BUNA', 2)
    rect(doc, v, .10, -.10, .16, .20, 7)                     # muro (revoque)
    rect(doc, v, -.30, 0, .085, .0125, 5)                    # placa
    for a, b in [((.085, 0), (.085, .015)), ((.085, .015), (.10, .015)), ((.085, 0), (.10, 0))]: dl(doc, v, a, b, 4)   # perfil Z
    rect(doc, v, -.30, .0125, .085, .0475, 2)                # perfil 35
    f = L.AxisFrame(v, DB.XYZ.Zero, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims = [L.tick_dim(doc, f, u'Buña', [.085 / M, .10 / M], True, -.04 / M, tick=.01 / M), L.tick_dim(doc, f, u'Placa', [0, .0125 / M], False, -.32 / M, tick=.01 / M)]
    L.tn(doc, v.Id, DB.XYZ(-.30 / M, -.10 / M, 0), u'Buña perimetral: perfil Z 15 × 15 mm\natornillado a la solera; separa placa y muro', 'text')
    return {'view': v, 'box': None, 'title': u'Detalle buña perimetral', 'kind': 'detail', 'sector': u'Detalles', 'tags': [u'BUÑA'], 'dims': S.dims_out(dims), 'elements': [], 'data': None}

def detail_tapa(doc):
    v = drafting(doc, PRE + 'DETALLE TAPA', 10)
    rect(doc, v, -.20, -.20, .80, .80, 2)                    # placa alrededor
    rect(doc, v, 0, 0, .60, .60, 6)                          # marco tapa
    rect(doc, v, .02, .02, .58, .58, 3)                      # tapa
    f = L.AxisFrame(v, DB.XYZ.Zero, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims = [L.tick_dim(doc, f, u'Tapa ancho', [0, .60 / M], True, -.10 / M, tick=.03 / M), L.tick_dim(doc, f, u'Tapa largo', [0, .60 / M], False, -.10 / M, tick=.03 / M)]
    L.tn(doc, v.Id, DB.XYZ(-.20 / M, -.30 / M, 0), u'Tapa de inspección 60 × 60 con marco de aluminio\ny placa del mismo tipo que el cielorraso (vista desde abajo)', 'text')
    return {'view': v, 'box': None, 'title': u'Detalle tapa de inspección 60×60', 'kind': 'detail', 'sector': u'Detalles', 'tags': [u'TAPA'], 'dims': S.dims_out(dims), 'elements': [], 'data': None}

def details_sheet(doc):
    its = [detail_ceiling(doc, 'TC-02'), detail_ceiling(doc, 'TC-01'), detail_buna(doc), detail_tapa(doc)]
    doc.Regenerate()
    for it in its:   # drafting views have no crop box: use the extents of what was drawn
        bb = DB.BoundingBoxXYZ(); pts = []
        for e in DB.FilteredElementCollector(doc, it['view'].Id).WhereElementIsNotElementType():
            b = e.get_BoundingBox(it['view'])
            if b is not None and e.Category is not None: pts += [b.Min, b.Max]
        bb.Min = DB.XYZ(min(p.X for p in pts) - .05 / M, min(p.Y for p in pts) - .05 / M, 0); bb.Max = DB.XYZ(max(p.X for p in pts) + .05 / M, max(p.Y for p in pts) + .05 / M, 0)
        it['box'] = bb
    s = S.lay_sheet(doc, 'CIE-D-01', u'Detalles de cielorrasos (propuesta)', u'TC-02 placa ST · TC-01 placa RH · buña perimetral Z 15 mm · tapa de inspección 60×60', its, FOOT, rubro=RUBRO, sheet_name=u'Cielorrasos · detalles')
    return [dict(s, kind='general', level=u'Detalles', sector=u'Detalles')]

def index_part(doc, job):
    old = [s for s in DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet) if s.SheetNumber == 'CIE-00']
    for s in old: doc.Delete(s.Id)
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CIE-00'; sheet.Name = u'Cielorrasos · índice'
    head = u'CASA ÁNGEL · CIELORRASOS · ÍNDICE Y CÓMPUTO (PROPUESTA A CONFIRMAR)'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CIE-00', 'title': u'Índice y cómputo (propuesta)', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Cielorrasos', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'cp-' + part + '.json')
    if part == 'probe':
        rows = probe(doc); R1.write(os.path.join(OUT, 'cp-probe.json'), {'readAt': L.now(), 'rooms': rows})
        return {'status': 'success', 'rooms': [(r['number'], r['name'], round(r['area_m2'], 2), round(r['rest_m2'], 2), [round(c[1], 2) for c in r['covered']], r['above'] and (r['above']['cat'], round(r['clear_m'], 2), round(r['above']['slope_deg'], 1)), r['aboveRest'] and (r['aboveRest']['cat'], round((r['aboveRest']['z'] - r['z']) * M, 2), round(r['aboveRest']['slope_deg'], 1))) for r in rows]}
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('cp-') and fn.endswith('.json')): continue
            rec = R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for sh in rec['sheets']:
                if sh.get('exported') and not job.get('all'): done.append(sh['number']); continue
                opts.FileName = 'r28-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, sh['sheetId']).Id]), opts)); done.append(sh['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if job.get('reset') or job.get('resetPart'):
        rec = R1.read(path) if job.get('resetPart') else None
        def body():
            if rec: ids = [el(doc, i).Id for sh in rec['sheets'] for i in [sh['sheetId']] + [v['id'] for v in sh['views']] if el(doc, i) is not None]
            else: ids = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if (isinstance(v, DB.ViewSheet) and (v.SheetNumber.startswith('CIE-P-') or v.SheetNumber == 'CIE-D-01')) or name(v).startswith(PRE)]
            n = 0
            for i in ids:
                if doc.GetElement(i) is not None: doc.Delete(i); n += 1
            return n
        n, checked = L.guarded(doc, 'ADER CIE R28 - reset', body)
        for fn in os.listdir(OUT):
            if fn.startswith('cp-') and fn.endswith('.json') and fn not in ('cp-plan.json', 'cp-probe.json') and (not rec or os.path.join(OUT, fn) == path): os.remove(os.path.join(OUT, fn))
        doc.Save(); return {'status': 'success', 'deleted': n}
    if os.path.exists(path):
        rec = R1.read(path)
        if all(el(doc, sh['sheetId']) for sh in rec['sheets']): return {'status': 'success', 'existing': [sh['number'] for sh in rec['sheets']]}
    d = L.read('cp-plan')
    for r in d['rooms']:
        for k in ('name', 'tag', 'label'):
            if r.get(k): r[k] = R1.clean(r[k])
    def body():
        if part == 'plans':
            ft = filled_type(doc); solid = P.solid_fill(doc)
            return [level_plan(doc, lid, lc, ln, d, ft, solid) for lid, lc, ln in LEVELS]
        if part == 'details': return details_sheet(doc)
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER CIE R28 - ' + part, body)
    for sh in sheets:
        for v in sh['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [v['scale'] for v in sh['views']]) for sh in sheets]}
