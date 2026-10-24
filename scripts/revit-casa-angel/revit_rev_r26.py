# -*- coding: utf-8 -*-
"""R26: Revestimientos (PROPUESTA a confirmar), documentation only — no geometry or wall layers are changed.
Hypotheses: baños/toilettes revestidos 0–2,40 m; cocina y lavadero franja 0,60 m sobre mesada (0,90–1,50); resto pintado 0–2,60 m;
fachada hormigón visto sin revestimiento. Codes: RV-<nivel>-nn local revestido · RF-nn franja · PI-<nivel>-nn local pintado.
Parts: inventory (read-only), plans, fichas, index, export, reset/resetPart."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
X = imp.load_source('ader_ext_r23_for_rev', os.path.join(ROOT, 'revit_ext_r23.py'))
S = X.S; L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; R1 = L.R1
c2 = X.c2; item = X.item
RUBRO = u'REVESTIMIENTOS'
PRE = 'ADER RV R26 - '
H_WET, H_PAINT, BAND = 2.40, 2.60, (0.90, 1.50)
FOOT = u'PROPUESTA A CONFIRMAR · Revestimientos: baños y toilettes revestidos de 0,00 a 2,40 m; cocina y lavadero franja de 0,60 m sobre mesada (0,90 a 1,50 m); resto de muros pintado hasta 2,60 m; fachada de hormigón visto sin revestimiento. Superficies por cara terminada del local con vanos descontados. Material y formato a definir. El modelo no se modificó.'
LEVELS = {311: (u'00. Planta Baja', 'PB'), 694: (u'01. Planta Alta', 'PA'), 353988: (u'02. Planta Entrepiso', 'PE')}
OPEN_TYPES = (u'Puerta Arco', u'Vano', u'Ventanal', u'Vent. ')
COL = {'RV':(25, 98, 143), 'RF': (196, 98, 16), 'PI': (150, 150, 150)}

def is_wet(nm): return any(k in nm for k in (u'Baño', u'Toilette'))
def band_kind(nm): return u'Cocina' if nm.startswith(u'Cocina') else (u'Lavadero' if nm.startswith(u'Lavadero') else None)

def xy(p): return [p.X, p.Y, p.Z]
def P(a): return DB.XYZ(a[0], a[1], a[2])

def overlap(ops, length, z0, z1):
    s = 0.0
    for o in ops:
        dl = min(o['t1'], length) - max(o['t0'], 0); dz = min(o['z1'], z1) - max(o['z0'], z0)
        if dl > 0 and dz > 0: s += dl * dz
    return s

def faces_of(doc, room, lev_z):
    opt = DB.SpatialElementBoundaryOptions(); opt.SpatialElementBoundaryLocation = DB.SpatialElementBoundaryLocation.Finish
    raw = []
    for loop in room.GetBoundarySegments(opt):
        for seg in loop:
            c = seg.GetCurve(); a, b = c.GetEndPoint(0), c.GetEndPoint(1)
            raw.append({'a': a, 'b': b, 'arc': not isinstance(c, DB.Line), 'len': c.Length, 'eid': seg.ElementId.IntegerValue})
    # merge consecutive collinear straight segments into faces
    faces = []
    for s in raw:
        d = DB.XYZ(s['b'].X - s['a'].X, s['b'].Y - s['a'].Y, 0)
        if d.GetLength() < 1e-6: continue
        d = d.Normalize()
        if faces and not s['arc'] and not faces[-1]['arc']:
            f = faces[-1]; fd = DB.XYZ(f['b'].X - f['a'].X, f['b'].Y - f['a'].Y, 0).Normalize()
            if fd.DotProduct(d) > .999 and f['b'].DistanceTo(s['a']) < .01:
                f['b'] = s['b']; f['len'] += s['len']; f['segs'].append(s); continue
        faces.append({'a': s['a'], 'b': s['b'], 'arc': s['arc'], 'len': s['len'], 'segs': [s]})
    out = []
    for f in faces:
        a, b = f['a'], f['b']; d = DB.XYZ(b.X - a.X, b.Y - a.Y, 0).Normalize(); n = DB.XYZ(-d.Y, d.X, 0)
        mid = (a + b) * .5
        if not room.IsPointInRoom(DB.XYZ(mid.X, mid.Y, lev_z + 1.0 / M) + n * (.25 / M)): n = -n
        ops = []; glazed = 0.0; elems = []
        for s in f['segs']:
            e = doc.GetElement(DB.ElementId(Int64(s['eid']))) if s['eid'] > 0 else None
            if e is not None: elems.append(s['eid'])
            open_type = isinstance(e, DB.Wall) and any(k in u(name(e.WallType)) for k in OPEN_TYPES)
            if e is None or not isinstance(e, DB.Wall) or open_type or e.WallType.Kind == DB.WallKind.Curtain:
                # room separation line, curtain wall or wall used as an opening (arch / vano / ventanal): no finish
                t0 = (s['a'] - a).DotProduct(d); t1 = (s['b'] - a).DotProduct(d)
                ops.append({'id': s['eid'] if e is not None else 0, 't0': min(t0, t1), 't1': max(t0, t1), 'z0': 0.0, 'z1': 9.0 / M, 'curtain': True,
                            'reason': u'separación' if e is None or not isinstance(e, DB.Wall) else (u'vano' if open_type else u'muro cortina')}); continue
            if False:
                t0 = (s['a'] - a).DotProduct(d); t1 = (s['b'] - a).DotProduct(d)
                ops.append({'id': s['eid'], 't0': min(t0, t1), 't1': max(t0, t1), 'z0': 0.0, 'z1': 9.0 / M, 'curtain': True}); continue
            if not isinstance(e, DB.Wall): continue
            for iid in e.FindInserts(True, False, True, True):
                ins = doc.GetElement(iid)
                if ins is None or ins.get_BoundingBox(None) is None: continue
                try: p0, p1, z0, z1, _ = L.extents(doc, ins)
                except Exception: continue
                t0 = (p0 - a).DotProduct(d); t1 = (p1 - a).DotProduct(d)
                lo, hi = min(t0, t1), max(t0, t1)
                if hi <= 0 or lo >= f['len']: continue
                if any(o['id'] == iid.IntegerValue for o in ops): continue
                ops.append({'id': iid.IntegerValue, 't0': lo, 't1': hi, 'z0': z0 - lev_z, 'z1': z1 - lev_z, 'curtain': isinstance(ins, DB.Wall)})
        out.append({'a': xy(a), 'b': xy(b), 'n': [n.X, n.Y, 0], 'arc': f['arc'], 'len': f['len'], 'elements': elems, 'openings': ops})
    return out

def inventory(doc):
    eq = L.read('eq-plan')['elements']
    rows = []
    for room in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if room.Area <= 0 or u'Ascensor' in u(name(room)): continue
        lid = room.LevelId.IntegerValue; lev_z = doc.GetElement(room.LevelId).Elevation
        nm = u(name(room)); faces = faces_of(doc, room, lev_z)
        bk = band_kind(nm); wet = is_wet(nm)
        # franjas: items of Equipamiento against a face of this room
        bands = []
        if bk:
            its = [r for r in eq if (r['kind'] in ('ME', 'LV') or (r['kind'] == 'EQ' and u'cocina' in r['what'])) and r['room'] and nm in R1.clean(r['room'])]
            for it in its:
                e = el(doc, it['id']); bb = e.get_BoundingBox(None); c = (bb.Min + bb.Max) * .5
                corners = [DB.XYZ(x_, y_, 0) for x_ in (bb.Min.X, bb.Max.X) for y_ in (bb.Min.Y, bb.Max.Y)]
                for k, f in enumerate(faces):
                    if f['arc']: continue
                    a = P(f['a']); b = P(f['b']); d = DB.XYZ(b.X - a.X, b.Y - a.Y, 0).Normalize(); n = P(f['n'])
                    dist = abs((DB.XYZ(c.X, c.Y, 0) - DB.XYZ(a.X, a.Y, 0)).DotProduct(n))
                    depth = min(bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y)
                    if dist > depth / 2 + .2 / M: continue
                    ts = [(q - DB.XYZ(a.X, a.Y, 0)).DotProduct(d) for q in corners]
                    t0, t1 = max(0, min(ts)), min(f['len'], max(ts))
                    if t1 - t0 > .2 / M: bands.append({'face': k, 't0': t0, 't1': t1, 'item': it['code']})
            # merge intervals per face
            merged = []
            for k in sorted(set(x['face'] for x in bands)):
                iv = sorted([(x['t0'], x['t1'], x['item']) for x in bands if x['face'] == k])
                cur = [iv[0][0], iv[0][1], [iv[0][2]]]
                for t0, t1, cd in iv[1:]:
                    if t0 <= cur[1] + .05 / M: cur[1] = max(cur[1], t1); cur[2].append(cd)
                    else: merged.append({'face': k, 't0': cur[0], 't1': cur[1], 'items': cur[2]}); cur = [t0, t1, [cd]]
                merged.append({'face': k, 't0': cur[0], 't1': cur[1], 'items': cur[2]})
            bands = merged
        rev = paint = gross_rev = gross_paint = band_m2 = 0.0
        for k, f in enumerate(faces):
            Lf = f['len']
            if wet:
                g = Lf * H_WET / M; net = g - overlap(f['openings'], Lf, 0, H_WET / M)
                f['rev_m2'] = max(0, net) * M * M; f['revGross_m2'] = g * M * M
                gp = Lf * (H_PAINT - H_WET) / M; f['paint_m2'] = max(0, gp - overlap(f['openings'], Lf, H_WET / M, H_PAINT / M)) * M * M
            else:
                g = Lf * H_PAINT / M; net = g - overlap(f['openings'], Lf, 0, H_PAINT / M)
                bm = 0.0
                for bd in [x for x in bands if x['face'] == k]:
                    seg = [{'t0': o['t0'] - bd['t0'], 't1': o['t1'] - bd['t0'], 'z0': o['z0'], 'z1': o['z1']} for o in f['openings']]
                    bl = bd['t1'] - bd['t0']; ba = bl * (BAND[1] - BAND[0]) / M - overlap(seg, bl, BAND[0] / M, BAND[1] / M)
                    bd['m2'] = max(0, ba) * M * M; bd['len_m'] = bl * M; bm += bd['m2']
                f['band_m2'] = bm; f['paint_m2'] = max(0, net) * M * M - bm; f['rev_m2'] = 0.0
            f['opening_m2'] = overlap(f['openings'], Lf, 0, (H_WET if wet else H_PAINT) / M) * M * M
            rev += f['rev_m2']; paint += f['paint_m2']; band_m2 += f.get('band_m2', 0)
        lv = LEVELS.get(lid, (u'?', '?'))
        rows.append({'id': eid(room), 'number': u(room.Number), 'name': nm, 'level': lv[0], 'levelCode': lv[1], 'levelId': lid, 'area_m2': room.Area * M * M, 'perimeter_m': room.Perimeter * M,
                     'wet': wet, 'bandKind': bk, 'faces': faces, 'bands': bands, 'rev_m2': rev, 'paint_m2': paint, 'band_m2': band_m2,
                     'openings_m2': sum(f['opening_m2'] for f in faces), 'center': xy(room.Location.Point) if isinstance(room.Location, DB.LocationPoint) else None})
    rows.sort(key=lambda r: (r['levelCode'] != 'PB', r['levelCode'] != 'PA', r['number']))
    n = {}
    for r in rows:
        k = 'RV' if r['wet'] else 'PI'; key = k + r['levelCode']; n[key] = n.get(key, 0) + 1
        r['kind'] = k; r['code'] = '%s-%s-%02d' % (k, r['levelCode'], n[key])
    nb = 0
    for r in rows:
        for bd in r['bands']:
            nb += 1; bd['code'] = 'RF-%02d' % nb
    return {'rooms': rows, 'hypotheses': {'wet_h': H_WET, 'paint_h': H_PAINT, 'band': BAND}}

# ---------------------------------------------------------------- drawing

def line(doc, v, p0, p1, rgb, w=6):
    dc = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(p0, p1))
    ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineColor(DB.Color(*rgb)); ov.SetProjectionLineWeight(w)
    v.SetElementOverrides(dc.Id, ov); return dc

def rlabel(r): return u'%s · %s · %s' % (r['number'], r['name'], r['levelCode'])

def tag_text(r):
    if r['kind'] == 'RV': return u'%s · %s\nrevestimiento %s m²' % (r['code'], r['name'], c2(r['rev_m2']))
    t = u'%s · %s\npintura %s m²' % (r['code'], r['name'], c2(r['paint_m2']))
    if r['bands']: t += u'\nfranja %s m² (%s)' % (c2(r['band_m2']), u', '.join(b['code'] for b in r['bands']))
    return t

def draw_faces(doc, v, r, z, inset=.06):
    for k, f in enumerate(r['faces']):
        if f['arc'] or f['len'] < .05 / M: continue
        a, b, n = P(f['a']), P(f['b']), P(f['n'])
        if r['kind'] == 'RV':
            line(doc, v, DB.XYZ(a.X, a.Y, z) + n * (inset / M), DB.XYZ(b.X, b.Y, z) + n * (inset / M), COL['RV'], 8)
        for bd in [x for x in r['bands'] if x['face'] == k]:
            d = (DB.XYZ(b.X, b.Y, 0) - DB.XYZ(a.X, a.Y, 0)).Normalize()
            q0 = DB.XYZ(a.X, a.Y, z) + d * bd['t0'] + n * (inset / M); q1 = DB.XYZ(a.X, a.Y, z) + d * bd['t1'] + n * (inset / M)
            line(doc, v, q0, q1, COL['RF'], 10)

def general(doc, rows, lid, number):
    lev = el(doc, lid); z = lev.Elevation; lname, lcode = LEVELS[lid]
    rooms = [el(doc, r['id']) for r in rows]
    v = S.new_plan(doc, lev, S.bounds(rooms, z, 1.2 / M), PRE + 'PLANTA ' + lcode, depth=-.3)
    zz = v.Origin.Z
    for r in rows:
        draw_faces(doc, v, r, zz)
        c = P(r['center']) if r['center'] else None
        if c: L.tn(doc, v.Id, DB.XYZ(c.X - .8 / M, c.Y, z), tag_text(r), 'tag' if (r['kind'] == 'RV' or r['bands']) else 'room')
    rv = [r for r in rows if r['kind'] == 'RV']
    sub = u'PROPUESTA A CONFIRMAR · revestimiento %s m² en %d locales · franjas %s m² · pintura %s m² · vanos descontados' % (c2(sum(r['rev_m2'] for r in rv)), len(rv), c2(sum(r['band_m2'] for r in rows)), c2(sum(r['paint_m2'] for r in rows)))
    sector = u'Revestimientos · ' + lname
    lines = [u'Azul: muros revestidos 0,00–2,40 (RV).', u'Naranja: franja 0,90–1,50 sobre mesada (RF).', u'Resto: pintura 0,00–2,60 (PI).']
    it = item(v, v.CropBox, u'Revestimientos · ' + lname, 'plan', sector, [r['code'] for r in rows], [], [r['id'] for r in rows], lines)
    return dict(S.lay_sheet(doc, number, u'Planta · ' + lname, sub, [it], FOOT, rubro=RUBRO, sheet_name=u'Revestimientos · ' + number[3:]), kind='general', level=lname, sector=sector)

def face_elev(doc, r, k, f, lev, sector, wet):
    z = lev.Elevation; a, b, n = P(f['a']), P(f['b']), P(f['n'])
    a = DB.XYZ(a.X, a.Y, z); b = DB.XYZ(b.X, b.Y, z); mid = (a + b) * .5; half = f['len'] / 2
    right = DB.XYZ.BasisZ.CrossProduct(n); o = mid + n * (.5 / M); top = (2.9 if wet else 2.0) / M
    vname = PRE + r['code'] + ' - C%d' % (k + 1)
    v, bx = X.section(doc, o, right, -half - .35 / M, half + .35 / M, -.25 / M, top, .9 / M, vname)
    if v.ViewDirection.DotProduct(n) < 0:
        doc.Delete(v.Id)
        t = bx.Transform; t2 = DB.Transform.Identity; t2.Origin = t.Origin; t2.BasisX = -t.BasisX; t2.BasisY = t.BasisY; t2.BasisZ = -t.BasisZ
        b2 = DB.BoundingBoxXYZ(); b2.Transform = t2; b2.Min = DB.XYZ(-bx.Max.X, bx.Min.Y, -bx.Max.Z); b2.Max = DB.XYZ(-bx.Min.X, bx.Max.Y, -bx.Min.Z)
        v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(L.SECTION_VFT)), b2); bx = b2
        L.setup_view(doc, v); v.Name = vname; v.CropBoxVisible = False
        try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
        except: pass
    try: v.SetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_Levels), True)
    except Exception: pass
    doc.Regenerate(); f_ = L.Frame(v)
    xa, xb = sorted([f_.x(a), f_.x(b)]); y0 = z - f_.o.Z
    d = (b - a).Normalize(); sgn = 1 if f_.x(a + d) > f_.x(a) else -1
    tx = lambda t: f_.x(a) + sgn * t
    dims = []; edges = [xa, xb]
    line(doc, v, f_.p(xa, y0), f_.p(xb, y0), (60, 60, 60), 3)
    if wet:
        yh = y0 + H_WET / M
        line(doc, v, f_.p(xa, yh), f_.p(xb, yh), COL['RV'], 8)
        for t in [i * .4 for i in range(1, 6)]:
            line(doc, v, f_.p(xa, y0 + t / M), f_.p(xb, y0 + t / M), (150, 180, 210), 1)
        dims.append(L.tick_dim(doc, f_, r['code'] + u' C%d revestimiento h' % (k + 1), [y0, yh], False, xb + .25 / M, tick=.08 / M))
        txt = u'C%d · revestimiento %s m² (bruto %s − vanos %s)' % (k + 1, c2(f['rev_m2']), c2(f['revGross_m2']), c2(f['revGross_m2'] - f['rev_m2']))
    else:
        txt = u'C%d' % (k + 1)
        for bd in [x for x in r['bands'] if x['face'] == k]:
            x0, x1 = sorted([tx(bd['t0']), tx(bd['t1'])]); edges += [x0, x1]
            for yy in BAND: line(doc, v, f_.p(x0, y0 + yy / M), f_.p(x1, y0 + yy / M), COL['RF'], 8)
            for xx in (x0, x1): line(doc, v, f_.p(xx, y0 + BAND[0] / M), f_.p(xx, y0 + BAND[1] / M), COL['RF'], 8)
            dims.append(L.tick_dim(doc, f_, bd['code'] + u' franja alto', [y0 + BAND[0] / M, y0 + BAND[1] / M], False, x1 + .2 / M, tick=.08 / M))
            dims.append(L.tick_dim(doc, f_, bd['code'] + u' franja largo', [x0, x1], True, y0 + BAND[1] / M + .2 / M, tick=.08 / M))
            txt += u' · %s franja %s × 0,60 = %s m²' % (bd['code'], c2(bd['len_m']), c2(bd['m2']))
    for o in f['openings']:
        if o['t1'] - o['t0'] < .05 / M or o['z0'] > (H_WET if wet else BAND[1]) / M: continue
        x0, x1 = sorted([tx(max(0, o['t0'])), tx(min(f['len'], o['t1']))]); edges += [x0, x1]
    dims.insert(0, L.tick_dim(doc, f_, r['code'] + u' C%d largo y vanos' % (k + 1), L.uniq(sorted(edges)), True, top - .15 / M, tick=.08 / M))
    L.tn(doc, v.Id, f_.p(xa, top - .45 / M), txt, 'tag')
    L.tn(doc, v.Id, L.crop_corner(v, .06 / M, .06 / M), sector, 'room')
    return item(v, bx, r['code'] + u' · cara C%d' % (k + 1), 'elevation', sector, [r['code']] + [x['code'] for x in r['bands'] if x['face'] == k], dims, [r['id']] + [o['id'] for o in f['openings']][:6])

def room_plan(doc, r, lev, sector):
    room = el(doc, r['id']); z = lev.Elevation
    v = S.new_plan(doc, lev, S.bounds([room], z, .8 / M), PRE + r['code'] + ' - PLANTA', depth=-.3)
    try: v.SetCategoryHidden(DB.ElementId(DB.BuiltInCategory.OST_Furniture), False)
    except Exception: pass
    zz = v.Origin.Z; draw_faces(doc, v, r, zz, inset=.04)
    for k, f in enumerate(r['faces']):
        if f['arc'] or f['len'] < .45 / M: continue
        a, b, n = P(f['a']), P(f['b']), P(f['n']); m = (a + b) * .5
        L.tn(doc, v.Id, DB.XYZ(m.X, m.Y, z) + n * (.3 / M), u'C%d' % (k + 1), 'tag')
    c = P(r['center']) if r['center'] else None
    if c: L.tn(doc, v.Id, DB.XYZ(c.X - .5 / M, c.Y, z), r['code'], 'room')
    if r['kind'] == 'RV':
        lines = [u'%s · %s' % (r['code'], rlabel(r)), u'Revestimiento 0,00–2,40: %s m² netos (vanos %s m²)' % (c2(r['rev_m2']), c2(sum(f['revGross_m2'] for f in r['faces']) - r['rev_m2'])),
                 u'Pintura 2,40–2,60: %s m²' % c2(r['paint_m2']), u'Material y formato: a definir (propuesta a confirmar).']
    else:
        lines = [u'%s · %s' % (r['code'], rlabel(r))] + [u'%s: %s × 0,60 = %s m² (%s)' % (b['code'], c2(b['len_m']), c2(b['m2']), u', '.join(b['items'])) for b in r['bands']] + [u'Pintura resto: %s m²' % c2(r['paint_m2']), u'Material de franja: a definir.']
    return item(v, v.CropBox, r['code'] + u' · planta de caras', 'plan', sector, [r['code']], [], [r['id']], lines)

def fichas(doc, rows, which):
    out = []
    for r in rows:
        if which == 'wet' and r['kind'] != 'RV': continue
        if which == 'band' and not r['bands']: continue
        lev = el(doc, r['levelId']); sector = rlabel(r)
        its = [room_plan(doc, r, lev, sector)]
        for k, f in enumerate(r['faces']):
            if f['arc'] or f['len'] < .5 / M: continue
            if which == 'band' and not any(b['face'] == k for b in r['bands']): continue
            if r['kind'] == 'RV' and f['rev_m2'] < .05: continue
            its.append(face_elev(doc, r, k, f, lev, sector, r['kind'] == 'RV'))
        num = ('RV-F-' + r['code'][3:]) if r['kind'] == 'RV' else ('RV-F-' + r['name'].split(' ')[0].upper())
        title = u'Ficha · %s %s' % (r['code'], r['name'])
        sub = (u'Revestimiento %s m² netos · h 2,40 · propuesta a confirmar' % c2(r['rev_m2'])) if r['kind'] == 'RV' else (u'Franjas %s m² · 0,90–1,50 · propuesta a confirmar' % c2(r['band_m2']))
        s = S.lay_sheet(doc, num, title, sub, its, FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Revestimientos · ' + r['code'])
        out.append(dict(s, kind='element', element=r['code'], elementId=str(r['id']), elementKind=(r['kind'] if r['kind'] == 'RV' else 'RF'), level=r['level'], sector=sector))
    return out

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'RV-00'; sheet.Name = u'Revestimientos · índice'
    head = u'CASA ÁNGEL · REVESTIMIENTOS · ÍNDICE Y CÓMPUTO (PROPUESTA A CONFIRMAR)'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'RV-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Revestimientos', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']
    if part == 'inventory':
        d = inventory(doc); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'rev-plan.json'), d)
        return {'status': 'success', 'rooms': [(r['code'], r['name'], round(r['rev_m2'], 2), round(r['paint_m2'], 2), round(r['band_m2'], 2), round(r['openings_m2'], 2), len(r['faces'])) for r in d['rooms']]}
    path = os.path.join(OUT, 'rev-' + part + '.json')
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('rev-') and fn.endswith('.json')): continue
            rec = R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for sh in rec['sheets']:
                if sh.get('exported') and not job.get('all'): done.append(sh['number']); continue
                opts.FileName = 'r26-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, sh['sheetId']).Id]), opts)); done.append(sh['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': len(done)}
    if job.get('reset') or job.get('resetPart'):
        rec = R1.read(path) if job.get('resetPart') else None
        def body():
            if rec: ids = [el(doc, i).Id for sh in rec['sheets'] for i in [sh['sheetId']] + [v['id'] for v in sh['views']] if el(doc, i) is not None]
            else: ids = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if (isinstance(v, DB.ViewSheet) and v.SheetNumber.startswith('RV-')) or name(v).startswith(PRE)]
            n = 0
            for i in ids:
                if doc.GetElement(i) is not None: doc.Delete(i); n += 1
            return n
        n, checked = L.guarded(doc, 'ADER RV R26 - reset', body)
        for fn in os.listdir(OUT):
            if fn.startswith('rev-') and fn.endswith('.json') and fn != 'rev-plan.json' and (not rec or os.path.join(OUT, fn) == path): os.remove(os.path.join(OUT, fn))
        doc.Save(); return {'status': 'success', 'deleted': n}
    if os.path.exists(path):
        rec = R1.read(path)
        if all(el(doc, sh['sheetId']) for sh in rec['sheets']): return {'status': 'success', 'existing': [sh['number'] for sh in rec['sheets']]}
    d = L.read('rev-plan')
    for r in d['rooms']: r['name'] = R1.clean(r['name']); r['level'] = R1.clean(r['level'])
    def body():
        if part == 'plans':
            return [general(doc, [r for r in d['rooms'] if r['levelId'] == lid], lid, 'RV-%02d' % k) for k, lid in enumerate([311, 694, 353988], 1)]
        if part.startswith('fichas-wet'): return fichas(doc, [r for r in d['rooms'] if not part[10:] or r['levelCode'] == part[10:]], 'wet')
        if part == 'fichas-band': return fichas(doc, d['rooms'], 'band')
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER RV R26 - ' + part, body)
    for sh in sheets:
        for v in sh['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [v['scale'] for v in sh['views']]) for sh in sheets]}
