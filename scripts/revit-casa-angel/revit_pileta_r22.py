# -*- coding: utf-8 -*-
"""R22: Pileta sheets, documentation only. PIL-01 planta acotada · PIL-02 cortes · PIL-F-VASO ficha · PIL-00 índice.
Codes: VA-01..04 muros del vaso · FO-01 fondo · BO-01 borde/solárium · AG-01 agua."""
import os, imp, datetime
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_pil', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_pil', os.path.join(ROOT, 'revit_fichas_r12.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz; R1 = L.R1
RUBRO = u'PILETA'
FOOT = u'Pileta: geometría nativa del vaso (muros "Muro Pileta" con venecitas, fondo "Piso Pileta", borde y volumen de agua). Cotas en metros (no asociativas). Equipo de filtrado, cañerías e iluminación: no modelado / a definir.'

def collect(doc):
    rows = []
    def tname(e): return u(name(doc.GetElement(e.GetTypeId())))
    walls = [e for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Walls).WhereElementIsNotElementType() if 'Pileta' in tname(e)]
    floors = [e for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Floors).WhereElementIsNotElementType() if 'ileta' in tname(e)]
    water = [e for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_GenericModel).WhereElementIsNotElementType() if 'pileta' in tname(e).lower()]
    walls.sort(key=lambda e: (round(e.Location.Curve.Evaluate(.5, True).Y, 1), round(e.Location.Curve.Evaluate(.5, True).X, 1)))
    c2 = lambda x: (u'%.2f' % x).replace(u'.', u',')
    for i, e in enumerate(walls, 1):
        L_ = e.get_Parameter(DB.BuiltInParameter.CURVE_ELEM_LENGTH).AsDouble() * M; H = e.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble() * M
        A = e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M; V = e.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * M ** 3
        rows.append({'id': eid(e), 'code': 'VA-%02d' % i, 'kind': 'VA', 'type': tname(e), 'length_m': L_, 'height_m': H, 'thickness_m': e.Width * M, 'area_m2': A, 'volume_m3': V,
                     'label': u'VA-%02d · %s × %s · e %s' % (i, c2(L_), c2(H), c2(e.Width * M * 100).replace(',00', '')), 'status': u'Muro del vaso (venecitas 20 cm en el modelo)'})
    for e in floors:
        t = tname(e); A = e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M; V = e.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * M ** 3
        code = 'FO-01' if 'Piso' in t else 'BO-01'
        rows.append({'id': eid(e), 'code': code, 'kind': code[:2], 'type': t, 'area_m2': A, 'volume_m3': V,
                     'label': u'%s · %s · %s m²' % (code, u'fondo' if code == 'FO-01' else u'borde / solárium', c2(A)),
                     'status': u'Fondo: venecitas 5 cm + base 10 cm' if code == 'FO-01' else u'Borde: material "Piso Pileta" 15 cm'})
    for e in water:
        b = e.get_BoundingBox(None); V = (e.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED).AsDouble() * M ** 3) if e.get_Parameter(DB.BuiltInParameter.HOST_VOLUME_COMPUTED) else 0
        rows.append({'id': eid(e), 'code': 'AG-01', 'kind': 'AG', 'type': tname(e), 'volume_m3': V, 'depth_m': (b.Max.Z - b.Min.Z) * M,
                     'label': u'AG-01 · agua · %s m³' % c2(V), 'status': u'Volumen de agua (modelo genérico)'})
    for r in rows:
        b = el(doc, r['id']).get_BoundingBox(None); r['bbox'] = R1.bbox(el(doc, r['id']))
    return rows

def item(v, box, title, kind, sector, tags, dims, elements, data_=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data_}

def build(doc, rows):
    level = el(doc, 311); els = [el(doc, r['id']) for r in rows]; sector = u'Pileta · 00. Planta Baja'
    pool = [el(doc, r['id']) for r in rows if r['kind'] in ('VA', 'FO', 'AG')]
    pts = [p for e in pool for p in [e.get_BoundingBox(None).Min, e.get_BoundingBox(None).Max]]
    bmin = DB.XYZ(min(p.X for p in pts), min(p.Y for p in pts), min(p.Z for p in pts)); bmax = DB.XYZ(max(p.X for p in pts), max(p.Y for p in pts), max(p.Z for p in pts))
    c = (bmin + bmax) * .5
    v = S.new_plan(doc, level, S.bounds(pool, level.Elevation, 1.6 / M), 'ADER PIL R22 - PLANTA', depth=-2.5)
    dims = []
    for r, e in zip(rows, els):
        S.colorize(doc, v, e, (40, 120, 190) if r['kind'] in ('VA', 'FO', 'AG') else (120, 120, 120))
        if r['kind'] == 'VA':
            dims += S.tag_plan(doc, v, e, r, level.Elevation, c)
        else:
            bb = e.get_BoundingBox(None); m = (bb.Min + bb.Max) * .5
            L.tn(doc, v.Id, DB.XYZ(m.X, m.Y - (.4 / M if r['kind'] == 'FO' else 0), level.Elevation), r['label'], 'tag')
    fx = L.AxisFrame(v, DB.XYZ(bmin.X, bmin.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY); fy = L.AxisFrame(v, DB.XYZ(bmin.X, bmin.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    dims += [L.tick_dim(doc, fx, u'Vaso largo X', [0, bmax.X - bmin.X], True, .6 / M), L.tick_dim(doc, fy, u'Vaso ancho Y', [0, bmax.Y - bmin.Y], True, .6 / M)]
    plan = item(v, v.CropBox, u'Planta de pileta', 'plan', sector, [r['code'] for r in rows], dims, [r['id'] for r in rows])
    secs = []
    for axis, right, half in [('longitudinal', DB.XYZ.BasisX if (bmax.X - bmin.X) >= (bmax.Y - bmin.Y) else DB.XYZ.BasisY, max(bmax.X - bmin.X, bmax.Y - bmin.Y) / 2),
                              ('transversal', DB.XYZ.BasisY if (bmax.X - bmin.X) >= (bmax.Y - bmin.Y) else DB.XYZ.BasisX, min(bmax.X - bmin.X, bmax.Y - bmin.Y) / 2)]:
        vs, bx = F.section(doc, DB.XYZ(c.X, c.Y, level.Elevation), right, None, -half - .8 / M, half + .8 / M, (bmin.Z - level.Elevation) - .5 / M, (bmax.Z - level.Elevation) + .8 / M, 'ADER PIL R22 - CORTE ' + axis.upper())
        for r, e in zip(rows, els): S.colorize(doc, vs, e, (40, 120, 190))
        doc.Regenerate(); f = L.Frame(vs); xs = sorted([f.x(c - right * half), f.x(c + right * half)])
        ds = [L.tick_dim(doc, f, u'Vaso ' + axis, xs, True, bmax.Z - f.o.Z + .35 / M), L.tick_dim(doc, f, u'Profundidad total', [bmin.Z - f.o.Z, bmax.Z - f.o.Z], False, xs[1] + .5 / M)]
        L.tn(doc, vs.Id, f.p(xs[0], bmax.Z - f.o.Z + .7 / M), u'Pileta · corte ' + axis, 'tag'); L.tn(doc, vs.Id, L.crop_corner(vs, .06 / M, .06 / M), sector, 'room')
        secs.append(item(vs, bx, u'Corte ' + axis, 'section', sector, [r['code'] for r in rows if r['kind'] in ('VA', 'FO')], ds, [r['id'] for r in rows if r['kind'] in ('VA', 'FO', 'AG')]))
    c2 = lambda x: (u'%.2f' % x).replace(u'.', u',')
    va = [r for r in rows if r['kind'] == 'VA']; fo = [r for r in rows if r['kind'] == 'FO']; ag = [r for r in rows if r['kind'] == 'AG']
    sub = (u'Muros del vaso %s m² · fondo %s m² · agua %s m³' % (c2(sum(r['area_m2'] for r in va)), c2(sum(r['area_m2'] for r in fo)), c2(sum(r['volume_m3'] for r in ag))))
    sheets = [dict(S.lay_sheet(doc, 'PIL-01', u'Planta de pileta', sub, [plan], FOOT, rubro=RUBRO, sheet_name=u'Pileta · 01'), kind='general', level=u'00. Planta Baja', sector=sector),
              dict(S.lay_sheet(doc, 'PIL-02', u'Cortes de pileta', sub, secs, FOOT, rubro=RUBRO, sheet_name=u'Pileta · 02'), kind='general', level=u'00. Planta Baja', sector=sector)]
    # ficha del vaso: planta (nueva), corte transversal (nuevo), axo
    v2 = S.new_plan(doc, level, S.bounds(pool, level.Elevation, .6 / M), 'ADER PIL R22 - VASO PLANTA', depth=-2.5)
    for r, e in zip(rows, els):
        if r['kind'] in ('VA', 'FO', 'AG'): S.colorize(doc, v2, e, (40, 120, 190))
    d2 = [L.tick_dim(doc, L.AxisFrame(v2, DB.XYZ(bmin.X, bmin.Y, v2.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY), u'Vaso largo X', [0, bmax.X - bmin.X], True, .4 / M),
          L.tick_dim(doc, L.AxisFrame(v2, DB.XYZ(bmin.X, bmin.Y, v2.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX), u'Vaso ancho Y', [0, bmax.Y - bmin.Y], True, .4 / M)]
    L.tn(doc, v2.Id, DB.XYZ(c.X, c.Y, level.Elevation), u'VASO · ' + c2(sum(r['volume_m3'] for r in ag)) + u' m³', 'tag')
    lines = [u'Vaso: ' + u', '.join(r['code'] for r in va) + u' + FO-01', u'Revestimiento (venecitas): muros ' + c2(sum(r['area_m2'] for r in va)) + u' m² + fondo ' + c2(sum(r['area_m2'] for r in fo)) + u' m²',
             u'Agua: ' + c2(sum(r['volume_m3'] for r in ag)) + u' m³ · profundidad modelada ' + c2(max([r.get('depth_m', 0) for r in ag] or [0])) + u' m', u'Equipo, cañerías e iluminación: a definir.']
    it1 = item(v2, v2.CropBox, u'Vaso · planta', 'plan', sector, [r['code'] for r in rows if r['kind'] in ('VA', 'FO', 'AG')], d2, [r['id'] for r in rows if r['kind'] in ('VA', 'FO', 'AG')], lines)
    axe = F.axo(doc, el(doc, fo[0]['id']) if fo else pool[0], 'VASO', u'Vaso de pileta', sector); axe['title'] = u'Vaso · axonométrica'
    sheets.append(dict(S.lay_sheet(doc, 'PIL-F-VASO', u'Ficha del vaso', lines[1], [it1, secs[1] if False else item(*F.section(doc, DB.XYZ(c.X, c.Y, level.Elevation), DB.XYZ.BasisX, None, -(bmax.X - bmin.X) / 2 - .5 / M, (bmax.X - bmin.X) / 2 + .5 / M, (bmin.Z - level.Elevation) - .4 / M, (bmax.Z - level.Elevation) + .6 / M, 'ADER PIL R22 - VASO CORTE'), title=u'Vaso · corte', kind='section', sector=sector, tags=[], dims=[], elements=[r['id'] for r in rows if r['kind'] in ('VA', 'FO')]), axe], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Pileta · vaso'),
                       kind='element', element='VASO', elementId=str(fo[0]['id'] if fo else ''), elementKind='VA', level=u'00. Planta Baja', sector=sector))
    return sheets

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'PIL-00'; sheet.Name = u'Pileta · índice'
    head = u'CASA ÁNGEL · PILETA · ÍNDICE Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'PIL-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Pileta', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'pil-' + part + '.json')
    if part == 'inventory':
        rows = collect(doc); R1.write(os.path.join(OUT, 'pil-plan.json'), {'readAt': L.now(), 'elements': rows}); return {'status': 'success', 'elements': [(r['code'], r['label']) for r in rows]}
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('pil-') and fn.endswith('.json')): continue
            rec = R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r22-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path) and not job.get('reset'):
        rec = R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    rows = L.read('pil-plan')['elements']
    for r in rows:
        for k in ('label', 'status', 'type'):
            if k in r: r[k] = R1.clean(r[k])
    if job.get('reset'):
        def body():
            ids = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if (isinstance(v, DB.ViewSheet) and v.SheetNumber.startswith('PIL-')) or name(v).startswith('ADER PIL R22') or name(v) == 'ADER EST R12 - VASO - AXO']
            n = 0
            for i in ids:
                if doc.GetElement(i) is not None: doc.Delete(i); n += 1
            return n
        n, checked = L.guarded(doc, 'ADER PIL R22 - reset', body)
        for fn in os.listdir(OUT):
            if fn.startswith('pil-') and fn.endswith('.json') and fn != 'pil-plan.json': os.remove(os.path.join(OUT, fn))
        doc.Save(); return {'status': 'success', 'deleted': n}
    def body():
        if part == 'sheets': return build(doc, rows)
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER PIL R22 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
