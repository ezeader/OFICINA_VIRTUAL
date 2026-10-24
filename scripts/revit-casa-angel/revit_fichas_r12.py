# -*- coding: utf-8 -*-
"""R12: one sheet per structural element (EST-F-<code>): plan, elevation/section A, section B, axonometric.
Documentation only. Reinforcement is not designed here: every sheet says 'Armadura: a definir por el calculista'."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_fichas', os.path.join(ROOT, 'revit_structure_r11.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz
LEVEL_NAMES = S.LEVEL_NAMES
REBAR = u'Armadura: a definir por el calculista.'
FOOT = u'Ficha de elemento estructural: geometría nativa, cotas en metros (ancladas a extremos, no asociativas). Códigos como anotación. ' + REBAR

def section(doc, origin, right, look, x0, x1, y0, y1, vname):
    """Section looking along `look` (towards the viewer = -look side), cut plane through origin."""
    t = DB.Transform.Identity; t.Origin = origin; t.BasisX = right; t.BasisY = DB.XYZ.BasisZ; t.BasisZ = right.CrossProduct(DB.XYZ.BasisZ)
    bx = DB.BoundingBoxXYZ(); bx.Transform = t; bx.Min = DB.XYZ(x0, y0, -.6); bx.Max = DB.XYZ(x1, y1, .05)
    v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(L.SECTION_VFT)), bx)
    L.setup_view(doc, v, levels=True); v.Name = vname; v.CropBoxVisible = False
    try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
    except: pass
    return v, bx

def hide_other_levels(doc, v, level_id):
    others = [l.Id for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if l.Id != level_id]
    if others: v.HideElements(List[DB.ElementId](others))

def axo(doc, e, code, label, sector):
    b = e.get_BoundingBox(None); pad = .6 / M
    bx = DB.BoundingBoxXYZ(); bx.Min = DB.XYZ(b.Min.X - pad, b.Min.Y - pad, b.Min.Z - .3 / M); bx.Max = DB.XYZ(b.Max.X + pad, b.Max.Y + pad, b.Max.Z + .3 / M)
    ax = DB.View3D.CreateIsometric(doc, DB.ElementId(Int64(getattr(L, 'VIEW3D_VFT', 49559)))); L.setup_view(doc, ax)
    ax.Name = 'ADER EST R12 - ' + code + ' - AXO'; ax.SetSectionBox(bx); ax.IsSectionBoxActive = True
    d = DB.XYZ(-1, -1, -.75).Normalize(); right = d.CrossProduct(DB.XYZ.BasisZ).Normalize()
    ax.SetOrientation(DB.ViewOrientation3D(DB.XYZ.Zero, right.CrossProduct(d).Normalize(), d))
    L.D.fit3d(doc, ax)
    try: ax.SaveOrientationAndLock()
    except Exception: pass
    S.colorize(doc, ax, e, S.COLORS.get(code[:2], (25, 98, 143))); doc.Regenerate()
    c = (b.Min + b.Max) * .5
    L.axo_note(doc, ax, c, label, 'tag'); L.axo_note(doc, ax, DB.XYZ(b.Min.X, b.Min.Y, b.Min.Z), sector, 'room')
    return {'view': ax, 'box': ax.CropBox, 'title': code + u' · axonométrica', 'kind': 'axo', 'sector': sector, 'tags': [code], 'dims': [], 'elements': [eid(e)]}

def plan_item(doc, e, row, level, sector):
    v = S.new_plan(doc, level, S.bounds([e], level.Elevation, 1.0 / M), 'ADER EST R12 - ' + row['code'] + ' - PLANTA', depth=(-1.0 if row['kind'] in ('PL', 'LO') else -.3))
    S.colorize(doc, v, e, S.COLORS.get(row['kind'], (25, 98, 143)))
    dims = []; z = level.Elevation
    if isinstance(e, DB.Wall):
        a, b, d, n = S.wall_axis(e); mid = (a + b) * .5; w = e.Width
        L.tn(doc, v.Id, DB.XYZ(mid.X, mid.Y, z) + n * (.4 / M) - d * (.6 / M), row['label'], 'tag')
        f = L.AxisFrame(v, DB.XYZ(a.X, a.Y, v.Origin.Z), d, -n)
        dims.append(L.tick_dim(doc, f, row['code'] + u' largo', [0, a.DistanceTo(b)], True, .45 / M, tick=.08 / M))
        g = L.AxisFrame(v, DB.XYZ(b.X, b.Y, v.Origin.Z), n, d)      # thickness across the wall, beyond its end
        dims.append(L.tick_dim(doc, g, row['code'] + u' espesor', [-w / 2, w / 2], True, .45 / M, tick=.08 / M))
    else:
        bb = e.get_BoundingBox(None); c = (bb.Min + bb.Max) * .5
        L.tn(doc, v.Id, DB.XYZ(c.X, c.Y, z), row['label'], 'tag')
        fx = L.AxisFrame(v, DB.XYZ(bb.Min.X, bb.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY)
        fy = L.AxisFrame(v, DB.XYZ(bb.Min.X, bb.Min.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
        dims += [L.tick_dim(doc, fx, row['code'] + u' extensión X', [0, bb.Max.X - bb.Min.X], True, .4 / M),
                 L.tick_dim(doc, fy, row['code'] + u' extensión Y', [0, bb.Max.Y - bb.Min.Y], True, .4 / M)]
    L.tn(doc, v.Id, DB.XYZ(v.CropBox.Min.X + .2 / M, v.CropBox.Max.Y - .25 / M, z), sector, 'room')
    return {'view': v, 'box': v.CropBox, 'title': row['code'] + u' · planta', 'kind': 'plan', 'sector': sector, 'tags': [row['code']], 'dims': S.dims_out(dims), 'elements': [eid(e)]}

def wall_section(doc, e, row, sector):
    a, b, d, n = S.wall_axis(e); mid = (a + b) * .5; lev = L.level_of(doc, e)
    _, _, z0, z1, _ = L.extents(doc, e); w = e.Width
    origin = DB.XYZ(mid.X, mid.Y, lev.Elevation)
    v, bx = section(doc, origin, n, d, -(w / 2 + .9 / M), w / 2 + 1.1 / M, (z0 - lev.Elevation) - .5 / M, (z1 - lev.Elevation) + .9 / M, 'ADER EST R12 - ' + row['code'] + ' - CORTE')
    hide_other_levels(doc, v, e.LevelId); S.colorize(doc, v, e, S.COLORS[row['kind']]); doc.Regenerate()
    f = L.Frame(v); xs = sorted([f.x(mid + n * (w / 2)), f.x(mid - n * (w / 2))]); ylev = lev.Elevation - f.o.Z; yb = z0 - f.o.Z; yt = z1 - f.o.Z
    dims = [L.tick_dim(doc, f, row['code'] + u' espesor', xs, True, yt + .3 / M),
            L.tick_dim(doc, f, row['code'] + u' arranque + alto', L.uniq([ylev, yb, yt], tol=.005 / M), False, xs[1] + .45 / M)]
    L.tn(doc, v.Id, f.p(xs[0] - .8 / M, yt + .7 / M), row['code'] + u' · corte transversal', 'tag')
    L.tn(doc, v.Id, L.crop_corner(v, .06 / M, .06 / M), sector, 'room')
    return {'view': v, 'box': bx, 'title': row['code'] + u' · corte', 'kind': 'section', 'sector': sector, 'tags': [row['code']], 'dims': S.dims_out(dims), 'elements': [eid(e)]}

def floor_section(doc, e, row, sector, axis, tag):
    bb = e.get_BoundingBox(None); c = (bb.Min + bb.Max) * .5; lev = doc.GetElement(e.LevelId)
    right = DB.XYZ.BasisX if axis == 'X' else DB.XYZ.BasisY
    half = ((bb.Max.X - bb.Min.X) if axis == 'X' else (bb.Max.Y - bb.Min.Y)) / 2
    origin = DB.XYZ(c.X, c.Y, lev.Elevation)
    v, bx = section(doc, origin, right, None, -half - .8 / M, half + .8 / M, (bb.Min.Z - lev.Elevation) - .6 / M, (bb.Max.Z - lev.Elevation) + .9 / M, 'ADER EST R12 - ' + row['code'] + ' - CORTE ' + tag)
    hide_other_levels(doc, v, e.LevelId); S.colorize(doc, v, e, S.COLORS.get(row['kind'], (90, 140, 60))); doc.Regenerate()
    f = L.Frame(v); x0 = f.x(origin - right * half); x1 = f.x(origin + right * half); xs = sorted([x0, x1])
    yb = bb.Min.Z - f.o.Z; yt = bb.Max.Z - f.o.Z
    dims = [L.tick_dim(doc, f, row['code'] + u' ancho corte ' + tag, xs, True, yt + .35 / M),
            L.tick_dim(doc, f, row['code'] + u' espesor', [yb, yt], False, xs[1] + .4 / M)]
    L.tn(doc, v.Id, f.p(xs[0], yt + .7 / M), row['code'] + u' · corte ' + tag, 'tag')
    L.tn(doc, v.Id, L.crop_corner(v, .06 / M, .06 / M), sector, 'room')
    return {'view': v, 'box': bx, 'title': row['code'] + u' · corte ' + tag, 'kind': 'section', 'sector': sector, 'tags': [row['code']], 'dims': S.dims_out(dims), 'elements': [eid(e)]}

def data_lines(row):
    c2 = lambda v: (u'%.2f' % (v or 0)).replace(u'.', u',')
    lines = [row['label'], u(row['status'])]
    if row['kind'] in ('MH', 'VE'):
        lines.append(u'Largo ' + c2(row.get('length_m')) + u' m · Alto ' + c2(row.get('height_m')) + u' m · Espesor ' + c2(row.get('thickness_m')) + u' m · Área ' + c2(row.get('area_m2')) + u' m² · Volumen ' + c2(row.get('volume_m3')) + u' m³')
    else:
        lines.append(u'Área ' + c2(row.get('area_m2')) + u' m² · Espesor total ' + c2(row.get('thickness_m')) + u' m · Capa de H° ' + c2(row.get('concreteLayer_m')) + u' m')
    lines.append(REBAR)
    return lines

def ficha(doc, row, opens):
    e = el(doc, row['id'])
    if e is None: return None
    lid = int(e.LevelId.Value) if int(e.LevelId.Value) in LEVEL_NAMES else row['sheetLevel']
    level = el(doc, lid); sector = u'Sector: ' + LEVEL_NAMES.get(row['sheetLevel'], u(row['level']))
    items = [plan_item(doc, e, row, level, sector)]
    if isinstance(e, DB.Wall):
        el_item = S.wall_elevation(doc, e, row, opens, 'ADER EST R12 - ' + row['code'] + ' - ALZADO'); el_item['title'] = row['code'] + u' · vista (alzado)'; el_item['data'] = None
        items += [el_item, wall_section(doc, e, row, sector)]
    else:
        items += [floor_section(doc, e, row, sector, 'X', 'A'), floor_section(doc, e, row, sector, 'Y', 'B')]
    items.append(axo(doc, e, row['code'], row['label'], sector))
    items[0]['data'] = data_lines(row)
    sheet = S.lay_sheet(doc, 'EST-F-' + row['code'], u'Ficha ' + row['code'], row['label'] + u' · ' + REBAR, items, FOOT, plan_region=True)
    sheet.update(element=row['code'], elementId=str(row['id']), kind='element', elementKind=row['kind'], level=LEVEL_NAMES.get(row['sheetLevel'], u(row['level'])), sector=sector)
    return sheet

def reset(doc, part):
    path = os.path.join(OUT, 'est-f-' + part + '.json'); rec = L.R1.read(path)
    ids = [s['sheetId'] for s in rec['sheets']] + [v['id'] for s in rec['sheets'] for v in s['views']]
    def body():
        for i in ids:
            e = el(doc, i)
            if e is not None and (isinstance(e, DB.ViewSheet) and e.SheetNumber.startswith('EST-F-') or isinstance(e, DB.View) and name(e).startswith('ADER EST R12')): doc.Delete(e.Id)
        return len(ids)
    n, checked = L.guarded(doc, 'ADER EST R12 - reset ' + part, body)
    os.remove(path); doc.Save(); return {'status': 'success', 'deleted': n}

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'est-f-' + part + '.json')
    if job.get('reset'): return reset(doc, part)
    if os.path.exists(path):
        rec = L.R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': len(rec['sheets'])}
    data = S.plan_data(); opens = dict((i['id'], i['code']) for i in L.read('plan')['items'])
    codes = job['codes']
    rows = [r for r in data['elements'] if r['code'] in codes]
    def body():
        out = []
        for r in rows:
            s = ficha(doc, r, opens)
            if s: out.append(s)
        return out
    sheets, checked = L.guarded(doc, 'ADER EST R12 - fichas ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    L.R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
