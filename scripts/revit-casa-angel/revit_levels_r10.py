# -*- coding: utf-8 -*-
"""R10: one general openings plan per level (documentation only), exported to PDF.
Every opening is tagged by code and every room by number + name."""
import os, imp, datetime
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
L = imp.load_source('ader_openings_r4_for_levels', os.path.join(ROOT, 'revit_openings_r4.py'))
OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
LEVELS = [(311, 'PB'), (694, 'PA'), (353988, 'PE')]

def level_job(doc, job):
    plan = L.read('plan'); items = dict((i['id'], i) for i in plan['items'])
    rooms_on = {}
    for r in plan['rooms']:
        rooms_on.setdefault(r['level'], []).append(r)
    path = os.path.join(OUT, 'levels.json')
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, x['sheetId']) for x in rec['levels']): return {'status': 'success', 'existing': True}
    L.register_font()
    vptype = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ElementType) if name(t) == 'ADER ABR - viewport')
    def body():
        out = []
        for lid, code in LEVELS:
            level = el(doc, lid); rr = rooms_on.get(lid, [])
            ids = sorted(set(i for r in rr for i in r['items']))
            elements = [el(doc, i) for i in ids]
            rooms = [el(doc, r['id']) for r in rr if r['id']]
            pts = []
            for e in elements + [x for x in rooms if x is not None]:
                b = e.get_BoundingBox(None)
                if b: pts += [b.Min, b.Max]
            pad = 1.2 / M
            bx = DB.BoundingBoxXYZ()
            bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, level.Elevation - 1)
            bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, level.Elevation + 12)
            v = DB.ViewPlan.Create(doc, DB.ElementId(Int64(L.PLAN_VFT)), level.Id); L.setup_view(doc, v)
            v.Name = 'ADER ABR R10 - ' + code + ' - PLANTA GENERAL'; v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False
            try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
            except: pass
            vr = v.GetViewRange()
            vr.SetLevelId(DB.PlanViewPlane.CutPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.CutPlane, 1.30 / M)
            vr.SetLevelId(DB.PlanViewPlane.TopClipPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.TopClipPlane, 4.0 / M)
            vr.SetLevelId(DB.PlanViewPlane.BottomClipPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, 0)
            vr.SetLevelId(DB.PlanViewPlane.ViewDepthPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, -.3 / M)
            v.SetViewRange(vr)
            for e in elements:
                L.highlight(doc, v, e)
                a, b, z0, z1, n = L.extents(doc, e)
                room = next((x for x in rooms if x is not None and items[eid(e)]['rooms'] and eid(x) == items[eid(e)]['rooms'][0]), None)
                vd = L.view_dir_for(doc, e, room); mid = (a + b) * .5
                L.tn(doc, v.Id, DB.XYZ(mid.X, mid.Y, level.Elevation) + vd * (.75 / M), items[eid(e)]['code'], 'tag')
            for r in rr:
                room = el(doc, r['id']) if r['id'] else None
                if room is not None and isinstance(room.Location, DB.LocationPoint):
                    p = room.Location.Point; L.tn(doc, v.Id, DB.XYZ(p.X, p.Y, level.Elevation), L.room_label(r), 'room')
            doc.Regenerate()
            sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); number = 'ABR-R4-' + code + '-00'
            sheet.SheetNumber = number; sheet.Name = u'Planta general · ABR'
            title = u'CASA ÁNGEL · ABERTURAS · ' + u(level.Name).upper() + u' · PLANTA GENERAL'
            L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), title, 'title')
            sub = str(len(ids)) + u' aberturas: ' + u', '.join(items[i]['code'] for i in ids)
            L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .075, 0), sub, 'sub')
            w, h = L.sheet_size(v.CropBox, 1)
            s = L.snap(max(w / (L.X1 - L.X0 - .04), h / (L.TOP - L.BOTTOM - L.TITLE_H - .03)))
            vp, meta = L.place(doc, sheet, v, s, (L.X0, L.BOTTOM - L.DATA_H + .02, L.X1, L.TOP), u'Planta general · ' + u(level.Name), vptype)
            out.append({'code': code, 'level': u(level.Name), 'levelId': lid, 'viewId': eid(v), 'sheetId': eid(sheet), 'sheetNumber': number,
                        'scale': s, 'box': meta['box'], 'label': meta['label'], 'anchor': meta['anchor'],
                        'notes': [{'text': title, 'anchor': [L.X0 + .01, L.Y1 - .012]}, {'text': sub, 'anchor': [L.X0 + .01, L.Y1 - .075]}],
                        'items': ids, 'rooms': [r['id'] for r in rr if r['id']]})
        return out
    levels, checked = L.guarded(doc, 'ADER ABR R10 - plantas generales', body)
    doc.Save()
    opts = DB.PDFExportOptions(); opts.Combine = True
    opts.PaperFormat = DB.ExportPaperFormat.ISO_A1; opts.PaperOrientation = DB.PageOrientationType.Landscape
    opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
    for x in levels:
        opts.FileName = 'r10-level-' + x['code']
        x['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, x['sheetId']).Id]), opts))
    rec = {'readAt': L.now(), 'physicalChecked': checked, 'levels': levels}
    L.R1.write(path, rec)
    return {'status': 'success', 'levels': [(x['code'], x['scale'], len(x['items']), len(x['rooms']), x['exported']) for x in levels]}

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    return level_job(doc, job)
