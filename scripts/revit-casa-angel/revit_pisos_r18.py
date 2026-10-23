# -*- coding: utf-8 -*-
"""R18: Pisos y zócalos sheets (documentation only).
PIS-PB/PA/PE-01 plantas por nivel (pisos coloreados por tipo, locales rotulados) · PIS-F-TP-nn fichas por tipo con corte de paquete 1:5 · PIS-00 índice."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_floors', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_floors', os.path.join(ROOT, 'revit_fichas_r12.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
if 5 not in L.SCALES: L.SCALES.insert(0, 5)
RUBRO = u'PISOS Y ZÓCALOS'
LEVELS = [(311, 'PB', u'00. Planta Baja'), (694, 'PA', u'01. Planta Alta'), (353988, 'PE', u'02. Planta Entrepiso')]
PALETTE = [(244, 226, 196), (214, 230, 245), (222, 240, 214), (250, 214, 214), (232, 222, 246), (255, 240, 200), (210, 240, 236), (245, 225, 240),
           (226, 226, 226), (240, 216, 190), (205, 220, 205), (230, 230, 200), (210, 230, 210)]
FOOT = u'Pisos: paquetes según tipo de piso del modelo; terminación = capa superior. Cotas en metros (no asociativas). Códigos TP/PI/ZO como anotación. Zócalos: solo 5 tramos modelados; el resto se computa por perímetro de local.'

def data(): return L.read('floors-plan')

def solid_fill(doc):
    for fp in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
        try:
            if fp.GetFillPattern().IsSolidFill: return fp.Id
        except: pass
    return None

def paint(doc, v, e, rgb, fill):
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb)
    if fill is not None:
        ov.SetSurfaceForegroundPatternId(fill); ov.SetSurfaceForegroundPatternColor(c)
    ov.SetProjectionLineColor(DB.Color(120, 120, 120)); v.SetElementOverrides(e.Id, ov)

def item(v, box, title, kind, sector, tags, dims, elements, data_=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data_}

def level_plan(doc, lid, lc, lname, d, fill, colors):
    level = el(doc, lid)
    pieces = [(el(doc, p['id']), p) for p in d['pieces'] if p['levelCode'] == lc and el(doc, p['id']) is not None]
    rooms = [r for r in d['rooms'] if r['levelCode'] == lc]
    room_els = [el(doc, r['id']) for r in rooms]
    v = S.new_plan(doc, level, S.bounds([e for e, p in pieces] + [x for x in room_els if x is not None], level.Elevation, .8 / M), 'ADER PIS R18 - ' + lc + ' - PLANTA', depth=-.6)
    for e, p in pieces: paint(doc, v, e, colors[p['typeCode']], fill)
    for r, re_ in zip(rooms, room_els):
        if re_ is None or not isinstance(re_.Location, DB.LocationPoint): continue
        pt = re_.Location.Point
        L.tn(doc, v.Id, DB.XYZ(pt.X, pt.Y + .35 / M, level.Elevation), r['number'] + u' · ' + u(r['name']), 'room')
        L.tn(doc, v.Id, DB.XYZ(pt.X, pt.Y - .15 / M, level.Elevation), r['label'], 'tag')
    zs = []
    for z in d['skirtings']:
        e = el(doc, z['id'])
        if e is None: continue
        bb = e.get_BoundingBox(None)
        if abs(bb.Min.Z - level.Elevation) > 1.5 / M: continue
        S.colorize(doc, v, e, (200, 60, 40)); c = (bb.Min + bb.Max) * .5
        L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, level.Elevation), z['label'], 'tag'); zs.append((e, z))
    tags = [r['typeCode'] for r in rooms if r['typeCode']] + [z['code'] for e, z in zs]
    it = item(v, v.CropBox, u'Planta de pisos · ' + lname, 'plan', lname, sorted(set(tags)), [], [eid(e) for e, p in pieces] + [r['id'] for r in rooms] + [eid(e) for e, z in zs])
    tot = sum(p['area_m2'] for e, p in pieces)
    by = {}
    for e, p in pieces: by[p['typeCode']] = by.get(p['typeCode'], 0) + p['area_m2']
    sub = (u'%.2f m² de pisos · ' % tot + u' · '.join(k + u' ' + (u'%.2f' % v_) + u' m²' for k, v_ in sorted(by.items()))).replace('.', ',')
    return dict(S.lay_sheet(doc, 'PIS-' + lc + '-01', u'Planta de pisos · ' + lname, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Pisos · ' + lc), kind='general', level=lname, sector=lname)

def paquete_section(doc, t, e, pt, top_z, vname):
    lev = doc.GetElement(e.LevelId)
    th = sum(l['thickness_m'] for l in t['layers']) / M
    v, bx = F.section(doc, DB.XYZ(pt.X, pt.Y, lev.Elevation), DB.XYZ.BasisX, None, -.45 / M, .75 / M, (top_z - lev.Elevation) - th - .15 / M, (top_z - lev.Elevation) + .2 / M, vname)
    doc.Regenerate()
    f = L.Frame(v); y = top_z - f.o.Z; ys = [y]; xc = f.x(pt)
    for l in t['layers']:
        if l['thickness_m'] <= 0: continue
        y0 = ys[-1]; y1 = y0 - l['thickness_m'] / M; ys.append(y1)
        L.tn(doc, v.Id, f.p(xc + .45 / M, (y0 + y1) / 2 + .01 / M), (l['material'] + u' ' + (u'%.1f' % (l['thickness_m'] * 100)).replace('.', ',') + u' cm'), 'text')
    dims = [L.tick_dim(doc, f, t['code'] + u' capas', L.uniq(ys, tol=.001 / M), False, xc + .3 / M, tick=.05 / M),
            L.tick_dim(doc, f, t['code'] + u' espesor total', [ys[-1], ys[0]], False, xc + .2 / M, tick=.05 / M)]
    L.tn(doc, v.Id, f.p(xc - .4 / M, y + .17 / M), t['code'] + u' · corte de paquete', 'tag')
    return v, bx, dims

def type_ficha(doc, t, d, fill, colors):
    pieces = [(el(doc, p['id']), p) for p in d['pieces'] if p['typeCode'] == t['code'] and el(doc, p['id']) is not None]
    e0, p0 = pieces[0]; lc = p0['levelCode']; lid = next(x[0] for x in LEVELS if x[1] == lc); lname = next(x[2] for x in LEVELS if x[1] == lc)
    same = [(e, p) for e, p in pieces if p['levelCode'] == lc]
    level = el(doc, lid)
    v = S.new_plan(doc, level, S.bounds([e for e, p in same], level.Elevation, 1.0 / M), 'ADER PIS R18 - ' + t['code'] + ' - PLANTA', depth=-.6)
    dims = []
    for e, p in same:
        paint(doc, v, e, colors[t['code']], fill)
        bb = e.get_BoundingBox(None); c = (bb.Min + bb.Max) * .5
        L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, level.Elevation), p['label'], 'tag')
    rooms = [r for r in d['rooms'] if r['typeCode'] == t['code']]
    for r in rooms:
        re_ = el(doc, r['id'])
        if re_ is not None and isinstance(re_.Location, DB.LocationPoint) and int(re_.LevelId.Value) == lid:
            q = re_.Location.Point; L.tn(doc, v.Id, DB.XYZ(q.X, q.Y + .35 / M, level.Elevation), r['number'] + u' · ' + u(r['name']), 'room')
    c2 = lambda x: (u'%.2f' % x).replace(u'.', u',')
    lines = [t['label'], u'Paquete: ' + t['layerText'] + u' · total ' + c2(t['thickness_m'] * 100) + u' cm',
             u'Locales: ' + (u', '.join(r['number'] + u' ' + u(r['name']) + u' (' + c2(r['area_m2']) + u' m²)' for r in rooms) or u'sin local asociado'),
             u'Piezas: ' + u', '.join(p['code'] for e, p in pieces)]
    items = [item(v, v.CropBox, t['code'] + u' · planta (' + lname + u')', 'plan', lname, [t['code']] + [p['code'] for e, p in same], dims, [eid(e) for e, p in same], lines)]
    # paquete section at a room centre on this type (or the piece centre)
    pt = None
    for r in rooms:
        re_ = el(doc, r['id'])
        if re_ is not None and isinstance(re_.Location, DB.LocationPoint) and r['piece'] == p0['code']: pt = re_.Location.Point; break
    bb = e0.get_BoundingBox(None)
    if pt is None: pt = (bb.Min + bb.Max) * .5
    vs, bxs, ds = paquete_section(doc, t, e0, pt, bb.Max.Z, 'ADER PIS R18 - ' + t['code'] + ' - PAQUETE')
    items.append(item(vs, bxs, t['code'] + u' · corte de paquete', 'section', lname, [t['code']], ds, [eid(e0)]))
    ax = F.axo(doc, e0, t['code'], p0['label'], u'Sector: ' + lname); ax['title'] = t['code'] + u' · axonométrica'
    items.append(ax)
    sheet = S.lay_sheet(doc, 'PIS-F-' + t['code'], u'Ficha ' + t['code'] + u' · ' + t['type'].split(' /')[0], t['label'], items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Pisos · ' + t['code'])
    sheet.update(kind='element', element=t['code'], elementId=str(eid(e0)), elementKind='TP', level=lname, sector=lname)
    return sheet

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'PIS-00'; sheet.Name = u'Pisos · índice'
    head = u'CASA ÁNGEL · PISOS Y ZÓCALOS · ÍNDICE, TIPOS Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        x = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(x, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [x, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(x, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'PIS-00', 'title': u'Índice, tipos y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Pisos', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'pis-' + part + '.json')
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('pis-') and fn.endswith('.json')): continue
            rec = L.R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r18-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            L.R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    d = data(); fill = solid_fill(doc)
    colors = dict((t['code'], PALETTE[i % len(PALETTE)]) for i, t in enumerate(d['types']))
    def body():
        if part == 'plans': return [level_plan(doc, lid, lc, ln, d, fill, colors) for lid, lc, ln in LEVELS]
        if part == 'types': return [type_ficha(doc, t, d, fill, colors) for t in d['types']]
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER PIS R18 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    L.R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
