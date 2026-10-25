# -*- coding: utf-8 -*-
"""R30 Cubierta (DOC-Cubierta), on top of R29 (revit_cub_doc_r29):
- P-01 / P-02 / C-01 rebuilt without overlapping texts: greedy label placement with leaders, two-line agua labels,
  room numbers as a separate layer + legend/table column inside the plan crop, no level heads in the sections.
- D-01 (1:5 / 1:10): package perpendicular and parallel to the slope with hatched layers at real thickness and total
  dimension; cabio support over MH and over VC; cabio-VC junction (hanger).
- D-02 (1:5): alero, cumbrera ventilada, limatesa, limahoya, babeta, bajada.
Writes the same record files as R29 (cub29-sheets.json / cub29-details.json) so publish_cub_r29 keeps working."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
B = imp.load_source('ader_cubdoc_r29_for_r30', os.path.join(ROOT, 'revit_cub_doc_r29.py'))
L = B.L; S = B.S; X = B.X; R1 = B.R1; CTX = B.CTX
M = L.M; OUT = L.OUT; eid = L.eid; name = B.name; u = B.u; c2 = B.c2; P = B.P; deg = B.deg
PRE = 'ADER CUB R30 - '
FOOT = B.FOOT.replace(u'Cubierta R29', u'Cubierta R30')
RUBRO = B.RUBRO
SLOPE = 26.7

# ---------------------------------------------------------------- label placement (plan views, model units = ft)
CW, LH = .62 * 3.5 / 1000, 1.65 * 3.5 / 1000      # tag char width / line height on paper (m)

def tbox(text, scale, key='tag'):
    k = {'tag': 1.0, 'text': 3.0 / 3.5, 'room': 4.0 / 3.5}[key]
    ls = text.split(u'\n'); w = max(len(x) for x in ls) * CW * scale * k + .25; h = len(ls) * LH * scale * k + .2
    return w / M, h / M

def free(b, placed, crop):
    x0, y0, x1, y1 = b
    if crop and (x0 < crop[0] or x1 > crop[2] or y0 < crop[1] or y1 > crop[3]): return False
    for p in placed:
        if not (x1 < p[0] or x0 > p[2] or y1 < p[1] or y0 > p[3]): return False
    return True

def place(doc, v, anchor, text, placed, crop, key='tag', z=0.0, dirs=None):
    """Top-left text origin near `anchor` (XYZ) without overlapping `placed`; leader + dot when moved."""
    w, h = tbox(text, v.Scale, key)
    cands = [(0, 0)]
    for r in (1.2, 2.0, 3.0, 4.0, 5.5, 7.0):
        for a in (dirs or (0, 45, 90, 135, 180, 225, 270, 315)):
            cands.append((r * math.cos(math.radians(a)) / M, r * math.sin(math.radians(a)) / M))
    fb = None
    for dx, dy in cands:
        cx, cy = anchor.X + dx, anchor.Y + dy                      # label centre
        b = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        if free(b, placed, crop): break
        if fb is None and free(b, [], crop): fb = (dx, dy, b)
    else:
        if fb: dx, dy, b = fb                                       # no free slot: stay inside the crop
    placed.append(b)
    L.tn(doc, v.Id, DB.XYZ(b[0], b[3], z), text, key)
    if (dx, dy) != (0, 0):
        q = DB.XYZ(min(max(anchor.X, b[0]), b[2]), min(max(anchor.Y, b[1]), b[3]), z)
        a = DB.XYZ(anchor.X, anchor.Y, z)
        B.line(doc, v, a, q, (90, 90, 90), 1); B.circle(doc, v, a, .05 / M, (90, 90, 90))
    return b

def widen(v, left_m):
    bx = v.CropBox; mn = bx.Min; bx.Min = DB.XYZ(mn.X - left_m / M, mn.Y, mn.Z); v.CropBox = bx
    return bx

def legend(doc, v, x, ytop, z, blocks, placed):
    y = ytop
    for title, lines in blocks:
        L.tn(doc, v.Id, DB.XYZ(x, y, z), title, 'room'); w, h = tbox(title, v.Scale, 'room'); placed.append((x, y - h, x + w, y)); y -= h
        if lines:
            t = u'\n'.join(lines); L.tn(doc, v.Id, DB.XYZ(x, y, z), t, 'text'); w, h = tbox(t, v.Scale, 'text'); placed.append((x, y - h, x + w, y)); y -= h + .4 / M

def crop_of(v):
    bx = v.CropBox; return (bx.Min.X, bx.Min.Y, bx.Max.X, bx.Max.Y)

# ---------------------------------------------------------------- P-01
def sheet_p01(doc):
    v, lev, d = B.roof_plan(doc, u'03. Planta de Techos', PRE + 'PLANTA DE TECHOS')
    z = v.Origin.Z; zl = lev.Elevation; bajadas = []; placed = []
    for e in d['edges']:
        k = B.edge_kind(e, None)
        if e['len_m'] < .2: continue
        a, b = P(e['a']), P(e['b']); a = DB.XYZ(a.X, a.Y, z); b = DB.XYZ(b.X, b.Y, z)
        B.line(doc, v, a, b, B.ECOL.get(k, (0, 0, 0)), 9 if k in ('cumbrera', 'limatesa', 'limahoya', 'limahoya horizontal', 'alero') else 5)
        if k == 'alero':
            nb = int(math.ceil(e['len_m'] / 10.0))
            for i in range(nb):
                q = a + (b - a) * ((i + .5) / nb); B.circle(doc, v, q, .07 / M, (25, 98, 200)); bajadas.append([round(q.X * M, 2), round(q.Y * M, 2)])
    W = 11.0; widen(v, W); crop = crop_of(v)
    # room numbers first (small, at the room point), then agua labels (big ones first: they keep their centre)
    rooms = []
    for rm in d['rooms']:
        nm_ = R1.clean(rm['name'])
        if nm_ in B.WOOD_ROOMS and rm['level'] != u'00. Planta Baja' or nm_ == u'Hall':
            p = P(rm['p']); rooms.append(u'%s %s' % (rm['number'], nm_))
            place(doc, v, DB.XYZ(p.X, p.Y, zl), u'(%s)' % rm['number'], placed, crop, 'text', zl)
    ag = sorted([a for a in d['aguas'] if a['area_m2'] >= 1.0], key=lambda a: -a['area_m2'])
    for a in ag:
        c = P(a['center'])
        place(doc, v, DB.XYZ(c.X, c.Y, zl), u'%s %s\n%s° · %s %%' % (a['code'], B.arrow(a['down']), deg(a['slope_deg']), deg(a['slope_pct'])), placed, crop, 'tag', zl)
    table = []
    for r in sorted(set(x['roofCode'] for x in d['aguas'] if x['roofCode'])):
        g = [x for x in d['aguas'] if x['roofCode'] == r]
        table.append(u'%s · alero +%s · cumbrera +%s · %s m²' % (r, c2(min(x['zmin_m'] for x in g)), c2(max(x['zmax_m'] for x in g)), c2(sum(x['area_m2'] for x in g))))
        for x in sorted(g, key=lambda x: x['code']):
            if x['area_m2'] >= 1.0: table.append(u'   %s  %s m²  %s°' % (x['code'], c2(x['area_m2']), deg(x['slope_deg'])))
    lines = [u'Verde: alero con canaleta', u'Círculo azul: bajada Ø100 (1 c/ ≤10 ml)', u'Rojo: cumbrera ventilada', u'Naranja: limatesa · azul: limahoya',
             u'Violeta: encuentro con muro (babeta)', u'Gris: borde libre (fascia)', u'Flecha: sentido de la pendiente', u'(nn): local con machimbre visto']
    legend(doc, v, crop[0] + .3 / M, crop[3] - .3 / M, zl, [(u'Referencias', lines), (u'Faldones (aguas)', table), (u'Machimbre visto', rooms)], [])
    it = X.item(v, v.CropBox, u'Planta de techos por faldón', 'plan', u'Cubierta', [a['code'] for a in d['aguas']], [], [a['roof'] for a in d['aguas']], lines)
    s = S.lay_sheet(doc, 'CUB-P-01', u'Planta de techos por faldón', u'Aguas, pendientes, cumbreras, limatesas, limahoyas, canaletas y bajadas · locales con machimbre visto', [it], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · P-01')
    return dict(s, kind='general', level=u'03. Planta de Techos', sector=u'Cubierta', bajadas=bajadas)

# ---------------------------------------------------------------- P-02
def sheet_p02(doc):
    v, lev, d = B.roof_plan(doc, u'03. Planta de Techos', PRE + 'ESTRUCTURA', show_roofs=False)
    zl = lev.Elevation; placed = []
    widen(v, 11.0); crop = crop_of(v)
    vcs = sorted([x for x in d['framing'] if x['kind'] == 'VC'], key=lambda x: -x['len_m'])
    for x in vcs:
        a, b = P(x['a']), P(x['b']); m = (a + b) * .5; t = math.degrees(math.atan2(b.Y - a.Y, b.X - a.X))
        place(doc, v, DB.XYZ(m.X, m.Y, zl), x['code'], placed, crop, 'tag', zl, dirs=(t + 90, t - 90, t + 45, t - 45, t + 135, t - 135, t, t + 180))
    luz = {}
    for x in d['framing']:
        if x['kind'] == 'VP': luz.setdefault(x['roof'], []).append(x['len_m'])
    vps = [x for x in d['framing'] if x['kind'] == 'VP' and x['roof'] == 'CU-02']
    tab = [u'%s · %d cabios · luz máx. %s' % (r, len(ls), c2(max(ls))) for r, ls in sorted(luz.items())]
    vct = [u'%s  %s ml' % (x['code'], c2(x['len_m'])) for x in sorted(vcs, key=lambda x: x['code'])]
    half = (len(vct) + 1) // 2
    lines = [u'VC: vigas LVL 6×20 (cumbreras, limatesas,', u'   portantes) · a verificar por calculista', u'VP: cabios LVL 5×15 c/0,96 (antes 3×10)', u'CR: listones LVL 2,5×5',
             u'CU-02: modelada en R29 (%d cabios + VC-35..37)' % len(vps), u'Clavaderas 5×7,5 sobre cabios;', u'contraclavaderas 2,5×5']
    legend(doc, v, crop[0] + .3 / M, crop[3] - .3 / M, zl, [(u'Referencias', lines), (u'Cabios por cubierta', tab), (u'Vigas VC', [a + (u'      ' + vct[i + half] if i + half < len(vct) else u'') for i, a in enumerate(vct[:half])])], [])
    it = X.item(v, v.CropBox, u'Estructura del techo', 'plan', u'Cubierta', [x['code'] for x in vcs], [], [x['id'] for x in d['framing']], lines)
    s = S.lay_sheet(doc, 'CUB-P-02', u'Estructura del techo inclinado', u'VC 6×20 · cabios VP 5×15 c/0,96 · listones CR 2,5×5 · CU-02 incluido', [it], FOOT, rubro=RUBRO, sheet_name=u'Cubierta · P-02')
    return dict(s, kind='general', level=u'03. Planta de Techos', sector=u'Cubierta')

# ---------------------------------------------------------------- C-01
def section_roof(doc, d, code, vname):
    ag = [a for a in d['aguas'] if a['roofCode'] == code]; pts = [P(p) for a in ag for p in a['poly']]
    big = max(ag, key=lambda a: a['area_m2']); right = DB.XYZ(big['down'][0], big['down'][1], 0).Normalize(); c = B.cen(big)
    xs = [(p - c).DotProduct(right) for p in pts]; zs = [p.Z for p in pts]
    lev0 = min(zs) - 1.0 / M
    other = DB.XYZ(-right.Y, right.X, 0); depth = max(abs((p - c).DotProduct(other)) for p in pts) + .5 / M
    v, bx = X.section(doc, DB.XYZ(c.X, c.Y, lev0), right, min(xs) - 1.0 / M, max(xs) + 1.0 / M, -.5 / M, (max(zs) - lev0) + 1.0 / M, depth, vname)
    for cat in (DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_Grids):
        try: v.SetCategoryHidden(DB.ElementId(cat), True)
        except Exception: pass
    doc.Regenerate(); f = L.Frame(v)
    sx = sorted([f.x(DB.XYZ(c.X, c.Y, 0) + right * min(xs)), f.x(DB.XYZ(c.X, c.Y, 0) + right * max(xs))])
    dims = [L.tick_dim(doc, f, code + u' desarrollo en planta', sx, True, max(zs) - f.o.Z + .5 / M, tick=.08 / M),
            L.tick_dim(doc, f, code + u' alero y cumbrera', [min(zs) - f.o.Z, max(zs) - f.o.Z], False, sx[1] + .5 / M, tick=.08 / M)]
    return X.item(v, bx, u'%s · corte · %s° · alero +%s · cumbrera +%s' % (code, deg(big['slope_deg']), c2(min(zs) * M), c2(max(zs) * M)), 'section', u'Cubierta', [code], dims, [a['roof'] for a in ag[:1]])

def sheet_c01(doc):
    d = L.read('cub29-plan')
    its = [section_roof(doc, d, 'CU-01', PRE + 'CORTE CU-01'), section_roof(doc, d, 'CU-02', PRE + 'CORTE CU-02'), section_roof(doc, d, 'CU-03', PRE + 'CORTE CU-03')]
    s = S.lay_sheet(doc, 'CUB-C-01', u'Cortes de cubierta', u'CU-01, CU-02 (estructura nueva) y CU-03 · paquete R29: machimbre visto, EPS 75, membrana, cámara ventilada, teja · ver CUB-D-01 / D-02', its, FOOT, rubro=RUBRO, sheet_name=u'Cubierta · cortes')
    return dict(s, kind='general', level=u'Cortes', sector=u'Cubierta')

# ---------------------------------------------------------------- drafting helpers (metres, 2D)
FILLS = {'madera': u'Madera 1', 'machimbre': u'Madera - Acabado', 'eps': u'Aislamiento - Rígido', 'hormigon': u'Hormigón', 'ladrillo': u'Albañilería - Ladrillo',
         'acero': u'Acero', 'mamposteria': u'Diagonal abajo 1.5 mm', 'teja': u'Teja plana', 'solido': u'<Solid fill>', 'contrachapado': u'Contrachapado'}
_FRT = {}

def frt(doc, key):
    if key in _FRT: return _FRT[key]
    nm_ = u'ADER CUB R30 - ' + key
    t = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType) if u(name(x)) == nm_), None)
    if t is None:
        base = next(x for x in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType) if u(name(x)) == u'Diagonal arriba')
        t = base.Duplicate(nm_)
        pat = next(p for p in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement) if u(name(p)) == FILLS[key] and p.GetFillPattern().Target == DB.FillPatternTarget.Drafting)
        t.ForegroundPatternId = pat.Id
        if key == 'solido': t.ForegroundPatternColor = DB.Color(60, 60, 60)
    _FRT[key] = t; return t

def V(a): return DB.XYZ(a[0] / M, a[1] / M, 0)

def region(doc, v, pts, key):
    cl = DB.CurveLoop()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-4: cl.Append(DB.Line.CreateBound(V(a), V(b)))
    return DB.FilledRegion.Create(doc, frt(doc, key).Id, v.Id, List[DB.CurveLoop]([cl]))

def dl(doc, v, a, b, w=3, pat=None):
    if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-4: return None
    c = doc.Create.NewDetailCurve(v, DB.Line.CreateBound(V(a), V(b)))
    ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineWeight(w)
    if pat:
        lp = next((p for p in DB.FilteredElementCollector(doc).OfClass(DB.LinePatternElement) if u(name(p)) == pat), None)
        if lp is not None: ov.SetProjectionLinePatternId(lp.Id)
    v.SetElementOverrides(c.Id, ov); return c

def poly(doc, v, pts, w=3, closed=True):
    for i in range(len(pts) - (0 if closed else 1)): dl(doc, v, pts[i], pts[(i + 1) % len(pts)], w)

def rect(doc, v, x0, y0, x1, y1, key=None, w=3):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if key: region(doc, v, pts, key)
    poly(doc, v, pts, w)

def add(p, d, s): return (p[0] + d[0] * s, p[1] + d[1] * s)

def quad(p0, d, n, l0, l1, o0, o1):
    """Band along unit d from l0 to l1, between normal offsets o0..o1 (n = unit normal)."""
    return [add(add(p0, d, l0), n, o0), add(add(p0, d, l1), n, o0), add(add(p0, d, l1), n, o1), add(add(p0, d, l0), n, o1)]

def band(doc, v, p0, d, n, l0, l1, o0, o1, key=None, w=3):
    q = quad(p0, d, n, l0, l1, o0, o1)
    if key: region(doc, v, q, key)
    poly(doc, v, q, w); return q

def note(doc, v, target, at, text, key='text'):
    dl(doc, v, target, at, 1); L.tn(doc, v.Id, DB.XYZ(at[0] / M, (at[1] + .012) / M, 0), text, key)

def dimv(doc, v, label, o, d, n, offs, at):
    """Dimension across the package: positions = offsets along n, placed at `at` along d."""
    f = L.AxisFrame(v, V(o), DB.XYZ(d[0], d[1], 0), DB.XYZ(n[0], n[1], 0))
    return L.tick_dim(doc, f, label, [x / M for x in offs], False, at / M, tick=.015 / M)

def dimh(doc, v, label, o, d, n, offs, at):
    f = L.AxisFrame(v, V(o), DB.XYZ(d[0], d[1], 0), DB.XYZ(n[0], n[1], 0))
    return L.tick_dim(doc, f, label, [x / M for x in offs], True, at / M, tick=.015 / M)

def drafting(doc, vname, scale):
    vft = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == DB.ViewFamily.Drafting)
    v = DB.ViewDrafting.Create(doc, vft.Id); v.Name = vname; v.Scale = scale; return v

def item(doc, v, title, tags, dims):
    it = B.detail_item(doc, v, title, tags, dims); it['scale'] = v.Scale; return it

# package stack above the cabio base line (offsets along n, m) — cut between cabios except the cabio band itself
PK = [('cabio', 0, .15, 'madera'), ('machimbre', .15, .169, 'machimbre'), ('barrera', .169, .171, 'solido'), ('eps', .171, .246, 'eps'),
      ('membrana', .246, .248, 'solido'), ('camara', .248, .273, None), ('liston', .273, .298, None), ('teja', .298, .318, 'teja')]
TOP = .318
LABELS = {'cabio': u'Cabio LVL 5×15 c/0,96', 'machimbre': u'Machimbre pino 3/4" visto, barnizado', 'barrera': u'Barrera de vapor PE 200 µm',
          'eps': u'EPS 75 mm 20 kg/m³ entre clavaderas 5×7,5', 'membrana': u'Membrana hidrófuga respirable', 'camara': u'Cámara ventilada 25 (contraclavadera 2,5×5)',
          'liston': u'Listón 2,5×5 (paso según teja)', 'teja': u'Teja cerámica'}

def slope_pkg(doc, v, p0, d, n, l0, l1, skip=(), paso=.34):
    for k, o0, o1, key in PK:
        if k in skip: continue
        if k == 'liston':
            s = l0 + .03
            while s + .05 <= l1: band(doc, v, p0, d, n, s, s + .05, o0, o1, 'madera', 2); s += paso
            continue
        if k == 'camara':
            dl(doc, v, add(add(p0, d, l0), n, o1), add(add(p0, d, l1), n, o1), 1, u'Oculto'); continue
        band(doc, v, p0, d, n, l0, l1, o0, o1, key, 4 if k in ('cabio', 'teja') else 2)

def unit(a): r = math.radians(a); return (math.cos(r), math.sin(r))
def up(d): return (-d[1], d[0]) if d[0] >= 0 else (d[1], -d[0])

def labels_column(doc, v, pts, x, y0, dy=.07, keys=None):
    """pts: list of (target, text); leaders to a column at x."""
    for i, (t, s) in enumerate(pts): note(doc, v, t, (x, y0 - i * dy), s)

# ---------------------------------------------------------------- D-01
def d_perp(doc):
    v = drafting(doc, PRE + 'D-01 PAQUETE PERPENDICULAR', 5); dims = []
    W = 1.40; c1, c2_ = .20, .20 + .957
    for cx in (c1, c2_): rect(doc, v, cx, 0, cx + .05, .15, 'madera', 5)                   # cabios en sección
    rect(doc, v, 0, .15, W, .169, 'machimbre', 3); rect(doc, v, 0, .169, W, .171, 'solido', 1)
    for cx in (c1, c2_): rect(doc, v, cx, .171, cx + .05, .246, 'madera', 4)               # clavaderas 5x7,5
    for a, b in ((0, c1), (c1 + .05, c2_), (c2_ + .05, W)): rect(doc, v, a, .171, b, .246, 'eps', 2)
    rect(doc, v, 0, .246, W, .248, 'solido', 1)
    for cx in (c1, c2_): rect(doc, v, cx, .248, cx + .05, .273, 'madera', 3)               # contraclavaderas
    rect(doc, v, 0, .273, W, .298, None, 2); dl(doc, v, (0, .2855), (W, .2855), 1, u'Oculto')   # listón en vista (corrido)
    rect(doc, v, 0, .298, W, .318, 'teja', 4)
    x = W + .10; tgt = [((c2_ + .025, .07), LABELS['cabio']), ((W - .05, .16), LABELS['machimbre']), ((W - .05, .170), LABELS['barrera']), ((W - .1, .21), LABELS['eps']),
                       ((c2_ + .025, .21), u'Clavadera 5×7,5 sobre cabio'), ((W - .05, .247), LABELS['membrana']), ((c2_ + .025, .26), u'Contraclavadera 2,5×5 (cámara 25)'),
                       ((W - .05, .286), u'Listón 2,5×5 en vista'), ((W - .05, .308), LABELS['teja'])]
    labels_column(doc, v, tgt, x, .50, .045)
    o = (0, 0); d = (1, 0); n = (0, 1)
    dims.append(dimv(doc, v, u'Capas', o, d, n, [0, .15, .169, .171, .246, .248, .273, .298, .318], -.06))
    dims.append(dimv(doc, v, u'Paquete total', o, d, n, [0, .318], -.16))
    dims.append(dimh(doc, v, u'Separación de cabios', o, d, n, [c1 + .025, c2_ + .025], -.07))
    L.tn(doc, v.Id, V((0, -.13)), u'Corte perpendicular a la pendiente · cotas en m', 'text')
    return item(doc, v, u'D-01a · Paquete · corte perpendicular a la pendiente', [u'PAQUETE'], dims)

def d_par(doc):
    v = drafting(doc, PRE + 'D-01 PAQUETE PARALELO', 5); dims = []
    d = unit(SLOPE); n = up(d); p0 = (0, 0); Ln = 1.30
    for k, o0, o1, key in PK:
        if k == 'liston':
            s = .05
            while s + .05 <= Ln: band(doc, v, p0, d, n, s, s + .05, o0, o1, 'madera', 2); s += .34
        elif k == 'camara': band(doc, v, p0, d, n, 0, Ln, o0, o1, 'madera', 2)          # contraclavadera cortada a lo largo
        elif k == 'eps': band(doc, v, p0, d, n, 0, Ln, o0, o1, 'madera', 2)             # clavadera cortada a lo largo
        else: band(doc, v, p0, d, n, 0, Ln, o0, o1, key, 4 if k in ('cabio', 'teja') else 2)
    x = Ln * d[0] + .22; top = add(add(p0, d, Ln), n, .32)[1] + .05
    pts = [(add(add(p0, d, .9), n, .075), LABELS['cabio'] + u' (cortado a lo largo)'), (add(add(p0, d, 1.0), n, .16), LABELS['machimbre']), (add(add(p0, d, 1.05), n, .17), LABELS['barrera']),
           (add(add(p0, d, 1.1), n, .21), u'Clavadera 5×7,5 (EPS entre clavaderas, fuera del corte)'), (add(add(p0, d, 1.15), n, .247), LABELS['membrana']),
           (add(add(p0, d, 1.2), n, .26), u'Contraclavadera 2,5×5 = cámara ventilada'), (add(add(p0, d, .75), n, .285), u'Listón 2,5×5 c/0,34 (según teja)'), (add(add(p0, d, 1.25), n, .31), LABELS['teja'])]
    labels_column(doc, v, pts, x, top, .045)
    dims.append(dimv(doc, v, u'Paquete total', p0, d, n, [0, TOP], -.08))
    dims.append(dimh(doc, v, u'Paso de listones', p0, d, n, [.075, .415], TOP + .06))
    L.tn(doc, v.Id, V((0, -.12)), u'Corte paralelo a la pendiente (por el eje del cabio) · %s° · cotas en m' % deg(SLOPE), 'text')
    return item(doc, v, u'D-01b · Paquete · corte paralelo a la pendiente', [u'PAQUETE'], dims)

def cabio_notched(doc, v, seat_x0, seat_x1, ys, x_from, x_to):
    """Cabio 5x15 at SLOPE whose underside passes through (seat_x1, ys); bird's-mouth seat from seat_x0 to seat_x1 at ys."""
    t = math.tan(math.radians(SLOPE)); h = .15 / math.cos(math.radians(SLOPE))
    yb = lambda x: ys + (x - seat_x1) * t
    pts = [(x_from, yb(x_from)), (seat_x0, yb(seat_x0)), (seat_x0, ys), (seat_x1, ys), (x_to, yb(x_to)), (x_to, yb(x_to) + h), (x_from, yb(x_from) + h)]
    region(doc, v, pts, 'madera'); poly(doc, v, pts, 5)
    return yb, h

def d_apoyo_mh(doc):
    v = drafting(doc, PRE + 'D-01 APOYO SOBRE MURO', 10); dims = []
    rect(doc, v, 0, -.60, .20, 0, 'mamposteria', 5)                     # muro MH 20
    rect(doc, v, 0, 0, .20, .20, 'hormigon', 5)                      # encadenado H°A° 20x20
    rect(doc, v, .025, .20, .175, .25, 'madera', 4)                  # solera 5x15
    dl(doc, v, (.10, .05), (.10, .27), 2)                            # varilla roscada Ø10
    yb, h = cabio_notched(doc, v, .025, .175, .25, -.75, .80)
    d = unit(SLOPE); n = up(d); p0 = (.175, .25)
    slope_pkg(doc, v, p0, d, n, (-.75 - .175) / d[0], (.80 - .175) / d[0], skip=('cabio',), paso=.34)
    ang = [(.175, .25), (.175, .33), (.175, .25), (.26, .25)]; dl(doc, v, ang[0], ang[1], 4); dl(doc, v, ang[2], ang[3], 4)   # escuadra
    rect(doc, v, -.775, yb(-.75) - .03, -.75, yb(-.75) + .17, 'madera', 4)    # fascia 2,5x20
    x = 1.05
    pts = [((.10, -.30), u'Muro MH 20 (Estructura)'), ((.10, .10), u'Encadenado H°A° 20×20'), ((.15, .225), u'Solera LVL 5×15 · varilla roscada Ø10 c/0,60 anclada al encadenado'),
           ((.10, .245), u'Rebaje (pico de pájaro) ≤ 1/3 de la altura del cabio'), ((.22, .29), u'Escuadra galvanizada 90×90×2 + tornillos 5×50 (2 por cabio)'),
           ((.40, yb(.40) + .07), u'Cabio LVL 5×15 c/0,96'), ((-.79, yb(-.80) + .1), u'Alero: fascia 2,5×20 + canaleta (ver D-02)')]
    labels_column(doc, v, pts, x, .95, .07)
    f = L.AxisFrame(v, V((0, 0)), DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims.append(L.tick_dim(doc, f, u'Muro', [0, .20 / M], True, -.68 / M, tick=.03 / M))
    L.tn(doc, v.Id, V((-.80, -.70)), u'Apoyo de cabio sobre muro MH · cotas en m', 'text')
    return item(doc, v, u'D-01c · Apoyo de cabio sobre muro (MH)', [u'APOYO-MH'], dims)

def d_apoyo_vc(doc):
    v = drafting(doc, PRE + 'D-01 APOYO SOBRE VC', 10); dims = []
    rect(doc, v, 0, -.20, .06, 0, 'madera', 6)                       # VC 6x20 en sección
    yb, h = cabio_notched(doc, v, 0, .06, 0, -.70, .70)
    for xx in (-.002, .062): dl(doc, v, (xx, -.08), (xx, .06), 4)     # estribo / escuadras a ambos lados
    x = .85
    pts = [((.03, -.10), u'Viga VC LVL 6×20 (cumbrera / portante)'), ((.03, .005), u'Asiento con rebaje sobre VC (≤ 1/3 h)'),
           ((.064, -.04), u'Escuadras galv. a ambos lados + tornillos 5×70'), ((.35, yb(.35) + .08), u'Cabio LVL 5×15 c/0,96')]
    labels_column(doc, v, pts, x, .55, .07)
    f = L.AxisFrame(v, V((0, 0)), DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims.append(L.tick_dim(doc, f, u'VC', [-.20 / M, 0], False, -.10 / M, tick=.03 / M))
    L.tn(doc, v.Id, V((-.70, -.30)), u'Cabio apoyado sobre VC · cotas en m', 'text')
    return item(doc, v, u'D-01d · Apoyo de cabio sobre viga VC', [u'APOYO-VC'], dims)

def d_union(doc):
    v = drafting(doc, PRE + 'D-01 UNION CABIO VC', 10); dims = []
    rect(doc, v, 0, -.20, 1.20, 0, 'madera', 5)                      # VC 6x20 en vista lateral
    hh = .15 / math.cos(math.radians(SLOPE))
    for cx in (.30,):
        rect(doc, v, cx, -hh, cx + .05, 0, 'madera', 4)              # cabio en sección (enrasado arriba)
        poly(doc, v, [(cx - .035, -.02), (cx - .003, -.02), (cx - .003, -hh - .003), (cx + .053, -hh - .003), (cx + .053, -.02), (cx + .085, -.02)], 3, closed=False)
    pts = [((.60, -.10), u'VC LVL 6×20 (vista lateral)'), ((.325, -.08), u'Cabio LVL 5×15 enrasado con la cara superior de la VC'),
           ((.38, -.02), u'Colgador chapa galv. 2 mm (estribo) · 8 tornillos 5×50'), ((.30, -hh - .003), u'Alternativa: apoyo sobre la VC (D-01d)')]
    labels_column(doc, v, pts, 1.35, .25, .07)
    f = L.AxisFrame(v, V((0, 0)), DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims.append(L.tick_dim(doc, f, u'VC', [-.20 / M, 0], False, -.08 / M, tick=.03 / M))
    L.tn(doc, v.Id, V((0, -.35)), u'Unión cabio – VC con colgador (limatesas, limahoyas y portantes) · cotas en m', 'text')
    return item(doc, v, u'D-01e · Unión cabio – VC (colgador)', [u'UNION'], dims)

# ---------------------------------------------------------------- D-02 (1:5)
def d_alero(doc):
    v = drafting(doc, PRE + 'D-02 ALERO', 5); dims = []
    d = unit(SLOPE); n = up(d); p0 = (0, 0); Ln = .90
    slope_pkg(doc, v, p0, d, n, 0, Ln)
    tp = add(p0, n, TOP)
    rect(doc, v, -.025, -.13, 0, .05, 'madera', 4)                   # fascia 2,5x20 a plomo
    cx = -.025; cy = tp[1] - .03
    poly(doc, v, [(cx - .02, cy + .01), (cx - .02, cy - .10), (cx - .14, cy - .10), (cx - .16, cy + .02)], 4, closed=False)   # canaleta
    dl(doc, v, add(p0, n, .247), (cx - .06, cy - .03), 2)            # membrana descarga a canaleta
    for i in range(5): dl(doc, v, (-.005, .17 + i * .012), (.02, .175 + i * .012), 1)            # peine
    pts = [((-.012, -.05), u'Fascia pino 2,5×20 barnizada'), ((cx - .08, cy - .09), u'Canaleta chapa galv. N°24, pendiente 0,5 % a bajada'),
           ((-.01, .19), u'Peine anti-pájaros / rejilla: entrada de aire a la cámara'), ((cx - .05, cy - .025), u'Membrana volcada a la canaleta (goterón)'),
           (add(add(p0, d, .5), n, .07), LABELS['cabio']), (add(add(p0, d, .6), n, .21), LABELS['eps'])]
    labels_column(doc, v, pts, Ln * d[0] + .15, add(add(p0, d, Ln), n, TOP)[1] + .05)
    dims.append(dimv(doc, v, u'Paquete', p0, d, n, [0, TOP], Ln + .05))
    return item(doc, v, u'D-02a · Alero con canaleta y entrada de aire', [u'ALERO'], dims)

def ridge(doc, v, ang, vc=True, top_piece=u'Cumbrera cerámica sobre perfil de ventilación', tag=u'CUMBRERA'):
    for side in (-1, 1):
        dd = (side * math.cos(math.radians(ang)), -math.sin(math.radians(ang)))
        nn = up(dd)
        p0 = (side * .04, 0)
        slope_pkg(doc, v, p0, dd, nn, 0, .70, skip=())
    if vc: rect(doc, v, -.03, -.20, .03, 0, 'madera', 5)
    t = TOP / math.cos(math.radians(ang)) + .04 * math.tan(math.radians(ang))
    rect(doc, v, -.06, t - .01, .06, t + .03, None, 2)               # perfil de ventilación
    poly(doc, v, [(-.13, t), (-.10, t + .07), (0, t + .10), (.10, t + .07), (.13, t)], 4, closed=False)   # pieza
    for s in (-1, 1): dl(doc, v, (s * .04, .25), (s * .04, t - .01), 1, u'Oculto')
    return t

def d_cumbrera(doc):
    v = drafting(doc, PRE + 'D-02 CUMBRERA', 5); dims = []
    t = ridge(doc, v, SLOPE)
    pts = [((0, t + .09), u'Cumbrera cerámica fijada con grampas'), ((.05, t + .01), u'Perfil / cinta de ventilación (salida de aire de la cámara)'),
           ((0, -.15), u'VC LVL 6×20 de cumbrera'), ((.35, .05), LABELS['cabio']), ((.30, .19), LABELS['eps']), ((.04, .2), u'Membrana solapada 15 cm sobre la cumbrera')]
    labels_column(doc, v, pts, .80, t + .25)
    return item(doc, v, u'D-02b · Cumbrera ventilada', [u'CUMBRERA'], dims)

def d_limatesa(doc):
    v = drafting(doc, PRE + 'D-02 LIMATESA', 5); dims = []
    a = math.degrees(math.atan(math.tan(math.radians(SLOPE)) / math.sqrt(2)))
    t = ridge(doc, v, a)
    pts = [((0, t + .09), u'Caballete cerámico + perfil de ventilación'), ((0, -.15), u'VC LVL 6×20 de limatesa (cabios colgados, D-01e)'),
           ((.30, .08), u'Cabios de faldón cortados a inglete'), ((.04, .2), u'Membrana continua sobre la limatesa')]
    labels_column(doc, v, pts, .80, t + .25)
    L.tn(doc, v.Id, V((-.70, -.32)), u'Corte perpendicular a la limatesa (pendiente aparente %s°)' % deg(a), 'text')
    return item(doc, v, u'D-02c · Limatesa', [u'LIMATESA'], dims)

def d_limahoya(doc):
    v = drafting(doc, PRE + 'D-02 LIMAHOYA', 5); dims = []
    a = math.degrees(math.atan(math.tan(math.radians(SLOPE)) / math.sqrt(2)))
    for side in (-1, 1):
        dd = (side * math.cos(math.radians(a)), math.sin(math.radians(a)))
        slope_pkg(doc, v, (side * .04, 0), dd, up(dd), 0, .70)
    rect(doc, v, -.03, -.20, .03, 0, 'madera', 5)
    t = TOP / math.cos(math.radians(a)) - .03
    poly(doc, v, [(-.32, t + .32 * math.tan(math.radians(a)) + .01), (-.06, t - .005), (.06, t - .005), (.32, t + .32 * math.tan(math.radians(a)) + .01)], 5, closed=False)   # canal
    pts = [((0, t - .005), u'Canal de chapa galv. N°24 con pestañas (desarrollo 50 cm)'), ((-.25, .2), u'Membrana continua + faja de refuerzo 50 cm'),
           ((0, -.10), u'VC LVL 6×20 de limahoya'), ((.40, .07), u'Cabios de faldón colgados (D-01e)')]
    labels_column(doc, v, pts, .80, .55)
    L.tn(doc, v.Id, V((-.70, -.28)), u'Corte perpendicular a la limahoya (pendiente aparente %s°)' % deg(a), 'text')
    return item(doc, v, u'D-02d · Limahoya', [u'LIMAHOYA'], dims)

def d_babeta(doc):
    v = drafting(doc, PRE + 'D-02 BABETA', 5); dims = []
    d = unit(SLOPE); n = up(d); Ln = .80
    p0 = (0, 0); end = add(p0, d, Ln)
    slope_pkg(doc, v, p0, d, n, 0, Ln - .02)
    wx = end[0] + .02
    rect(doc, v, wx, end[1] - .30, wx + .20, end[1] + .70, 'mamposteria', 5)       # muro
    tt = add(add(p0, d, Ln - .25), n, TOP + .005); te = (wx, add(add(p0, d, Ln), n, TOP)[1] + .005)
    poly(doc, v, [tt, te, (wx, te[1] + .15), (wx + .025, te[1] + .17)], 4, closed=False)       # babeta
    poly(doc, v, [(wx - .015, te[1] + .22), (wx + .02, te[1] + .19), (wx + .02, te[1] + .25)], 3, closed=False)   # contrababeta en regata
    pts = [(tt, u'Babeta chapa galv. N°24 · solape ≥ 15 cm sobre la teja'), ((wx, te[1] + .10), u'Subida ≥ 15 cm sobre el muro'),
           ((wx + .02, te[1] + .22), u'Contrababeta en regata + sellador poliuretánico'), (add(add(p0, d, .4), n, .247), u'Membrana levantada 15 cm sobre el muro'),
           ((wx + .10, end[1] + .3), u'Muro (Estructura / Exteriores)')]
    labels_column(doc, v, pts, wx + .35, end[1] + .70)
    return item(doc, v, u'D-02e · Babeta contra muro', [u'BABETA'], dims)

def d_bajada(doc):
    v = drafting(doc, PRE + 'D-02 BAJADA', 5); dims = []
    rect(doc, v, .12, -1.0, .32, .05, 'mamposteria', 5)                  # muro
    poly(doc, v, [(-.18, .05), (-.18, -.05), (0, -.05), (0, .05)], 4, closed=False)          # canaleta en sección
    poly(doc, v, [(-.13, -.05), (-.07, -.12), (-.07, -.16)], 3, closed=False); poly(doc, v, [(-.05, -.05), (-.03, -.12), (-.03, -.16)], 3, closed=False)   # embudo
    rect(doc, v, -.10, -.95, 0, -.16, None, 4)                        # caño Ø100
    for yy in (-.30, -.80):
        rect(doc, v, -.105, yy - .015, .005, yy + .015, 'acero', 2); dl(doc, v, (.005, yy), (.12, yy), 3)
    poly(doc, v, [(-.10, -.95), (-.18, -1.0), (-.08, -1.0), (0, -.95)], 3, closed=False)      # codo / zapata
    pts = [((-.10, .0), u'Canaleta chapa galv. N°24'), ((-.06, -.10), u'Embudo soldado + rejilla parahojas'), ((-.05, -.55), u'Bajada PVC Ø100 (1 cada ≤ 10 ml de canaleta)'),
           ((-.05, -.30), u'Abrazaderas galv. c/1,50 m con brocas al muro'), ((-.10, -.99), u'Codo a cámara / desagüe pluvial (ver Sanitarias)')]
    labels_column(doc, v, pts, .50, .10, .06)
    f = L.AxisFrame(v, V((0, 0)), DB.XYZ.BasisX, DB.XYZ.BasisY)
    dims.append(L.tick_dim(doc, f, u'Bajada Ø100', [-.10 / M, 0], True, -1.05 / M, tick=.02 / M))
    return item(doc, v, u'D-02f · Bajada pluvial', [u'BAJADA'], dims)

def lay(doc, number, title, sub, items, sheet_name, scales=(5, 10)):
    old = list(L.SCALES); L.SCALES[:] = list(scales)
    try: s = S.lay_sheet(doc, number, title, sub, items, FOOT, rubro=RUBRO, sheet_name=sheet_name)
    finally: L.SCALES[:] = old
    return dict(s, kind='general', level=u'Detalles', sector=u'Detalles')

def sheet_details(doc):
    s1 = lay(doc, 'CUB-D-01', u'Paquete de cubierta a escala real', u'Capas a espesor real: cabio 15 · machimbre 19 · barrera · EPS 75 · membrana · cámara 25 · listón 25 · teja 20 = 31,8 cm sobre el cabio',
             [d_perp(doc), d_par(doc)], u'Cubierta · D-01', (5, 10))
    s3 = lay(doc, 'CUB-D-03', u'Apoyos y uniones de cabios', u'Apoyo sobre muro MH (solera anclada al encadenado) · apoyo sobre viga VC · unión cabio – VC con colgador',
             [d_apoyo_mh(doc), d_apoyo_vc(doc), d_union(doc)], u'Cubierta · D-03', (10,))
    s2 = lay(doc, 'CUB-D-02', u'Zinguería y ventilación (1)', u'Alero con canaleta y entrada de aire · cumbrera ventilada · limatesa',
             [d_alero(doc), d_cumbrera(doc), d_limatesa(doc)], u'Cubierta · D-02', (10,))
    s4 = lay(doc, 'CUB-D-04', u'Zinguería y ventilación (2)', u'Limahoya · babeta contra muro · bajada pluvial',
             [d_limahoya(doc), d_babeta(doc), d_bajada(doc)], u'Cubierta · D-04', (10,))
    return [s1, s3, s2, s4]

# ---------------------------------------------------------------- run
def run(doc, uidoc, job):
    L.assert_pilot(doc)
    part = job['part']
    if part == 'probe':
        frt_ = [(u(name(t)), u(name(doc.GetElement(t.ForegroundPatternId))) if doc.GetElement(t.ForegroundPatternId) else None) for t in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType)]
        return {'status': 'success', 'filledRegionTypes': frt_}
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None, 'Abrir Casa-Angel-DOC-Cubierta.rvt'
    path = os.path.join(OUT, {'sheets': 'cub29-sheets.json', 'details': 'cub29-details.json'}[part])
    if os.path.exists(path) and R1.read(path).get('revision') == 'R30' and not job.get('redo'): return {'status': 'success', 'existing': True}
    if os.path.exists(path):   # remove the R29 sheets/views of this part first (documentation only)
        rec = R1.read(path)
        def wipe():
            n = 0
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id); n += 1
            return n
        B.plain(doc, 'ADER CUB R30 - borrar laminas R29 ' + part, wipe); os.rename(path, path.replace('.json', '-r29.json' if rec.get('revision') != 'R30' else '-old.json'))
    L.register_font()
    def body():
        if part == 'sheets': return [sheet_p01(doc), sheet_p02(doc), sheet_c01(doc)]
        if part == 'details': return sheet_details(doc)
    sheets = B.plain(doc, 'ADER CUB R30 - ' + part, body)
    for sh in sheets:
        for x in sh['views']: x.pop('view', None)
    R1.write(path, {'part': part, 'revision': 'R30', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [x['scale'] for x in sh['views']]) for sh in sheets]}
