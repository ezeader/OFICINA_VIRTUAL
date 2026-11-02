# -*- coding: utf-8 -*-
"""R38 Albañilería · planos maestros (Casa-Angel-DOC-Albanileria.rvt, pilot linked and never modified).
model  : every wall of PB/PA/PE (no curtain walls, portón or 'Puerta Arco'): category by type (H° visto / exterior–interior /
         interior–interior / otros), code M-<lv>-nn left→right in rows from top to bottom, measures and layers.
masters: ALB-PB-01 / ALB-PA-01 / ALB-PE-01 · plan as large as possible, walls filled by category (filled regions over the
         halftone link), only the code on each wall, room names, legend and measures table.
details: ALB-<lv>-02.. · each wall: elevation (openings + measures) and section (layers), several walls per sheet in code order."""
import os, imp, math, json, io
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
P = imp.load_source('ader_clidoc_r32_for_alb', os.path.join(ROOT, 'revit_clima_doc_r32.py'))
C = P.C; B = P.B; L = P.L; S = P.S; X = P.X; R1 = P.R1; CTX = P.CTX
A20 = imp.load_source('ader_alb_r20_for_r38', os.path.join(ROOT, 'revit_alb_r20.py'))
M = L.M; OUT = L.OUT; eid = L.eid; u = L.u
PRE = 'ADER ALB R38 - '
S.COLORS['AB'] = (196, 98, 16)
RUBRO = u'ALBAÑILERÍA'
LVC = {u'00. Planta Baja': 'PB', u'005. Acceso ppal': 'PB', u'01. Planta Alta': 'PA', u'02. Planta Entrepiso': 'PE'}
LVN = {'PB': u'00. Planta Baja', 'PA': u'01. Planta Alta', 'PE': u'02. Planta Entrepiso'}
CAT = {'HV': (u'H° visto', (85, 85, 85)), 'EI': (u'Exterior – interior', (235, 90, 0)), 'II': (u'Interior – interior', (0, 90, 230)), 'OT': (u'Otros (no es muro de albañilería)', (200, 200, 200))}
II_SHADES = {'TM-01': (0, 90, 230), 'TM-02': (0, 40, 150), 'TM-03': (0, 175, 240), 'TM-07': (0, 165, 60), 'TM-08': (0, 100, 40)}
TYPECAT = {'TM-04': 'HV', 'TM-06': 'HV', 'TM-05': 'EI', 'TM-01': 'II', 'TM-02': 'II', 'TM-03': 'II', 'TM-07': 'II', 'TM-08': 'II', 'TM-09': 'OT', 'TM-10': 'OT'}
SKIP = (u'Hojas Portón', u'Puerta Arco')
FOOT = u'Albañilería R38 (archivo de documentación con el modelo principal vinculado, sin modificarlo). Color por categoría de muro; los muros de H° se computan en Estructura. ' \
       u'Códigos M-<nivel>-nn de izquierda a derecha y de arriba hacia abajo. Medidas en metros: largo × alto × espesor.'

def nm(e):
    try: return u(DB.Element.Name.GetValue(e))
    except Exception: return u''

import re
def unesc(x):
    """strings written by IronPython keep non-ASCII as literal backslash-x escapes: restore them."""
    return re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: unichr(int(m.group(1), 16)), x) if isinstance(x, basestring) else x

def tcl(w): return u'H° (Estructura)' if w['typeCode'] == u'HA' else w['typeCode']

def c2(x): return (u'%.2f' % x).replace(u'.', u',')

# ---------------------------------------------------------------- model
def model(doc, ld):
    alb = R1.read(os.path.join(OUT, 'alb-plan.json')); tcode = dict((t['type'], t['code']) for t in alb['types']); tlayers = dict((t['code'], t['layers']) for t in alb['types'])
    walls = []
    for w in DB.FilteredElementCollector(ld).OfClass(DB.Wall):
        try:
            if w.WallType.Kind == DB.WallKind.Curtain or not isinstance(w.Location, DB.LocationCurve): continue
        except Exception: continue
        tn = nm(w.WallType)
        if any(s in tn for s in SKIP): continue
        lv = LVC.get(nm(ld.GetElement(w.LevelId)))
        if lv is None: continue
        c = w.Location.Curve; bb = w.get_BoundingBox(None)
        if bb is None or c.Length * M < .05: continue
        tc = tcode.get(tn)
        cat = TYPECAT.get(tc) if tc else ('HV' if u'Hormig' in tn or u'H°' in tn else None)
        if cat is None: continue
        pts = [c.Evaluate(i / 8.0, True) for i in range(9)] if isinstance(c, DB.Arc) else [c.GetEndPoint(0), c.GetEndPoint(1)]
        layers = tlayers.get(tc)
        if layers is None:
            cs = w.WallType.GetCompoundStructure()
            layers = [{'material': nm(ld.GetElement(l.MaterialId)) if l.MaterialId.IntegerValue > 0 else u'(genérico)', 'function': str(l.Function), 'thickness_m': round(l.Width * M, 4)} for l in cs.GetLayers()] if cs else []
        hp = w.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)
        h = hp.AsDouble() * M if hp is not None and hp.AsDouble() > 0 else (bb.Max.Z - bb.Min.Z) * M
        ins = [ld.GetElement(i) for i in w.FindInserts(True, False, False, False)]
        walls.append({'id': w.Id.IntegerValue, 'type': tn, 'typeCode': tc or u'HA', 'cat': cat, 'level': lv, 'length_m': round(c.Length * M, 3), 'height_m': round(h, 3),
                      'thickness_m': round(w.Width * M, 3), 'pts': [[round(p.X * M, 3), round(p.Y * M, 3)] for p in pts], 'arc': isinstance(c, DB.Arc),
                      'mid': [round(c.Evaluate(.5, True).X * M, 3), round(c.Evaluate(.5, True).Y * M, 3)], 'z': [round(bb.Min.Z * M, 3), round(bb.Max.Z * M, 3)],
                      'openings': [{'id': x.Id.IntegerValue, 'cat': x.Category.Name if x.Category else u'', 'type': nm(ld.GetElement(x.GetTypeId()))} for x in ins if x is not None],
                      'layers': layers, 'concrete': tc is None})
    for lv in ('PB', 'PA', 'PE'):
        ws = [w for w in walls if w['level'] == lv and w['cat'] != 'OT']
        ws.sort(key=lambda w: (-int(math.floor(w['mid'][1] / 1.5)), w['mid'][0]))   # rows of 1,5 m from the top, left to right
        for i, w in enumerate(ws): w['code'] = u'M-%s-%02d' % (lv, i + 1)
    for w in walls:
        if w['cat'] == 'OT': w['code'] = None
    R1.write(os.path.join(OUT, 'alb38-model.json'), {'walls': walls, 'readAt': L.now()})
    return walls

# ---------------------------------------------------------------- drawing helpers
_FRT = {}
def frt(doc, key, rgb):
    nm_ = u'ADER ALB R38b ' + key
    if nm_ in _FRT: return _FRT[nm_]
    t = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType) if nm(x) == nm_), None)
    if t is None:
        base = next(x for x in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType))
        t = base.Duplicate(nm_)
        solid = next(p for p in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement) if p.GetFillPattern().IsSolidFill)
        t.ForegroundPatternId = solid.Id; t.ForegroundPatternColor = DB.Color(*rgb)
        try: t.LineWeight = 5                      # heavy outline: the cut reads as a solid band
        except Exception: pass
        try: t.BackgroundPatternId = DB.ElementId.InvalidElementId
        except Exception: pass
    _FRT[nm_] = t; return t

def wall_region(doc, v, w, z, t):
    pts = [DB.XYZ(p[0] / M, p[1] / M, z) for p in w['pts']]; h = w['thickness_m'] / 2 / M
    left = []; right = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        d = (b - a).Normalize(); n = DB.XYZ(-d.Y, d.X, 0)
        left.append(p + n * h); right.append(p - n * h)
    ring = left + list(reversed(right)); loop = DB.CurveLoop()
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        if a.DistanceTo(b) > .002: loop.Append(DB.Line.CreateBound(a, b))
    try: DB.FilledRegion.Create(doc, t.Id, v.Id, List[DB.CurveLoop]([loop])); return True
    except Exception: return False

def colour(w):
    if w['cat'] == 'II': return II_SHADES.get(w['typeCode'], CAT['II'][1])
    return CAT[w['cat']][1]

def table_items(doc, vname, blocks, scale, chunk=22):
    cols = []; cur = []; n = 0
    for t, ls in blocks:
        for i in range(0, max(len(ls), 1), chunk):
            part = ls[i:i + chunk]
            if n + len(part) + 1 > chunk and cur: cols.append(cur); cur = []; n = 0
            cur.append((t if i == 0 else t + u' (cont.)', part)); n += len(part) + 1
    if cur: cols.append(cur)
    out = []
    for k, col in enumerate(cols):
        v = C.drafting(doc, vname + (u' %d' % (k + 1) if len(cols) > 1 else u''), scale)
        C.legend(doc, v, 0, 0, 0, col, [])
        out.append(C.item(doc, v, (u'Cuadro (%d/%d)' % (k + 1, len(cols))) if len(cols) > 1 else u'Cuadro', [], []))
    return out

# ---------------------------------------------------------------- masters
def master(doc, ld, lv, walls, rooms):
    ws = [w for w in walls if w['level'] == lv]
    pts = [DB.XYZ(p[0] / M, p[1] / M, 0) for w in ws for p in w['pts']]
    v, lev = P.plan_view(doc, LVN[lv], PRE + lv + ' MAESTRO', pts, 50, pad=.8); z = lev.Elevation
    crop = C.crop_of(v); placed = []; boxes = []
    for w in ws:
        t = frt(doc, w['typeCode'] if w['cat'] == 'II' else w['cat'], colour(w)); wall_region(doc, v, w, z, t)
    for r in rooms:
        if LVC.get(r['level']) != lv: continue
        C.place(doc, v, DB.XYZ(r['c'][0] / M, r['c'][1] / M, z), r['name'], placed, crop, 'room', z)
    for w in ws:      # wall bands are obstacles for the code labels
        xs = [p[0] for p in w['pts']]; ys = [p[1] for p in w['pts']]; h = w['thickness_m'] / 2 + .05
        placed.append(((min(xs) - h) / M, (min(ys) - h) / M, (max(xs) + h) / M, (max(ys) + h) / M))
    for w in sorted([w for w in ws if w['code']], key=lambda w: w['code']):
        q = DB.XYZ(w['mid'][0] / M, w['mid'][1] / M, z)
        C.place(doc, v, q, w['code'], placed, crop, 'tag', z)
        xs = [p[0] for p in w['pts']]; ys = [p[1] for p in w['pts']]; m = .15
        boxes.append(({'code': w['code'], 'elementId': str(w['id']), 'label': u'%s · %s · %s × %s × %s' % (w['code'], tcl(w), c2(w['length_m']), c2(w['height_m']), c2(w['thickness_m']))},
                      DB.XYZ((min(xs) - m) / M, (min(ys) - m) / M, z), DB.XYZ((max(xs) + m) / M, (max(ys) + m) / M, z)))
    coded = sorted([w for w in ws if w['code']], key=lambda w: w['code'])
    rows = [u'%s · %s · %s × %s × %s' % (w['code'], tcl(w), c2(w['length_m']), c2(w['height_m']), c2(w['thickness_m'])) for w in coded]
    leg = [u'Gris: %s (se computa en Estructura)' % CAT['HV'][0], u'Naranja: %s (TM-05)' % CAT['EI'][0], u'Azules/verdes: %s · TM-01/02/03 mampostería, TM-07/08 Durlock' % CAT['II'][0],
           u'Gris claro: %s (TM-09 chimenea, TM-10 cierre de cielorraso), sin código' % CAT['OT'][0], u'Medidas: largo × alto × espesor (m)']
    its = [X.item(v, v.CropBox, u'Planta · ' + LVN[lv], 'plan', LVN[lv], [w['code'] for w in coded], [], [])]
    oldx = L.X1; L.X1 = L.X1 - .62          # right-hand strip for legend + measures table (sheet text): the plan gets the rest
    old = list(L.SCALES); L.SCALES[:] = [50, 75, 100, 125]
    try: s = S.lay_sheet(doc, 'ALB-%s-01' % lv, u'Plano maestro de muros · ' + LVN[lv], u'%d muros codificados · color por categoría · medidas en el cuadro' % len(coded), its, FOOT, rubro=RUBRO, sheet_name=u'Albañilería · %s-01' % lv)
    finally: L.SCALES[:] = old; L.X1 = oldx
    sh = doc.GetElement(DB.ElementId(Int64(int(s['sheetId'])))); x = L.X1 - .60; y = L.TOP
    L.tn(doc, sh.Id, DB.XYZ(x, y, 0), u'Referencias', 'sub'); s['notes'].append({'text': u'Referencias', 'anchor': [x, y]}); y -= .028
    for key in ['HV', 'EI', 'II', 'OT']:
        sty = P.style(doc, 'ALB muestra2 ' + key, CAT[key][1], 9)
        for k in range(3):
            yy = y - .007 - k * .002
            dc = doc.Create.NewDetailCurve(sh, DB.Line.CreateBound(DB.XYZ(x + .005, yy, 0), DB.XYZ(x + .05, yy, 0))); dc.LineStyle = sty
        txt = {'HV': u'H° visto (se computa en Estructura)', 'EI': u'Exterior – interior (TM-05)', 'II': u'Interior – interior: TM-01/02/03 mampostería · TM-07/08 Durlock', 'OT': u'Otros: TM-09 chimenea · TM-10 cierre de cielorraso (sin código)'}[key]
        L.tn(doc, sh.Id, DB.XYZ(x + .065, y + .002, 0), txt, 'text'); y -= .024
    y -= .015
    t2 = u'Muros %s · largo × alto × espesor (m)' % lv
    L.tn(doc, sh.Id, DB.XYZ(x, y, 0), t2, 'sub'); s['notes'].append({'text': t2, 'anchor': [x, y]}); y -= .028
    half = (len(rows) + 1) // 2 if len(rows) > 26 else len(rows)
    for k, chunk in enumerate([rows[:half], rows[half:]] if half < len(rows) else [rows]):
        L.tn(doc, sh.Id, DB.XYZ(x + k * .31, y, 0), u'\n'.join(chunk), 'room')
    doc.Regenerate()
    s['views'][0]['albElements'] = sheet_boxes(doc, v, s['views'][0], boxes)
    return dict(s, kind='general', level=LVN[lv], sector=u'Planos maestros')

def sheet_boxes(doc, v, meta, pts_boxes):
    vp = next(x for x in DB.FilteredElementCollector(doc).OfClass(DB.Viewport) if x.ViewId == v.Id)
    mp = v.GetModelToProjectionTransforms()[0].GetModelToProjectionTransform(); ps = vp.GetProjectionToSheetTransform()
    f = lambda p: ps.OfPoint(mp.OfPoint(p))
    (bx0, by0, _), (bx1, by1, _) = meta['box']; m = 3 / (2383.94 / 2.7592)
    rx0, ry0, rx1, ry1 = bx0 - m, by0 - m, bx1 + m, by1 + m; out = []
    for key, lo, hi in pts_boxes:
        pp = [f(DB.XYZ(x, y, lo.Z)) for x in (lo.X, hi.X) for y in (lo.Y, hi.Y)]
        sx0 = min(p.X for p in pp); sx1 = max(p.X for p in pp); sy0 = min(p.Y for p in pp); sy1 = max(p.Y for p in pp)
        b = [(sx0 - rx0) / (rx1 - rx0), (ry1 - sy1) / (ry1 - ry0), (sx1 - rx0) / (rx1 - rx0), (ry1 - sy0) / (ry1 - ry0)]
        out.append(dict(key, box=[round(max(0., min(1., x)), 4) for x in b]))
    return out

# ---------------------------------------------------------------- details
def details(doc, ld, lv, walls, per=4, only=None):
    ws = sorted([w for w in walls if w['level'] == lv and w['code']], key=lambda w: w['code'])
    groups = [ws[i:i + per] for i in range(0, len(ws), per)]; out = []
    for k, g in enumerate(groups):
        num = 'ALB-%s-%02d' % (lv, k + 2)
        if only and num not in only: continue
        its = []; cuts = []
        for w in g:
            e = ld.GetElement(DB.ElementId(Int64(w['id'])))
            wd = {'code': w['code'], 'label': u'%s · %s × %s × %s' % (w['code'], c2(w['length_m']), c2(w['height_m']), c2(w['thickness_m'])), 'id': w['id'],
                  'kind': 'AB', 'sheetLevel': None, 'level': LVN[lv], 'status': tcl(w)}
            ev = S.wall_elevation(doc, e, wd, {}, PRE + w['code'] + ' VISTA'); ev['title'] = u'%s · vista · %s' % (w['code'], tcl(w)); ev['data'] = None; its.append(ev)
            for l_ in w['layers'] or []: l_['material'] = unesc(l_['material'])
            t = {'code': w['code'], 'layers': w['layers'] or [{'material': u'(genérico)', 'thickness_m': w['thickness_m']}]}
            vs, bxs, ds = A20.wall_layers_section(doc, t, e, PRE + w['code'] + ' CORTE')
            cuts.append(A20.item(vs, bxs, u'%s · corte (capas)' % w['code'], 'section', LVN[lv], [w['code']], ds, [w['id']]))
        s = lay_rows(doc, num, u'Muros %s a %s · vista y corte' % (g[0]['code'], g[-1]['code']), u'%s · %d muros · alzado con vanos y medidas + corte con capas 1:10' % (LVN[lv], len(g)),
                     list(zip(its, cuts)), u'Albañilería · %s-%02d' % (lv, k + 2))
        out.append(dict(s, kind='general', level=LVN[lv], sector=u'Detalle de muros · ' + lv, walls=[w['code'] for w in g]))
    return out

VSC = [20, 25, 50, 75, 100]
def lay_rows(doc, number, title, sub, pairs, sheet_name):
    """one row per wall: elevation (largest scale that fits) on the left, layer section always at 1:10 on the right."""
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = number; sheet.Name = sheet_name
    head = u'CASA ÁNGEL · ' + RUBRO + u' · ' + title.upper(); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title')
    sy = L.Y1 - .075; L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, sy, 0), sub, 'sub'); notes.append({'text': sub, 'anchor': [L.X0 + .01, sy]})
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    vpt = S.vptype(doc); views = []; n = max(len(pairs), 4)
    top = L.TOP - .02; bot = L.BOTTOM; rh = (top - bot) / n; xs = L.X0 + .01; xm = L.X0 + (L.X1 - L.X0) * .68
    for k, (ev, cut) in enumerate(pairs):
        y1 = top - k * rh; y0 = y1 - rh
        w_, h_ = L.sheet_size(ev['box'], 1)
        sc = next((c for c in VSC if w_ / c <= (xm - xs) - .04 and h_ / c <= rh - L.TITLE_H - .03), VSC[-1])
        for it, cell, scale in ((ev, (xs, y0, xm, y1), sc), (cut, (xm, y0, L.X1 - .01, y1), 10)):
            vp, meta = L.place(doc, sheet, it['view'], scale, (cell[0], cell[1] - L.DATA_H, cell[2], cell[3]), it['title'], vpt)
            meta.update(kind=it['kind'], sector=it['sector'], tags=it['tags'], dims=it['dims'], elements=it['elements']); views.append(meta)
    return {'sheetId': eid(sheet), 'number': number, 'title': title, 'views': views, 'notes': notes}

# ---------------------------------------------------------------- run
def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, X.F, X, A20, None])
    seen = set()
    for m in (A20.L, getattr(A20.F, 'L', None), getattr(A20.S, 'L', None)):   # the R20 helpers load their own module copies
        if m is not None and id(m) not in seen and m is not L: seen.add(id(m)); CTX.activate(doc, m, [m, A20.F, A20.S, A20])
    assert ld is not None and 'albanileria' in doc.PathName.lower(), 'Abrir Casa-Angel-DOC-Albanileria.rvt'
    part = job['part']; path = os.path.join(OUT, 'alb38-sheets.json')
    if part == 'model': return {'status': 'success', 'walls': len(model(doc, ld))}
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        rec = R1.read(path); done = []
        for sh in rec['sheets']:
            e = doc.GetElement(DB.ElementId(Int64(sh['sheetId'])))
            if e is None: done.append(sh['number'] + ' FALTA'); continue
            opts.FileName = 'r38-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([e.Id]), opts)); done.append(sh['number'])
        R1.write(path, rec); return {'status': 'success', 'exported': done}
    L.register_font()
    B.plain(doc, PRE + 'datos del proyecto', lambda: B.project_info(doc, ld))
    walls = R1.read(os.path.join(OUT, 'alb38-model.json'))['walls']
    rooms = [r for r in R1.read(os.path.join(OUT, 'dom35-plan.json'))['rooms']]
    for r in rooms: r['level'] = LVN[r['level']]
    prev = R1.read(path)['sheets'] if os.path.exists(path) else []
    lvs = job.get('levels') or ['PB', 'PA', 'PE']; only = job.get('only')
    def keep(sh): return not ((part == 'masters' and sh['number'].endswith('-01') and sh['number'][4:6] in lvs) or (part == 'details' and not sh['number'].endswith('-01') and sh['number'][4:6] in lvs and (not only or sh['number'] in only)))
    old = [sh for sh in prev if not keep(sh)]
    def wipe():
        for sh in old:
            for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                e = doc.GetElement(DB.ElementId(Int64(int(i))))
                if e is not None: doc.Delete(e.Id)
    if old: B.plain(doc, PRE + 'borrar', wipe)
    new = []
    for lv in lvs:
        if part == 'masters': new += B.plain(doc, PRE + 'maestro ' + lv, lambda: [master(doc, ld, lv, walls, rooms)])
        elif part == 'details': new += B.plain(doc, PRE + 'detalles ' + lv, lambda: details(doc, ld, lv, walls, job.get('per', 4), only))
    for sh in new:
        for x in sh['views']: x.pop('view', None)
    sheets = sorted([sh for sh in prev if keep(sh)] + new, key=lambda s: s['number'])
    R1.write(path, {'revision': 'R38', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'sheets': [(sh['number'], [x['scale'] for x in sh['views']]) for sh in new]}
