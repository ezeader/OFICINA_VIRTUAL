# -*- coding: utf-8 -*-
"""R29 Cubierta documentation inside Casa-Angel-DOC-Cubierta.rvt (pilot linked).
inventory (read-only, from the link): aguas (faces) with slope/area, edge classification (alero, cumbrera, limatesa, limahoya,
encuentro con muro / borde), timber pieces (VC / VP cabios / CR listones) incl. the CU-02 structure modeled in R29."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
X = imp.load_source('ader_ext_r23_for_cubdoc', os.path.join(ROOT, 'revit_ext_r23.py'))
S = X.S; L = S.L; F = X.F
CTX = imp.load_source('ader_docctx_r30_cub', os.path.join(ROOT, 'docctx_r30.py'))
OUT = L.OUT; M = L.M; eid = L.eid; u = L.u; name = L.name; R1 = L.R1
c2 = X.c2

def mxyz(p): return [round(p.X * M, 3), round(p.Y * M, 3), round(p.Z * M, 3)]

def roof_faces(e):
    out = []
    for g in e.get_Geometry(DB.Options()):
        if isinstance(g, DB.Solid) and g.Volume > 0:
            out += [f for f in g.Faces if isinstance(f, DB.PlanarFace) and f.FaceNormal.Z < -.1]   # underside = machimbre visto
    return out

def classify(ld, roofs, walls):
    """Edges of the underside faces: shared by 2 faces → cumbrera (horizontal) / limatesa / limahoya; single → alero (lowest
    horizontal), encuentro con muro (wall within 0,30 m) or borde libre."""
    edges = {}
    for r in roofs:
        for k, f in enumerate(roof_faces(r)):
            for cl in f.GetEdgesAsCurveLoops():
                for c in cl:
                    a, b = c.GetEndPoint(0), c.GetEndPoint(1)
                    if a.DistanceTo(b) < .05 / M: continue
                    key = tuple(sorted([(round(a.X, 1), round(a.Y, 1), round(a.Z, 1)), (round(b.X, 1), round(b.Y, 1), round(b.Z, 1))]))
                    edges.setdefault(key, []).append((r, f, a, b))
    out = []
    for key, segs in edges.items():
        r, f, a, b = segs[0]; L_ = a.DistanceTo(b) * M; horiz = abs(a.Z - b.Z) < .02 / M; mid = (a + b) * .5
        if len(segs) >= 2:
            # step from the edge midpoint towards the interior of each face (perpendicular to the edge, towards the face
            # centroid): both faces lower → limatesa / cumbrera; both higher → limahoya (sloped or horizontal)
            t = DB.XYZ(b.X - a.X, b.Y - a.Y, 0); t = t.Normalize() if t.GetLength() > 1e-9 else DB.XYZ.BasisX
            zs = []
            perp = DB.XYZ(-t.Y, t.X, 0)
            for _, fx, _, _ in segs[:2]:
                n = fx.FaceNormal
                for sg in (1, -1):     # the side of the edge where the face actually is
                    p = mid + perp * (sg * .2 / M); z = fx.Origin.Z - (n.X * (p.X - fx.Origin.X) + n.Y * (p.Y - fx.Origin.Y)) / n.Z
                    pr = fx.Project(DB.XYZ(p.X, p.Y, z))
                    if pr is not None and pr.Distance < .01 and fx.IsInside(pr.UVPoint):
                        zs.append(z - mid.Z); break
            down = all(z < -1e-4 for z in zs) and zs; up = all(z > 1e-4 for z in zs) and zs
            kind = ('cumbrera' if horiz else 'limatesa') if down else (('limahoya' if not horiz else 'limahoya horizontal') if up else 'quiebre')
        else:
            n = f.FaceNormal; low = horiz and (f.Origin.Z - (n.X * (mid.X - f.Origin.X) + n.Y * (mid.Y - f.Origin.Y)) / n.Z) >= mid.Z - .01 / M
            near_wall = any(w.get_BoundingBox(None) is not None and w.get_BoundingBox(None).Min.X - .3 / M <= mid.X <= w.get_BoundingBox(None).Max.X + .3 / M and
                            w.get_BoundingBox(None).Min.Y - .3 / M <= mid.Y <= w.get_BoundingBox(None).Max.Y + .3 / M and w.get_BoundingBox(None).Max.Z >= mid.Z + .2 / M for w in walls)
            down = DB.XYZ(-n.X, -n.Y, 0)
            # an eave: horizontal edge at the low side of its face (face rises away from it)
            inner = mid - down.Normalize() * (.3 / M) if down.GetLength() > 1e-6 else mid
            zin = f.Origin.Z - (n.X * (inner.X - f.Origin.X) + n.Y * (inner.Y - f.Origin.Y)) / n.Z
            if horiz and zin > mid.Z + .01 / M and not near_wall: kind = 'alero'
            elif near_wall: kind = 'muro'
            else: kind = 'borde'
        out.append({'kind': kind, 'roof': eid(r), 'a': mxyz(a), 'b': mxyz(b), 'len_m': round(L_, 3), 'nFaces': len(segs), 'roofs': sorted(set(eid(s[0]) for s in segs))})
    return out

def inventory(doc, ld):
    old = dict((e['id'], e) for e in L.read('roof-plan')['elements'])
    roofs = [e for e in DB.FilteredElementCollector(ld).OfClass(DB.RoofBase)]
    rcode = dict((eid(r), old[eid(r)]['code']) for r in roofs if eid(r) in old)
    aguas = []
    for r in sorted(roofs, key=lambda r: rcode.get(eid(r), 'Z')):
        fs = sorted(roof_faces(r), key=lambda f: -f.Area)
        for k, f in enumerate(fs):
            n = f.FaceNormal; sl = math.degrees(math.acos(min(1, abs(n.Z)))); bb = f.GetBoundingBox()
            c = f.Evaluate((bb.Min + bb.Max) * .5)
            pts = [cc.GetEndPoint(0) for cc in f.GetEdgesAsCurveLoops()[0]]
            aguas.append({'code': '%s%s' % (rcode.get(eid(r), 'CU'), 'abcdefghij'[k]), 'roof': eid(r), 'roofCode': rcode.get(eid(r)), 'area_m2': round(f.Area * M * M, 3),
                          'slope_deg': round(sl, 1), 'slope_pct': round(math.tan(math.radians(sl)) * 100, 1), 'down': [round(-n.X, 3), round(-n.Y, 3)],
                          'center': mxyz(c), 'zmin_m': round(min(p.Z for p in pts) * M, 3), 'zmax_m': round(max(p.Z for p in pts) * M, 3), 'poly': [mxyz(p) for p in pts]})
    walls = [w for w in DB.FilteredElementCollector(ld).OfClass(DB.Wall)]
    edges = classify(ld, roofs, walls)
    fr = []
    for e in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_StructuralFraming).WhereElementIsNotElementType():
        t = ld.GetElement(e.GetTypeId()); tn = u(name(t))
        kind = 'VC' if 'Viga Cubierta' in tn else ('VP' if ('Cabio' in tn or 'Viga Principal' in tn) else ('CR' if ('List' in tn or 'Correa' in tn) else None))
        if kind is None or not isinstance(e.Location, DB.LocationCurve): continue
        c = e.Location.Curve; a, b = c.GetEndPoint(0), c.GetEndPoint(1)
        fr.append({'id': eid(e), 'kind': kind, 'code': old.get(eid(e), {}).get('code'), 'type': tn, 'w_m': round(t.LookupParameter('Width').AsDouble() * M, 3), 'h_m': round(t.LookupParameter('Height').AsDouble() * M, 3),
                   'len_m': round(c.Length * M, 3), 'a': mxyz(a), 'b': mxyz(b), 'roof': old.get(eid(e), {}).get('roof') or 'CU-02'})
    n = {'VC': max([int(x['code'][3:]) for x in fr if x['kind'] == 'VC' and x['code']] or [0]), 'VP': max([int(x['code'][3:]) for x in fr if x['kind'] == 'VP' and x['code']] or [0])}
    for x in sorted(fr, key=lambda x: x['id']):
        if not x['code']:
            n[x['kind']] += 1; x['code'] = ('VC-%02d' if x['kind'] == 'VC' else 'VP-%03d') % n[x['kind']]; x['new'] = True
    rooms = []
    for rm in DB.FilteredElementCollector(ld).OfCategory(DB.BuiltInCategory.OST_Rooms).WhereElementIsNotElementType():
        if rm.Area > 0 and isinstance(rm.Location, DB.LocationPoint):
            rooms.append({'id': eid(rm), 'number': u(rm.Number), 'name': u(rm.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()), 'level': u(name(ld.GetElement(rm.LevelId))), 'p': mxyz(rm.Location.Point)})
    rt = ld.GetElement(roofs[0].GetTypeId()); cs = rt.GetCompoundStructure()
    layers = [[str(l.Function), u(name(ld.GetElement(l.MaterialId))) if l.MaterialId.IntegerValue > 0 else u'', round(l.Width * M, 4)] for l in cs.GetLayers()]
    return {'aguas': aguas, 'edges': edges, 'framing': fr, 'rooms': rooms, 'roofType': u(name(rt)), 'layers': layers}

# ---------------------------------------------------------------- sheets (host = DOC file)

RUBRO = u'CUBIERTA'
PRE = 'ADER CUB R29 - '
FOOT = u'Cubierta R29 (archivo de documentación con el modelo principal vinculado). Paquete modelado: teja 20 · cámara ventilada 25 (contraclavaderas) · membrana respirable · EPS 75 entre clavaderas · barrera de vapor · machimbre 3/4" visto. Cabios LVL 5×15 c/0,96; vigas VC LVL 6×20 a verificar por el calculista. Cotas en metros.'
ECOL = {'alero': (40, 140, 60), 'cumbrera': (200, 30, 30), 'limatesa': (220, 120, 0), 'limahoya': (25, 98, 200), 'limahoya horizontal': (25, 98, 200), 'quiebre': (25, 98, 200), 'muro': (150, 40, 120), 'borde': (120, 120, 120)}
WOOD_ROOMS = (u'Playroom', u'Comedor', u'Living', u'Puente', u'SM', u'Hall PE', u'Atelier', u'Hall', u'Sala de TV')

def P(a): return DB.XYZ(a[0] / M, a[1] / M, a[2] / M)

def deg(x): return (u'%.1f' % x).replace(u'.', u',')

def cen(a):
    ps = a['poly']; return DB.XYZ(sum(p[0] for p in ps) / len(ps) / M, sum(p[1] for p in ps) / len(ps) / M, sum(p[2] for p in ps) / len(ps) / M)

def line(doc, v, p0, p1, rgb, w=6):
    if p0.DistanceTo(p1) < .01: return None
    dc = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(p0, p1))
    ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineColor(DB.Color(*rgb)); ov.SetProjectionLineWeight(w); v.SetElementOverrides(dc.Id, ov)
    return dc

def circle(doc, v, c, r, rgb):
    arc = DB.Arc.Create(c, r, 0, 2 * math.pi - 1e-3, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dc = doc.Create.NewDetailCurve(v, arc); ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineColor(DB.Color(*rgb)); ov.SetProjectionLineWeight(6); v.SetElementOverrides(dc.Id, ov)

ARROWS = [(0, u'→'), (45, u'↗'), (90, u'↑'), (135, u'↖'), (180, u'←'), (225, u'↙'), (270, u'↓'), (315, u'↘')]
def arrow(d):
    ang = math.degrees(math.atan2(d[1], d[0])) % 360
    return min(ARROWS, key=lambda a: min(abs(a[0] - ang), 360 - abs(a[0] - ang)))[1]

def roof_plan(doc, lvname, vname, show_roofs=True):
    lev = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if name(l) == lvname)
    d = L.read('cub29-plan'); pts = [P(p) for a in d['aguas'] for p in a['poly']]
    bx = DB.BoundingBoxXYZ(); pad = 2.0 / M
    bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, lev.Elevation - 5 / M); bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, lev.Elevation + 5 / M)
    v = DB.ViewPlan.Create(doc, DB.ElementId(Int64(L.PLAN_VFT)), lev.Id); L.setup_view(doc, v); v.Name = vname
    v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False
    v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)
    vr = v.GetViewRange()
    for plane, off in [(DB.PlanViewPlane.TopClipPlane, 3.0), (DB.PlanViewPlane.CutPlane, 2.5), (DB.PlanViewPlane.BottomClipPlane, -4.0), (DB.PlanViewPlane.ViewDepthPlane, -4.0)]:
        vr.SetLevelId(plane, lev.Id); vr.SetOffset(plane, off / M)
    v.SetViewRange(vr)
    for c, hide in [(DB.BuiltInCategory.OST_Roofs, not show_roofs), (DB.BuiltInCategory.OST_StructuralFraming, show_roofs), (DB.BuiltInCategory.OST_Furniture, True)]:
        try: v.SetCategoryHidden(DB.ElementId(c), hide)
        except Exception: pass
    return v, lev, d

def edge_kind(e, roofs_n):
    k = e['kind']
    if k == 'quiebre' and len(e.get('roofs', [])) > 1: return 'limahoya'
    return k

def sheet_p01(doc):
    v, lev, d = roof_plan(doc, u'03. Planta de Techos', PRE + 'PLANTA DE TECHOS')
    z = v.Origin.Z; dims = []; bajadas = []
    for e in d['edges']:
        k = edge_kind(e, None)
        if e['len_m'] < .2: continue
        a, b = P(e['a']), P(e['b']); a = DB.XYZ(a.X, a.Y, z); b = DB.XYZ(b.X, b.Y, z)
        line(doc, v, a, b, ECOL.get(k, (0, 0, 0)), 9 if k in ('cumbrera', 'limatesa', 'limahoya', 'limahoya horizontal', 'alero') else 5)
        if k == 'alero':
            nb = int(math.ceil(e['len_m'] / 10.0))
            for i in range(nb):
                q = a + (b - a) * ((i + .5) / nb); circle(doc, v, q, .07 / M, (25, 98, 200)); bajadas.append([round(q.X * M, 2), round(q.Y * M, 2)])
    for a in d['aguas']:
        if a['area_m2'] < 1.0: continue
        c = P(a['center'])
        L.tn(doc, v.Id, DB.XYZ(c.X - .9 / M, c.Y, lev.Elevation), u'%s %s\n%s° · %s %%\n%s m²' % (a['code'], arrow(a['down']), deg(a['slope_deg']), deg(a['slope_pct']), c2(a['area_m2'])), 'tag')
    # eave and ridge levels
    for r in sorted(set(x['roofCode'] for x in d['aguas'] if x['roofCode'])):
        ag = [x for x in d['aguas'] if x['roofCode'] == r]; lo = min(x['zmin_m'] for x in ag); hi = max(x['zmax_m'] for x in ag)
        top = max(ag, key=lambda x: x['zmax_m']); c = P(top['center'])
        L.tn(doc, v.Id, DB.XYZ(c.X - .9 / M, c.Y - 1.2 / M, lev.Elevation), u'%s · alero +%s · cumbrera +%s' % (r, c2(lo), c2(hi)), 'room')
    for rm in d['rooms']:
        nm_ = R1.clean(rm['name'])
        if nm_ in WOOD_ROOMS and rm['level'] != u'00. Planta Baja' or nm_ == u'Hall':
            p = P(rm['p']); L.tn(doc, v.Id, DB.XYZ(p.X - .6 / M, p.Y - .5 / M, lev.Elevation), u'%s %s · machimbre visto' % (rm['number'], nm_), 'room')
    lines = [u'Verde: alero con canaleta · círculo azul: bajada Ø100 (1 cada ≤10 ml).', u'Rojo: cumbrera ventilada · naranja: limatesa · azul: limahoya.', u'Violeta: encuentro con muro (babeta / cupertina).',
             u'Gris: borde libre (fascia).', u'Flecha: sentido de la pendiente.']
    it = X.item(v, v.CropBox, u'Planta de techos por faldón (propuesta)', 'plan', u'Cubierta', [a['code'] for a in d['aguas']], dims, [a['roof'] for a in d['aguas']], lines)
    s = S.lay_sheet(doc, 'CUB-P-01', u'Planta de techos por faldón', u'Aguas, pendientes, cumbreras, limatesas, limahoyas, canaletas y bajadas · locales con machimbre visto', [it], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · P-01')
    return dict(s, kind='general', level=u'03. Planta de Techos', sector=u'Cubierta', bajadas=bajadas)

def sheet_p02(doc):
    v, lev, d = roof_plan(doc, u'03. Planta de Techos', PRE + 'ESTRUCTURA', show_roofs=False)
    z = v.Origin.Z
    for x in d['framing']:
        if x['kind'] != 'VC': continue
        a, b = P(x['a']), P(x['b']); m = (a + b) * .5
        L.tn(doc, v.Id, DB.XYZ(m.X, m.Y, lev.Elevation), x['code'], 'tag')
    notes = {}
    for x in d['framing']:
        if x['kind'] == 'VP': notes.setdefault(x['roof'], []).append(x['len_m'])
    for a in d['aguas']:
        if a['area_m2'] < 15: continue
        ls = notes.get(a['roofCode'], [0]); c = P(a['center'])
        L.tn(doc, v.Id, DB.XYZ(c.X - 1.2 / M, c.Y - 1.0 / M, lev.Elevation), u'Cabios LVL 5×15 c/0,96 · luz máx. %s' % c2(max(ls)), 'room')
    vps = [x for x in d['framing'] if x['kind'] == 'VP' and x['roof'] == 'CU-02']
    lines = [u'VC: vigas LVL 6×20 (cumbreras, limatesas, portantes) · a verificar por calculista.', u'VP: cabios LVL 5×15 c/0,96 (antes 3×10) · CR: listones LVL 2,5×5.',
             u'CU-02: estructura modelada en R29 (%d cabios + VC-35..37).' % len(vps), u'Clavaderas 5×7,5 sobre cabios; contraclavaderas 2,5×5.']
    it = X.item(v, v.CropBox, u'Estructura del techo', 'plan', u'Cubierta', [x['code'] for x in d['framing'] if x['kind'] == 'VC'], [], [x['id'] for x in d['framing']], lines)
    s = S.lay_sheet(doc, 'CUB-P-02', u'Estructura del techo inclinado', u'VC 6×20 · cabios VP 5×15 c/0,96 · listones CR 2,5×5 · CU-02 incluido', [it], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · P-02')
    return dict(s, kind='general', level=u'03. Planta de Techos', sector=u'Cubierta')

def section_roof(doc, d, code, vname):
    ag = [a for a in d['aguas'] if a['roofCode'] == code]; pts = [P(p) for a in ag for p in a['poly']]
    big = max(ag, key=lambda a: a['area_m2']); dn = DB.XYZ(big['down'][0], big['down'][1], 0).Normalize()
    right = dn; c = cen(big)
    xs = [(p - c).DotProduct(right) for p in pts]; zs = [p.Z for p in pts]
    lev0 = min(zs) - 1.0 / M
    other = DB.XYZ(-right.Y, right.X, 0); depth = max(abs((p - c).DotProduct(other)) for p in pts) + .5 / M
    v, bx = X.section(doc, DB.XYZ(c.X, c.Y, lev0), right, min(xs) - 1.0 / M, max(xs) + 1.0 / M, -.5 / M, (max(zs) - lev0) + 1.0 / M, depth, vname)
    doc.Regenerate(); f = L.Frame(v)
    sx = sorted([f.x(DB.XYZ(c.X, c.Y, 0) + right * min(xs)), f.x(DB.XYZ(c.X, c.Y, 0) + right * max(xs))])
    dims = [L.tick_dim(doc, f, code + u' desarrollo en planta', sx, True, max(zs) - f.o.Z + .5 / M, tick=.08 / M),
            L.tick_dim(doc, f, code + u' alero y cumbrera', [min(zs) - f.o.Z, max(zs) - f.o.Z], False, sx[1] + .5 / M, tick=.08 / M)]
    L.tn(doc, v.Id, f.p(sx[0], max(zs) - f.o.Z + .9 / M), u'%s · %s° · paquete R29 (machimbre visto, EPS 75, membrana, cámara ventilada, teja)' % (code, deg(big['slope_deg'])), 'tag')
    return X.item(v, bx, code + u' · corte', 'section', u'Cubierta', [code], dims, [a['roof'] for a in ag[:1]])

def sheet_c01(doc):
    d = L.read('cub29-plan')
    its = [section_roof(doc, d, 'CU-01', PRE + 'CORTE CU-01'), section_roof(doc, d, 'CU-02', PRE + 'CORTE CU-02'), section_roof(doc, d, 'CU-03', PRE + 'CORTE CU-03')]
    s = S.lay_sheet(doc, 'CUB-C-01', u'Cortes de cubierta', u'CU-01, CU-02 (estructura nueva) y CU-03 · ver detalles CUB-D-01 / D-02', its, FOOT, rubro=RUBRO, sheet_name=u'Cubierta · cortes')
    return dict(s, kind='general', level=u'Cortes', sector=u'Cubierta')

# drafting details (real size in m)
def drafting(doc, vname, scale):
    vft = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == DB.ViewFamily.Drafting)
    v = DB.ViewDrafting.Create(doc, vft.Id); v.Name = vname; v.Scale = scale; return v

def dl(doc, v, a, b, w=3):
    c = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(DB.XYZ(a[0] / M, a[1] / M, 0), DB.XYZ(b[0] / M, b[1] / M, 0)))
    ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineWeight(w); v.SetElementOverrides(c.Id, ov); return c

def rect(doc, v, x0, y0, x1, y1, w=3):
    for a, b in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]: dl(doc, v, a, b, w)

def txt(doc, v, x, y, s, key='text'): L.tn(doc, v.Id, DB.XYZ(x / M, y / M, 0), s, key)

def detail_item(doc, v, title, tags, dims):
    doc.Regenerate(); pts = []
    for e in DB.FilteredElementCollector(doc, v.Id).WhereElementIsNotElementType():
        b = e.get_BoundingBox(v)
        if b is not None and e.Category is not None: pts += [b.Min, b.Max]
    bb = DB.BoundingBoxXYZ(); bb.Min = DB.XYZ(min(p.X for p in pts) - .05 / M, min(p.Y for p in pts) - .05 / M, 0); bb.Max = DB.XYZ(max(p.X for p in pts) + .05 / M, max(p.Y for p in pts) + .05 / M, 0)
    return {'view': v, 'box': bb, 'title': title, 'kind': 'detail', 'sector': u'Detalles', 'tags': tags, 'dims': S.dims_out(dims), 'elements': [], 'data': None}

def d_paquete(doc):
    v = drafting(doc, PRE + 'DETALLE PAQUETE', 5)
    layers = [(u'Cabio LVL 5×15 (c/0,96)', .15), (u'Machimbre pino 3/4" visto (barnizado)', .019), (u'Barrera de vapor PE 200 µm', .002), (u'Clavadera 5×7,5 sobre cabio + EPS 75 mm 20 kg/m³', .075),
              (u'Membrana hidrófuga respirable', .002), (u'Contraclavadera 2,5×5 = cámara ventilada 25', .025), (u'Listón 2,5×5 (paso según teja)', .025), (u'Teja cerámica', .02)]
    y = 0.0; dims = []
    rect(doc, v, .40, 0, .45, .15, 5)                      # cabio section
    y = .15
    for k, (t, h) in enumerate(layers[1:], 1):
        if k == 3: rect(doc, v, .40, y, .45, y + h, 4); dl(doc, v, (0, y), (1.0, y), 2); dl(doc, v, (0, y + h), (1.0, y + h), 2)
        elif k == 5: rect(doc, v, .4125, y, .4375, y + h, 4); dl(doc, v, (0, y + h), (1.0, y + h), 1)
        elif k == 6: rect(doc, v, .10, y, .15, y + h, 3); rect(doc, v, .70, y, .75, y + h, 3)
        else: rect(doc, v, 0, y, 1.0, y + max(h, .003), 4 if k in (1, 7) else 2)
        ly = .02 + k * .045; dl(doc, v, (1.0, y + h / 2), (1.06, ly), 1); txt(doc, v, 1.08, ly + .012, t)
        y += h
    f = L.AxisFrame(v, DB.XYZ.Zero, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims.append(L.tick_dim(doc, f, u'Paquete total sobre cabio', [.15 / M, y / M], False, -.08 / M, tick=.02 / M))
    dims.append(L.tick_dim(doc, f, u'Cabio', [0, .15 / M], False, -.08 / M, tick=.02 / M))
    txt(doc, v, 0, -.06, u'Corte tipo perpendicular a la pendiente (esquemático, esc. 1:5)', 'sub')
    return detail_item(doc, v, u'Paquete de cubierta · corte tipo', [u'PAQUETE'], dims)

def d_apoyo(doc):
    v = drafting(doc, PRE + 'DETALLE APOYO', 10)
    rect(doc, v, 0, 0, .20, .40, 6)                         # muro / viga de apoyo
    rect(doc, v, -.05, .40, .25, .46, 4)                    # solera de apoyo 6x?
    s = math.tan(math.radians(26.7))
    for x0 in (-.3,):
        pass
    dl(doc, v, (-.40, .46 - .0), (.60, .46 + 1.0 * s), 5); dl(doc, v, (-.40, .61), (.60, .61 + 1.0 * s), 5)   # cabio (inclinado)
    dl(doc, v, (.25, .46), (.25, .46 + .25 * s + .15), 2)
    txt(doc, v, -.40, .30, u'Cabio LVL 5×15 con rebaje (pájaro) sobre solera\nfijado con escuadra / estribo metálico galvanizado\ny tirafondo Ø8 al apoyo (muro o viga VC)')
    txt(doc, v, .25, .05, u'Apoyo: muro de Estructura (MH) o viga VC')
    return detail_item(doc, v, u'Apoyo de cabio y anclaje', [u'APOYO'], [])

def d_zingueria(doc):
    v = drafting(doc, PRE + 'DETALLE ZINGUERIA', 10); dims = []
    s = math.tan(math.radians(26.7))
    # 1) alero con canaleta y entrada de aire
    dl(doc, v, (0, 0), (.9, .9 * s), 5); dl(doc, v, (0, .14), (.9, .14 + .9 * s), 3)
    rect(doc, v, -.14, -.12, 0, .02, 4); txt(doc, v, -.16, -.20, u'1 · Alero: canaleta chapa galv. N°24 + peine anti-pájaros (entrada de aire a la cámara)')
    # 2) cumbrera ventilada
    ox = 1.3
    dl(doc, v, (ox, 0), (ox + .5, .5 * s), 5); dl(doc, v, (ox + 1.0, 0), (ox + .5, .5 * s), 5)
    rect(doc, v, ox + .42, .5 * s + .02, ox + .58, .5 * s + .08, 4); txt(doc, v, ox, -.20, u'2 · Cumbrera ventilada: pieza cerámica sobre perfil de ventilación')
    # 3) limahoya
    ox = 2.6
    dl(doc, v, (ox, .5 * s), (ox + .5, 0), 5); dl(doc, v, (ox + 1.0, .5 * s), (ox + .5, 0), 5); dl(doc, v, (ox + .3, .2 * s), (ox + .5, -.03), 3); dl(doc, v, (ox + .7, .2 * s), (ox + .5, -.03), 3)
    txt(doc, v, ox, -.20, u'3 · Limahoya: chapa galv. con pestañas, membrana continua debajo')
    # 4) babeta contra muro
    ox = 3.9
    rect(doc, v, ox + .8, -.1, ox + 1.0, .9, 5); dl(doc, v, (ox, 0), (ox + .8, .8 * s), 5)
    dl(doc, v, (ox + .6, .6 * s + .02), (ox + .8, .8 * s + .02), 3); dl(doc, v, (ox + .8, .8 * s + .02), (ox + .8, .8 * s + .2), 3)
    txt(doc, v, ox, -.20, u'4 · Babeta / cupertina contra muro: chapa galv. + sellador')
    return detail_item(doc, v, u'Zinguería y ventilación', [u'ZINGUERIA'], dims)

def sheet_details(doc):
    s1 = S.lay_sheet(doc, 'CUB-D-01', u'Paquete de cubierta y apoyo de cabio', u'Machimbre visto · barrera de vapor · EPS 75 entre clavaderas · membrana respirable · cámara ventilada · teja', [d_paquete(doc), d_apoyo(doc)], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · D-01')
    s2 = S.lay_sheet(doc, 'CUB-D-02', u'Zinguería y ventilación', u'Alero con canaleta y entrada de aire · cumbrera ventilada · limahoya · babeta', [d_zingueria(doc)], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · D-02')
    return [dict(s1, kind='general', level=u'Detalles', sector=u'Detalles'), dict(s2, kind='general', level=u'Detalles', sector=u'Detalles')]

def project_info(doc, ld):
    src = ld.ProjectInformation; dst = doc.ProjectInformation
    for bip in (DB.BuiltInParameter.PROJECT_NAME, DB.BuiltInParameter.CLIENT_NAME, DB.BuiltInParameter.PROJECT_NUMBER, DB.BuiltInParameter.PROJECT_ISSUE_DATE,
                DB.BuiltInParameter.PROJECT_STATUS, DB.BuiltInParameter.PROJECT_AUTHOR, DB.BuiltInParameter.PROJECT_ADDRESS):
        a, b = src.get_Parameter(bip), dst.get_Parameter(bip)
        if a is not None and b is not None and not b.IsReadOnly and a.AsString(): b.Set(a.AsString())
    return [{'info': True, 'views': [], 'sheetId': 0, 'number': 'info'}]

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'CUB-00'; sheet.Name = u'Cubierta · índice'
    head = u'CASA ÁNGEL · CUBIERTA · ÍNDICE Y CÓMPUTO (R29)'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'CUB-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'Cubierta', 'sector': u'General'}]

def plain(doc, label, body):
    tx = DB.Transaction(doc, label); tx.Start()
    try: r = body(); tx.Commit(); return r
    except Exception: tx.RollBack(); raise

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    ld = CTX.activate(doc, L, [L, S, F, X, None])
    assert ld is not None, 'Abrir Casa-Angel-DOC-Cubierta.rvt'
    part = job['part']
    if part == 'inventory':
        d = inventory(doc, ld); d['readAt'] = L.now(); R1.write(os.path.join(OUT, 'cub29-plan.json'), d)
        import collections
        ek = collections.Counter(); el_ = collections.Counter()
        for e in d['edges']: ek[e['kind']] += 1; el_[e['kind']] += e['len_m']
        return {'status': 'success', 'aguas': len(d['aguas']), 'edges': dict((k, [ek[k], round(el_[k], 2)]) for k in ek), 'framing': dict((k, len([x for x in d['framing'] if x['kind'] == k])) for k in ('VC', 'VP', 'CR')),
                'new': [x['code'] for x in d['framing'] if x.get('new')], 'roofType': d['roofType']}
    path = os.path.join(OUT, 'cub29-' + part + '.json')
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in ('cub29-sheets.json', 'cub29-details.json', 'cub29-index.json'):
            if not os.path.exists(os.path.join(OUT, fn)): continue
            rec = R1.read(os.path.join(OUT, fn))
            for sh in rec['sheets']:
                opts.FileName = 'r29-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([doc.GetElement(DB.ElementId(Int64(sh['sheetId']))).Id]), opts)); done.append(sh['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if job.get('resetPart'):
        rec = R1.read(path)
        def body():
            n = 0
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [v['id'] for v in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id); n += 1
            return n
        n = plain(doc, 'ADER CUB R29 - reset ' + part, body); os.remove(path); doc.Save(); return {'status': 'success', 'deleted': n}
    if os.path.exists(path): return {'status': 'success', 'existing': True}
    L.register_font()
    def body():
        if part == 'sheets': return [sheet_p01(doc), sheet_p02(doc), sheet_c01(doc)]
        if part == 'details': return sheet_details(doc)
        if part == 'index': return index_part(doc, job)
        if part == 'info': return project_info(doc, ld)
        raise Exception('Unknown part')
    sheets = plain(doc, 'ADER CUB R29 - ' + part, body)
    for sh in sheets:
        for v in sh['views']: v.pop('view', None)
    R1.write(path, {'part': part, 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [v['scale'] for v in sh['views']]) for sh in sheets]}
