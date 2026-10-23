# -*- coding: utf-8 -*-
"""R20: Albañilería sheets, documentation only.
ALB-PB/PA/PE-01 plantas (muros coloreados por tipo, rotulados) · ALB-F-TM-nn fichas por tipo (planta, corte de muro con capas, vista, axo) · ALB-00 índice."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_alb', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_alb', os.path.join(ROOT, 'revit_fichas_r12.py'))
P = imp.load_source('ader_pisos_r18_for_alb', os.path.join(ROOT, 'revit_pisos_r18.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
if 5 not in L.SCALES: L.SCALES.insert(0, 5)
S.COLORS['AB'] = (196, 98, 16)
RUBRO = u'ALBAÑILERÍA'
LEVELS = [(311, 'PB', u'00. Planta Baja'), (694, 'PA', u'01. Planta Alta'), (353988, 'PE', u'02. Planta Entrepiso')]
PAL = [(214, 90, 40), (40, 110, 190), (40, 150, 80), (170, 70, 170), (220, 150, 20), (20, 150, 160), (120, 90, 50), (200, 60, 120), (90, 90, 90), (150, 150, 40)]
FOOT = u'Albañilería: muros y tabiques no estructurales del modelo (los de hormigón están en Estructura). Cotas en metros (no asociativas). Códigos TM/AB como anotación. Composición genérica en mampostería: a definir.'

def data(): return L.read('alb-plan')

def paint(doc, v, e, rgb, fill):
    ov = DB.OverrideGraphicSettings(); c = DB.Color(*rgb)
    ov.SetCutLineColor(c); ov.SetProjectionLineColor(c); ov.SetCutLineWeight(4)
    if fill is not None:
        ov.SetCutForegroundPatternId(fill); ov.SetCutForegroundPatternColor(c)
    v.SetElementOverrides(e.Id, ov)

def item(v, box, title, kind, sector, tags, dims, elements, data_=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data_}

def level_plan(doc, lid, lc, ln, d, fill, colors):
    level = el(doc, lid)
    ws = [(el(doc, w['id']), w) for w in d['walls'] if w['levelCode'] == lc and el(doc, w['id']) is not None]
    rooms = [r for r in L.read('plan')['rooms'] if r['level'] == lid and r['id']]
    room_els = [el(doc, r['id']) for r in rooms]
    v = S.new_plan(doc, level, S.bounds([e for e, w in ws] + [x for x in room_els if x is not None], level.Elevation, .8 / M), 'ADER ALB R20 - ' + lc + ' - PLANTA')
    bx = v.CropBox; centre = (bx.Min + bx.Max) * .5; dims = []
    for e, w in ws:
        paint(doc, v, e, colors[w['typeCode']], fill); dims += S.tag_plan(doc, v, e, w, level.Elevation, centre)
    S.room_labels(doc, v, lid, level.Elevation)
    it = item(v, v.CropBox, u'Muros y tabiques · ' + ln, 'plan', ln, [w['code'] for e, w in ws], dims, [eid(e) for e, w in ws])
    by = {}
    for e, w in ws: by[w['typeCode']] = by.get(w['typeCode'], 0) + (w['area_m2'] or 0)
    sub = (u'%d muros · ' % len(ws) + u' · '.join(k + u' ' + (u'%.2f' % x) + u' m²' for k, x in sorted(by.items()))).replace('.', ',')
    return dict(S.lay_sheet(doc, 'ALB-' + lc + '-01', u'Muros y tabiques · ' + ln, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Albañilería · ' + lc), kind='general', level=ln, sector=ln)

def wall_layers_section(doc, t, e, vname):
    a, b, dd, n = S.wall_axis(e); mid = (a + b) * .5; lev = L.level_of(doc, e); w = e.Width
    _, _, z0, z1, _ = L.extents(doc, e)
    zc = min(z0 + 1.0 / M, (z0 + z1) / 2)
    v, bx = F.section(doc, DB.XYZ(mid.X, mid.Y, lev.Elevation), n, None, -(w / 2 + .2 / M), w / 2 + .45 / M, (zc - lev.Elevation) - .25 / M, (zc - lev.Elevation) + .25 / M, vname)
    doc.Regenerate()
    f = L.Frame(v); xa = f.x(mid + n * (w / 2)); xb = f.x(mid - n * (w / 2))
    x0, x1 = sorted([xa, xb]); xs = [x0]; y = zc - f.o.Z
    # Revit lists layers from the exterior face; draw them from x0 regardless of side (labels say order).
    for l in t['layers']:
        if l['thickness_m'] <= 0: continue
        xs.append(xs[-1] + l['thickness_m'] / M)
    dims = [L.tick_dim(doc, f, t['code'] + u' capas', L.uniq(xs, tol=.001 / M), True, y + .12 / M, tick=.04 / M),
            L.tick_dim(doc, f, t['code'] + u' espesor', [x0, x1], True, y + .2 / M, tick=.04 / M)]
    for k, l in enumerate([l for l in t['layers'] if l['thickness_m'] > 0]):
        L.tn(doc, v.Id, f.p(x1 + .08 / M, y + .1 / M - k * .045 / M), str(k + 1) + u'. ' + l['material'] + u' ' + (u'%.1f' % (l['thickness_m'] * 100)).replace('.', ',') + u' cm', 'text')
    L.tn(doc, v.Id, f.p(x0 - .15 / M, y + .3 / M), t['code'] + u' · corte de muro', 'tag')
    return v, bx, dims

def type_ficha(doc, t, d, fill, colors):
    ws = [(el(doc, w['id']), w) for w in d['walls'] if w['typeCode'] == t['code'] and el(doc, w['id']) is not None]
    ws.sort(key=lambda x: -(x[1]['length_m'] or 0))
    e0, w0 = ws[0]; lc = w0['levelCode']; lid, _, ln = next(x for x in LEVELS if x[1] == lc)
    same = [(e, w) for e, w in ws if w['levelCode'] == lc]
    level = el(doc, lid)
    v = S.new_plan(doc, level, S.bounds([e for e, w in same], level.Elevation, 1.0 / M), 'ADER ALB R20 - ' + t['code'] + ' - PLANTA')
    bx = v.CropBox; centre = (bx.Min + bx.Max) * .5; dims = []
    for e, w in same:
        paint(doc, v, e, colors[t['code']], fill); dims += S.tag_plan(doc, v, e, w, level.Elevation, centre)
    c2 = lambda x: (u'%.2f' % x).replace(u'.', u',')
    lines = [t['label'], u'Capas: ' + t['layerText'] + u' · espesor ' + c2(t['thickness_m'] * 100) + u' cm',
             u'%d muros · %s ml · %s m² · %s m³' % (t['count'], c2(t['length_m']), c2(t['area_m2']), c2(t['volume_m3'])),
             (u'Composición genérica en el modelo: definir ladrillo/bloque, revoques y terminaciones.' if t['generic'] else u'Muros: ' + u', '.join(w['code'] for e, w in ws))]
    items = [item(v, v.CropBox, t['code'] + u' · planta (' + ln + u')', 'plan', ln, [w['code'] for e, w in same], dims, [eid(e) for e, w in same], lines)]
    vs, bxs, ds = wall_layers_section(doc, t, e0, 'ADER ALB R20 - ' + t['code'] + ' - CORTE')
    items.append(item(vs, bxs, t['code'] + u' · corte de muro', 'section', ln, [t['code']], ds, [eid(e0)]))
    ev = S.wall_elevation(doc, e0, w0, {}, 'ADER ALB R20 - ' + t['code'] + ' - VISTA'); ev['title'] = w0['code'] + u' · vista'; ev['data'] = None
    items.append(ev)
    ax = F.axo(doc, e0, w0['code'], w0['label'], u'Sector: ' + ln); ax['title'] = w0['code'] + u' · axonométrica'; items.append(ax)
    sheet = S.lay_sheet(doc, 'ALB-F-' + t['code'], u'Ficha ' + t['code'] + u' · ' + t['type'], t['label'], items, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Albañilería · ' + t['code'])
    sheet.update(kind='element', element=t['code'], elementId=str(eid(e0)), elementKind='TM', level=ln, sector=ln)
    return sheet

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'ALB-00'; sheet.Name = u'Albañilería · índice'
    head = u'CASA ÁNGEL · ALBAÑILERÍA · ÍNDICE, TIPOS Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'ALB-00', 'title': u'Índice, tipos y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Albañilería', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'alb-' + part + '.json')
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('alb-') and fn.endswith('.json')): continue
            rec = L.R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r20-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            L.R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    d = data(); fill = P.solid_fill(doc)
    colors = dict((t['code'], PAL[i % len(PAL)]) for i, t in enumerate(d['types']))
    def body():
        if part == 'plans': return [level_plan(doc, lid, lc, ln, d, fill, colors) for lid, lc, ln in LEVELS]
        if part == 'types': return [type_ficha(doc, t, d, fill, colors) for t in d['types']]
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER ALB R20 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    L.R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
