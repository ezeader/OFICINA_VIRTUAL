# -*- coding: utf-8 -*-
"""R35 Domótica etapa 2 in Casa-Angel-DOC-Domotica.rvt (pilot linked, never modified): 12 sheets from dom35-plan.json.
Elements are 2D symbols (detail lines with one line style per system) + code tag; rooms labelled (with A/B/C on IL sheets);
table per sheet (código · tipo · local · nivel · montaje). Sheet boxes of every symbol and room are computed here for the web hover."""
import os, imp, math, json, io
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
P = imp.load_source('ader_clidoc_r32_for_dom', os.path.join(ROOT, 'revit_clima_doc_r32.py'))
C = P.C; B = P.B; L = P.L; S = P.S; X = P.X; R1 = P.R1; CTX = P.CTX
M = L.M; OUT = L.OUT; eid = L.eid
PRE = 'ADER DOM R35 - '
RUBRO = u'DOMÓTICA'
FOOT = u'Domótica R35 (archivo de documentación con el modelo principal vinculado, sin modificarlo). Elementos dibujados como símbolos 2D ubicados por reglas sobre locales y aberturas del modelo; ' \
       u'«opc» = opcional. Iluminación: A domótica completa · B solo sensor · C preparado (llave común + caja profunda con neutro).'
LVN = {'PB': u'00. Planta Baja', 'PA': u'01. Planta Alta', 'PE': u'02. Planta Entrepiso'}
COL = {'IL': (230, 140, 0), 'CR': (0, 120, 200), 'CL': (200, 30, 30), 'CA': (110, 60, 160), 'RD': (0, 140, 90), 'AU': (190, 60, 140), 'AC': (90, 90, 90), 'RG': (40, 150, 200), 'SG': (220, 0, 0)}
SHAPE = {'PIR': 'circle', 'PRE': 'circle2', 'DH': 'circle2', 'AU': 'circle', 'AP': 'circle2', 'TK': 'square', 'TE': 'square', 'RG': 'square', 'VP': 'square', 'CE': 'square',
         'TL': 'rect', 'ME': 'square', 'RK': 'rect', 'GW': 'rect', 'SI': 'square', 'CAM': 'tri', 'CM': 'bar', 'DA': 'diamond', 'MG': 'diamond', 'LL': 'diamond', 'SV': 'diamond', 'DG': 'diamond', 'EVG': 'square', 'PO': 'rect'}
SHEETS = [('DOM-00', u'Índice y planta general', None, None), ('DOM-IL-PB', u'Iluminación y sensores · Planta Baja', 'IL', 'PB'), ('DOM-IL-PA', u'Iluminación y sensores · Planta Alta', 'IL', 'PA'),
          ('DOM-IL-PE', u'Iluminación y sensores · Entrepiso', 'IL', 'PE'), ('DOM-CR', u'Cortinas', 'CR', None), ('DOM-CL', u'Climatización (referencia CLI)', 'CL', None),
          ('DOM-CA', u'Cámaras', 'CA', None), ('DOM-RD', u'Red Wi-Fi, rack, tableros y energía', 'RD', None), ('DOM-AU', u'Audio', 'AU', None), ('DOM-AC', u'Acceso', 'AC', None),
          ('DOM-RG', u'Riego', 'RG', None), ('DOM-SG', u'Seguridad técnica', 'SG', None)]
PT_PER_FT = 2383.94 / 2.7592

def plan():
    with io.open(os.path.join(OUT, 'dom35-plan.json'), encoding='utf-8') as f: return json.load(f)

def pos(ld, e, z):
    if e.get('x') is not None: return DB.XYZ(e['x'] / M, e['y'] / M, z)
    p = P.loc(ld, e['ref']); return DB.XYZ(p.X, p.Y, z) if p is not None else None

def ln(doc, v, a, b, sty):
    if a.DistanceTo(b) < .01: return
    dc = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(a, b)); dc.LineStyle = sty

def arc(doc, v, c, r, sty):
    # one open arc (tiny gap): two semicircles sharing end points get auto-joined and Revit then fails with "Can't keep elements joined"
    dc = doc.Create.NewDetailCurve(v, DB.Arc.Create(c, r, 0, 2 * math.pi - 1e-3, DB.XYZ.BasisX, DB.XYZ.BasisY)); dc.LineStyle = sty

def symbol(doc, v, e, q, sty, thin):
    s = .14 / M * (1.0 if v.Scale <= 50 else 1.4); k = SHAPE.get(e['kind'], 'circle'); o = lambda dx, dy: DB.XYZ(q.X + dx, q.Y + dy, q.Z)
    poly = lambda pts: [ln(doc, v, o(*pts[i - 1]), o(*pts[i]), sty) for i in range(len(pts))]
    if k == 'circle': arc(doc, v, q, s, sty)
    elif k == 'circle2': arc(doc, v, q, s, sty); arc(doc, v, q, s * .45, sty)
    elif k == 'square': poly([(-s, -s), (s, -s), (s, s), (-s, s)])
    elif k == 'rect': poly([(-s * 1.8, -s * .8), (s * 1.8, -s * .8), (s * 1.8, s * .8), (-s * 1.8, s * .8)])
    elif k == 'diamond': poly([(0, -s * 1.2), (s * 1.2, 0), (0, s * 1.2), (-s * 1.2, 0)])
    elif k == 'tri':
        a = e['cone'][0]; pts = [(s * 1.4 * math.cos(a + t), s * 1.4 * math.sin(a + t)) for t in (0, 2.4, -2.4)]; poly(pts)
        R_ = e['cone'][2] / M; h = math.radians(e['cone'][1]) / 2
        for t in (-h, h): ln(doc, v, q, o(R_ * math.cos(a + t), R_ * math.sin(a + t)), thin)
        n = 8
        for i in range(n): ln(doc, v, o(R_ * math.cos(a - h + 2 * h * i / n), R_ * math.sin(a - h + 2 * h * i / n)), o(R_ * math.cos(a - h + 2 * h * (i + 1) / n), R_ * math.sin(a - h + 2 * h * (i + 1) / n)), thin)
    elif k == 'bar':
        w = min(max(e.get('width') or 1.0, .5), 2.5) / M / 2; poly([(-w, -s * .35), (w, -s * .35), (w, s * .35), (-w, s * .35)])

def sheet_box(doc, v, sh_view, pts_boxes):
    vp = next(x for x in DB.FilteredElementCollector(doc).OfClass(DB.Viewport) if x.ViewId == v.Id)
    mp = v.GetModelToProjectionTransforms()[0].GetModelToProjectionTransform(); ps = vp.GetProjectionToSheetTransform()
    f = lambda p: ps.OfPoint(mp.OfPoint(p))
    (bx0, by0, _), (bx1, by1, _) = sh_view['box']; m = 3 / PT_PER_FT
    rx0, ry0, rx1, ry1 = bx0 - m, by0 - m, bx1 + m, by1 + m; out = []
    for key, lo, hi in pts_boxes:
        pp = [f(DB.XYZ(x, y, lo.Z)) for x in (lo.X, hi.X) for y in (lo.Y, hi.Y)]
        sx0 = min(p.X for p in pp); sx1 = max(p.X for p in pp); sy0 = min(p.Y for p in pp); sy1 = max(p.Y for p in pp)
        b = [(sx0 - rx0) / (rx1 - rx0), (ry1 - sy1) / (ry1 - ry0), (sx1 - rx0) / (rx1 - rx0), (ry1 - sy0) / (ry1 - ry0)]
        out.append(dict(key, box=[round(max(0., min(1., x)), 4) for x in b]))
    return out

def level_plan(doc, ld, pl, lv, els, vname, scale, il, codes_only):
    rooms = [r for r in pl['rooms'] if r['level'] == lv]
    pts = [DB.XYZ(r['c'][0] / M, r['c'][1] / M, 0) for r in rooms] + [q for e in els for q in [pos(ld, e, 0)] if q is not None]
    lrooms = dict((r['id'], ld.GetElement(DB.ElementId(Int64(r['id'])))) for r in rooms)
    for r in lrooms.values():
        bb = r.get_BoundingBox(None) if r is not None else None
        if bb: pts += [bb.Min, bb.Max]
    v, lev = P.plan_view(doc, LVN[lv], vname, pts, scale, pad=1.2); z = lev.Elevation
    crop = C.crop_of(v); placed = []; boxes = []
    for r in rooms:
        lab = r['name'] + ((u' · ' + r['zone']) if il and r.get('zone') else u'')
        C.place(doc, v, DB.XYZ(r['c'][0] / M, r['c'][1] / M - .45 / M, z), lab, placed, crop, 'text', z)
        re_ = lrooms.get(r['id']); bb = re_.get_BoundingBox(None) if re_ is not None else None
        if bb: boxes.append(({'code': u'room-%d' % r['id'], 'elementId': str(r['id']), 'label': r['name'] + ((u' · nivel ' + r['zone']) if r.get('zone') else u''), 'room': True},
                             DB.XYZ(bb.Min.X, bb.Min.Y, z), DB.XYZ(bb.Max.X, bb.Max.Y, z)))
    thin = P.style(doc, 'DOM fino', (120, 120, 120), 1); used = []
    for e in els:
        if e['kind'] == 'LZ': continue                       # the zone is shown in the room label
        q = pos(ld, e, z)
        if q is None: continue
        k = 0   # two symbols on the same spot make Revit join their detail lines ("Can't keep elements joined"): nudge apart
        while any(q.DistanceTo(u_) < .30 / M for u_ in used) and k < 8:
            k += 1; q = DB.XYZ(q.X + .35 / M * math.cos(k * 2.4), q.Y + .35 / M * math.sin(k * 2.4), z)
        used.append(q)
        sty = P.style(doc, 'DOM ' + e['system'], COL[e['system']], 4)
        symbol(doc, v, e, q, sty, thin)
        txt = e['code'] + (u' opc' if e['opt'] else u'') if codes_only else e['code'] + (u' opc' if e['opt'] else u'') + ((u' · ' + e['note']) if e['kind'] == 'CM' else u'')
        C.place(doc, v, DB.XYZ(q.X + .2 / M, q.Y + .2 / M, z), txt, placed, crop, 'text' if codes_only else 'tag', z)
        h = .25 / M; boxes.append(({'code': e['code'], 'label': u'%s · %s · %s' % (e['code'], e['type'], e['room'])}, DB.XYZ(q.X - h, q.Y - h, z), DB.XYZ(q.X + h, q.Y + h, z)))
    it = X.item(v, v.CropBox, u'%s · %s' % (u'Planta', LVN[lv]), 'plan', LVN[lv], [e['code'] for e in els], [], [])
    return v, it, boxes

def table(doc, vname, title, els, extra=(), scale=100, chunk=16):
    """table split in columns of `chunk` lines (one drafting view each) so the sheet layout keeps the plans at their scale."""
    rows = [u'%s · %s · %s · %s · %s%s' % (e['code'], e['type'], e['room'], e['level'], e['mount'], u' · opc' if e['opt'] else u'') for e in els if e['kind'] != 'LZ']
    if any(e['kind'] == 'LZ' for e in els):
        rows += [u''] + [u'%s · %s · nivel %s' % (e['code'], e['room'], e.get('zone')) for e in els if e['kind'] == 'LZ']
    blocks = ([(title, rows or [u'(sin elementos)'])] if rows or not extra else []) + list(extra)
    cols = []; cur = []; n = 0
    for t, ls in blocks:
        for i in range(0, max(len(ls), 1), chunk):
            part = ls[i:i + chunk]
            if n + len(part) + 1 > chunk and cur: cols.append(cur); cur = []; n = 0
            cur.append((t if i == 0 else t + u' (cont.)', part)); n += len(part) + 1
    if cur: cols.append(cur)
    out = []
    for k, col in enumerate(cols):
        v = C.drafting(doc, vname + (u' %d' % (k + 1) if len(cols) > 1 else u''), scale)   # drafted at the sheet scale so the text spacing holds
        C.legend(doc, v, 0, 0, 0, col, [])
        out.append(C.item(doc, v, title + (u' (%d/%d)' % (k + 1, len(cols)) if len(cols) > 1 else u''), [], []))
    return None, out

def legend_blocks(pl):
    seen = []
    for e in pl['elements']:
        k = (e['system'], e['kind'], e['type'])
        if k not in seen: seen.append(k)
    sysn = {'IL': u'Iluminación', 'CR': u'Cortinas', 'CL': u'Climatización', 'CA': u'Cámaras', 'RD': u'Red y energía', 'AU': u'Audio', 'AC': u'Acceso', 'RG': u'Riego', 'SG': u'Seguridad'}
    shp = {'circle': u'círculo', 'circle2': u'círculo doble', 'square': u'cuadrado', 'rect': u'rectángulo', 'diamond': u'rombo', 'tri': u'triángulo + cono', 'bar': u'barra (ancho del vano)'}
    out = []
    for s_ in sysn:
        ls = [u'%s · %s · %s' % (k, t, shp.get(SHAPE.get(k), u'—') if k != 'LZ' else u'etiqueta de local') for (sy, k, t) in seen if sy == s_]
        if ls: out.append((sysn[s_] + u' (color propio)', ls))
    return out

def build(doc, ld, number, title, sysk, lvk, pl):
    els = [e for e in pl['elements'] if (sysk is None or e['system'] == sysk) and (lvk is None or e['level'] == lvk)]
    its = []; vb = []
    if lvk:
        v, it, bx = level_plan(doc, ld, pl, lvk, els, PRE + number + ' PLANTA', 50, True, False); its.append(it); vb.append((v, bx))
    else:
        for lv in ('PB', 'PA', 'PE'):
            v, it, bx = level_plan(doc, ld, pl, lv, [e for e in els if e['level'] == lv], PRE + number + ' ' + lv, 100, sysk == 'IL', sysk is None); its.append(it); vb.append((v, bx))
    SC = ([50, 75] if lvk == 'PE' else [75]) if lvk else [100, 125]
    if sysk is None:
        # DOM-00: plans only in the layout; legend and sheet list as text in a right-hand strip
        oldx = L.X1; L.X1 = L.X1 - .52
        old = list(L.SCALES); L.SCALES[:] = SC
        try: s = S.lay_sheet(doc, number, title, u'Etapa 2 · ubicación en planta · %d elementos (solo códigos; detalle en cada lámina)' % len([e for e in els if e['kind'] != 'LZ']), its, FOOT, rubro=RUBRO, sheet_name=u'Domótica · 00')
        finally: L.SCALES[:] = old; L.X1 = oldx
        sh = doc.GetElement(DB.ElementId(Int64(int(s['sheetId'])))); x = L.X1 - .50; y = L.TOP
        for t, ls in legend_blocks(pl) + [(u'Láminas', [u'%s  %s' % (n, t_) for n, t_, _, _ in SHEETS])]:
            L.tn(doc, sh.Id, DB.XYZ(x, y, 0), t, 'sub'); s['notes'].append({'text': t, 'anchor': [x, y]}); y -= .022
            L.tn(doc, sh.Id, DB.XYZ(x, y, 0), u'\n'.join(ls), 'text'); y -= .0125 * len(ls) + .02
    else:
        tv, tt = table(doc, PRE + number + ' CUADRO', u'Cuadro ' + number, els, (), max(SC)); its += tt
        old = list(L.SCALES); L.SCALES[:] = SC
        try: s = S.lay_sheet(doc, number, title, u'Etapa 2 · ubicación en planta · %d elementos' % len([e for e in els if e['kind'] != 'LZ']), its, FOOT, plan_region=bool(lvk), rubro=RUBRO, sheet_name=u'Domótica · ' + number[4:])
        finally: L.SCALES[:] = old
    doc.Regenerate()
    for (v, bx), meta in zip(vb, s['views']):
        meta['domElements'] = sheet_box(doc, v, meta, bx)
    return dict(s, kind='general', level=LVN.get(lvk, u'General') if lvk else u'General', sector=sysk or u'General', system=sysk)

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None and 'domotica' in doc.PathName.lower(), 'Abrir Casa-Angel-DOC-Domotica.rvt'
    part = job['part']; path = os.path.join(OUT, 'dom35-sheets.json')
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        rec = R1.read(path); done = []
        for sh in rec['sheets']:
            opts.FileName = 'r35-' + sh['number']; e = doc.GetElement(DB.ElementId(Int64(sh['sheetId'])))
            if e is None: done.append(sh['number'] + ' FALTA'); continue
            try: sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([e.Id]), opts)); done.append(sh['number'])
            except Exception as ex: done.append('%s ERROR %s %s' % (sh['number'], type(e).__name__, ex))
        R1.write(path, rec); return {'status': 'success', 'exported': done}
    prev = []
    if os.path.exists(path) and job.get('append'):   # build some sheets and keep the others (one call per sheet keeps each job short)
        prev = [x for x in R1.read(path)['sheets'] if x['number'] not in (job.get('only') or [])]
        old = [x for x in R1.read(path)['sheets'] if x['number'] in (job.get('only') or [])]
        def wipe1():
            for sh in old:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id)
        B.plain(doc, 'ADER DOM R35 - borrar ' + ','.join(job.get('only') or []), wipe1)
    elif os.path.exists(path):
        if not job.get('redo'): return {'status': 'success', 'existing': True}
        rec = R1.read(path)
        def wipe():
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id)
        B.plain(doc, 'ADER DOM R35 - borrar', wipe); os.remove(path)
    L.register_font()
    B.plain(doc, 'ADER DOM R35 - datos del proyecto', lambda: B.project_info(doc, ld))
    pl = plan(); only = job.get('only'); sheets = []
    for n, t, sk, lk in SHEETS:
        if only and n not in only: continue
        sh = B.plain(doc, 'ADER DOM R35 - ' + n, lambda: build(doc, ld, n, t, sk, lk, pl))
        for x in sh['views']: x.pop('view', None)
        sheets.append(sh)
    order = [n for n, _, _, _ in SHEETS]
    sheets = sorted(prev + sheets, key=lambda x: order.index(x['number']))
    R1.write(path, {'part': 'sheets', 'revision': 'R35', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'sheets': [(sh['number'], [x['scale'] for x in sh['views']]) for sh in sheets]}
