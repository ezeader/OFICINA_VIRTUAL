# -*- coding: utf-8 -*-
"""R4: room-grouped openings sheets with fabrication dimensions. IronPython 2.7.

Documentation-only: views, sheets, viewports, dimensions, detail lines used as
dimension anchors, text notes and annotation types. Physical elements are
snapshotted before every write job and compared before commit.
"""
import os, io, json, math, datetime, imp
from Autodesk.Revit import DB
from System import Int64
from System.Collections.Generic import List

ROOT = os.path.dirname(__file__)
OUT = os.path.join(ROOT, 'openings-r4')
R1 = imp.load_source('ader_openings_r4_lib', os.path.join(ROOT, 'revit_openings_r1.py'))
D = imp.load_source('ader_openings_r4_docs', os.path.join(ROOT, 'revit_openings_docs.py'))
clean = R1.clean; name = R1.name; eid = R1.eid; xyz = R1.xyz
M = .3048
FONT = 'Bahnschrift SB Condensed ADER'
PILOT = 'casa-angel-piloto-documentacion.rvt'
PLAN_VFT, SECTION_VFT, TITLEBLOCK = 49552, 49554, 4428
SCALES = [10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250]
# Inner frame of the A1 title block in sheet feet (measured on exported PDF).
X0, X1, Y0, Y1 = .215, 2.25, .165, 1.785
TOP = Y1 - .15; BOTTOM = Y0 + .085
LEVEL_CODE = {311: 'PB', 694: 'PA', 353988: 'PE'}

if not os.path.isdir(OUT): os.makedirs(OUT)

def el(doc, i): return doc.GetElement(DB.ElementId(Int64(int(i))))
def read(n): return R1.read(os.path.join(OUT, n + '.json'))
def write(n, d): R1.write(os.path.join(OUT, n + '.json'), d)
def now(): return datetime.datetime.utcnow().isoformat() + 'Z'
def u(s):
    if s is None: return u''
    if isinstance(s, unicode): return s
    return clean(s)
def m3(v): return u'%.3f' % v
def snap(req):
    for s in SCALES:
        if s >= req - 1e-9: return s
    return int(math.ceil(req / 50.) * 50)

def assert_pilot(doc):
    assert os.path.basename(doc.PathName).lower() == PILOT, 'Only the Casa Angel pilot is authorized'
    assert not doc.IsFamilyDocument and not doc.IsReadOnly

def guarded(doc, label, body):
    """Run body() inside one transaction; physical snapshot must stay identical."""
    before = D.physical(doc)
    tx = DB.Transaction(doc, label); tx.Start()
    try:
        result = body()
        doc.Regenerate()
        assert D.physical(doc) == before, 'Physical geometry changed; rolled back'
        assert tx.Commit() == DB.TransactionStatus.Committed
    except:
        if tx.GetStatus() == DB.TransactionStatus.Started: tx.RollBack()
        raise
    return result, len(before)

def register_font():
    try:
        import clr
        clr.AddReferenceToFileAndPath(os.path.join(ROOT, 'AderRevitFontLoader2.dll'))
        from AderRevitFontLoader2 import Register
        return Register(os.path.join(ROOT, 'Bahnschrift-SB-Condensed-ADER.ttf'))
    except Exception as ex:
        return 'error: ' + str(ex)

def refs(e, kind):
    try:
        r = e.GetReferences(getattr(DB.FamilyInstanceReferenceType, kind))
        return r[0] if r and r.Count else None
    except: return None

def named_ref(e, label):
    for kind in ['StrongReference', 'WeakReference']:
        try:
            for r in e.GetReferences(getattr(DB.FamilyInstanceReferenceType, kind)):
                if e.GetReferenceName(r) == label: return r
        except: pass
    return None

def ptype(e, n):
    p = e.LookupParameter(n)
    if p is None and isinstance(e, DB.FamilyInstance): p = e.Symbol.LookupParameter(n)
    return p.AsDouble() if p and p.StorageType == DB.StorageType.Double else None

# ---------------------------------------------------------------- annotation types

TEXT_TYPES = {
    'title': ('ADER ABR R6 - Titulo 7mm', 7.0, False),
    'sub': ('ADER ABR R6 - Subtitulo 4.5mm', 4.5, False),
    'text': ('ADER ABR R6 - Texto 3mm', 3.0, False),
    'tag': ('ADER ABR R6 - Etiqueta 3.5mm', 3.5, True),
    'room': ('ADER ABR R6 - Local 4mm', 4.0, False),
}

def text_type(doc, key):
    n = TEXT_TYPES[key][0]
    return next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType) if name(t) == n)

def dim_type(doc):
    return next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.DimensionType) if name(t) == 'ADER ABR R4 - Cotas')

def set_font(t):
    p = t.get_Parameter(DB.BuiltInParameter.TEXT_FONT)
    p.Set('Arial'); p.Set(FONT)

def setup(doc):
    registered = register_font()
    def body():
        base = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType) if name(t) == 'ADER ABR - texto')
        made = []
        for key, (n, size, box) in TEXT_TYPES.items():
            t = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.TextNoteType) if name(x) == n), None)
            if t is None: t = base.Duplicate(n); made.append(n)
            set_font(t)
            t.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(size / 304.8)
            t.get_Parameter(DB.BuiltInParameter.TEXT_BOX_VISIBILITY).Set(1 if box else 0)
            t.get_Parameter(DB.BuiltInParameter.TEXT_BACKGROUND).Set(0 if (box or key == 'room') else 1)
            try: t.get_Parameter(DB.BuiltInParameter.TEXT_WIDTH_SCALE).Set(1.0)
            except: pass
        d2 = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.DimensionType) if name(t) == 'ADER ABR R2 - Cotas')
        d4 = next((t for t in DB.FilteredElementCollector(doc).OfClass(DB.DimensionType) if name(t) == 'ADER ABR R4 - Cotas'), None)
        if d4 is None: d4 = d2.Duplicate('ADER ABR R4 - Cotas'); made.append('ADER ABR R4 - Cotas')
        set_font(d4); d4.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(3.0 / 304.8)
        fo = d4.GetUnitsFormatOptions(); fo.UseDefault = False; fo.SetUnitTypeId(DB.UnitTypeId.Meters); fo.Accuracy = .001; d4.SetUnitsFormatOptions(fo)
        # Studio font on the earlier openings annotation types too (R2 sheets).
        set_font(base); set_font(d2)
        return made
    made, checked = guarded(doc, 'ADER ABR R4 - annotation types', body)
    doc.Save()
    result = {'status': 'success', 'font_register': registered, 'created': made, 'physicalChecked': checked, 'at': now()}
    write('setup', result)
    return result

# ---------------------------------------------------------------- geometry helpers

def level_of(doc, e): return doc.GetElement(e.LevelId)

def extents(doc, e):
    """Element extents: horizontal axis (2 XYZ ends), base z, top z, normal."""
    if isinstance(e, DB.Wall):
        c = e.Location.Curve; lev = level_of(doc, e)
        base = lev.Elevation + (e.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET).AsDouble() or 0)
        top = base + e.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble()
        n = e.Orientation
        return c.GetEndPoint(0), c.GetEndPoint(1), base, top, DB.XYZ(n.X, n.Y, 0).Normalize()
    b = e.get_BoundingBox(None); n = e.FacingOrientation; n = DB.XYZ(n.X, n.Y, 0).Normalize()
    x = DB.XYZ.BasisZ.CrossProduct(n)
    c = (b.Min + b.Max) * .5
    pts = [DB.XYZ(a, bb, c.Z) for a in [b.Min.X, b.Max.X] for bb in [b.Min.Y, b.Max.Y]]
    s = [(p - c).DotProduct(x) for p in pts]
    return c + x * min(s), c + x * max(s), b.Min.Z, b.Max.Z, n

def host_width(e):
    h = getattr(e, 'Host', None)
    return h.Width if isinstance(h, DB.Wall) else (e.Width if isinstance(e, DB.Wall) else .5)

def view_dir_for(doc, e, room):
    a, b, z0, z1, n = extents(doc, e)
    if room is not None:
        mid = (a + b) * .5; z = level_of(doc, e).Elevation + 1.0 / M
        off = host_width(e) / 2 + .6 / M
        front = room.IsPointInRoom(DB.XYZ(mid.X + n.X * off, mid.Y + n.Y * off, z))
        back = room.IsPointInRoom(DB.XYZ(mid.X - n.X * off, mid.Y - n.Y * off, z))
        if back and not front: return -n
        if front and not back: return n
        if isinstance(room.Location, DB.LocationPoint):
            d = room.Location.Point - mid; d = DB.XYZ(d.X, d.Y, 0)
            if d.DotProduct(n) < 0: n = -n
    return n

def elevation_box(doc, e, room):
    a, b, z0, z1, _ = extents(doc, e)
    vd = view_dir_for(doc, e, room)          # toward the viewer, inside the room
    x = DB.XYZ.BasisZ.CrossProduct(vd).Normalize()
    lev = level_of(doc, e)
    mid = (a + b) * .5
    origin = DB.XYZ(mid.X, mid.Y, lev.Elevation)
    t = DB.Transform.Identity; t.Origin = origin; t.BasisX = x; t.BasisY = DB.XYZ.BasisZ; t.BasisZ = vd
    ua = [(p - origin).DotProduct(x) for p in [a, b]]
    lo, hi = min(ua), max(ua)
    curtain = isinstance(e, DB.Wall)
    hw = host_width(e) / 2.
    bx = DB.BoundingBoxXYZ(); bx.Transform = t
    top = max(z1 - lev.Elevation + 1.0 / M * (1.05 if curtain else .85), 3.2 / M)
    bx.Min = DB.XYZ(lo - .45 / M, -.35 / M, -(hw + 1.0 / M))
    bx.Max = DB.XYZ(hi + (1.0 if curtain else .9) / M, top, hw + .45 / M)
    return bx, vd

def plan_box(doc, room, elements, level):
    pts = []
    if room is not None:
        rb = room.get_BoundingBox(None); pts += [rb.Min, rb.Max]
    for e in elements:
        b = e.get_BoundingBox(None); pts += [b.Min, b.Max]
    pad = .75 / M
    bx = DB.BoundingBoxXYZ()
    bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, level.Elevation - 1)
    bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, level.Elevation + 12)
    return bx

# ---------------------------------------------------------------- view setup

def setup_view(doc, v, levels=False):
    R1.configure_view(doc, v)
    show = [DB.BuiltInCategory.OST_Dimensions, DB.BuiltInCategory.OST_TextNotes, DB.BuiltInCategory.OST_Lines,
            DB.BuiltInCategory.OST_WindowTags, DB.BuiltInCategory.OST_DoorTags]
    if levels: show.append(DB.BuiltInCategory.OST_Levels)
    for c in show:
        try: v.SetCategoryHidden(DB.ElementId(c), False)
        except: pass

def highlight(doc, v, e):
    ov = DB.OverrideGraphicSettings(); ov.SetProjectionLineColor(DB.Color(25, 98, 143)); ov.SetProjectionLineWeight(4); ov.SetCutLineColor(DB.Color(25, 98, 143))
    ids = [e.Id]
    if isinstance(e, DB.Wall): ids += list(e.CurtainGrid.GetPanelIds()) + list(e.CurtainGrid.GetMullionIds())
    for i in ids: v.SetElementOverrides(i, ov)

class Frame(object):
    def __init__(self, v):
        self.v = v; self.o = v.Origin; self.rx = v.RightDirection; self.uy = v.UpDirection
    def p(self, x, y): return self.o + self.rx * x + self.uy * y
    def x(self, p): return (p - self.o).DotProduct(self.rx)
    def y(self, p): return (p - self.o).DotProduct(self.uy)

# ---------------------------------------------------------------- dimensions

def new_dim(doc, v, line, ra):
    d = doc.Create.NewDimension(v, line, ra)
    d.ChangeTypeId(dim_type(doc).Id)
    return d

def dim_values(d):
    if d.NumberOfSegments > 1: return [s.Value * M for s in d.Segments]
    return [d.Value * M] if d.Value is not None else []

def try_dim(doc, v, line, references, label, expected=None):
    sub = DB.SubTransaction(doc); sub.Start()
    try:
        ra = DB.ReferenceArray()
        for r in references: ra.Append(r)
        d = new_dim(doc, v, line, ra); doc.Regenerate()
        values = dim_values(d)
        assert values, 'Empty dimension'
        if expected is not None:
            assert all(abs(a - b) < .0015 for a, b in zip(values, expected)) and len(values) == len(expected), 'Value mismatch %s vs %s' % (values, expected)
        sub.Commit()
        return {'id': eid(d), 'label': label, 'values_m': values, 'associative': True}
    except Exception as ex:
        if sub.GetStatus() == DB.TransactionStatus.Started: sub.RollBack()
        return {'label': label, 'error': str(ex)}

def tick_dim(doc, f, label, positions, horizontal, at, tick=.10 / M):
    """Non-associative dimension anchored to short detail lines at model positions."""
    ra = DB.ReferenceArray(); ticks = []
    for s in positions:
        if horizontal: a, b = f.p(s, at - tick), f.p(s, at - tick * .35)
        else: a, b = f.p(at - tick, s), f.p(at - tick * .35, s)
        dc = doc.Create.NewDetailCurve(f.v, DB.Line.CreateBound(a, b)); ticks.append(eid(dc))
        ra.Append(dc.GeometryCurve.Reference)
    line = DB.Line.CreateBound(f.p(min(positions), at), f.p(max(positions), at)) if horizontal else DB.Line.CreateBound(f.p(at, min(positions)), f.p(at, max(positions)))
    d = new_dim(doc, f.v, line, ra)
    doc.Regenerate()
    return {'id': eid(d), 'label': label, 'values_m': dim_values(d), 'associative': False, 'anchors': ticks}

def uniq(vals, tol=.005 / M):
    out = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > tol: out.append(v)
    return out

def dims_family(doc, f, e, lev):
    a, b, z0, z1, _ = extents(doc, e)
    xs = sorted([f.x(a), f.x(b)]); yb, yt = z0 - f.o.Z, z1 - f.o.Z
    ylev = lev.Elevation - f.o.Z
    sill = (e.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).AsDouble() or 0)
    head = e.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM).AsDouble()
    family = e.Symbol.FamilyName; out = []
    W = ptype(e, 'Width'); H = ptype(e, 'Height'); RW = ptype(e, 'Rough Width'); RH = ptype(e, 'Rough Height')
    xr = xs[1] + .35 / M; xr2 = xs[1] + .65 / M; ytop = max(yt, ylev + head) + .25 / M
    hl = DB.Line.CreateBound(f.p(xs[0], ytop), f.p(xs[1], ytop))
    sliding = family == 'Puerta interior corredera'
    wlabel = 'Ancho de vano' if sliding else 'Ancho'
    wexp = (RW if sliding else W)
    out.append(try_dim(doc, f.v, hl, [refs(e, 'Left'), refs(e, 'Right')], wlabel, [wexp * M] if wexp else None))
    lref = DB.Reference(lev)
    vl = lambda x: DB.Line.CreateBound(f.p(x, ylev), f.p(x, ylev + head))
    if family == 'JALO_PUERTA ABATIBLE':
        r = try_dim(doc, f.v, vl(xr), [named_ref(e, 'ALTURA PAVIMENTO'), named_ref(e, 'ALTURA HUECO')], 'Alto', [ptype(e, 'ALTURA') * M])
        if r.get('error'): r = try_dim(doc, f.v, vl(xr), [lref, refs(e, 'Top')], 'Alto (piso a dintel)', [head * M])
        out.append(r)
    elif sill > .01 / M:
        out.append(try_dim(doc, f.v, vl(xr), [lref, refs(e, 'Bottom'), refs(e, 'Top')], 'Antepecho + alto', [sill * M, H * M]))
        out.append(try_dim(doc, f.v, vl(xr2), [lref, refs(e, 'Top')], 'Altura de dintel', [head * M]))
    else:
        label = 'Alto de vano (piso a dintel)' if sliding else 'Alto (piso a dintel)'
        out.append(try_dim(doc, f.v, vl(xr), [lref, refs(e, 'Top')], label, [(RH if sliding else head) * M]))
    for r in out:
        if r.get('error'):   # fall back to geometric anchors, flagged as non-associative
            r['fallbackFrom'] = r.pop('error')
            if r['label'].startswith('Ancho'): r.update(tick_dim(doc, f, r['label'], xs, True, ytop))
            else: r.update(tick_dim(doc, f, r['label'], [ylev, yt] if sill <= .01 / M else [ylev, yb, yt], False, xr))
    return out

def dims_curtain(doc, f, e, lev):
    a, b, z0, z1, _ = extents(doc, e)
    xs = sorted([f.x(a), f.x(b)]); ylev = lev.Elevation - f.o.Z
    g = e.CurtainGrid
    vx = [f.x(doc.GetElement(i).FullCurve.GetEndPoint(0)) for i in g.GetVGridLineIds()]
    uz = [doc.GetElement(i).FullCurve.GetEndPoint(0).Z - f.o.Z for i in g.GetUGridLineIds()]
    vx = [x for x in vx if xs[0] + .01 < x < xs[1] - .01]
    uz = [z for z in uz if z0 - f.o.Z + .01 < z < z1 - f.o.Z - .01]
    ytop = z1 - f.o.Z
    out = []
    if vx: out.append(tick_dim(doc, f, 'Modulos (ejes de grilla)', uniq(xs + vx), True, ytop + .25 / M))
    out.append(tick_dim(doc, f, 'Largo total', xs, True, ytop + (.5 if vx else .25) / M))
    ys = uniq([ylev, z0 - f.o.Z, ytop] + uz)
    xr = xs[1] + .35 / M
    out.append(tick_dim(doc, f, 'Arranque + modulos verticales' if len(ys) > 2 else 'Alto total', ys, False, xr))
    if len(ys) > 2: out.append(tick_dim(doc, f, 'Altura total desde nivel', [ylev, ytop], False, xr + .3 / M))
    return out

class AxisFrame(Frame):
    def __init__(self, v, o, rx, uy):
        self.v = v; self.o = o; self.rx = rx; self.uy = uy

def plan_dim(doc, plan, e, room):
    a, b, z0, z1, n = extents(doc, e)
    vd = view_dir_for(doc, e, room)
    lev = doc.GetElement(plan.GenLevel.Id)
    if isinstance(e, DB.Wall):
        z = plan.Origin.Z; rx = (b - a); rx = DB.XYZ(rx.X, rx.Y, 0).Normalize()
        f = AxisFrame(plan, DB.XYZ(a.X, a.Y, z), rx, vd)
        L = a.DistanceTo(b); xs = [0, L]
        vx = [f.x(DB.XYZ(q.X, q.Y, z)) for q in [doc.GetElement(i).FullCurve.GetEndPoint(0) for i in e.CurtainGrid.GetVGridLineIds()]]
        vx = [x for x in vx if .01 < x < L - .01]
        out = []
        if vx: out.append(tick_dim(doc, f, 'Modulos en planta', uniq(xs + vx), True, .45 / M, tick=.08 / M))
        out.append(tick_dim(doc, f, 'Largo en planta', xs, True, (.70 if vx else .45) / M, tick=.08 / M))
        return out
    off = vd * (.45 / M); p0 = DB.XYZ(a.X, a.Y, 0) + off; p1 = DB.XYZ(b.X, b.Y, 0) + off
    p0 = DB.XYZ(p0.X, p0.Y, lev.Elevation); p1 = DB.XYZ(p1.X, p1.Y, lev.Elevation)
    return [try_dim(doc, plan, DB.Line.CreateBound(p0, p1), [refs(e, 'Left'), refs(e, 'Right')], 'Ancho en planta')]

CAPSULE_SOURCES = [364138, 1020050, 1020586]

def capsule_arcs(doc, v):
    """Arcs seen true-size in the view (normal parallel to view direction), from the elevator assembly; read only."""
    opt = DB.Options(); opt.View = v; opt.ComputeReferences = True
    found = []
    def walk(g, owner, tr):
        for o in g:
            if isinstance(o, DB.GeometryInstance): walk(o.GetSymbolGeometry(), owner, tr.Multiply(o.Transform) if tr else o.Transform)
            elif isinstance(o, DB.Solid):
                for ed in o.Edges:
                    c = ed.AsCurve()
                    if not isinstance(c, DB.Arc) or c.Radius * M < .1: continue
                    nrm = tr.OfVector(c.Normal) if tr else c.Normal
                    if abs(nrm.DotProduct(v.ViewDirection)) < .99: continue
                    found.append({'owner': owner, 'center': tr.OfPoint(c.Center) if tr else c.Center, 'r': c.Radius, 'ref': ed.Reference})
    for t in CAPSULE_SOURCES:
        e = el(doc, t); comps = [e]
        if isinstance(e, DB.Wall) and e.CurtainGrid: comps += [doc.GetElement(i) for i in list(e.CurtainGrid.GetMullionIds())]
        for c in comps:
            g = c.get_Geometry(opt)
            if g: walk(g, t, None)
    return found

def radial_type(doc, d):
    t = next((x for x in DB.FilteredElementCollector(doc).OfClass(DB.DimensionType) if name(x) == 'ADER ABR R4 - Radio'), None)
    if t is None:
        t = doc.GetElement(d.GetTypeId()).Duplicate('ADER ABR R4 - Radio'); set_font(t)
        fo = t.GetUnitsFormatOptions(); fo.UseDefault = False; fo.SetUnitTypeId(DB.UnitTypeId.Meters); fo.Accuracy = .001; t.SetUnitsFormatOptions(fo)
    t.get_Parameter(DB.BuiltInParameter.TEXT_SIZE).Set(3.0 / 304.8)
    return t

def capsule_dims(doc, f, e):
    arcs = capsule_arcs(doc, f.v); out = []; notes = []
    uniq_arcs = {}
    for a in arcs:
        k = (a['owner'], round(f.x(a['center']) * M, 2), round(f.y(a['center']) * M, 2), round(a['r'] * M, 3))
        uniq_arcs.setdefault(k, a)
    if not uniq_arcs: return out, notes
    lev = level_of(doc, e); ylev = lev.Elevation - f.o.Z
    by_owner = {}
    for k, a in uniq_arcs.items(): by_owner.setdefault(k[0], []).append(a)
    xoff = 0
    for owner in sorted(by_owner):
        rows = by_owner[owner]; R = max(a['r'] for a in rows)
        outer = [a for a in rows if abs(a['r'] - R) < 1e-6]
        cx = sum(f.x(a['center']) for a in outer) / len(outer)
        cys = uniq([f.y(a['center']) for a in outer], tol=.002 / M)
        label = u'muro 364138' if owner == 364138 else u'MC-' + str(owner)
        for cy in cys:
            for dx, dy in [(.08 / M, 0), (0, .08 / M)]:
                doc.Create.NewDetailCurve(f.v, DB.Line.CreateBound(f.p(cx - dx, cy - dy), f.p(cx + dx, cy + dy)))
        done = set()
        for a in rows:
            k = (round(f.y(a['center']) * M, 2), round(a['r'] * M, 3))
            if k in done or a['ref'] is None: continue
            done.add(k)
            sub = DB.SubTransaction(doc); sub.Start()
            try:
                c = a['center']; up = 1 if f.y(c) > (min(cys) + max(cys)) / 2 else -1
                origin = f.p(f.x(c) + a['r'] * .45, f.y(c) + up * a['r'] * .55)
                d = DB.RadialDimension.Create(doc, f.v, a['ref'], origin); d.ChangeTypeId(radial_type(doc, d).Id); doc.Regenerate()
                sub.Commit(); out.append({'id': eid(d), 'label': u'Arco ' + label + u' (diámetro; R ' + m3(a['r'] * M) + u')', 'values_m': [d.Value * M], 'radius_m': a['r'] * M, 'associative': True})
            except Exception as ex:
                if sub.GetStatus() == DB.TransactionStatus.Started: sub.RollBack()
                out.append({'label': u'Radio ' + label, 'values_m': [a['r'] * M], 'associative': False, 'note': 'RadialDimension no disponible: ' + str(ex)[:80]})
        ys = uniq([ylev] + [y for cy in cys for y in (cy - R, cy, cy + R)], tol=.002 / M)
        ys = [y for y in ys if y >= ylev - 1e-6]
        xl = cx - R - (.35 + xoff) / M
        out.append(tick_dim(doc, f, u'Cápsula ' + label + u': extremos y centros desde nivel', ys, False, xl))
        out.append(tick_dim(doc, f, u'Cápsula ' + label + u': tramo recto entre centros', [min(cys), max(cys)], False, xl - .25 / M))
        out.append(tick_dim(doc, f, u'Cápsula ' + label + u': radio / ancho', [cx - R, cx, cx + R], True, max(cys) + R + (.25 + xoff) / M))
        notes.append(label + u': R ' + m3(R * M) + u' · centros +' + u' / +'.join(m3((y - ylev) * M) for y in cys) + u' · tramo recto ' + m3((max(cys) - min(cys)) * M) + u' · alto total ' + m3((max(cys) - min(cys) + 2 * R) * M) + u' m')
        xoff += .55
    return out, notes

# ---------------------------------------------------------------- labels

def cm(v): return (u'%.2f' % v).replace(u'.', u',')

def element_label(doc, e, code):
    if isinstance(e, DB.Wall):
        a, b, z0, z1, _ = extents(doc, e)
        return code + u' · ' + cm(a.DistanceTo(b) * M) + u' × ' + cm((z1 - z0) * M)
    W = ptype(e, 'Width'); H = ptype(e, 'Height')
    if W is None or H is None: return code
    return code + u' · ' + cm(W * M) + u' × ' + cm(H * M)

def room_label(rr):
    return u'Sin local asignado' if rr['number'] == 'SL' else rr['number'] + u' · ' + u(rr['name'])

def crop_corner(v, dx, dy):
    """Model point near the top-left corner of a section's crop, on its cut plane."""
    cb = v.CropBox
    return cb.Transform.OfPoint(DB.XYZ(cb.Min.X + dx, cb.Max.Y - dy, cb.Max.Z))

def make_axo(doc, room, elements, level, prefix):
    pts = []
    if room is not None:
        rb = room.get_BoundingBox(None); pts += [rb.Min, rb.Max]
    for e in elements:
        b = e.get_BoundingBox(None); pts += [b.Min, b.Max]
    pad = .4 / M
    bx = DB.BoundingBoxXYZ()
    bx.Min = DB.XYZ(min(p.X for p in pts) - pad, min(p.Y for p in pts) - pad, level.Elevation - .1 / M)
    bx.Max = DB.XYZ(max(p.X for p in pts) + pad, max(p.Y for p in pts) + pad, max([level.Elevation + 2.55 / M] + [e.get_BoundingBox(None).Max.Z + .05 / M for e in elements]))
    ax = DB.View3D.CreateIsometric(doc, DB.ElementId(Int64(49559))); setup_view(doc, ax)
    ax.Name = prefix + ' - AXO'; ax.SetSectionBox(bx); ax.IsSectionBoxActive = True
    d = DB.XYZ(-1, -1, -.75).Normalize(); right = d.CrossProduct(DB.XYZ.BasisZ).Normalize()
    ax.SetOrientation(DB.ViewOrientation3D(DB.XYZ.Zero, right.CrossProduct(d).Normalize(), d))
    D.fit3d(doc, ax)
    try: ax.SaveOrientationAndLock()
    except Exception: pass
    for e in elements: highlight(doc, ax, e)
    return ax

def axo_note(doc, ax, p, text, key):
    """Text in a locked 3D view, placed on the view plane through p; skipped if Revit refuses."""
    sub = DB.SubTransaction(doc); sub.Start()
    try:
        o = ax.Origin; vd = ax.ViewDirection
        q = p - vd * (p - o).DotProduct(vd)
        tn(doc, ax.Id, q, text, key); doc.Regenerate(); sub.Commit(); return True
    except Exception:
        if sub.GetStatus() == DB.TransactionStatus.Started: sub.RollBack()
        return False

# ---------------------------------------------------------------- text

def tn(doc, view_id, p, text, key):
    return DB.TextNote.Create(doc, view_id, p, u(text), text_type(doc, key).Id)

def data_lines(doc, e, item, room_names):
    lines = []
    typ = u(name(doc.GetElement(e.GetTypeId())))
    mats = sorted(set(u(name(doc.GetElement(i))) for i in e.GetMaterialIds(False)))
    if isinstance(e, DB.Wall):
        a, b, z0, z1, _ = extents(doc, e); lev = level_of(doc, e)
        g = e.CurtainGrid
        lines.append(u'Muro cortina · ' + typ + u' · ' + str(g.GetPanelIds().Count) + u' paneles / ' + str(g.GetMullionIds().Count) + u' montantes')
        lines.append(u'Largo ' + m3(a.DistanceTo(b) * M) + u' · Alto ' + m3((z1 - z0) * M) + u' · Arranque +' + m3((z0 - lev.Elevation) * M) + u' · Superior +' + m3((z1 - lev.Elevation) * M) + u' m')
    else:
        sym = e.Symbol; fam = u(sym.FamilyName)
        lines.append(typ + u' · ' + fam)
        sill = (e.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).AsDouble() or 0) * M
        head = e.get_Parameter(DB.BuiltInParameter.INSTANCE_HEAD_HEIGHT_PARAM).AsDouble() * M
        W = ptype(e, 'Width'); H = ptype(e, 'Height')
        if fam == 'Puerta interior corredera':
            lines.append(u'Hoja ' + m3(W * M) + u' × ' + m3(H * M) + u' · Vano ' + m3(ptype(e, 'Rough Width') * M) + u' × ' + m3(ptype(e, 'Rough Height') * M) + u' m')
        else:
            lines.append(u'Ancho ' + m3(W * M) + u' · Alto ' + m3(H * M) + u' · Antepecho ' + m3(sill) + u' · Dintel ' + m3(head) + u' m')
        if 'techo' in typ.lower(): lines.append(u'Tipo muro a techo: piso terminado a dintel ' + m3(head) + u' m (verificar con cielorraso)')
    lines.append(u'Muro ' + m3(host_width(e) * M) + u' m' + (u' · Materiales: ' + u', '.join(mats) if mats else u''))
    if len(room_names) > 1: lines.append(u'Compartida con: ' + u' / '.join(room_names[1:]) + u' (computar una vez)')
    return lines

# ---------------------------------------------------------------- layout

def sheet_size(bx, scale):
    return ((bx.Max.X - bx.Min.X) / scale, (bx.Max.Y - bx.Min.Y) / scale)

TITLE_H, DATA_H, MIN_W, GAP = .06, .15, .46, .05

def row_options(sz, W):
    """(scale, width, height) per allowed scale for one row of item sizes."""
    out = []
    for s in SCALES:
        w = sum(max(a / s, MIN_W) + GAP for a, b in sz)
        if w <= W + 1e-9: out.append((s, w, max(b / s for a, b in sz) + TITLE_H + DATA_H))
    return out

def pack_rows(sizes, W, H):
    """Ordered items into rows; minimise sum(log scale) under the region height (DP on height)."""
    n = len(sizes); best = None
    def comps(k):
        if k == 0:
            yield []
            return
        for first in range(1, k + 1):
            for rest in comps(k - first): yield [first] + rest
    for comp in comps(n):
        rows = []; i = 0
        for c in comp: rows.append(list(range(i, i + c))); i += c
        states = {0: (0., [])}
        for r in rows:
            opts = row_options([sizes[j] for j in r], W); nxt = {}
            for used, (cost, picks) in states.items():
                for sc, w, h in opts:
                    hu = used + int(math.ceil(h / .005))
                    if hu * .005 > H + 1e-9: continue
                    c2 = cost + len(r) * math.log(sc)
                    if hu not in nxt or c2 < nxt[hu][0]: nxt[hu] = (c2, picks + [(r, sc, h)])
            states = nxt
            if not states: break
        for used, (cost, picks) in states.items():
            if len(picks) == len(rows) and (best is None or cost < best[0] - 1e-9): best = (cost, picks)
    return best

LIMITS = {'family': 20, 'curtain': 50, 'axo': 50}

def layout_ok(L, kinds):
    if L is None or (kinds and not L.get('rows')): return False
    if L.get('plan') and L['plan'][1] > 50: return False
    for r, sc, h in (L['rows'][1] if L.get('rows') else []):
        for j in r:
            if sc > LIMITS[kinds[j]]: return False
    return True

def paginate(psize, axo_size, elevs, kind_of):
    """One sheet when everything stays at full scale; otherwise sheet 1 = plan + axo, then balanced elevation sheets."""
    sz = lambda xs: [sheet_size(x[3], 1) for x in xs]
    L = choose_layout(psize, sz([axo_size] + elevs))
    if layout_ok(L, ['axo'] + [kind_of(x) for x in elevs]): return [([axo_size] + elevs, L)]
    pages = [([axo_size], choose_layout(psize, sz([axo_size])))]
    n = len(elevs); npages = int(math.ceil(n / 4.))
    while True:
        size = int(math.ceil(float(n) / npages)); chunks = [elevs[i:i + size] for i in range(0, n, size)]
        layouts = [choose_layout(None, sz(c)) for c in chunks]
        if all(layout_ok(l, [kind_of(x) for x in c]) for l, c in zip(layouts, chunks)) or size == 1: break
        npages += 1
    return pages + list(zip(chunks, layouts))

def choose_layout(plan_size, elev_sizes):
    W = X1 - X0; H = TOP - BOTTOM
    if plan_size is None:
        return {'plan': None, 'region': (X0, BOTTOM, X1, TOP), 'rows': pack_rows(elev_sizes, W, H)}
    if not elev_sizes:
        s = snap(max(plan_size[0] / (W - .04), plan_size[1] / (H - .07)))
        return {'plan': ((X0, BOTTOM, X1, TOP), s), 'region': None, 'rows': None}
    options = []
    for fw in [.22, .28, .34, .40, .46, .52, .58, .64, .70]:
        pw = W * fw; ps = snap(max(plan_size[0] / (pw - .03), plan_size[1] / (H - TITLE_H - .03)))
        g = pack_rows(elev_sizes, W - pw, H)
        if g: options.append((1.3 * math.log(ps) + g[0], {'plan': ((X0, BOTTOM, X0 + pw, TOP), ps), 'region': (X0 + pw, BOTTOM, X1, TOP), 'rows': g}))
    for fh in [.30, .38, .46, .54, .62]:
        ph = H * fh; ps = snap(max(plan_size[0] / (W - .04), plan_size[1] / (ph - TITLE_H - .03)))
        g = pack_rows(elev_sizes, W, H - ph)
        if g: options.append((1.3 * math.log(ps) + g[0], {'plan': ((X0, TOP - ph, X1, TOP), ps), 'region': (X0, BOTTOM, X1, TOP - ph), 'rows': g}))
    options.sort(key=lambda o: o[0])
    return options[0][1]

def place(doc, sheet, v, scale, cell, title, vptype):
    """Center the viewport in the cell's drawing area, title above, return meta."""
    x0, y0, x1, y1 = cell
    v.Scale = scale
    vp = DB.Viewport.Create(doc, sheet.Id, v.Id, DB.XYZ((x0 + x1) / 2, (y0 + y1) / 2, 0)); vp.ChangeTypeId(vptype.Id)
    doc.Regenerate()
    cx = (x0 + x1) / 2; cy = (y0 + DATA_H + y1 - TITLE_H) / 2
    vp.SetBoxCenter(DB.XYZ(cx, cy, 0)); doc.Regenerate()
    o = vp.GetBoxOutline()
    label = u(title) + u'   1:' + str(scale)
    anchor = [o.MinimumPoint.X, o.MaximumPoint.Y + .045]
    tn(doc, sheet.Id, DB.XYZ(anchor[0], anchor[1], 0), label, 'sub')
    return vp, {'id': eid(v), 'name': u(title), 'label': label, 'scale': scale, 'anchor': anchor,
                'box': [xyz(o.MinimumPoint), xyz(o.MaximumPoint)]}

# ---------------------------------------------------------------- room job

def room_job(doc, key):
    plan_data = read('plan')
    rr = next(r for r in plan_data['rooms'] if r['key'] == str(key))
    path = os.path.join(OUT, 'room-' + rr['key'] + '.json')
    if os.path.exists(path):
        rec = R1.read(path)
        if all(el(doc, p['sheet_id']) for p in rec['pages']): return {'status': 'success', 'existing': True, 'key': rr['key']}
    register_font()
    items = dict((i['id'], i) for i in plan_data['items'])
    rooms_by_id = dict((r['id'], r) for r in plan_data['rooms'] if r['id'])
    room = el(doc, rr['id']) if rr['id'] else None
    elements = [el(doc, i) for i in rr['items']]
    level = el(doc, rr['level'])
    vptype = next(t for t in DB.FilteredElementCollector(doc).OfClass(DB.ElementType) if name(t) == 'ADER ABR - viewport')
    prefix = 'ADER ABR R4 - ' + rr['sheet'].replace('ABR-R4-', '')
    codes = [items[i]['code'] for i in rr['items']]
    # pagination: first page carries the plan
    n = len(elements)
    chunks = [elements] if n <= 4 else [elements[:3]] + [elements[i:i + 6] for i in range(3, n, 6)]
    def body():
        record = {'key': rr['key'], 'room_id': rr['id'], 'name': u(rr['name']), 'level': u(rr['level_name']), 'number': rr['number'],
                  'codes': codes, 'pages': [], 'elements': {}, 'readAt': now()}
        # views first (sizes known from crop boxes)
        plan = DB.ViewPlan.Create(doc, DB.ElementId(Int64(PLAN_VFT)), level.Id); setup_view(doc, plan)
        plan.Name = prefix + ' - PLANTA'
        pb = plan_box(doc, room, elements, level); plan.CropBox = pb; plan.CropBoxActive = True; plan.CropBoxVisible = False
        try: plan.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
        except: pass
        vr = plan.GetViewRange()
        vr.SetLevelId(DB.PlanViewPlane.CutPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.CutPlane, 1.30 / M)
        vr.SetLevelId(DB.PlanViewPlane.TopClipPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.TopClipPlane, 4.0 / M)
        vr.SetLevelId(DB.PlanViewPlane.BottomClipPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, 0)
        vr.SetLevelId(DB.PlanViewPlane.ViewDepthPlane, level.Id); vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, -.3 / M)
        plan.SetViewRange(vr)
        elevs = []
        for e in elements:
            item = items[eid(e)]
            highlight(doc, plan, e)
            bx, vd = elevation_box(doc, e, room)
            v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(SECTION_VFT)), bx)
            if v.ViewDirection.DotProduct(vd) < 0:     # Revit convention guard: look from inside the room
                doc.Delete(v.Id)
                t = bx.Transform; t2 = DB.Transform.Identity; t2.Origin = t.Origin; t2.BasisX = -t.BasisX; t2.BasisY = t.BasisY; t2.BasisZ = -t.BasisZ
                b2 = DB.BoundingBoxXYZ(); b2.Transform = t2; b2.Min = DB.XYZ(-bx.Max.X, bx.Min.Y, -bx.Max.Z); b2.Max = DB.XYZ(-bx.Min.X, bx.Max.Y, -bx.Min.Z)
                v = DB.ViewSection.CreateSection(doc, DB.ElementId(Int64(SECTION_VFT)), b2); bx = b2
            setup_view(doc, v, levels=True); v.Name = prefix + ' - ' + item['code'] + ' - ALZADO'; v.CropBoxVisible = False
            try: v.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(0)
            except: pass
            others = [l.Id for l in DB.FilteredElementCollector(doc).OfClass(DB.Level) if l.Id != e.LevelId and l.Id != level.Id]
            if others: v.HideElements(List[DB.ElementId](others))
            highlight(doc, v, e)
            elevs.append((e, item, v, bx))
        doc.Regenerate()
        # dimensions, tags and data per element
        for e, item, v, bx in elevs:
            f = Frame(v); lev = level_of(doc, e)
            dims = dims_curtain(doc, f, e, lev) if isinstance(e, DB.Wall) else dims_family(doc, f, e, lev)
            a, b, z0, z1, _ = extents(doc, e)
            xc = (f.x(a) + f.x(b)) / 2; yc = (z0 + z1) / 2 - f.o.Z
            tn(doc, v.Id, f.p(xc - .15 / M, min(yc + .1 / M, z1 - f.o.Z - .1 / M)), element_label(doc, e, item['code']), 'tag')
            tn(doc, v.Id, crop_corner(v, .06 / M, .06 / M), room_label(rr), 'room')
            pd = plan_dim(doc, plan, e, room)
            cap_notes = []
            if eid(e) in (1020586, 1020050):
                cd, cap_notes = capsule_dims(doc, f, e); dims = dims + cd
            # plan tag: offset into the room from the element mid point
            vd = view_dir_for(doc, e, room); mid = (a + b) * .5
            tp = DB.XYZ(mid.X, mid.Y, level.Elevation) + vd * (.95 / M)
            tn(doc, plan.Id, tp, element_label(doc, e, item['code']), 'tag')
            names = [u(rr['name'])] + [u(rooms_by_id[r]['name']) for r in item['rooms'] if r != rr['id'] and r in rooms_by_id]
            record['elements'][str(eid(e))] = {'code': item['code'], 'viewId': eid(v), 'viewDirection': xyz(v.ViewDirection),
                                              'dimensions': dims + (pd or []), 'data': data_lines(doc, e, item, names) + [u'C\u00e1psula ' + x for x in cap_notes]}
        if room is not None and isinstance(room.Location, DB.LocationPoint):
            rp = room.Location.Point; tn(doc, plan.Id, DB.XYZ(rp.X, rp.Y, level.Elevation), room_label(rr), 'room')
        else:
            pc = plan.CropBox; tn(doc, plan.Id, DB.XYZ(pc.Min.X + .3 / M, pc.Max.Y - .3 / M, level.Elevation), room_label(rr), 'room')
        ax = make_axo(doc, room, elements, level, prefix); axo_tags = 0
        doc.Regenerate()
        for e in elements:
            b = e.get_BoundingBox(None); c = (b.Min + b.Max) * .5
            axo_tags += axo_note(doc, ax, c, element_label(doc, e, items[eid(e)]['code']), 'tag')
        if room is not None and isinstance(room.Location, DB.LocationPoint):
            rp = room.Location.Point; axo_tags += axo_note(doc, ax, DB.XYZ(rp.X, rp.Y, level.Elevation + .05 / M), room_label(rr), 'room')
        record['axoId'] = eid(ax); record['axoTags'] = axo_tags
        doc.Regenerate()
        # layout pages
        psize = sheet_size(plan.CropBox, 1)
        axo_item = (None, {'code': None}, ax, ax.CropBox)
        pages_plan = paginate(psize, axo_item, elevs, lambda x: 'curtain' if isinstance(x[0], DB.Wall) else 'family')
        for pi, (ev, L) in enumerate(pages_plan):
            number = rr['sheet'] + ('' if pi == 0 else '-' + str(pi + 1)); npages = len(pages_plan)
            sheet = DB.ViewSheet.Create(doc, DB.ElementId(Int64(TITLEBLOCK))); sheet.SheetNumber = number
            sheet.Name = u(rr['name']) + u' · ABR' + (u'' if npages == 1 else u' ' + str(pi + 1) + u'/' + str(npages))
            title = u'CASA ÁNGEL · ABERTURAS · ' + u(rr['level_name']).upper() + u' · ' + (rr['number'] + u' ' if rr['number'] != 'SL' else u'') + u(rr['name']).upper()
            notes = [{'text': title, 'anchor': [X0 + .01, Y1 - .012]}]
            tn(doc, sheet.Id, DB.XYZ(X0 + .01, Y1 - .012, 0), title, 'title')
            sub = u'Hoja ' + str(pi + 1) + u' de ' + str(npages) + u' · ' + str(len(codes)) + u' elementos: ' + u', '.join(codes)
            tn(doc, sheet.Id, DB.XYZ(X0 + .01, Y1 - .075, 0), sub, 'sub'); notes.append({'text': sub, 'anchor': [X0 + .01, Y1 - .075]})
            foot = u'Cotas en metros (0.001 m) sobre geometría nativa. Cotas de muros cortina y cápsula del ascensor: referidas a ejes de grilla, extremos y centros de arcos (no asociativas, salvo radios). Alzados vistos desde el interior del local. Elementos compartidos entre locales: un solo cómputo por código.'
            tn(doc, sheet.Id, DB.XYZ(X0 + .01, Y0 + .05, 0), foot, 'text'); notes.append({'text': foot, 'anchor': [X0 + .01, Y0 + .05]})
            views = []
            if L['plan']:
                cell, s = L['plan']
                vp, meta = place(doc, sheet, plan, s, cell, u'Planta del local \u00b7 ' + room_label(rr), vptype); meta['kind'] = 'plan'; views.append(meta)
            if ev:
                cost, picks = L['rows']; rx0, ry0, rx1, ry1 = L['region']
                slack_y = ((ry1 - ry0) - sum(h for r, sc, h in picks)) / len(picks); ytop = ry1
                for r, sc, h in picks:
                    hh = h + slack_y
                    widths = [max(sheet_size(ev[j][3], 1)[0] / sc, MIN_W) + GAP for j in r]
                    slack_x = ((rx1 - rx0) - sum(widths)) / len(r); x = rx0
                    for j, w in zip(r, widths):
                        e, item, v, bx = ev[j]
                        cell = (x, ytop - hh, x + w + slack_x, ytop); x += w + slack_x
                        if e is None:
                            vp, meta = place(doc, sheet, v, sc, cell, u'Axonom\u00e9trica del local \u00b7 ' + room_label(rr), vptype)
                            meta['kind'] = 'axo'; views.append(meta); continue
                        vp, meta = place(doc, sheet, v, sc, cell, item['code'] + u' · alzado interior', vptype)
                        meta.update(kind='elevation', elementId=eid(e), code=item['code'])
                        o = vp.GetBoxOutline(); y = o.MinimumPoint.Y - .012
                        data = record['elements'][str(eid(e))]['data']
                        tn(doc, sheet.Id, DB.XYZ(o.MinimumPoint.X, y, 0), u'\n'.join(data), 'text')
                        record['elements'][str(eid(e))]['sheet'] = number
                        views.append(meta)
                    ytop -= hh
            record['pages'].append({'sheet_id': eid(sheet), 'sheet_number': number, 'page': pi + 1, 'views': views, 'notes': notes})
        record['planId'] = eid(plan)
        return record
    record, checked = guarded(doc, 'ADER ABR R4 - ' + rr['sheet'], body)
    record['physicalChecked'] = checked; record['exported'] = False
    R1.write(path, record); doc.Save()
    errs = [d for x in record['elements'].values() for d in x['dimensions'] if d.get('error')]
    return {'status': 'success', 'key': rr['key'], 'pages': [p['sheet_number'] for p in record['pages']],
            'scales': [[v['scale'] for v in p['views']] for p in record['pages']], 'axoTags': record.get('axoTags'),
            'dims': sum(len(x['dimensions']) for x in record['elements'].values()), 'dimErrors': len(errs),
            'nonAssociative': len([d for x in record['elements'].values() for d in x['dimensions'] if d.get('associative') is False])}

def export_job(doc, key):
    path = os.path.join(OUT, 'room-' + str(key) + '.json'); r = R1.read(path)
    reg = register_font()
    opts = DB.PDFExportOptions(); opts.Combine = True; opts.FileName = 'r4-room-' + str(key)
    opts.PaperFormat = DB.ExportPaperFormat.ISO_A1; opts.PaperOrientation = DB.PageOrientationType.Landscape
    opts.ZoomType = DB.ZoomType.FitToPage; opts.ColorDepth = DB.ColorDepthType.Color; opts.StopOnError = True
    ids = List[DB.ElementId]([el(doc, p['sheet_id']).Id for p in r['pages']])
    r['exported'] = bool(doc.Export(OUT, ids, opts)); r['fontRegister'] = reg
    R1.write(path, r)
    return {'status': 'success', 'exported': r['exported'], 'key': key}

def baseline(doc):
    data = D.physical(doc); write('physical-before', data)
    return {'status': 'success', 'physical': len(data)}

def verify(doc):
    from routes.json_safety import sanitize_for_json
    before = read('physical-before')
    ok = json.loads(json.dumps(sanitize_for_json(D.physical(doc)))) == before
    out = {'status': 'success' if ok else 'error', 'physicalUnchanged': ok, 'physicalElements': len(before), 'at': now()}
    write('verification', out); return out

def reset_job(doc, key):
    path = os.path.join(OUT, 'room-' + str(key) + '.json'); r = R1.read(path)
    ids = [p['sheet_id'] for p in r['pages']] + [r['planId']] + ([r['axoId']] if r.get('axoId') else []) + [x['viewId'] for x in r['elements'].values()]
    def body():
        for i in ids:
            e = el(doc, i)
            if e is not None and isinstance(e, (DB.ViewSheet, DB.View)) and name(e).startswith(('ADER ABR R4', )) or (e is not None and isinstance(e, DB.ViewSheet) and e.SheetNumber.startswith('ABR-R4')):
                doc.Delete(e.Id)
        return len(ids)
    n, checked = guarded(doc, 'ADER ABR R4 - reset ' + str(key), body)
    os.rename(path, path + '.reset-' + datetime.datetime.utcnow().strftime('%H%M%S'))
    doc.Save()
    return {'status': 'success', 'deleted': n, 'physicalChecked': checked}

def check_job(doc):
    out = []
    for fn in sorted(os.listdir(OUT)):
        if not (fn.startswith('room-') and fn.endswith('.json')): continue
        r = R1.read(os.path.join(OUT, fn)); room = el(doc, r['room_id']) if r['room_id'] else None
        for k, x in r['elements'].items():
            v = el(doc, x['viewId']); e = el(doc, k)
            visible = any(eid(q) == int(k) for q in DB.FilteredElementCollector(doc, v.Id).WhereElementIsNotElementType())
            a, b, z0, z1, n = extents(doc, e); mid = (a + b) * .5
            row = {'key': r['key'], 'code': x['code'], 'visible': visible, 'viewDir': xyz(v.ViewDirection), 'normal': xyz(n), 'mid': xyz(mid)}
            if room is not None:
                row['roomPoint'] = xyz(room.Location.Point)
                for s in [1, -1]:
                    q = mid + v.ViewDirection * (s * (host_width(e) / 2 + .6)); q = DB.XYZ(q.X, q.Y, level_of(doc, e).Elevation + 3)
                    row['inRoom' + ('Front' if s > 0 else 'Back')] = room.IsPointInRoom(q)
            out.append(row)
    write('check', out)
    return {'status': 'success', 'rows': len(out), 'notVisible': [(o['key'], o['code']) for o in out if not o['visible']],
            'wrongSide': [(o['key'], o['code']) for o in out if o.get('inRoomBack') and not o.get('inRoomFront')]}

def crop_job(doc, pairs):
    out = []
    for key, code in pairs:
        r = read('room-' + key); x = next(v for k, v in r['elements'].items() if v['code'] == code); k = next(k for k, v in r['elements'].items() if v['code'] == code)
        v = el(doc, x['viewId']); e = el(doc, k); cb = v.CropBox; inv = cb.Transform.Inverse; b = e.get_BoundingBox(None)
        pts = [inv.OfPoint(DB.XYZ(i, j, l)) for i in [b.Min.X, b.Max.X] for j in [b.Min.Y, b.Max.Y] for l in [b.Min.Z, b.Max.Z]]
        far = v.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_OFFSET_FAR)
        out.append({'key': key, 'code': code, 'cropMin': xyz(cb.Min), 'cropMax': xyz(cb.Max), 'basis': [xyz(cb.Transform.Origin), xyz(cb.Transform.BasisX), xyz(cb.Transform.BasisZ)],
                    'elemMin': [min(p_.X for p_ in pts), min(p_.Y for p_ in pts), min(p_.Z for p_ in pts)], 'elemMax': [max(p_.X for p_ in pts), max(p_.Y for p_ in pts), max(p_.Z for p_ in pts)],
                    'far': far.AsDouble() if far else None, 'farClip': v.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING).AsInteger()})
    write('crop-check', out); return {'status': 'success', 'rows': out}

def arc_probe(doc):
    r = read('room-785703'); out = {'views': [], 'openings': []}
    targets = [364138, 1020586, 1020050]
    def walk(g, owner, tr, rows, view_key):
        for o in g:
            if isinstance(o, DB.GeometryInstance):
                walk(o.GetSymbolGeometry(), owner, tr.Multiply(o.Transform) if tr else o.Transform, rows, view_key)
            elif isinstance(o, DB.Solid):
                for ed in o.Edges:
                    c = ed.AsCurve()
                    if isinstance(c, DB.Arc):
                        cc = tr.OfPoint(c.Center) if tr else c.Center
                        rows.append({'owner': owner, 'center': xyz(cc), 'radius_m': c.Radius * M, 'ref': ed.Reference is not None, 'instance': tr is not None,
                                     'stable': ed.Reference.ConvertToStableRepresentation(doc) if ed.Reference else None,
                                     'normal': xyz(tr.OfVector(c.Normal) if tr else c.Normal), 'p0': xyz(tr.OfPoint(c.GetEndPoint(0)) if tr else c.GetEndPoint(0)), 'p1': xyz(tr.OfPoint(c.GetEndPoint(1)) if tr else c.GetEndPoint(1))})
            elif isinstance(o, DB.Arc):
                rows.append({'owner': owner, 'curveArc': True, 'center': xyz(o.Center), 'radius_m': o.Radius * M, 'ref': o.Reference is not None})
    views = [r['planId']] + [x['viewId'] for x in r['elements'].values()]
    for vid in views:
        v = el(doc, vid); rows = []
        opt = DB.Options(); opt.View = v; opt.ComputeReferences = True; opt.IncludeNonVisibleObjects = False
        for t in targets:
            e = el(doc, t); comps = [e]
            if isinstance(e, DB.Wall) and e.CurtainGrid: comps += [doc.GetElement(i) for i in list(e.CurtainGrid.GetPanelIds()) + list(e.CurtainGrid.GetMullionIds())]
            for c in comps:
                try:
                    g = c.get_Geometry(opt)
                    if g: walk(g, (t, eid(c), c.Category.Name), None, rows, vid)
                except Exception as ex: rows.append({'owner': (t, eid(c)), 'error': str(ex)})
        uniq = {}
        for x in rows:
            k = (round(x.get('center', [0])[0], 3), round(x.get('center', [0, 0])[1], 3), round(x.get('center', [0, 0, 0])[2], 3), round(x.get('radius_m', 0), 4), x['owner'][0])
            uniq.setdefault(k, x)
        out['views'].append({'id': vid, 'name': u(name(v)), 'viewDir': xyz(v.ViewDirection), 'arcs': list(uniq.values())[:60], 'arcCount': len(rows)})
    w = el(doc, 364138)
    for o in DB.FilteredElementCollector(doc).OfClass(DB.Opening):
        try:
            if o.Host and eid(o.Host) in targets: out['openings'].append({'id': eid(o), 'host': eid(o.Host), 'rect': o.IsRectBoundary, 'curves': [str(type(c).__name__) for c in o.BoundaryCurves] if not o.IsRectBoundary else None})
        except: pass
    try: out['wallProfileSketch'] = bool(w.SketchId and w.SketchId != DB.ElementId.InvalidElementId)
    except Exception as ex: out['wallProfileSketch'] = str(ex)
    for t in [1020586, 1020050]:
        e = el(doc, t)
        try: out['sketch_' + str(t)] = bool(e.SketchId and e.SketchId != DB.ElementId.InvalidElementId)
        except Exception as ex: out['sketch_' + str(t)] = str(ex)
    write('arc-probe', out)
    return {'status': 'success', 'views': [(x['name'], x['arcCount'], len(x['arcs'])) for x in out['views']], 'openings': out['openings'],
            'sketch': [out.get('wallProfileSketch'), out.get('sketch_1020586'), out.get('sketch_1020050')]}

def run(doc, uidoc, job):
    assert_pilot(doc)
    action = job['action']
    if action == 'r4_probe': raise Exception('probe already recorded')
    if action == 'r4_baseline': return baseline(doc)
    if action == 'r4_setup': return setup(doc)
    if action == 'r4_room': return room_job(doc, job['key'])
    if action == 'r4_export': return export_job(doc, job['key'])
    if action == 'r4_verify': return verify(doc)
    if action == 'r4_check': return check_job(doc)
    if action == 'r4_crop': return crop_job(doc, job['pairs'])
    if action == 'r4_arcs': return arc_probe(doc)
    if action == 'r4_reset': return reset_job(doc, job['key'])
    if action == 'r22_pil': return imp.load_source('ader_pil_r22', os.path.join(ROOT, 'revit_pileta_r22.py')).run(doc, uidoc, job)
    if action == 'r21_cie': return imp.load_source('ader_cie_r21', os.path.join(ROOT, 'revit_ceil_r21.py')).run(doc, uidoc, job)
    if action == 'r20_alb': return imp.load_source('ader_alb_r20', os.path.join(ROOT, 'revit_alb_r20.py')).run(doc, uidoc, job)
    if action == 'r19_clima': return imp.load_source('ader_clima_r19', os.path.join(ROOT, 'revit_clima_r19.py')).run(doc, uidoc, job)
    if action == 'r18_pisos': return imp.load_source('ader_pisos_r18', os.path.join(ROOT, 'revit_pisos_r18.py')).run(doc, uidoc, job)
    if action == 'r17_floors_inv': return imp.load_source('ader_floors_r17', os.path.join(ROOT, 'revit_floors_r17.py')).run(doc, uidoc, job)
    if action == 'r16_cubierta': return imp.load_source('ader_cubierta_r16', os.path.join(ROOT, 'revit_cubierta_r16.py')).run(doc, uidoc, job)
    if action == 'r15_roof_inv': return imp.load_source('ader_roof_r15', os.path.join(ROOT, 'revit_roof_r15.py')).run(doc, uidoc, job)
    if action == 'r14_rubros': return imp.load_source('ader_rubros_r14', os.path.join(ROOT, 'revit_rubros_r14.py')).run(doc, uidoc, job)
    if action == 'r13_mark': return imp.load_source('ader_mark_r13', os.path.join(ROOT, 'revit_mark_r13.py')).run(doc, uidoc, job)
    if action == 'r12_fichas': return imp.load_source('ader_fichas_r12', os.path.join(ROOT, 'revit_fichas_r12.py')).run(doc, uidoc, job)
    if action == 'r11_est': return imp.load_source('ader_structure_r11', os.path.join(ROOT, 'revit_structure_r11.py')).run(doc, uidoc, job)
    if action == 'r10_levels': return imp.load_source('ader_levels_r10', os.path.join(ROOT, 'revit_levels_r10.py')).run(doc, uidoc, job)
    if action == 'r9_survey': return imp.load_source('ader_survey_r9', os.path.join(ROOT, 'revit_survey_r9.py')).run(doc, uidoc, job)
    if action == 'r4_inventory': return imp.load_source('ader_inventory_r4', os.path.join(ROOT, 'revit_inventory_r4.py')).run(doc, uidoc, job)
    raise Exception('Unsupported R4 job: ' + action)
