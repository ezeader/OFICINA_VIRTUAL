# -*- coding: utf-8 -*-
"""R34 Parrilla (Casa-Angel-DOC-Parrilla.rvt, pilot linked). Parrilla de obra a medida (decisión del usuario 2026-10-26):
boca 1,50 m, campana hasta cielorraso, ladrillo refractario visto, conducto por cubierta con sombrerete fijo.
- probe (read-only, pilot or DOC): PR-01 / CH-01 / CH-02, Quincho, cielorraso, cubierta y muros vecinos -> par34-probe.json
- info / plans / details / index / export: documentation only in the DOC file (plan views of the linked model with the
  design drawn as detail lines, drafting views for the parrilla and the conducto). The pilot is never modified.
Each view records its hover parts (code, label, box normalised to the drawing) for the web."""
import os, imp, math
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
C = imp.load_source('ader_cubdoc_r30_for_par', os.path.join(ROOT, 'revit_cub_doc_r30.py'))
B = C.B; L = C.L; S = C.S; X = C.X; R1 = C.R1; CTX = C.CTX
M = L.M; OUT = L.OUT; eid = L.eid; u = C.u; name = C.name
IDS = {'PR-01': 743956, 'CH-01': 738025, 'CH-02': 745388}
PRE = 'ADER PAR R34 - '
RUBRO = u'PARRILLA'
FOOT = (u'Parrilla R34 (archivo de documentación con el modelo principal vinculado). Parrilla de obra a medida en el Quincho: boca 1,50 m, hogar a +0,90, '
        u'campana de ladrillo refractario visto hasta el cielorraso (+2,50), conducto Ø 35 cm por cubierta con sombrerete fijo. Modelada en 3D solo en este archivo: el modelo '
        u'principal sigue con el equipo K42DB y 2 conductos Ø 25 (no se modificó). Cotas en metros.')

# ---------------------------------------------------------------- design (metres). Local x from the west outer face, y from the wall face, z from NPT
WALL_Y = 2.018          # inner face of the south H° wall (Muro Hormigón 20 cm, axis 1,918)
EAST_X = 4.243          # west face of the 10 cm partition (Muro Interior 10 cm, axis 4,293)
JA, BOCA, LANA = .12, 1.50, .025
WIDTH = JA + BOCA + JA + LANA          # 1,765 incl. ceramic-wool board against the partition
X0 = EAST_X - WIDTH                     # model x of the west outer face
FONDO, HOGAR, FRENTE = .064, .60, .12
DEPTH = FONDO + HOGAR + FRENTE          # 0,784
Z_LOSA0, Z_LOSA1, Z_HOGAR, Z_BOCA, Z_CIELO, Z_LO0, Z_LO1 = .74, .84, .90, 1.50, 2.50, 2.80, 3.00
CH_X, CH_Y = 3.92, 2.30                 # conducto axis (model)
CH_D, CH_DE = .35, .40                  # inner Ø / outer Ø double wall
CAJON = (4.063, 1.882, 4.738, 3.232)    # Durlock box in the Comedor (walls 986634/986707/986754), top +4,00
CAJON_NEW_X = CH_X - CH_DE / 2 - .06    # proposed west face
ROOF_RIDGE_X, ROOF_RIDGE_Z, ROOF_TAN = 2.085, 8.627, math.tan(math.radians(16.8))   # CU-03 (from the probe)
def roof_z(x): return ROOF_RIDGE_Z - abs(x - ROOF_RIDGE_X) * ROOF_TAN
Z_ROOF = roof_z(CH_X)
Z_TOP = 9.40                            # conducto top (= model CH top; ≥ cumbrera + 0,60)
G0 = 1.90                               # garganta start: lateral slope (1,50 → Ø 35) ≤ 45° (R1001.8.1)
Z_SOMB = Z_TOP + .20 + .15
LX = lambda x: X0 + x; LY = lambda y: WALL_Y + y
def c2(v): return (u'%.2f' % v).replace(u'.', u',')
def c3(v): return (u'%.3f' % v).replace(u'.', u',')

PARTS = {   # code: label (hover / tags)
    'PR-01': u'PR-01 · parrilla de obra · %s × %s · boca %s' % (c2(WIDTH), c2(DEPTH), c2(BOCA)),
    'PR-JA': u'PR-JA · jambas ladrillo refractario visto 12 cm · %s × %s m (2)' % (c2(DEPTH), c2(Z_CIELO)),
    'PR-FO': u'PR-FO · fondo refractario de plano 6,4 cm · %s × %s m' % (c2(BOCA), c2(Z_CIELO - Z_LOSA1)),
    'PR-SO': u'PR-SO · solera refractaria de plano · %s × %s m · hogar +%s' % (c2(BOCA), c2(HOGAR), c2(Z_HOGAR)),
    'PR-LO': u'PR-LO · losa base H°A° 10 cm · %s × %s m' % (c2(BOCA), c2(DEPTH)),
    'PR-CA': u'PR-CA · frente de campana ladrillo refractario visto · %s × %s m' % (c2(BOCA), c2(Z_CIELO - Z_BOCA)),
    'PR-DI': u'PR-DI · dintel 2 L 2½" × ¼" · %s ml c/u' % c2(WIDTH - LANA),
    'PR-GA': u'PR-GA · garganta chapa 2 mm + registro de tiro en el collar Ø %s' % c2(CH_D),
    'PR-PA': u'PR-PA · parrilla regulable acero inox 1,00 × 0,55 con elevación a manivela',
    'PR-BR': u'PR-BR · brasero (canasto) hierro 0,35 × 0,50',
    'PR-LE': u'PR-LE · leñero abierto bajo la losa · %s × %s × %s' % (c2(BOCA), c2(DEPTH), c2(Z_LOSA0)),
    'PR-AI': u'PR-AI · placa lana cerámica 25 mm contra el tabique · %s × %s m' % (c2(DEPTH), c2(Z_CIELO)),
    'CH-01': u'CH-01 · conducto Ø %s acero inox · +%s a +%s · %s ml' % (c2(CH_D), c2(Z_CIELO), c2(Z_TOP), c2(Z_TOP - Z_CIELO)),
    'CH-PA': u'CH-PA · pase en losa L01 0,50 × 0,50 (amplía el pase existente)',
    'CH-CJ': u'CH-CJ · cajón Durlock del Comedor: ampliar al oeste hasta x %s y llevar hasta la cubierta (a confirmar)' % c2(CAJON_NEW_X),
    'CH-BA': u'CH-BA · babeta / collar de cubierta + brochal entre cabios',
    'CH-SO': u'CH-SO · sombrerete fijo acero inox Ø 0,70 + malla antichispa',
}

# ---------------------------------------------------------------- probe (read only)
def mx(p): return [round(p.X * M, 3), round(p.Y * M, 3), round(p.Z * M, 3)]
def bbm(e, v=None):
    b = e.get_BoundingBox(v)
    return [mx(b.Min), mx(b.Max)] if b else None

def model_doc(doc):
    for li in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        ld = li.GetLinkDocument()
        if ld is not None: return ld
    return doc

def probe(doc):
    d = model_doc(doc); res = {'levels': sorted([(round(l.Elevation * M, 3), u(name(l))) for l in DB.FilteredElementCollector(d).OfClass(DB.Level)])}
    pr = d.GetElement(DB.ElementId(Int64(IDS['PR-01']))); lp = pr.Location
    res['PR-01'] = {'family': u(pr.Symbol.FamilyName), 'type': u(name(pr.Symbol)), 'point': mx(lp.Point), 'bbox': bbm(pr), 'host': (u(name(pr.Host)) + ' #' + str(pr.Host.Id.IntegerValue)) if pr.Host else None}
    for k in ('CH-01', 'CH-02'):
        e = d.GetElement(DB.ElementId(Int64(IDS[k]))); c = e.Location.Curve
        res[k] = {'a': mx(c.GetEndPoint(0)), 'b': mx(c.GetEndPoint(1)), 'len_m': round(c.Length * M, 3), 'type': u(name(d.GetElement(e.GetTypeId()))),
                  'diam': e.get_Parameter(DB.BuiltInParameter.RBS_CURVE_DIAMETER_PARAM).AsValueString() if e.get_Parameter(DB.BuiltInParameter.RBS_CURVE_DIAMETER_PARAM) else None}
    p = lp.Point; rooms = []
    for r in DB.FilteredElementCollector(d).OfCategory(DB.BuiltInCategory.OST_Rooms):
        if r.Area <= 0: continue
        if not r.IsPointInRoom(DB.XYZ(p.X, p.Y, r.Level.Elevation + 1.0 / M)): continue
        rooms.append({'id': r.Id.IntegerValue, 'name': u(r.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()), 'number': r.Number, 'level': u(name(r.Level)), 'area_m2': round(r.Area * M * M, 2)})
    res['rooms'] = rooms
    def around(cat, pad):
        out = []
        for e in DB.FilteredElementCollector(d).OfCategory(cat).WhereElementIsNotElementType():
            b = e.get_BoundingBox(None)
            if b is not None and b.Min.X - pad < p.X < b.Max.X + pad and b.Min.Y - pad < p.Y < b.Max.Y + pad: out.append(e)
        return out
    res['ceilings'] = [{'id': e.Id.IntegerValue, 'type': u(name(d.GetElement(e.GetTypeId()))), 'bbox': bbm(e)} for e in around(DB.BuiltInCategory.OST_Ceilings, 0)]
    res['roofs'] = [{'id': e.Id.IntegerValue, 'type': u(name(d.GetElement(e.GetTypeId()))), 'bbox': bbm(e)} for e in around(DB.BuiltInCategory.OST_Roofs, 0)]
    res['framing'] = [{'id': e.Id.IntegerValue, 'type': u(name(d.GetElement(e.GetTypeId()))), 'bbox': bbm(e)} for e in around(DB.BuiltInCategory.OST_StructuralFraming, 3.0 / M)]
    R1.write(os.path.join(OUT, 'par34-probe.json'), res)
    return res

# ---------------------------------------------------------------- fills with fallback (template patterns differ between DOC files)
_FRT = {}
FILLS = {'ladrillo': [u'Albañilería - Ladrillo', u'Diagonal abajo 1.5 mm'], 'refractario': [u'Diagonal cruzada 1.5 mm', u'Diagonal cruzada', u'Albañilería - Ladrillo'],
         'hormigon': [u'Hormigón'], 'acero': [u'Acero', u'<Solid fill>'], 'aislacion': [u'Aislamiento - Rígido', u'Diagonal arriba 1.5 mm'],
         'solido': [u'<Solid fill>'], 'tabique': [u'Diagonal abajo 1.5 mm', u'Diagonal abajo'], 'machimbre': [u'Madera - Acabado', u'Madera 1'], 'eps': [u'Aislamiento - Rígido'],
         'teja': [u'Teja plana', u'<Solid fill>'], 'madera': [u'Madera 1', u'Madera - Acabado']}

def frt(doc, key):
    if key in _FRT: return _FRT[key]
    nm_ = u'ADER PAR R34 - ' + key
    t = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType) if u(name(x)) == nm_), None)
    if t is None:
        base = next(x for x in DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType))
        t = base.Duplicate(nm_)
        pats = dict((u(name(p)), p) for p in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement) if p.GetFillPattern().Target == DB.FillPatternTarget.Drafting)
        pat = next((pats[n] for n in FILLS[key] if n in pats), None) or next((p for n, p in pats.items() if 'solid' in n.lower()), None)
        if pat is not None: t.ForegroundPatternId = pat.Id
        t.ForegroundPatternColor = DB.Color(60, 60, 60) if key == 'solido' else DB.Color(0, 0, 0)
        try: t.BackgroundPatternId = DB.ElementId.InvalidElementId
        except Exception: pass
    _FRT[key] = t; return t

C.frt = frt     # C.region / C.rect / C.band / C.slope_pkg use it

ZCUR = [0.0]     # elevation of the detail plane (plan views of upper levels)
def V(a): return DB.XYZ(a[0] / M, a[1] / M, ZCUR[0])
C.V = V
def rect(doc, v, x0, y0, x1, y1, key=None, w=3): C.rect(doc, v, x0, y0, x1, y1, key, w)
def dl(doc, v, a, b, w=3, pat=None): return C.dl(doc, v, a, b, w, pat)
def txt(doc, v, x, y, s, key='text'): L.tn(doc, v.Id, V((x, y)), s, key)
def circ(doc, v, c, r, w=3, pat=None):
    arc = DB.Arc.Create(DB.XYZ(c[0] / M, c[1] / M, ZCUR[0]), r / M, 0, 2 * math.pi - 1e-3, DB.XYZ.BasisX, DB.XYZ.BasisY)
    dc = doc.Create.NewDetailCurve(v, arc); ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineWeight(w)
    if pat:
        lp = next((p for p in DB.FilteredElementCollector(doc).OfClass(DB.LinePatternElement) if u(name(p)) == pat), None)
        if lp is not None: ov.SetProjectionLinePatternId(lp.Id)
    v.SetElementOverrides(dc.Id, ov); return dc
def chain_h(doc, v, label, xs, at): return C.dimh(doc, v, label, (0, 0), (1, 0), (0, 1), xs, at)
def chain_v(doc, v, label, ys, at): return C.dimv(doc, v, label, (0, 0), (1, 0), (0, 1), ys, at)
def labels(doc, v, pts, x, ytop, dy): C.labels_column(doc, v, sorted(pts, key=lambda t: -t[0][1]), x, ytop, dy)

def extents(doc, v):
    doc.Regenerate(); pts = []
    for e in DB.FilteredElementCollector(doc, v.Id).WhereElementIsNotElementType():
        b = e.get_BoundingBox(v)
        if b is not None and e.Category is not None: pts += [b.Min, b.Max]
    return (min(p.X for p in pts), min(p.Y for p in pts), max(p.X for p in pts), max(p.Y for p in pts))

def hover(parts, ext):
    """parts: [(code, (x0, y0, x1, y1) metres in view coords)] -> web elements, box normalised (x right, y down)."""
    x0, y0, x1, y1 = ext; w = x1 - x0; h = y1 - y0; out = []
    for code, r in parts:
        a, b, c, d = r[0] / M, r[1] / M, r[2] / M, r[3] / M
        box = [max(0, (min(a, c) - x0) / w), max(0, (y1 - max(b, d)) / h), min(1, (max(a, c) - x0) / w), min(1, (y1 - min(b, d)) / h)]
        out.append({'code': code, 'elementId': None, 'label': PARTS[code], 'box': [round(q, 4) for q in box]})
    return out

def ditem(doc, v, title, tags, dims, parts):
    it = C.item(doc, v, title, tags, dims); it['elements'] = hover(parts, extents(doc, v)); return it

# ---------------------------------------------------------------- plan views of the linked model
def plan_view(doc, lvname, vname, box, scale, cut=1.2, bottom=-.6, hide_extra=()):
    lev = next(l for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if name(l) == lvname)
    v = DB.ViewPlan.Create(doc, DB.ElementId(Int64(L.PLAN_VFT)), lev.Id); L.setup_view(doc, v); v.Name = vname; v.Scale = scale
    bx = DB.BoundingBoxXYZ(); bx.Min = DB.XYZ(box[0] / M, box[1] / M, lev.Elevation - 10 / M); bx.Max = DB.XYZ(box[2] / M, box[3] / M, lev.Elevation + 10 / M)
    v.CropBox = bx; v.CropBoxActive = True; v.CropBoxVisible = False
    try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
    except Exception: pass
    vr = v.GetViewRange()
    for plane, off in [(DB.PlanViewPlane.TopClipPlane, cut + .8), (DB.PlanViewPlane.CutPlane, cut), (DB.PlanViewPlane.BottomClipPlane, bottom), (DB.PlanViewPlane.ViewDepthPlane, bottom)]:
        vr.SetLevelId(plane, lev.Id); vr.SetOffset(plane, off / M)
    v.SetViewRange(vr); ZCUR[0] = lev.Elevation * M
    for cat in (DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_GenericModel, DB.BuiltInCategory.OST_Rooms,
                DB.BuiltInCategory.OST_SpecialityEquipment, DB.BuiltInCategory.OST_DuctCurves, DB.BuiltInCategory.OST_DuctFitting, DB.BuiltInCategory.OST_Casework) + tuple(hide_extra):
        try: v.SetCategoryHidden(DB.ElementId(cat), True)
        except Exception: pass
    for li in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        ov = DB.OverrideGraphicSettings(); ov.SetHalftone(True); v.SetElementOverrides(li.Id, ov)
    return v, lev

def pitem(v, box, title, level, tags, dims, parts, notes):
    it = X.item(v, v.CropBox, title, 'plan', level, tags, dims, [])
    it['elements'] = hover(parts, (box[0] / M, box[1] / M, box[2] / M, box[3] / M)); it['data'] = None
    return it

def plan_pb(doc):
    box = (.4, 1.45, 5.4, 4.35)
    v, lev = plan_view(doc, u'00. Planta Baja', PRE + 'UBICACION PB', box, 25)
    def mr(x0, y0, x1, y1, key=None, w=3):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if key: C.region(doc, v, pts, key)
        C.poly(doc, v, pts, w)
    xa, xb = LX(0), LX(WIDTH - LANA)
    mr(xa, LY(0), LX(JA), LY(DEPTH), 'ladrillo', 4); mr(LX(JA + BOCA), LY(0), xb, LY(DEPTH), 'ladrillo', 4)       # jambas cortadas a +1,20
    mr(xb, LY(0), EAST_X, LY(DEPTH), 'aislacion', 2)
    mr(LX(JA), LY(0), LX(JA + BOCA), LY(FONDO), 'refractario', 3)
    dl(doc, v, (LX(JA), LY(DEPTH - FRENTE)), (LX(JA + BOCA), LY(DEPTH - FRENTE)), 2, u'Oculto'); dl(doc, v, (LX(JA), LY(DEPTH)), (LX(JA + BOCA), LY(DEPTH)), 2, u'Oculto')
    circ(doc, v, (CH_X, CH_Y), CH_D / 2, 3, u'Oculto')
    C.poly(doc, v, [(.45, LY(.6)), (xa, LY(.6))], 1, closed=False); txt(doc, v, .6, LY(.45), u'Mesada existente', 'text')
    dims = [chain_h(doc, v, u'Parrilla: boca', [LX(JA), LX(JA + BOCA)], LY(DEPTH) + .25), chain_h(doc, v, u'Parrilla: ancho total', [xa, EAST_X], LY(DEPTH) + .50),
            chain_v(doc, v, u'Parrilla: fondo total', [LY(0), LY(DEPTH)], xa - .18)]
    txt(doc, v, xa, 3.95, u'PR-01 · parrilla de obra\n%s × %s · boca %s · hogar +%s' % (c2(WIDTH), c2(DEPTH), c2(BOCA), c2(Z_HOGAR)), 'tag')
    txt(doc, v, EAST_X + .15, CH_Y + .45, u'CH-01 Ø 35\n(encima, ver PA)', 'text')
    txt(doc, v, .5, 4.30, u'QUINCHO (12) · PB · NPT ±0,00', 'room')
    txt(doc, v, .5, 1.76, u'Muro H° 20 (exterior)', 'text'); txt(doc, v, EAST_X + .15, 3.55, u'Tabique 10', 'text')
    txt(doc, v, .5, 3.95, u'Corte a +1,20 · oculto: campana\ny conducto encima · el K42DB y\nlos conductos Ø 25 del modelo\nquedan reemplazados', 'text')
    parts = [('PR-01', (xa, LY(0), EAST_X, LY(DEPTH))), ('CH-01', (CH_X - .15, CH_Y - .15, CH_X + .15, CH_Y + .15))]
    return pitem(v, box, u'Ubicación · Quincho · planta baja', u'00. Planta Baja', ['PR-01', 'CH-01'], dims, parts, [])

def plan_pa(doc):
    box = (2.9, .9, 5.3, 4.1)
    v, lev = plan_view(doc, u'01. Planta Alta', PRE + 'CONDUCTO PA', box, 25)
    for r_, w in ((CH_DE / 2, 4), (CH_D / 2, 2)): circ(doc, v, (CH_X, CH_Y), r_, w)
    x0, y0, x1, y1 = CAJON
    C.poly(doc, v, [(CAJON_NEW_X, y0), (x0, y0)], 3); C.poly(doc, v, [(CAJON_NEW_X, y1), (x0, y1)], 3); dl(doc, v, (CAJON_NEW_X, y0), (CAJON_NEW_X, y1), 3)
    dims = [chain_h(doc, v, u'Cajón: ampliación propuesta', [CAJON_NEW_X, x0], y1 + .35), chain_h(doc, v, u'Conducto: eje al cajón existente', [CH_X, x0], y0 - .35)]
    txt(doc, v, 3.0, 3.95, u'COMEDOR (PA) · +3,00', 'room')
    txt(doc, v, 3.0, 3.05, u'CH-01 doble pared\nØ 35 / 40 ext.', 'text')
    txt(doc, v, 3.0, 1.45, u'Cajón Durlock existente: x 4,06–4,74, a +4,00\nEl conducto cae 0,34 m al oeste: ampliar\nel cajón (trazo negro) hasta el machimbre', 'text')
    parts = [('CH-01', (CH_X - .175, CH_Y - .175, CH_X + .175, CH_Y + .175)), ('CH-CJ', (CAJON_NEW_X, y0, x1, y1))]
    return pitem(v, box, u'Conducto por la planta alta · Comedor', u'01. Planta Alta', ['CH-01', 'CH-CJ'], dims, parts, [])

def plan_roof(doc):
    box = (2.9, .9, 5.3, 4.1)
    v, lev = plan_view(doc, u'03. Planta de Techos', PRE + 'CONDUCTO TECHO', box, 25, cut=1.5, bottom=-2.0)
    d = L.read('par34-probe'); fr = d['framing']; xs, ys = [], []
    for f in fr:
        (a, b) = f['bbox']; t = f['type']
        if u'Cabio' in t and a[0] < CH_X < b[0] and box[1] < (a[1] + b[1]) / 2 < box[3]:
            yc = (a[1] + b[1]) / 2; ys.append(yc); dl(doc, v, (box[0] + .05, yc), (box[2] - .05, yc), 2, u'Oculto')
        if u'List' in t and box[0] < (a[0] + b[0]) / 2 < box[2] and a[1] < CH_Y < b[1]:
            xc = (a[0] + b[0]) / 2; xs.append(xc); dl(doc, v, (xc, box[1] + .05), (xc, box[3] - .05), 1, u'Oculto')
    for r_, w in ((CH_DE / 2, 4), (CH_D / 2, 2)): circ(doc, v, (CH_X, CH_Y), r_, w)
    h = .25; C.poly(doc, v, [(CH_X - h, CH_Y - h), (CH_X + h, CH_Y - h), (CH_X + h, CH_Y + h), (CH_X - h, CH_Y + h)], 3)
    ys = sorted(ys); below = max([y for y in ys if y < CH_Y] or [CH_Y - .5]); above = min([y for y in ys if y > CH_Y] or [CH_Y + .5])
    dims = [chain_v(doc, v, u'Cabios a ambos lados del conducto', [below, above], CH_X + .85), chain_v(doc, v, u'Pase entre cabios', [CH_Y - h, CH_Y + h], CH_X + .45)]
    txt(doc, v, 3.0, 3.95, u'CUBIERTA CU-03 · 16,8°', 'room')
    txt(doc, v, 3.0, 1.75, u'Pase 0,50 × 0,50 entre cabios c/0,96 (oculto)\ncon brochal: corta 1 listón, ningún cabio\nTecho en el conducto +%s · ver PAR-D-03' % c2(Z_ROOF), 'text')
    parts = [('CH-BA', (CH_X - h, CH_Y - h, CH_X + h, CH_Y + h)), ('CH-SO', (CH_X - .3, CH_Y - .3, CH_X + .3, CH_Y + .3))]
    return pitem(v, box, u'Cruce de cubierta · planta de techos', u'03. Planta de Techos', ['CH-BA', 'CH-SO'], dims, parts, [])

# ---------------------------------------------------------------- PAR-D-01 (1:20)
def d_planta(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-01 PLANTA', 20); W = WIDTH
    rect(doc, v, -.30, -.20, W + .10, 0, 'hormigon', 5)                                   # muro H° 20
    rect(doc, v, W, 0, W + .10, DEPTH + .40, 'tabique', 3)                                # tabique 10 (existente)
    rect(doc, v, 0, 0, JA, DEPTH, 'ladrillo', 5); rect(doc, v, JA + BOCA, 0, 2 * JA + BOCA, DEPTH, 'ladrillo', 5)
    rect(doc, v, 2 * JA + BOCA, 0, W, DEPTH, 'aislacion', 2)
    rect(doc, v, JA, 0, JA + BOCA, FONDO, 'refractario', 3)
    rect(doc, v, JA + .04, FONDO + .06, JA + .39, FONDO + .56, None, 3)                   # brasero
    for i in range(1, 7): dl(doc, v, (JA + .04 + i * .05, FONDO + .06), (JA + .04 + i * .05, FONDO + .56), 1)
    px0, px1 = JA + .46, JA + 1.46
    rect(doc, v, px0, FONDO + .025, px1, FONDO + .575, None, 4)                            # parrilla regulable
    k = px0 + .05
    while k < px1 - .02: dl(doc, v, (k, FONDO + .025), (k, FONDO + .575), 1); k += .05
    for yy in (DEPTH - FRENTE, DEPTH): dl(doc, v, (JA, yy), (JA + BOCA, yy), 2, u'Oculto')  # frente de campana encima
    cx, cy = CH_X - X0, CH_Y - WALL_Y; circ(doc, v, (cx, cy), CH_D / 2, 2, u'Oculto')
    circ(doc, v, (2 * JA + BOCA - .06, FONDO + .30), .03, 3)                               # eje de manivela
    dims = [chain_h(doc, v, u'Ancho: jamba · boca · jamba', [0, JA, JA + BOCA, 2 * JA + BOCA], DEPTH + .18),
            chain_h(doc, v, u'Ancho total', [0, W], DEPTH + .32),
            chain_v(doc, v, u'Fondo: hogar · frente', [FONDO, FONDO + HOGAR, DEPTH], -.18), chain_v(doc, v, u'Fondo total', [0, DEPTH], -.34),
            chain_h(doc, v, u'Brasero', [JA + .04, JA + .39], -.32), chain_h(doc, v, u'Parrilla regulable', [px0, px1], -.32)]
    pts = [((JA / 2, .40), u'PR-JA · jamba ladrillo refractario visto 12 cm'), ((JA + .8, FONDO / 2), u'PR-FO · fondo refractario de plano 6,4 cm'),
           ((JA + .2, FONDO + .3), u'PR-BR · brasero (canasto) 0,35 × 0,50'), ((px0 + .5, FONDO + .3), u'PR-PA · parrilla regulable inox 1,00 × 0,55'),
           ((W - .012, .5), u'PR-AI · lana cerámica 25 mm contra el tabique'), ((cx, cy + .15), u'CH-01 · collar Ø 35 encima (garganta)'),
           ((2 * JA + BOCA - .06, FONDO + .30), u'Eje de la manivela (elevación de la parrilla)'), ((W + .05, DEPTH + .2), u'Tabique 10 existente')]
    labels(doc, v, pts, W + .35, DEPTH + .75, .12)
    txt(doc, v, -.30, -.50, u'Planta cortada a +1,20 · trazo oculto: frente de campana y collar · cotas en m', 'text')
    parts = [('PR-JA', (0, 0, JA, DEPTH)), ('PR-JA', (JA + BOCA, 0, 2 * JA + BOCA, DEPTH)), ('PR-FO', (JA, 0, JA + BOCA, FONDO)), ('PR-BR', (JA + .04, FONDO + .06, JA + .39, FONDO + .56)),
             ('PR-PA', (px0, FONDO + .025, px1, FONDO + .575)), ('PR-AI', (2 * JA + BOCA, 0, W, DEPTH))]
    return ditem(doc, v, u'D-01a · Planta de la parrilla', ['PR-01'], dims, parts)

def d_frente(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-01 VISTA FRONTAL', 20); W = 2 * JA + BOCA
    rect(doc, v, 0, 0, JA, Z_CIELO, 'ladrillo', 4); rect(doc, v, JA + BOCA, 0, W, Z_CIELO, 'ladrillo', 4)
    rect(doc, v, JA, Z_BOCA, JA + BOCA, Z_CIELO, 'ladrillo', 4)                            # frente de campana
    rect(doc, v, JA, Z_LOSA0, JA + BOCA, Z_LOSA1, 'hormigon', 3); rect(doc, v, JA, Z_LOSA1, JA + BOCA, Z_HOGAR, 'refractario', 2)
    rect(doc, v, JA, Z_BOCA - .064, JA + BOCA, Z_BOCA, 'acero', 2)                         # dintel L 2½"
    rect(doc, v, JA, 0, JA + BOCA, Z_LOSA0, None, 2)                                       # leñero
    for i in range(4): rect(doc, v, JA + .15 + i * .33, .02, JA + .43 + i * .33, .16, None, 1)   # leña
    dl(doc, v, (JA + .46, Z_HOGAR + .22), (JA + 1.46, Z_HOGAR + .22), 4)                   # parrilla
    rect(doc, v, JA + .04, Z_HOGAR + .02, JA + .39, Z_HOGAR + .30, None, 2)                # brasero
    circ(doc, v, (W - .06, 1.30), .04, 3); dl(doc, v, (W - .06, 1.30), (W + .10, 1.30), 3)   # manivela
    dl(doc, v, (-.30, Z_CIELO), (W + .30, Z_CIELO), 2); txt(doc, v, -.95, Z_CIELO + .10, u'Cielorraso +2,50', 'text')
    rect(doc, v, -.30, Z_LO0, W + .30, Z_LO1, 'hormigon', 2); txt(doc, v, -1.25, Z_LO1 + .10, u'Losa L01 +2,80 / +3,00', 'text')
    cx = CH_X - X0
    for xx in (cx - CH_D / 2, cx + CH_D / 2): dl(doc, v, (xx, Z_CIELO), (xx, Z_LO1 + .25), 2, u'Oculto')
    dl(doc, v, (-.30, 0), (W + .30, 0), 4); txt(doc, v, -.75, .10, u'NPT ±0,00', 'text')
    dims = [chain_v(doc, v, u'Alturas: leñero · losa + solera · boca · campana', [0, Z_LOSA0, Z_HOGAR, Z_BOCA, Z_CIELO], W + .30),
            chain_v(doc, v, u'Altura total hasta cielorraso', [0, Z_CIELO], W + .48),
            chain_h(doc, v, u'Frente: jamba · boca · jamba', [0, JA, JA + BOCA, W], -.20)]
    pts = [((JA + .75, 2.0), u'PR-CA · frente de campana ladrillo refractario visto (junta tomada)'), ((JA + .7, Z_BOCA - .03), u'PR-DI · dintel 2 L 2½" × ¼" (frente y trasdós)'),
           ((JA + 1.0, Z_HOGAR + .22), u'PR-PA · parrilla regulable · regulación +1,00 a +1,30'), ((JA + .2, Z_HOGAR + .15), u'PR-BR · brasero'),
           ((JA + .9, Z_HOGAR - .03), u'PR-SO · solera refractaria (hogar +0,90)'), ((JA + .9, (Z_LOSA0 + Z_LOSA1) / 2), u'PR-LO · losa H°A° 10 cm sobre jambas'),
           ((JA + .9, .40), u'PR-LE · leñero abierto'), ((W - .06, 1.30), u'Manivela de elevación (lateral derecho)'), ((cx, Z_LO1), u'CH-01 · conducto Ø 35 (sigue a cubierta)')]
    labels(doc, v, pts, W + .75, Z_CIELO + .35, .17)
    txt(doc, v, -.30, -.30, u'Vista frontal desde el Quincho · cotas en m', 'text')
    parts = [('PR-JA', (0, 0, JA, Z_CIELO)), ('PR-JA', (JA + BOCA, 0, W, Z_CIELO)), ('PR-CA', (JA, Z_BOCA, JA + BOCA, Z_CIELO)), ('PR-DI', (JA, Z_BOCA - .064, JA + BOCA, Z_BOCA)),
             ('PR-SO', (JA, Z_LOSA1, JA + BOCA, Z_HOGAR)), ('PR-LO', (JA, Z_LOSA0, JA + BOCA, Z_LOSA1)), ('PR-LE', (JA, 0, JA + BOCA, Z_LOSA0)),
             ('PR-PA', (JA + .46, Z_HOGAR + .17, JA + 1.46, Z_HOGAR + .27)), ('PR-BR', (JA + .04, Z_HOGAR + .02, JA + .39, Z_HOGAR + .30))]
    return ditem(doc, v, u'D-01b · Vista frontal', ['PR-01'], dims, parts)

def d_corte(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-01 CORTE', 20); D = DEPTH
    rect(doc, v, -.20, 0, 0, Z_LO1, 'hormigon', 5)                                         # muro H°
    rect(doc, v, -.20, Z_LO0, D + .45, Z_LO1, 'hormigon', 4)                               # losa L01
    dl(doc, v, (D, Z_CIELO), (D + .45, Z_CIELO), 3); txt(doc, v, D + .50, Z_CIELO + .05, u'Cielorraso +2,50', 'text')
    rect(doc, v, 0, Z_LOSA1, FONDO, Z_CIELO, 'refractario', 3)                             # fondo
    rect(doc, v, 0, Z_LOSA0, D, Z_LOSA1, 'hormigon', 3)                                    # losa base
    rect(doc, v, FONDO, Z_LOSA1, FONDO + HOGAR, Z_HOGAR, 'refractario', 2)                 # solera
    rect(doc, v, D - FRENTE, Z_BOCA, D, Z_CIELO, 'ladrillo', 4)                            # frente de campana
    rect(doc, v, D - FRENTE, Z_BOCA - .064, D, Z_BOCA, 'acero', 2)                         # dintel
    cy = CH_Y - WALL_Y; g0 = G0
    C.poly(doc, v, [(FONDO, g0), (cy - CH_D / 2, Z_CIELO - .02), (cy - CH_D / 2, Z_LO1 + .30)], 3, closed=False)       # garganta
    C.poly(doc, v, [(D - FRENTE, g0), (cy + CH_D / 2, Z_CIELO - .02), (cy + CH_D / 2, Z_LO1 + .30)], 3, closed=False)
    dl(doc, v, (cy - CH_D / 2 + .02, Z_CIELO + .10), (cy + CH_D / 2 - .02, Z_CIELO + .16), 3)                         # registro (mariposa)
    dl(doc, v, (FONDO + .025, Z_HOGAR + .22), (FONDO + .575, Z_HOGAR + .22), 4)           # parrilla
    rect(doc, v, FONDO + .02, Z_HOGAR + .02, FONDO + .58, Z_HOGAR + .05, None, 1)          # bandeja de grasa
    dl(doc, v, (-.40, 0), (D + .45, 0), 4); txt(doc, v, -.85, .10, u'NPT ±0,00', 'text')
    dims = [chain_v(doc, v, u'Corte: leñero · losa + solera · boca · campana', [0, Z_LOSA0, Z_HOGAR, Z_BOCA, Z_CIELO], D + .25),
            chain_h(doc, v, u'Fondo: hogar · frente', [FONDO, FONDO + HOGAR, D], -.20), chain_h(doc, v, u'Fondo total', [0, D], -.36),
            chain_h(doc, v, u'Collar del conducto', [cy - CH_D / 2, cy + CH_D / 2], Z_LO1 + .40)]
    pts = [((-.10, 1.2), u'Muro H° 20 existente'), ((FONDO / 2, 1.8), u'PR-FO · refractario de plano + mortero refractario'),
           ((.2, 2.3), u'PR-GA · garganta chapa 2 mm (de +1,90 al collar, ≤ 45°)'), ((cy, Z_CIELO + .13), u'Registro de tiro (mariposa) con comando exterior'),
           ((D - .06, 2.0), u'PR-CA · frente de campana 12 cm'), ((D - .06, Z_BOCA - .03), u'PR-DI · dintel 2 L 2½" × ¼"'),
           ((.35, Z_HOGAR + .22), u'PR-PA · parrilla regulable (+1,00 a +1,30)'), ((.35, Z_HOGAR + .035), u'Bandeja recolectora de grasa'),
           ((.4, (Z_LOSA0 + Z_LOSA1) / 2), u'PR-LO · losa H°A° 10 cm'), ((.4, .4), u'PR-LE · leñero'), ((cy, Z_LO1 + .2), u'CH-01 · conducto Ø 35 → cubierta (PAR-D-02)')]
    labels(doc, v, pts, D + .75, Z_LO1 + .45, .17)
    txt(doc, v, -.40, -.50, u'Corte A-A por el eje del conducto · cotas en m', 'text')
    parts = [('PR-FO', (0, Z_LOSA1, FONDO, Z_CIELO)), ('PR-LO', (0, Z_LOSA0, D, Z_LOSA1)), ('PR-SO', (FONDO, Z_LOSA1, FONDO + HOGAR, Z_HOGAR)),
             ('PR-CA', (D - FRENTE, Z_BOCA, D, Z_CIELO)), ('PR-GA', (FONDO, g0, D - FRENTE, Z_CIELO)), ('CH-01', (cy - CH_D / 2, Z_CIELO, cy + CH_D / 2, Z_LO1 + .30)),
             ('PR-LE', (0, 0, D, Z_LOSA0))]
    return ditem(doc, v, u'D-01c · Corte A-A', ['PR-01'], dims, parts)

# ---------------------------------------------------------------- PAR-D-02
def d_conducto(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-02 CORTE CONDUCTO', 50)
    ox = CH_X; fx = lambda x: x - ox                     # horizontal = model x relative to the conducto axis
    xl, xr = fx(1.70), fx(5.20)
    for zz, lab in ((0, u'PB ±0,00'), (Z_CIELO, u'Cielorraso PB +2,50'), (Z_LO1, u'PA +3,00'), (4.00, u'Tope cajón existente +4,00'), (Z_TOP, u'Tope conducto +%s' % c2(Z_TOP))):
        dl(doc, v, (xl, zz), (xr, zz), 1, u'Oculto' if zz not in (0, Z_LO1) else None); txt(doc, v, xl - 2.7, zz + .18, lab, 'text')
    rect(doc, v, xl, Z_LO0, xr, Z_LO1, 'hormigon', 3)
    pr0, pr1 = fx(X0), fx(EAST_X - LANA)
    C.poly(doc, v, [(pr0, 0), (pr0, Z_CIELO), (pr1, Z_CIELO), (pr1, 0)], 4, closed=False); txt(doc, v, pr0 + .05, 1.4, u'PR-01', 'tag')
    rect(doc, v, -CH_D / 2, Z_CIELO, CH_D / 2, Z_LO1, None, 3)                                   # simple pared (plenum PB)
    rect(doc, v, -CH_DE / 2, Z_LO1, CH_DE / 2, Z_TOP, None, 4)                                   # doble pared
    dl(doc, v, (-CH_D / 2, Z_LO1), (-CH_D / 2, Z_TOP), 1); dl(doc, v, (CH_D / 2, Z_LO1), (CH_D / 2, Z_TOP), 1)
    cj0 = fx(CAJON_NEW_X); cj1 = fx(CAJON[2])
    for xx in (cj0, cj1): dl(doc, v, (xx, Z_LO1), (xx, roof_z(xx + ox) - .34), 2, u'Oculto')
    dl(doc, v, (fx(CAJON[0]), Z_LO1), (fx(CAJON[0]), 4.0), 3)
    rx = [fx(x) for x in (1.70, ROOF_RIDGE_X, 5.20)]
    for off, w in ((0, 4), (-.33, 2)):
        C.poly(doc, v, [(rx[0], roof_z(1.70) + off), (rx[1], ROOF_RIDGE_Z + off), (rx[2], roof_z(5.20) + off)], w, closed=False)
    zs = Z_TOP + .25
    for s in (-1, 1): dl(doc, v, (s * CH_DE / 2, Z_TOP), (s * CH_DE / 2, zs), 2)
    C.poly(doc, v, [(-.35, zs), (0, zs + .15), (.35, zs), (-.35, zs)], 4, closed=False)
    dims = [chain_v(doc, v, u'Conducto: simple pared · doble pared', [Z_CIELO, Z_LO1, Z_TOP], xr + .40),
            chain_v(doc, v, u'Remate sobre la cumbrera', [ROOF_RIDGE_Z, Z_TOP], fx(ROOF_RIDGE_X) - .30),
            chain_v(doc, v, u'Remate sobre el techo en el conducto', [Z_ROOF, Z_TOP], -.70),
            chain_h(doc, v, u'Distancia conducto – cumbrera', [fx(ROOF_RIDGE_X), 0], ROOF_RIDGE_Z + 1.30)]
    pts = [((0, 2.75), u'CH-01 · Ø 35 simple pared en el plenum (0,50 ml)'), ((fx(CH_X), Z_LO1 - .10), u'CH-PA · pase en losa L01 0,50 × 0,50'),
           ((0, 6.0), u'CH-01 · Ø 35 doble pared aislado de +3,00 a +%s (%s ml)' % (c2(Z_TOP), c2(Z_TOP - Z_LO1))),
           ((cj0, 5.5), u'CH-CJ · cajón Durlock ampliado hasta el machimbre (a confirmar)'), ((0, Z_ROOF - .1), u'CH-BA · babeta / collar + brochal entre cabios'),
           ((0, zs + .1), u'CH-SO · sombrerete fijo'), ((fx(ROOF_RIDGE_X), ROOF_RIDGE_Z), u'Cumbrera CU-03 +%s' % c2(ROOF_RIDGE_Z))]
    labels(doc, v, pts, xr + 1.20, 9.6, .55)
    txt(doc, v, xl, -.45, u'Corte esquemático este-oeste por el eje del conducto\nRemate ≥ 0,60 sobre la cumbrera a menos de 3 m · cotas en m', 'text')
    parts = [('PR-01', (pr0, 0, pr1, Z_CIELO)), ('CH-01', (-CH_DE / 2, Z_CIELO, CH_DE / 2, Z_TOP)), ('CH-PA', (-.20, Z_LO0, .20, Z_LO1)), ('CH-CJ', (cj0, Z_LO1, cj1, roof_z(cj0 + ox) - .34)),
             ('CH-BA', (-.30, Z_ROOF - .40, .30, Z_ROOF + .10)), ('CH-SO', (-.35, Z_TOP, .35, zs + .15))]
    return ditem(doc, v, u'D-02a · Conducto: corte esquemático', ['CH-01'], dims, parts)

def d_pase(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-02 PASE DE CUBIERTA', 10)
    d = C.unit(-16.8); n = (-d[1], d[0]) if d[0] >= 0 else (d[1], -d[0])
    p0 = (-.90 * d[0], -.90 * d[1]); Ln = 1.80; gap = (CH_DE / 2 + .05) / d[0]
    C.slope_pkg(doc, v, p0, d, n, 0, .90 - gap, skip=('cabio',)); C.slope_pkg(doc, v, p0, d, n, .90 + gap, Ln, skip=('cabio',))
    top = lambda x: (x * (d[1] / d[0])) + C.TOP / d[0]
    zb, zt = -.45, .75
    for s in (-1, 1):
        rect(doc, v, s * CH_D / 2, zb, s * CH_DE / 2, zt, 'aislacion', 2)
    for s in (-1, 1):                                                                   # babeta: base plate + collar
        xa, xb = s * (CH_DE / 2 + .01), s * (CH_DE / 2 + .30)
        C.poly(doc, v, [(xb, top(xb) + .006), (xa, top(xa) + .006), (xa, top(xa) + .16)], 4, closed=False)
        rect(doc, v, s * CH_DE / 2, top(0) + .19, s * (CH_DE / 2 + .012), top(0) + .23, 'acero', 2)   # abrazadera / corta-gotas
    for s in (-1, 1): dl(doc, v, (s * (CH_DE / 2 + .005), top(s * .2) + .02), (s * (CH_DE / 2 + .045), top(s * .2) + .02), 1)
    dims = [chain_h(doc, v, u'Conducto doble pared Ø 35 / 40', [-CH_DE / 2, -CH_D / 2, CH_D / 2, CH_DE / 2], zt + .10),
            chain_h(doc, v, u'Separación a la madera (mín. 5 cm)', [CH_DE / 2, CH_DE / 2 + .05], zb - .10)]
    pts = [((0, zt - .1), u'CH-01 · conducto doble pared aislado (lana mineral 25 mm)'), ((.45, top(.45) + .005), u'CH-BA · babeta chapa galv. N°24 / inox: arriba bajo la teja, abajo sobre la teja'),
           ((CH_DE / 2, top(0) + .21), u'Abrazadera corta-gotas + sellador siliconado alta temperatura'), ((CH_DE / 2 + .03, top(.2) + .02), u'Hueco con lana mineral (≥ 5 cm a machimbre y cabios)'),
           ((.6, top(.6) - .25), u'Paquete CU-03: machimbre · barrera · EPS · membrana · cámara · listón · teja'), ((-.6, top(-.6) - .25), u'Brochal LVL 5×15 entre cabios (pase 0,50 × 0,50)')]
    labels(doc, v, pts, 1.15, zt + .25, .10)
    txt(doc, v, -.95, zb - .25, u'Cruce del conducto por la cubierta (corte por el eje, entre cabios) · cotas en m', 'text')
    parts = [('CH-01', (-CH_DE / 2, zb, CH_DE / 2, zt)), ('CH-BA', (-(CH_DE / 2 + .30), top(-.5) - .02, CH_DE / 2 + .30, top(0) + .25))]
    return ditem(doc, v, u'D-02b · Pase de cubierta y babeta', ['CH-BA'], dims, parts)

def d_sombrerete(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-02 SOMBRERETE', 10); R = .35; H = .25
    for s_ in (-1, 1):
        rect(doc, v, s_ * CH_D / 2, -.60, s_ * CH_DE / 2, 0, 'aislacion', 2)
        dl(doc, v, (s_ * (CH_DE / 2 - .005), 0), (s_ * (CH_DE / 2 - .005), H), 3)        # patas planchuela
    C.poly(doc, v, [(-R, H), (0, H + .15), (R, H), (-R, H)], 4, closed=False)              # cono
    C.poly(doc, v, [(-.21, 0), (-.21, H), (.21, H), (.21, 0)], 1, closed=False)            # malla
    for k in range(-4, 5): dl(doc, v, (k * .05, .005), (k * .05, H - .005), 1, u'Oculto')
    dims = [chain_h(doc, v, u'Sombrerete Ø', [-R, R], H + .30), chain_v(doc, v, u'Altura libre de salida', [0, H], -.50), chain_v(doc, v, u'Cono', [H, H + .15], -.65)]
    pts = [((.15, H + .08), u'CH-SO · cono fijo acero inox Ø 0,70 (2 × Ø)'), ((CH_DE / 2 - .005, .12), u'Patas planchuela inox 25 × 3 (4)'),
           ((.21, .06), u'Malla antichispa inox 10 mm'), ((0, -.30), u'CH-01 · conducto doble pared Ø 35 / 40')]
    labels(doc, v, pts, .75, .65, .10)
    txt(doc, v, -.65, -.75, u'Sombrerete fijo · altura libre ≥ 2/3 Ø (0,25 ≥ 0,23) · salida libre ≥ sección del conducto · cotas en m', 'text')
    parts = [('CH-SO', (-R, 0, R, H + .15)), ('CH-01', (-CH_DE / 2, -.60, CH_DE / 2, 0))]
    return ditem(doc, v, u'D-02c · Sombrerete fijo', ['CH-SO'], dims, parts)

# ---------------------------------------------------------------- sheets
def lay(doc, number, title, sub, items, sheet_name, scales, kind_level, plan_region=False):
    old = list(L.SCALES); L.SCALES[:] = list(scales)
    try: s = S.lay_sheet(doc, number, title, sub, items, FOOT, plan_region=plan_region, rubro=RUBRO, sheet_name=sheet_name)
    finally: L.SCALES[:] = old
    return dict(s, kind='general', level=kind_level[0], sector=kind_level[1])

def sheets_plans(doc):
    return [lay(doc, 'PAR-P-01', u'Ubicación de la parrilla y recorrido del conducto', u'Quincho (PB) · Comedor (PA) · cubierta CU-03 · el conducto pasa entre cabios',
                [plan_pb(doc), plan_pa(doc), plan_roof(doc)], u'Parrilla · P-01', (25,), (u'Plantas', u'1 · Ubicación'))]

def sheets_details(doc):
    s1 = lay(doc, 'PAR-D-01', u'Parrilla de obra a medida', u'Boca 1,50 · hogar +0,90 · campana de ladrillo refractario visto hasta el cielorraso · parrilla regulable + brasero · leñero',
             [d_planta(doc), d_frente(doc), d_corte(doc)], u'Parrilla · D-01', (20, 25), (u'Detalles', u'2 · Parrilla'))
    s2 = lay(doc, 'PAR-D-02', u'Conducto de humos: corte esquemático', u'Ø 35: simple pared en el plenum de PB, doble pared aislado desde la PA · remate +%s sobre cumbrera +%s' % (c2(Z_TOP), c2(ROOF_RIDGE_Z)),
             [d_conducto(doc)], u'Parrilla · D-02', (20, 25, 50), (u'Detalles', u'3 · Conducto'))
    s3 = lay(doc, 'PAR-D-03', u'Cruce de cubierta y sombrerete fijo', u'Pase entre cabios con brochal · babeta y corta-gotas · sombrerete fijo con malla antichispa',
             [d_pase(doc), d_sombrerete(doc)], u'Parrilla · D-03', (10,), (u'Detalles', u'3 · Conducto'))
    rec = R1.read(os.path.join(OUT, 'par34-model.json'))
    s4 = lay(doc, 'PAR-D-04', u'Tiraje: verificación y modelo 3D', u'Sección, garganta, campana, altura y remate verificados con reglas de chimeneas de mampostería (CRC 2025 cap. 10)',
             [axo(doc, rec['model']), d_tiraje(doc)], u'Parrilla · D-04', (20, 25, 50), (u'Detalles', u'4 · Tiraje'))
    return [s1, s2, s3, s4]

def index_part(doc, job):
    sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(L.TITLEBLOCK))); sheet.SheetNumber = 'PAR-00'; sheet.Name = u'Parrilla · índice'
    head = u'CASA ÁNGEL · PARRILLA · ÍNDICE Y CÓMPUTO (R34)'
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y1 - .012, 0), head, 'title'); notes = [{'text': head, 'anchor': [L.X0 + .01, L.Y1 - .012]}]
    for k, col in enumerate(job['columns']):
        xx = L.X0 + .01 + k * (L.X1 - L.X0) / len(job['columns'])
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP, 0), col['title'], 'sub'); notes.append({'text': col['title'], 'anchor': [xx, L.TOP]})
        L.tn(doc, sheet.Id, DB.XYZ(xx, L.TOP - .05, 0), u'\n'.join(col['lines']), 'text')
    L.tn(doc, sheet.Id, DB.XYZ(L.X0 + .01, L.Y0 + .05, 0), FOOT, 'text'); notes.append({'text': FOOT, 'anchor': [L.X0 + .01, L.Y0 + .05]})
    return [{'sheetId': eid(sheet), 'number': 'PAR-00', 'title': u'Índice y cómputo', 'views': [], 'notes': notes, 'kind': 'general', 'level': u'General', 'sector': u'General'}]

# ---------------------------------------------------------------- 3D model in the DOC file (DirectShape, Generic Models). The pilot is untouched.
def _loop(pts):
    cl = DB.CurveLoop()
    for i in range(len(pts)): cl.Append(DB.Line.CreateBound(pts[i], pts[(i + 1) % len(pts)]))
    return cl

def box(x0, y0, z0, x1, y1, z1):
    pts = [DB.XYZ(x / M, y / M, z0 / M) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop]([_loop(pts)]), DB.XYZ.BasisZ, (z1 - z0) / M)

def cyl(cx, cy, r, z0, z1):
    c = DB.XYZ(cx / M, cy / M, z0 / M); cl = DB.CurveLoop()
    cl.Append(DB.Arc.Create(c, r / M, 0, math.pi, DB.XYZ.BasisX, DB.XYZ.BasisY)); cl.Append(DB.Arc.Create(c, r / M, math.pi, 2 * math.pi, DB.XYZ.BasisX, DB.XYZ.BasisY))
    return DB.GeometryCreationUtilities.CreateExtrusionGeometry(List[DB.CurveLoop]([cl]), DB.XYZ.BasisZ, (z1 - z0) / M)

def model_parts():
    xi0, xi1 = LX(JA), LX(JA + BOCA); yd = LY(DEPTH)
    px0, px1 = LX(JA + .46), LX(JA + 1.46)
    return [('PR-JA', [box(LX(0), LY(0), 0, xi0, yd, Z_CIELO), box(xi1, LY(0), 0, LX(2 * JA + BOCA), yd, Z_CIELO)]),
            ('PR-AI', [box(LX(2 * JA + BOCA), LY(0), 0, EAST_X, yd, Z_CIELO)]),
            ('PR-FO', [box(xi0, LY(0), Z_LOSA1, xi1, LY(FONDO), Z_CIELO)]),
            ('PR-LO', [box(xi0, LY(0), Z_LOSA0, xi1, yd, Z_LOSA1)]),
            ('PR-SO', [box(xi0, LY(FONDO), Z_LOSA1, xi1, LY(FONDO + HOGAR), Z_HOGAR)]),
            ('PR-CA', [box(xi0, LY(DEPTH - FRENTE), Z_BOCA, xi1, yd, Z_CIELO)]),
            ('PR-DI', [box(xi0, LY(DEPTH - FRENTE), Z_BOCA - .064, xi1, yd, Z_BOCA)]),
            ('PR-PA', [box(px0, LY(FONDO + .025), Z_HOGAR + .20, px1, LY(FONDO + .575), Z_HOGAR + .22)]),
            ('PR-BR', [box(LX(JA + .04), LY(FONDO + .06), Z_HOGAR + .02, LX(JA + .39), LY(FONDO + .56), Z_HOGAR + .30)]),
            ('CH-01', [cyl(CH_X, CH_Y, CH_D / 2, Z_CIELO, Z_LO1), cyl(CH_X, CH_Y, CH_DE / 2, Z_LO1, Z_TOP)]),
            ('CH-SO', [cyl(CH_X, CH_Y, .35, Z_TOP + .25, Z_TOP + .30)])]

def model_part(doc):
    out = []
    for code, solids in model_parts():
        ds = DB.DirectShape.CreateElement(doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
        ds.SetShape(List[DB.GeometryObject]([x for x in solids])); ds.SetName(u'ADER PAR R34 ' + code)
        p = ds.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if p is not None: p.Set(code)
        c = ds.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if c is not None: c.Set(PARTS[code])
        out.append({'code': code, 'id': eid(ds), 'label': PARTS[code]})
    return out

def axo(doc, model):
    vft = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType) if t.ViewFamily == DB.ViewFamily.ThreeDimensional)
    v = DB.View3D.CreateIsometric(doc, vft.Id); v.Name = PRE + 'AXONOMETRIA'; v.Scale = 50
    eye = DB.XYZ((CH_X - 5.0) / M, (WALL_Y + 8.0) / M, 8.0 / M); tgt = DB.XYZ(3.3 / M, 2.4 / M, 4.4 / M)
    fwd = (tgt - eye).Normalize(); right = fwd.CrossProduct(DB.XYZ.BasisZ).Normalize(); up = right.CrossProduct(fwd)
    v.SetOrientation(DB.ViewOrientation3D(eye, up, fwd))
    bx = DB.BoundingBoxXYZ(); bx.Min = DB.XYZ(1.9 / M, (WALL_Y + .01) / M, -.3 / M); bx.Max = DB.XYZ((EAST_X + .005) / M, 3.3 / M, 10.0 / M)
    v.IsSectionBoxActive = True; v.SetSectionBox(bx)
    try: v.DisplayStyle = DB.DisplayStyle.ShadingWithEdges
    except Exception: pass
    for cat in (DB.BuiltInCategory.OST_Furniture, DB.BuiltInCategory.OST_PlumbingFixtures, DB.BuiltInCategory.OST_SpecialityEquipment, DB.BuiltInCategory.OST_DuctCurves,
                DB.BuiltInCategory.OST_DuctFitting, DB.BuiltInCategory.OST_Casework, DB.BuiltInCategory.OST_Windows, DB.BuiltInCategory.OST_Doors, DB.BuiltInCategory.OST_Ceilings,
                DB.BuiltInCategory.OST_Levels, DB.BuiltInCategory.OST_SectionBox):
        try: v.SetCategoryHidden(DB.ElementId(cat), True)
        except Exception: pass
    for li in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance):
        ov = DB.OverrideGraphicSettings(); ov.SetHalftone(True); ov.SetSurfaceTransparency(70); v.SetElementOverrides(li.Id, ov)
    red = DB.OverrideGraphicSettings(); red.SetProjectionLineColor(DB.Color(150, 40, 20))
    sp = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement) if x.GetFillPattern().IsSolidFill), None)
    if sp is not None: red.SetSurfaceForegroundPatternId(sp.Id); red.SetSurfaceForegroundPatternColor(DB.Color(196, 120, 90))
    grey = DB.OverrideGraphicSettings()
    if sp is not None: grey.SetSurfaceForegroundPatternId(sp.Id); grey.SetSurfaceForegroundPatternColor(DB.Color(170, 170, 175))
    for m in model:
        v.SetElementOverrides(DB.ElementId(Int64(m['id'])), grey if m['code'].startswith('CH') or m['code'] in ('PR-PA', 'PR-BR', 'PR-DI') else red)
    doc.Regenerate(); bb = DB.BoundingBoxXYZ(); bb.Min = DB.XYZ(0, 0, 0); bb.Max = DB.XYZ(4.8 / M, 11.0 / M, 0)
    return {'view': v, 'box': bb, 'title': u'D-04a · Axonometría (modelo en el archivo DOC)', 'kind': 'axo', 'sector': u'Tiraje', 'tags': ['PR-01', 'CH-01'], 'dims': [], 'elements': [], 'data': None}

def checks():
    area = BOCA * (Z_BOCA - Z_HOGAR); fl = math.pi * (CH_D / 2) ** 2
    cy = CH_Y - WALL_Y; lat = math.degrees(math.atan(((BOCA - CH_D) / 2) / (Z_CIELO - .02 - G0)))
    fr = math.degrees(math.atan(((DEPTH - FRENTE) - (cy + CH_D / 2)) / (Z_CIELO - .02 - G0)))
    roof_ok = Z_ROOF + .90; ridge_ok = ROOF_RIDGE_Z + .60
    return [(u'1. Sección del conducto', [u'Boca %s × %s = %s m² · conducto Ø %s = %s m²' % (c2(BOCA), c2(Z_BOCA - Z_HOGAR), c2(area), c2(CH_D), c3(fl)),
                                         u'Relación 1/%s ≥ 1/12 (conducto redondo) · CUMPLE' % (u'%.1f' % (area / fl)).replace(u'.', u','), u'(el Ø 30 previo daba 1/13,8: no cumplía)']),
            (u'2. Garganta y campana', [u'Garganta a +%s: %s sobre el dintel (≥ 0,20) · CUMPLE' % (c2(G0), c2(G0 - Z_BOCA)), u'Paredes de la campana: lateral %d°, frente %d° (≤ 45° de la vertical) · CUMPLE' % (round(lat), round(fr)),
                                       u'Altura de la cámara %s ≤ ancho de boca %s · CUMPLE' % (c2(Z_CIELO - G0), c2(BOCA)), u'Registro de tiro (mariposa) en el collar']),
            (u'3. Altura y recorrido', [u'Tiraje: hogar +%s a tope +%s = %s m, recto, sin codos' % (c2(Z_HOGAR), c2(Z_TOP), c2(Z_TOP - Z_HOGAR)), u'Sección constante Ø %s en todo el recorrido' % c2(CH_D)]),
            (u'4. Remate', [u'≥ 0,90 sobre el techo en el pase: +%s ≤ +%s · CUMPLE' % (c2(roof_ok), c2(Z_TOP)), u'≥ 0,60 sobre la cumbrera a < 3 m (%s m): +%s ≤ +%s · CUMPLE' % (c2(CH_X - ROOF_RIDGE_X), c2(ridge_ok), c2(Z_TOP)),
                            u'Sombrerete fijo Ø 0,70, salida libre 0,25']),
            (u'5. Hogar y combustibles', [u'Fondo del hogar %s ≥ 0,51 · refractario 6,4 cm ≥ 5 cm · CUMPLE' % c2(HOGAR), u'Separación a madera / Durlock ≥ 5 cm (doble pared aislado) · CUMPLE',
                                         u'Aire de reposición: el Quincho tiene portón; no cerrar herméticamente']),
            (u'Referencia', [u'California Residential Code 2025, cap. 10: R1001.6/7/8 (hogar,', u'garganta, cámara de humo), R1003.9 (remate), R1003.15 (sección),', u'R1003.18 (combustibles). Verificar con la normativa local.'])]

def d_tiraje(doc):
    ZCUR[0] = 0.0; v = C.drafting(doc, PRE + 'D-04 TIRAJE', 50)
    C.legend(doc, v, 0, 0, 0, checks(), [])
    return ditem(doc, v, u'D-04b · Verificación del tiraje', ['CH-01'], [], [])

def run(doc, uidoc, job):
    L.assert_pilot(doc)
    part = job['part']
    if part == 'probe':
        r = probe(doc)
        return {'status': 'success', 'PR-01': r['PR-01'], 'rooms': r['rooms'], 'roofs': r['roofs'], 'framing': len(r['framing'])}
    ld = CTX.activate(doc, L, [L, S, X.F, X, None])
    assert ld is not None and os.path.basename(doc.PathName) == 'Casa-Angel-DOC-Parrilla.rvt', 'Abrir Casa-Angel-DOC-Parrilla.rvt'
    path = os.path.join(OUT, 'par34-' + part + '.json')
    if part == 'model':
        mp = os.path.join(OUT, 'par34-model.json')
        if os.path.exists(mp):
            old = R1.read(mp)
            def wipe_m():
                for m in old['model']:
                    e = doc.GetElement(DB.ElementId(Int64(m['id'])))
                    if e is not None: doc.Delete(e.Id)
            B.plain(doc, PRE + 'borrar modelo', wipe_m)
        model = B.plain(doc, PRE + 'modelo 3D', lambda: model_part(doc))
        R1.write(mp, {'revision': 'R34', 'model': model, 'readAt': L.now()}); doc.Save()
        return {'status': 'success', 'model': [(m['code'], m['id']) for m in model]}
    if part == 'export':
        L.register_font()
        opts = DB.PDFExportOptions(); opts.Combine = True; opts.PaperFormat = DB.ExportPaperFormat.ISO_A1
        opts.PaperOrientation = DB.PageOrientationType.Landscape; opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
        done = []
        for fn in ('par34-plans.json', 'par34-details.json', 'par34-index.json'):
            if not os.path.exists(os.path.join(OUT, fn)): continue
            rec = R1.read(os.path.join(OUT, fn))
            for sh in rec['sheets']:
                opts.FileName = 'r34-' + sh['number']; sh['exported'] = bool(doc.Export(OUT, List[DB.ElementId]([DB.ElementId(Int64(sh['sheetId']))]), opts)); done.append(sh['number'])
            R1.write(os.path.join(OUT, fn), rec)
        return {'status': 'success', 'exported': done}
    if os.path.exists(path) and not job.get('redo'): return {'status': 'success', 'existing': True}
    if os.path.exists(path):
        rec = R1.read(path)
        def wipe():
            for sh in rec['sheets']:
                for i in [sh['sheetId']] + [x['id'] for x in sh['views']]:
                    e = doc.GetElement(DB.ElementId(Int64(int(i))))
                    if e is not None: doc.Delete(e.Id)
        B.plain(doc, PRE + 'borrar ' + part, wipe); os.remove(path)
    L.register_font()
    def body():
        if part == 'info': return B.project_info(doc, ld)
        if part == 'index': return index_part(doc, job)
        if part == 'plans': return sheets_plans(doc)
        if part == 'details': return sheets_details(doc)
        raise Exception('Unknown part')
    sheets = B.plain(doc, PRE + part, body)
    for sh in sheets:
        for x in sh['views']: x.pop('view', None)
    R1.write(path, {'part': part, 'revision': 'R34', 'sheets': sheets, 'readAt': L.now()})
    doc.Save()
    return {'status': 'success', 'part': part, 'sheets': [(sh['number'], [x['scale'] for x in sh['views']]) for sh in sheets]}
