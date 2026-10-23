# -*- coding: utf-8 -*-
"""R16: Cubierta sheets (documentation only).
CUB-01 planta de techos · CUB-02 estructura de madera · CUB-03.. cortes · CUB-F-CU-nn fichas de techos · CUB-F-VC-nn fichas de vigas 6x20."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_roof', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_roof', os.path.join(ROOT, 'revit_fichas_r12.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
TOP_LEVEL, PE_LEVEL = 354178, 353988
RUBRO = u'CUBIERTA'
COL = {'CU': (176, 90, 40), 'VC': (120, 70, 20), 'VP': (150, 110, 60), 'CR': (190, 150, 90), 'FA': (40, 90, 160), 'CA': (40, 90, 160), 'AL': (90, 90, 90)}
FOOT = u'Cubierta: geometría nativa; cotas en metros ancladas a extremos (no asociativas). Códigos CU/VC/VP/CR/FA/CA/AL como anotación. Membrana, aislación, cumbreras y bajadas: no modelado / a definir.'

def plan_data(): return L.read('roof-plan')

def colorize(doc, v, e, kind):
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*COL.get(kind, (25, 98, 143)))
    ov.SetProjectionLineColor(c); ov.SetCutLineColor(c); ov.SetProjectionLineWeight(4); v.SetElementOverrides(e.Id, ov)

def top_plan(doc, elements, vname, pad=1.0, hide=None):
    """Plan from above the roofs (level 03 + 1.3 m) looking down to Entrepiso - 0.6 m."""
    level = el(doc, TOP_LEVEL); pe = el(doc, PE_LEVEL)
    depth = (pe.Elevation - level.Elevation) / (1 / M) * 1.0 - .6        # metres, negative
    v = S.new_plan(doc, level, S.bounds(elements, level.Elevation, pad / M), vname, depth=depth)
    if hide: v.HideElements(List[DB.ElementId]([x.Id for x in hide]))
    return v, level

def roof_rows(data, kinds): return [r for r in data['elements'] if r['kind'] in kinds]

def tag(doc, v, e, row, z):
    b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
    L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, z), row['label'], 'tag')

def extent_dims(doc, v, e, code):
    bb = e.get_BoundingBox(None)
    fx = L.AxisFrame(v, DB.XYZ(bb.Min.X, bb.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY)
    fy = L.AxisFrame(v, DB.XYZ(bb.Min.X, bb.Min.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    return [L.tick_dim(doc, fx, code + u' extensión X', [0, bb.Max.X - bb.Min.X], True, .5 / M), L.tick_dim(doc, fy, code + u' extensión Y', [0, bb.Max.Y - bb.Min.Y], True, .5 / M)]

def item(v, box, title, kind, sector, tags, dims, elements, data=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data}

def section_through(doc, c, right, half, z0, z1, vname):
    lev = el(doc, PE_LEVEL)
    v, bx = F.section(doc, DB.XYZ(c.X, c.Y, lev.Elevation), right, None, -half - .8 / M, half + .8 / M, (z0 - lev.Elevation) - .8 / M, (z1 - lev.Elevation) + .8 / M, vname)
    return v, bx

# ---------------------------------------------------------------- parts

def general_part(doc):
    data = plan_data(); sheets = []
    roofs = [(el(doc, r['id']), r) for r in roof_rows(data, ['CU', 'FA', 'CA', 'AL'])]
    v, level = top_plan(doc, [e for e, r in roofs], 'ADER CUB R16 - PLANTA DE TECHOS')
    dims = []
    for e, r in roofs:
        colorize(doc, v, e, r['kind']); tag(doc, v, e, r, level.Elevation)
        if r['kind'] == 'CU': dims += extent_dims(doc, v, e, r['code'])
    tot = sum(r['area_m2'] for e, r in roofs if r['kind'] == 'CU')
    it = item(v, v.CropBox, u'Planta de techos', 'plan', u'Cubierta', [r['code'] for e, r in roofs], dims, [eid(e) for e, r in roofs])
    sub = (u'Tejas: %.1f m² en 3 techos · fascias %.1f ml · canaletas %.1f ml' % (tot, sum(r['length_m'] for e, r in roofs if r['kind'] == 'FA'), sum(r['length_m'] for e, r in roofs if r['kind'] == 'CA'))).replace('.', ',')
    sheets.append(dict(S.lay_sheet(doc, 'CUB-01', u'Planta de techos', sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · 01'), kind='general', level=u'Cubierta', sector=u'Cubierta'))
    # timber structure, roofs hidden
    fr = [(el(doc, r['id']), r) for r in roof_rows(data, ['VC', 'VP', 'CR'])]
    roof_els = [e for e, r in roofs if r['kind'] == 'CU']
    v, level = top_plan(doc, [e for e, r in fr] + roof_els, 'ADER CUB R16 - ESTRUCTURA DE MADERA', hide=roof_els)
    for e, r in fr: colorize(doc, v, e, r['kind'])
    for e, r in fr:
        if r['kind'] == 'VC': tag(doc, v, e, r, level.Elevation)
    it = item(v, v.CropBox, u'Estructura de madera (vigas VC rotuladas; VP y CR en planilla)', 'plan', u'Cubierta', [r['code'] for e, r in fr], [], [eid(e) for e, r in fr])
    n = dict((k, [r for e, r in fr if r['kind'] == k]) for k in ['VC', 'VP', 'CR'])
    sub = (u'VC 6×20: %d u. %.1f ml · VP 3×10: %d u. %.1f ml · CR 1,5×5: %d u. %.1f ml' % (len(n['VC']), sum(r['length_m'] for r in n['VC']), len(n['VP']), sum(r['length_m'] for r in n['VP']), len(n['CR']), sum(r['length_m'] for r in n['CR']))).replace('.', ',')
    sheets.append(dict(S.lay_sheet(doc, 'CUB-02', u'Estructura de madera', sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · 02'), kind='general', level=u'Cubierta', sector=u'Cubierta'))
    # sections: two per main roof
    items = []
    for e, r in roofs:
        if r['kind'] != 'CU' or r['area_m2'] < 50: continue
        b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
        for axis, right, half in [('X', DB.XYZ.BasisX, (b.Max.X - b.Min.X) / 2), ('Y', DB.XYZ.BasisY, (b.Max.Y - b.Min.Y) / 2)]:
            vs, bx = section_through(doc, c, right, half, b.Min.Z, b.Max.Z, 'ADER CUB R16 - ' + r['code'] + ' - CORTE ' + axis)
            colorize(doc, vs, e, 'CU'); doc.Regenerate()
            f = L.Frame(vs); xs = sorted([f.x(c - right * half), f.x(c + right * half)]); yb = b.Min.Z - f.o.Z; yt = b.Max.Z - f.o.Z
            ds = [L.tick_dim(doc, f, r['code'] + u' ancho ' + axis, xs, True, yt + .4 / M), L.tick_dim(doc, f, r['code'] + u' altura', [yb, yt], False, xs[1] + .5 / M)]
            L.tn(doc, vs.Id, f.p(xs[0], yt + .9 / M), r['label'], 'tag'); L.tn(doc, vs.Id, L.crop_corner(vs, .06 / M, .06 / M), u'Cubierta · ' + r['code'], 'room')
            items.append(item(vs, bx, r['code'] + u' · corte ' + axis, 'section', u'Cubierta', [r['code']], ds, [eid(e)]))
    for k in range(0, len(items), 2):
        ch = items[k:k + 2]; n_ = k // 2 + 3
        sheets.append(dict(S.lay_sheet(doc, 'CUB-%02d' % n_, u'Cortes de cubierta · ' + ch[0]['tags'][0], u'Alturas y anchos de techo; pendientes en la ficha del techo.', ch, FOOT, rubro=RUBRO, sheet_name=u'Cubierta · %02d' % n_), kind='general', level=u'Cubierta', sector=u'Cubierta'))
    return sheets

def roof_ficha(doc, r, data):
    e = el(doc, r['id']); b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
    v, level = top_plan(doc, [e], 'ADER CUB R16 - ' + r['code'] + ' - PLANTA', pad=.8)
    colorize(doc, v, e, 'CU'); tag(doc, v, e, r, level.Elevation)
    dims = extent_dims(doc, v, e, r['code'])
    sector = u'Cubierta · ' + u(r.get('level', u''))
    fr = [x for x in data['elements'] if x.get('roof') == r['code'] and x['kind'] in ('VC', 'VP', 'CR')]
    c2 = lambda x: (u'%.2f' % x).replace(u'.', u',')
    lines = [r['label'], u'Aguas: ' + u'; '.join(c2(a['area_m2']) + u' m² a ' + (u'%.1f' % a['slope_deg']).replace('.', ',') + u'°' for a in r['aguas']),
             u'Madera bajo este techo: ' + u' · '.join(k + u' ' + str(len([x for x in fr if x['kind'] == k])) + u' u. ' + c2(sum(x['length_m'] or 0 for x in fr if x['kind'] == k)) + u' ml' for k in ['VC', 'VP', 'CR']),
             u'Membrana / aislación: no modeladas (a definir).']
    items = [item(v, v.CropBox, r['code'] + u' · planta', 'plan', sector, [r['code']], dims, [eid(e)], lines)]
    for axis, right, half in [('A', DB.XYZ.BasisX, (b.Max.X - b.Min.X) / 2), ('B', DB.XYZ.BasisY, (b.Max.Y - b.Min.Y) / 2)]:
        vs, bx = section_through(doc, c, right, half, b.Min.Z, b.Max.Z, 'ADER CUB R16 - ' + r['code'] + ' - CORTE ' + axis)
        colorize(doc, vs, e, 'CU'); doc.Regenerate()
        f = L.Frame(vs); xs = sorted([f.x(c - right * half), f.x(c + right * half)]); yb = b.Min.Z - f.o.Z; yt = b.Max.Z - f.o.Z
        ds = [L.tick_dim(doc, f, r['code'] + u' ancho corte ' + axis, xs, True, yt + .4 / M), L.tick_dim(doc, f, r['code'] + u' altura', [yb, yt], False, xs[1] + .5 / M)]
        L.tn(doc, vs.Id, f.p(xs[0], yt + .9 / M), r['code'] + u' · corte ' + axis, 'tag'); L.tn(doc, vs.Id, L.crop_corner(vs, .06 / M, .06 / M), sector, 'room')
        items.append(item(vs, bx, r['code'] + u' · corte ' + axis, 'section', sector, [r['code']], ds, [eid(e)]))
    ax = F.axo(doc, e, r['code'], r['label'], sector); ax['title'] = r['code'] + u' · axonométrica'
    items.append(ax)
    sheet = S.lay_sheet(doc, 'CUB-F-' + r['code'], u'Ficha ' + r['code'], r['label'], items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Cubierta · ' + r['code'])
    sheet.update(kind='element', element=r['code'], elementId=str(r['id']), elementKind='CU', level=u'Cubierta', sector=sector)
    return sheet

def beam_ficha(doc, r):
    e = el(doc, r['id']); c_ = e.Location.Curve; a = c_.GetEndPoint(0); b = c_.GetEndPoint(1)
    d = DB.XYZ(b.X - a.X, b.Y - a.Y, 0); d = d.Normalize() if d.GetLength() > 1e-6 else DB.XYZ.BasisX; n = DB.XYZ(-d.Y, d.X, 0)
    sector = u'Cubierta · ' + (r.get('roof') or u'') + u' · ' + u(r.get('level', u''))
    v, level = top_plan(doc, [e], 'ADER CUB R16 - ' + r['code'] + ' - PLANTA', pad=.8)
    colorize(doc, v, e, 'VC'); tag(doc, v, e, r, level.Elevation)
    f = L.AxisFrame(v, DB.XYZ(a.X, a.Y, v.Origin.Z), d, n)
    dims = [L.tick_dim(doc, f, r['code'] + u' largo en planta', [0, DB.XYZ(b.X - a.X, b.Y - a.Y, 0).GetLength()], True, .35 / M, tick=.06 / M)]
    lines = [r['label'], u(r['status']), u'Largo real ' + (u'%.2f' % (r['length_m'] or 0)).replace('.', ',') + u' m · sección 6 × 20 cm · ' + (u'%.3f' % (r['volume_m3'] or 0)).replace('.', ',') + u' m³ madera']
    items = [item(v, v.CropBox, r['code'] + u' · planta', 'plan', sector, [r['code']], dims, [eid(e)], lines)]
    bb = e.get_BoundingBox(None); mid = (a + b) * .5; L2 = c_.Length / 2
    ve, bx = section_through(doc, mid, d, DB.XYZ(b.X - a.X, b.Y - a.Y, 0).GetLength() / 2, bb.Min.Z, bb.Max.Z, 'ADER CUB R16 - ' + r['code'] + ' - VISTA')
    colorize(doc, ve, e, 'VC'); doc.Regenerate()
    fe = L.Frame(ve); xs = sorted([fe.x(a), fe.x(b)]); ys = sorted([a.Z - fe.o.Z, b.Z - fe.o.Z])
    ds = [L.tick_dim(doc, fe, r['code'] + u' proyección horizontal', xs, True, bb.Max.Z - fe.o.Z + .3 / M)]
    if ys[1] - ys[0] > .01: ds.append(L.tick_dim(doc, fe, r['code'] + u' desnivel', ys, False, xs[1] + .4 / M))
    L.tn(doc, ve.Id, fe.p(xs[0], bb.Max.Z - fe.o.Z + .7 / M), r['label'], 'tag')
    items.append(item(ve, bx, r['code'] + u' · vista', 'elevation', sector, [r['code']], ds, [eid(e)]))
    vs, bx2 = section_through(doc, mid, n, .4 / M, bb.Min.Z, bb.Max.Z, 'ADER CUB R16 - ' + r['code'] + ' - CORTE')
    colorize(doc, vs, e, 'VC'); doc.Regenerate()
    fs = L.Frame(vs); w = .06 / M; zc = mid.Z - fs.o.Z; xc = fs.x(mid)
    ds2 = [L.tick_dim(doc, fs, r['code'] + u' ancho sección', [xc - w / 2, xc + w / 2], True, zc + .35 / M, tick=.04 / M),
           L.tick_dim(doc, fs, r['code'] + u' alto sección', [zc - .1 / M, zc + .1 / M], False, xc + .3 / M, tick=.04 / M)]
    L.tn(doc, vs.Id, fs.p(xc - .3 / M, zc + .55 / M), r['code'] + u' · 6 × 20', 'tag')
    items.append(item(vs, bx2, r['code'] + u' · corte', 'section', sector, [r['code']], ds2, [eid(e)]))
    ax = F.axo(doc, e, r['code'], r['label'], sector); ax['title'] = r['code'] + u' · axonométrica'
    items.append(ax)
    sheet = S.lay_sheet(doc, 'CUB-F-' + r['code'], u'Ficha ' + r['code'], r['label'] + u' · Madera Kerto LVL', items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Cubierta · ' + r['code'])
    sheet.update(kind='element', element=r['code'], elementId=str(r['id']), elementKind='VC', level=u'Cubierta', sector=sector)
    return sheet

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CUB-00'; sheet.Name = u'Cubierta · índice'
    head = u'CASA ÁNGEL · CUBIERTA · ÍNDICE, CRITERIOS Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        x = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(x, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [x, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(x, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CUB-00', 'title': u'Índice, criterios y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Cubierta', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'cub-' + part + '.json')
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('cub-') and fn.endswith('.json')): continue
            rec = L.R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r16-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            L.R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    data = plan_data()
    def body():
        if part == 'general': return general_part(doc)
        if part == 'roofs': return [roof_ficha(doc, r, data) for r in roof_rows(data, ['CU'])]
        if part.startswith('vc'): return [beam_ficha(doc, r) for r in roof_rows(data, ['VC']) if r['code'] in job['codes']]
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER CUB R16 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    L.R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
