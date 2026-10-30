# -*- coding: utf-8 -*-
"""R24: Equipamiento fijo, documentation only.
Codes: PL placares · MU muebles fijos (TV, pared, vinoteca, mesas de luz) · VA vanitorios · ME mesadas / bajomesadas ·
LV lavaderos · MA mamparas · EQ equipos de cocina. Fijo = familia in situ (carpintería) + mamparas + equipos.
Parts: probe / inventory (read-only), plans, fichas, index, export, reset."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
X = imp.load_source('ader_ext_r23_for_eq', os.path.join(ROOT, 'revit_ext_r23.py'))
S = X.S; L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; R1 = L.R1
c2 = X.c2; item = X.item
RUBRO = u'EQUIPAMIENTO FIJO'
PRE = 'ADER EQ R24 - '
FOOT = u'Equipamiento fijo: geometría nativa (familias in situ de carpintería, mamparas y equipos). Medidas de caja envolvente del modelo; cotas en metros (no asociativas). Herrajes, materiales de fabricación y despiece: a definir con el carpintero.'
LEVELS = [(311, u'00. Planta Baja', 'PB'), (694, u'01. Planta Alta', 'PA'), (353988, u'02. Planta Entrepiso', 'PE')]
KIND_OF = [('PL', [u'Armario1', u'Armario3', u'Armario4', u'Armario5', u'Armario6']), ('MU', [u'Armario/ tele', u'Mueble Pared', u'Mueble Vinoteca', u'Mesa de luz']),
           ('VA', [u'Bacha Baño Ppal', u'Bacha doble']), ('ME', [u'Mesada', u'Cajonera']), ('LV', [u'Lavadero']),
           ('MA', [u'Mampara', u'Shower-screens']), ('EQ', [u'DualFuelRange', u'WallRangehood', u'Heladera'])]
NAMES = {'PL': u'placard', 'MU': u'mueble fijo', 'VA': u'vanitorio', 'ME': u'mesada', 'LV': u'lavadero', 'MA': u'mampara', 'EQ': u'equipo'}
EQN = {u'DualFuelRange': u'cocina (horno + anafe)', u'WallRangehood': u'campana', u'Heladera': u'heladera'}
COL = {'PL': (25, 98, 143), 'MU': (90, 140, 60), 'VA': (196, 98, 16), 'ME': (150, 40, 120), 'LV': (196, 98, 16), 'MA': (120, 120, 120), 'EQ': (200, 30, 30)}
FICHA = ('PL', 'MU', 'VA', 'ME', 'LV')
CATS = ['OST_Casework', 'OST_Furniture', 'OST_SpecialityEquipment', 'OST_GenericModel', 'OST_PlumbingFixtures', 'OST_MechanicalEquipment']

def fam_type(doc, e):
    t = doc.GetElement(e.GetTypeId())
    return (u(t.FamilyName) if t is not None and hasattr(t, 'FamilyName') else u''), (u(name(t)) if t else u'')

def level_for(z):
    return LEVELS[0] if z < 2.9 / M else (LEVELS[1] if z < 5.9 / M else LEVELS[2])

def room_for(doc, e):
    b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5; lv = level_for(b.Min.Z + .05 / M)
    z = el(doc, lv[0]).Elevation
    for dz in (.5, 1.2, .2):
        r = doc.GetRoomAtPoint(DB.XYZ(c.X, c.Y, z + dz / M))
        if r and r.LevelId.IntegerValue == lv[0]: return u'%s · %s' % (u(r.Number), u(name(r)))
    for dz in (.5, 1.2):
        r = doc.GetRoomAtPoint(DB.XYZ(c.X, c.Y, z + dz / M))
        if r: return u'%s · %s' % (u(r.Number), u(name(r)))
    return None

def kind_for(doc, e):
    fam, typ = fam_type(doc, e)
    for k, keys in KIND_OF:
        for key in keys:
            if fam.startswith(key) or key in fam:
                if k in ('PL', 'MU', 'VA', 'ME', 'LV') and isinstance(e, DB.FamilyInstance) and not e.Symbol.Family.IsInPlace and fam != u'Cajonera' and fam != u'Bacha doble': return None
                return k
    return None

def mats(doc, e):
    try: return sorted(set(u(name(doc.GetElement(i))) for i in e.GetMaterialIds(False)))
    except Exception: return []

def inventory(doc):
    rows = []; loose = []
    for cat in CATS:
        for e in DB.FilteredElementCollector(doc).OfCategory(getattr(DB.BuiltInCategory, cat)).WhereElementIsNotElementType():
            b = e.get_BoundingBox(None)
            if b is None: continue
            k = kind_for(doc, e); fam, typ = fam_type(doc, e)
            if k is None:
                if cat in ('OST_Furniture', 'OST_GenericModel') and u'Pase' not in fam and u'Agua' not in fam:
                    loose.append({'id': eid(e), 'family': fam, 'type': typ, 'level': level_for(b.Min.Z + .05 / M)[2]})
                continue
            lv = level_for(b.Min.Z + .05 / M); z = el(doc, lv[0]).Elevation
            dx, dy, dz = (b.Max.X - b.Min.X) * M, (b.Max.Y - b.Min.Y) * M, (b.Max.Z - b.Min.Z) * M
            rows.append({'id': eid(e), 'kind': k, 'family': fam, 'type': typ, 'level': lv[1], 'levelCode': lv[2], 'levelId': lv[0], 'room': room_for(doc, e),
                         'width_m': max(dx, dy), 'depth_m': min(dx, dy), 'height_m': dz, 'bottom_m': (b.Min.Z - z) * M, 'top_m': (b.Max.Z - z) * M,
                         'inPlace': isinstance(e, DB.FamilyInstance) and e.Symbol.Family.IsInPlace, 'materials': mats(doc, e), 'cx': (b.Min.X + b.Max.X) / 2, 'cy': (b.Min.Y + b.Max.Y) / 2})
    order = dict((k, i) for i, (k, _) in enumerate(KIND_OF))
    rows.sort(key=lambda r: (order[r['kind']], r['levelCode'], -round(r['cy'], 0), r['cx']))
    n = {}
    for r in rows:
        n[r['kind']] = n.get(r['kind'], 0) + 1; r['code'] = '%s-%02d' % (r['kind'], n[r['kind']])
        what = NAMES[r['kind']]
        if r['kind'] == 'EQ': what = [v for k2, v in EQN.items() if k2 in r['family']][0]
        if r['kind'] == 'MU':
            what = u'mesa de luz' if u'Mesa de luz' in r['family'] else (u'vinoteca' if u'Vinoteca' in r['family'] else (u'rack de TV' if u'tele' in r['family'] else u'mueble de pared'))
        if r['kind'] == 'ME' and r['family'] == u'Cajonera': what = u'bajomesada con cajones'
        r['what'] = what
        r['label'] = u'%s · %s · %s × %s × %s' % (r['code'], what, c2(r['width_m']), c2(r['depth_m']), c2(r['height_m']))
        r['status'] = u'%s · %s%s' % (r['room'] or u'sin local', r['level'], u' · in situ' if r['inPlace'] else u'')
        r['bbox'] = R1.bbox(el(doc, r['id']))
    return {'elements': rows, 'loose': loose}

# ---------------------------------------------------------------- views

def show(v):
    for c in (DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_Casework, DB.BuiltInCategory.OST_SpecialityEquipment, DB.BuiltInCategory.OST_PlumbingFixtures):
        try: v.SetCategoryHidden(DB.ElementId(c), False)
        except Exception: pass

def front(doc, e, lev_z):
    """Unit normal of the long side looking from the room into the element."""
    b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5; dx = b.Max.X - b.Min.X; dy = b.Max.Y - b.Min.Y
    cands = [DB.XYZ(0, 1, 0), DB.XYZ(0, -1, 0)] if dx >= dy else [DB.XYZ(1, 0, 0), DB.XYZ(-1, 0, 0)]
    half = (dy if dx >= dy else dx) / 2
    for n in cands:
        p = DB.XYZ(c.X, c.Y, lev_z + 1.0 / M) + n * (half + .5 / M)
        if doc.GetRoomAtPoint(p) is not None: return n, half, (dx if dx >= dy else dy) / 2
    return cands[0], half, (dx if dx >= dy else dy) / 2

flips = []

def elevation(doc, e, r, lev, sector):
    b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5; z = lev.Elevation
    n, half, w2 = front(doc, e, z); right = DB.XYZ.BasisZ.CrossProduct(n)
    o = DB.XYZ(c.X, c.Y, z) + n * (half + .3 / M)
    v, bx = X.section(doc, o, right, -w2 - .6 / M, w2 + .6 / M, (b.Min.Z - z) - .3 / M, (b.Max.Z - z) + .5 / M, 2 * half + .6 / M, PRE + r['code'] + ' - ALZADO')
    if v.ViewDirection.DotProduct(n) < 0:   # Revit flipped the section: rebuild it looking from the room side
        doc.Delete(v.Id)
        t = bx.Transform; t2 = DB.Transform.Identity; t2.Origin = t.Origin; t2.BasisX = -t.BasisX; t2.BasisY = t.BasisY; t2.BasisZ = -t.BasisZ
        b2 = DB.BoundingBoxXYZ(); b2.Transform = t2; b2.Min = DB.XYZ(-bx.Max.X, bx.Min.Y, -bx.Max.Z); b2.Max = DB.XYZ(-bx.Min.X, bx.Max.Y, -bx.Min.Z)
        v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(L.SECTION_VFT)), b2); bx = b2
        L.setup_view(doc, v, levels=True); v.Name = PRE + r['code'] + ' - ALZADO'; v.CropBoxVisible = False
        try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
        except: pass
    flips.append((r['code'], round(v.ViewDirection.X, 2), round(v.ViewDirection.Y, 2), round(n.X), round(n.Y)))
    show(v); S.colorize(doc, v, e, COL[r['kind']]); doc.Regenerate(); f = L.Frame(v)
    xs = sorted([f.x(c - right * w2), f.x(c + right * w2)])
    ds = [L.tick_dim(doc, f, r['code'] + u' ancho', xs, True, b.Max.Z - f.o.Z + .25 / M, tick=.08 / M),
          L.tick_dim(doc, f, r['code'] + u' nivel + alto', L.uniq([z - f.o.Z, b.Min.Z - f.o.Z, b.Max.Z - f.o.Z], tol=.005 / M), False, xs[1] + .35 / M, tick=.08 / M)]
    L.tn(doc, v.Id, f.p((xs[0] + xs[1]) / 2 - .3 / M, (b.Min.Z + b.Max.Z) / 2 - f.o.Z), r['code'], 'tag')
    L.tn(doc, v.Id, L.crop_corner(v, .06 / M, .06 / M), sector, 'room')
    return item(v, bx, r['code'] + u' · alzado frontal', 'elevation', sector, [r['code']], ds, [r['id']])

def plan(doc, e, r, lev, sector):
    v = S.new_plan(doc, lev, S.bounds([e], lev.Elevation, .9 / M), PRE + r['code'] + ' - PLANTA', depth=-.3)
    vr = v.GetViewRange(); vr.SetOffset(DB.PlanViewPlane.CutPlane, max(1.3, r['top_m'] + .1) / M)
    vr.SetOffset(DB.PlanViewPlane.TopClipPlane, max(4.0, r['top_m'] + .5) / M); v.SetViewRange(vr)
    show(v); S.colorize(doc, v, e, COL[r['kind']])
    b = e.get_BoundingBox(None); z = lev.Elevation
    fx = L.AxisFrame(v, DB.XYZ(b.Min.X, b.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY); fy = L.AxisFrame(v, DB.XYZ(b.Min.X, b.Min.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    ds = [L.tick_dim(doc, fx, r['code'] + u' en X', [0, b.Max.X - b.Min.X], True, .3 / M, tick=.08 / M), L.tick_dim(doc, fy, r['code'] + u' en Y', [0, b.Max.Y - b.Min.Y], True, .3 / M, tick=.08 / M)]
    L.tn(doc, v.Id, DB.XYZ((b.Min.X + b.Max.X) / 2 - .2 / M, (b.Min.Y + b.Max.Y) / 2, z), r['code'], 'tag')
    lines = [r['label'], u'Local: ' + (r['room'] or u'sin local') + u' · ' + r['level'], u'Familia: ' + r['family'] + (u' (in situ)' if r['inPlace'] else u''),
             u'Desde nivel: +%s a +%s' % (c2(r['bottom_m']), c2(r['top_m'])), u'Materiales: ' + (u', '.join(r['materials'][:4]) or u'sin material'), u'Herrajes y terminación: a definir.']
    return item(v, v.CropBox, r['code'] + u' · planta', 'plan', sector, [r['code']], ds, [r['id']], lines)

def general(doc, rows, lid, lname, lcode, number):
    lev = el(doc, lid); z = lev.Elevation; es = [el(doc, r['id']) for r in rows]
    v = S.new_plan(doc, lev, S.bounds(es, z, 1.5 / M), PRE + 'PLANTA ' + lcode, depth=-.3)
    vr = v.GetViewRange(); vr.SetOffset(DB.PlanViewPlane.CutPlane, 2.0 / M); v.SetViewRange(vr); show(v)
    for r, e in zip(rows, es):
        S.colorize(doc, v, e, COL[r['kind']]); b = e.get_BoundingBox(None)
        L.tn(doc, v.Id, DB.XYZ((b.Min.X + b.Max.X) / 2 - .15 / M, (b.Min.Y + b.Max.Y) / 2, z), r['code'], 'tag')
    S.room_labels(doc, v, lid, z)
    sector = u'Equipamiento · ' + lname
    lines = []
    for k, _ in KIND_OF:
        rs = [r for r in rows if r['kind'] == k]
        if rs: lines.append(u'%s (%d): %s' % (NAMES[k].capitalize(), len(rs), u', '.join(r['code'] for r in rs)))
    it = item(v, v.CropBox, u'Equipamiento fijo · ' + lname, 'plan', sector, [r['code'] for r in rows], [], [r['id'] for r in rows], lines)
    sub = u'%d elementos fijos · ' % len(rows) + u' · '.join(u'%s %d' % (k, len([r for r in rows if r['kind'] == k])) for k, _ in KIND_OF if any(r['kind'] == k for r in rows))
    return dict(S.lay_sheet(doc, number, u'Planta · ' + lname, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Equipamiento · ' + number[3:]), kind='general', level=lname, sector=sector)

def plans_part(doc, d):
    rows = d['elements']; out = []
    for k, (lid, lname, lcode) in enumerate(LEVELS, 1):
        rs = [r for r in rows if r['levelId'] == lid]
        if rs: out.append(general(doc, rs, lid, lname, lcode, 'EQ-%02d' % k))
    return out

def fichas_part(doc, d, kinds):
    out = []
    for r in d['elements']:
        if r['kind'] not in kinds: continue
        e = el(doc, r['id']); lev = el(doc, r['levelId']); sector = (r['room'] or u'sin local') + u' · ' + r['levelCode']
        p = plan(doc, e, r, lev, sector); ev = elevation(doc, e, r, lev, sector)
        ax = X.axo(doc, [e], r['code'], r['label'], sector, COL[r['kind']]); ax['title'] = r['code'] + u' · axonométrica'
        ax['view'].Name = PRE + r['code'] + ' - AXO'; show(ax['view'])
        s = S.lay_sheet(doc, 'EQ-F-' + r['code'], u'Ficha · ' + r['code'] + u' ' + r['what'], r['label'], [p, ev, ax], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Equipamiento · ' + r['code'])
        out.append(dict(s, kind='element', element=r['code'], elementId=str(r['id']), elementKind=r['kind'], level=r['level'], sector=sector))
    return out

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'EQ-00'; sheet.Name = u'Equipamiento · índice'
    head = u'CASA ÁNGEL · EQUIPAMIENTO FIJO · ÍNDICE Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'EQ-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Equipamiento', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'eq-' + part + '.json')
    if part == 'inventory':
        d = inventory(doc); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'eq-plan.json'), d)
        return {'status': 'success', 'elements': [(r['code'], r['label'], r['status']) for r in d['elements']], 'loose': len(d['loose'])}
    if part == 'fronts':
        d = L.read('eq-plan'); res = []
        for r in d['elements']:
            e = el(doc, r['id']); z = el(doc, r['levelId']).Elevation; b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
            n, half, w2 = front(doc, e, z)
            tests = []
            for m in [DB.XYZ(1,0,0), DB.XYZ(-1,0,0), DB.XYZ(0,1,0), DB.XYZ(0,-1,0)]:
                p = DB.XYZ(c.X, c.Y, z + 1.0 / M) + m * (half + .5 / M); rr = doc.GetRoomAtPoint(p)
                tests.append(u(rr.Number) if rr else None)
            res.append((r['code'], [round(n.X), round(n.Y)], tests))
        return {'status': 'success', 'fronts': res}
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('eq-') and fn.endswith('.json')): continue
            rec = R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                if s.get('exported') and not job.get('all'): done.append(s['number']); continue
                opts.FileName = 'r24-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': len(done)}
    if job.get('resetPart'):
        rec = R1.read(path)
        def body():
            n = 0
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [v['id'] for v in sh['views']]:
                    if el(doc, i) is not None: doc.Delete(el(doc, i).Id); n += 1
            return n
        n, checked = L.guarded(doc, 'ADER EQ R24 - reset ' + part, body)
        os.remove(path); doc.Save(); return {'status': 'success', 'deleted': n}
    if job.get('reset'):
        def body():
            ids = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if (isinstance(v, DB.ViewSheet) and v.SheetNumber.startswith('EQ-')) or name(v).startswith(PRE)]
            n = 0
            for i in ids:
                if doc.GetElement(i) is not None: doc.Delete(i); n += 1
            return n
        n, checked = L.guarded(doc, 'ADER EQ R24 - reset', body)
        for fn in os.listdir(OUT):
            if fn.startswith('eq-') and fn.endswith('.json') and fn not in ('eq-plan.json', 'eq-probe.json'): os.remove(os.path.join(OUT, fn))
        doc.Save(); return {'status': 'success', 'deleted': n}
    if os.path.exists(path):
        rec = R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    d = L.read('eq-plan')
    for r in d['elements']:
        for k in ('label', 'status', 'type', 'family', 'room', 'what', 'level'):
            if r.get(k): r[k] = R1.clean(r[k])
        r['materials'] = [R1.clean(m) for m in r['materials']]
    def body():
        if part == 'plans': return plans_part(doc, d)
        if part.startswith('fichas-'): return fichas_part(doc, d, part[7:].split('+'))
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER EQ R24 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
