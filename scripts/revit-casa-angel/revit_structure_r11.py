# -*- coding: utf-8 -*-
"""R11: structure sheets EST-00 / EST-<nivel>-01 / EST-FU-01 / EST-SEC-* / EST-REV-*.
Documentation only (views, sheets, viewports, dimensions on detail-line anchors, text notes).
Codes MH-/VE-/LO-/PL- are written only as annotations; no element parameter is modified."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_est', os.path.join(ROOT, 'revit_openings_r4.py'))
OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
LEVEL_NAMES = {311: u'00. Planta Baja', 694: u'01. Planta Alta', 353988: u'02. Planta Entrepiso'}
LEVEL_CODE = {311: 'PB', 694: 'PA', 353988: 'PE'}

def plan_data():
    return L.read('structure-plan')

def vptype(doc):
    return next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ElementType) if name(t) == 'ADER ABR - viewport')

def colorize(doc, v, e, rgb):
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb)
    ov.SetProjectionLineColor(c); ov.SetCutLineColor(c); ov.SetProjectionLineWeight(4); ov.SetCutLineWeight(5)
    v.SetElementOverrides(e.Id, ov)
COLORS = {'MH': (25, 98, 143), 'VE': (196, 98, 16), 'LO': (90, 140, 60), 'PL': (90, 140, 60)}

def show_grids(v):
    for c in [DB.BuiltInCategory.OST_Grids]:
        try: v.SetCategoryHidden(DB.ElementId(c), False)
        except: pass

def new_plan(doc, level, bx, vname, depth=-.3):
    v = DB.ViewPlan.Create(doc, DB.ElementId(Int64(L.PLAN_VFT)), level.Id); L.setup_view(doc, v)
    v.Name = vname; v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False
    # Annotation crop on: labels of rooms outside the crop must not enlarge the viewport.
    v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)
    mgr = v.GetCropRegionShapeManager()
    for prop in ['TopAnnotationCropOffset', 'BottomAnnotationCropOffset', 'LeftAnnotationCropOffset', 'RightAnnotationCropOffset']:
        try: setattr(mgr, prop, .01)
        except Exception: pass
    vr = v.GetViewRange()
    vr.SetLevelId(DB.PlanViewPlane.CutPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.CutPlane, 1.30 / M)
    vr.SetLevelId(DB.PlanViewPlane.TopClipPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.TopClipPlane, 4.0 / M)
    vr.SetLevelId(DB.PlanViewPlane.BottomClipPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, depth / M)
    vr.SetLevelId(DB.PlanViewPlane.ViewDepthPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, depth / M)
    v.SetViewRange(vr)
    return v

def bounds(elements, z, pad):
    pts = []
    for e in elements:
        b = e.get_BoundingBox(None)
        if b: pts += [b.Min, b.Max]
    bx = DB.BoundingBoxXYZ()
    bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, z - 3)
    bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, z + 12)
    return bx

def wall_axis(e):
    c = e.Location.Curve; a = c.GetEndPoint(0); b = c.GetEndPoint(1)
    d = DB.XYZ(b.X - a.X, b.Y - a.Y, 0).Normalize(); n = DB.XYZ(-d.Y, d.X, 0)
    return a, b, d, n

def tag_plan(doc, v, e, row, z, centre=None):
    if isinstance(e, DB.Wall):
        a, b, d, n = wall_axis(e); mid = (a + b) * .5
        if centre is not None and n.DotProduct(DB.XYZ(centre.X - mid.X, centre.Y - mid.Y, 0)) < 0: n = -n   # tag towards the building
        p = DB.XYZ(mid.X, mid.Y, z) + n * (.35 / M) - d * (.6 / M)
        if n.X < -.5: p = p - DB.XYZ.BasisX * (len(row['label']) * .13 / M)   # text grows to +X: keep it inside
        L.tn(doc, v.Id, p, row['label'], 'tag')
        f = L.AxisFrame(v, DB.XYZ(a.X, a.Y, v.Origin.Z), d, -n)
        return [L.tick_dim(doc, f, row['code'] + u' largo', [0, a.DistanceTo(b)], True, .35 / M, tick=.08 / M)]
    bb = e.get_BoundingBox(None); c = (bb.Min + bb.Max) * .5
    L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, z), row['label'], 'tag')
    return []

def room_labels(doc, v, level_id, z):
    for r in L.read('plan')['rooms']:
        if r['level'] != level_id or not r['id']: continue
        room = el(doc, r['id'])
        if room is not None and isinstance(room.Location, DB.LocationPoint):
            p = room.Location.Point; L.tn(doc, v.Id, DB.XYZ(p.X, p.Y, z), L.room_label(r), 'room')

def make_section(doc, e, vname):
    bx, vd = L.elevation_box(doc, e, None)
    v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(L.SECTION_VFT)), bx)
    if v.ViewDirection.DotProduct(vd) < 0:
        doc.Delete(v.Id)
        t = bx.Transform; t2 = DB.Transform.Identity; t2.Origin = t.Origin; t2.BasisX = -t.BasisX; t2.BasisY = t.BasisY; t2.BasisZ = -t.BasisZ
        b2 = DB.BoundingBoxXYZ(); b2.Transform = t2; b2.Min = DB.XYZ(-bx.Max.X, bx.Min.Y, -bx.Max.Z); b2.Max = DB.XYZ(-bx.Min.X, bx.Max.Y, -bx.Min.Z)
        v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(L.SECTION_VFT)), b2); bx = b2
    L.setup_view(doc, v, levels=True); v.Name = vname; v.CropBoxVisible = False
    try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
    except: pass
    others = [l.Id for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if l.Id != e.LevelId]
    if others: v.HideElements(List[DB.ElementId](others))
    return v, bx

def wall_elevation(doc, e, row, open_codes, vname=None):
    v, bx = make_section(doc, e, vname or ('ADER EST R11 - ' + row['code'] + ' - ALZADO'))
    colorize(doc, v, e, COLORS[row['kind']])
    doc.Regenerate()
    f = L.Frame(v); lev = L.level_of(doc, e)
    a, b, z0, z1, _ = L.extents(doc, e)
    xs = sorted([f.x(a), f.x(b)]); ylev = lev.Elevation - f.o.Z; yt = z1 - f.o.Z; yb = z0 - f.o.Z
    dims = []; tags = [row['code']]; elems = [eid(e)]
    edges = []
    for iid in e.FindInserts(True, False, True, True):
        ins = doc.GetElement(iid)
        if ins is None or ins.get_BoundingBox(None) is None: continue
        try: ia, ib, iz0, iz1, _ = L.extents(doc, ins)
        except Exception: continue
        x0, x1 = sorted([f.x(ia), f.x(ib)])
        if x1 < xs[0] or x0 > xs[1]: continue
        edges += [max(xs[0], x0), min(xs[1], x1)]
        code = open_codes.get(eid(ins))
        if code:
            tags.append(code); elems.append(eid(ins))
            L.tn(doc, v.Id, f.p((x0 + x1) / 2 - .15 / M, (iz0 + iz1) / 2 - f.o.Z), code, 'tag')
    if edges: dims.append(L.tick_dim(doc, f, row['code'] + u' vanos', L.uniq(xs + edges), True, yt + .25 / M))
    dims.append(L.tick_dim(doc, f, row['code'] + u' largo', xs, True, yt + (.5 if edges else .25) / M))
    dims.append(L.tick_dim(doc, f, row['code'] + u' arranque + alto', L.uniq([ylev, yb, yt], tol=.005 / M), False, xs[1] + .35 / M))
    L.tn(doc, v.Id, f.p((xs[0] + xs[1]) / 2 - .5 / M, (yb + yt) / 2), row['label'], 'tag')
    L.tn(doc, v.Id, L.crop_corner(v, .06 / M, .06 / M), u'Sector: ' + LEVEL_NAMES.get(row['sheetLevel'], u(row['level'])), 'room')
    return {'view': v, 'box': bx, 'title': row['code'] + u' · alzado', 'kind': 'elevation', 'sector': LEVEL_NAMES.get(row['sheetLevel'], u(row['level'])),
            'tags': tags, 'dims': dims, 'elements': elems, 'data': [row['label'], row['status']]}

# ---------------------------------------------------------------- sheet layout

def lay_sheet(doc, number, title, sub, items, foot, plan_region=False, rubro=u'ESTRUCTURA', sheet_name=None):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = number; sheet.Name = sheet_name or (u'Estructura · ' + number[4:])
    head = u'CASA ÁNGEL · ' + rubro + u' · ' + u(title).upper()
    notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title')
    single = len(items) == 1
    if sub:   # single-drawing sheets: subtitle goes to the footer so the drawing can use the full height
        sy = L.Y0 + .095 if single else L.Y1 - .075
        L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, sy, 0), sub, 'sub'); notes.append({'text': sub, 'anchor': [L.X0 + .01, sy]})
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), foot, 'text'); notes.append({'text': foot, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    vpt = vptype(doc); views = []
    if len(items) == 1:
        it = items[0]; v = it['view']
        top = L.Y1 - .095; bot = L.Y0 + .11
        aw = L.X1 - L.X0 - .02; ah = top - bot
        vp = DB.Viewport.Create(doc, sheet.Id, v.Id, DB.XYZ((L.X0 + L.X1) / 2, (L.TOP + L.BOTTOM) / 2, 0)); vp.ChangeTypeId(vpt.Id)
        for s in L.SCALES:          # measure the real viewport (grid heads included) instead of the crop
            v.Scale = s; doc.Regenerate(); o = vp.GetBoxOutline(); d = o.MaximumPoint - o.MinimumPoint
            if d.X <= aw and d.Y <= ah: break
        vp.SetBoxCenter(DB.XYZ((L.X0 + L.X1) / 2, (bot + top) / 2, 0)); doc.Regenerate(); o = vp.GetBoxOutline()
        label = u(it['title']) + u'   1:' + str(v.Scale); anchor = [o.MinimumPoint.X, o.MaximumPoint.Y + .045]
        L.tn(doc, sheet.Id, DB.XYZ(anchor[0], anchor[1], 0), label, 'sub')
        meta = {'id': eid(v), 'name': u(it['title']), 'label': label, 'scale': v.Scale, 'anchor': anchor, 'box': [xyz(o.MinimumPoint), xyz(o.MaximumPoint)]}
        meta.update(kind=it['kind'], sector=it['sector'], tags=it['tags'], dims=it['dims'], elements=it['elements']); views.append(meta)
    else:
        sizes = [L.sheet_size(it['box'], 1) for it in items]
        if plan_region:   # first item (plan) gets its own column/band; the others are packed in the rest
            lay = L.choose_layout(sizes[0], sizes[1:])
            cell, ps = lay['plan']; it0 = items[0]
            vp, meta = L.place(doc, sheet, it0['view'], ps, cell, it0['title'], vpt)
            meta.update(kind=it0['kind'], sector=it0['sector'], tags=it0['tags'], dims=it0['dims'], elements=it0['elements'])
            if it0.get('data'):
                o = vp.GetBoxOutline(); L.tn(doc, sheet.Id, DB.XYZ(o.MinimumPoint.X, o.MinimumPoint.Y - .012, 0), u'\n'.join(it0['data']), 'text')
            views.append(meta); items = items[1:]; sizes = sizes[1:]
        else:
            lay = L.choose_layout(None, sizes)
        if not lay['rows']:   # very large context crops: allow coarser scales instead of failing
            for extra in [300, 400, 500, 750, 1000]:
                if extra not in L.SCALES: L.SCALES.append(extra)
            lay = L.choose_layout(None, sizes)
        cost, picks = lay['rows']; rx0, ry0, rx1, ry1 = lay['region']
        slack_y = ((ry1 - ry0) - sum(hh for r, sc, hh in picks)) / len(picks); ytop = ry1
        for r, sc, hh in picks:
            hh2 = hh + slack_y
            widths = [max(sizes[j][0] / sc, L.MIN_W) + L.GAP for j in r]
            slack_x = ((rx1 - rx0) - sum(widths)) / len(r); x = rx0
            for j, w in zip(r, widths):
                it = items[j]; cell = (x, ytop - hh2, x + w + slack_x, ytop); x += w + slack_x
                vp, meta = L.place(doc, sheet, it['view'], sc, cell, it['title'], vpt)
                meta.update(kind=it['kind'], sector=it['sector'], tags=it['tags'], dims=it['dims'], elements=it['elements'])
                if it.get('data'):
                    o = vp.GetBoxOutline(); L.tn(doc, sheet.Id, DB.XYZ(o.MinimumPoint.X, o.MinimumPoint.Y - .012, 0), u'\n'.join(it['data']), 'text')
                views.append(meta)
            ytop -= hh2
    return {'sheetId': eid(sheet), 'number': number, 'title': u(title), 'views': views, 'notes': notes}

FOOT = u'Estructura: documentación sobre geometría nativa. Códigos MH/VE/LO/PL solo como anotación (no se escribieron en el modelo). Cotas en metros; largos y vanos anclados a extremos (no asociativos). Losas L01.00 de PA/PE: a confirmar.'

def dims_out(dims):
    return [{'label': d['label'], 'values_m': [round(x, 4) for x in d.get('values_m', [])], 'associative': d.get('associative')} for d in dims]

# ---------------------------------------------------------------- jobs

def plans_part(doc):
    data = plan_data(); sheets = []
    for lid in [311, 694, 353988]:
        rows = [r for r in data['elements'] if r['sheetLevel'] == lid and r['kind'] != 'PL']
        elements = [(el(doc, r['id']), r) for r in rows]; elements = [(e, r) for e, r in elements if e is not None]
        level = el(doc, lid); z = level.Elevation
        bx = bounds([e for e, r in elements if r['kind'] in ('MH', 'VE')], z, .6 / M)
        def inside(e):
            b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
            return bx.Min.X < c.X < bx.Max.X and bx.Min.Y < c.Y < bx.Max.Y
        outside = [r['code'] for e, r in elements if not inside(e)]
        elements = [(e, r) for e, r in elements if inside(e)]
        v = new_plan(doc, level, bx, 'ADER EST R11 - ' + LEVEL_CODE[lid] + ' - PLANTA')
        dims = []
        centre = (bx.Min + bx.Max) * .5
        for e, r in elements:
            colorize(doc, v, e, COLORS[r['kind']]); dims += tag_plan(doc, v, e, r, z, centre)
        room_labels(doc, v, lid, z)
        item = {'view': v, 'box': v.CropBox, 'title': u'Planta de estructura · ' + LEVEL_NAMES[lid], 'kind': 'plan', 'sector': LEVEL_NAMES[lid],
                'tags': [r['code'] for e, r in elements], 'dims': dims_out(dims), 'elements': [eid(e) for e, r in elements]}
        mh = [r for e, r in elements if r['kind'] == 'MH']
        sub = u'%d muros MH · %.2f m³ · %d losas/paquetes · %d encadenados' % (len(mh), sum(r['volume_m3'] or 0 for r in mh), len([1 for e, r in elements if r['kind'] == 'LO']), len([1 for e, r in elements if r['kind'] == 'VE']))
        if outside: sub += u' · fuera del recorte (exterior): ' + u', '.join(outside)
        sheets.append(dict(lay_sheet(doc, 'EST-' + LEVEL_CODE[lid] + '-01', u'Planta de estructura · ' + LEVEL_NAMES[lid], sub.replace('.', ','), [item], FOOT), level=LEVEL_NAMES[lid], sector=LEVEL_NAMES[lid], outside=outside))
    # foundation
    row = next(r for r in data['elements'] if r['kind'] == 'PL'); e = el(doc, row['id']); level = el(doc, 311)
    v = new_plan(doc, level, bounds([e], level.Elevation, .5 / M), 'ADER EST R11 - FU - PLATEA', depth=-1.0)
    colorize(doc, v, e, COLORS['PL'])
    others = [f.Id for f in DB.FilteredElementCollector(doc, v.Id).OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsNotElementType() if f.Id != e.Id]
    if others: v.HideElements(List[DB.ElementId](others))
    bb = e.get_BoundingBox(None); c = (bb.Min + bb.Max) * .5
    L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, level.Elevation), row['label'], 'tag')
    fx = L.AxisFrame(v, DB.XYZ(bb.Min.X, bb.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY)
    fy = L.AxisFrame(v, DB.XYZ(bb.Min.X, bb.Min.Y, v.Origin.Z), DB.XYZ.BasisY, DB.XYZ.BasisX * -1)
    dims = [L.tick_dim(doc, fx, u'PL-01 extensión X', [0, bb.Max.X - bb.Min.X], True, .5 / M), L.tick_dim(doc, fy, u'PL-01 extensión Y', [0, bb.Max.Y - bb.Min.Y], True, .5 / M)]
    room_labels(doc, v, 311, level.Elevation)
    item = {'view': v, 'box': v.CropBox, 'title': u'Platea de fundación PL-01', 'kind': 'plan', 'sector': u'Fundación · 00. Planta Baja',
            'tags': ['PL-01'], 'dims': dims_out(dims), 'elements': [eid(e)]}
    sheets.append(dict(lay_sheet(doc, 'EST-FU-01', u'Fundación · platea PB', row['label'] + u' · resto de fundaciones: no modelado / a definir', [item], FOOT), level=u'00. Planta Baja', sector=u'Fundación'))
    return sheets

def sections_part(doc, lid):
    data = plan_data(); opens = dict((i['id'], i['code']) for i in L.read('plan')['items'])
    rows = [r for r in data['elements'] if r['sheetLevel'] == lid and r['kind'] in ('MH', 'VE')]
    items = [wall_elevation(doc, el(doc, r['id']), r, opens) for r in rows if el(doc, r['id']) is not None]
    for it in items: it['dims'] = dims_out(it['dims'])
    doc.Regenerate()
    n = len(items); npages = int(math.ceil(n / 6.))
    while True:
        size = int(math.ceil(float(n) / npages)); chunks = [items[i:i + size] for i in range(0, n, size)]
        ok = all(L.layout_ok(L.choose_layout(None, [L.sheet_size(it['box'], 1) for it in c]), ['curtain'] * len(c)) for c in chunks)
        if ok or size == 1: break
        npages += 1
    sheets = []
    for k, c in enumerate(chunks, 1):
        number = 'EST-SEC-' + LEVEL_CODE[lid] + '-%02d' % k
        sub = u'Alzados de muros y encadenados · ' + u', '.join(it['tags'][0] for it in c)
        sheets.append(dict(lay_sheet(doc, number, u'Alzados · ' + LEVEL_NAMES[lid] + u' · %d/%d' % (k, len(chunks)), sub, c, FOOT), level=LEVEL_NAMES[lid], sector=LEVEL_NAMES[lid]))
    return sheets

def review_part(doc):
    data = plan_data(); code_of = dict((r['id'], r['code']) for r in data['elements'])
    opens = dict((i['id'], i['code']) for i in L.read('plan')['items'])
    items = []
    for c in data['cases']:
        els = [el(doc, i) for i in c['elementIds']]; els = [e for e in els if e is not None and e.get_BoundingBox(None)]
        if els:
            b0 = els[0].get_BoundingBox(None); c0 = (b0.Min + b0.Max) * .5
            near = [e for e in els if ((e.get_BoundingBox(None).Min + e.get_BoundingBox(None).Max) * .5).DistanceTo(c0) < 20 / M]
            els = near or els[:1]
        if not els: continue
        lid = next((int(e.LevelId.Value) for e in els if int(e.LevelId.Value) in LEVEL_NAMES), 311); level = el(doc, lid)
        v = new_plan(doc, level, bounds(els, level.Elevation, 1.5 / M), 'ADER EST R11 - REV %02d' % c['n'])
        tags = []
        for e in els:
            cd = code_of.get(eid(e)) or opens.get(eid(e)) or (u'Elem. ' + str(eid(e)))
            colorize(doc, v, e, (200, 40, 40)); tags.append(cd)
            bb = e.get_BoundingBox(None); m = (bb.Min + bb.Max) * .5
            L.tn(doc, v.Id, DB.XYZ(m.X, m.Y, level.Elevation), cd, 'tag')
        room_labels(doc, v, lid, level.Elevation)
        obs = u(c['observation']); prop = u(c['proposedCorrection'])
        items.append({'view': v, 'box': v.CropBox, 'title': u'Caso %02d · ' % c['n'] + u(c['title'])[:48], 'kind': 'review', 'sector': LEVEL_NAMES[lid],
                      'tags': tags, 'dims': [], 'elements': [eid(e) for e in els], 'caseId': c['id'],
                      'data': [u'Observación: ' + (obs[:110] + (u'…' if len(obs) > 110 else u'')), u'Propuesta: ' + (prop[:110] + (u'…' if len(prop) > 110 else u'')), u'Sin corrección geométrica (pendiente de aprobación).']})
    sheets = []; per = 4
    chunks = [items[i:i + per] for i in range(0, len(items), per)]
    for k, ch in enumerate(chunks, 1):
        sheets.append(dict(lay_sheet(doc, 'EST-REV-%02d' % k, u'Casos de revisión · %d/%d' % (k, len(chunks)), u', '.join(it['title'].split(u' · ')[0] for it in ch), ch, FOOT), level=None, sector=u'Revisión'))
        for meta, it in zip(sheets[-1]['views'], ch): meta['caseId'] = it['caseId']
    return sheets

def index_part(doc, job):
    lines = job['lines']
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'EST-00'; sheet.Name = u'Estructura · índice'
    head = u'CASA ÁNGEL · ESTRUCTURA · ÍNDICE, CRITERIOS Y CÓMPUTO DE HORMIGÓN'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title')
    notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    cols = job['columns']
    for k, col in enumerate(cols):
        x = L.X0 + .01 + k * (L.X1 - L.X0) / len(cols)
        L.tn(doc, sheet.Id, DB.XYZ(x, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [x, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(x, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'EST-00', 'title': u'Índice, criterios y cómputo', 'views': [], 'notes': notes, 'level': None, 'sector': u'General'}]

def reset_part(doc, target):
    path = os.path.join(OUT, 'est-' + target + '.json'); rec = L.R1.read(path)
    ids = [s['sheetId'] for s in rec['sheets']] + [v['id'] for s in rec['sheets'] for v in s['views']]
    def body():
        for i in ids:
            e = el(doc, i)
            if e is not None and (isinstance(e, DB.ViewSheet) and e.SheetNumber.startswith('EST-') or isinstance(e, DB.View) and name(e).startswith('ADER EST R11')): doc.Delete(e.Id)
        return len(ids)
    n, checked = L.guarded(doc, 'ADER EST R11 - reset ' + target, body)
    os.rename(path, path + '.reset'); doc.Save()
    return {'status': 'success', 'deleted': n}

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'est-' + part + '.json')
    if part == 'reset': return reset_part(doc, job['target'])
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('est-') and fn.endswith('.json')): continue
            rec = L.R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r11-' + s['number']
                s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            L.R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    def body():
        if part == 'plans': return plans_part(doc)
        if part.startswith('sec-'): return sections_part(doc, int(part[4:]))
        if part == 'review': return review_part(doc)
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER EST R11 - ' + part, body)
    for s in sheets:
        for v in s['views']:
            v.pop('view', None)
    L.R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
