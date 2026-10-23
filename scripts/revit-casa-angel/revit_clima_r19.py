# -*- coding: utf-8 -*-
"""R19: Climatización (piso radiante) sheets, documentation only.
CLI-PB/PA/PE-01 plantas de serpentines por local · CLI-F-CI-* fichas por circuito/local · CLI-F-CO-N/S fichas de colectores · CLI-00 índice."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_clima', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_clima', os.path.join(ROOT, 'revit_fichas_r12.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
RUBRO = u'CLIMATIZACIÓN'
LEVELS = [(311, 'PB', u'00. Planta Baja'), (694, 'PA', u'01. Planta Alta'), (353988, 'PE', u'02. Planta Entrepiso')]
PAL = [(214, 60, 40), (30, 110, 190), (40, 150, 80), (170, 70, 170), (220, 140, 20), (20, 150, 160), (120, 90, 50), (200, 60, 120)]
FOOT = u'Climatización: piso radiante con serpentines PEX Ø20 (mando + retorno) según el modelo. Longitudes por local tomadas en el nivel de cada tramo. Bomba de calor, circuitos por salida de colector y sistemas de retorno: no modelado / a definir.'

def data(): return L.read('hvac-plan')

def color(doc, v, ids, rgb, w=3):
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb); ov.SetProjectionLineColor(c); ov.SetProjectionLineWeight(w); ov.SetCutLineColor(c)
    for i in ids:
        e = el(doc, i)
        if e is not None: v.SetElementOverrides(e.Id, ov)

def hvac_view(doc, v):
    for c in [DB.BuiltInCategory.OST_Floors, DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel]:
        try: v.SetCategoryHidden(DB.ElementId(c), True)
        except: pass
    for c in [DB.BuiltInCategory.OST_PipeCurves, DB.BuiltInCategory.OST_PipeFitting, DB.BuiltInCategory.OST_PipeAccessory, DB.BuiltInCategory.OST_MechanicalEquipment]:
        try: v.SetCategoryHidden(DB.ElementId(c), False)
        except: pass

def item(v, box, title, kind, sector, tags, dims, elements, data_=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data_}

def room_point(doc, rid):
    r = el(doc, rid)
    return r.Location.Point if r is not None and isinstance(r.Location, DB.LocationPoint) else None

def plans_part(doc, d):
    sheets = []
    for lid, lc, ln in LEVELS:
        level = el(doc, lid); cs = [x for x in d['elements'] if x['kind'] == 'CI' and x['levelCode'] == lc]
        rooms = [el(doc, x['roomId']) for x in cs]
        acc = [x for x in d['elements'] if x['kind'] in ('CO', 'GA', 'TE') and el(doc, x['id']) is not None and -.3 / M < el(doc, x['id']).get_BoundingBox(None).Min.Z - level.Elevation < 2.8 / M]
        v = S.new_plan(doc, level, S.bounds([r for r in rooms if r is not None], level.Elevation, .8 / M), 'ADER CLI R19 - ' + lc + ' - PLANTA', depth=-.6)
        hvac_view(doc, v)
        for k, x in enumerate(cs):
            color(doc, v, x['pipeIds'], PAL[k % len(PAL)])
            pt = room_point(doc, x['roomId'])
            if pt: L.tn(doc, v.Id, DB.XYZ(pt.X, pt.Y, level.Elevation), x['label'], 'tag')
        di = [x for x in d['elements'] if x['kind'] == 'DI' and x['levelCode'] == lc]
        for x in di: color(doc, v, x['pipeIds'], (140, 140, 140), 2)
        for x in acc:
            e = el(doc, x['id']); b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
            L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, level.Elevation), x['label'], 'tag')
        tot = sum(x['length_m'] for x in cs)
        sub = (u'%d locales · %.1f ml de serpentín en locales' % (len(cs), tot) + (u' · distribución %.1f ml' % di[0]['length_m'] if di else u'')).replace('.', ',')
        it = item(v, v.CropBox, u'Serpentines por local · ' + ln, 'plan', ln, [x['code'] for x in cs] + [x['code'] for x in acc], [], [x['roomId'] for x in cs] + [x['id'] for x in acc])
        sheets.append(dict(S.lay_sheet(doc, 'CLI-' + lc + '-01', u'Piso radiante · ' + ln, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Climatización · ' + lc), kind='general', level=ln, sector=ln))
    return sheets

def circuit_ficha(doc, x, k):
    room = el(doc, x['roomId']); level = el(doc, int(room.LevelId.Value)); rb = room.get_BoundingBox(None)
    ln = u(level.Name); sector = u'Local ' + u(x['room']) + u' · ' + ln
    v = S.new_plan(doc, level, S.bounds([room], level.Elevation, .6 / M), 'ADER CLI R19 - ' + x['code'] + ' - PLANTA', depth=-.6)
    hvac_view(doc, v); color(doc, v, x['pipeIds'], PAL[k % len(PAL)])
    pt = room_point(doc, x['roomId'])
    L.tn(doc, v.Id, DB.XYZ(pt.X, pt.Y, level.Elevation), x['label'], 'tag')
    L.tn(doc, v.Id, DB.XYZ(pt.X, pt.Y + .45 / M, level.Elevation), u(x['room']), 'room')
    fx = L.AxisFrame(v, DB.XYZ(rb.Min.X, rb.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY)
    fy = L.AxisFrame(v, DB.XYZ(rb.Min.X, rb.Min.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    dims = [L.tick_dim(doc, fx, x['code'] + u' local X', [0, rb.Max.X - rb.Min.X], True, .35 / M), L.tick_dim(doc, fy, x['code'] + u' local Y', [0, rb.Max.Y - rb.Min.Y], True, .35 / M)]
    c2 = lambda a: (u'%.2f' % a).replace(u'.', u',')
    lines = [x['label'], u'Mando ' + c2(x['supply_m']) + u' ml · Retorno ' + c2(x['return_m']) + u' ml · Local ' + c2(x['area_m2']) + u' m²',
             u'Densidad ' + c2(x['density']) + u' m/m² (paso 15 cm ≈ 6,7 m/m²) · ' + u(x['status']), u'Sistemas Revit: ' + u', '.join(x['systems'])]
    items = [item(v, v.CropBox, x['code'] + u' · planta', 'plan', sector, [x['code']], dims, [x['roomId']], lines)]
    # axonometric of the room with floors hidden
    b = rb; pad = .3 / M
    bx = DB.BoundingBoxXYZ(); bx.Min = DB.XYZ(b.Min.X - pad, b.Min.Y - pad, level.Elevation - .4 / M); bx.Max = DB.XYZ(b.Max.X + pad, b.Max.Y + pad, level.Elevation + 1.2 / M)
    ax = DB.View3D.CreateIsometric(doc, DB.ElementId(Int64(49559))); L.setup_view(doc, ax); hvac_view(doc, ax)
    ax.Name = 'ADER CLI R19 - ' + x['code'] + ' - AXO'; ax.SetSectionBox(bx); ax.IsSectionBoxActive = True
    dd = DB.XYZ(-1, -1, -1.1).Normalize(); right = dd.CrossProduct(DB.XYZ.BasisZ).Normalize()
    ax.SetOrientation(DB.ViewOrientation3D(DB.XYZ.Zero, right.CrossProduct(dd).Normalize(), dd)); L.D.fit3d(doc, ax)
    try: ax.SaveOrientationAndLock()
    except Exception: pass
    color(doc, ax, x['pipeIds'], PAL[k % len(PAL)]); doc.Regenerate()
    L.axo_note(doc, ax, DB.XYZ(pt.X, pt.Y, level.Elevation), x['label'], 'tag')
    items.append(item(ax, ax.CropBox, x['code'] + u' · axonométrica', 'axo', sector, [x['code']], [], [x['roomId']]))
    sheet = S.lay_sheet(doc, 'CLI-F-' + x['code'], u'Circuito ' + x['code'] + u' · ' + u(x['room']), x['label'], items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Climatización · ' + x['code'])
    sheet.update(kind='element', element=x['code'], elementId=str(x['roomId']), elementKind='CI', level=ln, sector=sector)
    return sheet

def colector_ficha(doc, x, d):
    e = el(doc, x['id']); level = doc.GetElement(e.LevelId) if e.LevelId != DB.ElementId.InvalidElementId else el(doc, 353988 if x['code'] == 'CO-N' else 694)
    b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5; ln = u(level.Name); sector = u'Colector ' + (u'Norte' if x['code'] == 'CO-N' else u'Sur') + u' · ' + u(x['room'] or u'')
    lv = el(doc, 353988 if x['code'] == 'CO-N' else 694)
    v = S.new_plan(doc, lv, S.bounds([e], lv.Elevation, 1.2 / M), 'ADER CLI R19 - ' + x['code'] + ' - PLANTA', depth=-.6)
    hvac_view(doc, v); color(doc, v, [x['id']], (200, 40, 40), 5)
    L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, lv.Elevation), x['label'], 'tag')
    lines = [x['label'], u(x['status']), u'Salidas y circuitos por salida: no definidos en el modelo (a definir).']
    items = [item(v, v.CropBox, x['code'] + u' · planta', 'plan', sector, [x['code']], [], [x['id']], lines)]
    vs, bx = F.section(doc, DB.XYZ(c.X, c.Y, lv.Elevation), DB.XYZ.BasisY, None, -1.0 / M, 1.0 / M, (b.Min.Z - lv.Elevation) - .4 / M, (b.Max.Z - lv.Elevation) + .4 / M, 'ADER CLI R19 - ' + x['code'] + ' - VISTA')
    hvac_view(doc, vs); color(doc, vs, [x['id']], (200, 40, 40), 5); doc.Regenerate()
    f = L.Frame(vs); xs = sorted([f.x(DB.XYZ(c.X, b.Min.Y, c.Z)), f.x(DB.XYZ(c.X, b.Max.Y, c.Z))])
    ds = [L.tick_dim(doc, f, x['code'] + u' ancho', xs, True, b.Max.Z - f.o.Z + .2 / M), L.tick_dim(doc, f, x['code'] + u' altura', [b.Min.Z - f.o.Z, b.Max.Z - f.o.Z], False, xs[1] + .3 / M)]
    L.tn(doc, vs.Id, f.p(xs[0], b.Max.Z - f.o.Z + .45 / M), x['code'], 'tag')
    items.append(item(vs, bx, x['code'] + u' · vista', 'elevation', sector, [x['code']], ds, [x['id']]))
    ax = F.axo(doc, e, x['code'], x['label'], sector); ax['title'] = x['code'] + u' · axonométrica'; items.append(ax)
    sheet = S.lay_sheet(doc, 'CLI-F-' + x['code'], u'Colector ' + x['code'], x['label'], items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Climatización · ' + x['code'])
    sheet.update(kind='element', element=x['code'], elementId=str(x['id']), elementKind='CO', level=ln, sector=sector)
    return sheet

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CLI-00'; sheet.Name = u'Climatización · índice'
    head = u'CASA ÁNGEL · CLIMATIZACIÓN · ÍNDICE, CRITERIOS Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CLI-00', 'title': u'Índice, criterios y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Climatización', 'sector': u'General'}]

def reset(doc, part):
    path = os.path.join(OUT, 'cli-' + part + '.json'); rec = L.R1.read(path)
    ids = [s_['sheetId'] for s_ in rec['sheets']] + [v['id'] for s_ in rec['sheets'] for v in s_['views']]
    def body():
        for i in ids:
            e = el(doc, i)
            if e is not None and (isinstance(e, DB.ViewSheet) and e.SheetNumber.startswith('CLI-') or isinstance(e, DB.View) and name(e).startswith('ADER CLI R19')): doc.Delete(e.Id)
        return len(ids)
    n, checked = L.guarded(doc, 'ADER CLI R19 - reset ' + part, body)
    os.remove(path); doc.Save(); return {'status': 'success', 'deleted': n}

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'cli-' + part + '.json')
    if job.get('reset'): return reset(doc, part)
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('cli-') and fn.endswith('.json')): continue
            rec = L.R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r19-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            L.R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    d = data()
    cis = [x for x in d['elements'] if x['kind'] == 'CI']
    def body():
        if part == 'plans': return plans_part(doc, d)
        if part.startswith('ci'): return [circuit_ficha(doc, x, cis.index(x)) for x in cis if x['code'] in job['codes']]
        if part == 'colectores': return [colector_ficha(doc, x, d) for x in d['elements'] if x['kind'] == 'CO']
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER CLI R19 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    L.R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
