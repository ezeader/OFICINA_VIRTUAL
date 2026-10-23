# -*- coding: utf-8 -*-
"""R21 read-only ceilings inventory + R21 Cielorrasos sheets (documentation only)."""
import os, imp, datetime
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_ceil', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_ceil', os.path.join(ROOT, 'revit_fichas_r12.py'))
P = imp.load_source('ader_pisos_r18_for_ceil', os.path.join(ROOT, 'revit_pisos_r18.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz; R1 = L.R1
if 5 not in L.SCALES: L.SCALES.insert(0, 5)
RUBRO = u'CIELORRASOS'
LEVELS = [(311, 'PB', u'00. Planta Baja'), (694, 'PA', u'01. Planta Alta'), (353988, 'PE', u'02. Planta Entrepiso')]
PAL = [(214, 230, 245), (250, 214, 214), (222, 240, 214), (240, 225, 200)]
FOOT = u'Cielorrasos: planta de cielorrasos (vista desde abajo). Altura = cara inferior sobre el nivel. Locales sin cielorraso modelado indicados en rojo. Cotas en metros. Códigos TC/CR como anotación.'

def solids(e):
    out = []
    for g in e.get_Geometry(DB.Options()) or []:
        if isinstance(g, DB.Solid) and g.Volume > 0: out.append(g)
    return out

def inventory(doc):
    ceils = []; geo = {}
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Ceilings).WhereElementIsNotElementType():
        t = doc.GetElement(e.GetTypeId()); cs = t.GetCompoundStructure() if t else None; lev = doc.GetElement(e.LevelId); b = e.get_BoundingBox(None)
        ceils.append({'id': eid(e), 'type': u(name(t)), 'level': u(name(lev)), 'levelId': int(e.LevelId.Value), 'area_m2': e.get_Parameter(DB.BuiltInParameter.HOST_AREA_COMPUTED).AsDouble() * M * M,
                      'perimeter_m': (e.get_Parameter(DB.BuiltInParameter.HOST_PERIMETER_COMPUTED).AsDouble() * M) if e.get_Parameter(DB.BuiltInParameter.HOST_PERIMETER_COMPUTED) else None,
                      'height_m': (b.Min.Z - lev.Elevation) * M, 'layers': [{'material': u(name(doc.GetElement(l.MaterialId))) if l.MaterialId != DB.ElementId.InvalidElementId else u'', 'thickness_m': l.Width * M} for l in (cs.GetLayers() if cs else [])], 'bbox': R1.bbox(e)})
        geo[eid(e)] = solids(e)
    rooms = []
    for r in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if r.Area <= 0 or not isinstance(r.Location, DB.LocationPoint): continue
        p = r.Location.Point; lev = doc.GetElement(r.LevelId)
        line = DB.Line.CreateBound(DB.XYZ(p.X, p.Y, lev.Elevation + .5 / M), DB.XYZ(p.X, p.Y, lev.Elevation + 4.5 / M))
        hit = None
        for cid, ss in geo.items():
            for s_ in ss:
                try:
                    res = s_.IntersectWithCurve(line, DB.SolidCurveIntersectionOptions())
                    if res.SegmentCount > 0: hit = cid; break
                except: pass
            if hit: break
        hp = r.get_Parameter(DB.BuiltInParameter.ROOM_HEIGHT)
        rooms.append({'id': eid(r), 'name': u(r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()), 'number': u(r.Number), 'level': u(name(lev)), 'levelId': int(r.LevelId.Value),
                      'area_m2': r.Area * M * M, 'perimeter_m': r.Perimeter * M, 'ceiling': hit, 'finishCeiling': u(r.get_Parameter(DB.BuiltInParameter.ROOM_FINISH_CEILING).AsString() or u'')})
    R1.write(os.path.join(OUT, 'ceil-raw.json'), {'readAt': datetime.datetime.utcnow().isoformat() + 'Z', 'ceilings': ceils, 'rooms': rooms})
    return {'status': 'success', 'ceilings': len(ceils), 'rooms': len(rooms), 'roomsWithCeiling': len([r for r in rooms if r['ceiling']])}

# ---------------------------------------------------------------- sheets

def ceiling_vft(doc):
    return next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == DB.ViewFamily.CeilingPlan)

def ceiling_plan(doc, level, elements, vname, pad=.8):
    v = DB.ViewPlan.Create(doc, ceiling_vft(doc).Id, level.Id); L.setup_view(doc, v)
    v.Name = vname; v.CropBox = S.bounds(elements, level.Elevation, pad / M); v.CropBoxActive = True; v.CropBoxVisible = False
    v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)
    vr = v.GetViewRange()
    for plane, off in [(DB.PlanViewPlane.BottomClipPlane, 0.), (DB.PlanViewPlane.CutPlane, 1.8), (DB.PlanViewPlane.TopClipPlane, 2.9), (DB.PlanViewPlane.ViewDepthPlane, 2.9)]:
        vr.SetLevelId(plane, level.Id); vr.SetOffset(plane, off / M)
    try: v.SetViewRange(vr)
    except Exception: pass
    mgr = v.GetCropRegionShapeManager()
    for prop in ['TopAnnotationCropOffset', 'BottomAnnotationCropOffset', 'LeftAnnotationCropOffset', 'RightAnnotationCropOffset']:
        try: setattr(mgr, prop, .01)
        except Exception: pass
    return v

def item(v, box, title, kind, sector, tags, dims, elements, data_=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data_}

def paint(doc, v, e, rgb, fill):
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb)
    if fill is not None: ov.SetSurfaceForegroundPatternId(fill); ov.SetSurfaceForegroundPatternColor(c)
    v.SetElementOverrides(e.Id, ov)

def level_plan(doc, lid, lc, ln, d, fill, colors):
    level = el(doc, lid)
    cs = [(el(doc, c['id']), c) for c in d['ceilings'] if c['levelCode'] == lc]
    rooms = [r for r in d['rooms'] if r['levelCode'] == lc]; rels = [el(doc, r['id']) for r in rooms]
    v = ceiling_plan(doc, level, [e for e, c in cs] + [x for x in rels if x is not None], 'ADER CIE R21 - ' + lc + ' - CIELORRASOS')
    for e, c in cs:
        paint(doc, v, e, colors[c['typeCode']], fill); b = e.get_BoundingBox(None); m = (b.Min + b.Max) * .5
        L.tn(doc, v.Id, DB.XYZ(m.X, m.Y + .3 / M, level.Elevation), c['label'], 'tag')
    for r, re_ in zip(rooms, rels):
        if re_ is None or not isinstance(re_.Location, DB.LocationPoint): continue
        p = re_.Location.Point
        L.tn(doc, v.Id, DB.XYZ(p.X, p.Y - .2 / M, level.Elevation), r['number'] + u' · ' + u(r['name']) + (u'' if r['ceiling'] else (u' · CIELORRASO PARCIAL' if r.get('partial') else u' · SIN CIELORRASO')), 'room')
    tot = sum(c['area_m2'] for e, c in cs); miss = [r for r in rooms if not r['ceiling'] and not r.get('partial')]
    sub = (u'%d cielorrasos · %.2f m² · %d locales sin cielorraso modelado (%.2f m²)' % (len(cs), tot, len(miss), sum(r['area_m2'] for r in miss))).replace('.', ',')
    it = item(v, v.CropBox, u'Planta de cielorrasos · ' + ln, 'plan', ln, [c['code'] for e, c in cs], [], [eid(e) for e, c in cs] + [r['id'] for r in rooms])
    return dict(S.lay_sheet(doc, 'CIE-' + lc + '-01', u'Planta de cielorrasos · ' + ln, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Cielorrasos · ' + lc), kind='general', level=ln, sector=ln)

def type_ficha(doc, t, d, fill, colors):
    cs = [(el(doc, c['id']), c) for c in d['ceilings'] if c['typeCode'] == t['code']]
    e0, c0 = max(cs, key=lambda x: x[1]['area_m2']); lc = c0['levelCode']; lid, _, ln = next(x for x in LEVELS if x[1] == lc); level = el(doc, lid)
    same = [(e, c) for e, c in cs if c['levelCode'] == lc]
    v = ceiling_plan(doc, level, [e for e, c in same], 'ADER CIE R21 - ' + t['code'] + ' - PLANTA', pad=1.0)
    for e, c in same:
        paint(doc, v, e, colors[t['code']], fill); b = e.get_BoundingBox(None); m = (b.Min + b.Max) * .5
        L.tn(doc, v.Id, DB.XYZ(m.X, m.Y, level.Elevation), c['label'], 'tag')
    c2 = lambda x: (u'%.2f' % x).replace(u'.', u',')
    lines = [t['label'], u'Capas: ' + t['layerText'], u'Piezas: ' + u', '.join(c['code'] + u' (' + c2(c['area_m2']) + u' m², h ' + c2(c['height_m']) + u')' for e, c in cs)]
    items = [item(v, v.CropBox, t['code'] + u' · planta (' + ln + u')', 'plan', ln, [c['code'] for e, c in same], [], [eid(e) for e, c in same], lines)]
    b = e0.get_BoundingBox(None); m = (b.Min + b.Max) * .5; lv = doc.GetElement(e0.LevelId)
    half = (b.Max.X - b.Min.X) / 2
    vs, bx = F.section(doc, DB.XYZ(m.X, m.Y, lv.Elevation), DB.XYZ.BasisX, None, -half - .5 / M, half + .5 / M, -.3 / M, (b.Max.Z - lv.Elevation) + .5 / M, 'ADER CIE R21 - ' + t['code'] + ' - CORTE')
    doc.Regenerate(); f = L.Frame(vs); ylev = lv.Elevation - f.o.Z; yb = b.Min.Z - f.o.Z; xs = sorted([f.x(DB.XYZ(b.Min.X, m.Y, m.Z)), f.x(DB.XYZ(b.Max.X, m.Y, m.Z))])
    ds = [L.tick_dim(doc, f, t['code'] + u' altura libre', [ylev, yb], False, xs[1] + .3 / M), L.tick_dim(doc, f, t['code'] + u' ancho', xs, True, b.Max.Z - f.o.Z + .25 / M)]
    L.tn(doc, vs.Id, f.p(xs[0], b.Max.Z - f.o.Z + .45 / M), c0['label'], 'tag')
    items.append(item(vs, bx, t['code'] + u' · corte', 'section', ln, [t['code']], ds, [eid(e0)]))
    ax = F.axo(doc, e0, c0['code'], c0['label'], u'Sector: ' + ln); ax['title'] = c0['code'] + u' · axonométrica'; items.append(ax)
    sheet = S.lay_sheet(doc, 'CIE-F-' + t['code'], u'Ficha ' + t['code'] + u' · ' + t['type'], t['label'], items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Cielorrasos · ' + t['code'])
    sheet.update(kind='element', element=t['code'], elementId=str(eid(e0)), elementKind='TC', level=ln, sector=ln)
    return sheet

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CIE-00'; sheet.Name = u'Cielorrasos · índice'
    head = u'CASA ÁNGEL · CIELORRASOS · ÍNDICE, TIPOS Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CIE-00', 'title': u'Índice, tipos y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Cielorrasos', 'sector': u'General'}]

def reset(doc, part):
    path = os.path.join(OUT, 'cie-' + part + '.json'); rec = R1.read(path)
    ids = [x['sheetId'] for x in rec['sheets']] + [v['id'] for x in rec['sheets'] for v in x['views']]
    def body():
        for i in ids:
            e = el(doc, i)
            if e is not None and (isinstance(e, DB.ViewSheet) and e.SheetNumber.startswith('CIE-') or isinstance(e, DB.View) and (name(e).startswith('ADER CIE R21') or name(e).startswith('ADER EST R12 - CE-'))): doc.Delete(e.Id)
        return len(ids)
    n, checked = L.guarded(doc, 'ADER CIE R21 - reset ' + part, body)
    os.remove(path); doc.Save(); return {'status': 'success', 'deleted': n}

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    part = job['part']
    if part == 'inventory': return inventory(doc)
    if job.get('reset'): return reset(doc, part)
    if part == 'cleanup':
        def body():
            ids = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View3D) if name(v).startswith('ADER EST R12 - CE-')]
            for i in ids: doc.Delete(i)
            return len(ids)
        n, checked = L.guarded(doc, 'ADER CIE R21 - cleanup', body); doc.Save(); return {'status': 'success', 'deleted': n}
    L.register_font(); path = os.path.join(OUT, 'cie-' + part + '.json')
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('cie-') and fn.endswith('.json')): continue
            rec = R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r21-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path):
        rec = R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    d = L.read('ceil-plan'); fill = P.solid_fill(doc)
    colors = dict((t['code'], PAL[i % len(PAL)]) for i, t in enumerate(d['types']))
    def body():
        if part == 'plans': return [level_plan(doc, lid, lc, ln, d, fill, colors) for lid, lc, ln in LEVELS]
        if part == 'types': return [type_ficha(doc, t, d, fill, colors) for t in d['types']]
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER CIE R21 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
