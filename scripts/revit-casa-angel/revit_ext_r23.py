# -*- coding: utf-8 -*-
"""R23: Exteriores, documentation only.
Codes: TE terreno (toposólidos) · CA calle · AC base de acceso · EA escalones de acceso · EE escalera exterior ·
BA barandas exteriores · PO hojas de portón. Parts: probe (read-only), inventory (read-only), sheets, index, export, reset."""
import os, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
S = imp.load_source('ader_structure_r11_for_ext', os.path.join(ROOT, 'revit_structure_r11.py'))
F = imp.load_source('ader_fichas_r12_for_ext', os.path.join(ROOT, 'revit_fichas_r12.py'))
L = S.L; OUT = L.OUT; M = L.M; el = L.el; eid = L.eid; u = L.u; name = L.name; xyz = L.xyz; R1 = L.R1
if 5 not in L.SCALES: L.SCALES.insert(0, 5)
for _s in [300, 400, 500]:
    if _s not in L.SCALES: L.SCALES.append(_s)
RUBRO = u'EXTERIORES'
PRE = 'ADER EXT R23 - '
FOOT = u'Exteriores: geometría nativa del modelo (toposólidos, piso "Calle", acceso, escalones, escalera exterior, barandas y portón). Cotas en metros (no asociativas). Vegetación, solados, cercos, riego e iluminación exterior: no modelados / a definir.'
TOPO = [1023311, 354442, 358856, 356624]
CALLE = 734491; BASE = 398391
STEPS = [628255, 628637, 628772, 629011, 628854, 629059]
STAIR = 1028909
RAILS = [(682570, u'Terraza PA (deck)'), (884409, u'Frente PA (balcón sobre acceso)'), (885104, u'Terraza PA este'),
         (1033525, u'Escalera exterior (patio pileta)'), (1034520, u'Escalera exterior (patio pileta)')]
RAILS_INT = [401577, 401581, 682785, 695817]
GATE = [664505, 664506, 664507, 664508, 670378]
COL = {'TE': (70, 140, 60), 'CA': (120, 110, 100), 'AC': (196, 98, 16), 'EA': (196, 98, 16), 'EE': (196, 98, 16), 'BA': (25, 98, 143), 'PO': (150, 40, 120)}

def c2(x): return (u'%.2f' % (0.0 if abs(x) < .005 else x)).replace(u'.', u',')
def c1(x): return (u'{:,.1f}'.format(x)).replace(u',', u'X').replace(u'.', u',').replace(u'X', u'.')

def tname(doc, e):
    t = doc.GetElement(e.GetTypeId())
    return u(name(t)) if t else u''

def pval(e, bip):
    p = e.get_Parameter(bip)
    return p.AsDouble() if p and p.HasValue else 0.0

def room_at(doc, p):
    for dz in (1.0 / M, 0.3 / M):
        r = doc.GetRoomAtPoint(DB.XYZ(p.X, p.Y, p.Z + dz))
        if r: return u'%s · %s' % (u(r.Number), u(name(r)))
    return None

def bb(e):
    b = e.get_BoundingBox(None)
    return [[b.Min.X * M, b.Min.Y * M, b.Min.Z * M], [b.Max.X * M, b.Max.Y * M, b.Max.Z * M]] if b else None

def top_point(e, doc=None):
    """Centroid of the largest upward triangle of the element's geometry (outside rooms when possible)."""
    best = (0, None); free = (0, None)
    def solids(g):
        for o in g:
            if isinstance(o, DB.Solid) and o.Volume > 0: yield o
            elif isinstance(o, DB.GeometryInstance):
                for s in solids(o.GetInstanceGeometry()): yield s
    for s in solids(e.get_Geometry(DB.Options())):
        for f in s.Faces:
            m = f.Triangulate()
            for i in range(m.NumTriangles):
                t = m.get_Triangle(i); a, b, c = t.get_Vertex(0), t.get_Vertex(1), t.get_Vertex(2)
                n = (b - a).CrossProduct(c - a)
                if n.Z <= 0: continue
                ar = n.GetLength() / 2
                if n.Z / (2 * ar) > .7 and ar > best[0]: best = (ar, (a + b + c) / 3.0)
                if doc is not None and n.Z / (2 * ar) > .7 and ar > free[0]:
                    q = (a + b + c) / 3.0
                    if doc.GetRoomAtPoint(DB.XYZ(q.X, q.Y, q.Z + 1.0 / M)) is None: free = (ar, q)
    return free[1] or best[1]

# ---------------------------------------------------------------- probe / inventory (read-only)

def probe(doc):
    out = {'toposolids': [], 'floors': [], 'railings': [], 'walls': [], 'planting': [], 'other': {}, 'wallTypes': {}}
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Toposolid).WhereElementIsNotElementType():
        out['toposolids'].append({'id': eid(e), 'type': tname(doc, e), 'area': pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED) * M * M, 'bbox': bb(e)})
    for e in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Planting).WhereElementIsNotElementType():
        out['planting'].append({'id': eid(e), 'type': tname(doc, e), 'bbox': bb(e)})
    return out

def inventory(doc):
    rows = []
    topo = sorted([el(doc, i) for i in TOPO], key=lambda e: -pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED))
    for k, e in enumerate(topo, 1):
        b = e.get_BoundingBox(None); A = pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED) * M * M; V = pval(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED) * M ** 3
        code = 'TE-%02d' % k
        rows.append({'id': eid(e), 'code': code, 'kind': 'TE', 'type': tname(doc, e), 'area_m2': A, 'volume_m3': V, 'zmin_m': b.Min.Z * M, 'zmax_m': b.Max.Z * M,
                     'size_m': [(b.Max.X - b.Min.X) * M, (b.Max.Y - b.Min.Y) * M],
                     'label': u'%s · terreno · %s m²' % (code, c1(A)), 'status': u'Toposólido "%s" (cota sup. %s a %s m)' % (tname(doc, e), c2(b.Min.Z * M + 1.2), c2(b.Max.Z * M))})
    e = el(doc, CALLE); A = pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED) * M * M
    rows.append({'id': CALLE, 'code': 'CA-01', 'kind': 'CA', 'type': tname(doc, e), 'area_m2': A, 'volume_m3': pval(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED) * M ** 3,
                 'label': u'CA-01 · calle · %s m²' % c1(A), 'status': u'Piso "Calle" (1 m de tierra en el modelo)'})
    e = el(doc, BASE); b = e.get_BoundingBox(None); A = pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED) * M * M
    rows.append({'id': BASE, 'code': 'AC-01', 'kind': 'AC', 'type': tname(doc, e), 'area_m2': A, 'volume_m3': pval(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED) * M ** 3, 'top_m': b.Max.Z * M,
                 'label': u'AC-01 · base de acceso · %s m² · +%s' % (c2(A), c2(b.Max.Z * M)), 'status': u'Piso "Base Acceso" (nivel 005. Acceso ppal)'})
    steps = sorted([el(doc, i) for i in STEPS], key=lambda e: -e.get_BoundingBox(None).Max.Z)
    for k, e in enumerate(steps, 1):
        b = e.get_BoundingBox(None); A = pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED) * M * M; code = 'EA-%02d' % k
        sx, sy = sorted([(b.Max.X - b.Min.X) * M, (b.Max.Y - b.Min.Y) * M], reverse=True)
        rows.append({'id': eid(e), 'code': code, 'kind': 'EA', 'type': tname(doc, e), 'area_m2': A, 'volume_m3': pval(e, DB.BuiltInParameter.HOST_VOLUME_COMPUTED) * M ** 3, 'top_m': b.Max.Z * M,
                     'thickness_m': (b.Max.Z - b.Min.Z) * M, 'size_m': [sx, sy],
                     'label': u'%s · %s × %s · +%s' % (code, c2(sx), c2(sy), c2(b.Max.Z * M)), 'status': u'Escalón de acceso (piso "%s")' % tname(doc, e)})
    e = el(doc, STAIR); b = e.get_BoundingBox(None)
    st = {'risers': e.ActualRisersNumber, 'riser_m': e.ActualRiserHeight * M, 'tread_m': e.ActualTreadDepth * M, 'height_m': e.Height * M,
          'base_m': e.BaseElevation * M, 'top_m': e.TopElevation * M}
    runs = []
    for rid in e.GetStairsRuns():
        r = doc.GetElement(rid)
        runs.append({'id': eid(r), 'width_m': r.ActualRunWidth * M, 'risers': r.ActualRisersNumber, 'treads': r.ActualTreadsNumber, 'length_m': r.GetStairsPath().GetExactLength() * M if r.GetStairsPath() else None})
    rows.append(dict({'id': STAIR, 'code': 'EE-01', 'kind': 'EE', 'type': tname(doc, e), 'runs': runs,
                      'label': u'EE-01 · escalera exterior · %d alzadas de %s' % (st['risers'], c2(st['riser_m'])),
                      'status': u'Escalera "%s": huella %s, sube %s m (de +%s a +%s)' % (tname(doc, e), c2(st['tread_m']), c2(st['height_m']), c2(st['base_m']), c2(st['top_m']))}, **st))
    for k, (i, where) in enumerate(RAILS, 1):
        e = el(doc, i); b = e.get_BoundingBox(None); crv = list(e.GetPath()); ln = sum(c.Length for c in crv) * M
        h = None
        try: h = doc.GetElement(e.GetTypeId()).TopRailHeight * M
        except Exception: h = (b.Max.Z - b.Min.Z) * M
        code = 'BA-%02d' % k
        rows.append({'id': i, 'code': code, 'kind': 'BA', 'type': tname(doc, e), 'length_m': ln, 'segments': len(crv), 'height_m': h, 'sector': where,
                     'level': u(name(doc.GetElement(e.LevelId))) if doc.GetElement(e.LevelId) else u'(escalera)',
                     'label': u'%s · %s ml · h %s' % (code, c2(ln), c2(h)), 'status': u'Baranda "%s" · %s' % (tname(doc, e), where)})
    gate = sorted([el(doc, i) for i in GATE], key=lambda e: (round(e.Location.Curve.Evaluate(.5, True).X, 0), e.Location.Curve.Evaluate(.5, True).Y))
    for k, e in enumerate(gate, 1):
        Ln = e.Location.Curve.Length * M; H = pval(e, DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM) * M; A = pval(e, DB.BuiltInParameter.HOST_AREA_COMPUTED) * M * M
        code = 'PO-%02d' % k
        rows.append({'id': eid(e), 'code': code, 'kind': 'PO', 'type': tname(doc, e), 'length_m': Ln, 'height_m': H, 'thickness_m': e.Width * M, 'area_m2': A,
                     'label': u'%s · %s × %s' % (code, c2(Ln), c2(H)), 'status': u'Hoja de portón (muro "%s", e %s cm)' % (tname(doc, e), c2(e.Width * M * 100).replace(u',00', u''))})
    for r in rows: r['bbox'] = R1.bbox(el(doc, r['id']))
    planting = [u(name(t)) for t in DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Planting).WhereElementIsElementType()]
    placed = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Planting).WhereElementIsNotElementType().GetElementCount()
    ints = []
    for i in RAILS_INT:
        e = el(doc, i); ints.append({'id': i, 'type': tname(doc, e), 'length_m': sum(c.Length for c in e.GetPath()) * M})
    return {'elements': rows, 'plantingTypes': planting, 'plantingPlaced': placed, 'interiorRailings': ints}

# ---------------------------------------------------------------- views

def item(v, box, title, kind, sector, tags, dims, elements, data_=None):
    return {'view': v, 'box': box, 'title': title, 'kind': kind, 'sector': sector, 'tags': tags, 'dims': S.dims_out(dims), 'elements': elements, 'data': data_}

def box_of(es, z, pad):
    return S.bounds(es, z, pad)

def section(doc, origin, right, x0, x1, y0, y1, depth, vname):
    """Section whose viewer looks along -(right x Z); far clip `depth` behind the cut plane."""
    t = DB.Transform.Identity; t.Origin = origin; t.BasisX = right; t.BasisY = DB.XYZ.BasisZ; t.BasisZ = right.CrossProduct(DB.XYZ.BasisZ)
    bx = DB.BoundingBoxXYZ(); bx.Transform = t; bx.Min = DB.XYZ(x0, y0, -depth); bx.Max = DB.XYZ(x1, y1, .05)
    v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(L.SECTION_VFT)), bx)
    L.setup_view(doc, v, levels=True); v.Name = vname; v.CropBoxVisible = False
    try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
    except: pass
    return v, bx

def axo(doc, es, code, label, sector, rgb):
    pts = [p for e in es for p in [e.get_BoundingBox(None).Min, e.get_BoundingBox(None).Max]]; pad = .6 / M
    bx = DB.BoundingBoxXYZ(); bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, min(p.Z for p in pts) - .3 / M)
    bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, max(p.Z for p in pts) + .3 / M)
    ax = DB.View3D.CreateIsometric(doc, DB.ElementId(Int64(49559))); L.setup_view(doc, ax)
    ax.Name = PRE + code + ' - AXO'; ax.SetSectionBox(bx); ax.IsSectionBoxActive = True
    d = DB.XYZ(-1, -1, -.75).Normalize(); right = d.CrossProduct(DB.XYZ.BasisZ).Normalize()
    ax.SetOrientation(DB.ViewOrientation3D(DB.XYZ.Zero, right.CrossProduct(d).Normalize(), d))
    L.D.fit3d(doc, ax)
    try: ax.SaveOrientationAndLock()
    except Exception: pass
    for e in es: S.colorize(doc, ax, e, rgb)
    doc.Regenerate()
    c = (bx.Min + bx.Max) * .5
    L.axo_note(doc, ax, c, label, 'tag'); L.axo_note(doc, ax, bx.Min, sector, 'room')
    return {'view': ax, 'box': ax.CropBox, 'title': code + u' · axonométrica', 'kind': 'axo', 'sector': sector, 'tags': [code], 'dims': [], 'elements': [eid(e) for e in es], 'data': None}

def label_at(doc, v, e, r, z, dy=0):
    p = top_point(e, doc) if r['kind'] in ('TE', 'CA') else None
    if p is None:
        b = e.get_BoundingBox(None); p = (b.Min + b.Max) * .5
    L.tn(doc, v.Id, DB.XYZ(p.X, p.Y + dy, z), r['label'], 'tag')

def build(doc, d):
    rows = d['elements']; by = dict((r['code'], r) for r in rows); E = lambda r: el(doc, r['id'])
    pb = el(doc, 311); pa = el(doc, 694); z0 = pb.Elevation; z1 = pa.Elevation
    K = lambda *ks: [r for r in rows if r['kind'] in ks]
    sheets = []
    # ---- EXT-01 implantación (terreno + calle)
    big = el(doc, TOPO[0]); sec = u'Exteriores · terreno'
    v = S.new_plan(doc, pb, S.bounds([big], z0, 3 / M), PRE + 'IMPLANTACION', depth=-2.5)
    for r in K('TE', 'CA'): S.colorize(doc, v, E(r), COL[r['kind']])
    for r in K('TE', 'CA'):
        if r['code'] in ('TE-03', 'TE-04'): continue   # small pieces: shown on EXT-02
        label_at(doc, v, E(r), r, z0)
    b = big.get_BoundingBox(None)
    fx = L.AxisFrame(v, DB.XYZ(b.Min.X, b.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY); fy = L.AxisFrame(v, DB.XYZ(b.Min.X, b.Min.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    dims = [L.tick_dim(doc, fx, u'Terreno modelado X', [0, b.Max.X - b.Min.X], True, 1.5 / M, tick=.6 / M),
            L.tick_dim(doc, fy, u'Terreno modelado Y', [0, b.Max.Y - b.Min.Y], True, 1.5 / M, tick=.6 / M)]
    hb = el(doc, 2287528).get_BoundingBox(None)
    L.tn(doc, v.Id, DB.XYZ((hb.Min.X + hb.Max.X) / 2 - 2 / M, (hb.Min.Y + hb.Max.Y) / 2, z0), u'CASA', 'room')
    te = K('TE'); ca = K('CA')
    sub = u'Terreno %s m² en %d toposólidos · calle %s m²' % (c1(sum(r['area_m2'] for r in te)), len(te), c1(ca[0]['area_m2']))
    sheets.append(dict(S.lay_sheet(doc, 'EXT-01', u'Implantación general', sub, [item(v, v.CropBox, u'Implantación', 'plan', sec, [r['code'] for r in te + ca], dims, [r['id'] for r in te + ca])],
                                   FOOT, rubro=RUBRO, sheet_name=u'Exteriores · 01'), kind='general', level=u'00. Planta Baja', sector=sec))
    # ---- EXT-02 planta de exteriores PB (entorno de la casa)
    sec = u'Exteriores · 00. Planta Baja'
    near = [E(r) for r in K('AC', 'EA', 'EE', 'PO')] + [el(doc, 405334), el(doc, 370633), el(doc, 2287528)]
    v = S.new_plan(doc, pb, S.bounds(near, z0, 5 / M), PRE + 'PLANTA PB', depth=-2.5)
    pbr = K('TE', 'AC', 'EA', 'EE', 'PO')
    dims = []
    for r in pbr: S.colorize(doc, v, E(r), COL[r['kind']])
    for r in K('TE'):
        if r['code'] != 'TE-01': label_at(doc, v, E(r), r, z0)
    b = E(by['AC-01']).get_BoundingBox(None); L.tn(doc, v.Id, DB.XYZ(b.Max.X + .4 / M, b.Min.Y + .3 / M, z0), by['AC-01']['label'], 'tag')
    b = E(by['EE-01']).get_BoundingBox(None); L.tn(doc, v.Id, DB.XYZ(b.Min.X - 3 / M, b.Min.Y - 2.4 / M, z0), by['EE-01']['label'], 'tag')
    lbl = u'Escalones EA-01..%02d (2,00 × 1,00 · +0,20 a +0,80)' % len(K('EA'))
    eb = [E(r).get_BoundingBox(None) for r in K('EA')]
    L.tn(doc, v.Id, DB.XYZ(min(x.Min.X for x in eb) - 7.5 / M, min(x.Min.Y for x in eb) + .3 / M, z0), lbl, 'tag')
    po = K('PO'); pbx = [E(r).get_BoundingBox(None) for r in po]
    L.tn(doc, v.Id, DB.XYZ(min(x.Min.X for x in pbx) - 4.5 / M, (min(x.Min.Y for x in pbx) + max(x.Max.Y for x in pbx)) / 2 + 1.4 / M, z0),
         u'Portón PO-01..%02d · %s m²' % (len(po), c2(sum(r['area_m2'] for r in po))), 'tag')
    S.room_labels(doc, v, 311, z0)
    sub = u'Acceso %s m² · %d escalones · escalera exterior · portón %s m²' % (c2(by['AC-01']['area_m2']), len(K('EA')), c2(sum(r['area_m2'] for r in po)))
    sheets.append(dict(S.lay_sheet(doc, 'EXT-02', u'Planta de exteriores · Planta Baja', sub, [item(v, v.CropBox, u'Exteriores PB', 'plan', sec, [r['code'] for r in pbr], dims, [r['id'] for r in pbr])],
                                   FOOT, rubro=RUBRO, sheet_name=u'Exteriores · 02'), kind='general', level=u'00. Planta Baja', sector=sec))
    # ---- EXT-03 barandas exteriores (planta PA + axo)
    sec = u'Exteriores · 01. Planta Alta'
    ba = K('BA'); bae = [E(r) for r in ba]
    v = S.new_plan(doc, pa, S.bounds(bae, z1, 1.5 / M), PRE + 'BARANDAS PA', depth=-3.2)
    dims = []
    for r, e in zip(ba, bae):
        S.colorize(doc, v, e, COL['BA'])
        b = e.get_BoundingBox(None); p = DB.XYZ(b.Min.X, b.Max.Y + .3 / M, z1)
        if r['code'] == 'BA-04': p = DB.XYZ(b.Min.X - 3.0 / M, b.Max.Y + .5 / M, z1)
        if r['code'] == 'BA-05': p = DB.XYZ(b.Max.X + .4 / M, b.Min.Y - .3 / M, z1)
        if r['code'] == 'BA-02': p = DB.XYZ(b.Min.X, b.Min.Y - .6 / M, z1)
        L.tn(doc, v.Id, p, r['label'], 'tag')
        for c in e.GetPath():
            a0, a1 = c.GetEndPoint(0), c.GetEndPoint(1)
            if a0.DistanceTo(a1) < 1.0 / M: continue
            dd = DB.XYZ(a1.X - a0.X, a1.Y - a0.Y, 0).Normalize(); n = DB.XYZ(-dd.Y, dd.X, 0)
            f = L.AxisFrame(v, DB.XYZ(a0.X, a0.Y, v.Origin.Z), dd, -n)
            dims.append(L.tick_dim(doc, f, r['code'] + u' tramo', [0, DB.XYZ(a0.X, a0.Y, 0).DistanceTo(DB.XYZ(a1.X, a1.Y, 0))], True, .3 / M, tick=.08 / M))
    S.room_labels(doc, v, 694, z1)
    lines = [r['label'] + u' · ' + r['sector'] for r in ba] + [u'Total exteriores: %s ml' % c2(sum(r['length_m'] for r in ba))]
    it = item(v, v.CropBox, u'Barandas exteriores · planta', 'plan', sec, [r['code'] for r in ba], dims, [r['id'] for r in ba], lines)
    ax = axo(doc, bae, u'BA', u'Barandas exteriores · %s ml' % c2(sum(r['length_m'] for r in ba)), sec, COL['BA']); ax['title'] = u'Barandas · axonométrica'; ax['tags'] = [r['code'] for r in ba]
    sheets.append(dict(S.lay_sheet(doc, 'EXT-03', u'Barandas exteriores', u'%d barandas · %s ml · tipo "%s"' % (len(ba), c2(sum(r['length_m'] for r in ba)), ba[0]['type']), [it, ax], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Exteriores · 03'),
                       kind='general', level=u'01. Planta Alta', sector=sec))
    # ---- EXT-F-ACCESO: planta + corte por escalones + axo
    sec = u'Exteriores · acceso principal'
    acc = K('AC', 'EA'); ae = [E(r) for r in acc]
    v = S.new_plan(doc, pb, S.bounds(ae, z0, 1.2 / M), PRE + 'ACCESO PLANTA', depth=-1.0)
    dims = []
    for r, e in zip(acc, ae):
        S.colorize(doc, v, e, COL[r['kind']]); b = e.get_BoundingBox(None)
        if r['kind'] == 'EA':
            L.tn(doc, v.Id, DB.XYZ(b.Min.X + .05 / M, (b.Min.Y + b.Max.Y) / 2, z0), r['code'] + u' +' + c2(r['top_m']), 'tag')
        else: label_at(doc, v, e, r, z0)
    allb = [e.get_BoundingBox(None) for e in ae]
    bmin = DB.XYZ(min(x.Min.X for x in allb), min(x.Min.Y for x in allb), 0); bmax = DB.XYZ(max(x.Max.X for x in allb), max(x.Max.Y for x in allb), 0)
    eb = [E(r).get_BoundingBox(None) for r in K('EA')]
    xs = sorted(set([round(x.Min.X - bmin.X, 4) for x in eb] + [round(x.Max.X - bmin.X, 4) for x in eb]))
    ys = sorted(set([round(x.Min.Y - bmin.Y, 4) for x in eb] + [round(x.Max.Y - bmin.Y, 4) for x in eb]))
    fx = L.AxisFrame(v, DB.XYZ(bmin.X, bmin.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY); fy = L.AxisFrame(v, DB.XYZ(bmin.X, bmin.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    dims += [L.tick_dim(doc, fx, u'Escalones en X', xs, True, .45 / M, tick=.08 / M), L.tick_dim(doc, fy, u'Escalones en Y', ys, True, .45 / M, tick=.08 / M),
             L.tick_dim(doc, fx, u'Acceso total X', [0, bmax.X - bmin.X], True, .8 / M, tick=.08 / M)]
    lines = [by['AC-01']['label'], u'Escalones: ' + u', '.join(r['code'] + u' +' + c2(r['top_m']) for r in K('EA')), u'Alzada 0,20 · pieza 2,00 × 1,00 × 0,10', u'Terminación de pisada: a definir.']
    itp = item(v, v.CropBox, u'Acceso · planta', 'plan', sec, [r['code'] for r in acc], dims, [r['id'] for r in acc], lines)
    xc = (min(x.Min.X for x in eb) + max(x.Max.X for x in eb)) / 2
    xcut = el(doc, 628255).get_BoundingBox(None); xcut = (xcut.Min.X + xcut.Max.X) / 2 + .3 / M   # through EA-01..EA-04 + base
    vs, bx = section(doc, DB.XYZ(xcut, 0, z0), -DB.XYZ.BasisY, -(bmax.Y + .8 / M), -(bmin.Y - .8 / M), -.6 / M, 2.2 / M, 1.2 / M, PRE + 'ACCESO CORTE')
    for r, e in zip(acc, ae): S.colorize(doc, vs, e, COL[r['kind']])
    doc.Regenerate(); f = L.Frame(vs)
    tops = sorted(set([0.0] + [round(r['top_m'] / M, 5) for r in acc]))
    ds = [L.tick_dim(doc, f, u'Niveles de escalones', [t + z0 - f.o.Z for t in tops], False, min(f.x(DB.XYZ(xcut, bmin.Y, 0)), f.x(DB.XYZ(xcut, bmax.Y, 0))) - .5 / M)]
    hit = [x for x in [E(r).get_BoundingBox(None) for r in acc] if x.Min.X <= xcut <= x.Max.X]
    ys2 = sorted(set([round(f.x(DB.XYZ(xcut, x.Min.Y, 0)), 4) for x in hit] + [round(f.x(DB.XYZ(xcut, x.Max.Y, 0)), 4) for x in hit]))
    ds.append(L.tick_dim(doc, f, u'Huellas en corte', ys2, True, 1.3 / M + z0 - f.o.Z, tick=.08 / M))
    L.tn(doc, vs.Id, L.crop_corner(vs, .06 / M, .06 / M), sec, 'room')
    its = item(vs, bx, u'Acceso · corte por escalones', 'section', sec, [r['code'] for r in acc], ds, [r['id'] for r in acc])
    axa = axo(doc, ae, u'ACCESO', u'Acceso principal', sec, COL['EA']); axa['title'] = u'Acceso · axonométrica'; axa['tags'] = [r['code'] for r in acc]
    sheets.append(dict(S.lay_sheet(doc, 'EXT-F-ACCESO', u'Ficha · acceso principal', lines[1], [itp, its, axa], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Exteriores · acceso'),
                       kind='element', element='AC-01', elementId=str(BASE), elementKind='AC', level=u'00. Planta Baja', sector=sec))
    # ---- EXT-F-EE-01: escalera exterior: planta + corte + axo
    sec = u'Exteriores · patio pileta'
    r = by['EE-01']; e = E(r); be = [e] + [el(doc, 1033525), el(doc, 1034520)]
    v = S.new_plan(doc, pb, S.bounds(be, z0, 1.2 / M), PRE + 'ESCALERA PLANTA', depth=-1.0)
    for x in be: S.colorize(doc, v, x, COL['EE'])
    b = e.get_BoundingBox(None)
    L.tn(doc, v.Id, DB.XYZ(b.Max.X + .3 / M, b.Max.Y, z0), r['label'], 'tag')
    fx = L.AxisFrame(v, DB.XYZ(b.Min.X, b.Min.Y, v.Origin.Z), DB.XYZ.BasisX, -DB.XYZ.BasisY); fy = L.AxisFrame(v, DB.XYZ(b.Min.X, b.Min.Y, v.Origin.Z), DB.XYZ.BasisY, -DB.XYZ.BasisX)
    dims = [L.tick_dim(doc, fx, u'EE-01 ancho X', [0, b.Max.X - b.Min.X], True, .45 / M, tick=.08 / M), L.tick_dim(doc, fy, u'EE-01 largo Y', [0, b.Max.Y - b.Min.Y], True, .45 / M, tick=.08 / M)]
    lines = [r['label'], r['status'], u'Tramos: ' + u'; '.join(u'%d alzadas, ancho %s' % (x['risers'], c2(x['width_m'])) for x in r['runs']), u'Barandas: BA-04, BA-05.']
    itp = item(v, v.CropBox, u'EE-01 · planta', 'plan', sec, ['EE-01', 'BA-04', 'BA-05'], dims, [STAIR, 1033525, 1034520], lines)
    long_x = (b.Max.X - b.Min.X) >= (b.Max.Y - b.Min.Y)
    c = (b.Min + b.Max) * .5
    right = DB.XYZ.BasisX if long_x else DB.XYZ.BasisY
    half = (max(b.Max.X - b.Min.X, b.Max.Y - b.Min.Y)) / 2
    vs, bx = section(doc, DB.XYZ(c.X, c.Y, z0), right, -half - .8 / M, half + .8 / M, -.4 / M, (b.Max.Z - z0) + 1.2 / M, (min(b.Max.X - b.Min.X, b.Max.Y - b.Min.Y)) / 2 + .2 / M, PRE + 'ESCALERA CORTE')
    for x in be: S.colorize(doc, vs, x, COL['EE'])
    doc.Regenerate(); f = L.Frame(vs)
    xs = sorted([f.x(c - right * half), f.x(c + right * half)])
    ds = [L.tick_dim(doc, f, u'EE-01 desarrollo', xs, True, (b.Max.Z - f.o.Z) + .4 / M, tick=.08 / M),
          L.tick_dim(doc, f, u'EE-01 base + altura', [r['base_m'] / M - f.o.Z, r['top_m'] / M - f.o.Z], False, xs[1] + .5 / M, tick=.08 / M)]
    L.tn(doc, vs.Id, L.crop_corner(vs, .06 / M, .06 / M), sec, 'room')
    its = item(vs, bx, u'EE-01 · corte', 'section', sec, ['EE-01'], ds, [STAIR, 1033525, 1034520])
    axe = axo(doc, be, u'EE-01', r['label'], sec, COL['EE']); axe['title'] = u'EE-01 · axonométrica'; axe['tags'] = ['EE-01', 'BA-04', 'BA-05']
    sheets.append(dict(S.lay_sheet(doc, 'EXT-F-EE-01', u'Ficha · escalera exterior EE-01', r['status'], [itp, its, axe], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Exteriores · escalera'),
                       kind='element', element='EE-01', elementId=str(STAIR), elementKind='EE', level=u'00. Planta Baja', sector=sec))
    # ---- EXT-F-PORTON: planta + alzado + axo
    sec = u'Exteriores · portón'
    pe = [E(x) for x in po]
    v = S.new_plan(doc, pb, S.bounds(pe, z0, 3.0 / M), PRE + 'PORTON PLANTA', depth=-.3)
    dims = []
    allb = [x.get_BoundingBox(None) for x in pe]; ctr = DB.XYZ(min(x.Min.X for x in allb) - 3 / M, (min(x.Min.Y for x in allb) + max(x.Max.Y for x in allb)) / 2, z0)
    for x, e in zip(po, pe):
        S.colorize(doc, v, e, COL['PO']); dims += S.tag_plan(doc, v, e, x, z0, ctr)
    lines = [x['label'] for x in po] + [u'Total hojas: %s m² · e 5 cm' % c2(sum(x['area_m2'] for x in po)), u'Herrajes, guías y accionamiento: a definir.']
    itp = item(v, v.CropBox, u'Portón · planta', 'plan', sec, [x['code'] for x in po], dims, [x['id'] for x in po], lines)
    inline = [x for x, e in zip(po, pe) if e.get_BoundingBox(None).Max.X - e.get_BoundingBox(None).Min.X < .5 / M]
    ib = [E(x).get_BoundingBox(None) for x in inline]
    y0, y1 = min(x.Min.Y for x in ib), max(x.Max.Y for x in ib); xo = max(x.Max.X for x in allb) + .6 / M
    vs, bx = section(doc, DB.XYZ(xo, (y0 + y1) / 2, z0), DB.XYZ.BasisY, -(y1 - y0) / 2 - .8 / M, (y1 - y0) / 2 + .8 / M, -.4 / M, 3.6 / M, (xo - min(x.Min.X for x in allb)) + .3 / M, PRE + 'PORTON ALZADO')
    for e in pe: S.colorize(doc, vs, e, COL['PO'])
    doc.Regenerate(); f = L.Frame(vs)
    xs = L.uniq(sorted([f.x(DB.XYZ(xo, x.Min.Y, z0)) for x in ib] + [f.x(DB.XYZ(xo, x.Max.Y, z0)) for x in ib]))
    hmax = max(x['height_m'] for x in inline) / M
    ds = [L.tick_dim(doc, f, u'Hojas de portón', xs, True, z0 + hmax - f.o.Z + .3 / M, tick=.08 / M),
          L.tick_dim(doc, f, u'Portón largo total', [xs[0], xs[-1]], True, z0 + hmax - f.o.Z + .6 / M, tick=.08 / M),
          L.tick_dim(doc, f, u'Portón alto', [z0 - f.o.Z, z0 + hmax - f.o.Z], False, xs[-1] + .4 / M, tick=.08 / M)]
    for x in inline:
        bx_ = E(x).get_BoundingBox(None)
        L.tn(doc, vs.Id, f.p(f.x(DB.XYZ(xo, (bx_.Min.Y + bx_.Max.Y) / 2, z0)) - .3 / M, z0 + hmax / 2 - f.o.Z), x['code'], 'tag')
    L.tn(doc, vs.Id, L.crop_corner(vs, .06 / M, .06 / M), sec, 'room')
    its = item(vs, bx, u'Portón · alzado', 'elevation', sec, [x['code'] for x in inline], ds, [x['id'] for x in po])
    axp = axo(doc, pe, u'PORTON', u'Portón · %d hojas' % len(po), sec, COL['PO']); axp['title'] = u'Portón · axonométrica'; axp['tags'] = [x['code'] for x in po]
    sheets.append(dict(S.lay_sheet(doc, 'EXT-F-PORTON', u'Ficha · portón', u'%d hojas · %s m²' % (len(po), c2(sum(x['area_m2'] for x in po))), [itp, its, axp], FOOT, plan_region=True, rubro=RUBRO, sheet_name=u'Exteriores · portón'),
                       kind='element', element='PO', elementId=str(po[0]['id']), elementKind='PO', level=u'00. Planta Baja', sector=sec))
    return sheets

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'EXT-00'; sheet.Name = u'Exteriores · índice'
    head = u'CASA ÁNGEL · EXTERIORES · ÍNDICE Y CÓMPUTO'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'EXT-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Exteriores', 'sector': u'General'}]

def run(doc, uidoc, job):
    L.assert_pilot(doc); L.register_font()
    part = job['part']; path = os.path.join(OUT, 'ext-' + part + '.json')
    if part == 'probe':
        d = probe(doc); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'ext-probe.json'), d)
        return {'status': 'success', 'counts': dict((k, len(v)) for k, v in d.items() if isinstance(v, list))}
    if part == 'inventory':
        d = inventory(doc); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'ext-plan.json'), d)
        return {'status': 'success', 'elements': [(r['code'], r['label']) for r in d['elements']]}
    if part == 'export':
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in sorted(os.listdir(OUT)):
            if not (fn.startswith('ext-') and fn.endswith('.json')): continue
            rec = R1.read(os.path.join(OUT, fn))
            if not isinstance(rec, dict) or 'sheets' not in rec: continue
            for s in rec['sheets']:
                opts.FileName = 'r23-' + s['number']; s['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([el(doc, s['sheetId']).Id]), opts)); done.append(s['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if job.get('reset'):
        def body():
            ids = [v.Id for v in DB.FilteredElementCollector(doc).OfClass(DB.View) if (isinstance(v, DB.ViewSheet) and v.SheetNumber.startswith('EXT-')) or name(v).startswith(PRE)]
            n = 0
            for i in ids:
                if doc.GetElement(i) is not None: doc.Delete(i); n += 1
            return n
        n, checked = L.guarded(doc, 'ADER EXT R23 - reset', body)
        for fn in os.listdir(OUT):
            if fn.startswith('ext-') and fn.endswith('.json') and fn not in ('ext-plan.json', 'ext-probe.json'): os.remove(os.path.join(OUT, fn))
        doc.Save(); return {'status': 'success', 'deleted': n}
    if os.path.exists(path):
        rec = R1.read(path)
        if all(el(doc, s['sheetId']) for s in rec['sheets']): return {'status': 'success', 'existing': [s['number'] for s in rec['sheets']]}
    d = L.read('ext-plan')
    for r in d['elements']:
        for k in ('label', 'status', 'type', 'sector'):
            if k in r: r[k] = R1.clean(r[k])
    def body():
        if part == 'sheets': return build(doc, d)
        if part == 'index': return index_part(doc, job)
        raise Exception('Unknown part')
    sheets, checked = L.guarded(doc, 'ADER EXT R23 - ' + part, body)
    for s in sheets:
        for v in s['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'physicalChecked': checked, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(s['number'], [v['scale'] for v in s['views']]) for s in sheets]}
